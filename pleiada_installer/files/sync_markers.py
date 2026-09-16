"""
sync_markers.py — anclas MEDIDAS entre el reloj del input y el video (v0.9.18)

Cierra el gate T0 `capture.sync_verified` del contrato de AI Ranch, que hoy fallamos
porque el único ancla que había era el reloj de pared al recibir OUTPUT_STARTED
(estimado, con la latencia de arranque de OBS adentro).

Dos mecanismos, los dos desde el Recorder por WebSocket, sin tocar el juego:

  1. MARCADOR VISIBLE: un `color_source_v3` blanco de 32x32 px en la esquina (0,0)
     de la escena de grabación. Se enciende ~150 ms al arrancar y ~150 ms antes
     de parar. Se anota la hora de pared (time.time, el MISMO reloj del
     ANCHOR_START que escribe pleiada_app) del pedido y del ack. En el post-
     proceso se busca el primer/último frame con la esquina blanca → PTS del
     archivo. Medido (07-09-2026, spike): el marcador aparece en el archivo y
     video−input = 0 ms al inicio, −8 ms al final; ack 0–2 ms. Es el método
     `visible_input_marker` del schema `clock_sync` de AI Ranch: anclas de fit.

  2. SONDAS DE TIMECODE: `GetRecordStatus.outputDuration` (ms del encoder) contra
     la hora de pared del pedido, cada N segundos. Invisibles. Medido: corren
     ~220 ms detrás de la pared pero con jitter de ±9 ms (medio cuadro), o sea
     que calibradas con el marcador del inicio sirven como anclas de VALIDACIÓN
     a lo largo de toda la sesión y detectan drift.

Salida: `sync_markers.csv` en la carpeta de la sesión:
    timestamp_ms,event_type,ack_ms,detail
    1788816472243,MARKER_ON,1788816472245,start
    1788816472395,MARKER_OFF,1788816472396,start
    1788816533400,TIMECODE,1788816533401,60933
    ...
    1788817000100,MARKER_ON,1788817000101,end
`timestamp_ms` es la hora de pared del pedido; `ack_ms` la de la respuesta de
OBS. Para TIMECODE, `detail` es outputDuration en ms.

El marcador queda en los primeros y últimos ~150 ms del video (9 cuadros a 60 fps),
que ya no son gameplay (el usuario está apretando el hotkey). Se declara en el
metadata para que el post-proceso los excluya o los marque.

NUNCA lanza hacia afuera: es telemetría, no puede tumbar una grabación.
"""
import csv
import threading
import time
import uuid
from pathlib import Path

SYNC_FILE     = "sync_markers.csv"
MARKER_INPUT  = "Pleiada Sync Marker"
MARKER_PX     = 32
MARKER_MS     = 150      # ~9 cuadros a 60 fps: imposible de perder aunque se dupliquen frames
PROBE_EVERY_S = 60


def _now_ms():
    return int(time.time() * 1000)


def _persist_scene(req, scene):
    """Obliga a OBS a GUARDAR la colección de escenas en disco.

    Medido el 16-09-2026 contra OBS 32 (PLE-190): OBS escribe el JSON de la
    colección al crear la fuente y al encenderla, pero NO al borrarla con
    `RemoveInput`. Si después OBS muere, al reabrir carga el JSON viejo y el
    marcador vuelve a aparecer, visible. De los pedidos probados, mover un ítem
    de la escena a su MISMA posición (`SetSceneItemIndex`) dispara el guardado
    y no cambia nada; si la escena quedó vacía, renombrarla ida y vuelta también.
    """
    # RemoveInput es asincrónico del lado de OBS: el ítem de la escena se va unos
    # ms después de la respuesta. Si se guarda antes, el JSON queda con un ítem
    # sin fuente (medido: OBS lo descarta al cargar, pero mejor no dejarlo).
    items = []
    for _ in range(10):
        items = req("GetSceneItemList", {"sceneName": scene}).get("sceneItems") or []
        if not any(i.get("sourceName") == MARKER_INPUT for i in items):
            break
        time.sleep(0.05)
    if items:
        it = items[0]
        req("SetSceneItemIndex", {"sceneName": scene, "sceneItemId": it["sceneItemId"],
                                  "sceneItemIndex": it.get("sceneItemIndex", 0)})
    else:
        req("SetSceneName", {"sceneName": scene, "newSceneName": scene + " "})
        req("SetSceneName", {"sceneName": scene + " ", "newSceneName": scene})


