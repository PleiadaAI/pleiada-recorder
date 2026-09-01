# Guía de QA — Gameplay Recorder v0.9.15

## Qué hay de nuevo

Esta versión **corrige dos de los cuatro puntos de la v0.9.14**. Los otros dos ya
pasaron y no se tocaron.

Gracias por el reporte anterior: los cuatro casos de franjas negras que probaron
eran cuatro fallas reales, y el detalle de cada uno fue lo que permitió encontrar
la causa.

| # | Estado | Qué cambió |
|---|---|---|
| A | Sin cambios | El audio se sigue grabando muteado |
| B | Sin cambios | Sigue sin declararse la precisión de sincronía |
| C | **Corregido** | La detección de franjas negras estaba mal planteada |
| D | **Corregido** | Ya no se enciende al cambiar opciones que no son controles |

**A y B no hace falta volver a probarlos a fondo**, alcanza con el smoke test del
final. C y D sí, completos.

---

## C · Detección de franjas negras — corregido

**Qué estaba mal.** La versión anterior comparaba la *proporción* de la imagen del
juego contra la del video (16:9, 4:3, etc.) y de ahí deducía si sobraba negro.
Ese razonamiento asume que OBS agranda la imagen del juego hasta llenar el cuadro,
centrándola. **OBS no hace eso**: la deja en su tamaño original, apoyada contra el
borde de arriba a la izquierda. Por eso el negro les quedaba a la derecha y abajo,
y por eso el caso 16:9 en ventana decía "sin franjas" aunque medio cuadro estuviera
negro: la proporción coincidía.

**Qué cambió.** Ahora se mide la geometría real: dónde quedó dibujada la imagen del
juego y de qué tamaño, y cuánto del cuadro quedó sin cubrir.

**Campos nuevos en `session_metadata.json`**, dentro de `"video"` → `"encuadre"`:

| Campo | Qué dice |
|---|---|
| `barras_lado` | Ahora puede decir también `"costados_y_arriba_abajo"` |
| `barras_por_borde` | Cuánto negro hay en cada borde por separado |
| `dibujado_x`, `dibujado_y` | En qué punto del cuadro arranca la imagen del juego |
| `dibujado_ancho`, `dibujado_alto` | Qué tamaño ocupa |
| `fuente_excede_lienzo` | `true` si el juego es más grande que el cuadro y se recorta |

### Cómo probarlo

Repetir **las mismas cinco configuraciones de la vuelta pasada**. Para cada una,
mirar el video y comparar contra lo que dice el archivo.

| Configuración | Qué tiene que decir |
|---|---|
| 16:9 pantalla completa | `ocupa_cuadro_completo: true`, `barras_lado: "ninguna"` |
| 16:9 en ventana | `false`, y los bordes donde de verdad esté el negro |
| 4:3 en ventana | `false`, idem |
| 4:3 pantalla completa | `false`, idem |
| 16:10 pantalla completa | `false`, idem |
| 16:10 en ventana | `false`, idem |

**La prueba de fuego es `barras_por_borde`:** los cuatro números tienen que
coincidir con lo que se ve. Si el negro está a la derecha y abajo, `derecha` y
`abajo` tienen que ser mayores a 0 y los otros dos 0.

⚠️ **Esto es lo más importante que pueden mandar:** para cada caso, **el
`session_metadata.json` + una captura del video**. Con el bloque `encuadre` completo
—que ahora dice posición y tamaño— se puede verificar la cuenta sin tener la máquina
delante. La vuelta pasada faltaban justamente esos números y hubo un caso (4:3 con
negro abajo) que no se pudo reconstruir.

⚠️ Si al cerrar la sesión OBS ya no está corriendo, `encuadre` sale en `null`. Eso
es esperado, no es un error.

---

## D · Cambios en los controles durante la grabación — corregido

