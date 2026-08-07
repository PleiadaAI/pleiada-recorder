# Changelog — Pleiada Recorder

## v0.8.11 — 05/08/2026 — las subidas dejan de ir por un solo caño

### El problema
Miembros con conexiones de 900 Mbps reportaban subidas a 0,4 MB/s: un dataset de 1,2 GB
tardaba ~50 minutos y uno de una hora de juego, días. No había ningún límite de velocidad
ni en la app ni en el bucket. **La app le entregaba los datos a la red de a 8 KB por vez**
y esperaba; así la conexión nunca tenía datos suficientes en vuelo y quedaba limitada por
el programa, no por internet.

Con ese patrón la velocidad es `tamaño del buffer del socket / tiempo de ida y vuelta`
— **no depende del ancho de banda contratado**, solo de la distancia al bucket. Con el
buffer de 64 KB de Windows:

| Distancia al bucket (São Paulo) | Techo |
|---|---|
| 44 ms | 1,4 MB/s |
| 160 ms | **0,4 MB/s** |

Por eso el número era parecido entre miembros con conexiones muy distintas, y por eso el
test de velocidad de la ISP daba bien: mide otra cosa.

### El arreglo
- **Los datos se entregan de a 256 KB en vez de 8 KB.** Este es el arreglo de fondo.
  Medido contra producción el 05/08, mismo archivo y misma ruta, alternando: **1,33 MB/s
  → 20,3 MB/s**. Un dataset de 1,2 GB pasa de ~50 minutos a ~1.
- **Las partes suben en paralelo** (4 a la vez). Aporta poco en conexiones buenas —que con
  el arreglo anterior ya quedan llenas— pero sí ayuda en las conexiones con más latencia,
  que son justo las de los miembros afectados, y evita que una parte trabada frene al resto.
- **Partes más chicas y adaptadas al archivo** (16 MB; más grandes solo en archivos muy
  grandes, para no pasar de 1.000 partes). Reintentar una parte cortada ahora cuesta
  segundos en vez de minutos.
- **Los permisos de subida se piden por lotes, a medida que hacen falta.** Antes se pedían
  todos al empezar y vencían a las 6 horas: con los datasets de hoy (11–20 GB por hora de
  juego), una sesión larga se quedaba sin permisos a mitad de camino y **la subida fallaba
  entera cerca del final**. Ese era el peor síntoma de todo esto y desaparece.
- Los archivos medianos (más de 64 MB, antes 200) también entran por este camino.
- El archivo se lee del disco a medida que se envía: 8 partes en vuelo ocupan ~2 MB de
  memoria en vez de cientos.
- `Documentos\Pleiada Logs\upload.log` ahora registra **siempre** el resumen de cada
  archivo (MB, segundos, MB/s, partes, reintentos), no solo los errores. Sin eso no había
  con qué diagnosticar un reporte de lentitud.
- Válvula para soporte: `upload_concurrency` en `settings.json` baja o sube las conexiones
  en paralelo (1 a 16) si a alguien el router no le banca 4. Sin interfaz, a propósito.

Cancelar y reintentar siguen funcionando igual, y una subida cancelada sigue sin registrarse.
Los Recorders que todavía no se actualizaron siguen subiendo con el método viejo: el backend
mantiene los dos protocolos.

## v0.8.10 — 28/07/2026 — Gameplay Recorder + un criterio único de validación

> **Actualización obligatoria.** Las versiones anteriores quedan bloqueadas para grabar
> hasta aplicarla.

### La app pasa a llamarse Gameplay Recorder
- Nombre nuevo en todo lo que el usuario lee: título de la ventana, header, pantalla de
  login, acceso directo, textos del instalador y el Synch Checker (ahora **Gameplay Synch
  Checker**).
- **Ícono nuevo**: la G de Gameplay Alliance, en un `.ico` multi-resolución de 16 a 256 px
  para que se vea nítido en la barra de tareas, el escritorio y la vista de iconos grandes.
- Las imágenes del asistente de instalación se rehicieron con la marca nueva. Las viejas
  decían "Pleiada Recorder / Gaming Alliance" — con el nombre del programa mal escrito— y
  "Instalador v1.0" cuando la app iba por v0.8.8. El número de versión se sacó del banner:
  un dato que hay que acordarse de tocar en cada build siempre termina desactualizado.
