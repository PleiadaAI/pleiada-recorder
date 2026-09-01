# Cómo publicar actualizaciones del Pleiada Recorder

> Guía operativa paso a paso. Escrita para que cualquier persona del equipo pueda
> publicar una actualización sin conocimiento previo del proyecto.
> Última revisión: 2026-07-15.

---

## 1. Cómo funciona el sistema (leer una vez)

- **El push de un tag `vX.Y.Z` a GitHub ES el deploy a producción.** No hay un botón
  aparte: al pushear el tag, GitHub Actions compila los instaladores y publica el
  release automáticamente, y a partir de ese momento **toda la base instalada empieza
  a ver la actualización** la próxima vez que abra el Recorder. Hacerlo consciente.
- El CI (archivo `.github/workflows/build.yml`) genera y publica 3 archivos en cada
  GitHub Release:
  | Archivo | Qué es |
  |---|---|
  | `PleiadaRecorder_Setup.exe` | Instalador completo (app + Python + AHK + OBS). Para instalaciones nuevas / la página de descarga. |
  | `PleiadaRecorder_Update.exe` | Updater liviano (solo los scripts de la app). Lo descarga la app instalada para auto-actualizarse. |
  | `latest.json` | Manifiesto que lee la app al arrancar: versión nueva, versión mínima, URLs y hashes SHA-256. |
- **Los dos .exe salen firmados digitalmente** (SSL.com / eSigner) a nombre de
  Sunrise Advisors Generation Ltd. Lo hace el CI solo, entre compilar y publicar: no
  hay nada que hacer al publicar. Lo único a saber acá es que **si faltan los secrets
  de firma, el build de un tag falla a propósito** — un release de producción no sale
  sin firmar. Activación, detalle y troubleshooting en
  [`FIRMA_CODIGO_SSLCOM.md`](FIRMA_CODIGO_SSLCOM.md).
- La app instalada chequea al arrancar
  `https://github.com/PleiadaAI/pleiada-recorder/releases/latest/download/latest.json`.
  Si la versión del manifiesto es más nueva que la instalada, muestra el banner
  "Nueva versión disponible" con **Actualizar ahora / Más tarde**.
- **Actualización OPCIONAL** (el caso normal): el usuario puede tocar "Más tarde" y
  seguir usando la app.
- **Actualización MANDATORIA**: si la versión instalada es **menor** que el campo
  `min_version` del manifiesto, la app bloquea el botón de grabar (y el hotkey) y
  muestra "Esta versión ya no es compatible. Actualizá para seguir grabando." hasta
  que el usuario actualice.
- **La versión vive en UN solo lugar editable:** `VERSION = "vX.Y.Z"` al inicio de
  `pleiada_installer/files/pleiada_app.pyw`. El tag de git tiene que coincidir con
  ese valor — si no coinciden, **el CI falla el build a propósito** (es la red de
  seguridad para que nunca salga un release desalineado).

---

## 2. Publicar una actualización OPCIONAL (procedimiento estándar)

### Paso 1 — Preparar el repo
```
cd C:\Users\mspin\Documents\pleiada-recorder
git checkout main
git pull origin main
```
Desarrollar el cambio en una rama (`git checkout -b feature/mi-cambio`) y mergear a
`main` cuando esté probado.

### Paso 2 — Subir la versión
Editar `pleiada_installer/files/pleiada_app.pyw`, línea ~14:
```python
VERSION = "v0.9.0"      # ← la versión nueva, SIEMPRE con el prefijo "v"
```
Convención: `vX.Y.Z`. Subir `Y` para features, `Z` para fixes chicos.

### Paso 3 — Escribir el CHANGELOG
Agregar una sección **arriba de todo** en `CHANGELOG.md` con este formato exacto
(el CI la extrae para las notas del release):
```markdown
## V9.0 — 20/07/2026

### Título del cambio
- Detalle...
```
⚠️ El encabezado tiene que ser `## V` + la versión **sin** el `v0.` inicial:
tag `v0.9.0` → encabezado `## V9.0`. Si el CI no encuentra la sección, el release
sale con la nota genérica "Ver CHANGELOG.md para detalles." (no falla).

### Paso 4 — Decidir: ¿OPCIONAL o MANDATORIA?
**Decisión obligatoria antes de cada release, y la toma Martín** — quien publique
debe preguntarle release por release, nunca asumirla. Opcional = no tocar nada
(caso por defecto). Mandatoria = seguir además la sección 3 antes de commitear.

### Paso 5 — Commit y push a main
```
git add -A
git commit -m "v0.9.0 - descripción corta del release"
git push origin main
```

### Paso 6 — Tag = disparar el deploy
```
git tag v0.9.0
git push origin v0.9.0
```
Esto arranca el build en GitHub Actions (~10-15 min).

### Paso 7 — Verificar (checklist post-release)
1. https://github.com/PleiadaAI/pleiada-recorder/actions → el workflow del tag en verde.
   - Si falla en "Validate version consistency": el tag no coincide con `VERSION`
     en pleiada_app.pyw. Corregir el archivo, commitear, borrar y recrear el tag:
     `git tag -d v0.9.0 && git push origin :refs/tags/v0.9.0` y repetir el Paso 6.
2. https://github.com/PleiadaAI/pleiada-recorder/releases → el release nuevo con los
   **3 assets** (Setup.exe, Update.exe, latest.json).
3. Abrir `https://github.com/PleiadaAI/pleiada-recorder/releases/latest/download/latest.json`
   en el navegador y confirmar que `version` es la nueva.
