# Guía de QA — Gameplay Recorder v0.9.17

## Qué hay de nuevo

**Una sola función nueva: el bono por metadata de controles.** Al terminar una sesión válida, si el título grabado todavía no tiene su mapa de controles en nuestra base, el Recorder ofrece un bono por compartir la pantalla de controles del título. El resto de la app no cambió.

Cómo funciona, en cuatro líneas:

1. Terminás una sesión con una orden de destino. Si el título necesita su mapa de controles, aparece una tarjeta con el monto del bono (el 25 % del precio por hora de la orden, monto fijo por aporte).
2. Sacás una o más capturas de la pantalla de controles de teclado y mouse del título, **con los controles por defecto**, y las subís desde el Recorder.
3. El Recorder las analiza en el momento (10 a 60 segundos). Si encuentra lo mínimo, el aporte queda en **Validación pendiente**. Si no, te dice qué faltó y podés reintentar.
4. Cuando otra persona manda los mismos controles para ese título, el mapa se valida y el bono de las dos pasa a **Pago pendiente**. Lo ves en tu perfil, debajo del dataset.

**Para esta ronda hay una orden de prueba nueva: `GA-2026-021 · QA · Metadata de controles (orden de prueba)`.** Es la que ofrece el bono; `GA-2026-019` sigue existiendo y NO lo ofrece (sirve como control). Como siempre con las órdenes de prueba: **si ya estaban logueados, cerrar sesión y volver a entrar** para que se inscriba sola.

---

## Antes de empezar

- Instalar `PleiadaRecorder_Setup_v0.9.17.exe` sobre la versión anterior. En el título de la ventana tiene que decir **v0.9.17**.
- Cerrar sesión y volver a entrar en el Recorder (la orden de prueba se asigna al loguearse).
- Elegir **dos títulos** de acción o aventura que tengan instalados, uno "conocido" y uno "raro". Anoten cuáles: el flujo se prueba en los dos, y con **dos testers distintos sobre el mismo título** para la prueba de validación.
- Tener a mano cómo sacar capturas: `Impr Pant` (queda en el portapapeles, hay que pegarla en Paint y guardar), `Win+Shift+S` (guarda en Imágenes\Capturas de pantalla) o el overlay de Steam (`F12`, guarda en la carpeta de Steam).

---

## A · La oferta aparece cuando corresponde, y solo entonces

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| A1 | Grabar 1 minuto con `GA-2026-021` como destino, un título que no sea de motor Source. Cortar. | En "Sesión lista para enviar" aparece la tarjeta **"Ganá el 25 % de la hora por la metadata"** con el monto **US$ 0,75** y un solo botón: **Compartir controles**. |
| A2 | Lo mismo, pero eligiendo `GA-2026-019` como destino. | **No aparece** ninguna tarjeta de bono. La pantalla es la de siempre. |
| A3 | Grabar en modo libre (un título que no entre en ninguna orden, o sin orden elegida). | Aparece la tarjeta **"Este título no tiene mapa de controles"**, que habla del **sorteo mensual** y no menciona dinero. |
| A4 | Grabar **Counter-Strike 2, Left 4 Dead 2 o Portal 2** (motor Source) con `GA-2026-021`. | **No aparece** tarjeta: en esos títulos el Recorder lee los controles solo. En `session_metadata.json` → `input.binding_source` dice `config`. |
| A5 | Una sesión que **no pase** el sync check (cortar a los 10 segundos). | No aparece ninguna tarjeta: la sesión no se sube y no hay nada que bonificar. |

⚠️ La tarjeta llega uno o dos segundos después que el resto de la pantalla (pregunta al servidor). Si no aparece, esperen tres segundos antes de anotarlo.

---

## B · El modal al subir sin aportar

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| B1 | En el caso A1, tocar **Subir Data Set** sin haber compartido controles. | Se abre un cuadro **"¿Subir el dataset sin la metadata?"** con dos botones: **Compartir controles** (lleva al paso 1) y **Subir sin metadata** (sigue con la subida de siempre). |
| B2 | En A2 y A3, tocar Subir Data Set. | **No** hay cuadro: va derecho a la subida. En A3 (modo libre) los botones son los de siempre para una sesión libre. |
| B3 | Compartir controles, completar el aporte (ver C) y recién después tocar Subir Data Set. | No vuelve a preguntar. |

