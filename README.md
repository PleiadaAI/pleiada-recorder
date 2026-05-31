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

3. En el Recorder, seleccioná de la lista el juego que vas a grabar (tiene que coincidir con el que capturaste en OBS). Luego hacé clic en **Iniciar grabación**. El botón cambia a **Detener grabación** y el contador empieza a correr.

4. Jugá unos 60 segundos y luego hacé clic en **Detener grabación** desde el Recorder (nunca desde OBS, para que los archivos queden sincronizados).

5. Los archivos quedan guardados automáticamente en:
   `Documentos › Pleiada Recordings`

6. Aprovechá para verificar en los archivos que no se haya grabado en la pantalla ni en el registro del teclado nada privado ni personal. De ser así, ese contenido será eliminado permanentemente. ⚠ Si modificás algún archivo, la sesión será rechazada.

---

### Paso 3 — Verificación automática

Después de cada sesión, el Recorder verifica **automáticamente** que el video y los logs quedaron bien sincronizados. No tenés que hacer nada.

**Resultados posibles:**
- ✅ **SINCRONIZADOS** → la sesión quedó lista, podés entregarla.
- ⚠ **OFFSET / ✗ ERROR** → la sesión se descarta automáticamente; iniciá una nueva grabación.

Los archivos válidos quedan en la carpeta de la sesión, listos para revisar y subir.

