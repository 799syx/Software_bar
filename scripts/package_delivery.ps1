param(
    [string]$OutputDir = "delivery",
    [switch]$IncludeDist,
    [switch]$IncludeDemoDatabase
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

if ([System.IO.Path]::IsPathRooted($OutputDir)) {
    $DeliveryDir = $OutputDir
} else {
    $DeliveryDir = Join-Path $Root $OutputDir
}

$DeliveryDir = [System.IO.Path]::GetFullPath($DeliveryDir)
if (-not $DeliveryDir.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputDir must be inside the workspace: $DeliveryDir"
}

New-Item -ItemType Directory -Force -Path $DeliveryDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ZipPath = Join-Path $DeliveryDir "scenic-guide-delivery-$Timestamp.zip"

function Test-RelativePrefix {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][string]$Prefix
    )
    return $RelativePath -eq $Prefix -or $RelativePath.StartsWith("$Prefix/", [System.StringComparison]::OrdinalIgnoreCase)
}

function Should-Exclude {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath
    )

    $path = $RelativePath.Replace("\", "/")
    $fileName = [System.IO.Path]::GetFileName($path)

    if (Test-RelativePrefix $path ".git") { return $true }
    if (Test-RelativePrefix $path "delivery") { return $true }
    if (Test-RelativePrefix $path ".tmp") { return $true }
    if (Test-RelativePrefix $path "tests/probe") { return $true }
    if (Test-RelativePrefix $path "backend/data/tmp") { return $true }
    if (Test-RelativePrefix $path "frontend-vue/node_modules") { return $true }
    if (-not $IncludeDist -and (Test-RelativePrefix $path "frontend-vue/dist")) { return $true }

    if ($path -match "(^|/)__pycache__(/|$)") { return $true }
    if ($path -match "(^|/)\.pytest_cache(/|$)") { return $true }
    if ($path -match "(^|/)\.ruff_cache(/|$)") { return $true }
    if ($path -match "(^|/)\.mypy_cache(/|$)") { return $true }

    if ($fileName -match "^\.env($|\.|-)") { return $true }
    if ($path -in @("backend/.env", "frontend-vue/.env")) { return $true }
    if ($fileName -match "\.pyc$|\.log$|\.tmp$") { return $true }
    if ($fileName -match "^screenshot-.*\.png$|^jimeng-.*\.png$") { return $true }
    if ($fileName -match "^屏幕截图.*\.png$|^屏幕录制.*\.mp4$") { return $true }
    if ($fileName -match "\.zip$") { return $true }

    if (-not $IncludeDemoDatabase -and $path -match "^backend/data/.*\.(db|db-journal|sqlite|sqlite3)$") { return $true }
    if ($path -eq "backend/data/behavior_analytics_cache.json") { return $true }

    return $false
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

$zip = [System.IO.Compression.ZipFile]::Open($ZipPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    $rootPrefixLength = $Root.TrimEnd("\").Length + 1
    $files = Get-ChildItem -LiteralPath $Root -File -Recurse -Force
    foreach ($file in $files) {
        $fullPath = $file.FullName
        if (-not $fullPath.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to package path outside workspace: $fullPath"
        }
        $relativePath = $fullPath.Substring($rootPrefixLength).Replace("\", "/")
        if (Should-Exclude -RelativePath $relativePath) {
            continue
        }
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $zip,
            $fullPath,
            $relativePath,
            [System.IO.Compression.CompressionLevel]::Optimal
        ) | Out-Null
    }
} finally {
    $zip.Dispose()
}

$sizeMb = [Math]::Round((Get-Item -LiteralPath $ZipPath).Length / 1MB, 2)
Write-Host "Delivery package created: $ZipPath ($sizeMb MB)"
Write-Host "Default database mode: startup rebuilds backend/data/scenic_guide.db from seed and public data."
