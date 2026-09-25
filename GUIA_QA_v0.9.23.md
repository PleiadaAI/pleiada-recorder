# Guía de QA — Gameplay Recorder v0.9.23

Build local, sin firma de código (Windows puede mostrar el aviso de SmartScreen: "Más información" → "Ejecutar de todas formas"). Actualización sobre cualquier versión anterior con `PleiadaRecorder_Update.exe`; instalación limpia con `PleiadaRecorder_Setup.exe`. La versión se ve en el encabezado de la app: **v0.9.23**.

## Qué hay de nuevo

1. **Vuelve el audio del título.** Desde la v0.9.15 las grabaciones salían sin audio. Ahora el Recorder captura **solo el sonido que reproduce el título** (música, efectos, diálogos). El audio de escritorio y el micrófono siguen apagados: lo que suene en Discord, YouTube, Spotify u otra aplicación **no** se graba.
2. **Metadata más precisa en Windows 11 reciente.** En Windows 11 24H2 y 25H2 la información del proceso del título (ejecutable, versión, motor, placa de video, modo de ventana) podía salir vacía o tomada de otro programa. Corregido.

## Cómo se prueba

### Caso A — Audio del título presente, audio de otras apps ausente

1. Abrir un título que tenga sonido (música o efectos claros).
2. Abrir en paralelo algo que suene fuera del título: un video de YouTube en el navegador o una llamada de Discord.
3. Grabar al menos 1 minuto jugando.
4. Detener. Abrir la carpeta de la sesión (botón "Abrir carpeta") y reproducir el `.mp4` con VLC o el reproductor de Windows.

**Resultado esperado**
- Se oye el sonido del título.
- No se oye YouTube ni Discord.
- En `session_metadata.json`, bloque `audio`: `capture` = `application`, `target_process` = el ejecutable del título, `bitrate_kbps` mayor a 20, `silent_suspected` = `false`.

### Caso B — Título sin sonido o audio no capturable

1. Silenciar el título desde sus opciones (volumen maestro en 0) y grabar 1 minuto.

**Resultado esperado**
- El `.mp4` no tiene sonido audible.
- En `session_metadata.json`, `audio.capture` = `application` y `audio.silent_suspected` = `true`. Es un aviso, no un error: la grabación es válida.

### Caso C — OBS: fuentes de audio

1. Con una grabación en curso, abrir OBS y mirar el panel "Fuentes" y el "Mezclador de audio".

**Resultado esperado**
- Existe una fuente **"Audio del juego"** activa (no muteada), del tipo "Captura de audio de aplicación".
- "Audio del escritorio" y "Mic/Aux" aparecen muteadas.
- Al grabar por segunda vez, sigue habiendo **una sola** fuente "Audio del juego" (no se duplica).

### Caso D — Ejecutable del título correcto con Slack o Discord abiertos (Windows 11 24H2/25H2)

Requiere una PC con Windows 11 24H2 o 25H2. Para confirmarlo: en PowerShell, `where.exe wmic` no devuelve nada.

1. Abrir Slack o Discord y crear o abrir un canal cuyo nombre sea **exactamente el nombre del título** que se va a grabar (por ejemplo, un canal "playground" si el título es Playground). Dejar esa ventana abierta.
2. Grabar 1 minuto del título.
3. Abrir `session_metadata.json`.

**Resultado esperado**
- `game.process_detected` = el ejecutable del título (no `slack.exe` ni `discord.exe`).
- `game.game_version` = una versión coherente con el título (no la de Slack).
- `game.engine` con valor cuando el motor es reconocible (Unity, Unreal, Source); puede quedar vacío en títulos de motor propio.
- `environment.gpus` con al menos una placa de video y su versión de driver.
- `environment.window_mode` con valor: `windowed`, `borderless` o `fullscreen`.

### Caso E — Regresión rápida

1. Grabar una sesión normal de 2 minutos con cualquier título.

**Resultado esperado**
- La grabación arranca y se detiene como siempre; el cuadrado blanco del marcador de sincronía aparece al inicio y al final.
- Los archivos de la sesión son los mismos que en la v0.9.22 más ningún archivo nuevo: el cambio está dentro del `.mp4` (pista de audio) y del `session_metadata.json` (bloque `audio`).
- La subida funciona igual que antes.

## Qué reportar

Por cada caso: versión que muestra la app, título usado, sistema operativo y build de Windows (Configuración → Sistema → Acerca de), y el `session_metadata.json` de la sesión adjunto al ticket.
