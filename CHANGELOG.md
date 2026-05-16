# Changelog — Pleiada Recorder

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
