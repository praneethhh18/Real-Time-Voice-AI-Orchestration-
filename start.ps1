# ================================================================
#  Voice AI Demo - One-Click Launcher (Windows)
# ----------------------------------------------------------------
#  What this script does:
#    1. Finds a compatible Python (3.10 / 3.11 / 3.12)
#       Python 3.13+ is rejected because livekit-agents and a few
#       ML deps don't have wheels for it yet.
#    2. Verifies Node is installed and backend\.env exists
#    3. First run only: creates venv, pip install, npm install
#       (also wipes & rebuilds the venv if it was made with a
#        too-new Python)
#    4. Launches 3 PowerShell windows: backend / agent / frontend
#    5. Opens http://localhost:5173 in your browser
#
#  Usage:    .\start.ps1
#  Or:       double-click start.bat
# ================================================================

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

function Section($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Ok($msg)      { Write-Host "[ok]    $msg" -ForegroundColor Green }
function Warn($msg)    { Write-Host "[warn]  $msg" -ForegroundColor Yellow }
function Err($msg)     { Write-Host "[error] $msg" -ForegroundColor Red }


# ---------------- Find a compatible Python ----------------
Section "Locating a compatible Python (3.10 / 3.11 / 3.12)"

# `py` is the Windows Python launcher. It lets us pick a specific version
# regardless of which one comes first on PATH.
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Err "The Windows 'py' launcher is missing. Reinstall Python from https://python.org and"
    Err "tick 'Install launcher for all users' in the installer."
    exit 1
}

$preferred = @("3.11", "3.12", "3.10")
$pyExe = $null
$pyVer = $null

foreach ($v in $preferred) {
    $out = & py "-$v" -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $out) {
        $pyExe = $out.Trim()
        $pyVer = $v
        break
    }
}

if (-not $pyExe) {
    Err "No compatible Python found."
    Err "You need Python 3.10, 3.11, or 3.12 installed. Python 3.13+ is too new for livekit-agents."
    Err ""
    Err "Install it from https://python.org/downloads/release/python-3119/"
    Err "When the installer runs, tick BOTH:"
    Err "   [x] Add python.exe to PATH"
    Err "   [x] Install launcher for all users (recommended)"
    exit 1
}

Ok "Using Python $pyVer at $pyExe"


# ---------------- Other pre-flight checks ----------------
Section "Pre-flight checks"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Err "Node.js is not on PATH. Install Node 18+ from https://nodejs.org and re-run."
    exit 1
}
Ok "Node found: $(node --version)"

if (-not (Test-Path "$root\backend\.env")) {
    Err "backend\.env is missing. Copy backend\.env.example to backend\.env and fill in your keys."
    exit 1
}
Ok "backend\.env present"


# ---------------- Backend setup (first run only) ----------------
Section "Backend setup"

$venvPath     = "$root\backend\.venv"
$venvPython   = "$venvPath\Scripts\python.exe"
$venvActivate = "$venvPath\Scripts\Activate.ps1"

# If a venv exists but was built with the WRONG Python (e.g. 3.14),
# wipe it so we don't keep failing in the same way.
if (Test-Path $venvPython) {
    $existingVer = & $venvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    if ($existingVer -and $existingVer -ne $pyVer) {
        Warn "Existing venv was built with Python $existingVer; rebuilding with Python $pyVer..."
        Remove-Item -Recurse -Force $venvPath
    }
}

if (-not (Test-Path $venvActivate)) {
    Warn "Creating Python $pyVer virtual environment (one-time)..."
    Push-Location "$root\backend"
    & $pyExe -m venv .venv
    Pop-Location
    Ok "Virtual environment created"
} else {
    Ok "Virtual environment already exists (Python $pyVer)"
}

# Marker: presence of the `livekit` package folder tells us deps installed.
$reqMarker = "$venvPath\Lib\site-packages\livekit"
if (-not (Test-Path $reqMarker)) {
    Warn "Installing Python dependencies (this can take 3-5 minutes the first time)..."
    Push-Location "$root\backend"
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Err "pip install failed. See the error above."
        Pop-Location
        exit 1
    }
    Pop-Location
    Ok "Python dependencies installed"
} else {
    Ok "Python dependencies already installed"
}

# Pre-download the embedding model. Without this, the FIRST call after a
# fresh install waits ~25s for sentence-transformers to fetch
# all-MiniLM-L6-v2 from Hugging Face — that exceeds LiveKit's IPC init
# timeout and breaks the very first call. Once cached locally
# (~/.cache/huggingface/), subsequent calls reuse the cache and this is
# a no-op.
$modelMarker = "$env:USERPROFILE\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2"
if (-not (Test-Path $modelMarker)) {
    Warn "Pre-downloading embedding model (one-time, ~80 MB)..."
    & $venvPython -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
    if ($LASTEXITCODE -ne 0) {
        Warn "Model pre-download failed; agent will retry on first call (slower)."
    } else {
        Ok "Embedding model cached"
    }
} else {
    Ok "Embedding model already cached"
}


# ---------------- Frontend setup (first run only) ----------------
Section "Frontend setup"

if (-not (Test-Path "$root\frontend\node_modules")) {
    Warn "Installing Node dependencies (one-time)..."
    Push-Location "$root\frontend"
    npm install
    Pop-Location
    Ok "Node dependencies installed"
} else {
    Ok "Node dependencies already installed"
}


# ---------------- Launch the three services ----------------
Section "Launching services"

# Each service runs in its own PowerShell window so logs are visible
# and you can Ctrl+C any one independently.

# 1. FastAPI backend (port 8000)
$backendCmd = "Set-Location '$root\backend'; .\.venv\Scripts\Activate.ps1; " + `
              "Write-Host '== Backend API on http://localhost:8000 ==' -ForegroundColor Cyan; " + `
              "uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCmd
Ok "Started backend window (port 8000)"
Start-Sleep -Seconds 2

# 2. LiveKit voice agent worker
$agentCmd = "Set-Location '$root\backend'; .\.venv\Scripts\Activate.ps1; " + `
            "Write-Host '== Voice Agent worker ==' -ForegroundColor Cyan; " + `
            "python -m app.agent.voice_agent dev"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $agentCmd
Ok "Started agent window"
Start-Sleep -Seconds 2

# 3. React frontend (Vite dev server, port 5173)
$frontendCmd = "Set-Location '$root\frontend'; " + `
               "Write-Host '== Frontend on http://localhost:5173 ==' -ForegroundColor Cyan; " + `
               "npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCmd
Ok "Started frontend window (port 5173)"


# ---------------- Wait + open browser ----------------
Section "Waiting for services to come up"
$waitSeconds = 10
for ($i = $waitSeconds; $i -gt 0; $i--) {
    Write-Host "  Opening browser in $i seconds...`r" -NoNewline
    Start-Sleep -Seconds 1
}
Write-Host ""

Start-Process "http://localhost:5173"
Ok "Opened http://localhost:5173"


# ---------------- Final summary ----------------
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Demo is up. Three terminal windows are running:" -ForegroundColor Green
Write-Host "    1. Backend API   - http://localhost:8000  (Swagger: /docs)"
Write-Host "    2. Voice Agent   - connects to LiveKit Cloud"
Write-Host "    3. Frontend      - http://localhost:5173"
Write-Host ""
Write-Host "  To stop everything:" -ForegroundColor Yellow
Write-Host "    Close the three terminal windows, or run: .\stop.ps1"
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to close this launcher window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
