# Backlog — Gameplay Recorder

Cosas decididas que todavía **no** están implementadas, y que no entran en la versión en
curso. Lo más urgente arriba. Cuando algo se implementa, se borra de acá.

---

## 1. Remuxear a progressive + faststart al cerrar la sesión

**Estado: comprometido por escrito a Troveo (17/08/2026), NO implementado.**

Oleg pidió MP4 progressive con el `moov` al principio. Hoy el Recorder entrega
fragmentado, y el remux lo estamos haciendo nosotros después, en una EC2. Medido el
19/08/2026 sobre 130 GB: **1,55 GB/min**, o sea que el corpus entero (10,5 TB) son 116
horas de proceso. Hacerlo en la PC del miembro al cerrar la sesión reparte ese trabajo
entre miles de máquinas que no pagamos, y el archivo llega ya correcto.

**La captura tiene que seguir siendo fragmentada**: el anchor de sincronía se calcula
leyendo los `moof` en vivo (espera el 2º moof, resta la duración del 1º). El remux va
*después* de cerrar el archivo, nunca cambiando el formato de captura.

El comando exacto, ya validado contra un archivo real de 8 GB:

```
ffmpeg -i <sesion>.mp4 -map 0 -c copy -movflags +faststart+negative_cts_offsets <salida>.mp4
```

**`+negative_cts_offsets` no es opcional y no se puede simplificar a `+faststart` solo.**
Medido sobre A Plague Tale (hevc, 60 min): el original arranca en 0 ms si el
decodificador respeta la edit list y en **33,3 ms si la ignora**. Con `+faststart` a
secas esa asimetría sobrevive al remux, y el presupuesto de sincronía del dataset es
±50 ms. Con `+negative_cts_offsets` da 0 ms en los dos casos.
**NO agregar `-avoid_negative_ts make_zero` ni `-fflags +genpts`**: metían un corrimiento
real de 33 ms.

**Beneficio que no es obvio:** si el remux ocurre ANTES de calcular el bloque `integrity`
del metadata, el SHA-256 declarado corresponde al archivo que efectivamente recibe el
cliente. Hoy, remuxeando después, el hash del metadata no coincide con el MP4 entregado y
hay que explicarlo en el README de cada entrega.

Orden obligatorio: **cerrar el MP4 → sync check → remux → hash → upload**. El sync check
mide la duración leyendo los fragmentos; si se remuxea antes, se rompe.

A verificar antes de implementar: **si hay un ffmpeg utilizable del lado del usuario**.
OBS trae las librerías, pero no necesariamente el ejecutable. Y el remux agrega una espera
al final de la sesión (una pasada de I/O sobre el archivo), así que hay que mostrarlo en
pantalla y no dejar al usuario mirando una ventana quieta.

## 2. Test intermitente en el uploader paralelo

**Estado: detectado el 19/08/2026, sin diagnosticar. Preexistente — no lo introdujo la
v0.9.**

`test_los_bytes_llegan_completos_y_en_orden` falla ~2 de cada 8 corridas, y no falla por
poco: reporta 6,5 MB o 11,8 MB recibidos contra 12,6 MB esperados. Siempre de menos.

Las dos lecturas posibles son muy distintas y hay que decidir cuál es antes de confiar en
el resultado del test:

- **Es del test.** El assert lee el diccionario de partes recibidas apenas vuelve
  `_upload_multipart_file`, y algún hilo todavía está escribiendo. Molesto, inofensivo.
- **Es del uploader.** La función vuelve antes de que todas las partes hayan terminado.
  Eso sí importa: significa que damos por subido algo incompleto.

Se hizo visible con la máquina cargada (builds corriendo en paralelo), que es
exactamente cuándo aparecen las carreras. No apareció antes porque el test corría solo.

## 3. El gate de pantalla muerta asume CRF, y la flota graba CBR

**Estado: detectado el 18/08/2026, sin medir el impacto.**

`pleiada_sync_limits.py` documenta que el gate de imagen quieta depende de que OBS grabe
por calidad (CRF/CQP): *"Si un usuario forzara CBR, el negro se rellenaría hasta el bitrate
objetivo y este gate quedaría ciego para esa sesión"*.

Pero `pleiada_app.pyw` fuerza `RecQuality=Stream` + `VBitrate=2500` en todo el parque, que
es CBR. O sea que la condición que el gate declara necesitar **no se cumple para ninguna
sesión**, no para un usuario suelto. Es el mismo patrón del gate de AFK que falló abierto:
una precondición documentada que nadie volvió a chequear.

Hay que medir cuántas capturas en negro pasó el gate automático — las 22 de la entrega
troveo-001 las encontró la revisión humana, no el gate.

## 4. Detectar y registrar joystick

**Estado: sin implementar. `gamepad_connected` está hardcodeado en `false`.**

Medido sobre el bucket: ~85 sesiones / 46 h probablemente jugadas con joystick. Hoy salen
con los CSV de input vacíos y son indistinguibles de una falla de captura hasta que se mira
el `mouse_log`. Desde v0.9.0 el gate las rechaza, así que el usuario al menos se entera —
pero grabó una hora al pedo.

## 5. Elegir dónde se guardan las grabaciones

**Estado: aprobado para una versión futura (16/08/2026). No entra en la actual.**

Hoy la carpeta es fija: `Documentos\Pleiada Recordings`. El usuario tendría que poder
cambiarla desde Ajustes — típicamente para grabar en un disco secundario con más espacio.

La constante se usa en cuatro lugares del código, así que el cambio en sí es chico. Lo que
hace que no sea trivial:

- **Las grabaciones viejas quedan en la ruta anterior.** La lista de grabaciones tiene que
  seguir encontrándolas, o hay que ofrecer moverlas. Si no, el usuario cambia la carpeta y
  cree que perdió las sesiones que tenía.
- **El movimiento del MP4 es el riesgo real.** OBS graba en su propia carpeta y el Recorder
  mueve el archivo a la carpeta de sesión al cerrar. Dentro del mismo disco es instantáneo;
  a otro disco pasa a ser una copia de varios GB, y eso cae en el camino crítico del cierre
  de sesión. Hay que probarlo con un archivo grande entre discos distintos antes de darlo
  por hecho.
- Validar que la carpeta exista, sea escribible y tenga espacio; no permitir el cambio
  mientras hay una grabación en curso.

## 6. Subir el bitrate de grabación

**Estado: en hold desde el 28/07/2026.** Parche en
`_programa\bitrate_fix_configure_obs.patch`.

Hoy se graba a 2500 kbps. Subir la calidad lleva el dataset de ~1,1 GB/h a 11–20 GB/h, o
sea que multiplica por diez la subida y el costo de S3. Retomar solo si un cliente lo pide
explícitamente y el número cierra.

---

## Decisiones tomadas de NO hacer

- **Borrar carpetas de grabaciones desde la app** (16/08/2026). Los archivos de una sesión
  quedan en solo lectura a propósito y así se mantienen; no se agrega una acción de borrado.
