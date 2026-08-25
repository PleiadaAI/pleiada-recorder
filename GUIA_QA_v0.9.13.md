# Guía de QA — v0.9.13

Reemplaza a las guías anteriores: **el encabezado del Recorder tiene que decir v0.9.13**.
Instalar el build nuevo antes de empezar.

---

## Si ya probaste un build anterior, leé esto primero

Los builds v0.9.11 y v0.9.12 están descartados. Este agrega **un arreglo** sobre el último:

| Lo que pasaba | Qué se arregló | Dónde se prueba |
|---|---|---|
| Si actualizabas con OBS abierto, la mejora de calidad no llegaba: OBS seguía grabando con la configuración vieja | El Recorder lo detecta y reinicia OBS una vez, antes de la primera grabación | **A.0 — hay que hacerlo ANTES que todo lo demás** |

**Lo que NO cambió** es la calidad de grabación ni los arreglos del build anterior. Si ya
validaste A.1 a A.7 en tu máquina, alcanza con una pasada rápida — salvo **A.0, que es nuevo
y hay que hacerlo sí o sí**, y **la parte C**, que sigue faltando de AMD e Intel.

> ⚠️ **A.0 sólo se puede probar UNA vez por máquina**, porque depende de cómo instalás. Si ya
> instalaste este build, no lo podés reproducir: avisá y seguí con el resto.

---

## Antes de arrancar

- ⚠️ **Esta ronda necesita variedad de máquinas más que muchos casos por máquina.** El cambio
  se comporta distinto según la placa de video, y de algunas familias todavía no tenemos
  ninguna medición. **A.0 y A.6 los prueban todos; la parte C sólo AMD e Intel.**
- ⚠️ **La primera vez que grabes, OBS se va a cerrar y volver a abrir solo.** Es esperado y
  está explicado en A.3. Que pase **una vez** es correcto; que pase **siempre**, no.

---

## Qué cambió respecto de la 0.9.10

Hasta la v0.9.10 el Recorder le pedía a OBS mucho menos espacio del que necesita una
grabación de 1080p a 60 fps, y además lo repartía de forma pareja segundo a segundo. El
gameplay no es parejo: una escena quieta no necesita casi nada y una con la cámara girando
entre vegetación necesita mucho. Sobraba en los momentos tranquilos y faltaba justo en los de
acción — que eran los que peor se veían.

Ahora el Recorder le pide a OBS **calidad fija con un tope de tamaño**. Las grabaciones nuevas
pesan bastante más que las viejas.

Además, la configuración se aplica **sin importar cómo tengas OBS configurado**. Antes, quien
tuviera OBS en modo Avanzado no recibía nada de esto.

---

## Parte A — Lo que hay que verificar en todas las máquinas

### A.0 · Actualizar con OBS abierto 🔴 **hacer esto ANTES de instalar**

Este es el caso nuevo del build, y **se prueba en el momento de instalar**. Si ya lo
instalaste, saltealo y avisá.

1. **Con el build anterior todavía instalado**, abrir OBS y dejarlo abierto.
2. **Sin cerrar OBS**, instalar este build.
3. Abrir el Recorder y grabar una sesión de **2 o 3 minutos**.

**Esperado:** antes de arrancar la grabación, **OBS se cierra y se vuelve a abrir solo, una
vez**. Puede tardar unos segundos de más. Después la sesión arranca normal.

4. Mirar el tamaño del .mp4 y el `bitrate_kbps` de `session_metadata.json`.

**Esperado:** el mismo tamaño que en A.1 (~60 MB por minuto), y `bitrate_kbps` por encima de
4.000.

> 🔴 **Si la grabación sale mucho más chica de lo esperado, o `bitrate_bajo` dice `true`, es
> el bug reabierto.** Es exactamente lo que este build viene a arreglar: anotarlo con el
> tamaño y el `bitrate_kbps`.

5. Grabar **otra sesión más**, seguida.

**Esperado:** esta vez OBS **no** se reinicia. El reinicio es una sola vez.

> 🔴 Si OBS se reinicia también en la segunda y la tercera, es otro bug: anotarlo.

### A.1 · Las grabaciones pesan alrededor de 3× más que antes 🔴

Es el chequeo más rápido para confirmar que el cambio llegó a esa máquina.

