# Guía de QA — v0.9.9

Reemplaza a las guías anteriores: **el encabezado del Recorder tiene que decir v0.9.9**.
Instalar el build nuevo antes de empezar.

**Tres cosas de contexto antes de arrancar:**

- ⚠️ **La ruta del log de errores que les dimos en las guías anteriores estaba mal.** No es
  `%APPDATA%`. Es `C:\Users\<usuario>\Documents\Pleiada Logs\`, y ahí adentro están `crash.log`
  y `faulthandler.log`. Si en rondas anteriores nos dijeron que el archivo no existía, era por
  esto. **Si les quedaron logs viejos en esa carpeta, mándenlos igual**: puede haber
  información de fallas que quedaron sin diagnosticar.
- Cuando abren un título que el Recorder no conocía, puede tardar unos minutos en aparecer la
  orden de destino, porque el catálogo se refresca cada tanto. Si al primer intento sale como
  grabación libre, esperen un rato y vuelvan a la pantalla principal antes de anotarlo como
  falla.
- **Del lado del servidor cambió cómo se reconocen los títulos.** Varios juegos que antes les
  pedían identificarse a mano ahora se reconocen solos. Si tienen anotado de una ronda anterior
  que algún título "no se identificaba", vuelvan a probarlo.

---

## Parte A — Los tres arreglos de esta versión

### A.1 · El título que identificaste no se vuelve a preguntar 🔴

**Qué estaba mal:** con un juego que el Recorder no conocía, lo identificabas por IGDB, te
avisaba que no había ninguna orden para ese título, volvías al menú inicial — y lo primero que
decía era *"No pudimos identificar el título"*, por el mismo juego que acababas de identificar
segundos antes.

Es el caso más importante de la ronda.

1. Con OBS apuntando a un título que el Recorder no reconozca, dejar que aparezca el
   cuestionario e identificarlo (por nombre, por enlace de IGDB, o por Steam).
2. Cuando vuelva a la pantalla principal con el título en verde, apretar **Iniciar grabación**
   y después **cancelar** durante la cuenta regresiva.

**Esperado:** vuelve a la pantalla principal y **reconoce el título solo**, en verde. No
pregunta nada.

3. Sin tocar OBS, entrar a **Mis grabaciones** y volver al inicio. Repetir 3 o 4 veces.

**Esperado:** siempre lo reconoce solo.

4. **Cerrar la app por completo y volver a abrirla**, con el mismo juego abierto.

**Esperado:** lo reconoce solo. La identificación no se pierde al reiniciar.

> 🔴 **Si en cualquiera de estos pasos les vuelve a pedir identificar el título, es el bug
> reabierto.** Anoten en cuál de los cuatro pasos pasó.

5. **Prueba cruzada, si son dos testers:** que **otra persona** abra ese mismo juego en **otra
   máquina** y espere la detección.

**Esperado:** se lo reconoce automáticamente, sin cuestionario, aunque esa persona nunca lo
haya identificado. Una vez que alguien identifica un título, queda identificado para todos.

---

### A.2 · El botón dice si la grabación va a ser libre

**Qué estaba mal:** con un título identificado pero sin ninguna orden que lo acepte, el botón
igual decía "Iniciar grabación", y recién después de grabar te enterabas de que no lo podías
subir.

1. Con un título identificado que **no** entre en ninguna orden, mirar el botón.

**Esperado:** dice **"Iniciar grabación libre"**.

2. Con un título que **sí** entre en la orden de prueba, mirar el botón.

**Esperado:** dice **"Iniciar grabación"**, sin la palabra "libre".

3. Grabar en modo libre 2–3 minutos y detener.

**Esperado:** graba normal y la sesión queda en Mis grabaciones.

---

### A.3 · La barra de la ventana se puede arrastrar entera

**Qué estaba mal:** la ventana solo se dejaba arrastrar desde una franja finita arriba a la
izquierda. En el resto de la barra el clic no hacía nada.

1. Arrastrar la ventana agarrándola de:
   - el logo **✦**
   - el texto **"Gameplay Recorder"**
   - el número de versión
   - el nombre de usuario (a la derecha, cuando están logueados)
   - cualquier espacio vacío de la barra

**Esperado:** la ventana se mueve desde **todos** esos puntos.

2. Verificar que los tres botones de la barra **sigan funcionando**:
   - la flecha **←** de volver
   - el engranaje **⚙** de Ajustes
   - la **×** de cerrar

**Esperado:** los tres responden al clic como siempre. **Si alguno dejó de andar, repórtenlo**:
es el efecto colateral típico de este arreglo.

---

### A.4 · Títulos cuyo ejecutable tiene acentos o eñes 🔴

**Qué estaba mal:** con un título cuyo ejecutable lleva un carácter con acento —por ejemplo
`Malón.exe`— el Recorder decía *"OBS apunta a Malón.exe, pero ese título no está corriendo.
Abrilo y volvé a esta pantalla"*, **con el juego abierto y capturándose adelante**. Nunca
llegaba a identificarlo ni ofrecía el cuestionario: se quedaba pegado en *Esperando el título*.

Afecta a cualquier ejecutable con `á é í ó ú ñ ü` o cualquier carácter fuera del inglés, que
son comunes en títulos en castellano, portugués y francés.

1. Abrir un título cuyo ejecutable tenga un acento o una eñe y apuntarle la fuente de OBS.

**Esperado:** lo detecta normalmente — lo identifica solo, o abre el cuestionario si no lo
conoce. Lo que **no** puede pasar es que diga que el título no está corriendo.

> Para verificar el nombre del ejecutable: en OBS, propiedades de la fuente de Captura de
> Videojuego, el desplegable **Ventana** lo muestra entre corchetes.

2. Si no tienen ninguno a mano, sirve renombrar una copia de cualquier `.exe` inofensivo
   agregándole un acento, abrirlo y apuntarle OBS.

3. Grabar 2–3 minutos con ese título y detener.

**Esperado:** la sesión se graba y aparece en Mis grabaciones con el nombre bien escrito, sin
caracteres raros.

---

### A.5 · Los acentos de la pantalla principal

Varios textos del panel de detección estaban escritos sin tildes.

1. Recorrer los estados del panel: esperando, identificando, título identificado con orden,
   título identificado sin orden, OBS cerrado, OBS ya grabando, modo de captura incorrecto.

**Esperado:** todos los textos con sus tildes y eñes correctas — *está*, *título*, *órdenes*,
*Podés*, *Chequeá*, *sesión*, *grabación*, *contraseña*, *específica*.

> Si ven un carácter raro en lugar de una tilde (`Ã³`, `¢`, un rombo con signo de pregunta),
> **eso sí es un bug** y es distinto: es un problema de codificación, no de redacción.
> Repórtenlo con captura.

---

## Parte B — El flujo de identificación completo

Si el Recorder no logra identificar lo que OBS está capturando, le pregunta al jugador. Esta
parte prueba ese flujo entero.

**La regla que no cambia, y que es lo más importante de toda la guía:** el título se identifica
**siempre, antes de grabar**. Si al final de todos los pasos seguimos sin saber qué es, la
grabación queda bloqueada. **No existe ningún camino que termine en "grabalo igual sin
identificar".** Si encuentran uno, ése es el bug más grave que pueden reportar.

### Cómo llegar a estas pantallas

- Un título reciente o poco conocido que el Recorder no reconozca.
- Si no tienen ninguno a mano: **apunten la fuente de OBS a la ventana de un programa que no sea
  un juego** (un editor de texto, una calculadora).

> En los dos casos la fuente tiene que ser **Captura de Videojuego** en modo **ventana
> específica**. Con la fuente en "cualquier aplicación en pantalla completa" el Recorder no
> puede saber qué está enganchado y ni siquiera llega a intentar identificarlo.

### B.1 · Aparece el cuestionario, no un bloqueo

**Esperado:** la pantalla **"No pudimos identificar el título"**, con un campo para escribir el
nombre y un botón **Buscar**. Arriba, un recuadro **OBS ESTÁ CAPTURANDO** que muestra lo que la
app está viendo.

> Ese recuadro tiene que coincidir con lo que apuntaron en OBS. Si dice otra cosa, eso ya es un
> hallazgo: anótenlo con una captura de la configuración de la fuente en OBS.

### B.2 · Buscar por nombre y elegir de la lista

1. Escribir un nombre real (por ejemplo `metro last light`) y apretar **Buscar**.

**Esperado:** **"¿Es alguno de estos?"** con hasta 5 resultados, cada uno con su año.

2. **Tocar el nombre** de un resultado. → Se abre el navegador en su ficha de IGDB.
3. Volver al Recorder, apretar **Es este**, y después **Sí, es este**.

**Esperado:** vuelve a la pantalla principal con el título en verde, listo para grabar.

### B.3 · Búsqueda sin resultados

1. Buscar algo que no exista, por ejemplo `asdfghjkl`.

**Esperado:** **"No encontramos ese título"**, con tres salidas (otro nombre, enlace de IGDB,
página de Steam) y un botón para volver al inicio.

### B.4 · Identificar pegando el enlace de IGDB

1. Desde la lista de resultados, **Ninguno es el mío** → pantalla **"Pegá el enlace de IGDB"**.
2. Apretar **Abrir IGDB** → abre el sitio en el navegador.
3. Buscar ahí cualquier juego, copiar la dirección (`https://www.igdb.com/games/algo`), pegarla
   y **Confirmar**.

