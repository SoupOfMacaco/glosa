# Compila la app y el instalador.
# Uso:  .\build.ps1            (usa la versión de app\__init__.py)
param([string]$Python = "python")

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$version = (Select-String -Path app\__init__.py -Pattern '__version__ = "(.+)"').Matches[0].Groups[1].Value
Write-Host "Compilando Traductor en Vivo $version"

& $Python tools\make_icon.py
& $Python -m PyInstaller TraductorEnVivo.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falló" }

$iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Warning "No se encontró Inno Setup 6: solo se generó dist\TraductorEnVivo\. Instálalo para crear el instalador."
    exit 0
}
& $iscc "/DAppVersion=$version" installer\setup.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falló" }
Write-Host "Instalador listo: dist\TraductorEnVivo-Setup-$version.exe"
