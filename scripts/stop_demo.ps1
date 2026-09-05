param(
    [int[]]$Ports = @(8000, 5173, 8010),
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Get-ListeningProcess {
    param([int[]]$TargetPorts)

    $connections = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $TargetPorts -contains $_.LocalPort }

    foreach ($connection in $connections) {
        $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
        if (-not $process) {
            continue
        }
        [pscustomobject]@{
            Port = $connection.LocalPort
            Id = $process.Id
            Name = $process.ProcessName
            Path = $process.Path
        }
    }
}

$targets = Get-ListeningProcess -TargetPorts $Ports |
    Sort-Object Port, Id -Unique

if (-not $targets) {
    Write-Host "No demo processes are listening on ports: $($Ports -join ', ')."
    exit 0
}

Write-Host "Demo processes found:"
$targets | Format-Table Port, Id, Name, Path -AutoSize

if ($DryRun) {
    Write-Host "Dry run only. No process was stopped."
    exit 0
}

foreach ($target in $targets) {
    try {
        Stop-Process -Id $target.Id -Force -ErrorAction Stop
        Write-Host "Stopped PID $($target.Id) on port $($target.Port) ($($target.Name))."
    } catch {
        Write-Warning "Failed to stop PID $($target.Id) on port $($target.Port): $($_.Exception.Message)"
    }
}

Start-Sleep -Milliseconds 500
$remaining = Get-ListeningProcess -TargetPorts $Ports
if ($remaining) {
    Write-Warning "Some ports are still occupied:"
    $remaining | Format-Table Port, Id, Name, Path -AutoSize
    exit 1
}

Write-Host "Demo ports released: $($Ports -join ', ')."
