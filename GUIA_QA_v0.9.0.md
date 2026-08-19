# Guía de QA — Gameplay Recorder v0.9.0

Build: `PleiadaRecorder_Update.exe` · estampado 0.9.0

Esta versión cambia la pantalla principal: **el juego ya no se elige de una lista**. El
Recorder lee qué está capturando OBS y lo identifica solo. Todo lo demás de la guía sale
de ese cambio.

Hay un segundo documento, `GUIA_QA_v0.9.0_input_vacio.md`, que cubre el rechazo de
sesiones sin teclado ni mouse registrado. Los dos se prueban sobre este mismo build.

---

## Antes de empezar

- Instalar el `.exe` y abrir el Recorder. **El encabezado tiene que decir v0.9.0.** Si dice
  otra versión, no se instaló lo que corresponde y el resto de la guía no aplica.
- En OBS, la fuente de captura tiene que ser **Captura de Videojuego (Game Capture)** y
  estar en modo **ventana específica**, apuntada a la ventana del juego. En modo "cualquier
  aplicación en pantalla completa" el Recorder no puede leer el ejecutable y no va a
  identificar nada: eso es esperado, no un error.
- Hace falta estar logueado y con conexión.

---

## 1. El juego se identifica solo

**Qué cambió:** desapareció el buscador de juegos. La pantalla principal muestra un panel
que dice qué está capturando OBS.

### 1.1 Camino normal
1. Abrir un juego del programa y apuntar la fuente de OBS a su ventana.
2. Volver al Recorder sin tocar nada.

**Esperado:** en pocos segundos el panel pasa de "Esperando el juego" a mostrar el nombre
del juego, con su género, vista y modo debajo. Aparece la lista de órdenes que lo aceptan
y el botón Grabar se habilita.

### 1.2 Elección de orden
Si hay más de una orden que acepta el juego, se muestran todas y se puede elegir.

**Esperado:** viene seleccionada la primera; al cambiar la selección, la sesión se graba
contra la orden elegida. Verificar después de subir que la sesión quedó en esa orden.

### 1.3 Cuando no está claro cuál es
Apuntar OBS a un juego que tenga otras entregas con nombre parecido en el catálogo.

**Esperado:** el panel pregunta cuál se está jugando y ofrece hasta cuatro opciones. Al
elegir una, sigue el camino normal. **No** tiene que aparecer una opción "ninguno de
estos".

### 1.4 Un título que no está en el programa
Abrir un juego que no esté en el catálogo.

**Esperado:** el panel avisa que está buscando la ficha **en IGDB** —el texto tiene que
nombrar IGDB— y después pasa una de dos cosas. Si el juego es del tipo que las órdenes
abiertas están buscando, se suma al programa, aparece "Sumado al programa" y se puede
grabar contra esa orden. Si no, cae en grabación libre (punto 2).

### 1.5 Lo único que impide grabar
Apuntar la fuente de OBS a algo que no sea un juego: el navegador, el escritorio, o el
launcher de Steam o Epic.

**Esperado:** el panel dice que no se pudo identificar el título y el botón Grabar queda
deshabilitado. **Este es el único caso en toda la app donde no se puede grabar.**

### 1.6 Lo que ya no debería pasar — *lo más importante de probar*
En las versiones anteriores el Recorder bloqueaba la grabación cuando no lograba verificar
que la ventana de OBS coincidía con el juego elegido, y también si no encontraba el proceso
del juego corriendo. **Los dos controles se eliminaron.**

Probar especialmente con los casos que antes fallaban:
- Juegos con dos puntos en el nombre, como *Horizon Zero Dawn: Complete Edition*.
- Juegos de la misma saga, como los *Marvel's Spider-Man*.
- Juegos que corren como administrador.
- Juegos cuyo ejecutable no tiene nada que ver con el nombre.

