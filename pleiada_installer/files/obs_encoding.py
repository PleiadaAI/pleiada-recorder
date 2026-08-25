"""
obs_encoding.py — Configuracion de grabacion del dataset. Fuente de verdad unica.

Compartido entre:
  · pleiada_app.pyw   — la re-aplica antes de CADA grabacion
  · configure_obs.py  — la escribe en disco al instalar y al actualizar (LITE incluido)

Igual que `pleiada_sync_limits.py` con los gates: si un valor de grabacion se
toca, se toca ACA y en ningun otro lado.


PORQUE ESTO EXISTE (25-08-2026)
================================
Hasta la v0.9.10 el perfil grababa a 2500 kbps CBR. A 1080p60 eso destruye el
detalle: medido, VMAF 37,2 de media y 6,4 en el peor frame del clip. La comunidad
lo reportaba como "videos de baja resolucion" — el sintoma era correcto, la causa
no. Subir el bitrate a 8000 sin cambiar nada mas ya lleva el VMAF a 75,0 y saca
al material de inservible, pero deja el problema de fondo.

El problema de fondo es el RATE CONTROL, no el numero. CBR reparte mal: gasta
bits de mas en las escenas faciles y se queda sin ninguno justo en las de
movimiento, que son las que tienen valor para entrenar. Por eso a 8000 CBR el
peor frame seguia en 22,6 mientras la media ya estaba en 75.


LA MEDICION
===========
20 s de material real, re-codificados desde una referencia comun. VMAF medio /
VMAF del peor frame del clip. Mismo contenido en todas las filas, la unica
variable es la config:

    CBR 8000 (solo subir el numero)        3,33 GB/h   75,0 / 22,6
    NVENC VBR 8000 techo 12000             3,45 GB/h   83,4 / 56,5   <- ESTE
    x264  CRF 23 techo 8000, preset fast   3,48 GB/h   83,8 / 59,2   <- ESTE

Por el MISMO peso que costaria solo subir el numero: +8 de media y el peor frame
2,5 veces mejor. La calidad sale gratis; lo unico que cambia es como se reparten
los bits.

Dos cosas que salieron de medir y conviene no volver a descubrir:

  · NO HAY UN VALOR UNICO PAREJO PARA TODA LA FLOTA. El mismo "CQP/CRF 23" da
    VMAF 86 a 5,2 GB/h en x264 y VMAF 98 a 9,9 GB/h en NVENC. Cualquier fix con
    un solo numero para todos le erra a la mitad de las maquinas. De ahi que la
    config sea por familia de GPU.
  · EL PRESET DE x264 ES CALIDAD GRATIS. `fast` contra `veryfast` da +7 de media
    y +17 en el peor frame POR EL MISMO TAMAÑO. Cuesta CPU, asi que solo se usa
    donde no hay encoder por hardware — que es justo donde la CPU esta libre.


PORQUE MODO AVANZADO Y NO SIMPLE
=================================
El modo Simple de OBS **no puede expresar calidad constante con techo**. Sus
unicas opciones son:

  · RecQuality=Stream  -> CBR con VBitrate (lo que hacemos hoy)
  · RecQuality=Small   -> CRF/CQP 23, SIN techo
  · RecQuality=HQ      -> CRF/CQP 16, SIN techo

Ojo con los nombres, que estan invertidos respecto de la UI: `HQ` es "calidad
indistinguible, ARCHIVO GRANDE" (el mas pesado que no es lossless) y `Small` es
"alta calidad, tamaño medio". Elegir `HQ` es lo que hizo que el fix de julio
midiera 11-20 GB/h y quedara en hold un mes.

Sin techo, en NVENC `Small` da ~7 GB/h reales: una hora de sesion tarda mas de
una hora en subirse con 10 Mbps de upstream, y eso rompe al uploader.

En modo Avanzado los parametros del encoder viven en `recordEncoder.json`, donde
si se puede pedir calidad constante CON techo. Como efecto lateral, esto arregla
tambien el problema de los dos codecs: hasta ahora `VBitrate`/`RecQuality` se
escribian solo en [SimpleOutput], asi que quien tuviera OBS en Avanzado grababa
con lo que hubiera —medido: 3 muestras H.264 a 2,5 Mbps y una HEVC a 16 Mbps el
mismo dia—. Ahora los dos modos quedan bajo control.

Todo lo de este archivo esta VERIFICADO CONTRA OBS REAL (32.1.2): se escribio la
config, se grabo, y se leyo del log de OBS que aplico exactamente estas claves.
Lo que OBS ignora en silencio quedo documentado abajo.
"""

