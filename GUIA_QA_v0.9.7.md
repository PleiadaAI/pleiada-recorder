# Guía de QA — v0.9.7

Reemplaza a las guías anteriores: **el encabezado del Recorder tiene que decir v0.9.7**.
Instalar el build nuevo antes de empezar.

**Dos cosas de contexto antes de arrancar:**

- Cuando abren un título que el Recorder no conocía, puede tardar unos minutos en aparecer la
  orden de destino, porque el catálogo se refresca cada tanto. Si al primer intento sale como
  grabación libre, esperen un rato y vuelvan a entrar a la pantalla principal antes de anotarlo
  como falla.
- **Se corrigió una clasificación de títulos que estaba mal del lado del servidor.** Si en la
  ronda anterior anotaron que algún título "no entraba en la orden", vuelvan a probarlo: puede
  que ahora sí entre. No hace falta el build nuevo para eso, ya está aplicado.

---

## Parte A — Lo nuevo: cuando el Recorder no reconoce el título, ahora pregunta

Hasta la versión anterior, si el Recorder no lograba identificar lo que OBS estaba capturando,
mostraba un cartel de bloqueo y ahí se terminaba: el jugador no podía grabar y no tenía nada
que hacer al respecto. Es lo que reportaron en PLE-169.

Ahora, en vez de bloquear de entrada, le pregunta al jugador cuál es el título. Si con esa
información logramos identificarlo, lo deja grabar.

**La regla que no cambió, y que es lo más importante de toda esta guía:** el título se
identifica **siempre, antes de grabar**. Si al final de todos los pasos seguimos sin saber qué
es, la grabación queda bloqueada. **No existe ningún camino que termine en "grabalo igual sin
identificar".** Si encuentran uno, ése es el bug más grave que pueden reportar en esta ronda.

### Cómo llegar a estas pantallas

Necesitan que el Recorder **no** reconozca lo que OBS captura. Dos formas:

- Un título reciente o poco conocido que no esté en el catálogo.
- Si no tienen ninguno a mano: **apunten la fuente de OBS a la ventana de un programa que no sea
  un juego** (un editor de texto, una calculadora, lo que sea). Sirve igual para recorrer todas
  las pantallas.

> En los dos casos la fuente tiene que ser **Captura de Videojuego** en modo **ventana
> específica**. Con la fuente en "cualquier aplicación en pantalla completa" el Recorder no
> puede saber qué está enganchado y ni siquiera llega a intentar identificarlo.

---

### A.1 · Aparece el cuestionario, no el bloqueo

1. Con OBS apuntando a algo que el Recorder no reconozca, esperar la detección.

**Esperado:** la app cambia a una pantalla que dice **"No pudimos identificar el título"**, con
un campo para escribir el nombre y un botón **Buscar**.

Arriba del campo hay un recuadro **OBS ESTÁ CAPTURANDO** que muestra lo que la app está viendo.

> Ese recuadro tiene que coincidir con lo que ustedes apuntaron en OBS. Si dice otra cosa, eso
> ya es un hallazgo: anótenlo con una captura de la configuración de la fuente en OBS.

**No esperado:** que se quede en el cartel viejo de bloqueo sin ofrecer nada.

---

### A.2 · Buscar por nombre y elegir de la lista

1. Escribir un nombre de juego real (por ejemplo `metro last light`) y apretar **Buscar**.

**Esperado:** aparece **"¿Es alguno de estos?"** con hasta 5 resultados, cada uno con su año.

2. **Tocar el nombre** de cualquiera de los resultados.

**Esperado:** se abre el navegador en la ficha de ese juego en IGDB. La app queda donde estaba.

3. Volver al Recorder y apretar **Es este** en uno de los resultados.

**Esperado:** una pantalla de confirmación con ese título. Apretar **Sí, es este**.

4. **Esperado, y es el punto clave del caso:** vuelve a la pantalla principal con el título **en
   verde**, listo para grabar — y **no vuelve a preguntar**. La app no puede reabrir el
   cuestionario que acaban de completar.

5. Quedarse en la pantalla principal **un minuto entero sin tocar nada**.

**Esperado:** el título sigue en verde. No parpadea, no vuelve al cuestionario, no cambia solo.

6. Apretar **Iniciar grabación**, grabar 2–3 minutos y detener.

**Esperado:** graba normal y la sesión aparece en Mis grabaciones.

---

### A.3 · Búsqueda que no encuentra nada

1. Volver al cuestionario y buscar algo que no exista, por ejemplo `asdfghjkl`.

