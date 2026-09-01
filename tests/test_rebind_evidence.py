"""
Evidencia de re-mapeo de teclas: `_meta_rebind_evidence()` de pleiada_app.pyw.

Nace del reporte de QA del 02-09-2026 (Pedro): el campo se encendia al cambiar
CUALQUIER opcion del juego, no solo un bind. La causa es que la unica senal era
la fecha de modificacion del archivo de config, y en Source `config.cfg` guarda
los binds JUNTO con video, audio y sensibilidad: subir el volumen reescribe el
archivo entero.

El arreglo es comparar el key mapping leido al arrancar contra el leido al
cerrar. Estos tests fijan las dos senales: la debil (mtime, que se queda por
compatibilidad y para cuando no hay snapshot) y la fuerte (comparacion de binds).

Se corre sin juego y sin OBS.

    python tests\test_rebind_evidence.py
"""
import io
import os
import re
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "pleiada_installer", "files", "pleiada_app.pyw")

with io.open(APP, encoding="utf-8") as f:
    fuente = f.read()
m = re.search(r"^_KM_CONFIG_USADO = .*?(?=^def _parse_ue_input_ini\(\):|^def _parse_ue_input_ini\()",
              fuente, re.S | re.M)
if not m:
    sys.exit("No se encontro el bloque de rebind en pleiada_app.pyw")
ns = {"os": os, "_obs_dbg": lambda *a, **k: None}
exec(compile(m.group(0), APP, "exec"), ns)
_meta_rebind_evidence = ns["_meta_rebind_evidence"]
_KM_CONFIG_USADO = ns["_KM_CONFIG_USADO"]

TMP = tempfile.mkdtemp(prefix="pleiada_rebind_")
CFG = os.path.join(TMP, "config.cfg")

START = 1_000_000_000_000
END = START + 60 * 60 * 1000       # una hora de sesion
DENTRO = START + 30 * 60 * 1000    # a mitad de la sesion
ANTES = START - 60 * 60 * 1000     # una hora antes de empezar

WASD = {"w": "move_forward", "a": "move_left",
        "s": "move_backward", "d": "move_right"}
ESDF = {"e": "move_forward", "s": "move_left",
        "d": "move_backward", "f": "move_right"}


def preparar(mtime_ms, inicio=None):
    """Deja el config con esa fecha de modificacion y el snapshot pedido."""
    with io.open(CFG, "w", encoding="utf-8") as f:
        f.write('bind "w" "+forward"\n')
    seg = mtime_ms / 1000.0
    os.utime(CFG, (seg, seg))
    _KM_CONFIG_USADO["path"] = CFG
    _KM_CONFIG_USADO["inicio"] = inicio


fallos = []


def chequear(nombre, r, esperado):
    errores = ["%s=%r, esperaba %r" % (k, r.get(k), v)
               for k, v in esperado.items() if r.get(k) != v]
    if errores:
        fallos.append(nombre)
        print("FALLA  %s" % nombre)
        for e in errores:
            print("         %s" % e)
        print("         devolvio: %r" % (r,))
    else:
        print("ok     %s" % nombre)


# 🔴 El caso que reporto QA: el jugador cambio volumen/resolucion a mitad de
# sesion. El archivo se reescribio, pero los binds son los mismos.
preparar(DENTRO, inicio={"path": CFG, "mapping": dict(WASD), "mtime_unix_ms": ANTES})
chequear("cambia audio/video, NO toca teclas",
         _meta_rebind_evidence(START, END, dict(WASD), "config"),
         {"verificable": True,
          "config_modificada_durante_sesion": True,   # la senal debil se enciende
          "binds_modificados_durante_sesion": False}) # la fuerte, no

# El caso que SI hay que marcar: se re-mapeo el movimiento a mitad de sesion.
preparar(DENTRO, inicio={"path": CFG, "mapping": dict(WASD), "mtime_unix_ms": ANTES})
r = _meta_rebind_evidence(START, END, dict(ESDF), "config")
chequear("re-mapea WASD a ESDF durante la sesion", r,
         {"verificable": True,
          "config_modificada_durante_sesion": True,
          "binds_modificados_durante_sesion": True,
          # w y a desaparecen, e y f aparecen, s y d cambian de accion
          "binds_cambiados_total": 6})
if r.get("binds_cambiados") != ["a", "d", "e", "f", "s", "w"]:
    fallos.append("lista de binds cambiados")
    print("FALLA  lista de binds cambiados: %r" % (r.get("binds_cambiados"),))
else:
    print("ok     lista de binds cambiados: %r" % (r["binds_cambiados"],))

# Sesion limpia: no se toco nada.
preparar(ANTES, inicio={"path": CFG, "mapping": dict(WASD), "mtime_unix_ms": ANTES})
chequear("no se toca nada",
         _meta_rebind_evidence(START, END, dict(WASD), "config"),
         {"verificable": True,
          "config_modificada_durante_sesion": False,
          "binds_modificados_durante_sesion": False})

# Un solo bind agregado (no reemplazado).
preparar(DENTRO, inicio={"path": CFG, "mapping": dict(WASD), "mtime_unix_ms": ANTES})
mas = dict(WASD); mas["space"] = "jump"
chequear("agrega un bind nuevo",
         _meta_rebind_evidence(START, END, mas, "config"),
         {"binds_modificados_durante_sesion": True, "binds_cambiados_total": 1})

# Sin snapshot de arranque (el thread no llego a terminar, o no hay parser):
# se degrada a la senal vieja y se dice por que.
preparar(DENTRO, inicio=None)
chequear("sin snapshot de arranque",
         _meta_rebind_evidence(START, END, dict(WASD), "config"),
         {"verificable": True,
          "config_modificada_durante_sesion": True,
          "binds_modificados_durante_sesion": None,
          "motivo_sin_comparacion": "no se pudo leer el mapping al arrancar"})

# Al cerrar no se pudo leer el config (el juego lo borro, o se desinstalo):
# tampoco se compara.
preparar(DENTRO, inicio={"path": CFG, "mapping": dict(WASD), "mtime_unix_ms": ANTES})
chequear("al cerrar el mapping no viene del config",
         _meta_rebind_evidence(START, END, dict(WASD), "game_default"),
         {"binds_modificados_durante_sesion": None,
          "motivo_sin_comparacion": "no se pudo leer el mapping al cerrar"})

# Motor sin parser (Unity y otros): no se afirma nada en ninguna direccion.
_KM_CONFIG_USADO["path"] = None
_KM_CONFIG_USADO["inicio"] = None
chequear("motor sin parser",
         _meta_rebind_evidence(START, END, None, "unknown"),
         {"verificable": False,
          "motivo": "sin archivo de configuración leído"})

# El archivo ya no esta.
_KM_CONFIG_USADO["path"] = os.path.join(TMP, "no_existe.cfg")
chequear("el config ya no esta",
         _meta_rebind_evidence(START, END, dict(WASD), "config"),
         {"verificable": False,
          "motivo": "el archivo ya no está accesible"})

print("\n%s" % ("TODO OK" if not fallos else "%d FALLAS: %s" % (len(fallos), fallos)))
sys.exit(1 if fallos else 0)
