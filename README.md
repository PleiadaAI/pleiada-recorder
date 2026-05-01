# Pleiada Recorder

**Pleiada Recorder** es una herramienta gratuita desarrollada por [Pleiada](https://pleiada.ai) para el programa **Gameplay Alliance**. Graba tu pantalla con OBS y registra tus movimientos de teclado y mouse — todo sincronizado — para que tu forma de jugar sirva para entrenar agentes de Inteligencia Artificial.

---

## Primeros pasos

### Paso 1 — Configuración inicial con OBS

Antes de tu primera grabación tenés que configurar OBS una sola vez (si ya lo tenías instalado, igualmente tenés que realizar estos ajustes).

1. Iniciá el juego que quieras grabar y dejalo en pausa donde quieras iniciar la grabación.

2. Si lo acabás de instalar por primera vez, abrí OBS y seleccioná **"Optimizar solo para grabación..."** y dale Siguiente. Luego asegurate que la resolución sea al menos 1080 y los FPS sean **"60 o 30 pero en alta resolución"**.

3. Sin importar si lo tenías instalado o no, en la sección **Fuentes** (abajo a la izquierda) hacé clic en el **+**, seleccioná **"Captura de Juego"** y dejá el nombre que aparece. Luego en **Modo** seleccioná **"Capturar Ventana específica"** y en **Ventana** seleccioná la que esté mostrando tu juego ya iniciado.

4. En la sección **Mezclador de audio** (abajo al centro), si aparece una sección llamada **"Mic/Aux"**, silenciala haciendo clic en el 🔊 hasta que quede rojo (muteado).

✔ Solo tenés que hacer esto una vez.

---

### Paso 2 — Prueba inicial

Ahora vamos a hacer una grabación corta para verificar que todo funciona bien.

1. Si no iniciaste el juego en los pasos anteriores, hacelo ahora y dejalo en pausa.

2. Hacé doble clic en el ícono **Pleiada Recorder** del escritorio. Aparece una pequeña ventana flotante — podés moverla arrastrando el encabezado.

3. Hacé clic en el botón **⏺** para iniciar la grabación. El botón cambia a **⏹** y el contador empieza a correr.

4. Jugá unos 60 segundos y luego hacé clic en **⏹** para detener.

5. Los archivos quedan guardados automáticamente en:
   `Documentos › Pleiada Recordings`

6. Aprovechá para verificar en los 4 archivos que no se haya grabado en la pantalla o en el registro del teclado nada privado ni personal. De ser así, ese contenido será eliminado permanentemente.

---

### Paso 3 — Verificar sincronización (Synch Checker)

Después de cada sesión, verificá que el video y los logs quedaron bien sincronizados.

1. Hacé doble clic en el ícono **Synch Checker** del escritorio.

2. Hacé clic en **Seleccionar carpeta** y elegí la carpeta de la sesión (por ejemplo: `2026-04-25 13-09-07 recording`).

3. Hacé clic en **Verificar Sync**.

**Resultados posibles:**
- ✅ **SINCRONIZADOS** → la sesión está bien, podés entregarla.
- ⚠ **OFFSET LEVE** → desfase menor a 2 seg, generalmente aceptable.
- ✖ **OFFSET CRÍTICO** → desfase grande, la sesión puede no ser usable.

¿Dudas? Visitá [pleiada.ai/faqs](https://www.pleiada.ai/faqs)

---

## Uso cotidiano

Una vez configurado OBS, el flujo de cada sesión es:

1. Iniciá el juego.
2. Abrí **Pleiada Recorder** desde el escritorio.
3. Presioná **⏺** para empezar a grabar.
4. Jugá tu sesión. La grabación se detiene automáticamente al llegar a **1 hora 5 minutos**. Para evitar subidas de archivos muy pesados.
5. Cuando termines (o cuando se detenga sola), presioná **⏹**.
6. Abrí **Synch Checker** y verificá la sesión antes de entregarla.

> Si necesitás grabar más de 1h 5min, podés iniciar una nueva grabación — quedará guardada en una carpeta separada como una sesión nueva.

---

## ¿Dónde se guardan los archivos?

Cada sesión genera una carpeta en:

```
Documentos\Pleiada Recordings\
  └── 2026-04-26 15-13-40 recording\
        ├── 2026-04-26 15-13-42.mp4    ← video
        ├── mouse_log.csv              ← movimientos del mouse
        ├── key_log.csv                ← teclas presionadas
        └── video_timeline.csv         ← línea de tiempo
```

---

## Privacidad

Lo que graba Pleiada Recorder es **información anónima**: no captura tu nombre, cuenta, datos personales ni nada que te identifique. Sin embargo, **es responsabilidad del usuario** asegurarse de:

- No grabar pantallas que contengan información privada o personal (contraseñas, chats, datos bancarios, etc.).
- No utilizar el teclado durante la grabación para escribir contenido que pertenezca al ámbito privado.

En caso de que cualquier información privada llegue a nuestros servidores — ya sea a través de la captura de video o del registro del teclado — procederemos a eliminarla de forma permanente. Dicho contenido quedará automáticamente fuera de cualquier oportunidad comercial futura.

**Qué se registra:**

| Qué | Cómo |
|-----|------|
| Video de pantalla | Archivo local; se sube manualmente |
| Nombres de teclas | Ej: `a`, `Space`, `LShift` — sin texto ni contenido |
| Posición del mouse | Coordenadas en píxeles |
| Clics y scroll | Solo identificador del botón y delta de scroll |

No se accede al micrófono, cámara, portapapeles, historial de navegación ni ningún otro dato personal. Todo queda en tu computadora hasta que lo subís vos.

---

## Contacto y soporte

- Información del programa: [pleiada.ai](https://pleiada.ai)
- Preguntas frecuentes: [pleiada.ai/faqs](https://pleiada.ai/faqs)
- Términos: [pleiada.ai/terms](https://pleiada.ai/terms)

---

---

## Para devs

### Arquitectura

```
┌─────────────────────────────────────────────┐
│            gameplay_logger.ahk              │
│  (AutoHotkey v2 — floating GUI + input log) │
└────────────────────┬────────────────────────┘
                     │ subprocess calls
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
  obs_control.py start    obs_control.py stop
  (Python — OBS WebSocket v5 client)
          │
          │ ws://localhost:4455
          ▼
  ┌───────────────┐
  │  OBS Studio   │  ← configurado por configure_obs.py al instalar
  │  (recording)  │
  └───────────────┘
```

### Componentes

#### `gameplay_logger.ahk`
**Runtime:** AutoHotkey v2.0+

GUI frameless (`-Caption +ToolWindow +AlwaysOnTop`), posicionada en el centro inferior del área de trabajo del monitor primario. Draggable via `WM_NCHITTEST` en el header (primeros 28 px). Al iniciar una sesión crea una carpeta con timestamp, lanza `obs_control.py start` (bloqueante), y activa timers de tracking (mouse: 8 ms, timeline: 50 ms, UI clock: 1 s). La grabación se detiene automáticamente a los **3900 segundos (1h 5min)**. Al detener, escribe el anchor final en los CSVs y lanza `obs_control.py stop` en background.

#### `obs_control.py`
**Runtime:** Python 3.12+ / **Deps:** `websocket-client`

CLI wrapper del OBS WebSocket v5 API.

```
python obs_control.py start
python obs_control.py stop [session_folder]
```

**Start:** detecta `obs64.exe` via tasklist → busca el ejecutable (paths conocidos → registro → glob) → conecta WS con auth SHA-256 → si falla, mata y relanza OBS (1 reintento) → desmutea `wasapi_output_capture`, mutea todos los `wasapi_input_capture` → llama `StartRecord` → confirma `outputActive=True` (hasta 50 polls × 100 ms).

**Stop:** llama `StopRecord` → lee `outputPath` de la respuesta → fallback a escaneo de `~/Videos` si el path está vacío → mueve el video a `session_folder` con hasta 20 reintentos.

**Debug log:** `%TEMP%\pleiada_obs_debug.txt`

#### `configure_obs.py`
**Runtime:** Python 3.12+

Corre una sola vez durante la instalación (vía Inno Setup, hidden). Configura:

| Target | Archivo | Acción |
|--------|---------|--------|
| WebSocket plugin | `%APPDATA%\obs-studio\plugin_config\obs-websocket\config.json` | Puerto 4455, sin auth, suprime first-run alert |
| Perfil de grabación | `%APPDATA%\obs-studio\basic\profiles\Pleiada\basic.ini` | MP4, 1920×1080, 60 fps, 2500 kbps video, 160 kbps audio |
| Scene collection | `%APPDATA%\obs-studio\basic\scenes\Pleiada.json` | Escena con `monitor_capture` + `wasapi_output_capture`, sin micrófono |
| Perfil/escena activa | `%APPDATA%\obs-studio\global.ini` | Apunta a perfil `Pleiada` y escena `Pleiada`; `FirstRun=false` |

#### `pleiada_setup_wizard.pyw`
**Runtime:** Python 3.12+ (Tkinter)

Wizard de 3 pasos post-instalación. Ventana 580×560 px centrada en pantalla. El footer se packea antes que el contenido para garantizar visibilidad de los botones independientemente de la altura del contenido.

#### `pleiada_check.pyw`
**Runtime:** Python 3.12+ (Tkinter + OpenCV + Pillow)

Herramienta standalone de verificación de sync entre el video y los logs de una sesión.

---

### Installer

Construido con [Inno Setup 6](https://jrsoftware.org/isinfo.php) desde `pleiada_installer/setup.iss`.

**Secuencia:**
1. Página de consentimiento (checkbox requerido)
2. Python 3.12.8 silencioso (user-scope) si no existe `HKCU\Software\Python\PythonCore\3.12`
3. AutoHotkey v2.0.24
4. OBS Studio 32.1.2 (cierra OBS si está corriendo antes y después)
5. Paquetes pip: `websocket-client`, `Pillow`, `opencv-python`
6. `configure_obs.py` (hidden)
7. `pleiada_setup_wizard.pyw`

**Shortcuts creados:**

| Acceso directo | Target |
|----------------|--------|
| Pleiada Recorder | `gameplay_logger.ahk` |
| Synch Checker | `pleiada_check.pyw` |

---

### Building from Source

**Requisitos:** Windows 10/11 x64, [Inno Setup 6](https://jrsoftware.org/isdl.php), PowerShell 5.1+, acceso a internet.

```powershell
git clone https://github.com/PleiadaAI/pleiada-recorder.git
cd pleiada-recorder
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
cd pleiada_installer
.\BuildPleiadaSetup.ps1
```

El instalador compilado queda en `pleiada_installer/Output/`.

**CI/CD (GitHub Actions):** un push de tag dispara el build en `windows-latest`, compila el `.exe` y publica un GitHub Release.

```bash
git tag v0.17.2
git push origin v0.17.2
```

---

### Dependencias

| Paquete | Versión | Licencia | Uso |
|---------|---------|----------|-----|
| [AutoHotkey v2](https://www.autohotkey.com/) | 2.0.24 | GPL-2.0 | GUI, input hooks, orquestación |
| [OBS Studio](https://obsproject.com/) | 32.1.2 | GPL-2.0 | Grabación de pantalla y audio |
| [Python](https://www.python.org/) | 3.12.8 | PSF-2.0 | Runtime de scripts de control |
| [websocket-client](https://github.com/websocket-client/websocket-client) | latest | Apache-2.0 | OBS WebSocket v5 |
| [Pillow](https://python-pillow.org/) | latest | HPND | Procesamiento de imágenes (sync checker) |
| [opencv-python](https://github.com/opencv/opencv-python) | latest | MIT | Análisis de frames (sync checker) |
| [Inno Setup](https://jrsoftware.org/isinfo.php) | 6.x | ISL | Compilador del instalador (solo build) |

---

### Licencia

MIT License — Copyright © 2026 Pleiada