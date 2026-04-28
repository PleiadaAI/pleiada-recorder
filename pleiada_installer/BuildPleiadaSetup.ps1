# =================================================================
#  BuildPleiadaSetup.ps1
#  Descarga los 3 instaladores y compila PleiadaRecorder_Setup.exe
#  Ejecutar desde PowerShell como Administrador
# =================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step($msg) { Write-Host "" ; Write-Host "[ $msg ]" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "  OK  $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  !!  $msg" -ForegroundColor Yellow }

# -- Verificar carpeta correcta
if (-not (Test-Path "$ScriptDir\setup.iss")) {
    Write-Error "No se encuentra setup.iss en $ScriptDir"
    exit 1
}

# -- Crear carpetas
Write-Step "Preparando carpetas"
New-Item -ItemType Directory -Force -Path "$ScriptDir\deps"   | Out-Null
New-Item -ItemType Directory -Force -Path "$ScriptDir\assets" | Out-Null
New-Item -ItemType Directory -Force -Path "$ScriptDir\Output" | Out-Null
Write-OK "deps, assets, Output listos"

# -- Funcion de descarga
function Download-File {
    param($url, $dest, $label)
    if (Test-Path $dest) {
        $sz = (Get-Item $dest).Length
        if ($sz -gt 1048576) {
            $mb = [math]::Round($sz / 1048576, 1)
            Write-OK "$label ya existe ($mb MB) - omitiendo"
            return
        }
    }
    Write-Host "  Descargando $label ..." -NoNewline
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($url, $dest)
    $mb = [math]::Round((Get-Item $dest).Length / 1048576, 1)
    Write-Host " $mb MB  OK" -ForegroundColor Green
}

# -- 1. Descargar dependencias
Write-Step "Descargando instaladores de dependencias"

Download-File `
    "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe" `
    "$ScriptDir\deps\python-3.12.8-amd64.exe" `
    "Python 3.12.8"

Download-File `
    "https://www.autohotkey.com/download/ahk-v2.exe" `
    "$ScriptDir\deps\AutoHotkey_2.0.24_setup.exe" `
    "AutoHotkey v2"

Download-File `
    "https://github.com/obsproject/obs-studio/releases/download/32.1.2/OBS-Studio-32.1.2-Windows-x64-Installer.exe" `
    "$ScriptDir\deps\OBS-Studio-32.1.2-Windows-x64-Installer.exe" `
    "OBS Studio 32.1.2"

# -- 2. Verificar assets y parchear setup.iss si faltan
Write-Step "Verificando assets"

$issContent = Get-Content "$ScriptDir\setup.iss" -Raw

if (-not (Test-Path "$ScriptDir\assets\pleiada.ico")) {
    Write-Warn "assets\pleiada.ico no encontrado - se comentan las lineas del icono en setup.iss"
    $issContent = $issContent -replace '(?m)^(UninstallDisplayIcon=.*)', ';$1'
    $issContent = $issContent -replace '(?m)^(SetupIconFile=.*)', ';$1'
    $issContent = $issContent -replace '(?m)^(Source: "assets\\pleiada\.ico".*)', ';$1'
}

if ((-not (Test-Path "$ScriptDir\assets\wizard_banner.bmp")) -or
    (-not (Test-Path "$ScriptDir\assets\wizard_small.bmp"))) {
    Write-Warn "wizard .bmp no encontrados - se usan imagenes por defecto de Inno Setup"
    $issContent = $issContent -replace '(?m)^(WizardImageFile=.*)', ';$1'
    $issContent = $issContent -replace '(?m)^(WizardSmallImageFile=.*)', ';$1'
}

Set-Content "$ScriptDir\setup.iss" $issContent -Encoding UTF8
Write-OK "setup.iss verificado"

# -- 3. Localizar Inno Setup
Write-Step "Buscando Inno Setup"

$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Warn "Inno Setup no encontrado. Descargando instalador..."
    $isTmp = "$env:TEMP\innosetup-installer.exe"
    Download-File "https://jrsoftware.org/download.php/is.exe" $isTmp "Inno Setup 6"
    Write-Host "  Instalando Inno Setup..."
    Start-Process -FilePath $isTmp -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART" -Wait
    Remove-Item $isTmp -Force
    $iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $iscc) {
        Write-Error "No se pudo instalar Inno Setup. Instalalo manualmente desde https://jrsoftware.org/isdl.php y reejecutar."
        exit 1
    }
}
Write-OK "ISCC encontrado: $iscc"

# -- 4. Compilar
Write-Step "Compilando PleiadaRecorder_Setup_V17.exe"
Write-Host "  $iscc `"$ScriptDir\setup.iss`""

& $iscc "$ScriptDir\setup.iss"
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    $exePath = "$ScriptDir\Output\PleiadaRecorder_Setup_V17.exe"
    $mb = [math]::Round((Get-Item $exePath).Length / 1048576, 1)
    Write-Host ""
    Write-Host "=================================================" -ForegroundColor Green
    Write-Host "  PleiadaRecorder_Setup_V17.exe generado con exito!" -ForegroundColor Green
    Write-Host "  Tamano: $mb MB" -ForegroundColor Green
    Write-Host "  Ruta:   $exePath" -ForegroundColor Green
    Write-Host "=================================================" -ForegroundColor Green
} else {
    Write-Error "La compilacion fallo (codigo $exitCode)"
    exit 1
}
