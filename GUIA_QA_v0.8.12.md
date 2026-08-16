# Guía de QA — Gameplay Recorder v0.8.12

16/08/2026 · rama `feature/v0.8.12` · commits `7b21b9c` y `cb0dc42`

Esta guía explica **qué cambió y por qué**, y cómo probar cada cosa. El checklist seco,
con casilleros para tildar, está en `QA_v0.8.12.md` — esta guía es para entender qué estás
mirando; ese otro es para no saltearte nada.

La versión junta cinco cambios de tres fechas distintas. Ninguno se publicó todavía.

---

## Antes de arrancar: instalar la versión local

Se compiló el instalador **LITE** (solo los archivos de la app, sin Python/OBS/AutoHotkey,
que ya tenés):

```
C:\Users\mspin\Documents\pleiada-recorder\pleiada_installer\Output\PleiadaRecorder_Update.exe
```

2,2 MB, estampado 0.8.12. Es el mismo artefacto que usa el auto-update, así que instalarlo
prueba de paso ese camino.

La alternativa, si vas a iterar y no querés reinstalar cada vez, es copiar los archivos
sueltos con `deploy_test.bat` — **botón derecho → Ejecutar como administrador**, porque
Program Files no deja escribir de otra forma. Lo arreglé en esta misma tanda: copiaba un
archivo que no existe y no copiaba `pleiada_app.pyw`, así que un deploy de prueba te dejaba
corriendo la versión vieja creyendo que probabas la nueva. Ahora también hace backup de la
instalación actual en `Documents\Pleiada Recorder backups\<fecha>` antes de pisar nada.

**Primer chequeo, sin el cual todo lo demás no vale:** abrir el Recorder y confirmar que el
encabezado dice **v0.8.12**. Si dice v0.8.11, no instalaste lo que creés.

El backend ya está en producción (`LAMBDA_VERSION 2026-08-15.1`), así que la parte de
órdenes se prueba contra datos reales.

---

## 1. Las órdenes completadas ya no aparecen como destino

### Qué pasaba
Al terminar una grabación, en "Orden de destino" te aparecía **GA-2026-007 (ACCIÓN)**, una
orden cerrada desde fines de julio. Si la elegías, la subida entraba: esas horas se comían
el margen de la orden terminada en vez de ir a la orden abierta.

Eran dos fallas encadenadas. El Recorder filtraba por un campo que significa *visible*, no
*abierta* — el backend manda las completadas también, para que el dashboard pueda mostrar
el historial. Y el gate del backend nunca miraba el estado de la orden: validaba
inscripción, juego y cupos, nada más.

### Lo que hay que cuidar al probarlo
Hay dos situaciones que suenan parecidas y **no** son lo mismo:

- **Orden completada:** la cerró el equipo. No acepta nada más.
- **Orden llena:** llegó al 100% de sus horas pero sigue activa. **Sí** tiene que seguir
  aceptando subidas, hasta un 10% extra. Es lo que evita que pierdas la sesión que estabas
  grabando justo cuando la orden se llenó.

Si el arreglo rompe la segunda, hace más daño que el bug. Por eso el filtro mira el estado
crudo de la orden y no el derivado, que mezcla las dos.

### Cómo probarlo
1. Grabá una sesión corta (2–3 min) de un juego de acción o shooter.
2. En la pantalla de subida, la lista de órdenes tiene que mostrar **solo GA-2026-010**.
   Las 007, 008 y 009 no van más — de hecho ya no las manda ni el backend, porque las pasé
   a `cerrado`.
3. Subila y confirmá que entra normal.

**El caso de la orden llena** no se puede provocar con los datos de hoy: hoy no hay ninguna
orden activa por encima del 100%. Si querés verificarlo igual, la forma es pedirle a la API
`my_calls` con tu token y confirmar que 010 llega con `call_status: "activo"`; el filtro
solo saltea las que dicen `completado`.

**Con un Recorder viejo:** si abrís una instalación v0.8.11 que todavía liste una orden
completada y le das Subir, tiene que frenar con "Esta orden ya está completa" **antes** de
transferir nada. No a mitad de la subida.

---

## 2. El video se guarda con el mismo nombre con el que se sube

### Qué pasaba
El hash del video quedaba guardado bajo un nombre que el archivo no tenía en ningún lado.
OBS nombra la grabación con espacios (`2026-08-02 22-33-10.mp4`) y el backend los reemplaza
por guiones bajos al armar la ruta en S3. Resultado: buscar el hash del video por el nombre
del archivo no encontraba nada. Los cuatro CSV nunca tuvieron el problema porque sus
nombres son fijos.

Ahora el MP4 se renombra al moverlo a la carpeta de sesión, con la misma regla que aplica
el backend, y el metadata declara que los nombres ya son seguros.

### Cómo probarlo
1. Grabá una sesión y mirá la carpeta: el MP4 tiene que llamarse
   `2026-XX-XX_HH-MM-SS.mp4`, con **guiones bajos**, no espacios.
2. Abrí `session_metadata.json` y buscá el bloque `integrity`: la clave del video tiene que
   ser exactamente ese nombre, y tiene que aparecer `"naming": "s3-safe"`.
3. Subila y verificá en la consola de S3 que el objeto se llama igual.

### El riesgo de esta parte
Toca el movimiento del archivo al terminar de grabar, que está en el camino crítico. Si el
renombrado falla, se rompe algo mucho más caro que el bug que arregla. Mirá en
`Documents\Pleiada Logs` que aparezca `Video movido a:` y que **no** haya `ADVERTENCIA`, y
probá una sesión larga (30+ min) para confirmar que mover un archivo grande no falla ni te
deja el MP4 abandonado en `Videos`.