def _remove_if_present(req, scene=None):
    """Borra la fuente del marcador si existe en OBS (en cualquier escena) y
    fuerza el guardado. `req(tipo, datos)` devuelve responseData o lanza.
    Devuelve True si borró."""
    r = req("GetInputList", {"inputKind": "color_source_v3"})
    names = [i.get("inputName") for i in (r.get("inputs") or [])]
    if MARKER_INPUT not in names:
        return False
    req("RemoveInput", {"inputName": MARKER_INPUT})
    if not scene:
        cur = req("GetCurrentProgramScene")
        scene = cur.get("currentProgramSceneName") or cur.get("sceneName")
    _persist_scene(req, scene)
    return True


def remove_leftovers(connect_fn, send_fn, dbg=None):
    """v0.9.21 (PLE-190): si OBS murió a mitad de una grabación, la fuente quedó
    guardada en la escena y al reabrir OBS aparece VISIBLE en Fuentes. Se llama
    desde la app cada vez que OBS vuelve a contestar. Nunca lanza."""
    ws = None
    try:
        ws = connect_fn()

        def _req(t, d=None):
            dd = send_fn(ws, t, d).get("d", {})
            if not dd.get("requestStatus", {}).get("result", False):
                raise RuntimeError(f"{t}: {dd.get('requestStatus')}")
            return dd.get("responseData", {}) or {}

        if _remove_if_present(_req):
            if dbg:
                dbg("sync_markers: fuente huérfana borrada de OBS")
            return True
        return False
    except Exception as e:
        if dbg:
            dbg(f"sync_markers cleanup: {e}")
        return False
    finally:
        try:
            if ws:
                ws.close()
        except Exception:
            pass


