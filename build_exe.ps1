$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "Installing build dependencies..."
python -m pip install -r requirements-build.txt

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
    "--hidden-import", "popup", "config", "multimodal",
    "--add-data", "popup.py;.", "config.py;.", "multimodal.py;."
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

$executable = Join-Path $PSScriptRoot "dist\NovaLens\NovaLens.exe"

if (-not (Test-Path $executable)) {
    throw "The build finished, but NovaLens.exe was not found."
}

Write-Host ""
Write-Host "Build complete:"
Write-Host $executable
Write-Host ""
Write-Host "Place a .env file next to NovaLens.exe before testing."
