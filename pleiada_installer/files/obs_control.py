"""
obs_control.py  V13
Controla OBS Studio via WebSocket.
Uso desde AHK:
    obs_control.py start
    obs_control.py stop [carpeta_sesion]
"""

import sys
import json
import hashlib
import base64
import uuid
import shutil
import os
import time
import struct
import subprocess
import glob
import websocket

OBS_HOST     = "localhost"
OBS_PORT     = 4455
OBS_PASSWORD = ""

DEBUG_LOG   = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "pleiada_obs_debug.txt")
ANCHOR_FILE = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "pleiada_anchor_ts.txt")

def dbg(msg):
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

# ── OBS executable ───────────────────────────────────────────────

OBS_CANDIDATES = [
    r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
    r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe",
]

def find_obs():
    for path in OBS_CANDIDATES:
        if os.path.isfile(path):
            return path
    try:
        import winreg
        reg_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\OBS Studio"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\OBS Studio"),
            (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\OBS Studio"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\OBS Studio"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\OBS Studio"),
        ]
        for hive, subkey in reg_keys:
            try:
                with winreg.OpenKey(hive, subkey) as k:
                    for val_name in ("InstallLocation", ""):
                        try:
                            install_dir, _ = winreg.QueryValueEx(k, val_name)
                            candidate = os.path.join(install_dir.strip(), "bin", "64bit", "obs64.exe")
                            if os.path.isfile(candidate):
                                dbg(f"OBS encontrado via registro: {candidate}")
                                return candidate
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        for match in glob.glob(os.path.join(base, "obs*", "bin", "64bit", "obs64.exe")):
            dbg(f"OBS encontrado via glob: {match}")
            return match
    return None

def obs_is_running():
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq obs64.exe", "/NH"],
            stderr=subprocess.DEVNULL
        ).decode(errors="ignore")
        return "obs64.exe" in out
    except Exception:
        return False

def launch_obs():
    obs = find_obs()
    if not obs:
        dbg("OBS no encontrado en rutas conocidas")
        return False
    dbg(f"Lanzando OBS: {obs}")
    obs_dir = os.path.dirname(obs)
    subprocess.Popen([obs], cwd=obs_dir, close_fds=True)
    for i in range(30):
        time.sleep(1)
        try:
            ws = websocket.WebSocket()
            ws.connect(f"ws://{OBS_HOST}:{OBS_PORT}", timeout=1)
            ws.close()
            dbg(f"OBS WebSocket listo en {i+1} seg")
            return True
        except Exception:
            pass
    dbg("OBS no levanto en 30 seg")
    return False

# ── WebSocket helpers ────────────────────────────────────────────

def connect_and_auth():
    ws = websocket.WebSocket()
    ws.connect(f"ws://{OBS_HOST}:{OBS_PORT}", timeout=5)
    hello = json.loads(ws.recv())
    dbg(f"hello: {hello}")
    auth_data = hello["d"].get("authentication")
    if not auth_data:
        ws.send(json.dumps({"op": 1, "d": {"rpcVersion": 1}}))
        json.loads(ws.recv())
        return ws
    secret = base64.b64encode(
        hashlib.sha256((OBS_PASSWORD + auth_data["salt"]).encode()).digest()
    ).decode()
    auth_str = base64.b64encode(
        hashlib.sha256((secret + auth_data["challenge"]).encode()).digest()
    ).decode()
    ws.send(json.dumps({"op": 1, "d": {"rpcVersion": 1, "authentication": auth_str}}))
    json.loads(ws.recv())
    return ws

def send(ws, request_type, data=None):
    msg = {
        "op": 6,
        "d": {
            "requestType": request_type,
            "requestId":   str(uuid.uuid4()),
            "requestData": data or {}
        }
    }
    ws.send(json.dumps(msg))
    while True:
        raw = ws.recv()
        parsed = json.loads(raw)
        if parsed.get("op") == 5:
            dbg(f"[EVENT skipped] {raw[:120]}")
            continue
        dbg(f"{request_type} -> {raw}")
        return parsed

