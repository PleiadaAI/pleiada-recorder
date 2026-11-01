# Guía de QA — Gameplay Recorder v0.10.0

Esta versión cambia el diseño de toda la app y suma controles nuevos antes de subir. Si pasa este QA, sale a producción como **actualización obligatoria**.

La prueba tiene dos objetivos: que todo se vea bien y que nada de lo que ya funcionaba se haya roto. El diseño se rehízo sobre la lógica existente, así que los flujos tienen que comportarse igual que antes, salvo lo que se indica en esta guía.

## Qué recibís

| Archivo | Para qué sirve |
|---|---|
| `PleiadaRecorder_Update.exe` | Actualiza una instalación existente. Usalo en las máquinas que ya tienen el Recorder. |
| `PleiadaRecorder_Setup.exe` | Instalación limpia, en una máquina sin Recorder. |
| `Sesiones_de_prueba_QA_v0.10.0.zip` | Seis sesiones sintéticas para los casos 4.5, 4.6 y 4.7. |

El build no tiene firma de código. Si Windows muestra SmartScreen, elegí "Más información" y después "Ejecutar de todas formas".

Después de instalar, confirmá que la barra de arriba diga **v0.10.0**.

## Qué cambió

### Diseño nuevo

- Fondo violeta oscuro, tarjetas con esquinas redondeadas y botones principales con degradé violeta a rosa.
- Barra de título nueva, con logo.
- Chip de usuario abajo en la pantalla principal, en lugar de "SESIÓN: No iniciada".
- Mientras grabás, el tiempo restante está debajo del contador grande.
- Las cuentas regresivas tienen un anillo.
- Textos nuevos en tips, resultado de la sesión, oferta de metadata, identificación del título y subida.
- El aviso de actualización ya no tiene el botón "Más tarde".

### Controles nuevos de sesión

- **Mínimo de 5 minutos.** Una sesión más corta queda como no apta, y el mensaje informa el mínimo.
- **Sesiones de versiones anteriores.** Mantienen el mínimo de 30 segundos.
- **Control de video antes de subir.** Se rechaza una sesión con menos de 1080p, más ancha que 16:9 o con menos de 59 FPS.

### Qué no cambió

- Synch Checker y el asistente de instalación conservan su aspecto anterior. No reportes eso como error.
- Annotations no viene en este build.
- El formato de los archivos de sesión es el mismo.

## Antes de empezar

1. Anotá versión de Windows, placa de video, resolución y escala de pantalla de tu máquina.
2. Tené a mano un título real, con una orden abierta si podés.
3. Grabá las sesiones de prueba de 1 a 4 minutos **con tu versión anterior, antes de actualizar**. Las usás en el caso 4.3.
4. Los registros de la app están en `Documentos\Pleiada Logs`. Si algo falla, adjuntalos al reporte.

Cuando la sesión válida pide 6 minutos, grabá al menos ese tiempo: el mínimo es 5.

---

## Parte 1 — Instalación y primer inicio

| # | Qué hacer | Resultado esperado |
|---|---|---|
| 1.1 | Actualizar con `PleiadaRecorder_Update.exe` sobre una versión anterior | Termina sin errores, abre v0.10.0 y hay un solo acceso directo en el escritorio |
| 1.2 | Instalar con `PleiadaRecorder_Setup.exe` en una máquina limpia | Instala OBS y dependencias, y la app abre |
| 1.3 | Abrir la app ya con sesión iniciada | Entra directo y el chip muestra lo que va antes de la @ del email |
| 1.4 | Cerrar sesión en Ajustes e iniciar sesión con tu email y el código | Vuelve a la pantalla principal y el chip muestra tu **nombre de usuario** |

---

## Parte 2 — Revisión visual

Recorré cada pantalla. En todas, verificá:

