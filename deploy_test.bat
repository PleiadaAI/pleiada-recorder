@echo off
:: ============================================================
::  deploy_test.bat — Copia los archivos editados al install dir
::  para probar sin recompilar el instalador.
::  EJECUTAR COMO ADMINISTRADOR (Program Files no deja escribir si no).
::
::  Antes de pisar nada hace un backup de la instalacion actual en
::  Documents\Pleiada Recorder backups\<fecha>, asi se puede volver
::  a la version anterior copiando esa carpeta de vuelta.
::
::  15/08/2026: la lista de archivos estaba desactualizada — copiaba
::  gameplay_logger.ahk (no existe, es input_logger.ahk) y NO copiaba
::  pleiada_app.pyw, que es donde vive casi todo. Un deploy de prueba
::  no llevaba los cambios y el QA corria sobre la version vieja.
:: ============================================================

net session >nul 2>&1
if errorlevel 1 (
  echo.
  echo  ERROR: hay que ejecutarlo como Administrador.
  echo  Boton derecho sobre el .bat  ^>  Ejecutar como administrador.
  echo.
  pause
  exit /b 1
)

set SRC=%~dp0pleiada_installer\files
set DST=C:\Program Files\Pleiada Recorder
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set STAMP=%%c-%%b-%%a
set BAK=%USERPROFILE%\Documents\Pleiada Recorder backups\%STAMP%

echo.
echo  Backup de la instalacion actual en:
echo    %BAK%
robocopy "%DST%" "%BAK%" /E /XD __pycache__ /NFL /NDL /NJH /NJS /NC /NS >nul
if errorlevel 8 (
  echo  ERROR: fallo el backup. No se copia nada.
  pause
  exit /b 1
)

echo.
echo  Copiando archivos nuevos a: %DST%
robocopy "%SRC%" "%DST%" *.pyw *.py *.ahk *.json /XD __pycache__ /NFL /NDL /NJH /NJS /NC /NS
if errorlevel 8 (
  echo.
  echo  ERROR al copiar. La instalacion puede haber quedado a medias:
  echo  restaurar desde %BAK%
  pause
  exit /b 1
)

echo.
echo  Listo. Abri Gameplay Recorder desde el escritorio y confirma la
echo  version en el encabezado antes de arrancar el QA.
echo.
pause
