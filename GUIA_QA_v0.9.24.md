# Guía de QA — Gameplay Recorder v0.9.24

Build local, sin firma de código (Windows puede mostrar el aviso de SmartScreen: "Más información" → "Ejecutar de todas formas"). Actualización sobre cualquier versión anterior con `PleiadaRecorder_Update.exe`; instalación limpia con `PleiadaRecorder_Setup.exe`. La versión se ve en el encabezado de la app: **v0.9.24**.

## Qué hay de nuevo

1. **Duración mínima de 5 minutos.** Una sesión más corta queda como no apta, y el mensaje informa el mínimo.
2. **Sesiones grabadas con versiones anteriores.** Mantienen el mínimo anterior de 30 segundos.
3. **Control de video antes de subir.** El Recorder rechaza una sesión si la resolución es menor a 1080p, si la relación de aspecto es más ancha que 16:9 o si tiene menos de 59 FPS.
4. **Actualización obligatoria.** Las versiones anteriores quedan bloqueadas para grabar.

## Cómo se prueba

Grabar siempre al menos **6 minutos** para las pruebas de sesión válida.

### Caso A — Sesión corta

1. Grabar 2 minutos de un título y detener.

**Resultado esperado**
- Aparece "Sesión no apta para enviar".
- El mensaje dice: "La sesión duró menos de 5 minutos. Grabá al menos 5 minutos de gameplay para que los datos sean válidos."
- En "Mis grabaciones" figura como **No válida**, sin botón "Subir".

### Caso B — Sesión válida

1. Grabar 6 minutos jugando y detener.
2. Subirla.

**Resultado esperado**
- Aparece "¡Sesión lista para enviar!".
- La subida termina bien.
- En `session_metadata.json`, `recorder_version` = `v0.9.24` y `sync.video_spec_failures` = `[]`.

### Caso C — Sesión corta de una versión anterior

Preparación: antes de actualizar, grabar con la versión anterior una sesión de entre 1 y 4 minutos, y no subirla.

1. Actualizar a la v0.9.24.
2. Abrir "Mis grabaciones" y subir esa sesión.
3. Abrir la misma sesión en Gameplay Synch Checker.

**Resultado esperado**
- La sesión sigue como **Pendiente** y se sube bien.
- El Synch Checker no la marca como corta.

### Caso D — Sesión de menos de 30 segundos de una versión anterior

Preparación: necesita una sesión de prueba que entrega el equipo.

1. Abrirla en Gameplay Synch Checker.

**Resultado esperado**
- El mensaje dice: "La sesión duró menos de 30 segundos."

### Caso E — Video fuera de especificación

Preparación: necesita tres sesiones de prueba que entrega el equipo, una por cada falla. Copiarlas en `Documentos\Pleiada Recordings` y abrir "Mis grabaciones".

| Sesión | Mensaje esperado al apretar "Subir" |
|---|---|
| 1280×720 a 60 FPS | "La grabación no llega a la resolución mínima que pide el programa…" |
| 2560×1080 a 60 FPS | "La grabación tiene una relación de aspecto que no podemos usar…" |
| 1920×1080 a 30 FPS | "La grabación quedó por debajo de los cuadros por segundo mínimos…" |

**Resultado esperado**
- No arranca ninguna subida.
- Al apretar "Volver" y reabrir la lista, la sesión figura como **No válida**.
- Gameplay Synch Checker muestra el mismo mensaje sobre esas sesiones.

### Caso F — Formatos que siguen siendo válidos

Preparación: necesita dos sesiones de prueba que entrega el equipo, una de 2560×1440 y otra de 2560×1600, ambas a 60 FPS.

1. Apretar "Subir" en cada una.

**Resultado esperado**
- Las dos pasan a la pantalla normal de confirmación de subida.

### Caso G — Duración máxima y reinicio automático

1. En Ajustes, activar el reinicio automático y dejar la duración máxima en 30 minutos.
2. Grabar hasta que se detenga sola.

**Resultado esperado**
- La sesión se detiene a los 30 minutos, se valida y arranca la siguiente.

### Caso H — Actualización obligatoria

1. Con una versión anterior instalada, abrir la app con esta versión publicada como obligatoria.

**Resultado esperado**
- La app pide actualizar y no deja grabar hasta hacerlo.
- Las sesiones pendientes siguen en "Mis grabaciones" después de actualizar.
