# backup_jetson.ps1
# Rsync the entire Jetson root filesystem to a local folder over SSH.
# Run from Windows PowerShell:  .\scripts\backup_jetson.ps1
#
# Requirements:
#   - rsync installed on Windows (comes with Git for Windows, or install via winget)
#   - SSH host alias 'jetson' configured in ~/.ssh/config
#
# Winget install if needed:
#   winget install --id GnuWin32.Rsync   (or use the one bundled with Git: C:\Program Files\Git\usr\bin\rsync.exe)

$ErrorActionPreference = "Stop"

# ── Config ────────────────────────────────────────────────────────────────────
$SSH_HOST    = "jetson"
$BACKUP_ROOT = "C:\jetson-backup"
$TIMESTAMP   = Get-Date -Format "yyyy-MM-dd_HHmm"
$DEST        = "$BACKUP_ROOT\$TIMESTAMP"
# ─────────────────────────────────────────────────────────────────────────────

# Resolve rsync — try native first, fall back to WSL
$USE_WSL = $false
$RSYNC   = (Get-Command rsync -ErrorAction SilentlyContinue)?.Source
if (-not $RSYNC) {
    $GIT_RSYNC = "C:\Program Files\Git\usr\bin\rsync.exe"
    if (Test-Path $GIT_RSYNC) {
        $RSYNC = $GIT_RSYNC
    } elseif (Get-Command wsl -ErrorAction SilentlyContinue) {
        $WSL_RSYNC = wsl which rsync 2>$null
        if ($WSL_RSYNC) {
            $USE_WSL = $true
            $RSYNC   = "wsl rsync (via WSL)"
        }
    }
}
if (-not $RSYNC) {
    Write-Error "rsync not found.`nOptions:`n  1. Install WSL: wsl --install`n  2. Install Git for Windows (includes rsync)"
    exit 1
}

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  Jetson Day-1 Backup" -ForegroundColor Cyan
Write-Host "  Host   : $SSH_HOST" -ForegroundColor Cyan
Write-Host "  Dest   : $DEST" -ForegroundColor Cyan
Write-Host "  rsync  : $RSYNC" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

# Create destination
New-Item -ItemType Directory -Force -Path $DEST | Out-Null

# Directories to exclude (pseudo/runtime filesystems + large caches)
$EXCLUDES = @(
    "/proc/*",
    "/sys/*",
    "/dev/*",
    "/run/*",
    "/tmp/*",
    "/mnt/*",
    "/media/*",
    "/lost+found",
    "/snap/*",
    "/var/cache/apt/*",
    "/var/tmp/*",
    "/home/*/.cache/*",
    "/root/.cache/*"
)

Write-Host "Starting rsync..." -ForegroundColor Yellow
Write-Host "(This will take several minutes for ~27 GB)" -ForegroundColor DarkGray
Write-Host ""

$START = Get-Date

if ($USE_WSL) {
    # Convert Windows path to WSL path: C:\jetson-backup\... → /mnt/c/jetson-backup/...
    $WSL_DEST = "/mnt/" + $DEST.Replace(":\", "/").Replace("\", "/").ToLower()
    # WSL rsync uses the Windows SSH config automatically via ~/.ssh symlink
    # We pass --rsh so WSL uses the same 'jetson' alias from ~/.ssh/config
    wsl rsync `
        --archive `
        --hard-links `
        --acls `
        --xattrs `
        --verbose `
        --progress `
        --human-readable `
        --stats `
        --rsh="ssh" `
        @($EXCLUDES | ForEach-Object { "--exclude=$_" }) `
        "${SSH_HOST}:/" `
        "${WSL_DEST}/"
} else {
    & $RSYNC `
        --archive `
        --hard-links `
        --acls `
        --xattrs `
        --verbose `
        --progress `
        --human-readable `
        --stats `
        --rsh="ssh" `
        @($EXCLUDES | ForEach-Object { "--exclude=$_" }) `
        "${SSH_HOST}:/" `
        "$DEST/"
}

$EXIT = $LASTEXITCODE
$ELAPSED = ((Get-Date) - $START).ToString("hh\:mm\:ss")

Write-Host ""
if ($EXIT -eq 0 -or $EXIT -eq 24) {
    # Exit 24 = some files vanished during transfer (normal for a live system)
    $SIZE = (Get-ChildItem -Recurse -File $DEST -ErrorAction SilentlyContinue |
             Measure-Object -Property Length -Sum).Sum / 1GB
    Write-Host "=====================================================" -ForegroundColor Green
    Write-Host "  Backup COMPLETE" -ForegroundColor Green
    Write-Host "  Elapsed : $ELAPSED" -ForegroundColor Green
    Write-Host ("  Size    : {0:N1} GB" -f $SIZE) -ForegroundColor Green
    Write-Host "  Path    : $DEST" -ForegroundColor Green
    Write-Host "=====================================================" -ForegroundColor Green

    # Write a manifest file
    $MANIFEST = "$DEST\_backup_manifest.txt"
    @"
Jetson Backup Manifest
======================
Date      : $TIMESTAMP
Host      : $SSH_HOST
rsync exit: $EXIT
Elapsed   : $ELAPSED
Size (GB) : $([math]::Round($SIZE, 2))
Excluded  :
$($EXCLUDES -join "`n")
"@ | Set-Content $MANIFEST
    Write-Host ""
    Write-Host "Manifest written to: $MANIFEST" -ForegroundColor DarkGray

} else {
    Write-Host "=====================================================" -ForegroundColor Red
    Write-Host "  Backup FAILED (rsync exit code $EXIT)" -ForegroundColor Red
    Write-Host "  Elapsed : $ELAPSED" -ForegroundColor Red
    Write-Host "=====================================================" -ForegroundColor Red
    exit $EXIT
}
