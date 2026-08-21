# Guía de QA — Gameplay Recorder v0.9.2

Build: `PleiadaRecorder_Update.exe` · estampado 0.9.2

Esta versión no trae funciones nuevas: corrige tres bugs reportados en la 0.9.1, arregla
los textos de la app y suma un panel de tips en la pantalla principal.

Un cambio de vocabulario que se ve en toda la pantalla principal: donde antes decía
**juego** ahora dice **título**. "TÍTULO DETECTADO", "Esperando el título". Es
intencional.

---

## Antes de empezar

- Instalar el `.exe` y abrir el Recorder. **El encabezado tiene que decir v0.9.2.** Si dice
  otra versión, no se instaló lo que corresponde y el resto de la guía no aplica.
- En OBS, la fuente tiene que ser **Captura de Videojuego (Game Capture)** en modo
  **ventana específica**, apuntada a la ventana del título. En modo "cualquier aplicación
  en pantalla completa" el Recorder no puede leer el ejecutable: eso es esperado.
- Hace falta estar logueado y con conexión.

---

## 1. Cancelar durante la cuenta regresiva

**Qué estaba mal:** cancelar durante los 10 segundos previos hacía lo mismo que Detener —
no preguntaba nada, corría la verificación de archivos y la carpeta de la sesión quedaba
en `Documentos\Pleiada Recordings`.

### 1.1 Cancelar con el botón

1. Con un título detectado, apretar **Iniciar grabación**.
2. Durante la cuenta regresiva, apretar **Cancelar**.

**Esperado:**
- Aparece un cartel de confirmación que dice que todavía no empezó a grabar y que no queda
  ningún archivo. **No menciona ningún video**, porque todavía no hay.
- Al confirmar: no corre ninguna verificación, no aparece la pantalla de análisis, y se
  vuelve al inicio.
- **La carpeta de la sesión desaparece de `Documentos\Pleiada Recordings`.** Conviene
  tener la carpeta abierta al lado para verlo: aparece al apretar Iniciar y se borra al
  cancelar.
- OBS no queda grabando.

### 1.2 Decir que no

Repetir 1.1 pero responder **No** en la confirmación.

**Esperado:** la cuenta regresiva sigue corriendo como si nada y la grabación arranca
normal al llegar a cero.

### 1.3 Cancelar con el atajo de teclado

Repetir 1.1 pero, en vez del botón, usar el **atajo de detener** durante la cuenta
regresiva.

**Esperado:** exactamente lo mismo que 1.1, incluida la confirmación. Antes de la cuenta
regresiva ese atajo cancela; una vez que la grabación arrancó, detiene normalmente.

### 1.4 Cerrar la app durante la cuenta regresiva

Apretar Iniciar y cerrar el Recorder con la X mientras corre la cuenta.

**Esperado:** cierra sin preguntar nada y **sin dejar la carpeta de la sesión**.

### 1.5 Que Detener siga funcionando igual

Grabar 2 o 3 minutos de verdad y apretar **Detener**.

**Esperado:** sin cambios respecto de la 0.9.1 — corre la verificación, se arma el
dataset y la sesión queda disponible para subir. Este caso es el control: si algo de acá
cambió, es un problema.

---

## 2. No se puede grabar sin el título abierto

**Qué estaba mal:** OBS recuerda la última ventana que se le configuró, aunque el título
esté cerrado. El Recorder lo tomaba como detectado y dejaba grabar sin el título abierto:
se grababa una pantalla sin nada.

### 2.1 El caso del bug

1. Abrir un título y apuntarle la fuente de OBS.
2. Esperar a que el Recorder lo detecte (panel en verde).
3. **Cerrar el título**, dejando OBS y el Recorder abiertos.

**Esperado:** en pocos segundos el panel vuelve solo a **"Esperando el título"**, con un
mensaje que nombra el ejecutable y aclara que no está corriendo. El botón **Iniciar
grabación se deshabilita**.

### 2.2 Que vuelva solo

Sin tocar nada en el Recorder, volver a abrir el mismo título.

**Esperado:** el panel vuelve a detectarlo solo, sin apretar nada y sin reiniciar la app.
El botón se habilita de nuevo.