- El logo original y un script que regenera todos los assets a partir de él quedaron dentro
  del repo (`gen_wizard_art.py`); antes el ícono no tenía fuente versionada.

**Lo que a propósito NO se renombró todavía**, porque tocarlo sin migrar rompe a los
usuarios actuales: la carpeta `Documentos\Pleiada Recordings` (donde están las sesiones ya
grabadas), la configuración en `AppData` (renombrarla desloguea a todos), el perfil de OBS
y la carpeta de logs. Va en una versión propia, con migración.

Dos detalles de la actualización que se contemplaron: el instalador ahora cierra la app
buscando **los dos** nombres de ventana —si solo buscara el nuevo, no encontraría la
versión anterior corriendo y los archivos quedarían bloqueados al copiar— y borra el
acceso directo viejo del escritorio para que no queden dos.

### El Synch Checker y el uploader dejan de contradecirse: un solo criterio de sincronización
- **Causa raíz:** el uploader (`run_sync_check`) y el Synch Checker tenían sus propios
  umbrales hardcodeados, con valores distintos. Una sesión cuyo video excedía entre 10 y
  15 segundos la ventana de sesión **se subía sin problema**, pero el verificador se la
  mostraba al uploader como "OFFSET": un error reportado sobre algo que sí había entrado.
- Peor todavía, cada uno calculaba la duración de la sesión sobre una base distinta —el
  uploader promediaba los 4 CSV, el verificador usaba uno solo— así que podían llegar a
  cifras de desfase diferentes sobre la misma sesión, y la discrepancia no se limitaba a
  esa franja de 10-15 s.
- Ahora ambos leen los umbrales y los gates de `pleiada_sync_limits.py`, un único módulo
  compartido. Ganó el criterio del uploader, que es el que decide qué se sube.
- La franja de 10-15 s pasa a explicarse por su causa real (el logger arrancó unos
  segundos después que OBS, normal en equipos lentos) y no como "flush del encoder", que
  a esa magnitud no era cierto.

### El Synch Checker ya no aprueba sesiones que el uploader rechaza
- El verificador **no conocía** el mínimo de duración de sesión ni el límite de
  inactividad continua, así que podía mostrar "SESIÓN LISTA PARA ENVIAR" sobre una
  sesión que después el uploader rechazaba. Ahora aplica los dos gates y los explica.
- Sección **Actividad** nueva en el reporte, que confirma que el chequeo de inactividad
  corrió.

### El gate AFK ahora también mira la proporción, no solo el tiempo
- El umbral absoluto solo no alcanzaba: una sesión de 7 minutos que es casi toda un único
  período sin actividad **pasaba** (no llega a los 10 minutos), mientras que una de 2 horas
  con el mismo período se rechazaba. Ahora una sesión también se rechaza si el período
  inactivo ocupa más de la mitad del total.
- El criterio ya existía en la verificación server-side desde el 24/07; esto lo trae al
  Recorder, así que la sesión se rechaza **antes de subirla** en vez de marcarse después.
- Medido sobre 47 sesiones locales: la mediana de la proporción inactiva es 0,000 y el
  gameplay real más alto llega a 0,398 — la única sesión que cae ya la rechazaba el
  criterio anterior. No cambia el mensaje que ve el uploader, que sigue sin revelar
  ningún umbral.

### El lector de MP4 también deja de estar duplicado
- `_mp4_frag_duration_ms` y `_mp4_is_truncated` existían por duplicado en el uploader y en
  el Synch Checker, y **las dos copias ya habían divergido**: el uploader ubicaba el índice
  del MP4 recorriendo el archivo desde el principio, mientras que el verificador lo buscaba
  en los últimos 512 KB — un punto que cae dentro del bloque de video y no sirve para
  encontrar nada. Medido sobre los 63 MP4 de prueba: la copia del verificador fallaba en
  39 de los 42 MP4 estándar, y caía a estimar la duración contando frames con OpenCV, que
  queda ~1-2 s corto. Resultado: verificador y uploader calculaban un desfase distinto
  sobre la misma sesión.
