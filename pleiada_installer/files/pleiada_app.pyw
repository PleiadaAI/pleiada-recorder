"""
pleiada_app.pyw  —  Pleiada Recorder v0.3
Aplicación unificada: login, selección de juego, grabación, sync check, empaquetado.
"""

import tkinter as tk
from tkinter import font as tkfont
import json, os, sys, time, threading, subprocess, struct, glob, re, shutil, zipfile, io
import csv as _csv_mod, hashlib as _hashlib, platform as _platform
import ctypes, ctypes.wintypes
from pathlib import Path

# ─── Versión ──────────────────────────────────────────────────────────────────
VERSION = "v0.5.0"

# ─── Rutas ────────────────────────────────────────────────────────────────────
_frozen    = getattr(sys, "frozen", False)
APP_DIR    = Path(sys.executable).parent if _frozen else Path(__file__).parent
APPDATA    = Path(os.environ.get("APPDATA", Path.home()))
AUTH_FILE  = APPDATA / "Pleiada" / "auth.json"
SETTINGS_FILE = APPDATA / "Pleiada" / "settings.json"   # v0.5: hotkeys y prefs
GAMES_FILE = APP_DIR / "games_list.json"
GAMES_CACHE = APPDATA / "Pleiada" / "games_list_cache.json"   # v0.4: caché de Airtable
TEMP_DIR   = Path(os.environ.get("TEMP", "C:\\Temp"))
ANCHOR_FILE = TEMP_DIR / "pleiada_anchor_ts.txt"
GAME_FILE   = TEMP_DIR / "pleiada_game_name.txt"
BASE_DIR    = Path.home() / "Documents" / "Pleiada Recordings"
AHK_SCRIPT  = APP_DIR / "input_logger.ahk"

# ─── Design tokens ────────────────────────────────────────────────────────────
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

WIN_W, WIN_H = 420, 640
MAX_SECONDS  = 3900   # 1 h 5 min

# ─── Credenciales (login falso — v0.3) ────────────────────────────────────────

def load_auth():
    try:
        with open(AUTH_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_auth(email, remember):
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    if remember:
        with open(AUTH_FILE, "w", encoding="utf-8") as f:
            json.dump({"email": email, "remember": True}, f)
    else:
        AUTH_FILE.unlink(missing_ok=True)

def validate_login(email, password):
    return "@" in email and "." in email and len(password) >= 4

# ─── Settings / hotkeys (v0.5) ────────────────────────────────────────────────

# Hotkeys por defecto: F9 = iniciar, F10 = detener. Sin modificadores.
DEFAULT_SETTINGS = {
    "hotkey_start": {"vk": 0x78, "label": "F9"},
    "hotkey_stop":  {"vk": 0x79, "label": "F10"},
}

def load_settings():
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            s = json.load(f)
        # Completar claves faltantes con defaults
        out = json.loads(json.dumps(DEFAULT_SETTINGS))
        out.update({k: v for k, v in s.items() if k in DEFAULT_SETTINGS})
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

# Mapa keysym de Tkinter → (vk, label legible) para reasignar hotkeys.
# Cubre F1-F12, letras, dígitos y algunas teclas comunes.
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
    # Dígitos
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

# ─── Lista de juegos ──────────────────────────────────────────────────────────
#
# Fuente de verdad: base "Pleiada Games" en Airtable (dinámica, editable sin recompilar).
# Orden de prioridad al cargar:
#   1. games_list_cache.json (descargado de Airtable)
#   2. games_list.json bundleado en el installer (fallback final)
# El sync con Airtable corre en background al iniciar la app (sync_games_list).
#
# Token read-only (scope: data.records:read). Si se extrae del binario, solo puede
# leer la lista de juegos — no puede modificar ni borrar nada de la base.

AIRTABLE_TOKEN      = "patDpnvFjK67EiN0g.c56e7a6c69976db0a23bc0dd018f6bf77169a9d8f11a16aa14029c2c80eda165"
AIRTABLE_BASE_ID    = "appeyQ2C1DFa7e2HC"
AIRTABLE_GAMES_TID  = "tblrd5RYBLUmng4zF"
AIRTABLE_CONFIG_TID = "tblwzcB6aluMoJGPs"
GAMES_CACHE_TTL     = 86400   # 24 h — no chequear Airtable más seguido que esto

_games_cache = None

def load_games():
    """Carga la lista de juegos: caché de Airtable → fallback al JSON bundleado."""
    global _games_cache
    if _games_cache is not None:
        return _games_cache
    # 1. Intentar caché de Airtable
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
    """GET a la API de Airtable. Lanza excepción si falla."""
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
            if str(f.get("active", "")).lower() not in ("true", "1", "checked", ""):
                continue
            name = (f.get("Name") or "").strip()
            if not name:
                continue
            def _split(v):
                return [x.strip() for x in v.split(",") if x.strip()] if isinstance(v, str) else (v or [])
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
            })
        offset = page.get("offset")
        if not offset:
            break
    return games

def sync_games_list():
    """
    Sincroniza la lista de juegos con Airtable. Nunca lanza excepción.
    Actualiza GAMES_CACHE y el caché en memoria si hay una versión nueva.
    Llamar en un thread daemon al iniciar la app.
    """
    global _games_cache
    cached_version = None
    try:
        if GAMES_CACHE.exists():
            with open(GAMES_CACHE, encoding="utf-8") as f:
                c = json.load(f)
            cached_version = c.get("version")
            # Si el caché es reciente, no molestar a Airtable
            if time.time() - c.get("downloaded_at", 0) < GAMES_CACHE_TTL:
                return
    except Exception:
        pass

    remote_version = _airtable_remote_version()
    if remote_version is None:
        return  # offline o error — seguimos con lo que haya

    if remote_version == cached_version:
        # Sin cambios: solo refrescar el timestamp para respetar el TTL
        try:
            with open(GAMES_CACHE, encoding="utf-8") as f:
                c = json.load(f)
            c["downloaded_at"] = time.time()
            with open(GAMES_CACHE, "w", encoding="utf-8") as f:
                json.dump(c, f, ensure_ascii=False)
        except Exception:
            pass
        return

    # Versión nueva → descargar todo
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

def fuzzy_search(query, max_results=8):
    if not query or len(query) < 2:
        return []
    q = query.lower()
    games = load_games()
    results = [g for g in games if q in g["game"].lower()]
    # Exactos primero, luego starts-with, luego contains
    exact  = [g for g in results if g["game"].lower() == q]
    starts = [g for g in results if g["game"].lower().startswith(q) and g not in exact]
    rest   = [g for g in results if g not in exact and g not in starts]
    return (exact + starts + rest)[:max_results]

# ─── OBS helpers (inlined desde obs_control.py) ───────────────────────────────

import hashlib, base64, uuid, websocket

OBS_HOST     = "localhost"
OBS_PORT     = 4455
OBS_PASSWORD = ""

class OBSAuthError(RuntimeError):
    """OBS WebSocket rechazó la autenticación (contraseña activada en OBS)."""
    pass

def _obs_dbg(msg):
    try:
        log = TEMP_DIR / "pleiada_obs_debug.txt"
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

def _obs_title_matches(game_name, win_title):
    """True si el título de ventana de OBS corresponde al juego seleccionado.

    Estrategia (en orden):
    1. Substring bidireccional normalizado — cubre "FarCry®6Trial" vs "Far Cry 6"
       PLE-35: si el match es unidireccional (game_name ⊂ win_title), verificar que
       el contenido extra en win_title no sean version qualifiers → rechaza
       "Borderlands 3" vs "Borderlands 3 Definitive Edition".
    2. Al menos una palabra significativa del juego (≥ 2 chars) aparece en el título
    3. Sin datos o sin palabras → no bloquear (beneficio de la duda)

    Normalización: minúsculas + solo alfanuméricos (elimina ®, ©, ™, espacios, guiones, etc.)
    """
    # Palabras que indican una versión/edición específica del juego.
    # Si aparecen en el título de OBS pero NO en el nombre seleccionado → mismatch.
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
        return True   # sin datos → no bloquear

    # Substring bidireccional
    if a in b:
        return True   # win_title ⊆ game_name → OK siempre

    if b in a:
        # game_name ⊆ win_title — verificar que el extra no sea un version qualifier
        # Extraer palabras del win_title que NO están en el game_name normalizado
        extra_words = [_n(w) for w in win_title.split() if _n(w) not in b and len(_n(w)) >= 3]
        if any(w in _VERSION_QUALIFIERS for w in extra_words):
            return False   # PLE-35: versión diferente seleccionada
        return True

    # Palabras significativas del juego (≥ 2 chars normalizados) en el título de OBS
    words = [_n(w) for w in game_name.split() if len(_n(w)) >= 2]
    if not words:
        return True   # ninguna palabra verificable → no bloquear

    return any(w in a for w in words)