### 2.3 Cerrarlo justo antes de empezar

1. Con el título detectado y el botón habilitado, cerrar el título.
2. Apretar **Iniciar grabación** enseguida, antes de que el panel se actualice.

**Esperado:** un cartel "Título no detectado" avisando que ya no está corriendo. **No
arranca ninguna grabación ni se crea carpeta.**

### 2.4 Que no bloquee de más — el caso importante

Jugar normal una sesión de 5 o 10 minutos, con el título abierto todo el tiempo.

**Esperado:** nada distinto de siempre. El panel no parpadea, no aparece ningún cartel y
la grabación no se interrumpe. **Si en algún momento dice que el título no está corriendo
mientras estás jugando, es un bug y hay que reportarlo con el nombre del título.** Es el
riesgo principal de este cambio.

Probarlo con un título que use launcher (Ubisoft, EA, Rockstar, Epic) suma, porque son los
casos donde el ejecutable que ve OBS puede no ser el mismo que arranca el launcher.

---

## 3. Títulos que no están en el catálogo

> **Antes de probar esta sección, confirmá con Martín que el cambio del lado del servidor
> ya está aplicado.** Es lo único de esta guía que no viaja dentro del instalador: si el
> servidor todavía no se actualizó, el comportamiento va a ser el viejo y no tiene sentido
> reportarlo.

**Qué estaba mal:** algunos títulos que no están en el catálogo quedaban en "No pudimos
identificar el título" y no se podían grabar, aunque son títulos reconocidos. Pasaba
cuando la ventana reporta el nombre **sin espacios** (`TravellersRest` en vez de
`Travellers Rest`).

### 3.1 El caso reportado

1. Abrir **Travellers Rest** y apuntarle la fuente de OBS.
2. Esperar a que el Recorder lo identifique.

**Esperado:** lo identifica como "Travellers Rest", con género, vista y modo. Como no está
en el catálogo, abajo dice que ninguna orden abierta está buscando este tipo de título —
**y el botón Iniciar grabación queda habilitado igual.** Se puede grabar y guardar.

### 3.2 Otros títulos con el nombre pegado

Si tenés a mano otro título cuya ventana muestre el nombre sin espacios, probalo también y
anotá cuál usaste.

### 3.3 Que siga frenando lo que no es un título

Apuntar la fuente de OBS a una ventana que no sea un juego: el explorador de archivos, un
navegador, Slack.

**Esperado:** sigue diciendo que no pudo identificar el título y **no** deja grabar. Este
filtro tiene que seguir funcionando.

---

## 4. Textos y acentos

**Qué estaba mal:** en la 0.9.1 todos los acentos de la app se veían rotos —
"Iniciar grabaciÃ³n", "SESIÃ"N MÃX".

**Esperado:** recorrer las pantallas (principal, ajustes, grabación, mis grabaciones,
cancelación) y que **todos los textos se lean bien**: grabación, sesión, título, período,
válidas, configuración. Cualquier cosa que se vea como `Ã` o `Â` es un bug: anotar en qué
pantalla apareció.

---

## 5. Tips en la pantalla principal

Nuevo panel entre el aviso de actividad y el botón de grabar, con ocho recomendaciones de
calidad.

**Esperado:**
- Se lee completo, sin texto cortado al costado.
- **Debajo del panel siguen visibles el botón Iniciar grabación, "Mis grabaciones", la
  fila SESIÓN y el link del tutorial.** Si algo de eso quedó fuera de la ventana, es un
  bug: la ventana no se puede agrandar ni tiene scroll.
- Los iconitos se ven en blanco y negro, no a color. Es así a propósito.
- Verificarlo también con la pantalla en escala 125% y 150% de Windows, que es donde el
  texto ocupa más y algo puede quedar afuera.

---

## Qué no hace falta volver a probar

La detección automática, la elección de orden, la subida y el rechazo de sesiones sin
teclado ni mouse no se tocaron en esta versión. Si algo de eso falla, es un hallazgo
nuevo, no una regresión de estos fixes.

---

## Cómo reportar

Un ticket por caso, indicando el número de la sección de esta guía, el título usado y qué
pasó. Para los casos de la sección 2, agregar si el título usa launcher y cuál.
