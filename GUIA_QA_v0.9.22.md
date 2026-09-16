# Guía de QA — Gameplay Recorder v0.9.22

## Qué hay de nuevo

Build corto sobre la v0.9.21 con un solo cambio: **PLE-190 corregido de raíz**. Todo lo demás de las guías v0.9.20 y v0.9.21 sigue vigente.

Lo que pasaba: OBS guarda su escena en disco cuando el Recorder crea el marcador de sincronía, pero no volvía a guardarla cuando el Recorder lo borra. Si OBS se cerraba por la fuerza después, al reabrir cargaba la versión guardada y "Pleiada Sync Marker" reaparecía en Fuentes. Ahora el Recorder obliga a OBS a guardar la escena después de cada borrado, y además limpia cualquier resto en cuanto OBS vuelve a responder, estando el Recorder en la pantalla principal.

---

## Antes de empezar

- Instalar `PleiadaRecorder_Setup.exe` (build v0.9.22) sobre la versión anterior. En el título de la ventana y en **Ajustes → Versión** tiene que decir **v0.9.22**.
- Orden de prueba: `GA-2026-019`.
- Si en OBS ya quedó un "Pleiada Sync Marker" de una prueba anterior, borrarlo a mano antes de empezar (clic derecho → Eliminar), para que el caso S1 arranque limpio.
- Este build **no está firmado**: Windows puede mostrar "Editor desconocido" o una advertencia de SmartScreen al instalarlo. Es esperado en un build de prueba.

---

## S · Marcador y cierre forzado de OBS

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| S1 | Grabar 1 minuto, matar OBS desde el Administrador de tareas **sin detener** en el Recorder, detener desde el Recorder, y volver a abrir OBS a mano. Si OBS pregunta por el modo seguro, elegir **Ejecutar en modo normal**. | Al abrir OBS, **"Pleiada Sync Marker" no está en Fuentes**. |
| S2 | Repetir S1 pero matando OBS **en los primeros 2 segundos** de la grabación (justo cuando arranca). | Igual: al reabrir OBS, la fuente no está. Si excepcionalmente apareciera, con el Recorder en la pantalla principal tiene que **desaparecer sola en menos de un minuto**, sin grabar nada. |
| S3 | Con OBS reabierto después de S1, grabar 2 minutos normales, mirando la lista de Fuentes. | La fuente no figura durante la grabación (solo un instante al arrancar y al detener). El MP4 tiene el cuadrado blanco en los primeros y en los últimos cuadros. |
| S4 | Cerrar OBS normalmente (con la X) después de S3 y volver a abrirlo. | La fuente no está. La escena queda igual que antes de todas las pruebas: mismas fuentes, mismo orden. |
| S5 | Detener una grabación normal con OBS abierto (control). | Todo como en la v0.9.21: el resultado tarda lo mismo que siempre y la sesión sale válida con `sync_markers.csv` completo (`start` y `end`). |

---

## Smoke test — que no se haya roto nada

1. Instalar sobre la versión anterior; la app abre; el título dice **v0.9.22**.
2. Login; la lista de títulos carga; se puede elegir orden.
3. Grabar 3 minutos con `GA-2026-019`, cortar, sesión completa: **1 video + 5 CSV + `session_metadata.json`**.
4. Subir una sesión desde la pantalla de resultado y otra desde Mis grabaciones.

---

## Qué reportar

Para cada caso: qué probaste, qué esperabas, qué pasó, y una captura de la lista de Fuentes de OBS después de reabrirlo.

Si la app se cierra sola o se congela, mandá también los archivos de:

```
C:\Users\<tu usuario>\Documents\Pleiada Logs\
```

(`crash.log` y `faulthandler.log`)

## Datos del build

| | |
|---|---|
| Versión | **v0.9.22** |
| Reemplaza a | v0.9.21 |
| Firma | Sin firmar (build de prueba) |
| Orden de prueba | `GA-2026-019` |
| Tickets que cubre | PLE-190 |