**Esperado:** **"No encontramos ese título"**, con tres salidas: probar con otro nombre, cargar
el enlace de IGDB, o buscarlo por su página de Steam. Y un botón para volver al inicio.

---

### A.4 · Identificar pegando el enlace de IGDB

1. Desde la lista de resultados, apretar **Ninguno es el mío**.

**Esperado:** la pantalla **"Pegá el enlace de IGDB"**.

2. Apretar el enlace **Abrir IGDB**.

**Esperado:** abre el sitio de IGDB en el navegador.

3. Buscar ahí cualquier juego, copiar la dirección de la barra del navegador
   (queda del tipo `https://www.igdb.com/games/algo`), pegarla en el campo y apretar
   **Confirmar**.

**Esperado:** vuelve a la pantalla principal con ese título identificado, en verde.

4. Repetir pegando una dirección inventada, por ejemplo
   `https://www.igdb.com/games/esto-no-existe-12345`.

**Esperado:** un mensaje de error **en la misma pantalla**, sin perder lo que escribieron y sin
sacarlos de ahí.

---

### A.5 · Última instancia: la página de Steam

1. En la pantalla del enlace de IGDB, apretar **No lo encuentro en IGDB**.

**Esperado:** la pantalla **"Probemos de otra manera:"**, con un campo para el enlace de Steam
y un desplegable de perspectiva que arranca en **No sé**.

2. Pegar el enlace de un juego de Steam, por ejemplo:

   ```
   https://store.steampowered.com/app/220/HalfLife_2/
   ```

   Dejar la perspectiva en **No sé** y apretar **Confirmar**.

**Esperado:** vuelve a la pantalla principal con el título identificado.

3. Repetir el caso eligiendo una perspectiva del desplegable (Primera persona, Tercera persona,
   etc.) en vez de dejar "No sé".

**Esperado:** lo mismo. El desplegable tiene que abrirse y cerrarse bien, con las opciones
legibles sobre el fondo oscuro.

4. Probar con un enlace de Steam que **no** sea un videojuego:

   ```
   https://store.steampowered.com/app/431960/Wallpaper_Engine/
   ```

**Esperado:** lo rechaza con un mensaje del tipo *"eso no parece un videojuego"*. **No** lo tiene
que aceptar.

5. Probar con un enlace que no sea de Steam, por ejemplo `https://www.google.com`.

**Esperado:** avisa que no es la dirección de un juego en Steam, en la misma pantalla.

---

### A.6 · El bloqueo, y que se pueda salir de él

Éste es el caso que más nos interesa de la ronda.

1. Recorrer el flujo hasta la pantalla de Steam y, después de un intento fallido, apretar
   **No lo puedo identificar**.

**Esperado:** la pantalla **"No podemos habilitar la grabación"**, que explica que sin saber qué
título es no se puede catalogar la sesión.

2. Apretar **Volver a la pantalla de inicio**.

**Esperado, y acá está el punto:** vuelve a la pantalla principal, que muestra en el panel **"No
pudimos identificar el título"** con un enlace **Identificar el título**.

> 🔴 **Lo que NO puede pasar: que al volver al inicio se les reabra solo el cuestionario que
> acaban de abandonar.** Si entran en un ida y vuelta del que no se sale, repórtenlo como
> bloqueante.

3. Verificar que el botón **Iniciar grabación** esté **deshabilitado**.

4. Probar también el atajo de teclado de iniciar grabación.

**Esperado:** no arranca nada. Sin título identificado no se graba, ni por botón ni por atajo.

5. Apretar el enlace **Identificar el título**.

**Esperado:** vuelve a abrir el cuestionario, esta vez porque ustedes lo pidieron.

6. Sin cerrar la app, **cambiar la fuente de OBS a un juego que el Recorder sí conozca**.

**Esperado:** el panel se recupera solo y lo identifica normal, sin reiniciar la app.

---

### A.7 · La flecha de volver

En cada pantalla del flujo hay una flecha **←** arriba a la izquierda.

**Esperado:** lleva al paso anterior sin colgar la app, y desde el primer paso vuelve a la
pantalla principal. Recorran los pasos hacia adelante y hacia atrás dos o tres veces.

---

## Parte B — Smoke completo antes de producción

