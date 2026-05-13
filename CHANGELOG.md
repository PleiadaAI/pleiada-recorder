# Changelog — Pleiada Recorder

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
