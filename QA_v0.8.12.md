# QA — Gameplay Recorder v0.8.12 (naming del MP4 + config forzada + detección de juego + órdenes completadas)

Build: pendiente · estampado 0.8.12
Backend: **SÍ hay cambios** (actualizado 15/08). Por el naming del MP4 no hacía falta tocar
nada —`_clean()` queda intacto y actúa como no-op—, pero el fix de las órdenes completadas
(punto 2quater) es mitad backend y mitad Recorder: la Lambda `2026-08-15.1` agrega el campo
`call_status` que este Recorder necesita para filtrar.
**Orden de deploy: primero la Lambda, después el Recorder.** Al revés no sirve: sin
`call_status` el Recorder no puede distinguir una orden completada de una llena y sigue
ofreciendo las dos.

## Antes de empezar
**Esta versión no se pensó para salir sola.** Se decidió el 10/08 esperar y agruparla con
más ajustes (ver "Contexto de la decisión" al final). Este checklist queda listo para
correrlo cuando se arme el release con el resto de los cambios — a ese release hay que
sumarle el QA de lo que se junte.

El cambio toca el **move del MP4 al terminar la grabación**, que está en el camino crítico
de la captura. Ahí es donde hay que poner el foco: si el rename falla, se rompe algo mucho
más caro que el bug que arregla.

---

## 1. Lo verificado automáticamente (ya hecho, no hace falta repetir)

- La regla de saneo del Recorder (`_SAFE_NAME` en `pleiada_app.pyw`) es **idéntica carácter
  por carácter** a la del backend (`_SAFE` en `lambda_function.py`): `[^A-Za-z0-9._@-]`.
- Es **idempotente** sobre 10 casos, incluidos `2026-08-02 22-33-10 (1).mp4` y un nombre de
  260 caracteres. Aplicarla dos veces da lo mismo: un nombre ya saneado nunca se degrada.
- `py_compile` de `pleiada_app.pyw` pasa.

---

## 2. Lo que hay que probar a mano

### 2.1 El nombre coincide en las tres puntas — **lo principal**
- [ ] Grabar una sesión corta (2–3 min).
- [ ] El MP4 en la carpeta de sesión se llama `2026-XX-XX_HH-MM-SS.mp4`, con **guiones
      bajos**, no espacios.
- [ ] `session_metadata.json` → `integrity.files` tiene esa misma clave, exacta.
- [ ] Aparece `"naming": "s3-safe"` dentro del bloque `integrity`.
- [ ] Subirla y confirmar en la consola de S3 que el objeto tiene **exactamente** ese nombre.
- [ ] Buscar el hash del video por el nombre del archivo: lo encuentra directo, sin
      necesidad del índice dual.

### 2.2 No se rompió la captura — **el riesgo real de esta versión**
- [ ] El video se mueve a la carpeta de sesión sin errores en `Documentos\Pleiada Logs`.
      Buscar líneas `Video movido a:` y que **no** haya `ADVERTENCIA`.
- [ ] El sync check da OK y la sesión queda válida.
- [ ] El MP4 se abre y reproduce completo (no truncado).
- [ ] Los archivos quedan en solo-lectura como siempre (`_protect_session_files` corre
      después del rename, no antes).
- [ ] Grabar una sesión larga (30+ min) y confirmar que el move del archivo grande no
      falla ni deja el MP4 en `~\Videos`.

### 2.3 Sesión con demo POV (TF2 o L4D2)
- [ ] El `.dem` se copia a la carpeta de sesión con su nombre `pleiada_<ts>.dem`.
- [ ] Aparece en `integrity.files` y el marcador `naming` **sigue estando** (el nombre del
      demo ya era seguro, así que no lo tiene que invalidar).

### 2.4 Compatibilidad hacia atrás
- [ ] Subir una sesión **grabada con v0.8.11** (con el MP4 con espacios todavía en disco):
      tiene que subir igual que siempre, sin el campo `naming`. El fallback de
      `hashes_por_nombre` la sigue cubriendo.
- [ ] Volver a subir una sesión ya subida: sigue diciendo que ya estaba subida.
- [ ] Un Recorder v0.8.11 sin actualizar sigue subiendo bien (el backend no cambió).

### 2.5 El marcador no miente
- [ ] Renombrar a mano el MP4 de una sesión de prueba **antes** de generar el metadata,
      poniéndole un espacio, y confirmar que `naming` **no** se emite. El campo solo sale
      si todos los nombres del bloque ya son seguros.

