# Guía de QA — v0.9.6 (cierre antes de producción)

Reemplaza a las guías anteriores: **el encabezado del Recorder tiene que decir v0.9.6**.
Instalar el build nuevo antes de empezar.

**Un detalle de tiempos que aplica a toda la guía:** cuando abren un título que el Recorder no
conocía, puede tardar unos minutos en aparecer la orden de destino, porque el catálogo se
refresca cada tanto. Si al primer intento sale como grabación libre, esperen un rato y vuelvan
a entrar a la pantalla principal antes de anotarlo como falla.

---

## Parte A — Lo nuevo de esta versión

### A.1 · Detectó la orden pero no dejaba subir (PLE-168)

**Qué estaba mal:** con Resident Evil 3, la pantalla principal mostraba el título y la orden de
destino, pero al subir la grabación decía *"Resident Evil 3 no entra en ninguna de tus órdenes
activas"*. Las dos pantallas se contradecían.

1. Abrir **Resident Evil 3**, esperar la detección.

**Esperado:** título en verde y, debajo, **ORDEN DE DESTINO** con la orden de prueba.

2. Grabar 2–3 minutos, detener y **subir**.

**Esperado:** la pantalla de subida ofrece **la misma orden** que mostró la principal, y la
subida termina bien.

> La regla de oro de este caso: **si la primera pantalla te dejó grabar contra una orden, la de
> subida tiene que dejarte subir a esa misma orden.** Si alguna vez se contradicen, es un bug —
> anoten las dos capturas.

3. Repetir con **Sylvio**, que estaba en la misma situación.

### A.2 · Elegir en "¿Cuál estás jugando?" y grabar (PLE-167)

**Qué estaba mal:** al elegir uno de los títulos que ofrecía el Recorder, apretar Iniciar
grabación devolvía la pantalla al paso anterior y la grabación no arrancaba nunca.

1. Abrir **Metro: Last Light** (el que ejecuta `Metro LL.exe`).
2. El panel pregunta *¿Cuál estás jugando?*. Elegir una opción.
3. Apretar **Iniciar grabación**.

**Esperado:** arranca la cuenta regresiva, llega a cero y graba. La pantalla **no** vuelve atrás
en ningún momento — ni al apretar Iniciar, ni al terminar la cuenta.

4. Dejarlo grabar 2–3 minutos y detener.

**Esperado:** la sesión termina bien y no se cancela sola durante la grabación.

### A.3 · Counter-Strike (PLE-166)

**Qué estaba mal:** el Counter-Strike clásico se identificaba como *Counter-Strike 2*, y al
grabar la pantalla entraba en un ciclo entre "Esperando título" y los dos nombres.

1. Abrir **Counter-Strike 1.6**.

**Esperado:** el panel muestra **Counter-Strike** (el clásico), o pregunta cuál de los dos es.
Lo que **no** tiene que pasar es que diga *Counter-Strike 2* solo, sin preguntar.

2. Grabar corto y detener.

> Si tienen Counter-Strike 2 instalado, ábranlo también: tiene que seguir identificándose como
> **Counter-Strike 2**, directo y sin preguntar.

### A.4 · Team Fortress 2 (PLE-163)

1. Abrir TF2, grabar corto y detener.

**Esperado:** se identifica como **Team Fortress 2** y se puede grabar.

> ⚠️ **TF2 queda como grabación libre a propósito: NO se va a poder subir, y eso no es un bug.**
> Acá se prueba que se puede grabar, no que se pueda subir.

---

## Parte B — Smoke completo antes de producción

| # | Qué hacer | Qué tiene que pasar |
|---|---|---|
| 1 | Actualizar desde una versión anterior con el Updater | Abre en v0.9.6, con los acentos y los íconos bien |
| 2 | Abrir la app ya logueados | Entra directo a la pantalla principal, sin errores |
| 3 | Con el título abierto y OBS corriendo, esperar la detección | Título en verde, con género · perspectiva · modo |
| 4 | Entrar a **Mis grabaciones** y volver al inicio, rápido, 3 o 4 veces, sin esperar a que detecte | Siempre vuelve a detectar. **Nunca hay que cerrar la app** |
| 5 | Lo mismo entrando a **Ajustes** | Igual que el punto 4 |
| 6 | Cerrar OBS y volver a abrirlo, sin tocar el Recorder | El panel se recupera solo |
| 7 | Poner a grabar a OBS por su cuenta y después detenerlo desde OBS | El panel se recupera solo |
| 8 | En OBS, dejar una fuente de Captura de Pantalla y después volver a Captura de Videojuego | El panel se recupera solo |
| 9 | Cerrar el título (sin cerrar OBS) | El panel avisa que ese título no está corriendo |
| 10 | Iniciar grabación y **cancelar durante la cuenta regresiva** | Pide confirmación, no corre la verificación, y la carpeta no queda en Documentos |
| 11 | Iniciar grabación, dejar que arranque y **cancelar ya grabando** | Corta también en OBS: OBS **no** queda grabando por detrás |
| 12 | Grabar 2–3 minutos y detener | Termina, verifica y aparece en Mis grabaciones |
| 13 | Subir esa sesión a la orden de prueba | Sube completa y queda registrada |
| 14 | Volver a intentar subir la misma sesión | Avisa que ya estaba subida; no la duplica |
| 15 | **Durante una grabación, cambiar la fuente de OBS a otro juego** | La sesión se cancela sola y avisa por qué |
| 16 | Windows en escala **125%**, abrir la app | Se leen completos el bloque de Sesión y el link del tutorial |
| 17 | Lo mismo en **150%** | Igual que el 16 |
| 18 | Un título que no esté en el catálogo y que la orden no acepte | Se puede grabar igual, avisando que ninguna orden lo está buscando |
| 19 | Cerrar sesión desde Ajustes y volver a entrar con el código | Vuelve a la pantalla principal y detecta normal |

### Prueba de sesión vencida (una sola vez, en una máquina)

1. Cerrar el Recorder.
2. Abrir `%APPDATA%\Pleiada\auth.json` con el Bloc de notas y cambiar unos caracteres del token
   (no del email). Guardar.
3. Abrir el Recorder.

**Esperado:** aparece **"Tu sesión venció."** con el botón **Iniciar sesión**. No tiene que
aparecer ningún cartel de error de título.

---

## Qué reportar

Por cada falla: el número del paso o el caso de la Parte A, el título, la escala de pantalla, y
el video o la captura. Si la app se queda pegada o deja de responder, antes de cerrarla copien
`%APPDATA%\Pleiada\logs\crash.log` y adjúntenlo — si no existe, díganlo igual, que también es
un dato.
