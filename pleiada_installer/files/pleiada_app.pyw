"""
pleiada_app.pyw  â€”  Gameplay Recorder
AplicaciÃ³n unificada: login, selecciÃ³n de juego, grabaciÃ³n, sync check, empaquetado.
"""

import tkinter as tk
from tkinter import font as tkfont, ttk
import json, os, sys, stat, time, threading, subprocess, struct, glob, re, shutil, zipfile, io
import csv as _csv_mod, hashlib as _hashlib, platform as _platform
import ctypes, ctypes.wintypes
from pathlib import Path
import session_uploader
import pleiada_api
import pleiada_sync_limits as sync_limits

# â”€â”€â”€ VersiÃ³n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
VERSION = "v0.9.1"

# â”€â”€â”€ Rutas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_frozen    = getattr(sys, "frozen", False)
APP_DIR    = Path(sys.executable).parent if _frozen else Path(__file__).parent
APPDATA    = Path(os.environ.get("APPDATA", Path.home()))
AUTH_FILE  = APPDATA / "Pleiada" / "auth.json"
SETTINGS_FILE = APPDATA / "Pleiada" / "settings.json"   # v0.5: hotkeys y prefs
GAMES_FILE = APP_DIR / "games_list.json"
# v0.8.6: renombrado a _v2 para invalidar caches viejos â€” el filtro cambiÃ³ de
# "active" a "Publicado" y un cachÃ© previo con la misma list_version nunca se
# re-descargarÃ­a (sync_games_list compara versiones, no contenido).
GAMES_CACHE = APPDATA / "Pleiada" / "games_list_cache_v2.json"   # v0.4: cachÃ© de Airtable
TEMP_DIR   = Path(os.environ.get("TEMP", "C:\\Temp"))
ANCHOR_FILE = TEMP_DIR / "pleiada_anchor_ts.txt"
GAME_FILE   = TEMP_DIR / "pleiada_game_name.txt"
BASE_DIR    = Path.home() / "Documents" / "Pleiada Recordings"
AHK_SCRIPT  = APP_DIR / "input_logger.ahk"

# â”€â”€â”€ Crash / error logging (v0.7.1, ubicaciÃ³n v0.8.4) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Captura crashes, excepciones no manejadas (main + threads), errores de callbacks
# de Tkinter (que de otro modo se tragan en un .exe windowed) y crashes nativos
# (faulthandler). Vive en Documentos\Pleiada Logs: una carpeta que el usuario
# puede encontrar fÃ¡cil y mandar a soporte (AppData estÃ¡ oculto para la mayorÃ­a).
import faulthandler, traceback
LOG_DIR = Path.home() / "Documents" / "Pleiada Logs"
_fault_fp = None

def _crashlog(text):
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_DIR / "crash.log", "a", encoding="utf-8") as f:
            f.write(f"\n===== {ts}  ({VERSION}) =====\n{text}\n")
    except Exception:
        pass