class SyncMarkers:
    """Un objeto por grabación. `start()` arranca el hilo; `end_marker()` lo cierra
    con el marcador final, ANTES de StopRecord."""

    def __init__(self, session_dir, connect_fn, send_fn, dbg=None,
                 probe_every_s=PROBE_EVERY_S):
        self.dir = Path(session_dir)
        self.path = self.dir / SYNC_FILE
        self._connect = connect_fn
        self._send = send_fn
        self._dbg = dbg or (lambda m: None)
        self._every = probe_every_s
        self._stop = threading.Event()
        self._done = threading.Event()
        self._lock = threading.Lock()
        self.ws = None
        self.scene = None
        self.item_id = None
        self.counts = {"markers": 0, "probes": 0}
        self.error = None

    # ── csv ─────────────────────────────────────────────────────────────────
    def _log(self, ev, t_req, t_ack, detail=""):
        try:
            new = not self.path.exists()
            with open(self.path, "a", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["timestamp_ms", "event_type", "ack_ms", "detail"])
                w.writerow([t_req, ev, t_ack, detail])
        except Exception as e:
            self._dbg(f"sync_markers log: {e}")

    # ── obs ─────────────────────────────────────────────────────────────────
    def _req(self, t, d=None):
        r = self._send(self.ws, t, d)
        dd = r.get("d", {})
        if not dd.get("requestStatus", {}).get("result", False):
            raise RuntimeError(f"{t}: {dd.get('requestStatus')}")
        return dd.get("responseData", {}) or {}

    def _setup(self):
        self.ws = self._connect()
        cur = self._req("GetCurrentProgramScene")
        self.scene = cur.get("currentProgramSceneName") or cur.get("sceneName")
        # resto de una corrida anterior (crash): se pisa
        _remove_if_present(lambda t, d=None: self._req(t, d), self.scene)

    # v0.9.21 (PLE-189/190): la fuente existe SOLO mientras dura el flash. Hasta la
    # v0.9.20 se creaba oculta al arrancar y se borraba al detener, así que en la
    # lista de Fuentes de OBS se veía "Pleiada Sync Marker" con el ojo apagado
    # durante toda la grabación, y si OBS moría a mitad de sesión quedaba guardada
    # en la escena hasta la próxima grabación.
    def _create(self):
        r = self._req("CreateInput", {
            "sceneName": self.scene, "inputName": MARKER_INPUT, "inputKind": "color_source_v3",
            "inputSettings": {"color": 0xFFFFFFFF, "width": MARKER_PX, "height": MARKER_PX},
            "sceneItemEnabled": False})
        self.item_id = r.get("sceneItemId")
        self._req("SetSceneItemTransform", {"sceneName": self.scene, "sceneItemId": self.item_id,
                                            "sceneItemTransform": {"positionX": 0, "positionY": 0}})

    def _remove(self):
        if self.ws is None or self.item_id is None:
            return
        try:
            self._req("RemoveInput", {"inputName": MARKER_INPUT})
            # PLE-190: sin esto OBS no escribe el JSON y el marcador "resucita"
            # al reabrir OBS después de un crash.
            _persist_scene(lambda t, d=None: self._req(t, d), self.scene)
        except Exception as e:
            self._dbg(f"sync_markers remove: {e}")
        finally:
            self.item_id = None

    def _teardown(self):
        try:
            self._remove()
        except Exception as e:
            self._dbg(f"sync_markers teardown: {e}")
        finally:
            try:
                if self.ws:
                    self.ws.close()
            except Exception:
                pass
            self.ws = None
            self.item_id = None

    def _flash(self, label):
        """Crear, ON, MARKER_MS, OFF, borrar. Devuelve True si se pudo.
        La hora de MARKER_ON es la del pedido de encendido, no la de creación: la
        fuente ya existe (oculta) cuando se toma `t0`, igual que antes."""
        try:
            self._create()
            t0 = _now_ms()
            self._req("SetSceneItemEnabled", {"sceneName": self.scene, "sceneItemId": self.item_id,
                                              "sceneItemEnabled": True})
            self._log("MARKER_ON", t0, _now_ms(), label)
            time.sleep(MARKER_MS / 1000.0)
            t1 = _now_ms()
            self._req("SetSceneItemEnabled", {"sceneName": self.scene, "sceneItemId": self.item_id,
                                              "sceneItemEnabled": False})
            self._log("MARKER_OFF", t1, _now_ms(), label)
            self.counts["markers"] += 1
            return True
        except Exception as e:
            self._dbg(f"sync_markers flash {label}: {e}")
            return False
        finally:
            self._remove()

    def _probe(self):
        t0 = _now_ms()
        st = self._req("GetRecordStatus")
        self._log("TIMECODE", t0, _now_ms(), st.get("outputDuration", ""))
        self.counts["probes"] += 1
        return bool(st.get("outputActive", False))

    # ── ciclo de vida ───────────────────────────────────────────────────────
    def start(self):
        threading.Thread(target=self._run, daemon=True, name="sync_markers").start()

    def _run(self):
        try:
            with self._lock:
                self._setup()
                self._flash("start")
            while not self._stop.wait(self._every):
                with self._lock:
                    if self.ws is None:
                        break
                    try:
                        if not self._probe():
                            break        # OBS dejó de grabar por su cuenta
                    except Exception as e:
                        self._dbg(f"sync_markers probe: {e}")
                        break
        except Exception as e:
            self.error = str(e)
            self._dbg(f"sync_markers run: {e}")
        finally:
            self._done.set()

    def end_marker(self, timeout_s=3.0):
        """Marcador final + limpieza. Llamar ANTES de StopRecord. Bloquea ≤ timeout."""
        self._stop.set()
        got = self._lock.acquire(timeout=timeout_s)
        try:
            # v0.9.21: la fuente ya no vive entre flashes, así que la condición es
            # "hay conexión y escena", no "hay item" (con item_id el final no salía).
            if self.ws is not None and self.scene:
                try:
                    self._probe()
                except Exception:
                    pass
                self._flash("end")
            self._teardown()
        finally:
            if got:
                self._lock.release()

    def abort(self):
        """Grabación cancelada: sin marcador final, solo limpiar."""
        self._stop.set()
        got = self._lock.acquire(timeout=2.0)
        try:
            self._teardown()
        finally:
            if got:
                self._lock.release()

    def summary(self):
        """Para session_metadata.json → timing.sync_markers."""
        return {
            "file": SYNC_FILE if self.path.exists() else None,
            "method": "visible_input_marker",
            "marker_px": MARKER_PX, "marker_position": "top_left",
            "marker_duration_ms": MARKER_MS,
            "markers": self.counts["markers"], "timecode_probes": self.counts["probes"],
            "clock": "host wall clock (time.time), same as ANCHOR_START/ANCHOR_END",
            "notes": ("White square rendered into the recording for ~150 ms right after the "
                      "recording started and right before it stopped; request/ack wall-clock "
                      "times in sync_markers.csv. Match the marked frames' PTS against those "
                      "times to fit the input->video clock mapping. TIMECODE rows are encoder "
                      "outputDuration probes for drift validation."),
            "error": self.error,
        }