- Ningún texto cortado o superpuesto.
- Ningún botón fuera de la ventana.
- Tarjetas y botones con esquinas redondeadas, sin rectángulos de otro color en las esquinas.
- Texto legible sobre el fondo.
- Que se lea "título" en vez de "juego" donde corresponda.

| Pantalla | Cómo llegar | Qué mirar |
|---|---|---|
| Iniciar sesión | Cerrar sesión desde Ajustes | Logo, "Desarrollado por Gameplay Alliance" |
| Código por email | Enviar código | Campo de código, "Reenviar código", "Cambiar email" |
| Principal, buscando | Abrir la app con OBS sin título | "Esperando el título", botón apagado |
| Principal, lista | Título detectado | Borde degradé en la tarjeta, botón con degradé |
| Principal, no disponible | Título bloqueado | Borde rojo en la tarjeta y mensaje claro |
| Tips | Pantalla principal | Siete tips, sin íconos, en una sola tarjeta |
| Chip de usuario | Pantalla principal, abajo | Punto verde y nombre |
| Ajustes | Ícono ⚙ | Se ve todo hasta "Cerrar sesión", sin scroll ni cortes |
| Mis grabaciones | Enlace en la principal | Atrás arriba a la izquierda, lista con scroll |

### Escala de pantalla y resolución

Repetí la pantalla principal, Ajustes y el paso 1 de la metadata con la escala de Windows en **100 %, 125 % y 150 %**. Si tenés una notebook de 768 px de alto, probala también.

**Resultado esperado:** nada queda fuera de la ventana. En pantallas muy bajas los tips pueden ocultarse, y eso es correcto.

### Controles de la ventana

| # | Qué hacer | Resultado esperado |
|---|---|---|
| 2.1 | Arrastrar la ventana desde la barra de título | Se mueve, también desde el logo y el nombre |
| 2.2 | Hacer clic en ⚙, en × y en ‹ | Cada uno hace lo suyo y no mueve la ventana |
| 2.3 | Pasar el mouse sobre botones | Cambia el aspecto y aparece la mano |
| 2.4 | Hacer clic en un botón y soltar afuera | No ejecuta la acción |
| 2.5 | Hacer clic en un botón apagado | No hace nada |
| 2.6 | Cambiar los atajos en Ajustes | Toma la tecla nueva y funciona sin foco |

---

## Parte 3 — Grabación completa

### 3.1 Sesión válida de principio a fin

1. Abrí un título y grabá 6 minutos jugando con normalidad.
2. Detené con el botón, y repetí otra sesión deteniendo con el atajo.
3. Subí una de las sesiones.

**Resultado esperado**
- Cuenta regresiva con anillo; el número se pone rojo en los últimos segundos.
- "Tiempo restante de grabación:" debajo del contador grande, y baja segundo a segundo.
- Después de detener aparece "¡Sesión lista para enviar!" con el texto sobre el primer nivel de Control de Calidad.
- La subida termina y muestra "Sesión subida correctamente a Gameplay Alliance."
- En `session_metadata.json`, `recorder_version` = `v0.10.0` y `sync.video_spec_failures` = `[]`.

### 3.2 Cancelar

1. Cancelá durante la cuenta regresiva.
2. Iniciá otra grabación y cancelala mientras graba.

**Resultado esperado:** vuelve a la principal desde la cuenta regresiva. Al cancelar grabando aparece "Grabación cancelada", y la sesión no queda para subir.

### 3.3 Duración máxima y reinicio automático

1. En Ajustes, activá el reinicio automático con 30 minutos de duración máxima.
2. Grabá hasta que se detenga sola.

**Resultado esperado:** se detiene a los 30 minutos, se valida, muestra "Sesión guardada" con el anillo y la cuenta de 10 segundos, y arranca la siguiente. "Cancelar" corta el reinicio.

### 3.4 Rendimiento

Durante una grabación de un título exigente, compará contra tu versión anterior en la misma escena:

- FPS del título.
- Fotogramas perdidos en OBS.
- Uso de CPU del Recorder en el Administrador de tareas.

