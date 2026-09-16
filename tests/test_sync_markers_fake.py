#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_markers.py contra un OBS FALSO (sin websocket): verifica la secuencia de
requests, no la sincronía (eso lo mide smoke_sync_markers.py contra OBS real).

v0.9.21 (PLE-189/190):
  1. La fuente "Pleiada Sync Marker" existe SOLO durante cada flash: CreateInput
     justo antes de encender y RemoveInput justo después de apagar. Entre flashes
     no está en la escena.
  2. `remove_leftovers()` borra la fuente si quedó de un crash y no hace nada si
     no está.
  3. Si OBS muere (los requests lanzan), nada explota y el CSV queda con lo que
     se pudo escribir.

Correr:  python tests/test_sync_markers_fake.py
"""
import io
import os
import sys
import tempfile
import threading
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")   # consola cp1252 rompe con flechas
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "pleiada_installer", "files"))
import sync_markers as SM  # noqa: E402

fallos = []


def check(nombre, cond, detalle=""):
    if cond:
        print("ok     " + nombre)
    else:
        fallos.append(nombre)
        print("FALLA  " + nombre + (": " + detalle if detalle else ""))


class FakeOBS:
    """Simula lo mínimo del websocket de OBS que usa sync_markers."""

    def __init__(self, leftover=False):
        self.inputs = {"Pleiada Sync Marker": False} if leftover else {}
        self.log = []          # (requestType, inputName/None, enabled/None)
        self.muerto = False
        self.next_id = 100
        self.closed = 0

    def connect(self):
        if self.muerto:
            raise ConnectionRefusedError("obs muerto")
        return self

    def close(self):
        self.closed += 1

    def send(self, ws, t, d=None):
        d = d or {}
        if self.muerto:
            raise ConnectionResetError("obs muerto")
        ok = {"requestStatus": {"result": True}, "responseData": {}}
        if t == "GetCurrentProgramScene":
            ok["responseData"] = {"currentProgramSceneName": "Escena"}
        elif t == "GetInputList":
            ok["responseData"] = {"inputs": [{"inputName": n} for n in self.inputs]}
        elif t == "CreateInput":
            self.inputs[d["inputName"]] = d.get("sceneItemEnabled", True)
            self.next_id += 1
            ok["responseData"] = {"sceneItemId": self.next_id}
            self.log.append(("CreateInput", d["inputName"], self.inputs[d["inputName"]]))
        elif t == "RemoveInput":
            self.inputs.pop(d["inputName"], None)
            self.log.append(("RemoveInput", d["inputName"], None))
        elif t == "SetSceneItemEnabled":
            self.inputs[SM.MARKER_INPUT] = d["sceneItemEnabled"]
            self.log.append(("SetSceneItemEnabled", None, d["sceneItemEnabled"]))
        elif t == "SetSceneItemTransform":
            pass
        elif t == "GetSceneItemList":
            ok["responseData"] = {"sceneItems": [{"sceneItemId": 9, "sourceName": "Captura de juego",
                                                  "sceneItemIndex": 0}]}
        elif t == "SetSceneItemIndex":
            # PLE-190: es lo que fuerza a OBS a guardar la escena en disco
            self.log.append(("PERSIST", None, None))
        elif t == "GetRecordStatus":
            ok["responseData"] = {"outputActive": True, "outputDuration": 1234}
        else:
            ok = {"requestStatus": {"result": False, "code": 204}}
        return {"d": ok}


def correr(obs, probe_every_s=0.2, esperar=0.5):
    tmp = Path(tempfile.mkdtemp())
    sm = SM.SyncMarkers(tmp, obs.connect, obs.send, probe_every_s=probe_every_s)
    sm.start()
    threading.Event().wait(esperar)
    return sm, tmp


# ── 1. la fuente solo vive durante el flash ───────────────────────────────────
obs = FakeOBS()
sm, tmp = correr(obs)
check("entre flashes la fuente NO está en la escena", SM.MARKER_INPUT not in obs.inputs,
      repr(obs.inputs))
sm.end_marker()
sec = [(t, e) for t, _, e in obs.log]
esperado = [("CreateInput", False), ("SetSceneItemEnabled", True), ("SetSceneItemEnabled", False),
            ("RemoveInput", None), ("PERSIST", None)] * 2
check("secuencia crear→ON→OFF→borrar→guardar, dos veces", sec == esperado, repr(sec))
check("después de detener no queda la fuente", SM.MARKER_INPUT not in obs.inputs)
check("websocket cerrado", obs.closed >= 1)
csv_txt = (tmp / SM.SYNC_FILE).read_text(encoding="utf-8")
check("csv con start y end", csv_txt.count("MARKER_ON") == 2 and csv_txt.count("MARKER_OFF") == 2
      and ",start" in csv_txt and ",end" in csv_txt, csv_txt)
check("summary cuenta 2 marcadores", sm.summary()["markers"] == 2 and sm.summary()["error"] is None)

# ── 2. resto de un crash anterior ─────────────────────────────────────────────
obs = FakeOBS(leftover=True)
check("remove_leftovers borra la fuente huérfana y fuerza el guardado",
      SM.remove_leftovers(obs.connect, obs.send) is True and SM.MARKER_INPUT not in obs.inputs
      and [t for t, _, _ in obs.log] == ["RemoveInput", "PERSIST"], repr(obs.log))
check("remove_leftovers sin fuente no hace nada",
      SM.remove_leftovers(obs.connect, obs.send) is False
      and not any(t == "RemoveInput" for t, _, _ in obs.log[1:]))
obs.muerto = True
check("remove_leftovers con OBS muerto no lanza", SM.remove_leftovers(obs.connect, obs.send) is False)

# _setup también limpia el resto antes del primer flash
obs = FakeOBS(leftover=True)
sm, tmp = correr(obs)
check("_setup borra el resto (y guarda) antes del primer flash",
      obs.log[:2] == [("RemoveInput", SM.MARKER_INPUT, None), ("PERSIST", None, None)], repr(obs.log[:3]))
sm.end_marker()

# ── 3. cancelar: sin marcador final, sin fuente ───────────────────────────────
obs = FakeOBS()
sm, tmp = correr(obs)
sm.abort()
check("abort: un solo flash y sin fuente",
      sum(1 for t, _, _ in obs.log if t == "CreateInput") == 1 and SM.MARKER_INPUT not in obs.inputs)

# ── 4. OBS muere a mitad de sesión ────────────────────────────────────────────
obs = FakeOBS()
sm, tmp = correr(obs)
obs.muerto = True
threading.Event().wait(0.5)      # las sondas fallan y el hilo termina solo
sm.end_marker(timeout_s=1.0)
check("OBS muerto: end_marker no lanza y el hilo terminó", sm._done.is_set())
check("OBS muerto: solo el marcador de inicio", sm.summary()["markers"] == 1)

print()
if fallos:
    print("FALLARON %d: %s" % (len(fallos), ", ".join(fallos)))
    sys.exit(1)
print("todo ok")
