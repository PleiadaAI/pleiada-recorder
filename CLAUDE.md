# CLAUDE.md — pleiada-recorder

Guía durable del repo. **No** contiene estado de trabajo en curso.

> El estado de trabajo vive en **`HANDOFF.md`**, en esta misma carpeta. Está en `.gitignore`
> a propósito —este repo es público y el handoff es interno— así que **no viene en el clon**:
> llega por Google Drive. Si estás retomando y no lo ves, pedilo antes de tocar nada. Si está,
> leerlo junto con este archivo.

---

## 1. Qué es este repo

Cliente Windows del programa **Gameplay Alliance**: graba gameplay con OBS, registra
teclado y mouse sincronizados, verifica la sesión y la sube a S3.

- Remoto: `https://github.com/PleiadaAI/pleiada-recorder` — **repo PÚBLICO**.
- Licencia: **source-available** (ver `LICENSE`): se puede leer y auditar, no reutilizar.
  ⚠ El pie del `README.md` todavía dice "MIT License" — es un resto viejo y está mal;
  la fuente de verdad es `LICENSE`.
- Nunca commitear secretos acá (tokens de escritura, claves AWS, nombres de recursos de
  infraestructura). El backend está deliberadamente afuera (ver §7).

### Nombre del producto (importante, hay dos)

Desde v0.8.10 la app se llama **Gameplay Recorder** en todo lo que el usuario lee. Lo que
**sigue** diciendo "Pleiada" a propósito, porque renombrarlo sin migración rompe usuarios:

| Sigue "Pleiada" | Por qué |
|---|---|
| `Documentos\Pleiada Recordings` | ahí están las sesiones ya grabadas |
| `AppData\Pleiada\*` | renombrarla desloguea a todos |
| Perfil y escena "Pleiada" de OBS | |
| `Documentos\Pleiada Logs` | |
| `AppId` del instalador = `"Pleiada Recorder"` | si cambia, el updater LITE monta una instalación **paralela** |
| `PleiadaRecorder_Setup.exe` / `_Update.exe` | el sitio linkea al permalink `releases/latest/download/PleiadaRecorder_Setup.exe` |
| Nombres de archivo `pleiada_*.pyw`, repo `pleiada-recorder` | |
| `source_id = sha256("pleiada:"+guid)` | cambiarlo rompe la identidad de todos los datasets ya entregados |

El rename de las carpetas de datos es una versión aparte, con migración. No hacerlo de paso.

---

## 2. Estructura

```
pleiada-recorder/
├── CHANGELOG.md                      # una sección por versión, la nueva arriba
├── COMO_PUBLICAR_ACTUALIZACIONES.md  # runbook de release (leer antes de publicar)
├── LICENSE                           # source-available
├── README.md                         # doc de usuario (ver §8: la parte "Para devs" está vieja)
├── .github/workflows/build.yml       # CI: tag → compila → publica Release
└── pleiada_installer/
    ├── setup.iss                     # Inno Setup: genera el completo Y el LITE
    ├── min_version.txt               # versión mínima soportada (update obligatorio)
    ├── update_games_list.py          # PASO OBLIGATORIO antes de cada build
    ├── gen_wizard_art.py             # regenera .ico + BMPs desde el logo 512
    ├── BuildPleiadaSetup.ps1         # build local: baja deps + compila
    ├── files/                        # TODO lo que se instala
    ├── assets/                       # íconos e imágenes del wizard
    ├── deps/                         # (gitignored) los 3 instaladores, ~179 MB
    └── Output/                       # (gitignored) los .exe compilados
```

### `pleiada_installer/files/` — los componentes

