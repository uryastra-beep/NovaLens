param(
    [switch]$SkipPortableBuild
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$version = (python -c "from app_info import APP_VERSION; print(APP_VERSION)").Trim()
if (-not $version) {
    throw "Nova Lens version could not be read from app_info.py."
}
$installerName = "NovaLens-Setup-v$version-Windows-x64.exe"
$installerOutput = Join-Path $PSScriptRoot "installer-output"
$installerPath = Join-Path $installerOutput $installerName
$checksumPath = "$installerPath.sha256"
$scriptPath = Join-Path $PSScriptRoot "installer\NovaLens.iss"

if (-not $SkipPortableBuild) {
    Write-Host "Building the Nova Lens portable application first..."
    & (Join-Path $PSScriptRoot "build_exe.ps1")
}

$portableExecutable = Join-Path $PSScriptRoot "dist\NovaLens\NovaLens.exe"
if (-not (Test-Path $portableExecutable)) {
    throw "NovaLens.exe was not found. Run .\build_exe.ps1 first or remove -SkipPortableBuild."
}

$isccCandidates = @()
$isccCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
if ($null -ne $isccCommand) {
    $isccCandidates += $isccCommand.Source
}

if (${env:ProgramFiles(x86)}) {
    $isccCandidates += Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
}
if ($env:ProgramFiles) {
    $isccCandidates += Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"
}
if ($env:LOCALAPPDATA) {
    $isccCandidates += Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
}

$iscc = $isccCandidates |
    Where-Object { $_ -and (Test-Path $_) } |
    Select-Object -First 1

if (-not $iscc) {
    throw "Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php and run this command again."
}

Write-Host "Using Inno Setup compiler: $iscc"

if (Test-Path $installerOutput) {
    Remove-Item -Recurse -Force $installerOutput
}
New-Item -ItemType Directory -Path $installerOutput | Out-Null

Write-Host "Building Nova Lens Setup v$version..."
& $iscc "/DMyAppVersion=$version" $scriptPath

if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE."
}

if (-not (Test-Path $installerPath)) {
    throw "The installer build finished, but $installerName was not found."
}

$hash = (Get-FileHash -Path $installerPath -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $installerName" | Set-Content -Path $checksumPath -Encoding ascii

Write-Host ""
Write-Host "Installer build complete:"
Write-Host $installerPath
Write-Host ""
Write-Host "SHA-256 checksum:"
Write-Host $checksumPath