---

## 2bis. Config de grabación forzada (agregado 14/08)

Todo esto se prueba **antes** de apretar Grabar, tocando OBS a mano, y se verifica en
`%TEMP%\pleiada_obs_debug.txt` (líneas `Config de grabación forzada:` y `Video forzado:`).

### 2bis.1 Vuelve al default nuestro
- [ ] En OBS, con el perfil `Pleiada` activo, poner **Modo de salida: Avanzado**, subir el
      bitrate y bajar la resolución a 1280×720 @ 30. Grabar 2 min con el Recorder.
- [ ] Al terminar: en Ajustes → Salida, el modo volvió a **Sencillo**, la tasa de bits a
      **2500**, la calidad a **Igual que la transmisión** y el formato a **MP4 fragmentado**.
- [ ] En Ajustes → Vídeo: **1920×1080** base y salida, **60** FPS.
- [ ] El MP4 resultante es 1080p60. Confirmar con el Synch Checker o con las propiedades
      del archivo — **no** alcanza con mirar la UI de OBS.
- [ ] **Lo importante: el peso.** Una sesión de 2 min tiene que pesar ~40 MB, no ~300 MB.
      Si pesa de más, `RecQuality` no se aplicó y hay que ver si OBS necesita recargar el
      perfil para tomarlo (ver 2bis.4).

### 2bis.2 Es silencioso
- [ ] No aparece ningún cartel, modal ni mensaje sobre configuración. El usuario aprieta
      Grabar y graba.
- [ ] El tiempo entre apretar Grabar y que arranque la grabación no se nota más largo.

### 2bis.3 Perfil ajeno y perfil borrado
- [ ] Activar otro perfil de OBS (ej. `Sin_Título`), grabar, y confirmar que el Recorder
      pasa a `Pleiada` **sin escribir nada** en el perfil del usuario: volver a ese perfil
      después y verificar que sus valores siguen intactos.
- [ ] Borrar el perfil `Pleiada` en OBS y grabar: se recrea solo y la grabación arranca.
      En el log tiene que estar `CreateProfile result=True`.

### 2bis.4 El riesgo conocido de esta parte
- [ ] **Verificar que OBS toma los parámetros sin reiniciar.** `SetProfileParameter`
      escribe la config, pero si OBS ya tenía el output armado puede seguir usando los
      valores viejos hasta recargar el perfil. Es lo primero a mirar si 2bis.1 falla por
      peso: si pasa, la solución es un `SetCurrentProfile` al mismo perfil después de
      escribir, para forzar la recarga.
- [ ] Grabar **dos sesiones seguidas** sin cerrar OBS y confirmar que la segunda también
      sale 1080p60 con el peso esperado.

## 2ter. Detección del juego capturado (agregado 14/08)

Viene de `_programa\bug_deteccion_juego_obs_2026-08-13.md`.

### 2ter.1 Escapes `#XX` — el 25% del catálogo
- [ ] Elegir un título con `:` en el nombre (ej. `Horizon Zero Dawn: Complete Edition`),
      apuntar el Game Capture a esa ventana y confirmar que el Recorder **no** bloquea y
      que en pantalla el título se ve con `:` y no con `#3A`.
- [ ] En `session_metadata.json`, `game.obs_title` sale decodificado y
      `game.obs_window_raw` conserva el string crudo con `#3A`.

### 2ter.2 Matcher endurecido — **lo delicado**
- [ ] Los tres casos del reporte bloquean: con OBS capturando
      `Marvel's Spider-Man Remastered`, seleccionar `Marvel's Spider-Man`,
      `Marvel's Spider-Man 2` y `Marvel's Spider-Man: Miles Morales` → los tres frenan.
- [ ] **Lista de pares reales.** Antes de publicar, correr el matcher contra pares
      (título elegido, window string real de OBS) tomados de sesiones ya subidas. Sin esa
      lista, esto no sale: endurecer convierte falsos positivos silenciosos en **bloqueos
      visibles**, y un bloqueo de más frena a alguien que hoy graba bien.
- [ ] Revisar `%TEMP%\pleiada_obs_debug.txt` buscando `title_match ENDURECIDO bloqueó:`.
      Cada línea es un caso que la regla vieja dejaba pasar: son los candidatos a falso
      bloqueo y hay que mirarlos uno por uno.