**Esperado:** en todos, el juego se identifica y se puede grabar. Si alguno queda trabado,
anotar el nombre del juego, el nombre exacto de la ventana en OBS y el ejecutable: son los
tres datos que hacen falta para arreglarlo.

### 1.7 Cambiar de juego sin cerrar el Recorder
Con el Recorder en la pantalla principal, cerrar el juego y abrir otro, cambiando la fuente
de OBS.

**Esperado:** el panel se actualiza solo en pocos segundos, sin tocar nada.

---

## 2. Grabación libre

**Qué es:** si ninguna orden abierta busca ese título, igual se puede grabar. La sesión
queda guardada pero no se puede subir.

1. Apuntar OBS a un juego que ninguna orden esté pidiendo.

**Esperado:** el panel muestra el juego identificado y avisa que ninguna orden abierta lo
está buscando. El texto **no** tiene que prometer que va a aparecer una: dice que puede
aparecer o puede no aparecer nunca, e invita a mirar el dashboard y las redes.

2. Grabar una sesión corta y detenerla.

**Esperado:** la verificación corre igual que siempre y la sesión se guarda completa. Al
terminar no se ofrece subirla. En `session_metadata.json`, el campo `recording_mode` tiene
que decir `libre`.

---

## 3. Cancelar una grabación

**Qué es:** un botón nuevo, debajo de Detener, mientras se está grabando. Descarta la
sesión en vez de cerrarla.

1. Empezar a grabar y esperar un par de minutos.
2. Apretar **Cancelar grabación**.

**Esperado:** pide confirmación. Al confirmar, la grabación se corta, **no** corre la
verificación, y la carpeta de la sesión desaparece de `Documentos\Pleiada Recordings`. La
pantalla dice dónde quedó el video: ese archivo tiene que existir en esa ruta.

3. Ir a **Mis grabaciones**.

**Esperado:** la sesión cancelada no aparece en la lista y no se puede subir de ninguna
forma.

4. Repetir y **cancelar la confirmación** en vez de aceptarla.

**Esperado:** sigue grabando normalmente, sin cortes ni saltos en el contador.

**Detener tiene que seguir funcionando igual que siempre:** cierra, verifica, genera el
dataset y lo deja listo para subir. Probar los dos en la misma sesión de QA.

---

## 4. Atrás

Aparece a la izquierda de la barra de título.

**Esperado:** se ve en Ajustes y en Mis grabaciones, y vuelve a la pantalla principal.
**No** se ve en la pantalla principal, y **no** se ve mientras se está grabando: ahí las
únicas salidas son Detener y Cancelar.

---

## 5. Mis grabaciones

El acceso de la pantalla principal ahora dice **Mis grabaciones**, no "Subir grabaciones".

**Esperado:** el nombre coincide con el de la sección que abre. Las grabaciones anteriores
siguen apareciendo y se pueden subir como siempre.

---

## 6. Formato del video — probar con OBS en modo Avanzado

**Qué cambió:** el Recorder forza el formato de grabación también cuando OBS está en modo
de salida Avanzado. Antes solo lo hacía en modo Sencillo, y quien tuviera Avanzado grababa
en otro formato sin enterarse.

1. En OBS: Ajustes → Salida → **Modo de salida: Avanzado**. Guardar.
2. Grabar una sesión corta con el Recorder.
3. Volver a Ajustes → Salida en OBS y mirar el formato de grabación.

**Esperado:** quedó en **MP4 fragmentado**, en los dos modos de salida. El video se
reproduce completo y la sesión pasa la verificación.

Probar también con el perfil `Pleiada` borrado de OBS: se tiene que recrear solo y la
grabación tiene que arrancar igual.

---

## Qué reportar

Por cada problema: qué juego, qué decía la ventana de OBS, qué ejecutable, y qué mostró el
Recorder. Si hay un bloqueo inesperado, adjuntar `%TEMP%\pleiada_obs_debug.txt` y los logs
de `Documentos\Pleiada Logs`.
