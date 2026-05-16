"""
pleiada_setup_wizard.pyw  V14
Wizard de configuracion inicial — se lanza al finalizar la instalacion.
3 paginas: OBS setup / Prueba de grabacion / Synch Checker.
"""

import tkinter as tk
import webbrowser
import sys
import os

# ── Colores ──────────────────────────────────────────────────────
BG      = "#1a1a2e"
BG2     = "#16213e"
ACCENT  = "#7c6fcd"
TEXT    = "#E0E0E0"
SUBTEXT = "#a0a0c0"
BTN_BG  = "#7c6fcd"
BTN_FG  = "#ffffff"
BTN_HOV = "#9c8fe0"
SEP     = "#2a2a4e"
GREEN   = "#4caf50"
LINK    = "#9c8fe0"

WIN_W = 580
WIN_H = 630

PAGES = [
    {
        "step": "1 / 3",
        "title": "Configuración inicial con OBS",
        "body": (
            "Antes de tu primera grabación tenés que configurar OBS una sola vez\n"
            "(si ya lo tenías instalado, igualmente tenés que realizar estos ajustes).\n\n"
            "1.  Iniciá el juego que quieras grabar y dejalo en pausa donde\n"
            "     quieras iniciar la grabación.\n\n"
            "2.  Si lo acabás de instalar por primera vez, abrí OBS y seleccioná\n"
            "     \"Optimizar solo para grabación...\" y dale Siguiente. Luego\n"
            "     asegurate que la resolución sea al menos 1080 y los FPS sean\n"
            "     \"60 o 30 pero en alta resolución\".\n\n"
            "3.  Sin importar si lo tenías instalado o no, en la sección Fuentes\n"
            "     (abajo a la izquierda) hacé clic en el  +  , seleccioná\n"
            "     \"Captura de Juego\"  y dejá el nombre que aparece. Luego en\n"
            "     Modo seleccioná  \"Capturar Ventana específica\"  y en Ventana\n"
            "     seleccioná la que esté mostrando tu juego ya iniciado.\n\n"
            "4.  En la sección Mezclador de audio (abajo al centro), si aparece\n"
            "     una sección de nombre \"Mic/Aux\", silenciala haciendo clic en\n"
            "     el 🔊 hasta que quede rojo (muteado)."
        ),
        "listo": "Solo tenés que hacer esto una vez.",
    },
    {
        "step": "2 / 3",
        "title": "Prueba inicial",
        "body": (
            "Ahora vamos a hacer una grabación corta para verificar que todo funciona bien.\n\n"
            "1.  Si no iniciaste el juego en los pasos anteriores, hacelo ahora\n"
            "     y dejalo en pausa.\n\n"
            "2.  Hacé doble clic en el ícono  Pleiada Recorder  del escritorio.\n"
            "     Aparece una pequeña ventana flotante — podés moverla\n"
            "     arrastrando el encabezado.\n\n"
            "3.  Hacé clic en el botón  Iniciar grabación  para comenzar.\n"
            "     El botón cambia a  Detener grabación  y el contador empieza a correr.\n\n"
            "4.  Jugá unos 60 segundos y luego hacé clic en  Detener grabación.\n\n"
            "5.  Los archivos quedan guardados automáticamente en:\n"
            "     Documentos  ›  Pleiada Recordings"
        ),
    },
    {
        "step": "3 / 3",
        "title": "SYNCH CHECKER — Verificar sincronización",
        "body": (
            "Después de cada sesión, verificá que el video y los logs\n"
            "quedaron bien sincronizados.\n\n"
            "1.  Hacé doble clic en el ícono  Synch Checker  del escritorio.\n\n"
            "2.  Hacé clic en  Seleccionar carpeta  y elegí la carpeta de la\n"
            "     sesión (por ejemplo:  2026-04-25 13-09-07 recording ).\n\n"
            "3.  Hacé clic en  Verificar Sync.\n\n"
            "Resultados posibles:\n"
            "  ✅  SINCRONIZADOS  →  la sesión está bien, podés entregarla.\n"
            "  ⚠   OFFSET          →  desfase detectado, la sesión puede no ser usable.\n\n"
            "¿Dudas? Visitá  "
        ),
        "link": "https://www.pleiada.ai/faqs",
        "link_text": "www.pleiada.ai/faqs",
    },
]


def find_pleiada_ico():
    """Busca pleiada.ico junto al script, con multiples fallbacks."""
    candidates = []
    try:
        # __file__ es lo mas confiable cuando Python ejecuta el .pyw directamente
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pleiada.ico"))
    except Exception:
        pass
    try:
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "pleiada.ico"))
    except Exception:
        pass
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


