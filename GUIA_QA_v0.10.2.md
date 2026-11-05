# Guía de QA — Gameplay Recorder v0.10.2

Esta versión corrige los tickets reportados sobre la v0.10.1.
- **Sobre una instalación existente:** `PleiadaRecorder_Update.exe`.
- **En una máquina limpia:** `PleiadaRecorder_Setup.exe`.

La barra de arriba tiene que decir **v0.10.2**.

Si pasa este QA, sale a producción como actualización obligatoria. Además de verificar cada ticket, repetí una grabación completa y una subida (partes 3 y 6 de la guía de la v0.10.0), para confirmar que no se rompió nada. Adjuntá `Documentos\Pleiada Logs\recorder.log` en todos los reportes.

## PLE-257 — Sesión rechazada por "AFK" mientras se jugaba

**Qué pasaba.** El Recorder registra el teclado y el mouse solo mientras el título está en primer plano, para no guardar lo que se escribe en otros programas. En la sesión de Pedro, a los 36 segundos otro programa se quedó con el primer plano y el juego siguió en segundo plano. Se perdieron 59 minutos de input, y el mensaje decía "período largo sin actividad", aunque estaba jugando.

**Qué cambia:**
- Un aviso durante la grabación.
- Un mensaje de rechazo que explica la causa real.
- Un registro de qué programa tenía el primer plano.

### Aviso en vivo

1. Iniciá una grabación y entrá al juego.
2. Pasá a otra ventana con Alt+Tab, por ejemplo el navegador o el Recorder, y quedate ahí más de 1 minuto.
3. Volvé al juego.

**Resultado esperado:**
- **Pasado el minuto:**
  - Suena el aviso de Windows, y se repite cada minuto mientras sigas fuera del juego.
  - En la pantalla de grabación del Recorder aparece un recuadro amarillo: "⚠ El título no está en primer plano: el Recorder no está registrando tus teclas ni tu mouse. Hacé clic en la ventana del título para seguir."
  - El aviso nunca saca del juego ni le roba el primer plano a otra ventana.
- **Al volver al juego:** dentro de 1 segundo desaparece el recuadro y deja de sonar.
- **Si el cambio de ventana dura menos de 1 minuto**, no hay aviso.

### Mensaje de rechazo

1. Iniciá una grabación de al menos 10 minutos.
2. Jugá un poco y después pasá a otra ventana y quedate ahí la mayor parte del tiempo. Movés el mouse, pero sin volver al juego.
3. Detené la grabación.

**Resultado esperado:** la sesión sale "no apta" con este texto, y no con el de AFK: "El Recorder no registró tus teclas ni tu mouse durante gran parte de la grabación porque el título no estaba en primer plano. Antes de jugar, hacé clic en la ventana del título y no cambies de ventana mientras grabás."

Una sesión AFK de verdad sigue mostrando el mensaje de siempre: juego en primer plano, sin tocar nada por más de 10 minutos.

### Registro

En `recorder.log`, al final de cada grabación, aparecen:
- Una línea `foco: juego=... fuera_total=...s tramo_max=...s`.
- Una línea `foco cambio:` por cada vez que cambió el programa en primer plano, con su nombre.

**Si vuelve a pasar en una sesión real**, adjuntá el `recorder.log`. Esas líneas dicen qué programa se quedó con el primer plano: por ejemplo un overlay de Steam, NVIDIA, AMD o Discord.

## PLE-256 — ⚙ en la pantalla de grabación

1. Iniciá una grabación y mirá la barra de arriba durante la cuenta regresiva y mientras graba.
2. Iniciá una subida y mirá la barra de arriba mientras sube.

**Resultado esperado:** ⚙ no aparece desde "Iniciando grabación" hasta que detenés la grabación, ni durante una subida. Vuelve a aparecer al detener y en la pantalla principal.

## PLE-255 — Loop con Atrás antes de subir

1. Desde una sesión lista, entrá a "Subir Data Set" y tocá ‹.
2. Volvé a entrar, avanzá hasta "Antes de subir el dataset", tocá ‹, y en la pantalla siguiente tocá ‹ otra vez.
3. Si tenés una sesión fuera de spec, repetí con esa pantalla.

**Resultado esperado:** ‹ lleva al mismo lugar que "Volver" en cada pantalla, y nunca vuelve a una pantalla que ya dejaste.

## PLE-252 — Pasos de la metadata (reabierto)

1. En el paso 2, sin capturas cargadas, tocá "3 REVISAR".
2. Cargá una captura y tocá "3 REVISAR".
3. Volvé al paso 2, borrá todas las capturas y tocá "3 REVISAR".

**Resultado esperado:**
- **Sin capturas:** "3 REVISAR" está apagado y no hace nada, igual que el botón "Revisar".
- **Con al menos una captura:** se enciende al instante y lleva al paso 3, sin salir y volver a entrar.
- **Al borrar la última:** se vuelve a apagar.

"1 QUÉ" y "2 CÓMO" siguen llevando a su paso.

## Cómo reportar

Igual que en la v0.10.0, y siempre con `Documentos\Pleiada Logs\recorder.log` adjunto.