**Esperado:** vuelve a la pantalla principal con ese título identificado.

4. Repetir con una dirección inventada, por ejemplo
   `https://www.igdb.com/games/esto-no-existe-12345`.

**Esperado:** el error se muestra **en la misma pantalla**, sin perder lo que escribieron.

### B.5 · Última instancia: la página de Steam

1. **No lo encuentro en IGDB** → pantalla **"Probemos de otra manera:"**, con un campo para el
   enlace de Steam y un desplegable de perspectiva que arranca en **No sé**.
2. Pegar `https://store.steampowered.com/app/220/HalfLife_2/`, dejar **No sé**, **Confirmar**.

**Esperado:** vuelve a la pantalla principal con el título identificado.

3. Repetir eligiendo una perspectiva del desplegable en vez de "No sé".

**Esperado:** lo mismo. El desplegable tiene que abrirse y cerrarse bien, con las opciones
legibles sobre el fondo oscuro.

4. Probar con algo que **no** sea un videojuego:
   `https://store.steampowered.com/app/431960/Wallpaper_Engine/`

**Esperado:** lo rechaza. **No** lo tiene que aceptar.

5. Probar con un enlace que no sea de Steam, por ejemplo `https://www.google.com`.

**Esperado:** avisa que no es la dirección de un juego en Steam, en la misma pantalla.