| # | Qué hacer | Qué tiene que pasar |
|---|---|---|
| 1 | Actualizar desde una versión anterior con el Updater | Abre en v0.9.7, con los acentos y los íconos bien |
| 2 | Abrir la app ya logueados | Entra directo a la pantalla principal, sin errores |
| 3 | Con un título conocido abierto y OBS corriendo, esperar la detección | Título en verde, con género · perspectiva · modo |
| 4 | Entrar a **Mis grabaciones** y volver al inicio, rápido, 3 o 4 veces, sin esperar a que detecte | Siempre vuelve a detectar. **Nunca hay que cerrar la app** |
| 5 | Lo mismo entrando a **Ajustes** | Igual que el punto 4 |
| 6 | Entrar y salir del cuestionario de identificación varias veces seguidas, rápido | Igual: siempre vuelve a detectar |
| 7 | Cerrar OBS y volver a abrirlo, sin tocar el Recorder | El panel se recupera solo |
| 8 | Poner a grabar a OBS por su cuenta y después detenerlo desde OBS | El panel se recupera solo |
| 9 | En OBS, dejar una fuente de Captura de Pantalla y después volver a Captura de Videojuego | El panel se recupera solo |
| 10 | Cerrar el título (sin cerrar OBS) | El panel avisa que ese título no está corriendo |
| 11 | Iniciar grabación y **cancelar durante la cuenta regresiva** | Pide confirmación, no corre la verificación, y la carpeta no queda en Documentos |
| 12 | Iniciar grabación, dejar que arranque y **cancelar ya grabando** | Corta también en OBS: OBS **no** queda grabando por detrás |
| 13 | Grabar 2–3 minutos y detener | Termina, verifica y aparece en Mis grabaciones |
| 14 | Subir esa sesión a la orden de prueba | Sube completa y queda registrada |
| 15 | Volver a intentar subir la misma sesión | Avisa que ya estaba subida; no la duplica |
| 16 | **Durante una grabación, cambiar la fuente de OBS a otro juego** | La sesión se cancela sola y avisa por qué |
| 17 | Grabar y subir un título identificado por el cuestionario (caso A.2) | Sube igual que cualquier otro |
| 18 | Windows en escala **125%**, recorrer las pantallas del cuestionario | Se leen completos los textos y los botones no quedan fuera de la ventana |
| 19 | Lo mismo en **150%** | Igual que el 18 |
| 20 | Un título que no esté en el catálogo y que la orden no acepte | Se puede grabar igual, avisando que ninguna orden lo está buscando |
| 21 | Cerrar sesión desde Ajustes y volver a entrar con el código | Vuelve a la pantalla principal y detecta normal |

### Prueba de sesión vencida, ahora también dentro del cuestionario

1. Cerrar el Recorder.
2. Abrir `%APPDATA%\Pleiada\auth.json` con el Bloc de notas y cambiar unos caracteres del token
   (no del email). Guardar.
3. Abrir el Recorder, llegar al cuestionario y apretar **Buscar**.

**Esperado:** aparece **"Tu sesión venció."** con el botón **Iniciar sesión**. No tiene que
quedarse colgado en "Buscando…" ni mostrar un error de título.

---

## Qué NO es un bug en esta ronda

- **Que un título identificado por el cuestionario quede como grabación libre.** Identificarlo y
  que entre en una orden son dos cosas distintas: puede quedar bien identificado y aun así no
  ser lo que las órdenes abiertas están buscando.
- **Que Team Fortress 2 no se pueda subir.** Se graba en libre a propósito.
- **Que la perspectiva que eligieron en el paso de Steam no coincida con la que muestra después
  la app.** Cuando el título ya lo conocíamos, manda el dato que ya teníamos.

---

## Qué reportar

Por cada falla: el número del paso o el caso de la Parte A, qué título o programa tenían
apuntado en OBS, la escala de pantalla, y el video o la captura. Si la app se queda pegada o
deja de responder, antes de cerrarla copien el log de errores y adjúntenlo.

> ⚠️ **La ruta del log que les dimos en las guías anteriores estaba mal.** No es `%APPDATA%`.
> Está en:
>
> ```
> C:\Users\<usuario>\Documents\Pleiada Logs\
> ```
>
> Ahí adentro: `crash.log` y `faulthandler.log`. Si en rondas anteriores nos dijeron que el
> archivo no existía, era por esto — estaban mirando una carpeta que nunca existió. Si tienen
> logs viejos de esa carpeta de rondas anteriores, mándenlos también.

Para los casos del cuestionario, sumen **qué escribieron o pegaron exactamente**: el nombre
buscado o el enlace completo. Sin eso no podemos reproducirlo.