class PleiadaWizard:
    def __init__(self, root):
        self.root = root
        self.page = 0
        self._build_window()
        self._show_page(0)

    # ── Construccion de la ventana ───────────────────────────────

    def _build_window(self):
        root = self.root
        root.title("Pleiada Recorder — Configuración inicial")
        root.configure(bg=BG)
        root.resizable(False, False)

        # Centrar en pantalla
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x  = (sw - WIN_W) // 2
        y  = (sh - WIN_H) // 2
        root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

        # ── Barra de acento superior ─────────────────────────────
        tk.Frame(root, bg=ACCENT, height=4).pack(fill="x", side="top")

        # ── Cabecera ─────────────────────────────────────────────
        header = tk.Frame(root, bg=BG, pady=12)
        header.pack(fill="x", side="top")

        # Emoji de monitor — tamaño grande para que sea visible
        tk.Label(
            header, text="🖵",
            font=("Segoe UI Emoji", 24),
            bg=BG, fg=ACCENT
        ).pack(side="left", padx=(20, 2))
        tk.Label(
            header, text="🖱 ⌨",
            font=("Segoe UI Emoji", 16),
            bg=BG, fg=ACCENT
        ).pack(side="left", padx=(0, 10))
        tk.Label(
            header, text="Pleiada Recorder",
            font=("Segoe UI", 14, "bold"), bg=BG, fg=TEXT
        ).pack(side="left")

        # Separador cabecera / contenido
        tk.Frame(root, bg=SEP, height=1).pack(fill="x", side="top")

        # ── Footer — se packea ANTES que el content para garantizar visibilidad ──
        tk.Frame(root, bg=SEP, height=1).pack(fill="x", side="bottom")
        footer = tk.Frame(root, bg=BG, pady=12, padx=24)
        footer.pack(fill="x", side="bottom")

        self.lbl_step = tk.Label(
            footer, text="",
            font=("Segoe UI", 9), bg=BG, fg=SUBTEXT
        )
        self.lbl_step.pack(side="left")

        self.btn_next = tk.Button(
            footer, text="Continuar  →",
            font=("Segoe UI", 10, "bold"),
            bg=BTN_BG, fg=BTN_FG,
            activebackground=BTN_HOV, activeforeground=BTN_FG,
            relief="flat", bd=0, padx=22, pady=8, cursor="hand2",
            command=self._next_page
        )
        self.btn_next.pack(side="right")

        self.btn_back = tk.Button(
            footer, text="←  Volver",
            font=("Segoe UI", 10),
            bg=BG, fg=SUBTEXT,
            activebackground=BG2, activeforeground=TEXT,
            relief="flat", bd=0, padx=16, pady=8, cursor="hand2",
            command=self._prev_page
        )
        self.btn_back.pack(side="right", padx=(0, 8))

        # ── Contenido central ────────────────────────────────────
        self.content = tk.Frame(root, bg=BG2, padx=30, pady=16)
        self.content.pack(fill="both", expand=True, side="top")

    # ── Mostrar pagina ───────────────────────────────────────────

    def _show_page(self, idx):
        page = PAGES[idx]

        for w in self.content.winfo_children():
            w.destroy()

        # Numero de paso
        tk.Label(
            self.content, text=f"PASO {page['step']}",
            font=("Segoe UI", 8, "bold"), bg=BG2, fg=ACCENT
        ).pack(anchor="w", pady=(0, 4))

        # Titulo
        tk.Label(
            self.content, text=page["title"],
            font=("Segoe UI", 13, "bold"), bg=BG2, fg=TEXT,
            wraplength=WIN_W - 70, justify="left"
        ).pack(anchor="w", pady=(0, 8))

        # Separador decorativo
        tk.Frame(self.content, bg=ACCENT, height=2, width=40).pack(anchor="w", pady=(0, 10))

        # Cuerpo
        body_text = page["body"]

        if "link" in page:
            tk.Label(
                self.content, text=body_text,
                font=("Segoe UI", 10), bg=BG2, fg=TEXT,
                wraplength=WIN_W - 70, justify="left"
            ).pack(anchor="w")
            lnk = tk.Label(
                self.content, text=page["link_text"],
                font=("Segoe UI", 10, "underline"), bg=BG2, fg=LINK,
                cursor="hand2"
            )
            lnk.pack(anchor="w")
            lnk.bind("<Button-1>", lambda e: webbrowser.open(page["link"]))
        else:
            tk.Label(
                self.content, text=body_text,
                font=("Segoe UI", 10), bg=BG2, fg=TEXT,
                wraplength=WIN_W - 70, justify="left"
            ).pack(anchor="w")

        # Linea "listo" con tilde verde
        if "listo" in page:
            listo_frame = tk.Frame(self.content, bg=BG2)
            listo_frame.pack(anchor="w", pady=(10, 0))
            tk.Label(
                listo_frame, text="✔",
                font=("Segoe UI", 11, "bold"), bg=BG2, fg=GREEN
            ).pack(side="left", padx=(0, 6))
            tk.Label(
                listo_frame, text=page["listo"],
                font=("Segoe UI", 10, "bold"), bg=BG2, fg=GREEN
            ).pack(side="left")

        # Footer
        self.lbl_step.config(text=f"Paso {page['step']}")
        is_last = idx == len(PAGES) - 1
        self.btn_next.config(text="Terminar" if is_last else "Continuar  →")
        if idx > 0:
            self.btn_back.pack(side="right", padx=(0, 8))
        else:
            self.btn_back.pack_forget()

    # ── Navegacion ───────────────────────────────────────────────

    def _next_page(self):
        if self.page < len(PAGES) - 1:
            self.page += 1
            self._show_page(self.page)
        else:
            self.root.destroy()

    def _prev_page(self):
        if self.page > 0:
            self.page -= 1
            self._show_page(self.page)


def main():
    root = tk.Tk()
    icon_path = find_pleiada_ico()
    if icon_path:
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass
    PleiadaWizard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
