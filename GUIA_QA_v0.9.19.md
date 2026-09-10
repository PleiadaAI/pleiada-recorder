# Guía de QA — Gameplay Recorder v0.9.19

## Qué hay de nuevo

Build corto sobre la v0.9.18, con lo que salió de PLE-184. Todo lo demás de la guía v0.9.18 sigue vigente.

**En la app (necesita esta versión):**

1. **Las capturas con nombres largos y parecidos ya no se confunden.** Antes, seis capturas de Halo con nombres como "Halo The Master Chief Collection 09_09_2026 23_45_12.png" llegaban como una sola. Ya no hace falta renombrar nada.
2. **Dos capturas con el mismo nombre de archivo** (desde carpetas distintas) no se pueden cargar juntas: al elegir la segunda dice "ya cargaste una imagen con ese nombre. Renombrala y volvé a elegirla".
3. **Los errores técnicos** ("Algo falló de nuestro lado") ahora explican debajo que no es un problema de las capturas y que ese intento no cuenta.

**En el servidor (ya activo, también con la v0.9.18):**

4. Si las capturas llegan con nombres que se confunden, el mensaje pide renombrarlas con nombres cortos y distintos. Con la v0.9.19 este mensaje no debería aparecer nunca.
5. Un reintento después de "Las capturas no llegaron completas" ya funciona con las mismas imágenes.

---

## Antes de empezar

- Instalar `PleiadaRecorder_Setup.exe` (build v0.9.19) sobre la versión anterior. En el título de la ventana tiene que decir **v0.9.19**.
- Cerrar sesión y volver a entrar en el Recorder.
- Órdenes de prueba: `GA-2026-021` con bono, `GA-2026-019` sin bono.

---

## M · Nombres de captura

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| M1 | Repetir el caso de Halo: seis capturas de la pantalla de controles con los nombres largos originales (sin renombrar), de un título cuyos botones de mouse sean texto. | Se analizan las seis. No aparece "no llegaron completas" ni "nombres parecidos". |
| M2 | Copiar una captura a otra carpeta con el mismo nombre y elegir las dos. | La segunda no se carga: "ya cargaste una imagen con ese nombre. Renombrala y volvé a elegirla". |
| M3 | Con la **v0.9.18**, el mismo caso M1. | Rechazo con "Los nombres de las capturas son demasiado parecidos…". Renombrarlas cortas (halo_1, halo_2…) y funciona. |

---

## N · Errores técnicos

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| N1 | Cortar la conexión a internet justo después de tocar **Analizar metadata**. | Pantalla "No se pudo analizar", recuadro "Algo falló de nuestro lado", y debajo: "No es un problema de las capturas. Este intento no cuenta: podés volver a intentar con las mismas imágenes." |
| N2 | Reconectar y tocar **Volver a intentar** → Analizar con las mismas capturas. | Se analizan normalmente. El contador de intentos no avanzó por el fallo técnico. |

---

## Smoke test — que no se haya roto nada

1. Instalar sobre la versión anterior; la app abre; el título dice **v0.9.19**.
2. Login; la lista de títulos carga; se puede elegir orden.
3. Grabar 3 minutos con `GA-2026-019`, cortar, sesión completa: **1 video + 4 CSV + `session_metadata.json`**.
4. Subir una sesión desde la pantalla de resultado y otra desde Mis grabaciones.
5. Un aporte de controles completo (caso D1 de la guía v0.9.17) termina en "Controles recibidos".

---

## Qué reportar

Para cada caso: qué probaste, qué esperabas, qué pasó, y **las capturas que mandaste** con sus nombres de archivo tal cual.

Si la app se cierra sola o se congela, mandá también los archivos de:

```
C:\Users\<tu usuario>\Documents\Pleiada Logs\
```

(`crash.log` y `faulthandler.log`)

## Datos del build

| | |
|---|---|
| Versión | **v0.9.19** |
| Reemplaza a | v0.9.18 |
| Orden de prueba con bono | `GA-2026-021` |
| Orden de prueba sin bono (control) | `GA-2026-019` |
| Tickets que cubre | PLE-184 |
