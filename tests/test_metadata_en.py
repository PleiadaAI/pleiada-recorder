#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
session_metadata.json sale en INGLES: los traductores de frontera de
pleiada_app.pyw (`_en_framing`, `_en_rebind`, `_en_input_events`,
`_EN_RECORDING_MODE`, `_EN_NO_INPUT_CAUSE`).

Por que existe: hasta v0.9.19 el metadata llevaba claves y valores en espanol
(`encuadre`, `idle_fraccion`, `eventos_input`, `rebind_evidence.verificable`,
`recording_mode: "libre"`) y asi llego a los clientes. Regla de la casa: todo lo
que viaja con un dataset va en ingles.

Dos cosas se prueban:
  1. Los bloques internos (en espanol, tal cual los producen la app y
     pleiada_sync_limits) se traducen a lo que se espera, clave por clave.
  2. Ninguna clave ni valor de texto del resultado contiene una palabra de la
     lista negra en espanol. Si alguien agrega un campo nuevo en espanol, este
     test lo agarra aunque no este en la tabla del punto 1.

Correr:  python tests/test_metadata_en.py
"""
import io
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "pleiada_installer", "files", "pleiada_app.pyw")

with io.open(APP, encoding="utf-8") as f:
    fuente = f.read()
m = re.search(r"^_EN_RECORDING_MODE = .*?(?=^def build_session_metadata)",
              fuente, re.S | re.M)
if not m:
    sys.exit("No se encontro el bloque de traductores en pleiada_app.pyw")
ns = {}
exec(compile(m.group(0), APP, "exec"), ns)

_en_framing = ns["_en_framing"]
_en_rebind = ns["_en_rebind"]
_en_input_events = ns["_en_input_events"]
_EN_RECORDING_MODE = ns["_EN_RECORDING_MODE"]
_EN_NO_INPUT_CAUSE = ns["_EN_NO_INPUT_CAUSE"]

fallos = []


def check(nombre, cond, detalle=""):
    if cond:
        print("ok     " + nombre)
    else:
        fallos.append(nombre)
        print("FALLA  " + nombre + (": " + detalle if detalle else ""))


# ── 1. Traduccion clave por clave ─────────────────────────────────────────────

# Tal cual lo escribe _encuadre_con_pixeles() (v0.9.14+), con barras y muestreo.
ENCUADRE = {
    "fuente_ancho": 2560, "fuente_alto": 1080,
    "lienzo_ancho": 1920, "lienzo_alto": 1080,
    "dibujado_ancho": 1920.0, "dibujado_alto": 810.0,
    "dibujado_x": 0.0, "dibujado_y": 135.0,
    "aspecto_fuente": 2.3704, "aspecto_lienzo": 1.7778,
    "barras_fraccion": 0.25, "barras_lado": "arriba_abajo",
    "barras_por_borde": {"izquierda": 0.0, "derecha": 0.0, "arriba": 0.125, "abajo": 0.125},
    "fuente_excede_lienzo": False,
    "ocupa_cuadro_completo": False,
    "barras_pixeles": {
        "muestras": 0, "muestras_todo_negro": 0,
        "motivo": "no hay captura de juego activa",
        "por_borde": None,
    },
}
ESPERADO_FRAMING = {
    "source_width": 2560, "source_height": 1080,
    "canvas_width": 1920, "canvas_height": 1080,
    "drawn_width": 1920.0, "drawn_height": 810.0,
    "drawn_x": 0.0, "drawn_y": 135.0,
    "source_aspect": 2.3704, "canvas_aspect": 1.7778,
    "bars_fraction": 0.25, "bars_side": "top_bottom",
    "bars_per_edge": {"left": 0.0, "right": 0.0, "top": 0.125, "bottom": 0.125},
    "source_exceeds_canvas": False,
    "fills_full_frame": False,
    "bars_pixels": {
        "samples": 0, "samples_all_black": 0,
        "reason": "no active game capture",
        "per_edge": None,
    },
}
r = _en_framing(ENCUADRE)
check("framing: traduccion completa", r == ESPERADO_FRAMING,
      json.dumps(r, ensure_ascii=False))

# Con muestreo de pixeles que si corrio (por_borde lleno + fraccion).
enc2 = dict(ENCUADRE, barras_lado="costados_y_arriba_abajo")
enc2["barras_pixeles"] = {"muestras": 3, "muestras_todo_negro": 1, "motivo": None,
                          "por_borde": {"izquierda": 0.1, "derecha": 0.1,
                                        "arriba": 0.0, "abajo": 0.0},
                          "fraccion": 0.2}
r2 = _en_framing(enc2)
check("framing: bars_side compuesto", r2["bars_side"] == "sides_and_top_bottom")
check("framing: bars_pixels.per_edge",
      r2["bars_pixels"]["per_edge"] == {"left": 0.1, "right": 0.1, "top": 0.0, "bottom": 0.0}
      and r2["bars_pixels"]["fraction"] == 0.2)
check("framing: None se respeta", _en_framing(None) is None)

# Las cuatro variantes de barras_lado y los siete motivos del muestreo.
for lado, en in (("ninguna", "none"), ("costados", "sides"),
                 ("arriba_abajo", "top_bottom"),
                 ("costados_y_arriba_abajo", "sides_and_top_bottom")):
    check("framing: bars_side %s" % lado,
          _en_framing({"barras_lado": lado})["bars_side"] == en)
MOTIVOS = ["no se pudo conectar a OBS", "OBS no ofrece capturas en BMP",
           "no hay captura de juego activa", "OBS no pudo renderizar la captura",
           "no se pudo leer la captura", "no se llegó a tomar ninguna muestra útil",
           "error al muestrear"]
# Los motivos que escribe la app tienen que estar TODOS en la tabla: se leen del
# codigo fuente para que agregar uno nuevo sin traducirlo rompa el test.
motivos_en_codigo = set(re.findall(r'_BARRAS_PIXELES\["motivo"\] = "([^"]+)"', fuente))
check("framing: todos los motivos del codigo tienen traduccion",
      motivos_en_codigo <= set(ns["_EN_BARS_PIXELS_REASON"]),
      "sin traducir: %r" % (motivos_en_codigo - set(ns["_EN_BARS_PIXELS_REASON"]),))
check("framing: la lista del test cubre los motivos del codigo",
      motivos_en_codigo <= set(MOTIVOS), repr(motivos_en_codigo - set(MOTIVOS)))

# rebind_evidence, las tres formas que produce _meta_rebind_evidence().
r = _en_rebind({"verificable": False, "motivo": "sin archivo de configuración leído"})
check("rebind: sin config", r == {"verifiable": False,
                                  "reason": "no configuration file was read"},
      json.dumps(r, ensure_ascii=False))
r = _en_rebind({"verificable": True, "archivo": "config.cfg", "mtime_unix_ms": 1,
                "config_modificada_durante_sesion": False,
                "binds_modificados_durante_sesion": None,
                "motivo_sin_comparacion": "no se pudo leer el mapping al cerrar"})
check("rebind: sin comparacion",
      r == {"verifiable": True, "file": "config.cfg", "mtime_unix_ms": 1,
            "config_modified_during_session": False,
            "binds_modified_during_session": None,
            "no_comparison_reason": "could not read the key mapping at session end"},
      json.dumps(r, ensure_ascii=False))
r = _en_rebind({"verificable": True, "archivo": "Input.ini", "mtime_unix_ms": 2,
                "config_modificada_durante_sesion": True,
                "binds_modificados_durante_sesion": True,
                "binds_cambiados": ["w", "e"], "binds_cambiados_total": 2})
check("rebind: con binds cambiados",
      r["binds_changed"] == ["w", "e"] and r["binds_changed_total"] == 2
      and r["binds_modified_during_session"] is True)
fn_rebind = re.search(r"^def _meta_rebind_evidence.*?(?=^def )", fuente, re.S | re.M).group(0)
motivos_rebind = set(re.findall(r'"motivo": "([^"]+)"', fn_rebind)) | \
    set(re.findall(r'out\["motivo_sin_comparacion"\] = "([^"]+)"', fn_rebind))
check("rebind: todos los motivos del codigo tienen traduccion",
      motivos_rebind <= set(ns["_EN_REBIND_REASON"]),
      "sin traducir: %r" % (motivos_rebind - set(ns["_EN_REBIND_REASON"]),))

# sync: conteo, causa y modo de grabacion.
check("input_events",
      _en_input_events({"teclado": 330, "mouse_crudo": 8482, "botones": 31,
                        "mouse_posicion": 981})
      == {"keyboard": 330, "mouse_raw": 8482, "buttons": 31, "mouse_position": 981})
check("input_events: None se respeta", _en_input_events(None) is None)
check("no_input_cause", _EN_NO_INPUT_CAUSE == {"captura_bloqueada": "capture_blocked",
                                                "sin_teclado_ni_mouse": "no_keyboard_no_mouse"})
check("recording_mode", _EN_RECORDING_MODE.get("libre") == "free"
      and _EN_RECORDING_MODE.get("manual") == "manual")

# ── 2. Lista negra: nada en espanol en claves ni valores de texto ─────────────

PALABRAS_ES = re.compile(
    r"(fraccion|encuadre|fuente|lienzo|dibujado|aspecto|barras|borde|izquierda|"
    r"derecha|arriba|abajo|ninguna|costados|ocupa|cuadro|excede|muestras|negro|"
    r"motivo|verificable|archivo|modificad|durante|sesion|comparacion|cambiad|"
    r"teclado|crudo|botones|posicion|eventos|causa|bloqueada|libre|bajo|"
    r"\bno se\b|\bsin \b|\bal \b|\bel \b|\bla \b|\bde \b)", re.I)


def recorrer(obj, ruta="", acc=None):
    if acc is None:
        acc = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if PALABRAS_ES.search(str(k)):
                acc.append("%s.%s (clave)" % (ruta, k))
            recorrer(v, ruta + "." + str(k), acc)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            recorrer(v, "%s[%d]" % (ruta, i), acc)
    elif isinstance(obj, str) and PALABRAS_ES.search(obj):
        acc.append("%s = %r (valor)" % (ruta, obj))
    return acc


salida = {
    "recording_mode": _EN_RECORDING_MODE["libre"],
    "input": {"rebind_evidence": _en_rebind(
        {"verificable": False, "motivo": "el archivo ya no está accesible"})},
    "video": {"framing": r2},
    "sync": {"no_input_cause": _EN_NO_INPUT_CAUSE["sin_teclado_ni_mouse"],
             "input_events": _en_input_events({"teclado": 0, "mouse_crudo": 0,
                                               "botones": 0, "mouse_posicion": 0})},
}
for motivo in MOTIVOS:
    salida["video"]["framing_%d" % MOTIVOS.index(motivo)] = _en_framing(
        {"barras_pixeles": {"motivo": motivo}})
for motivo in ns["_EN_REBIND_REASON"]:
    salida["input"]["rb_%d" % list(ns["_EN_REBIND_REASON"]).index(motivo)] = \
        _en_rebind({"motivo_sin_comparacion": motivo})
restos = recorrer(salida)
check("lista negra: nada en espanol en la salida", not restos, "; ".join(restos))

# Y el bloque que arma build_session_metadata no puede volver a escribir las
# claves viejas: se busca en el fuente el literal de cada clave vieja como clave
# del dict de salida (con comillas y dos puntos).
bloque = re.search(r"^def build_session_metadata.*?session_metadata\.json escrito",
                   fuente, re.S | re.M).group(0)
viejas = ["encuadre", "idle_fraccion", "sin_input_rejected", "sin_input_causa",
          "eventos_input", "bitrate_bajo"]
presentes = [k for k in viejas if re.search(r'"%s":\s' % k, bloque)]
check("build_session_metadata: no escribe claves viejas", not presentes, repr(presentes))
check("build_session_metadata: schema_version 1.3",
      '"schema_version":   "1.3"' in bloque)

print()
if fallos:
    print("FALLARON %d: %s" % (len(fallos), ", ".join(fallos)))
    sys.exit(1)
print("todo ok")