---

## C · Compartir controles: los tres pasos

**Paso 1 · Lo mínimo que necesitamos.** Tiene que verse el esquema con las cuatro teclas de movimiento y el botón principal del mouse marcados en verde, las tres viñetas (varias pestañas / restablecer controles / sensibilidad y mando no sirven) y el recuadro **"Hacen falta dos personas"**. Botones Volver y Siguiente **completos y visibles** abajo (esta pantalla es alta: si alguno queda cortado, es un hallazgo; anotar resolución y escala de Windows).

**Paso 2 · Cómo lo compartís.** Una sola vía: **Elegir imágenes…** abre el selector de archivos (se pueden elegir varias a la vez). No hay pegar del portapapeles ni escribir el mapa: es a propósito.

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| C1 | Elegir una captura válida de la pantalla de controles (PNG o JPG, al menos 1280 × 720). | Aparece la miniatura con una ✕, y el contador dice **1 de 6 imágenes · X de 40 MB**. El botón Revisar se habilita. |
| C2 | Elegir la **misma** imagen otra vez. | Mensaje **"esa imagen ya está cargada"**, sigue en 1 de 6. |
| C3 | Elegir un archivo que no sea imagen (un .txt, un .pdf). | Mensaje "no es una imagen PNG, JPG o WebP". |
| C4 | Elegir una imagen chica (menos de 1280 × 720, por ejemplo un ícono). | Mensaje "es muy chica (…) Necesitamos al menos 1280 × 720". |
| C5 | Cargar 6 imágenes y tratar de sumar una séptima. | Mensaje "Ya cargaste 6 imágenes, el máximo." |
| C6 | Tocar la ✕ de una miniatura. | Desaparece y el contador baja. Con cero imágenes, Revisar se deshabilita. |
| C7 | Una captura PNG pesada (4K, más de 5 MB). | Se acepta (hasta 10 MB de entrada). El Recorder la reduce antes de subir; no hace falta que hagan nada. |

**Paso 3 · Revisá antes de enviar.** Resumen (título, dataset, cuántas capturas, monto del bono o "Ticket para el sorteo mensual"), las miniaturas, y el recuadro amarillo **"OBLIGATORIO PARA ANALIZAR"** con la casilla.

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| C8 | Sin marcar la casilla. | El botón **Analizar metadata** está deshabilitado (gris). |
| C9 | Marcar la casilla. | El botón se habilita (violeta). Desmarcarla lo vuelve a deshabilitar. |
| C10 | Volver desde el paso 3 al 2 y al 1, y de ahí al resultado de la sesión. | Las imágenes cargadas **se conservan** al volver al paso 2. La tarjeta del bono sigue en el resultado. |

---

## D · El análisis, con capturas buenas y malas

Al tocar **Analizar metadata** aparece la pantalla **"Analizando tus capturas"** con el indicador animado y cuatro etapas que se van tildando. Tarda entre 10 y 60 segundos. **Anotar cuánto tardó** en cada caso.

| Caso | Capturas | Resultado esperado |
|---|---|---|
| D1 | La pantalla de controles de teclado y mouse, **por defecto**, completa (todas las pestañas si hay más de una). | Pantalla **"Controles recibidos"**: "Leímos N controles de <título>", estado **Validación pendiente**, botón **Continuar con la subida del dataset**. N tiene que ser parecido a la cantidad de controles que muestra el título (anótenlo). |
| D2 | La pantalla de **sensibilidad del mouse** (la de sliders). | Pantalla **"No pudimos leer lo mínimo"** con el motivo "vimos la pantalla de sensibilidad". Dice **Intento 1 de 3**. Botones Subir sin metadata / Volver a intentar. |
| D3 | La pantalla del **mando / gamepad**. | Mismo error, motivo "la pantalla del mando". |
| D4 | Una captura de **otro título** (por ejemplo el escritorio o un juego distinto). | Error. El motivo puede ser "otro título" o el genérico de información mínima; cualquiera de los dos es correcto. |
| D5 | Solo la pestaña de **vehículo** de un título que tiene a pie y vehículo. | Error: falta lo mínimo (la pestaña de vehículo no cuenta como movimiento del personaje). |
| D6 | Una captura muy borrosa o comprimida (guardar como JPG calidad 20). | Error por ilegible, o un N bajo si igual la lee. Anotar cuál. |
| D7 | Después de un error, **Volver a intentar** → sumar la captura correcta a las que estaban → Analizar. | Vuelve al paso 2 **con las imágenes anteriores cargadas**, y con la buena agregada pasa a "Controles recibidos". |
| D8 | Tres errores seguidos en la misma sesión. | En el tercero, el texto dice que ya probaste tres veces y **Volver a intentar queda deshabilitado**; queda Subir sin metadata. |
| D9 | Con controles **personalizados** (cambiar W por otra tecla en el título antes de capturar). | Error "no parecen ser los por defecto", o acepta con N bajo. Anotar cuál: es un caso que queremos ver con datos reales. |

