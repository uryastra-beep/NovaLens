$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "Stopping running Nova Lens processes..."
Get-Process NovaLens -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process flet -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
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

            Write-Host "Waiting for Windows to release $Path..."
            Start-Sleep -Seconds 2
        }
    }
}

Write-Host "Cleaning previous build output..."
Remove-DirectoryWithRetry (Join-Path $PSScriptRoot "build")
Remove-DirectoryWithRetry (Join-Path $PSScriptRoot "dist")

$releaseZip = Join-Path $PSScriptRoot "NovaLens-v1.0.1-beta.1-Windows-x64.zip"
Remove-Item $releaseZip -Force -ErrorAction SilentlyContinue

Write-Host "Installing and upgrading runtime dependencies..."
python -m pip install --upgrade -r requirements.txt

Write-Host "Installing and upgrading build dependencies..."
python -m pip install --upgrade -r requirements-build.txt

$packArguments = @(
    "pack",
    "launcher.py",
    "--name", "NovaLens",
    "-D",
    "-y",
    "--product-name", "Nova Lens",
    "--product-version", "1.0.1.0",
    "--file-version", "1.0.1.0",
    "--file-description", "Nova Lens desktop AI assistant",
    "--company-name", "Nova Lens",
    "--copyright", "Copyright (c) 2026 Nova Lens",
    "--hidden-import", "popup", "popup_exe", "config", "multimodal",
    "--add-data", "popup.py;.", "popup_exe.py;.", "config.py;.", "multimodal.py;."
)

$iconPath = Join-Path $PSScriptRoot "assets\NovaLens.ico"

if (Test-Path $iconPath) {
    $packArguments += @("--icon", $iconPath)
}
else {
    Write-Host "No custom icon found at assets\NovaLens.ico."
    Write-Host "The test build will use the default icon."
}

Write-Host "Building Nova Lens 1.0.1 test folder..."
flet @packArguments

$distFolder = Join-Path $PSScriptRoot "dist\NovaLens"
$executable = Join-Path $distFolder "NovaLens.exe"

if (-not (Test-Path $executable)) {
    throw "The build finished, but NovaLens.exe was not found."
}

# A user key must never be shipped inside the release folder.
Remove-Item (Join-Path $distFolder ".env") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $distFolder "config.json") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $distFolder "debug.log") -Force -ErrorAction SilentlyContinue

Write-Host "Creating the Windows release ZIP..."
Compress-Archive -Path $distFolder -DestinationPath $releaseZip -Force

Write-Host ""
Write-Host "Build complete:"
Write-Host $executable
Write-Host ""
Write-Host "Release ZIP ready:"
Write-Host $releaseZip
Write-Host ""
Write-Host "Open NovaLens.exe and add your own Gemini API key in Settings."
Write-Host "Nova Lens stores the key locally in the user's AppData folder."
