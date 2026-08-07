$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$version = "1.0.1"
$releaseName = "NovaLens-v$version-Windows-x64.zip"
$releaseZip = Join-Path $PSScriptRoot $releaseName
$checksumFile = "$releaseZip.sha256"

Write-Host "Stopping running Nova Lens processes..."
# Never kill generic flet.exe or pythonw.exe processes: they may belong to
# unrelated applications on the user's computer.
Get-Process NovaLens -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
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
            Get-Process NovaLens -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
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
    "--hidden-import", "popup", "popup_exe", "config", "multimodal", "native_clickthrough", "localization",
    "--add-data", "popup.py;.", "popup_exe.py;.", "config.py;.", "multimodal.py;."
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
flet @packArguments

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
