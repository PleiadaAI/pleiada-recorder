# Guía de QA — Gameplay Recorder v0.10.1

Esta versión corrige los tickets que reportaron sobre la v0.10.0. Se instala igual que la anterior: `PleiadaRecorder_Update.exe` sobre una instalación existente, o `PleiadaRecorder_Setup.exe` en una máquina limpia. La barra de arriba tiene que decir **v0.10.1**.

Si pasa este QA, sale a producción como actualización obligatoria. Además de verificar cada ticket, repetí una grabación completa y una subida (partes 3 y 6 de la guía de la v0.10.0) para confirmar que no se rompió nada.

## Nuevo: dónde está el registro de la app

El registro de lo que hace el Recorder (OBS, detección del título, inicio y corte de grabación, errores) ahora está en:

`Documentos\Pleiada Logs\recorder.log`

Adjuntalo en **todos** los reportes. Cada línea tiene fecha y hora. Cuando pasa de 5 MB, la versión anterior queda como `recorder.log.1`.

Los otros archivos de esa carpeta están vacíos casi siempre, y eso es normal:

| Archivo | Cuándo escribe |
|---|---|
| `faulthandler.log` | Solo si la app se cierra de golpe |
| `crash.log` | Solo ante un error interno; aparece la primera vez que hay uno |
| `upload.log` | Solo durante las subidas |

## Tickets para volver a probar

### PLE-250 — Navegar con la sesión vencida

1. Con la sesión vencida, abrí la app.

**Resultado esperado:** en la pantalla "Tu sesión venció." no aparecen ⚙ ni ‹. F9 no inicia una grabación. Lo único posible es "Iniciar sesión". En la pantalla de inicio de sesión tampoco aparece ⚙.

### PLE-253 — Atrás durante una subida

1. Empezá a subir una sesión y tocá ‹ en la barra de arriba.
2. Volvé a subir la misma sesión.

**Resultado esperado:** ‹ hace lo mismo que "Cancelar": corta la subida y vuelve. El segundo intento arranca normalmente.

### PLE-246 — Pantalla de 768 de alto

1. Con la resolución en 1366×768, o cualquiera de 768 de alto, y escala al 100 %, abrí la app.

**Resultado esperado:** la ventana entra entera sobre la barra de tareas. Los tips se ocultan para hacer lugar, y es lo esperado.

### PLE-247 — Versión pisada en la barra

1. Con la escala en 125 %, 150 % y 175 %, mirá la barra de arriba.

**Resultado esperado:** "Gameplay Recorder" y la versión no se superponen. ⚙ y × quedan alineados a la derecha.

### PLE-248 — "Cerrar sesión" a 175 %

1. Con la escala al 175 %, abrí Ajustes.

**Resultado esperado:** el email y "Cerrar sesión" quedan fijos abajo y siempre visibles. Si el resto no entra, aparece una barra fina a la derecha y se puede bajar con la rueda del mouse.

Hacé la misma prueba en los pasos 1, 2 y 3 de la metadata: si el contenido no entra, scrollea, y los botones de abajo siempre se ven.

### PLE-252 — Pasos de la metadata

1. En los pasos de la metadata, tocá "1 QUÉ", "2 CÓMO" y "3 REVISAR".

**Resultado esperado:** cada paso lleva a su pantalla. "3 REVISAR" está apagado hasta que cargues al menos una captura, igual que el botón "Revisar". "Siguiente" y "Volver" siguen funcionando.

### PLE-254 — Disco lleno

**Antes de grabar:** dejá con poco espacio el disco donde OBS guarda las grabaciones e intentá grabar.

**Resultado esperado:** aparece "No hay espacio en el disco", con la unidad, y no arranca la grabación. Liberá espacio y debería dejarte grabar.

**Durante la grabación:** si podés, llená el disco mientras grabás.

**Resultado esperado:** cuando OBS corta, aparece "La grabación se cortó" con la unidad. La sesión se descarta y no queda nada para subir. Adjuntá `recorder.log`.

### PLE-249 — Cuenta regresiva a 150 % y 175 %

1. Con la escala en 150 % y 175 %, iniciá una grabación.

**Resultado esperado:** el número se ve dentro del anillo, sin ningún recuadro alrededor.

### PLE-242, 243 y 245 — Hover de los botones principales

1. Pasá el mouse por "Subir", "Ver órdenes abiertas", "Iniciar grabación" e "Iniciar grabación libre".

**Resultado esperado:** el botón se aclara.

### PLE-244 — Soltar el clic fuera del botón

1. En cada botón y enlace, apretá el clic, salí del área y soltá.

**Resultado esperado:** no pasa nada. La acción solo se ejecuta si soltás sobre el botón. Probalo en "Reenviar código", "Cambiar email", "Mis grabaciones", "Ver tutorial de configuración", ⚙, ‹, ×, los atajos, la duración máxima y el reinicio automático.

## PLE-251 — No es un error

Una grabación hecha con la pantalla en 1280×768 se sube porque OBS la guarda en 1920×1080: el Recorder configura OBS para grabar siempre en esa resolución, y el control de video mide el archivo final. El criterio es el mismo del control de calidad de las entregas, así que esa sesión se acepta.

## Cómo reportar

Igual que en la v0.10.0, y siempre con `Documentos\Pleiada Logs\recorder.log` adjunto.