- Ahora las dos leen la misma implementación desde `pleiada_sync_limits.py`, la que ya
  usaba el uploader. Verificado: idéntica al comportamiento anterior del uploader en los 63
  archivos, y el verificador pasa de discrepar en 39 a coincidir en todos.
- Esto **solo afectaba a grabaciones en MP4 estándar**, que desde v0.8.5 no deberían
  producirse (se fuerza MP4 fragmentado). El uploader nunca estuvo afectado.

### Corrección menor
- El promedio de duración de los CSV descartaba silenciosamente cualquier archivo cuyo
  `ANCHOR_START` fuera 0. En la práctica no se disparaba (los anchors son epoch), pero
  quedaba como trampa latente.

## v0.8.8 — 22/07/2026 — build de producción (lanzamiento del Marketplace)

- Se retira el preset TEMPORAL de 5 minutos de Ajustes → GRABACIÓN (era solo para QA).
  Presets finales: 30 min / 1 h.

### Multipart: los datasets grandes ya no chocan contra el límite de S3
- **Causa raíz del "EOF occurred in violation of protocol" con sesiones largas:** S3
  rechaza subidas simples de más de 5 GiB (`EntityTooLarge`), y el MP4 de una sesión de
  30 min supera eso de sobra. Ahora los archivos de más de 200 MB se suben en **partes
  de 100 MB**, cada una con sus propios reintentos: no hay más límite de tamaño, y un
  corte de red repite una parte de 100 MB en vez de tirar gigas ya subidos.
- Cancelar (o un fallo definitivo) libera las partes ya subidas en S3 automáticamente.
- Requiere backend `2026-07-22.2` + permiso IAM `s3:AbortMultipartUpload`.

### Subidas resistentes a cortes de red (reporte QA: "EOF occurred in violation of protocol")
- **Reintentos automáticos por archivo** (hasta 3, con espera progresiva y conexión
  nueva): las redes hogareñas a veces matan conexiones TLS largas a mitad de un archivo
  grande — antes eso tiraba toda la subida con un error críptico; ahora se reintenta
  solo. Un PUT interrumpido no deja nada en S3, así que reintentar es seguro.
- **Log de diagnóstico de subidas** en `Documentos\Pleiada Logs\upload.log`: cada fallo
  registra archivo, tamaño, intento, segundos transcurridos y el error exacto — si una
  subida sigue fallando, ese log dice dónde y por qué.

## v0.8.7 — 21/07/2026

### Fix: entrar a Ajustes durante una subida la "cancelaba" y los reintentos morían con error SSL
- **Causa raíz (reporte QA en v0.8.5):** el engranaje ⚙ no tenía guarda durante la subida
  (solo durante la grabación). Abrir Ajustes destruía la vista de progreso pero el thread
  de subida seguía vivo en background; al reintentar se apilaba OTRO thread subiendo los
  mismos archivos en paralelo y las conexiones se mataban entre sí:
  `<urlopen error EOF occurred in violation of protocol (_ssl.c:2417)>`.
- **Fix:** (a) nunca puede haber dos subidas a la vez (flag `_uploading`: si hay una en
  curso, no se lanza otra); (b) durante una subida se bloquean Ajustes y Cerrar sesión —
  la única salida de la pantalla de subida es su botón Cancelar (que desde v0.8.4 cancela
  de verdad).

## v0.8.6 — 20/07/2026 (sin compilar)

### El listado de juegos del Recorder ahora es EXACTAMENTE el del catálogo público
- **Causa raíz del reporte de QA "no me aparece Metro 2033":** el Recorder
  filtraba la lista de Airtable por la columna `active` (438 juegos) en vez de
  `Publicado` (222) — la columna autoritativa que usa
  `catalogo.gameplayalliance.gg`. Además, el fallback bundleado en el
  instalador era una lista vieja de 536 juegos sin Metro 2033: en un install
  fresco sin conexión a Airtable (o buscando antes de que termine el sync),
  el buscador mostraba esa lista vieja.