⚠️ Si el servidor no responde ("No pudimos analizar las capturas en este momento"), no cuenta como intento. Reintentar en un minuto; si persiste, avisar.

---

## E · Validación entre dos testers (la prueba importante)

Para el **mismo título**, con `GA-2026-021`:

| Paso | Quién | Qué hacer | Resultado esperado |
|---|---|---|---|
| E1 | Tester 1 | Grabar, compartir controles (D1), subir el dataset. | "Controles recibidos" → Validación pendiente. En el **perfil web** (gameplayalliance.gg/profile → Mis subidas) aparece el dataset y, debajo, un renglón violeta **"<Título> · Metadata"** con **Validación pendiente** y US$ 0,75. |
| E2 | Tester 1 | Grabar el mismo título otra vez y cortar. | **No** aparece la tarjeta del bono: ya aportaste ese título. |
| E3 | Tester 2 | Grabar el mismo título, compartir controles con **la misma pantalla por defecto**, subir. | "Controles recibidos". Poco después, en el perfil de **los dos**, el renglón de metadata pasa a **Validada · Pago pendiente**. |
| E4 | Tester 3 (o cualquiera después de E3) | Grabar el mismo título y cortar. | **No** aparece la tarjeta: el título ya tiene su mapa. |
| E5 | Tester 2, variante | En E3, compartir controles y **no** subir el dataset (cerrar el Recorder). | En el perfil aparece **Validada · Falta subir el dataset**. Al subir esa sesión desde "Mis grabaciones", pasa a Pago pendiente. |

⚠️ En E3 la validación depende de que las dos capturas digan lo mismo. Si los dos testers usan pantallas distintas del mismo título (uno la de movimiento, otro la de combate), puede quedar en Validación pendiente: anotar qué pantalla mandó cada uno.

---

## F · Perfil web

En **gameplayalliance.gg/profile**, sección **Mis subidas**:

- Cada aporte es un renglón **debajo del dataset** del que salió, con fondo violeta claro, ícono ⌨ y el nombre "<Título> · Metadata".
- Estados posibles: **Validación pendiente**, **Validada · Pago pendiente**, **Validada · Falta subir el dataset**, **Pagada**. Sin wallet cargada dice "Validada · Pago bloqueado s/ wallet".
- Los filtros (Pendientes de QA, QA OK…) muestran el renglón de metadata junto a su dataset; no tiene filtro propio.
- Un aporte que dio error en el Recorder **no aparece** en el perfil: nunca se registró.

---

## Smoke test — que no se haya roto nada

1. Instalar sobre la versión anterior; la app abre; el título dice **v0.9.17**.
2. Login; la lista de títulos carga; se puede elegir orden.
3. Identificación del título funciona igual que antes.
4. Grabar 3 minutos con `GA-2026-019`, cortar, sesión completa: **1 video + 4 CSV + `session_metadata.json`**. Sin tarjeta de bono.
5. Subir la sesión sin pasar por ningún cuadro nuevo.
6. Synch Checker con el mismo veredicto de siempre.
7. Una sesión con bono completada (D1) y subida: el dataset se sube igual que siempre y aparece en el perfil con su renglón de metadata.

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
| Versión | **v0.9.17** |
| Reemplaza a | v0.9.16 (no se publica) |
| Orden de prueba con bono | `GA-2026-021` |
| Orden de prueba sin bono (control) | `GA-2026-019` |
