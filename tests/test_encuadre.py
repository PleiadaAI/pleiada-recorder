"""
Geometria del encuadre: `_encuadre_geometria()` de pleiada_app.pyw.

Nace del reporte de QA del 02-09-2026 (Pedro), que probo la deteccion de franjas
negras en cuatro configuraciones y fallo en las cuatro. La causa: la v1 comparaba
el ASPECTO de la fuente contra el del lienzo, asumiendo que OBS escala la captura
para que entre centrada. OBS no hace eso: la deja en su tamano nativo pegada
arriba a la izquierda (alignment 5, su default), asi que el negro queda a la
derecha y abajo.

El caso que lo deja mas claro es el 16:9 en ventana: el aspecto coincide con el
del lienzo, asi que la comparacion de proporciones dice "sin barras" mientras el
video tiene medio cuadro en negro.

Se corre sin OBS y sin juego: se le pasa el transform a mano.

    python tests\test_encuadre.py
"""
import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "pleiada_installer", "files", "pleiada_app.pyw")

# pleiada_app.pyw es una app de escritorio: importarla entera levanta Tk, lee
# settings y quiere hablar con OBS. Se extrae solo el bloque de geometria, que no
# depende de nada de eso.
with io.open(APP, encoding="utf-8") as f:
    fuente = f.read()
m = re.search(r"^_OBS_ALIGN_LEFT.*?(?=^def _meta_encuadre\(\):)",
              fuente, re.S | re.M)
if not m:
    sys.exit("No se encontro el bloque de geometria en pleiada_app.pyw")
ns = {}
exec(compile(m.group(0), APP, "exec"), ns)
_encuadre_geometria = ns["_encuadre_geometria"]

LIENZO_W, LIENZO_H = 1920.0, 1080.0
ALIGN_TOPLEFT = 5      # el default de OBS
ALIGN_CENTER = 0


def tr(sw, sh, w=None, h=None, x=0, y=0, align=ALIGN_TOPLEFT):
    """Transform minimo de un scene item, como lo devuelve GetSceneItemTransform."""
    return {
        "sourceWidth": sw, "sourceHeight": sh,
        "width": sw if w is None else w,
        "height": sh if h is None else h,
        "positionX": x, "positionY": y, "alignment": align,
        "scaleX": 1.0, "scaleY": 1.0,
        "cropLeft": 0, "cropRight": 0, "cropTop": 0, "cropBottom": 0,
    }


CASOS = []


def caso(nombre, transform, ocupa, lado, bordes=None, excede=None):
    CASOS.append((nombre, transform, ocupa, lado, bordes, excede))


# ── Los cuatro que reporto QA ────────────────────────────────────────────────

# El unico que la v1 acertaba: la captura llena el lienzo exacto.
caso("16:9 pantalla completa 1920x1080",
     tr(1920, 1080), ocupa=True, lado="ninguna")

# 🔴 El que mas claro deja el bug: la v1 decia `ninguna` / `true` porque el
# aspecto coincide, y el video tenia medio cuadro negro.
caso("16:9 en ventana 1280x720 arriba a la izquierda",
     tr(1280, 720), ocupa=False, lado="costados_y_arriba_abajo",
     bordes={"izquierda": 0.0, "derecha": 1 - 1280 / 1920,
             "arriba": 0.0, "abajo": 1 - 720 / 1080})

# 4:3 mas chico que el lienzo: negro a la derecha y abajo, no "costados".
caso("4:3 en ventana 1024x768 arriba a la izquierda",
     tr(1024, 768), ocupa=False, lado="costados_y_arriba_abajo",
     bordes={"izquierda": 0.0, "derecha": 1 - 1024 / 1920,
             "arriba": 0.0, "abajo": 1 - 768 / 1080})

# 16:10 mas chico que el lienzo: idem.
caso("16:10 en ventana 1680x1050 arriba a la izquierda",
     tr(1680, 1050), ocupa=False, lado="costados_y_arriba_abajo",
     bordes={"izquierda": 0.0, "derecha": 1 - 1680 / 1920,
             "arriba": 0.0, "abajo": 1 - 1050 / 1080})

