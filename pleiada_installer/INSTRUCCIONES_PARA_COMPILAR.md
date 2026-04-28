# Como compilar PleiadaRecorder_Setup.exe

## Paso 1 — Descargar Inno Setup
Ir a https://jrsoftware.org/isdl.php y descargar **innosetup-6.x.x.exe**
Instalarlo en tu PC (es gratuito).

## Paso 2 — Descargar los instaladores de dependencias
Colocar los siguientes archivos en la carpeta `deps\`:

| Archivo | Link de descarga |
|---|---|
| python-3.11.5-amd64.exe | https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe |
| AutoHotkey_2.0.24_setup.exe | https://www.autohotkey.com/download/ahk-v2.exe |
| OBS-Studio-30.0.2-Full-Installer-x64.exe | https://github.com/obsproject/obs-studio/releases/download/30.0.2/OBS-Studio-30.0.2-Full-Installer-x64.exe |

## Paso 3 — Agregar el icono de Pleiada
Colocar en la carpeta `assets\`:
- pleiada.ico       (icono 256x256 .ico)
- wizard_banner.bmp (imagen 497x314 px para el wizard)
- wizard_small.bmp  (imagen 55x58 px para el wizard)

Si no tenes los archivos .bmp, en setup.iss comentar las lineas:
  WizardImageFile=assets\wizard_banner.bmp
  WizardSmallImageFile=assets\wizard_small.bmp

## Paso 4 — Compilar
1. Abrir Inno Setup Compiler
2. File -> Open -> seleccionar setup.iss
3. Build -> Compile (o presionar F9)
4. El archivo PleiadaRecorder_Setup.exe se genera en la carpeta Output\

## Estructura de carpetas esperada
pleiada_installer\
├── setup.iss
├── files\
│   ├── gameplay_logger.ahk
│   ├── obs_control.py
│   └── configure_obs.py
├── deps\
│   ├── python-3.11.5-amd64.exe
│   ├── AutoHotkey_2.0.24_setup.exe
│   └── OBS-Studio-30.0.2-Full-Installer-x64.exe
├── assets\
│   ├── pleiada.ico
│   ├── wizard_banner.bmp
│   └── wizard_small.bmp
└── Output\
    └── PleiadaRecorder_Setup.exe  (generado al compilar)

## Requerimientos minimos del sistema para los estudiantes
- Windows 10 64-bit o superior
- 4GB RAM minimo (8GB recomendado)
- 10GB de espacio libre en disco
- Conexion a internet al momento de instalar
- Permiso de administrador en la PC
- GPU compatible con OBS (cualquier tarjeta de los ultimos 8 anos)
