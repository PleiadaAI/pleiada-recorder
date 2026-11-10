# Gameplay Recorder

**Gameplay Recorder** es la herramienta oficial del programa **[Gameplay Alliance](https://gameplayalliance.gg)**, desarrollada por [Pleiada](https://pleiada.ai). Graba tu partida con OBS y registra tu teclado y tu mouse, todo sincronizado, para que tu forma de jugar sirva como dato para entrenar agentes de Inteligencia Artificial.

> Versión vigente: **v0.10.4**. La guía completa, con capturas de cada pantalla, está en **[recorder.gameplayalliance.gg](https://recorder.gameplayalliance.gg/)**. El historial de versiones está en [`CHANGELOG.md`](CHANGELOG.md).

**[⬇ Descargar el instalador para Windows](https://github.com/PleiadaAI/pleiada-recorder/releases/latest/download/PleiadaRecorder_Setup.exe)** · Windows 10 / 11 · Gratuito

---

## Qué hace

- **Graba en un clic.** Iniciás y detenés la grabación desde una ventana flotante (o con **F9** / **F10** sin salir del juego), sin tocar OBS.
- **Reconoce el título solo.** Mira qué ventana está capturando OBS y averigua qué estás jugando. Si no puede, te pregunta.
- **Verifica cada sesión.** Al terminar comprueba que video y logs estén sincronizados, y revisa pantallas negras, FPS, inactividad (AFK) y otros aspectos técnicos. Lo que no pasa, no sale de tu PC.
- **Te avisa mientras grabás.** Si OBS deja de grabar, si el título pierde el primer plano o si queda poco espacio en el disco, lo ves en el momento.
- **Sube la sesión** a la orden en la que estás inscripto, desde la misma ventana o más tarde desde **Mis grabaciones**.
- **No pisa tu OBS.** Mientras graba usa su propio perfil de OBS y, al terminar, vuelve al que tenías.
- **Se mantiene al día.** Al arrancar se fija si hay una versión nueva y te la ofrece desde la misma ventana.

---

## Primeros pasos

### 1. Instalá

Descargá [`PleiadaRecorder_Setup.exe`](https://github.com/PleiadaAI/pleiada-recorder/releases/latest/download/PleiadaRecorder_Setup.exe) y ejecutalo. El instalador está **firmado digitalmente** e instala, si no los tenés:

- [OBS Studio](https://obsproject.com/) — graba el video.
- [AutoHotkey v2](https://www.autohotkey.com/) — registra teclado y mouse.
- Python 3.12 y sus dependencias.

Los dos primeros son aplicaciones de código abierto, usadas por millones de personas. Al terminar se abre la guía en tu navegador.

### 2. Configurá OBS (una sola vez)

1. Abrí el título que vas a grabar.
2. Si es la primera vez que abrís OBS y aparece el asistente de configuración automática, podés cancelarlo: **la resolución (1080p), los FPS (60) y la calidad los ajusta el Recorder solo**, antes de cada grabación. También silencia el micrófono.
3. En **Fuentes** (abajo a la izquierda) hacé clic en **+** y elegí **Captura de Videojuego** (o *Captura de juego* / *Game Capture*, según la versión).
4. En sus propiedades, en **Modo** elegí **Capturar ventana específica** y en **Ventana**, la de tu título.

> ⚠ **"Capturar ventana específica" es obligatorio.** Es el único modo en el que OBS informa qué ventana y qué ejecutable está capturando, que es lo que el Recorder usa para reconocer el título.

### 3. Inscribite en una orden

Las órdenes abiertas están en **[gameplayalliance.gg/dashboard](https://gameplayalliance.gg/dashboard/)**. Sin inscripción podés grabar igual, pero la sesión no se puede subir hasta que te inscribas en una orden que acepte ese título.

### 4. Grabá

1. Abrí **Gameplay Recorder** desde el escritorio e iniciá sesión con el email con el que te registraste (te llega un código; si no lo ves, revisá Spam).
2. Con el título identificado, tocá **Iniciar grabación** o apretá **F9**. El botón te dice antes de grabar si la sesión va a una orden o si es una *grabación libre*.
3. Jugá con la ventana del título **en primer plano**: si cambiás de ventana, no se registran tus teclas ni tu mouse, y el Recorder te avisa.
4. Para terminar, tocá **Detener grabación** o apretá **F10**. **Nunca la detengas desde OBS.**

Cada sesión tiene que durar **al menos 5 minutos**. La duración máxima es de 60 minutos (se puede bajar en Ajustes); al llegar, la grabación se detiene sola y, si lo activás, arranca una nueva.

### 5. Revisá y subí

El Recorder verifica la sesión automáticamente. Si está **lista para enviar**, revisá que no haya nada personal en los archivos y tocá **Subir Data Set**. Si **no es apta**, te dice el motivo y no se envía.

> ⚠ No modifiques los archivos de la sesión: si cambiás alguno, se rechaza.

---

## Ajustes (⚙)

| Opción | Qué hace |
|---|---|
| Atajos de teclado | Cambiar **F9** (iniciar) y **F10** (detener). Funcionan aunque el Recorder no esté en primer plano, incluso en pantalla completa, y no se registran en los logs. |
| Duración máxima de sesión | Hasta 60 minutos. |
| Reiniciar grabación automáticamente | Al llegar a la duración máxima, arranca una sesión nueva. |
| DPI de tu mouse (opcional) | Ayuda a interpretar los movimientos del mouse en el dataset. |

También muestra la versión instalada y permite cerrar sesión.

---

## Metadata de controles

Si grabás un título que todavía no tiene su mapa de controles, el Recorder te propone compartir una captura de la pantalla de controles (con los controles por defecto). El aporte se valida cuando otro usuario manda los mismos controles. Las condiciones vigentes del programa están en la [guía](https://recorder.gameplayalliance.gg/#metadata).

---

## ¿Dónde se guardan los archivos?

```
Documentos\Pleiada Recordings\
  └── <Título>_<fecha>__<hora> recording\
        ├── <video>.mp4             ← video (MP4 fragmentado)
        ├── mouse_log.csv           ← posición y botones del mouse
        ├── mouse_delta_log.csv     ← movimiento del mouse por hardware (Raw Input)
        ├── key_log.csv             ← teclas presionadas y soltadas
        ├── video_timeline.csv      ← línea de tiempo del video
        └── session_metadata.json   ← metadata de la sesión
```

Los registros de diagnóstico quedan en `Documentos\Pleiada Logs`.

> Las carpetas siguen diciendo "Pleiada" a propósito: ahí están las sesiones ya grabadas.

---

## Privacidad

Lo que se graba es **información anónima**. Aun así, **es tu responsabilidad** no mostrar en pantalla ni escribir con el teclado nada privado (contraseñas, chats, datos bancarios, etc.). Si algo así llega a nuestros servidores, se elimina de forma permanente y ese dataset queda fuera de cualquier uso comercial.

| Qué se registra | Cómo |
|---|---|
| Video | La ventana del título que capturás en OBS. Queda en tu PC hasta que lo subís vos. |
| Audio | Solo el del juego (captura por proceso). El micrófono y el audio del escritorio se silencian, para que no entren voces ni chats de voz. |
| Teclado | Nombres de teclas (`W`, `Space`, `LShift`), **solo mientras el título está en primer plano**. Nunca texto. |
| Mouse | Posición, movimiento por hardware, botones y rueda. |
| Equipo | Specs de hardware y sistema operativo, velocidad del puntero, distribución del teclado y modelo de mouse y teclado. Sin datos que te identifiquen. |

No se accede a la cámara, el portapapeles, el historial de navegación ni a ningún otro dato personal.

---

## Preguntas frecuentes

**El Recorder se queda en "Esperando el título".**
La fuente de OBS no está en **Capturar ventana específica**, o no apunta a la ventana del título. Revisá el paso 2.

**La sesión se rechazó por "Sin teclado ni mouse".**
Pasa si el título corre como administrador o su anticheat bloquea la captura: probá abrir el Recorder como administrador. El joystick todavía no se registra.

**La sesión se rechazó por "Título fuera de primer plano".**
Otra ventana (un overlay, el navegador, el propio Recorder) tuvo el foco gran parte de la sesión. Hacé clic en la ventana del título antes de jugar y no cambies de ventana mientras grabás.

**OBS dejó de grabar en medio de la sesión.**
El Recorder corta la sesión y te avisa. Revisá en OBS si muestra algún error (por ejemplo, falta de espacio en el disco) y volvé a grabar.

---

## Contacto

- Soporte: [gg_support@gameplayalliance.gg](mailto:gg_support@gameplayalliance.gg)
- Programa: [gameplayalliance.gg](https://gameplayalliance.gg)
- Términos y condiciones: [gameplayalliance.gg/terminos-condiciones](https://gameplayalliance.gg/terminos-condiciones)

---

## Para devs

El código se publica para que cualquiera pueda **leerlo y auditarlo**. No es open source: ver [Licencia](#licencia).

### Componentes

Todo lo que se instala está en `pleiada_installer/files/`:

| Archivo | Qué es |
|---|---|
| `pleiada_app.pyw` | **La app** (Tkinter, un solo archivo): login por código, identificación del título, grabación, verificación, metadata y subida. Incluye el cliente de OBS WebSocket v5 (puerto 4455). `VERSION` vive acá y es la única fuente de verdad de la versión. |
| `input_logger.ahk` | Logger headless (AutoHotkey v2): hooks low-level + Raw Input, para capturar en fullscreen exclusivo. Filtra el input al ejecutable del título y deja el estado del foco para el aviso en vivo. |
| `pleiada_sync_limits.py` | Fuente de verdad única de los umbrales y gates que deciden si una sesión es válida, y lector de MP4. La comparten la app y el checker. |
| `obs_encoding.py` | Fuente de verdad única de la configuración de grabación (encoder, calidad, resolución y FPS). |
| `obs_control.py` | Wrapper CLI del OBS WebSocket (start/stop, mueve el MP4). |
| `sync_markers.py` | Anclas medidas entre el reloj del input y el video (marcador visible en la escena). |
| `input_devices.py` | Metadata de los dispositivos de entrada (velocidad del puntero, layout, VID/PID, tasa de sondeo). |
| `pleiada_api.py` | Cliente HTTP del backend: login, órdenes, URLs presignadas. |
| `session_uploader.py` | Subida a S3 con URLs presignadas (multipart en paralelo para archivos grandes). |
| `configure_obs.py` | Configura OBS: WebSocket, perfil y escena "Pleiada". Corre desde el instalador completo y desde el de actualización. |
| `pleiada_check.pyw` | Synch Checker: verificador standalone de una sesión (Tkinter + OpenCV). |
| `games_list.json` | Lista de títulos bundleada (respaldo). |

El backend no está en este repositorio.

### Build

Requisitos: Windows 10/11 x64, [Inno Setup 6](https://jrsoftware.org/isdl.php), PowerShell 5.1+.

```powershell
cd pleiada_installer
python update_games_list.py        # obligatorio antes de cada build
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DAppVersion=X.Y.Z setup.iss           # instalador completo
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DLITE /DAppVersion=X.Y.Z setup.iss    # actualización (LITE)
```

`/DAppVersion` tiene que coincidir con `VERSION` en `pleiada_app.pyw`. El completo necesita los instaladores de Python, AutoHotkey y OBS en `pleiada_installer/deps/` (`BuildPleiadaSetup.ps1` los descarga).

**CI/CD (GitHub Actions):** pushear un tag `vX.Y.Z` compila los dos instaladores, los **firma** y publica el Release con `PleiadaRecorder_Setup.exe`, `PleiadaRecorder_Update.exe` y `latest.json`, que es lo que lee la app para actualizarse. El build falla si el tag no coincide con `VERSION`.

### Dependencias

| Paquete | Versión | Licencia | Uso |
|---|---|---|---|
| [OBS Studio](https://obsproject.com/) | 32.1.2 | GPL-2.0 | Grabación de video y audio |
| [AutoHotkey v2](https://www.autohotkey.com/) | 2.0.24 | GPL-2.0 | Hooks de teclado y mouse |
| [Python](https://www.python.org/) | 3.12.8 | PSF-2.0 | Runtime de la app |
| [websocket-client](https://github.com/websocket-client/websocket-client) | latest | Apache-2.0 | OBS WebSocket v5 |
| [Pillow](https://python-pillow.org/) | latest | HPND | Imágenes |
| [opencv-python](https://github.com/opencv/opencv-python) | latest | MIT | Análisis de frames (Synch Checker) |
| [Inno Setup](https://jrsoftware.org/isinfo.php) | 6.x | ISL | Compilador del instalador (solo build) |

---

## Licencia

**Source-available**: se puede leer y auditar, no usar, copiar, modificar ni redistribuir. Ver [`LICENSE`](LICENSE). El uso del programa instalable se rige por los [términos y condiciones de Gameplay Alliance](https://gameplayalliance.gg/terminos-condiciones).

Copyright © 2026 Pleiada. Todos los derechos reservados.
