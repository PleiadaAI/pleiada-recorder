"""
Deteccion de franjas negras DENTRO de la imagen: `_barras_de_bmp()` y
`_encuadre_con_pixeles()` de pleiada_app.pyw.

Nace del segundo reporte de QA del 01-09-2026 (Yai): de ocho configuraciones, la
geometria acerto seis y fallo las dos de PANTALLA COMPLETA a una resolucion
distinta a la del monitor. En ese caso la placa de video escala el juego y agrega
las franjas ANTES de que OBS capture: para OBS la fuente es el monitor entero,
lleno, y las barras son contenido de la imagen. La geometria no puede verlas.

Las dos sesiones que fallaron reportaron `fuente_ancho: 2560, fuente_alto: 1440`
(la resolucion del escritorio, no la del juego). Se extrajeron cuadros de los MP4
y se midieron los pixeles:

    16:10 a 1920x1200 sobre 2560x1440  ->   5,0% de negro por lado
    4:3   a 1600x1200 sobre 2560x1440  ->  12,5% de negro por lado

Los dos numeros coinciden exactamente con la cuenta de escalar conservando
proporcion, asi que esos casos se reproducen aca sinteticamente: se arma un BMP
con las mismas franjas y se comprueba que el detector las encuentra.

Se corre sin OBS y sin juego.

    python tests\test_barras_pixeles.py
"""
import io
import os
import re
import struct
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "pleiada_installer", "files", "pleiada_app.pyw")

# Se extrae solo el bloque que no depende de OBS ni de Tk.
with io.open(APP, encoding="utf-8") as f:
    fuente = f.read()
bloques = []
for ini, fin in (("_BARRAS_PX_MAX_MUESTRAS = ", "def _muestrear_barras_pixeles"),
                 ("def _encuadre_con_pixeles", "def _meta_encuadre")):
    m = re.search(r"^%s.*?(?=^%s)" % (re.escape(ini), re.escape(fin)),
                  fuente, re.S | re.M)
    if not m:
        sys.exit("No se encontro el bloque %r en pleiada_app.pyw" % ini)
    bloques.append(m.group(0))
ns = {"struct": struct}
exec(compile("\n".join(bloques), APP, "exec"), ns)
_barras_de_bmp = ns["_barras_de_bmp"]
_encuadre_con_pixeles = ns["_encuadre_con_pixeles"]
_BARRAS_PIXELES = ns["_BARRAS_PIXELES"]


def bmp(w, h, izq=0, der=0, arriba=0, abajo=0, fondo=(120, 90, 60)):
    """BMP 24 bits con un rectangulo de color y franjas negras a los lados."""
    stride = ((w * 24 + 31) // 32) * 4
    filas = []
    for y in range(h):
        fila = bytearray(stride)
        if arriba <= y < h - abajo:
            for x in range(izq, w - der):
                i = x * 3
                fila[i], fila[i + 1], fila[i + 2] = fondo[2], fondo[1], fondo[0]
        filas.append(bytes(fila))
    filas.reverse()          # el BMP se guarda de abajo hacia arriba
    pixeles = b"".join(filas)
    off = 54
    return (b"BM" + struct.pack("<IHHI", off + len(pixeles), 0, 0, off)
            + struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(pixeles),
                          2835, 2835, 0, 0)
            + pixeles)


fallos = []


def chequear(nombre, obtenido, esperado, tol=0.001):
    errores = []
    for k, v in esperado.items():
        o = obtenido.get(k) if isinstance(obtenido, dict) else None
        if isinstance(v, float):
            if o is None or abs(o - v) > tol:
                errores.append("%s=%r, esperaba %.4f" % (k, o, v))
        elif o != v:
            errores.append("%s=%r, esperaba %r" % (k, o, v))
    if errores:
        fallos.append(nombre)
        print("FALLA  %s" % nombre)
        for e in errores:
            print("         %s" % e)
        print("         devolvio: %r" % (obtenido,))
    else:
        print("ok     %s" % nombre)


print("--- deteccion sobre la imagen ---")

# 🔴 Los dos casos que fallaron en QA, con los porcentajes medidos sobre el MP4.
chequear("4:3 1600x1200 en 2560x1440 (12,5% por lado)",
         _barras_de_bmp(bmp(480, 270, izq=60, der=60)),
         {"todo_negro": False, "izquierda": 0.125, "derecha": 0.125,
          "arriba": 0.0, "abajo": 0.0})

chequear("16:10 1920x1200 en 2560x1440 (5% por lado)",
         _barras_de_bmp(bmp(480, 270, izq=24, der=24)),
         {"todo_negro": False, "izquierda": 0.05, "derecha": 0.05,
          "arriba": 0.0, "abajo": 0.0})