| Archivo | Qué es |
|---|---|
| `pleiada_app.pyw` | **La app** (Tkinter, ~243 KB, un solo archivo). Login OTP, selector de juego, grabación, sync check, empaquetado, metadata y subida. Cliente OBS WebSocket v5 inlineado (puerto 4455). **`VERSION` vive en la línea 17 y es la única fuente de verdad de la versión.** |
| `pleiada_check.pyw` | **Gameplay Synch Checker**, verificador standalone (Tkinter + OpenCV). |
| `pleiada_sync_limits.py` | **Módulo compartido**: umbrales de sincronía, gates (duración mínima, AFK, video quieto), `activity()` y el lector de MP4 (`mp4_duration_ms`, `mp4_is_truncated`). Ver §4. |
| `input_logger.ahk` | Logger headless (AutoHotkey v2): hooks low-level + Raw Input, para capturar en fullscreen exclusivo. |
| `obs_control.py` | Wrapper CLI del OBS WebSocket (start/stop, mute mic, mueve el MP4). |
| `session_uploader.py` | Subida a S3 (incluye multipart para archivos grandes). |
| `pleiada_api.py` | Cliente HTTP de la Lambda `pleiada-api`. |
| `configure_obs.py` | Configura OBS: WebSocket, perfil, escena. Corre desde el instalador — **en el completo y en el LITE** (ver §5). |
| `pleiada_setup_wizard.pyw` | Wizard post-instalación. |
| `games_list.json` | Lista de juegos bundleada (fallback). Se regenera antes de cada build. |

### Salida de una sesión

`Documentos\Pleiada Recordings\<juego>_<ts> recording\` = 1 MP4 + **4 CSV**
(`video_timeline.csv`, `mouse_log.csv`, `mouse_delta_log.csv`, `key_log.csv`, todos con
`ANCHOR_START`/`ANCHOR_END`) + `session_metadata.json` (schema_version "1.0").

---

## 3. Comandos

No hay suite de tests en este repo. Lo que hay:

```powershell
# Chequeo de sintaxis (mínimo antes de commitear)
python -m py_compile pleiada_installer\files\pleiada_app.pyw
```

```powershell
# PASO OBLIGATORIO antes de CUALQUIER build: regenera games_list.json desde Airtable
cd pleiada_installer
python update_games_list.py
```

```powershell
# Compilar. SIEMPRE pasar /DAppVersion, y que coincida con VERSION en pleiada_app.pyw.
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DAppVersion=X.Y.Z setup.iss           # completo (~181 MB)
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DLITE /DAppVersion=X.Y.Z setup.iss    # updater LITE (~2 MB)
```

Sin `/DAppVersion` queda el fallback viejo del `.iss` y el instalador sale mal estampado.
El completo necesita los 3 instaladores en `deps/` (ver `INSTRUCCIONES_PARA_COMPILAR.md`);
el LITE no. Requiere Inno Setup 6.

```powershell
# Solo si cambia el logo o el texto de marca
cd pleiada_installer
python gen_wizard_art.py
```

---

## 4. Decisión estructural: un solo criterio de validación

`pleiada_sync_limits.py` es la **fuente de verdad única** de los umbrales y gates que
deciden si una sesión es válida. Antes vivían duplicados en `pleiada_app.pyw` y
`pleiada_check.pyw` y ya habían divergido: el uploader subía sesiones que el verificador
mostraba como error, y el lector de MP4 daba duraciones distintas sobre el mismo archivo.

**Regla: cualquier umbral o gate nuevo va en ese módulo, no en la app ni en el checker.**
Cuando gana un criterio, gana el del uploader — es el que decide qué se sube.

Consecuencia operativa: `pleiada_sync_limits.py` tiene que estar en `[Files]` de
`setup.iss`. Si falta, el Synch Checker revienta al importar.

**Copia deliberada fuera del repo:** `Pleiada Tools\qa_muestreo\sync_verify.py` (verificador
server-side) repite los mismos umbrales a mano. No hay import entre repos. **Si cambian acá,
cambiarlos allá.**

---

## 5. Auto-update y releases

Está todo en **`COMO_PUBLICAR_ACTUALIZACIONES.md`** — leerlo antes de publicar. Lo esencial:

- **Pushear un tag `vX.Y.Z` ES el deploy a producción.** El CI compila y publica el Release,
  y toda la base instalada ve la actualización en el próximo arranque.
- El Release lleva **3 assets**: `PleiadaRecorder_Setup.exe`, `PleiadaRecorder_Update.exe`,
  `latest.json`. La app lee `latest.json` desde `releases/latest/download/`.
- **La versión vive en un solo lugar editable:** `VERSION` en `pleiada_app.pyw`. El CI
  **falla el build a propósito** si el tag no coincide (paso "Validate version consistency").
- Update **obligatorio** = subir `min_version.txt`. Toda versión instalada menor queda
  bloqueada para grabar. **La decisión es de Martín, release por release** — nunca asumirla.
- El instalador LITE **también** corre `configure_obs.py`. Es la única vía por la que la
  flota ya instalada recibe cambios de configuración de OBS; dejarlo bajo `#ifndef LITE`
  hace que los arreglos solo lleguen a instalaciones limpias. Es idempotente
  (`configure_websocket` preserva el password existente).

