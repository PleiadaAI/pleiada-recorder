# Backlog — Gameplay Recorder

Cosas decididas que todavía **no** están implementadas, y que no entran en la versión en
curso. Lo más urgente arriba. Cuando algo se implementa, se borra de acá.

---

## 1. Elegir dónde se guardan las grabaciones

**Estado: aprobado para una versión futura (16/08/2026). No entra en la actual.**

Hoy la carpeta es fija: `Documentos\Pleiada Recordings`. El usuario tendría que poder
cambiarla desde Ajustes — típicamente para grabar en un disco secundario con más espacio.

La constante se usa en cuatro lugares del código, así que el cambio en sí es chico. Lo que
hace que no sea trivial:

- **Las grabaciones viejas quedan en la ruta anterior.** La lista de grabaciones tiene que
  seguir encontrándolas, o hay que ofrecer moverlas. Si no, el usuario cambia la carpeta y
  cree que perdió las sesiones que tenía.
- **El movimiento del MP4 es el riesgo real.** OBS graba en su propia carpeta y el Recorder
  mueve el archivo a la carpeta de sesión al cerrar. Dentro del mismo disco es instantáneo;
  a otro disco pasa a ser una copia de varios GB, y eso cae en el camino crítico del cierre
  de sesión. Hay que probarlo con un archivo grande entre discos distintos antes de darlo
  por hecho.
- Validar que la carpeta exista, sea escribible y tenga espacio; no permitir el cambio
  mientras hay una grabación en curso.

## 2. Subir el bitrate de grabación

**Estado: en hold desde el 28/07/2026.** Parche en
`_programa\bitrate_fix_configure_obs.patch`.

Hoy se graba a 2500 kbps. Subir la calidad lleva el dataset de ~1,1 GB/h a 11–20 GB/h, o
sea que multiplica por diez la subida y el costo de S3. Retomar solo si un cliente lo pide
explícitamente y el número cierra.

---

## Decisiones tomadas de NO hacer

- **Borrar carpetas de grabaciones desde la app** (16/08/2026). Los archivos de una sesión
  quedan en solo lectura a propósito y así se mantienen; no se agrega una acción de borrado.
