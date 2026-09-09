"""Bono por metadata (v0.9.17, ampliado en v0.9.18): recorre las pantallas con datos de
prueba y saca una captura de cada una. No habla con el backend: las llamadas
se stubean. Sirve para ver los píxeles antes de entregar (regla: arrancar la
app y mirar la captura, py_compile no ve los NameError ni los acentos rotos).

Corre con mainloop real y pasos encadenados con `after`, porque la app
despacha los resultados de los threads con `root.after` y eso solo funciona
con el loop de Tk corriendo.

Uso:  python tests/smoke_bono.py <carpeta_de_salida>
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

FILES = Path(r"C:\Users\mspin\Documents\pleiada-recorder\pleiada_installer\files")
sys.path.insert(0, str(FILES))
import tkinter as tk
from PIL import Image, ImageDraw, ImageGrab

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("pleiada_app", FILES / "pleiada_app.pyw")
app_mod = importlib.util.module_from_spec(spec)
sys.modules["pleiada_app"] = app_mod
spec.loader.exec_module(app_mod)
App = app_mod.PleiadaApp
pleiada_api = app_mod.pleiada_api
session_uploader = app_mod.session_uploader

# ── sesión falsa en disco ────────────────────────────────────────────────────
SDIR = OUT / "Delta Force_06_09_26__22_14_03 recording"
SDIR.mkdir(exist_ok=True)
(SDIR / "session_metadata.json").write_text(json.dumps({
    "session_id": "abc123", "game": {"title": "Delta Force"},
    "input": {"binding_source": "inferred_from_gameplay"},
    "timing": {"duration_ms": 2820000}}), encoding="utf-8")
(SDIR / "key_log.csv").write_text(
    "ts,ev,key,vk\n" + "".join(f"1,KEY_DOWN,{k},0\n" for k in
                               ["w"] * 50 + ["a"] * 20 + ["d"] * 20 + ["s"] * 10 +
                               ["LShift"] * 8 + ["r"] * 5 + ["Space"] * 4), encoding="utf-8")

# ── captura de prueba (1920x1080 con texto) ──────────────────────────────────
# Un recorte chico, como los de Win+Shift+S: es lo que rechazaba el mínimo viejo.
img = Image.new("RGB", (360, 260), (24, 24, 40))
d = ImageDraw.Draw(img)
for i, (a, k) in enumerate([("Avanzar", "W"), ("Retroceder", "S"), ("Izquierda", "A"),
                            ("Derecha", "D"), ("Disparar", "Botón izq."), ("Recargar", "R"),
                            ("Interactuar", "F"), ("Saltar", "Espacio")]):
    d.text((20, 20 + i * 28), f"{a:<20} {k}", fill=(230, 230, 240))
CAP = OUT / "captura_prueba.png"
img.save(CAP)

# ── stubs del backend ────────────────────────────────────────────────────────
OFERTA = {"oferta": "bono", "pct": 25, "monto_usd": 0.75}
pleiada_api.metadata_offer = lambda *a, **k: dict(OFERTA)
pleiada_api.submit_key_mapping = lambda *a, **k: {
    "aporte_id": "x", "urls": {"captura_prueba.png": "https://example.invalid/put"}}


class _Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False


session_uploader._open = lambda req, timeout=0: _Ctx()


def _analyze(*a, **k):
    time.sleep(1.5)
    return {"estado": "ok", "binds": 17, "binds_total": 40, "validado": False, "sorteo": False,
            "monto_usd": 0.75}


pleiada_api.analyze_key_mapping = _analyze

# ── esqueleto de la app ──────────────────────────────────────────────────────
root = tk.Tk()
root.title("Gameplay Recorder v0.9.18 (smoke)")
# WIN_H menos los ~44 px de la barra de título propia de la app real, que este
# esqueleto no dibuja: así la captura mide lo mismo que ve el usuario.
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
self.selected_game = {"game": "Delta Force"}; self.selected_call = "GA-2026-021"
self.auth_token = "fake"; self.session_dir = SDIR; self._uploading = False
self._last_sync_statuses = {k: "ok" for k in ("mouse_log.csv", "mouse_delta_log.csv",
                                              "key_log.csv", "video_timeline.csv",
                                              "video", "metadata")}
self._settings = {}
RESULTS = {"session_ok": True, "signed_diff": 12, "csv_dur": 2820000, "video_dur": 2819988,
           "csvs_ok": True}

fallos = []


def _print_window(hwnd):
    """Captura la ventana con PrintWindow(PW_RENDERFULLCONTENT): sirve aunque
    la ventana esté tapada o la sesión bloqueada, que es cuando ImageGrab
    devuelve el fondo de pantalla en vez de la app."""
    import ctypes
    from ctypes import wintypes
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    hdc = user32.GetWindowDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    user32.PrintWindow(hwnd, mdc, 2)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]
    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth, bi.biHeight, bi.biPlanes, bi.biBitCount = w, -h, 1, 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    gdi32.DeleteObject(bmp); gdi32.DeleteDC(mdc); user32.ReleaseDC(hwnd, hdc)
    return Image.frombuffer("RGB", (w, h), buf.raw, "raw", "BGRX", 0, 1)


def shot(nombre):
    root.update_idletasks()
    hwnd = int(root.winfo_id())
    # winfo_id es el frame interno; el toplevel real es su padre.
    import ctypes
    parent = ctypes.windll.user32.GetParent(hwnd)
    _print_window(parent or hwnd).save(OUT / f"{nombre}.png")
    print("   captura", nombre)


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


def esperar(cond, texto):
    if not any(cond(t) for t in textos(self.content)):
        fallos.append(texto)


# ── pasos, encadenados con after ─────────────────────────────────────────────
def p1():
    self._show_result(True, RESULTS, None)
    root.after(700, p2)


def p2():
    esperar(lambda t: "25 % de la hora" in t, "A: no aparece la tarjeta del bono")
    shot("A_resultado_bono")
    OFERTA.update({"oferta": "sorteo", "pct": 0, "monto_usd": 0})
    self._bono = None; self.selected_call = None
    self._show_result(True, RESULTS, None)
    root.after(700, p3)


def p3():
    esperar(lambda t: "sorteo mensual" in t, "A2: no aparece la tarjeta del sorteo")
    shot("A2_resultado_sorteo")
    OFERTA.update({"oferta": "bono", "pct": 25, "monto_usd": 0.75})
    self._bono = None; self.selected_call = "GA-2026-021"
    self._show_result(True, RESULTS, None)
    root.after(700, p4)


def p4():
    self._bono_antes_de_subir()
    root.after(400, p5)


def p5():
    shot("B_modal")
    for w in root.winfo_children():
        if isinstance(w, tk.Toplevel):
            try:
                _print_window(int(w.winfo_id())).save(OUT / "B_modal_toplevel.png")
                print("   captura B_modal_toplevel")
            except Exception as ex:
                fallos.append(f"B: no se pudo capturar el modal: {ex}")
            w.grab_release(); w.destroy()
    self._bono_paso1()
    root.after(300, p6)


def p6():
    esperar(lambda t: "dos personas" in t, "C: falta el recuadro de dos personas")
    shot("C_paso1")
    self._bono_paso2()
    root.after(300, p7)


def p7():
    shot("D_paso2_vacio")
    e = self._bono_agregar_imagen(str(CAP))
    if e:
        fallos.append(f"D: la captura de prueba fue rechazada: {e}")
    e2 = self._bono_agregar_imagen(str(CAP))
    if not e2 or "ya está cargada" not in e2:
        fallos.append(f"D: no detectó la imagen repetida: {e2}")
    self._bono_paso2()
    root.after(300, p8)


def p8():
    esperar(lambda t: "1 de 10" in t, "D: el contador no dice 1 de 10")
    shot("D_paso2_con_imagen")
    self._bono_paso3()
    root.after(300, p9)


def p9():
    esperar(lambda t: "OBLIGATORIO" in t, "E: falta el recuadro obligatorio")
    shot("E_paso3")
    self._bono_analizar()
    root.after(600, p10)


def p10():
    shot("F_analizando")
    root.after(2200, p11)


def p11():
    esperar(lambda t: "Controles recibidos" in t, "G: no llegó a Controles recibidos")
    shot("G_recibidos")
    self._bono_error("sensitivity", "En lo que enviaste vimos la pantalla de sensibilidad, "
                     "no la de controles de teclado.")
    root.after(300, p12)


def p12():
    esperar(lambda t: "Intento 1 de 3" in t, "F2: no muestra el intento")
    shot("F2_error")
    # v0.9.18 (PLE-176): el rechazo por piso trae el detalle de qué faltó.
    self._bono_error("piso", "No encontramos la información mínima: las cuatro teclas de "
                     "movimiento, el botón principal del mouse y al menos ocho controles.",
                     detalle_piso="Falta el botón principal del mouse.")
    root.after(300, p13)


def p13():
    esperar(lambda t: "Falta el botón principal del mouse." in t, "F2 piso: no muestra el detalle")
    esperar(lambda t: "Intento 2 de 3" in t, "F2 piso: no cuenta el intento")
    shot("F2_error_piso_detalle")
    # v0.9.18 (PLE-178): la oferta desde "Mis grabaciones", con la orden ya elegida.
    self._bono = None
    self._bono_antes_de_subir_guardada(SDIR, lambda: fallos.append("H: return_to inesperado"),
                                       "GA-2026-021")
    root.after(700, p14)


def p14():
    esperar(lambda t: "Antes de subir el dataset" in t, "H: no aparece la pantalla previa")
    esperar(lambda t: "25 % de la hora" in t, "H: falta la tarjeta del bono")
    esperar(lambda t: t == "Subir sin metadata", "H: falta el botón de subir sin metadata")
    shot("H_oferta_guardada")
    self._bono_paso1()
    root.after(300, p15)


def p15():
    esperar(lambda t: "dos personas" in t, "H→C: no llegó al paso 1")
    self._bono_volver_al_resultado()
    root.after(300, p16)


def p16():
    esperar(lambda t: "Antes de subir el dataset" in t, "C→H: Volver no regresó a la oferta")
    shot("H_oferta_guardada_volver")
    if not self._bono.get("continuar"):
        fallos.append("H: falta el continuar de la subida")
    # G con el total leído (PLE-179).
    self._bono_ok({"binds": 17, "binds_total": 40})
    root.after(300, p17)


def p17():
    esperar(lambda t: "Leímos 40 controles de Delta Force, 17 de juego" in t,
            "G: no muestra el total leído")
    shot("G_recibidos_total")
    root.after(100, fin)


def fin():
    root.destroy()


root.after(200, p1)
root.mainloop()
print()
print("TODO OK" if not fallos else f"{len(fallos)} FALLAS:")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
