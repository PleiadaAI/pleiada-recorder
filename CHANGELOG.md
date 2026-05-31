# Changelog — Pleiada Recorder

## V4.6 — 30/05/2026

> Primera versión de la **arquitectura unificada** (app única: login, selector de
> juego, grabación, sync automático y metadata) publicada en `main`. Reemplaza la
> línea V25.x basada en `gameplay_logger.ahk`.

### Metadata de sesión (nuevo)
- **`session_metadata.json`** por sesión, junto a los CSVs y el MP4. Incluye:
  timing y sincronización, datos del juego, calidad de video, hardware/OS y key mapping.
- **Key mapping real:** se lee del config del propio juego — Source (`config.cfg`)
  y Unreal (`Input.ini`, formatos legacy y `UserActionMappings`). Si el usuario
  personalizó sus controles, se refleja su binding real (`binding_source: "config"`).
  Si no se encuentra el config, se infiere del gameplay (`inferred_from_gameplay`).
- **Búsqueda multi-disco:** localiza la instalación del juego en cualquier unidad
  vía las bibliotecas de Steam.
- **Enriquecimiento IGDB:** motor, perspectiva de cámara, temas, idiomas y
  desarrollador de cada juego, vía la API de IGDB.

### Lista de juegos dinámica
- El listado de juegos se sincroniza desde una base en Airtable al iniciar la app
  (caché local de 24 h, fallback al listado bundleado). Permite agregar juegos sin
  recompilar el instalador.

### Calidad de video
- Resolución, FPS, codec, frame count y bitrate extraídos de cada grabación.

### Cambios de flujo
- El video ya **no se cifra ni empaqueta**: los archivos quedan locales en la
  carpeta de sesión para su revisión y subida.
- Validación de duración mínima (30 s) y de juego en ejecución antes de grabar.
- Countdown de inicio reducido a 10 s.

### Fixes
- Botón "Nueva grabación" siempre visible. Textos sin recorte en pantallas con
  escalado DPI. Detección de fuente de OBS por escena.

## V25.5 — 16/05/2026
- **Mejora — nombre de sesión con juego:** la carpeta de cada grabación ahora incluye el nombre del juego capturado en OBS: `NombreJuego_dd_mm_aa__hh_mm_ss recording`. El nombre se extrae automáticamente de la fuente "Captura de Juego" configurada en OBS (campo "Ventana específica"). Si no hay ventana configurada, se usa el formato anterior de solo fecha y hora.
- **Fix — Synch Checker detecta video truncado:** si OBS se cerró abruptamente y el archivo MP4 quedó incompleto (sin el bloque `moov`), el Synch Checker ahora lo detecta y muestra un mensaje claro: "Archivo incompleto — OBS cerró sin finalizar la grabación." En lugar de mostrar duración N/A sin explicación. Los archivos generados con la configuración recomendada (MP4 fragmentado) no se ven afectados por este problema.
- **Fix — detección de video truncado (falso positivo):** el Synch Checker marcaba incorrectamente como "Archivo incompleto" videos perfectamente válidos. El bug tenía dos variantes: (1) en MP4 fragmentado, el último `mdat` siempre declara un size levemente mayor que los bytes reales escritos — comportamiento normal del muxer de OBS; (2) en MP4 estándar, el `moov` está al final del archivo después de un `mdat` de varios GB — la búsqueda fallaba porque intentaba leer desde el interior del `mdat`. Corregido: la detección ahora recorre los top-level boxes leyendo solo los headers (8 bytes) y saltando el contenido, encontrando el `moov` en cualquier posición sin falsos positivos.
- **Mejora — FAQ en README:** nueva sección de Preguntas Frecuentes con el caso "¿Por qué el Synch Checker muestra 'Archivo incompleto'?" y sus implicancias para el dataset.

## V25.4 — 16/05/2026
- **Mejora — botón "?" en el Recorder:** nuevo botón en la title bar que reabre el wizard de configuración inicial en cualquier momento (útil para reconfigurar Game Capture al cambiar de juego).
- **Fix — tutorial desactualizado (paso 1, punto 3):** agregada la instrucción faltante: "en Modo seleccioná 'Capturar Ventana específica' y en Ventana seleccioná la que esté mostrando tu juego ya iniciado."
- **Fix — app sigue abierta al desinstalar:** el desinstalador ahora cierra Pleiada Recorder automáticamente antes de eliminar los archivos (`[UninstallRun]` con taskkill por título de ventana).
- **Fix — textos recortados en Recorder:** los controles de "Pleiada Recorder" (w182→w200) y "Listo para grabar" (w130→w145) ampliados para evitar recorte con escalado DPI alto.
- **Fix — scrollbar recortada en Synch Checker:** reemplazado `ScrolledText` por `Text + Scrollbar` manual con layout `grid` e insets explícitos; la barra de scroll ya no queda clipeada por el borde del frame.
- **Mejora — Examinar abre Pleiada Recordings:** el diálogo de selección de carpeta en el Synch Checker se abre directamente en `Documentos\Pleiada Recordings` en lugar de la carpeta raíz del sistema.

