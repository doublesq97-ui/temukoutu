$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$pidFile = Join-Path $root 'artifacts\server.pid'
if (Test-Path -LiteralPath $pidFile) {
    $serverPid = [int](Get-Content -LiteralPath $pidFile)
    # Verify process ownership instead of trusting a possibly stale PID file.
    try {
        $server = Get-CimInstance Win32_Process -Filter "ProcessId=$serverPid"
        if ($server -and $server.CommandLine -match 'uvicorn backend.app.main:app' -and $server.ExecutablePath -eq (Join-Path $root '.venv\Scripts\python.exe')) {
            # Windows venv python.exe can be a redirector with a child interpreter.
            $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$serverPid")
            foreach ($child in $children) {
                if ($child.CommandLine -match 'uvicorn backend.app.main:app') {
                    Stop-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
                }
            }
            Stop-Process -Id $serverPid -ErrorAction SilentlyContinue
            Remove-Item -LiteralPath $pidFile
            Write-Host 'Application stopped.'
        } else { throw 'PID does not match this application. Close the matching Python process manually.' }
    } catch { Write-Error "Cannot verify process owner: $_"; exit 1 }
} else { Write-Host 'No server.pid found.' }
