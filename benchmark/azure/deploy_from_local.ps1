# Sync ChorusGraph to Azure VM and run tests.
param(
    [string]$Branch = "master",
    [int]$Tasks = 30,
    [int]$Seed = 42,
    [switch]$RunBenchmark
)

$ErrorActionPreference = "Stop"
$Az = "az"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$SyncScript = Join-Path $PSScriptRoot "sync_and_test.sh"
$BenchFlag = if ($RunBenchmark) { "1" } else { "0" }
$GhToken = ""
try {
    $GhToken = (& gh auth token 2>$null).Trim()
} catch {
    Write-Warning "gh auth token unavailable — private clone may fail on VM"
}

$Remote = @"
#!/bin/bash
set -euo pipefail
export REPO_DIR=/opt/insightits/ChorusGraph
export BRANCH=$Branch
export RUN_BENCHMARK=$BenchFlag
export TASKS=$Tasks
export SEED=$Seed
export GITHUB_TOKEN=$GhToken
$(Get-Content $SyncScript -Raw)
"@

$Tmp = Join-Path $env:TEMP "chorusgraph_azure_sync.sh"
Set-Content -Path $Tmp -Value $Remote -Encoding UTF8

Write-Host "Deploying to vm-insightits-prod (branch=$Branch, benchmark=$BenchFlag)..."
$result = & $Az vm run-command invoke `
    --resource-group RG-INSIGHTITS-PROD `
    --name vm-insightits-prod `
    --command-id RunShellScript `
    --scripts "@$Tmp" `
    -o json | ConvertFrom-Json

$msg = $result.value[0].message
if ($msg -match '\[stdout\]([\s\S]*?)(\[stderr\]|$)') {
    Write-Host $Matches[1].Trim()
}
if ($msg -match '\[stderr\]([\s\S]*)') {
  $err = $Matches[1].Trim()
  if ($err) { Write-Host $err -ForegroundColor Yellow }
}