- El sync ahora filtra por `Publicado` (regla: lo que se ve en el catálogo es
  lo que se puede grabar). El caché local pasa a `games_list_cache_v2.json`
  para invalidar caches viejos con el filtro anterior.
- Nuevo paso de build: `update_games_list.py` regenera el bundle desde
  Airtable con el mismo filtro y el mismo código de descarga de la app
  (documentado en INSTRUCCIONES_PARA_COMPILAR.md). Bundle regenerado:
  222 juegos publicados con metadata completa (incluye default_key_mapping).
- OJO dato: los juegos con órdenes activas deben tener el tilde Publicado en
  Airtable — al momento de este cambio, Elden Ring (GA-2026-003) NO lo tiene.

## v0.8.5 — 20/07/2026 (sin compilar)

### Grabación crash-safe: fragmented MP4 (caso L4D2 20/07)
- **Causa raíz del dataset perdido de L4D2 (20/07):** OBS grababa MP4 clásico, cuyo
  índice (`moov`) se escribe recién al finalizar. OBS murió/fue cerrado sin finalizar
  → 30 min de video (705 MB) quedaron ilegibles, sin resolución/fps/duración
  (`video.*: null`, `truncated: true`).
- El perfil Pleiada de OBS ahora graba **fragmented MP4** (`RecFormat2=fragmented_mp4`):
  cada fragmento es autosuficiente, así que un crash de OBS pierde como mucho el último
  GOP y el archivo sigue siendo reproducible y verificable. Migración triple:
  perfil nuevo del instalador + migración del `basic.ini` existente en el instalador +
  la app fuerza el formato vía WebSocket antes de CADA `StartRecord` (cubre perfiles
  tocados a mano). Si el usuario dejó otro perfil activo en OBS, el Recorder
  activa el perfil "Pleiada" antes de grabar (garantiza 1080p60 + bitrate +
  formato); nunca se escribe sobre los perfiles propios del usuario — solo se
  cambia cuál está activo.
- El sync check ya soportaba fMP4 (duración vía scan de `moof`); verificado con
  fMP4 sano, fMP4 truncado al 60% (usable hasta el último fragmento) y el MP4
  clásico roto de L4D2 (detectado como truncado).

### Gate AFK: sesiones con más de 10 min seguidos sin inputs no son válidas
- El sync check ahora mide el idle continuo máximo (mismo cálculo que el bloque
  `activity` del metadata) y rechaza la sesión si supera `MAX_CONT_IDLE_MS`
  (10 minutos). La pantalla de resultado explica el motivo y la pantalla de
  inicio avisa la regla ANTES de grabar — ambos textos hablan de "períodos
  largos" sin revelar el umbral exacto, a propósito. El metadata registra
  `sync.afk_rejected`. Solo en el Recorder por ahora (el backend no lo valida).
- Origen: la sesión L4D2 del 20/07 grabó 30 min con el jugador alt-tabbeado
  desde el segundo 3 (705 MB de pantalla estática).

### TEMPORAL QA: preset de duración de 5 min
- Ajustes → GRABACIÓN suma el preset `5m` junto a 30m/1h, para que QA pruebe
  ciclos completos rápido. **Sacarlo antes de pasar a producción.**

### Stop de grabación graceful: esperar a que OBS finalice el archivo
- `StopRecord` responde al instante, pero OBS sigue escribiendo el archivo varios
  segundos más. Antes el Recorder intentaba mover el MP4 inmediatamente (con
  reintentos ciegos de 10 s): con archivos grandes o discos lentos podía capturar
  un video a medio finalizar.
- Ahora el stop espera el evento `RecordStateChanged → OUTPUT_STOPPED` (hasta 30 s,
  con fallback a poll de `GetRecordStatus`) antes de buscar/mover el video, y al
  moverlo verifica que tenga índice (`moov`/`moof`) — si no lo tiene, lo deja
  logueado para diagnóstico y el sync check marca la sesión como no válida.
- Además en v0.8.5 (ya commiteado antes): la pantalla de error de subida muestra
  el motivo real del servidor.

## v0.8.4 — 18/07/2026

