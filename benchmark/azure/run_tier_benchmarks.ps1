# Run ChorusGraph MVP benchmarks on Azure for mid (100) and/or heavy (300) task tiers.
# Builds the ACR image once, then launches one-shot ACIs sequentially.
#
# Examples:
#   .\benchmark\azure\run_tier_benchmarks.ps1 -Tiers both -Wait
#   .\benchmark\azure\run_tier_benchmarks.ps1 -Tiers mid -Wait -Cleanup
#   .\benchmark\azure\run_tier_benchmarks.ps1 -Tiers heavy -SkipBuild -Wait
param(
    [ValidateSet("light", "mid", "heavy", "both", "light_mid")]
    [string]$Tiers = "both",
    [int]$Seed = 42,
    [string]$Scenarios = "all",
    [switch]$SkipBuild,
    [switch]$Wait,
    [switch]$Cleanup,
    [string]$ResourceGroup = "chorus-rg-us"
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Deploy = Join-Path $ScriptDir "deploy_and_run.ps1"

$tierList = switch ($Tiers) {
    "both"      { @("mid", "heavy") }
    "light_mid" { @("light", "mid") }
    default     { @($Tiers) }
}

$tierMeta = @{
    light = @{ tasks = 40;  cpu = 4; memory = 8;  label = "smoke (40 tasks/scenario)" }
    mid   = @{ tasks = 100; cpu = 4; memory = 8;  label = "regression (100 tasks/scenario)" }
    heavy = @{ tasks = 300; cpu = 4; memory = 16; label = "scale (300 tasks/scenario)" }
}

Write-Host "==> ChorusGraph Azure tier benchmarks"
Write-Host "    Tiers:     $($tierList -join ', ')"
Write-Host "    Scenarios: $Scenarios | Seed: $Seed"
Write-Host "    Cleanup:   $Cleanup"
Write-Host ""

$runIds = @{}
$buildSkipped = $SkipBuild
# Sequential tiers must wait for each run to finish before starting the next.
$effectiveWait = $Wait -or ($tierList.Count -gt 1)
if ($tierList.Count -gt 1 -and -not $Wait) {
    Write-Host "NOTE: -Tiers both implies -Wait (sequential). Waiting for each tier to finish."
}

foreach ($tier in $tierList) {
    $meta = $tierMeta[$tier]
    $containerName = "chorus-mvp-benchmark-$tier"

    Write-Host "========================================"
    Write-Host "TIER: $tier - $($meta.label)"
    Write-Host "  container: $containerName"
    Write-Host "  size:      $($meta.cpu) vCPU / $($meta.memory) GB"
    Write-Host "  total runs: $($meta.tasks) tasks x 8 scenarios = $($meta.tasks * 8) scenario-runs"
    Write-Host "========================================"

    $deployParams = @{
        Tier           = $tier
        ContainerName  = $containerName
        Cpu            = [int]$meta.cpu
        MemoryGb       = [double]$meta.memory
        Seed           = $Seed
        Scenarios      = $Scenarios
        ResourceGroup  = $ResourceGroup
    }
    if ($buildSkipped) { $deployParams.SkipBuild = $true }
    if ($effectiveWait) { $deployParams.Wait = $true }
    if ($Cleanup) { $deployParams.Cleanup = $true }

    $runId = & $Deploy @deployParams
    if ($LASTEXITCODE -ne 0) { throw "deploy_and_run failed for tier=$tier" }
    $runIds[$tier] = $runId.Trim()
    Write-Host "    run_id: $($runIds[$tier])"
    Write-Host ""

  # Only build on first tier
    $buildSkipped = $true
}

Write-Host "==> Tier benchmark launch complete"
foreach ($tier in $tierList) {
    Write-Host "  $tier -> run_id=$($runIds[$tier]) blob://benchmark-results/mvp_scenarios/$($runIds[$tier])/"
}
if (-not $Wait -and -not $effectiveWait) {
    Write-Host ""
    Write-Host "Follow logs:"
    foreach ($tier in $tierList) {
        $cname = "chorus-mvp-benchmark-$tier"
        Write-Host "  az container logs -g $ResourceGroup -n $cname --follow"
    }
}

# Emit JSON summary for CI / scripting
[PSCustomObject]@{
    tiers  = $runIds
    seed   = $Seed
    when   = (Get-Date).ToUniversalTime().ToString('o')
} | ConvertTo-Json
