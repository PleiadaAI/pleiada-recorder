"""
Gameplay Synch Checker  —  UI v2.1
GUI para verificar la sincronizacion entre video y logs de Gameplay Recorder.
Rediseño visual basado en mockup aprobado (mayo 2026).
"""

# ── Registrar AppUserModelID ANTES de crear la ventana ──────────────────────
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "Pleiada.SynchChecker.1"
    )
except Exception:
    pass

import tkinter as tk
from tkinter import filedialog
import csv
import os
import glob
import threading

# Umbrales y gates compartidos con pleiada_app.pyw (run_sync_check), que es el
# que decide qué se sube. Antes estaban hardcodeados acá con otros valores y el
# verificador contradecía al uploader sobre la misma sesión.
import pleiada_sync_limits as sync_limits

# ── Paleta Pleiada v2 ────────────────────────────────────────────────────────
BG           = "#0d0d18"
BG_TITLEBAR  = "#0a0a12"
BG_INPUT     = "#0d0d1e"
BG_RESULTS   = "#060610"
ACCENT       = "#6B68C4"
ACCENT_HOVER = "#7d7ad0"
ACCENT_DIM   = "rgba(107,104,196,0.15)"
BORDER       = "#2a2850"
TEXT         = "#e8e8f0"
TEXT_DIM     = "#7b78a8"
OK_COLOR     = "#3ecf8e"
WARN_COLOR   = "#febc2e"
ERR_COLOR    = "#e05555"

FONT_TITLE   = ("Segoe UI",    15, "bold")
FONT_SUB     = ("Segoe UI",     9)
FONT_LABEL   = ("Segoe UI",     8, "bold")
FONT_MAIN    = ("Segoe UI",    10)
FONT_MONO    = ("Segoe UI",     9)
FONT_BTN     = ("Segoe UI",    11, "bold")

# ── Lógica de análisis ───────────────────────────────────────────────────────

def fmt_ms(ms):
    if ms is None:
        return "N/A"
    h  =  int(ms) // 3_600_000
    m  = (int(ms) %  3_600_000) // 60_000
    s  = (int(ms) %     60_000) // 1_000
    r  =  int(ms) %      1_000
    return f"{h:02d}:{m:02d}:{s:02d}.{r:03d}"

def check_csv(path, name):
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    total = len(rows)
    start_ts = end_ts = None
    for r in rows:
        et = r.get("event_type", "")
        if et == "ANCHOR_START":
            start_ts = int(r["timestamp_ms"])
        elif et == "ANCHOR_END":
            end_ts = int(r["timestamp_ms"])
    duration_ms = (end_ts - start_ts) if (start_ts and end_ts) else None
    return {"name": name, "total_rows": total,
            "start_ts": start_ts, "end_ts": end_ts,
            "duration_ms": duration_ms}

def _mp4_is_truncated(path):
    """True si el MP4 está truncado/corrupto. Vive en pleiada_sync_limits, que es
    la misma implementación que usa el uploader."""
    return sync_limits.mp4_is_truncated(path)


def _mp4_frag_duration_ms(path):
    """Duración real del MP4 en ms, desde pleiada_sync_limits.

    La copia que vivía acá buscaba el moov en los últimos 512 KB, offset que cae
    dentro del mdat: fallaba en 39 de los 42 MP4 estándar del corpus y caía al
    conteo de frames de OpenCV, que queda ~1-2 s corto. Resultado: el verificador
    calculaba un signed_diff distinto al del uploader sobre la misma sesión."""
    return sync_limits.mp4_duration_ms(path)


def check_video(path):
    # Para MP4 de OBS (fragmentado), parsear boxes moof/tfdt/trun da
    # la duración real; CAP_PROP_FRAME_COUNT suele quedar ~1-2 s corto.
    frag_dur_ms  = None
    is_truncated = False
    if path and path.lower().endswith('.mp4'):
        is_truncated = _mp4_is_truncated(path)
        if not is_truncated:
            frag_dur_ms = _mp4_frag_duration_ms(path)

    try:
        import cv2
        v   = cv2.VideoCapture(path)
        fps = v.get(cv2.CAP_PROP_FPS)
        total_frames = v.get(cv2.CAP_PROP_FRAME_COUNT)
        v.release()
        duration_ms = frag_dur_ms if frag_dur_ms else (
            (total_frames / fps * 1000) if fps > 0 else None
        )
        return {"fps": fps, "total_frames": int(total_frames),
                "duration_ms": duration_ms, "opencv": True,
                "truncated": is_truncated}
    except ImportError:
        return {"opencv": False, "truncated": is_truncated}

