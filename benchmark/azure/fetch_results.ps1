# Download MVP benchmark results from Azure Blob after ACI run.
param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$StorageAccount = "stinsightitsprod01",
    [string]$StorageResourceGroup = "rg-insightits-prod",
    [string]$BlobContainer = "benchmark-results",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $OutputDir) {
    $OutputDir = Join-Path $RepoRoot "benchmark/results/azure_$RunId"
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$storageKey = az storage account keys list -g $StorageResourceGroup -n $StorageAccount --query "[0].value" -o tsv
az storage blob download-batch `
    --destination $OutputDir `
    --source $BlobContainer `
    --pattern "mvp_scenarios/$RunId/*" `
    --account-name $StorageAccount `
    --account-key $storageKey

Write-Host "Downloaded to $OutputDir"
$report = Get-ChildItem -Path $OutputDir -Recurse -Filter "COMPARISON_REPORT.md" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($report) { Get-Content $report.FullName }
