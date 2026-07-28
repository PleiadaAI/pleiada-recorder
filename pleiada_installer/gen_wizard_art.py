"""
Regenera los assets de marca del instalador desde el logo de Gameplay Alliance.

Genera:
  assets/gameplay_recorder.ico       icono de la app (16..256, multi-resolucion)
  assets/gameplay_recorder_icon.png  logo del header del Synch Checker
  assets/wizard_banner.bmp           imagen lateral del asistente (164x314)
  assets/wizard_small.bmp            icono del encabezado del asistente (55x58)

Inno exige BMP para las dos del asistente, y respeta las medidas exactas.
No hace falta correrlo en cada build: solo si cambia el logo o el texto de marca.

    python gen_wizard_art.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
LOGO   = os.path.join(ASSETS, "gameplay_alliance_logo_512.png")

BG     = (13, 13, 24)      # #0d0d18, el mismo fondo que la app
ACCENT = (139, 108, 240)   # violeta del logo
TEXTO  = (232, 232, 240)

FONTS  = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
f_bold = ImageFont.truetype(os.path.join(FONTS, "segoeuib.ttf"), 15)
f_sub  = ImageFont.truetype(os.path.join(FONTS, "segoeui.ttf"),  11)

logo = Image.open(LOGO).convert("RGBA")


def centrado(d, ancho, y, texto, fuente, color):
    w = d.textbbox((0, 0), texto, font=fuente)[2]
    d.text(((ancho - w) // 2, y), texto, font=fuente, fill=color)


def icono():
    # Windows elige el tamano segun el contexto: 16 barra de tareas,
    # 32 escritorio, 256 vista de iconos grandes.
    tam = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    logo.save(os.path.join(ASSETS, "gameplay_recorder.ico"), format="ICO", sizes=tam)
    logo.resize((256, 256), Image.LANCZOS).save(
        os.path.join(ASSETS, "gameplay_recorder_icon.png"))


def banner():
    b = Image.new("RGB", (164, 314), BG)
    d = ImageDraw.Draw(b)
    d.rectangle([0, 0, 163, 3], fill=ACCENT)          # barra superior de acento

    L = 76
    mini = logo.resize((L, L), Image.LANCZOS)
    b.paste(mini, ((164 - L) // 2, 42), mini)

    centrado(d, 164, 140, "Gameplay Recorder", f_bold, TEXTO)
    centrado(d, 164, 163, "Gameplay Alliance", f_sub, ACCENT)
    d.line([38, 188, 126, 188], fill=ACCENT, width=1)

    # A propósito SIN número de versión: el banner anterior decía "Instalador
    # v1.0" con la app ya en v0.8.8. Un dato que hay que acordarse de tocar en
    # cada build termina siempre desactualizado.
    b.save(os.path.join(ASSETS, "wizard_banner.bmp"))
    b.save(os.path.join(ASSETS, "wizard_banner_preview.png"))


def chico():
    s = Image.new("RGB", (55, 58), BG)
    L = 44
    mini = logo.resize((L, L), Image.LANCZOS)
    s.paste(mini, ((55 - L) // 2, (58 - L) // 2), mini)
    s.save(os.path.join(ASSETS, "wizard_small.bmp"))


if __name__ == "__main__":
    icono()
    banner()
    chico()
    for f in ("gameplay_recorder.ico", "gameplay_recorder_icon.png",
              "wizard_banner.bmp", "wizard_small.bmp"):
        p = os.path.join(ASSETS, f)
        im = Image.open(p)
        print(f"  {f:34} {str(im.size):12} {os.path.getsize(p)/1024:7.1f} KB")
