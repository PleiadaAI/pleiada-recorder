# Guía de QA — Gameplay Recorder v0.9.3

Build: `PleiadaRecorder_Update.exe` · estampado 0.9.3

Segunda ronda sobre la v0.9.2. Corrige los tres bugs que quedaron abiertos de esa ronda y
ajusta el panel de tips.

---

## Antes de empezar

- Instalar el `.exe` y abrir el Recorder. **El encabezado tiene que decir v0.9.3.** Si dice
  otra versión, no se instaló lo que corresponde y el resto de la guía no aplica.
- En OBS, la fuente tiene que ser **Captura de Videojuego (Game Capture)** en modo
  **ventana específica**, apuntada a la ventana del título.
- Hace falta estar logueado y con conexión.

---

## 1. OBS que se cierra y se vuelve a abrir

**Qué estaba mal:** si cerrabas OBS y lo abrías de nuevo sin cerrar el Recorder, el
Recorder no volvía a buscar nada. Había que reiniciar la app.

La causa era interna: el Recorder recordaba "este título ya lo resolví" y esa marca no se
borraba cuando el panel se caía a "Esperando el título". Cuando OBS volvía, el Recorder
veía lo mismo de antes, daba por hecho que ya estaba resuelto y no redibujaba nada.

### 1.1 El caso reportado

1. Con un título abierto y detectado (panel en verde), **cerrar OBS**.
2. El panel pasa a "OBS no está corriendo o no responde".
3. **Volver a abrir OBS**, sin tocar el Recorder.

**Esperado:** en pocos segundos el panel vuelve solo a detectar el título y el botón
Iniciar se habilita. **Sin reiniciar la app.**

### 1.2 Detener una grabación desde OBS

1. Con el Recorder abierto en la pantalla principal, poner a grabar a **OBS** por su cuenta
   (no desde el Recorder). El panel pasa a "OBS ya está grabando".
2. Detener esa grabación desde OBS.

**Esperado:** el panel se recupera solo y vuelve a detectar el título.

### 1.3 Corregir el modo de captura

1. En OBS, dejar activa una fuente de **Captura de Pantalla** o **Captura de Ventana**. El
   panel avisa "Modo de captura incorrecto".
2. Cambiarla a **Captura de Videojuego (Game Capture)** apuntada al título.

**Esperado:** el panel se recupera solo.

Los tres casos son el mismo bug de fondo. Si alguno queda pegado, anotá cuál.

### 1.4 Que el panel no quede en blanco

Entrar a **Ajustes** y volver a la pantalla principal, varias veces, en distintos estados
(detectado, esperando, bloqueado).

**Esperado:** el panel siempre muestra algo. Un panel vacío es un bug.

### 1.5 Que no parpadee

Dejar el Recorder abierto un par de minutos con OBS cerrado, mirando el panel.

**Esperado:** el cartel se queda quieto. No tiene que redibujarse ni titilar cada pocos
segundos.

---

## 2. Cancelar durante la cuenta regresiva, confirmando tarde

**Qué estaba mal:** el cartel de confirmación no frenaba la cuenta regresiva — seguía
corriendo por detrás. Si confirmabas justo cuando llegaba a cero, el Recorder volvía al
inicio como si hubiera cancelado bien, **pero OBS se quedaba grabando solo**.

### 2.1 El caso reportado — el importante

1. Apretar **Iniciar grabación**.
2. Apretar **Cancelar** cuando queden **1 o 2 segundos**.
3. Confirmar apenas aparece el cartel.

**Esperado:**
- La cuenta regresiva **se congela** mientras el cartel está abierto. No sigue bajando.
- Al confirmar, se vuelve al inicio y **OBS no queda grabando**. Verificarlo en la ventana
  de OBS: el botón tiene que decir "Iniciar grabación", no "Detener".
- No queda carpeta en `Documentos\Pleiada Recordings`.

Probarlo varias veces con distintos tiempos, incluso demorando a propósito la respuesta del
cartel 10 o 15 segundos.

### 2.2 Decir que no y que la cuenta siga

1. Apretar Iniciar, y **Cancelar** en el segundo 5.
2. Esperar unos segundos con el cartel abierto y responder **No**.

**Esperado:** la cuenta regresiva **retoma desde donde estaba** (5) y la grabación arranca
normal al llegar a cero. Esta es la parte más fácil de romper al arreglar lo anterior.

### 2.3 El atajo de teclado con el cartel abierto

Con el cartel de cancelación abierto, apretar el **atajo de detener**.

**Esperado:** no aparece un segundo cartel encima del primero.

### 2.4 Cancelar ya grabando

Grabar 1 o 2 minutos de verdad y apretar **Cancelar**.

**Esperado:** sin cambios respecto de la 0.9.2 — pide confirmación, avisa que el video
queda en la carpeta de OBS, y se descarta la sesión. Este caso es el control.

---

## 3. Textos cortados en escala 125% y 150%

**Qué estaba mal:** en pantallas con escalado de Windows al 125% o 150%, la ventana quedaba
más corta de lo que necesitaba el contenido, y la fila **SESIÓN** y el link **Ver tutorial
de configuración** quedaban cortados o directamente afuera.

### 3.1 Al 125%

Configuración de Windows → Pantalla → Escala **125%**. **Cerrar y volver a abrir el
Recorder** (el tamaño se calcula al arrancar).

**Esperado:** se ve todo, hasta el link del tutorial abajo de todo. El panel de tips sigue
estando.

### 3.2 Al 150%

Lo mismo con escala **150%**.

**Esperado:** se ve todo el pie. **En pantallas de 1080 de alto, el panel de tips no
aparece** — es a propósito: a esa escala la ventana entera no entra en el monitor, y se
prioriza que el resto quede usable. En pantallas más altas (1440) los tips sí se ven.

### 3.3 Volver al 100%

Devolver la escala a 100% y reabrir.

**Esperado:** todo como siempre, con los tips.

Anotá siempre la **resolución y la escala** del monitor donde probaste, porque el
comportamiento esperado depende de las dos.

---

## 4. Panel de tips

Cambió respecto de la 0.9.2:

- El aviso de actividad que estaba suelto arriba del panel **ya no está**: ahora es parte
  del primer tip ("...salteálas). Períodos largos sin actividad de teclado o mouse van a
  ser rechazados").
- Se corrigió el espacio de más que tenían los renglones de **Ultrawide** y **Muteá tu
  micrófono**.

**Esperado:** los ocho tips arrancan todos a la misma altura, sin uno corrido respecto de
los otros, y no hay texto cortado al costado.

---

## Qué no hace falta volver a probar

La detección automática, la elección de orden, la subida y el rechazo de sesiones sin
teclado ni mouse no se tocaron. Tampoco cambió nada de lo que ya se validó en la 0.9.2
(títulos fuera del catálogo, acentos).

**Sí conviene repasar** el caso de la 0.9.2 que quedó sin confirmar: que **no se pueda
grabar con el título cerrado**, y sobre todo que jugando normal 10 minutos el Recorder
nunca diga que el título no está corriendo.

---

## Cómo reportar

Un ticket por caso, indicando el número de la sección de esta guía, el título usado y qué
pasó. Para la sección 3, agregar resolución y escala del monitor.
