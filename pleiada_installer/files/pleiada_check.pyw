"""
Pleiada Synch Checker  —  UI v2.1
GUI para verificar la sincronizacion entre video y logs de Pleiada Recorder.
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
from tkinter import filedialog, scrolledtext
import csv
import os
import glob
import threading

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

# ── Constelación Pleiada — coordenadas para el logo ─────────────────────────
LOGO_DOTS  = [(17, 6), (27, 12), (24, 22), (10, 20), (9, 29)]
LOGO_LINES = [(0, 1), (1, 2), (2, 3), (3, 4)]

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

def _mp4_frag_duration_ms(path):
    """
    Calcula la duración real de un MP4 fragmentado (formato OBS)
    parseando los boxes moof → traf → tfhd + tfdt + trun.
    Retorna la duración en milisegundos, o None si falla/no aplica.
    """
    import struct

    def next_box(f, pos, limit):
        if pos + 8 > limit:
            return None, None, None
        f.seek(pos)
        raw = f.read(8)
        if len(raw) < 8:
            return None, None, None
        size     = struct.unpack('>I', raw[:4])[0]
        box_type = raw[4:8]
        if size < 8:
            return None, None, None
        return pos + size, box_type, pos + 8

    def find_box(f, start, end, target):
        """Primer box de tipo `target` dentro de [start, end). Retorna (data_start, box_end)."""
        pos = start
        while True:
            box_end, btype, data_start = next_box(f, pos, end)
            if box_end is None:
                return None, None
            if btype == target:
                return data_start, box_end
            pos = box_end

    try:
        file_size = os.path.getsize(path)

        with open(path, 'rb') as f:
            # ── 1. Timescale desde moov/trak/mdia/mdhd ─────────────
            moov_data, moov_end = find_box(f, 0, min(file_size, 131072), b'moov')
            if moov_data is None:
                return None

            trak_data, trak_end = find_box(f, moov_data, moov_end, b'trak')
            if trak_data is None:
                return None

            mdia_data, mdia_end = find_box(f, trak_data, trak_end, b'mdia')
            if mdia_data is None:
                return None

            mdhd_data, _ = find_box(f, mdia_data, mdia_end, b'mdhd')
            if mdhd_data is None:
                return None

            f.seek(mdhd_data)
            version = struct.unpack('B', f.read(1))[0]
            f.read(3)                     # flags
            f.read(16 if version == 1 else 8)  # creation + modification time
            timescale = struct.unpack('>I', f.read(4))[0]
            if not timescale:
                return None

            # ── 2. Escanear todos los moof y acumular tiempo ────────
            last_end_time = 0
            pos = 0

            while pos < file_size:
                box_end, btype, data_start = next_box(f, pos, file_size)
                if box_end is None:
                    break

                if btype == b'moof':
                    traf_data, traf_end = find_box(f, data_start, box_end, b'traf')
                    if traf_data is None:
                        pos = box_end
                        continue

                    # tfhd → default_sample_duration
                    default_dur = 0
                    tfhd_data, _ = find_box(f, traf_data, traf_end, b'tfhd')
                    if tfhd_data is not None:
                        f.seek(tfhd_data)
                        f.read(1)  # version
                        fl = f.read(3)
                        tfhd_flags = (fl[0] << 16) | (fl[1] << 8) | fl[2]
                        f.read(4)  # track_ID
                        if tfhd_flags & 0x000001: f.read(8)  # base-data-offset
                        if tfhd_flags & 0x000002: f.read(4)  # sample-description-index
                        if tfhd_flags & 0x000008:
                            default_dur = struct.unpack('>I', f.read(4))[0]

                    # tfdt → base_decode_time del fragmento
                    base_decode_time = 0
                    tfdt_data, _ = find_box(f, traf_data, traf_end, b'tfdt')
                    if tfdt_data is not None:
                        f.seek(tfdt_data)
                        tfdt_ver = struct.unpack('B', f.read(1))[0]
                        f.read(3)  # flags
                        if tfdt_ver == 1:
                            base_decode_time = struct.unpack('>Q', f.read(8))[0]
                        else:
                            base_decode_time = struct.unpack('>I', f.read(4))[0]

                    # trun → suma de duraciones de las muestras del fragmento
                    frag_duration = 0
                    trun_data, _ = find_box(f, traf_data, traf_end, b'trun')
                    if trun_data is not None:
                        f.seek(trun_data)
                        f.read(1)  # version
                        fl = f.read(3)
                        trun_flags   = (fl[0] << 16) | (fl[1] << 8) | fl[2]
                        sample_count = struct.unpack('>I', f.read(4))[0]
                        if trun_flags & 0x001: f.read(4)  # data-offset
                        if trun_flags & 0x004: f.read(4)  # first-sample-flags
                        has_dur   = bool(trun_flags & 0x100)
                        has_size  = bool(trun_flags & 0x200)
                        has_sflags= bool(trun_flags & 0x400)
                        has_cts   = bool(trun_flags & 0x800)
                        for _ in range(sample_count):
                            if has_dur:
                                frag_duration += struct.unpack('>I', f.read(4))[0]
                            else:
                                frag_duration += default_dur
                            if has_size:   f.read(4)
                            if has_sflags: f.read(4)
                            if has_cts:    f.read(4)

                    end_time = base_decode_time + frag_duration
                    if end_time > last_end_time:
                        last_end_time = end_time

                pos = box_end

        if last_end_time == 0:
            return None
        return round(last_end_time / timescale * 1000)

    except Exception:
        return None


def check_video(path):
    # Para MP4 de OBS (fragmentado), parsear boxes moof/tfdt/trun da
    # la duración real; CAP_PROP_FRAME_COUNT suele quedar ~1-2 s corto.
    frag_dur_ms = None
    if path.lower().endswith('.mp4'):
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
                "duration_ms": duration_ms, "opencv": True}
    except ImportError:
        return {"opencv": False}

def find_files_in_folder(folder):
    video = None
    for ext in ("*.mp4", "*.mkv", "*.avi", "*.mov", "*.flv"):
        matches = glob.glob(os.path.join(folder, ext))
        if matches:
            video = max(matches, key=os.path.getmtime)
            break
    mouse    = os.path.join(folder, "mouse_log.csv")
    key      = os.path.join(folder, "key_log.csv")
    timeline = os.path.join(folder, "video_timeline.csv")
    return (
        video                                                if video and os.path.isfile(video) else None,
        mouse    if os.path.isfile(mouse)    else None,
        key      if os.path.isfile(key)      else None,
        timeline if os.path.isfile(timeline) else None,
    )

def run_analysis(video, mouse, key, timeline):
    lines = []

    def add(text="", color=TEXT, dot=False):
        lines.append((text, color, dot))

    add("PLEIADA — Reporte de sincronización", ACCENT)
    add()

    results = []
    csv_files = [(mouse, "mouse_log"), (key, "key_log"), (timeline, "video_timeline")]
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

    add("Sincronización entre los 3 CSV", ACCENT)
    starts = [r["start_ts"] for r in results if r.get("start_ts")]
    ends   = [r["end_ts"]   for r in results if r.get("end_ts")]

    if len(starts) == 3:
        diff_start = max(starts) - min(starts)
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

    add()
    add("Video", ACCENT)
    vinfo = check_video(video)
    if not vinfo.get("opencv"):
        add("opencv-python no instalado.", WARN_COLOR, dot=True)
        add("Ejecutá: pip install opencv-python", WARN_COLOR, dot=True)
    else:
        add(f"Archivo        : {os.path.basename(video)}", TEXT, dot=True)
        add(f"FPS            : {vinfo['fps']}", TEXT, dot=True)
        add(f"Frames totales : {vinfo['total_frames']}", TEXT, dot=True)
        add(f"Duración       : {fmt_ms(vinfo['duration_ms'])}", TEXT, dot=True)

        if results and results[0].get("duration_ms") and vinfo.get("duration_ms"):
            csv_dur = results[0]["duration_ms"]
            vid_dur = vinfo["duration_ms"]
            diff    = abs(csv_dur - vid_dur)
            add()
            add("Comparación CSV vs Video", ACCENT)
            add(f"Duración CSV   : {fmt_ms(csv_dur)}", TEXT, dot=True)
            add(f"Duración video : {fmt_ms(vid_dur)}", TEXT, dot=True)
            signed_diff = vid_dur - csv_dur   # + = video más largo
            add(f"Diferencia     : {abs(signed_diff):.0f} ms ({signed_diff/1000:+.2f} seg)", TEXT, dot=True)
            if 0 <= signed_diff <= 3000:
                # El video es ligeramente más largo: OBS grabó un poco
                # después de que el logger se detuvo (flush del encoder).
                # El inicio está correctamente sincronizado.
                tail = signed_diff / 1000
                add(f"SINCRONIZADOS — video extiende {tail:.2f}s post-sesión (normal)", OK_COLOR, dot=True)
            elif abs(signed_diff) < 500:
                add("SINCRONIZADOS — diferencia menor a 500 ms", OK_COLOR, dot=True)
            elif signed_diff < -500:
                add(f"OFFSET — el video inició {abs(signed_diff)/1000:.2f}s tarde respecto al logger", WARN_COLOR, dot=True)
            elif signed_diff > 3000:
                add(f"OFFSET — el video extiende {signed_diff/1000:.1f}s extra (verificar encoder)", WARN_COLOR, dot=True)

    add()
    add("Verificación completada", ACCENT)
    return lines

# ── Logo canvas helper ───────────────────────────────────────────────────────

def draw_logo(canvas, size=36):
    """Dibuja el icono de constelación Pleiada en un Canvas tk."""
    r = 8
    s = size
    # Fondo redondeado via polygon smooth (simula border-radius)
    canvas.create_polygon(
        r, 0,   s-r, 0,
        s, r,   s, s-r,
        s-r, s, r, s,
        0, s-r, 0, r,
        smooth=True, fill="#13132a", outline=ACCENT, width=1
    )
    # Líneas de constelación
    for i, j in LOGO_LINES:
        x1, y1 = LOGO_DOTS[i]
        x2, y2 = LOGO_DOTS[j]
        canvas.create_line(x1, y1, x2, y2,
                           fill=ACCENT, width=1, stipple="gray50")
    # Puntos
    for idx, (x, y) in enumerate(LOGO_DOTS):
        r2 = 2 if idx < 4 else 1.5
        canvas.create_oval(x-r2, y-r2, x+r2, y+r2, fill=ACCENT, outline="")

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
        self.title("Pleiada Synch Checker")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(560, 540)

        self._folder_var = tk.StringVar()
        self._placeholder_active = True

        # ── Icono de ventana ──
        self._icon_img = None
        ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "synch_checker.ico")
        if not os.path.exists(ico_path):
            ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pleiada.ico")
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

        # Logo — usa el PNG real si está disponible, sino fallback a canvas
        LOGO_SIZE = 40
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "pleiada_icon.png")
        logo_shown = False
        if os.path.exists(logo_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(logo_path).convert("RGBA")
                img = img.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
                self._logo_photo = ImageTk.PhotoImage(img)
                tk.Label(hdr_inner, image=self._logo_photo,
                         bg=BG_TITLEBAR, bd=0).pack(side="left", padx=(0, 14))
                logo_shown = True
            except Exception:
                pass
        if not logo_shown:
            logo_cv = tk.Canvas(hdr_inner, width=LOGO_SIZE, height=LOGO_SIZE,
                                bg=BG_TITLEBAR, highlightthickness=0)
            logo_cv.pack(side="left", padx=(0, 14))
            draw_logo(logo_cv, size=LOGO_SIZE)

        # Texto del header
        hdr_text = tk.Frame(hdr_inner, bg=BG_TITLEBAR)
        hdr_text.pack(side="left")
        tk.Label(hdr_text, text="Pleiada Synch Checker",
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
        result_frame = tk.Frame(body,
                                bg=BG_RESULTS,
                                highlightbackground=BORDER,
                                highlightthickness=1)
        result_frame.pack(fill="both", expand=True)

        self.output = scrolledtext.ScrolledText(
            result_frame,
            bg=BG_RESULTS, fg=TEXT,
            font=FONT_MONO,
            relief="flat",
            state="disabled",
            wrap="word",
            insertbackground=TEXT,
            padx=14, pady=12,
            bd=0
        )
        self.output.pack(fill="both", expand=True)

        self.output.vbar.config(
            bg=BG_TITLEBAR,
            troughcolor=BG,
            activebackground=ACCENT,
            width=8,
            relief="flat"
        )

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
        folder = filedialog.askdirectory(title="Seleccionar carpeta de sesión")
        if folder:
            self._placeholder_active = False
            self._entry.config(fg=TEXT)
            self._folder_var.set(folder)

    def _refresh_files(self):
        folder = self._folder_var.get()
        if not folder or not os.path.isdir(folder) or self._placeholder_active:
            self._files_label.config(text="")
            return
        video, mouse, key, timeline = find_files_in_folder(folder)
        lines = [
            f"  {'✔' if video    else '✗'}  Video     : {os.path.basename(video)    if video    else 'no encontrado'}",
            f"  {'✔' if mouse    else '✗'}  mouse_log : {os.path.basename(mouse)    if mouse    else 'no encontrado'}",
            f"  {'✔' if key      else '✗'}  key_log   : {os.path.basename(key)      if key      else 'no encontrado'}",
            f"  {'✔' if timeline else '✗'}  timeline  : {os.path.basename(timeline) if timeline else 'no encontrado'}",
        ]
        self._files_label.config(text="\n".join(lines))

    def _run(self):
        folder = self._folder_var.get()
        if self._placeholder_active or not folder or not os.path.isdir(folder):
            self._write_lines([("Seleccioná una carpeta de sesión.", ERR_COLOR, True)])
            return

        video, mouse, key, timeline = find_files_in_folder(folder)
        missing = []
        if not video:    missing.append("video (.mp4/.mkv)")
        if not mouse:    missing.append("mouse_log.csv")
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
                lines = run_analysis(video, mouse, key, timeline)
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
    app = App()
    app.mainloop()