import json
import os
import subprocess


# ── Deteccion de GPU ─────────────────────────────────────────────────────────

_FAMILIA_CACHE = None


def familia_gpu():
    """
    "nvidia" | "amd" | "intel" | "" (sin GPU con encoder conocido).

    Cacheada: esto corre antes de CADA grabacion y lanzar PowerShell cuesta
    ~1 s. Se calcula una vez por proceso.

    Se consulta por CIM y no por wmic: wmic esta deprecado y ya no viene en
    algunas builds de Win11 24H2+ (26100+), donde la llamada falla en silencio.
    Se deja wmic de fallback para Windows viejos. `_meta_hardware()` en
    pleiada_app.pyw todavia usa wmic solo — no es critico (es telemetria), pero
    esta anotado en BACKLOG.md.

    OJO: hay que mirar TODOS los nombres, no el primero. En una maquina real el
    primero era "Meta Virtual Monitor" y la NVIDIA venia segunda.
    """
    global _FAMILIA_CACHE
    if _FAMILIA_CACHE is not None:
        return _FAMILIA_CACHE
    _FAMILIA_CACHE = _detectar_familia()
    return _FAMILIA_CACHE


def _detectar_familia():
    nombres = ""
    for cmd in (
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         "(Get-CimInstance Win32_VideoController).Name"],
        ["wmic", "path", "win32_VideoController", "get", "name"],
    ):
        try:
            out = subprocess.run(
                cmd, capture_output=True, timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            nombres = (out.stdout or b"").decode(errors="ignore").lower()
            if nombres.strip():
                break
        except Exception:
            continue

    # Orden deliberado: si hay NVIDIA y una integrada Intel, gana NVIDIA.
    if any(t in nombres for t in ("nvidia", "geforce", "rtx", "gtx", "quadro")):
        return "nvidia"
    if any(t in nombres for t in ("radeon", "amd ", "firepro")):
        return "amd"
    if "intel" in nombres:
        return "intel"
    return ""


# ── Encoders de OBS por familia ──────────────────────────────────────────────
# Los ids salen del propio OBS ("Available Encoders" en su log). Se fija H.264 a
# proposito: HEVC rinde mejor por byte, pero es un cambio de formato de ENTREGA
# y hay que consultarlo con el cliente antes. Hoy HEVC esta apareciendo sin que
# nadie lo decidiera, en las maquinas que quedaron en modo Avanzado, y eso es el
# peor escenario: medio dataset en un codec y medio en otro.

ENCODER_AVANZADO = {
    "nvidia": "obs_nvenc_h264_tex",
    "amd":    "h264_texture_amf",
    "intel":  "obs_qsv11_v2",
    "":       "obs_x264",
}

# Equivalentes de modo Simple. No se usan para grabar (grabamos en Avanzado),
# pero se dejan escritos para que el perfil quede coherente si alguien vuelve a
# Simple a mano.
ENCODER_SIMPLE = {
    "nvidia": "nvenc",
    "amd":    "amd",
    "intel":  "qsv",
    "":       "x264",
}


# ── Parametros del encoder de grabacion (recordEncoder.json) ─────────────────
# TECHO: 12000 kbps de pico, 8000 de objetivo. Da 3,45-3,48 GB/h en el material
# mas exigente y menos en el resto, que es exactamente lo que se busca — el
# techo solo tiene que morder en las escenas dificiles.
#
# keyint_sec=2 no se toca: `pleiada_sync_limits.video_stillness` agrupa en
# ventanas de 5 s asumiendo un keyframe cada ~4 s o menos.

_TECHO_KBPS      = 12000   # pico permitido, encoders por hardware (VBR)
_OBJETIVO_KBPS   = 8000    # objetivo, encoders por hardware (VBR)
_X264_TECHO_KBPS = 8000    # techo VBV de x264 (ver la nota en el bloque x264)
_KEYINT_SEG      = 2


def record_encoder_settings(fam=None):
    """
    Contenido de `recordEncoder.json` para la familia de GPU dada.

    VERIFICADO contra OBS 32.1.2 leyendo su log despues de grabar:

      NVIDIA -> rate_control: VBR / bitrate: 8000 / max_bitrate: 12000 /
                keyint: 120 / preset: p5 / tuning: hq / multipass: qres /
                profile: high / b-frames: 2

      x264   -> rate_control: CRF / crf: 23 / preset: fast / profile: high /
                keyint: 120 / custom settings: vbv-maxrate=8000 vbv-bufsize=16000

    ⚠ QUE IGNORA OBS, comprobado: en NVENC la clave `cqlevel` se descarta en
    silencio. NVENC en OBS **no sabe hacer calidad constante con techo** (lo que
    en ffmpeg seria `-rc vbr -cq N -b:v 0 -maxrate X`); lo mas cerca que llega es
    VBR con objetivo y techo, que es lo que queda escrito aca. Si en algun
    momento OBS lo soporte, revisar: con capped-CQ real la misma calidad salia a
    3,80 GB/h con el peor frame en 58,3.

    ⚠ AMD (AMF) e INTEL (QSV) estan SIN MEDIR: no habia hardware para probarlos.
    Salen calibrados de la ronda de QA — hasta entonces, provisorios.

    PERO EL RIESGO ESTA ACOTADO, y conviene entender por que antes de asustarse:
    las tres claves que controlan el PESO —`rate_control`, `bitrate`,
    `max_bitrate`— estan confirmadas en las tres familias (se leyeron de los
    locales de obs-nvenc, obs-ffmpeg/AMF y obs-qsv11 en una instalacion real de
    OBS 32.1.2). O sea que el techo de 12.000 kbps aplica si o si, y el peor caso
    en AMD/Intel es que el material salga con un poco mas o menos de calidad de
    la buscada — no que se dispare el tamaño ni que la grabacion falle.

    Lo que si es extrapolado son las perillas de calidad/velocidad, y ahi OBS ya
    nos mostro como se comporta: si no reconoce un valor, lo descarta en silencio
    y usa su default. Valores validos, leidos del propio OBS:
      · AMF  `preset`:       speed | balanced | quality | highQuality
      · QSV  `target_usage`: TU1 (mejor calidad) .. TU7 (mas rapido)
    ⚠ El primer intento para QSV fue `"balanced"` copiando la nomenclatura de
    AMF, y **esta mal**: QSV no usa esos nombres. Es justo la clase de error que
    OBS no reporta.
    """
    fam = familia_gpu() if fam is None else fam

    if fam == "nvidia":
        return {
            "rate_control": "VBR",
            "bitrate":      _OBJETIVO_KBPS,
            "max_bitrate":  _TECHO_KBPS,
            "keyint_sec":   _KEYINT_SEG,
            "preset2":      "p5",     # p6/p7 no mejoran nada cuando el techo
                                      # muerde: medido 85,0 / 85,0 / 85,1
            "tune":         "hq",
            "multipass":    "qres",
            "profile":      "high",
            "bf":           2,
            "lookahead":    False,
            "psycho_aq":    True,
        }

    if fam == "amd":
        return {
            "rate_control": "VBR",
            "bitrate":      _OBJETIVO_KBPS,
            "max_bitrate":  _TECHO_KBPS,
            "keyint_sec":   _KEYINT_SEG,
            "preset":       "quality",   # speed | balanced | quality | highQuality
            "profile":      "high",
        }

    if fam == "intel":
        return {
            "rate_control": "VBR",
            "bitrate":      _OBJETIVO_KBPS,
            "max_bitrate":  _TECHO_KBPS,
            "keyint_sec":   _KEYINT_SEG,
            "target_usage": "TU4",       # TU1 (mejor calidad) .. TU7 (mas rapido)
            "profile":      "high",
        }

    # Sin encoder por hardware: x264. `fast` y no `veryfast` porque es calidad
    # gratis (+7 de media, +17 en el peor frame, mismo tamaño) y en estas
    # maquinas la CPU no esta compitiendo con NVENC/AMF/QSV.
    #
    # OJO con los numeros: NO son los mismos que arriba y no es un descuido.
    # Son dos modelos de rate control distintos. En NVENC VBR, 8000 es el
    # OBJETIVO y 12000 el techo. En x264 CRF, la calidad la fija `crf` y
    # `vbv-maxrate` ES el techo, con el bufsize al doble (la convencion de x264
    # para VBV). Los dos aterrizan en el mismo peso —3,45 y 3,48 GB/h— y en la
    # misma calidad —83,4 y 83,8—, que es justamente lo que se buscaba: un solo
    # presupuesto de peso, dos configs que caen en el mismo lugar.
    return {
        "rate_control": "CRF",
        "crf":          23,
        "keyint_sec":   _KEYINT_SEG,
        "preset":       "fast",
        "profile":      "high",
        "tune":         "",
        "x264opts":     "vbv-maxrate=%d vbv-bufsize=%d" % (
                            _X264_TECHO_KBPS, _X264_TECHO_KBPS * 2),
    }


# ── Claves del basic.ini ─────────────────────────────────────────────────────

def perfil_objetivo(fam=None):
    """
    [(seccion, clave, valor)] que tiene que tener el basic.ini del perfil.

    `rec_file_path` no esta aca: depende de la maquina y lo resuelve
    `escribir_config`, copiando lo que ya tenga [SimpleOutput].FilePath para no
    mover las grabaciones de lugar.
    """
    fam = familia_gpu() if fam is None else fam
    return [
        # Avanzado: es el unico modo donde se puede pedir calidad con techo.
        ("Output",       "Mode",           "Advanced"),

        # Lo que efectivamente graba.
        ("AdvOut",       "RecType",        "Standard"),
        ("AdvOut",       "RecEncoder",     ENCODER_AVANZADO.get(fam, "obs_x264")),
        ("AdvOut",       "RecFormat2",     "fragmented_mp4"),
        ("AdvOut",       "RecUseRescale",  "false"),
        ("AdvOut",       "RecTracks",      "1"),
        ("AdvOut",       "RecAudioEncoder", "ffmpeg_aac"),
        ("AdvOut",       "Track1Bitrate",  "160"),
        ("AdvOut",       "RecRB",          "false"),

        # Simple queda coherente por si alguien vuelve a Simple a mano. No es lo
        # que graba, pero que no quede el 2500 viejo esperando.
        ("SimpleOutput", "RecFormat2",     "fragmented_mp4"),
        ("SimpleOutput", "RecQuality",     "Small"),
        ("SimpleOutput", "RecEncoder",     ENCODER_SIMPLE.get(fam, "x264")),
        ("SimpleOutput", "VBitrate",       str(_OBJETIVO_KBPS)),
        ("SimpleOutput", "ABitrate",       "160"),
        ("SimpleOutput", "Preset",         "fast"),
    ]


VIDEO_OBJETIVO = {
    "baseWidth":      1920,
    "baseHeight":     1080,
    "outputWidth":    1920,
    "outputHeight":   1080,
    "fpsNumerator":   60,
    "fpsDenominator": 1,
}


# ── Escritura en disco ───────────────────────────────────────────────────────

def escribir_config(profile_dir, fam=None):
    """
    Deja `basic.ini` y `recordEncoder.json` del perfil como tienen que estar.

    Retorna True si hubo que CAMBIAR algo, False si ya estaba bien. Ese booleano
    es el que decide si hace falta reiniciar OBS: los parametros del encoder de
    modo Avanzado se leen al construir la salida —al arrancar OBS y al aplicar
    Ajustes—, no en cada StartRecord, asi que escribir el archivo con OBS ya
    corriendo no cambia la grabacion en curso.

    Preserva todo lo demas del ini (rutas, hotkeys, ajustes del usuario).
    """
    fam = familia_gpu() if fam is None else fam
    cambio = False

    ini_path = os.path.join(profile_dir, "basic.ini")
    # Sin basic.ini no hay perfil que corregir. No se crea uno a medias: de eso
    # se encarga configure_obs.py al instalar, y la app tiene su propio camino
    # por WebSocket (CreateProfile) si el usuario lo borro.
    if not os.path.isfile(ini_path):
        return False

    objetivo = {}
    for sec, clave, valor in perfil_objetivo(fam):
        objetivo.setdefault("[%s]" % sec, {})[clave] = valor

    # La ruta de grabacion se hereda de lo que ya use el usuario, para no mover
    # las sesiones de carpeta al pasar a Avanzado.
    destino = _leer_clave(ini_path, "[SimpleOutput]", "FilePath")
    if destino:
        objetivo.setdefault("[AdvOut]", {})["RecFilePath"] = destino
    cambio = _forzar_ini(ini_path, objetivo) or cambio

    enc_path = os.path.join(profile_dir, "recordEncoder.json")
    deseado  = record_encoder_settings(fam)
    actual   = None
    try:
        with open(enc_path, "r", encoding="utf-8") as f:
            actual = json.load(f)
    except Exception:
        actual = None
    if actual != deseado:
        try:
            os.makedirs(profile_dir, exist_ok=True)
            with open(enc_path, "w", encoding="utf-8") as f:
                json.dump(deseado, f, indent=0)
            cambio = True
        except Exception:
            pass

    return cambio


def _leer_clave(ini_path, seccion, clave):
    try:
        sec = ""
        with open(ini_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                t = line.strip()
                if t.startswith("[") and t.endswith("]"):
                    sec = t
                    continue
                if sec == seccion and t.split("=")[0].strip() == clave:
                    return t.split("=", 1)[1] if "=" in t else None
    except Exception:
        pass
    return None


def _forzar_ini(ini_path, objetivo):
    """
    Fuerza {seccion: {clave: valor}} en el ini, preservando el resto.
    Retorna True si algo cambio.

    Generaliza el `_migrate_rec_format` que habia en configure_obs.py, que solo
    sabia forzar RecFormat2. Misma leccion del 17/08: forzar una clave en una
    sola seccion deja mal a todo el que tenga OBS en el otro modo.
    """
    try:
        with open(ini_path, "r", encoding="utf-8-sig") as f:
            lineas = f.read().split("\n")
    except Exception:
        return False

    out, sec, puestas, cambio = [], "", {}, False

    def volcar(s):
        """Agrega las claves de `s` que no aparecieron, al cerrar la seccion."""
        nonlocal cambio
        if s not in objetivo:
            return
        faltan = [(k, v) for k, v in objetivo[s].items()
                  if k not in puestas.get(s, ())]
        if not faltan:
            return
        # Las claves van ANTES de la linea en blanco que separa de la seccion
        # siguiente, no despues del encabezado: si se cuelan detras de un
        # "[Video]" quedan dentro de la seccion equivocada.
        while out and not out[-1].strip():
            out.pop()
        for k, v in faltan:
            out.append("%s=%s" % (k, v))
            puestas.setdefault(s, set()).add(k)
            cambio = True
        out.append("")

    for linea in lineas:
        t = linea.strip()
        if t.startswith("[") and t.endswith("]"):
            volcar(sec)
            sec = t
            out.append(linea)
            continue
        clave = t.split("=")[0].strip()
        if sec in objetivo and clave in objetivo[sec]:
            if clave in puestas.get(sec, ()):
                continue          # duplicado: se descarta
            nuevo = "%s=%s" % (clave, objetivo[sec][clave])
            if t != nuevo:
                cambio = True
            out.append(nuevo)
            puestas.setdefault(sec, set()).add(clave)
            continue
        out.append(linea)
    volcar(sec)

    for s, claves in objetivo.items():
        if s not in puestas:
            out.append("")
            out.append(s)
            for k, v in claves.items():
                out.append("%s=%s" % (k, v))
            cambio = True

    if cambio:
        try:
            texto = "\n".join(out)
            if not texto.endswith("\n"):
                texto += "\n"       # sin esto el archivo queda sin salto final
            with open(ini_path, "w", encoding="utf-8-sig") as f:
                f.write(texto)
        except Exception:
            return False
    return cambio


# ── Centinelas de OBS ────────────────────────────────────────────────────────

def firma_config(profile_dir):
    """
    (mtime, tamaño) de los dos archivos de config. Sirve para saber si cambiaron
    sin volver a parsearlos.
    """
    out = []
    for n in ("basic.ini", "recordEncoder.json"):
        try:
            st = os.stat(os.path.join(profile_dir, n))
            out.append((round(st.st_mtime, 3), st.st_size))
        except Exception:
            out.append(None)
    return tuple(out)


def config_mas_nueva_que(profile_dir, ts):
    """
    True si `recordEncoder.json` se escribio DESPUES de `ts` (epoch en segundos),
    o sea: OBS esta corriendo con ajustes de encoder mas viejos que los del disco.

    Para que existe: `escribir_config` solo avisa de los cambios que hace ELLA.
    Pero el instalador tambien escribe esta config —es su via principal— y lo
    hace con OBS posiblemente abierto. En ese caso la app ve el archivo ya
    correcto, no cambia nada, y no reinicia OBS... que sigue corriendo con su
    config VIEJA en memoria y graba con ella. Ese es el agujero que dejaba
    grabaciones con los ajustes previos despues de actualizar.

    ⚠ SE MIRA SOLO recordEncoder.json, y NO basic.ini. Medido el 25-08-2026:
    **OBS reescribe basic.ini ~1,5 s despues de arrancar**, siempre, asi que su
    mtime queda por delante del arranque del proceso pase lo que pase y como
    señal da falso positivo permanente — lo que provocaria un reinicio de OBS
    antes de CADA grabacion. `recordEncoder.json`, en cambio, OBS no lo toca
    (verificado dejandolo correr 25 s tras el arranque), y ademas es justo el
    archivo que lleva los ajustes del encoder, que es lo que nos importa.
    """
    if not ts:
        return False
    try:
        return os.path.getmtime(
            os.path.join(profile_dir, "recordEncoder.json")) > ts
    except Exception:
        return False


def limpiar_centinelas():
    """
    Borra los centinelas huerfanos de `%APPDATA%\\obs-studio\\.sentinel`.

    OBS crea un archivo ahi al arrancar y lo borra al cerrar bien. Si queda
    huerfano —porque a OBS lo mataron a la fuerza— el arranque siguiente se
    queda en un MODAL BLOQUEANTE ("Se ha detectado un error en OBS Studio") y el
    WebSocket nunca levanta: la app espera 30 s y se rinde.

    Reproducido el 25-08-2026. `--disable-shutdown-check` NO lo evita: OBS
    igual escribe "Crash or unclean shutdown detected" y muestra el dialogo.
    Verificado que borrando los centinelas arranca limpio, con el WebSocket
    arriba en menos de 1 s.

    Aplica a cualquier `taskkill /F` sobre obs64.exe, incluido el que la app ya
    hacia para recuperar un WebSocket en mal estado.
    """
    try:
        d = os.path.join(os.environ.get("APPDATA", ""), "obs-studio", ".sentinel")
        if not os.path.isdir(d):
            return 0
        n = 0
        for nombre in os.listdir(d):
            try:
                os.remove(os.path.join(d, nombre))
                n += 1
            except Exception:
                pass
        return n
    except Exception:
        return 0
