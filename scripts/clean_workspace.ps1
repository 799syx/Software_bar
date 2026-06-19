param(
    [switch]$Dist,
    [switch]$Database,
    [switch]$NodeModules,
    [switch]$Screenshots,
    [switch]$Delivery,
    [switch]$All
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

function Remove-InWorkspace {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [switch]$Recurse
    )

    $resolvedItems = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue
    foreach ($item in $resolvedItems) {
        $fullPath = $item.Path
        if (-not $fullPath.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove path outside workspace: $fullPath"
        }
        try {
            Remove-Item -LiteralPath $fullPath -Force -Recurse:$Recurse -ErrorAction Stop
            Write-Host "Removed $fullPath"
        } catch {
            Write-Warning "Could not remove ${fullPath}: $($_.Exception.Message)"
        }
    }
}

Get-ChildItem -LiteralPath $Root -Directory -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "\\frontend-vue\\node_modules(\\|$)" } |
    ForEach-Object { Remove-InWorkspace -Path $_.FullName -Recurse }

foreach ($basePath in @((Join-Path $Root "backend"), (Join-Path $Root "tests"))) {
    if (Test-Path -LiteralPath $basePath) {
        Get-ChildItem -LiteralPath $basePath -File -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue |
            ForEach-Object { Remove-InWorkspace -Path $_.FullName }
    }
}

Get-ChildItem -LiteralPath $Root -File -Recurse -Filter "*.log" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-InWorkspace -Path $_.FullName }

Remove-InWorkspace -Path (Join-Path $Root ".tmp") -Recurse
Remove-InWorkspace -Path (Join-Path $Root "tests\probe") -Recurse

if ($Delivery) {
    $Dist = $true
    $Database = $true
    $NodeModules = $true
    $Screenshots = $true
}

if ($Dist -or $All) {
    Remove-InWorkspace -Path (Join-Path $Root "frontend-vue\dist") -Recurse
}

if ($Database -or $All) {
    Remove-InWorkspace -Path (Join-Path $Root "backend\data\scenic_guide.db")
    Remove-InWorkspace -Path (Join-Path $Root "backend\data\behavior_analytics_cache.json")
    Remove-InWorkspace -Path (Join-Path $Root "backend\data\tmp") -Recurse
    Remove-InWorkspace -Path (Join-Path $Root "tests\probe") -Recurse
}

if ($NodeModules -or $All) {
    Remove-InWorkspace -Path (Join-Path $Root "frontend-vue\node_modules") -Recurse
}

if ($Screenshots -or $All) {
    foreach ($pattern in @("screenshot-*.png", "屏幕截图*.png", "屏幕录制*.mp4", "jimeng-*.png")) {
        Get-ChildItem -LiteralPath $Root -File -Filter $pattern -ErrorAction SilentlyContinue |
            ForEach-Object { Remove-InWorkspace -Path $_.FullName }
    }
}

if ($Delivery) {
    Remove-InWorkspace -Path (Join-Path $Root ".env")
    Remove-InWorkspace -Path (Join-Path $Root "backend\.env")
    Remove-InWorkspace -Path (Join-Path $Root "frontend-vue\.env")
}

Write-Host "Workspace cleanup complete."
