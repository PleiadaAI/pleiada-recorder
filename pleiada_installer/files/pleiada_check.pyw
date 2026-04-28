"""
Pleiada Synch Checker
GUI para verificar la sincronizacion entre video y logs de Pleiada Recorder.
"""

# ── Registrar AppUserModelID ANTES de crear la ventana ───────────
# Sin esto, Windows muestra un cuadrado blanco en la taskbar.
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

# ── Colores y estilos ─────────────────────────────────────────────
BG          = "#1a1a2e"
BG_CARD     = "#16213e"
ACCENT      = "#7c6fcd"
ACCENT_DARK = "#5a4fa0"
TEXT        = "#e0e0e0"
TEXT_DIM    = "#888888"
OK_COLOR    = "#4caf50"
WARN_COLOR  = "#ff9800"
ERR_COLOR   = "#f44336"
FONT_MAIN   = ("Segoe UI", 10)
FONT_BOLD   = ("Segoe UI", 10, "bold")
FONT_TITLE  = ("Segoe UI", 14, "bold")
FONT_SUB    = ("Segoe UI", 10)
FONT_MONO   = ("Consolas", 10)

# ── Logica de analisis ────────────────────────────────────────────

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

def check_video(path):
    try:
        import cv2
        v   = cv2.VideoCapture(path)
        fps = v.get(cv2.CAP_PROP_FPS)
        # CAP_PROP_FRAME_COUNT es inexacto en MP4s de OBS —
        # hacer seek al final para obtener el conteo real
        v.set(cv2.CAP_PROP_POS_AVI_RATIO, 1)
        total_frames = v.get(cv2.CAP_PROP_POS_FRAMES)
        v.release()
        duration_ms  = (total_frames / fps * 1000) if fps > 0 else None
        return {"fps": fps, "total_frames": int(total_frames),
                "duration_ms": duration_ms, "opencv": True}
    except ImportError:
        return {"opencv": False}

def find_files_in_folder(folder):
    """
    Dado un folder, devuelve (video_path, mouse_path, key_path, timeline_path).
    video_path puede ser None si no se encuentra.
    """
    video = None
    for ext in ("*.mp4", "*.mkv", "*.avi", "*.mov", "*.flv"):
        matches = glob.glob(os.path.join(folder, ext))
        if matches:
            # Tomar el mas reciente si hay varios
            video = max(matches, key=os.path.getmtime)
            break

    mouse    = os.path.join(folder, "mouse_log.csv")
    key      = os.path.join(folder, "key_log.csv")
    timeline = os.path.join(folder, "video_timeline.csv")

    return (
        video                          if video and os.path.isfile(video)    else None,
        mouse    if os.path.isfile(mouse)    else None,
        key      if os.path.isfile(key)      else None,
        timeline if os.path.isfile(timeline) else None,
    )

def run_analysis(video, mouse, key, timeline):
    lines = []

    def add(text="", color=TEXT):
        lines.append((text, color))

    add("=" * 52)
    add("  PLEIADA — Reporte de sincronizacion", ACCENT)
    add("=" * 52)

    # Analizar CSVs
    results = []
    csv_files = [(mouse, "mouse_log"), (key, "key_log"), (timeline, "video_timeline")]
    for path, name in csv_files:
        try:
            r = check_csv(path, name)
            results.append(r)
            add()
            add(f"  {name}:", ACCENT)
            add(f"    Filas totales  : {r['total_rows']}")
            add(f"    ANCHOR_START   : {r['start_ts']}")
            add(f"    ANCHOR_END     : {r['end_ts']}")
            add(f"    Duracion       : {fmt_ms(r['duration_ms'])}")
        except Exception as e:
            add(f"  ERROR leyendo {name}: {e}", ERR_COLOR)

    # Sync entre CSVs
    add()
    add("-" * 52)
    add("  SINCRONIZACION ENTRE LOS 3 CSV:", ACCENT)
    starts = [r["start_ts"] for r in results if r.get("start_ts")]
    ends   = [r["end_ts"]   for r in results if r.get("end_ts")]

    if len(starts) == 3:
        diff_start = max(starts) - min(starts)
        diff_end   = max(ends)   - min(ends) if ends else None
        ok_s = diff_start == 0
        ok_e = diff_end == 0 if diff_end is not None else False
        add(f"    Diferencia ANCHOR_START : {diff_start} ms",
            OK_COLOR if ok_s else ERR_COLOR)
        add(f"    {'OK' if ok_s else 'DESFASADO'}",
            OK_COLOR if ok_s else ERR_COLOR)
        if diff_end is not None:
            add(f"    Diferencia ANCHOR_END   : {diff_end} ms",
                OK_COLOR if ok_e else ERR_COLOR)
            add(f"    {'OK' if ok_e else 'DESFASADO'}",
                OK_COLOR if ok_e else ERR_COLOR)
    else:
        add("    No se pudieron analizar todos los CSVs.", ERR_COLOR)

    # Analizar video
    add()
    add("  VIDEO:", ACCENT)
    vinfo = check_video(video)
    if not vinfo.get("opencv"):
        add("    opencv-python no instalado.", WARN_COLOR)
        add("    Ejecuta: pip install opencv-python", WARN_COLOR)
    else:
        add(f"    Archivo        : {os.path.basename(video)}")
        add(f"    FPS            : {vinfo['fps']}")
        add(f"    Frames totales : {vinfo['total_frames']}")
        add(f"    Duracion       : {fmt_ms(vinfo['duration_ms'])}")

        if results and results[0].get("duration_ms") and vinfo.get("duration_ms"):
            csv_dur = results[0]["duration_ms"]
            vid_dur = vinfo["duration_ms"]
            diff    = abs(csv_dur - vid_dur)
            add()
            add("-" * 52)
            add("  COMPARACION CSV vs VIDEO:", ACCENT)
            add(f"    Duracion CSV   : {fmt_ms(csv_dur)}")
            add(f"    Duracion video : {fmt_ms(vid_dur)}")
            add(f"    Diferencia     : {diff:.0f} ms ({diff/1000:.2f} seg)")
            if diff < 500:
                add(f"    Resultado      : SINCRONIZADOS", OK_COLOR)
                add(f"    (diferencia menor a 500 ms)", OK_COLOR)
            elif diff < 2000:
                add(f"    Resultado      : OFFSET LEVE", WARN_COLOR)
                add(f"    Ajustar {diff:.0f} ms en post-procesamiento", WARN_COLOR)
            else:
                add(f"    Resultado      : OFFSET CRITICO", ERR_COLOR)
                add(f"    {diff/1000:.1f} seg de desfase — revisar inicio de OBS", ERR_COLOR)

    add()
    add("=" * 52)
    return lines