def reconnect_ws(max_attempts=30):
    """Espera a que OBS WS vuelva a estar disponible. Retorna ws autenticado o None."""
    for _ in range(max_attempts):
        time.sleep(0.5)
        try:
            return connect_and_auth()
        except Exception:
            pass
    return None

# ── Buscar video reciente en carpeta Videos ──────────────────────

def find_recent_video(since_time):
    videos_dir = os.path.join(os.path.expanduser("~"), "Videos")
    patterns   = ["*.mp4", "*.mkv", "*.flv", "*.avi", "*.mov"]
    candidates = []
    for pat in patterns:
        candidates.extend(glob.glob(os.path.join(videos_dir, pat)))
        candidates.extend(glob.glob(os.path.join(videos_dir, "**", pat), recursive=True))
    recent = [f for f in candidates if os.path.getmtime(f) >= since_time]
    if not recent:
        dbg(f"Sin videos recientes desde {since_time} en {videos_dir}")
        return None
    best = max(recent, key=os.path.getmtime)
    dbg(f"Video reciente encontrado: {best}")
    return best

# ── Anchor timestamp via primer moof ────────────────────────────
#
# Para sincronizar el ANCHOR_START con el primer frame real del video
# independientemente del hardware o del encoder, monitoreamos el archivo
# MP4 que OBS está escribiendo:
#
#   1. Esperamos a que aparezca un nuevo .mp4 en el directorio de grabaciones
#   2. Leemos el timescale del mdhd (moov box, escrito al inicio)
#   3. Esperamos el primer moof box (primer fragmento con frames reales)
#   4. Calculamos:
#        anchor_ts = timestamp_deteccion - duracion_primer_moof_ms
#      → anchor_ts ≈ Unix-ms del primer frame capturado (±50 ms)
#   5. Escribimos anchor_ts en ANCHOR_FILE para que AHK lo use como ANCHOR_START
#
# Esto funciona en cualquier hardware porque medimos el timing directamente
# del archivo en lugar de estimar la latencia del encoder.

def _mp4_next_box(f, pos, limit):
    """Lee el encabezado del box en `pos`. Retorna (end_pos, box_type, data_start)."""
    if pos + 8 > limit:
        return None, None, None
    f.seek(pos)
    raw = f.read(8)
    if len(raw) < 8:
        return None, None, None
    size     = struct.unpack('>I', raw[:4])[0]
    box_type = raw[4:8]
    if size < 8:
        return None, None, None
    return pos + size, box_type, pos + 8

def _mp4_find_box(f, start, end, target):
    """Primer box de tipo `target` en [start, end). Retorna (data_start, box_end)."""
    pos = start
    while True:
        box_end, btype, data = _mp4_next_box(f, pos, end)
        if box_end is None:
            return None, None
        if btype == target:
            return data, box_end
        pos = box_end

def _mp4_read_timescale(path):
    """Lee el timescale del mdhd del primer trak en el moov. Retorna int o None."""
    try:
        file_size = os.path.getsize(path)
        if file_size < 200:
            return None
        with open(path, 'rb') as f:
            moov_data, moov_end = _mp4_find_box(f, 0, min(file_size, 131072), b'moov')
            if moov_data is None:
                return None
            trak_data, trak_end = _mp4_find_box(f, moov_data, moov_end, b'trak')
            if trak_data is None:
                return None
            mdia_data, mdia_end = _mp4_find_box(f, trak_data, trak_end, b'mdia')
            if mdia_data is None:
                return None
            mdhd_data, _ = _mp4_find_box(f, mdia_data, mdia_end, b'mdhd')
            if mdhd_data is None:
                return None
            f.seek(mdhd_data)
            version = struct.unpack('B', f.read(1))[0]
            f.read(3)
            f.read(16 if version == 1 else 8)  # creation + modification time
            ts = struct.unpack('>I', f.read(4))[0]
            return ts if ts > 0 else None
    except Exception:
        return None

