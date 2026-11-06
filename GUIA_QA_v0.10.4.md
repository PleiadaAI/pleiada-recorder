# Guía de QA — Gameplay Recorder v0.10.4

Esta versión corrige los tickets reportados sobre la v0.10.2 y el feedback de la ronda de la v0.10.3.
- **Sobre una instalación existente:** `PleiadaRecorder_Update.exe`.
- **En una máquina limpia:** `PleiadaRecorder_Setup.exe`.

La barra de arriba tiene que decir **v0.10.4**.

Si pasa este QA, sale a producción como actualización obligatoria. Además de verificar cada ticket, repetí una grabación completa y una subida (partes 3 y 6 de la guía de la v0.10.0), para confirmar que no se rompió nada. Adjuntá `Documentos\Pleiada Logs\recorder.log` en todos los reportes.

## PLE-258 / PLE-259 — Carpeta de grabación de OBS

**Qué pasaba.** El Recorder pasaba OBS al perfil "Pleiada", que graba en una carpeta que puede no existir. OBS fallaba y el Recorder seguía mostrando "grabando". Además, OBS quedaba en el perfil "Pleiada" con su carpeta, en lugar de la que había elegido el usuario.

**Qué cambia:**
- OBS graba en `Documentos\Pleiada Recordings\_obs`, una carpeta que el Recorder crea si no existe.
- Al terminar, OBS vuelve al perfil que tenía el usuario.
- Si OBS no arranca o deja de grabar, el Recorder lo detecta y lo avisa.

### Grabación normal y perfil del usuario

1. En OBS, elegí un perfil propio (menú Perfil) con una carpeta de grabación cualquiera, y dejalo abierto.
2. Hacé una grabación corta desde el Recorder y detenela.

**Resultado esperado:**
- La sesión se guarda bien en `Documentos\Pleiada Recordings\<juego>_<fecha> recording\`.
- Al terminar, OBS vuelve a mostrar el perfil que habías elegido, con su carpeta de grabación sin cambios.
- La carpeta `_obs` no aparece como sesión en "Mis grabaciones".
- Lo mismo tiene que pasar si **cancelás** la grabación durante la cuenta regresiva.

### Carpeta que no existe (el caso del ticket)

1. Borrá o renombrá `Documentos\Pleiada Recordings\_obs`, si existe.
2. Iniciá una grabación.

**Resultado esperado:** la grabación arranca normalmente y la carpeta `_obs` se vuelve a crear.

### OBS no arranca

1. Provocá que OBS no pueda grabar. Por ejemplo, en el perfil "Pleiada" de OBS elegí un codificador que la placa no soporte.
2. Iniciá una grabación.

**Resultado esperado:** a los pocos segundos de terminar la cuenta regresiva, el Recorder muestra la pantalla **"OBS no pudo empezar a grabar"**, con el texto "Revisá en OBS si muestra algún error, cerralo y volvé a intentar." No queda en "grabando", y no aparece una sesión vacía en "Mis grabaciones".

### OBS deja de grabar en el medio

1. Iniciá una grabación.
2. A los 30 segundos, detené la grabación **desde OBS** (botón "Detener grabación" de OBS).

**Resultado esperado:** en unos 10 segundos, el Recorder muestra la pantalla **"OBS dejó de grabar"**, con el texto "OBS dejó de grabar antes de que detuvieras la sesión, así que la sesión se descartó. Revisá en OBS si muestra algún error y volvé a grabar." OBS vuelve al perfil del usuario.

## PLE-260 — Card del bono al elegir una orden al subir

**Qué pasaba.** Si al terminar la sesión se ofrecía el sorteo (sesión sin orden) y después se elegía una orden al subir, la card del bono no aparecía, porque el Recorder ya contaba la oferta como hecha.

1. Grabá una sesión de un título sin mapa de controles y sin elegir orden. Al terminar, cerrá la oferta del sorteo sin aportar.
2. En "Mis grabaciones", subí esa sesión y elegí una orden que pague bono por metadata.

**Resultado esperado:** antes de subir aparece la card del bono de esa orden. Si ya habías aportado los controles de esa sesión, no se ofrece de nuevo.

## Botones del mouse dibujados como íconos

**Qué pasaba.** Si la pantalla de controles del juego dibuja los botones del mouse como íconos, el aporte se rechazaba con "Solo leemos controles escritos como texto".

> Requiere que `pleiada-api` esté en la versión **2026-11-06.2**.

1. Aportá los controles de un título cuya pantalla de controles muestre los botones del mouse como íconos.
2. Tocá "Revisar".

**Resultado esperado:**
- En lugar del rechazo aparece **"Completá los botones del mouse"**, con el texto "En tus capturas algunos botones del mouse aparecen como íconos. Elegí cuál es en cada acción."
- Hay una fila por cada acción que no se pudo leer (acción · sección). Cada campo empieza en "—" y tiene una flecha **▾** a la derecha.
- **Elegir de la lista:** clic en ▾ → aparece la lista de botones → elegís uno.
- **Elegir presionando:** clic en el campo → el campo dice **"Presioná el botón…"** → con el mouse sobre el campo, apretá el botón (izquierdo, derecho o central) o girá la rueda. El campo toma ese botón. Si sacás el mouse del campo sin apretar nada, vuelve a como estaba.
- Los botones laterales del mouse se detectan solo en algunos mouse: si no los toma, se eligen desde ▾.
- **"Enviar"** se habilita recién cuando todas las filas tienen un botón elegido.
- Al enviar, el aporte sigue como cualquier otro: queda aceptado, o se rechaza con el motivo de siempre si falta información mínima.
- "Subir sin metadata" sube la sesión sin el aporte. ‹ vuelve a las capturas.
- Solo llegan a esta pantalla los botones del mouse: las teclas del teclado se leen siempre como texto, así que no hay un caso de teclado que probar.

### Volver atrás y reenviar las mismas capturas (issue de la ronda v0.10.3)

1. Llegá a "Completá los botones del mouse" como arriba.
2. Tocá ‹ para volver a las capturas, sin enviar.
3. Sin cambiar las capturas, tocá "Revisar" otra vez.

**Resultado esperado:** vuelve a aparecer "Completá los botones del mouse". Ya no sale "Una de estas capturas ya fue enviada antes". Probalo también saliendo con "Subir sin metadata" y aportando después la misma sesión con las mismas capturas.