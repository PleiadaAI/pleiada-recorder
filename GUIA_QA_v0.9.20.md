# Guía de QA — Gameplay Recorder v0.9.20

## Qué hay de nuevo

Tres cambios, todos del lado de la app. Todo lo demás de las guías v0.9.18 y v0.9.19 sigue vigente.

1. **Marcador de sincronía en el video.** Al arrancar y al detener la grabación, durante una fracción de segundo aparece un **cuadrado blanco chico en la esquina superior izquierda** de la imagen grabada. Sirve para medir con exactitud la alineación entre el video y los registros de teclado y mouse. Además, la carpeta de la sesión trae un archivo nuevo, `sync_markers.csv`, que se sube junto con el resto.
2. **Campo "DPI de tu mouse (opcional)" en Ajustes**, y un bloque nuevo de información de dispositivos (mouse y teclado) dentro de `session_metadata.json`.
3. **`session_metadata.json` sale entero en inglés.** Hasta la v0.9.19 varias claves y valores estaban en español. Cambia el número de esquema a `1.3`.

---

## Antes de empezar

- Instalar `PleiadaRecorder_Setup.exe` (build v0.9.20) sobre la versión anterior. En el título de la ventana y en **Ajustes → Versión** tiene que decir **v0.9.20**.
- Cerrar sesión y volver a entrar en el Recorder.
- Órdenes de prueba: `GA-2026-019` (sin bono) para todo lo de esta guía; `GA-2026-021` (con bono) solo para el smoke test.
- Para los casos S hace falta un reproductor que permita ir cuadro por cuadro (VLC con la tecla **E**, o MPC-HC con **Ctrl+→**).
- Este build **no está firmado**: Windows puede mostrar "Editor desconocido" o una advertencia de SmartScreen al instalarlo. Es esperado en un build de prueba.

---

## S · Marcador de sincronía

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| S1 | Grabar 3 minutos con `GA-2026-019` y detener con el atajo de teclado. Abrir el MP4 e ir cuadro por cuadro desde el principio. | En los **primeros cuadros** (hasta unos 10) hay un **cuadrado blanco de 32×32 px en la esquina superior izquierda**. Después desaparece y no vuelve a verse durante el gameplay. |
| S2 | En el mismo MP4, ir cuadro por cuadro desde el final hacia atrás. | En los **últimos cuadros** (hasta unos 10) vuelve a aparecer el mismo cuadrado blanco. |
| S3 | Abrir la carpeta de la sesión. | Hay un archivo nuevo **`sync_markers.csv`**. Abierto con el bloc de notas tiene la cabecera `timestamp_ms,event_type,ack_ms,detail` y, para 3 minutos, estas filas en este orden: `MARKER_ON` y `MARKER_OFF` con `detail` = `start`; dos o tres filas `TIMECODE` (una por minuto, con un número en `detail`); y `MARKER_ON` y `MARKER_OFF` con `detail` = `end`. |
| S4 | En `session_metadata.json` de esa sesión, buscar `sync_markers`. | Dentro de `timing` hay un bloque `sync_markers` con `"markers": 2`, `"timecode_probes"` igual a la cantidad de filas `TIMECODE` del CSV y `"error": null`. En `integrity → files` figura `sync_markers.csv` con su hash. |
| S5 | Con la grabación en curso, mirar la ventana de OBS. | En la lista de fuentes de la escena **no** queda ninguna fuente llamada "Pleiada Sync Marker" una vez que arrancó la grabación (aparece solo un instante al inicio y al final). Después de detener, la escena queda igual que antes de grabar. |
| S6 | Grabar 1 minuto y **Cancelar** (no detener). | La app no se cierra ni se congela. En OBS no queda la fuente "Pleiada Sync Marker". Si quedó carpeta de sesión, `sync_markers.csv` tiene solo las filas de `start` y `TIMECODE`, sin `end`. |
| S7 | Grabar 2 minutos y cerrar OBS por la fuerza (Administrador de tareas) sin detener la grabación en el Recorder. Después detener desde el Recorder. | El Recorder termina la sesión como en versiones anteriores (mensaje de video faltante o sesión incompleta) y no tarda más de unos segundos en responder al detener. Sin crash. |
| S8 | Subir la sesión de S1 desde "Sesión lista para enviar" y otra desde **Mis grabaciones**. | Las dos suben completas. La carpeta de la sesión tiene **1 video + 5 CSV + `session_metadata.json`**. El panel de verificación sigue mostrando los cuatro CSV de siempre, el video y el metadata; `sync_markers.csv` no se lista ahí y es esperado. |

---

