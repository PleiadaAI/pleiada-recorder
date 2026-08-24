"""PLE-170, lado cliente: el enlace "No es este título" reabre el cuestionario.

Verifica que aparezca en el panel resuelto, que suelte la declaración local de
ese ejecutable, y que efectivamente abra el flujo.
"""
import importlib.util
import sys
from pathlib import Path

FILES = Path(r"C:\Users\mspin\Documents\pleiada-recorder\pleiada_installer\files")
sys.path.insert(0, str(FILES))
import tkinter as tk

spec = importlib.util.spec_from_file_location("pleiada_app", FILES / "pleiada_app.pyw")
app_mod = importlib.util.module_from_spec(spec)
sys.modules["pleiada_app"] = app_mod
spec.loader.exec_module(app_mod)
App = app_mod.PleiadaApp

app_mod.DECLARADOS_FILE = Path(__file__).parent / "declarados_corregir.json"
app_mod.DECLARADOS_FILE.unlink(missing_ok=True)

root = tk.Tk()
root.geometry("420x730")
self = object.__new__(App)
self.root = root
self.content = tk.Frame(root, bg=app_mod.BG)
self.content.pack(fill="both", expand=True)
self._det_box = tk.Frame(self.content, bg=app_mod.CARD); self._det_box.pack(fill="x")
self._det_calls_box = tk.Frame(self.content, bg=app_mod.BG); self._det_calls_box.pack(fill="x")
self._rec_btn_idle = tk.Button(self.content, text="  Iniciar grabación", state="disabled")
self._rec_btn_idle.pack()
self._det_state = ""; self._det_msg = ""; self._det_last = "supertux2.exe"
self._ident_intentado = "supertux2.exe"
self._det_exe = "supertux2.exe"; self._det_titulo = "SuperTux v0.7.0"
self._det_gen = 0; self._det_timer_id = None; self._det_active = False
self._dropdown_win = None; self._dropdown_visible = False; self._pkg_anim_id = None
self._update_required = False
self.selected_game = None; self.selected_call = None; self.auth_token = "fake"

abierto = []
self._ident_nombre_view = lambda e, t: abierto.append((e, t))

fallos = []

# El caso de PLE-170: el panel muestra Worm.is con SuperTux corriendo.
self._render_det_resuelto({"name": "Worm.is: The Game", "genre": "Casual",
                           "perspective": "", "mode": "Multiplayer"}, [])
root.update()

etiquetas = []


def recorrer(w):
    for h in w.winfo_children():
        try:
            if h.cget("text"):
                etiquetas.append((h.cget("text"), h))
        except tk.TclError:
            pass
        recorrer(h)


recorrer(self._det_calls_box)
textos = [t for t, _ in etiquetas]
print("textos del panel:")
for t in textos:
    print("   ", repr(t[:64]))

enlace = next((w for t, w in etiquetas if t == "No es este título"), None)
if enlace is None:
    fallos.append("no aparece el enlace 'No es este título'")
else:
    print("\nOK   el enlace está en el panel")

# Había una declaración local para ese exe: tiene que soltarse.
app_mod.save_declarado("supertux2.exe", {"tipo": "steam", "url": "u", "perspectiva": ""})
assert app_mod.load_declarados(), "precondición: la declaración existe"

if enlace is not None:
    enlace.event_generate("<Button-1>")
    root.update()

if abierto != [("supertux2.exe", "SuperTux v0.7.0")]:
    fallos.append(f"no reabrió el cuestionario con el exe correcto: {abierto}")
else:
    print("OK   reabre el cuestionario con exe y ventana correctos")

if app_mod.load_declarados():
    fallos.append("no soltó la declaración local del exe")
else:
    print("OK   soltó la declaración local")

if self._ident_intentado is not None:
    fallos.append("no limpió _ident_intentado (el flujo no se abriría solo)")
else:
    print("OK   limpió la marca de 'ya lo intenté'")

app_mod.DECLARADOS_FILE.unlink(missing_ok=True)
root.destroy()
print()
print("TODO OK" if not fallos else f"{len(fallos)} FALLAS:")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
