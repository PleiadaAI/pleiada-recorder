# Guía de QA — Gameplay Recorder v0.9.4

Build: `PleiadaRecorder_Update.exe` · estampado 0.9.4

Tercera ronda. Corrige los tres bugs abiertos de la v0.9.3 (PLE-162, PLE-163, PLE-164) y
queda por confirmar el de escalado que ya venía arreglado (PLE-161).

---

## Antes de empezar

- Instalar el `.exe` y abrir el Recorder. **El encabezado tiene que decir v0.9.4.** Si dice
  otra versión, no se instaló lo que corresponde y el resto de la guía no aplica.
- En OBS, la fuente tiene que ser **Captura de Videojuego (Game Capture)** en modo
  **ventana específica**, apuntada a la ventana del título.
- Hace falta estar logueado y con conexión.
- **Si algo queda pegado o no responde**, antes de cerrar la app copiá el archivo
  `%APPDATA%\Pleiada\logs\crash.log` y adjuntalo al ticket. Si ese archivo no existe, decilo
  en el ticket: también es un dato.

---

## 1. Cambiar de sección mientras busca el título (PLE-162)

**Qué estaba mal:** si salías de la pantalla principal justo mientras el Recorder estaba
buscando el título, al volver no encontraba nada nunca más. La búsqueda quedaba dando
vueltas y la única salida era cerrar la app y abrirla de nuevo.

### 1.1 El caso reportado

1. Abrir el Recorder en la pantalla principal, con el título abierto y OBS corriendo.
2. **Sin esperar** a que aparezca el título detectado, entrar a **Mis grabaciones**.
3. Volver al inicio y, otra vez sin esperar, entrar a **Ajustes**.
4. Volver al inicio y ahora sí esperar.

**Esperado:** en pocos segundos el panel muestra el título y el botón Iniciar se habilita.
**Sin cerrar la app.** Repetir el ida y vuelta varias veces seguidas, cuanto más rápido
mejor: el bug aparecía justo cuando se cambiaba de pantalla en el peor momento.

### 1.2 La misma prueba con OBS cerrado

1. Cerrar OBS. El panel dice que OBS no está corriendo.
2. Hacer el mismo ida y vuelta rápido entre inicio, Mis grabaciones y Ajustes.
3. Abrir OBS.

**Esperado:** el panel se recupera solo y vuelve a buscar el título.

### 1.3 Que no quede nada a medias

Después de los dos casos de arriba, iniciar una grabación corta (1–2 minutos) y detenerla.

**Esperado:** graba y detiene normal, y al terminar el panel vuelve a detectar el título.

---

## 2. Títulos que abrevian su nombre (PLE-163)

**Qué estaba mal:** hay títulos cuya ventana no muestra el nombre completo sino una
abreviatura. *Metro: Last Light* aparece como **Metro LL**, y con eso el Recorder no lo
reconocía: decía "No pudimos identificar el título" con el juego abierto y no dejaba grabar.

**Qué hace ahora:** cuando el nombre viene abreviado, el Recorder muestra los títulos del
catálogo que coinciden y **te pregunta cuál estás jugando**. No elige solo a propósito:
*Metro LL* puede ser *Metro: Last Light* o *Metro: Last Light Redux*, que son dos juegos
distintos, y la sesión tiene que quedar etiquetada con el que realmente jugaste.

### 2.1 El caso reportado

1. Abrir **Metro: Last Light Complete Edition** (el de Steam, el que ejecuta `Metro LL.exe`).
2. Apuntar la fuente de OBS a su ventana y abrir el Recorder.

**Esperado:** el panel pregunta *¿Cuál estás jugando?* y ofrece **Metro: Last Light** y
**Metro: Last Light Redux**. Al elegir uno, el panel queda en verde con ese nombre y el
botón Iniciar se habilita.

3. Grabar una sesión corta y subirla.

**Esperado:** la grabación queda asociada al título elegido, no al otro.

### 2.2 Que no pregunte de más

Con cualquier otro título del catálogo que ya venía funcionando (por ejemplo Cult of the
Lamb o Left 4 Dead 2), abrir y detectar como siempre.

**Esperado:** lo reconoce directo, en verde, **sin** preguntar nada. Si algún título que
antes se detectaba solo ahora abre la pregunta, es un bug: anotá cuál.

---

## 3. Sesión vencida (PLE-164)

**Qué estaba mal:** cuando la sesión de tu usuario vencía, el Recorder no lo decía. Mostraba
un aviso amarillo de "No pudimos verificar el título" con el motivo abajo y un Reintentar
que fallaba siempre. La única forma de salir era darse cuenta solo y desloguearse a mano
desde Ajustes.

**Qué hace ahora:** si la sesión venció, la app te lo dice apenas abre y te ofrece volver a
entrar con tu email.

### 3.1 Simular la sesión vencida

1. Cerrar el Recorder.
2. Abrir `%APPDATA%\Pleiada\auth.json` con el Bloc de notas. Es una línea con tu email y un
   token largo.
3. Cambiar **unos cuantos caracteres del token** (no del email) y guardar. Con eso el token
   deja de ser válido, igual que si hubiera vencido.
4. Abrir el Recorder.

**Esperado:** aparece la pantalla **"Tu sesión venció."** con el botón **Iniciar sesión**.
NO tiene que aparecer el cartel de "No pudimos verificar el título".

5. Tocar **Iniciar sesión**, entrar con el email y el código.

**Esperado:** vuelve a la pantalla principal y detecta el título normalmente.

### 3.2 Después de actualizar

Repetir el update desde una versión anterior con el Updater, como en el reporte original.

**Esperado:** después de actualizar, o detecta el título normalmente, o —si la sesión
venció— muestra la pantalla de "Tu sesión venció". Nunca las dos cosas mezcladas.

### 3.3 El ícono, cuando el error es otro

1. Desconectar internet (o cortar el WiFi) con el Recorder abierto en la pantalla principal.

**Esperado:** el cartel "No pudimos verificar el título" ahora aparece con una **✕ roja**
—no con el triángulo amarillo— y con el botón **Reintentar**. Al volver la conexión,
Reintentar tiene que resolver el título.

---

## 4. Textos en escala 125% y 150% (PLE-161)

Ya venía corregido en la build anterior y falta confirmarlo.

1. En Windows, **Configuración → Sistema → Pantalla → Escala**, poner **125%**.
2. Cerrar y abrir el Recorder.
3. Repetir con **150%**.

**Esperado:** en las dos escalas se leen completos el bloque de **Sesión** y el enlace de
**Ver tutorial de configuración** en la parte de abajo, sin texto cortado ni fuera de la
ventana. El panel de TIPS puede no aparecer en las escalas grandes: eso es a propósito, para
que el pie entre.

---

## Qué reportar

Para cada caso que falle: qué versión decía el encabezado, qué título y qué escala de
pantalla, el video o la captura, y el `crash.log` si existe.
