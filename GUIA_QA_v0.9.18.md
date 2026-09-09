# Guía de QA — Gameplay Recorder v0.9.18

## Qué hay de nuevo

Esta versión responde a los hallazgos de la ronda anterior sobre el bono por metadata de controles. No hay funciones nuevas fuera de ese flujo.

**En la app (necesita esta versión):**

1. **La oferta del bono también aparece al subir una sesión guardada** desde **Mis grabaciones**. Antes solo aparecía al terminar de grabar.
2. **"Controles recibidos" muestra el total leído y cuántos son de juego**: "Leímos 40 controles de <título>, 18 de juego". Los controles de menú se guardan pero no cuentan para el mínimo.
3. **Cuando falta lo mínimo, dice qué faltó**: las teclas de movimiento que no encontró, el botón principal del mouse, o que hay menos controles de los necesarios.
4. **Una captura borrosa se rechaza al cargarla**, antes de enviar nada: "la captura está borrosa y las teclas no se leen".
5. En el paso 1, las filas Recargar, Interactuar y Saltar dicen **(ejemplo)**: no son requisito.

**En el servidor (ya activo, también con la v0.9.17):**

6. **Capturas donde los botones del mouse se muestran como íconos** (un dibujito del mouse con una mitad pintada, como en Silent Hill 2, Resident Evil 3 o Cult of the Lamb) **se rechazan** con el mensaje "Solo leemos controles escritos como texto…". El aporte no se registra.
7. Una captura con teclas poco habituales (Esquivar en Espacio, Atacar en K) **ya no se rechaza como "no por defecto"**. Ese rechazo solo ocurre si la pantalla del título muestra que los controles fueron cambiados.
8. Las capturas borrosas o ilegibles se rechazan aunque el título sea conocido.
9. Dos aportes del mismo título con las mismas pantallas ya coinciden aunque una tecla tenga varias filas (Atacar y Avanzar diálogo en el mismo botón).

---

## Antes de empezar

- Instalar `PleiadaRecorder_Setup.exe` (build v0.9.18) sobre la versión anterior. En el título de la ventana tiene que decir **v0.9.18**.
- Cerrar sesión y volver a entrar en el Recorder.
- La orden de prueba con bono sigue siendo `GA-2026-021`; `GA-2026-019` sigue sin bono.
- Elegir títulos cuya pantalla de controles muestre los botones del mouse **como texto** ("Botón izquierdo del mouse", "Left Mouse Button", "Mouse 1"). Los que los muestran como ícono sirven solo para el caso I.

---

## G · La oferta desde Mis grabaciones

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| G1 | Grabar un título sin mapa de controles con `GA-2026-021`, cortar y en "Sesión lista para enviar" **no** subir (volver al inicio). Después ir a **Mis grabaciones → Subir** en esa sesión, elegir la orden y tocar **Subir**. | Aparece la pantalla **"Antes de subir el dataset"** con la tarjeta del bono y dos salidas: **Compartir controles** y **Subir sin metadata**. |
| G2 | En G1, tocar **Compartir controles**, completar los tres pasos y analizar con una captura buena. | "Controles recibidos" y el botón **Continuar con la subida del dataset** lleva a la subida de esa misma sesión, con la orden fija. |
| G3 | En G1, tocar **Subir sin metadata**. | Sube directo, como siempre. |
| G4 | En G1, desde el paso 1 tocar **Volver**. | Vuelve a "Antes de subir el dataset", no a la pantalla de resultado de la sesión. |
| G5 | Subir desde Mis grabaciones una sesión con `GA-2026-019`, o una sesión de un título que ya tiene mapa. | **No** aparece la pantalla nueva: va derecho a la subida. |
| G6 | Una sesión a la que ya se le compartieron controles al terminar de grabar, subirla después desde Mis grabaciones. | No vuelve a ofrecer. |

---

## H · Mensajes nuevos

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| H1 | Analizar una captura buena de un título con varias pantallas de controles (movimiento, combate, menú). | "Leímos N controles de <título>, M de juego", con N mayor que M. Si el título tiene una sola pantalla sin menús, dice solo "Leímos N controles". |
| H2 | Analizar solo la pantalla de combate, sin la de movimiento. | "No pudimos leer lo mínimo" y, debajo del texto general, **"Faltan las teclas de movimiento: W, A, S, D."** (o las que falten). |
| H3 | Analizar una pantalla de movimiento sin ningún botón de mouse, de un título que sí usa el mouse. | El detalle dice **"Falta el botón principal del mouse."** |
| H4 | Un título con pocos controles (menos de ocho de juego). | El detalle dice **"Leímos N controles de juego, menos de los necesarios."** |
| H5 | En el paso 1, mirar el esquema. | Las filas Recargar, Interactuar y Saltar dicen **(ejemplo)**. Las marcadas con ● siguen siendo las únicas obligatorias. |