def find_files_in_folder(folder):
    video = None
    for ext in ("*.mp4", "*.mkv", "*.avi", "*.mov", "*.flv"):
        matches = glob.glob(os.path.join(folder, ext))
        if matches:
            video = max(matches, key=os.path.getmtime)
            break
    mouse    = os.path.join(folder, "mouse_log.csv")
    delta    = os.path.join(folder, "mouse_delta_log.csv")
    key      = os.path.join(folder, "key_log.csv")
    timeline = os.path.join(folder, "video_timeline.csv")
    return (
        video                                                if video and os.path.isfile(video) else None,
        mouse    if os.path.isfile(mouse)    else None,
        delta    if os.path.isfile(delta)    else None,
        key      if os.path.isfile(key)      else None,
        timeline if os.path.isfile(timeline) else None,
    )

def run_analysis(video, mouse, delta, key, timeline):
    lines = []

    def add(text="", color=TEXT, dot=False):
        lines.append((text, color, dot))

    # Variables de estado para el resumen final
    diff_start    = None    # diferencia entre ANCHOR_START de los 4 CSVs
    signed_diff   = None    # vid_dur - csv_dur (+ = video más largo)
    vinfo         = {}      # resultado de check_video (inicializado defensivamente)
    csv_dur       = None    # media de los 4 CSV, igual que run_sync_check
    act           = None    # actividad de input (None si no se pudo medir)
    short_session = False   # gate PLE-41
    afk           = False   # gate de inactividad continua
    still         = None    # medida de imagen quieta (None si no se pudo leer)
    video_still   = False   # gate de video quieto (negro / congelado)

    add("GAMEPLAY RECORDER — Reporte de sincronización", ACCENT)
    add()

    results = []
    csv_files = [
        (mouse,    "mouse_log"),
        (delta,    "mouse_delta_log"),
        (key,      "key_log"),
        (timeline, "video_timeline"),
    ]
    for path, name in csv_files:
        try:
            r = check_csv(path, name)
            results.append(r)
            add(f"{name}", ACCENT)
            add(f"Filas totales  : {r['total_rows']}", TEXT, dot=True)
            add(f"ANCHOR_START   : {r['start_ts']}", TEXT, dot=True)
            add(f"ANCHOR_END     : {r['end_ts']}", TEXT, dot=True)
            add(f"Duración       : {fmt_ms(r['duration_ms'])}", TEXT, dot=True)
            add()
        except Exception as e:
            add(f"ERROR leyendo {name}: {e}", ERR_COLOR, dot=True)
            add()

    add("Sincronización entre los 4 CSV", ACCENT)
    starts = [r["start_ts"] for r in results if r.get("start_ts")]
    ends   = [r["end_ts"]   for r in results if r.get("end_ts")]

    if len(starts) == 4:
        diff_start = max(starts) - min(starts)  # actualiza variable de estado
        diff_end   = max(ends) - min(ends) if ends else None
        ok_s = diff_start == 0
        ok_e = diff_end == 0 if diff_end is not None else False
        add(f"Diferencia ANCHOR_START : {diff_start} ms",
            OK_COLOR if ok_s else ERR_COLOR, dot=True)
        if diff_end is not None:
            add(f"Diferencia ANCHOR_END   : {diff_end} ms",
                OK_COLOR if ok_e else ERR_COLOR, dot=True)
    else:
        add("No se pudieron analizar todos los CSVs.", ERR_COLOR, dot=True)

    # ── Duración de sesión y actividad ───────────────────────────────────────
    # csv_dur: media de los 4 CSV, igual que run_sync_check. Antes se usaba
    # results[0], que ni siquiera era siempre mouse_log — check_csv() falla y el
    # archivo no entra en results si falta — así que el verificador podía
    # calcular un signed_diff distinto al del uploader sobre la misma sesión.
    csv_dur       = sync_limits.csv_duration_ms(
        [(r.get("start_ts"), r.get("end_ts")) for r in results]
    )
    short_session = sync_limits.is_short_session(csv_dur)

    _folder = next((os.path.dirname(p) for p in (mouse, delta, key, timeline) if p), None)
    if _folder and starts and ends:
        act = sync_limits.activity(_folder, min(starts), max(ends))
    afk = bool(act and sync_limits.is_afk(act.get("longest_idle_seconds"), csv_dur))

    # Gate de input vacío. `act is None` significaba dos cosas muy distintas
    # —"no se pudo medir" y "no hay un solo evento que medir"— y las dos salían
    # acá como una advertencia amarilla que no gateaba nada. El conteo las separa.
    conteo   = sync_limits.contar_eventos_input(_folder) if _folder else None
    sin_input = bool(conteo and sync_limits.is_sin_input(conteo, csv_dur))
    causa     = sync_limits.diagnostico_sin_input(conteo, csv_dur) if conteo else None

    # Gate de video quieto. Mira la IMAGEN, no los inputs: agarra el caso del
    # juego minimizado o el game capture caído, donde OBS graba negro mientras
    # el jugador sigue tecleando.
    if video:
        still = sync_limits.video_stillness(video)
    video_still = sync_limits.is_video_still(still)

    add()
    add("Actividad", ACCENT)
    if sin_input:
        if causa == "captura_bloqueada":
            add("Input       : el video se grabó pero no quedó registrado el teclado ni el mouse",
                ERR_COLOR, dot=True)
        else:
            add("Input       : no hay actividad de teclado ni de mouse en la sesión",
                ERR_COLOR, dot=True)
    elif act is None:
        add("No se pudo evaluar la actividad de input.", WARN_COLOR, dot=True)
    elif afk:
        add("Inactividad : se detectó un período demasiado largo", ERR_COLOR, dot=True)
    else:
        add("Inactividad : dentro de lo esperado", OK_COLOR, dot=True)

    if still is None:
        add("Imagen      : no se pudo evaluar", WARN_COLOR, dot=True)
    elif video_still:
        add("Imagen      : se detectó un período largo sin cambios en pantalla", ERR_COLOR, dot=True)
    else:
        add("Imagen      : dentro de lo esperado", OK_COLOR, dot=True)

    add()
    add("Video", ACCENT)
    vinfo = check_video(video)
    if not vinfo.get("opencv"):
        add("opencv-python no instalado.", WARN_COLOR, dot=True)
        add("Ejecutá: pip install opencv-python", WARN_COLOR, dot=True)
    elif vinfo.get("truncated"):
        add(f"Archivo        : {os.path.basename(video)}", TEXT, dot=True)
        add("Archivo incompleto — OBS cerró sin finalizar la grabación.", ERR_COLOR, dot=True)
        add("El índice del video (moov) no existe. Duración no disponible.", ERR_COLOR, dot=True)
    else:
        add(f"Archivo        : {os.path.basename(video)}", TEXT, dot=True)
        add(f"FPS            : {vinfo['fps']}", TEXT, dot=True)
        add(f"Frames totales : {vinfo['total_frames']}", TEXT, dot=True)
        add(f"Duración       : {fmt_ms(vinfo['duration_ms'])}", TEXT, dot=True)

        if csv_dur and vinfo.get("duration_ms"):
            vid_dur = vinfo["duration_ms"]
            add()
            add("Comparación CSV vs Video", ACCENT)
            add(f"Duración CSV   : {fmt_ms(csv_dur)}", TEXT, dot=True)
            add(f"Duración video : {fmt_ms(vid_dur)}", TEXT, dot=True)
            signed_diff = vid_dur - csv_dur   # + = video más largo  # actualiza variable de estado
            add(f"Diferencia     : {abs(signed_diff):.0f} ms ({signed_diff/1000:+.2f} seg)", TEXT, dot=True)
            # signed_diff = vid_dur - csv_dur
            #   > 0  : video extiende más allá de ANCHOR_END (flush del encoder — normal)
            #   ≈ 0  : video se detiene cerca de ANCHOR_END (normal)
            #   < 0  : video termina antes de ANCHOR_END; puede ser el GOP parcial
            #          final descartado por OBS al detener (hasta ~4-5 s — normal),
            #          o un offset real si la diferencia es mayor.
            if 0 <= signed_diff <= sync_limits.ENCODER_FLUSH_MAX_MS:
                tail = signed_diff / 1000
                add(f"SINCRONIZADOS — video extiende {tail:.2f}s post-sesión (flush del encoder, normal)", OK_COLOR, dot=True)
            elif 0 < signed_diff <= sync_limits.DIFF_MAX_MS:
                # Franja que antes se mostraba como OFFSET pero el uploader ya aceptaba:
                # a esta magnitud la causa no es el flush del encoder (≈1-2 s) sino el
                # anchor_fallback — OBS ya grababa mientras AHK/WebSocket arrancaban.
                add(f"SINCRONIZADOS — el video incluye {signed_diff/1000:.1f}s fuera de la ventana de sesión (arranque tardío del logger, es normal)", OK_COLOR, dot=True)
            elif abs(signed_diff) < sync_limits.NEAR_ZERO_MS:
                add("SINCRONIZADOS — diferencia menor a 500 ms", OK_COLOR, dot=True)
            elif sync_limits.DIFF_MIN_MS <= signed_diff < -sync_limits.NEAR_ZERO_MS:
                # GOP parcial final descartado al detener OBS — normal con keyframe interval de 4 s
                add(f"SINCRONIZADOS — el video terminó {abs(signed_diff)/1000:.2f}s antes de ANCHOR_END (GOP parcial final, normal)", OK_COLOR, dot=True)
            elif signed_diff < sync_limits.DIFF_MIN_MS:
                add(f"OFFSET — el video inició {abs(signed_diff)/1000:.2f}s tarde respecto al logger", WARN_COLOR, dot=True)
            elif signed_diff > sync_limits.DIFF_MAX_MS:
                add(f"OFFSET — el video extiende {signed_diff/1000:.1f}s extra (verificar configuración OBS)", WARN_COLOR, dot=True)

    add()
    # ── Resumen final ────────────────────────────────────────────────────────
    csvs_ok       = diff_start  is not None and diff_start == 0
    video_ok      = signed_diff is not None and sync_limits.video_in_range(signed_diff)
    video_trouble = vinfo.get("truncated", False)

    SEP = "─" * 48

    if short_session:
        # Gate PLE-41 del uploader: sin esto el verificador daba "LISTA PARA
        # ENVIAR" sobre sesiones que run_sync_check rechazaba.
        add(SEP, ERR_COLOR)
        add("⚠   SESIÓN NO APTA PARA ENVIAR", ERR_COLOR)
        add("    La sesión no llegó al mínimo de duración para enviar.", ERR_COLOR)
        add("    Por favor grabá una sesión más larga.", ERR_COLOR)
        add(SEP, ERR_COLOR)

    elif video_still:
        # Gate de video quieto. Va ANTES que el de AFK: si disparan los dos, la
        # causa real suele ser que OBS no estaba capturando, y decirle "estuviste
        # inactivo" lo manda a buscar el problema donde no está.
        add(SEP, ERR_COLOR)
        add("⚠   SESIÓN NO APTA PARA ENVIAR", ERR_COLOR)
        add("    Encontramos un período largo donde la imagen no cambió (pantalla negra o congelada).", ERR_COLOR)
        add("    Descartá esta sesión e iniciá una nueva grabación. Verificá que OBS esté capturando el juego antes de grabar.", ERR_COLOR)
        add(SEP, ERR_COLOR)

    elif sin_input:
        # Gate de input vacío. Va antes que el de AFK: si la captura falló, el
        # jugador jugó toda la sesión y decirle "estuviste inactivo" lo manda a
        # buscar el problema donde no está.
        add(SEP, ERR_COLOR)
        add("⚠   SESIÓN NO APTA PARA ENVIAR", ERR_COLOR)
        if causa == "captura_bloqueada":
            add("    El video se grabó bien, pero no quedó registrado lo que hiciste con el teclado y el mouse.", ERR_COLOR)
            add("    Suele pasar cuando el juego corre como administrador o su anticheat bloquea la captura.", ERR_COLOR)
            add("    Abrí el Recorder como administrador e iniciá una nueva grabación. Si vuelve a pasar con este juego, avisanos.", ERR_COLOR)
        else:
            add("    La sesión no tiene actividad de teclado ni de mouse.", ERR_COLOR)
            add("    Si jugaste con joystick todavía no podemos registrarlo: grabá con teclado y mouse e iniciá una nueva grabación.", ERR_COLOR)
        add(SEP, ERR_COLOR)

    elif afk:
        # Gate de inactividad continua del uploader. El límite exacto no se
        # publica: el mensaje es genérico a propósito.
        add(SEP, ERR_COLOR)
        add("⚠   SESIÓN NO APTA PARA ENVIAR", ERR_COLOR)
        add("    Encontramos un período de inactividad demasiado largo.", ERR_COLOR)
        add("    Descartá esta sesión e iniciá una nueva grabación. Asegurate de grabar puro gameplay con actividad de teclado y mouse.", ERR_COLOR)
        add(SEP, ERR_COLOR)

    elif csvs_ok and video_ok:
        # Todo OK: CSVs + video sincronizados
        add(SEP, OK_COLOR)
        add("✅  SESIÓN LISTA PARA ENVIAR", OK_COLOR)
        add("    Los 5 archivos están sincronizados.", OK_COLOR)
        add(SEP, OK_COLOR)

    elif csvs_ok and video_trouble:
        # CSVs OK pero el video está incompleto o no pudo leerse
        add(SEP, ERR_COLOR)
        add("⚠   SESIÓN NO APTA PARA ENVIAR", ERR_COLOR)
        add("    Los 4 CSV están sincronizados, pero el video no es válido.", ERR_COLOR)
        add("    Descartá esta sesión e iniciá una nueva grabación.", ERR_COLOR)
        add(SEP, ERR_COLOR)

    elif csvs_ok and signed_diff is None:
        # CSVs OK pero duración del video no disponible (no truncado, pero no parseable)
        add(SEP, ACCENT)
        add("    Los 4 CSV están sincronizados.", OK_COLOR)
        add("⚠   Video: duración no disponible — sync con video no verificada.", WARN_COLOR)
        add(SEP, ACCENT)

    elif not csvs_ok:
        # Diferencia entre los ANCHOR de los CSVs
        add(SEP, ERR_COLOR)
        add("⚠   SESIÓN NO APTA PARA ENVIAR", ERR_COLOR)
        add("    Los CSV no están sincronizados entre sí.", ERR_COLOR)
        add("    Descartá esta sesión e iniciá una nueva grabación.", ERR_COLOR)
        add(SEP, ERR_COLOR)

    else:
        # Offset detectado entre CSV y video
        add(SEP, ERR_COLOR)
        add("⚠   SESIÓN NO APTA PARA ENVIAR", ERR_COLOR)
        add("    Se detectó un desfase entre el video y los logs.", ERR_COLOR)
        add("    Descartá esta sesión e iniciá una nueva grabación.", ERR_COLOR)
        add(SEP, ERR_COLOR)

    return lines

