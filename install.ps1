# ╔══════════════════════════════════════════════════════════════════╗
# ║           TRANSCRIBE-AI  ·  Windows Installer (PowerShell)      ║
# ╚══════════════════════════════════════════════════════════════════╝
#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step  { param($msg) Write-Host "▶ $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "  ✅ $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "  ⚠️  $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "  ❌ $msg" -ForegroundColor Red }

Write-Host @"

  TRANSCRIBE-AI  ·  Windows Installer
  Powered by Groq Whisper · pyannote.audio · ffmpeg

"@ -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigDir  = Join-Path $env:APPDATA "transcribe"
$ConfigFile = Join-Path $ConfigDir "config"

# ── Python ──────────────────────────────────────────────────────────
Write-Step "Checking Python"
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3") { $python = $cmd; break }
    } catch { }
}
if (-not $python) {
    Write-Fail "Python 3 not found. Download from https://python.org (check 'Add to PATH')"
    exit 1
}
Write-Ok "Found $(&$python --version 2>&1) at $(Get-Command $python | Select-Object -ExpandProperty Source)"

# ── ffmpeg ──────────────────────────────────────────────────────────
Write-Step "Checking ffmpeg"
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Ok "ffmpeg found"
} else {
    Write-Warn "ffmpeg not found."
    Write-Host "     Install options:"
    Write-Host "       winget:     winget install Gyan.FFmpeg"
    Write-Host "       chocolatey: choco install ffmpeg"
    Write-Host "       scoop:      scoop install ffmpeg"
    Write-Host "       manual:     https://ffmpeg.org/download.html"
    $ans = Read-Host "     Continue without ffmpeg? (y/N)"
    if ($ans -notmatch "^[Yy]") { exit 1 }
}

# ── pip dependencies ─────────────────────────────────────────────────
Write-Step "Installing Python dependencies"
& $python -m pip install --quiet --upgrade pip
& $python -m pip install --quiet -r (Join-Path $ScriptDir "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Fail "pip install failed. Check your internet connection."
    exit 1
}
Write-Ok "Dependencies installed"

# ── Config directory ─────────────────────────────────────────────────
Write-Step "Setting up config"
if (-not (Test-Path $ConfigDir)) { New-Item -ItemType Directory -Path $ConfigDir | Out-Null }
if (-not (Test-Path $ConfigFile)) { New-Item -ItemType File -Path $ConfigFile | Out-Null }
Write-Ok "Config: $ConfigFile"

# ── GROQ_API_KEY ──────────────────────────────────────────────────────
Write-Host ""
$groqKey = ""
if (Test-Path $ConfigFile) {
    $groqKey = (Get-Content $ConfigFile | Where-Object { $_ -match "^GROQ_API_KEY=" } |
        ForEach-Object { ($_ -split "=",2)[1].Trim('"') } | Select-Object -First 1)
}
if (-not $groqKey) { $groqKey = $env:GROQ_API_KEY }

if ($groqKey) {
    Write-Ok "GROQ_API_KEY already configured"
} else {
    Write-Host "▶ Groq API Key required" -ForegroundColor Cyan
    Write-Host "  Free Whisper transcription — no credit card needed."
    Write-Host "  Get your key at: https://console.groq.com"
    Write-Host ""
    $groqKey = Read-Host "  Paste your GROQ_API_KEY (or press Enter to skip)"
    if ($groqKey) {
        Add-Content -Path $ConfigFile -Value "GROQ_API_KEY=`"$groqKey`""
        Write-Ok "GROQ_API_KEY saved to $ConfigFile"
    } else {
        Write-Warn "Skipped — add later: echo 'GROQ_API_KEY=`"gsk_...`"' >> `"$ConfigFile`""
    }
}

# ── HF_TOKEN ─────────────────────────────────────────────────────────
Write-Host ""
$hfKey = ""
if (Test-Path $ConfigFile) {
    $hfKey = (Get-Content $ConfigFile | Where-Object { $_ -match "^HF_TOKEN=" } |
        ForEach-Object { ($_ -split "=",2)[1].Trim('"') } | Select-Object -First 1)
}
if (-not $hfKey) { $hfKey = $env:HF_TOKEN }

if ($hfKey) {
    Write-Ok "HF_TOKEN already configured"
} else {
    Write-Host "▶ HuggingFace Token (optional — for speaker diarization)" -ForegroundColor Cyan
    Write-Host "  1. Get token at: https://huggingface.co/settings/tokens"
    Write-Host "  2. Accept terms:  https://huggingface.co/pyannote/speaker-diarization-3.1"
    Write-Host ""
    $hfKey = Read-Host "  Paste your HF_TOKEN (or press Enter to skip)"
    if ($hfKey) {
        Add-Content -Path $ConfigFile -Value "HF_TOKEN=`"$hfKey`""
        Write-Ok "HF_TOKEN saved to $ConfigFile"
    } else {
        Write-Warn "Skipped — speaker diarization disabled until HF_TOKEN is set"
    }
}

# ── Install package ───────────────────────────────────────────────────
Write-Step "Installing transcribe-ai CLI"
& $python -m pip install --quiet -e $ScriptDir
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Package install failed."
    exit 1
}
Write-Ok "transcribe command registered"

# ── Env var for config ────────────────────────────────────────────────
Write-Step "Setting TRANSCRIBE_CONFIG environment variable"
[System.Environment]::SetEnvironmentVariable("TRANSCRIBE_CONFIG", $ConfigFile, "User")
Write-Ok "TRANSCRIBE_CONFIG=$ConfigFile (user scope)"

# ── Done ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "══════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✅  transcribe-ai installed successfully!   " -ForegroundColor Green
Write-Host "══════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  Usage:"
Write-Host "    transcribe recording.mp3 en"
Write-Host "    transcribe recording.mp3 en --no-diarize"
Write-Host "    transcribe recording.mp3 de --speakers 3"
Write-Host ""
Write-Host "  Config: $ConfigFile"
Write-Host ""
Write-Host "  Open a new terminal window to use the transcribe command."
Write-Host ""
