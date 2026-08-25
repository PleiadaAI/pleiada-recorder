# Backlog — Gameplay Recorder

Cosas decididas que todavía **no** están implementadas, y que no entran en la versión en
curso. Lo más urgente arriba. Cuando algo se implementa, se borra de acá.

---

## 0-. Calidad de grabación: lo que quedó pendiente de la v0.9.12

**La v0.9.12 ya implementó el grueso** (calidad constante con techo, en modo Avanzado, con
la config escrita en disco y OBS reiniciado cuando hace falta — todo en `obs_encoding.py`).
Queda esto:

### 0-.a · Calibrar AMD (AMF) e Intel (QSV) 🔴

**Los valores que van hoy para esas dos familias son una EXTRAPOLACIÓN, no una medición.**
No había hardware para probarlos. Las claves siguen la forma documentada por OBS y la misma
estructura que las de NVENC, pero nadie verificó ni que OBS las acepte ni a qué peso y
calidad aterrizan.

Medido y verificado contra OBS real (VMAF medio / peor frame del clip):

| encoder | config | GB/h | VMAF | peor |
|---|---|---:|---:|---:|
| NVENC | VBR 8000 / máx 12000, p5 | 3,45 | 83,4 | 56,5 |
| x264 | CRF 23 + `vbv-maxrate=8000`, preset `fast` | 3,48 | 83,8 | 59,2 |
| — | *(CBR 8000, lo que hacía la v0.9.12)* | 3,33 | 75,0 | 22,6 |

La parte C de `GUIA_QA_v0.9.12.md` está escrita para traer justamente ese dato: tamaño real
del MP4 y `bitrate_kbps` sobre un título con movimiento y otro quieto, por placa. **Con eso
se ajustan los números de `record_encoder_settings()` para esas dos familias.**

Ojo con dos cosas al calibrar:

- **No existe un valor único parejo entre familias.** El mismo "CQP/CRF 23" da VMAF 86 a
  5,2 GB/h en x264 y VMAF 98 a 9,9 GB/h en NVENC. Es la razón de que la config sea por
  familia y no un número global.
- **En NVENC, `cqlevel` se descarta en silencio.** OBS no sabe hacer calidad constante con
  techo en NVENC (lo que en ffmpeg sería `-rc vbr -cq N -b:v 0 -maxrate X`); lo más cerca es
  VBR con objetivo y techo, que es lo que quedó. Si OBS algún día lo soporta, vale revisarlo:
  con capped-CQ real la misma calidad salía a 3,80 GB/h con el peor frame en 58,3.

### 0-.b · `is_bitrate_bajo` va a empezar a dar falsos positivos

`BITRATE_PISO_KBPS = 4_000` servía para partir aguas entre la config vieja (~2.670 kbps) y la
nueva. Con calidad constante, **un título visualmente simple puede pesar 2.000 kbps y estar
perfecto**. Hoy sigue siendo útil como señal de "en esta máquina el fix no aplicó" durante el
rollout, pero cuando la flota esté toda en v0.9.12 el booleano sobra y conviene dejar solo el
número. **Si aparecen falsos positivos, lo que sobra es el flag — no hay que subir la calidad
para acallarlo.**

### 0-.c · `_meta_hardware()` todavía detecta GPUs por `wmic`

`pleiada_app.pyw` usa `wmic` para la telemetría de hardware, y `wmic` está deprecado y ya no
viene en algunas builds de Win11 24H2+ (26100+), donde falla en silencio y `gpus` queda en
`None`. `obs_encoding.familia_gpu()` ya usa CIM con `wmic` de fallback: conviene que
`_meta_hardware` haga lo mismo. No es crítico —es telemetría, no gatea nada— pero explica
huecos en el metadata de las máquinas nuevas.

### 0-.d · Recalibrar `VIDEO_PISO_BYTES` cuando haya corpus nuevo

El gate de imagen quieta volvió a funcionar (estuvo inerte entre la v0.8.12 y la v0.9.12
porque el CBR rellenaba la pantalla negra hasta el bitrate objetivo). Los umbrales actuales
separan con margen —~26 KB por ventana en negro contra ~5.000 KB de gameplay— así que **no
hace falta tocarlos ahora**. Vale revisarlos cuando haya un corpus grabado con la config
nueva, sobre todo el piso de 200 KB contra títulos visualmente simples.

---

## 0. Alinear el gate AFK con el servidor: 10 min → 5 min

**Estado: decidido por Martín el 24/08/2026. El servidor YA está en 5 min; el cliente
sigue en 10.** Va en el próximo build, junto con el gate de input recalibrado
(20 ev/min) — ver el punto 0b, que **no** está en la misma situación: ahí el código del
cliente ya se cambió y lo único que falta es compilar, mientras que acá todavía hay que
editar `pleiada_sync_limits.py`.

En `pleiada_sync_limits.py`:

```
MAX_CONT_IDLE_MS = 300_000   # hoy 600_000
```

`sync_verify.py` (Pleiada Tools/qa_muestreo) ya quedó en 300_000 el 24/08/2026. Los dos
archivos son copias deliberadas, sin import entre repos: **si uno se toca, el otro
también**, y el encabezado de los dos lo dice.

**Por qué se pudo bajar solo de un lado sin romper nada:** el umbral exacto nunca se le
comunicó al uploader. El copy al usuario es genérico por regla —sin números ni
umbrales—, así que no hay promesa que romper. Lo que sí pasa mientras dure la
divergencia: una sesión con un hueco de entre 5 y 10 minutos **sube sin aviso y se
rechaza después**, en vez de avisarle al uploader en el momento, que es peor experiencia
y gasta ancho de banda de los dos lados. Es el precio de no esperar un release.

