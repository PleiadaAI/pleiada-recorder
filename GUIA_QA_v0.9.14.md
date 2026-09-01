# Guía de QA — Gameplay Recorder v0.9.14

## Qué hay de nuevo

Cuatro cambios, todos relacionados con lo que declaramos sobre cada grabación. **Ninguno
cambia cómo se graba ni la calidad del video**: el peso y la imagen tienen que salir
iguales que en la v0.9.13.

| # | Cambio | Se ve en |
|---|---|---|
| A | El audio de escritorio ahora se graba **muteado** | el MP4 |
| B | El archivo de datos de la sesión deja de declarar una precisión de sincronía que no medíamos | `session_metadata.json` |
| C | Se detecta si el juego **no ocupa todo el cuadro** (franjas negras) | `session_metadata.json` |
| D | Se registra si el archivo de controles del juego **cambió durante la grabación** | `session_metadata.json` |

---

## A · El audio se graba muteado

**Qué esperamos:** el MP4 de la sesión **no tiene sonido**. Ni el del juego, ni el
micrófono, ni nada.

Es a propósito: por el audio del escritorio se podía colar chat de voz de otras personas
que nunca dieron permiso para aparecer en un dataset.

**Cómo probarlo**

1. Grabá una sesión normal de 2-3 minutos con el juego haciendo ruido.
2. Abrí el MP4 resultante en cualquier reproductor.
3. **Tiene que estar mudo.**
4. Abrí OBS y mirá el mezclador de audio: las dos fuentes (escritorio y micrófono) tienen
   que aparecer **silenciadas**.

⚠️ **Caso importante:** si antes de grabar entrás a OBS y desmuteás el audio de escritorio
a mano, al arrancar la grabación **el Recorder lo tiene que volver a mutear**. Probalo:
es el caso que más nos interesa.

---

## B · El archivo de datos ya no declara precisión de sincronía

**Qué esperamos:** abrir `session_metadata.json` de una sesión nueva y, dentro del bloque
`timing`, **no encontrar** los campos `anchor_method` ni `anchor_precision_ms`. En su
lugar hay un campo `anchor_notes` con un texto en inglés que explica el tema.

**Por qué:** esos dos campos decían un método y un número que no correspondían con lo que
el programa hace realmente. Un cliente los estaba auditando. Se sacan en vez de
reemplazarlos por otro número, porque esa precisión no la medimos por sesión.

**Cómo probarlo**

1. Grabá cualquier sesión.
2. Abrí `session_metadata.json` con el Bloc de notas.
3. Buscá `"timing"`. Tiene que tener `start_unix_ms`, `end_unix_ms`, `duration_ms`,
   `anchor_ts` y `anchor_notes`.
4. **No tiene que aparecer** `anchor_method` ni `anchor_precision_ms` por ningún lado.

---

## C · Detección de franjas negras

**Qué esperamos:** que el archivo de datos diga si el juego ocupó todo el cuadro o si
quedaron barras negras.

En `session_metadata.json`, dentro de `"video"`, hay un bloque `"encuadre"`.

**Cómo probarlo — caso normal**

1. Grabá un juego que corra en pantalla completa 16:9 (lo habitual).
2. En `encuadre` tiene que decir `"ocupa_cuadro_completo": true` y `"barras_lado": "ninguna"`.

**Cómo probarlo — caso con barras (el que importa)**

1. Buscá un juego que corra en otra proporción: uno viejo en 4:3, o poné el juego en modo
   ventana con una ventana no-16:9, o una pantalla 16:10.
2. Grabá 1-2 minutos.
3. Ahora `"ocupa_cuadro_completo"` tiene que ser `false`, `"barras_fraccion"` un número
   mayor a 0, y `"barras_lado"` tiene que decir `"costados"` o `"arriba_abajo"` según
   corresponda.
4. Mirá el video: **las barras negras tienen que estar donde el archivo dice.**

⚠️ Si al cerrar la sesión OBS ya no está corriendo, `encuadre` sale en `null`. Eso es
esperado, no es un error.

---

## D · Cambios en los controles durante la grabación

**Qué esperamos:** si el jugador entra al menú de opciones y cambia una tecla **mientras
está grabando**, queda registrado.

En `session_metadata.json`, dentro de `"input"`, hay un bloque `"rebind_evidence"`.

**Cómo probarlo**

1. Elegí un juego de los que sí podemos leer: **Counter-Strike 2, Left 4 Dead 2, Portal 2**
   (motor Source) o un juego hecho en **Unreal**.
2. Empezá a grabar.
3. A mitad de la sesión, entrá a las opciones del juego y **cambiá una tecla**. Guardá.
4. Volvé al juego, jugá un poco más y cortá la grabación.
5. En `rebind_evidence` tiene que decir `"config_modificada_durante_sesion": true`.

**Y el caso contrario, igual de importante:** grabá otra sesión **sin tocar los controles**.
Tiene que decir `false`.

⚠️ En juegos hechos en Unity y otros motores no tenemos forma de leer el archivo de
controles. Ahí el bloque va a decir `"verificable": false` con un motivo. **Eso es lo
esperado, no es un error.**

⚠️ Puede dar `true` sin que hayas cambiado una tecla, si el juego reescribe su archivo de
configuración por otro motivo (cambiar resolución, volumen, brillo). Si te pasa, anotalo
con el detalle de qué tocaste: nos sirve para saber cuánto ruido tiene la señal.

---

## Smoke test — que no se haya roto nada

Además de lo nuevo, confirmar que sigue funcionando lo de siempre:

1. Instalar sobre una versión anterior y que la app abra sin errores.
2. Login.
3. Que la lista de títulos cargue y se pueda elegir una orden.
4. Identificación del título: que reconozca el juego que está corriendo.
5. Grabar 3 minutos, cortar, y que la sesión quede completa: **1 video + 4 archivos CSV +
   `session_metadata.json`**.
6. Que el peso del video sea parecido al de la v0.9.13 para el mismo juego (no tiene que
   haber cambiado la calidad).
7. Subir la sesión y que llegue sin errores.
8. Abrir el Synch Checker sobre la sesión y que dé el mismo veredicto de siempre.

---

## Qué reportar

Para cada caso: qué probaste, qué esperabas, qué pasó, y **adjuntá el
`session_metadata.json`** de la sesión — ahí está casi todo lo que necesitamos ver.

Si la app se cierra sola o se congela, mandá también los archivos de:

```
C:\Users\<tu usuario>\Documents\Pleiada Logs\
```

(`crash.log` y `faulthandler.log`)

## Datos del build

| | |
|---|---|
| Versión | **v0.9.14** |
| Instalador completo | `PleiadaRecorder_Setup.exe` — 181 MB |
| Actualizador | `PleiadaRecorder_Update.exe` — 2,2 MB |
| Lista de títulos incluida | 583 publicados |
