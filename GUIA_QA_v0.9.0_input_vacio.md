# Guía de QA — Gameplay Recorder v0.9.0: sesiones sin input

18/08/2026

Esta guía cubre **un solo cambio** de la v0.9.0: el Recorder ahora detecta y rechaza
las sesiones donde no quedó registrado lo que hizo el jugador. Explica qué pasaba,
qué cambió y cómo probar cada cosa.

---

## Qué pasaba

Aparecían sesiones con el video perfecto —una hora de gameplay, imagen impecable— y
los archivos `key_log.csv` y `mouse_delta_log.csv` **vacíos**: sólo la cabecera y las
dos marcas de inicio y fin, cero eventos. Es la peor falla posible para un dataset de
gameplay: el cliente recibe un video del que no se puede aprender nada, porque no
está registrado lo que el jugador apretó.

Lo grave no es que pasara, sino que **ninguna verificación lo detectaba**. El chequeo
de inactividad mide los *huecos* entre eventos y necesita al menos dos eventos para
medir un hueco. Con los archivos vacíos no podía medir nada, y "no pude medir" se
trataba como "todo bien". La sesión pasaba el check del Recorder, pasaba el Synch
Checker con un cartel amarillo de "no se pudo evaluar la actividad", se subía, y
llegaba al cliente.

Dos causas distintas terminan en el mismo archivo vacío:

- **La captura se bloqueó.** El jugador jugó normalmente pero los eventos no
  llegaron al log. Pasa cuando el juego corre como administrador, cuando su
  anticheat bloquea la captura, o cuando el filtro interno que decide "esto es el
  juego, esto no" apunta al programa equivocado.
- **No hubo teclado ni mouse.** O se jugó con joystick —que todavía no registramos—
  o directamente no se jugó.

Se ven igual en los archivos y se resuelven distinto, así que el Recorder ahora las
separa y le dice cosas distintas al usuario.

---

## Qué cambió

**1. El Recorder rechaza la sesión antes de subirla.** En vez de mirar huecos, ahora
mira volumen: si en toda la sesión no hay eventos de teclado, botones ni movimiento
de mouse, no se sube.

**2. El Synch Checker la marca en rojo.** Donde antes decía "No se pudo evaluar la
actividad de input" en amarillo y te dejaba enviar igual, ahora dice **SESIÓN NO APTA
PARA ENVIAR** y explica cuál de las dos causas fue.

**3. El logger se auto-corrige.** A los 15 segundos de empezar, y después cada 15
segundos durante los primeros 5 minutos, el Recorder chequea si está capturando. Si
detecta que el cursor se mueve pero no está registrando nada, corrige solo el filtro
y sigue grabando. En el peor caso se pierden los primeros 15 segundos en vez de la
sesión entera.

---

## Cómo probarlo

Antes de nada: abrí el Recorder y confirmá que el encabezado dice **v0.9.0**. Si dice
otra cosa, no instalaste lo que creés y el resto no vale.

### 1. Una sesión normal tiene que seguir pasando

Es la prueba más importante de todas: el cambio **no puede** empezar a rechazar
sesiones buenas.

1. Grabá 2-3 minutos de cualquier juego con teclado y mouse, jugando normal.
2. Detené la grabación.

**Esperado:** la sesión pasa el check como siempre y se puede enviar. Ningún cartel
nuevo, ninguna advertencia.

Repetilo con **tres juegos distintos**, y que uno sea de los que casi no usan el
mouse (un juego de plataformas, por ejemplo) y otro de los que casi no usan el
teclado (algo de estrategia o point-and-click). Los dos tienen que pasar: que falte
uno de los dos dispositivos es normal, lo que no es normal es que falten los dos.

### 2. Una sesión sin tocar nada tiene que rechazarse

1. Empezá una grabación con el juego abierto y en primer plano.
2. **No toques el teclado ni el mouse durante 2 minutos.** Dejá la mano quieta.
3. Detené la grabación.

**Esperado:** el Recorder rechaza la sesión con un cartel que dice que no hay
actividad de teclado ni de mouse, y que si jugaste con joystick todavía no podemos
registrarlo.

> Ojo: para detener la grabación vas a tener que usar el atajo o el mouse. Está bien:
> los atajos del Recorder no cuentan como input de gameplay y un par de eventos
> sueltos siguen estando por debajo del corte.

### 3. Si tenés joystick, probalo

1. Grabá 2-3 minutos de un juego **jugando sólo con joystick**, sin tocar teclado ni
   mouse.
2. Detené la grabación.

**Esperado:** rechazada, con el mensaje que menciona el joystick.

Esto es a propósito y es una decisión de producto, no un bug: hoy no capturamos
joystick, así que esa sesión no sirve como dataset y no queremos que el usuario la
suba creyendo que sí.

### 4. El Synch Checker tiene que decir lo mismo que el Recorder

Agarrá la carpeta de la sesión rechazada en el punto 2 y abrila con el Synch Checker.

**Esperado:** **SESIÓN NO APTA PARA ENVIAR** en rojo, con la misma explicación. Lo
que no puede pasar es que el Checker diga "lista para enviar" sobre una sesión que el
Recorder rechazó, o al revés.

### 5. La auto-corrección del filtro

Esta es la más difícil de provocar a mano, porque hay que hacer que el Recorder crea
que el juego es otro programa. Si podés reproducirla:

1. Configurá OBS para capturar el juego A.
2. Empezá la grabación y jugá al juego B durante 2 minutos, moviendo el mouse.

**Esperado:** los primeros segundos pueden salir sin registrar, pero de los 15
segundos en adelante la sesión captura normal y **no** se rechaza. Antes de este
cambio, esa sesión salía con los archivos completamente vacíos.

Si no llegás a montar el escenario, decilo y lo pruebo yo con el harness
automatizado; no te trabes con esta.

---

## Qué reportar

Por cada prueba: qué hiciste, qué esperabas y qué pasó. Si algo se rechazó, **mandá
la carpeta entera de la sesión** (los 4 CSV y el `session_metadata.json`, el MP4 no
hace falta) — con eso se reconstruye la decisión completa.

Lo que más me interesa que busques, en este orden:

1. **Falsos positivos.** Una sesión que jugaste de verdad y el Recorder rechazó. Es
   el riesgo real del cambio: rechazar de más le hace perder horas pagas a la gente.
2. **Mensajes que confunden.** Si el cartel te manda a buscar el problema donde no
   está, o si después de leerlo no sabés qué hacer, anotalo con tus palabras.
3. **Diferencias entre el Recorder y el Synch Checker** sobre la misma sesión.