def _mp4_first_moof_duration_ms(path, timescale):
    """
    Busca el primer moof en el archivo y retorna su duración en ms.
    Retorna None si el moof todavía no existe.
    """
    try:
        file_size = os.path.getsize(path)
        with open(path, 'rb') as f:
            pos = 0
            while pos < file_size:
                box_end, btype, data_start = _mp4_next_box(f, pos, file_size)
                if box_end is None:
                    break
                if btype == b'moof':
                    traf_data, traf_end = _mp4_find_box(f, data_start, box_end, b'traf')
                    if traf_data is None:
                        return None

                    # tfhd → default_sample_duration
                    default_dur = 0
                    tfhd_data, _ = _mp4_find_box(f, traf_data, traf_end, b'tfhd')
                    if tfhd_data is not None:
                        f.seek(tfhd_data)
                        f.read(1)
                        fl = f.read(3)
                        flags = (fl[0] << 16) | (fl[1] << 8) | fl[2]
                        f.read(4)  # track_ID
                        if flags & 0x000001: f.read(8)
                        if flags & 0x000002: f.read(4)
                        if flags & 0x000008:
                            default_dur = struct.unpack('>I', f.read(4))[0]

                    # trun → suma de duraciones
                    frag_ticks = 0
                    trun_data, _ = _mp4_find_box(f, traf_data, traf_end, b'trun')
                    if trun_data is not None:
                        f.seek(trun_data)
                        f.read(1)
                        fl = f.read(3)
                        trun_flags  = (fl[0] << 16) | (fl[1] << 8) | fl[2]
                        sample_count = struct.unpack('>I', f.read(4))[0]
                        if trun_flags & 0x001: f.read(4)
                        if trun_flags & 0x004: f.read(4)
                        has_dur   = bool(trun_flags & 0x100)
                        has_size  = bool(trun_flags & 0x200)
                        has_flags = bool(trun_flags & 0x400)
                        has_cts   = bool(trun_flags & 0x800)
                        for _ in range(sample_count):
                            if has_dur:
                                frag_ticks += struct.unpack('>I', f.read(4))[0]
                            else:
                                frag_ticks += default_dur
                            if has_size:  f.read(4)
                            if has_flags: f.read(4)
                            if has_cts:   f.read(4)

                    if frag_ticks > 0:
                        return round(frag_ticks / timescale * 1000)
                    return None
                pos = box_end
    except Exception as e:
        dbg(f"_mp4_first_moof_duration_ms: {e}")
    return None

def compute_anchor_ts(rec_dir, existing_videos):
    """
    Monitorea rec_dir esperando un nuevo .mp4, luego espera el primer moof
    y calcula el anchor timestamp (Unix ms) del primer frame del video.
    Retorna el anchor en ms, o None si falla/timeout.
    """
    # 1. Esperar nuevo archivo .mp4
    new_file = None
    for _ in range(100):   # hasta 10 s
        time.sleep(0.1)
        for candidate in glob.glob(os.path.join(rec_dir, "*.mp4")):
            if candidate not in existing_videos:
                new_file = candidate
                break
        if new_file:
            dbg(f"Nuevo video detectado: {new_file}")
            break

    if not new_file:
        dbg("compute_anchor_ts: no apareció nuevo .mp4 en 10 s")
        return None

    # 2. Leer timescale del mdhd (OBS escribe el moov casi inmediatamente)
    timescale = None
    for _ in range(50):    # hasta 5 s
        time.sleep(0.1)
        timescale = _mp4_read_timescale(new_file)
        if timescale:
            dbg(f"Timescale: {timescale}")
            break

    if not timescale:
        dbg("compute_anchor_ts: no se pudo leer timescale")
        return None

    # 3. Esperar primer moof y calcular anchor
    for _ in range(150):   # hasta 15 s
        time.sleep(0.1)
        dur_ms = _mp4_first_moof_duration_ms(new_file, timescale)
        if dur_ms is not None:
            detection_ts = int(time.time() * 1000)
            anchor_ts    = detection_ts - dur_ms
            dbg(f"Primer moof: dur={dur_ms} ms  detection={detection_ts}  anchor={anchor_ts}")
            return anchor_ts

    dbg("compute_anchor_ts: timeout esperando primer moof (15 s)")
    return None

