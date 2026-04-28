"""
configure_obs.py
Configura OBS automaticamente durante la instalacion de Pleiada Recorder:
  1. Activa el WebSocket (sin password, puerto 4455)
  2. Crea el perfil "Pleiada" (MP4, 1080p, 30fps)
  3. Crea la coleccion de escenas "Pleiada":
       - Captura del monitor principal
       - Audio del escritorio (juego)
       - Sin microfono
  4. Apunta global.ini al perfil y escena Pleiada
"""

import json
import os
import sys


# ── 1. WebSocket ─────────────────────────────────────────────────

def configure_websocket():
    appdata = os.environ.get("APPDATA", "")
    ws_dir  = os.path.join(appdata, "obs-studio", "plugin_config", "obs-websocket")
    ws_path = os.path.join(ws_dir, "config.json")
    os.makedirs(ws_dir, exist_ok=True)

    config = {
        "alerts_enabled": False,
        "auth_required":  False,
        "first_load":     False,
        "server_enabled": True,
        "server_password": "",
        "server_port":    4455
    }
    # Preservar password si ya existe
    if os.path.exists(ws_path):
        try:
            with open(ws_path, "r") as f:
                existing = json.load(f)
            if existing.get("server_password"):
                config["server_password"] = existing["server_password"]
                config["auth_required"]   = existing.get("auth_required", False)
        except Exception:
            pass

    with open(ws_path, "w") as f:
        json.dump(config, f, indent=4)


# ── 2. Perfil de grabacion ────────────────────────────────────────

def configure_profile():
    appdata     = os.environ.get("APPDATA", "")
    profile_dir = os.path.join(appdata, "obs-studio", "basic", "profiles", "Pleiada")
    os.makedirs(profile_dir, exist_ok=True)

    basic_ini = (
        "[General]\n"
        "Name=Pleiada\n"
        "\n"
        "[Output]\n"
        "Mode=Simple\n"
        "\n"
        "[SimpleOutput]\n"
        "RecFormat2=mp4\n"
        "VBitrate=2500\n"
        "ABitrate=160\n"
        "RecRB=false\n"
        "\n"
        "[Video]\n"
        "BaseCX=1920\n"
        "BaseCY=1080\n"
        "OutputCX=1920\n"
        "OutputCY=1080\n"
        "FPSType=0\n"
        "FPSCommon=60\n"
        "\n"
        "[Audio]\n"
        "SampleRate=48000\n"
        "ChannelSetup=Stereo\n"
    )
    ini_path = os.path.join(profile_dir, "basic.ini")
    # Solo crear si no existe (respeta configuracion previa del usuario)
    if not os.path.exists(ini_path):
        with open(ini_path, "w", encoding="utf-8") as f:
            f.write(basic_ini)


# ── 3. Coleccion de escenas ───────────────────────────────────────

