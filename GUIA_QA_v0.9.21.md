# Guía de QA — Gameplay Recorder v0.9.21

## Qué hay de nuevo

Build corto sobre la v0.9.20 con lo que salió de la ronda anterior. Todo lo demás de la guía v0.9.20 sigue vigente.

1. **La fuente "Pleiada Sync Marker" ya no queda en la lista de Fuentes de OBS durante la grabación** (PLE-189). Ahora existe solo el instante del flash, al arrancar y al detener.
2. **Si OBS se cierra por la fuerza durante una grabación, la fuente ya no queda guardada en la escena** (PLE-190). Al reabrir OBS, el Recorder la borra en cuanto OBS vuelve a responder.
3. **Detener con OBS cerrado ya no tarda más de un minuto** (PLE-141). Si OBS no está corriendo, el Recorder pasa a la verificación en segundos.
4. **`mouse → polling` en `session_metadata.json` ya no es `null`** (PLE-188): siempre es un bloque, y cuando no se pudo estimar dice por qué en `reason`. Además, corrección de la guía anterior: el layout de teclado son los campos `keyboard → klid` y `keyboard → locale`; el campo `keyboard → layout` nunca existió.

---

## Antes de empezar

- Instalar `PleiadaRecorder_Setup.exe` (build v0.9.21) sobre la versión anterior. En el título de la ventana y en **Ajustes → Versión** tiene que decir **v0.9.21**.
- Orden de prueba: `GA-2026-019`.
- Para los casos S hace falta un reproductor que permita ir cuadro por cuadro (VLC con la tecla **E**).
- Este build **no está firmado**: Windows puede mostrar "Editor desconocido" o una advertencia de SmartScreen al instalarlo. Es esperado en un build de prueba.

---

## S · Fuente del marcador en OBS

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| S1 | Grabar 2 minutos con la ventana de OBS a la vista, mirando la lista de **Fuentes** de la escena durante toda la grabación. | "Pleiada Sync Marker" **no figura** en la lista mientras se graba. Como mucho se la ve aparecer y desaparecer un instante al arrancar y otro al detener. |
| S2 | Detener y abrir el MP4 cuadro por cuadro, principio y final. | El cuadrado blanco de 32×32 sigue estando en los primeros y en los últimos cuadros, igual que en la v0.9.20. `sync_markers.csv` tiene las filas `MARKER_ON` / `MARKER_OFF` con `start` y con `end`. |
| S3 | Grabar 1 minuto, matar OBS desde el Administrador de tareas **sin detener** en el Recorder, y detener recién después desde el Recorder. Después volver a abrir OBS a mano. | Al reabrir OBS, si "Pleiada Sync Marker" aparece en Fuentes, **desaparece sola en menos de un minuto** con el Recorder en la pantalla principal (sin grabar nada). Si no aparece, mejor. |
| S4 | En S3, cronometrar desde que se toca **Detener** hasta que aparece la pantalla de resultado. | **Menos de 20 segundos.** La sesión queda como no válida (video incompleto), igual que antes; lo que cambia es el tiempo. |
| S5 | Grabar 1 minuto y **Cancelar** con OBS abierto. | Sin fuente en OBS después de cancelar; la app responde normal. |
| S6 | Detener una grabación normal, con OBS abierto (control). | Todo como en la v0.9.20: el resultado tarda lo mismo que siempre y la sesión sale válida. |

---

## D · Metadata de dispositivos

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| D1 | Grabar 2 minutos de un título que use el **mouse** (moviéndolo de verdad) y abrir `session_metadata.json` → `input → device_metadata → mouse → polling`. | `estimated_hz` es un número plausible (típico 125, 500 o 1000), `interval_mode_ms` el intervalo en ms, `samples` la cantidad de movimientos. |
| D2 | Grabar 1 minuto de un título **solo de teclado**, sin tocar el mouse. | `polling` sigue siendo un bloque, con `"estimated_hz": null` y `"reason": "no raw mouse movement in this session"`. |
| D3 | Grabar 1 minuto moviendo el mouse muy poco (unos segundos). | `"estimated_hz": null` y `"reason": "too few raw mouse samples (need 200)"`, con `samples` menor que 200. |
| D4 | En `keyboard`, revisar los campos. | `klid` (por ejemplo `0000080A`) y `locale` (por ejemplo `es-AR`) con valor. No existe `layout`. |

---

## Smoke test — que no se haya roto nada

1. Instalar sobre la versión anterior; la app abre; el título dice **v0.9.21**.
2. Login; la lista de títulos carga; se puede elegir orden.
3. Grabar 3 minutos con `GA-2026-019`, cortar, sesión completa: **1 video + 5 CSV + `session_metadata.json`**, y el cuadrado blanco en los extremos del video.
4. Subir una sesión desde la pantalla de resultado y otra desde Mis grabaciones.

---

## Qué reportar

Para cada caso: qué probaste, qué esperabas, qué pasó. Para S3 y S4, el tiempo medido y una captura de la lista de Fuentes de OBS. Para los casos D, el `session_metadata.json`.

Si la app se cierra sola o se congela, mandá también los archivos de:

```
C:\Users\<tu usuario>\Documents\Pleiada Logs\
```

(`crash.log` y `faulthandler.log`)

## Datos del build

| | |
|---|---|
| Versión | **v0.9.21** |
| Reemplaza a | v0.9.20 |
| Firma | Sin firmar (build de prueba) |
| Orden de prueba | `GA-2026-019` |
| Tickets que cubre | PLE-141, PLE-188, PLE-189, PLE-190 |