**Qué estaba mal.** La única señal era la fecha de modificación del archivo de
configuración del juego. En los juegos con motor Source ese archivo guarda los
controles **junto con** video, audio y sensibilidad del mouse, así que subir el
volumen lo reescribe entero y encendía la alerta. Es exactamente lo que reportaron.

**Qué cambió.** Ahora se lee el mapa de teclas **al empezar** a grabar y **al
terminar**, y se comparan. Si cambió una tecla, cambió de verdad.

**El campo viejo se queda** (`config_modificada_durante_sesion`) y va a seguir
encendiéndose al cambiar el volumen: es a propósito, sirve para los casos donde no
se pudo leer el mapa. **El campo nuevo es el que vale.**

En `session_metadata.json`, dentro de `"input"` → `"rebind_evidence"`:

| Campo | Qué dice |
|---|---|
| `binds_modificados_durante_sesion` | **El que importa.** `true` solo si cambió una tecla |
| `binds_cambiados` | Qué teclas cambiaron |
| `binds_cambiados_total` | Cuántas |
| `motivo_sin_comparacion` | Aparece cuando la comparación no se pudo hacer |

### Cómo probarlo

Con un juego de los que sí podemos leer: **Counter-Strike 2, Left 4 Dead 2,
Portal 2** (motor Source) o un juego hecho en **Unreal**.

| Prueba | `config_modificada...` | `binds_modificados...` |
|---|---|---|
| 1. Cambiar una **tecla** a mitad de sesión | `true` | **`true`** |
| 2. Cambiar **volumen o resolución**, sin tocar teclas | `true` | **`false`** ← el arreglo |
| 3. No tocar nada | `false` | `false` |

**La prueba 2 es la que fallaba.** Si ahí `binds_modificados_durante_sesion` sale
`true`, el arreglo no funcionó: anotá exactamente qué opción tocaste.

En la prueba 1, `binds_cambiados` tiene que listar la tecla que cambiaste (y puede
listar también la que quedó libre; eso es correcto).

⚠️ Si aparece `motivo_sin_comparacion`, anotalo tal cual y decinos cuánto tardaste
en empezar a jugar desde que arrancó la grabación. El mapa se lee en segundo plano
al arrancar, y necesitamos saber si en alguna máquina no llega a tiempo.

⚠️ En Unity y otros motores sigue sin poder leerse: ahí va `verificable: false` con
un motivo. Es lo esperado.

---

## Smoke test — que no se haya roto nada

1. Instalar sobre una versión anterior y que la app abra sin errores.
2. Que en el título de la ventana diga **v0.9.15**.
3. Login.
4. Que la lista de títulos cargue y se pueda elegir una orden.
5. Identificación del título: que reconozca el juego que está corriendo.
6. Grabar 3 minutos, cortar, y que la sesión quede completa: **1 video + 4 archivos
   CSV + `session_metadata.json`**.
7. Que el peso del video sea parecido al de la v0.9.13 para el mismo juego.
8. Que el MP4 siga saliendo **mudo** (punto A).
9. Que en `timing` sigan **sin** aparecer `anchor_method` ni `anchor_precision_ms`
   (punto B).
10. Subir la sesión y que llegue sin errores.
11. Abrir el Synch Checker sobre la sesión y que dé el mismo veredicto de siempre.

⚠️ **Arrancar a grabar tiene que sentirse igual de rápido que antes.** Esta versión
hace una lectura extra al arrancar; está puesta en segundo plano justamente para que
no se note. Si notás una demora entre apretar F9 y que empiece a grabar, es un
hallazgo importante: anotalo.

---

## Qué reportar

Para cada caso: qué probaste, qué esperabas, qué pasó, y **adjuntá el
`session_metadata.json`**. Para el punto C, sumá **una captura del video**.

Si la app se cierra sola o se congela, mandá también los archivos de:

```
C:\Users\<tu usuario>\Documents\Pleiada Logs\
```

(`crash.log` y `faulthandler.log`)

## Datos del build

| | |
|---|---|
| Versión | **v0.9.15** |
| Reemplaza a | v0.9.14 (no se publica) |