**Resultado esperado:** sin diferencias apreciables. Reportá cualquier congelamiento de la ventana o cierre inesperado, y adjuntá los registros.

---

## Parte 4 — Controles de sesión

### 4.1 Sesión corta

1. Grabá 2 minutos y detené.

**Resultado esperado**
- "Sesión no apta para enviar", con este mensaje: "La sesión duró menos de 5 minutos. Grabá al menos 5 minutos de gameplay para que los datos sean válidos."
- En Mis grabaciones figura **No válida**, sin "Subir".

Conocido: en esta pantalla todos los archivos pueden aparecer marcados con error. No lo reportes.

### 4.2 Sesión larga sin actividad

1. Grabá 6 minutos sin tocar teclado ni mouse.

**Resultado esperado:** queda como no apta, con un mensaje que no indica números.

### 4.3 Sesión corta de una versión anterior

Usá la sesión de 1 a 4 minutos que grabaste antes de actualizar, sin haberla subido.

1. Abrí Mis grabaciones y subila.

**Resultado esperado:** figura **Pendiente** y se sube bien.

### 4.4 Actualización obligatoria

Esta prueba se hace cuando la versión esté publicada en el entorno de prueba. Coordiná con el equipo antes de ejecutarla.

**Resultado esperado**
- El aviso ofrece solo "Actualizar ahora", sin "Más tarde".
- No deja grabar hasta actualizar.
- Las sesiones pendientes siguen en Mis grabaciones después de actualizar.

### Sesiones sintéticas: preparación

Descomprimí el zip dentro de `Documentos\Pleiada Recordings` y abrí Mis grabaciones. Son videos de patrón de prueba con título "Sesión de prueba QA". **No las subas:** en los casos que pasan, frená en la pantalla de confirmación con "Volver". Al terminar, borrá esas carpetas.

### 4.5 Video fuera de especificación

| Sesión | Mensaje esperado al apretar "Subir" |
|---|---|
| `QA E1 1280x720 60fps` | "La grabación no llega a la resolución mínima que pide el programa…" |
| `QA E2 2560x1080 60fps` | "La grabación tiene una relación de aspecto que no podemos usar…" |
| `QA E3 1920x1080 30fps` | "La grabación quedó por debajo de los cuadros por segundo mínimos…" |

**Resultado esperado:** no arranca ninguna subida. Al volver y reabrir la lista, la sesión figura **No válida**.

### 4.6 Formatos válidos

| Sesión | Resultado esperado |
|---|---|
| `QA F1 2560x1440 60fps` | Pasa a la confirmación de subida |
| `QA F2 2560x1600 60fps` | Pasa a la confirmación de subida |

### 4.7 Menos de 30 segundos, de una versión anterior

1. Abrí `QA D menos de 30 segundos` en Gameplay Synch Checker.

**Resultado esperado:** el mensaje dice "La sesión duró menos de 30 segundos."

---

## Parte 5 — Identificación del título

Usá un programa que no sea un juego conocido, o un título recién salido, para forzar este flujo.

| # | Qué hacer | Resultado esperado |
|---|---|---|
| 5.1 | Capturar en OBS una ventana no identificable | Tarjeta roja "No pudimos identificar el título" y enlace "Identificar el título" |
| 5.2 | Escribir el nombre y tocar "Buscar" | Lista "¿Es alguno de estos?" con botón **Seleccionar** en cada opción |
| 5.3 | Tocar "Seleccionar" en una opción | Pantalla "¿Confirmás que es este?" |
| 5.4 | Tocar "ver ficha en IGDB" | Abre la ficha en el navegador |
| 5.5 | Tocar "Ninguno es el mío" | Ofrece otro nombre, enlace de IGDB o Steam |
| 5.6 | Pegar un enlace inválido | Muestra el error y deja corregirlo |
| 5.7 | Completar por Steam con perspectiva "No sé" | Confirma el título |
| 5.8 | Terminar sin identificarlo | "No podemos habilitar la grabación", con "Volver a la pantalla de inicio" |
| 5.9 | Volver a abrir ese ejecutable tras identificarlo | No vuelve a preguntar |

