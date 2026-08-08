$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$version = (python -c "from app_info import APP_VERSION; print(APP_VERSION)").Trim()
if (-not $version) {
    throw "Nova Lens version could not be read from app_info.py."
}
$releaseName = "NovaLens-v$version-Windows-x64.zip"
$releaseZip = Join-Path $PSScriptRoot $releaseName
$checksumFile = "$releaseZip.sha256"

function Stop-NovaLensProcessTrees {
    # taskkill /T follows only NovaLens.exe process trees, including their Flet
    # desktop children. It does not stop unrelated python.exe or flet.exe apps.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"

    try {
        & taskkill.exe /IM NovaLens.exe /T /F *> $null
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

Write-Host "Stopping running Nova Lens processes..."
Stop-NovaLensProcessTrees
Start-Sleep -Seconds 2

function Remove-DirectoryWithRetry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [int]$Attempts = 5
    )

    if (-not (Test-Path $Path)) {
        return
    }

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            Remove-Item -Recurse -Force $Path -ErrorAction Stop
            return
        }
        catch {
            if ($attempt -eq $Attempts) {
                throw
            }

            Write-Host "Waiting for Windows to release $Path ($attempt/$Attempts)..."
            Start-Sleep -Seconds 2
        }
    }
}

function Compress-ReleaseWithRetry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$Destination,
        [int]$Attempts = 8
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            Remove-Item $Destination -Force -ErrorAction SilentlyContinue
            Compress-Archive `
                -Path $Source `
                -DestinationPath $Destination `
                -CompressionLevel Optimal `
                -Force `
                -ErrorAction Stop

            if (-not (Test-Path $Destination)) {
                throw "The ZIP command finished without creating the file."
            }

            return
        }
        catch {
            Remove-Item $Destination -Force -ErrorAction SilentlyContinue

            if ($attempt -eq $Attempts) {
                throw
            }

            Write-Host "A packaged file is still locked. Retrying ZIP creation ($attempt/$Attempts)..."
            Stop-NovaLensProcessTrees
            Start-Sleep -Seconds 3
        }
    }
}

Write-Host "Cleaning previous build output..."
Remove-DirectoryWithRetry (Join-Path $PSScriptRoot "build")
Remove-DirectoryWithRetry (Join-Path $PSScriptRoot "dist")
Remove-Item $releaseZip -Force -ErrorAction SilentlyContinue
Remove-Item $checksumFile -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $PSScriptRoot "NovaLens-v1.0.1-beta.1-Windows-x64.zip") -Force -ErrorAction SilentlyContinue

Write-Host "Installing pinned runtime dependencies..."
python -m pip install -r requirements.txt

Write-Host "Installing pinned build dependencies..."
python -m pip install -r requirements-build.txt

# Resolve the Flet CLI from the same Python environment used by pip instead of
# relying on the user's PATH. This works with activated virtual environments,
# user-site installs, and GitHub Actions.
$scriptsDir = (python -c "import sysconfig; print(sysconfig.get_path('scripts'))").Trim()
$fletExe = Join-Path $scriptsDir "flet.exe"

if (-not (Test-Path $fletExe)) {
    throw "Flet was installed for the active Python environment, but its CLI was not found at: $fletExe"
}

Write-Host "Using Flet CLI: $fletExe"

$packArguments = @(
    "pack",
    "launcher.py",
    "--name", "NovaLens",
    "-D",
    "-y",
    "--product-name", "Nova Lens",
    "--product-version", "$version.0",
    "--file-version", "$version.0",
    "--file-description", "Nova Lens desktop AI assistant",
    "--company-name", "Nova Lens",
    "--copyright", "Copyright (c) 2026 Nova Lens",
    "--hidden-import", "popup", "popup_exe", "config", "multimodal", "audio_indicator", "bubble_layout", "control_bubble", "screen_selector", "localization", "app_info", "popup_layout", "reporting",
    "--add-data", "popup.py;.", "popup_exe.py;.", "config.py;.", "multimodal.py;.", "audio_indicator.py;.", "control_bubble.py;."
)

$iconPath = Join-Path $PSScriptRoot "assets\NovaLens.ico"

if (Test-Path $iconPath) {
    $packArguments += @("--icon", $iconPath)
}
else {
    Write-Host "No custom icon found at assets\NovaLens.ico."
    Write-Host "The build will use the default application icon."
}

Write-Host "Building Nova Lens v$version for Windows x64..."
& $fletExe @packArguments

if ($LASTEXITCODE -ne 0) {
    throw "Flet pack failed with exit code $LASTEXITCODE."
}

$distFolder = Join-Path $PSScriptRoot "dist\NovaLens"
$executable = Join-Path $distFolder "NovaLens.exe"
$internalFolder = Join-Path $distFolder "_internal"

if (-not (Test-Path $executable)) {
    throw "The build finished, but NovaLens.exe was not found."
}

if (-not (Test-Path $internalFolder)) {
    throw "The build finished, but the required _internal folder was not found."
}

# Never ship user secrets, local settings, temporary credentials, or debug files.
Remove-Item (Join-Path $distFolder ".env") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $distFolder ".env.tmp") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $distFolder "config.json") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $distFolder "config.tmp.json") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $distFolder "debug.log") -Force -ErrorAction SilentlyContinue

Write-Host "Waiting for the build tools to release packaged files..."
Start-Sleep -Seconds 5

Write-Host "Creating the official Windows release ZIP..."
Compress-ReleaseWithRetry -Source $distFolder -Destination $releaseZip

$hash = (Get-FileHash -Path $releaseZip -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $releaseName" | Set-Content -Path $checksumFile -Encoding ascii

Write-Host ""
Write-Host "Build complete:"
Write-Host $executable
Write-Host ""
Write-Host "Official release package:"
Write-Host $releaseZip
Write-Host ""
Write-Host "SHA-256 checksum:"
Write-Host $checksumFile
Write-Host ""
Write-Host "Extract the ZIP before opening NovaLens.exe."
Write-Host "Nova Lens stores the user's API key and settings locally in AppData."
