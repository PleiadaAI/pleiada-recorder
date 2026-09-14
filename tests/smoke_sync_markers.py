"""Smoke del módulo sync_markers contra OBS real: graba ~5 s con el perfil
Pleiada, usa la clase tal cual la usa la app (start → sondas → end_marker), y
verifica en el MP4 que los dos marcadores están y que sus PTS coinciden con los
tiempos del CSV dentro de un cuadro. Borra el video al final.

Uso: python tests/smoke_sync_markers.py   (OBS abierto o lo abre)
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

FILES = Path(__file__).resolve().parents[1] / "pleiada_installer" / "files"
sys.path.insert(0, str(FILES))
import sync_markers as SM  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# conexión mínima (la app usa obs_connect/obs_send propios; acá los equivalentes)
import uuid, websocket  # noqa: E402


def connect():
    ws = websocket.WebSocket(); ws.connect("ws://localhost:4455", timeout=5)
    json.loads(ws.recv()); ws.send(json.dumps({"op": 1, "d": {"rpcVersion": 1}})); json.loads(ws.recv())
    return ws


def send(ws, t, d=None):
    ws.send(json.dumps({"op": 6, "d": {"requestType": t, "requestId": str(uuid.uuid4()), "requestData": d or {}}}))
    while True:
        p = json.loads(ws.recv())
        if p.get("op") == 5:
            continue
        return p


def main():
    sdir = Path(tempfile.mkdtemp(prefix="smoke_sync_"))
    ws = connect()
    for _ in range(20):
        if send(ws, "GetVersion")["d"]["requestStatus"]["result"]:
            break
        time.sleep(1)
    rec_dir = send(ws, "GetRecordDirectory")["d"]["responseData"]["recordDirectory"]
    before = set(os.listdir(rec_dir))
    send(ws, "StartRecord")
    ws.settimeout(10)
    t_anchor = None
    while t_anchor is None:
        p = json.loads(ws.recv())
        if p.get("op") == 5 and p["d"].get("eventType") == "RecordStateChanged" \
                and p["d"]["eventData"].get("outputState") == "OBS_WEBSOCKET_OUTPUT_STARTED":
            t_anchor = int(time.time() * 1000)

    sm = SM.SyncMarkers(sdir, connect, send, dbg=print, probe_every_s=1)
    sm.start()
    time.sleep(4.5)
    t0 = time.time()
    sm.end_marker()
    print(f"end_marker tardó {time.time() - t0:.2f} s; resumen: {sm.summary()}")
    send(ws, "StopRecord")
    for _ in range(300):
        p = json.loads(ws.recv())
        if p.get("op") == 5 and p["d"].get("eventType") == "RecordStateChanged" \
                and p["d"]["eventData"].get("outputState") == "OBS_WEBSOCKET_OUTPUT_STOPPED":
            break
    leftover = [i["sourceName"] for i in send(ws, "GetSceneItemList", {"sceneName": sm.scene or "Escena"})["d"]["responseData"]["sceneItems"]]
    ws.close()
    assert SM.MARKER_INPUT not in leftover, "el marcador quedó en la escena"

    rows = list(csv.DictReader(open(sdir / SM.SYNC_FILE, encoding="utf-8")))
    kinds = [r["event_type"] for r in rows]
    print("csv:", kinds)
    assert kinds.count("MARKER_ON") == 2 and kinds.count("TIMECODE") >= 3

    new = [f for f in os.listdir(rec_dir) if f not in before and f.lower().endswith(".mp4")]
    path = Path(rec_dir) / new[0]
    time.sleep(1)
    pts = [float(x) * 1000 for x in subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time",
         "-of", "csv=p=0", str(path)]).decode().split() if x]
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-vf",
                                   "crop=32:32:0:0,format=gray", "-f", "rawvideo", "-"])
    white = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 32, 32).mean(axis=(1, 2)) > 200
    n = min(len(pts), len(white))
    segs = []
    for i in range(n):
        if white[i]:
            if segs and i == segs[-1][1] + 1:
                segs[-1][1] = i
            else:
                segs.append([i, i])
    ons = [int(r["timestamp_ms"]) - t_anchor for r in rows if r["event_type"] == "MARKER_ON"]
    print("segmentos:", [(a, b, round(pts[a])) for a, b in segs], " pedidos:", ons)
    assert len(segs) == 2, "no se ven dos marcadores en el video"
    errs = [pts[a] - t for (a, _), t in zip(segs, ons)]
    print("video−input por marcador (ms):", [round(e, 1) for e in errs])
    assert all(abs(e) <= 34 for e in errs), "más de 2 cuadros de error"
    keep = sys.argv[1] if len(sys.argv) > 1 else None
    if keep:
        # --keep: dejar mp4 + csv como "sesión" mínima para probar el exporter
        kd = Path(keep); kd.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(kd / path.name))
        shutil.copy2(sdir / SM.SYNC_FILE, kd / SM.SYNC_FILE)
        (kd / "anchor_ms.txt").write_text(str(t_anchor), encoding="utf-8")
        print("guardado en", kd)
    else:
        path.unlink()
    shutil.rmtree(sdir, ignore_errors=True)
    print("SMOKE OK")


if __name__ == "__main__":
    main()