## V25.3 — 16/05/2026
- **Fix overlay invasivo:** el floater de Pleiada Recorder ya no es `+AlwaysOnTop` ni `+ToolWindow`. Ahora aparece en la barra de tareas de Windows y puede traerse al frente con Alt+Tab sin interrumpir el juego. El overlay tampoco queda grabado en el video cuando OBS captura en modo ventana. El Raw Input (`RIDEV_INPUTSINK`) sigue funcionando sin cambios — captura teclado y mouse aunque el juego tenga el foco.

## V25.2 — 16/05/2026
- **Fix Synch Checker — 5 archivos:** `mouse_delta_log.csv` ahora se verifica junto a los otros 4 archivos. El reporte muestra los 5 y la sincronización se mide entre los 4 CSVs.
- **Fix Synch Checker — GOP parcial final:** el rango "normal" en la comparación CSV vs Video se amplió a `[-4500ms, +10000ms]`. Cuando OBS detiene la grabación en medio de un GOP (hasta ~4s antes de ANCHOR_END), ahora se reporta como "SINCRONIZADOS — GOP parcial final descartado, normal" en lugar de "OFFSET". El diagnóstico confirmado via debug log: el anchor es correcto, el video termina antes de ANCHOR_END cuando OBS descarta el último GOP incompleto.
- **Fix Synch Checker — mensaje de resumen:** actualizado a "5 archivos"; distingue entre video que extiende post-sesión (flush del encoder) y video que termina antes de ANCHOR_END (GOP parcial).

## V25.1 — 15/05/2026
- **Fix ortografía — popup de instalación:** corregidas 10 tildes faltantes en el texto de consentimiento del instalador (información, ¡Bienvenidos!, Está, código, QUÉ, sesión, grabación, anónima, ningún, identificación, instalación, leído, términos).
- **Fix ortografía — popup de error (términos no aceptados):** "leido los terminos" → "leído los términos".
- **Mejora — botón Volver en el wizard:** el tutorial post-instalación ahora tiene un botón "← Volver" en los pasos 2 y 3 para poder revisar el paso anterior.
- **Fix — tutorial paso 2/3:** el texto ya no hace referencia a íconos ⏺/⏹ que no existen en la UI; ahora menciona los textos reales de los botones ("Iniciar grabación" / "Detener grabación").
- **Fix — tutorial paso 3/3:** los resultados del Synch Checker estaban desactualizados (mostraban "OFFSET LEVE" y "OFFSET CRÍTICO" eliminados en V24); ahora muestra solo "SINCRONIZADOS" u "OFFSET".

## V25 — 15/05/2026
- **Raw Input — mouse_delta_log.csv (nuevo archivo):** registra los deltas de hardware (dx/dy) del mouse por evento, vía Windows Raw Input (WM_INPUT). Funciona aunque el juego tenga el cursor capturado (modos FPS/TPS con aim-lock). Complementa al `mouse_log.csv` que sigue registrando posición absoluta del cursor y botones.
- **Raw Input — KEY_UP:** el `key_log.csv` ahora incluye eventos `KEY_UP` además de `KEY_DOWN`. Permite reconstruir exactamente cuándo se presionó y soltó cada tecla.
- **Raw Input — cobertura total de teclas:** se eliminó el whitelist de ~60 hotkeys de AutoHotkey. Ahora se capturan absolutamente todas las teclas (letras, números, modificadores, F-keys, teclas de media, Windows key, etc.) sin auto-repeat falso.
- **Raw Input — botones de mouse mejorados:** `mouse_log.csv` reemplaza `CLICK` por `BUTTON_DOWN`/`BUTTON_UP`. Agrega botones X1/X2 (laterales) y eventos `SCROLL` con delta de rueda (+120 = un tick arriba, -120 = un tick abajo).
- **ANCHOR en 4 archivos:** `ANCHOR_START` y `ANCHOR_END` ahora se escriben en los 4 CSVs (`mouse_log`, `mouse_delta_log`, `key_log`, `video_timeline`).

