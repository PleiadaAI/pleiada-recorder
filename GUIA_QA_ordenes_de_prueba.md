# Órdenes de prueba — guía para el equipo de QA

Para probar el Recorder hay que poder grabar y subir, y para eso hace falta una **orden**
que acepte el título que se está jugando. Cuando no hay ninguna orden real abierta que sirva,
les habilitamos una **orden de prueba**: funciona igual que una real, pero solo la ven ustedes.

Esto va a repetirse en cada ronda de QA, así que conviene tenerlo claro de entrada.

---

## Cómo funciona una orden de prueba

- **Aparece sola.** No hay que inscribirse ni pedir nada: al iniciar sesión en el Recorder con
  su email de testeo, la orden ya está disponible.
- **Solo la ven ustedes.** No figura en el listado público de órdenes del sitio. Ningún usuario
  del programa la ve ni puede subir a ella.
- **Las sesiones no se pagan y se borran al terminar la ronda.** Graben tranquilos: nada de lo
  que suban acá cuenta como aporte al programa ni queda en el dataset.
- **Se apaga cuando termina el QA.** De un día para el otro la orden puede desaparecer: es
  esperado, no es un error.

Si más adelante habilitamos otra orden de prueba, les va a aparecer sola la próxima vez que
inicien sesión. No hay ningún paso manual de su lado, nunca.

---

## Para arrancar

1. Abrir el Recorder e iniciar sesión con el email de testeo (`testhfrog+…@gmail.com`).
   El código de acceso llega por mail como siempre.
2. Abrir un título y apuntar la fuente de OBS a su ventana.
3. En el panel principal tiene que aparecer el título identificado y, debajo, la orden
   **“QA · Acción y aventura (orden de prueba)”** como destino.

**Si ya estaban logueados**, cerrar sesión y volver a entrar: la orden se habilita al iniciar
sesión, así que con una sesión vieja abierta puede no aparecer todavía.

---

## Qué títulos sirven

Cualquier título de **acción o aventura**: shooters, acción-aventura, RPG de acción, survival,
terror, sigilo, souls-like, plataformas, peleas, roguelikes. Entran unos 390 títulos del
catálogo, así que lo más probable es que lo que ya tengan instalado sirva.

**No entran** simulación, puzzle, carreras ni estrategia. Si abren uno de esos, el Recorder va
a identificar el título pero les va a avisar que ninguna orden lo está buscando: eso también es
un caso válido para probar (grabación libre).

Si abren un título que **no está en el catálogo** y es de acción o aventura, el Recorder lo va a
sumar solo. Es uno de los puntos a testear.

---

## Qué probar

Los dos documentos de siempre, sobre este mismo build:

- `GUIA_QA_v0.9.0.md` — identificación automática del título, elección de orden, grabación
  libre, cancelar grabación, formato de video.
- `GUIA_QA_v0.9.0_input_vacio.md` — rechazo de sesiones sin teclado ni mouse registrado.

La orden de prueba es lo que habilita el punto de **subir**: hasta ahora se podía grabar pero
no había a dónde subir, así que la mitad del circuito quedaba sin probar. Ahora se puede llegar
hasta el final: grabar, detener, subir, y ver la sesión reflejada.

---

## Dos cosas que NO son errores

- **En el sitio, la orden aparece en “Mis órdenes” pero no en el listado de órdenes
  disponibles.** Es a propósito: es una orden de prueba, no se publica.
- **Hay un tope de horas por persona.** Si les aparece un aviso de que alcanzaron el máximo de
  la orden, no es un bug: avisen y lo subimos.

---

## Qué reportar

Por cada problema: qué título, qué decía la ventana en OBS, qué ejecutable, y qué mostró el
Recorder. Si hubo un bloqueo inesperado, adjuntar `%TEMP%\pleiada_obs_debug.txt` y los logs de
`Documentos\Pleiada Logs`.

Un caso que vale la pena reportar aparte: **si la orden de prueba no aparece** después de cerrar
sesión y volver a entrar. Indicar con qué email entraron y si el título se identificó bien.