# ── Botón redondeado via Canvas ──────────────────────────────────────────────

class _RoundBtn(tk.Canvas):
    """Botón con esquinas redondeadas sin PIL."""

    def __init__(self, parent, text, command,
                 bg=ACCENT_HOVER, hover_bg="#9390dc",
                 disabled_bg=None, fg="white",
                 font=FONT_BTN, radius=14, **kw):
        super().__init__(parent, highlightthickness=0, cursor="hand2",
                         bg=parent["bg"], **kw)
        self._text       = text
        self._command    = command
        self._bg         = bg
        self._hover_bg   = hover_bg
        self._disabled_bg = disabled_bg or BORDER
        self._fg         = fg
        self._font       = font
        self._radius     = radius
        self._enabled    = True
        self._current_bg = bg

        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>",  self._on_click)
        self.bind("<Enter>",     self._on_enter)
        self.bind("<Leave>",     self._on_leave)

    def _on_click(self, e):
        if self._enabled:
            self._command()

    def _on_enter(self, e):
        if self._enabled:
            self._current_bg = self._hover_bg
            self._draw()

    def _on_leave(self, e):
        if self._enabled:
            self._current_bg = self._bg
            self._draw()

    def _draw(self):
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 4 or h < 4:
            return
        r = min(self._radius, h // 2)
        c = self._current_bg
        self.delete("all")
        # Fill: center + side strips
        self.create_rectangle(r, 0, w-r, h, fill=c, outline=c)
        self.create_rectangle(0, r, w, h-r, fill=c, outline=c)
        # Four arcs for corners
        self.create_arc(0,     0,     2*r, 2*r, start=90,  extent=90, fill=c, outline=c)
        self.create_arc(w-2*r, 0,     w,   2*r, start=0,   extent=90, fill=c, outline=c)
        self.create_arc(0,     h-2*r, 2*r, h,   start=180, extent=90, fill=c, outline=c)
        self.create_arc(w-2*r, h-2*r, w,   h,   start=270, extent=90, fill=c, outline=c)
        # Texto centrado
        self.create_text(w // 2, h // 2, text=self._text,
                         fill=self._fg, font=self._font, anchor="center")

    def config(self, **kw):
        redraw = False
        if "text" in kw:
            self._text = kw.pop("text")
            redraw = True
        if "state" in kw:
            state = kw.pop("state")
            self._enabled = (state == "normal")
            self._current_bg = self._bg if self._enabled else self._disabled_bg
            self.config(cursor="hand2" if self._enabled else "arrow")
            redraw = True
        if "bg" in kw:
            self._bg = kw.pop("bg")
            if self._enabled:
                self._current_bg = self._bg
            redraw = True
        if kw:
            super().config(**kw)
        if redraw:
            self._draw()

    # alias para compatibilidad con tk.Button
    configure = config

# ── GUI ──────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gameplay Synch Checker")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(560, 540)

        self._folder_var = tk.StringVar()
        self._placeholder_active = True

        # ── Icono de ventana ──
        self._icon_img = None
        ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "synch_checker.ico")
        if not os.path.exists(ico_path):
            ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gameplay_recorder.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(default=ico_path)
            except Exception:
                pass
            try:
                from PIL import Image, ImageTk
                img = Image.open(ico_path)
                self._tk_icon_big   = ImageTk.PhotoImage(img.resize((64, 64), Image.LANCZOS))
                self._tk_icon_small = ImageTk.PhotoImage(img.resize((32, 32), Image.LANCZOS))
                self.wm_iconphoto(True, self._tk_icon_big, self._tk_icon_small)
            except Exception:
                pass

        self._build_ui()
        self.geometry("680x580")

    # ── Construcción de UI ───────────────────────────────────────────────────

    def _build_ui(self):

        # ── Header ─────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_TITLEBAR)
        header.pack(fill="x")

        hdr_inner = tk.Frame(header, bg=BG_TITLEBAR)
        hdr_inner.pack(side="left", padx=16, pady=14)

        # Logo. Si el PNG falta o Pillow falla, el header va sin logo: antes
        # había un fallback que lo dibujaba en canvas, pero era la constelación
        # vieja — mostrar la marca anterior es peor que no mostrar ninguna.
        LOGO_SIZE = 40
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "gameplay_recorder_icon.png")
        if os.path.exists(logo_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(logo_path).convert("RGBA")
                img = img.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
                self._logo_photo = ImageTk.PhotoImage(img)
                tk.Label(hdr_inner, image=self._logo_photo,
                         bg=BG_TITLEBAR, bd=0).pack(side="left", padx=(0, 14))
            except Exception:
                pass

        # Texto del header
        hdr_text = tk.Frame(hdr_inner, bg=BG_TITLEBAR)
        hdr_text.pack(side="left")
        tk.Label(hdr_text, text="Gameplay Synch Checker",
                 bg=BG_TITLEBAR, fg=TEXT,
                 font=FONT_TITLE).pack(anchor="w")
        tk.Label(hdr_text, text="Verificador de sync entre logs y video",
                 bg=BG_TITLEBAR, fg=TEXT_DIM,
                 font=FONT_SUB).pack(anchor="w")


        # Separador
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # ── Cuerpo principal ────────────────────────────────────────────────
        body = tk.Frame(self, bg=BG, padx=20, pady=18)
        body.pack(fill="both", expand=True)

        # Label carpeta
        tk.Label(body, text="Carpeta de sesión",
                 bg=BG, fg=TEXT_DIM,
                 font=FONT_LABEL).pack(anchor="w", pady=(0, 8))

        # Fila input + botón
        field_row = tk.Frame(body, bg=BG)
        field_row.pack(fill="x", pady=(0, 16))

        input_frame = tk.Frame(field_row, bg=BG_INPUT,
                               highlightbackground=BORDER,
                               highlightthickness=1)
        input_frame.pack(side="left", fill="x", expand=True)

        self._entry = tk.Entry(
            input_frame,
            textvariable=self._folder_var,
            bg=BG_INPUT, fg=TEXT_DIM,
            font=FONT_MAIN,
            relief="flat",
            insertbackground=TEXT,
            bd=0
        )
        self._entry.pack(fill="x", expand=True, ipady=9, padx=12)
        self._entry.insert(0, "Seleccioná una carpeta...")

        # Comportamiento del placeholder
        self._entry.bind("<FocusIn>",  self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)

        self._btn_browse = tk.Button(
            field_row,
            text="Examinar",
            bg="#1a1a30", fg=ACCENT,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            cursor="hand2",
            activebackground="#22223a",
            activeforeground=ACCENT_HOVER,
            highlightbackground=BORDER,
            highlightthickness=1,
            command=self._browse,
            padx=16, pady=0
        )
        self._btn_browse.pack(side="right", padx=(8, 0), ipady=9)

        # Hover en Examinar
        self._btn_browse.bind("<Enter>", lambda e: self._btn_browse.config(bg="#22223a"))
        self._btn_browse.bind("<Leave>", lambda e: self._btn_browse.config(bg="#1a1a30"))

        # ── Archivos detectados ──
        self._files_frame = tk.Frame(body, bg=BG)
        self._files_frame.pack(fill="x", pady=(0, 4))
        self._files_label = tk.Label(
            self._files_frame, text="",
            bg=BG, fg=TEXT_DIM,
            font=FONT_MONO,
            justify="left", anchor="w"
        )
        self._files_label.pack(anchor="w")

        # ── Botón Verificar Sync (redondeado, -20% alto) ──
        self.btn = _RoundBtn(
            body,
            text="Verificar Sync",
            command=self._run,
            bg=ACCENT_HOVER,
            hover_bg="#9390dc",
            radius=14,
            height=34       # ~20% menos que el pady=12 original (~42px → 34px)
        )
        self.btn.pack(fill="x", pady=(8, 18))

        # ── Label Resultados ──
        tk.Label(body, text="Resultados",
                 bg=BG, fg=TEXT_DIM,
                 font=FONT_LABEL).pack(anchor="w", pady=(0, 8))

        # ── Área de resultados ──
        # Se usa Text + Scrollbar manual con grid para evitar que la
        # barra de scroll quede recortada por el borde del frame exterior.
        result_frame = tk.Frame(body,
                                bg=BG_RESULTS,
                                highlightbackground=BORDER,
                                highlightthickness=1)
        result_frame.pack(fill="both", expand=True)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        result_frame.columnconfigure(1, minsize=20)   # PLE-19: columna scrollbar con ancho mínimo garantizado

        _vbar = tk.Scrollbar(
            result_frame,
            bg=BG_TITLEBAR,
            troughcolor=BG,
            activebackground=ACCENT,
            width=10,
            relief="flat",
            bd=0,
            highlightthickness=0
        )
        _vbar.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=4)  # PLE-19: más margen derecho

        self.output = tk.Text(
            result_frame,
            bg=BG_RESULTS, fg=TEXT,
            font=FONT_MONO,
            relief="flat",
            state="disabled",
            wrap="word",
            insertbackground=TEXT,
            padx=14, pady=12,
            bd=0,
            highlightthickness=0,
            yscrollcommand=_vbar.set
        )
        self.output.grid(row=0, column=0, sticky="nsew")
        _vbar.config(command=self.output.yview)

        # Tags de color
        for tag, color in [
            ("ok",     OK_COLOR),
            ("warn",   WARN_COLOR),
            ("err",    ERR_COLOR),
            ("accent", ACCENT),
            ("dim",    TEXT_DIM),
            ("text",   TEXT),
        ]:
            self.output.tag_config(tag, foreground=color)

        self.output.tag_config("dot_ok",   foreground=OK_COLOR)
        self.output.tag_config("dot_warn", foreground=WARN_COLOR)
        self.output.tag_config("dot_err",  foreground=ERR_COLOR)
        self.output.tag_config("dot_info", foreground=ACCENT)

        # Placeholder inicial
        self._write_lines([("Los resultados aparecerán aquí.", TEXT_DIM, False)])

        # Trace de carpeta
        self._folder_var.trace_add("write", lambda *_: self._refresh_files())

    # ── Placeholder ─────────────────────────────────────────────────────────

    def _on_focus_in(self, event):
        if self._placeholder_active:
            self._entry.delete(0, tk.END)
            self._entry.config(fg=TEXT)
            self._placeholder_active = False

    def _on_focus_out(self, event):
        if not self._folder_var.get():
            self._entry.insert(0, "Seleccioná una carpeta...")
            self._entry.config(fg=TEXT_DIM)
            self._placeholder_active = True

    # ── Acciones ─────────────────────────────────────────────────────────────

    def _browse(self):
        # Abrir por default en Pleiada Recordings (donde están todas las sesiones)
        default_dir = os.path.join(os.path.expanduser("~"), "Documents", "Pleiada Recordings")
        if not os.path.isdir(default_dir):
            default_dir = os.path.expanduser("~")
        folder = filedialog.askdirectory(
            title="Seleccionar carpeta de sesión",
            initialdir=default_dir
        )
        if folder:
            self._placeholder_active = False
            self._entry.config(fg=TEXT)
            self._folder_var.set(folder)

    def _refresh_files(self):
        folder = self._folder_var.get()
        if not folder or not os.path.isdir(folder) or self._placeholder_active:
            self._files_label.config(text="")
            return
        video, mouse, delta, key, timeline = find_files_in_folder(folder)
        lines = [
            f"  {'✔' if video    else '✗'}  Video          : {os.path.basename(video)    if video    else 'no encontrado'}",
            f"  {'✔' if mouse    else '✗'}  mouse_log      : {os.path.basename(mouse)    if mouse    else 'no encontrado'}",
            f"  {'✔' if delta    else '✗'}  mouse_delta_log: {os.path.basename(delta)    if delta    else 'no encontrado'}",
            f"  {'✔' if key      else '✗'}  key_log        : {os.path.basename(key)      if key      else 'no encontrado'}",
            f"  {'✔' if timeline else '✗'}  timeline       : {os.path.basename(timeline) if timeline else 'no encontrado'}",
        ]
        self._files_label.config(text="\n".join(lines))

    def _run(self):
        folder = self._folder_var.get()
        if self._placeholder_active or not folder or not os.path.isdir(folder):
            self._write_lines([("Seleccioná una carpeta de sesión.", ERR_COLOR, True)])
            return

        video, mouse, delta, key, timeline = find_files_in_folder(folder)
        missing = []
        if not video:    missing.append("video (.mp4/.mkv)")
        if not mouse:    missing.append("mouse_log.csv")
        if not delta:    missing.append("mouse_delta_log.csv")
        if not key:      missing.append("key_log.csv")
        if not timeline: missing.append("video_timeline.csv")

        if missing:
            lines = [("Archivos no encontrados en la carpeta:", ERR_COLOR, False)]
            for m in missing:
                lines.append((f"— {m}", ERR_COLOR, True))
            self._write_lines(lines)
            return

        self.btn.config(state="disabled", text="Analizando...", bg=BORDER)
        self._write_lines([("Analizando sesión...", TEXT_DIM, True)])

        def worker():
            try:
                lines = run_analysis(video, mouse, delta, key, timeline)
            except Exception as e:
                lines = [(f"Error inesperado: {e}", ERR_COLOR, True)]
            self.after(0, lambda: self._finish(lines))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self, lines):
        self._write_lines(lines)
        self.btn.config(state="normal", text="Verificar Sync", bg=ACCENT_HOVER)

    def _write_lines(self, lines):
        """
        lines: lista de (text, color, dot)
        dot=True: muestra un punto de color antes del texto.
        """
        color_map = {
            OK_COLOR:   ("ok",   "dot_ok"),
            WARN_COLOR: ("warn", "dot_warn"),
            ERR_COLOR:  ("err",  "dot_err"),
            ACCENT:     ("accent","dot_info"),
            TEXT_DIM:   ("dim",  "dot_info"),
        }

        self.output.config(state="normal")
        self.output.delete("1.0", "end")

        for item in lines:
            # Soporte para tuplas de 2 o 3 elementos
            if len(item) == 3:
                text, color, dot = item
            else:
                text, color = item
                dot = False

            tag, dot_tag = color_map.get(color, ("text", "dot_info"))

            if not text:
                self.output.insert("end", "\n")
                continue

            if dot:
                self.output.insert("end", "  ● ", dot_tag)
                self.output.insert("end", text + "\n", tag)
            else:
                # Sección/encabezado — con indicador visual, sin mayúsculas forzadas
                self.output.insert("end", "▸ " + text + "\n", tag)

        self.output.config(state="disabled")
        self.output.see("1.0")