### B.6 · El bloqueo, y que se pueda salir de él

1. En la pantalla de Steam, después de un intento fallido, apretar **No lo puedo identificar**.

**Esperado:** **"No podemos habilitar la grabación"**.

2. Apretar **Volver a la pantalla de inicio**.

**Esperado:** vuelve a la principal, con **"No pudimos identificar el título"** y un enlace
**Identificar el título**.

> 🔴 **Lo que NO puede pasar: que al volver al inicio se reabra solo el cuestionario que acaban
> de abandonar.** Si entran en un ida y vuelta del que no se sale, es bloqueante.

3. Verificar que **Iniciar grabación** esté **deshabilitado**, y probar también el atajo de
   teclado.

**Esperado:** no arranca nada, ni por botón ni por atajo.

4. Apretar **Identificar el título** → vuelve a abrir el cuestionario, esta vez a pedido.
5. Sin cerrar la app, cambiar la fuente de OBS a un juego conocido.

**Esperado:** el panel se recupera solo, sin reiniciar la app.

### B.7 · La flecha de volver

En cada pantalla del flujo hay una flecha **←** arriba a la izquierda. Recorran los pasos hacia
adelante y hacia atrás dos o tres veces.

**Esperado:** lleva al paso anterior sin colgar la app, y desde el primer paso vuelve a la
pantalla principal.

---

## Parte C — Smoke completo antes de producción