# ── GUI ───────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pleiada Synch Checker")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(580, 500)

        self._folder_var = tk.StringVar()

        # Cargar icono — taskbar + header
        self._icon_img = None
        ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "synch_checker.ico")
        if not os.path.exists(ico_path):
            ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pleiada.ico")

        if os.path.exists(ico_path):
            try:
                # iconbitmap: establece el icono en la barra de titulo y taskbar
                self.iconbitmap(default=ico_path)
            except Exception:
                pass
            try:
                # wm_iconphoto: refuerza el icono en la taskbar (necesario en algunos sistemas)
                from PIL import Image, ImageTk
                img = Image.open(ico_path)
                img_big   = img.resize((64, 64), Image.LANCZOS)
                img_small = img.resize((32, 32), Image.LANCZOS)
                self._tk_icon_big   = ImageTk.PhotoImage(img_big)
                self._tk_icon_small = ImageTk.PhotoImage(img_small)
                self.wm_iconphoto(True, self._tk_icon_big, self._tk_icon_small)
                # Icono para el header (48px)
                img_hdr = img.resize((48, 48), Image.LANCZOS)
                self._icon_img = ImageTk.PhotoImage(img_hdr)
            except Exception:
                pass

        self._build_ui()
        self.geometry("680x540")

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────
        hdr = tk.Frame(self, bg=ACCENT, pady=14)
        hdr.pack(fill="x")

        hdr_inner = tk.Frame(hdr, bg=ACCENT)
        hdr_inner.pack()

        if self._icon_img:
            tk.Label(hdr_inner, image=self._icon_img, bg=ACCENT).pack(side="left", padx=(0, 12))

        hdr_text = tk.Frame(hdr_inner, bg=ACCENT)
        hdr_text.pack(side="left")
        tk.Label(hdr_text, text="Pleiada Synch Checker",
                 bg=ACCENT, fg="white", font=FONT_TITLE).pack(anchor="w")
        tk.Label(hdr_text, text="Verificador de sync entre los logs y el video generado.",
                 bg=ACCENT, fg="#d0c8ff", font=FONT_SUB).pack(anchor="w")

        # ── Selector de carpeta ──────────────────────────────────
        picker_frame = tk.Frame(self, bg=BG, pady=16, padx=20)
        picker_frame.pack(fill="x")

        tk.Label(picker_frame, text="Carpeta de la sesion:", bg=BG, fg=TEXT_DIM,
                 font=FONT_MAIN).pack(anchor="w", pady=(0, 6))

        entry_row = tk.Frame(picker_frame, bg=BG_CARD, bd=0)
        entry_row.pack(fill="x")

        self._entry = tk.Entry(entry_row, textvariable=self._folder_var,
                               bg="#0f3460", fg=TEXT, font=FONT_MAIN,
                               relief="flat", insertbackground=TEXT)
        self._entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(10, 0))

        btn_browse = tk.Button(entry_row, text="Seleccionar carpeta",
                               bg=ACCENT_DARK, fg="white", font=FONT_MAIN,
                               relief="flat", cursor="hand2",
                               activebackground=ACCENT, activeforeground="white",
                               command=self._browse, padx=12, pady=6)
        btn_browse.pack(side="right", padx=(6, 0))

        # ── Archivos detectados ──────────────────────────────────
        self._files_frame = tk.Frame(self, bg=BG, padx=20)
        self._files_frame.pack(fill="x")

        self._files_label = tk.Label(self._files_frame, text="",
                                     bg=BG, fg=TEXT_DIM, font=FONT_MAIN,
                                     justify="left", anchor="w")
        self._files_label.pack(anchor="w")

        # ── Boton Verificar Sync ─────────────────────────────────
        btn_frame = tk.Frame(self, bg=BG, padx=20, pady=10)
        btn_frame.pack(fill="x")

        self.btn = tk.Button(btn_frame, text="Verificar Sync",
                             bg=ACCENT, fg="white", font=FONT_BOLD,
                             relief="flat", cursor="hand2",
                             activebackground=ACCENT_DARK, activeforeground="white",
                             command=self._run, pady=10)
        self.btn.pack(fill="x")

        # ── Resultados ───────────────────────────────────────────
        res_frame = tk.Frame(self, bg=BG, padx=20, pady=4)
        res_frame.pack(fill="both", expand=True)

        tk.Label(res_frame, text="Resultados", bg=BG, fg=TEXT_DIM,
                 font=FONT_BOLD).pack(anchor="w")

        self.output = scrolledtext.ScrolledText(
            res_frame, bg="#0a0a1a", fg=TEXT, font=FONT_MONO,
            relief="flat", state="disabled", wrap="word",
            insertbackground=TEXT)
        self.output.pack(fill="both", expand=True, pady=(4, 12))

        for tag, color in [("ok", OK_COLOR), ("warn", WARN_COLOR),
                            ("err", ERR_COLOR), ("accent", ACCENT),
                            ("dim", TEXT_DIM), ("text", TEXT)]:
            self.output.tag_config(tag, foreground=color)

        # Actualizar lista de archivos cuando cambia la carpeta
        self._folder_var.trace_add("write", lambda *_: self._refresh_files())

    def _browse(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de sesion")
        if folder:
            self._folder_var.set(folder)

    def _refresh_files(self):
        folder = self._folder_var.get()
        if not folder or not os.path.isdir(folder):
            self._files_label.config(text="")
            return
        video, mouse, key, timeline = find_files_in_folder(folder)
        lines = []
        lines.append(f"  {'✓' if video    else '✗'}  Video     : {os.path.basename(video)    if video    else 'no encontrado'}")
        lines.append(f"  {'✓' if mouse    else '✗'}  mouse_log : {os.path.basename(mouse)    if mouse    else 'no encontrado'}")
        lines.append(f"  {'✓' if key      else '✗'}  key_log   : {os.path.basename(key)      if key      else 'no encontrado'}")
        lines.append(f"  {'✓' if timeline else '✗'}  timeline  : {os.path.basename(timeline) if timeline else 'no encontrado'}")
        self._files_label.config(text="\n".join(lines))

    def _run(self):
        folder = self._folder_var.get()
        if not folder or not os.path.isdir(folder):
            self._write_lines([("  Selecciona una carpeta de sesion.", ERR_COLOR)])
            return

        video, mouse, key, timeline = find_files_in_folder(folder)
        missing = []
        if not video:    missing.append("video (.mp4/.mkv)")
        if not mouse:    missing.append("mouse_log.csv")
        if not key:      missing.append("key_log.csv")
        if not timeline: missing.append("video_timeline.csv")

        if missing:
            msg = "  No se encontraron los siguientes archivos en la carpeta:\n"
            for m in missing:
                msg += f"    - {m}\n"
            self._write_lines([(msg.strip(), ERR_COLOR)])
            return

        self.btn.config(state="disabled", text="Analizando...")
        self._write_lines([("  Analizando...", TEXT_DIM)])

        def worker():
            try:
                lines = run_analysis(video, mouse, key, timeline)
            except Exception as e:
                lines = [(f"  Error inesperado: {e}", ERR_COLOR)]
            self.after(0, lambda: self._finish(lines))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self, lines):
        self._write_lines(lines)
        self.btn.config(state="normal", text="Verificar Sync")

    def _write_lines(self, lines):
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        color_map = {
            OK_COLOR:   "ok",
            WARN_COLOR: "warn",
            ERR_COLOR:  "err",
            ACCENT:     "accent",
            TEXT_DIM:   "dim",
        }
        for text, color in lines:
            tag = color_map.get(color, "text")
            self.output.insert("end", text + "\n", tag)
        self.output.config(state="disabled")
        self.output.see("end")


if __name__ == "__main__":
    app = App()
    app.mainloop()
