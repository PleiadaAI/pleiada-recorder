"""v0.9.24: recorre las pantallas de rechazo con datos de prueba y captura cada una.
No habla con el backend. Hay que mirar los pixeles: py_compile no ve los NameError
ni los acentos rotos.

Uso:  python tests/smoke_v0924.py <carpeta_de_salida> <mp4_ultrawide>
"""
import importlib.util
import json
import shutil
import sys
from pathlib import Path

FILES = Path(__file__).resolve().parents[1] / "pleiada_installer" / "files"
sys.path.insert(0, str(FILES))
import tkinter as tk
from PIL import ImageGrab

OUT = Path(sys.argv[1])
MP4 = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("pleiada_app", FILES / "pleiada_app.pyw")
app_mod = importlib.util.module_from_spec(spec)
sys.modules["pleiada_app"] = app_mod
spec.loader.exec_module(app_mod)
App = app_mod.PleiadaApp

SDIR = OUT / "Sesion vieja ultrawide recording"
SDIR.mkdir(exist_ok=True)
shutil.copy(MP4, SDIR / "video.mp4")
(SDIR / "session_metadata.json").write_text(json.dumps({
    "recorder_version": "v0.9.23", "session_id": "abc123", "game": {"title": "Prueba"},
    "timing": {"duration_ms": 2820000}}), encoding="utf-8")
app_mod.write_session_state(SDIR, valid=True, uploaded=False, game="Prueba")

root = tk.Tk()
root.geometry(f"420x{app_mod.WIN_H - 44}+60+60")
root.configure(bg=app_mod.BG)
self = object.__new__(App)
self.root = root
self.content = tk.Frame(root, bg=app_mod.BG)
self.content.pack(fill="both", expand=True)
self._det_state = ""; self._det_msg = ""; self._det_last = None
self._det_gen = 0; self._det_timer_id = None; self._det_active = False
self._dropdown_win = None; self._dropdown_visible = False; self._pkg_anim_id = None
self._update_required = False
self.selected_game = {"game": "Prueba"}; self.selected_call = None
self.auth_token = "fake"; self.session_dir = SDIR; self._uploading = False
self._last_sync_statuses = {k: "ok" for k in ("mouse_log.csv", "mouse_delta_log.csv",
                                              "key_log.csv", "video_timeline.csv",
                                              "metadata")}
self._last_sync_statuses["video"] = "err"
self._settings = {}


def captura(nombre):
    root.update_idletasks()
    x, y = root.winfo_rootx(), root.winfo_rooty()
    ImageGrab.grab((x, y, x + root.winfo_width(), y + root.winfo_height())).save(OUT / nombre)


def paso_1():
    self._show_result(False, {"session_ok": False, "short_session": True}, None, None)
    root.after(700, paso_2)


def paso_2():
    captura("1_corta.png")
    self._show_result(False, {"session_ok": False, "csv_dur": 2820000, "video_dur": 2820000,
                              "signed_diff": 0, "csvs_ok": True,
                              "video_spec_fallas": ["aspect_ratio", "fps"]}, None, None)
    root.after(700, paso_3)


def paso_3():
    captura("2_spec.png")
    self._start_upload_flow(SDIR, lambda: None)
    root.after(2500, paso_4)


def paso_4():
    captura("3_subida.png")
    print("estado:", app_mod.read_session_state(SDIR))
    print("listado:", [s for d, s in app_mod.list_local_sessions() if d == SDIR])
    root.destroy()


root.after(300, paso_1)
root.mainloop()
print("smoke ok")