def obs_connect():
    ws = websocket.WebSocket()
    ws.connect(f"ws://{OBS_HOST}:{OBS_PORT}", timeout=5)
    hello = json.loads(ws.recv())
    auth_data = hello["d"].get("authentication")
    if not auth_data:
        ws.send(json.dumps({"op": 1, "d": {"rpcVersion": 1}}))
        json.loads(ws.recv())
        return ws
    # OBS tiene contraseña en el WebSocket — intentar autenticar con OBS_PASSWORD
    secret = base64.b64encode(
        hashlib.sha256((OBS_PASSWORD + auth_data["salt"]).encode()).digest()
    ).decode()
    auth_str = base64.b64encode(
        hashlib.sha256((secret + auth_data["challenge"]).encode()).digest()
    ).decode()
    ws.send(json.dumps({"op": 1, "d": {"rpcVersion": 1, "authentication": auth_str}}))
    # Si la contraseña es incorrecta OBS cierra la conexión sin responder (recv vacío)
    try:
        raw = ws.recv()
        if not raw:
            raise OBSAuthError()
        json.loads(raw)   # Identified — si llega acá, auth OK
    except OBSAuthError:
        try: ws.close()
        except: pass
        raise OBSAuthError(
            "OBS WebSocket tiene contraseña activada.\n"
            "Desactivala en: OBS → Herramientas → WebSocket Server Settings → "
            "desmarcá 'Enable Authentication'."
        )
    except Exception:
        try: ws.close()
        except: pass
        raise OBSAuthError(
            "OBS WebSocket tiene contraseña activada.\n"
            "Desactivala en: OBS → Herramientas → WebSocket Server Settings → "
            "desmarcá 'Enable Authentication'."
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
            stderr=subprocess.DEVNULL
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
    subprocess.Popen([obs, "--disable-shutdown-check"], cwd=obs_dir)
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
    """Devuelve el título de la ventana del juego configurado en OBS, o ''.
    Puede lanzar OBSAuthError si el WebSocket requiere contraseña."""
    ws = obs_connect()   # deja propagar OBSAuthError
    resp    = obs_send(ws, "GetInputList")
    inputs  = resp.get("d", {}).get("responseData", {}).get("inputs", [])
    gc_src  = next((i for i in inputs if i.get("inputKind") == "game_capture"), None)
    if not gc_src:
        ws.close(); return ""
    sr     = obs_send(ws, "GetInputSettings", {"inputName": gc_src["inputName"]})
    window = sr.get("d", {}).get("responseData", {}).get("inputSettings", {}).get("window", "")
    ws.close()
    return window.split(":")[0].strip() if window else ""

def obs_check_status():
    """Retorna (is_recording, win_title, wrong_source) en una sola conexión WebSocket.

    is_recording  : True si OBS está grabando ahora.
    win_title     : título de la ventana del Game Capture source ('' si no hay o no apunta a nada).
    wrong_source  : nombre legible del modo incorrecto si el usuario NO usa Game Capture
                    pero sí tiene otra fuente de captura activa (ej: "Captura de Pantalla").
                    None si todo está bien o si no hay ninguna fuente de captura.
    Puede lanzar OBSAuthError."""

    _WRONG_SOURCES = {
        "monitor_capture": "Captura de Pantalla",
        "screen_capture":  "Captura de Pantalla",
        "window_capture":  "Captura de Ventana",
    }

    ws = obs_connect()   # deja propagar OBSAuthError

    # ¿Está grabando?
    rec_resp     = obs_send(ws, "GetRecordStatus")
    is_recording = rec_resp.get("d", {}).get("responseData", {}).get("outputActive", False)

    # Fuentes de captura
    win_title    = ""
    win_match    = ""
    wrong_source = None
    try:
        resp   = obs_send(ws, "GetInputList")
        inputs = resp.get("d", {}).get("responseData", {}).get("inputs", [])

        # PLE-33: solo marcar fuente incompatible si está activa (enabled) en la escena actual
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
                # Game Capture encontrado — leer qué juego tiene configurado
                sr     = obs_send(ws, "GetInputSettings", {"inputName": gc_src["inputName"]})
                window = sr.get("d", {}).get("responseData", {}).get("inputSettings", {}).get("window", "")
                if window:
                    # Formato OBS: "WindowTitle:WindowClass:ExeName.exe"
                    # (el orden de class y exe varía según versión/tipo de fuente)
                    # Buscamos el componente que termina en .exe, sin importar posición.
                    parts     = window.split(":")
                    win_title = parts[0].strip()
                    exe_part  = ""
                    for _p in parts[1:]:
                        _p = _p.strip()
                        if _p.lower().endswith(".exe"):
                            exe_part = re.sub(r'\.exe$', '', _p, flags=re.IGNORECASE)
                            break
                    win_match = f"{win_title} {exe_part}".strip()
    except Exception:
        pass

    ws.close()
    return is_recording, win_title, win_match, wrong_source

def _obs_do_start():
    """Asume OBS ya está corriendo. Conecta, configura audio, envía StartRecord.
    Retorna True si la grabación arrancó, False si falló.
    Puede lanzar OBSAuthError si el WebSocket requiere contraseña."""
    ws = None
    try:
        ws = obs_connect()   # puede lanzar OBSAuthError — se deja propagar

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
        raise   # dejar que llegue a _launch_at_zero para mostrar mensaje específico
    except Exception as e:
        _obs_dbg(f"_obs_do_start: {e}")
        if ws:
            try: ws.close()
            except: pass
        return False

def obs_start_recording():
    """Lanza OBS si no está corriendo, luego inicia la grabación."""
    try:
        if not obs_is_running():
            if not launch_obs():
                return False
    except Exception as e:
        _obs_dbg(f"obs_start_recording launch check: {e}")
        return False
    return _obs_do_start()

def obs_stop_recording(session_dir=None):
    """Detiene la grabación en OBS y mueve el archivo al session_dir."""
    output_path = None
    session_start = (os.path.getmtime(str(session_dir))
                     if session_dir and session_dir.exists() else time.time() - 300)
    try:
        ws   = obs_connect()
        resp = obs_send(ws, "StopRecord")
        ws.close()
        output_path = resp.get("d", {}).get("responseData", {}).get("outputPath", "")
    except Exception as e:
        _obs_dbg(f"obs_stop_recording ws error: {e}")

    if not output_path or not os.path.isfile(output_path):
        time.sleep(2)
        vdir = Path.home() / "Videos"
        candidates = list(vdir.glob("*.mp4")) + list(vdir.glob("**/*.mp4"))
        recent = [f for f in candidates if f.stat().st_mtime >= session_start]
        if recent:
            output_path = str(max(recent, key=lambda f: f.stat().st_mtime))

    if output_path and os.path.isfile(output_path) and session_dir:
        dest = session_dir / Path(output_path).name
        for _ in range(20):
            try:
                shutil.move(output_path, dest)
                _obs_dbg(f"Video movido a: {dest}")
                return str(dest)
            except (PermissionError, OSError):
                time.sleep(0.5)
    return output_path or ""

# ─── Anchor timestamp (copiado de obs_control.py) ─────────────────────────────

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

# ─── AHK launcher ─────────────────────────────────────────────────────────────

_ahk_proc = None

def _find_ahk():
    local_app = os.environ.get("LOCALAPPDATA", "")
    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    candidates = [
        # Program Files — instalación system-wide
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

    # Búsqueda en PATH del sistema
    import shutil as _sh
    return _sh.which("AutoHotkey64") or _sh.which("AutoHotkey") or "AutoHotkey.exe"

def start_ahk_logger(log_dir_str, game_exe=""):
    """Lanza AHK con el directorio de sesión y (opcionalmente) el exe del juego.
    PLE-43/13: si se pasa game_exe, AHK solo registra inputs cuando ese proceso
    está en primer plano, evitando capturar inputs fuera del contexto de juego."""
    global _ahk_proc
    ahk  = _find_ahk()
    args = [ahk, str(AHK_SCRIPT), log_dir_str]
    if game_exe:
        args.append(game_exe)   # A_Args[2] en AHK — filtra por ventana activa
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

# ─── Sync checker (inlined desde pleiada_check.pyw) ───────────────────────────

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
    """True si el archivo MP4 está realmente truncado/corrupto.

    Estrategia: recorre los boxes top-level desde el byte 0 siguiendo
    tamaños reales. Esto evita el falso-positivo de buscar 'moov' en
    la mitad del payload del box 'mdat' (que puede ser de 100+ MB).
    Acepta el archivo si encuentra moov O moof (fragmented MP4 de OBS).
    """
    try:
        fsize = os.path.getsize(path)
        if fsize < 200:
            return True
        with open(path, 'rb') as f:
            pos = 0
            while pos + 8 <= fsize:
                f.seek(pos)
                raw = f.read(8)
                if len(raw) < 8:
                    break
                size  = struct.unpack('>I', raw[:4])[0]
                btype = raw[4:8]
                if btype in (b'moov', b'moof'):
                    return False          # archivo completo
                if size == 1:            # tamaño 64-bit
                    ext = f.read(8)
                    if len(ext) < 8:
                        break
                    size = struct.unpack('>Q', ext)[0]
                    if size < 16:
                        break
                elif size == 0:          # box hasta EOF
                    break
                elif size < 8:
                    break
                if pos + size > fsize:   # box declara más allá del EOF → truncado
                    break
                pos += size
        return True
    except Exception:
        return False

def _mp4_frag_duration_ms(path):
    """Duración real del MP4 en ms.

    Soporta ambos formatos que puede producir OBS:
    · MP4 estándar (moov al final): lee mdhd.duration directamente.
    · MP4 fragmentado (moof boxes):  acumula tfdt + trun sample durations.

    Portado desde pleiada_check.pyw v25.5 que resolvió definitivamente
    este problema.
    """
    try:
        fsize = os.path.getsize(path)

        with open(path, 'rb') as f:
            # 1. Localizar moov siguiendo la cadena de top-level boxes desde el
            #    byte 0. Es la única forma confiable cuando moov está al final de
            #    un mdat de cientos de MB: buscar desde un offset arbitrario dentro
            #    del payload del mdat produce tamaños basura y nunca llega a moov.
            moov_data = moov_end = None
            scan_pos = 0
            while scan_pos + 8 <= fsize:
                box_end, btype, data_start = _mp4_next_box(f, scan_pos, fsize)
                if box_end is None:
                    break
                if btype == b'moov':
                    moov_data, moov_end = data_start, box_end
                    break
                scan_pos = box_end
            if moov_data is None:
                return None   # sin moov → archivo truncado o formato desconocido

            # 2. Navegar moov → trak → mdia → mdhd para leer timescale y duration
            trak_d, trak_e = _mp4_find_box(f, moov_data, moov_end, b'trak')
            if not trak_d: return None
            mdia_d, mdia_e = _mp4_find_box(f, trak_d, trak_e, b'mdia')
            if not mdia_d: return None
            mdhd_d, _ = _mp4_find_box(f, mdia_d, mdia_e, b'mdhd')
            if not mdhd_d: return None

            f.seek(mdhd_d)
            version = struct.unpack('B', f.read(1))[0]
            f.read(3)                              # flags
            f.read(16 if version == 1 else 8)      # creation + modification time
            timescale = struct.unpack('>I', f.read(4))[0]
            if not timescale: return None

            # mdhd.duration: en MP4 estándar tiene la duración real;
            # en MP4 fragmentado suele ser 0 o el sentinel 0xFFFF…
            if version == 1:
                mdhd_dur = struct.unpack('>Q', f.read(8))[0]
            else:
                mdhd_dur = struct.unpack('>I', f.read(4))[0]
            sentinel = 0xFFFFFFFFFFFFFFFF if version == 1 else 0xFFFFFFFF
            if mdhd_dur and mdhd_dur != sentinel:
                return round(mdhd_dur / timescale * 1000)

            # 3. Fallback: MP4 fragmentado — acumular tfdt + trun sobre todos los moof
            last_end_time = 0
            pos = 0
            while pos < fsize:
                box_end, btype, data = _mp4_next_box(f, pos, fsize)
                if box_end is None: break
                if btype == b'moof':
                    traf_d, traf_e = _mp4_find_box(f, data, box_end, b'traf')
                    if traf_d:
                        # tfhd → default_sample_duration
                        default_dur = 0
                        tfhd_d, _ = _mp4_find_box(f, traf_d, traf_e, b'tfhd')
                        if tfhd_d:
                            f.seek(tfhd_d); f.read(1)
                            fl = f.read(3)
                            tfhd_flags = (fl[0] << 16) | (fl[1] << 8) | fl[2]
                            f.read(4)   # track_ID
                            if tfhd_flags & 0x000001: f.read(8)
                            if tfhd_flags & 0x000002: f.read(4)
                            if tfhd_flags & 0x000008:
                                default_dur = struct.unpack('>I', f.read(4))[0]
                        # tfdt → base_decode_time
                        base_dt = 0
                        tfdt_d, _ = _mp4_find_box(f, traf_d, traf_e, b'tfdt')
                        if tfdt_d:
                            f.seek(tfdt_d); tfdt_ver = struct.unpack('B', f.read(1))[0]
                            f.read(3)
                            base_dt = struct.unpack('>Q', f.read(8))[0] if tfdt_ver == 1 \
                                      else struct.unpack('>I', f.read(4))[0]
                        # trun → suma de duraciones de muestras
                        frag_dur = 0
                        trun_d, _ = _mp4_find_box(f, traf_d, traf_e, b'trun')
                        if trun_d:
                            f.seek(trun_d); f.read(1)
                            fl = f.read(3)
                            trun_flags = (fl[0] << 16) | (fl[1] << 8) | fl[2]
                            count = struct.unpack('>I', f.read(4))[0]
                            if trun_flags & 0x001: f.read(4)
                            if trun_flags & 0x004: f.read(4)
                            has_dur = bool(trun_flags & 0x100)
                            has_sz  = bool(trun_flags & 0x200)
                            has_fl  = bool(trun_flags & 0x400)
                            has_cts = bool(trun_flags & 0x800)
                            for _ in range(count):
                                frag_dur += struct.unpack('>I', f.read(4))[0] if has_dur else default_dur
                                if has_sz:  f.read(4)
                                if has_fl:  f.read(4)
                                if has_cts: f.read(4)
                        end_time = base_dt + frag_dur
                        if end_time > last_end_time:
                            last_end_time = end_time
                pos = box_end

        if last_end_time == 0:
            return None
        return round(last_end_time / timescale * 1000)

    except Exception:
        return None

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
        "short_session": False,   # PLE-41: True si la sesión fue < 30 s
    }

    csv_names   = ["mouse_log.csv", "mouse_delta_log.csv", "key_log.csv", "video_timeline.csv"]
    csv_anchors = []

    # — Pasos 0-3: verificar CSVs ——————————————————————
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

    # Duración CSV (media de los 4 archivos válidos)
    durations = [e - s for s, e in csv_anchors if s and e and e > s]
    csv_dur   = round(sum(durations) / len(durations)) if durations else None
    result["csv_dur"] = csv_dur
    result["csvs_ok"] = all_csv_ok

    # PLE-41: duración mínima — sesiones muy cortas producen diffs ~0 que pasan el check
    # incorrectamente aunque no haya juego grabado. Mínimo 30 segundos de sesión válida.
    _MIN_SESSION_MS = 30_000
    if csv_dur is not None and csv_dur < _MIN_SESSION_MS:
        if progress_cb:
            for _i in range(5):
                progress_cb(_i, "err")
        result["short_session"] = True
        result["session_ok"]    = False
        return result

    # — Paso 4: verificar video ————————————————————————
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

    # Comparar duración CSV vs video
    if csv_dur and video_dur:
        diff = video_dur - csv_dur
        result["signed_diff"] = diff
        # Tolerancias:
        #   +15 s: cubre anchor_fallback (WebSocket + AHK startup) en hw lento
        #   -4.5 s: cubre GOP parcial al final
        in_range = (-4500 <= diff <= 15000)
        result["video_ok"] = in_range
        if progress_cb: progress_cb(4, "ok" if in_range else "offset")
    else:
        result["video_ok"] = True
        if progress_cb: progress_cb(4, "ok")

    result["session_ok"] = result["csvs_ok"] and result["video_ok"]
    return result

# ─── Packager ─────────────────────────────────────────────────────────────────

def package_session(session_dir):
    """
    Crea un ZIP con todos los archivos de la sesión (sin cifrar).
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

# ─── Session metadata (v0.4) ─────────────────────────────────────────────────

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
    """Calcula Hz de muestreo de video_timeline y posición de mouse desde los CSVs."""
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
    Extrae resolución, FPS, codec, frame count y bitrate del MP4 vía OpenCV.
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

        # Bitrate promedio real = tamaño / duración
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
    """CPU, RAM, GPUs, resolución y refresh rate del monitor principal."""
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
    # GPUs via wmic (Windows 10/11, deprecado en 24H2 pero aún funcional)
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
    # Monitor — resolución
    try:
        hw["monitor_width"]  = ctypes.windll.user32.GetSystemMetrics(0)
        hw["monitor_height"] = ctypes.windll.user32.GetSystemMetrics(1)
    except Exception:
        hw["monitor_width"] = hw["monitor_height"] = None
    # Monitor — refresh rate via GetDeviceCaps(VREFRESH) — simple y confiable
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

# ── Fase 2: helpers de detección ─────────────────────────────────────────────

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
      2. ventana visible cuyo título matchee el de OBS o el nombre del juego  -> PID -> ruta
    Loguea el resultado para diagnóstico.
    """
    # 1. .exe expuesto por OBS en el window string ("Title:Class:exe")
    exe = next((p.strip() for p in (obs_window or "").split(":")
                if p.strip().lower().endswith(".exe")), "")
    if exe:
        path = _meta_exe_path(exe)
        if path:
            _obs_dbg(f"exe_path via OBS exe '{exe}': {path}")
            return path

    # 2. Buscar la ventana del juego por título y resolver su PID -> ruta
    obs_title = (obs_window or "").split(":")[0].strip()
    cands = [c for c in (obs_title, game_name) if c]
    if not cands:
        _obs_dbg(f"exe_path: sin candidatos de título (obs_window='{obs_window}')")
        return None

    def _n(s):
        return re.sub(r"[^a-z0-9]+", "", s.lower())
    cand_norm = [_n(c) for c in cands]

    result = {"pid": None}

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
            result["pid"] = pid.value
            return False
        return True

    try:
        ctypes.windll.user32.EnumWindows(_cb, 0)
    except Exception:
        pass

    if result["pid"]:
        path = _meta_pid_image_path(result["pid"])
        _obs_dbg(f"exe_path via window title (pid={result['pid']}): {path}")
        return path

    _obs_dbg(f"exe_path: no resuelto (obs_window='{obs_window}', game='{game_name}')")
    return None

def _meta_detect_engine(game_dir):
    """Detecta el motor del juego por firmas de archivos en el directorio de instalación."""
    if not game_dir or not os.path.isdir(game_dir):
        return None
    checks = [
        # (ruta relativa al game_dir, nombre del motor)
        # — orden importa: firmas más específicas primero —
        (os.path.join("Engine", "Binaries"),       "Unreal Engine"),
        (os.path.join("Engine", "Config"),         "Unreal Engine"),
        ("UnityPlayer.dll",                        "Unity"),
        # Source 2: estructura game/bin/win64 con engine2.dll (NO usar vscript.dll,
        # que también existe en Source 1 — daba falso positivo en Portal 2).
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

# ── Key mapping parsers ───────────────────────────────────────────────────────

_UE_KEY_MAP = {
    "SpaceBar": "Space", "LeftShift": "LShift", "RightShift": "RShift",
    "LeftControl": "LCtrl", "RightControl": "RCtrl",
    "LeftAlt": "LAlt", "RightAlt": "RAlt",
    "LeftMouseButton": "LButton", "RightMouseButton": "RButton",
    "MiddleMouseButton": "MButton",
    "MouseScrollUp": "WheelUp", "MouseScrollDown": "WheelDown",
}
# Mapeo EXACTO (action name en lowercase → semántica normalizada). Las acciones
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
        # Cámara (look/turn/yaw/pitch) ANTES que movimiento — "LookRight" contiene
        # "right" pero es cámara, no strafe.
        if "look" in al or "turn" in al or "yaw" in al or "pitch" in al:
            if "up" in al or "pitch" in al:
                mapping.setdefault(k, "look_up" if sc > 0 else "look_down")
            else:
                mapping.setdefault(k, "look_right" if sc > 0 else "look_left")
        elif "forward" in al or "backward" in al:
            mapping.setdefault(k, "move_forward" if sc > 0 else "move_backward")
        elif "right" in al or "left" in al or "strafe" in al:
            mapping.setdefault(k, "move_right" if sc > 0 else "move_left")

    # ── Formato 1: legacy +ActionMappings / +AxisMappings ─────────────────────
    legacy = False
    for m in re.finditer(r'\+ActionMappings=\(ActionName="([^"]+)".*?Key=([^,)]+)', content):
        legacy = True
        _add_action(m.group(1), m.group(2).strip())
    for m in re.finditer(r'\+AxisMappings=\(AxisName="([^"]+)".*?Scale=([^,]+).*?Key=([^,)]+)', content):
        legacy = True
        _add_axis(m.group(1), m.group(2), m.group(3).strip())

    # ── Formato 2: custom UserActionMappings / UserAxisMappings (Icarus, etc.) ─
    if not legacy:
        for m in re.finditer(r'ActionName="([^"]+)",Key=(\w+)', content):
            _add_action(m.group(1), m.group(2))
        for m in re.finditer(r'AxisName="([^"]+)"(?:,Scale=(-?[\d.]+))?,Key=(\w+)', content):
            _add_axis(m.group(1), m.group(2), m.group(3))

    return mapping

# ── Búsqueda amplia del juego en cualquier disco (Steam libraries) ────────────

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
    """Busca la carpeta de instalación del juego en todas las Steam libraries."""
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
                if en and (en == target or target in en or en in target):
                    return os.path.join(common, entry)
        except Exception:
            pass
    return None

def _meta_unreal_key_mapping(game_dir, game_name=""):
    """
    Busca key mapping de un juego Unreal Engine:
    1. Input.ini del usuario en %LOCALAPPDATA%\\{Game}\\... → binding_source: 'config'
       (matchea la carpeta por nombre del juego; %LOCALAPPDATA% no depende del disco)
    2. DefaultInput.ini del juego (en install dir, cualquier disco) → 'default'
    """
    def _n(s):
        return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

    # ── Paso 1: Input.ini del usuario ─────────────────────────────────────────
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        candidates = glob.glob(os.path.join(
            local, "*", "Saved", "Config", "WindowsNoEditor", "Input.ini"))
        # también UE5: WindowsClient / Windows
        candidates += glob.glob(os.path.join(
            local, "*", "Saved", "Config", "Windows*", "Input.ini"))
        candidates = list(dict.fromkeys(candidates))
        ini = None
        if candidates:
            # 1a. matchear por nombre del juego
            gn = _n(game_name)
            if gn:
                ini = next((c for c in candidates
                            if gn in _n(c.split(os.sep + "Saved")[0])), None)
            # 1b. matchear por carpeta derivada del install dir
            if not ini and game_dir:
                gdn = _n(os.path.basename(os.path.dirname(os.path.dirname(game_dir))))
                ini = next((c for c in candidates if gdn and gdn in _n(c)), None)
            # 1c. el más reciente
            if not ini:
                ini = max(candidates, key=os.path.getmtime)
        if ini and os.path.isfile(ini):
            mapping = _parse_ue_input_ini(ini)
            if mapping:
                _obs_dbg(f"unreal key mapping: config usuario {ini} ({len(mapping)} binds)")
                return mapping, "config"

    # ── Paso 2: DefaultInput.ini del juego (install dir, cualquier disco) ──────
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
    # Tokens de teclas de gamepad/controller — se excluyen del key_mapping de
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
                    # Filtrar binds de gamepad — solo teclado y mouse
                    if any(tok in key for tok in _GAMEPAD_TOKENS):
                        continue
                    sem = _SOURCE_SEM.get(cmd)
                    if sem:
                        mapping[key] = sem
        return (mapping, "config") if mapping else (None, "unknown")
    except Exception:
        return None, "unknown"

def _meta_infer_key_mapping(session_dir):
    """
    Infiere el key mapping de las teclas/botones realmente usados en la sesión
    + convención FPS/acción. Fallback cuando no se encuentra el config del juego.
    Retorna (mapping, keys_observed).
    """
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

    conv = {
        "w": "move_forward", "a": "move_left", "s": "move_backward", "d": "move_right",
        "space": "jump", "shift": "sprint", "control": "crouch", "ctrl": "crouch",
        "c": "crouch_toggle", "alt": "walk", "e": "interact", "r": "reload",
        "f": "use_or_flashlight", "q": "lean_or_ability", "v": "melee", "g": "throw_grenade",
        "tab": "inventory", "i": "inventory", "b": "build_menu", "j": "journal",
        "escape": "pause_menu", "1": "hotbar_1", "2": "hotbar_2", "3": "hotbar_3",
        "4": "hotbar_4", "5": "hotbar_5",
    }
    mouse_conv = {"LEFT": "attack_primary", "RIGHT": "aim_or_secondary",
                  "MIDDLE": "special", "X1": "extra_1", "X2": "extra_2"}
    mapping = {}
    for k in keys:
        if k.lower() in conv:
            mapping[k] = conv[k.lower()]
    for b in mouse:
        if b.upper() in mouse_conv:
            mapping[f"Mouse{b.capitalize()}"] = mouse_conv[b.upper()]
    keys_observed = {"keyboard": dict(keys.most_common()),
                     "mouse_buttons": dict(mouse.most_common())}
    return mapping, keys_observed

def _meta_key_mapping(exe_path, engine, game_name=""):
    """
    Dispatcher de key mapping. SIEMPRE intenta primero el config REAL del juego
    (Source: config.cfg / Unreal: Input.ini), buscándolo en cualquier disco.
    La inferencia del gameplay queda como fallback (se hace fuera, en build_session_metadata).
    """
    game_dir = os.path.dirname(exe_path) if exe_path else None
    eng = (engine or "").lower()
    if "unreal" in eng:
        return _meta_unreal_key_mapping(game_dir, game_name)
    elif "source" in eng:
        return _meta_source_key_mapping(game_dir, game_name)
    return None, "unknown"  # Unity y otros: sin parser → se infiere del gameplay


def build_session_metadata(session_dir, selected_game, sync_results, exe_path=""):
    """
    Escribe session_metadata.json en session_dir.
    Llamar después de run_sync_check(), antes de package_session().
    Solo escribe un archivo nuevo — no modifica ningún CSV ni el video.
    Falla silenciosamente.
    """
    try:
        start_ms, end_ms = _meta_csv_anchors(session_dir)
        duration_ms = (end_ms - start_ms) if (start_ms and end_ms) else None

        # Detectar si el anchor fue moof2 o fallback (fallback tiende a ser múltiplo de 1000)
        anchor_method    = "moof2"
        anchor_precision = 50
        if start_ms and (start_ms % 1000 < 10 or start_ms % 1000 > 990):
            anchor_method    = "fallback_system_time"
            anchor_precision = 1000

        # IDs anónimos
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

        # Fase 2 — detección activa
        game_dir     = os.path.dirname(exe_path) if exe_path else None
        engine_local = _meta_detect_engine(game_dir)
        engine_igdb  = game.get("engine")
        engine       = engine_local or engine_igdb
        engine_source = ("detected" if engine_local
                         else "igdb" if engine_igdb else None)
        game_version = _meta_game_version(exe_path)
        # Key mapping: SIEMPRE intentar primero el config REAL del juego (cualquier disco).
        key_map, binding_src = _meta_key_mapping(exe_path, engine, game.get("game", ""))
        keys_observed = None
        # Fallback: si no se encontró el config real, inferir del gameplay de la sesión.
        if not key_map:
            key_map, keys_observed = _meta_infer_key_mapping(session_dir)
            binding_src = "inferred_from_gameplay" if key_map else "unknown"
        # window_mode: usar el exe realmente resuelto (Airtable process_name suele ser null)
        _proc_for_window = (os.path.basename(exe_path) if exe_path
                            else game.get("process_name", ""))
        window_mode  = _meta_window_mode(_proc_for_window)
        sys_lang     = _meta_system_language()

        metadata = {
            "schema_version":   "1.0",
            "session_id":       session_id,
            "source_id":        source_id,
            "recorder_version": VERSION,
            "recording_mode":   "manual",

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
                # keys_observed solo se incluye cuando el mapping fue inferido
                **({"keys_observed": keys_observed} if keys_observed else {}),
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
                "frames_dropped": None,  # Fase 3
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
            },

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
        }

        out = session_dir / "session_metadata.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        _obs_dbg(f"session_metadata.json escrito en {out}")

    except Exception as e:
        _obs_dbg(f"build_session_metadata error: {e}")


# ─── Widgets helpers ──────────────────────────────────────────────────────────

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

# ─── App principal ────────────────────────────────────────────────────────────

class PleiadaApp:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pleiada Recorder")
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

        # Ícono de la ventana (alt-tab, barra de tareas)
        _ico = APP_DIR / "pleiada.ico"
        if _ico.exists():
            try:
                self.root.wm_iconbitmap(str(_ico))
            except Exception:
                pass

        # Forzar aparición en barra de tareas (overrideredirect=True la oculta por defecto)
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

        # Estado de la sesión
        self.logged_in     = False
        self.user_email    = ""
        self.selected_game = None   # dict con game/perspective/genre/mode
        self.session_dir   = None   # Path
        self.recording     = False
        self.rec_seconds   = 0
        self._timer_id     = None
        self._cd_timer_id  = None   # countdown pre-grabación
        self._pending_anchor = None  # anchor refinado en background durante countdown
        self._obs_prep     = ("", set())  # (rec_dir_str, existing_vids) preparado antes del countdown
        self._pkg_anim_id  = None   # after-id de la animación de packaging
        self._we_stopped   = False  # True cuando NOSOTROS detenemos OBS (para ignorar el evento)
        self._recording_exe      = ""   # PLE-37: exe del juego capturado (ej: "Borderlands3.exe")
        self._recording_exe_path = ""   # v0.4 Fase 2: ruta completa del exe (para metadata)
        self._ahk_proc     = None
        self._dropdown_win      = None
        self._obs_status        = "idle"   # idle | checking | ok | warn | err
        self._last_sync_statuses = {}      # key → "ok"/"err"/"missing"/"truncated"/"offset"

        # v0.5: settings + hotkeys globales
        self._settings        = load_settings()
        self._hotkey_running  = True
        self._capturing_hotkey = None   # "start"/"stop" cuando se reasigna un atajo

        self._build_window()
        # v0.4: sincronizar lista de juegos con Airtable en background (no bloquea el arranque)
        threading.Thread(target=sync_games_list, daemon=True).start()
        # v0.5: listener de hotkeys globales (iniciar/detener grabación sin foco)
        threading.Thread(target=self._hotkey_listener, daemon=True).start()
        self._check_auto_login()

    # ── Construcción de la ventana ─────────────────────────────────────────────

    def _build_window(self):
        """Frame raíz: borde 1px + contenido."""
        outer = tk.Frame(self.root, bg=BORDER2, bd=0)
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        self._build_titlebar(outer)
        _mk_separator(outer, color=BORDER2)

        self.content = tk.Frame(outer, bg=BG)
        self.content.pack(fill="both", expand=True)

    def _build_titlebar(self, parent):
        tb = tk.Frame(parent, bg=BG2, height=38)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        # Logo mark (✦)
        tk.Label(tb, text="✦", fg=ACCENT, bg=BG2,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(14, 0), pady=8)

        # Título + versión
        tk.Label(tb, text="Pleiada Recorder", fg=TEXT, bg=BG2,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(6, 2))
        tk.Label(tb, text=VERSION, fg=DIM, bg=BG2,
                 font=("Segoe UI", 9)).pack(side="left")

        # Botón cerrar (macOS-style dot)
        close_btn = tk.Label(tb, text="", bg="#3a2a3e", width=2,
                             cursor="hand2", relief="flat")
        close_btn.pack(side="right", padx=(0, 12), pady=12)
        close_btn.bind("<Button-1>", lambda e: self._on_close())
        close_btn.bind("<Enter>",  lambda e: close_btn.config(text="×", fg="#ff5f57"))
        close_btn.bind("<Leave>",  lambda e: close_btn.config(text="", fg=BG))

        # Botón "Cerrar sesión" (visible solo cuando logueado)
        self._signout_lbl = tk.Label(tb, text="Cerrar sesión", fg=DIM, bg=BG2,
                                      font=("Segoe UI", 10), cursor="hand2")
        self._signout_lbl.pack(side="right", padx=(0, 14))
        self._signout_lbl.bind("<Button-1>", lambda e: self._sign_out())
        self._signout_lbl.bind("<Enter>",  lambda e: self._signout_lbl.config(fg=TEXT))
        self._signout_lbl.bind("<Leave>",  lambda e: self._signout_lbl.config(fg=DIM))
        self._signout_lbl.pack_forget()  # oculto hasta login

        # Sep vertical antes de close dot
        tk.Frame(tb, bg=BORDER2, width=1, height=16).pack(side="right", pady=11)

        # v0.5: ícono de Settings (⚙)
        self._settings_btn = tk.Label(tb, text="⚙", fg=DIM, bg=BG2,
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

    def _drag_move(self, e):
        x = e.x_root - self._drag_x
        y = e.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ── Login ──────────────────────────────────────────────────────────────────

    def _check_auto_login(self):
        auth = load_auth()
        if auth and auth.get("remember") and auth.get("email"):
            self.logged_in  = True
            self.user_email = auth["email"]
            _uname = auth["email"].split('@')[0]
            _uname = (_uname[:20] + "…") if len(_uname) > 20 else _uname  # PLE-36
            self._signout_lbl.config(text=f"  {_uname}  ✕")
            self._signout_lbl.pack(side="right", padx=(0, 14))
            self._show_idle()
        else:
            self._show_login()

    def _show_login(self):
        self._clear_content()
        self._signout_lbl.pack_forget()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=36, pady=0)

        # Espaciador superior
        tk.Frame(frame, bg=BG, height=30).pack()

        # Logo area
        tk.Label(frame, text="✦", fg=ACCENT, bg=BG,
                 font=("Segoe UI", 28)).pack()
        tk.Label(frame, text="Pleiada Recorder", fg=TEXT, bg=BG,
                 font=("Segoe UI", 17, "bold")).pack(pady=(10, 0))
        tk.Label(frame, text="Gameplay Alliance — sesión de grabación", fg=DIM, bg=BG,
                 font=("Segoe UI", 11)).pack(pady=(4, 32))

        # Email
        tk.Label(frame, text="EMAIL", fg=DIM, bg=BG,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", pady=(0, 5))
        email_var = tk.StringVar()
        email_entry = tk.Entry(frame, textvariable=email_var, bg=CARD, fg=TEXT,
                               insertbackground=ACCENT, relief="flat",
                               font=("Segoe UI", 12), bd=0)
        email_entry.pack(fill="x", ipady=10)
        _mk_separator(frame, color=BORDER, height=1, pady=0)

        tk.Frame(frame, bg=BG, height=14).pack()

        # Password
        tk.Label(frame, text="CONTRASEÑA", fg=DIM, bg=BG,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", pady=(0, 5))
        pwd_var = tk.StringVar()
        pwd_entry = tk.Entry(frame, textvariable=pwd_var, bg=CARD, fg=TEXT,
                             insertbackground=ACCENT, show="●", relief="flat",
                             font=("Segoe UI", 12), bd=0)
        pwd_entry.pack(fill="x", ipady=10)
        _mk_separator(frame, color=BORDER, height=1, pady=0)

        tk.Frame(frame, bg=BG, height=12).pack()

        # Remember me — custom toggle (Checkbutton nativo no funciona bien en dark theme)
        remember_var  = tk.BooleanVar(value=True)
        rem_frame     = tk.Frame(frame, bg=BG)
        rem_frame.pack(fill="x", pady=(4, 18))

        rem_box_lbl = tk.Label(rem_frame, text="✓", width=2,
                                font=("Segoe UI", 10, "bold"),
                                fg="#fff", bg=ACCENT, cursor="hand2",
                                relief="flat")
        rem_box_lbl.pack(side="left")
        rem_txt_lbl = tk.Label(rem_frame, text="  Mantenerme conectado",
                                fg=TEXT, bg=BG, font=("Segoe UI", 11),
                                cursor="hand2")
        rem_txt_lbl.pack(side="left")

        def _toggle_remember(e=None):
            remember_var.set(not remember_var.get())
            if remember_var.get():
                rem_box_lbl.config(text="✓", bg=ACCENT, fg="#fff")
            else:
                rem_box_lbl.config(text="", bg=CARD, fg=DIM)

        rem_box_lbl.bind("<Button-1>", _toggle_remember)
        rem_txt_lbl.bind("<Button-1>", _toggle_remember)

        # Error label
        err_lbl = tk.Label(frame, text="", fg=RED, bg=BG, font=("Segoe UI", 10))
        err_lbl.pack(pady=(0, 6))

        # Login button
        def on_login():
            email = email_var.get().strip()
            pwd   = pwd_var.get()
            if not validate_login(email, pwd):
                err_lbl.config(text="Email o contraseña inválidos.")
                return
            self.logged_in  = True
            self.user_email = email
            save_auth(email, remember_var.get())
            _uname = email.split('@')[0]
            _uname = (_uname[:20] + "…") if len(_uname) > 20 else _uname  # PLE-36
            self._signout_lbl.config(text=f"  {_uname}  ✕")
            self._signout_lbl.pack(side="right", padx=(0, 14))
            self._show_idle()

        btn = tk.Button(frame, text="Entrar", fg="#fff", bg=ACCENT,
                         relief="flat", bd=0, cursor="hand2",
                         font=("Segoe UI", 12, "bold"),
                         activebackground="#9080e0", activeforeground="#fff",
                         command=on_login)
        btn.pack(fill="x", ipady=12)

        email_entry.bind("<Return>", lambda e: pwd_entry.focus())
        pwd_entry.bind("<Return>",   lambda e: on_login())
        email_entry.focus()

    def _sign_out(self):
        if self.recording:
            return  # no sign out during recording
        self.logged_in  = False
        self.user_email = ""
        self.selected_game = None
        save_auth("", False)
        self._signout_lbl.pack_forget()
        self._show_login()

    # ── Settings (v0.5) ────────────────────────────────────────────────────────

    def _show_settings(self):
        if self.recording:
            return  # no abrir settings durante la grabación
        if not self.logged_in:
            return  # settings solo con sesión iniciada
        self._capturing_hotkey = None
        self._clear_content()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)

        _mk_section_label(frame, "AJUSTES")

        # — Versión —
        vrow = tk.Frame(frame, bg=BG)
        vrow.pack(fill="x", pady=(2, 0))
        tk.Label(vrow, text="Versión:", fg=DIM, bg=BG,
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Label(vrow, text=f"  {VERSION}", fg=TEXT, bg=BG,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(vrow, text="✓ Actualizado", fg=GREEN, bg=BG,
                 font=("Segoe UI", 9)).pack(side="right")

        _mk_separator(frame, color=BORDER2, pady=(14, 12))

        # — Atajos de teclado —
        _mk_section_label(frame, "ATAJOS DE TECLADO")
        self._hotkey_btns = {}
        for key, label in (("hotkey_start", "Iniciar grabación"),
                           ("hotkey_stop",  "Detener grabación")):
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
        tk.Label(frame, text="Hacé clic en un atajo y presioná la nueva tecla.\n"
                              "Los atajos funcionan aunque la ventana no esté en foco.",
                 fg=DIM, bg=BG, font=("Segoe UI", 9), justify="left",
                 wraplength=WIN_W - 60, anchor="w").pack(fill="x", pady=(8, 0))

        _mk_separator(frame, color=BORDER2, pady=(14, 12))

        # — Cuenta —
        _mk_section_label(frame, "CUENTA")
        tk.Label(frame, text=self.user_email or "—", fg=DIM, bg=BG,
                 font=("Segoe UI", 10), anchor="w").pack(fill="x")
        tk.Button(frame, text="Cerrar sesión", fg=TEXT, bg=CARD,
                  relief="flat", bd=0, cursor="hand2",
                  font=("Segoe UI", 10), activebackground=CARD2,
                  activeforeground=TEXT, command=self._sign_out,
                  highlightthickness=1, highlightbackground=BORDER).pack(
            fill="x", ipady=8, pady=(8, 0))

        # spacer + Volver
        tk.Frame(frame, bg=BG).pack(fill="both", expand=True)
        tk.Button(frame, text="←  Volver", fg=DIM, bg=BG,
                  relief="flat", bd=0, cursor="hand2",
                  font=("Segoe UI", 10), activebackground=BG,
                  activeforeground=TEXT, command=self._show_idle).pack(
            fill="x", ipady=8)

    def _begin_capture_hotkey(self, key):
        """Entra en modo captura: el próximo KeyPress define el atajo."""
        self._capturing_hotkey = key
        btn = self._hotkey_btns[key]
        btn.config(text="Presioná una tecla…", fg=YELLOW)
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
            # tecla no soportada → restaurar
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
        """Thread daemon: detecta los hotkeys globales vía GetAsyncKeyState.
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
        # Solo si hay sesión, juego seleccionado, OBS ok y no grabando
        if self.recording or not self.logged_in:
            return
        if self.selected_game and self._obs_status == "ok":
            self._start_recording()

    def _hotkey_stop(self):
        if self.recording:
            self._stop_recording()

    # ── Pantalla Idle (selector de juego) ──────────────────────────────────────

    def _show_idle(self):
        self._clear_content()
        self.selected_game = None
        self._obs_status   = "idle"

        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)

        # — Sección: Juego ————————————————————————————
        _mk_section_label(frame, "JUEGO A GRABAR")

        # Selector container (relativo para dropdown)
        sel_outer = tk.Frame(frame, bg=CARD, bd=0, relief="flat",
                             highlightthickness=1, highlightbackground=BORDER)
        sel_outer.pack(fill="x")

        sel_inner = tk.Frame(sel_outer, bg=CARD)
        sel_inner.pack(fill="x", padx=14, pady=0)

        search_lbl = tk.Label(sel_inner, text="⌕", fg=DIM, bg=CARD,
                               font=("Segoe UI", 13))
        search_lbl.pack(side="left", pady=12)

        self._search_var = tk.StringVar()
        self._search_entry = tk.Entry(sel_inner, textvariable=self._search_var,
                                       bg=CARD, fg=TEXT, insertbackground=ACCENT,
                                       relief="flat", bd=0, font=("Segoe UI", 12),
                                       highlightthickness=0)
        self._search_entry.pack(side="left", fill="x", expand=True, pady=12, padx=(6, 0))

        self._chevron_lbl = tk.Label(sel_inner, text="⌄", fg=DIM, bg=CARD,
                                      font=("Segoe UI", 10))
        self._chevron_lbl.pack(side="right")

        # Game tag (visible al seleccionar)
        self._game_tag_lbl = tk.Label(sel_inner, text="", fg=ACCENT, bg=CARD,
                                       font=("Segoe UI", 8, "bold"))
        self._game_tag_lbl.pack(side="right", padx=(0, 6))

        # Hint debajo del selector
        self._hint_frame = tk.Frame(frame, bg=BG)
        self._hint_frame.pack(fill="x", pady=(8, 0))
        self._hint_lbl = tk.Label(self._hint_frame, text="Escribí el nombre del juego para buscar.",
                                   fg=DIM, bg=BG, font=("Segoe UI", 10), anchor="w")
        self._hint_lbl.pack(side="left")

        # Dropdown de resultados
        self._dropdown_var  = tk.StringVar()
        self._dropdown_data = []  # lista de game dicts
        self._dropdown_visible = False
        self._search_var.trace_add("write", self._on_search_changed)
        self._search_entry.bind("<FocusIn>",  self._on_search_focus)
        self._search_entry.bind("<FocusOut>", lambda e: self.root.after(150, self._hide_dropdown))
        self._search_entry.bind("<Down>",  lambda e: self._dropdown_focus(1))
        self._search_entry.bind("<Up>",    lambda e: self._dropdown_focus(-1))
        self._search_entry.bind("<Return>", lambda e: self._select_dropdown_item())
        self._search_entry.bind("<Escape>", lambda e: self._hide_dropdown())

        # OBS status
        self._obs_frame = tk.Frame(frame, bg=BG)
        self._obs_frame.pack(fill="x", pady=(14, 0))
        self._obs_dot = tk.Label(self._obs_frame, text="●", fg=DIMMER, bg=BG,
                                  font=("Segoe UI", 10))
        self._obs_dot.pack(side="left")
        self._obs_lbl = tk.Label(self._obs_frame, text="Seleccioná un juego para verificar OBS.",
                                  fg=DIM, bg=BG, font=("Segoe UI", 10), anchor="w",
                                  wraplength=WIN_W - 60)
        self._obs_lbl.pack(side="left", padx=(6, 0), fill="x", expand=True)

        # Warn box (mismatch)
        self._warn_frame = tk.Frame(frame, bg="#1a1500",
                                     highlightthickness=1,
                                     highlightbackground="#7a5c16",
                                     bd=0)
        self._warn_ico = tk.Label(self._warn_frame, text="⚠", fg=YELLOW, bg="#1a1500",
                                   font=("Segoe UI", 11))
        self._warn_ico.pack(side="left", padx=(10, 0), pady=10)
        self._warn_txt = tk.Label(self._warn_frame, text="", fg="#f5d77a", bg="#1a1500",
                                   font=("Segoe UI", 10), wraplength=WIN_W - 100, justify="left",
                                   anchor="w")
        self._warn_txt.pack(side="left", padx=(8, 10), pady=10)
        # warn_frame initially hidden

        # — Separador ————————————————————————————————
        tk.Frame(frame, bg=BORDER2, height=1).pack(fill="x", pady=(0, 0))

        # — Sección: Sesión ————————————————————————————
        session_row = tk.Frame(frame, bg=BG)
        session_row.pack(fill="x", pady=(14, 0))
        tk.Label(session_row, text="SESIÓN MÁX", fg=DIM, bg=BG,
                  font=("Segoe UI", 8, "bold"), anchor="w").pack(side="left")
        tk.Label(session_row, text="01:05:00", fg=TEXT, bg=BG,
                  font=("Cascadia Code", 11), anchor="e").pack(side="right")

        # spacer
        tk.Frame(frame, bg=BG).pack(fill="both", expand=True)

        # — Botón Iniciar ————————————————————————————
        self._rec_btn_idle = tk.Button(
            frame, text="  Iniciar grabación", fg=DIMMER, bg=CARD,
            relief="flat", bd=0, cursor="arrow",
            font=("Segoe UI", 12, "bold"),
            activebackground=CARD, activeforeground=DIMMER,
            state="disabled", command=self._start_recording
        )
        self._rec_btn_idle.pack(fill="x", ipady=14, pady=(0, 2))
        self._update_record_btn()

        # — Footer ————————————————————————————————————
        _mk_separator(frame, color=BORDER2, pady=(12, 0))
        footer = tk.Frame(frame, bg=BG)
        footer.pack(fill="x", pady=(10, 0))
        tk.Label(footer, text="SESIÓN", fg=DIM, bg=BG,
                  font=("Segoe UI", 8, "bold"), anchor="w").pack(side="left")
        tk.Label(footer, text="No iniciada", fg=DIMMER, bg=BG,
                  font=("Cascadia Code", 10), anchor="e").pack(side="right")

        # — Link tutorial ————————————————————————————
        tutorial_lbl = tk.Label(frame, text="Ver tutorial de configuración ↗",
                                 fg=DIMMER, bg=BG, font=("Segoe UI", 9),
                                 cursor="hand2", anchor="w")
        tutorial_lbl.pack(fill="x", pady=(6, 0))
        tutorial_lbl.bind("<Enter>", lambda e: tutorial_lbl.config(fg=ACCENT))
        tutorial_lbl.bind("<Leave>", lambda e: tutorial_lbl.config(fg=DIMMER))
        tutorial_lbl.bind("<Button-1>", lambda e: self._open_tutorial())

        # Posicionar dropdown al hacer click
        sel_outer.bind("<Button-1>", lambda e: self._search_entry.focus())

        self._idle_frame = frame
        self._sel_outer  = sel_outer

    def _on_search_focus(self, e=None):
        self._sel_outer.config(highlightbackground=ACCENT)
        self._on_search_changed()

    def _on_search_changed(self, *args):
        q = self._search_var.get()
        # Si el usuario modificó el texto y había un juego seleccionado → deseleccionar
        if self.selected_game and q != self.selected_game["game"]:
            self.selected_game = None
            self._chevron_lbl.config(text="⌄", fg=DIM, cursor="")
            self._chevron_lbl.unbind("<Button-1>")
            self._game_tag_lbl.config(text="")
            self._hint_lbl.config(text="Escribí el nombre del juego para buscar.", fg=DIM)
            self._obs_dot.config(fg=DIMMER)
            self._obs_lbl.config(text="Seleccioná un juego para verificar OBS.", fg=DIM)
            self._warn_frame.pack_forget()
            self._obs_status = "idle"
            self._update_record_btn()
        if len(q) < 2:
            self._hide_dropdown()
            return
        results = fuzzy_search(q)
        if results:
            self._show_dropdown(results)
        else:
            self._show_no_results()

    def _show_dropdown(self, results):
        self._hide_dropdown()
        self._dropdown_data = results

        # Crear Toplevel relativo a la ventana principal
        dd = tk.Toplevel(self.root)
        dd.overrideredirect(True)
        dd.configure(bg=CARD2)
        self._dropdown_win = dd

        # Calcular posición
        self.root.update_idletasks()
        rx  = self.root.winfo_rootx()
        ry  = self.root.winfo_rooty()
        sx  = self._sel_outer.winfo_x()
        sy  = self._sel_outer.winfo_y()
        sw  = self._sel_outer.winfo_width()
        # relative to content → add titlebar height
        y_off = self._sel_outer.winfo_rooty() + self._sel_outer.winfo_height() + 4

        dd.geometry(f"{sw}x1+{rx + sx}+{y_off}")

        outer = tk.Frame(dd, bg=CARD2, bd=1, relief="solid",
                          highlightthickness=1, highlightbackground=BORDER)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text="RESULTADOS", fg=DIM, bg=CARD2,
                  font=("Segoe UI", 8, "bold"), anchor="w",
                  pady=8, padx=10).pack(fill="x")

        self._dd_listbox_items = []
        for g in results:
            row = tk.Frame(outer, bg=CARD2, cursor="hand2")
            row.pack(fill="x", padx=4, pady=1)
            row.game = g

            tk.Label(row, text=g["game"], fg=TEXT, bg=CARD2,
                      font=("Segoe UI", 11), anchor="w").pack(
                side="left", fill="x", expand=True, padx=(10, 10), pady=7)

            row.bind("<Enter>",    lambda e, r=row: r.config(bg="#1e1c40") or [c.config(bg="#1e1c40") for c in r.winfo_children()])
            row.bind("<Leave>",    lambda e, r=row: r.config(bg=CARD2) or [c.config(bg=CARD2) for c in r.winfo_children()])
            row.bind("<Button-1>", lambda e, g=g: self._select_game(g))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, g=g: self._select_game(g))

            self._dd_listbox_items.append(row)

        # Resize dropdown height
        dd.update_idletasks()
        total_h = sum(r.winfo_reqheight() for r in self._dd_listbox_items) + 36
        dd.geometry(f"{sw}x{min(total_h, 300)}+{rx + sx}+{y_off}")
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
        tk.Label(outer, text="Sin resultados — revisá la ortografía.", fg=DIM, bg=CARD2,
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
        # Entry sigue editable — el usuario puede volver a buscar
        self._sel_outer.config(highlightbackground=BORDER)
        self._game_tag_lbl.config(text="")
        # Mostrar × para limpiar la selección
        self._chevron_lbl.config(text="×", fg=TEXT, cursor="hand2")
        self._chevron_lbl.bind("<Button-1>", lambda e: self._clear_game_selection())
        # Update hint
        self._hint_lbl.config(text="✓  Juego seleccionado.", fg=GREEN)
        # Check OBS game match
        self._check_obs_game()
        self._update_record_btn()

    def _clear_game_selection(self):
        self.selected_game = None
        self._search_var.set("")
        self._search_entry.focus()
        self._chevron_lbl.config(text="⌄", fg=DIM, cursor="")
        self._chevron_lbl.unbind("<Button-1>")
        self._game_tag_lbl.config(text="")
        self._hint_lbl.config(text="Escribí el nombre del juego para buscar.", fg=DIM)
        self._obs_dot.config(fg=DIMMER)
        self._obs_lbl.config(text="Seleccioná un juego para verificar OBS.", fg=DIM)
        self._warn_frame.pack_forget()
        self._obs_status = "idle"
        self._update_record_btn()

    def _check_obs_game(self):
        """Verifica en OBS qué juego está capturado (en thread)."""
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
                # OBS no está corriendo o no responde — tratar como advertencia
                self.root.after(0, lambda: self._set_obs_status(
                    "warn", "OBS no está corriendo o no responde al WebSocket."))
                return

            # Check 1 — OBS ya grabando
            if is_recording:
                self.root.after(0, lambda: self._set_obs_status(
                    "already_recording",
                    "OBS ya está grabando. Detené la grabación desde OBS antes de continuar."
                ))
                return

            # Check 2 — modo de captura incorrecto (Display/Window Capture)
            if wrong_source:
                self.root.after(0, lambda ws=wrong_source: self._set_obs_status(
                    "wrong_source", ws
                ))
                return

            # Check 3 — verificar que el juego correcto está en Game Capture
            if not win_title:
                status = "warn"
                msg    = "OBS no detecta ningún juego capturado. Revisá la fuente Game Capture."
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
        self._obs_status = status
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
            self._obs_lbl.config(text="No se detectó Game Capture en OBS.", fg=YELLOW)
            self._warn_txt.config(text=msg)
            self._warn_frame.pack(fill="x", pady=(8, 0))
        elif status == "mismatch":
            self._obs_lbl.config(text="Juego incorrecto en OBS.", fg=RED)
            self._warn_txt.config(text=msg + "\n\nCambiá la fuente Game Capture antes de grabar.")
            self._warn_frame.pack(fill="x", pady=(8, 0))
        elif status == "already_recording":
            self._obs_lbl.config(text="OBS ya está grabando.", fg=RED)
            self._warn_txt.config(
                text=msg + "\n\nLa grabación debe iniciarse desde el Recorder, no desde OBS.")
            self._warn_frame.pack(fill="x", pady=(8, 0))
        elif status == "wrong_source":
            # msg contiene el nombre legible del modo incorrecto (ej: "Captura de Pantalla")
            self._obs_lbl.config(text=f"Modo de captura incorrecto: {msg}.", fg=RED)
            self._warn_txt.config(
                text=f"Estás usando '{msg}' en OBS, que no es compatible con Pleiada.\n\n"
                     f"Cambiá la fuente a 'Captura de Videojuego' (Game Capture) y apuntala "
                     f"al proceso del juego.")
            self._warn_frame.pack(fill="x", pady=(8, 0))
        elif status == "auth_error":
            self._obs_lbl.config(text="OBS WebSocket: autenticación fallida.", fg=RED)
            self._warn_txt.config(text=msg)
            self._warn_frame.pack(fill="x", pady=(8, 0))
        self._update_record_btn()

    def _update_record_btn(self):
        if not hasattr(self, "_rec_btn_idle"):
            return
        can_record = (
            self.selected_game is not None and
            self._obs_status == "ok"   # PLE-31: botón solo habilitado cuando OBS confirmado
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

    # ── Iniciar / Detener grabación ────────────────────────────────────────────

    def _start_recording(self):
        if not self.selected_game or self._obs_status == "mismatch":
            return

        # PLE-42: validar que el juego esté en ejecución antes de iniciar.
        # Solo se bloquea si el juego tiene process_name conocido en games_list.json.
        # Para los juegos sin process_name (null) se omite el chequeo.
        _proc = self.selected_game.get("process_name")
        if _proc:
            try:
                _tl = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {_proc}", "/NH"],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if _proc.lower() not in _tl.stdout.lower():
                    import tkinter.messagebox as _mb
                    _mb.showwarning(
                        "Juego no detectado",
                        f"No se detectó '{self.selected_game['game']}' en ejecución.\n\n"
                        "Iniciá el juego antes de comenzar la grabación."
                    )
                    return
            except Exception:
                pass   # error en tasklist → beneficio de la duda, continuar

        self._show_recording_starting()

        def _worker():
            # 1. Crear carpeta de sesión
            game   = re.sub(r'[\\/:*?"<>|]', "", self.selected_game["game"])
            dt     = time.strftime("%d_%m_%y__%H_%M_%S")
            sname  = f"{game}_{dt} recording"
            sdir   = BASE_DIR / sname
            BASE_DIR.mkdir(parents=True, exist_ok=True)
            sdir.mkdir(parents=True, exist_ok=True)
            self.session_dir = sdir

            # 2. Asegurarse de que OBS esté corriendo (lanzarlo si hace falta).
            #    Esto puede tardar hasta ~30 s si OBS no está abierto.
            #    NO iniciamos la grabación todavía — eso ocurre en countdown=0.
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

            # 4. Guardia final + obtener rec_dir (una sola conexión WebSocket)
            rec_dir_str   = ""
            existing_vids = set()
            try:
                ws = obs_connect()

                # Guardia: OBS no debe estar grabando en este momento
                rec_status = obs_send(ws, "GetRecordStatus")
                if rec_status.get("d", {}).get("responseData", {}).get("outputActive", False):
                    ws.close()
                    self.root.after(0, lambda: self._recording_start_error(
                        "OBS empezó a grabar mientras preparabas la sesión.\n"
                        "Detené la grabación en OBS y volvé a intentarlo."
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

                    # PLE-33: solo bloquear si la fuente incompatible está activa en la escena
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

                    # Sin fuentes incompatibles — verificar que game_capture apunta al juego correcto
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
                    pass   # si falla la verificación, continuamos igualmente

                r = obs_send(ws, "GetRecordDirectory")
                ws.close()
                rec_dir_str = r.get("d", {}).get("responseData", {}).get("recordDirectory", "")
                if rec_dir_str and os.path.isdir(rec_dir_str):
                    existing_vids = set(glob.glob(os.path.join(rec_dir_str, "*.mp4")))
            except OBSAuthError as e:
                self.root.after(0, lambda m=str(e): self._recording_start_error(m))
                return
            except Exception:
                pass   # OBS no responde — continuamos sin rec_dir

            # 5. Guardar prep para el thread que arranca en countdown=0
            self._obs_prep = (rec_dir_str, existing_vids)

            # 6. Mostrar countdown — OBS aún no está grabando
            self.recording = True
            self.root.after(0, self._show_countdown)
            # (La grabación real arranca en _launch_at_zero, cuando el countdown llega a 0)

        threading.Thread(target=_worker, daemon=True).start()

    def _recording_start_error(self, msg="Error: no se pudo iniciar OBS."):
        self._show_idle()
        # Mostrar mensaje de error en el panel de OBS (pantalla idle)
        if hasattr(self, "_obs_lbl"):
            self._obs_lbl.config(text=msg, fg=RED)
        if hasattr(self, "_warn_txt") and "\n" in msg:
            # Mensaje largo (ej: auth error) → también en el panel de advertencia
            try:
                self._warn_txt.config(text=msg)
                self._warn_frame.pack(fill="x", pady=(8, 0))
            except Exception:
                pass

    def _stop_recording(self):
        if not self.recording:
            return
        self._we_stopped = True   # le decimos al listener que NOSOTROS paramos
        self.recording = False
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

            # 5. Correr sync check — acumular statuses por archivo para mostrarlos en resultado
            _keys = ["mouse_log.csv", "mouse_delta_log.csv", "key_log.csv", "video_timeline.csv", "video"]
            self._last_sync_statuses = {}

            def _on_progress(i, s):
                if i < len(_keys):
                    self._last_sync_statuses[_keys[i]] = s
                self.root.after(0, lambda i=i, s=s: self._sync_progress(i, s))

            results = run_sync_check(sdir, progress_cb=_on_progress)

            # 6. Guardar metadata sidecar localmente (siempre, ok o fallido).
            #    Ya NO se empaqueta un .pleiada — los archivos quedan sueltos en la
            #    carpeta de sesión (CSVs + MP4 + session_metadata.json).
            self.root.after(0, self._show_packaging_anim)   # "Guardando localmente los archivos..."
            build_session_metadata(sdir, self.selected_game, results,
                                   exe_path=self._recording_exe_path)

            # 7. Mostrar resultado
            self.root.after(0, lambda: self._show_result(results["session_ok"], results, None))

        threading.Thread(target=_worker, daemon=True).start()

    # ── Pantalla: iniciando grabación ──────────────────────────────────────────

    def _show_recording_starting(self):
        self._clear_content()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="", bg=BG).pack(expand=True)
        tk.Label(frame, text="⏳  Iniciando grabación...", fg=DIM, bg=BG,
                  font=("Segoe UI", 13)).pack()
        tk.Label(frame, text="Conectando a OBS, por favor esperá.", fg=DIMMER, bg=BG,
                  font=("Segoe UI", 10)).pack(pady=(8, 0))
        tk.Label(frame, text="", bg=BG).pack(expand=True)

    # ── Pantalla: cuenta regresiva pre-grabación ──────────────────────────────

    _COUNTDOWN_SECS = 10   # PLE-34: reducido de 15 a 10 segundos

    def _show_countdown(self):
        self._clear_content()
        game  = (self.selected_game or {}).get("game", "—")
        genre = (self.selected_game or {}).get("genre", "")

        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=18)

        # — Status row ————————————————————————————————————————
        status_row = tk.Frame(frame, bg=BG)
        status_row.pack(fill="x")
        self._cd_dot = tk.Label(status_row, text="●", fg=YELLOW, bg=BG,
                                 font=("Segoe UI", 10, "bold"))
        self._cd_dot.pack(side="left")
        tk.Label(status_row, text="INICIANDO", fg=YELLOW, bg=BG,
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(6, 0))

        # — Nombre del juego ———————————————————————————————————
        tk.Label(frame, text=game, fg=TEXT, bg=BG,
                  font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", pady=(14, 4))
        tk.Label(frame, text=genre, fg=DIM, bg=BG,
                  font=("Segoe UI", 10), anchor="w").pack(fill="x")

        # — Número grande de countdown (misma fuente que el timer) ————————
        tk.Frame(frame, bg=BG).pack(fill="y", expand=True)
        self._cd_num_lbl = tk.Label(frame, text=str(self._COUNTDOWN_SECS),
                                     fg=YELLOW, bg=BG,
                                     font=("Cascadia Code", 52, "normal"))
        self._cd_num_lbl.pack()
        tk.Label(frame, text="La grabación comenzará en...", fg=DIM, bg=BG,
                  font=("Segoe UI", 10)).pack(pady=(10, 0))
        tk.Frame(frame, bg=BG).pack(fill="y", expand=True)

        _mk_separator(frame, color=BORDER2, pady=(0, 14))

        # — Botón cancelar ———————————————————————————————————
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
            # Mostrar ▶ brevemente mientras el thread de OBS arranca
            try:
                self._cd_num_lbl.config(text="▶", fg=GREEN)
            except Exception:
                pass
            # OBS StartRecord ocurre en thread separado — no bloquea la UI
            threading.Thread(target=self._launch_at_zero, daemon=True).start()
            return
        # Color: amarillo mientras queda tiempo, rojo en los últimos 5
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
        Envía StartRecord a OBS, captura el anchor timestamp, arranca AHK
        y muestra la pantalla de grabación activa."""
        if not self.recording:
            return

        # a. Verificación final de fuente OBS — el usuario pudo cambiar algo durante el countdown
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

        # b. Enviar StartRecord (OBS ya está corriendo — _worker lo garantizó)
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

        # b. Anchor timestamp — capturado justo al confirmar STARTED
        anchor_ts = int(time.time() * 1000)

        # c. Escribir anchor file (AHK lo lee al arrancar)
        try:
            ANCHOR_FILE.write_text(str(anchor_ts), encoding="utf-8")
        except Exception:
            pass

        # d. Arrancar AHK — pasar exe del juego para filtrar inputs por ventana activa (PLE-43/13)
        start_ahk_logger(str(self.session_dir), self._recording_exe)

        # e. Listener de stop externo de OBS + monitor de fuente
        self._we_stopped = False
        # PLE-37: capturar exe del juego para detectar si el proceso cierra
        _win = ""
        try:
            _sr = obs_connect()
            _inputs = obs_send(_sr, "GetInputList").get("d", {}).get("responseData", {}).get("inputs", [])
            _gc = next((i for i in _inputs if i.get("inputKind") == "game_capture"), None)
            if _gc:
                _ws_set = obs_send(_sr, "GetInputSettings", {"inputName": _gc["inputName"]})
                _win = _ws_set.get("d", {}).get("responseData", {}).get("inputSettings", {}).get("window", "")
                self._recording_exe = next(
                    (p.strip() for p in _win.split(":") if p.strip().lower().endswith(".exe")), ""
                )
            _sr.close()
        except Exception:
            self._recording_exe = ""
        # v0.4 Fase 2: cachear ruta completa del exe (juego está corriendo en este punto).
        # Resolución robusta: OBS exe -> wmic, con fallback a buscar la ventana del juego.
        self._recording_exe_path = _meta_find_game_exe_path(
            _win, (self.selected_game or {}).get("game", "")
        )
        self._start_obs_stop_listener()
        self._start_obs_source_monitor()

        # f. Mostrar pantalla de grabación activa
        self.root.after(0, lambda: self._show_recording_active(anchor_ts))

    # ── OBS stop listener ─────────────────────────────────────────────────────

    def _start_obs_stop_listener(self):
        """Abre una conexión WebSocket dedicada y escucha RecordStateChanged en background.
        Si OBS detiene la grabación sin que nosotros lo hayamos pedido, cancela la sesión."""

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
                                # OBS dejó de grabar — ¿fuimos nosotros?
                                if not self._we_stopped and self.recording:
                                    self.root.after(0, self._obs_external_stop)
                                break
                    except Exception as exc:
                        # Timeout es la excepción esperada del polling — continuar
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
        """Llamado en el main thread cuando OBS detuvo la grabación externamente.
        Cancela la sesión: para AHK abruptamente, elimina archivos, vuelve al idle."""
        if not self.recording:
            return   # ya fue detenida normalmente justo a la vez — ignorar

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

        # Parar AHK de golpe (sin esperar ANCHOR_END — la sesión se descarta)
        stop_ahk_logger(None)

        # Eliminar carpeta de sesión con todos los CSVs
        if sdir and sdir.exists():
            try:
                shutil.rmtree(str(sdir), ignore_errors=True)
            except Exception:
                pass

        self.session_dir = None

        # Eliminar el MP4 que OBS guardó (está en el dir de grabación de OBS, no en sdir)
        threading.Thread(
            target=self._delete_obs_video, args=(obs_prep,), daemon=True
        ).start()

        # Volver al idle y mostrar advertencia
        self._show_idle()
        if hasattr(self, "_obs_lbl"):
            try:
                self._obs_lbl.config(
                    text="OBS detuvo la grabación.", fg=RED)
            except Exception:
                pass
        if hasattr(self, "_warn_txt"):
            try:
                self._warn_txt.config(
                    text="OBS detuvo la grabación antes de que el Recorder terminara.\n\n"
                         "La sesión fue cancelada. Siempre usá el botón 'Detener' del Recorder "
                         "para finalizar correctamente."
                )
                self._warn_frame.pack(fill="x", pady=(8, 0))
            except Exception:
                pass

    # ── Eliminación segura del MP4 descartado ─────────────────────────────────

    def _delete_obs_video(self, obs_prep):
        """Busca y elimina permanentemente el MP4 que OBS creó para una sesión cancelada.
        Corre en thread background porque OBS puede tardar unos segundos en terminar de
        escribir el archivo después de StopRecord.

        obs_prep: tupla (rec_dir_str, existing_vids_set) capturada antes de la grabación.
        """
        rec_dir_str, existing_vids = obs_prep
        if not rec_dir_str or not os.path.isdir(rec_dir_str):
            _obs_dbg("_delete_obs_video: rec_dir desconocido, buscando en carpeta Videos")
            # Fallback: buscar en ~/Videos el MP4 más reciente (últimos 5 min)
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
            _obs_dbg("_delete_obs_video: no se encontró MP4 nuevo para eliminar")
            return

        # Esperar a que OBS suelte el handle del archivo (hasta 10 s adicionales)
        for _ in range(20):
            try:
                os.remove(new_file)
                _obs_dbg(f"_delete_obs_video: eliminado permanentemente → {new_file}")
                return
            except (PermissionError, OSError):
                time.sleep(0.5)

        _obs_dbg(f"_delete_obs_video: no se pudo eliminar (handle ocupado) → {new_file}")

    # ── Monitor de fuente OBS durante grabación ───────────────────────────────

    def _start_obs_source_monitor(self):
        """Sondea la fuente de OBS cada 3 s durante la grabación.
        Detecta:
        - Fuente incorrecta o ventana cambiada → cancela la sesión.
        - PLE-37: el proceso del juego cerró → cancela la sesión automáticamente.
        """

        def _game_process_running(exe_name):
            """Retorna True si el proceso exe_name está corriendo."""
            if not exe_name:
                return True   # sin exe conocido → no bloquear
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/NH"],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return exe_name.lower() in result.stdout.lower()
            except Exception:
                return True   # error → beneficio de la duda

        def _monitor():
            time.sleep(4)   # dar tiempo a que la grabación arranque bien
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
                        f"Cambiaste la fuente en OBS a '{wrong_source}' durante la grabación.\n\n"
                        "La sesión fue cancelada automáticamente."
                    )
                elif win_title:
                    selected = (self.selected_game or {}).get("game", "")
                    if not _obs_title_matches(selected, win_match or win_title):
                        problem_msg = (
                            f"OBS cambió a capturar '{win_title}' durante la grabación.\n\n"
                            "La sesión fue cancelada automáticamente."
                        )

                # PLE-37: verificar que el proceso del juego sigue corriendo
                if not problem_msg:
                    rec_exe = self._recording_exe
                    if rec_exe and not _game_process_running(rec_exe):
                        game_not_found_count += 1
                        if game_not_found_count >= 2:   # 2 checks consecutivos sin el proceso
                            game_display = rec_exe.replace(".exe", "")
                            problem_msg = (
                                f"El juego '{game_display}' se cerró durante la grabación.\n\n"
                                "La sesión fue cancelada automáticamente."
                            )
                    else:
                        game_not_found_count = 0   # reset si el proceso volvió a aparecer

                if problem_msg and not self._we_stopped and self.recording:
                    self.root.after(0, lambda m=problem_msg: self._obs_mid_recording_cancel(m))
                    break

                time.sleep(3)

        threading.Thread(target=_monitor, daemon=True).start()

    def _obs_mid_recording_cancel(self, reason_msg):
        """Llamado en el main thread cuando la fuente de OBS cambió durante la grabación.
        Para OBS (sigue grabando), para AHK, elimina sesión, vuelve al idle."""
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

        # Parar OBS (sigue grabando — a diferencia del stop externo, aquí debemos detenerlo)
        try:
            ws = obs_connect()
            obs_send(ws, "StopRecord")
            ws.close()
        except Exception:
            pass

        # Eliminar carpeta de sesión con todos los CSVs
        if sdir and sdir.exists():
            try:
                shutil.rmtree(str(sdir), ignore_errors=True)
            except Exception:
                pass

        self.session_dir = None

        # Eliminar el MP4 que OBS guardó (necesita esperar a que OBS termine de escribirlo)
        threading.Thread(
            target=self._delete_obs_video, args=(obs_prep,), daemon=True
        ).start()

        # Volver al idle con mensaje de error
        self._show_idle()
        if hasattr(self, "_obs_lbl"):
            try:
                self._obs_lbl.config(text="Grabación cancelada automáticamente.", fg=RED)
            except Exception:
                pass
        if hasattr(self, "_warn_txt"):
            try:
                self._warn_txt.config(text=reason_msg)
                self._warn_frame.pack(fill="x", pady=(8, 0))
            except Exception:
                pass

    # ── Pantalla: grabando ─────────────────────────────────────────────────────

    def _show_recording_active(self, anchor_ts):
        self._clear_content()
        self.rec_seconds = 0
        game = (self.selected_game or {}).get("game", "—")

        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=18)

        # Status row — right items primero para evitar overlap en ventanas angostas
        status_row = tk.Frame(frame, bg=BG)
        status_row.pack(fill="x")
        # Derecha: límite + countdown (se packean antes para reservar espacio)
        self._countdown_lbl = tk.Label(status_row, text="01:05:00", fg=DIM, bg=BG,
                                        font=("Cascadia Code", 11))
        self._countdown_lbl.pack(side="right")
        tk.Label(status_row, text="límite  ", fg=DIMMER, bg=BG,
                  font=("Segoe UI", 9)).pack(side="right")
        # Izquierda: dot + GRABANDO
        self._rec_dot = tk.Label(status_row, text="●", fg=RED, bg=BG,
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
        stop_btn = tk.Button(frame, text="  ⏹  Detener grabación", fg=RED, bg="#1a0808",
                              relief="flat", bd=0, cursor="hand2",
                              font=("Segoe UI", 12, "bold"),
                              activebackground="#2a1010", activeforeground=RED,
                              command=self._stop_recording,
                              highlightthickness=1, highlightbackground="#7a2020")
        stop_btn.pack(fill="x", ipady=12)

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
        rem = max(0, MAX_SECONDS - self.rec_seconds)
        rh  = rem // 3600
        rm  = (rem % 3600) // 60
        rs  = rem % 60
        col = YELLOW if rem <= 300 else DIM
        self._countdown_lbl.config(text=f"{rh:02d}:{rm:02d}:{rs:02d}", fg=col)

        if self.rec_seconds >= MAX_SECONDS:
            self._stop_recording()
            return

        self._timer_id = self.root.after(1000, self._ticker)

    def _pulse_dot(self):
        if not self.recording:
            return
        cur = self._rec_dot.cget("fg")
        self._rec_dot.config(fg=RED if cur == BG else BG)
        self.root.after(700, self._pulse_dot)

    # ── Pantalla: verificando ──────────────────────────────────────────────────

    def _show_syncing(self, sdir):
        self._clear_content()
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=20)

        tk.Label(frame, text="VERIFICANDO SESIÓN", fg=DIM, bg=BG,
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
            mark = tk.Label(row, text="·", fg=ACCENT, bg="#0b0b1d",
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
            mark.config(text="✓", fg=GREEN)
            val.config(text="ok", fg=GREEN)
        elif status == "missing":
            mark.config(text="✗", fg=RED)
            val.config(text="falta", fg=RED)
        elif status == "err":
            mark.config(text="✗", fg=RED)
            val.config(text="error", fg=RED)
        elif status == "truncated":
            mark.config(text="✗", fg=RED)
            val.config(text="truncado", fg=RED)
        elif status == "offset":
            mark.config(text="⚠", fg=YELLOW)
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

    # ── Pantalla: resultado ────────────────────────────────────────────────────

    def _show_result(self, ok, results, out_path):
        self._clear_content()

        # PLE-45: botones anclados al fondo — siempre visibles sin importar
        # resolución o escalado de pantalla. Se packean ANTES que el canvas
        # para que Tkinter les reserve espacio antes de expandir el scroll.
        tk.Frame(self.content, bg=BORDER2, height=1).pack(side="bottom", fill="x")
        btn_outer = tk.Frame(self.content, bg=BG, padx=22, pady=10)
        btn_outer.pack(side="bottom", fill="x")
        btn_row = tk.Frame(btn_outer, bg=BG)
        btn_row.pack(fill="x")

        # Canvas scrollable — ocupa el espacio restante por encima del btn_row
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

        # Mousewheel scroll (análisis scrolleable si el contenido excede el área)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        # ── Botones — definidos acá para capturar canvas en el closure ────────
        def go_again():
            canvas.unbind_all("<MouseWheel>")
            self.session_dir = None
            self._show_idle()

        tk.Button(btn_row, text="Nueva grabación", fg=TEXT, bg=CARD,
                   relief="flat", bd=0, cursor="hand2",
                   font=("Segoe UI", 11), activebackground=CARD2,
                   activeforeground=TEXT, command=go_again,
                   highlightthickness=1, highlightbackground=BORDER).pack(
            side="left", fill="x", expand=True, ipady=10, padx=(0, 6) if ok else (0, 0))

        if ok:
            def open_site():
                import webbrowser
                webbrowser.open("https://gameplayalliance.gg")
            tk.Button(btn_row, text="Gameplayalliance.gg ↗", fg="#fff", bg=ACCENT,
                       relief="flat", bd=0, cursor="hand2",
                       font=("Segoe UI", 11, "bold"), activebackground="#9080e0",
                       command=open_site).pack(side="right", fill="x", expand=True,
                                               ipady=10, padx=(6, 0))

        inner = tk.Frame(frame, bg=BG)
        inner.pack(fill="both", expand=True, padx=22, pady=16)

        # ── Notify card ───────────────────────────────────────────────────────
        if ok:
            card_bg  = "#06140d"
            card_brd = "#1e6644"
            icon_txt = "✓"
            icon_col = GREEN
            title    = "¡Sesión lista para enviar!"
            body     = ("La sesión fue analizada y se encuentra sincronizada. "
                        "Verifica que no haya nada personal en los archivos, no los "
                        "modifiques, y comienza la subida a la plataforma")
        else:
            card_bg  = "#140606"
            card_brd = "#7a2020"
            icon_txt = "✗"
            icon_col = RED
            title    = "Sesión no apta para enviar"
            if results and results.get("short_session"):
                # PLE-41: sesión demasiado corta
                body = "La sesión duró menos de 30 segundos.\nGrabá al menos 30 segundos de gameplay para que los datos sean válidos."
            else:
                body = "Los archivos no pasaron el sync check.\nDescartá esta sesión e iniciá una nueva."

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

        # ── Panel de análisis (siempre visible) ───────────────────────────────
        _mk_section_label(inner, "ANÁLISIS DE SINCRONIZACIÓN")

        vbg = "#0b0b1d"
        verify = tk.Frame(inner, bg=vbg, highlightthickness=1, highlightbackground=BORDER2)
        verify.pack(fill="x", pady=(0, 12))

        file_items = [
            ("mouse_log.csv",       "mouse_log.csv"),
            ("mouse_delta_log.csv", "mouse_delta_log.csv"),
            ("key_log.csv",         "key_log.csv"),
            ("video_timeline.csv",  "video_timeline.csv"),
            ("video",               "video MP4"),
        ]
        statuses = self._last_sync_statuses
        status_labels = {
            "ok":       ("✓", GREEN,  "ok"),
            "missing":  ("✗", RED,    "falta"),
            "err":      ("✗", RED,    "error"),
            "truncated":("✗", RED,    "truncado"),
            "offset":   ("⚠", YELLOW, "desfase"),
        }
        for key, label in file_items:
            s = statuses.get(key, "pending")
            mark_txt, col, val_txt = status_labels.get(s, ("·", DIMMER, "—"))
            row = tk.Frame(verify, bg=vbg)
            row.pack(fill="x", padx=14, pady=3)
            tk.Label(row, text=mark_txt, fg=col, bg=vbg,
                      font=("Cascadia Code", 10), width=2, anchor="w").pack(side="left")
            tk.Label(row, text=label, fg=TEXT if s != "pending" else DIM, bg=vbg,
                      font=("Cascadia Code", 10), anchor="w", width=22).pack(side="left")
            tk.Label(row, text=val_txt, fg=col, bg=vbg,
                      font=("Cascadia Code", 10), anchor="e").pack(side="right")

        # Línea de detalle numérico
        if results:
            diff    = results.get("signed_diff")
            csv_dur = results.get("csv_dur")
            vid_dur = results.get("video_dur")
            truncated = results.get("truncated", False)

            tk.Frame(verify, bg=BORDER2, height=1).pack(fill="x", padx=14, pady=(4, 0))
            drow = tk.Frame(verify, bg=vbg)
            drow.pack(fill="x", padx=14, pady=(4, 10))

            if truncated:
                tk.Label(drow, text="Video truncado — OBS cerró sin finalizar la grabación.",
                          fg=RED, bg=vbg, font=("Cascadia Code", 9), wraplength=WIN_W - 80,
                          justify="left", anchor="w").pack(fill="x")
            elif diff is not None and csv_dur and vid_dur:
                # Derecha primero para evitar overlap con items de izquierda
                diff_col = GREEN if ok else RED
                tk.Label(drow, text=f"Δ {diff:+d} ms", fg=diff_col, bg=vbg,
                          font=("Cascadia Code", 9, "bold")).pack(side="right")
                tk.Label(drow, text=f"CSV: {csv_dur} ms", fg=DIM, bg=vbg,
                          font=("Cascadia Code", 9)).pack(side="left")
                tk.Label(drow, text=f"Video: {vid_dur} ms", fg=DIM, bg=vbg,
                          font=("Cascadia Code", 9)).pack(side="left", padx=(14, 0))
            elif not results.get("csvs_ok"):
                tk.Label(drow, text="Uno o más archivos CSV están incompletos o faltan.",
                          fg=RED, bg=vbg, font=("Cascadia Code", 9), wraplength=WIN_W - 80,
                          justify="left", anchor="w").pack(fill="x")

        # ── Sesión / archivo ──────────────────────────────────────────────────
        if self.session_dir:
            _mk_section_label(inner, "SESIÓN")
            srow = tk.Frame(inner, bg=BG)
            srow.pack(fill="x", pady=(0, 8))
            tk.Label(srow, text=self.session_dir.name, fg=DIM, bg=BG,
                      font=("Cascadia Code", 9), anchor="w", wraplength=WIN_W - 100,
                      justify="left").pack(side="left", fill="x", expand=True)
            def _open_folder(d=self.session_dir):
                subprocess.Popen(["explorer", str(d)])
            folder_btn = tk.Label(srow, text="📁", bg=BG, fg=YELLOW,
                                   font=("Segoe UI Emoji", 16), cursor="hand2",
                                   padx=4)
            folder_btn.pack(side="right", anchor="e")
            folder_btn.bind("<Button-1>", lambda e: _open_folder())

        # (botones movidos al fondo fijo de self.content — ver inicio de _show_result)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _clear_content(self):
        self._hide_dropdown()
        # Cancelar animación de packaging si está corriendo
        if getattr(self, "_pkg_anim_id", None):
            try:
                self.root.after_cancel(self._pkg_anim_id)
            except Exception:
                pass
            self._pkg_anim_id = None
        for w in self.content.winfo_children():
            w.destroy()

    def _open_tutorial(self):
        """Relanza el wizard de configuración inicial (tutorial post-instalación)."""
        wizard = APP_DIR / "pleiada_setup_wizard.pyw"
        if not wizard.exists():
            return
        # Buscar pythonw.exe igual que el instalador
        pythonw = None
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    key = winreg.OpenKey(hive, r"Software\Python\PythonCore\3.12\InstallPath")
                    d, _ = winreg.QueryValueEx(key, "")
                    winreg.CloseKey(key)
                    candidate = Path(d) / "pythonw.exe"
                    if candidate.exists():
                        pythonw = str(candidate)
                        break
                except Exception:
                    pass
        except Exception:
            pass
        if not pythonw:
            import shutil as _sh
            pythonw = _sh.which("pythonw") or _sh.which("pythonw.exe") or "pythonw.exe"
        try:
            subprocess.Popen([pythonw, str(wizard)], cwd=str(APP_DIR),
                             creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            _obs_dbg(f"_open_tutorial: {e}")

    def _on_close(self):
        if self.recording:
            self._stop_recording()
        self.root.after(500, self.root.destroy)

    def run(self):
        self.root.mainloop()


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # PLE-18: DPI awareness — evita que Windows clipee contenido en pantallas escaladas.
    # Debe llamarse ANTES de crear cualquier ventana Tk.
    try:
        import ctypes as _ct_dpi
        try:
            _ct_dpi.windll.shcore.SetProcessDpiAwareness(2)   # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:
            _ct_dpi.windll.user32.SetProcessDPIAware()        # fallback para Windows < 8.1

        # PLE-44: escalar WIN_W/WIN_H según el DPI del sistema para evitar textos
        # cortados en pantallas con escalado 125%/150%. Con DpiAwareness(2) el proceso
        # recibe píxeles físicos, pero las fuentes en puntos escalan con el DPI —
        # sin este ajuste la ventana queda angosta relativa al tamaño de letra.
        _sys_dpi = _ct_dpi.windll.user32.GetDpiForSystem()
        if _sys_dpi and _sys_dpi != 96:
            _dpi_scale = _sys_dpi / 96.0
            WIN_W = int(420 * _dpi_scale)
            WIN_H = int(640 * _dpi_scale)
    except Exception:
        pass

    # PLE-38: Single-instance guard — impide abrir dos grabaciones en paralelo.
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
                "Pleiada Recorder",
                "Pleiada Recorder ya está abierto.\n\nCerrá la ventana existente antes de abrir una nueva."
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