def _install_crash_logging():
    global _fault_fp
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _fault_fp = open(LOG_DIR / "faulthandler.log", "a", encoding="utf-8")
        faulthandler.enable(file=_fault_fp, all_threads=True)
    except Exception:
        pass
    def _excepthook(et, ev, tb):
        _crashlog("UNHANDLED (main):\n" + "".join(traceback.format_exception(et, ev, tb)))
        try: sys.__excepthook__(et, ev, tb)
        except Exception: pass
    sys.excepthook = _excepthook
    def _threadhook(args):
        _crashlog(f"UNHANDLED (thread {getattr(args.thread,'name','?')}):\n" +
                  "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))
    try:
        threading.excepthook = _threadhook
    except Exception:
        pass

def _tk_callback_excepthook(exc, val, tb):
    """report_callback_exception de Tkinter: errores en handlers de la GUI."""
    _crashlog("GUI callback exception:\n" + "".join(traceback.format_exception(exc, val, tb)))

# â”€â”€â”€ Design tokens â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BG      = "#0d0d18"
BG2     = "#0a0a12"
CARD    = "#13132a"
CARD2   = "#181838"
ACCENT  = "#7c6fcd"
TEXT    = "#e8e8f0"
DIM     = "#7b78a8"
DIMMER  = "#4f4d75"
GREEN   = "#3ecf8e"
YELLOW  = "#febc2e"
RED     = "#e05555"
BORDER  = "#2a2850"
BORDER2 = "#1f1d3d"

# Alto: la barra de tÃ­tulo propia mide 38 px fijos y la vista de Ajustes pide 681,
# asÃ­ que con 640 el botÃ³n de Cerrar sesiÃ³n quedaba FUERA de la ventana (reportado
# 25/07). 730 deja 692 de contenido: 11 px de margen sobre lo que pide.
# OJO: no alcanza si ademÃ¡s estÃ¡ visible el banner de actualizaciÃ³n, que se packea
# arriba del contenido. Lo que aguanta que Ajustes siga creciendo es hacerlo
# scrollable â€” queda en backlog.
WIN_W, WIN_H = 420, 730
MAX_SECONDS  = 3900   # 1 h 5 min

# Gate AFK: una sesiÃ³n con mÃ¡s de este tiempo CONTINUO sin inputs (teclado/
# mouse) se marca como no vÃ¡lida para subir. Caso real 20/07/26: 30 min
# grabados con el jugador alt-tabbeado desde el segundo 3.
# Definido en pleiada_sync_limits para que el Synch Checker aplique el mismo gate.
MAX_CONT_IDLE_MS = sync_limits.MAX_CONT_IDLE_MS   # 10 minutos

# â”€â”€â”€ Credenciales (login OTP â€” v0.8) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def load_auth():
    try:
        with open(AUTH_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_auth(email, token):
    """Guarda email + token de sesiÃ³n. Si token es vacÃ­o, borra el archivo."""
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    if token:
        with open(AUTH_FILE, "w", encoding="utf-8") as f:
            json.dump({"email": email, "token": token}, f)
    else:
        AUTH_FILE.unlink(missing_ok=True)

# â”€â”€â”€ Estado de subida por sesiÃ³n (v0.8) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
UPLOAD_STATE_FILE = ".pleiada_upload.json"   # sidecar; NO se sube (ver session_uploader._EXCLUDE)

def _session_state_path(sdir):
    return Path(sdir) / UPLOAD_STATE_FILE

def read_session_state(sdir):
    try:
        with open(_session_state_path(sdir), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def write_session_state(sdir, **kw):
    st = read_session_state(sdir)
    st.update(kw)
    p = _session_state_path(sdir)
    try:
        if p.exists():
            os.chmod(p, stat.S_IWRITE)   # por si quedÃ³ read-only
    except Exception:
        pass
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(st, f)
    except Exception:
        pass

def _fmt_eta(s):
    if not s or s <= 0:
        return ""
    s = int(s)
    if s < 60:
        return f"~{s}s restantes"
    return f"~{s // 60}m {s % 60:02d}s restantes"

def list_local_sessions():
    """Devuelve [(Path, {status, size_label})] de sesiones locales, mÃ¡s nuevas primero."""
    out = []
    try:
        dirs = [d for d in BASE_DIR.iterdir() if d.is_dir()]
    except Exception:
        return out
    for d in sorted(dirs, key=lambda d: d.stat().st_mtime, reverse=True):
        try:
            files = [f for f in d.iterdir() if f.is_file()]
        except Exception:
            continue
        has_mp4  = any(f.suffix.lower() == ".mp4" for f in files)
        has_meta = any(f.name == "session_metadata.json" for f in files)
        st = read_session_state(d)
        total = sum(f.stat().st_size for f in files if f.name != UPLOAD_STATE_FILE)
        size_label = (f"{total / 1024**2:.1f} MB" if total >= 1024**2
                      else f"{total / 1024:.0f} KB")
        if st.get("uploaded"):
            status = "uploaded"
        elif not (has_mp4 and has_meta):
            status = "incomplete"
        elif st.get("valid") is False:
            status = "invalid"
        else:
            status = "pending"
        out.append((d, {"status": status, "size_label": size_label}))
    return out

# â”€â”€â”€ Settings / hotkeys (v0.5) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Hotkeys por defecto: F9 = iniciar, F10 = detener. Sin modificadores.
DEFAULT_SETTINGS = {
    "hotkey_start": {"vk": 0x78, "label": "F9"},
    "hotkey_stop":  {"vk": 0x79, "label": "F10"},
    "max_session_minutes": 60,    # v0.7.1: duraciÃ³n mÃ¡x de sesiÃ³n, clamp [1, 60] min
    "auto_restart":        False, # v0.7.1: reiniciar grabaciÃ³n tras auto-stop por tiempo
}

def load_settings():
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            s = json.load(f)
        # Completar claves faltantes con defaults
        out = json.loads(json.dumps(DEFAULT_SETTINGS))
        out.update({k: v for k, v in s.items() if k in DEFAULT_SETTINGS})
        # v0.7.1: clamp/coerciÃ³n de los valores nuevos
        try:
            out["max_session_minutes"] = max(1, min(60, int(out["max_session_minutes"])))
        except Exception:
            out["max_session_minutes"] = 60
        out["auto_restart"] = bool(out.get("auto_restart", False))
        return out
    except Exception:
        return json.loads(json.dumps(DEFAULT_SETTINGS))

def save_settings(settings):
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# Mapa keysym de Tkinter â†’ (vk, label legible) para reasignar hotkeys.
# Cubre F1-F12, letras, dÃ­gitos y algunas teclas comunes.
def _keysym_to_vk(keysym):
    ks = keysym
    # F1-F24
    if ks.upper().startswith("F") and ks[1:].isdigit():
        n = int(ks[1:])
        if 1 <= n <= 24:
            return 0x70 + (n - 1), f"F{n}"
    # Letras
    if len(ks) == 1 and ks.isalpha():
        return ord(ks.upper()), ks.upper()
    # DÃ­gitos
    if len(ks) == 1 and ks.isdigit():
        return ord(ks), ks
    # Teclas especiales comunes
    special = {
        "space": (0x20, "Space"), "Insert": (0x2D, "Insert"),
        "Home": (0x24, "Home"), "End": (0x23, "End"),
        "Prior": (0x21, "PageUp"), "Next": (0x22, "PageDown"),
        "Pause": (0x13, "Pause"), "Scroll_Lock": (0x91, "ScrollLock"),
    }
    if ks in special:
        return special[ks]
    return None, None

# â”€â”€â”€ Lista de juegos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#
# Fuente de verdad: base "Pleiada Games" en Airtable (dinÃ¡mica, editable sin recompilar).
# Orden de prioridad al cargar:
#   1. games_list_cache.json (descargado de Airtable)
#   2. games_list.json bundleado en el installer (fallback final)
# El sync con Airtable corre en background al iniciar la app (sync_games_list).
#
# Token read-only (scope: data.records:read). Si se extrae del binario, solo puede
# leer la lista de juegos â€” no puede modificar ni borrar nada de la base.

AIRTABLE_TOKEN      = "patDpnvFjK67EiN0g.c56e7a6c69976db0a23bc0dd018f6bf77169a9d8f11a16aa14029c2c80eda165"
AIRTABLE_BASE_ID    = "appeyQ2C1DFa7e2HC"
AIRTABLE_GAMES_TID  = "tblrd5RYBLUmng4zF"
AIRTABLE_CONFIG_TID = "tblwzcB6aluMoJGPs"

_games_cache = None

def load_games():
    """Carga la lista de juegos: cachÃ© de Airtable â†’ fallback al JSON bundleado."""
    global _games_cache
    if _games_cache is not None:
        return _games_cache
    # 1. Intentar cachÃ© de Airtable
    try:
        with open(GAMES_CACHE, encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("games"):
            _games_cache = cache["games"]
            return _games_cache
    except Exception:
        pass
    # 2. Fallback: JSON bundleado en el installer
    try:
        with open(GAMES_FILE, encoding="utf-8") as f:
            _games_cache = json.load(f)
    except Exception:
        _games_cache = []
    return _games_cache

def _airtable_get(endpoint, params=None):
    """GET a la API de Airtable. Lanza excepciÃ³n si falla."""
    import urllib.request as _ur, urllib.parse as _up
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{endpoint}"
    if params:
        url += "?" + _up.urlencode(params, doseq=True)
    req = _ur.Request(url, headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}"})
    with _ur.urlopen(req, timeout=5) as r:
        return json.loads(r.read())

def _airtable_remote_version():
    """Lee Config.list_version. Retorna string o None."""
    try:
        cfg = _airtable_get(AIRTABLE_CONFIG_TID, {"maxRecords": 5})
        for rec in cfg.get("records", []):
            f = rec.get("fields", {})
            if f.get("Name") == "list_version":
                return f.get("value")
    except Exception:
        pass
    return None

def _airtable_download_games():
    """Descarga todos los juegos activos de Airtable (paginado). Retorna lista de dicts."""
    games  = []
    offset = None
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        page = _airtable_get(AIRTABLE_GAMES_TID, params)
        for rec in page.get("records", []):
            f = rec.get("fields", {})
            # Solo juegos con el tilde "Publicado" en Airtable â€” la MISMA regla
            # que el catÃ¡logo pÃºblico (catalogo.gameplayalliance.gg). Publicado
            # es la columna autoritativa de visibilidad (decisiÃ³n MartÃ­n
            # 20/07/26); "active" ya no gobierna el listado del Recorder.
            if not f.get("Publicado"):
                continue
            name = (f.get("Name") or "").strip()
            if not name:
                continue
            def _split(v):
                return [x.strip() for x in v.split(",") if x.strip()] if isinstance(v, str) else (v or [])
            # default_key_mapping: JSON curado (teclaâ†’acciÃ³n) del binding de fÃ¡brica del
            # juego. Fallback cuando no se puede leer el config real (ej: RDR2 binario).
            # Se guarda como dato en Airtable, NO como cÃ³digo por juego.
            def _parse_default_km(v):
                if isinstance(v, dict):
                    return v or None
                if isinstance(v, str) and v.strip():
                    try:
                        d = json.loads(v)
                        return d if isinstance(d, dict) and d else None
                    except Exception:
                        return None
                return None
            games.append({
                "game":           name,
                "perspective":    f.get("perspective") or "",
                "genre":          f.get("genre") or "",
                "mode":           f.get("mode") or "",
                "process_name":   f.get("process_name") or None,
                "process_source": f.get("process_source") or "",
                "engine":         f.get("engine") or None,
                "themes":         _split(f.get("themes")),
                "languages":      _split(f.get("languages")),
                "developer":      f.get("developer") or None,
                "igdb_id":        f.get("igdb_id") or None,
                "default_key_mapping": _parse_default_km(f.get("default_key_mapping")),
            })
        offset = page.get("offset")
        if not offset:
            break
    return games

def sync_games_list():
    """
    Sincroniza la lista de juegos con Airtable. Nunca lanza excepciÃ³n.
    Actualiza GAMES_CACHE y el cachÃ© en memoria si hay una versiÃ³n nueva.
    Llamar en un thread daemon al iniciar la app.
    """
    global _games_cache
    cached_version = None
    try:
        if GAMES_CACHE.exists():
            with open(GAMES_CACHE, encoding="utf-8") as f:
                c = json.load(f)
            cached_version = c.get("version")
    except Exception:
        pass

    # La lista es dinÃ¡mica (se actualiza a diario): chequear SIEMPRE la versiÃ³n al
    # abrir â€” es 1 request liviano (Config.list_version). Solo se descarga el listado
    # completo si la versiÃ³n cambiÃ³. Si offline, se usa el cachÃ© existente.
    remote_version = _airtable_remote_version()
    if remote_version is None:
        return  # offline o error â€” seguimos con el cachÃ©/fallback

    if remote_version == cached_version:
        return  # ya tenemos la Ãºltima versiÃ³n, no descargar

    # VersiÃ³n nueva â†’ descargar todo
    try:
        games = _airtable_download_games()
        if games:
            GAMES_CACHE.parent.mkdir(parents=True, exist_ok=True)
            with open(GAMES_CACHE, "w", encoding="utf-8") as f:
                json.dump({"version": remote_version, "downloaded_at": time.time(),
                           "games": games}, f, ensure_ascii=False)
            _games_cache = games   # refrescar memoria para el search del UI
            _obs_dbg(f"sync_games_list: {len(games)} juegos actualizados (v{remote_version})")
    except Exception as e:
        _obs_dbg(f"sync_games_list download error: {e}")

def fuzzy_search(query, max_results=None):
    """
    Sin query â†’ toda la lista ordenada alfabÃ©ticamente (para scroll).
    Con query â†’ matches ordenados por relevancia (exacto â†’ empieza-con â†’ contiene),
    alfabÃ©tico dentro de cada grupo. Filtra desde el primer caracter.
    max_results=None devuelve todos (el dropdown maneja el scroll).
    """
    games = load_games()
    if not query:
        out = sorted(games, key=lambda g: g["game"].lower())
        return out[:max_results] if max_results else out
    q = query.lower()
    results = [g for g in games if q in g["game"].lower()]
    exact  = [g for g in results if g["game"].lower() == q]
    starts = sorted([g for g in results if g["game"].lower().startswith(q) and g not in exact],
                    key=lambda g: g["game"].lower())
    rest   = sorted([g for g in results if g not in exact and g not in starts],
                    key=lambda g: g["game"].lower())
    out = exact + starts + rest
    return out[:max_results] if max_results else out

# â”€â”€â”€ Auto-update (v0.8) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#
# El CI publica en cada release un manifiesto latest.json junto a los .exe:
#   { version, min_version, update_url, update_sha256, ... }
# La app lo chequea al arrancar (en background) y ofrece actualizar con el
# updater liviano PleiadaRecorder_Update.exe. Si la versiÃ³n instalada es menor
# que min_version, la grabaciÃ³n queda bloqueada hasta actualizar.

UPDATE_MANIFEST_URL = ("https://github.com/PleiadaAI/pleiada-recorder"
                       "/releases/latest/download/latest.json")

def _parse_version(v):
    """'v0.7.0' / '0.7' â†’ (0, 7, 0). None si no parsea."""
    try:
        parts = str(v).strip().lstrip("vV").split(".")
        nums = []
        for p in parts[:3]:
            m = re.match(r"\d+", p.strip())
            if not m:
                return None
            nums.append(int(m.group()))
        if not nums:
            return None
        while len(nums) < 3:
            nums.append(0)
        return tuple(nums)
    except Exception:
        return None

def check_for_update():
    """
    Lee el manifiesto de updates del Ãºltimo release. Nunca lanza excepciÃ³n.
    Retorna el manifiesto (dict) con dos claves calculadas:
      _newer  â†’ hay una versiÃ³n mÃ¡s nueva que la instalada
      _forced â†’ la instalada es menor que min_version (bloquear grabaciÃ³n)
    o None si no hay red / manifiesto invÃ¡lido.
    """
    try:
        import urllib.request as _ur
        req = _ur.Request(UPDATE_MANIFEST_URL,
                          headers={"User-Agent": f"PleiadaRecorder/{VERSION}"})
        with _ur.urlopen(req, timeout=8) as r:
            manifest = json.loads(r.read().decode("utf-8"))
        remote = _parse_version(manifest.get("version"))
        local  = _parse_version(VERSION)
        if not remote or not local:
            return None
        manifest["_newer"]  = remote > local
        min_v = _parse_version(manifest.get("min_version"))
        manifest["_forced"] = bool(min_v) and local < min_v
        return manifest
    except Exception:
        return None

# â”€â”€â”€ OBS helpers (inlined desde obs_control.py) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

import hashlib, base64, uuid, websocket

OBS_HOST     = "localhost"
OBS_PORT     = 4455
OBS_PASSWORD = ""

# â”€â”€ Config de grabaciÃ³n del dataset (v0.8.12) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# El instalador escribe estos valores UNA sola vez, al crear el perfil Pleiada
# (configure_obs.py). Nada los volvÃ­a a mirar despuÃ©s: si el usuario tocaba
# Ajustes â†’ Salida en OBS, quedaba cambiado para siempre y el Recorder seguÃ­a
# grabando con lo que hubiera. Esto se re-aplica en silencio antes de CADA
# grabaciÃ³n, para que todas las sesiones del dataset pesen y se vean igual.
#
# Los dos extremos rompen algo distinto:
#   - por debajo: material inservible para el cliente.
#   - por encima: calidad alta lleva el dataset de ~1,1 GB/h a 11-20 GB/h y
#     multiplica subida y costo de S3 por diez o mÃ¡s.
#
# RecQuality=Stream es lo que hoy aplica de hecho en la flota (el instalador
# NUNCA escribiÃ³ la clave, asÃ­ que quedaba el default de OBS). Se escribe
# explÃ­cito para dejar de depender de quÃ© versiÃ³n de OBS tenga cada uno.
# El fix que lo subÃ­a a HQ estÃ¡ en hold desde el 28/07 (_programa\
# bitrate_fix_configure_obs.patch): mientras siga en hold, esto lo sostiene.
OBS_PROFILE_NAME = "Pleiada"
OBS_TARGET_PROFILE = [
    # (categorÃ­a, clave, valor)
    ("Output",       "Mode",       "Simple"),           # primero: define quÃ© secciÃ³n lee OBS
    ("SimpleOutput", "RecFormat2", "fragmented_mp4"),   # crash-safe (ver _obs_do_start)
    # El basic.ini del perfil tiene un SEGUNDO RecFormat2 en [AdvOut], con valor
    # hybrid_mp4. Forzar solo SimpleOutput dejaba grabando hybrid a todo el que
    # tuviera OBS en modo de salida Avanzado â€” y el hybrid escribe el moov al
    # final, que es lo que a Troveo le llegÃ³ como "dos sabores" de MP4 (17/08).
    # Se escribe en las dos categorÃ­as: Mode=Simple deberÃ­a alcanzar, pero si esa
    # escritura falla o el usuario lo revierte, AdvOut tiene que estar bien igual.
    ("AdvOut",       "RecFormat2", "fragmented_mp4"),
    ("SimpleOutput", "RecQuality", "Stream"),           # graba al bitrate de abajo, no por CRF
    ("SimpleOutput", "VBitrate",   "2500"),
    ("SimpleOutput", "ABitrate",   "160"),
]
OBS_TARGET_VIDEO = {
    "baseWidth":      1920,
    "baseHeight":     1080,
    "outputWidth":    1920,
    "outputHeight":   1080,
    "fpsNumerator":   60,
    "fpsDenominator": 1,
}

class OBSAuthError(RuntimeError):
    """OBS WebSocket rechazÃ³ la autenticaciÃ³n (contraseÃ±a activada en OBS)."""
    pass

def _obs_dbg(msg):
    try:
        log = TEMP_DIR / "pleiada_obs_debug.txt"
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

def _obs_unescape(s):
    """Decodifica los escapes `#XX` que OBS mete en el window string.

    OBS escapa los caracteres que usa como separador: un ':' real del tÃ­tulo
    viaja como '#3A'. Visto en producciÃ³n: el Recorder mostraba
    "Horizon Zero Dawn#3A Complete Edition" por "Horizon Zero Dawn: Complete
    Edition". Sin decodificar, al normalizar queda un '3a' pegado al nombre y
    el match por substring falla SIEMPRE, cayendo al fallback por palabras.
    Alcance: 125 de 504 tÃ­tulos publicados tienen ':' (25% del catÃ¡logo).

    OJO con el orden: esto se aplica DESPUÃ‰S de partir el window string por
    ':', nunca antes. Los ':' reales estÃ¡n escapados justamente para que el
    split no los vea; decodificar primero los convierte en separadores y parte
    el tÃ­tulo al medio ("Horizon Zero Dawn" perdiendo "Complete Edition"),
    que es peor que el bug original â€” se llevarÃ­a puesto el chequeo de ediciÃ³n
    de PLE-35.
    """
    if not s:
        return s
    try:
        return re.sub(r'#([0-9A-Fa-f]{2})', lambda m: chr(int(m.group(1), 16)), s)
    except Exception:
        return s

def _obs_sequel_numeral(name):
    """Numeral de secuela de un tÃ­tulo, o None. 'Spider-Man 2' â†’ 2, 'GTA V' â†’ 5.

    Se toma el ÃšLTIMO numeral del nombre ('Left 4 Dead 2' â†’ 2, no 4).
    """
    _ROMAN = {"ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6,
              "vii": 7, "viii": 8, "ix": 9, "x": 10}
    num = None
    for t in re.findall(r"[a-z0-9]+", (name or "").lower()):
        if t.isdigit():
            num = int(t)
        elif t in _ROMAN:
            num = _ROMAN[t]
    return num

def _obs_title_matches(game_name, win_title):
    """True si el tÃ­tulo de ventana de OBS corresponde al juego seleccionado.

    Estrategia (en orden):
    1. Substring bidireccional normalizado â€” cubre "FarCryÂ®6Trial" vs "Far Cry 6"
       PLE-35: si el match es unidireccional (game_name âŠ‚ win_title), verificar que
       el contenido extra en win_title no sean version qualifiers â†’ rechaza
       "Borderlands 3" vs "Borderlands 3 Definitive Edition".
    2. Al menos una palabra significativa del juego (â‰¥ 2 chars) aparece en el tÃ­tulo
    3. Sin datos o sin palabras â†’ no bloquear (beneficio de la duda)

    NormalizaciÃ³n: minÃºsculas + solo alfanumÃ©ricos (elimina Â®, Â©, â„¢, espacios, guiones, etc.)
    """
    # Palabras que indican una versiÃ³n/ediciÃ³n especÃ­fica del juego.
    # Si aparecen en el tÃ­tulo de OBS pero NO en el nombre seleccionado â†’ mismatch.
    _VERSION_QUALIFIERS = {
        "definitive", "edition", "redux", "remastered", "enhanced",
        "complete", "ultimate", "deluxe", "anniversary", "gold",
        "premium", "extended", "reloaded", "directors", "director",
        "goty", "legendary", "platinum", "royal", "trilogy",
    }

    def _n(s):
        return re.sub(r'[^a-z0-9]', '', s.lower())

    a = _n(win_title)
    b = _n(game_name)

    if not a or not b:
        return True   # sin datos â†’ no bloquear

    # Substring bidireccional
    if a in b:
        return True   # win_title âŠ† game_name â†’ OK siempre

    if b in a:
        # game_name âŠ† win_title â€” verificar que el extra no sea un version qualifier
        # Extraer palabras del win_title que NO estÃ¡n en el game_name normalizado
        extra_words = [_n(w) for w in win_title.split() if _n(w) not in b and len(_n(w)) >= 3]
        if any(w in _VERSION_QUALIFIERS for w in extra_words):
            return False   # PLE-35: versiÃ³n diferente seleccionada
        return True

    # Fallback por palabras. v0.8.12: antes alcanzaba UNA sola palabra en comÃºn,
    # y eso dejaba pasar sesiones etiquetadas con el tÃ­tulo equivocado â€” el caso
    # reproducido es "Marvel's Spider-Man: Miles Morales" seleccionado contra
    # "Marvel's Spider-Man Remastered" capturado: matcheaba por "marvels" y el
    # dataset salÃ­a con el tÃ­tulo que no era, sin que QA pudiera detectarlo.
    # Ahora se exigen TODAS las palabras significativas, mÃ¡s el numeral de
    # secuela cuando el juego elegido lo tiene ("Spider-Man 2" contra un tÃ­tulo
    # sin el 2 = juego distinto; el '2' solo se caÃ­a antes por len < 2).
    words = [_n(w) for w in game_name.split() if len(_n(w)) >= 2]
    if not words:
        return True   # ninguna palabra verificable â†’ no bloquear

    ok = all(w in a for w in words)

    # Numeral de secuela: solo se exige en un sentido. Si el juego elegido tiene
    # numeral, el tÃ­tulo de OBS tiene que traerlo. Al revÃ©s NO se exige: los
    # tÃ­tulos de OBS vienen llenos de nÃºmeros de versiÃ³n ("v4.630.0.0") y pedir
    # simetrÃ­a bloquearÃ­a a gente que hoy graba bien.
    n_game = _obs_sequel_numeral(game_name)
    if ok and n_game is not None and _obs_sequel_numeral(win_title) != n_game:
        ok = False

    # TelemetrÃ­a de calibraciÃ³n: lo que la regla nueva bloquea y la vieja dejaba
    # pasar. Endurecer esto convierte falsos positivos silenciosos en bloqueos
    # visibles, asÃ­ que queda el rastro para ajustar con pares reales en vez de
    # a ojo. Va al log de debug, no molesta al usuario.
    if not ok and any(w in a for w in words):
        _obs_dbg(f"title_match ENDURECIDO bloqueÃ³: juego='{game_name}' "
                 f"obs='{win_title}' (la regla vieja lo dejaba pasar)")

    return ok

def obs_connect():
    ws = websocket.WebSocket()
    ws.connect(f"ws://{OBS_HOST}:{OBS_PORT}", timeout=5)
    hello = json.loads(ws.recv())
    auth_data = hello["d"].get("authentication")
    if not auth_data:
        ws.send(json.dumps({"op": 1, "d": {"rpcVersion": 1}}))
        json.loads(ws.recv())
        return ws
    # OBS tiene contraseÃ±a en el WebSocket â€” intentar autenticar con OBS_PASSWORD
    secret = base64.b64encode(
        hashlib.sha256((OBS_PASSWORD + auth_data["salt"]).encode()).digest()
    ).decode()
    auth_str = base64.b64encode(
        hashlib.sha256((secret + auth_data["challenge"]).encode()).digest()
    ).decode()
    ws.send(json.dumps({"op": 1, "d": {"rpcVersion": 1, "authentication": auth_str}}))
    # Si la contraseÃ±a es incorrecta OBS cierra la conexiÃ³n sin responder (recv vacÃ­o)
    try:
        raw = ws.recv()
        if not raw:
            raise OBSAuthError()
        json.loads(raw)   # Identified â€” si llega acÃ¡, auth OK
    except OBSAuthError:
        try: ws.close()
        except: pass
        raise OBSAuthError(
            "OBS WebSocket tiene contraseÃ±a activada.\n"
            "Desactivala en: OBS â†’ Herramientas â†’ WebSocket Server Settings â†’ "
            "desmarcÃ¡ 'Enable Authentication'."
        )
    except Exception:
        try: ws.close()
        except: pass
        raise OBSAuthError(
            "OBS WebSocket tiene contraseÃ±a activada.\n"
            "Desactivala en: OBS â†’ Herramientas â†’ WebSocket Server Settings â†’ "
            "desmarcÃ¡ 'Enable Authentication'."
        )
    return ws

def obs_send(ws, req_type, data=None):
    msg = {"op": 6, "d": {
        "requestType": req_type,
        "requestId":   str(uuid.uuid4()),
        "requestData": data or {}
    }}
    ws.send(json.dumps(msg))
    while True:
        raw    = ws.recv()
        parsed = json.loads(raw)
        if parsed.get("op") == 5:
            continue   # skip events
        return parsed

def obs_is_running():
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq obs64.exe", "/NH"],
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW   # Bug 9: sin ventana de consola
        ).decode(errors="ignore")
        return "obs64.exe" in out
    except Exception:
        return False

def find_obs_exe():
    candidates = [
        r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
        r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None

def launch_obs():
    obs = find_obs_exe()
    if not obs:
        return False
    obs_dir = os.path.dirname(obs)
    subprocess.Popen([obs, "--disable-shutdown-check"], cwd=obs_dir,
                     creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(30):
        time.sleep(1)
        try:
            ws = websocket.WebSocket()
            ws.connect(f"ws://{OBS_HOST}:{OBS_PORT}", timeout=1)
            ws.close()
            return True
        except Exception:
            pass
    return False

def obs_get_game_window():
    """Devuelve el tÃ­tulo de la ventana del juego configurado en OBS, o ''.
    Puede lanzar OBSAuthError si el WebSocket requiere contraseÃ±a."""
    ws = obs_connect()   # deja propagar OBSAuthError
    resp    = obs_send(ws, "GetInputList")
    inputs  = resp.get("d", {}).get("responseData", {}).get("inputs", [])
    gc_src  = next((i for i in inputs if i.get("inputKind") == "game_capture"), None)
    if not gc_src:
        ws.close(); return ""
    sr     = obs_send(ws, "GetInputSettings", {"inputName": gc_src["inputName"]})
    window = sr.get("d", {}).get("responseData", {}).get("inputSettings", {}).get("window", "")
    ws.close()
    # unescape DESPUÃ‰S del split (ver _obs_unescape)
    return _obs_unescape(window.split(":")[0].strip()) if window else ""

def obs_capture_target():
    """Que esta capturando OBS ahora: (is_recording, titulo, exe, wrong_source).

    obs_check_status devuelve el titulo y el exe pegados en un solo string, que
    servia para comparar contra un juego ya elegido. Desde v0.9 el juego se
    deduce de esto, asi que el exe tiene que venir separado: es la clave con la
    que el backend resuelve el titulo sin depender del nombre de la ventana.

    El exe solo existe si la fuente esta en modo "ventana especifica"; en
    "cualquier aplicacion en pantalla completa" OBS no expone que engancho.
    """
    ws = obs_connect()
    is_recording = False
    title = exe = ""
    wrong = None
    try:
        rec = obs_send(ws, "GetRecordStatus")
        is_recording = rec.get("d", {}).get("responseData", {}).get("outputActive", False)
        inputs = (obs_send(ws, "GetInputList")
                  .get("d", {}).get("responseData", {}).get("inputs", []))
        try:
            cur = (obs_send(ws, "GetCurrentProgramScene")
                   .get("d", {}).get("responseData", {}).get("currentProgramSceneName", ""))
            items = (obs_send(ws, "GetSceneItemList", {"sceneName": cur})
                     .get("d", {}).get("responseData", {}).get("sceneItems", []))
            enabled = {i.get("sourceName", "") for i in items if i.get("sceneItemEnabled", False)}
        except Exception:
            enabled = None
        _WRONG = {"monitor_capture": "Captura de Pantalla",
                  "screen_capture":  "Captura de Pantalla",
                  "window_capture":  "Captura de Ventana"}
        for inp in inputs:
            if inp.get("inputKind") in _WRONG:
                if enabled is None or inp.get("inputName", "") in enabled:
                    wrong = _WRONG[inp["inputKind"]]
                    break
        if not wrong:
            gc = next((i for i in inputs if i.get("inputKind") == "game_capture"), None)
            if gc:
                window = (obs_send(ws, "GetInputSettings", {"inputName": gc["inputName"]})
                          .get("d", {}).get("responseData", {})
                          .get("inputSettings", {}).get("window", ""))
                if window:
                    parts = window.split(":")
                    title = _obs_unescape(parts[0].strip())
                    for _p in parts[1:]:
                        _p = _obs_unescape(_p.strip())
                        if _p.lower().endswith(".exe"):
                            exe = _p
                            break
    finally:
        try:
            ws.close()
        except Exception:
            pass
    return is_recording, title, exe, wrong


def obs_check_status():
    """Retorna (is_recording, win_title, wrong_source) en una sola conexiÃ³n WebSocket.

    is_recording  : True si OBS estÃ¡ grabando ahora.
    win_title     : tÃ­tulo de la ventana del Game Capture source ('' si no hay o no apunta a nada).
    wrong_source  : nombre legible del modo incorrecto si el usuario NO usa Game Capture
                    pero sÃ­ tiene otra fuente de captura activa (ej: "Captura de Pantalla").
                    None si todo estÃ¡ bien o si no hay ninguna fuente de captura.
    Puede lanzar OBSAuthError."""

    _WRONG_SOURCES = {
        "monitor_capture": "Captura de Pantalla",
        "screen_capture":  "Captura de Pantalla",
        "window_capture":  "Captura de Ventana",
    }

    ws = obs_connect()   # deja propagar OBSAuthError

    # Â¿EstÃ¡ grabando?
    rec_resp     = obs_send(ws, "GetRecordStatus")
    is_recording = rec_resp.get("d", {}).get("responseData", {}).get("outputActive", False)

    # Fuentes de captura
    win_title    = ""
    win_match    = ""
    wrong_source = None
    try:
        resp   = obs_send(ws, "GetInputList")
        inputs = resp.get("d", {}).get("responseData", {}).get("inputs", [])

        # PLE-33: solo marcar fuente incompatible si estÃ¡ activa (enabled) en la escena actual
        try:
            _scene_r   = obs_send(ws, "GetCurrentProgramScene")
            _cur_scene = _scene_r.get("d", {}).get("responseData", {}).get("currentProgramSceneName", "")
            _si_r      = obs_send(ws, "GetSceneItemList", {"sceneName": _cur_scene})
            _si_list   = _si_r.get("d", {}).get("responseData", {}).get("sceneItems", [])
            _enabled   = {i.get("sourceName", "") for i in _si_list if i.get("sceneItemEnabled", False)}
        except Exception:
            _enabled   = None   # fallback: no filtrar (comportamiento anterior)

        for inp in inputs:
            kind = inp.get("inputKind", "")
            name = inp.get("inputName", "")
            if kind in _WRONG_SOURCES:
                if _enabled is None or name in _enabled:
                    wrong_source = _WRONG_SOURCES[kind]
                    break

        if not wrong_source:
            gc_src = next((i for i in inputs if i.get("inputKind") == "game_capture"), None)
            if gc_src:
                # Game Capture encontrado â€” leer quÃ© juego tiene configurado
                sr     = obs_send(ws, "GetInputSettings", {"inputName": gc_src["inputName"]})
                window = sr.get("d", {}).get("responseData", {}).get("inputSettings", {}).get("window", "")
                if window:
                    # Formato OBS: "WindowTitle:WindowClass:ExeName.exe"
                    # (el orden de class y exe varÃ­a segÃºn versiÃ³n/tipo de fuente)
                    # Buscamos el componente que termina en .exe, sin importar posiciÃ³n.
                    # unescape DESPUÃ‰S del split (ver _obs_unescape)
                    parts     = window.split(":")
                    win_title = _obs_unescape(parts[0].strip())
                    exe_part  = ""
                    for _p in parts[1:]:
                        _p = _obs_unescape(_p.strip())
                        if _p.lower().endswith(".exe"):
                            exe_part = re.sub(r'\.exe$', '', _p, flags=re.IGNORECASE)
                            break
                    win_match = f"{win_title} {exe_part}".strip()
    except Exception:
        pass

    ws.close()
    return is_recording, win_title, win_match, wrong_source

def _obs_do_start():
    """Asume OBS ya estÃ¡ corriendo. Conecta, configura audio, envÃ­a StartRecord.
    Retorna True si la grabaciÃ³n arrancÃ³, False si fallÃ³.
    Puede lanzar OBSAuthError si el WebSocket requiere contraseÃ±a."""
    ws = None
    try:
        ws = obs_connect()   # puede lanzar OBSAuthError â€” se deja propagar

        # Unmute desktop audio, mute mic
        try:
            resp   = obs_send(ws, "GetInputList")
            inputs = resp.get("d", {}).get("responseData", {}).get("inputs", [])
            for inp in inputs:
                kind = inp.get("inputKind", "")
                name = inp.get("inputName", "")
                if kind == "wasapi_output_capture":
                    obs_send(ws, "SetInputMute", {"inputName": name, "inputMuted": False})
                elif kind == "wasapi_input_capture":
                    obs_send(ws, "SetInputMute", {"inputName": name, "inputMuted": True})
        except Exception as e:
            _obs_dbg(f"audio setup error: {e}")

        # Forzar formato de grabaciÃ³n crash-safe (fragmented MP4).
        # Un MP4 clÃ¡sico escribe el Ã­ndice (moov) reciÃ©n al finalizar: si OBS
        # muere o lo matan antes de ese paso, TODO el archivo queda ilegible
        # (caso real 20/07/26: sesiÃ³n de 30 min â†’ 705 MB sin moov). Con fMP4
        # cada fragmento es autosuficiente y una grabaciÃ³n interrumpida sigue
        # siendo reproducible hasta el Ãºltimo GOP escrito.
        # Se fuerza acÃ¡ (y no solo en el instalador) para cubrir perfiles
        # creados por instaladores viejos o modificados a mano en OBS.
        # SetProfileParameter escribe sobre el perfil ACTIVO de OBS, asÃ­ que
        # primero se activa el perfil "Pleiada" si el usuario dejÃ³ otro activo
        # (usar OBS por fuera de Pleiada no debe degradar el dataset: el perfil
        # Pleiada garantiza 1080p60 + bitrate + formato). Nunca se escribe
        # sobre los perfiles propios del usuario â€” solo se cambia cuÃ¡l estÃ¡
        # activo. Ãšnico caso borde: si el perfil Pleiada fue borrado, se
        # fuerza el formato sobre el perfil activo (la integridad del dataset
        # gana) y queda logueado.
        #
        # v0.8.12: ademÃ¡s del formato se re-aplica TODA la config de grabaciÃ³n
        # (OBS_TARGET_PROFILE + OBS_TARGET_VIDEO). Antes solo se forzaba
        # RecFormat2, asÃ­ que bitrate, calidad, resoluciÃ³n y FPS quedaban a
        # merced de lo que el usuario hubiera tocado en OBS. Es silencioso a
        # propÃ³sito: no hay modal ni aviso, se corrige y se graba.
        try:
            _plist    = obs_send(ws, "GetProfileList").get("d", {}).get("responseData", {})
            _cur      = _plist.get("currentProfileName", "")
            _profiles = _plist.get("profiles", [])
            if _cur != OBS_PROFILE_NAME:
                if OBS_PROFILE_NAME in _profiles:
                    obs_send(ws, "SetCurrentProfile", {"profileName": OBS_PROFILE_NAME})
                    _obs_dbg(f"Perfil activo era '{_cur}' â€” cambiado a {OBS_PROFILE_NAME}")
                else:
                    # El usuario lo borrÃ³: se recrea vacÃ­o y se puebla abajo, en vez
                    # de escribir sobre el perfil propio del usuario.
                    _r = obs_send(ws, "CreateProfile", {"profileName": OBS_PROFILE_NAME})
                    _ok = _r.get("d", {}).get("requestStatus", {}).get("result", False)
                    _obs_dbg(f"Perfil {OBS_PROFILE_NAME} no existÃ­a (activo: '{_cur}') â€” "
                             f"CreateProfile result={_ok}")
                    if not _ok:
                        # No se pudo crear: se fuerza sobre el activo. La integridad
                        # del dataset gana; queda logueado.
                        _obs_dbg("No se pudo crear el perfil â€” se fuerza sobre el activo")

            for _cat, _key, _val in OBS_TARGET_PROFILE:
                obs_send(ws, "SetProfileParameter", {
                    "parameterCategory": _cat,
                    "parameterName":     _key,
                    "parameterValue":    _val,
                })
            _obs_dbg(f"Config de grabaciÃ³n forzada: "
                     + ", ".join(f"{k}={v}" for _c, k, v in OBS_TARGET_PROFILE))
        except Exception as e:
            _obs_dbg(f"Forzado de perfil/config error (continuando): {e}")

        # ResoluciÃ³n y FPS. Van por SetVideoSettings y no por SetProfileParameter
        # porque OBS aplica esto en caliente; escribir [Video] en el .ini reciÃ©n
        # tomarÃ­a efecto al reiniciar OBS. Se hace ANTES de StartRecord: con la
        # grabaciÃ³n activa, OBS rechaza el cambio.
        try:
            obs_send(ws, "SetVideoSettings", dict(OBS_TARGET_VIDEO))
            _obs_dbg(f"Video forzado: {OBS_TARGET_VIDEO['outputWidth']}x"
                     f"{OBS_TARGET_VIDEO['outputHeight']} @ "
                     f"{OBS_TARGET_VIDEO['fpsNumerator']} fps")
        except Exception as e:
            _obs_dbg(f"SetVideoSettings error (continuando): {e}")

        # StartRecord
        started = False
        for _ in range(20):
            resp = obs_send(ws, "StartRecord")
            code = resp.get("d", {}).get("requestStatus", {}).get("code", 0)
            if code == 100:
                started = True; break
            time.sleep(0.5)
        if not started:
            ws.close(); return False

        # Wait for STARTED event
        ws.settimeout(10)
        try:
            for _ in range(200):
                raw    = ws.recv()
                parsed = json.loads(raw)
                if parsed.get("op") == 5:
                    ed = parsed.get("d", {})
                    if (ed.get("eventType") == "RecordStateChanged" and
                            ed.get("eventData", {}).get("outputState") == "OBS_WEBSOCKET_OUTPUT_STARTED"):
                        ws.close(); return True
        except Exception:
            pass

        ws.close(); return True   # optimistic
    except OBSAuthError:
        raise   # dejar que llegue a _launch_at_zero para mostrar mensaje especÃ­fico
    except Exception as e:
        _obs_dbg(f"_obs_do_start: {e}")
        if ws:
            try: ws.close()
            except: pass
        return False

def obs_start_recording():
    """Lanza OBS si no estÃ¡ corriendo, luego inicia la grabaciÃ³n."""
    try:
        if not obs_is_running():
            if not launch_obs():
                return False
    except Exception as e:
        _obs_dbg(f"obs_start_recording launch check: {e}")
        return False
    return _obs_do_start()


# Misma regla que `_clean()` del backend (lambda_function.py): al pedir las presigned
# URLs, el backend sanea cada nombre para el key de S3 ([^A-Za-z0-9._@-] â†’ "_"). El MP4
# de OBS viene con espacios ("2026-08-02 22-33-10.mp4"), asÃ­ que el objeto en S3 quedaba
# con guiones bajos mientras `integrity.files` guardaba el nombre con espacios: buscar el
# hash del video por su nombre real no encontraba nada. Se sanea acÃ¡, al mover el archivo,
# para que el nombre en disco, en `integrity` y en S3 sean el mismo.
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._@-]")

def _safe_filename(name):
    """Nombre de archivo seguro para el key de S3, idÃ©ntico al que arma el backend."""
    return _SAFE_NAME.sub("_", (name or "").strip())[:200]


def obs_stop_recording(session_dir=None):
    """Detiene la grabaciÃ³n en OBS, ESPERA a que termine de finalizar el
    archivo y reciÃ©n entonces lo mueve al session_dir.

    Mover el video sin esperar el evento OUTPUT_STOPPED puede capturar un
    MP4 a medio finalizar (sin el Ã­ndice completo): el StopRecord del
    WebSocket responde de inmediato, pero OBS sigue escribiendo el archivo
    en background durante varios segundos mÃ¡s."""
    output_path = None
    stopped     = False
    session_start = (os.path.getmtime(str(session_dir))
                     if session_dir and session_dir.exists() else time.time() - 300)
    try:
        ws   = obs_connect()
        resp = obs_send(ws, "StopRecord")
        output_path = resp.get("d", {}).get("responseData", {}).get("outputPath", "")

        # Esperar RecordStateChanged â†’ OUTPUT_STOPPED (= archivo finalizado).
        # El evento ademÃ¡s trae el outputPath definitivo.
        ws.settimeout(2)
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                parsed = json.loads(ws.recv())
            except Exception:
                continue   # timeout de recv â†’ reintentar hasta el deadline
            if parsed.get("op") == 5:
                ed = parsed.get("d", {})
                if (ed.get("eventType") == "RecordStateChanged" and
                        ed.get("eventData", {}).get("outputState") == "OBS_WEBSOCKET_OUTPUT_STOPPED"):
                    ev_path = ed.get("eventData", {}).get("outputPath", "")
                    if ev_path:
                        output_path = ev_path
                    stopped = True
                    _obs_dbg("OUTPUT_STOPPED recibido â€” archivo finalizado por OBS")
                    break
        ws.close()
    except Exception as e:
        _obs_dbg(f"obs_stop_recording ws error: {e}")

    if not stopped:
        # Fallback: poll GetRecordStatus hasta que la grabaciÃ³n no estÃ© activa.
        _obs_dbg("Sin OUTPUT_STOPPED â€” fallback a poll de GetRecordStatus")
        for _ in range(15):
            try:
                ws2    = obs_connect()
                status = obs_send(ws2, "GetRecordStatus")
                ws2.close()
                if not (status.get("d", {}).get("responseData", {})
                              .get("outputActive", False)):
                    stopped = True
                    break
            except Exception:
                pass
            time.sleep(1)

    if not output_path or not os.path.isfile(output_path):
        time.sleep(2)
        vdir = Path.home() / "Videos"
        candidates = list(vdir.glob("*.mp4")) + list(vdir.glob("**/*.mp4"))
        recent = [f for f in candidates if f.stat().st_mtime >= session_start]
        if recent:
            output_path = str(max(recent, key=lambda f: f.stat().st_mtime))

    if output_path and os.path.isfile(output_path) and session_dir:
        dest = session_dir / _safe_filename(Path(output_path).name)
        for _ in range(20):
            try:
                shutil.move(output_path, dest)
                _obs_dbg(f"Video movido a: {dest}")
                if _mp4_is_truncated(str(dest)):
                    # Sin moov NI moof: OBS muriÃ³ sin finalizar. Se deja el
                    # archivo para diagnÃ³stico; el sync check lo marcarÃ¡
                    # como truncado y la sesiÃ³n quedarÃ¡ como no vÃ¡lida.
                    _obs_dbg("ADVERTENCIA: el video movido no tiene Ã­ndice (moov/moof)")
                return str(dest)
            except (PermissionError, OSError):
                time.sleep(0.5)
    return output_path or ""

# â”€â”€â”€ Anchor timestamp (copiado de obs_control.py) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _mp4_next_box(f, pos, limit):
    if pos + 8 > limit:
        return None, None, None
    f.seek(pos)
    raw = f.read(8)
    if len(raw) < 8:
        return None, None, None
    size     = struct.unpack('>I', raw[:4])[0]
    box_type = raw[4:8]
    if size == 1:
        ext = f.read(8)
        if len(ext) < 8:
            return None, None, None
        size = struct.unpack('>Q', ext)[0]
        data_start = pos + 16
    elif size < 8:
        return None, None, None
    else:
        data_start = pos + 8
    return pos + size, box_type, data_start

def _mp4_find_box(f, start, end, target):
    pos = start
    while True:
        box_end, btype, data = _mp4_next_box(f, pos, end)
        if box_end is None:
            return None, None
        if btype == target:
            return data, box_end
        pos = box_end

def _mp4_read_timescale(path):
    try:
        file_size = os.path.getsize(path)
        if file_size < 200:
            return None
        with open(path, 'rb') as f:
            moov_data, moov_end = _mp4_find_box(f, 0, min(file_size, 131072), b'moov')
            if not moov_data:
                return None
            trak_d, trak_e = _mp4_find_box(f, moov_data, moov_end, b'trak')
            if not trak_d:
                return None
            mdia_d, mdia_e = _mp4_find_box(f, trak_d, trak_e, b'mdia')
            if not mdia_d:
                return None
            mdhd_d, _ = _mp4_find_box(f, mdia_d, mdia_e, b'mdhd')
            if not mdhd_d:
                return None
            f.seek(mdhd_d)
            ver = struct.unpack('B', f.read(1))[0]
            f.read(3); f.read(16 if ver == 1 else 8)
            ts = struct.unpack('>I', f.read(4))[0]
            return ts if ts > 0 else None
    except Exception:
        return None

def _parse_traf_duration(f, traf_data, traf_end):
    default_dur = 0
    tfhd_d, _ = _mp4_find_box(f, traf_data, traf_end, b'tfhd')
    if tfhd_d:
        f.seek(tfhd_d); f.read(1)
        fl    = f.read(3)
        flags = (fl[0] << 16) | (fl[1] << 8) | fl[2]
        f.read(4)
        if flags & 0x000001: f.read(8)
        if flags & 0x000002: f.read(4)
        if flags & 0x000008: default_dur = struct.unpack('>I', f.read(4))[0]
    frag = 0
    trun_d, _ = _mp4_find_box(f, traf_data, traf_end, b'trun')
    if trun_d:
        f.seek(trun_d); f.read(1)
        fl         = f.read(3)
        trun_flags = (fl[0] << 16) | (fl[1] << 8) | fl[2]
        count      = struct.unpack('>I', f.read(4))[0]
        if trun_flags & 0x001: f.read(4)
        if trun_flags & 0x004: f.read(4)
        has_dur = bool(trun_flags & 0x100)
        has_sz  = bool(trun_flags & 0x200)
        has_fl  = bool(trun_flags & 0x400)
        has_cts = bool(trun_flags & 0x800)
        for _ in range(count):
            frag += struct.unpack('>I', f.read(4))[0] if has_dur else default_dur
            if has_sz:  f.read(4)
            if has_fl:  f.read(4)
            if has_cts: f.read(4)
    return frag

def _first_moof_duration_ms(path, timescale):
    try:
        file_size = os.path.getsize(path)
        with open(path, 'rb') as f:
            pos = 0; moof_count = 0; first_ticks = 0
            while pos < file_size:
                box_end, btype, data = _mp4_next_box(f, pos, file_size)
                if box_end is None: break
                if btype == b'moof':
                    moof_count += 1
                    if moof_count == 1:
                        traf_d, traf_e = _mp4_find_box(f, data, box_end, b'traf')
                        if traf_d:
                            first_ticks = _parse_traf_duration(f, traf_d, traf_e)
                    elif moof_count == 2:
                        if first_ticks > 0:
                            return round(first_ticks / timescale * 1000)
                        return None
                pos = box_end
    except Exception:
        pass
    return None

# Auto-record de demos POV para juegos Source 1 (TF2/L4D2): dispara record/stop por la consola
# TCP del juego (-netconport 2121). No bloquea la grabaciÃ³n si falla (juego sin netcon â†’ no-op).
def _source_console(cmd, port=2121, timeout=4.0):
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout) as s:
            s.sendall((cmd + "\n").encode("utf-8")); time.sleep(0.15)
        return True
    except Exception:
        return False

def _autodemo_game(selected_game):
    """True si el juego usa demo POV con auto-record (TF2/L4D2). CS2 NO (va por GOTV server-side)."""
    t = ((selected_game or {}).get("game") or "").lower()
    return ("team fortress" in t) or ("left 4 dead" in t)

def compute_anchor_ts(rec_dir_str, existing_set):
    new_file = None
    for _ in range(100):
        time.sleep(0.1)
        for c in glob.glob(os.path.join(rec_dir_str, "*.mp4")):
            if c not in existing_set:
                new_file = c; break
        if new_file: break
    if not new_file:
        return None
    timescale = None
    for _ in range(50):
        time.sleep(0.1)
        timescale = _mp4_read_timescale(new_file)
        if timescale: break
    if not timescale:
        return None
    for _ in range(300):
        time.sleep(0.1)
        dur_ms = _first_moof_duration_ms(new_file, timescale)
        if dur_ms is not None:
            return int(time.time() * 1000) - dur_ms
    return None

# â”€â”€â”€ AHK launcher â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_ahk_proc = None

def _find_ahk():
    local_app = os.environ.get("LOCALAPPDATA", "")
    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    candidates = [
        # Program Files â€” instalaciÃ³n system-wide
        os.path.join(prog_files,     r"AutoHotkey\v2\AutoHotkey64.exe"),
        os.path.join(prog_files,     r"AutoHotkey\AutoHotkey64.exe"),
        os.path.join(prog_files,     r"AutoHotkey\AutoHotkey.exe"),
        os.path.join(prog_files_x86, r"AutoHotkey\v2\AutoHotkey64.exe"),
        os.path.join(prog_files_x86, r"AutoHotkey\AutoHotkey64.exe"),
        # Per-user install (AppData\Local\Programs)
        os.path.join(local_app, r"Programs\AutoHotkey\v2\AutoHotkey64.exe"),
        os.path.join(local_app, r"Programs\AutoHotkey\AutoHotkey64.exe"),
        os.path.join(local_app, r"Programs\AutoHotkey\AutoHotkey.exe"),
        # Rutas hardcoded como fallback
        r"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe",
        r"C:\Program Files\AutoHotkey\AutoHotkey64.exe",
        r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c

    # Buscar en registro de Windows
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for subkey in (r"SOFTWARE\AutoHotkey", r"SOFTWARE\WOW6432Node\AutoHotkey"):
                try:
                    key = winreg.OpenKey(hive, subkey)
                    install_dir, _ = winreg.QueryValueEx(key, "InstallDir")
                    winreg.CloseKey(key)
                    if install_dir:
                        for exe in ("AutoHotkey64.exe", "AutoHotkey.exe", r"v2\AutoHotkey64.exe"):
                            p = os.path.join(install_dir, exe)
                            if os.path.isfile(p):
                                return p
                except Exception:
                    pass
    except Exception:
        pass

    # BÃºsqueda en PATH del sistema
    import shutil as _sh
    return _sh.which("AutoHotkey64") or _sh.which("AutoHotkey") or "AutoHotkey.exe"

def start_ahk_logger(log_dir_str, game_exe="", hotkey_vks=""):
    """Lanza AHK con el directorio de sesiÃ³n y (opcionalmente) el exe del juego.
    PLE-43/13: si se pasa game_exe, AHK solo registra inputs cuando ese proceso
    estÃ¡ en primer plano, evitando capturar inputs fuera del contexto de juego.
    hotkey_vks: csv de cÃ³digos VK (ej "120,121") que AHK excluye del key_log
    para no registrar los atajos del Recorder (iniciar/detener)."""
    global _ahk_proc
    ahk  = _find_ahk()
    # Args posicionales: [1]=logDir  [2]=gameExe  [3]=hotkeyVKs (csv de vk a excluir)
    args = [ahk, str(AHK_SCRIPT), log_dir_str, game_exe, hotkey_vks]
    try:
        _ahk_proc = subprocess.Popen(args, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        _obs_dbg(f"AHK launch error: {e}")
        _ahk_proc = None

def stop_ahk_logger(log_dir=None):
    """Para AHK de forma ordenada via stop file. Retorna True si AHK estaba corriendo."""
    global _ahk_proc
    if not _ahk_proc:
        return False
    if log_dir:
        stop_file = Path(log_dir) / "pleiada_stop.txt"
        try:
            stop_file.write_text("stop", encoding="utf-8")
        except Exception:
            pass
        try:
            _ahk_proc.wait(timeout=5)   # AHK escribe ANCHOR_END y cierra handles
        except subprocess.TimeoutExpired:
            try: _ahk_proc.terminate()
            except Exception: pass
        except Exception:
            pass
    else:
        try:
            _ahk_proc.terminate()
        except Exception:
            pass
    _ahk_proc = None
    return True

# â”€â”€â”€ Sync checker (inlined desde pleiada_check.pyw) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _csv_anchors(path):
    """Retorna (start_ms, end_ms) desde ANCHOR_START/END en el CSV."""
    start_ms = end_ms = None
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    try:
                        ts = int(parts[0])
                        ev = parts[1]
                        if ev == "ANCHOR_START" and start_ms is None:
                            start_ms = ts
                        elif ev == "ANCHOR_END":
                            end_ms = ts
                    except ValueError:
                        pass
    except Exception:
        pass
    return start_ms, end_ms

def _mp4_is_truncated(path):
    """True si el MP4 estÃ¡ truncado/corrupto. Implementado en pleiada_sync_limits
    para que el Synch Checker aplique exactamente el mismo criterio."""
    return sync_limits.mp4_is_truncated(path)

def _mp4_frag_duration_ms(path):
    """DuraciÃ³n real del MP4 en ms. Implementado en pleiada_sync_limits: las dos
    copias que habÃ­a (acÃ¡ y en pleiada_check.pyw) ya habÃ­an divergido y daban
    duraciones distintas sobre el mismo MP4 estÃ¡ndar."""
    return sync_limits.mp4_duration_ms(path)

def run_sync_check(session_dir, progress_cb=None):
    """
    Ejecuta el sync check completo sobre session_dir.
    Llama progress_cb(step_idx, status) conforme avanza.
    Retorna dict con resultados.
    """
    result = {
        "csvs_ok":      False,
        "video_ok":     False,
        "video_dur":    None,
        "truncated":    False,
        "signed_diff":  None,
        "csv_dur":      None,
        "session_ok":   False,
        "short_session": False,   # PLE-41: True si la sesiÃ³n fue < 30 s
        "afk":           False,   # True si hubo > MAX_CONT_IDLE_MS seguidos sin inputs
        "longest_idle_s": None,
        "idle_fraccion": None,    # proporciÃ³n de la sesiÃ³n que ocupa ese hueco
        "video_still":       False,  # True si la imagen estuvo quieta demasiado tiempo
        "video_still_ms":    None,   # corrida continua mÃ¡s larga de imagen quieta
        "video_still_ratio": None,   # proporciÃ³n de la sesiÃ³n con imagen quieta
        "sin_input":         False,  # True si no quedÃ³ registrado el input del jugador
        "sin_input_causa":   None,   # "captura_bloqueada" | "sin_teclado_ni_mouse"
        "eventos_input":     None,   # conteo crudo por CSV, para el registro interno
    }

    csv_names   = ["mouse_log.csv", "mouse_delta_log.csv", "key_log.csv", "video_timeline.csv"]
    csv_anchors = []

    # â€” Pasos 0-3: verificar CSVs â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”
    all_csv_ok = True
    for i, name in enumerate(csv_names):
        path = session_dir / name
        if not path.exists():
            if progress_cb: progress_cb(i, "missing")
            all_csv_ok = False
            csv_anchors.append((None, None))
            continue
        start, end = _csv_anchors(str(path))
        ok = (start is not None and end is not None and end > start)
        if not ok:
            all_csv_ok = False
        if progress_cb: progress_cb(i, "ok" if ok else "err")
        csv_anchors.append((start, end))

    # DuraciÃ³n CSV (media de los 4 archivos vÃ¡lidos)
    csv_dur = sync_limits.csv_duration_ms(csv_anchors)
    result["csv_dur"] = csv_dur
    result["csvs_ok"] = all_csv_ok

    # PLE-41: duraciÃ³n mÃ­nima â€” sesiones muy cortas producen diffs ~0 que pasan el check
    # incorrectamente aunque no haya juego grabado. MÃ­nimo 30 segundos de sesiÃ³n vÃ¡lida.
    if sync_limits.is_short_session(csv_dur):
        if progress_cb:
            for _i in range(5):
                progress_cb(_i, "err")
        result["short_session"] = True
        result["session_ok"]    = False
        return result

    # â€” Paso 4: verificar video â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”
    video_files = list(session_dir.glob("*.mp4"))
    if not video_files:
        if progress_cb: progress_cb(4, "missing")
        result["session_ok"] = False
        return result

    video_path = video_files[0]
    truncated  = _mp4_is_truncated(str(video_path))
    result["truncated"] = truncated

    if truncated:
        if progress_cb: progress_cb(4, "truncated")
        result["video_ok"]   = False
        result["session_ok"] = False
        return result

    video_dur = _mp4_frag_duration_ms(str(video_path))
    result["video_dur"] = video_dur

    if video_dur is None:
        if progress_cb: progress_cb(4, "err")
        result["video_ok"] = False
        result["session_ok"] = False
        return result

    # Comparar duraciÃ³n CSV vs video
    if csv_dur and video_dur:
        diff = video_dur - csv_dur
        result["signed_diff"] = diff
        # Tolerancias (definidas en pleiada_sync_limits, compartidas con el Synch Checker):
        #   +15 s: cubre anchor_fallback (WebSocket + AHK startup) en hw lento
        #   -4.5 s: cubre GOP parcial al final
        in_range = sync_limits.video_in_range(diff)
        result["video_ok"] = in_range
        if progress_cb: progress_cb(4, "ok" if in_range else "offset")
    else:
        result["video_ok"] = True
        if progress_cb: progress_cb(4, "ok")

    # â€” Gate de video quieto: pantalla negra o imagen congelada â€”
    # Complementa el gate AFK, que solo mira inputs: si el juego queda minimizado
    # o el game capture se cae, OBS graba negro mientras el jugador sigue
    # tecleando y AFK no lo detecta.
    _still = sync_limits.video_stillness(str(video_path))
    if _still:
        result["video_still_ms"]    = _still.get("longest_still_ms")
        result["video_still_ratio"] = _still.get("still_ratio")
        result["video_still"]       = sync_limits.is_video_still(_still)

    # â€” Gate AFK: rechazar sesiones con demasiado tiempo continuo sin inputs â€”
    # (mismo cÃ¡lculo de idle que el bloque activity del metadata)
    try:
        _starts = [s for s, e in csv_anchors if s]
        _ends   = [e for s, e in csv_anchors if e]
        if _starts and _ends:
            _act = _meta_activity(session_dir, min(_starts), max(_ends))
            if _act:
                result["longest_idle_s"] = _act.get("longest_idle_seconds")
                # Dos brazos: hueco absoluto > 10 min, o hueco que ocupa mÃ¡s de
                # la mitad de la sesiÃ³n â€” una sesiÃ³n corta que es casi toda un
                # solo hueco pasaba el umbral absoluto sin ser gameplay vÃ¡lido.
                result["idle_fraccion"] = sync_limits.idle_fraccion(
                    _act.get("longest_idle_seconds"), csv_dur)
                if sync_limits.is_afk(_act.get("longest_idle_seconds"), csv_dur):
                    result["afk"] = True
    except Exception:
        pass   # si el cÃ¡lculo falla, no bloquear la sesiÃ³n por esto

    # â€” Gate de input vacÃ­o: la sesiÃ³n no registrÃ³ lo que hizo el jugador â€”
    # El gate AFK mide HUECOS entre eventos y necesita al menos dos para medir
    # algo: con los CSV vacÃ­os devuelve None y no gatea nada. O sea que el peor
    # caso posible â€”cero inputâ€” era el que mÃ¡s limpio pasaba el check. Este mira
    # el volumen, no los huecos, y por eso sÃ­ lo agarra.
    # A diferencia de los otros gates, este NO se traga la excepciÃ³n: si no se
    # pueden contar los eventos, la sesiÃ³n no se declara buena.
    _conteo = sync_limits.contar_eventos_input(session_dir)
    result["eventos_input"]   = _conteo
    result["sin_input"]       = sync_limits.is_sin_input(_conteo, csv_dur)
    result["sin_input_causa"] = sync_limits.diagnostico_sin_input(_conteo, csv_dur)

    result["session_ok"] = (result["csvs_ok"] and result["video_ok"]
                            and not result["afk"] and not result["video_still"]
                            and not result["sin_input"])
    return result

# â”€â”€â”€ Packager â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def package_session(session_dir):
    """
    Crea un ZIP con todos los archivos de la sesiÃ³n (sin cifrar).
    Guarda como <sessionName>.pleiada en el mismo directorio padre.
    Retorna path del archivo generado, o None si falla.
    """
    try:
        out_name = session_dir.name + ".pleiada"
        out_path = session_dir.parent / out_name
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(session_dir.iterdir()):
                if p.is_file():
                    zf.write(p, p.name)
        return out_path
    except Exception as e:
        _obs_dbg(f"package_session error: {e}")
        return None

# â”€â”€â”€ Session metadata (v0.4) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _meta_csv_anchors(session_dir):
    """Lee ANCHOR_START y ANCHOR_END de video_timeline.csv. Retorna (start_ms, end_ms)."""
    try:
        with open(session_dir / "video_timeline.csv", encoding="utf-8") as f:
            start = end = None
            for row in _csv_mod.reader(f):
                if len(row) >= 2:
                    if row[1] == "ANCHOR_START" and start is None:
                        start = int(row[0])
                    elif row[1] == "ANCHOR_END":
                        end = int(row[0])
            return start, end
    except Exception:
        return None, None

def _meta_input_hz(session_dir):
    """Calcula Hz de muestreo de video_timeline y posiciÃ³n de mouse desde los CSVs."""
    result = {}
    for fname, events in [("video_timeline.csv", {"FRAME"}),
                           ("mouse_log.csv",      {"MOVE"})]:
        try:
            ts = []
            with open(session_dir / fname, encoding="utf-8") as f:
                for row in _csv_mod.reader(f):
                    if len(row) >= 2 and row[1] in events:
                        ts.append(int(row[0]))
            if len(ts) > 10:
                intervals = [ts[i+1] - ts[i] for i in range(len(ts)-1) if ts[i+1] > ts[i]]
                if intervals:
                    result[fname.replace(".csv", "")] = round(1000 / (sum(intervals) / len(intervals)), 1)
        except Exception:
            pass
    return result

def _meta_video_info(session_dir):
    """
    Extrae resoluciÃ³n, FPS, codec, frame count y bitrate del MP4 vÃ­a OpenCV.
    OBS no incluye ffprobe standalone, pero opencv-python es dependencia del Recorder.
    """
    try:
        mp4s = list(session_dir.glob("*.mp4"))
        if not mp4s:
            return {}
        import cv2
        path = str(mp4s[0])
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return {}
        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))  or None
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or None
        fps    = cap.get(cv2.CAP_PROP_FPS)
        fps    = round(fps, 2) if fps else None
        nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        nframes = nframes if nframes > 0 else None
        fourcc  = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec   = ("".join(chr((fourcc >> 8*i) & 0xFF) for i in range(4)).strip("\x00 ")
                   if fourcc else None) or None
        cap.release()

        # Bitrate promedio real = tamaÃ±o / duraciÃ³n
        bitrate = None
        try:
            if fps and nframes:
                dur_s = nframes / fps
                if dur_s > 0:
                    bitrate = round(os.path.getsize(path) * 8 / dur_s / 1000)
        except Exception:
            pass

        return {
            "width":         width,
            "height":        height,
            "fps_nominal":   fps,
            "codec":         codec,
            "frame_count":   nframes,
            "bitrate_kbps":  bitrate,
        }
    except Exception as e:
        _obs_dbg(f"_meta_video_info: {e}")
        return {}

def _meta_hardware():
    """CPU, RAM, GPUs, resoluciÃ³n y refresh rate del monitor principal."""
    hw = {}
    # CPU
    try:
        hw["cpu"] = _platform.processor() or None
    except Exception:
        hw["cpu"] = None
    # RAM via GlobalMemoryStatusEx
    try:
        import ctypes as _ct_hw
        class _MEM(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_uint), ("dwMemoryLoad", ctypes.c_uint),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        ms = _MEM(); ms.dwLength = ctypes.sizeof(_MEM)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
        hw["ram_gb"] = round(ms.ullTotalPhys / (1024 ** 3), 1)
    except Exception:
        hw["ram_gb"] = None
    # GPUs via wmic (Windows 10/11, deprecado en 24H2 pero aÃºn funcional)
    try:
        r = subprocess.run(
            ["wmic", "path", "win32_VideoController", "get", "name,DriverVersion", "/format:csv"],
            capture_output=True, text=True, timeout=8,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        gpus = []
        for line in r.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3 and parts[2] and parts[2] != "Name":
                gpus.append({"name": parts[2], "driver": parts[1]})
        hw["gpus"] = gpus or None
    except Exception:
        hw["gpus"] = None
    # Monitor â€” resoluciÃ³n
    try:
        hw["monitor_width"]  = ctypes.windll.user32.GetSystemMetrics(0)
        hw["monitor_height"] = ctypes.windll.user32.GetSystemMetrics(1)
    except Exception:
        hw["monitor_width"] = hw["monitor_height"] = None
    # Monitor â€” refresh rate via GetDeviceCaps(VREFRESH) â€” simple y confiable
    try:
        VREFRESH = 116
        hdc = ctypes.windll.user32.GetDC(0)
        hz  = ctypes.windll.gdi32.GetDeviceCaps(hdc, VREFRESH)
        ctypes.windll.user32.ReleaseDC(0, hdc)
        hw["monitor_refresh_hz"] = hz if hz and hz > 1 else None
    except Exception:
        hw["monitor_refresh_hz"] = None
    return hw

def _meta_os():
    """OS name, version y build number."""
    try:
        ver = _platform.version()
        build = ver.split(".")[-1] if "." in ver else None
        return {"name": _platform.system(), "version": _platform.release(), "build": build}
    except Exception:
        return {"name": None, "version": None, "build": None}

# â”€â”€ Fase 2: helpers de detecciÃ³n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _meta_exe_path(exe_name):
    """Retorna la ruta completa del proceso exe_name via wmic, o None si no corre."""
    if not exe_name:
        return None
    try:
        r = subprocess.run(
            ["wmic", "process", "where", f'name="{exe_name}"',
             "get", "ExecutablePath", "/format:list"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        for line in r.stdout.splitlines():
            if line.startswith("ExecutablePath=") and line[15:].strip():
                return line[15:].strip()
    except Exception:
        pass
    return None

def _meta_pid_image_path(pid):
    """Ruta completa del ejecutable de un PID via QueryFullProcessImageNameW."""
    try:
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return None
        buf  = ctypes.create_unicode_buffer(4096)
        size = ctypes.c_uint(4096)
        ok = ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        ctypes.windll.kernel32.CloseHandle(h)
        return buf.value if ok else None
    except Exception:
        return None

def _meta_find_game_exe_path(obs_window, game_name):
    """
    Resuelve la ruta completa del .exe del juego (juego debe estar corriendo).
    Fallbacks en orden:
      1. .exe del window string de OBS  ->  wmic
      2. ventana visible cuyo tÃ­tulo matchee el de OBS o el nombre del juego  -> PID -> ruta
    Loguea el resultado para diagnÃ³stico.
    """
    # 1. .exe expuesto por OBS en el window string ("Title:Class:exe")
    # unescape DESPUÃ‰S del split (ver _obs_unescape)
    exe = next((_obs_unescape(p.strip()) for p in (obs_window or "").split(":")
                if p.strip().lower().endswith(".exe")), "")
    if exe:
        path = _meta_exe_path(exe)
        if path:
            _obs_dbg(f"exe_path via OBS exe '{exe}': {path}")
            return path

    # 2. Buscar la ventana del juego por tÃ­tulo y resolver su PID -> ruta
    obs_title = _obs_unescape((obs_window or "").split(":")[0].strip())
    cands = [c for c in (obs_title, game_name) if c]
    if not cands:
        _obs_dbg(f"exe_path: sin candidatos de tÃ­tulo (obs_window='{obs_window}')")
        return None

    def _n(s):
        return re.sub(r"[^a-z0-9]+", "", s.lower())
    cand_norm = [_n(c) for c in cands]

    # Procesos shell/sistema que NUNCA son el juego â€” Bug 8: el Explorador abierto
    # en la carpeta "Euro Truck Simulator 2_..." matcheaba por tÃ­tulo y resolvÃ­a a
    # explorer.exe. Excluimos estos del match.
    _SYS_EXE = {
        "explorer.exe", "applicationframehost.exe", "searchhost.exe",
        "searchapp.exe", "shellexperiencehost.exe", "dwm.exe", "sihost.exe",
        "startmenuexperiencehost.exe", "textinputhost.exe", "code.exe",
        "chrome.exe", "msedge.exe", "firefox.exe", "obs64.exe",
        "pythonw.exe", "python.exe", "autohotkey64.exe",
    }

    result = {"path": None}

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_long)
    def _cb(hwnd, _):
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True
        n = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if n <= 0:
            return True
        b = ctypes.create_unicode_buffer(n + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, b, n + 1)
        wt = _n(b.value)
        if wt and any(cn and (cn in wt or wt in cn) for cn in cand_norm):
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            path = _meta_pid_image_path(pid.value)
            # descartar procesos shell/sistema (no son el juego)
            if path and os.path.basename(path).lower() in _SYS_EXE:
                return True   # seguir buscando
            if path:
                result["path"] = path
                return False
        return True

    try:
        ctypes.windll.user32.EnumWindows(_cb, 0)
    except Exception:
        pass

    if result["path"]:
        _obs_dbg(f"exe_path via window title: {result['path']}")
        return result["path"]

    _obs_dbg(f"exe_path: no resuelto (obs_window='{obs_window}', game='{game_name}')")
    return None

def _meta_detect_engine(game_dir):
    """Detecta el motor del juego por firmas de archivos en el directorio de instalaciÃ³n."""
    if not game_dir or not os.path.isdir(game_dir):
        return None
    checks = [
        # (ruta relativa al game_dir, nombre del motor)
        # â€” orden importa: firmas mÃ¡s especÃ­ficas primero â€”
        (os.path.join("Engine", "Binaries"),       "Unreal Engine"),
        (os.path.join("Engine", "Config"),         "Unreal Engine"),
        ("UnityPlayer.dll",                        "Unity"),
        # Source 2: estructura game/bin/win64 con engine2.dll (NO usar vscript.dll,
        # que tambiÃ©n existe en Source 1 â€” daba falso positivo en Portal 2).
        (os.path.join("bin", "win64", "engine2.dll"), "Source 2"),
        (os.path.join("game", "bin", "win64"),     "Source 2"),
        # Source 1: engine.dll / tier0.dll en bin/
        (os.path.join("bin", "engine.dll"),        "Source"),
        (os.path.join("bin", "tier0.dll"),         "Source"),
        ("tier0.dll",                              "Source"),
        ("CrySystem.dll",                          "CryEngine"),
        ("frostbite.dll",                          "Frostbite"),
        ("REDprelauncher.exe",                     "REDengine"),
        (os.path.join("bin", "REDprelauncher.exe"), "REDengine"),
    ]
    for rel, engine in checks:
        if os.path.exists(os.path.join(game_dir, rel)):
            # Distinguir UE4 vs UE5 por BaseEngine.ini si es posible
            if engine == "Unreal Engine":
                ini = os.path.join(game_dir, "Engine", "Config", "BaseEngine.ini")
                if os.path.isfile(ini):
                    try:
                        with open(ini, encoding="utf-8", errors="ignore") as f:
                            txt = f.read(4096)
                        if "5." in txt and "EngineVersion" in txt:
                            return "Unreal Engine 5"
                        return "Unreal Engine 4"
                    except Exception:
                        pass
            return engine
    return None

def _meta_game_version(exe_path):
    """Lee el FileVersion del PE del ejecutable del juego via ctypes VerQueryValue."""
    if not exe_path or not os.path.isfile(exe_path):
        return None
    try:
        size = ctypes.windll.version.GetFileVersionInfoSizeW(exe_path, None)
        if not size:
            return None
        buf = ctypes.create_string_buffer(size)
        if not ctypes.windll.version.GetFileVersionInfoW(exe_path, 0, size, buf):
            return None
        p_info  = ctypes.c_void_p()
        n_info  = ctypes.c_uint()
        if ctypes.windll.version.VerQueryValueW(
            buf, "\\", ctypes.byref(p_info), ctypes.byref(n_info)
        ):
            class _FFI(ctypes.Structure):
                _fields_ = [
                    ("sig",   ctypes.c_uint32), ("struc", ctypes.c_uint32),
                    ("fvMS",  ctypes.c_uint32), ("fvLS",  ctypes.c_uint32),
                    ("pvMS",  ctypes.c_uint32), ("pvLS",  ctypes.c_uint32),
                    ("_rest", ctypes.c_byte * 28),
                ]
            fi = ctypes.cast(p_info, ctypes.POINTER(_FFI)).contents
            if fi.sig == 0xFEEF04BD:
                ma = fi.fvMS >> 16; mi = fi.fvMS & 0xFFFF
                pa = fi.fvLS >> 16; bu = fi.fvLS & 0xFFFF
                return f"{ma}.{mi}.{pa}.{bu}"
    except Exception:
        pass
    return None

def _meta_window_mode(exe_name):
    """Detecta si el juego corre en windowed, borderless o fullscreen."""
    if not exe_name:
        return None
    try:
        # Obtener PID
        r = subprocess.run(
            ["wmic", "process", "where", f'name="{exe_name}"',
             "get", "ProcessId", "/format:list"],
            capture_output=True, text=True, timeout=4,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        target_pid = None
        for line in r.stdout.splitlines():
            if line.startswith("ProcessId=") and line[10:].strip():
                target_pid = int(line[10:].strip())
                break
        if not target_pid:
            return None

        # Buscar ventana principal del proceso
        game_hwnd = ctypes.c_void_p(None)

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_long)
        def _cb(hwnd, _):
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == target_pid and ctypes.windll.user32.IsWindowVisible(hwnd):
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                if (rect.right - rect.left) > 200 and (rect.bottom - rect.top) > 200:
                    game_hwnd.value = hwnd
                    return False
            return True

        ctypes.windll.user32.EnumWindows(_cb, 0)
        if not game_hwnd.value:
            return None

        WS_CAPTION = 0x00C00000
        style  = ctypes.windll.user32.GetWindowLongW(game_hwnd.value, -16)
        rect   = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(game_hwnd.value, ctypes.byref(rect))
        win_w  = rect.right  - rect.left
        win_h  = rect.bottom - rect.top
        scr_w  = ctypes.windll.user32.GetSystemMetrics(0)
        scr_h  = ctypes.windll.user32.GetSystemMetrics(1)
        fills  = abs(win_w - scr_w) <= 4 and abs(win_h - scr_h) <= 4
        has_chrome = bool(style & WS_CAPTION)

        if has_chrome and not fills:
            return "windowed"
        elif fills and not has_chrome:
            return "borderless"
        elif fills:
            return "fullscreen"
        return "windowed"
    except Exception:
        return None

def _meta_system_language():
    """Retorna el locale del usuario (ej: 'es-AR', 'en-US')."""
    try:
        buf = ctypes.create_unicode_buffer(85)
        ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85)
        return buf.value or None
    except Exception:
        try:
            import locale as _lc
            lang, _ = _lc.getdefaultlocale()
            return lang
        except Exception:
            return None

# â”€â”€ Key mapping parsers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_UE_KEY_MAP = {
    "SpaceBar": "Space", "LeftShift": "LShift", "RightShift": "RShift",
    "LeftControl": "LCtrl", "RightControl": "RCtrl",
    "LeftAlt": "LAlt", "RightAlt": "RAlt",
    "LeftMouseButton": "LButton", "RightMouseButton": "RButton",
    "MiddleMouseButton": "MButton",
    "MouseScrollUp": "WheelUp", "MouseScrollDown": "WheelDown",
}
# Mapeo EXACTO (action name en lowercase â†’ semÃ¡ntica normalizada). Las acciones
# no listadas conservan su nombre real del juego en snake_case (preciso y honesto).
_UE_ACTION_SEM = {
    "jump": "jump", "dodge": "dodge_roll", "roll": "dodge_roll",
    "interact": "interact", "use": "interact", "altinteract": "interact_alt",
    "sprint": "sprint", "crouch": "crouch", "duck": "crouch",
    "altfire": "attack_secondary", "attack": "attack_primary",
    "lightattack": "attack_fast", "heavyattack": "attack_strong", "block": "block",
    "aim": "aim", "zoom": "aim", "fire": "attack_primary",
    "reload": "reload", "openinventory": "open_inventory",
    "inventory": "open_inventory", "crafting": "open_crafting",
    "map": "open_map", "openmap": "open_map", "pause": "pause_menu",
    "primaryaction": "attack_primary", "secondaryaction": "attack_secondary",
    "freelook": "free_look",
}

def _camel_snake(s):
    """AltInteract -> alt_interact, ChangeFireMode -> change_fire_mode."""
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", s)
    return re.sub(r"_+", "_", s).lower()

def _parse_ue_input_ini(ini_path):
    """
    Parsea un Input.ini de Unreal Engine. Soporta DOS formatos:
      1. Legacy:  +ActionMappings=(ActionName="X",...,Key=Y) / +AxisMappings=...
      2. Custom (UserActionMappings/UserAxisMappings con secciones Keyboard=/
         Controller=), p.ej. el de Icarus [/Script/Icarus.IcarusPlayerInput].
    En el formato 2 se descartan los binds de gamepad (Key=Gamepad_*).
    """
    mapping = {}
    try:
        with open(ini_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return mapping

    def _add_action(action, key):
        if key.startswith("Gamepad_"):
            return
        k   = _UE_KEY_MAP.get(key, key)
        # match exacto; si no, nombre real del juego en snake_case
        sem = _UE_ACTION_SEM.get(action.lower()) or _camel_snake(action)
        mapping.setdefault(k, sem)

    def _add_axis(axis, scale, key):
        if key.startswith("Gamepad_"):
            return
        k  = _UE_KEY_MAP.get(key, key)
        al = axis.lower()
        try:
            sc = float(scale) if scale not in (None, "") else 1.0
        except Exception:
            sc = 1.0
        # CÃ¡mara (look/turn/yaw/pitch) ANTES que movimiento â€” "LookRight" contiene
        # "right" pero es cÃ¡mara, no strafe.
        if "look" in al or "turn" in al or "yaw" in al or "pitch" in al:
            if "up" in al or "pitch" in al:
                mapping.setdefault(k, "look_up" if sc > 0 else "look_down")
            else:
                mapping.setdefault(k, "look_right" if sc > 0 else "look_left")
        elif "forward" in al or "backward" in al:
            mapping.setdefault(k, "move_forward" if sc > 0 else "move_backward")
        elif "right" in al or "left" in al or "strafe" in al:
            mapping.setdefault(k, "move_right" if sc > 0 else "move_left")

    # â”€â”€ Formato 1: legacy +ActionMappings / +AxisMappings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    legacy = False
    for m in re.finditer(r'\+ActionMappings=\(ActionName="([^"]+)".*?Key=([^,)]+)', content):
        legacy = True
        _add_action(m.group(1), m.group(2).strip())
    for m in re.finditer(r'\+AxisMappings=\(AxisName="([^"]+)".*?Scale=([^,]+).*?Key=([^,)]+)', content):
        legacy = True
        _add_axis(m.group(1), m.group(2), m.group(3).strip())

    # â”€â”€ Formato 2: custom UserActionMappings / UserAxisMappings (Icarus, etc.) â”€
    if not legacy:
        for m in re.finditer(r'ActionName="([^"]+)",Key=(\w+)', content):
            _add_action(m.group(1), m.group(2))
        for m in re.finditer(r'AxisName="([^"]+)"(?:,Scale=(-?[\d.]+))?,Key=(\w+)', content):
            _add_axis(m.group(1), m.group(2), m.group(3))

    return mapping

# â”€â”€ BÃºsqueda amplia del juego en cualquier disco (Steam libraries) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _meta_steam_libraries():
    """Retorna todas las rutas de bibliotecas de Steam (cualquier disco)."""
    roots = []
    for env in ("ProgramFiles(x86)", "ProgramFiles"):
        base = os.environ.get(env)
        if base:
            roots.append(os.path.join(base, "Steam"))
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            p, _ = winreg.QueryValueEx(k, "SteamPath")
            if p:
                roots.append(p.replace("/", "\\"))
    except Exception:
        pass

    libs = []
    for root in roots:
        if root and os.path.isdir(root):
            libs.append(root)
        vdf = os.path.join(root, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            try:
                with open(vdf, encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                for m in re.finditer(r'"path"\s*"([^"]+)"', txt):
                    libs.append(m.group(1).replace("\\\\", "\\"))
            except Exception:
                pass
    return list(dict.fromkeys(libs))   # dedup preservando orden

def _meta_find_install_dir(game_name):
    """Busca la carpeta de instalaciÃ³n del juego en todas las Steam libraries."""
    if not game_name:
        return None
    def _n(s):
        return re.sub(r"[^a-z0-9]+", "", s.lower())
    target = _n(game_name)
    if not target:
        return None
    for lib in _meta_steam_libraries():
        common = os.path.join(lib, "steamapps", "common")
        if not os.path.isdir(common):
            continue
        try:
            for entry in os.listdir(common):
                en = _n(entry)
                if not en:
                    continue
                # match exacto, o substring solo si es largo (>=5) â€” evita que un
                # nombre corto matchee la carpeta de otro juego (mismo criterio que Unreal).
                if (en == target
                        or (len(target) >= 5 and target in en)
                        or (len(en) >= 5 and en in target)):
                    return os.path.join(common, entry)
        except Exception:
            pass
    return None

def _meta_unreal_key_mapping(game_dir, game_name="", exe_path=""):
    """
    Busca key mapping de un juego Unreal Engine:
    1. Input.ini del usuario en %LOCALAPPDATA%\\{Proyecto}\\... â†’ binding_source: 'config'
    2. DefaultInput.ini del juego (en install dir, cualquier disco) â†’ 'default'

    IMPORTANTE: el match de la carpeta debe ser CONFIABLE. Si no se identifica el
    Input.ini del juego correcto, se devuelve None (â†’ se infiere del gameplay).
    NO se usa "el mÃ¡s reciente" como fallback, porque agarraba el Input.ini de OTRO
    juego (bug: a "The Last Caretaker" le asignaba el mapping de Icarus).
    """
    def _n(s):
        return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

    # Nombres candidatos para identificar la carpeta del proyecto en LOCALAPPDATA:
    #  - nombre del proyecto Unreal derivado del exe ("VoyageSteam-Win64-Shipping" â†’ "voyagesteam")
    #  - nombre de la carpeta de instalaciÃ³n
    #  - nombre del juego (Airtable)
    proj_names = set()
    if exe_path:
        base = os.path.basename(exe_path)
        base = re.sub(r"\.exe$", "", base, flags=re.IGNORECASE)
        # quitar sufijos tÃ­picos de Unreal: -Win64-Shipping, -WinGDK-Shipping, -Shipping, -Win64-Test...
        base = re.sub(r"[-_](Win64|WinGDK|Win32)([-_](Shipping|Test|Development))?$", "", base, flags=re.IGNORECASE)
        base = re.sub(r"[-_](Shipping|Test|Development)$", "", base, flags=re.IGNORECASE)
        if _n(base):
            proj_names.add(_n(base))
    if game_dir:
        # .../{Project}/Binaries/Win64 â†’ {Project}
        proj_names.add(_n(os.path.basename(os.path.dirname(os.path.dirname(game_dir)))))
    if game_name:
        proj_names.add(_n(game_name))
    proj_names.discard("")

    def _folder_matches(path):
        folder = _n(path.split(os.sep + "Saved")[0].rsplit(os.sep, 1)[-1])
        if not folder:
            return False
        for p in proj_names:
            if folder == p:
                return True
            # match parcial SOLO si el nombre compartido es largo (>=5 chars) â€” evita
            # falsos positivos de carpetas cortas (ej: "AS" âŠ‚ "theLASTcaretaker").
            if len(folder) >= 5 and folder in p:
                return True
            if len(p) >= 5 and p in folder:
                return True
        return False

    # â”€â”€ Paso 1: Input.ini del usuario (solo si matchea el proyecto con certeza) â”€
    local = os.environ.get("LOCALAPPDATA", "")
    if local and proj_names:
        candidates  = glob.glob(os.path.join(local, "*", "Saved", "Config", "WindowsNoEditor", "Input.ini"))
        candidates += glob.glob(os.path.join(local, "*", "Saved", "Config", "Windows*", "Input.ini"))
        candidates  = list(dict.fromkeys(candidates))
        ini = next((c for c in candidates if _folder_matches(c)), None)
        if ini and os.path.isfile(ini):
            mapping = _parse_ue_input_ini(ini)
            if mapping:
                _obs_dbg(f"unreal key mapping: config usuario {ini} ({len(mapping)} binds)")
                return mapping, "config"

    # â”€â”€ Paso 2: DefaultInput.ini del juego (install dir, cualquier disco) â”€â”€â”€â”€â”€â”€
    search_dirs = [d for d in (game_dir, _meta_find_install_dir(game_name)) if d]
    for sd in search_dirs:
        # buscar recursivamente Config/DefaultInput.ini hasta 2 niveles
        for pat in (os.path.join(sd, "Config", "DefaultInput.ini"),
                    os.path.join(sd, "*", "Config", "DefaultInput.ini"),
                    os.path.join(sd, "*", "*", "Config", "DefaultInput.ini")):
            for di in glob.glob(pat):
                mapping = _parse_ue_input_ini(di)
                if mapping:
                    _obs_dbg(f"unreal key mapping: default {di} ({len(mapping)} binds)")
                    return mapping, "default"

    return None, "unknown"

_SOURCE_SEM = {
    "+forward": "move_forward", "+back": "move_backward",
    "+moveleft": "move_left",   "+moveright": "move_right",
    "+jump": "jump",            "+duck": "crouch",
    "+speed": "sprint",         "+attack": "attack_primary",
    "+attack2": "attack_secondary", "+use": "interact",
    "+reload": "reload",        "+zoom": "aim",
}

def _meta_source_key_mapping(game_dir, game_name=""):
    """Parsea config.cfg de un juego Source Engine.
    El config vive en {install_dir}/{mod}/cfg/config.cfg (mod = portal2, hl2, csgo...).
    Busca en el dir del exe y, si falla, en el install dir (cualquier disco) por nombre.
    """
    search_dirs = [d for d in (game_dir, _meta_find_install_dir(game_name)) if d and os.path.isdir(d)]
    cfg = None
    for sd in search_dirs:
        cfg_candidates  = glob.glob(os.path.join(sd, "cfg", "config.cfg"))
        cfg_candidates += glob.glob(os.path.join(sd, "*", "cfg", "config.cfg"))
        cfg = next((p for p in cfg_candidates if os.path.isfile(p)), None)
        if cfg:
            break
    if not cfg:
        _obs_dbg(f"source key mapping: config.cfg no encontrado (dirs={search_dirs})")
        return None, "unknown"
    _obs_dbg(f"source key mapping: usando {cfg}")
    # Tokens de teclas de gamepad/controller â€” se excluyen del key_mapping de
    # teclado/mouse (el config.cfg de Source bindea ambos al mismo comando).
    _GAMEPAD_TOKENS = ("_BUTTON", "_TRIGGER", "_SHOULDER", "STICK", "DPAD",
                       "A_BUTTON", "B_BUTTON", "X_BUTTON", "Y_BUTTON", "BACK", "START")
    try:
        mapping = {}
        with open(cfg, encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.match(r'bind\s+"([^"]+)"\s+"([^"]+)"', line.strip(), re.IGNORECASE)
                if m:
                    key, cmd = m.group(1).upper(), m.group(2).lower()
                    # Filtrar binds de gamepad â€” solo teclado y mouse
                    if any(tok in key for tok in _GAMEPAD_TOKENS):
                        continue
                    sem = _SOURCE_SEM.get(cmd)
                    if sem:
                        mapping[key] = sem
        return (mapping, "config") if mapping else (None, "unknown")
    except Exception:
        return None, "unknown"

# ConvenciÃ³n general de inferencia (piso FPS/acciÃ³n). Hoisteada a nivel de mÃ³dulo
# para reutilizarla tanto en la inferencia como en el cÃ¡lculo de possible_remaps.
_INFER_CONV = {
    "w": "move_forward", "a": "move_left", "s": "move_backward", "d": "move_right",
    "space": "jump", "shift": "sprint", "control": "crouch", "ctrl": "crouch",
    "c": "crouch_toggle", "alt": "walk", "e": "interact", "r": "reload",
    "f": "use_or_flashlight", "q": "lean_or_ability", "v": "melee", "g": "throw_grenade",
    "tab": "inventory", "i": "inventory", "b": "build_menu", "j": "journal",
    "escape": "pause_menu", "1": "hotbar_1", "2": "hotbar_2", "3": "hotbar_3",
    "4": "hotbar_4", "5": "hotbar_5",
}
_INFER_MOUSE_CONV = {"LEFT": "attack_primary", "RIGHT": "aim_or_secondary",
                     "MIDDLE": "special", "X1": "extra_1", "X2": "extra_2"}

# Teclas multimedia/sistema que NO son acciones de gameplay â€” se ignoran al mapear
# y no se reportan como possible_remap (ruido para los AI Labs).
_NON_GAMEPLAY_KEYS = {
    "Volume_Up", "Volume_Down", "Volume_Mute", "Media_Play_Pause", "Media_Next",
    "Media_Prev", "Media_Stop", "Browser_Back", "Browser_Forward", "Browser_Home",
    "Launch_Mail", "Launch_Media", "Sleep", "PrintScreen", "Pause", "NumLock",
    "ScrollLock", "Insert", "Apps", "LWin", "RWin",
}

def _norm_key_for_conv(k):
    """Normaliza variantes L/R de modificadores al nombre de la convenciÃ³n.
    El logger escribe 'LShift'/'LControl'/'LAlt'; la convenciÃ³n usa 'shift'/'control'/'alt'.
    Sin esto, LShift (sprint) y LControl (crouch) se caÃ­an del mapping (bug histÃ³rico)."""
    kl = (k or "").lower()
    if kl in ("lshift", "rshift"):
        return "shift"
    if kl in ("lcontrol", "rcontrol", "lctrl", "rctrl"):
        return "control"
    if kl in ("lalt", "ralt", "lmenu", "rmenu"):
        return "alt"
    return kl

def _meta_observed_keys(session_dir):
    """Cuenta teclas/botones realmente usados en la sesiÃ³n.
    Retorna (keys_counter, mouse_counter, keys_observed_dict)."""
    import collections
    keys, mouse = collections.Counter(), collections.Counter()
    try:
        with open(session_dir / "key_log.csv", encoding="utf-8") as f:
            for r in _csv_mod.reader(f):
                if len(r) >= 3 and r[1] == "KEY_DOWN" and r[2]:
                    keys[r[2]] += 1
    except Exception:
        pass
    try:
        with open(session_dir / "mouse_log.csv", encoding="utf-8") as f:
            for r in _csv_mod.reader(f):
                if len(r) >= 5 and "BUTTON_DOWN" in r[1] and r[4]:
                    mouse[r[4]] += 1
    except Exception:
        pass
    keys_observed = {"keyboard": dict(keys.most_common()),
                     "mouse_buttons": dict(mouse.most_common())}
    return keys, mouse, keys_observed

def _meta_infer_key_mapping(session_dir):
    """
    Infiere el key mapping de las teclas/botones realmente usados en la sesiÃ³n
    + convenciÃ³n FPS/acciÃ³n. Fallback cuando no se encuentra config ni game_default.
    Retorna (mapping, keys_observed).
    """
    keys, mouse, keys_observed = _meta_observed_keys(session_dir)
    mapping = {}
    for k in keys:
        nk = _norm_key_for_conv(k)
        if nk in _INFER_CONV:
            mapping[k] = _INFER_CONV[nk]
        elif k in _NON_GAMEPLAY_KEYS:
            continue
        elif keys[k] >= 3:
            # Tecla usada con frecuencia pero sin acciÃ³n conocida: no la perdemos.
            mapping[k] = "unknown_action"
    for b in mouse:
        if b.upper() in _INFER_MOUSE_CONV:
            mapping[f"Mouse{b.capitalize()}"] = _INFER_MOUSE_CONV[b.upper()]
    return mapping, keys_observed

def _meta_possible_remaps(key_mapping, keys_observed):
    """
    Teclas/botones observados que NO estÃ¡n en el mapping autoritativo (config o
    game_default). Posible remap del usuario o bind extra. NO se pisa el mapping:
    se reporta aparte con un guess inferido + conteo. Retorna lista (puede ser []).
    El default no se 'resta' por falta de uso (no es seÃ±al confiable de remap).
    """
    if not keys_observed:
        return []
    mapped = set(key_mapping or {})
    out = []
    for k, n in (keys_observed.get("keyboard") or {}).items():
        if k in mapped or k in _NON_GAMEPLAY_KEYS:
            continue
        out.append({"key": k, "count": n,
                    "inferred_action": _INFER_CONV.get(_norm_key_for_conv(k), "unknown_action")})
    for b, n in (keys_observed.get("mouse_buttons") or {}).items():
        mk = f"Mouse{b.capitalize()}"
        if mk in mapped:
            continue
        out.append({"key": mk, "count": n,
                    "inferred_action": _INFER_MOUSE_CONV.get(b.upper(), "unknown_action")})
    return out

def _meta_activity(session_dir, start_ms, end_ms):
    """
    Mide actividad de input vs inactividad (cutscenes / menÃºs / AFK).
    Implementado en pleiada_sync_limits para que el gate AFK de acÃ¡ y el del
    Synch Checker corran exactamente el mismo cÃ¡lculo.
    """
    return sync_limits.activity(session_dir, start_ms, end_ms)

def _meta_key_mapping(exe_path, engine, game_name=""):
    """
    Dispatcher de key mapping. SIEMPRE intenta primero el config REAL del juego
    (Source: config.cfg / Unreal: Input.ini), buscÃ¡ndolo en cualquier disco.
    La inferencia del gameplay queda como fallback (se hace fuera, en build_session_metadata).
    """
    game_dir = os.path.dirname(exe_path) if exe_path else None
    eng = (engine or "").lower()
    if "unreal" in eng:
        return _meta_unreal_key_mapping(game_dir, game_name, exe_path)
    elif "source" in eng:
        return _meta_source_key_mapping(game_dir, game_name)
    return None, "unknown"  # Unity y otros: sin parser â†’ se infiere del gameplay


# â”€â”€â”€ Integridad y protecciÃ³n de archivos (v0.7 / schema 1.1) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _sha256_file(path):
    """SHA-256 de un archivo, leyendo en bloques de 1 MB (soporta MP4 grandes)."""
    h = _hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_integrity(session_dir):
    """
    Bloque de integridad: SHA-256 de los 4 CSV + el MP4 + el demo .dem (POV de TF2/L4D2,
    si existe), sobre los bytes finales (todo ya cerrado por el AHK y movido por OBS, y el
    demo ya copiado a la carpeta de sesiÃ³n). Certifica el ORIGINAL en el momento de captura;
    cualquier ediciÃ³n posterior cambia el hash â†’ la sesiÃ³n se rechaza en el upload. No incluye
    al propio session_metadata.json (no puede hashearse a sÃ­ mismo).

    Las claves son el nombre real del archivo en disco, que desde v0.8.12 coincide con el
    del objeto en S3 (ver `_safe_filename`). `naming: "s3-safe"` lo certifica: si el campo
    estÃ¡, el consumidor puede buscar el hash por el nombre del archivo tal cual lo recibe.
    Los datasets subidos antes de v0.8.12 no lo traen y pueden tener el MP4 con espacios
    acÃ¡ y con guiones bajos en S3 â€” para esos hay que indexar por las dos formas.
    """
    files = {}
    names = ["mouse_log.csv", "mouse_delta_log.csv", "key_log.csv", "video_timeline.csv"]
    targets = ([session_dir / n for n in names] + sorted(session_dir.glob("*.mp4"))
               + sorted(session_dir.glob("*.dem")))   # incluir el demo POV (TF2/L4D2) en el hash
    for p in targets:
        try:
            if p.is_file():
                files[p.name] = _sha256_file(p)
        except Exception as e:
            _obs_dbg(f"_build_integrity: {p.name}: {e}")
    bloque = {
        "algorithm": "sha256",
        "note": ("Hashes of the dataset as recorded by Gameplay Recorder. They certify the "
                 "ORIGINAL files at capture time; any later edit changes the hash and the "
                 "session is rejected at upload. AI Lab derivatives/preprocessing do not "
                 "affect this record."),
        "files": files,
    }
    # Solo se declara si TODOS los nombres ya son safe: el marcador es una garantÃ­a para el
    # consumidor, asÃ­ que no se emite cuando algÃºn archivo llegÃ³ con un nombre inesperado
    # (p. ej. una sesiÃ³n vieja reprocesada, con el MP4 con espacios todavÃ­a en disco).
    if files and all(n == _safe_filename(n) for n in files):
        bloque["naming"] = "s3-safe"
    return bloque


def _protect_session_files(session_dir):
    """
    Marca CSVs + MP4 + JSON + demo .dem (POV de TF2/L4D2) como solo-lectura. Disuasivo y seÃ±al de finalidad: el usuario
    puede leerlos y descartar la sesiÃ³n entera, pero no editarlos accidentalmente. Es
    removible por el dueÃ±o del equipo â€” la garantÃ­a real de no-ediciÃ³n la da el manifiesto
    de integridad (`integrity` en el metadata), verificable en el upload.
    """
    try:
        names = ["mouse_log.csv", "mouse_delta_log.csv", "key_log.csv",
                 "video_timeline.csv", "session_metadata.json"]
        targets = ([session_dir / n for n in names] + list(session_dir.glob("*.mp4"))
                   + list(session_dir.glob("*.dem")))   # incluir el demo POV (TF2/L4D2) como solo-lectura
        for p in targets:
            try:
                if p.is_file():
                    os.chmod(str(p), stat.S_IREAD)
            except Exception:
                pass
    except Exception as e:
        _obs_dbg(f"_protect_session_files: {e}")


def _unprotect_session_files(session_dir):
    """Revierte el read-only de una sesiÃ³n (para flujos que necesiten reescribir/borrar)."""
    try:
        for p in session_dir.iterdir():
            try:
                os.chmod(str(p), stat.S_IWRITE)
            except Exception:
                pass
    except Exception:
        pass


def build_session_metadata(session_dir, selected_game, sync_results, exe_path="",
                           obs_window="", modo="manual"):
    """
    Escribe session_metadata.json en session_dir.
    Llamar despuÃ©s de run_sync_check(), antes de package_session().
    Solo escribe un archivo nuevo â€” no modifica ningÃºn CSV ni el video.
    Falla silenciosamente.
    """
    try:
        start_ms, end_ms = _meta_csv_anchors(session_dir)
        duration_ms = (end_ms - start_ms) if (start_ms and end_ms) else None

        # Detectar si el anchor fue moof2 o fallback (fallback tiende a ser mÃºltiplo de 1000)
        anchor_method    = "moof2"
        anchor_precision = 50
        if start_ms and (start_ms % 1000 < 10 or start_ms % 1000 > 990):
            anchor_method    = "fallback_system_time"
            anchor_precision = 1000

        # IDs anÃ³nimos
        session_id = _hashlib.sha256(
            f"{session_dir.name}:{start_ms or 0}".encode()
        ).hexdigest()[:16]
        source_id = "unknown"
        try:
            import winreg as _wr
            with _wr.OpenKey(_wr.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Microsoft\Cryptography") as k:
                guid, _ = _wr.QueryValueEx(k, "MachineGuid")
            source_id = _hashlib.sha256(f"pleiada:{guid}".encode()).hexdigest()[:16]
        except Exception:
            pass

        game    = selected_game or {}
        hz      = _meta_input_hz(session_dir)
        video   = _meta_video_info(session_dir)
        hw      = _meta_hardware()
        os_info = _meta_os()

        # frames_dropped: frames esperados segÃºn el tiempo REAL de la sesiÃ³n (CSV anchors)
        # menos los frames realmente capturados en el video. Mide la calidad de captura
        # (OBS que no sostuvo el fps nominal). El video_dur sale del propio frame_count,
        # por eso la referencia de tiempo real es csv_dur, no el video.
        frames_dropped = None
        _fps, _fc, _csvd = video.get("fps_nominal"), video.get("frame_count"), (sync_results or {}).get("csv_dur")
        if _fps and _fc and _csvd:
            _expected = round(_csvd / 1000 * _fps)
            _fd = _expected - _fc
            frames_dropped = _fd if _fd > 0 else 0

        # Fase 2 â€” detecciÃ³n activa
        game_dir     = os.path.dirname(exe_path) if exe_path else None
        engine_local = _meta_detect_engine(game_dir)
        engine_igdb  = game.get("engine")
        engine       = engine_local or engine_igdb
        engine_source = ("detected" if engine_local
                         else "igdb" if engine_igdb else None)
        game_version = _meta_game_version(exe_path)
        # Key mapping â€” jerarquÃ­a: config (archivo real) > game_default (curado en
        # Airtable) > inferred_from_gameplay > unknown.
        # keys_observed se calcula SIEMPRE (para comparar contra el mapping y reportar
        # possible_remaps con transparencia, sin importar la fuente).
        _, _, keys_observed = _meta_observed_keys(session_dir)
        possible_remaps = []
        # 1) Config real del juego (cualquier disco).
        key_map, binding_src = _meta_key_mapping(exe_path, engine, game.get("game", ""))
        if key_map:
            possible_remaps = _meta_possible_remaps(key_map, keys_observed)
        else:
            # 2) game_default curado (Airtable) â€” fallback cuando no se puede leer el config.
            default_km = game.get("default_key_mapping")
            if isinstance(default_km, dict) and default_km:
                key_map = default_km
                binding_src = "game_default"
                possible_remaps = _meta_possible_remaps(key_map, keys_observed)
            else:
                # 3) Inferir del gameplay de la sesiÃ³n.
                key_map, _ = _meta_infer_key_mapping(session_dir)
                binding_src = "inferred_from_gameplay" if key_map else "unknown"
        # window_mode: usar el exe realmente resuelto (Airtable process_name suele ser null)
        _proc_for_window = (os.path.basename(exe_path) if exe_path
                            else game.get("process_name", ""))
        window_mode  = _meta_window_mode(_proc_for_window)
        sys_lang     = _meta_system_language()
        activity     = _meta_activity(session_dir, start_ms, end_ms)

        # Manifiesto de integridad (SHA-256 de CSVs + MP4) â€” schema 1.1.
        integrity = _build_integrity(session_dir)

        metadata = {
            "schema_version":   "1.1",
            "session_id":       session_id,
            "source_id":        source_id,
            "recorder_version": VERSION,
            # v0.9: "libre" = se grabo sin orden de destino porque ninguna
            # orden abierta aceptaba el titulo. El dataset es identico; lo que
            # cambia es que al cerrar no se ofrece subir. Queda en el metadata
            # para que la sesion se pueda reevaluar cuando abra una orden que si
            # lo acepte, sin depender de lo que recuerde la app.
            "recording_mode":   modo,

            "timing": {
                "start_unix_ms":       start_ms,
                "end_unix_ms":         end_ms,
                "duration_ms":         duration_ms,
                "anchor_ts":           start_ms,
                "anchor_method":       anchor_method,
                "anchor_precision_ms": anchor_precision,
            },

            "game": {
                "title":        game.get("game"),
                "perspective":  game.get("perspective"),
                "genre":        game.get("genre"),
                "mode":         game.get("mode"),
                "process_name": game.get("process_name"),
                # v0.8.12: el exe REALMENTE resuelto (OBS window string -> wmic, o
                # ventana por tÃ­tulo -> PID). Antes se calculaba para el window_mode
                # y se descartaba, y el metadata devolvÃ­a el `process_name` de
                # Airtable â€” que estÃ¡ vacÃ­o en 538 de 570 juegos. Circular: guardaba
                # lo que ya sabÃ­amos en vez de lo que la mÃ¡quina habÃ­a averiguado.
                # Con esto, cada sesiÃ³n reporta el exe real y se puede completar
                # Airtable sin preguntarle nada a nadie (ingest_process_name_s3.py).
                "process_detected": _proc_for_window or None,
                # v0.8.12: el window string crudo de OBS ("TÃ­tulo:Clase:exe.exe",
                # con los escapes #XX sin tocar) y el tÃ­tulo ya decodificado.
                # Es observabilidad, no enforcement: no bloquea nada, pero a
                # partir de acÃ¡ toda sesiÃ³n queda auto-verificable â€” capa A de QA
                # puede comparar el exe real contra el tÃ­tulo declarado y levantar
                # la bandera sola. Sin esto, un mismatch de tÃ­tulo es indetectable
                # una vez que la sesiÃ³n ya se subiÃ³.
                "obs_window_raw":   obs_window or None,
                "obs_title":        (_obs_unescape((obs_window or "").split(":")[0].strip())
                                     or None),
                "game_version": game_version,
                "engine":        engine,
                "engine_source": engine_source,             # "detected" | "igdb" | None
                "themes":        game.get("themes") or [],    # IGDB via Airtable
                "languages":     game.get("languages") or [], # IGDB via Airtable
                "developer":     game.get("developer"),       # IGDB via Airtable
            },

            "input": {
                "devices":           ["keyboard", "mouse"],
                "gamepad_connected": False,       # Fase 3
                "key_mapping":       key_map,
                "binding_source":    binding_src,
                # keys_observed se incluye siempre (teclas/botones realmente usados).
                **({"keys_observed": keys_observed} if keys_observed else {}),
                # possible_remaps: observado pero ausente del config/game_default
                # (posible remap del usuario o bind extra). Solo cuando hay base autoritativa.
                **({"possible_remaps": possible_remaps} if possible_remaps else {}),
                "sampling_hz": {
                    "video_timeline": hz.get("video_timeline"),
                    "mouse_position": hz.get("mouse_log"),
                },
            },

            "video": {
                "width":          video.get("width"),
                "height":         video.get("height"),
                "fps_nominal":    video.get("fps_nominal"),
                "codec":          video.get("codec"),
                "frame_count":    video.get("frame_count"),
                "bitrate_kbps":   video.get("bitrate_kbps"),
                "frames_dropped": frames_dropped,
                "hud_present":    None,  # Fase 3
            },

            "sync": {
                "session_ok":     sync_results.get("session_ok"),
                "csvs_ok":        sync_results.get("csvs_ok"),
                "video_ok":       sync_results.get("video_ok"),
                "signed_diff_ms": sync_results.get("signed_diff"),
                "csv_dur_ms":     sync_results.get("csv_dur"),
                "video_dur_ms":   sync_results.get("video_dur"),
                "short_session":  sync_results.get("short_session", False),
                "truncated":      sync_results.get("truncated", False),
                "afk_rejected":   sync_results.get("afk", False),
                # Los dos brazos del gate AFK, para que sync_verify.py pueda
                # comparar contra lo declarado sin recalcular.
                "longest_idle_s": sync_results.get("longest_idle_s"),
                "idle_fraccion":  sync_results.get("idle_fraccion"),
                # Gate de video quieto: la imagen no cambiÃ³ (negro / congelado).
                # Se guardan tambiÃ©n las medidas crudas para poder revisar
                # server-side dÃ³nde quedÃ³ el corte sin recalcular.
                "video_still_rejected": sync_results.get("video_still", False),
                "video_still_ms":       sync_results.get("video_still_ms"),
                "video_still_ratio":    sync_results.get("video_still_ratio"),
                # Gate de input vacÃ­o: quedÃ³ registrado o no lo que hizo el
                # jugador. El conteo crudo va entero para poder auditar
                # server-side por quÃ© se rechazÃ³ (o por quÃ© pasÃ³) sin releer
                # los CSV.
                "sin_input_rejected": sync_results.get("sin_input", False),
                "sin_input_causa":    sync_results.get("sin_input_causa"),
                "eventos_input":      sync_results.get("eventos_input"),
            },

            # Actividad de input: separa juego activo de cutscenes/menÃºs/AFK.
            # Para los AI Labs: ratio de relevancia de la sesiÃ³n grabada.
            **({"activity": activity} if activity else {}),

            "environment": {
                "os_name":            os_info.get("name"),
                "os_version":         os_info.get("version"),
                "os_build":           os_info.get("build"),
                "system_language":    sys_lang,
                "cpu":                hw.get("cpu"),
                "ram_gb":             hw.get("ram_gb"),
                "gpus":               hw.get("gpus"),
                "monitor_width":      hw.get("monitor_width"),
                "monitor_height":     hw.get("monitor_height"),
                "monitor_refresh_hz": hw.get("monitor_refresh_hz"),
                "window_mode":        window_mode,
            },

            "integrity": integrity,
        }

        out = session_dir / "session_metadata.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        _obs_dbg(f"session_metadata.json escrito en {out}")

    except Exception as e:
        _obs_dbg(f"build_session_metadata error: {e}")


# â”€â”€â”€ Widgets helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _hex(color):
    return color

def _mk_separator(parent, color=BORDER2, height=1, pady=0):
    f = tk.Frame(parent, bg=color, height=height)
    f.pack(fill="x", pady=pady)
    f.pack_propagate(False)
    return f

def _mk_label(parent, text, fg=TEXT, bg=BG, size=12, weight="normal",
              anchor="w", **kw):
    lbl = tk.Label(parent, text=text, fg=fg, bg=bg, font=("Segoe UI", size, weight),
                   anchor=anchor, **kw)
    return lbl

def _mk_section_label(parent, text):
    lbl = tk.Label(parent, text=text.upper(), fg=DIM, bg=BG,
                   font=("Segoe UI", 8, "bold"), anchor="w")
    lbl.pack(fill="x", pady=(0, 6))
    return lbl

# â”€â”€â”€ App principal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class PleiadaApp:

    def __init__(self):
        self.root = tk.Tk()
        self.root.report_callback_exception = _tk_callback_excepthook   # v0.7.1: log de errores GUI
        self.root.title("Gameplay Recorder")
        self.root.overrideredirect(True)
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self.root.geometry(f"{WIN_W}x{WIN_H}")
        # Centrar en pantalla
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - WIN_W) // 2
        y  = (sh - WIN_H) // 2
        self.root.geometry(f"+{x}+{y}")

        # Ãcono de la ventana (alt-tab, barra de tareas)
        _ico = APP_DIR / "gameplay_recorder.ico"
        if _ico.exists():
            try:
                self.root.wm_iconbitmap(str(_ico))
            except Exception:
                pass

        # Forzar apariciÃ³n en barra de tareas (overrideredirect=True la oculta por defecto)
        try:
            import ctypes as _ct
            _GWL_EXSTYLE      = -20
            _WS_EX_APPWINDOW  = 0x00040000
            _WS_EX_TOOLWINDOW = 0x00000080
            self.root.update_idletasks()
            _hwnd  = _ct.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            _style = _ct.windll.user32.GetWindowLongW(_hwnd, _GWL_EXSTYLE)
            _style = (_style | _WS_EX_APPWINDOW) & ~_WS_EX_TOOLWINDOW
            _ct.windll.user32.SetWindowLongW(_hwnd, _GWL_EXSTYLE, _style)
            # Hide + show para que el cambio de estilo tome efecto
            _ct.windll.user32.ShowWindow(_hwnd, 0)   # SW_HIDE
            _ct.windll.user32.ShowWindow(_hwnd, 5)   # SW_SHOW
        except Exception:
            pass

        # DWM rounded corners (Windows 11+)
        try:
            import ctypes
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.windll.user32.GetParent(self.root.winfo_id()),
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
                ctypes.sizeof(ctypes.c_int)
            )
        except Exception:
            pass

        # Estado de la sesiÃ³n
        self.logged_in     = False
        self.user_email    = ""
        self.auth_token    = ""
        self.open_calls    = []     # inscripciones a Open Calls (my_calls del backend)
        self.selected_game = None   # dict con game/perspective/genre/mode
        self.session_dir   = None   # Path
        self.recording     = False
        self.rec_seconds   = 0
        self._timer_id     = None
        self._cd_timer_id  = None   # countdown pre-grabaciÃ³n
        self._pending_anchor = None  # anchor refinado en background durante countdown
        self._obs_prep     = ("", set())  # (rec_dir_str, existing_vids) preparado antes del countdown
        self._pkg_anim_id  = None   # after-id de la animaciÃ³n de packaging
        self._we_stopped   = False  # True cuando NOSOTROS detenemos OBS (para ignorar el evento)
        self._auto_stopped = False  # v0.7.1: True si el Ãºltimo stop fue por llegar al lÃ­mite de tiempo
        self._max_seconds  = MAX_SECONDS  # v0.7.1: se setea por sesiÃ³n desde settings
        self._auto_restart_cancelled = False  # v0.7.1: cancelar el ciclo durante la cuenta regresiva
        self._uploading    = False  # v0.8.7: subida en curso â€” bloquea nav (âš™/salir) y doble subida
        self._recording_exe      = ""   # PLE-37: exe del juego capturado (ej: "Borderlands3.exe")
        self._recording_exe_path = ""   # v0.4 Fase 2: ruta completa del exe (para metadata)
        self._recording_obs_window = ""  # v0.8.12: window string crudo de OBS (para metadata)
        self._ahk_proc     = None
        self._dropdown_win      = None
        self._obs_status        = "idle"   # idle | checking | ok | warn | err
        self._last_sync_statuses = {}      # key â†’ "ok"/"err"/"missing"/"truncated"/"offset"

        # v0.5: settings + hotkeys globales
        self._settings        = load_settings()
        self._hotkey_running  = True
        self._capturing_hotkey = None   # "start"/"stop" cuando se reasigna un atajo

        # v0.8: auto-update
        self._update_manifest = None    # manifiesto si hay una versiÃ³n nueva
        self._update_required = False   # True si VERSION < min_version â†’ bloquea grabar
        self._updating        = False   # descarga del updater en curso
        self._upd_cancel      = False

        self._build_window()
        # v0.4: sincronizar lista de juegos con Airtable en background (no bloquea el arranque)
        threading.Thread(target=sync_games_list, daemon=True).start()
        # v0.5: listener de hotkeys globales (iniciar/detener grabaciÃ³n sin foco)
        threading.Thread(target=self._hotkey_listener, daemon=True).start()
        # v0.8: chequear si hay una versiÃ³n nueva (no bloquea el arranque)
        threading.Thread(target=self._update_check_worker, daemon=True).start()
        self._check_auto_login()

    # â”€â”€ ConstrucciÃ³n de la ventana â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build_window(self):
        """Frame raÃ­z: borde 1px + contenido."""
        outer = tk.Frame(self.root, bg=BORDER2, bd=0)
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        self._build_titlebar(outer)
        _mk_separator(outer, color=BORDER2)

        # v0.8: banner de actualizaciÃ³n â€” vive FUERA de self.content para
        # sobrevivir a los cambios de pantalla (_clear_content). Oculto hasta
        # que el chequeo detecte una versiÃ³n nueva.
        self._upd_banner = tk.Frame(outer, bg=CARD2)

        self.content = tk.Frame(outer, bg=BG)
        self.content.pack(fill="both", expand=True)

    def _build_titlebar(self, parent):
        tb = tk.Frame(parent, bg=BG2, height=38)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        # v0.9: Atras. Vive en la barra porque el flujo dejo de ser una sola
        # pantalla: identificar el juego, elegir entre candidatos y elegir orden
        # son pasos, y de cualquiera se tiene que poder volver. Se oculta cuando
        # no hay a donde ir (pantalla inicial) y mientras se graba: ahi el unico
        # camino valido es Detener o Cancelar.
        self._back_btn = tk.Label(tb, text="â€¹", fg=DIM, bg=BG2, width=2,
                                  font=("Segoe UI", 14), cursor="hand2",
                                  anchor="center")
        self._back_btn.bind("<Button-1>", lambda e: self._go_back())
        self._back_btn.bind("<Enter>", lambda e: self._back_btn.config(fg=TEXT))
        self._back_btn.bind("<Leave>", lambda e: self._back_btn.config(fg=DIM))

        # Logo mark (âœ¦)
        tk.Label(tb, text="âœ¦", fg=ACCENT, bg=BG2,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(14, 0), pady=8)

        # TÃ­tulo + versiÃ³n
        tk.Label(tb, text="Gameplay Recorder", fg=TEXT, bg=BG2,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(6, 2))
        tk.Label(tb, text=VERSION, fg=DIM, bg=BG2,
                 font=("Segoe UI", 9)).pack(side="left")

        # BotÃ³n cerrar â€” la Ã— se ve siempre (Bug 5), centrada en el cuadrado
        close_btn = tk.Label(tb, text="Ã—", bg="#3a2a3e", fg=DIM, width=2,
                             font=("Segoe UI", 12), anchor="center",
                             cursor="hand2", relief="flat")
        close_btn.pack(side="right", padx=(0, 12), pady=10)
        close_btn.bind("<Button-1>", lambda e: self._on_close())
        close_btn.bind("<Enter>",  lambda e: close_btn.config(fg="#ff5f57"))
        close_btn.bind("<Leave>",  lambda e: close_btn.config(fg=DIM))

        # Nombre de usuario (solo display â€” el deslogueo estÃ¡ en Opciones âš™). Bug 3.
        self._signout_lbl = tk.Label(tb, text="", fg=DIM, bg=BG2,
                                      font=("Segoe UI", 10))
        self._signout_lbl.pack(side="right", padx=(0, 14))
        self._signout_lbl.pack_forget()  # oculto hasta login

        # Sep vertical antes de close dot
        tk.Frame(tb, bg=BORDER2, width=1, height=16).pack(side="right", pady=11)

        # v0.5: Ã­cono de Settings (âš™)
        self._settings_btn = tk.Label(tb, text="âš™", fg=DIM, bg=BG2,
                                       font=("Segoe UI", 12), cursor="hand2")
        self._settings_btn.pack(side="right", padx=(0, 10))
        self._settings_btn.bind("<Button-1>", lambda e: self._show_settings())
        self._settings_btn.bind("<Enter>", lambda e: self._settings_btn.config(fg=TEXT))
        self._settings_btn.bind("<Leave>", lambda e: self._settings_btn.config(fg=DIM))

        # Dragging
        self._drag_x = self._drag_y = 0
        for w in (tb,):
            w.bind("<ButtonPress-1>",   self._drag_start)
            w.bind("<B1-Motion>",        self._drag_move)

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()
        # Bug 4: ocultar el dropdown de bÃºsqueda al mover el floater (sino queda desfasado)
        self._hide_dropdown()

    def _drag_move(self, e):
        x = e.x_root - self._drag_x
        y = e.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # â”€â”€ Auto-update (v0.8) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _update_check_worker(self):
        """Corre en un thread daemon al arrancar. Nunca lanza excepciÃ³n."""
        # Limpiar el updater residual de una actualizaciÃ³n anterior
        try:
            (TEMP_DIR / "PleiadaRecorder_Update.exe").unlink(missing_ok=True)
        except Exception:
            pass
        m = check_for_update()
        if not m or not (m.get("_newer") or m.get("_forced")):
            return
        self.root.after(0, lambda: self._on_update_available(m))

    def _on_update_available(self, manifest):
        self._update_manifest = manifest
        self._update_required = bool(manifest.get("_forced"))
        self._update_record_btn()
        self._upd_show_offer()

    def _upd_clear(self):
        for w in self._upd_banner.winfo_children():
            w.destroy()

    def _upd_hide(self):
        self._upd_clear()
        self._upd_banner.pack_forget()

    def _upd_row(self, text, fg=TEXT):
        """(Re)arma el banner: texto arriba + fila de botones abajo (retornada)."""
        self._upd_clear()
        self._upd_banner.config(highlightthickness=1, highlightbackground=ACCENT)
        self._upd_banner.pack(fill="x", before=self.content)
        inner = tk.Frame(self._upd_banner, bg=CARD2)
        inner.pack(fill="x", padx=12, pady=8)
        self._upd_text_lbl = tk.Label(inner, text=text, fg=fg, bg=CARD2,
                                      font=("Segoe UI", 10), wraplength=WIN_W - 60,
                                      justify="left", anchor="w")
        self._upd_text_lbl.pack(fill="x")
        btns = tk.Frame(inner, bg=CARD2)
        btns.pack(fill="x", pady=(6, 0))
        return btns

    def _upd_btn(self, parent, text, cmd, primary=False):
        b = tk.Label(parent, text=text, cursor="hand2",
                     bg=(ACCENT if primary else CARD2),
                     fg=("#ffffff" if primary else DIM),
                     font=("Segoe UI", 9, "bold"), padx=10, pady=3)
        b.pack(side="right", padx=(8, 0))
        b.bind("<Button-1>", lambda e: cmd())
        if not primary:
            b.bind("<Enter>", lambda e: b.config(fg=TEXT))
            b.bind("<Leave>", lambda e: b.config(fg=DIM))
        return b

    def _upd_show_offer(self):
        m = self._update_manifest or {}
        if self._update_required:
            btns = self._upd_row("Esta versiÃ³n ya no es compatible. "
                                 "ActualizÃ¡ para seguir grabando.", fg="#f5d77a")
        else:
            btns = self._upd_row(f"Nueva versiÃ³n disponible ({m.get('version', '')})")
            self._upd_btn(btns, "MÃ¡s tarde", self._upd_hide)
        self._upd_btn(btns, "Actualizar ahora", self._upd_start_download, primary=True)

    def _upd_show_error(self):
        self._updating = False
        btns = self._upd_row("No se pudo descargar la actualizaciÃ³n. "
                             "ProbÃ¡ de nuevo mÃ¡s tarde.", fg="#f5d77a")
        if not self._update_required:
            self._upd_btn(btns, "MÃ¡s tarde", self._upd_hide)
        self._upd_btn(btns, "Reintentar", self._upd_start_download, primary=True)

    def _upd_start_download(self):
        if self._updating:
            return
        if self.recording:
            import tkinter.messagebox as _mb
            _mb.showwarning("Gameplay Recorder",
                            "TerminÃ¡ la grabaciÃ³n antes de actualizar.")
            return
        url = (self._update_manifest or {}).get("update_url")
        if not url:
            self._upd_show_error()
            return
        self._updating   = True
        self._upd_cancel = False
        btns = self._upd_row("Descargando actualizaciÃ³n... 0%")
        self._upd_btn(btns, "Cancelar", self._upd_cancel_download)
        threading.Thread(
            target=self._upd_download_worker,
            args=(url, (self._update_manifest or {}).get("update_sha256")),
            daemon=True).start()

    def _upd_cancel_download(self):
        self._upd_cancel = True

    def _upd_set_progress(self, pct):
        if self._updating and self._upd_text_lbl.winfo_exists():
            self._upd_text_lbl.config(text=f"Descargando actualizaciÃ³n... {pct}%")

    def _upd_download_worker(self, url, sha256_expected):
        """Descarga el updater a %TEMP% verificando SHA-256. Thread daemon."""
        import urllib.request as _ur
        dest = TEMP_DIR / "PleiadaRecorder_Update.exe"
        ok = False
        try:
            req = _ur.Request(url, headers={"User-Agent": f"PleiadaRecorder/{VERSION}"})
            h = _hashlib.sha256()
            with _ur.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
                total = int(r.headers.get("Content-Length") or 0)
                done, last_pct = 0, -1
                while not self._upd_cancel:
                    chunk = r.read(65536)
                    if not chunk:
                        ok = True
                        break
                    f.write(chunk)
                    h.update(chunk)
                    done += len(chunk)
                    if total:
                        pct = min(int(done * 100 / total), 100)
                        if pct != last_pct:
                            last_pct = pct
                            self.root.after(0, lambda p=pct: self._upd_set_progress(p))
            # Integridad: el hash del manifiesto lo publicÃ³ el CI junto al .exe
            if ok and sha256_expected and \
                    h.hexdigest().lower() != str(sha256_expected).strip().lower():
                _obs_dbg("update: SHA-256 no coincide â€” descarga descartada")
                ok = False
        except Exception as e:
            _obs_dbg(f"update: error de descarga: {e}")
            ok = False

        self._updating = False
        if self._upd_cancel or not ok:
            try:
                dest.unlink(missing_ok=True)
            except Exception:
                pass
            self.root.after(0, self._upd_show_offer if self._upd_cancel
                            else self._upd_show_error)
            return
        self.root.after(0, lambda: self._upd_launch(dest))

    def _upd_launch(self, exe_path):
        """Lanza el updater (dispara UAC) y cierra la app."""
        self._upd_row("El Recorder se va a cerrar para actualizarse. "
                      "Se abre solo al terminar.")
        try:
            # El .exe pide admin en su manifest â†’ ShellExecute dispara UAC solo.
            # Si el usuario rechaza el UAC, startfile lanza OSError.
            os.startfile(str(exe_path),
                         arguments="/SILENT /NORESTART /SUPPRESSMSGBOXES")
        except OSError:
            self._upd_show_error()
            return
        # El updater cierra la app igual (taskkill) â€” esto es el camino prolijo.
        self.root.after(800, self.root.destroy)

    # â”€â”€ Login â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _check_auto_login(self):
        # Login optimista: si hay token guardado, entramos. Si el token venciÃ³,
        # el upload devuelve "auth" y ahÃ­ forzamos re-login con OTP.
        auth = load_auth()
        if auth and auth.get("token") and auth.get("email"):
            self.logged_in  = True
            self.user_email = auth["email"]
            self.auth_token = auth["token"]
            self._set_signout_label(auth["email"])
            self._refresh_open_calls()
            self._show_idle()
        else:
            self._show_login()

    def _refresh_open_calls(self):
        """Trae las inscripciones a Open Calls en background (no bloquea la UI).
        Es solo para UX (matching y mensajes): el gate real vive en el backend."""
        if not self.auth_token:
            return
        def _worker(token=self.auth_token):
            try:
                calls = pleiada_api.my_calls(token)
            except Exception:
                return   # sin red / token viejo: se reintenta en el prÃ³ximo evento
            def _apply():
                self.open_calls = calls
            self.root.after(0, _apply)
        threading.Thread(target=_worker, daemon=True).start()

    def _calls_for_game(self, game_title):
        """Inscripciones activas cuyo Open Call acepta este juego (matching local,
        espejo del criterio del backend: lista de juegos o genre âˆˆ categorÃ­as)."""
        t = (game_title or "").strip().lower()
        if not t:
            return []
        genre = ""
        for g in load_games():
            if (g.get("game") or "").strip().lower() == t:
                genre = (g.get("genre") or "").strip().lower()
                break
        out = []
        for c in self.open_calls or []:
            if c.get("status") != "activa" or not c.get("call_activo", True):
                continue
            # `call_activo` significa VISIBLE, y el backend trae activo + completado:
            # una orden completada hacÃ­a dÃ­as se seguÃ­a ofreciendo como destino de
            # subida (bug 15/08, caso GA-2026-007). El que manda es `call_status`,
            # el status crudo de la orden en Airtable.
            # Ojo: NO usar `call_estado`, que tambiÃ©n dice "completado" cuando la
            # orden llegÃ³ al 100% de horas pero sigue activa â€” ese caso tiene que
            # seguir aceptando subidas hasta el overflow del backend, que es lo que
            # evita perder la sesiÃ³n que estabas grabando cuando la orden se llenÃ³.
            if c.get("call_status", "activo") == "completado":
                continue
            rem = c.get("remaining_seconds")
            if rem is not None and rem <= 0:
                continue   # cupo personal agotado en ese call
            if c.get("targeting_mode") == "juegos_especificos":
                if t in {(j or "").strip().lower() for j in c.get("juegos", [])}:
                    out.append(c)
            else:
                cats = {(x or "").strip().lower() for x in c.get("categorias", [])}
                if genre and genre in cats:
                    out.append(c)
        return out

    def _set_signout_label(self, email):
        _uname = email.split('@')[0]
        _uname = (_uname[:20] + "â€¦") if len(_uname) > 20 else _uname  # PLE-36
        self._signout_lbl.config(text=f"  {_uname}")
        self._signout_lbl.pack(side="right", padx=(0, 14))

    def _login_header(self, frame):
        tk.Frame(frame, bg=BG, height=30).pack()
        tk.Label(frame, text="âœ¦", fg=ACCENT, bg=BG,
                 font=("Segoe UI", 28)).pack()
        tk.Label(frame, text="Gameplay Recorder", fg=TEXT, bg=BG,
                 font=("Segoe UI", 17, "bold")).pack(pady=(10, 0))
        tk.Label(frame, text="Gameplay Alliance â€” sesiÃ³n de grabaciÃ³n", fg=DIM, bg=BG,
                 font=("Segoe UI", 11)).pack(pady=(4, 32))

    # â”€â”€ Login paso 1: pedir el cÃ³digo â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _show_login(self):
        self._clear_content()
        self._signout_lbl.pack_forget()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=36, pady=0)
        self._login_header(frame)

        tk.Label(frame, text="IniciÃ¡ sesiÃ³n", fg=TEXT, bg=BG,
                 font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x")
        tk.Label(frame, text="IngresÃ¡ el email con el que te registraste al programa.",
                 fg=DIM, bg=BG, font=("Segoe UI", 10), anchor="w",
                 justify="left", wraplength=WIN_W - 80).pack(fill="x", pady=(4, 22))

        tk.Label(frame, text="EMAIL", fg=DIM, bg=BG,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", pady=(0, 5))
        email_var = tk.StringVar(value=self.user_email or "")
        email_entry = tk.Entry(frame, textvariable=email_var, bg=CARD, fg=TEXT,
                               insertbackground=ACCENT, relief="flat",
                               font=("Segoe UI", 12), bd=0)
        email_entry.pack(fill="x", ipady=10)
        _mk_separator(frame, color=BORDER, height=1, pady=0)

        tk.Frame(frame, bg=BG, height=18).pack()

        err_lbl = tk.Label(frame, text="", fg=RED, bg=BG, font=("Segoe UI", 10),
                           wraplength=WIN_W - 80, justify="left")
        err_lbl.pack(pady=(0, 6))

        btn = tk.Button(frame, text="Enviar cÃ³digo", fg="#fff", bg=ACCENT,
                        relief="flat", bd=0, cursor="hand2",
                        font=("Segoe UI", 12, "bold"),
                        activebackground="#9080e0", activeforeground="#fff")
        btn.pack(fill="x", ipady=12)

        def on_send():
            email = email_var.get().strip().lower()
            if "@" not in email or "." not in email:
                err_lbl.config(text="IngresÃ¡ un email vÃ¡lido.")
                return
            err_lbl.config(text="")
            btn.config(text="Enviandoâ€¦", state="disabled")

            def _worker():
                try:
                    pleiada_api.request_otp(email)
                    self.root.after(0, lambda: self._show_otp_step(email))
                except pleiada_api.ApiError as e:
                    msg = str(e)
                    self.root.after(0, lambda: (
                        btn.config(text="Enviar cÃ³digo", state="normal"),
                        err_lbl.config(text=msg)))
            threading.Thread(target=_worker, daemon=True).start()

        btn.config(command=on_send)
        email_entry.bind("<Return>", lambda e: on_send())
        email_entry.focus()

    # â”€â”€ Login paso 2: ingresar el cÃ³digo â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _show_otp_step(self, email):
        self._clear_content()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=36, pady=0)
        self._login_header(frame)

        tk.Label(frame, text="RevisÃ¡ tu email", fg=TEXT, bg=BG,
                 font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x")
        tk.Label(frame, text=f"Te enviamos un cÃ³digo de 6 dÃ­gitos a\n{email}",
                 fg=DIM, bg=BG, font=("Segoe UI", 10), anchor="w",
                 justify="left", wraplength=WIN_W - 80).pack(fill="x", pady=(4, 22))

        tk.Label(frame, text="CÃ“DIGO", fg=DIM, bg=BG,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", pady=(0, 5))
        code_var = tk.StringVar()
        code_entry = tk.Entry(frame, textvariable=code_var, bg=CARD, fg=TEXT,
                              insertbackground=ACCENT, relief="flat",
                              font=("Cascadia Code", 18), bd=0, justify="center")
        code_entry.pack(fill="x", ipady=10)
        _mk_separator(frame, color=BORDER, height=1, pady=0)

        tk.Frame(frame, bg=BG, height=18).pack()

        err_lbl = tk.Label(frame, text="", fg=RED, bg=BG, font=("Segoe UI", 10),
                           wraplength=WIN_W - 80, justify="left")
        err_lbl.pack(pady=(0, 6))

        btn = tk.Button(frame, text="Ingresar", fg="#fff", bg=ACCENT,
                        relief="flat", bd=0, cursor="hand2",
                        font=("Segoe UI", 12, "bold"),
                        activebackground="#9080e0", activeforeground="#fff")
        btn.pack(fill="x", ipady=12)

        def on_verify():
            code = code_var.get().strip()
            if len(code) < 6:
                err_lbl.config(text="El cÃ³digo tiene 6 dÃ­gitos.")
                return
            err_lbl.config(text="")
            btn.config(text="Verificandoâ€¦", state="disabled")

            def _worker():
                try:
                    token = pleiada_api.verify_otp(email, code)
                    def _ok():
                        self.logged_in  = True
                        self.user_email = email
                        self.auth_token = token
                        save_auth(email, token)
                        self._set_signout_label(email)
                        self._refresh_open_calls()
                        self._show_idle()
                    self.root.after(0, _ok)
                except pleiada_api.ApiError as e:
                    msg = str(e)
                    self.root.after(0, lambda: (
                        btn.config(text="Ingresar", state="normal"),
                        err_lbl.config(text=msg)))
            threading.Thread(target=_worker, daemon=True).start()

        btn.config(command=on_verify)
        code_entry.bind("<Return>", lambda e: on_verify())
        code_entry.focus()

        # Acciones secundarias: reenviar / cambiar email
        links = tk.Frame(frame, bg=BG)
        links.pack(fill="x", pady=(16, 0))

        resend_lbl = tk.Label(links, text="Reenviar cÃ³digo", fg=ACCENT, bg=BG,
                              font=("Segoe UI", 10), cursor="hand2")
        resend_lbl.pack(side="left")

        def on_resend(e=None):
            resend_lbl.config(text="Reenviandoâ€¦", fg=DIM)
            def _worker():
                try:
                    pleiada_api.request_otp(email)
                    self.root.after(0, lambda: resend_lbl.config(
                        text="CÃ³digo reenviado", fg=GREEN))
                except pleiada_api.ApiError:
                    self.root.after(0, lambda: resend_lbl.config(
                        text="Reenviar cÃ³digo", fg=ACCENT))
            threading.Thread(target=_worker, daemon=True).start()
        resend_lbl.bind("<Button-1>", on_resend)

        change_lbl = tk.Label(links, text="Cambiar email", fg=DIM, bg=BG,
                             font=("Segoe UI", 10), cursor="hand2")
        change_lbl.pack(side="right")
        change_lbl.bind("<Button-1>", lambda e: self._show_login())

    def _sign_out(self):
        if self.recording:
            return  # no sign out during recording
        if self._uploading:
            return  # v0.8.7: cerrar sesiÃ³n a mitad de subida romperÃ­a el finalize
        self.logged_in  = False
        self.auth_token = ""
        self.selected_game = None
        save_auth("", "")
        self._signout_lbl.pack_forget()
        self._show_login()

    # â”€â”€ Settings (v0.5) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _show_settings(self):
        if self.recording:
            return  # no abrir settings durante la grabaciÃ³n
        if self._uploading:
            return  # v0.8.7: tampoco durante una subida (destruÃ­a la vista de progreso
                    # y dejaba el thread zombi â€” la Ãºnica salida vÃ¡lida es Cancelar)
        if not self.logged_in:
            return  # settings solo con sesiÃ³n iniciada
        self._capturing_hotkey = None
        self._clear_content()
        self._set_back(self._show_idle)
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)

        # Back arriba â€” siempre visible (v0.7.1)
        _back = tk.Label(frame, text="â†  Volver", fg=DIM, bg=BG,
                         font=("Segoe UI", 10), cursor="hand2", anchor="w")
        _back.pack(fill="x", pady=(0, 10))
        _back.bind("<Button-1>", lambda e: self._show_idle())
        _back.bind("<Enter>", lambda e: _back.config(fg=TEXT))
        _back.bind("<Leave>", lambda e: _back.config(fg=DIM))

        _mk_section_label(frame, "AJUSTES")

        # â€” VersiÃ³n â€”
        vrow = tk.Frame(frame, bg=BG)
        vrow.pack(fill="x", pady=(2, 0))
        tk.Label(vrow, text="VersiÃ³n:", fg=DIM, bg=BG,
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Label(vrow, text=f"  {VERSION}", fg=TEXT, bg=BG,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(vrow, text="âœ“ Actualizado", fg=GREEN, bg=BG,
                 font=("Segoe UI", 9)).pack(side="right")

        _mk_separator(frame, color=BORDER2, pady=(14, 12))

        # â€” Atajos de teclado â€”
        _mk_section_label(frame, "ATAJOS DE TECLADO")
        self._hotkey_btns = {}
        for key, label in (("hotkey_start", "Iniciar grabaciÃ³n"),
                           ("hotkey_stop",  "Detener grabaciÃ³n")):
            hrow = tk.Frame(frame, bg=BG)
            hrow.pack(fill="x", pady=3)
            tk.Label(hrow, text=label + ":", fg=TEXT, bg=BG,
                     font=("Segoe UI", 10), anchor="w").pack(side="left")
            btn = tk.Label(hrow, text=self._settings[key]["label"],
                           fg=ACCENT, bg=CARD, font=("Cascadia Code", 10),
                           cursor="hand2", padx=12, pady=4,
                           highlightthickness=1, highlightbackground=BORDER)
            btn.pack(side="right")
            btn.bind("<Button-1>", lambda e, k=key: self._begin_capture_hotkey(k))
            self._hotkey_btns[key] = btn
        tk.Label(frame, text="HacÃ© clic en un atajo y presionÃ¡ la nueva tecla.\n"
                              "Los atajos funcionan aunque la ventana no estÃ© en foco.",
                 fg=DIM, bg=BG, font=("Segoe UI", 9), justify="left",
                 wraplength=WIN_W - 60, anchor="w").pack(fill="x", pady=(8, 0))

        _mk_separator(frame, color=BORDER2, pady=(14, 12))

        # â€” GrabaciÃ³n (v0.7.1) â€”
        _mk_section_label(frame, "GRABACIÃ“N")

        tk.Label(frame, text="DuraciÃ³n mÃ¡xima de sesiÃ³n", fg=TEXT, bg=BG,
                 font=("Segoe UI", 10), anchor="w").pack(fill="x", pady=(2, 2))
        self._maxdur_lbl = tk.Label(frame, text="", fg=ACCENT, bg=BG,
                                    font=("Cascadia Code", 12, "bold"), anchor="w")
        self._maxdur_lbl.pack(fill="x")

        presets_row = tk.Frame(frame, bg=BG)
        presets_row.pack(fill="x", pady=(6, 0))
        self._maxdur_preset_btns = {}
        for _mins in (30, 60):
            _b = tk.Label(presets_row, text=f"{_mins}m", bg=CARD, fg=TEXT,
                          font=("Segoe UI", 10), cursor="hand2", padx=11, pady=5,
                          highlightthickness=1, highlightbackground=BORDER)
            _b.pack(side="left", padx=(0, 6))
            _b.bind("<Button-1>", lambda e, m=_mins: self._set_max_minutes(m))
            self._maxdur_preset_btns[_mins] = _b

        tk.Label(frame, text="La grabaciÃ³n se detiene automÃ¡ticamente al alcanzar este tiempo. "
                             "MÃ¡ximo 1 hora.",
                 fg=DIM, bg=BG, font=("Segoe UI", 9), justify="left",
                 wraplength=WIN_W - 60, anchor="w").pack(fill="x", pady=(6, 0))
        self._refresh_maxdur_ui()

        ar_row = tk.Frame(frame, bg=BG)
        ar_row.pack(fill="x", pady=(14, 0))
        tk.Label(ar_row, text="Reiniciar grabaciÃ³n automÃ¡ticamente", fg=TEXT, bg=BG,
                 font=("Segoe UI", 10), anchor="w").pack(side="left")
        self._autorestart_btn = tk.Label(ar_row, text="", bg=CARD, fg=DIM,
                                          font=("Segoe UI", 9, "bold"), cursor="hand2",
                                          padx=12, pady=4, highlightthickness=1,
                                          highlightbackground=BORDER)
        self._autorestart_btn.pack(side="right")
        self._autorestart_btn.bind("<Button-1>", lambda e: self._toggle_auto_restart())
        self._refresh_autorestart_ui()

        tk.Label(frame, text="Cuando una grabaciÃ³n se detiene por alcanzar la duraciÃ³n mÃ¡xima, "
                             "espera 10 segundos e inicia una nueva sesiÃ³n automÃ¡ticamente. "
                             "Cada sesiÃ³n se guarda en su propia carpeta â€” no se sobrescriben.",
                 fg=DIM, bg=BG, font=("Segoe UI", 9), justify="left",
                 wraplength=WIN_W - 60, anchor="w").pack(fill="x", pady=(6, 0))

        _mk_separator(frame, color=BORDER2, pady=(14, 12))

        # â€” Cuenta (sin tÃ­tulo, v0.7.1) â€”
        tk.Label(frame, text=self.user_email or "â€”", fg=DIM, bg=BG,
                 font=("Segoe UI", 10), anchor="w").pack(fill="x")
        tk.Button(frame, text="Cerrar sesiÃ³n", fg=TEXT, bg=CARD,
                  relief="flat", bd=0, cursor="hand2",
                  font=("Segoe UI", 10), activebackground=CARD2,
                  activeforeground=TEXT, command=self._sign_out,
                  highlightthickness=1, highlightbackground=BORDER).pack(
            fill="x", ipady=8, pady=(8, 0))

        # spacer al fondo (el back vive arriba ahora)
        tk.Frame(frame, bg=BG).pack(fill="both", expand=True)

    # â”€â”€ Settings: duraciÃ³n mÃ¡xima y auto-reinicio (v0.7.1) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _set_max_minutes(self, mins):
        try:
            mins = max(1, min(60, int(mins)))
        except Exception:
            return
        self._settings["max_session_minutes"] = mins
        save_settings(self._settings)
        self._refresh_maxdur_ui()

    def _refresh_maxdur_ui(self):
        m = int(self._settings.get("max_session_minutes", 60))
        try:
            self._maxdur_lbl.config(text=f"{m} min")
            for mins, b in self._maxdur_preset_btns.items():
                on = (mins == m)
                b.config(bg=ACCENT if on else CARD, fg="#ffffff" if on else TEXT)
        except Exception:
            pass

    def _toggle_auto_restart(self):
        self._settings["auto_restart"] = not self._settings.get("auto_restart", False)
        save_settings(self._settings)
        self._refresh_autorestart_ui()

    def _refresh_autorestart_ui(self):
        on = bool(self._settings.get("auto_restart", False))
        try:
            self._autorestart_btn.config(text="ACTIVADO" if on else "DESACTIVADO",
                                          bg=GREEN if on else CARD,
                                          fg="#06140d" if on else DIM)
        except Exception:
            pass

    def _begin_capture_hotkey(self, key):
        """Entra en modo captura: el prÃ³ximo KeyPress define el atajo."""
        self._capturing_hotkey = key
        btn = self._hotkey_btns[key]
        btn.config(text="PresionÃ¡ una teclaâ€¦", fg=YELLOW)
        self.root.bind("<KeyPress>", self._on_capture_keypress)
        self.root.focus_force()

    def _on_capture_keypress(self, event):
        key = self._capturing_hotkey
        if not key:
            return
        vk, label = _keysym_to_vk(event.keysym)
        self.root.unbind("<KeyPress>")
        self._capturing_hotkey = None
        if vk is None:
            # tecla no soportada â†’ restaurar
            self._hotkey_btns[key].config(text=self._settings[key]["label"], fg=ACCENT)
            return
        # Evitar que start y stop sean la misma tecla
        other = "hotkey_stop" if key == "hotkey_start" else "hotkey_start"
        if self._settings[other]["vk"] == vk:
            self._hotkey_btns[key].config(text="Ya en uso", fg=RED)
            self.root.after(1200, lambda: self._hotkey_btns[key].config(
                text=self._settings[key]["label"], fg=ACCENT))
            return
        self._settings[key] = {"vk": vk, "label": label}
        save_settings(self._settings)
        self._hotkey_btns[key].config(text=label, fg=ACCENT)

    def _hotkey_listener(self):
        """Thread daemon: detecta los hotkeys globales vÃ­a GetAsyncKeyState.
        Funciona aunque la ventana no tenga foco (incl. fullscreen exclusivo)."""
        try:
            user32 = ctypes.windll.user32
        except Exception:
            return
        prev = {"hotkey_start": False, "hotkey_stop": False}
        while self._hotkey_running:
            time.sleep(0.04)   # ~25 Hz
            if self._capturing_hotkey:   # no disparar mientras se reasigna
                continue
            for key, action in (("hotkey_start", self._hotkey_start),
                                ("hotkey_stop",  self._hotkey_stop)):
                vk = self._settings.get(key, {}).get("vk")
                if not vk:
                    continue
                down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
                if down and not prev[key]:
                    self.root.after(0, action)
                prev[key] = down

    def _hotkey_start(self):
        # Solo si hay sesiÃ³n, juego seleccionado, OBS ok y no grabando
        if self.recording or not self.logged_in:
            return
        if self.selected_game:
            self._start_recording()

    def _hotkey_stop(self):
        if self.recording:
            self._stop_recording()

    # â”€â”€ Pantalla Idle (selector de juego) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _show_idle(self):
        self._clear_content()
        self.selected_game = None
        self._obs_status   = "idle"

        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)

        # â€” SecciÃ³n: Juego (detecciÃ³n automÃ¡tica, v0.9) â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”
        # Ya no hay selector: el juego sale de lo que OBS estÃ¡ capturando y lo
        # resuelve el backend. Este frame se rellena solo, segÃºn el estado.
        _mk_section_label(frame, "JUEGO DETECTADO")
        self._det_box = tk.Frame(frame, bg=CARD, highlightthickness=1,
                                 highlightbackground=BORDER)
        self._det_box.pack(fill="x")
        self._det_calls_box = tk.Frame(frame, bg=BG)
        self._det_calls_box.pack(fill="x", pady=(10, 0))
        self._set_back(None)          # pantalla inicial: no hay paso anterior
        self._det_state = "esperando"
        self._det_last  = None      # (exe, tÃ­tulo) ya resuelto: no repreguntar
        self.selected_call = None   # None = grabaciÃ³n libre
        self._render_det_esperando("Buscando una ventana de juego en OBSâ€¦")
        self._detect_start()

        # â€” Separador â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”
        tk.Frame(frame, bg=BORDER2, height=1).pack(fill="x", pady=(0, 0))

        # â€” SecciÃ³n: SesiÃ³n â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”
        session_row = tk.Frame(frame, bg=BG)
        session_row.pack(fill="x", pady=(14, 0))
        tk.Label(session_row, text="SESIÃ“N MÃX", fg=DIM, bg=BG,
                  font=("Segoe UI", 8, "bold"), anchor="w").pack(side="left")
        # v0.7.1: refleja la duraciÃ³n configurada en Ajustes (antes 01:05:00 fijo)
        _mx = int(self._settings.get("max_session_minutes", 60)) * 60
        tk.Label(session_row, text=f"{_mx // 3600:02d}:{(_mx % 3600) // 60:02d}:{_mx % 60:02d}",
                  fg=TEXT, bg=BG,
                  font=("Cascadia Code", 11), anchor="e").pack(side="right")

        # Aviso del gate AFK â€” el jugador tiene que saberlo ANTES de grabar.
        # A propÃ³sito NO se menciona el umbral exacto (pedido de MartÃ­n 20/7).
        tk.Label(frame, text="GrabÃ¡ jugando activamente: las sesiones con perÃ­odos largos "
                             "sin actividad de teclado o mouse no son vÃ¡lidas para subir.",
                  fg=DIM, bg=BG, font=("Segoe UI", 9), justify="left",
                  wraplength=WIN_W - 60, anchor="w").pack(fill="x", pady=(6, 0))

        # spacer
        tk.Frame(frame, bg=BG).pack(fill="both", expand=True)

        # â€” BotÃ³n Iniciar â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”
        self._rec_btn_idle = tk.Button(
            frame, text="  Iniciar grabaciÃ³n", fg=DIMMER, bg=CARD,
            relief="flat", bd=0, cursor="arrow",
            font=("Segoe UI", 12, "bold"),
            activebackground=CARD, activeforeground=DIMMER,
            state="disabled", command=self._start_recording
        )
        self._rec_btn_idle.pack(fill="x", ipady=14, pady=(0, 2))
        self._update_record_btn()

        # â€” Acceso a "Mis grabaciones" (subir sesiones grabadas antes) â€”â€”â€”â€”â€”â€”
        sessions_btn = tk.Label(frame, text="ðŸ“¤  Mis grabaciones",
                                fg=ACCENT, bg=BG, font=("Segoe UI", 10),
                                cursor="hand2", anchor="center")
        sessions_btn.pack(fill="x", pady=(8, 0))
        sessions_btn.bind("<Enter>", lambda e: sessions_btn.config(fg="#9d8fe8"))
        sessions_btn.bind("<Leave>", lambda e: sessions_btn.config(fg=ACCENT))
        sessions_btn.bind("<Button-1>", lambda e: self._show_sessions_list())

        # â€” Footer â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”
        _mk_separator(frame, color=BORDER2, pady=(12, 0))
        footer = tk.Frame(frame, bg=BG)
        footer.pack(fill="x", pady=(10, 0))
        tk.Label(footer, text="SESIÃ“N", fg=DIM, bg=BG,
                  font=("Segoe UI", 8, "bold"), anchor="w").pack(side="left")
        tk.Label(footer, text="No iniciada", fg=DIMMER, bg=BG,
                  font=("Cascadia Code", 10), anchor="e").pack(side="right")

        # â€” Link tutorial â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”
        tutorial_lbl = tk.Label(frame, text="Ver tutorial de configuraciÃ³n â†—",
                                 fg=DIMMER, bg=BG, font=("Segoe UI", 9),
                                 cursor="hand2", anchor="w")
        tutorial_lbl.pack(fill="x", pady=(6, 0))
        tutorial_lbl.bind("<Enter>", lambda e: tutorial_lbl.config(fg=ACCENT))
        tutorial_lbl.bind("<Leave>", lambda e: tutorial_lbl.config(fg=DIMMER))
        tutorial_lbl.bind("<Button-1>", lambda e: self._open_tutorial())

        self._idle_frame = frame

    def _on_search_focus(self, e=None):
        self._sel_outer.config(highlightbackground=ACCENT)
        self._on_search_changed()

    def _on_search_changed(self, *args):
        q = self._search_var.get()
        # Si el usuario modificÃ³ el texto y habÃ­a un juego seleccionado â†’ deseleccionar
        if self.selected_game and q != self.selected_game["game"]:
            self.selected_game = None
            self._chevron_lbl.config(text="âŒ„", fg=DIM, cursor="")
            self._chevron_lbl.unbind("<Button-1>")
            self._game_tag_lbl.config(text="")
            self._hint_lbl.config(text="EscribÃ­ el nombre del juego para buscar.", fg=DIM)
            self._obs_dot.config(fg=DIMMER)
            self._obs_lbl.config(text="SeleccionÃ¡ un juego para verificar OBS.", fg=DIM)
            self._warn_frame.pack_forget()
            self._obs_status = "idle"
            self._update_record_btn()
        # Sin texto â†’ lista completa alfabÃ©tica (con scroll). Con texto â†’ filtra.
        results = fuzzy_search(q.strip())
        if results:
            self._show_dropdown(results)
        elif q.strip():
            self._show_no_results()
        else:
            self._hide_dropdown()

    def _show_dropdown(self, results):
        self._hide_dropdown()
        self._dropdown_data = results

        # Crear Toplevel relativo a la ventana principal
        dd = tk.Toplevel(self.root)
        dd.overrideredirect(True)
        dd.configure(bg=CARD2)
        self._dropdown_win = dd

        # Calcular posiciÃ³n
        self.root.update_idletasks()
        rx  = self.root.winfo_rootx()
        sx  = self._sel_outer.winfo_x()
        sw  = self._sel_outer.winfo_width()
        y_off = self._sel_outer.winfo_rooty() + self._sel_outer.winfo_height() + 4

        outer = tk.Frame(dd, bg=CARD2, bd=1, relief="solid",
                          highlightthickness=1, highlightbackground=BORDER)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text="RESULTADOS", fg=DIM, bg=CARD2,
                  font=("Segoe UI", 8, "bold"), anchor="w",
                  pady=8, padx=10).pack(fill="x")

        # â”€â”€ Bug 7: tk.Listbox nativo (liviano, sin lag con cientos de items,
        #    scroll incorporado) en lugar de cientos de Frames+Labels â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        VISIBLE = 10
        body = tk.Frame(outer, bg=CARD2)
        body.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        lb = tk.Listbox(
            body, activestyle="none", bd=0, highlightthickness=0,
            bg=CARD2, fg=TEXT, font=("Segoe UI", 11),
            selectbackground="#1e1c40", selectforeground=TEXT,
            height=min(len(results), VISIBLE), cursor="hand2",
        )
        sb = tk.Scrollbar(body, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        if len(results) > VISIBLE:
            sb.pack(side="right", fill="y")
        lb.pack(side="left", fill="both", expand=True)

        for g in results:
            lb.insert("end", "  " + g["game"])

        def _pick(e=None):
            sel = lb.curselection()
            if sel:
                self._select_game(self._dropdown_data[sel[0]])
        lb.bind("<<ListboxSelect>>", _pick)
        lb.bind("<Return>", _pick)
        self._dd_listbox = lb

        # Altura del Toplevel segÃºn el contenido real
        dd.update_idletasks()
        total_h = outer.winfo_reqheight()
        dd.geometry(f"{sw}x{total_h}+{rx + sx}+{y_off}")
        self._dropdown_visible = True

    def _show_no_results(self):
        self._hide_dropdown()
        self._dropdown_data = []
        dd = tk.Toplevel(self.root)
        dd.overrideredirect(True)
        dd.configure(bg=CARD2)
        self._dropdown_win = dd

        rx = self.root.winfo_rootx()
        sx = self._sel_outer.winfo_x()
        sw = self._sel_outer.winfo_width()
        y_off = self._sel_outer.winfo_rooty() + self._sel_outer.winfo_height() + 4
        dd.geometry(f"{sw}x52+{rx + sx}+{y_off}")

        outer = tk.Frame(dd, bg=CARD2, bd=1, relief="solid",
                          highlightthickness=1, highlightbackground=BORDER)
        outer.pack(fill="both", expand=True)
        tk.Label(outer, text="Sin resultados â€” revisÃ¡ la ortografÃ­a.", fg=DIM, bg=CARD2,
                  font=("Segoe UI", 10)).pack(expand=True)
        self._dropdown_visible = True

    def _hide_dropdown(self):
        if self._dropdown_win:
            try:
                self._dropdown_win.destroy()
            except Exception:
                pass
            self._dropdown_win = None
        self._dropdown_visible = False

    def _dropdown_focus(self, direction):
        pass  # keyboard nav stub

    def _select_dropdown_item(self):
        if self._dropdown_data:
            self._select_game(self._dropdown_data[0])

    def _select_game(self, game_dict):
        self._hide_dropdown()
        self.selected_game = game_dict
        self._search_var.set(game_dict["game"])
        # Entry sigue editable â€” el usuario puede volver a buscar
        self._sel_outer.config(highlightbackground=BORDER)
        self._game_tag_lbl.config(text="")
        # Mostrar Ã— para limpiar la selecciÃ³n
        self._chevron_lbl.config(text="Ã—", fg=TEXT, cursor="hand2")
        self._chevron_lbl.bind("<Button-1>", lambda e: self._clear_game_selection())
        # Update hint
        self._hint_lbl.config(text="âœ“  Juego seleccionado.", fg=GREEN)
        # Check OBS game match
        self._check_obs_game()
        self._update_record_btn()

    def _clear_game_selection(self):
        self.selected_game = None
        self._search_var.set("")
        self._search_entry.focus()
        self._chevron_lbl.config(text="âŒ„", fg=DIM, cursor="")
        self._chevron_lbl.unbind("<Button-1>")
        self._game_tag_lbl.config(text="")
        self._hint_lbl.config(text="EscribÃ­ el nombre del juego para buscar.", fg=DIM)
        self._obs_dot.config(fg=DIMMER)
        self._obs_lbl.config(text="SeleccionÃ¡ un juego para verificar OBS.", fg=DIM)
        self._warn_frame.pack_forget()
        self._obs_status = "idle"
        self._update_record_btn()

    # â”€â”€ DetecciÃ³n automÃ¡tica del juego (v0.9) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _detect_start(self):
        self._det_active = True
        self._detect_poll()

    def _detect_stop(self):
        self._det_active = False
        tid = getattr(self, "_det_timer_id", None)
        if tid:
            try:
                self.root.after_cancel(tid)
            except Exception:
                pass
            self._det_timer_id = None

    def _detect_poll(self):
        """Mira OBS cada 2,5 s y, cuando cambia lo capturado, lo manda a resolver.

        Tres reglas que existen por el bug de parpadeo del 19/08:

        1. Un solo worker a la vez (`_det_busy`). El proximo tick se agenda
           cuando el worker TERMINA, no cuando arranca. Con el timeout de la API
           en 30 s y un tick cada 2,5 s, antes se apilaban hasta 12 pedidos
           simultaneos contra el backend.
        2. La clave de "esto ya lo resolvi" es el EXE cuando existe, no el par
           (exe, titulo). Hay juegos que cambian el titulo de la ventana en vivo
           â€”reloj, FPS, mapaâ€” y con el titulo adentro cada vuelta parecia un
           juego distinto y se reconsultaba.
        3. Si la consulta falla, NO se limpia la clave. Antes se limpiaba "para
           que reintente", y el reintento fallaba igual: resolviendo -> error ->
           resolviendo, cada 2,5 s, para siempre. Ahora el error queda quieto en
           pantalla, con el motivo y un boton para reintentar a mano.
        """
        if not getattr(self, "_det_active", False) or self.recording:
            return
        if getattr(self, "_det_busy", False):
            self._det_timer_id = self.root.after(2500, self._detect_poll)
            return
        self._det_busy = True

        def _fin():
            """Libera el turno y agenda el proximo tick."""
            self._det_busy = False
            if getattr(self, "_det_active", False) and not self.recording:
                self._det_timer_id = self.root.after(2500, self._detect_poll)

        def _ui(fn, *a):
            self.root.after(0, lambda: (fn(*a), _fin()))

        def _worker():
            try:
                is_rec, title, exe, wrong = obs_capture_target()
            except OBSAuthError as e:
                _obs_dbg(f"deteccion: OBS pide password: {e}")
                _ui(self._render_det_bloqueado,
                    "OBS pide contrasena en el WebSocket", str(e))
                return
            except Exception as e:
                _obs_dbg(f"deteccion: OBS no responde: {e}")
                _ui(self._render_det_esperando,
                    "OBS no esta corriendo o no responde. Abrilo y volve a esta pantalla.")
                return
            if is_rec:
                _ui(self._render_det_bloqueado, "OBS ya esta grabando",
                    "Detene la grabacion desde OBS antes de empezar una sesion.")
                return
            if wrong:
                _ui(self._render_det_bloqueado, "Modo de captura incorrecto: " + wrong,
                    "Cambia la fuente a Captura de Videojuego (Game Capture) y "
                    "apuntala a la ventana del juego.")
                return
            if not title and not exe:
                _ui(self._render_det_esperando,
                    "Abri el juego y apunta la fuente de OBS a su ventana.")
                return

            clave = exe.lower() if exe else ("t:" + title.lower())
            if clave == getattr(self, "_det_last", None):
                _fin()                      # ya resuelto: ni render ni consulta
                return
            self.root.after(0, lambda t=title: self._render_det_resolviendo(t))
            _obs_dbg(f"deteccion: resolviendo exe={exe!r} titulo={title!r}")
            try:
                res = pleiada_api.resolve_game(self.auth_token, exe, title)
            except pleiada_api.ApiError as e:
                # La clave NO se limpia: si se limpia, el proximo tick vuelve a
                # intentar y el ciclo de parpadeo arranca de nuevo.
                self._det_last = clave
                _obs_dbg(f"deteccion: resolve_game fallo ({e.code or 'sin codigo'}): {e}")
                _ui(self._render_det_error, str(e), e.code or "")
                return
            self._det_last = clave
            _obs_dbg(f"deteccion: estado={res.get('estado')!r} juego={(res.get('juego') or {}).get('name')!r}")
            _ui(self._apply_resolve, res)

        threading.Thread(target=_worker, daemon=True).start()

    def _reintentar_deteccion(self):
        """Vuelve a preguntar por lo mismo, a pedido del usuario."""
        self._det_last = None
        self._det_busy = False
        self._render_det_resolviendo("")
        self._detect_poll()

    # â€” Render de cada estado â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”

    def _det_clear(self):
        for box in (getattr(self, "_det_box", None), getattr(self, "_det_calls_box", None)):
            if box:
                for w in box.winfo_children():
                    w.destroy()

    def _render_det_esperando(self, msg):
        self._det_state = "esperando"
        self.selected_game = None
        self.selected_call = None
        self._det_clear()
        row = tk.Frame(self._det_box, bg=CARD)
        row.pack(fill="x", padx=14, pady=12)
        tk.Label(row, text="\u25cb", fg=DIM, bg=CARD, font=("Segoe UI", 10)).pack(side="left")
        tk.Label(row, text="Esperando el juego", fg=TEXT, bg=CARD,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(8, 0))
        tk.Label(self._det_calls_box, text=msg, fg=DIM, bg=BG, font=("Segoe UI", 10),
                 justify="left", anchor="w", wraplength=WIN_W - 60).pack(fill="x")
        tk.Label(self._det_calls_box,
                 text="La fuente tiene que estar en modo ventana especifica.",
                 fg=DIMMER, bg=BG, font=("Segoe UI", 9), justify="left", anchor="w",
                 wraplength=WIN_W - 60).pack(fill="x", pady=(6, 0))
        self._update_record_btn()

    def _render_det_resolviendo(self, titulo):
        self._det_state = "resolviendo"
        self.selected_game = None
        self._det_clear()
        row = tk.Frame(self._det_box, bg=CARD)
        row.pack(fill="x", padx=14, pady=12)
        tk.Label(row, text="\u25d0", fg=ACCENT, bg=CARD, font=("Segoe UI", 10)).pack(side="left")
        tk.Label(row, text=titulo or "Identificando...", fg=TEXT, bg=CARD,
                 font=("Segoe UI", 11, "bold"), anchor="w",
                 wraplength=WIN_W - 90).pack(side="left", padx=(8, 0))
        # Nombrar IGDB: la espera se entiende, y despues se entiende de donde
        # salio la clasificacion cuando se le dice que no encaja en ninguna orden.
        tk.Label(self._det_calls_box,
                 text="Identificando el titulo. Si no lo conocemos, buscamos su ficha en IGDB...",
                 fg=DIM, bg=BG, font=("Segoe UI", 10), justify="left", anchor="w",
                 wraplength=WIN_W - 60).pack(fill="x")
        self._update_record_btn()

    def _render_det_bloqueado(self, titulo, msg):
        self._det_state = "bloqueado"
        self.selected_game = None
        self.selected_call = None
        self._det_clear()
        row = tk.Frame(self._det_box, bg=CARD)
        row.pack(fill="x", padx=14, pady=12)
        tk.Label(row, text="\u2715", fg=RED, bg=CARD, font=("Segoe UI", 10)).pack(side="left")
        tk.Label(row, text=titulo, fg=TEXT, bg=CARD, font=("Segoe UI", 11, "bold"),
                 anchor="w", wraplength=WIN_W - 90).pack(side="left", padx=(8, 0))
        tk.Label(self._det_calls_box, text=msg, fg=DIM, bg=BG, font=("Segoe UI", 10),
                 justify="left", anchor="w", wraplength=WIN_W - 60).pack(fill="x")
        self._update_record_btn()

    def _render_det_error(self, msg, code=""):
        """Fallo la consulta al backend. Se queda quieto: reintentar es del usuario.

        Reintentar solo cada 2,5 s no arregla nada cuando el error es estable
        â€”sesion vencida, backend caido, sin internetâ€” y convierte la pantalla en
        un parpadeo del que no se puede leer ni el motivo.
        """
        self._det_state = "error"
        self.selected_game = None
        self.selected_call = None
        self._det_clear()
        row = tk.Frame(self._det_box, bg=CARD)
        row.pack(fill="x", padx=14, pady=12)
        tk.Label(row, text="\u26a0", fg=YELLOW, bg=CARD,
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Label(row, text="No pudimos verificar el titulo", fg=TEXT, bg=CARD,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(8, 0))
        tk.Label(self._det_calls_box, text=msg, fg=DIM, bg=BG, font=("Segoe UI", 10),
                 justify="left", anchor="w", wraplength=WIN_W - 60).pack(fill="x")
        if code in ("sesion_invalida", "auth"):
            tk.Label(self._det_calls_box,
                     text="ProbÃ¡ cerrar sesiÃ³n y volver a entrar desde Ajustes.",
                     fg=DIMMER, bg=BG, font=("Segoe UI", 9), anchor="w",
                     wraplength=WIN_W - 60).pack(fill="x", pady=(4, 0))
        b = tk.Label(self._det_calls_box, text="Reintentar", fg=ACCENT, bg=BG,
                     font=("Segoe UI", 10), cursor="hand2", anchor="w")
        b.pack(fill="x", pady=(10, 0))
        b.bind("<Button-1>", lambda e: self._reintentar_deteccion())
        self._update_record_btn()

    def _apply_resolve(self, res):
        estado = (res or {}).get("estado", "")
        if estado == "candidatos":
            self._render_det_candidatos(res)
            return
        if estado in ("no_identificado", "no_disponible"):
            self._render_det_bloqueado(
                "No pudimos identificar el titulo" if estado == "no_identificado"
                else "Titulo no disponible",
                res.get("message") or "")
            return
        self._render_det_resuelto(res.get("juego") or {}, res.get("calls") or [],
                                  admitido=(estado == "admitido"))

    def _render_det_candidatos(self, res):
        self._det_state = "candidatos"
        self.selected_game = None
        self._det_clear()
        row = tk.Frame(self._det_box, bg=CARD)
        row.pack(fill="x", padx=14, pady=12)
        tk.Label(row, text="Cual estas jugando?", fg=TEXT, bg=CARD,
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(self._det_calls_box,
                 text="No pudimos identificarlo solos. Estos son los que mas se parecen.",
                 fg=DIM, bg=BG, font=("Segoe UI", 10), justify="left", anchor="w",
                 wraplength=WIN_W - 60).pack(fill="x", pady=(0, 8))
        for cand in res.get("candidatos") or []:
            b = tk.Label(self._det_calls_box, text=cand.get("name", ""), fg=TEXT, bg=CARD,
                         font=("Segoe UI", 10), anchor="w", cursor="hand2",
                         padx=12, pady=9)
            b.pack(fill="x", pady=(0, 6))
            b.bind("<Button-1>", lambda e, c=cand: self._pick_candidato(c))
        self._update_record_btn()

    def _pick_candidato(self, cand):
        self._render_det_resolviendo(cand.get("name", ""))

        def _worker():
            try:
                calls = pleiada_api.calls_for_game(self.auth_token, cand.get("name", ""))
            except pleiada_api.ApiError:
                calls = []
            self.root.after(0, lambda: self._render_det_resuelto(cand, calls))

        threading.Thread(target=_worker, daemon=True).start()

    def _render_det_resuelto(self, juego, calls, admitido=False):
        """Juego identificado. Con ordenes se elige destino; sin ordenes, libre."""
        self._det_state = "resuelto"
        # El resto de la app (metadata, nombre de carpeta, pantallas de
        # grabacion) sigue leyendo selected_game como antes: solo cambia de
        # donde sale.
        self.selected_game = {
            "game":        juego.get("name", ""),
            "genre":       juego.get("genre", ""),
            "perspective": juego.get("perspective", ""),
            "mode":        juego.get("mode", ""),
        }
        self._det_clear()
        row = tk.Frame(self._det_box, bg=CARD)
        row.pack(fill="x", padx=14, pady=12)
        tk.Label(row, text="\u25cf", fg=GREEN, bg=CARD, font=("Segoe UI", 10)).pack(side="left")
        col = tk.Frame(row, bg=CARD)
        col.pack(side="left", padx=(8, 0), fill="x", expand=True)
        tk.Label(col, text=juego.get("name", ""), fg=TEXT, bg=CARD,
                 font=("Segoe UI", 11, "bold"), anchor="w",
                 wraplength=WIN_W - 110).pack(fill="x")
        detalle = " \u00b7 ".join(x for x in (juego.get("genre"), juego.get("perspective"),
                                              juego.get("mode")) if x)
        if detalle:
            tk.Label(col, text=detalle, fg=DIM, bg=CARD, font=("Segoe UI", 9),
                     anchor="w").pack(fill="x")
        if admitido:
            tk.Label(self._det_calls_box, text="Sumado al programa.", fg=GREEN, bg=BG,
                     font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(0, 6))

        if calls:
            self.selected_call = calls[0].get("call_id")
            self._call_var = tk.StringVar(value=self.selected_call)
            tk.Label(self._det_calls_box, text="ORDEN DE DESTINO", fg=DIM, bg=BG,
                     font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", pady=(0, 6))
            for c in calls:
                tk.Radiobutton(
                    self._det_calls_box, text=c.get("titulo", c.get("call_id", "")),
                    value=c.get("call_id"), variable=self._call_var,
                    command=lambda: setattr(self, "selected_call", self._call_var.get()),
                    fg=TEXT, bg=BG, selectcolor=CARD, activebackground=BG,
                    activeforeground=TEXT, font=("Segoe UI", 10), anchor="w",
                    highlightthickness=0, bd=0).pack(fill="x")
                precio = c.get("precio_hora_usd")
                if precio:
                    tk.Label(self._det_calls_box, text="    USD %.2f/h" % precio,
                             fg=DIM, bg=BG, font=("Segoe UI", 9), anchor="w").pack(fill="x")
        else:
            # Modo libre. El copy no promete que la orden vaya a llegar.
            self.selected_call = None
            tk.Label(self._det_calls_box,
                     text="Ninguna orden abierta esta buscando este tipo de titulo.",
                     fg=YELLOW, bg=BG, font=("Segoe UI", 10), anchor="w",
                     justify="left", wraplength=WIN_W - 60).pack(fill="x")
            tk.Label(self._det_calls_box,
                     text="Podes grabarlo y guardarlo igual. Puede aparecer una orden que "
                          "lo acepte, o puede no aparecer nunca. Chequea el dashboard y "
                          "nuestras redes por nuevas ordenes.",
                     fg=DIM, bg=BG, font=("Segoe UI", 9), anchor="w", justify="left",
                     wraplength=WIN_W - 60).pack(fill="x", pady=(4, 0))
        self._update_record_btn()

    def _check_obs_game(self):
        """Verifica en OBS quÃ© juego estÃ¡ capturado (en thread)."""
        self._obs_dot.config(fg=ACCENT)
        self._obs_lbl.config(text="Verificando OBS...", fg=DIM)
        self._obs_status = "checking"
        self._warn_frame.pack_forget()

        def _worker():
            selected = (self.selected_game or {}).get("game", "")
            try:
                is_recording, win_title, win_match, wrong_source = obs_check_status()
            except OBSAuthError as e:
                self.root.after(0, lambda m=str(e): self._set_obs_status("auth_error", m))
                return
            except Exception:
                # OBS no estÃ¡ corriendo o no responde â€” tratar como advertencia
                self.root.after(0, lambda: self._set_obs_status(
                    "warn", "OBS no estÃ¡ corriendo o no responde al WebSocket."))
                return

            # Check 1 â€” OBS ya grabando
            if is_recording:
                self.root.after(0, lambda: self._set_obs_status(
                    "already_recording",
                    "OBS ya estÃ¡ grabando. DetenÃ© la grabaciÃ³n desde OBS antes de continuar."
                ))
                return

            # Check 2 â€” modo de captura incorrecto (Display/Window Capture)
            if wrong_source:
                self.root.after(0, lambda ws=wrong_source: self._set_obs_status(
                    "wrong_source", ws
                ))
                return

            # Check 3 â€” verificar que el juego correcto estÃ¡ en Game Capture
            if not win_title:
                status = "warn"
                msg    = "OBS no detecta ningÃºn juego capturado. RevisÃ¡ la fuente Game Capture."
            else:
                if _obs_title_matches(selected, win_match or win_title):
                    status = "ok"
                    msg    = f"Juego detectado en OBS: {win_title}"
                else:
                    status = "mismatch"
                    msg    = f'OBS captura "{win_title}" pero seleccionaste "{selected}".'

            self.root.after(0, lambda: self._set_obs_status(status, msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _set_obs_status(self, status, msg):
        # v0.9: la pantalla principal ya no tiene el panel de estado de OBS: lo
        # reemplazo el de deteccion. Se conserva el metodo porque el flujo de
        # grabacion lo sigue llamando, pero no puede asumir que los widgets
        # existan.
        self._obs_status = status
        if not hasattr(self, "_obs_dot") or not self._obs_dot.winfo_exists():
            return
        colors = {
            "ok":               GREEN,
            "warn":             YELLOW,
            "mismatch":         RED,
            "already_recording":RED,
            "wrong_source":     RED,
            "auth_error":       RED,
            "checking":         ACCENT,
            "idle":             DIMMER,
        }
        self._obs_dot.config(fg=colors.get(status, DIM))

        if status == "ok":
            self._obs_lbl.config(text=msg, fg=GREEN)
            self._warn_frame.pack_forget()
        elif status == "warn":
            self._obs_lbl.config(text="No se detectÃ³ Game Capture en OBS.", fg=YELLOW)
            self._warn_txt.config(text=msg)
            self._warn_frame.pack(fill="x", pady=(8, 0))
        elif status == "mismatch":
            self._obs_lbl.config(text="Juego incorrecto en OBS.", fg=RED)
            self._warn_txt.config(text=msg + "\n\nCambiÃ¡ la fuente Game Capture antes de grabar.")
            self._warn_frame.pack(fill="x", pady=(8, 0))
        elif status == "already_recording":
            self._obs_lbl.config(text="OBS ya estÃ¡ grabando.", fg=RED)
            self._warn_txt.config(
                text=msg + "\n\nLa grabaciÃ³n debe iniciarse desde el Recorder, no desde OBS.")
            self._warn_frame.pack(fill="x", pady=(8, 0))
        elif status == "wrong_source":
            # msg contiene el nombre legible del modo incorrecto (ej: "Captura de Pantalla")
            self._obs_lbl.config(text=f"Modo de captura incorrecto: {msg}.", fg=RED)
            self._warn_txt.config(
                text=f"EstÃ¡s usando '{msg}' en OBS, que no es compatible con Gameplay Recorder.\n\n"
                     f"CambiÃ¡ la fuente a 'Captura de Videojuego' (Game Capture) y apuntala "
                     f"al proceso del juego.")
            self._warn_frame.pack(fill="x", pady=(8, 0))
        elif status == "auth_error":
            self._obs_lbl.config(text="OBS WebSocket: autenticaciÃ³n fallida.", fg=RED)
            self._warn_txt.config(text=msg)
            self._warn_frame.pack(fill="x", pady=(8, 0))
        self._update_record_btn()

    def _update_record_btn(self):
        # v0.9: el panel de deteccion llama a este metodo desde un worker, y en
        # la segunda visita a la pantalla el atributo existe pero apunta a un
        # widget ya destruido. hasattr no alcanza: hace falta winfo_exists.
        btn = getattr(self, "_rec_btn_idle", None)
        if btn is None:
            return
        try:
            if not btn.winfo_exists():
                return
        except Exception:
            return
        # v0.9: alcanza con que el juego este identificado. El estado de OBS ya
        # se evaluo para poder detectarlo, y el chequeo de coincidencia entre lo
        # declarado y lo capturado dejo de existir: no hay nada que declarar.
        can_record = (
            self.selected_game is not None and
            not self._update_required      # v0.8: bloqueado si VERSION < min_version
        )
        if can_record:
            self._rec_btn_idle.config(
                state="normal", cursor="hand2",
                bg=ACCENT, fg="#ffffff",
                activebackground="#9080e0", activeforeground="#fff"
            )
        else:
            self._rec_btn_idle.config(
                state="disabled", cursor="arrow",
                bg=CARD, fg=DIMMER,
                activebackground=CARD, activeforeground=DIMMER
            )

    # â”€â”€ Iniciar / Detener grabaciÃ³n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _start_recording(self):
        # v0.9: se sacaron la guarda por "mismatch" de OBS y el chequeo por
        # tasklist de que el proceso estuviera corriendo. Los dos comparaban
        # contra un juego DECLARADO por el usuario, y ya no hay declaracion: el
        # juego sale de lo que OBS captura. Eran la causa principal de los
        # bloqueos que la gente reportaba.
        if not self.selected_game:
            return
        if self._update_required:
            return
        self._detect_stop()

        self._show_recording_starting()

        def _worker():
            # 1. Crear carpeta de sesiÃ³n
            game   = re.sub(r'[\\/:*?"<>|]', "", self.selected_game["game"])
            dt     = time.strftime("%d_%m_%y__%H_%M_%S")
            sname  = f"{game}_{dt} recording"
            sdir   = BASE_DIR / sname
            BASE_DIR.mkdir(parents=True, exist_ok=True)
            sdir.mkdir(parents=True, exist_ok=True)
            self.session_dir = sdir

            # 2. Asegurarse de que OBS estÃ© corriendo (lanzarlo si hace falta).
            #    Esto puede tardar hasta ~30 s si OBS no estÃ¡ abierto.
            #    NO iniciamos la grabaciÃ³n todavÃ­a â€” eso ocurre en countdown=0.
            try:
                if not obs_is_running():
                    if not launch_obs():
                        self.root.after(0, lambda: self._recording_start_error())
                        return
            except Exception as e:
                _obs_dbg(f"_start_recording obs check: {e}")
                self.root.after(0, lambda: self._recording_start_error())
                return

            # 3. Escribir game_name
            try:
                GAME_FILE.write_text(game, encoding="utf-8")
            except Exception:
                pass

            # 4. Guardia final + obtener rec_dir (una sola conexiÃ³n WebSocket)
            rec_dir_str   = ""
            existing_vids = set()
            try:
                ws = obs_connect()

                # Guardia: OBS no debe estar grabando en este momento
                rec_status = obs_send(ws, "GetRecordStatus")
                if rec_status.get("d", {}).get("responseData", {}).get("outputActive", False):
                    ws.close()
                    self.root.after(0, lambda: self._recording_start_error(
                        "OBS empezÃ³ a grabar mientras preparabas la sesiÃ³n.\n"
                        "DetenÃ© la grabaciÃ³n en OBS y volvÃ© a intentarlo."
                    ))
                    return

                # Re-verificar fuente y ventana de captura justo antes de grabar
                _WRONG_SOURCES = {
                    "monitor_capture": "Captura de Pantalla",
                    "screen_capture":  "Captura de Pantalla",
                    "window_capture":  "Captura de Ventana",
                }
                try:
                    inp_resp = obs_send(ws, "GetInputList")
                    inputs   = inp_resp.get("d", {}).get("responseData", {}).get("inputs", [])

                    # PLE-33: solo bloquear si la fuente incompatible estÃ¡ activa en la escena
                    try:
                        _sr2  = obs_send(ws, "GetCurrentProgramScene")
                        _csn  = _sr2.get("d", {}).get("responseData", {}).get("currentProgramSceneName", "")
                        _sir  = obs_send(ws, "GetSceneItemList", {"sceneName": _csn})
                        _sil  = _sir.get("d", {}).get("responseData", {}).get("sceneItems", [])
                        _en2  = {i.get("sourceName", "") for i in _sil if i.get("sceneItemEnabled", False)}
                    except Exception:
                        _en2  = None
                    wrong_kind = None
                    for inp in inputs:
                        kind = inp.get("inputKind", "")
                        name = inp.get("inputName", "")
                        if kind in _WRONG_SOURCES:
                            if _en2 is None or name in _en2:
                                wrong_kind = _WRONG_SOURCES[kind]
                                break
                    if wrong_kind:
                        ws.close()
                        self.root.after(0, lambda wk=wrong_kind: (
                            self._show_idle(),
                            self._set_obs_status("wrong_source", wk)
                        ))
                        return

                    # Sin fuentes incompatibles â€” verificar que game_capture apunta al juego correcto
                    gc_src = next((i for i in inputs if i.get("inputKind") == "game_capture"), None)
                    if gc_src:
                        sr     = obs_send(ws, "GetInputSettings", {"inputName": gc_src["inputName"]})
                        window = sr.get("d", {}).get("responseData", {}).get("inputSettings", {}).get("window", "")
                        selected_name = (self.selected_game or {}).get("game", "")
                        if window:
                            _parts    = window.split(":")
                            win_title = _parts[0].strip()
                            _exe_part = ""
                            for _pp in _parts[1:]:
                                _pp = _pp.strip()
                                if _pp.lower().endswith(".exe"):
                                    _exe_part = re.sub(r'\.exe$', '', _pp, flags=re.IGNORECASE)
                                    break
                            win_match = f"{win_title} {_exe_part}".strip()
                        else:
                            win_title = win_match = ""
                        if win_title and not _obs_title_matches(selected_name, win_match or win_title):
                            ws.close()
                            self.root.after(0, lambda wt=win_title, sn=selected_name: (
                                self._show_idle(),
                                self._set_obs_status(
                                    "mismatch",
                                    f'OBS captura "{wt}" pero seleccionaste "{sn}".'
                                )
                            ))
                            return
                except Exception:
                    pass   # si falla la verificaciÃ³n, continuamos igualmente

                r = obs_send(ws, "GetRecordDirectory")
                ws.close()
                rec_dir_str = r.get("d", {}).get("responseData", {}).get("recordDirectory", "")
                if rec_dir_str and os.path.isdir(rec_dir_str):
                    existing_vids = set(glob.glob(os.path.join(rec_dir_str, "*.mp4")))
            except OBSAuthError as e:
                self.root.after(0, lambda m=str(e): self._recording_start_error(m))
                return
            except Exception:
                pass   # OBS no responde â€” continuamos sin rec_dir

            # 5. Guardar prep para el thread que arranca en countdown=0
            self._obs_prep = (rec_dir_str, existing_vids)

            # 6. Mostrar countdown â€” OBS aÃºn no estÃ¡ grabando
            self.recording = True
            self.root.after(0, self._show_countdown)
            # (La grabaciÃ³n real arranca en _launch_at_zero, cuando el countdown llega a 0)

        threading.Thread(target=_worker, daemon=True).start()

    def _recording_start_error(self, msg="Error: no se pudo iniciar OBS."):
        self._show_idle()
        # Mostrar mensaje de error en el panel de OBS (pantalla idle)
        if hasattr(self, "_obs_lbl"):
            self._obs_lbl.config(text=msg, fg=RED)
        if hasattr(self, "_warn_txt") and "\n" in msg:
            # Mensaje largo (ej: auth error) â†’ tambiÃ©n en el panel de advertencia
            try:
                self._warn_txt.config(text=msg)
                self._warn_frame.pack(fill="x", pady=(8, 0))
            except Exception:
                pass

    def _cancel_recording(self):
        """Descarta la sesion en curso: ni dataset ni analisis.

        Es lo contrario de Detener, que cierra bien y deja la sesion lista para
        subir. Aca se para OBS, se borra la carpeta con los CSV a medio escribir
        y NO se corre el sync check: no hay nada que verificar ni que subir, y
        el usuario no espera por un analisis de algo que descarto.

        El MP4 se deja donde OBS lo dejo. Es lo unico que sobrevive: si alguien
        cancela porque se equivoco de juego, el video sigue siendo suyo â€” pero
        no queda como sesion, asi que no se puede subir despues.
        """
        if not self.recording:
            return
        import tkinter.messagebox as _mb
        if not _mb.askyesno(
                "Cancelar grabaciÃ³n",
                "Se descarta esta sesiÃ³n: no se genera el dataset y no vas a "
                "poder subirla.\n\n"
                "El video queda en tu carpeta de grabaciones de OBS.\n\n"
                "Â¿Cancelar la grabaciÃ³n?",
                default="no", icon="warning"):
            return

        self._we_stopped = True     # el listener no lo toma como caida de OBS
        self.recording   = False
        if getattr(self, "_demo_name", ""):
            _source_console("stop")
        for attr in ("_cd_timer_id", "_timer_id"):
            tid = getattr(self, attr, None)
            if tid:
                self.root.after_cancel(tid)
                setattr(self, attr, None)

        sdir = self.session_dir
        self.session_dir = None
        self._show_cancelling()

        def _worker():
            try:
                stop_ahk_logger(str(sdir) if sdir else "")
            except Exception as e:
                _obs_dbg(f"cancel: stop_ahk_logger: {e}")
            # session_dir=None -> OBS cierra el archivo pero NO se mueve a la
            # carpeta de sesion, que es justamente lo que se va a borrar.
            video = ""
            try:
                video = obs_stop_recording(None) or ""
            except Exception as e:
                _obs_dbg(f"cancel: obs_stop_recording: {e}")
            if sdir:
                try:
                    _unprotect_session_files(sdir)
                except Exception:
                    pass
                try:
                    shutil.rmtree(sdir, ignore_errors=True)
                    _obs_dbg(f"Sesion cancelada, carpeta borrada: {sdir}")
                except Exception as e:
                    _obs_dbg(f"cancel: rmtree: {e}")
            self.root.after(0, lambda: self._show_cancelled(video))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_cancelling(self):
        self._clear_content()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)
        tk.Frame(frame, bg=BG).pack(fill="y", expand=True)
        tk.Label(frame, text="Cancelandoâ€¦", fg=TEXT, bg=BG,
                 font=("Segoe UI", 13, "bold")).pack()
        tk.Label(frame, text="Cerrando la grabaciÃ³n y descartando la sesiÃ³n.",
                 fg=DIM, bg=BG, font=("Segoe UI", 10),
                 wraplength=WIN_W - 60).pack(pady=(8, 0))
        tk.Frame(frame, bg=BG).pack(fill="y", expand=True)

    def _show_cancelled(self, video_path=""):
        self._clear_content()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)
        tk.Frame(frame, bg=BG).pack(fill="y", expand=True)
        tk.Label(frame, text="GrabaciÃ³n cancelada", fg=TEXT, bg=BG,
                 font=("Segoe UI", 13, "bold")).pack()
        tk.Label(frame, text="No se generÃ³ el dataset y la sesiÃ³n no queda "
                             "disponible para subir.",
                 fg=DIM, bg=BG, font=("Segoe UI", 10), justify="center",
                 wraplength=WIN_W - 60).pack(pady=(8, 0))
        if video_path:
            tk.Label(frame, text="El video quedÃ³ en:", fg=DIMMER, bg=BG,
                     font=("Segoe UI", 9)).pack(pady=(14, 0))
            tk.Label(frame, text=video_path, fg=DIM, bg=BG,
                     font=("Cascadia Code", 8), wraplength=WIN_W - 60,
                     justify="center").pack()
        tk.Frame(frame, bg=BG).pack(fill="y", expand=True)
        _mk_separator(frame, color=BORDER2, pady=(0, 14))
        tk.Button(frame, text="Volver", fg=TEXT, bg=CARD, relief="flat", bd=0,
                  cursor="hand2", font=("Segoe UI", 11), activebackground=CARD2,
                  activeforeground=TEXT, command=self._show_idle,
                  highlightthickness=1, highlightbackground=BORDER).pack(fill="x", ipady=10)

    def _stop_recording(self):
        if not self.recording:
            return
        self._we_stopped = True   # le decimos al listener que NOSOTROS paramos
        self.recording = False
        if getattr(self, "_demo_name", ""):   # cortar el demo POV (TF2/L4D2) si se estaba grabando
            _source_console("stop")
        if self._cd_timer_id:
            self.root.after_cancel(self._cd_timer_id)
            self._cd_timer_id = None
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None

        sdir = self.session_dir
        self._show_syncing(sdir)

        def _worker():
            # 1. Detener AHK de forma ordenada.
            #    AHK escribe ANCHOR_END a todos los CSVs y cierra sus handles
            #    antes de salir. Si AHK no estaba corriendo, Python escribe
            #    ANCHOR_END como fallback.
            ahk_ran = stop_ahk_logger(str(sdir))
            if not ahk_ran:
                end_ts  = int(time.time() * 1000)
                csv_map = {
                    "mouse_log.csv":       f"{end_ts},ANCHOR_END,,,",
                    "mouse_delta_log.csv": f"{end_ts},ANCHOR_END,,",
                    "key_log.csv":         f"{end_ts},ANCHOR_END,,",
                    "video_timeline.csv":  f"{end_ts},ANCHOR_END",
                }
                for name, line in csv_map.items():
                    p = sdir / name
                    try:
                        with open(p, "a", encoding="utf-8") as f:
                            f.write(line + "\n")
                    except Exception:
                        pass

            # 2. Detener OBS y mover video
            obs_stop_recording(sdir)

            # 4. Esperar a que el video aparezca en sdir
            for _ in range(40):
                if list(sdir.glob("*.mp4")):
                    break
                time.sleep(0.5)

            # 4b. Copiar el demo POV (TF2/L4D2) a la carpeta de sesiÃ³n â†’ el miembro sube UNA sola
            #     carpeta. Best-effort: si no se encuentra el .dem, no rompe nada (queda en el juego).
            dn   = getattr(self, "_demo_name", "")
            exep = getattr(self, "_recording_exe_path", "")
            if dn and exep:
                try:
                    gd = os.path.dirname(exep)
                    src = None
                    for _ in range(20):   # esperar a que el juego finalice el .dem tras `stop`
                        hits = (glob.glob(os.path.join(gd, dn + ".dem")) +
                                glob.glob(os.path.join(gd, "*", dn + ".dem")))
                        if hits:
                            src = hits[0]; break
                        time.sleep(0.5)
                    if src:
                        shutil.copy2(src, str(sdir / (dn + ".dem")))
                except Exception:
                    pass

            # 5. Correr sync check â€” acumular statuses por archivo para mostrarlos en resultado
            _keys = ["mouse_log.csv", "mouse_delta_log.csv", "key_log.csv", "video_timeline.csv", "video"]
            self._last_sync_statuses = {}

            def _on_progress(i, s):
                if i < len(_keys):
                    self._last_sync_statuses[_keys[i]] = s
                self.root.after(0, lambda i=i, s=s: self._sync_progress(i, s))

            results = run_sync_check(sdir, progress_cb=_on_progress)

            # 6. Guardar metadata sidecar localmente (siempre, ok o fallido).
            #    Ya NO se empaqueta un .pleiada â€” los archivos quedan sueltos en la
            #    carpeta de sesiÃ³n (CSVs + MP4 + session_metadata.json).
            self.root.after(0, self._show_packaging_anim)   # "Guardando localmente los archivos..."
            build_session_metadata(sdir, self.selected_game, results,
                                   exe_path=self._recording_exe_path,
                                   obs_window=self._recording_obs_window,
                                   modo=("manual" if getattr(self, "selected_call", None)
                                         else "libre"))
            # Bug 2: registrar el check del metadata json para mostrarlo en el anÃ¡lisis
            self._last_sync_statuses["metadata"] = ("ok"
                if (sdir / "session_metadata.json").exists() else "err")

            # 6b. Estado de subida (para la lista "Mis grabaciones"): vÃ¡lida/no vÃ¡lida,
            #     todavÃ­a no subida.
            write_session_state(sdir, valid=bool(results.get("session_ok")),
                                uploaded=False,
                                game=(self.selected_game or {}).get("game", ""))

            # 6c. ProtecciÃ³n read-only â€” SOLO si la sesiÃ³n pasÃ³ el sync check. Las
            #     rechazadas se descartan (el usuario borra la carpeta), asÃ­ que no se
            #     protegen â†’ evita conflictos con cualquier borrado posterior.
            if results.get("session_ok"):
                _protect_session_files(sdir)

            # 7. Mostrar resultado â€” o encadenar el auto-reinicio (v0.7.1)
            _auto = self._auto_stopped and self._settings.get("auto_restart")
            self._auto_stopped = False
            if _auto and results.get("session_ok"):
                self.root.after(0, self._begin_auto_restart)   # â†’ cuenta regresiva â†’ nueva sesiÃ³n
            else:
                # auto-stop con sesiÃ³n rechazada â†’ cortar el ciclo y avisar (decisiÃ³n del usuario)
                _note = "auto_restart_halted" if _auto else None
                self.root.after(0, lambda n=_note: self._show_result(
                    results["session_ok"], results, None, n))

        threading.Thread(target=_worker, daemon=True).start()

    # â”€â”€ Pantalla: iniciando grabaciÃ³n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _show_recording_starting(self):
        self._clear_content()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="", bg=BG).pack(expand=True)
        tk.Label(frame, text="â³  Iniciando grabaciÃ³n...", fg=DIM, bg=BG,
                  font=("Segoe UI", 13)).pack()
        tk.Label(frame, text="Conectando a OBS, por favor esperÃ¡.", fg=DIMMER, bg=BG,
                  font=("Segoe UI", 10)).pack(pady=(8, 0))
        tk.Label(frame, text="", bg=BG).pack(expand=True)

    # â”€â”€ Pantalla: cuenta regresiva pre-grabaciÃ³n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    _COUNTDOWN_SECS = 10   # PLE-34: reducido de 15 a 10 segundos

    def _show_countdown(self):
        self._clear_content()
        game  = (self.selected_game or {}).get("game", "â€”")
        genre = (self.selected_game or {}).get("genre", "")

        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=18)

        # â€” Status row â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”
        status_row = tk.Frame(frame, bg=BG)
        status_row.pack(fill="x")
        self._cd_dot = tk.Label(status_row, text="â—", fg=YELLOW, bg=BG,
                                 font=("Segoe UI", 10, "bold"))
        self._cd_dot.pack(side="left")
        tk.Label(status_row, text="INICIANDO", fg=YELLOW, bg=BG,
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(6, 0))

        # â€” Nombre del juego â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”
        tk.Label(frame, text=game, fg=TEXT, bg=BG,
                  font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", pady=(14, 4))
        tk.Label(frame, text=genre, fg=DIM, bg=BG,
                  font=("Segoe UI", 10), anchor="w").pack(fill="x")

        # â€” NÃºmero grande de countdown (misma fuente que el timer) â€”â€”â€”â€”â€”â€”â€”â€”
        tk.Frame(frame, bg=BG).pack(fill="y", expand=True)
        self._cd_num_lbl = tk.Label(frame, text=str(self._COUNTDOWN_SECS),
                                     fg=YELLOW, bg=BG,
                                     font=("Cascadia Code", 52, "normal"))
        self._cd_num_lbl.pack()
        tk.Label(frame, text="La grabaciÃ³n comenzarÃ¡ en...", fg=DIM, bg=BG,
                  font=("Segoe UI", 10)).pack(pady=(10, 0))
        tk.Frame(frame, bg=BG).pack(fill="y", expand=True)

        _mk_separator(frame, color=BORDER2, pady=(0, 14))

        # â€” BotÃ³n cancelar â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”
        tk.Button(frame, text="Cancelar", fg=DIMMER, bg=CARD,
                   relief="flat", bd=0, cursor="hand2",
                   font=("Segoe UI", 10), activebackground=CARD2,
                   activeforeground=DIM,
                   command=self._stop_recording,
                   highlightthickness=1, highlightbackground=BORDER2).pack(
            fill="x", ipady=8)

        self._cd_remaining = self._COUNTDOWN_SECS
        self._tick_countdown()
        self._pulse_cd_dot()

    def _tick_countdown(self):
        if not self.recording:
            return
        if self._cd_remaining <= 0:
            self._cd_timer_id = None
            # Mostrar â–¶ brevemente mientras el thread de OBS arranca
            try:
                self._cd_num_lbl.config(text="â–¶", fg=GREEN)
            except Exception:
                pass
            # OBS StartRecord ocurre en thread separado â€” no bloquea la UI
            threading.Thread(target=self._launch_at_zero, daemon=True).start()
            return
        # Color: amarillo mientras queda tiempo, rojo en los Ãºltimos 5
        col = RED if self._cd_remaining <= 5 else YELLOW
        self._cd_num_lbl.config(text=str(self._cd_remaining), fg=col)
        self._cd_remaining -= 1
        self._cd_timer_id = self.root.after(1000, self._tick_countdown)

    def _pulse_cd_dot(self):
        if not self.recording or not hasattr(self, "_cd_num_lbl"):
            return
        try:
            if not self._cd_num_lbl.winfo_exists():
                return
        except Exception:
            return
        cur = self._cd_dot.cget("fg")
        self._cd_dot.config(fg=YELLOW if cur == BG else BG)
        self.root.after(600, self._pulse_cd_dot)

    def _launch_at_zero(self):
        """Corre en thread separado cuando el countdown llega a 0.
        EnvÃ­a StartRecord a OBS, captura el anchor timestamp, arranca AHK
        y muestra la pantalla de grabaciÃ³n activa."""
        if not self.recording:
            return

        # a. VerificaciÃ³n final de fuente OBS â€” el usuario pudo cambiar algo durante el countdown
        try:
            _is_rec, win_title, win_match, wrong_source = obs_check_status()
            if wrong_source:
                self.recording = False
                self.root.after(0, lambda ws=wrong_source: (
                    self._show_idle(),
                    self._set_obs_status("wrong_source", ws)
                ))
                return
            if win_title:
                selected = (self.selected_game or {}).get("game", "")
                if not _obs_title_matches(selected, win_match or win_title):
                    self.recording = False
                    self.root.after(0, lambda wt=win_title, sn=selected: (
                        self._show_idle(),
                        self._set_obs_status(
                            "mismatch",
                            f'OBS captura "{wt}" pero seleccionaste "{sn}".'
                        )
                    ))
                    return
        except OBSAuthError as e:
            self.recording = False
            msg = str(e)
            self.root.after(0, lambda m=msg: self._recording_start_error(m))
            return
        except Exception:
            pass   # si OBS no responde en este punto, continuamos igual

        # b. Enviar StartRecord (OBS ya estÃ¡ corriendo â€” _worker lo garantizÃ³)
        try:
            ok = _obs_do_start()
        except OBSAuthError as e:
            self.recording = False
            msg = str(e)
            self.root.after(0, lambda m=msg: self._recording_start_error(m))
            return
        if not ok:
            self.recording = False
            self.root.after(0, self._recording_start_error)
            return

        # b. Anchor timestamp â€” capturado justo al confirmar STARTED
        anchor_ts = int(time.time() * 1000)

        # c. Escribir anchor file (AHK lo lee al arrancar)
        try:
            ANCHOR_FILE.write_text(str(anchor_ts), encoding="utf-8")
        except Exception:
            pass

        # c.bis Auto-record del demo POV (TF2/L4D2) por netcon â€” el miembro no toca la consola.
        self._demo_name = ""
        if _autodemo_game(self.selected_game):
            self._demo_name = f"pleiada_{anchor_ts}"
            _source_console(f"record {self._demo_name}")

        # d. Resolver el exe del juego ANTES de lanzar AHK (el filtro de ventana lo usa).
        #    BUGFIX v0.5: antes start_ahk_logger se llamaba con el _recording_exe de la
        #    grabaciÃ³n ANTERIOR (se resolvÃ­a despuÃ©s), y en la 2da grabaciÃ³n de una sesiÃ³n
        #    el filtro bloqueaba toda la captura por exe equivocado.
        self._we_stopped = False
        self._recording_exe = ""   # resetear: no arrastrar el exe de una grabaciÃ³n previa
        _win = ""
        try:
            _sr = obs_connect()
            _inputs = obs_send(_sr, "GetInputList").get("d", {}).get("responseData", {}).get("inputs", [])
            _gc = next((i for i in _inputs if i.get("inputKind") == "game_capture"), None)
            if _gc:
                _ws_set = obs_send(_sr, "GetInputSettings", {"inputName": _gc["inputName"]})
                _win = _ws_set.get("d", {}).get("responseData", {}).get("inputSettings", {}).get("window", "")
                self._recording_exe = next(
                    (_obs_unescape(p.strip()) for p in _win.split(":")
                     if p.strip().lower().endswith(".exe")), ""
                )
            _sr.close()
        except Exception:
            self._recording_exe = ""
        # Cachear ruta completa del exe (juego corriendo): OBS exe -> wmic, con fallback
        # a buscar la ventana del juego por tÃ­tulo.
        self._recording_exe_path = _meta_find_game_exe_path(
            _win, (self.selected_game or {}).get("game", "")
        )
        # v0.8.12: el window string CRUDO de OBS, tal cual llegÃ³. Va a la metadata
        # como observabilidad: sin esto no hay forma de auditar a posteriori quÃ©
        # estaba capturando OBS cuando se grabÃ³, y un mismatch de tÃ­tulo queda
        # indetectable una vez subida la sesiÃ³n.
        self._recording_obs_window = _win or ""

        # e. Arrancar AHK con el exe YA resuelto (filtro de ventana correcto) +
        #    los VK de los hotkeys del Recorder para que AHK no los registre en key_log.
        _hk_vks = ",".join(
            str(self._settings[k]["vk"])
            for k in ("hotkey_start", "hotkey_stop")
            if self._settings.get(k, {}).get("vk")
        )
        start_ahk_logger(str(self.session_dir), self._recording_exe, _hk_vks)

        # f. Listeners de OBS
        self._start_obs_stop_listener()
        self._start_obs_source_monitor()

        # f. Mostrar pantalla de grabaciÃ³n activa
        self.root.after(0, lambda: self._show_recording_active(anchor_ts))

    # â”€â”€ OBS stop listener â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _start_obs_stop_listener(self):
        """Abre una conexiÃ³n WebSocket dedicada y escucha RecordStateChanged en background.
        Si OBS detiene la grabaciÃ³n sin que nosotros lo hayamos pedido, cancela la sesiÃ³n."""

        def _listener():
            ws = None
            try:
                ws = obs_connect()
                ws.settimeout(1.5)   # timeout corto para salir del loop cuando recording=False
                while self.recording and not self._we_stopped:
                    try:
                        raw = ws.recv()
                        if not raw:
                            break
                        parsed = json.loads(raw)
                        if parsed.get("op") == 5:
                            ed = parsed.get("d", {})
                            if (ed.get("eventType") == "RecordStateChanged" and
                                    ed.get("eventData", {}).get("outputState")
                                    == "OBS_WEBSOCKET_OUTPUT_STOPPED"):
                                # OBS dejÃ³ de grabar â€” Â¿fuimos nosotros?
                                if not self._we_stopped and self.recording:
                                    self.root.after(0, self._obs_external_stop)
                                break
                    except Exception as exc:
                        # Timeout es la excepciÃ³n esperada del polling â€” continuar
                        exc_name = type(exc).__name__
                        if "timeout" in exc_name.lower():
                            continue
                        _obs_dbg(f"obs_stop_listener recv: {exc_name}: {exc}")
                        break
            except Exception as e:
                _obs_dbg(f"obs_stop_listener connect: {e}")
            finally:
                if ws:
                    try: ws.close()
                    except: pass

        threading.Thread(target=_listener, daemon=True).start()

    def _obs_external_stop(self):
        """Llamado en el main thread cuando OBS detuvo la grabaciÃ³n externamente.
        Cancela la sesiÃ³n: para AHK abruptamente, elimina archivos, vuelve al idle."""
        if not self.recording:
            return   # ya fue detenida normalmente justo a la vez â€” ignorar

        self._we_stopped = True
        self.recording   = False

        # Cancelar timers de UI
        if self._timer_id:
            try: self.root.after_cancel(self._timer_id)
            except: pass
            self._timer_id = None
        if self._cd_timer_id:
            try: self.root.after_cancel(self._cd_timer_id)
            except: pass
            self._cd_timer_id = None

        sdir = self.session_dir
        obs_prep = self._obs_prep   # capturar antes de resetear

        # Parar AHK de golpe (sin esperar ANCHOR_END â€” la sesiÃ³n se descarta)
        stop_ahk_logger(None)

        # Eliminar carpeta de sesiÃ³n con todos los CSVs
        if sdir and sdir.exists():
            try:
                shutil.rmtree(str(sdir), ignore_errors=True)
            except Exception:
                pass

        self.session_dir = None

        # Eliminar el MP4 que OBS guardÃ³ (estÃ¡ en el dir de grabaciÃ³n de OBS, no en sdir)
        threading.Thread(
            target=self._delete_obs_video, args=(obs_prep,), daemon=True
        ).start()

        # Volver al idle y mostrar advertencia
        self._show_idle()
        if hasattr(self, "_obs_lbl"):
            try:
                self._obs_lbl.config(
                    text="OBS detuvo la grabaciÃ³n.", fg=RED)
            except Exception:
                pass
        if hasattr(self, "_warn_txt"):
            try:
                self._warn_txt.config(
                    text="OBS detuvo la grabaciÃ³n antes de que el Recorder terminara.\n\n"
                         "La sesiÃ³n fue cancelada. Siempre usÃ¡ el botÃ³n 'Detener' del Recorder "
                         "para finalizar correctamente."
                )
                self._warn_frame.pack(fill="x", pady=(8, 0))
            except Exception:
                pass

    # â”€â”€ EliminaciÃ³n segura del MP4 descartado â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _delete_obs_video(self, obs_prep):
        """Busca y elimina permanentemente el MP4 que OBS creÃ³ para una sesiÃ³n cancelada.
        Corre en thread background porque OBS puede tardar unos segundos en terminar de
        escribir el archivo despuÃ©s de StopRecord.

        obs_prep: tupla (rec_dir_str, existing_vids_set) capturada antes de la grabaciÃ³n.
        """
        rec_dir_str, existing_vids = obs_prep
        if not rec_dir_str or not os.path.isdir(rec_dir_str):
            _obs_dbg("_delete_obs_video: rec_dir desconocido, buscando en carpeta Videos")
            # Fallback: buscar en ~/Videos el MP4 mÃ¡s reciente (Ãºltimos 5 min)
            rec_dir_str = str(Path.home() / "Videos")
            existing_vids = set()

        # Esperar hasta 15 s a que aparezca el archivo nuevo
        new_file = None
        for _ in range(75):
            time.sleep(0.2)
            for f in glob.glob(os.path.join(rec_dir_str, "*.mp4")):
                if f not in existing_vids:
                    new_file = f
                    break
            if new_file:
                break

        if not new_file:
            _obs_dbg("_delete_obs_video: no se encontrÃ³ MP4 nuevo para eliminar")
            return

        # Esperar a que OBS suelte el handle del archivo (hasta 10 s adicionales)
        for _ in range(20):
            try:
                os.remove(new_file)
                _obs_dbg(f"_delete_obs_video: eliminado permanentemente â†’ {new_file}")
                return
            except (PermissionError, OSError):
                time.sleep(0.5)

        _obs_dbg(f"_delete_obs_video: no se pudo eliminar (handle ocupado) â†’ {new_file}")

    # â”€â”€ Monitor de fuente OBS durante grabaciÃ³n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _start_obs_source_monitor(self):
        """Sondea la fuente de OBS cada 3 s durante la grabaciÃ³n.
        Detecta:
        - Fuente incorrecta o ventana cambiada â†’ cancela la sesiÃ³n.
        - PLE-37: el proceso del juego cerrÃ³ â†’ cancela la sesiÃ³n automÃ¡ticamente.
        """

        def _game_process_running(exe_name):
            """Retorna True si el proceso exe_name estÃ¡ corriendo."""
            if not exe_name:
                return True   # sin exe conocido â†’ no bloquear
            try:
                # /FO CSV no trunca el nombre del proceso (TABLE lo corta a 25 chars,
                # rompiendo exes largos tipo "{Proyecto}-Win64-Shipping.exe" de Unreal,
                # lo que cancelaba la sesiÃ³n por falso "el juego se cerrÃ³").
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return exe_name.lower() in result.stdout.lower()
            except Exception:
                return True   # error â†’ beneficio de la duda

        def _monitor():
            time.sleep(4)   # dar tiempo a que la grabaciÃ³n arranque bien
            game_not_found_count = 0   # PLE-37: contador de checks sin proceso

            while self.recording and not self._we_stopped:
                try:
                    _, win_title, win_match, wrong_source = obs_check_status()
                except Exception:
                    time.sleep(3)
                    continue

                if not self.recording or self._we_stopped:
                    break

                problem_msg = None

                # Verificar fuente de OBS
                if wrong_source:
                    problem_msg = (
                        f"Cambiaste la fuente en OBS a '{wrong_source}' durante la grabaciÃ³n.\n\n"
                        "La sesiÃ³n fue cancelada automÃ¡ticamente."
                    )
                elif win_title:
                    selected = (self.selected_game or {}).get("game", "")
                    if not _obs_title_matches(selected, win_match or win_title):
                        problem_msg = (
                            f"OBS cambiÃ³ a capturar '{win_title}' durante la grabaciÃ³n.\n\n"
                            "La sesiÃ³n fue cancelada automÃ¡ticamente."
                        )

                # PLE-37: verificar que el proceso del juego sigue corriendo
                if not problem_msg:
                    rec_exe = self._recording_exe
                    if rec_exe and not _game_process_running(rec_exe):
                        game_not_found_count += 1
                        if game_not_found_count >= 2:   # 2 checks consecutivos sin el proceso
                            game_display = rec_exe.replace(".exe", "")
                            problem_msg = (
                                f"El juego '{game_display}' se cerrÃ³ durante la grabaciÃ³n.\n\n"
                                "La sesiÃ³n fue cancelada automÃ¡ticamente."
                            )
                    else:
                        game_not_found_count = 0   # reset si el proceso volviÃ³ a aparecer

                if problem_msg and not self._we_stopped and self.recording:
                    self.root.after(0, lambda m=problem_msg: self._obs_mid_recording_cancel(m))
                    break

                time.sleep(3)

        threading.Thread(target=_monitor, daemon=True).start()

    def _obs_mid_recording_cancel(self, reason_msg):
        """Llamado en el main thread cuando la fuente de OBS cambiÃ³ durante la grabaciÃ³n.
        Para OBS (sigue grabando), para AHK, elimina sesiÃ³n, vuelve al idle."""
        if not self.recording:
            return

        self._we_stopped = True
        self.recording   = False

        # Cancelar timers UI
        if self._timer_id:
            try: self.root.after_cancel(self._timer_id)
            except: pass
            self._timer_id = None

        sdir = self.session_dir
        obs_prep = self._obs_prep   # capturar antes de resetear

        # Parar AHK de golpe
        stop_ahk_logger(None)

        # Parar OBS (sigue grabando â€” a diferencia del stop externo, aquÃ­ debemos detenerlo)
        try:
            ws = obs_connect()
            obs_send(ws, "StopRecord")
            ws.close()
        except Exception:
            pass

        # Eliminar carpeta de sesiÃ³n con todos los CSVs
        if sdir and sdir.exists():
            try:
                shutil.rmtree(str(sdir), ignore_errors=True)
            except Exception:
                pass

        self.session_dir = None

        # Eliminar el MP4 que OBS guardÃ³ (necesita esperar a que OBS termine de escribirlo)
        threading.Thread(
            target=self._delete_obs_video, args=(obs_prep,), daemon=True
        ).start()

        # Volver al idle con mensaje de error
        self._show_idle()
        if hasattr(self, "_obs_lbl"):
            try:
                self._obs_lbl.config(text="GrabaciÃ³n cancelada automÃ¡ticamente.", fg=RED)
            except Exception:
                pass
        if hasattr(self, "_warn_txt"):
            try:
                self._warn_txt.config(text=reason_msg)
                self._warn_frame.pack(fill="x", pady=(8, 0))
            except Exception:
                pass

    # â”€â”€ Pantalla: grabando â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _show_recording_active(self, anchor_ts):
        self._clear_content()
        self.rec_seconds = 0
        # v0.7.1: duraciÃ³n mÃ¡xima de ESTA sesiÃ³n desde settings (clamp ya aplicado al cargar)
        self._max_seconds  = int(self._settings.get("max_session_minutes", 60)) * 60
        self._auto_stopped = False
        game = (self.selected_game or {}).get("game", "â€”")

        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=18)

        # Status row â€” right items primero para evitar overlap en ventanas angostas
        status_row = tk.Frame(frame, bg=BG)
        status_row.pack(fill="x")
        # Derecha: lÃ­mite + countdown (se packean antes para reservar espacio)
        _mh, _mm, _ms = self._max_seconds // 3600, (self._max_seconds % 3600) // 60, self._max_seconds % 60
        self._countdown_lbl = tk.Label(status_row, text=f"{_mh:02d}:{_mm:02d}:{_ms:02d}", fg=DIM, bg=BG,
                                        font=("Cascadia Code", 11))
        self._countdown_lbl.pack(side="right")
        tk.Label(status_row, text="lÃ­mite  ", fg=DIMMER, bg=BG,
                  font=("Segoe UI", 9)).pack(side="right")
        # Izquierda: dot + GRABANDO
        self._rec_dot = tk.Label(status_row, text="â—", fg=RED, bg=BG,
                                  font=("Segoe UI", 10, "bold"))
        self._rec_dot.pack(side="left")
        tk.Label(status_row, text="GRABANDO", fg=RED, bg=BG,
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(6, 0))

        # Game label
        tk.Label(frame, text=game, fg=TEXT, bg=BG,
                  font=("Segoe UI", 13, "bold"), anchor="w",
                  wraplength=WIN_W - 44).pack(fill="x", pady=(14, 4))
        genre = (self.selected_game or {}).get("genre", "")
        tk.Label(frame, text=genre, fg=DIM, bg=BG,
                  font=("Segoe UI", 10), anchor="w").pack(fill="x")

        # Huge timer
        tk.Frame(frame, bg=BG).pack(fill="y", expand=True)
        self._timer_lbl = tk.Label(frame, text="00:00:00", fg=TEXT, bg=BG,
                                    font=("Cascadia Code", 52, "normal"))
        self._timer_lbl.pack(pady=(10, 0))
        tk.Frame(frame, bg=BG).pack(fill="y", expand=True)

        _mk_separator(frame, color=BORDER2, pady=(0, 14))

        # Stop button
        stop_btn = tk.Button(frame, text="  â¹  Detener grabaciÃ³n", fg=RED, bg="#1a0808",
                              relief="flat", bd=0, cursor="hand2",
                              font=("Segoe UI", 12, "bold"),
                              activebackground="#2a1010", activeforeground=RED,
                              command=self._stop_recording,
                              highlightthickness=1, highlightbackground="#7a2020")
        stop_btn.pack(fill="x", ipady=12)

        # Cancelar: descarta la sesion en vez de cerrarla. Va abajo y en gris â€”
        # Detener es la accion normal y tiene que seguir siendo la obvia.
        cancel_btn = tk.Button(frame, text="Cancelar grabaciÃ³n", fg=DIM, bg=BG,
                               relief="flat", bd=0, cursor="hand2",
                               font=("Segoe UI", 10),
                               activebackground=BG, activeforeground=TEXT,
                               command=self._cancel_recording,
                               highlightthickness=0)
        cancel_btn.pack(fill="x", pady=(8, 0))

        self._set_back(None)          # grabando no se sale con Atras
        # Start ticker
        self._ticker()
        self._pulse_dot()

    def _ticker(self):
        if not self.recording:
            return
        self.rec_seconds += 1
        h = self.rec_seconds // 3600
        m = (self.rec_seconds % 3600) // 60
        s = self.rec_seconds % 60
        self._timer_lbl.config(text=f"{h:02d}:{m:02d}:{s:02d}")

        # Update countdown
        rem = max(0, self._max_seconds - self.rec_seconds)
        rh  = rem // 3600
        rm  = (rem % 3600) // 60
        rs  = rem % 60
        col = YELLOW if rem <= 300 else DIM
        self._countdown_lbl.config(text=f"{rh:02d}:{rm:02d}:{rs:02d}", fg=col)

        if self.rec_seconds >= self._max_seconds:
            self._auto_stopped = True   # v0.7.1: distinguir auto-stop por tiempo del stop manual
            self._stop_recording()
            return

        self._timer_id = self.root.after(1000, self._ticker)

    def _pulse_dot(self):
        if not self.recording:
            return
        cur = self._rec_dot.cget("fg")
        self._rec_dot.config(fg=RED if cur == BG else BG)
        self.root.after(700, self._pulse_dot)

    # â”€â”€ Auto-reinicio de grabaciÃ³n (v0.7.1) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _begin_auto_restart(self):
        """Tras un auto-stop por tiempo con sesiÃ³n OK: cuenta regresiva de 10 s â†’ nueva sesiÃ³n."""
        self._auto_restart_cancelled = False
        self._auto_restart_left = 10
        self._clear_content()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)
        tk.Frame(frame, bg=BG).pack(fill="y", expand=True)
        tk.Label(frame, text="âœ“ SesiÃ³n guardada", fg=GREEN, bg=BG,
                 font=("Segoe UI", 12, "bold")).pack()
        tk.Label(frame, text="Reiniciando grabaciÃ³n en", fg=DIM, bg=BG,
                 font=("Segoe UI", 11)).pack(pady=(12, 0))
        self._restart_big = tk.Label(frame, text="10", fg=TEXT, bg=BG,
                                     font=("Cascadia Code", 52, "normal"))
        self._restart_big.pack()
        tk.Label(frame, text="Cada sesiÃ³n se guarda en su propia carpeta â€” no se sobrescriben.",
                 fg=DIMMER, bg=BG, font=("Segoe UI", 9), wraplength=WIN_W - 60).pack(pady=(0, 10))
        tk.Frame(frame, bg=BG).pack(fill="y", expand=True)
        _mk_separator(frame, color=BORDER2, pady=(0, 14))
        tk.Button(frame, text="Cancelar", fg=TEXT, bg=CARD, relief="flat", bd=0,
                  cursor="hand2", font=("Segoe UI", 11), activebackground=CARD2,
                  activeforeground=TEXT, command=self._cancel_auto_restart,
                  highlightthickness=1, highlightbackground=BORDER).pack(fill="x", ipady=10)
        self._tick_auto_restart()

    def _tick_auto_restart(self):
        if self._auto_restart_cancelled:
            return
        if self._auto_restart_left <= 0:
            if not self.selected_game:     # el juego se deseleccionÃ³ â†’ no reiniciar
                self._show_idle(); return
            self._start_recording()        # crea carpeta nueva con timestamp â†’ no se pisa nada
            return
        try:
            self._restart_big.config(text=str(self._auto_restart_left))
        except Exception:
            pass
        self._auto_restart_left -= 1
        self.root.after(1000, self._tick_auto_restart)

    def _cancel_auto_restart(self):
        self._auto_restart_cancelled = True
        self.session_dir = None
        self._show_idle()

    # â”€â”€ Pantalla: verificando â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _show_syncing(self, sdir):
        self._clear_content()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)

        tk.Label(frame, text="VERIFICANDO SESIÃ“N", fg=DIM, bg=BG,
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 14))

        # Verify panel
        verify = tk.Frame(frame, bg="#0b0b1d", bd=1, relief="solid",
                           highlightthickness=1, highlightbackground=BORDER2)
        verify.pack(fill="x")
        verify.configure(highlightbackground=BORDER2)

        self._sync_rows = {}
        items = [
            ("mouse_log.csv",       "mouse_log.csv"),
            ("mouse_delta_log.csv", "mouse_delta_log.csv"),
            ("key_log.csv",         "key_log.csv"),
            ("video_timeline.csv",  "video_timeline.csv"),
            ("video",               "video MP4"),
        ]
        for i, (key, label) in enumerate(items):
            row = tk.Frame(verify, bg="#0b0b1d")
            row.pack(fill="x", padx=14, pady=4)
            mark = tk.Label(row, text="Â·", fg=ACCENT, bg="#0b0b1d",
                             font=("Cascadia Code", 10), width=2)
            mark.pack(side="left")
            tk.Label(row, text=label, fg=TEXT, bg="#0b0b1d",
                      font=("Cascadia Code", 10), anchor="w", width=22).pack(side="left")
            val = tk.Label(row, text="verificando...", fg=ACCENT, bg="#0b0b1d",
                            font=("Cascadia Code", 10), anchor="e")
            val.pack(side="right")
            self._sync_rows[key] = (mark, val)

        self._sync_summary_lbl = tk.Label(verify, text="", fg=DIM, bg="#0b0b1d",
                                           font=("Segoe UI", 10, "bold"))
        self._sync_summary_lbl.pack(anchor="w", padx=14, pady=(8, 10))

    def _sync_progress(self, step_idx, status):
        keys  = ["mouse_log.csv", "mouse_delta_log.csv", "key_log.csv", "video_timeline.csv", "video"]
        if step_idx >= len(keys):
            return
        key = keys[step_idx]
        if key not in self._sync_rows:
            return
        mark, val = self._sync_rows[key]
        if status == "ok":
            mark.config(text="âœ“", fg=GREEN)
            val.config(text="ok", fg=GREEN)
        elif status == "missing":
            mark.config(text="âœ—", fg=RED)
            val.config(text="falta", fg=RED)
        elif status == "err":
            mark.config(text="âœ—", fg=RED)
            val.config(text="error", fg=RED)
        elif status == "truncated":
            mark.config(text="âœ—", fg=RED)
            val.config(text="truncado", fg=RED)
        elif status == "offset":
            mark.config(text="âš ", fg=YELLOW)
            val.config(text="desfase", fg=YELLOW)

    def _show_packaging_anim(self):
        """Muestra 'Guardando localmente los archivos...' animado en el panel de syncing."""
        if not hasattr(self, "_sync_summary_lbl"):
            return
        try:
            self._sync_summary_lbl.config(text="Guardando localmente los archivos...", fg=ACCENT)
        except Exception:
            return
        self._pkg_anim_state = 0
        self._pkg_anim_id = None
        self._animate_packaging_dots()

    def _animate_packaging_dots(self):
        try:
            if not self._sync_summary_lbl.winfo_exists():
                return
        except Exception:
            return
        frames = [
            "Guardando localmente los archivos   ",
            "Guardando localmente los archivos.  ",
            "Guardando localmente los archivos.. ",
            "Guardando localmente los archivos...",
        ]
        self._pkg_anim_state = (getattr(self, "_pkg_anim_state", 0) + 1) % len(frames)
        try:
            self._sync_summary_lbl.config(text=frames[self._pkg_anim_state], fg=ACCENT)
        except Exception:
            return
        self._pkg_anim_id = self.root.after(380, self._animate_packaging_dots)

    # â”€â”€ Pantalla: resultado â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _show_result(self, ok, results, out_path, note=None):
        self._clear_content()

        # PLE-45: botones anclados al fondo â€” siempre visibles sin importar
        # resoluciÃ³n o escalado de pantalla. Se packean ANTES que el canvas
        # para que Tkinter les reserve espacio antes de expandir el scroll.
        tk.Frame(self.content, bg=BORDER2, height=1).pack(side="bottom", fill="x")
        btn_outer = tk.Frame(self.content, bg=BG, padx=22, pady=10)
        btn_outer.pack(side="bottom", fill="x")
        btn_row = tk.Frame(btn_outer, bg=BG)
        btn_row.pack(fill="x")

        # Canvas scrollable â€” ocupa el espacio restante por encima del btn_row
        canvas = tk.Canvas(self.content, bg=BG, bd=0, highlightthickness=0)
        canvas.pack(side="top", fill="both", expand=True)

        frame = tk.Frame(canvas, bg=BG)
        frame_id = canvas.create_window((0, 0), window=frame, anchor="nw")

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas_configure(e):
            canvas.itemconfig(frame_id, width=e.width)
            canvas.after_idle(lambda: canvas.configure(scrollregion=canvas.bbox("all")))
        frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Mousewheel scroll (anÃ¡lisis scrolleable si el contenido excede el Ã¡rea)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        # â”€â”€ Botones â€” definidos acÃ¡ para capturar canvas en el closure â”€â”€â”€â”€â”€â”€â”€â”€
        def go_again():
            canvas.unbind_all("<MouseWheel>")
            self.session_dir = None
            self._show_idle()

        tk.Button(btn_row, text="Nueva grabaciÃ³n", fg=TEXT, bg=CARD,
                   relief="flat", bd=0, cursor="hand2",
                   font=("Segoe UI", 11), activebackground=CARD2,
                   activeforeground=TEXT, command=go_again,
                   highlightthickness=1, highlightbackground=BORDER).pack(
            side="left", fill="x", expand=True, ipady=10, padx=(0, 6) if ok else (0, 0))

        if ok:
            tk.Button(btn_row, text="Subir Data Set", fg="#fff", bg=ACCENT,
                       relief="flat", bd=0, cursor="hand2",
                       font=("Segoe UI", 11, "bold"), activebackground="#9080e0",
                       command=lambda: self._start_upload_flow(
                           self.session_dir, self._show_idle)).pack(
                           side="right", fill="x", expand=True, ipady=10, padx=(6, 0))

        inner = tk.Frame(frame, bg=BG)
        inner.pack(fill="both", expand=True, padx=22, pady=16)

        # v0.7.1: aviso si el reinicio automÃ¡tico se detuvo por una sesiÃ³n rechazada
        if note == "auto_restart_halted":
            tk.Label(inner, text="âš   Reinicio automÃ¡tico detenido â€” la Ãºltima grabaciÃ³n no pasÃ³ "
                                 "la verificaciÃ³n de sincronizaciÃ³n.",
                     fg=YELLOW, bg=BG, font=("Segoe UI", 10), justify="left",
                     wraplength=WIN_W - 80, anchor="w").pack(fill="x", pady=(0, 10))

        # â”€â”€ Notify card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if ok:
            card_bg  = "#06140d"
            card_brd = "#1e6644"
            icon_txt = "âœ“"
            icon_col = GREEN
            title    = "Â¡SesiÃ³n lista para enviar!"
            body     = ("La sesiÃ³n fue analizada y se encuentra sincronizada. "
                        "Verifica que no haya nada personal en los archivos, no los "
                        "modifiques, y comienza la subida a la plataforma")
        else:
            card_bg  = "#140606"
            card_brd = "#7a2020"
            icon_txt = "âœ—"
            icon_col = RED
            title    = "SesiÃ³n no apta para enviar"
            if results and results.get("short_session"):
                # PLE-41: sesiÃ³n demasiado corta
                body = "La sesiÃ³n durÃ³ menos de 30 segundos.\nGrabÃ¡ al menos 30 segundos de gameplay para que los datos sean vÃ¡lidos."
            elif results and results.get("video_still"):
                # Gate de video quieto. Va ANTES que el de AFK: si disparan los
                # dos, la causa real suele ser que OBS no estaba capturando, y
                # decirle "estuviste inactivo" lo manda a buscar donde no estÃ¡.
                # Tampoco se menciona el umbral (misma regla que AFK).
                body = ("La sesiÃ³n tiene un perÃ­odo largo donde la imagen no cambiÃ³ "
                        "(pantalla negra o congelada).\nVerificÃ¡ que OBS estÃ© capturando "
                        "el juego e iniciÃ¡ una nueva sesiÃ³n.")
            elif results and results.get("sin_input"):
                # Gate de input vacÃ­o. Va ANTES que el de AFK porque es mÃ¡s
                # especÃ­fico: AFK dirÃ­a "estuviste inactivo" cuando en realidad
                # el jugador jugÃ³ toda la sesiÃ³n y lo que fallÃ³ fue la captura.
                # Las dos causas se resuelven distinto, asÃ­ que el texto cambia.
                if results.get("sin_input_causa") == "captura_bloqueada":
                    body = ("No se registrÃ³ lo que hiciste con el teclado y el mouse, "
                            "aunque el video se grabÃ³ bien.\nSuele pasar cuando el juego "
                            "corre como administrador o su anticheat bloquea la captura. "
                            "AbrÃ­ el Recorder como administrador e iniciÃ¡ una nueva sesiÃ³n; "
                            "si vuelve a pasar con este juego, avisanos.")
                else:
                    body = ("La sesiÃ³n no tiene actividad de teclado ni de mouse.\nSi jugaste "
                            "con joystick, todavÃ­a no podemos registrarlo: grabÃ¡ con teclado "
                            "y mouse e iniciÃ¡ una nueva sesiÃ³n.")
            elif results and results.get("afk"):
                # Gate AFK: demasiado tiempo continuo sin inputs.
                # A propÃ³sito NO se menciona el umbral exacto (pedido de MartÃ­n 20/7).
                body = ("La sesiÃ³n tiene un perÃ­odo largo sin actividad de teclado o mouse "
                        "(AFK).\nGrabÃ¡ jugando activamente e iniciÃ¡ una nueva sesiÃ³n.")
            else:
                body = "Los archivos no pasaron el sync check.\nDescartÃ¡ esta sesiÃ³n e iniciÃ¡ una nueva."

        notify = tk.Frame(inner, bg=card_bg, highlightthickness=1,
                           highlightbackground=card_brd)
        notify.pack(fill="x", pady=(0, 12))
        nrow = tk.Frame(notify, bg=card_bg)
        nrow.pack(fill="x", padx=12, pady=10)
        tk.Label(nrow, text=icon_txt, fg=icon_col, bg=card_bg,
                  font=("Segoe UI", 13, "bold")).pack(side="left", padx=(0, 10))
        nright = tk.Frame(nrow, bg=card_bg)
        nright.pack(side="left", fill="x", expand=True)
        tk.Label(nright, text=title, fg=TEXT, bg=card_bg,
                  font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(nright, text=body, fg=DIM if ok else "#f0c0c0", bg=card_bg,
                  font=("Segoe UI", 10), anchor="w", justify="left",
                  wraplength=WIN_W - 130).pack(fill="x", pady=(3, 0))

        # â”€â”€ Panel de anÃ¡lisis (siempre visible) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        _mk_section_label(inner, "ANÃLISIS DE SINCRONIZACIÃ“N")

        vbg = "#0b0b1d"
        verify = tk.Frame(inner, bg=vbg, highlightthickness=1, highlightbackground=BORDER2)
        verify.pack(fill="x", pady=(0, 12))

        file_items = [
            ("mouse_log.csv",       "mouse_log.csv"),
            ("mouse_delta_log.csv", "mouse_delta_log.csv"),
            ("key_log.csv",         "key_log.csv"),
            ("video_timeline.csv",  "video_timeline.csv"),
            ("video",               "video MP4"),
            ("metadata",            "session_metadata.json"),   # Bug 2
        ]
        statuses = self._last_sync_statuses
        status_labels = {
            "ok":       ("âœ“", GREEN,  "ok"),
            "missing":  ("âœ—", RED,    "falta"),
            "err":      ("âœ—", RED,    "error"),
            "truncated":("âœ—", RED,    "truncado"),
            "offset":   ("âš ", YELLOW, "desfase"),
        }
        for key, label in file_items:
            s = statuses.get(key, "pending")
            mark_txt, col, val_txt = status_labels.get(s, ("Â·", DIMMER, "â€”"))
            row = tk.Frame(verify, bg=vbg)
            row.pack(fill="x", padx=14, pady=3)
            tk.Label(row, text=mark_txt, fg=col, bg=vbg,
                      font=("Cascadia Code", 10), width=2, anchor="w").pack(side="left")
            tk.Label(row, text=label, fg=TEXT if s != "pending" else DIM, bg=vbg,
                      font=("Cascadia Code", 10), anchor="w", width=22).pack(side="left")
            tk.Label(row, text=val_txt, fg=col, bg=vbg,
                      font=("Cascadia Code", 10), anchor="e").pack(side="right")

        # LÃ­nea de detalle numÃ©rico
        if results:
            diff    = results.get("signed_diff")
            csv_dur = results.get("csv_dur")
            vid_dur = results.get("video_dur")
            truncated = results.get("truncated", False)

            tk.Frame(verify, bg=BORDER2, height=1).pack(fill="x", padx=14, pady=(4, 0))
            drow = tk.Frame(verify, bg=vbg)
            drow.pack(fill="x", padx=14, pady=(4, 10))

            if truncated:
                tk.Label(drow, text="Video truncado â€” OBS cerrÃ³ sin finalizar la grabaciÃ³n.",
                          fg=RED, bg=vbg, font=("Cascadia Code", 9), wraplength=WIN_W - 80,
                          justify="left", anchor="w").pack(fill="x")
            elif diff is not None and csv_dur and vid_dur:
                # Derecha primero para evitar overlap con items de izquierda
                diff_col = GREEN if ok else RED
                tk.Label(drow, text=f"Î” {diff:+d} ms", fg=diff_col, bg=vbg,
                          font=("Cascadia Code", 9, "bold")).pack(side="right")
                tk.Label(drow, text=f"CSV: {csv_dur} ms", fg=DIM, bg=vbg,
                          font=("Cascadia Code", 9)).pack(side="left")
                tk.Label(drow, text=f"Video: {vid_dur} ms", fg=DIM, bg=vbg,
                          font=("Cascadia Code", 9)).pack(side="left", padx=(14, 0))
            elif not results.get("csvs_ok"):
                tk.Label(drow, text="Uno o mÃ¡s archivos CSV estÃ¡n incompletos o faltan.",
                          fg=RED, bg=vbg, font=("Cascadia Code", 9), wraplength=WIN_W - 80,
                          justify="left", anchor="w").pack(fill="x")

        # â”€â”€ SesiÃ³n / archivo â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if self.session_dir:
            _mk_section_label(inner, "SESIÃ“N")
            srow = tk.Frame(inner, bg=BG)
            srow.pack(fill="x", pady=(0, 8))
            tk.Label(srow, text=self.session_dir.name, fg=DIM, bg=BG,
                      font=("Cascadia Code", 9), anchor="w", wraplength=WIN_W - 100,
                      justify="left").pack(side="left", fill="x", expand=True)
            def _open_folder(d=self.session_dir):
                subprocess.Popen(["explorer", str(d)])
            folder_btn = tk.Label(srow, text="ðŸ“", bg=BG, fg=YELLOW,
                                   font=("Segoe UI Emoji", 16), cursor="hand2",
                                   padx=4)
            folder_btn.pack(side="right", anchor="e")
            folder_btn.bind("<Button-1>", lambda e: _open_folder())

        # (botones movidos al fondo fijo de self.content â€” ver inicio de _show_result)

    # â”€â”€ Upload a S3 (vistas in-window) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _start_upload_flow(self, session_dir, return_to):
        """Punto de entrada del flujo de subida. Refresca las inscripciones ANTES
        de decidir: el usuario pudo inscribirse en el dashboard despuÃ©s de abrir el
        Recorder, y si no refrescamos, la lista quedarÃ­a vieja y bloquearÃ­a la subida.
        """
        self._clear_content()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)
        tk.Frame(frame, bg=BG).pack(fill="both", expand=True)
        tk.Label(frame, text="Verificando tus Ã³rdenesâ€¦", fg=TEXT, bg=BG,
                 font=("Segoe UI", 12, "bold")).pack()
        tk.Frame(frame, bg=BG).pack(fill="both", expand=True)

        def _worker(token=self.auth_token):
            calls = None
            try:
                calls = pleiada_api.my_calls(token)
            except Exception:
                calls = None   # sin red / token viejo: seguimos con lo que haya
            def _done():
                if calls is not None:
                    self.open_calls = calls
                self._upload_confirm_view(session_dir, return_to)
            self.root.after(0, _done)
        threading.Thread(target=_worker, daemon=True).start()

    def _upload_confirm_view(self, session_dir, return_to):
        self._clear_content()
        info = session_uploader.session_info(session_dir)
        meta = session_uploader.session_meta(session_dir)
        matches = self._calls_for_game(meta["game_title"])
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)

        # â”€â”€ Sin call elegible: el upload estÃ¡ bloqueado (el backend lo
        #    rechazarÃ­a igual â€” esto solo se lo explica al usuario antes). â”€â”€
        if not matches:
            tk.Label(frame, text="Subir Data Set", fg=TEXT, bg=BG,
                     font=("Segoe UI", 14, "bold"), anchor="w").pack(fill="x", pady=(0, 12))
            card_bg, card_brd = "#140e06", "#7a5a20"
            notify = tk.Frame(frame, bg=card_bg, highlightthickness=1,
                              highlightbackground=card_brd)
            notify.pack(fill="x")
            juego = meta["game_title"] or "este juego"
            if self.open_calls:
                body = (f"{juego} no entra en ninguna de tus Ã³rdenes activas.\n\n"
                        "Las subidas solo se habilitan para juegos elegibles de una "
                        "orden en la que estÃ©s inscripto. RevisÃ¡ las Ã³rdenes abiertas "
                        "en el dashboard de Gameplay Alliance.")
            else:
                body = ("No estÃ¡s inscripto en ninguna orden abierta.\n\n"
                        "Para subir contenido, primero inscribite en una orden desde "
                        "el dashboard de Gameplay Alliance y grabÃ¡ un juego elegible.")
            tk.Label(notify, text="âš   Subida no disponible", fg=YELLOW, bg=card_bg,
                     font=("Segoe UI", 11, "bold"), anchor="w").pack(
                fill="x", padx=14, pady=(10, 2))
            tk.Label(notify, text=body, fg=DIM, bg=card_bg, font=("Segoe UI", 10),
                     anchor="w", justify="left", wraplength=WIN_W - 90).pack(
                fill="x", padx=14, pady=(0, 12))

            tk.Frame(frame, bg=BG).pack(fill="both", expand=True)
            btns = tk.Frame(frame, bg=BG)
            btns.pack(fill="x")
            tk.Button(btns, text="Volver", fg=DIM, bg=CARD, relief="flat", bd=0,
                      cursor="hand2", font=("Segoe UI", 11), activebackground=CARD2,
                      activeforeground=TEXT, command=return_to,
                      highlightthickness=1, highlightbackground=BORDER).pack(
                side="left", fill="x", expand=True, ipady=10, padx=(0, 6))
            def _open_dashboard():
                import webbrowser
                webbrowser.open("https://gameplayalliance.gg/dashboard/")
            tk.Button(btns, text="Ver Ã³rdenes abiertas", fg="#fff", bg=ACCENT, relief="flat",
                      bd=0, cursor="hand2", font=("Segoe UI", 11, "bold"),
                      activebackground="#9080e0", command=_open_dashboard).pack(
                side="right", fill="x", expand=True, ipady=10, padx=(6, 0))
            return

        tk.Label(frame, text="Subir Data Set", fg=TEXT, bg=BG,
                 font=("Segoe UI", 14, "bold"), anchor="w").pack(fill="x", pady=(0, 6))
        tk.Label(frame, text="Â¿QuerÃ©s subir esta sesiÃ³n a Gameplay Alliance?",
                 fg=DIM, bg=BG, font=("Segoe UI", 11), anchor="w",
                 justify="left", wraplength=WIN_W - 60).pack(fill="x", pady=(0, 16))

        card = tk.Frame(frame, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x")
        dur_min = max(1, meta["duration_seconds"] // 60) if meta["duration_seconds"] else None
        rows = [("SesiÃ³n",   session_dir.name),
                ("Archivos", f"{info['count']} ({info['size_label']})")]
        if meta["game_title"]:
            rows.insert(0, ("Juego", meta["game_title"]))
        if dur_min:
            rows.append(("DuraciÃ³n", f"{dur_min} min"))
        for label, value in rows:
            row = tk.Frame(card, bg=CARD)
            row.pack(fill="x", padx=14, pady=8)
            tk.Label(row, text=label, fg=DIM, bg=CARD, font=("Segoe UI", 9, "bold"),
                     width=9, anchor="w").pack(side="left")
            tk.Label(row, text=value, fg=TEXT, bg=CARD, font=("Segoe UI", 10),
                     anchor="w", justify="left", wraplength=WIN_W - 150).pack(
                side="left", fill="x", expand=True)

        # â”€â”€ Open Call de destino (1 match: fijo; varios: selector) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        call_var = tk.StringVar(value=matches[0]["call_id"])
        _mk_section_label(frame, "ORDEN DE DESTINO")
        sel = tk.Frame(frame, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        sel.pack(fill="x")
        for m in matches:
            row = tk.Frame(sel, bg=CARD)
            row.pack(fill="x", padx=10, pady=4)
            rem = m.get("remaining_seconds")
            extra = f" Â· te quedan {rem // 3600}h {(rem % 3600) // 60:02d}m" if rem is not None else ""
            txt = f"{m.get('titulo', m['call_id'])}  ({m['call_id']}){extra}"
            if len(matches) == 1:
                tk.Label(row, text="â†’ " + txt, fg=TEXT, bg=CARD,
                         font=("Segoe UI", 10), anchor="w", justify="left",
                         wraplength=WIN_W - 100).pack(fill="x")
            else:
                tk.Radiobutton(row, text=txt, variable=call_var, value=m["call_id"],
                               fg=TEXT, bg=CARD, selectcolor=BG, anchor="w",
                               activebackground=CARD, activeforeground=TEXT,
                               font=("Segoe UI", 10), justify="left",
                               wraplength=WIN_W - 110).pack(fill="x")

        tk.Frame(frame, bg=BG).pack(fill="both", expand=True)

        btns = tk.Frame(frame, bg=BG)
        btns.pack(fill="x")
        tk.Button(btns, text="Volver", fg=DIM, bg=CARD, relief="flat", bd=0,
                  cursor="hand2", font=("Segoe UI", 11), activebackground=CARD2,
                  activeforeground=TEXT, command=return_to,
                  highlightthickness=1, highlightbackground=BORDER).pack(
            side="left", fill="x", expand=True, ipady=10, padx=(0, 6))
        tk.Button(btns, text="Subir", fg="#fff", bg=ACCENT, relief="flat", bd=0,
                  cursor="hand2", font=("Segoe UI", 11, "bold"), activebackground="#9080e0",
                  command=lambda: self._upload_progress_view(
                      session_dir, return_to, call_var.get())).pack(
            side="right", fill="x", expand=True, ipady=10, padx=(6, 0))

    def _upload_progress_view(self, session_dir, return_to, call_id=""):
        # v0.8.7 (bug QA): nunca dos subidas a la vez. Antes, navegar fuera de esta
        # vista (âš™ Ajustes) dejaba el thread subiendo en background; un reintento
        # apilaba OTRO thread sobre los mismos archivos y las conexiones se mataban
        # entre sÃ­ (<urlopen error EOF occurred in violation of protocol>).
        if self._uploading:
            return
        self._uploading = True
        self._clear_content()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)

        tk.Label(frame, text="Subiendo Data Set", fg=TEXT, bg=BG,
                 font=("Segoe UI", 14, "bold"), anchor="w").pack(fill="x")

        tk.Frame(frame, bg=BG).pack(fill="both", expand=True)

        status_var = tk.StringVar(value="Iniciandoâ€¦")
        tk.Label(frame, textvariable=status_var, fg=TEXT, bg=BG,
                 font=("Segoe UI", 11), anchor="w", justify="left").pack(fill="x")
        detail_var = tk.StringVar(value="")
        tk.Label(frame, textvariable=detail_var, fg=DIM, bg=BG,
                 font=("Cascadia Code", 9), anchor="w").pack(fill="x", pady=(4, 0))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("GameplayRecorder.Horizontal.TProgressbar",
                         troughcolor=CARD, background=ACCENT, borderwidth=0)
        pct_var = tk.DoubleVar(value=0)
        ttk.Progressbar(frame, variable=pct_var, maximum=100,
                         style="GameplayRecorder.Horizontal.TProgressbar").pack(
            fill="x", pady=(12, 0))

        tk.Frame(frame, bg=BG).pack(fill="both", expand=True)

        cancelled = [False]
        cancel_event = threading.Event()
        def _cancel():
            cancelled[0] = True
            cancel_event.set()   # corta el thread de subida: aborta el PUT y no finaliza
            return_to()
        tk.Button(frame, text="Cancelar", fg=DIM, bg=CARD, relief="flat", bd=0,
                  cursor="hand2", font=("Segoe UI", 11), activebackground=CARD2,
                  activeforeground=TEXT, command=_cancel,
                  highlightthickness=1, highlightbackground=BORDER).pack(
            fill="x", ipady=10)

        def on_progress(sent, total, filename, speed, eta):
            if cancelled[0]:
                return
            short = filename if len(filename) <= 28 else "â€¦" + filename[-25:]
            pct   = (sent / total * 100) if total else 0
            mb    = 1024 * 1024
            detail = f"{sent/mb:.1f} / {total/mb:.1f} MB Â· {pct:.0f}%"
            if speed:
                detail += f" Â· {speed/mb:.1f} MB/s"
            etatxt = _fmt_eta(eta)
            if etatxt:
                detail += f" Â· {etatxt}"
            self.root.after(0, lambda: status_var.set(f"Subiendo {short}"))
            self.root.after(0, lambda: detail_var.set(detail))
            self.root.after(0, lambda: pct_var.set(pct))

        def on_done(status, msg):
            self._uploading = False   # el worker terminÃ³ (ok/error/cancelado): se libera la subida
            if cancelled[0]:
                return
            if status == "ok":
                write_session_state(session_dir, uploaded=True,
                                    uploaded_at=int(time.time()))
                self._refresh_open_calls()   # las horas usadas cambiaron
                self.root.after(0, lambda: self._upload_result_view(
                    "ok", "", session_dir, return_to))
            elif status == "already":
                write_session_state(session_dir, uploaded=True)
                self.root.after(0, lambda: self._upload_result_view(
                    "already", "", session_dir, return_to))
            elif status == "auth":
                self.root.after(0, self._on_upload_auth_expired)
            elif status == "gate":
                # rechazo por reglas del Open Call: no ofrecer "Reintentar" a ciegas
                self._refresh_open_calls()   # el estado local quedÃ³ viejo
                self.root.after(0, lambda: self._upload_result_view(
                    "gate", msg, session_dir, return_to))
            else:
                self.root.after(0, lambda: self._upload_result_view(
                    "error", msg, session_dir, return_to, call_id))

        threading.Thread(
            target=session_uploader.upload_session,
            args=(session_dir, self.auth_token, call_id, on_progress, on_done,
                  cancel_event),
            daemon=True,
        ).start()

    def _upload_result_view(self, status, msg, session_dir, return_to, call_id=""):
        self._clear_content()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)
        tk.Frame(frame, bg=BG).pack(fill="both", expand=True)

        if status in ("ok", "already"):
            tk.Label(frame, text="âœ“", fg=GREEN, bg=BG,
                     font=("Segoe UI", 34, "bold")).pack()
            text = ("SesiÃ³n subida correctamente\na Gameplay Alliance."
                    if status == "ok" else
                    "Este Data Set ya estaba subido.")
            tk.Label(frame, text=text, fg=TEXT, bg=BG, font=("Segoe UI", 12, "bold"),
                     justify="center").pack(pady=(8, 0))
        elif status == "gate":
            # El backend rechazÃ³ por reglas del Open Call (cupo, elegibilidad, cierre)
            tk.Label(frame, text="âš ", fg=YELLOW, bg=BG,
                     font=("Segoe UI", 34, "bold")).pack()
            tk.Label(frame, text="La subida no estÃ¡ habilitada.", fg=TEXT, bg=BG,
                     font=("Segoe UI", 12, "bold")).pack(pady=(8, 0))
            tk.Label(frame, text=msg or "Este contenido no entra en tus Ã³rdenes activas.",
                     fg=DIM, bg=BG, font=("Segoe UI", 10), justify="center",
                     wraplength=WIN_W - 60).pack(pady=(4, 0))
        else:
            tk.Label(frame, text="âœ—", fg=RED, bg=BG,
                     font=("Segoe UI", 34, "bold")).pack()
            tk.Label(frame, text="No se pudo subir la sesiÃ³n.", fg=TEXT, bg=BG,
                     font=("Segoe UI", 12, "bold")).pack(pady=(8, 0))
            # v0.8.5: mostrar el motivo real del servidor si vino (antes se
            # tragaba el msg y TODO error parecÃ­a "problema de conexiÃ³n" â€” bug QA)
            tk.Label(frame, text=msg or "RevisÃ¡ tu conexiÃ³n e intentÃ¡ de nuevo.",
                     fg=DIM, bg=BG, font=("Segoe UI", 10), justify="center",
                     wraplength=WIN_W - 60).pack(pady=(4, 0))

        tk.Frame(frame, bg=BG).pack(fill="both", expand=True)

        btns = tk.Frame(frame, bg=BG)
        btns.pack(fill="x")
        if status in ("ok", "already", "gate"):
            tk.Button(btns, text="Listo", fg="#fff", bg=ACCENT, relief="flat", bd=0,
                      cursor="hand2", font=("Segoe UI", 11, "bold"),
                      activebackground="#9080e0", command=return_to).pack(
                fill="x", ipady=10)
        else:
            tk.Button(btns, text="Volver", fg=DIM, bg=CARD, relief="flat", bd=0,
                      cursor="hand2", font=("Segoe UI", 11), activebackground=CARD2,
                      activeforeground=TEXT, command=return_to,
                      highlightthickness=1, highlightbackground=BORDER).pack(
                side="left", fill="x", expand=True, ipady=10, padx=(0, 6))
            tk.Button(btns, text="Reintentar", fg="#fff", bg=ACCENT, relief="flat",
                      bd=0, cursor="hand2", font=("Segoe UI", 11, "bold"),
                      activebackground="#9080e0",
                      command=lambda: self._upload_progress_view(
                          session_dir, return_to, call_id)).pack(
                side="right", fill="x", expand=True, ipady=10, padx=(6, 0))

    def _on_upload_auth_expired(self):
        self._clear_content()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)
        tk.Frame(frame, bg=BG).pack(fill="both", expand=True)
        tk.Label(frame, text="Tu sesiÃ³n venciÃ³.", fg=TEXT, bg=BG,
                 font=("Segoe UI", 13, "bold")).pack()
        tk.Label(frame, text="VolvÃ© a iniciar sesiÃ³n con tu email para subir la grabaciÃ³n.",
                 fg=DIM, bg=BG, font=("Segoe UI", 10), justify="center",
                 wraplength=WIN_W - 60).pack(pady=(6, 0))
        tk.Frame(frame, bg=BG).pack(fill="both", expand=True)
        def _relogin():
            self.logged_in  = False
            self.auth_token = ""
            save_auth("", "")
            self._signout_lbl.pack_forget()
            self._show_login()
        tk.Button(frame, text="Iniciar sesiÃ³n", fg="#fff", bg=ACCENT, relief="flat",
                  bd=0, cursor="hand2", font=("Segoe UI", 11, "bold"),
                  activebackground="#9080e0", command=_relogin).pack(fill="x", ipady=10)

    # â”€â”€ Lista de grabaciones (grabar varias, subir por separado) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _show_sessions_list(self):
        self._clear_content()
        self._set_back(self._show_idle)
        outer = tk.Frame(self.content, bg=BG)
        outer.pack(fill="both", expand=True)

        head = tk.Frame(outer, bg=BG, padx=22, pady=16)
        head.pack(fill="x")
        back = tk.Label(head, text="â†", fg=ACCENT, bg=BG, font=("Segoe UI", 16),
                        cursor="hand2")
        back.pack(side="left")
        back.bind("<Button-1>", lambda e: self._show_idle())
        tk.Label(head, text="  Mis grabaciones", fg=TEXT, bg=BG,
                 font=("Segoe UI", 14, "bold")).pack(side="left")

        canvas = tk.Canvas(outer, bg=BG, bd=0, highlightthickness=0)
        canvas.pack(side="top", fill="both", expand=True)
        lst = tk.Frame(canvas, bg=BG)
        lst_id = canvas.create_window((0, 0), window=lst, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(lst_id, width=e.width))
        lst.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        sessions = list_local_sessions()
        if not sessions:
            tk.Label(lst, text="No hay grabaciones todavÃ­a.", fg=DIM, bg=BG,
                     font=("Segoe UI", 11), pady=40).pack()
            return
        for sdir, state in sessions:
            self._session_row(lst, sdir, state)

    def _session_row(self, parent, sdir, state):
        card = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", padx=18, pady=5)
        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill="x", padx=12, pady=10)

        name = sdir.name.replace(" recording", "")
        tk.Label(inner, text=name, fg=TEXT, bg=CARD, font=("Segoe UI", 10, "bold"),
                 anchor="w", wraplength=WIN_W - 90, justify="left").pack(fill="x")

        meta = tk.Frame(inner, bg=CARD)
        meta.pack(fill="x", pady=(6, 0))
        badge = {
            "uploaded":   ("âœ“ Subida",   GREEN),
            "pending":    ("Pendiente",  YELLOW),
            "invalid":    ("No vÃ¡lida",  RED),
            "incomplete": ("Incompleta", DIMMER),
        }
        txt, col = badge.get(state.get("status"), ("â€”", DIMMER))
        tk.Label(meta, text=txt, fg=col, bg=CARD,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(meta, text=state.get("size_label", ""), fg=DIM, bg=CARD,
                 font=("Cascadia Code", 9)).pack(side="left", padx=(10, 0))

        if state.get("status") == "pending":
            tk.Button(meta, text="Subir", fg="#fff", bg=ACCENT, relief="flat", bd=0,
                      cursor="hand2", font=("Segoe UI", 9, "bold"),
                      activebackground="#9080e0",
                      command=lambda d=sdir: self._start_upload_flow(
                          d, self._show_sessions_list)).pack(side="right", ipady=2, ipadx=12)

    # â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    # â”€â”€ Navegacion (v0.9) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _set_back(self, destino=None):
        """Muestra el Atras y a donde vuelve. None lo oculta.

        No es una pila generica a proposito: cada pantalla declara su anterior.
        Una pila real se desincroniza con los saltos que hace el flujo de
        grabacion (auto-reinicio, errores, vuelta al inicio) y termina llevando
        al usuario a una pantalla que ya no aplica.
        """
        self._back_to = destino
        btn = getattr(self, "_back_btn", None)
        if btn is None:
            return
        try:
            if destino is None:
                btn.pack_forget()
            else:
                btn.pack(side="left", padx=(8, 0), before=btn.master.winfo_children()[1])
        except Exception:
            pass

    def _go_back(self):
        destino = getattr(self, "_back_to", None)
        if callable(destino):
            destino()

    def _clear_content(self):
        # v0.9: cortar el poll de deteccion al salir de la pantalla principal.
        # Si sigue vivo, el worker vuelve con un resultado y renderiza sobre
        # widgets ya destruidos.
        self._detect_stop()
        self._hide_dropdown()
        # Limpiar binding global de scroll (lo re-crea cada pantalla que lo use)
        try:
            self.content.unbind_all("<MouseWheel>")
        except Exception:
            pass
        # Cancelar animaciÃ³n de packaging si estÃ¡ corriendo
        if getattr(self, "_pkg_anim_id", None):
            try:
                self.root.after_cancel(self._pkg_anim_id)
            except Exception:
                pass
            self._pkg_anim_id = None
        for w in self.content.winfo_children():
            w.destroy()

    def _open_tutorial(self):
        """Abre el tutorial web (v0.8.4: reemplaza al wizard local de ventanas)."""
        try:
            import webbrowser
            webbrowser.open("https://recorder.gameplayalliance.gg/")
        except Exception as e:
            _obs_dbg(f"_open_tutorial: {e}")

    def _on_close(self):
        if self.recording:
            self._stop_recording()
        self.root.after(500, self.root.destroy)

    def run(self):
        self.root.mainloop()


# â”€â”€â”€ Entry point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

if __name__ == "__main__":
    _install_crash_logging()   # v0.7.1: captura crashes/ANR a %APPDATA%\Pleiada\logs

    # PLE-18: DPI awareness â€” evita que Windows clipee contenido en pantallas escaladas.
    # Debe llamarse ANTES de crear cualquier ventana Tk.
    try:
        import ctypes as _ct_dpi
        try:
            _ct_dpi.windll.shcore.SetProcessDpiAwareness(2)   # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:
            _ct_dpi.windll.user32.SetProcessDPIAware()        # fallback para Windows < 8.1

        # PLE-44: escalar WIN_W/WIN_H segÃºn el DPI del sistema para evitar textos
        # cortados en pantallas con escalado 125%/150%. Con DpiAwareness(2) el proceso
        # recibe pÃ­xeles fÃ­sicos, pero las fuentes en puntos escalan con el DPI â€”
        # sin este ajuste la ventana queda angosta relativa al tamaÃ±o de letra.
        _sys_dpi = _ct_dpi.windll.user32.GetDpiForSystem()
        if _sys_dpi and _sys_dpi != 96:
            _dpi_scale = _sys_dpi / 96.0
            WIN_W = int(420 * _dpi_scale)
            WIN_H = int(640 * _dpi_scale)
    except Exception:
        pass

    # PLE-38: Single-instance guard â€” impide abrir dos grabaciones en paralelo.
    # Usamos un Windows Named Mutex. Si ya existe, hay otra instancia corriendo.
    _mutex = None
    try:
        import ctypes as _ct2
        _mutex = _ct2.windll.kernel32.CreateMutexW(None, True, "PleiadaRecorderMutex_v031")
        _last_err = _ct2.windll.kernel32.GetLastError()
        if _last_err == 183:   # ERROR_ALREADY_EXISTS
            import tkinter as _tk2
            import tkinter.messagebox as _mb
            _r = _tk2.Tk(); _r.withdraw()
            _mb.showwarning(
                "Gameplay Recorder",
                "Gameplay Recorder ya estÃ¡ abierto.\n\nCerrÃ¡ la ventana existente antes de abrir una nueva."
            )
            _r.destroy()
            import sys as _sys2; _sys2.exit(0)
    except Exception:
        pass   # si falla el mutex, continuar igual (no bloquear el arranque)

    app = PleiadaApp()
    app.run()

    # Liberar mutex al salir
    if _mutex:
        try:
            import ctypes as _ct3
            _ct3.windll.kernel32.ReleaseMutex(_mutex)
            _ct3.windll.kernel32.CloseHandle(_mutex)
        except Exception:
            pass