| # | Qué hacer | Qué tiene que pasar |
|---|---|---|
| 1 | Actualizar desde una versión anterior con el Updater | Abre en v0.9.9, con los acentos y los íconos bien |
| 2 | Abrir la app ya logueados | Entra directo a la pantalla principal, sin errores |
| 3 | Con un título conocido abierto y OBS corriendo, esperar la detección | Título en verde, con género · perspectiva · modo |
| 4 | Entrar a **Mis grabaciones** y volver al inicio, rápido, 3 o 4 veces | Siempre vuelve a detectar. **Nunca hay que cerrar la app** |
| 5 | Lo mismo entrando a **Ajustes** | Igual que el punto 4 |
| 6 | Entrar y salir del cuestionario de identificación varias veces seguidas | Igual: siempre vuelve a detectar |
| 7 | Cerrar OBS y volver a abrirlo, sin tocar el Recorder | El panel se recupera solo |
| 8 | Poner a grabar a OBS por su cuenta y después detenerlo desde OBS | El panel se recupera solo |
| 9 | En OBS, dejar una fuente de Captura de Pantalla y volver a Captura de Videojuego | El panel se recupera solo |
| 10 | Cerrar el título (sin cerrar OBS) | El panel avisa que ese título no está corriendo |
| 11 | Iniciar grabación y **cancelar durante la cuenta regresiva** | Pide confirmación, no corre la verificación, y la carpeta no queda en Documentos |
| 12 | Iniciar grabación, dejar que arranque y **cancelar ya grabando** | Corta también en OBS: OBS **no** queda grabando por detrás |
| 13 | Grabar 2–3 minutos y detener | Termina, verifica y aparece en Mis grabaciones |
| 14 | Subir esa sesión a la orden de prueba | Sube completa y queda registrada |
| 15 | Volver a intentar subir la misma sesión | Avisa que ya estaba subida; no la duplica |
| 16 | **Durante una grabación, cambiar la fuente de OBS a otro juego** | La sesión se cancela sola y avisa por qué |
| 17 | Grabar y subir un título identificado por el cuestionario (caso B.2) | Sube igual que cualquier otro |
| 18 | Arrastrar la ventana durante una grabación | Se mueve, y la grabación no se corta |
| 19 | Windows en escala **125%**, recorrer las pantallas del cuestionario | Textos completos y botones dentro de la ventana |
| 20 | Lo mismo en **150%** | Igual que el 19 |
| 21 | Un título que no esté en el catálogo y que la orden no acepte | Se puede grabar igual, con el botón diciendo "Iniciar grabación libre" |
| 22 | Cerrar sesión desde Ajustes y volver a entrar con el código | Vuelve a la pantalla principal y detecta normal |

### Prueba de sesión vencida, también dentro del cuestionario

1. Cerrar el Recorder.
2. Abrir `%APPDATA%\Pleiada\auth.json` con el Bloc de notas y cambiar unos caracteres del token
   (no del email). Guardar.
3. Abrir el Recorder, llegar al cuestionario y apretar **Buscar**.

**Esperado:** **"Tu sesión venció."** con el botón **Iniciar sesión**. No tiene que quedarse
colgado en "Buscando…" ni mostrar un error de título.

---

## Qué NO es un bug en esta ronda

- **Que un título identificado quede como grabación libre.** Identificarlo y que entre en una
  orden son dos cosas distintas: puede quedar bien identificado y aun así no ser lo que las
  órdenes abiertas están buscando. El botón lo dice antes de grabar.
- **Que Team Fortress 2 se identifique pero no se pueda subir.** Es lo esperado.
- **Que la perspectiva que eligieron en el paso de Steam no coincida con la que muestra después
  la app.** Cuando el título ya lo conocíamos, manda el dato que ya teníamos.
- **Que un título tarde unos minutos en pasar de "grabación libre" a mostrar su orden.** El
  catálogo se refresca cada tanto.

---

## Qué reportar

Por cada falla: el número del paso o el caso, qué título o programa tenían apuntado en OBS, la
escala de pantalla, y el video o la captura.

Si la app se queda pegada o deja de responder, **antes de cerrarla** copien el contenido de:

```
C:\Users\<usuario>\Documents\Pleiada Logs\
```

Para los casos del cuestionario, sumen **qué escribieron o pegaron exactamente**: el nombre
buscado o el enlace completo. Sin eso no podemos reproducirlo.