### Compatibilidad
Una sesión grabada con v0.8.11 (con el MP4 con espacios todavía en disco) tiene que subir
igual que siempre, sin el campo `naming`. Los ~4.000 datasets ya subidos no cambian.

---

## 3. La configuración de grabación se sostiene sola

### Qué pasaba
Si el usuario tocaba OBS —bajaba la resolución, cambiaba el bitrate, pasaba a modo
avanzado— el Recorder grababa con esa configuración. Ahora la fuerza a la nuestra antes de
cada grabación, en silencio, y sin escribir nada en el perfil propio del usuario.

### Cómo probarlo
1. En OBS, con el perfil `Pleiada` activo, poné modo de salida **Avanzado**, subí el
   bitrate y bajá la resolución a 1280×720 @ 30.
2. Grabá 2 minutos con el Recorder.
3. Al terminar, en Ajustes → Salida tiene que haber vuelto a **Sencillo**, tasa **2500**,
   calidad **Igual que la transmisión**, formato **MP4 fragmentado**; y en Vídeo,
   **1920×1080** a **60** FPS.
4. **Lo que más importa es el peso:** dos minutos tienen que pesar ~40 MB, no ~300 MB.
   El peso es la prueba real de que se aplicó; la UI de OBS puede mostrar lo correcto y
   estar grabando con lo viejo.
5. Que sea silencioso: ningún cartel, ningún modal, y que no se note más lento el arranque.

### El riesgo conocido
OBS puede seguir usando los valores viejos hasta recargar el perfil. Es lo primero a
sospechar si el punto 4 falla por peso. Probá también **dos sesiones seguidas** sin cerrar
OBS: la segunda también tiene que salir bien.

Y probá con un perfil ajeno: activá otro perfil en OBS, grabá, y después volvé a ese perfil
para confirmar que sus valores siguen intactos.

---

## 4. Detección del juego capturado: dos bugs

### Qué pasaba
Uno: los títulos con dos puntos llegaban con el carácter escapado (`#3A` en vez de `:`), lo
que afectaba a un cuarto del catálogo. Dos: el matcher confundía juegos de la misma saga y
dejaba pasar capturas del juego equivocado.

### Cómo probarlo
1. Elegí un título con `:` en el nombre (por ejemplo *Horizon Zero Dawn: Complete Edition*),
   apuntá el Game Capture a esa ventana: el Recorder **no** tiene que bloquear, y en
   pantalla el título se ve con `:`, no con `#3A`.
2. Con OBS capturando *Marvel's Spider-Man Remastered*, seleccioná *Marvel's Spider-Man*,
   *Marvel's Spider-Man 2* y *Marvel's Spider-Man: Miles Morales*: los tres tienen que
   frenar.

### El riesgo, que es el más serio de la versión
Endurecer el matcher convierte falsos positivos silenciosos en **bloqueos visibles**. Un
bloqueo de más frena a alguien que hoy graba bien, y se entera recién cuando no puede
grabar. Antes de publicar hay que revisar `%TEMP%\pleiada_obs_debug.txt` buscando
`title_match ENDURECIDO bloqueó:` — cada línea es un caso que la regla vieja dejaba pasar,
y hay que mirarlos uno por uno.

Caso conocido que ahora bloquea y antes no: el usuario que abrevia el título en la ventana
(`AC Odyssey` contra `Assassin's Creed Odyssey`). Hay que decidir si se acepta o si se
relaja la regla.

---

## 5. El metadata guarda el ejecutable detectado

Cambio chico y sin riesgo: `session_metadata.json` ahora registra qué ejecutable se detectó
y el string crudo de la ventana de OBS. Es información, no un control nuevo: cuando viene
vacío o nulo no frena ni la grabación ni la subida. Probarlo es abrir el metadata de
cualquier sesión y ver que los campos están.

---

## Además, aunque no sea del Recorder

El bundle de juegos se regeneró con el catálogo de hoy: **501 títulos**. Entran los géneros
corregidos ayer (Bodycam pasó de Simulator a FPS, Don't Scream y Pacify a Horror, Thick as
Thieves a Stealth) y salen los tres joke games dados de baja.

Vale la pena aprovechar el QA para confirmar que **Bodycam aparece y sube** en la orden
010: era el caso que destapó todo esto.

---

## Orden sugerido

Probá primero **3 y 4**, que son los que pueden romper la captura de alguien que hoy graba
bien. Después **2**, que toca el guardado del archivo. **1 y 5** son los de menor riesgo:
el 1 solo saca opciones de una lista y el 5 agrega campos que nadie lee todavía.

## Si algo falla

Volver atrás es copiar de vuelta la carpeta de backup que dejó `deploy_test.bat`, o
reinstalar la v0.8.11. Nada de esta versión toca datos ya subidos ni cambia el formato de
los datasets viejos, así que un rollback no arrastra nada.

## Cuando el QA pase

Queda pendiente, y **nada de esto lo hago sin tu OK explícito**:

- Mergear `feature/v0.8.12` a `main` y pushear.
- Compilar el instalador completo:
  `ISCC.exe /DAppVersion=0.8.12 setup.iss` (el LITE ya está hecho).
- Regenerar `Output\latest.json` con 0.8.12.
- **No** subir `min_version.txt`: se decidió el 10/08 que el update es opcional.
- Release de GitHub.
