# Guía de QA — cierre de la v0.9.4

Dos partes: los dos casos que quedaron abiertos anoche, y un smoke de punta a punta antes de
salir a producción.

**Versión:** el encabezado del Recorder tiene que decir **v0.9.4**. Los dos fixes de esta
ronda son del lado del servidor: ya están activos y no hay nada que instalar de nuevo.

**Un detalle de tiempos que aplica a toda la guía:** cuando abren un título que el Recorder no
conocía, puede tardar hasta 10 minutos en aparecer la orden de destino, porque el catálogo se
refresca en ese intervalo. Si al primer intento sale como grabación libre, esperen un rato y
vuelvan a entrar a la pantalla principal antes de anotarlo como falla.

---

## Parte A — Los dos casos que reabrieron

### A.1 · Team Fortress 2 (PLE-163)

**Qué estaba mal:** TF2 quedaba con el cartel de título no disponible y no se podía grabar.
El Recorder lo identificaba bien; lo frenaba una regla interna nuestra que estaba aplicada de
más.

1. Abrir Team Fortress 2 con OBS apuntado a su ventana.

**Esperado:** el panel muestra **Team Fortress 2** en verde y el botón Iniciar grabación queda
habilitado.

2. Grabar una sesión corta y detenerla.

**Esperado:** graba y detiene normal.

> ⚠️ **TF2 queda como grabación libre a propósito: NO se va a poder subir, y eso no es un bug.**
> El panel va a decir que ninguna orden abierta está buscando ese tipo de título. Lo que se
> prueba acá es que **se puede grabar**, no que se pueda subir.

### A.2 · Metro: Last Light (PLE-163, el caso original)

Si alguno lo tiene instalado: abrir **Metro: Last Light** (el de Steam, el que ejecuta
`Metro LL.exe`).

**Esperado:** el panel pregunta *¿Cuál estás jugando?* con dos opciones — *Metro: Last Light* y
*Metro: Last Light Redux*. Al elegir una, queda en verde con ese nombre.

Si nadie lo tiene, salteénlo y anótenlo como no probado.

### A.3 · Sylvio (PLE-165)

**Importante:** la grabación de Sylvio que hicieron anoche **no se puede recuperar**. Quedó
guardada como grabación libre y no se reasigna sola a una orden. Hay que **grabar una sesión
nueva**.

1. Abrir Sylvio con OBS apuntado a su ventana.

**Esperado:** el panel muestra **Sylvio** en verde y debajo aparece **ORDEN DE DESTINO** con la
orden de prueba seleccionada.

2. Grabar una sesión corta, detenerla y **subirla**.

**Esperado:** la subida termina bien y la sesión queda asociada a la orden de prueba.

### A.4 · Raft (PLE-165)

1. Abrir Raft con OBS apuntado a su ventana.

**Esperado:** igual que Sylvio — título en verde y **ORDEN DE DESTINO** con la orden de prueba.
Después, grabar corto y subir.

---

## Parte B — Smoke completo antes de producción

Recorrido de punta a punta. La idea es confirmar que nada de lo arreglado en las tres rondas se
rompió. Si algo falla, **anoten el número del paso**.

| # | Qué hacer | Qué tiene que pasar |
|---|---|---|
| 1 | Actualizar desde una versión anterior con el Updater | Abre en v0.9.4, con los acentos y los íconos bien |
| 2 | Abrir la app ya logueados | Entra directo a la pantalla principal, sin errores |
| 3 | Con el título abierto y OBS corriendo, esperar la detección | Título en verde, con género · perspectiva · modo |
| 4 | Entrar a **Mis grabaciones** y volver al inicio, rápido, 3 o 4 veces seguidas, sin esperar a que detecte | Siempre vuelve a detectar el título. **Nunca hay que cerrar la app** |
| 5 | Lo mismo entrando a **Ajustes** | Igual que el punto 4 |
| 6 | Cerrar OBS y volver a abrirlo, sin tocar el Recorder | El panel se recupera solo |
| 7 | Poner a grabar a OBS por su cuenta y después detenerlo desde OBS | El panel se recupera solo |
| 8 | En OBS, dejar una fuente de Captura de Pantalla y después volver a Captura de Videojuego | El panel se recupera solo |
| 9 | Cerrar el título (sin cerrar OBS) | El panel avisa que ese título no está corriendo |
| 10 | Iniciar grabación y **cancelar durante la cuenta regresiva** | Pide confirmación, no corre la verificación, y la carpeta de la sesión no queda en Documentos |
| 11 | Iniciar grabación, dejar que arranque y **cancelar ya grabando** | Corta también en OBS: OBS **no** queda grabando por detrás |
| 12 | Grabar una sesión de 2–3 minutos y detenerla | Termina, verifica y aparece en Mis grabaciones |
| 13 | Subir esa sesión a la orden de prueba | Sube completa y queda registrada |
| 14 | Volver a intentar subir la misma sesión | Avisa que ya estaba subida; no la duplica |
| 15 | Poner Windows en escala **125%** y abrir la app | Se leen completos el bloque de Sesión y el link del tutorial |
| 16 | Lo mismo en **150%** | Igual que el 15 |
| 17 | Un título que no esté en el catálogo y que la orden no acepte | Se puede grabar igual, avisando que ninguna orden lo está buscando |
| 18 | Cerrar sesión desde Ajustes y volver a entrar con el código | Vuelve a la pantalla principal y detecta normal |

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
`%APPDATA%\Pleiada\logs\crash.log` y adjúntenlo — si ese archivo no existe, díganlo igual, que
también es un dato.