1. Grabar una sesión de **10 minutos** con cualquier título, jugando normal.
2. Mirar el tamaño del .mp4 en
   `Documentos\Pleiada Recordings\<título>_<fecha> recording\`

**Esperado: alrededor de 600 MB** para 10 minutos, y **parecido en todos los títulos**.

| Duración | Tamaño esperado |
|---|---|
| 5 min | ~300 MB |
| 10 min | ~600 MB |
| 30 min | ~1,7 GB |
| 60 min | ~3,4 GB |

> 🔴 **Si pesa alrededor de un tercio de eso** —unos 200 MB para 10 minutos— el cambio no se
> aplicó en esa máquina. Es el hallazgo más importante de la ronda: anotarlo y seguir con
> A.3 y la parte C.

> **El tamaño NO varía mucho entre títulos, y está bien que así sea.** Medido sobre cinco
> juegos de cargas visuales muy distintas: la diferencia fue de menos del 4%. La calidad se
> reparte mejor *dentro* de cada grabación —los momentos de acción reciben más que los
> quietos— pero el peso total por hora es parejo y predecible. Que dos títulos muy distintos
> pesen casi igual **no es un bug**.

### A.2 · El formato del archivo 🔴

1. Sobre el .mp4 de cualquier sesión: clic derecho → **Propiedades** → pestaña **Detalles**.
2. Mirar **Ancho de fotograma**, **Alto de fotograma** y **Velocidad de datos**.

**Esperado:** 1920 × 1080. Y en `session_metadata.json` (abrir con el Bloc de notas, buscar
con Ctrl+B) el campo **`bitrate_kbps`** tiene que estar **por encima de 4.000**, y
**`bitrate_bajo`** tiene que decir **`false`**.

> 🔴 Si `bitrate_bajo` dice **`true`**, anotarlo junto con el valor de `bitrate_kbps` y la
> placa de video. Quiere decir que en esa máquina el cambio no aplicó.

### A.3 · OBS se reinicia UNA vez, no siempre 🔴

1. Con OBS cerrado, abrir el Recorder y grabar una sesión corta. Cancelarla o cortarla.
2. **Repetir 3 o 4 veces seguidas** sin cerrar nada.

**Esperado:** en el **primer** intento OBS puede cerrarse y volver a abrirse solo, o tardar
unos segundos de más. **A partir del segundo, arranca directo y rápido.**

> 🔴 **Si OBS se reinicia en TODAS las grabaciones, es un bug y es serio.** Anotar en cuántos
> intentos seguidos pasó.

> 🔴 **Si después de un reinicio OBS se queda mostrando una ventana de error** y el Recorder
> se queda esperando, anotarlo con captura de pantalla. Es otro bug distinto y también
> importante.

### A.4 · Se ve mejor en las escenas de acción 🟡

1. Abrir el .mp4 del título con movimiento y buscar un momento con la cámara girando y
   vegetación, pasto o texturas finas.
2. Pausar y mirar en pantalla completa.

**Esperado:** se distinguen hojas, pasto y texturas **también mientras la cámara se mueve**.
Lo que se empastaba antes eran justamente los momentos de movimiento, mientras que los
quietos se veían pasables. Esa diferencia es la que tiene que haber desaparecido.

### A.5 · Vuelve la detección de pantalla negra 🟡

1. Empezar a grabar con un juego abierto.
2. **Cerrar el juego** dejando la grabación corriendo, y seguir moviendo el mouse y tecleando
   sobre el escritorio unos 3 o 4 minutos.
3. Detener y dejar que el Recorder verifique la sesión.

**Esperado:** el Recorder **rechaza** la sesión. Antes esta verificación no saltaba nunca.

> 🟡 Si la da por buena, anotarlo con cuánto tiempo estuvo la pantalla sin el juego.

### A.6 · Dos clicks seguidos en "Iniciar grabación" 🔴

Es el bug que reportaron. Se disparaba justo después de terminar una sesión, cuando la
pantalla recién se rearma y el botón vuelve a estar disponible.

1. Grabar una sesión corta y **detenerla** normalmente.
2. Apenas vuelva la pantalla principal, apretar **"Iniciar grabación" haciendo doble click**
   (dos clicks rápidos, a propósito).
3. Dejar correr el countdown hasta que arranque.

**Esperado:** arranca **una sola** grabación, normal. El contador de sesión corre y OBS muestra
que está grabando.

4. Detenerla y **repetir el doble click 3 o 4 veces más**, siempre apenas termina la anterior.

**Esperado:** siempre una sola grabación, y siempre queda subible.

> 🔴 **Si en algún intento sale el cartel "OBS ya está grabando" y la sesión queda en "No
> iniciada" mientras OBS sigue con el punto rojo, es el bug reabierto.** Anotar en qué intento
> pasó y mandar el archivo de log (ver abajo). Ese es el estado exacto que reportaron.

> 🔴 **Y si en vez de eso arrancan DOS grabaciones, o el video queda desfasado contra los
> datos de teclado y mouse**, también anotarlo: es la otra mitad del mismo problema.

5. Lo mismo pero con el **atajo de teclado** en vez del botón, apretándolo dos veces rápido.

### A.7 · Acceso directo en una PC sin Python 🟡 (sólo si tenés cómo probarlo)

Este caso **sólo se reproduce en una máquina donde Python no esté instalado**. Si tu PC ya lo
tiene, saltealo — no sirve de nada probarlo ahí.

1. En una PC limpia (o después de desinstalar Python desde "Agregar o quitar programas"),
   instalar el Recorder con el instalador **completo**.
2. Cuando termine, **abrir el acceso directo del escritorio**.

**Esperado:** abre el Recorder, normal.

> 🟡 Si sale **"Falta el acceso directo — Windows está buscando pythonw.exe"**, es el bug
> reabierto. Anotarlo con captura.

---

## Parte B — Que no se haya roto nada

Una pasada completa alcanza, por máquina.

1. **Grabar y subir una sesión entera**, de punta a punta.
   **Esperado:** el verificador la da por buena y la subida termina bien.
2. **Una sesión corta** (menos de 30 segundos) → la rechaza, igual que antes.
3. **Una sesión con teclado y mouse quietos** un buen rato → la rechaza por inactividad.
4. **Mis grabaciones**: entrar y volver al inicio un par de veces, sin errores.
5. **Que el audio esté**: abrir el .mp4 y confirmar que se escucha el juego.
6. **Que OBS te quede usable después.** Abrir OBS y mirar que tus escenas y fuentes sigan
   ahí. El Recorder toca la configuración de **grabación**, no tus escenas.

---

## Parte C — Calibración por placa de video ⭐ **el dato que nos falta**

El Recorder elige cómo grabar según la placa de video que tengas. Para las placas **NVIDIA**
y para las máquinas **sin placa dedicada** ya está medido. Para **AMD** y para **gráficos
integrados Intel** todavía no, y necesitamos los números reales.

**Si tu máquina es AMD o Intel, esta parte es la que no nos podemos perder.**

1. Anotar **la placa de video exacta**. Se ve en: clic derecho en el escritorio →
   **Configuración de pantalla** → **Configuración de pantalla avanzada**.
2. Grabar **una sesión de exactamente 10 minutos** con un título **de mucho movimiento**.
3. Anotar:
   - **el tamaño del .mp4 en MB**
   - el valor de **`bitrate_kbps`** de `session_metadata.json`
   - si al mirarlo **se ve bien en las escenas de movimiento** o si se empasta
4. Repetir con **un título quieto**, mismos 10 minutos, y anotar lo mismo.

> Con AMD o Intel puede pasar que el archivo salga **mucho** más pesado o mucho más liviano
> de lo esperado (referencia NVIDIA: ~600 MB para 10 minutos de movimiento). **Las dos cosas
> son un hallazgo útil, no una falla.** Es exactamente el dato que falta.

---

## Qué reportar

Por cada máquina:

- **Placa de video** (marca y modelo exactos).
- **A.0** — si OBS se reinició solo al instalar con OBS abierto, y el `bitrate_kbps` de
  esa primera grabación. Si no pudiste probarlo, decilo.
- **A.1** — duración de la sesión y tamaño del .mp4 en MB.
- **A.2** — `bitrate_kbps` y `bitrate_bajo`.
- **A.3** — cuántas veces se reinició OBS en 4 grabaciones seguidas.
- **A.4** — si las escenas de movimiento se ven bien.
- **A.5** — si rechazó la sesión con la pantalla sin juego.
- **A.6** — cuántos dobles clicks probaste y si alguno falló. **Siempre reportar esto**,
  aunque haya salido todo bien.
- **A.7** — sólo si pudiste probarlo en una PC sin Python.
- **Parte B** — cualquier cosa que se comporte distinto que antes.
- **Parte C** — si la máquina es AMD o Intel, los cuatro datos del punto 3 y 4.

Si algo se cierra solo o tira un error, mandar los archivos de
`C:\Users\<usuario>\Documents\Pleiada Logs\` (`crash.log` y `faulthandler.log`).

---

## Lo que ya sabemos y no hace falta reportar

- **Que OBS se reinicie la primera vez.** Es parte del cambio. Solo reportarlo si pasa
  siempre (A.3).
- **Que dos títulos muy distintos pesen casi lo mismo.** Está medido y es el comportamiento
  esperado (ver A.1).
- **Que las grabaciones pesen bastante más que antes** y tarden más en subir.
- **Que OBS ahora aparezca en modo "Avanzado"** si vas a mirar sus ajustes. Es a propósito:
  es el único modo donde se puede pedir esta calidad.
- **Las grabaciones viejas no cambian.** Esto aplica solo a las sesiones nuevas.