**Ojo con el Synch Checker.** `pleiada_check.pyw` comparte estos umbrales: si se cambia
`MAX_CONT_IDLE_MS` y no se rebuildea también el checker, vuelve exactamente el problema
que se arregló en v0.8.8 — el verificador diciendo "SESIÓN LISTA PARA ENVIAR" sobre algo
que el uploader rechaza.

**No hay que tocar `MAX_IDLE_FRACCION` (0,50)**: el brazo relativo no se discutió y
bajarlo es una decisión aparte, con su propia medición.

---

## 0b. El gate de input recalibrado ya está en el código y necesita un build

**Estado: decidido y aplicado por Martín el 24/08/2026. Las dos copias del código YA
están en 20 ev/min; lo que falta es el build.** No confundir con el punto 0: ahí falta
cambiar el cliente, acá el cliente ya está cambiado y falta compilarlo.

El gate viejo (piso 2 eventos + 1 evento/min) fallaba **abierto en sesiones cortas**:
`Hollow_Knight_30_07_26__20_17_15` (65,4 s, 2 eventos accionables) daba `sin_input=False`
y salía `aprobado`. Con n=2 el piso no dispara (`2 < 2` es False) y el brazo relativo
pedía 1,09 eventos. Criterio nuevo, un solo brazo:

```
umbral = MIN_EVENTOS_POR_MIN * max(dur_min, MIN_MINUTOS_GATE)    # 20 ev/min, mínimo 2 min
```

`MIN_EVENTOS_INPUT` pasó a ser **derivado** (`int(20 * 2) = 40`). No volver a ponerlo como
constante suelta: que los dos brazos pudieran descalibrarse entre sí es exactamente lo que
causó el bug.

**Qué falta, concretamente:**

1. **Bump de versión: v0.9.9 → v0.9.10** (`VERSION` + `/DAppVersion`). La copia instalada
   en `C:\Program Files\Pleiada Recorder` se dejó a propósito con el código viejo —
   parchearla a mano dejaría el build corriendo con un comportamiento distinto del que
   declara su propio `VERSION`, que es justo lo que la regla de versionado evita.
2. **Rebuildear también el Synch Checker.** `pleiada_check.pyw` importa
   `pleiada_sync_limits`, así que hereda el gate nuevo solo; pero si sale un installer con
   el uploader nuevo y el checker viejo, vuelve el problema de v0.8.8 — el verificador
   diciendo "SESIÓN LISTA PARA ENVIAR" sobre algo que el uploader rechaza. Mismo aviso que
   el punto 0.
3. **Guía de QA de la versión**, con el caso de la sesión corta: grabar <2 min haciendo
   casi nada tiene que dar rechazo *antes* de subir.

**El precio de que el build no salga**, igual que en el punto 0: el servidor ya rechaza a
20 ev/min y el cliente instalado sigue dejando subir a 1 ev/min, así que una sesión con
goteo de input **sube sin aviso y se rechaza después**, en vez de avisarle al uploader en
el momento. Gasta ancho de banda de los dos lados y es peor experiencia.

**No volver a intentar el arreglo intuitivo.** Evaluar el brazo relativo con
`max(dur_min, 2)` **manteniendo la tasa en 1,0** no arregla nada: da umbral = 2 eventos y
la sesión de 65 s sigue pasando. Medido sobre las 264 sesiones que pasaban el gate, esa
variante hace caer cero. Lo que estaba mal era la escala de la tasa, no el brazo de
duración: la mediana del gameplay real es 2.979 ev/min y el percentil 2 es 84,9, o sea que
el corte de 1/min estaba 85x por debajo de lo sano. Con 20 queda 4x de margen contra la
sesión sana más quieta de producción y 8x contra el corpus local.

Tests: `tests/test_input_vacio.py`, 21 casos (eran 15). El de margen bajó de exigir 10x a
4x, que es el margen real medido.

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

## 3. Medir cuántas capturas en negro dejó pasar el gate mientras estuvo ciego

**Estado: la CAUSA quedó arreglada en la v0.9.12; falta medir el daño ya hecho.**

El gate de imagen quieta declaraba necesitar que OBS grabara por calidad (CRF/CQP), pero
desde la v0.8.12 la app forzaba `RecQuality=Stream` + `VBitrate`, que es CBR. En CBR el
encoder rellena la pantalla negra hasta el bitrate objetivo, así que **la precondición que
el gate declaraba no se cumplía para NINGUNA sesión** — no para un usuario suelto. Mismo
patrón que el gate de AFK que falló abierto: una precondición documentada que nadie volvió
a chequear.

La v0.9.12 pasó a calidad constante y el gate volvió a discriminar (verificado: la pantalla
sin nada que capturar grabó a 42 kbps en vez de rellenar hasta los 8.000 del objetivo).

**Lo que falta es retroactivo:** medir cuántas capturas en negro pasó el gate automático
entre la v0.8.12 y la v0.9.12. Las 22 de la entrega troveo-001 las encontró la revisión
humana, no el gate. Se puede correr `video_stillness` server-side sobre el backlog, pero
**ojo: sobre las sesiones grabadas en CBR va a devolver limpio siempre**, porque el gate era
ciego justamente para ellas. Para ese material el único camino es muestreo humano.

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