---

## Parte 6 — Subida y órdenes

| # | Qué hacer | Resultado esperado |
|---|---|---|
| 6.1 | Subir una sesión con orden activa | La confirmación muestra Título, Sesión, Archivos, Duración y orden de destino |
| 6.2 | Subir un título que no entra en tus órdenes | "Subida no disponible", con texto de "títulos elegibles" y "Ver órdenes abiertas" |
| 6.3 | Subir sin inscripción a ninguna orden | "Subida no disponible" y "No estás inscripto en ninguna orden abierta" |
| 6.4 | Cortar internet durante una subida | Error con "Reintentar" y "Volver". Al reconectar, reintenta bien |
| 6.5 | Cancelar una subida en curso | Vuelve sin dejar la sesión rota |
| 6.6 | Subir dos veces la misma sesión | "Este Data Set ya estaba subido." |
| 6.7 | Dejar vencer la sesión o invalidarla, y subir | "Tu sesión venció." con botón "Iniciar sesión", y al entrar podés seguir |

---

## Parte 7 — Metadata de controles

Usá un título sin mapa de controles.

| # | Qué hacer | Resultado esperado |
|---|---|---|
| 7.1 | Terminar una sesión válida con orden | Oferta "Ganá un % adicional por la metadata", sin monto |
| 7.2 | Terminar una sesión válida sin orden | Oferta "Este título no tiene mapa de controles", con el sorteo |
| 7.3 | Tocar "Subir Data Set" sin compartir | Ventana "¿Subir el dataset sin la metadata?", con "Compartir controles" y "Subir sin metadata" |
| 7.4 | Abrir el paso 1 | Las cinco filas obligatorias con punto verde, y el texto de "Hacen falta dos personas" entero |
| 7.5 | Pasar al paso 2 con una imagen inválida y otra borrosa | Error claro por imagen |
| 7.6 | Pasar al paso 3 | "Analizar metadata" apagado hasta marcar la casilla |
| 7.7 | Enviar capturas correctas | "Analizando tus capturas" y después "Controles recibidos", con estado Validación pendiente |
| 7.8 | Enviar capturas que no sirven | "No pudimos leer lo mínimo" e intento 1 de 3 |
| 7.9 | Fallar tres veces | Avisa que ya probaste tres veces y deja subir sin metadata |
| 7.10 | Subir desde Mis grabaciones una sesión guardada | Pantalla "Antes de subir el dataset" con la misma oferta |

**Mínimo para aceptar un aporte:** las cuatro teclas de movimiento, el botón principal del mouse si el título lo usa, y al menos ocho controles a pie.

---

## Qué no es un error

- El degradé de los botones está fijo. No hay animaciones nuevas en esta versión.
- El chip muestra lo que va antes de la @ hasta que inicies sesión de nuevo.
- Synch Checker y el asistente de instalación mantienen el diseño anterior.
- Se muestra el mínimo de 5 minutos, a diferencia de otros límites, que no se informan.
- La ventana quedó 10 px más alta que antes.

## Cómo reportar

Por cada problema, mandá:

```text
Caso: (por ejemplo 5.3)
Máquina: Windows, placa de video, resolución, escala
Pasos:
Esperado:
Resultado:
Captura de pantalla:
Registros de Documentos\Pleiada Logs (si hubo error o cierre):
```

Un cierre inesperado o un error que mencione `Tcl` es **prioridad alta**: anotá qué estabas haciendo y adjuntá los registros de inmediato.

## Cierre del QA

Al terminar, mandá una tabla con cada parte y su estado (OK, con observaciones o bloqueante), la máquina usada y los casos no ejecutados.
