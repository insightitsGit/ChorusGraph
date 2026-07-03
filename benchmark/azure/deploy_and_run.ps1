# Deploy ChorusGraph MVP benchmark to Azure Container Instances (ACI).
# Does NOT use VMs — builds in ACR, runs as a one-shot container in chorus-rg-us.
param(
    [string]$ResourceGroup = "chorus-rg-us",
    [string]$AcrName = "chorusacrd7a6d0",
    [string]$AcrResourceGroup = "chorus-rg-acr",
    [string]$ContainerName = "chorus-mvp-benchmark",
    [string]$ImageTag = "chorusgraph-mvp-benchmark:latest",
    [string]$Location = "eastus",
    [int]$Cpu = 4,
    [double]$MemoryGb = 8,
    [int]$Tasks = 12,
    [int]$Seed = 42,
    [int]$RepeatBand = 40,
    [string]$Scenarios = "all",
    [string]$StorageAccount = "stinsightitsprod01",
    [string]$StorageResourceGroup = "rg-insightits-prod",
    [string]$BlobContainer = "benchmark-results",
    [switch]$SkipBuild,
    [switch]$Wait
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $RepoRoot

function Read-DotEnvKey {
    param([string]$Key)
    $envFile = Join-Path $RepoRoot ".env"
    if (-not (Test-Path $envFile)) { return $null }
    foreach ($line in Get-Content $envFile) {
        if ($line -match "^\s*$Key\s*=\s*(.+)$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

$geminiKey = $env:GEMINI_API_KEY
if (-not $geminiKey) { $geminiKey = Read-DotEnvKey "GEMINI_API_KEY" }
if (-not $geminiKey) {
    Write-Error "GEMINI_API_KEY not set in environment or .env"
}

$runId = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
$loginServer = az acr show -n $AcrName -g $AcrResourceGroup --query loginServer -o tsv
$image = "$loginServer/$ImageTag"

Write-Host "==> ChorusGraph MVP benchmark on Azure Container Instances"
Write-Host "    ACR:       $loginServer"
Write-Host "    Image:     $image"
Write-Host "    Container: $ContainerName ($ResourceGroup)"
Write-Host "    Run ID:    $runId"
Write-Host "    Scenarios: $Scenarios | Tasks: $Tasks | Seed: $Seed"

if (-not $SkipBuild) {
    Write-Host "`n==> Building image in ACR (az acr build)..."
    $env:PYTHONIOENCODING = "utf-8"
    $env:AZURE_CORE_NO_COLOR = "true"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    az acr build `
        --registry $AcrName `
        --resource-group $AcrResourceGroup `
        --image $ImageTag `
        --file benchmark/azure/Dockerfile `
        --platform linux `
        $RepoRoot 2>&1 | Out-String | Write-Host
    $buildExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($buildExit -ne 0) {
        Write-Host "    (log stream error; polling ACR build status...)"
    }
    $pollMax = 900
    $polled = 0
    $buildStatus = az acr task list-runs -r $AcrName --top 1 --query "[0].status" -o tsv
    while ($buildStatus -eq "Running" -and $polled -lt $pollMax) {
        Start-Sleep -Seconds 15
        $polled += 15
        $buildStatus = az acr task list-runs -r $AcrName --top 1 --query "[0].status" -o tsv
        Write-Host "    ACR build: $buildStatus (${polled}s)"
    }
    if ($buildStatus -ne "Succeeded") { throw "ACR build failed (status=$buildStatus)" }
    if ($buildExit -ne 0) { Write-Host "    (log stream error ignored; remote build Succeeded)" }
}

$creds = az acr credential show -n $AcrName -g $AcrResourceGroup | ConvertFrom-Json
$acrUser = $creds.username
$acrPass = $creds.passwords[0].value

Write-Host "`n==> Ensuring blob container '$BlobContainer' exists..."
$storageKey = az storage account keys list -g $StorageResourceGroup -n $StorageAccount --query "[0].value" -o tsv
az storage container create `
    --name $BlobContainer `
    --account-name $StorageAccount `
    --account-key $storageKey `
    --auth-mode key `
    -o none 2>$null

$connStr = az storage account show-connection-string `
    -g $StorageResourceGroup `
    -n $StorageAccount `
    --query connectionString -o tsv

Write-Host "`n==> Removing previous container instance (if any)..."
az container delete -g $ResourceGroup -n $ContainerName --yes 2>$null | Out-Null
Start-Sleep -Seconds 5

Write-Host "`n==> Creating ACI (one-shot, restart-policy Never)..."
az container create `
    --resource-group $ResourceGroup `
    --name $ContainerName `
    --location $Location `
    --image $image `
    --registry-login-server $loginServer `
    --registry-username $acrUser `
    --registry-password $acrPass `
    --cpu $Cpu `
    --memory ($MemoryGb) `
    --restart-policy Never `
    --os-type Linux `
    --secure-environment-variables "GEMINI_API_KEY=$geminiKey" "AZURE_STORAGE_CONNECTION_STRING=$connStr" `
    --environment-variables `
        "BENCHMARK_RUN_ID=$runId" `
        "BENCHMARK_SCENARIOS=$Scenarios" `
        "BENCHMARK_TASKS=$Tasks" `
        "BENCHMARK_SEED=$Seed" `
        "BENCHMARK_REPEAT_BAND=$RepeatBand" `
        "BENCHMARK_BLOB_CONTAINER=$BlobContainer" `
        "BENCHMARK_OUTPUT_DIR=/results/mvp_scenarios" `
    -o json | Out-Null

if ($LASTEXITCODE -ne 0) { throw "az container create failed" }

Write-Host "`n==> Container started. Logs: az container logs -g $ResourceGroup -n $ContainerName --follow"
Write-Host "    Results blob prefix: mvp_scenarios/$runId/"

if ($Wait) {
    Write-Host "`n==> Waiting for container to finish..."
    do {
        Start-Sleep -Seconds 30
        $state = az container show -g $ResourceGroup -n $ContainerName --query "instanceView.state" -o tsv
        Write-Host "    state: $state ($(Get-Date -Format 'HH:mm:ss'))"
    } while ($state -eq "Running")

    Write-Host "`n==> Container logs (tail):"
    az container logs -g $ResourceGroup -n $ContainerName 2>&1 | Select-Object -Last 80

    $localOut = Join-Path $RepoRoot "benchmark/results/azure_$runId"
    New-Item -ItemType Directory -Force -Path $localOut | Out-Null

    Write-Host "`n==> Downloading results from blob..."
    az storage blob download-batch `
        --destination $localOut `
        --source $BlobContainer `
        --pattern "mvp_scenarios/$runId/*" `
        --account-name $StorageAccount `
        --account-key $storageKey `
        -o none

    Write-Host "`n==> Local results: $localOut"
    $report = Get-ChildItem -Path $localOut -Recurse -Filter "COMPARISON_REPORT.md" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($report) {
        Write-Host "`n========== COMPARISON REPORT =========="
        Get-Content $report.FullName
    }
}

Write-Output $runId