4. En el log del workflow, paso **Verify Authenticode signature**: los dos .exe tienen
   que decir `Valid`, mostrar `Firmante: CN=Sunrise Advisors Generation Ltd, ...` y
   una línea `Timestamp:`. (Si alguno quedó `NotSigned` el build ya falló solo y no
   hay release.)
5. Abrir el Recorder en una máquina con la versión anterior → debe aparecer el banner
   "Nueva versión disponible" → "Actualizar ahora" → un prompt de UAC —que ahora dice
   **Sunrise Advisors Generation Ltd** en vez de "Editor desconocido"— → la app se
   reinicia actualizada (verificar la versión en la barra de título).

---

## 3. Publicar una actualización MANDATORIA (bloquea versiones viejas)

Es el mismo procedimiento de la sección 2, con UN paso extra antes del commit:

Editar `pleiada_installer/min_version.txt` (una sola línea):
```
v0.9.0
```

Semántica: **toda versión instalada MENOR que ese valor queda bloqueada para grabar**
hasta actualizarse. Normalmente se pone la misma versión que se está publicando
(= "todos deben tener esta o más nueva"), pero puede ser una anterior si versiones
intermedias siguen siendo aceptables.

Cuándo forzar (criterio):
- Cambió el schema de metadata de forma incompatible y el AI Lab no puede consumir
  datos de versiones viejas.
- Un bug de una versión anterior produce datasets inválidos.
- Cambios de seguridad / backend que rompen versiones viejas (ej. API del uploader).

Cuándo NO forzar: features nuevos, mejoras de UI, fixes menores. El update forzado
interrumpe al usuario — usarlo con criterio.

⚠️ `min_version` NO se puede subir "sin release": vive dentro del `latest.json` que
se publica con cada release. Para forzar, siempre hay que publicar una versión.

---

## 4. Qué ve el usuario (para soporte)

| Situación | Qué ve |
|---|---|
| Hay versión nueva (opcional) | Banner "Nueva versión disponible (vX.Y.Z)" con "Actualizar ahora" y "Más tarde". |
| Su versión < min_version | Banner "Esta versión ya no es compatible. Actualizá para seguir grabando." + botón de grabar deshabilitado. |
| Toca "Actualizar ahora" | Barra "Descargando actualización... N%" (cancelable) → "El Recorder se va a cerrar para actualizarse. Se abre solo al terminar." → **1 prompt de UAC** → la app se reinicia actualizada. |
| Rechaza el UAC | "No se pudo descargar la actualización. Probá de nuevo más tarde." con "Reintentar". |
| Sin internet | No pasa nada: la app funciona normal y reintenta el chequeo en el próximo arranque. |
| Está grabando y toca "Actualizar ahora" | Aviso "Terminá la grabación antes de actualizar." |

Notas técnicas: la descarga va a `%TEMP%` y se verifica con SHA-256 contra el
manifiesto antes de ejecutarse (si no coincide, se descarta). El updater cierra el
Recorder, copia los archivos a `C:\Program Files\Pleiada Recorder` y lo relanza.

---

## 5. Si algo sale mal (rollback)

**Regla de oro: NUNCA borrar el último release ni sus assets a mano.** La app apunta
siempre a `releases/latest`; un release manco (sin latest.json o sin Update.exe)
deja el chequeo fallando en silencio (inofensivo) pero sin camino de actualización.

Para "volver atrás" una versión mala: **publicar una versión NUEVA con el fix**
(ej. salió `v0.9.0` rota → publicar `v0.9.1`). La base instalada que ya se actualizó
a la rota recibe la buena por el mismo canal. Si la rota genera datasets inválidos,
publicar la `v0.9.1` como **mandatoria** (`min_version = v0.9.1`) para sacar a todos
de la versión mala.

Si el build del tag falló y no salió el release: no pasó nada en producción — el
release anterior sigue siendo `latest`. Corregir y re-taggear (ver Paso 7.1).

---

## 6. Probar localmente ANTES de publicar (opcional pero recomendado)

Requiere Inno Setup 6 instalado (`ISCC.exe`).

```powershell
cd C:\Users\mspin\Documents\pleiada-recorder\pleiada_installer
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DLITE /DAppVersion=0.9.0 setup.iss
```
Genera `Output\PleiadaRecorder_Update.exe`. Ejecutarlo sobre una instalación
existente: debe cerrar el Recorder, copiar los archivos y relanzarlo. (El instalador
completo requiere además bajar los 3 instaladores de dependencias a `deps\` — en
general no hace falta compilarlo local: lo hace el CI.)

Chequeo rápido de sintaxis de la app antes de commitear:
```powershell
python -m py_compile pleiada_installer\files\pleiada_app.pyw
```

---

## 7. Reglas del proyecto que aplican a los releases

- **Texto visible al usuario**: cualquier frase nueva de UI se confirma con Martín
  antes de publicar.
- El repo es **público** con licencia source-available: el código se puede leer,
  no reutilizar. No commitear secretos (tokens de escritura, claves AWS, etc.).
- Los releases se publican SIEMPRE como release normal (no draft, no pre-release):
  un pre-release no aparece en `releases/latest` y la base instalada no lo vería.
- El CI borra automáticamente los .exe y latest.json de releases viejos (los tags e
  historial quedan). No hace falta limpiar a mano.
- Limitación conocida del CHANGELOG en CI: el encabezado se deriva del tag quitando
  el prefijo `v0.` — el día que exista una versión `v1.0.0`, revisar el paso
  "Extract release notes" de `build.yml`.
