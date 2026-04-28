"""
obs_control.py  V12
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
import subprocess
import glob
import websocket

OBS_HOST     = "localhost"
OBS_PORT     = 4455
OBS_PASSWORD = ""

DEBUG_LOG = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "pleiada_obs_debug.txt")

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
                # Captura OSError, websocket.WebSocketTimeoutException,
                # WebSocketConnectionClosedException, etc.
                dbg(f"connect_and_auth fallo ({type(e).__name__}): {e}")
                if launch_attempt == 0:
                    # WS rechazo la conexion — OBS en mal estado: matar y relanzar
                    dbg("OBS en mal estado — reiniciando...")
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/IM", "obs64.exe"],
                            capture_output=True, timeout=5
                        )
                    except Exception as kill_err:
                        dbg(f"taskkill error: {kill_err}")
                    time.sleep(2)
                    # El loop volvera a hacer launch_obs() en la proxima iteracion
                else:
                    dbg("No se pudo conectar al WebSocket tras 2 intentos")
                    sys.exit(1)

        if ws is None:
            dbg("ws es None tras el loop — abortando")
            sys.exit(1)

        try:

            # ── Verificar audio: escritorio activo, mic silenciado ─
            # wasapi_output_capture = audio del juego/escritorio → desmutear
            # wasapi_input_capture  = microfono               → mutear siempre
            try:
                inputs_resp = send(ws, "GetInputList")
                inputs = (inputs_resp.get("d", {})
                                     .get("responseData", {})
                                     .get("inputs", []))

                # Audio del escritorio: desmutear o crear si no existe
                desktop_src = next(
                    (i for i in inputs
                     if i.get("inputKind") == "wasapi_output_capture"),
                    None
                )
                if desktop_src is None:
                    dbg("Fuente de audio de escritorio no encontrada — creando")
                    # Obtener escena activa para no hardcodear "Escena"
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

                # Microfono: silenciar siempre
                for inp in inputs:
                    if inp.get("inputKind") == "wasapi_input_capture":
                        name = inp.get("inputName", "")
                        send(ws, "SetInputMute", {"inputName": name, "inputMuted": True})
                        dbg(f"Microfono '{name}' — muteado OK")

            except Exception as e:
                dbg(f"Verificacion de audio error (continuando): {e}")

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

            active = False
            for i in range(50):
                time.sleep(0.1)
                status = send(ws, "GetRecordStatus")
                active = (status.get("d", {})
                                .get("responseData", {})
                                .get("outputActive", False))
                dbg(f"GetRecordStatus intento {i+1}: outputActive={active}")
                if active:
                    break

            ws.close()
            if active:
                dbg("StartRecord OK — OBS grabando activamente")
            else:
                dbg("OBS no confirmo outputActive=True tras 50 intentos")
                sys.exit(1)

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