- [ ] Caso conocido que ahora bloquea y antes no: título abreviado por el usuario en la
      ventana (`AC Odyssey` contra `Assassin's Creed Odyssey`). Decidir si se acepta o si
      hay que relajar la regla.
- [ ] Pedir a los usuarios que reportaron Dark Souls III y SuperHot el valor exacto del
      campo *Ventana* del Game Capture (Propiedades → desplegable "Ventana"): sin ese dato
      esos dos casos siguen sin reproducirse.

### 2ter.3 No enforcement nuevo en la metadata
- [ ] `game.process_detected`, `obs_window_raw` y `obs_title` aparecen en el metadata y
      ninguno frena la grabación ni la subida cuando vienen vacíos o nulos.

## 2quater. Órdenes completadas ya no reciben subidas (agregado 15/08)

Bug encontrado el 15/08: el Recorder ofrecía **GA-2026-007 (ACCIÓN)** como destino de
subida, con la orden en `completado` desde fines de julio. Se arregla en las dos puntas:
la Lambda rechaza en el gate y el Recorder deja de ofrecerla.

### 2quater.1 El Recorder no la ofrece
- [ ] Con un usuario inscripto a una orden **completada** y a una **activa** que acepten el
      mismo juego, grabar una sesión de ese juego: en "Orden de destino" tiene que aparecer
      **solo la activa**. Antes aparecían las dos.
- [ ] Si la completada era la única inscripción que aceptaba ese juego, sale la pantalla de
      "no entra en ninguna de tus órdenes activas" — no una lista con una opción muerta.

### 2quater.2 La orden LLENA pero activa sigue aceptando — **lo que no se puede romper**
- [ ] Con una orden en `activo` que ya pasó el 100% de sus horas (pero por debajo del 110%),
      confirmar que **sigue apareciendo** como destino y que la subida entra.
      Es el caso que protege al que estaba grabando cuando la orden se llenó: si esto se
      rompe, el fix causa más daño que el bug. El Recorder filtra por `call_status`
      (status crudo), **no** por `call_estado` (que mezcla completada con llena).

### 2quater.3 El gate del backend, con un Recorder viejo
- [ ] Con un Recorder **v0.8.11 sin actualizar** (que todavía ofrece la orden completada),
      elegirla y darle Subir: tiene que frenar con "Esta orden ya está completa" **antes**
      de empezar a transferir bytes, no a mitad de la subida.
- [ ] En CloudWatch la línea de cold start dice `LAMBDA_VERSION=2026-08-15.1`.

### 2quater.4 El dashboard no se rompe
- [ ] En el dashboard web, la orden completada sigue viéndose en el historial del usuario
      con sus horas y sus subidas. El fix saca la posibilidad de subir, no el registro.

---

## 3. Al publicar

- [ ] Regenerar `Output\latest.json` con v0.8.12.
- [ ] **NO subir `min_version.txt`.** Decidido el 10/08: el update es opcional. El fix es
      invisible para el uploader y no justifica forzar una actualización; el campo `naming`
      existe justamente para convivir con las dos convenciones.
- [ ] Release de GitHub + push: requiere OK explícito de Martín.

## 4. Lo que esta versión NO hace

No migra los ~4.000 datasets ya subidos. Siguen con el nombre viejo en `integrity` y sin
`naming`, y esa ausencia es la señal de que hay que indexar por las dos formas.
`hashes_por_nombre` en `Pleiada Tools\qa_muestreo\troveo\entregar.py` **se queda
permanente** — no se puede retirar con este fix.

## 5. Contexto de la decisión (10/08/2026)

Se evaluó si mandarlo como hotfix mandatorio. Se decidió que **no**:
no hay pérdida ni corrupción de datos (los hashes son correctos, los datasets están
enteros), el workaround del consumidor ya está en producción y no se puede retirar igual,
y el release toca el camino crítico de la captura en medio de un sprint con holgura cero.

**Lo que cambiaría esa decisión:** que entre un cliente que reciba datasets crudos y corra
su propia verificación de integridad, sin pasar por `entregar.py`. Ese cliente no tiene el
índice dual: vería "hash no encontrado" para el video y lo leería como dataset corrupto.
Ese es el riesgo verdadero — reputacional, no técnico. Mientras las entregas salgan por
`entregar.py`, está cubierto.
