param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8081,
    [string]$RuntimeDir = "",
    [switch]$NoBuild,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$observerDir = Join-Path $repoRoot "observer\agentsview"
$frontendDir = Join-Path $observerDir "frontend"
$embeddedDist = Join-Path $observerDir "internal\web\dist"
$assetDir = Join-Path $embeddedDist "assets"

function Resolve-CairnRuntimeDir {
    param([string]$Root, [string]$ExplicitRuntimeDir)

    if ($ExplicitRuntimeDir -ne "") {
        if ([System.IO.Path]::IsPathRooted($ExplicitRuntimeDir)) {
            return $ExplicitRuntimeDir
        }
        return Join-Path $Root $ExplicitRuntimeDir
    }

    $candidates = @(
        (Join-Path $Root "cairn\.cairn-runtime"),
        (Join-Path $Root ".cairn-runtime")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path (Join-Path $candidate "observer\runs")) {
            return $candidate
        }
    }

    return $candidates[0]
}

$runtimeDir = Resolve-CairnRuntimeDir -Root $repoRoot -ExplicitRuntimeDir $RuntimeDir

if (-not (Test-Path $observerDir)) {
    throw "Cairn observer source not found: $observerDir"
}

if (-not $NoBuild) {
    $needsBuild = -not (Test-Path $assetDir) -or -not (Get-ChildItem $assetDir -File -ErrorAction SilentlyContinue)
    if ($needsBuild) {
        Write-Host "Observer frontend assets are missing; building frontend..."
        Push-Location $frontendDir
        try {
            npm install
            npm run build
        } finally {
            Pop-Location
        }

        if (Test-Path $embeddedDist) {
            Remove-Item -LiteralPath $embeddedDist -Recurse -Force
        }
        New-Item -ItemType Directory -Path (Split-Path -Parent $embeddedDist) -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $frontendDir "dist") -Destination $embeddedDist -Recurse
        Set-Content -LiteralPath (Join-Path $embeddedDist ".keep") -Value "keep embed dir for generated frontend assets" -Encoding UTF8
    }
}

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

$env:CAIRN_RUNS_DIR = Join-Path $runtimeDir "observer\runs"
$env:AGENTSVIEW_DATA_DIR = Join-Path $runtimeDir "agentsview-data"
$env:CAIRN_ONLY = "1"

Write-Host "Starting Cairn Observer"
Write-Host "  source: $observerDir"
Write-Host "  runs:   $env:CAIRN_RUNS_DIR"
Write-Host "  data:   $env:AGENTSVIEW_DATA_DIR"
Write-Host "  url:    http://${HostAddress}:$Port/"

$args = @("run", "-tags", "fts5", ".\cmd\agentsview", "serve", "--host", $HostAddress, "--port", "$Port")
if ($NoBrowser) {
    $args += "--no-browser"
}

Push-Location $observerDir
try {
    & go @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