chequear("sin franjas",
         _barras_de_bmp(bmp(480, 270)),
         {"todo_negro": False, "izquierda": 0.0, "derecha": 0.0,
          "arriba": 0.0, "abajo": 0.0})

chequear("letterbox arriba y abajo",
         _barras_de_bmp(bmp(480, 270, arriba=27, abajo=27)),
         {"todo_negro": False, "izquierda": 0.0, "derecha": 0.0,
          "arriba": 0.1, "abajo": 0.1})

chequear("franjas en los cuatro bordes",
         _barras_de_bmp(bmp(480, 270, izq=48, der=48, arriba=27, abajo=27)),
         {"izquierda": 0.1, "derecha": 0.1, "arriba": 0.1, "abajo": 0.1})

# Un cuadro entero negro NO es un encuadre con barras: es pantalla apagada o
# transicion. Se marca aparte para poder descartarlo como muestra.
chequear("cuadro entero negro", _barras_de_bmp(bmp(480, 270, izq=240, der=240)),
         {"todo_negro": True})

# Escena oscura pero no negra: no tiene que contar como franja.
chequear("escena oscura, no negra",
         _barras_de_bmp(bmp(480, 270, fondo=(30, 30, 30))),
         {"todo_negro": False, "izquierda": 0.0, "arriba": 0.0})

# Casi negra pero por debajo del umbral: si cuenta (bordes sucios por compresion).
chequear("franja casi negra (ruido de compresion)",
         _barras_de_bmp(bmp(480, 270, izq=60, der=60, fondo=(200, 200, 200))),
         {"izquierda": 0.125, "derecha": 0.125})

if _barras_de_bmp(b"no soy un bmp") is not None:
    fallos.append("basura")
    print("FALLA  datos que no son BMP: esperaba None")
else:
    print("ok     datos que no son BMP")


print("\n--- veredicto combinado (geometria + pixeles) ---")

GEO_LLENO = {"barras_fraccion": 0.0, "barras_lado": "ninguna",
             "ocupa_cuadro_completo": True,
             "barras_por_borde": {"izquierda": 0.0, "derecha": 0.0,
                                  "arriba": 0.0, "abajo": 0.0}}


def con_px(muestras, margenes, motivo=None, negras=0):
    _BARRAS_PIXELES.update({"muestras": muestras, "margenes": margenes,
                            "motivo": motivo, "muestras_todo_negro": negras})
    return _encuadre_con_pixeles(dict(GEO_LLENO))


# 🔴 El caso de QA de punta a punta: la geometria dice que llena el cuadro y los
# pixeles encuentran las franjas. Gana el que vio algo.
r = con_px(5, {"izquierda": 0.125, "derecha": 0.125, "arriba": 0.0, "abajo": 0.0})
chequear("geometria dice lleno pero hay franjas en la imagen", r,
         {"ocupa_cuadro_completo": False, "barras_lado": "costados"})

r = con_px(5, {"izquierda": 0.0, "derecha": 0.0, "arriba": 0.0, "abajo": 0.0})
chequear("los dos coinciden en que llena el cuadro", r,
         {"ocupa_cuadro_completo": True, "barras_lado": "ninguna"})

# Sin medicion de pixeles NO se afirma que llena el cuadro: queda en None.
r = con_px(0, None, motivo="no se pudo conectar a OBS")
chequear("sin muestras: no se afirma nada", r,
         {"ocupa_cuadro_completo": None})

# Pero si la geometria YA vio un hueco, eso se sostiene sin pixeles.
geo_hueco = dict(GEO_LLENO)
geo_hueco["ocupa_cuadro_completo"] = False
geo_hueco["barras_lado"] = "costados_y_arriba_abajo"
_BARRAS_PIXELES.update({"muestras": 0, "margenes": None,
                        "motivo": "no hay captura de juego activa",
                        "muestras_todo_negro": 0})
chequear("sin muestras pero la geometria ya vio el hueco",
         _encuadre_con_pixeles(geo_hueco),
         {"ocupa_cuadro_completo": False,
          "barras_lado": "costados_y_arriba_abajo"})

# El motivo tiene que viajar a la metadata para poder auditarlo.
r = con_px(0, None, motivo="OBS no ofrece capturas en BMP")
if (r.get("barras_pixeles") or {}).get("motivo") != "OBS no ofrece capturas en BMP":
    fallos.append("motivo")
    print("FALLA  el motivo no llega a la metadata: %r" % (r.get("barras_pixeles"),))
else:
    print("ok     el motivo llega a la metadata")

if _encuadre_con_pixeles(None) is not None:
    fallos.append("geo None")
    print("FALLA  geometria None: esperaba None")
else:
    print("ok     geometria None")

print("")
print("--- el muestreo reintenta en vez de abandonar ---")