## D · DPI del mouse y dispositivos

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| D1 | Abrir **Ajustes** (engranaje) y bajar hasta el final. | Debajo de "Reiniciar grabación automáticamente" hay un campo **"DPI de tu mouse (opcional)"**, vacío, con un texto de ayuda debajo. Todo el bloque entra en la ventana sin cortarse, también con la pantalla al 125 % o 150 %. |
| D2 | Escribir `1600` y apretar Enter (o hacer clic afuera). Cerrar la app y volver a abrirla. | El valor queda guardado: al volver a Ajustes sigue diciendo `1600`. |
| D3 | Escribir `50`, después `abc`, después `99999`, apretando Enter cada vez. | Los tres se borran solos: el campo queda vacío. Solo se aceptan números entre 100 y 50000. |
| D4 | Con `1600` cargado, grabar 1 minuto y abrir `session_metadata.json`. | En `input → device_metadata → mouse`: `"counts_per_inch": 1600` y `"counts_per_inch_source": "user_declared"`. |
| D5 | Vaciar el campo, grabar 1 minuto y abrir `session_metadata.json`. | `"counts_per_inch": null` y `"counts_per_inch_source": "unknown"`. |
| D6 | En el mismo bloque `device_metadata`, revisar el resto. | `mouse → devices` lista al menos un dispositivo con `vid`, `pid` y, para marcas conocidas, `vendor` (Logitech, Razer, etc.). `mouse → polling → estimated_hz` es un número plausible (típico 125, 500 o 1000). `keyboard → layout` trae el idioma del teclado. Ningún campo trae la ruta del dispositivo ni una dirección Bluetooth. |
| D7 | Probar D6 con un mouse Bluetooth, si hay uno disponible. | El dispositivo aparece igual, con `"bus": "bluetooth"` (o similar) y sin dirección del aparato. |

---

## M · Metadata en inglés

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| M1 | Abrir `session_metadata.json` de cualquier sesión grabada con esta versión. | `"schema_version": "1.3"` y `"recorder_version": "v0.9.20"`. |
| M2 | Buscar en el archivo (Ctrl+F) estas palabras: `encuadre`, `fraccion`, `teclado`, `motivo`, `verificable`, `libre`, `ninguna`. | **Ninguna** aparece. Todas las claves y los valores de texto están en inglés. |
| M3 | Revisar que existan estas claves nuevas. | `video → framing` (con `bars_side`, `fills_full_frame`, `source_width`…), `sync → idle_fraction`, `sync → input_events` (con `keyboard`, `mouse_raw`, `buttons`, `mouse_position`), `sync → no_input_rejected`, `sync → bitrate_low`, `input → rebind_evidence → verifiable`. |
| M4 | Grabar un título de Unity o de un motor sin archivo de configuración legible. | `input → rebind_evidence` dice `"verifiable": false` y `"reason": "no configuration file was read"`. |
| M5 | Grabar un título en pantalla completa 16:9 que ocupe toda la imagen. | `video → framing → bars_side` es `"none"` y `fills_full_frame` es `true`. |
| M6 | Grabar el mismo título en modo ventana, con la ventana más chica que el monitor. | `bars_side` es `"sides"`, `"top_bottom"` o `"sides_and_top_bottom"` según dónde queden las franjas, y `fills_full_frame` es `false`. |
| M7 | Grabar con una orden elegida. | `"recording_mode": "manual"`. (Si se graba un título que ninguna orden abierta acepta, dice `"free"`.) |

---

## Smoke test — que no se haya roto nada

1. Instalar sobre la versión anterior; la app abre; el título dice **v0.9.20**.
2. Login; la lista de títulos carga; se puede elegir orden.
3. Grabar 3 minutos con `GA-2026-019`, cortar, sesión completa: **1 video + 5 CSV + `session_metadata.json`**.
4. Subir una sesión desde la pantalla de resultado y otra desde Mis grabaciones.
5. Un aporte de controles completo con `GA-2026-021` (caso D1 de la guía v0.9.17) termina en "Controles recibidos".
6. Los atajos de teclado, la duración máxima y el reinicio automático de Ajustes siguen funcionando.

---

## Qué reportar

Para cada caso: qué probaste, qué esperabas, qué pasó. Para los casos S y M, adjuntar el `session_metadata.json` y el `sync_markers.csv` de la sesión; para S1 y S2, una captura del cuadro donde se ve (o no se ve) el cuadrado blanco.

Si la app se cierra sola o se congela, mandá también los archivos de:

```
C:\Users\<tu usuario>\Documents\Pleiada Logs\
```

(`crash.log` y `faulthandler.log`)

## Datos del build

| | |
|---|---|
| Versión | **v0.9.20** |
| Reemplaza a | v0.9.19 |
| Firma | Sin firmar (build de prueba) |
| Orden de prueba sin bono | `GA-2026-019` |
| Orden de prueba con bono (solo smoke) | `GA-2026-021` |
