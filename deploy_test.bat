@echo off
:: ============================================================
::  deploy_test.bat — Copia archivos editados al install dir
::  para probar sin recompilar el instalador.
::  EJECUTAR COMO ADMINISTRADOR.
:: ============================================================

set SRC=%~dp0pleiada_installer\files
set DST=C:\Program Files\Pleiada Recorder

echo.
echo  Copiando archivos a: %DST%
echo.

copy /Y "%SRC%\gameplay_logger.ahk" "%DST%\gameplay_logger.ahk"
copy /Y "%SRC%\obs_control.py"      "%DST%\obs_control.py"
copy /Y "%SRC%\pleiada_check.pyw"   "%DST%\pleiada_check.pyw"

echo.
echo  Listo. Podes abrir Pleiada Recorder desde el escritorio.
echo.
pause