### Tres trampas de upgrade que ya están resueltas — no volver a romperlas

1. `AppId` NO acompaña al rename (queda `"Pleiada Recorder"`), si no se monta una
   instalación paralela.
2. El `taskkill` del instalador filtra por WINDOWTITLE y mata **los dos** títulos: al
   actualizar desde una versión anterior al rename, la app corriendo todavía se llama
   "Pleiada Recorder".
3. `[InstallDelete]` borra el acceso directo viejo del escritorio, si no quedan dos.

---

## 6. Convenciones del proyecto

- **Confirmar el copy con Martín antes de implementarlo.** Cualquier frase nueva que ve el
  usuario se aprueba antes.
- **Los mensajes al usuario nunca revelan umbrales.** Rechazos por duración, inactividad o
  imagen quieta se explican en genérico; el valor medido va al registro interno / metadata.
- **Nunca pushear, publicar ni deployar sin OK explícito de Martín, cada vez.**
- **QA antes de producción:** todo cambio pasa por test manual antes del push (que, por §5,
  es el deploy).
- **Versionado:** cada build con cambios lleva número de versión NUEVO (bump de `VERSION`
  + `/DAppVersion` igual). `vX.Y.Z`: `Y` para features, `Z` para fixes chicos.
- Todo el texto de usuario y los comentarios del código están en español (rioplatense).

---

## 7. Repos relacionados

El backend **no está en este repo** y no debe volver (`backend/` está en `.gitignore`).

| Repo | Qué |
|---|---|
| `PleiadaAI/pleiada-recorder` | este (público) |
| `PleiadaAI/pleiada-backend` | **privado**: Lambda `pleiada-api` (sa-east-1) + IAM + tests + tools |
| `PleiadaDevs/home_game_alliance` | sitio: home + `/dashboard` + T&C |
| `PleiadaDevs/catalogo-juegos` | catálogo por categorías |
| `PleiadaDevs/pleidada_site` | sitio institucional |
| `PleiadaDevs/pleiada_recorder_tutorial` | tutorial web (`recorder.gameplayalliance.gg`) |

Los 3 sitios son GitHub Pages: **1 repo = 1 dominio**, push a `main` = publicado.

**Deploy del backend = manual, lo hace Martín**: se le abre `lambda_function.py`, lo pega
entero en la consola de AWS Lambda y deployea. En estas máquinas no hay AWS CLI ni
credenciales. Regla del runbook, aprendida dos veces: **si un cambio usa una API de AWS
nueva, revisar los permisos IAM del rol ANTES de deployar.**

---

## 8. Documentación desactualizada (no confiar sin verificar)

- `README.md`, sección **"Para devs"**: describe una arquitectura vieja
  (`gameplay_logger.ahk` como GUI principal, `configure_obs.py` grabando a 2500 kbps,
  shortcuts que ya no son los que crea el instalador). La app unificada es
  `pleiada_app.pyw` y el logger se llama `input_logger.ahk`. El README de usuario (arriba
  de esa sección) sí está razonablemente al día.
- `README.md` dice licencia MIT: es `LICENSE` la que vale (source-available).
- El `Changelog` del README se quedó en V25.5 (mayo). El vigente es `CHANGELOG.md`.
- **Limitación conocida del CI:** el paso "Extract release notes" busca en `CHANGELOG.md`
  un encabezado `## V<tag sin "v0.">` (tag `v0.9.0` → `## V9.0`), pero desde v0.8.2 los
  encabezados se escriben `## v0.8.N — fecha — título`. **No matchean**, así que el Release
  sale con la nota genérica "Ver CHANGELOG.md para detalles". No rompe el build.