if __name__ == "__main__":
    # PLE-27: Single-instance guard — impide abrir dos Synch Checkers en paralelo.
    _mutex = None
    try:
        import ctypes as _ct2
        _mutex   = _ct2.windll.kernel32.CreateMutexW(None, True, "PleiadaSynchCheckerMutex_v032")
        _last_err = _ct2.windll.kernel32.GetLastError()
        if _last_err == 183:   # ERROR_ALREADY_EXISTS
            import tkinter as _tk2
            import tkinter.messagebox as _mb
            _r = _tk2.Tk(); _r.withdraw()
            _mb.showwarning(
                "Gameplay Synch Checker",
                "Synch Checker ya está abierto.\n\nCerrá la ventana existente antes de abrir una nueva."
            )
            _r.destroy()
            import sys as _sys2; _sys2.exit(0)
    except Exception:
        pass   # si falla el mutex, continuar igual

    # PLE-19: DPI awareness — evita que Windows clipee el scrollbar en pantallas escaladas.
    try:
        import ctypes as _ct_dpi
        try:
            _ct_dpi.windll.shcore.SetProcessDpiAwareness(2)   # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:
            _ct_dpi.windll.user32.SetProcessDPIAware()        # fallback Windows < 8.1
    except Exception:
        pass

    app = App()

    # Liberar mutex al salir
    if _mutex:
        try:
            import ctypes as _ct3
            _ct3.windll.kernel32.ReleaseMutex(_mutex)
            _ct3.windll.kernel32.CloseHandle(_mutex)
        except Exception:
            pass

    app.mainloop()