# ── Casos que la v1 SI acertaba, para no romperlos al arreglar ───────────────

# Escalado para entrar y centrado: el pillarbox clasico.
caso("4:3 escalado a 1440x1080 y centrado (pillarbox)",
     tr(1600, 1200, w=1440, h=1080, x=960, y=540, align=ALIGN_CENTER),
     ocupa=False, lado="costados",
     bordes={"izquierda": 240 / 1920, "derecha": 240 / 1920,
             "arriba": 0.0, "abajo": 0.0})

# Ultrawide escalado y centrado: el letterbox clasico.
caso("21:9 escalado a 1920x823 y centrado (letterbox)",
     tr(2560, 1097, w=1920, h=823, x=960, y=540, align=ALIGN_CENTER),
     ocupa=False, lado="arriba_abajo",
     bordes={"izquierda": 0.0, "derecha": 0.0,
             "arriba": (1080 - 823) / 2 / 1080, "abajo": (1080 - 823) / 2 / 1080})

# ── Bordes del metodo ────────────────────────────────────────────────────────

# Fuente mas alta que el lienzo, a tamano nativo: no deja negro abajo (se
# recorta), pero SI pierde imagen. Se dice aparte, no como barra.
caso("4:3 nativo 1600x1200 (mas alto que el lienzo)",
     tr(1600, 1200), ocupa=False, lado="costados",
     bordes={"izquierda": 0.0, "derecha": 1 - 1600 / 1920,
             "arriba": 0.0, "abajo": 0.0},
     excede=True)

# Un pixel de diferencia no es una barra: entra en la tolerancia.
caso("1919x1080 (redondeo, no es barra)",
     tr(1919, 1080), ocupa=True, lado="ninguna", excede=False)

# Alineacion por la derecha: el negro queda del otro lado.
caso("1280x720 anclado abajo a la derecha",
     tr(1280, 720, x=1920, y=1080, align=2 | 8),
     ocupa=False, lado="costados_y_arriba_abajo",
     bordes={"izquierda": 1 - 1280 / 1920, "derecha": 0.0,
             "arriba": 1 - 720 / 1080, "abajo": 0.0})

# La fuente todavia no capturo nada.
caso("fuente sin tamano", tr(0, 0), ocupa=None, lado=None)


def main():
    fallos = 0
    for nombre, transform, ocupa, lado, bordes, excede in CASOS:
        r = _encuadre_geometria(transform, LIENZO_W, LIENZO_H)
        errores = []
        if ocupa is None:
            if r is not None:
                errores.append("esperaba None y devolvio un dict")
        elif r is None:
            errores.append("devolvio None")
        else:
            if r["ocupa_cuadro_completo"] != ocupa:
                errores.append("ocupa_cuadro_completo=%s, esperaba %s"
                               % (r["ocupa_cuadro_completo"], ocupa))
            if r["barras_lado"] != lado:
                errores.append("barras_lado=%r, esperaba %r"
                               % (r["barras_lado"], lado))
            for k, v in (bordes or {}).items():
                if abs(r["barras_por_borde"][k] - v) > 0.001:
                    errores.append("borde %s=%.4f, esperaba %.4f"
                                   % (k, r["barras_por_borde"][k], v))
            if excede is not None and r["fuente_excede_lienzo"] != excede:
                errores.append("fuente_excede_lienzo=%s, esperaba %s"
                               % (r["fuente_excede_lienzo"], excede))
        if errores:
            fallos += 1
            print("FALLA  %s" % nombre)
            for e in errores:
                print("         %s" % e)
            if r:
                print("         devolvio: barras=%.4f lado=%s bordes=%s"
                      % (r["barras_fraccion"], r["barras_lado"],
                         r["barras_por_borde"]))
        else:
            extra = ""
            if r:
                extra = "  (negro %.1f%%)" % (r["barras_fraccion"] * 100)
            print("ok     %s%s" % (nombre, extra))

    print("\n%d/%d casos ok" % (len(CASOS) - fallos, len(CASOS)))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