---

## I · Íconos de mouse

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| I1 | Analizar la pantalla de controles de **Silent Hill 2**, **Resident Evil 3** o **Cult of the Lamb** (los botones del mouse son un dibujito). | "No pudimos leer lo mínimo" con el motivo **"Solo leemos controles escritos como texto. En estas capturas los botones del mouse aparecen como íconos y no los podemos interpretar."** Cuenta como intento. |
| I2 | El mismo título, cambiando el botón izquierdo por el derecho antes de capturar. | Mismo rechazo que I1. No importa si está invertido: no se lee. |

---

## J · Capturas borrosas

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| J1 | En el paso 2, elegir una captura desenfocada (por ejemplo, aplicar desenfoque en Paint 3D o achicarla mucho y agrandarla). | **No se carga**: mensaje "la captura está borrosa y las teclas no se leen". El contador no cambia. |
| J2 | Una captura nítida pero oscura o de bajo contraste (fondo negro, letras grises). | Se carga normalmente. Anotar título y resolución si alguna nítida es rechazada: es un hallazgo. |
| J3 | Con la **v0.9.17**, mandar la captura borrosa de J1 a analizar. | La rechaza el servidor: "Las capturas no se leen bien…". |

---

## K · Teclas poco habituales no son "no por defecto"

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| K1 | Un título con controles por defecto raros (Esquivar en Espacio, Atacar en una letra) y los botones del mouse como texto. Analizar la pantalla completa, con esa fila visible. | Se acepta. **No** aparece "no parecen ser los por defecto". |
| K2 | Un título que muestre en pantalla un preset **"Personalizado"** o una marca de "modificado" después de cambiar una tecla. | Se rechaza con "no parecen ser los por defecto". Si el título no muestra ninguna marca al cambiar teclas, el aporte se acepta: la validación entre dos usuarios es la que lo detecta. |

---

## L · Validación entre dos testers, de nuevo

Repetir la prueba E de la guía anterior con un título cuyos botones de mouse sean texto:

| Paso | Quién | Qué hacer | Resultado esperado |
|---|---|---|---|
| L1 | Tester 1 | Compartir controles por defecto y subir. | Validación pendiente. |
| L2 | Tester 2 | Compartir los mismos controles por defecto y subir. | Los dos pasan a **Validada · Pago pendiente**. |
| L3 | Tester 3 | Compartir con el botón izquierdo y el derecho invertidos. | Se acepta como Validación pendiente, pero **no cobra** y el título sigue validado con los controles de L1 y L2. |
| L4 | Dos testers | Mismo título, misma pantalla, pero uno saca la captura con la lista scrolleada distinto. | Validan igual mientras las dos capturas incluyan las teclas de movimiento y el mouse. |

---

## Smoke test — que no se haya roto nada

1. Instalar sobre la versión anterior; la app abre; el título dice **v0.9.18**.
2. Login; la lista de títulos carga; se puede elegir orden.
3. Grabar 3 minutos con `GA-2026-019`, cortar, sesión completa: **1 video + 4 CSV + `session_metadata.json`**. Sin tarjeta de bono.
4. Subir esa sesión desde la pantalla de resultado, y otra desde Mis grabaciones, sin pasar por ninguna pantalla nueva.
5. Synch Checker con el mismo veredicto de siempre.
6. Una sesión con bono completada y subida: aparece en el perfil con su renglón de metadata.

---

## Qué reportar

Para cada caso: qué probaste, qué esperabas, qué pasó, cuánto tardó el análisis, y **las capturas que mandaste** (las mismas imágenes) más el `session_metadata.json` de esa sesión.

Si la app se cierra sola o se congela, mandá también los archivos de:

```
C:\Users\<tu usuario>\Documents\Pleiada Logs\
```

(`crash.log` y `faulthandler.log`)

## Datos del build

| | |
|---|---|
| Versión | **v0.9.18** |
| Reemplaza a | v0.9.17 |
| Orden de prueba con bono | `GA-2026-021` |
| Orden de prueba sin bono (control) | `GA-2026-019` |
| Tickets que cubre | PLE-176, PLE-178, PLE-179, PLE-181, PLE-182, PLE-183 |
