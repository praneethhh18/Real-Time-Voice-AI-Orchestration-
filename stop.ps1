# ================================================================
#  Voice AI Demo - Stop everything
# ----------------------------------------------------------------
#  Kills the 3 child processes started by start.ps1 (uvicorn, the
#  agent worker, the Vite dev server) by matching their command lines.
#
#  This is a "best effort" cleanup — if it misses anything, just
#  close the 3 terminal windows by hand.
# ================================================================

$ErrorActionPreference = "Continue"

function StopMatching($pattern, $label) {
    $procs = Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -match $pattern }

    if ($procs) {
        foreach ($p in $procs) {
            Write-Host "Stopping $label (PID $($p.ProcessId))..." -ForegroundColor Yellow
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }
    } else {
        Write-Host "No $label process found." -ForegroundColor Gray
    }
}

Write-Host "Stopping voice-AI demo services..." -ForegroundColor Cyan
StopMatching "uvicorn"                       "FastAPI backend"
StopMatching "app\.agent\.voice_agent"       "LiveKit agent worker"
StopMatching "vite"                          "Vite dev server"
Write-Host "Done. (If any windows are still open, close them manually.)" -ForegroundColor Green
