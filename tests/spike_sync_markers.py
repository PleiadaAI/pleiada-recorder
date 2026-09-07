"""Spike T0 · capture.sync_verified: ¿podemos poner anclas MEDIDAS entre el reloj
del input y el video sin tocar el juego?

Dos mecanismos, los dos desde el Recorder por websocket:
  A. Marcador visible: un color_source_v3 blanco de 32x32 px en (0,0) de la escena
     de grabación, encendido ~150 ms al arrancar y al parar. Se anota la hora de
     pared (time.time, mismo reloj que ANCHOR_START) del pedido y del ack. Después
     se busca en el MP4 el primer/último frame con la esquina blanca → PTS.
  B. Sondas de timecode: GetRecordStatus.outputDuration (ms del encoder) contra
     time.time() al pedirlo. Invisible, se puede hacer cada N segundos.

Mide: (1) que el marcador aparece en el archivo; (2) la latencia pedido→frame;
(3) si outputDuration coincide con el PTS del archivo (así B valida sin marcador).

Graba ~8 s con el perfil Pleiada en la carpeta de OBS y borra el archivo al final.
Uso: python tests/spike_sync_markers.py   (OBS abierto o lo abre)
"""
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import numpy as np
import websocket

OBS = "ws://localhost:4455"
SCENE = "Escena"
MARK = "Pleiada Sync Marker"


def connect():
    ws = websocket.WebSocket(); ws.connect(OBS, timeout=5)
    json.loads(ws.recv()); ws.send(json.dumps({"op": 1, "d": {"rpcVersion": 1}})); json.loads(ws.recv())
    return ws


def send(ws, t, d=None):
    ws.send(json.dumps({"op": 6, "d": {"requestType": t, "requestId": str(uuid.uuid4()), "requestData": d or {}}}))
    while True:
        p = json.loads(ws.recv())
        if p.get("op") == 5:
            continue
        st = p["d"].get("requestStatus", {})
        if not st.get("result"):
            raise RuntimeError(f"{t}: {st}")
        return p["d"].get("responseData", {}) or {}


def now_ms():
    return time.time() * 1000.0


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # la consola es cp1252
    except Exception:
        pass
    ws = connect()
    for _ in range(20):
        try:
            send(ws, "GetVersion"); break
        except Exception:
            time.sleep(1)
    rec_dir = send(ws, "GetRecordDirectory")["recordDirectory"]
    before = set(os.listdir(rec_dir))

    # marcador: crear deshabilitado
    for i in send(ws, "GetSceneItemList", {"sceneName": SCENE})["sceneItems"]:
        if i["sourceName"] == MARK:
            send(ws, "RemoveInput", {"inputName": MARK})
    r = send(ws, "CreateInput", {"sceneName": SCENE, "inputName": MARK, "inputKind": "color_source_v3",
                                 "inputSettings": {"color": 0xFFFFFFFF, "width": 32, "height": 32},
                                 "sceneItemEnabled": False})
    item = r["sceneItemId"]
    send(ws, "SetSceneItemTransform", {"sceneName": SCENE, "sceneItemId": item,
                                       "sceneItemTransform": {"positionX": 0, "positionY": 0}})

    log = []
    def mark(on):
        t0 = now_ms()
        send(ws, "SetSceneItemEnabled", {"sceneName": SCENE, "sceneItemId": item, "sceneItemEnabled": on})
        t1 = now_ms()
        log.append(("MARKER_ON" if on else "MARKER_OFF", t0, t1))
        return t0, t1

    def probe():
        t0 = now_ms(); st = send(ws, "GetRecordStatus"); t1 = now_ms()
        log.append(("TIMECODE", t0, t1, st["outputDuration"], st["outputTimecode"]))

    # grabar
    t_start_req = now_ms()
    send(ws, "StartRecord")
    ws.settimeout(10)
    t_started = None
    while t_started is None:
        p = json.loads(ws.recv())
        if p.get("op") == 5 and p["d"].get("eventType") == "RecordStateChanged" \
                and p["d"]["eventData"].get("outputState") == "OBS_WEBSOCKET_OUTPUT_STARTED":
            t_started = now_ms()
    print(f"StartRecord→STARTED: {t_started - t_start_req:.0f} ms  (anchor = {t_started:.0f})")

    mark(True); time.sleep(0.15); mark(False)
    for _ in range(6):
        time.sleep(1.0); probe()
    mark(True); time.sleep(0.15); mark(False)
    time.sleep(0.3)
    send(ws, "StopRecord")
    for _ in range(300):
        p = json.loads(ws.recv())
        if p.get("op") == 5 and p["d"].get("eventType") == "RecordStateChanged" \
                and p["d"]["eventData"].get("outputState") == "OBS_WEBSOCKET_OUTPUT_STOPPED":
            break
    send(ws, "RemoveInput", {"inputName": MARK})
    ws.close()

    new = [f for f in os.listdir(rec_dir) if f not in before and f.lower().endswith((".mp4", ".mkv"))]
    assert new, "no apareció el archivo grabado"
    path = Path(rec_dir) / new[0]
    time.sleep(1)
    print("archivo:", path, path.stat().st_size, "bytes")

    # PTS de cada frame + brillo de la esquina 32x32
    pts = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "frame=pts_time", "-of", "csv=p=0", str(path)]).decode().split()
    pts = [float(x) * 1000 for x in pts if x]
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-vf", "crop=32:32:0:0,format=gray",
                                   "-f", "rawvideo", "-"])
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 32, 32)
    bright = frames.mean(axis=(1, 2))
    white = bright > 200
    n = min(len(pts), len(white))
    on_frames = [i for i in range(n) if white[i]]
    print(f"frames: {n}  con marcador: {len(on_frames)}  brillo min/max: {bright.min():.0f}/{bright.max():.0f}")
    if not on_frames:
        print("❌ el marcador NO aparece en el archivo"); path.unlink(); return
    # segmentos de marcador
    segs = []
    for i in on_frames:
        if segs and i == segs[-1][1] + 1:
            segs[-1][1] = i
        else:
            segs.append([i, i])
    print("segmentos (frame_ini, frame_fin, pts_ini_ms, pts_fin_ms):",
          [(a, b, round(pts[a]), round(pts[b])) for a, b in segs])

    ons = [e for e in log if e[0] == "MARKER_ON"]
    for (a, b), (_, t0, t1) in zip(segs, ons):
        video_t = pts[a]
        input_t = t0 - t_started          # ms desde el anchor, como el CSV
        print(f"  marcador: pedido +{input_t:.0f} ms desde anchor → frame {a} pts {video_t:.1f} ms  "
              f"⇒ video−input = {video_t - input_t:+.1f} ms  (ack tardó {t1 - t0:.1f} ms)")
    print("sondas timecode (t_req−anchor vs outputDuration):")
    for e in log:
        if e[0] == "TIMECODE":
            _, t0, t1, dur, tc = e
            print(f"  +{t0 - t_started:8.1f} ms  outputDuration={dur:6d}  Δ={dur - (t0 - t_started):+.1f} ms  ({tc}, rt {t1 - t0:.1f} ms)")
    path.unlink()
    print("archivo de prueba borrado")


if __name__ == "__main__":
    main()