## V24.1 — 14/05/2026
- **Fix Synch Checker — umbral de extensión de video:** ampliado de 3 s a 10 s. Con keyframe intervals grandes (4–8 s), OBS puede tardar hasta la duración de un GOP en hacer flush al detener — eso es normal y no indica desfase.
- **Fix Synch Checker — mensaje de cierre:** al finalizar la verificación se muestra explícitamente si los 4 archivos están sincronizados y cuántos ms extiende el video post-sesión.
- **Fix Synch Checker — ms redondeados:** corregido un valor flotante que aparecía en el mensaje de cierre (ej: `5218.666...` ms → `5219` ms).

## V24 — 13/05/2026
- **Fix sincronización por hardware (primer moof):** eliminado el offset de ~1.7 s que existía en todas las PCs. El recorder ya no usa el evento `OBS_WEBSOCKET_OUTPUT_STARTED` como referencia de inicio (ese evento dispara ~0.75 s antes del primer frame real). En su lugar, `obs_control.py` espera a que aparezca el primer box `moof` en el archivo MP4, calcula su duración exacta en ticks del encoder, y resta ese valor al timestamp de detección para obtener el instante real del primer frame. La corrección es completamente independiente del hardware: funciona igual en cualquier GPU, encoder o configuración de sistema.

## V23 — 13/05/2026
- **Fix duración de video (MP4 fragmentado):** el Synch Checker ahora parsea directamente los boxes `moof/tfdt/trun` del MP4 para obtener la duración real. El método anterior (`CAP_PROP_FRAME_COUNT` de OpenCV) subestimaba la duración ~1.7 s en grabaciones OBS, causando el "OFFSET LEVE" reportado. El resultado ahora es preciso y debería mostrar diferencia ≤ 100 ms.

## V22 — 13/05/2026
- **Fix sincronización:** el offset entre el video y los logs pasó de ~1.4 segundos a menos de 500 ms. El recorder ahora espera la confirmación exacta de OBS de que el primer frame fue escrito antes de iniciar el registro.
- **Fix Synch Checker:** corregido el cálculo de duración del video que generaba falsos "OFFSET CRÍTICO" en grabaciones de OBS. El resultado ahora refleja el desfase real.

## V21.1 — 03/05/2026
- **Fix íconos:** los íconos de Pleiada Recorder y Synch Checker en el escritorio ahora se ven en alta definición (se incluyen tamaños 16, 32, 48 y 256 px en el instalador).

## V20 — 03/05/2026
- **OBS inteligente:** si OBS ya está instalado en la versión requerida (32.1.2) o superior, la instalación lo saltea completamente.
- **OBS visible:** el instalador de OBS se muestra en primer plano para mayor transparencia con el usuario.

## V19 — 03/05/2026
- **Nuevos íconos:** íconos oficiales de Pleiada Recorder y Synch Checker en alta definición (16, 32, 48 y 256 px).
- **UI floater rediseñada:** tipografía Segoe UI unificada, timer más grande, botón redondeado con color púrpura, esquinas redondeadas en toda la ventana, puntos estilo macOS.
- **UI Synch Checker rediseñada:** logo oficial cargado desde PNG, botón "Verificar Sync" redondeado, tipografía unificada, etiquetas en minúscula.
- **Nombre de sesión dinámico:** durante la grabación muestra el nombre de la carpeta donde se guardan los archivos; al finalizar se convierte en un hipervínculo que abre esa carpeta.
- **Fix shortcut Synch Checker:** el acceso directo del escritorio ahora abre la aplicación correctamente (ruta con espacios corregida).

## V18 — 01/05/2026
- **Auto-stop de sesión:** la grabación se detiene automáticamente al alcanzar el límite de sesión (1 hora 5 minutos).
- **Textos del wizard actualizados:** mensajes de bienvenida e instrucciones revisados.

## V17.2 — 27/04/2026
- **Fix descarga de AutoHotkey:** se resolvió un bloqueo de Cloudflare durante la instalación automática de AutoHotkey.

## V17 — 27/04/2026
- Versión inicial de Pleiada Recorder.
- Instalación automática de Python 3.12, AutoHotkey v2, OBS Studio 32.1.2 y dependencias.
- Floater de grabación con timer, control de sesión y límite configurable.
- Synch Checker para verificar sincronización entre video y logs.
- Configuración automática de OBS WebSocket al instalar.