# ── Main ─────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    action      = sys.argv[1].lower()
    session_dir = sys.argv[2] if len(sys.argv) >= 3 else None
    dbg(f"=== action={action}  session_dir={session_dir} ===")

    if action == "start":

        # ── Lanzar OBS y conectar (con reinicio automatico si WS rechaza) ─
        ws = None
        for launch_attempt in range(2):
            if not obs_is_running():
                dbg(f"OBS no corre — lanzando (intento {launch_attempt + 1})...")
                if not launch_obs():
                    dbg("No se pudo iniciar OBS")
                    sys.exit(1)
            try:
                ws = connect_and_auth()
                dbg("WebSocket conectado OK")
                break
            except Exception as e:
                dbg(f"connect_and_auth fallo ({type(e).__name__}): {e}")
                if launch_attempt == 0:
                    dbg("OBS en mal estado — reiniciando...")
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/IM", "obs64.exe"],
                            capture_output=True, timeout=5
                        )
                    except Exception as kill_err:
                        dbg(f"taskkill error: {kill_err}")
                    time.sleep(2)
                else:
                    dbg("No se pudo conectar al WebSocket tras 2 intentos")
                    sys.exit(1)

        if ws is None:
            dbg("ws es None tras el loop — abortando")
            sys.exit(1)

        try:

            # ── Verificar audio: escritorio activo, mic silenciado ─
            try:
                inputs_resp = send(ws, "GetInputList")
                inputs = (inputs_resp.get("d", {})
                                     .get("responseData", {})
                                     .get("inputs", []))

                desktop_src = next(
                    (i for i in inputs
                     if i.get("inputKind") == "wasapi_output_capture"),
                    None
                )
                if desktop_src is None:
                    dbg("Fuente de audio de escritorio no encontrada — creando")
                    scene_resp = send(ws, "GetCurrentProgramScene")
                    scene_name = (scene_resp.get("d", {})
                                            .get("responseData", {})
                                            .get("currentProgramSceneName", "Escena"))
                    dbg(f"Escena activa: '{scene_name}'")
                    send(ws, "CreateInput", {
                        "sceneName":        scene_name,
                        "inputName":        "Audio del escritorio",
                        "inputKind":        "wasapi_output_capture",
                        "inputSettings":    {"device_id": "default"},
                        "sceneItemEnabled": True
                    })
                    dbg("wasapi_output_capture creado")
                else:
                    name = desktop_src.get("inputName", "Audio del escritorio")
                    send(ws, "SetInputMute", {"inputName": name, "inputMuted": False})
                    dbg(f"Audio escritorio '{name}' — desmuted OK")

                for inp in inputs:
                    if inp.get("inputKind") == "wasapi_input_capture":
                        name = inp.get("inputName", "")
                        send(ws, "SetInputMute", {"inputName": name, "inputMuted": True})
                        dbg(f"Microfono '{name}' — muteado OK")

            except Exception as e:
                dbg(f"Verificacion de audio error (continuando): {e}")

            # ── Capturar directorio de grabaciones y archivos existentes ──
            # (ANTES de StartRecord, para identificar el nuevo archivo)
            rec_dir         = ""
            existing_videos = set()
            try:
                resp    = send(ws, "GetRecordDirectory")
                rec_dir = (resp.get("d", {})
                               .get("responseData", {})
                               .get("recordDirectory", ""))
                dbg(f"GetRecordDirectory: '{rec_dir}'")
                if rec_dir and os.path.isdir(rec_dir):
                    existing_videos = set(glob.glob(os.path.join(rec_dir, "*.mp4")))
                    dbg(f"Videos existentes: {len(existing_videos)}")
            except Exception as e:
                dbg(f"GetRecordDirectory error (continuando): {e}")

            # ── Iniciar grabacion ──────────────────────────────────
            started = False
            for attempt in range(20):
                resp = send(ws, "StartRecord")
                code = resp.get("d", {}).get("requestStatus", {}).get("code", 0)
                dbg(f"StartRecord intento {attempt+1}: code={code}")
                if code == 100:
                    started = True
                    break
                time.sleep(0.5)

            if not started:
                dbg("StartRecord fallo tras 20 intentos")
                ws.close()
                sys.exit(1)

            # ── Esperar evento RecordStateChanged → STARTED ────────
            active = False
            ws.settimeout(10)
            try:
                for _ in range(200):
                    raw    = ws.recv()
                    parsed = json.loads(raw)
                    if parsed.get("op") == 5:
                        ed = parsed.get("d", {})
                        if ed.get("eventType") == "RecordStateChanged":
                            state = ed.get("eventData", {}).get("outputState", "")
                            dbg(f"RecordStateChanged: {state}")
                            if state == "OBS_WEBSOCKET_OUTPUT_STARTED":
                                active = True
                                break
                    elif parsed.get("op") == 7:
                        continue
            except Exception as e:
                dbg(f"Timeout esperando RecordStateChanged: {e} — fallback a polling")
                ws.settimeout(5)
                for i in range(30):
                    time.sleep(0.1)
                    status = send(ws, "GetRecordStatus")
                    active = (status.get("d", {})
                                    .get("responseData", {})
                                    .get("outputActive", False))
                    if active:
                        break

            ws.close()

            if not active:
                dbg("OBS no confirmo grabacion activa")
                sys.exit(1)

            # ── Calcular anchor timestamp via primer moof ──────────
            # Cerramos el WS antes de monitorear el archivo para no
            # bloquear el loop de eventos de OBS.
            # compute_anchor_ts espera el primer fragmento del video y
            # calcula el Unix-ms del primer frame (±50 ms).
            # AHK leerá este valor de ANCHOR_FILE y lo usará como
            # ANCHOR_START, garantizando sync independiente del hardware.
            anchor_ts = None
            if rec_dir and os.path.isdir(rec_dir):
                anchor_ts = compute_anchor_ts(rec_dir, existing_videos)

            if anchor_ts is None:
                anchor_ts = int(time.time() * 1000)
                dbg(f"Fallback anchor_ts = {anchor_ts}")

            try:
                with open(ANCHOR_FILE, "w", encoding="utf-8") as fh:
                    fh.write(str(anchor_ts))
                dbg(f"Anchor escrito en {ANCHOR_FILE}: {anchor_ts}")
            except Exception as e:
                dbg(f"Error escribiendo anchor: {e}")

            dbg("StartRecord OK — anchor listo para AHK")

        except Exception as e:
            dbg(f"Error en start: {e}")
            sys.exit(1)

    elif action == "stop":
        session_start = (os.path.getmtime(session_dir)
                         if session_dir and os.path.isdir(session_dir)
                         else time.time() - 300)
        output_path = None

        try:
            ws   = connect_and_auth()
            resp = send(ws, "StopRecord")
            ws.close()
            output_path = (resp.get("d", {})
                              .get("responseData", {})
                              .get("outputPath", ""))
            dbg(f"outputPath WebSocket: '{output_path}'")
        except Exception as e:
            dbg(f"WebSocket stop fallo: {e} — usando fallback")

        if not output_path or not os.path.isfile(output_path):
            time.sleep(2)
            output_path = find_recent_video(session_start)

        if output_path and session_dir and os.path.isfile(output_path):
            dest  = os.path.join(session_dir, os.path.basename(output_path))
            moved = False
            for attempt in range(20):
                try:
                    shutil.move(output_path, dest)
                    dbg(f"Video movido a: {dest} (intento {attempt+1})")
                    moved = True
                    break
                except (PermissionError, OSError) as e:
                    dbg(f"Reintento {attempt+1} mover video: {e}")
                    time.sleep(0.5)
            if not moved:
                dbg("No se pudo mover el video despues de 20 intentos")
        else:
            dbg(f"No se pudo mover el video. output_path='{output_path}'")

    sys.exit(0)

if __name__ == "__main__":
    main()