### Vuelve: duración máxima de sesión configurable + auto-reinicio (rescatado de v0.7.1)
- **Ajustes → GRABACIÓN:** presets de duración máxima (30 min / 1 h — el máximo que el
  Recorder permite grabar). La grabación se corta sola al llegar al límite; el contador
  de la pantalla de grabación y el "SESIÓN MÁX" del inicio reflejan el valor configurado.
- **Reinicio automático (toggle, OFF por defecto):** tras un corte por tiempo con sesión
  válida, muestra una cuenta regresiva de 10 s y arranca una sesión nueva en su propia
  carpeta (cancelable). Si la sesión no pasa el sync check, el ciclo se detiene y avisa.
- Este feature existía solo como cambios sin commitear en el worktree v0.7.1 (nunca se
  mergeó); se rescató (commit 1ceff25 en rama v0.7.1) y se re-implementó sobre v0.8.x.

### Vuelve: crash logging (rescatado de v0.7.1)
- Excepciones no manejadas (main + threads), errores de callbacks de la GUI y crashes
  nativos (faulthandler) quedan en `Documentos\Pleiada Logs\` — una carpeta fácil de
  encontrar para mandarla a soporte.

### El tutorial ahora es web
- Al terminar la instalación ya no se abren las ventanas del wizard local: se abre el
  browser en `https://recorder.gameplayalliance.gg/`. El link "Ver tutorial de
  configuración" de la app abre la misma URL.

## v0.8.3 — 18/07/2026

### Fix: "Cancelar" durante la subida no cancelaba de verdad (issue 7 QA)
- **Causa raíz:** el botón Cancelar solo silenciaba la UI; el thread de subida seguía
  corriendo en background, terminaba de subir los archivos y registraba la subida igual
  (por eso el Data Set "cancelado" aparecía en el dashboard). Ahora la cancelación
  aborta el PUT en curso y el registro (`finalize_upload`) no se llama nunca.
- Del lado del backend (deploy aparte), `finalize_upload` ahora verifica contra S3 que
  todos los archivos del dataset existan con tamaño > 0 antes de registrar la subida:
  una subida incompleta no puede quedar registrada, haga lo que haga el cliente.

## v0.8.2 — 18/07/2026

### Fix: los uploads a Órdenes abiertas fallaban con "No se pudo subir la sesión"
- **Causa raíz:** el uploader leía la duración de la sesión en la clave equivocada del
  metadata (`session.duration_ms` en vez de `timing.duration_ms`, schema 1.1), así que
  mandaba `duration_seconds=0` y el backend rechazaba la subida con un 400. Afectaba a
  todos los uploads. Ahora lee `timing.duration_ms` (con fallback a `end-start`).
- **Inscripciones frescas antes de subir:** el Recorder refresca la lista de órdenes
  inscriptas justo antes del flujo de subida (antes solo al iniciar sesión), por si el
  usuario se inscribe en el dashboard con el Recorder ya abierto.

## V7.0 — 10/06/2026

### Auto-grabación de demos POV (Team Fortress 2 / Left 4 Dead 2)
- **El recorder dispara y corta el demo del juego solo.** Para juegos Source 1 (TF2 y L4D2)
  lanzados con la consola TCP habilitada (`-netconport 2121`, lo deja el setup wizard), al
  empezar a grabar (F9) el recorder manda `record` por la consola y al parar (F10) manda
  `stop`. El miembro **no toca la consola**. El demo aporta la trayectoria de cámara que estos
  juegos no exponen de otra forma.
- **El demo queda dentro de la carpeta de sesión.** Al parar, el recorder copia el `.dem`
  (`pleiada_<anchor_ts>.dem`, nombrado con el anchor para correlación exacta con el video)
  desde la carpeta del juego a la de sesión → el miembro sube **una sola carpeta**. Best-effort:
  si el juego no usa netcon (CS2 va por GOTV server-side, u otros), no pasa nada y la grabación
  sigue normal.

### Protección e integridad de los archivos de sesión
- **Archivos de solo-lectura:** al finalizar una grabación que pasó el sync check, los 4 CSV,
  el MP4, el `session_metadata.json` **y el demo `.dem`** quedan marcados como **solo-lectura**.
  El usuario puede abrirlos y revisarlos (transparencia total) y descartar la sesión completa si
  no quiere compartirla, pero no editarlos. Las sesiones rechazadas no se protegen (se descartan).
