# Como compilar PleiadaRecorder_Setup.exe

## Paso 1 — Descargar Inno Setup
Ir a https://jrsoftware.org/isdl.php y descargar **innosetup-6.x.x.exe**
Instalarlo en tu PC (es gratuito).

## Paso 2 — Descargar los instaladores de dependencias
Colocar los siguientes archivos en la carpeta `deps\`:

| Archivo | Link de descarga |
|---|---|
| python-3.12.8-amd64.exe | https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe |
| AutoHotkey_2.0.24_setup.exe | https://www.autohotkey.com/download/ahk-v2.exe |
| OBS-Studio-32.1.2-Windows-x64-Installer.exe | https://github.com/obsproject/obs-studio/releases/download/32.1.2/OBS-Studio-32.1.2-Windows-x64-Installer.exe |

Los nombres tienen que coincidir EXACTO con los de `[Files]` en setup.iss.

## Paso 3 — Assets de marca (ya versionados en el repo)
Viven en `assets\` y no hay que conseguirlos: `gameplay_recorder.ico`,
`gameplay_recorder_icon.png`, `wizard_banner.bmp` (164x314) y
`wizard_small.bmp` (55x58).

Si cambia el logo, se regeneran los cuatro desde
`assets\gameplay_alliance_logo_512.png` con:
```
python gen_wizard_art.py
```
No hace falta correrlo en cada build, solo si cambia el logo o el texto de marca.

## Paso 4 — Compilar
Desde la linea de comandos, pasando SIEMPRE la version. Si se omite, queda el
fallback viejo que tiene setup.iss y el instalador sale mal estampado:

```
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DAppVersion=0.8.10 setup.iss
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DLITE /DAppVersion=0.8.10 setup.iss
```

El primero genera `Output\PleiadaRecorder_Setup.exe` (completo, ~181 MB); el
segundo `Output\PleiadaRecorder_Update.exe` (LITE, solo los archivos de la app,
es el que usa el auto-update). La version tiene que coincidir con `VERSION` en
`files\pleiada_app.pyw`.

Desde la GUI (File -> Open -> setup.iss -> F9) tambien compila, pero no permite
pasar `/DAppVersion`.

### Ojo: los builds locales salen SIN FIRMAR
La firma de codigo (SSL.com / eSigner) la hace el CI, no ISCC. Un .exe compilado
aca sale sin firma: Windows lo muestra como "Editor desconocido" y SmartScreen
advierte. Sirve igual para probar, pero **no es lo mismo que se publica**, y no
sirve para validar nada relacionado con la firma. Ver `..\FIRMA_CODIGO_SSLCOM.md`.

**Nunca distribuir un .exe compilado local como si fuera un release.** Lo que va a
produccion sale siempre del tag, por GitHub Actions.

### Por que los .exe siguen diciendo PleiadaRecorder
La app se llama Gameplay Recorder desde v0.8.10, pero el nombre de los .exe NO
cambio: el boton de descarga del sitio apunta al permalink
`releases/latest/download/PleiadaRecorder_Setup.exe`, y renombrarlos lo rompe
hasta actualizar el sitio. Por el mismo motivo `AppId` sigue siendo el historico
"Pleiada Recorder": si cambia, el updater monta una instalacion paralela.

## Paso previo obligatorio — Refrescar la lista de juegos bundleada
Antes de CADA compilacion, correr:
```
python update_games_list.py
```
Regenera `files\games_list.json` desde Airtable con el filtro "Publicado"
(la misma lista del catalogo publico). Si falla por falta de conexion, el
bundle anterior queda intacto — pero el instalador saldria con lista vieja.

## Estructura de carpetas esperada
```
pleiada_installer\
├── setup.iss
├── gen_wizard_art.py
├── update_games_list.py
├── files\
│   ├── pleiada_app.pyw          (la app; VERSION vive aca)
│   ├── pleiada_check.pyw         (Gameplay Synch Checker)
│   ├── pleiada_sync_limits.py    (umbrales y gates compartidos por los dos)
│   ├── input_logger.ahk
│   ├── obs_control.py
│   ├── session_uploader.py
│   ├── pleiada_api.py
│   ├── configure_obs.py
│   └── games_list.json
├── deps\
│   ├── python-3.12.8-amd64.exe
│   ├── AutoHotkey_2.0.24_setup.exe
│   └── OBS-Studio-32.1.2-Windows-x64-Installer.exe
├── assets\
│   ├── gameplay_alliance_logo_512.png  (fuente de los otros; no se instala)
│   ├── gameplay_recorder.ico
│   ├── gameplay_recorder_icon.png
│   ├── synch_checker.ico
│   ├── wizard_banner.bmp
│   └── wizard_small.bmp
└── Output\
    ├── PleiadaRecorder_Setup.exe   (generado al compilar)
    └── PleiadaRecorder_Update.exe  (generado con /DLITE)
```

## Requerimientos minimos del sistema para los estudiantes
- Windows 10 64-bit o superior
- 4GB RAM minimo (8GB recomendado)
- 10GB de espacio libre en disco
- Conexion a internet al momento de instalar
- Permiso de administrador en la PC
- GPU compatible con OBS (cualquier tarjeta de los ultimos 8 anos)
