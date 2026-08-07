# QA — Gameplay Recorder v0.8.11 (subidas en paralelo + blocksize)

Build: `Output\PleiadaRecorder_Setup.exe` · SHA256 `B1B3572D…` · estampado 0.8.11
Backend: `LAMBDA_VERSION=2026-08-05.4`

## Antes de empezar
El cliente nuevo **funciona con la Lambda vieja y con la nueva** (verificado el 05/08 con
una subida real de 200 MB contra producción sin deployar). Así que el orden no es crítico,
pero conviene deployar el backend primero para probar el camino definitivo.

---

## 1. Lo medido automáticamente (ya hecho, no hace falta repetir)

| | v0.8.10 | v0.8.11 |
|---|---|---|
| 200 MB contra producción | 1,35 MB/s (148 s) | **21,37 MB/s (9,4 s)** |

Mismo archivo, misma ruta, uno detrás del otro. Mejora **15,9x**.
130 tests de backend + 8 del uploader paralelo, todos en verde.

---

## 2. Lo que hay que probar a mano

### 2.1 Subida completa de una sesión real — **lo principal**
- [ ] Grabar una sesión (o usar una ya grabada sin subir) y subirla desde la app.
- [ ] La barra avanza **sin saltos raros hacia atrás** y llega a 100%.
- [ ] La velocidad que muestra es del orden de MB/s, no de KB/s.
- [ ] Termina en "listo" y la sesión aparece en el dashboard con las horas bien contadas.
- [ ] Revisar `Documentos\Pleiada Logs\upload.log`: tiene que haber una línea de resumen
      por archivo con MB, segundos, MB/s, partes y reintentos.

### 2.2 Cancelar
- [ ] Empezar una subida grande y tocar Cancelar a mitad.
- [ ] Vuelve a la pantalla anterior, y la sesión **NO** queda registrada en el dashboard.
- [ ] En la consola de S3, la carpeta de esa sesión no quedó con el MP4.

### 2.3 Reintento
- [ ] Cortar el wifi a mitad de una subida y volver a conectarlo a los pocos segundos.
- [ ] La subida se recupera sola, o falla con mensaje claro y el botón Reintentar funciona.
- [ ] `upload.log` registra los FALLO/OK de las partes afectadas.

### 2.4 Sesión larga — **el caso que antes fallaba entero**
- [ ] Subir una sesión de 1 hora (11–20 GB con el perfil actual de OBS).
- [ ] Antes esto moría cerca del final por permisos vencidos a las 6 h. Ahora los permisos
      se piden por lotes: tiene que terminar completa.
- [ ] Verificar en S3 que el MP4 quedó con el tamaño correcto (no truncado).

### 2.5 Doble subida y no-regresión
- [ ] Volver a subir la misma sesión: tiene que decir que ya estaba subida.
- [ ] Entrar a Ajustes durante una subida: sigue bloqueado (fix de v0.8.7).
- [ ] Un Recorder v0.8.10 sin actualizar sigue subiendo bien contra la Lambda nueva.

### 2.6 Si alguien reporta que le va lento igual
Bajar la concurrencia en `%APPDATA%\Pleiada\settings.json`:
```json
{ "upload_concurrency": 1 }
```
Acepta de 1 a 16. No tiene interfaz a propósito: es una válvula de soporte.

---

## 3. Pendiente de decisión (NO hecho)
- `Output\latest.json` sigue en v0.8.8 y `min_version.txt` en v0.8.10. Hay que
  regenerarlos al publicar, y decidir si v0.8.11 es **actualización obligatoria**.
  Dado que arregla el bug que rompe las sesiones de 1 h, la recomendación es que sí.
- Release de GitHub + push de los dos repos: requiere OK explícito.
- Verificar si el bucket tiene la regla de ciclo de vida `AbortIncompleteMultipartUpload`.
  Sin ella, las subidas que vinieron fallando dejaron partes huérfanas que se facturan.