def configure_scene_collection():
    """
    Escena unica con:
      - monitor_capture  (pantalla principal, con cursor)
      - wasapi_output_capture (audio del escritorio / juego)
      SIN fuente de microfono.
    """
    appdata    = os.environ.get("APPDATA", "")
    scenes_dir = os.path.join(appdata, "obs-studio", "basic", "scenes")
    os.makedirs(scenes_dir, exist_ok=True)

    scene_path = os.path.join(scenes_dir, "Pleiada.json")

    collection = {
        "current_program_scene": "Escena",
        "current_scene":         "Escena",
        "name":                  "Pleiada",
        "current_transition":    "Cortar",
        "transition_duration":   300,
        "groups":     [],
        "modules":    {},
        "scene_order": [{"name": "Escena"}],
        "transitions": [
            {
                "id":           "cut_transition",
                "name":         "Cortar",
                "settings":     {},
                "versioned_id": "cut_transition"
            }
        ],
        "sources": [
            # ── Captura de pantalla principal ──────────────────
            {
                "id":            "monitor_capture",
                "versioned_id":  "monitor_capture",
                "name":          "Pantalla Principal",
                "enabled":       True,
                "flags":         0,
                "mixers":        0,
                "monitoring_type": 0,
                "muted":         False,
                "volume":        1.0,
                "sync":          0,
                "deinterlace_field_order": 0,
                "deinterlace_mode":        0,
                "hotkeys":       {},
                "private_settings": {},
                "push-to-mute":       False,
                "push-to-mute-delay": 0,
                "push-to-talk":       False,
                "push-to-talk-delay": 0,
                "settings": {
                    "capture_cursor": True,
                    "monitor":        0,
                    "method":         0
                }
            },
            # ── Audio del escritorio (juego) — SIN mic ─────────
            {
                "id":            "wasapi_output_capture",
                "versioned_id":  "wasapi_output_capture",
                "name":          "Audio del escritorio",
                "enabled":       True,
                "flags":         0,
                "mixers":        255,
                "monitoring_type": 0,
                "muted":         False,
                "volume":        1.0,
                "sync":          0,
                "deinterlace_field_order": 0,
                "deinterlace_mode":        0,
                "hotkeys":       {},
                "private_settings": {},
                "push-to-mute":       False,
                "push-to-mute-delay": 0,
                "push-to-talk":       False,
                "push-to-talk-delay": 0,
                "settings": {
                    "device_id": "default"
                }
            },
            # ── Escena ─────────────────────────────────────────
            {
                "id":            "scene",
                "versioned_id":  "scene",
                "name":          "Escena",
                "enabled":       True,
                "flags":         0,
                "mixers":        0,
                "monitoring_type": 0,
                "muted":         False,
                "volume":        1.0,
                "sync":          0,
                "deinterlace_field_order": 0,
                "deinterlace_mode":        0,
                "hotkeys":       {"OBSBasic.SelectScene": []},
                "private_settings": {},
                "push-to-mute":       False,
                "push-to-mute-delay": 0,
                "push-to-talk":       False,
                "push-to-talk-delay": 0,
                "settings": {
                    "custom_size": False,
                    "id_counter":  1,
                    "items": [
                        {
                            "id":      1,
                            "name":    "Pantalla Principal",
                            "visible": True,
                            "locked":  False,
                            "align":   5,
                            "pos":     {"x": 0.0, "y": 0.0},
                            "rot":     0.0,
                            "scale":   {"x": 1.0, "y": 1.0},
                            "scale_filter": "disable",
                            "bounds":       {"x": 0.0, "y": 0.0},
                            "bounds_type":  0,
                            "bounds_align": 0,
                            "crop_top":    0,
                            "crop_bottom": 0,
                            "crop_left":   0,
                            "crop_right":  0,
                            "group_item_id": 0,
                            "hide_when_not_showing": False,
                            "private_settings": {}
                        }
                    ]
                }
            }
        ]
    }

    with open(scene_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=4, ensure_ascii=False)


# ── 4. global.ini — perfil y escena activos ───────────────────────

def configure_global():
    appdata     = os.environ.get("APPDATA", "")
    global_path = os.path.join(appdata, "obs-studio", "global.ini")

    target = {
        "Profile":             "Pleiada",
        "ProfileDir":          "Pleiada",
        "SceneCollection":     "Pleiada",
        "SceneCollectionFile": "Pleiada",
    }

    lines = []
    if os.path.exists(global_path):
        with open(global_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    in_basic  = False
    found     = set()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped == "[Basic]":
            in_basic = True
            new_lines.append(line)
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_basic:
                for k, v in target.items():
                    if k not in found:
                        new_lines.append(f"{k}={v}\n")
            in_basic = False
            new_lines.append(line)
            continue
        if in_basic and "=" in stripped:
            key = stripped.split("=")[0].strip()
            if key in target:
                new_lines.append(f"{key}={target[key]}\n")
                found.add(key)
                continue
        new_lines.append(line)

    if in_basic:
        for k, v in target.items():
            if k not in found:
                new_lines.append(f"{k}={v}\n")

    if not any("[Basic]" in l for l in new_lines):
        new_lines.append("\n[Basic]\n")
        for k, v in target.items():
            new_lines.append(f"{k}={v}\n")

    # Suprimir wizard de auto-configuracion en primer launch
    if not any("[General]" in l for l in new_lines):
        new_lines.append("\n[General]\n")
        new_lines.append("FirstRun=false\n")
    else:
        updated = []
        in_general = False
        has_first_run = False
        for line in new_lines:
            s = line.strip()
            if s == "[General]":
                in_general = True
                updated.append(line)
                continue
            if s.startswith("[") and s.endswith("]"):
                if in_general and not has_first_run:
                    updated.append("FirstRun=false\n")
                in_general = False
                updated.append(line)
                continue
            if in_general and s.startswith("FirstRun="):
                updated.append("FirstRun=false\n")
                has_first_run = True
                continue
            updated.append(line)
        if in_general and not has_first_run:
            updated.append("FirstRun=false\n")
        new_lines = updated

    with open(global_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


# ── Main ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        configure_websocket()
        configure_profile()
        configure_scene_collection()
        configure_global()
        sys.exit(0)
    except Exception as e:
        err_path = os.path.join(os.environ.get("TEMP", ""), "pleiada_obs_error.txt")
        with open(err_path, "w", encoding="utf-8") as f:
            f.write(str(e))
        sys.exit(1)
