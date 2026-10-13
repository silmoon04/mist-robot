param(
    [string]$Distribution = 'Ubuntu',
    [string]$WslRepo = '/home/hssil/mist-locomotion-msi/repo',
    [switch]$Stop,
    [switch]$Status,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'

function ConvertTo-NativeArgument([string]$Value) {
    if ($Value.Contains('"') -or $Value.Contains('\') -or $Value.Contains("`n") -or $Value.Contains("`r")) {
        throw 'Use a WSL distribution name and absolute Linux repository path without quotes or backslashes.'
    }
    if ($Value -match '\s') { return '"' + $Value + '"' }
    return $Value
}

try {
    if (-not $WslRepo.StartsWith('/')) { throw 'WslRepo must be an absolute Linux path.' }
    if ($Stop -and $Status) { throw 'Choose Stop or Status.' }
    $WslRepo = $WslRepo.TrimEnd('/')
    $PythonPath = "$WslRepo/.venv-locomotion/bin/python"
    $ManagerPath = "$WslRepo/locomotion/scripts/remote_session_smooth.py"
    $BaseArguments = @('--distribution', $Distribution, '--exec', $PythonPath, $ManagerPath)
    if ($Stop -or $Status) {
        $Action = if ($Stop) { 'stop' } else { 'status' }
        & wsl.exe @BaseArguments $Action
        exit $LASTEXITCODE
    }
    $ArgumentLine = (($BaseArguments + @('run')) | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' '
    $LogRoot = Join-Path (Split-Path $PSScriptRoot -Parent) '.remote-session'
    New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null
    $Invocation = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
    $OutLog = Join-Path $LogRoot "launcher-$Invocation.out.log"
    $ErrorLog = Join-Path $LogRoot "launcher-$Invocation.err.log"
    $Launcher = Start-Process -FilePath 'wsl.exe' -ArgumentList $ArgumentLine -WindowStyle Hidden `
        -RedirectStandardOutput $OutLog -RedirectStandardError $ErrorLog -PassThru
    Write-Host 'Opening smooth MIST simulation and joint preview...'
    $Deadline = [DateTime]::UtcNow.AddSeconds(35)
    $Ready = $false
    while ([DateTime]::UtcNow -lt $Deadline) {
        $Launcher.Refresh()
        if ($Launcher.HasExited) {
            $Launcher.WaitForExit()
            if ($null -ne $Launcher.ExitCode -and $Launcher.ExitCode -ne 0) { throw "Session startup failed. Read $ErrorLog." }
            if ((Test-Path -LiteralPath $ErrorLog) -and (Get-Item -LiteralPath $ErrorLog).Length -gt 0) {
                throw "Session startup failed. Read $ErrorLog."
            }
        }
        $Acknowledged = $false
        try {
            $Started = Get-Content -LiteralPath $OutLog -Raw | ConvertFrom-Json
            $Acknowledged = ($Started.managed_session -and $Started.services.simulation.ready -and $Started.services.joints.ready)
        } catch { }
        try {
            $Sim = Invoke-RestMethod 'http://127.0.0.1:8131/api/state' -TimeoutSec 2
            $Joints = Invoke-RestMethod 'http://127.0.0.1:8130/api/status' -TimeoutSec 2
            $Ready = ($Acknowledged -and $null -ne $Sim.controller -and $Joints.mode -eq 'dry-run' -and $Joints.q.Count -eq 12)
            if ($Ready) { break }
        } catch { }
        Start-Sleep -Milliseconds 300
    }
    if (-not $Ready) {
        throw "Remotes did not become ready. Read $ErrorLog and $WslRepo/locomotion/.remote-session/*.log."
    }
    Write-Host 'Simulation: http://127.0.0.1:8131/'
    Write-Host 'Joint preview (dry-run): http://127.0.0.1:8130/'
    if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:8131/' }
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