# Este bloque nace de probar contra un OBS real (01-09-2026): mientras el juego
# no esta dibujando, OBS responde 702 "Failed to render screenshot" y devuelve
# vacio. Pasa SIEMPRE en los primeros segundos de una sesion. La primera version
# abandonaba el muestreo ahi, o sea que ninguna sesion se hubiera medido nunca.

_m_muestreo = re.search(r"^def _muestrear_barras_pixeles.*?(?=^_OBS_ALIGN_LEFT)",
                        fuente, re.S | re.M)
if not _m_muestreo:
    sys.exit("No se encontro _muestrear_barras_pixeles en pleiada_app.pyw")


class _RelojFalso(object):
    """time.sleep que no duerme: el muestreo espera minutos entre capturas."""

    def __init__(self):
        self.dormido = 0

    def sleep(self, s):
        self.dormido += s


class _WSFalso(object):
    def close(self):
        pass


def correr_muestreo(respuestas, formatos=("bmp", "png"), grabando=True):
    """
    Corre el muestreador contra un OBS de mentira. `respuestas` es lo que
    devuelve cada GetSourceScreenshot: None = error 702 (no pudo renderizar), o
    los bytes de un BMP.
    """
    import base64 as _b64
    estado = {"i": 0}

    def _obs_send(ws, tipo, datos=None):
        def resp(d):
            return {"d": {"responseData": d}}
        if tipo == "GetRecordStatus":
            return resp({"outputActive": grabando})
        if tipo == "GetVersion":
            return resp({"supportedImageFormats": list(formatos)})
        if tipo == "GetCurrentProgramScene":
            return resp({"currentProgramSceneName": "Escena"})
        if tipo == "GetSceneItemList":
            return resp({"sceneItems": [{"inputKind": "game_capture",
                                         "sceneItemEnabled": True,
                                         "sceneItemId": 1,
                                         "sourceName": "Captura de juego"}]})
        if tipo == "GetSourceScreenshot":
            i = estado["i"]
            estado["i"] += 1
            b = respuestas[i] if i < len(respuestas) else None
            if b is None:
                return resp({})          # asi contesta OBS con el error 702
            return resp({"imageData": "data:image/bmp;base64,"
                         + _b64.b64encode(b).decode()})
        return resp({})

    ns2 = dict(ns)
    ns2.update({"time": _RelojFalso(), "obs_connect": lambda: _WSFalso(),
                "obs_send": _obs_send, "_obs_dbg": lambda *a: None,
                "base64": _b64})
    exec(compile(_m_muestreo.group(0), APP, "exec"), ns2)
    ns2["_BARRAS_PIXELES"].update({"muestras": 0, "margenes": None,
                                   "motivo": None, "muestras_todo_negro": 0})
    ns2["_muestrear_barras_pixeles"]()
    return ns2["_BARRAS_PIXELES"]


CON_BARRAS = bmp(480, 270, izq=60, der=60)
SIN_BARRAS = bmp(480, 270)

# 🔴 El caso real: las primeras capturas fallan y despues empieza a andar.
r = correr_muestreo([None, None, None, CON_BARRAS, CON_BARRAS])
chequear("arranca fallando y despues mide", r, {"muestras": 2})
if not r["margenes"] or abs(r["margenes"]["izquierda"] - 0.125) > 0.001:
    fallos.append("margenes tras reintentar")
    print("FALLA  margenes tras reintentar: %r" % (r["margenes"],))
else:
    print("ok     margenes tras reintentar")

# Nunca pudo capturar: se reporta el motivo, sin muestras y sin romperse.
chequear("nunca pudo capturar", correr_muestreo([None] * 20),
         {"muestras": 0, "margenes": None,
          "motivo": "OBS no pudo renderizar la captura"})

# Se queda con el MINIMO: un fundido a negro en el medio no inventa franjas.
r = correr_muestreo([CON_BARRAS, bmp(480, 270, izq=240, der=240), SIN_BARRAS])
chequear("un cuadro todo negro no cuenta como franja", r,
         {"muestras": 2, "muestras_todo_negro": 1})
if r["margenes"]["izquierda"] != 0.0:
    fallos.append("minimo entre muestras")
    print("FALLA  minimo entre muestras: %r" % (r["margenes"],))
else:
    print("ok     minimo entre muestras")

# Sin BMP no hay con que decodificar: se abandona y se dice por que.
chequear("OBS sin soporte de BMP",
         correr_muestreo([CON_BARRAS], formatos=("png", "jpg")),
         {"muestras": 0, "motivo": "OBS no ofrece capturas en BMP"})

# Si ya no se esta grabando, corta sin tomar nada.
chequear("la grabacion ya termino", correr_muestreo([CON_BARRAS], grabando=False),
         {"muestras": 0})

print("\n%s" % ("TODO OK" if not fallos else "%d FALLAS: %s" % (len(fallos), fallos)))
sys.exit(1 if fallos else 0)