- **Manifiesto de integridad (SHA-256):** el `session_metadata.json` incluye un bloque nuevo
  `integrity` con el hash de cada archivo del dataset (4 CSV + MP4 + demo `.dem` si existe).
  Certifica el original en el momento de captura: cualquier edición posterior cambia el hash y
  la sesión se rechaza en el upload. Los derivados/preprocesamiento del AI Lab no afectan este registro.
- **Schema de metadata `1.1`** (antes `1.0`): cambio **aditivo** (solo se agregó `integrity`,
  no se renombró nada). Compatible hacia atrás con los consumidores existentes.

## V6.0 — 31/05/2026

### Metadata de sesión — key mapping y actividad
- **Jerarquía de key mapping ampliada:** `config` (archivo real del juego) →
  **`game_default`** (mapeo de fábrica curado, distribuido por Airtable sin recompilar) →
  `inferred_from_gameplay` → `unknown`. Cubre juegos cuyo config es binario / no accesible
  (RAGE, UE5 Enhanced Input, Unity, propietarios).
- **Fix de modificadores:** `LShift` / `LControl` / `LAlt` ya no se pierden del mapping
  inferido (se normalizan antes del lookup). Teclas frecuentes sin acción conocida se
  registran como `unknown_action`.
- **`possible_remaps`:** teclas observadas ausentes del config / game_default se reportan
  aparte (posible remapeo del usuario), sin pisar el mapping autoritativo.
- **`keys_observed` siempre incluido** (teclas / botones realmente usados en la sesión).
- **Bloque `activity`:** `active_input_ratio`, `idle_seconds`, `longest_idle_seconds` —
  separa gameplay real de cutscenes / menús / AFK.

No hay cambios en el pipeline de grabación/sincronización ni en la UI.

## V5.3 — 31/05/2026

### Captura en pantalla completa exclusiva (fix mayor)
- **Teclado y botones de mouse** ahora se capturan vía low-level hooks
  (`WH_KEYBOARD_LL` / `WH_MOUSE_LL`), que funcionan en juegos en **fullscreen
  exclusivo** (ej: motor Prism3D de Euro Truck) donde el Raw Input no recibía nada.
  Los deltas de mouse siguen por Raw Input (re-registrado para enganchar en ese modo).
- **Detección de "juego activo"** robusta vía `GetForegroundWindow` (antes `WinActive`
  fallaba en fullscreen exclusivo y podía bloquear toda la captura).

### Atajos de teclado + panel de Ajustes (⚙)
- Nuevo ícono de **Ajustes** en la barra superior: ver versión, cerrar sesión y
  configurar atajos.
- **Atajos globales** F9 (iniciar) / F10 (detener), reasignables, que funcionan aunque
  el Recorder no tenga el foco. Las teclas de atajo **no se registran** en los logs.

### Metadata de sesión — mejoras
- **Key mapping del juego correcto:** se lee el config real del propio juego
  (Source `config.cfg` / Unreal `Input.ini`, incl. formato `UserActionMappings`),
  identificando la carpeta del proyecto con match confiable. Si no se encuentra, se
  infiere del gameplay. (Antes podía asignar el mapping de OTRO juego — corregido.)
- **`frames_dropped`**: nuevo campo — frames esperados según el tiempo real de la
  sesión menos los realmente capturados (métrica de calidad del video).
- El análisis de sincronización ahora también verifica `session_metadata.json`.

### Selector de juegos
- Lista de juegos **dinámica** desde la base online: se actualiza en la próxima apertura
  cuando se agregan juegos nuevos (sin reinstalar).
- Selector con **lista alfabética + scroll** (sin lag) y filtrado al escribir.

### Fixes de UI / robustez
- Ya no aparece una ventana de consola al iniciar grabación (sacaba al juego del fullscreen).
- Sesiones con ejecutables de nombre largo (juegos Unreal) ya no se cancelan por un falso
  "el juego se cerró".
- Botón de cerrar (×) siempre visible; nombre de usuario en la barra; checkbox de términos
  del instalador en dos líneas; correcciones varias de layout.

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
