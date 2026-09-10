"""PLE-178 (v0.9.18): la oferta del bono desde "Mis grabaciones".

Recorre el camino REAL: lista de grabaciones -> Subir -> pantalla de
confirmación (orden de destino) -> Subir -> tiene que aparecer "Antes de subir
el dataset" con la tarjeta del bono. Backend simulado. Sin capturas: chequea
los textos en pantalla.

Uso:  python tests/smoke_178.py <carpeta_de_salida>
"""
import importlib.util
import json
import sys
from pathlib import Path

FILES = Path(r"C:\Users\mspin\Documents\pleiada-recorder\pleiada_installer\files")
sys.path.insert(0, str(FILES))
import tkinter as tk

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("pleiada_app", FILES / "pleiada_app.pyw")
app_mod = importlib.util.module_from_spec(spec)
sys.modules["pleiada_app"] = app_mod
spec.loader.exec_module(app_mod)
App = app_mod.PleiadaApp
pleiada_api = app_mod.pleiada_api
session_uploader = app_mod.session_uploader

SDIR = OUT / "The Land of Pain_09_09_26__23_10_00 recording"
SDIR.mkdir(exist_ok=True)
(SDIR / "session_metadata.json").write_text(json.dumps({
    "session_id": "sess178", "game": {"title": "The Land of Pain"},
    "input": {"binding_source": "inferred_from_gameplay"},
    "timing": {"duration_ms": 900000}}), encoding="utf-8")
(SDIR / "key_log.csv").write_text("ts,ev,key,vk\n" + "".join(
    f"1,KEY_DOWN,{k},0\n" for k in ["w"] * 30 + ["a"] * 10 + ["d"] * 10 + ["s"] * 5), encoding="utf-8")

CALL = {"call_id": "GA-2026-021", "titulo": "QA · Metadata de controles", "precio_hora_usd": 3.0,
        "remaining_seconds": 7200}
llamadas = []
pleiada_api.my_calls = lambda token: [CALL]
pleiada_api.calls_for_game = lambda token, juego: [CALL]
def _offer(token, game, call_id="", binding_source=""):
    llamadas.append(("metadata_offer", game, call_id, binding_source))
    return {"oferta": "bono", "pct": 25, "monto_usd": 0.75, "motivo": "ok"}
pleiada_api.metadata_offer = _offer
session_uploader.session_info = lambda d: {"files": [], "count": 6, "size_label": "1,2 GB"}

root = tk.Tk()
root.title("smoke 178")
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
self.selected_game = None; self.selected_call = None
self.auth_token = "fake"; self.session_dir = None; self._uploading = False
self.open_calls = [CALL]
self._settings = {}
self._calls_for_game = lambda titulo: [CALL]
fallos = []


def textos(w, acc=None):
    acc = [] if acc is None else acc
    for h in w.winfo_children():
        try:
            t = h.cget("text")
            if t:
                acc.append(t)
        except tk.TclError:
            pass
        textos(h, acc)
    return acc


def boton(texto):
    def _buscar(w):
        for h in w.winfo_children():
            try:
                if isinstance(h, tk.Button) and h.cget("text") == texto:
                    return h
            except tk.TclError:
                pass
            r = _buscar(h)
            if r:
                return r
    return _buscar(self.content)


def p1():
    # Como desde "Mis grabaciones": return_to = la lista.
    self._start_upload_flow(SDIR, lambda: None)
    root.after(900, p2)


def p2():
    ts = textos(self.content)
    if not any("ORDEN DE DESTINO" in t for t in ts):
        fallos.append(f"no llegó a la confirmación: {ts[:6]}")
        return fin()
    b = boton("Subir")
    if not b:
        fallos.append("no hay botón Subir en la confirmación")
        return fin()
    b.invoke()
    root.after(900, p3)


def p3():
    ts = textos(self.content)
    if not any("Antes de subir el dataset" in t for t in ts):
        fallos.append(f"no apareció la oferta: {ts[:8]} | llamadas={llamadas}")
        return fin()
    if not any("25 % de la hora" in t for t in ts):
        fallos.append("la tarjeta del bono no está en la oferta")
    if not llamadas or llamadas[0][2] != "GA-2026-021":
        fallos.append(f"metadata_offer no recibió la orden elegida: {llamadas}")
    print("   oferta desde Mis grabaciones: OK", llamadas)
    fin()


def fin():
    root.after(100, root.destroy)


root.after(200, p1)
root.mainloop()
if fallos:
    print("FALLOS:"); [print("  -", f) for f in fallos]; sys.exit(1)
print("TODO OK")