¿Dudas? Visitá [gameplayalliance.gg](https://gameplayalliance.gg)

---

## Uso cotidiano

Una vez configurado OBS, el flujo de cada sesión es:

1. Iniciá el juego.
2. Abrí **Pleiada Recorder** desde el escritorio.
3. Seleccioná el juego de la lista y presioná **Iniciar grabación**.
4. Jugá tu sesión. La grabación se detiene automáticamente al llegar a **1 hora 5 minutos**, para evitar subidas de archivos muy pesados.
5. Cuando termines (o cuando se detenga sola), presioná **Detener grabación** desde el Recorder.
6. El Recorder verifica la sesión automáticamente y deja los archivos listos en la carpeta de la sesión.

> Si necesitás grabar más de 1h 5min, podés iniciar una nueva grabación — quedará guardada en una carpeta separada como una sesión nueva.

---

## Atajos de teclado y Ajustes

Pleiada Recorder tiene un panel de **Ajustes** (ícono ⚙ en la barra superior) y **atajos de teclado** para iniciar/detener la grabación sin tener que volver a la ventana del Recorder — muy útil cuando jugás en pantalla completa.

### Atajos por defecto

| Atajo | Acción |
|-------|--------|
| **F9** | Iniciar grabación |
| **F10** | Detener grabación |

Los atajos funcionan **aunque el Recorder no esté en primer plano** (incluso con el juego en pantalla completa). Para iniciar con F9 necesitás tener un juego seleccionado y OBS configurado, igual que con el botón.

### Cambiar los atajos

1. Hacé clic en el ícono **⚙** (arriba a la derecha).
2. En **Atajos de teclado**, hacé clic sobre el atajo que querés cambiar.
3. Presioná la nueva tecla. Queda guardada automáticamente.

> Las teclas que uses como atajos del Recorder **no se registran** en los logs de la sesión (no contaminan el dataset de gameplay).

### Panel de Ajustes (⚙)

Desde el panel de Ajustes también podés:
- Ver la **versión** instalada del Recorder.
- **Cerrar sesión** de tu cuenta.

---

## ¿Dónde se guardan los archivos?

Cada sesión genera una carpeta en:

```
Documentos\Pleiada Recordings\
  └── FarCry6_26_04_26__15_13_40 recording\
        ├── FarCry6_26_04_26__15_13_42.mp4  ← video
        ├── mouse_log.csv                   ← movimientos del mouse
        ├── mouse_delta_log.csv             ← deltas de hardware del mouse
        ├── key_log.csv                     ← teclas presionadas
        ├── video_timeline.csv              ← línea de tiempo
        └── session_metadata.json           ← metadata de la sesión
```

El archivo **`session_metadata.json`** acompaña a cada grabación con información no personal que enriquece el dataset: timing y sincronización, datos del juego (título, motor, perspectiva, género, idiomas, desarrollador), calidad de video (resolución, FPS, codec, bitrate), key mapping real del juego y specs de hardware/OS. Todo se genera automáticamente.

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

## Preguntas frecuentes (FAQs)

---

**¿Por qué el Synch Checker muestra "Archivo incompleto" en el video y no puede leer la duración?**

Significa que OBS no terminó de escribir el archivo de video correctamente. En el formato MP4 estándar, OBS escribe todos los datos de video primero y al final agrega el índice del archivo (el box `moov`). Si OBS se cierra de forma abrupta durante la grabación —por un crash, cierre forzado, corte de luz o reinicio del equipo— ese índice nunca se escribe. El archivo queda truncado: los datos de video están ahí, pero sin el índice ningún reproductor ni herramienta de IA puede leerlos.

**¿Este dataset es válido para el programa?**

No. Para que una sesión sea válida necesitás el par completo: video reproducible + logs sincronizados. Si el video está truncado, la sesión no es utilizable para entrenamiento de IA, aunque los CSV (mouse, teclado, timeline) estén perfectamente sincronizados. Descartá la sesión e iniciá una nueva grabación.

**¿Puede volver a pasar con la versión actual de Pleiada Recorder?**

Es muy poco probable. Pleiada Recorder configura OBS para grabar en **formato MP4 fragmentado**, donde el índice se escribe al comienzo del archivo y cada fragmento de video queda indexado a medida que se graba. Si OBS se cierra de forma inesperada, el video grabado hasta ese momento sigue siendo reproducible. El caso de video truncado afecta principalmente a grabaciones hechas con versiones anteriores o con una configuración manual de OBS diferente a la recomendada.

**¿Qué hago si me pasa?**

1. Verificá en el Synch Checker — si muestra "Archivo incompleto", la sesión no es válida.
2. Descartá la sesión e iniciá una nueva grabación.
3. Si el problema se repite, asegurate de usar siempre el botón **"Detener grabación"** de Pleiada Recorder para cerrar la sesión de forma limpia.

---

## Contacto y soporte

- Información del programa: [pleiada.ai](https://pleiada.ai)
- Preguntas frecuentes: [pleiada.ai/faqs](https://pleiada.ai/faqs)
- Términos: [pleiada.ai/terms](https://pleiada.ai/terms)

---

## Changelog

### V25.5 — 16/05/2026
- **Mejora — nombre de sesión con juego:** la carpeta de cada grabación ahora incluye el nombre del juego: `NombreJuego_dd_mm_aa__hh_mm_ss recording`. El nombre se extrae automáticamente de la fuente "Captura de Juego" de OBS. Si no hay ventana específica configurada, se usa solo fecha y hora.
- **Fix — Synch Checker detecta video truncado:** si OBS se cerró abruptamente y el MP4 quedó incompleto, ahora se muestra un mensaje claro en lugar de duración N/A sin explicación.

### V25.4 — 16/05/2026
- **Mejora — botón "?" en el Recorder:** reabre el wizard de configuración desde la title bar.
- **Fix — tutorial paso 1:** punto 3 ahora incluye la instrucción de "Capturar Ventana específica".
- **Fix — app sigue abierta al desinstalar:** el desinstalador cierra Pleiada Recorder automáticamente.
- **Fix — textos recortados en Recorder:** "Pleiada Recorder" y "Listo para grabar" ya no se recortan con DPI alto.
- **Fix — scrollbar recortada en Synch Checker:** barra de scroll completamente visible en todos los tamaños de ventana.
- **Mejora — Examinar abre Pleiada Recordings:** el diálogo de selección de carpeta se abre directamente en la carpeta de grabaciones.

### V25.3 — 16/05/2026
- **Fix overlay invasivo:** el floater ya no es siempre visible sobre el juego. Aparece en la barra de tareas de Windows y se puede traer al frente con Alt+Tab. El video de OBS ya no captura el overlay.

### V25.2 — 16/05/2026
- **Fix Synch Checker — 5 archivos:** `mouse_delta_log.csv` ahora se verifica junto a los otros 4 archivos.
- **Fix Synch Checker — GOP parcial final:** el rango "normal" se amplió a `[-4500ms, +10000ms]`. El GOP parcial al detener OBS ya no genera falso "OFFSET".
- **Fix Synch Checker — mensaje de resumen:** actualizado a "5 archivos"; distingue flush del encoder vs GOP parcial final.

### V25.1 — 15/05/2026
- **Fix ortografía — popup de instalación:** corregidas 10 tildes faltantes en el texto de consentimiento.
- **Fix ortografía — popup de error:** "leido los terminos" → "leído los términos".
- **Mejora — botón Volver en el wizard:** el tutorial post-instalación ahora tiene un botón "← Volver" en los pasos 2 y 3.
- **Fix — tutorial paso 2/3:** el texto ahora menciona los textos reales de los botones ("Iniciar grabación" / "Detener grabación") en lugar de íconos ⏺/⏹ que no existen en la UI.
- **Fix — tutorial paso 3/3:** resultados del Synch Checker actualizados (eliminados "OFFSET LEVE" / "OFFSET CRÍTICO", reemplazados por "OFFSET").

### V25 — 15/05/2026
- **Raw Input — mouse_delta_log.csv (nuevo archivo):** registra los deltas de hardware (dx/dy) del mouse por evento, vía Windows Raw Input (WM_INPUT). Funciona aunque el juego tenga el cursor capturado (modos FPS/TPS con aim-lock). Complementa al `mouse_log.csv` que sigue registrando posición absoluta del cursor y botones.
- **Raw Input — KEY_UP:** el `key_log.csv` ahora incluye eventos `KEY_UP` además de `KEY_DOWN`. Permite reconstruir exactamente cuándo se presionó y soltó cada tecla.
- **Raw Input — cobertura total de teclas:** se eliminó el whitelist de ~60 hotkeys de AutoHotkey. Ahora se capturan absolutamente todas las teclas (letras, números, modificadores, F-keys, teclas de media, Windows key, etc.) sin auto-repeat falso.
- **Raw Input — botones de mouse mejorados:** `mouse_log.csv` reemplaza `CLICK` por `BUTTON_DOWN`/`BUTTON_UP`. Agrega botones X1/X2 (laterales) y eventos `SCROLL` con delta de rueda.
- **ANCHOR en 4 archivos:** `ANCHOR_START` y `ANCHOR_END` ahora se escriben en los 4 CSVs.

### V24.1 — 14/05/2026
- **Fix Synch Checker — umbral de extensión de video:** ampliado de 3 s a 10 s. Con keyframe intervals grandes (4–8 s), OBS puede tardar hasta la duración de un GOP en hacer flush al detener — eso es normal y no indica desfase.
- **Fix Synch Checker — mensaje de cierre:** al finalizar la verificación se muestra explícitamente si los 4 archivos están sincronizados y cuántos ms extiende el video post-sesión.
- **Fix Synch Checker — ms redondeados:** corregido un valor flotante en el mensaje de cierre.

### V24 — 13/05/2026
- **Fix sincronización por hardware (segundo moof):** eliminado el offset de ~1.7 s que existía en todas las PCs. `obs_control.py` ya no usa el evento `OBS_WEBSOCKET_OUTPUT_STARTED` como referencia de inicio. En su lugar, espera a que aparezca el segundo box `moof` en el archivo MP4 (= primer GOP completo en disco), calcula la duración exacta del primer GOP en ticks del encoder, y resta ese valor al timestamp de detección para obtener el instante real del primer frame. La corrección es completamente independiente del hardware: funciona igual en cualquier GPU, encoder o configuración de sistema.
- **Synch Checker:** umbral de extensión del video ampliado a 10 s (antes 3 s). Con keyframe intervals grandes (4–8 s), OBS puede tardar hasta la duración de un GOP en hacer flush al detener la grabación — eso es normal y no indica desfase.
- **Synch Checker:** mensaje de cierre explícito — al finalizar la verificación se muestra si los 4 archivos están sincronizados y cuántos ms extiende el video post-sesión.

### V23 — 13/05/2026
- **Fix duración de video (MP4 fragmentado):** el Synch Checker ahora parsea directamente los boxes `moof/tfdt/trun` del MP4 para obtener la duración real. El método anterior (`CAP_PROP_FRAME_COUNT` de OpenCV) subestimaba la duración ~1.7 s en grabaciones OBS.

### V22 — 13/05/2026
- **Fix sincronización:** el offset entre el video y los logs pasó de ~1.4 s a menos de 500 ms.
- **Fix Synch Checker:** corregido el cálculo de duración del video que generaba falsos "OFFSET CRÍTICO".

### V21.1 — 03/05/2026
- **Fix íconos:** los íconos de escritorio ahora se ven en alta definición (16, 32, 48 y 256 px).

### V20 — 03/05/2026
- **OBS inteligente:** si OBS ya está instalado en la versión requerida (32.1.2) o superior, la instalación lo saltea.
- **OBS visible:** el instalador de OBS se muestra en primer plano.

### V19 — 03/05/2026
- **Nuevos íconos:** íconos oficiales de Pleiada Recorder y Synch Checker en alta definición.
- **UI floater rediseñada:** tipografía unificada, timer más grande, botón redondeado, esquinas redondeadas.
- **UI Synch Checker rediseñada:** logo oficial, botón redondeado, tipografía unificada.
- **Nombre de sesión dinámico:** muestra el nombre de carpeta durante la grabación; se convierte en hipervínculo al finalizar.
- **Fix shortcut Synch Checker:** corregida la ruta con espacios en el acceso directo del escritorio.

### V18 — 01/05/2026
- **Auto-stop de sesión:** la grabación se detiene automáticamente al llegar a 1 hora 5 minutos.

### V17.2 — 27/04/2026
- **Fix descarga de AutoHotkey:** resuelto un bloqueo de Cloudflare durante la instalación.

### V17 — 27/04/2026
- Versión inicial de Pleiada Recorder.
- Instalación automática de Python 3.12, AutoHotkey v2, OBS Studio 32.1.2 y dependencias.
- Floater de grabación con timer, control de sesión y límite configurable.
- Synch Checker para verificar sincronización entre video y logs.
- Configuración automática de OBS WebSocket al instalar.

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

**Start:** detecta `obs64.exe` via tasklist → busca el ejecutable (paths conocidos → registro → glob) → conecta WS con auth SHA-256 → si falla, mata y relanza OBS (1 reintento) → desmutea `wasapi_output_capture`, mutea todos los `wasapi_input_capture` → captura `GetRecordDirectory` y lista los MP4 existentes → llama `StartRecord` → espera el evento `RecordStateChanged → STARTED` → cierra el WS → monitorea el nuevo MP4: lee el `timescale` del `mdhd` y espera a que aparezca el **segundo `moof`** (= primer GOP completo en disco) → calcula `anchor_ts = T_detección − duración_primer_GOP_ms` → escribe el anchor en `%TEMP%\pleiada_anchor_ts.txt` para que AHK lo use como `ANCHOR_START`. Esta técnica es independiente del hardware: el offset se mide directamente del archivo generado por el encoder.

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