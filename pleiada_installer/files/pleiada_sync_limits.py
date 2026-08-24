"""
Criterios de sync check — fuente de verdad unica.

Compartido entre:
  · pleiada_app.pyw   (run_sync_check — gatea el upload)
  · pleiada_check.pyw (Synch Checker — el verificador que ve el uploader)

Hasta v0.8.8 cada archivo tenia sus propios umbrales hardcodeados y decidian
distinto sobre la MISMA sesion:

  · techo de tolerancia: app.pyw usaba +15000 ms, check.pyw +10000 ms, asi que
    toda sesion con signed_diff en (10s, 15s] se subia igual pero el verificador
    se la mostraba al uploader como "OFFSET". Confusion directa: un error
    reportado sobre algo que si habia entrado al bucket.
  · base de csv_dur: app.pyw promediaba los 4 CSV, check.pyw usaba uno solo, de
    modo que ambos podian calcular signed_diff distinto sobre la misma sesion y
    la discrepancia no se limitaba a esa franja.
  · check.pyw no conocia los gates de duracion minima (PLE-41) ni de AFK, asi
    que podia mostrar "SESION LISTA PARA ENVIAR" sobre sesiones que el uploader
    rechazaba.

Se unifico en el criterio de pleiada_app.pyw por ser el que decidio que entro
al bucket. sync_verify.py (Pleiada Tools/qa_muestreo) replica estos mismos
valores para la verificacion server-side; si cambian aca, actualizarlo tambien.

DIVERGENCIA CONOCIDA, no unificada a proposito: check.pyw y sync_verify.py
exigen spread de ANCHOR_START == 0 entre los 4 CSV; run_sync_check no compara
los anchors entre archivos. Agregarlo al uploader seria una via de rechazo
nueva sobre sesiones que hoy suben, asi que queda como decision aparte.
"""

import csv as _csv
import os as _os
import struct as _struct

# ── Tolerancia CSV vs video ──────────────────────────────────────────────────
# signed_diff = video_dur - csv_dur   (+ = el video es mas largo)
DIFF_MIN_MS = -4_500    # GOP parcial final descartado por OBS al detener
DIFF_MAX_MS = 15_000    # anchor_fallback (WebSocket + arranque de AHK) en hw lento

# Cortes internos, solo para explicar la causa en el reporte del Synch Checker.
# No gatean nada: cualquier valor en [DIFF_MIN_MS, DIFF_MAX_MS] es sesion valida.
NEAR_ZERO_MS         =    500   # |diff| menor a esto: ruido, sin causa que explicar
ENCODER_FLUSH_MAX_MS = 10_000   # hasta aca el excedente es flush del encoder;
                                # por encima ya es arranque tardio del logger

# ── Gates de sesion ──────────────────────────────────────────────────────────
MIN_SESSION_MS   =  30_000   # PLE-41: sesiones muy cortas dan diff ~0 y pasan
                             # el check sin que haya juego grabado
MAX_CONT_IDLE_MS = 300_000   # 5 min continuos sin input → sesion AFK.
                             # Bajado de 10 a 5 el 24-08-2026 para alinearlo con
                             # el servidor, que ya estaba en 5. Mientras estuvieron
                             # desalineados, una sesion con un hueco de entre 5 y 10
                             # min subia sin aviso y se rechazaba despues.
                             # OJO: sync_verify.py (Pleiada Tools/qa_muestreo) es una
                             # copia deliberada de estos umbrales. Si se toca uno, va
                             # el otro. Ya quedo en 300_000 el 24-08-2026.
IDLE_GAP_MS      =  10_000   # hueco sin mouse ni teclado que cuenta como idle

# Brazo RELATIVO del gate AFK. El umbral absoluto solo no alcanza: una sesion de
# 7 min que es 90% un unico hueco pasa (369 s < 600 s), mientras que una de 2 h
# con un hueco de 10 min (8% de la sesion) se rechaza. Caso real:
# Metro_2033_Redux_22_07_26__20_54_45.
# Nacio en sync_verify.py (server-side, 24-07-2026) y se porto al cliente el
# 25-07 para que el Recorder rechace antes de subir en vez de que la sesion se
# marque despues. Medido sobre las 166 sesiones subidas: al 50% cae 1 y ninguna
# mas. Medido tambien sobre 47 sesiones locales: mediana de la fraccion 0,000,
# la mas alta de gameplay real 0,398, y la unica que cae ya la rechazaba el
# brazo absoluto. No hay riesgo de barrer sesiones sanas.
MAX_IDLE_FRACCION = 0.50

# ── Gate de input vacio (18-08-2026) ─────────────────────────────────────────
# El gate AFK no agarra el peor caso posible: la sesion sin NINGUN evento de
# input. activity() necesita al menos 2 timestamps para medir un hueco, asi que
# con 0 o 1 evento devuelve None, y tanto run_sync_check como el Synch Checker
# como sync_verify.py hacen `bool(act and ...)`: sin medicion no hay AFK, y la
# sesion pasa. La sesion con los CSV de input literalmente vacios era la que mas
# limpio pasaba todos los checks.
#
# Como se ve en disco: los CSV vacios pesan siempre lo mismo, header +
# ANCHOR_START + ANCHOR_END y nada mas — key_log 95 B, mouse_delta_log 89 B,
# mouse_log 97 B.
#
# Medido sobre las 6.368 sesiones del bucket (censo_input_vacio.py, 18-08-2026):
# 925 sesiones / 645 h sin input utilizable, el 13% de las horas. De esas, 729
# tienen el mouse_log lleno — el cursor se movio toda la sesion, o sea que hubo
# mano en el teclado y en el mouse y no se registro ni un evento.
#
# RECALIBRADO 24-08-2026 — el gate fallaba ABIERTO en sesiones cortas.
# Caso: Hollow_Knight_30_07_26__20_17_15 (GA-2026-008), 65,4 s, 2 eventos
# accionables en total. El piso viejo era `n < 2` (2 no es menor que 2) y el
# brazo relativo pedia 1,09 eventos para 65 s: los dos brazos quedaban por
# debajo de lo que la sesion tenia y pasaba como `aprobado`.
#
# Los umbrales viejos (piso 2, 1 evento/min) estaban dos ordenes de magnitud
# por debajo del gameplay real. Medido sobre las 264 sesiones que pasaban el
# gate en las corridas de sync_verify (qa_819_n1 + qa_reemplazo + qa_refuerzo +
# qa_sinvideo, 1.098 sesiones unicas): mediana 2.979 eventos/min, p5 281, p2
# 84,9. En el corpus local de 76 sesiones, la sana mas quieta da 163 ev/min.
# O sea: el corte de 1/min estaba 85x por debajo del percentil 2 de lo sano.
#
# El brazo de duracion solo NO alcanza: con `max(dur_min, 2)` y una tasa de 1
# el umbral para 65 s queda en 2 eventos y la sesion de Hollow Knight sigue
# pasando. Lo que hay que subir es la TASA.
#
# Se unifican los dos brazos en una sola formula, `n < POR_MIN * max(dur_min,
# MIN_MINUTOS_GATE)`: el piso absoluto deja de ser una constante suelta y pasa
# a ser "lo que pide MIN_MINUTOS_GATE de sesion", de modo que no puedan volver
# a quedar descalibrados uno respecto del otro.
#
# Margen: 4x contra la sesion sana mas quieta de produccion (84,9 ev/min) y 8x
# contra el corpus local (163). Costo retroactivo medido sobre el backlog
# entero (4.549 de 4.600 sesiones cruzadas con el censo, 3.587 h, acotando
# eventos por bytes en las dos direcciones con anchos de fila de 23-43 B
# medidos sobre 556.713 filas reales): 2 sesiones / 0,89 h, el 0,02% de las
# horas, y ninguna sesion en zona gris. Las dos son Hollow_Knight_30_07_26 y
# Batman_Arkham_Knight_05_07_26__12_17_55 (<=126 eventos en 52 min).
#
# Ademas del caso corto, la tasa de 20 agarra
# Crimson_Desert_15_08_26__04_59_11 (70 eventos en 6,9 min = 10,1/min,
# active_input_ratio 0,016), que el gate viejo dejaba pasar y que troveo/
# armar_lote.py tuvo que rechazar con una regla aparte de ratio < 0,30.
MIN_EVENTOS_POR_MIN = 20.0     # tasa minima de input accionable por minuto
MIN_MINUTOS_GATE    = 2.0      # duracion minima con la que se evalua la tasa:
                               # abajo de esto el umbral no baja mas, o una
                               # sesion de 1 min pasaria con 20 eventos y una
                               # de 10 s con 3.
# Piso absoluto, derivado. No tocar a mano: es lo que pide MIN_MINUTOS_GATE.
MIN_EVENTOS_INPUT = int(MIN_EVENTOS_POR_MIN * MIN_MINUTOS_GATE)   # 40

# Cuantas filas de posicion de mouse por minuto alcanzan para afirmar que la mano
# estuvo en el mouse. mouse_log se llena por polling a ~16 Hz y —a diferencia de
# los otros tres— NO pasa por el filtro de ventana activa del logger, asi que es
# el testigo independiente: si esta lleno y los otros dos vacios, no fue que el
# jugador no jugo, fue que no se capturo.
#
# Va como TASA y no como total porque el total no escala con la duracion: la
# sesion de ETS2 del 30-05 tiene 163 filas en 91 s (107/min, mano en el mouse) y
# cualquier piso absoluto razonable la daria por quieta. Medido: las sesiones
# rotas del bucket dan cientos por minuto; las que de verdad no tocaron el mouse,
# cero.
MOUSE_POS_POR_MIN_TESTIGO = 60

# ── Gate de video quieto (pantalla negra / imagen congelada) ─────────────────
# El gate AFK mira inputs; este mira la IMAGEN. Son complementarios: si el juego
# queda minimizado o el game capture se cae, OBS graba negro mientras el jugador
# sigue tecleando, y AFK no lo agarra.
#
# Como se mide, sin decodificar un solo pixel: en el MP4 el tamano de cada frame
# ya esta en los boxes (trun en fragmentado, stsz en estandar). Una pantalla
# congelada o negra comprime a casi nada, asi que basta con leer esos tamanos
# —0,15 s sobre un archivo de 6 GB, contra ~2,5 min decodificando con OpenCV,
# que ademas saltea mal en MP4 fragmentado.
#
# OJO: esto depende de que OBS grabe por CALIDAD (CRF/CQP), que es lo que hace
# el perfil Pleiada (Mode=Simple sin RecQuality). Medido: la misma maquina grabo
# una sesion negra a 379 kb/s y gameplay a 31.937 kb/s. Si un usuario forzara
# CBR en su OBS, el negro se rellenaria hasta el bitrate objetivo y este gate
# quedaria ciego para esa sesion.
VIDEO_VENTANA_MS   = 5_000        # se agrega por ventanas: un keyframe cada ~4 s
                                  # parte toda corrida quieta si se mira frame
                                  # por frame, y no se detecta nada nunca
VIDEO_PISO_BYTES   = 200 * 1024   # piso absoluto por ventana. Hace falta porque
                                  # si la sesion ENTERA esta quieta el percentil
                                  # tambien queda bajo y nada parece anomalo.
                                  # Medido: negro real 112 KB/ventana; la ventana
                                  # de gameplay mas baja del corpus, 356 KB.
VIDEO_FRACCION_P90 = 0.10         # o por debajo del 10% del percentil 90 de la
                                  # propia sesion (se adapta al bitrate de cada
                                  # maquina, que hoy no esta fijado)

MAX_VIDEO_QUIETO_MS    = 600_000  # 10 min continuos de imagen quieta → rechazo.
                                  # Margen medido: el gameplay real mas quieto
                                  # del corpus llega a 3,75 min.
VIDEO_QUIETO_RATIO_MAX = 0.95     # o casi toda la sesion quieta, para las
                                  # grabaciones que salieron negras de arranque
                                  # y duran menos que la corrida minima. Margen:
                                  # el gameplay real mas alto del corpus, 72%.


# ── Predicados ───────────────────────────────────────────────────────────────

def csv_duration_ms(anchor_pairs):
    """
    Duracion de sesion segun los CSV: media de los archivos con anchors validos.

    `anchor_pairs` es un iterable de (start_ms, end_ms); los pares incompletos o
    invertidos se descartan. Promediar los 4 evita que la duracion dependa de
    que un archivo puntual falte o venga corto.

    Retorna ms redondeados, o None si ningun par es utilizable.
    """
    # `is not None` y no truthiness: un anchor en 0 es un timestamp valido y el
    # filtro viejo (`if s and e`) lo descartaba silenciosamente. `e > s` ya
    # descarta los pares invertidos o de duracion cero.
    durations = [e - s for s, e in anchor_pairs
                 if s is not None and e is not None and e > s]
    if not durations:
        return None
    return round(sum(durations) / len(durations))


def video_in_range(signed_diff_ms):
    """True si el desfase video/CSV cae dentro de la tolerancia aceptada."""
    return DIFF_MIN_MS <= signed_diff_ms <= DIFF_MAX_MS


def is_short_session(csv_dur_ms):
    """True si la sesion es mas corta que el minimo (PLE-41)."""
    return csv_dur_ms is not None and csv_dur_ms < MIN_SESSION_MS


def idle_fraccion(longest_idle_seconds, session_dur_ms):
    """Que proporcion de la sesion ocupa el hueco sin inputs mas largo (0..1)."""
    if not session_dur_ms:
        return None
    return round((longest_idle_seconds or 0) * 1000 / session_dur_ms, 3)


def is_afk(longest_idle_seconds, session_dur_ms=None):
    """
    True si la sesion se considera AFK, por cualquiera de los dos brazos:
      · absoluto : un tramo continuo sin inputs mayor a MAX_CONT_IDLE_MS
      · relativo : ese tramo ocupa mas de MAX_IDLE_FRACCION de la sesion

    `session_dur_ms` es opcional: sin el solo se evalua el brazo absoluto.
    """
    idle_ms = (longest_idle_seconds or 0) * 1000
    if idle_ms >= MAX_CONT_IDLE_MS:
        return True
    return bool(session_dur_ms and idle_ms >= MAX_IDLE_FRACCION * session_dur_ms)


def contar_eventos_input(session_dir):
    """
    Cuenta los eventos de cada CSV de input. No promedia ni interpreta: devuelve
    los cuatro numeros crudos para que el gate y el diagnostico decidan aparte.

        teclado        KEY_DOWN / KEY_UP        (key_log.csv)
        mouse_crudo    MOVE                     (mouse_delta_log.csv)
        botones        BUTTON_DOWN/UP, SCROLL   (mouse_log.csv)
        mouse_posicion MOVE                     (mouse_log.csv)

    Los tres primeros son el input accionable: lo que un modelo puede aprender.
    El cuarto es solo el testigo (ver MOUSE_POS_TESTIGO).
    """
    conteo = {"teclado": 0, "mouse_crudo": 0, "botones": 0, "mouse_posicion": 0}
    fuentes = (
        ("key_log.csv",         {"KEY_DOWN": "teclado", "KEY_UP": "teclado"}),
        ("mouse_delta_log.csv", {"MOVE": "mouse_crudo"}),
        ("mouse_log.csv",       {"BUTTON_DOWN": "botones", "BUTTON_UP": "botones",
                                 "SCROLL": "botones", "MOVE": "mouse_posicion"}),
    )
    for fname, mapa in fuentes:
        try:
            with open(_os.path.join(str(session_dir), fname),
                      encoding="utf-8", newline="") as f:
                for r in _csv.reader(f):
                    if len(r) >= 2:
                        destino = mapa.get(r[1])
                        if destino:
                            conteo[destino] += 1
        except Exception:
            pass
    return conteo


def eventos_accionables(conteo):
    """Teclas + botones + movimiento crudo de mouse: el input que sirve."""
    return conteo["teclado"] + conteo["mouse_crudo"] + conteo["botones"]


def is_sin_input(conteo, session_dur_ms=None):
    """
    True si la sesion trae menos de MIN_EVENTOS_POR_MIN eventos accionables
    por minuto, evaluado sobre un minimo de MIN_MINUTOS_GATE minutos:

        umbral = MIN_EVENTOS_POR_MIN * max(dur_min, MIN_MINUTOS_GATE)

    Un solo brazo, no dos. El piso absoluto (MIN_EVENTOS_INPUT) es el valor que
    toma esa misma formula en la duracion minima, y aplica tambien cuando no se
    conoce la duracion. Ver el bloque de constantes: tenerlos como dos brazos
    sueltos fue lo que dejo pasar la sesion de 65 s con 2 eventos.

    El video puede estar perfecto: este gate mira solo si quedo registrado lo
    que el jugador hizo. Sin eso la sesion no es un dataset, es un video.
    """
    n = eventos_accionables(conteo)
    dur_min = (session_dur_ms / 60_000) if session_dur_ms else 0
    return n < MIN_EVENTOS_POR_MIN * max(dur_min, MIN_MINUTOS_GATE)


def diagnostico_sin_input(conteo, session_dur_ms=None):
    """
    Por que quedo sin input. Separa dos causas que se ven igual en los CSV pero
    se resuelven distinto:

      "captura_bloqueada" — mouse_log lleno y los otros vacios. El cursor se
          movio toda la sesion, asi que hubo mano en el teclado y el mouse: los
          eventos se perdieron entre el jugador y el log (filtro de ventana
          activa apuntando al exe equivocado, anticheat o antivirus bloqueando
          los hooks, juego corriendo elevado). Es perdida de datos real.

      "sin_teclado_ni_mouse" — no se movio ni el cursor. O la sesion es un
          joystick (que hoy no se captura) o directamente no se jugo.

    Retorna None si la sesion tiene input y no hay nada que diagnosticar.
    """
    if not is_sin_input(conteo, session_dur_ms):
        return None
    pos = conteo["mouse_posicion"]
    if session_dur_ms:
        por_min = pos / (session_dur_ms / 60_000)
    else:
        # Sin duracion no hay tasa: se cae al piso de un minuto de movimiento.
        por_min = pos
    if por_min >= MOUSE_POS_POR_MIN_TESTIGO:
        return "captura_bloqueada"
    return "sin_teclado_ni_mouse"


# ── Lectura de boxes MP4 (solo headers, sin decodificar) ─────────────────────

def _next_box(f, pos, limite):
    """(fin_del_box, tipo, inicio_de_datos) o (None, None, None)."""
    if pos + 8 > limite:
        return None, None, None
    f.seek(pos)
    raw = f.read(8)
    if len(raw) < 8:
        return None, None, None
    size  = _struct.unpack('>I', raw[:4])[0]
    btype = raw[4:8]
    if size == 1:                      # tamano extendido de 64 bits
        ext = f.read(8)
        if len(ext) < 8:
            return None, None, None
        size = _struct.unpack('>Q', ext)[0]
        if size < 16:
            return None, None, None
        return pos + size, btype, pos + 16
    if size < 8:
        return None, None, None
    return pos + size, btype, pos + 8


def _find_box(f, ini, fin, objetivo):
    pos = ini
    while True:
        box_fin, btype, datos = _next_box(f, pos, fin)
        if box_fin is None:
            return None, None
        if btype == objetivo:
            return datos, box_fin
        pos = box_fin


def _find_all(f, ini, fin, objetivo):
    pos, out = ini, []
    while True:
        box_fin, btype, datos = _next_box(f, pos, fin)
        if box_fin is None:
            return out
        if btype == objetivo:
            out.append((datos, box_fin))
        pos = box_fin


def _find_moov(f, size):
    """
    Camina los boxes top-level desde 0. Sirve igual para moov al inicio (MP4
    fragmentado) que al final (MP4 estandar): el mdat se saltea por su campo
    size, sin leer su contenido. Buscar moov arrancando en `size - N` cae dentro
    del mdat y parsea basura.
    """
    pos = 0
    while pos < size:
        box_fin, btype, datos = _next_box(f, pos, size)
        if box_fin is None:
            return None, None
        if btype == b'moov':
            return datos, box_fin
        pos = box_fin
    return None, None


def _trak_video(f, moov_datos, moov_fin):
    """(mdia_datos, mdia_fin, track_id, timescale) del track de video."""
    for trak_datos, trak_fin in _find_all(f, moov_datos, moov_fin, b'trak'):
        mdia_datos, mdia_fin = _find_box(f, trak_datos, trak_fin, b'mdia')
        if mdia_datos is None:
            continue
        hdlr, _ = _find_box(f, mdia_datos, mdia_fin, b'hdlr')
        if hdlr is None:
            continue
        f.seek(hdlr + 8)
        if f.read(4) != b'vide':          # descarta el track de audio
            continue

        tkhd, _ = _find_box(f, trak_datos, trak_fin, b'tkhd')
        if tkhd is None:
            continue
        f.seek(tkhd)
        ver = _struct.unpack('B', f.read(1))[0]
        f.read(3)
        f.read(16 if ver == 1 else 8)
        track_id = _struct.unpack('>I', f.read(4))[0]

        mdhd, _ = _find_box(f, mdia_datos, mdia_fin, b'mdhd')
        if mdhd is None:
            continue
        f.seek(mdhd)
        ver2 = _struct.unpack('B', f.read(1))[0]
        f.read(3)
        f.read(16 if ver2 == 1 else 8)
        timescale = _struct.unpack('>I', f.read(4))[0]
        if not timescale:
            continue
        return mdia_datos, mdia_fin, track_id, timescale
    return None, None, None, None


def mp4_is_truncated(path):
    """
    True si el MP4 esta truncado/corrupto (OBS murio sin cerrar la grabacion).

    Recorre los boxes top-level desde el byte 0 saltando por size, asi que no
    lee el contenido del mdat. Acepta el archivo si encuentra moov O moof: un
    MP4 fragmentado de OBS es valido aunque el indice final no se haya escrito.
    """
    try:
        fsize = _os.path.getsize(path)
        if fsize < 200:
            return True
        with open(path, 'rb') as f:
            pos = 0
            while pos + 8 <= fsize:
                f.seek(pos)
                raw = f.read(8)
                if len(raw) < 8:
                    break
                size  = _struct.unpack('>I', raw[:4])[0]
                btype = raw[4:8]
                if btype in (b'moov', b'moof'):
                    return False              # archivo completo
                if size == 1:                # tamano 64-bit
                    ext = f.read(8)
                    if len(ext) < 8:
                        break
                    size = _struct.unpack('>Q', ext)[0]
                    if size < 16:
                        break
                elif size == 0:              # box hasta EOF
                    break
                elif size < 8:
                    break
                if pos + size > fsize:       # declara mas alla del EOF → truncado
                    break
                pos += size
        return True
    except Exception:
        return False


def mp4_duration_ms(path):
    """
    Duracion real del MP4 en ms, o None si no se puede parsear.

    Soporta los dos formatos que puede producir OBS:
      · MP4 estandar (moov al final): lee mdhd.duration directamente.
      · MP4 fragmentado (moof):       acumula tfdt + duraciones de trun.

    El moov se ubica con _find_moov, que camina los boxes top-level desde 0.
    La copia que tenia pleiada_check.pyw lo buscaba en los ultimos 512 KB, lo
    que cae dentro del mdat y parsea basura: medido sobre 63 archivos, fallaba
    en 39 de los 42 MP4 estandar (los 3 que andaban pesaban menos de 512 KB, o
    sea que el offset daba 0 de casualidad). El verificador caia entonces al
    conteo de frames de OpenCV, que queda ~1-2 s corto, y calculaba un
    signed_diff distinto al del uploader sobre la misma sesion.
    """
    try:
        fsize = _os.path.getsize(path)
        with open(path, 'rb') as f:
            moov_data, moov_end = _find_moov(f, fsize)
            if moov_data is None:
                return None   # sin moov → truncado o formato desconocido

            trak_d, trak_e = _find_box(f, moov_data, moov_end, b'trak')
            if not trak_d:
                return None
            mdia_d, mdia_e = _find_box(f, trak_d, trak_e, b'mdia')
            if not mdia_d:
                return None
            mdhd_d, _ = _find_box(f, mdia_d, mdia_e, b'mdhd')
            if not mdhd_d:
                return None

            f.seek(mdhd_d)
            version = _struct.unpack('B', f.read(1))[0]
            f.read(3)                              # flags
            f.read(16 if version == 1 else 8)      # creation + modification time
            timescale = _struct.unpack('>I', f.read(4))[0]
            if not timescale:
                return None

            # mdhd.duration: en MP4 estandar trae la duracion real; en
            # fragmentado suele ser 0 o el sentinel 0xFFFF...
            if version == 1:
                mdhd_dur = _struct.unpack('>Q', f.read(8))[0]
            else:
                mdhd_dur = _struct.unpack('>I', f.read(4))[0]
            sentinel = 0xFFFFFFFFFFFFFFFF if version == 1 else 0xFFFFFFFF
            if mdhd_dur and mdhd_dur != sentinel:
                return round(mdhd_dur / timescale * 1000)

            # Fragmentado: acumular tfdt + trun sobre todos los moof
            last_end_time = 0
            pos = 0
            while pos < fsize:
                box_end, btype, data = _next_box(f, pos, fsize)
                if box_end is None:
                    break
                if btype == b'moof':
                    traf_d, traf_e = _find_box(f, data, box_end, b'traf')
                    if traf_d:
                        default_dur = 0
                        tfhd_d, _ = _find_box(f, traf_d, traf_e, b'tfhd')
                        if tfhd_d:
                            f.seek(tfhd_d); f.read(1)
                            fl = f.read(3)
                            tfhd_flags = (fl[0] << 16) | (fl[1] << 8) | fl[2]
                            f.read(4)   # track_ID
                            if tfhd_flags & 0x000001: f.read(8)
                            if tfhd_flags & 0x000002: f.read(4)
                            if tfhd_flags & 0x000008:
                                default_dur = _struct.unpack('>I', f.read(4))[0]

                        base_dt = 0
                        tfdt_d, _ = _find_box(f, traf_d, traf_e, b'tfdt')
                        if tfdt_d:
                            f.seek(tfdt_d)
                            tfdt_ver = _struct.unpack('B', f.read(1))[0]
                            f.read(3)
                            base_dt = (_struct.unpack('>Q', f.read(8))[0] if tfdt_ver == 1
                                       else _struct.unpack('>I', f.read(4))[0])

                        frag_dur = 0
                        trun_d, _ = _find_box(f, traf_d, traf_e, b'trun')
                        if trun_d:
                            f.seek(trun_d); f.read(1)
                            fl = f.read(3)
                            trun_flags = (fl[0] << 16) | (fl[1] << 8) | fl[2]
                            count = _struct.unpack('>I', f.read(4))[0]
                            if trun_flags & 0x001: f.read(4)
                            if trun_flags & 0x004: f.read(4)
                            has_dur = bool(trun_flags & 0x100)
                            has_sz  = bool(trun_flags & 0x200)
                            has_fl  = bool(trun_flags & 0x400)
                            has_cts = bool(trun_flags & 0x800)
                            for _ in range(count):
                                frag_dur += (_struct.unpack('>I', f.read(4))[0]
                                             if has_dur else default_dur)
                                if has_sz:  f.read(4)
                                if has_fl:  f.read(4)
                                if has_cts: f.read(4)

                        end_time = base_dt + frag_dur
                        if end_time > last_end_time:
                            last_end_time = end_time
                pos = box_end

        if last_end_time == 0:
            return None
        return round(last_end_time / timescale * 1000)

    except Exception:
        return None


def _ventanas_fragmentado(f, size, track_id, timescale):
    """{indice_ventana: bytes} recorriendo moof/traf/trun."""
    acc, pos = {}, 0
    while pos < size:
        box_fin, btype, datos = _next_box(f, pos, size)
        if box_fin is None:
            break
        if btype == b'moof':
            for traf, traf_fin in _find_all(f, datos, box_fin, b'traf'):
                tfhd, _ = _find_box(f, traf, traf_fin, b'tfhd')
                if tfhd is None:
                    continue
                f.seek(tfhd)
                f.read(1)
                fl = f.read(3)
                flags = (fl[0] << 16) | (fl[1] << 8) | fl[2]
                if _struct.unpack('>I', f.read(4))[0] != track_id:
                    continue
                if flags & 0x000001: f.read(8)
                if flags & 0x000002: f.read(4)
                dur_default = _struct.unpack('>I', f.read(4))[0] if flags & 0x000008 else 0

                base_t = 0
                tfdt, _ = _find_box(f, traf, traf_fin, b'tfdt')
                if tfdt is not None:
                    f.seek(tfdt)
                    v = _struct.unpack('B', f.read(1))[0]
                    f.read(3)
                    base_t = _struct.unpack('>Q' if v == 1 else '>I',
                                            f.read(8 if v == 1 else 4))[0]

                trun, _ = _find_box(f, traf, traf_fin, b'trun')
                if trun is None:
                    continue
                f.seek(trun)
                f.read(1)
                fl = f.read(3)
                tflags = (fl[0] << 16) | (fl[1] << 8) | fl[2]
                n = _struct.unpack('>I', f.read(4))[0]
                if tflags & 0x001: f.read(4)
                if tflags & 0x004: f.read(4)
                hay_dur   = bool(tflags & 0x100)
                hay_size  = bool(tflags & 0x200)
                hay_flags = bool(tflags & 0x400)
                hay_cts   = bool(tflags & 0x800)
                if not hay_size:          # sin tamanos no se puede medir nada
                    continue
                t = base_t
                for _ in range(n):
                    d = _struct.unpack('>I', f.read(4))[0] if hay_dur else dur_default
                    s = _struct.unpack('>I', f.read(4))[0]
                    if hay_flags: f.read(4)
                    if hay_cts:   f.read(4)
                    k = int(t / timescale * 1000) // VIDEO_VENTANA_MS
                    acc[k] = acc.get(k, 0) + s
                    t += d
        pos = box_fin
    return acc


def _ventanas_estandar(f, mdia_datos, mdia_fin, timescale):
    """{indice_ventana: bytes} desde stsz (tamanos) + stts (duraciones)."""
    minf, minf_fin = _find_box(f, mdia_datos, mdia_fin, b'minf')
    if minf is None:
        return {}
    stbl, stbl_fin = _find_box(f, minf, minf_fin, b'stbl')
    if stbl is None:
        return {}

    stsz, _ = _find_box(f, stbl, stbl_fin, b'stsz')
    if stsz is None:
        return {}
    f.seek(stsz)
    f.read(4)                                    # version + flags
    uniforme = _struct.unpack('>I', f.read(4))[0]
    count    = _struct.unpack('>I', f.read(4))[0]
    if count <= 0:
        return {}
    if uniforme:
        tamanos = [uniforme] * count
    else:
        raw = f.read(4 * count)
        if len(raw) < 4 * count:
            return {}
        tamanos = _struct.unpack('>%dI' % count, raw)

    stts, _ = _find_box(f, stbl, stbl_fin, b'stts')
    if stts is None:
        return {}
    f.seek(stts)
    f.read(4)
    entradas = _struct.unpack('>I', f.read(4))[0]
    duraciones = []
    for _ in range(entradas):
        c, d = _struct.unpack('>II', f.read(8))
        duraciones.extend([d] * c)

    acc, t = {}, 0
    for i, s in enumerate(tamanos):
        k = int(t / timescale * 1000) // VIDEO_VENTANA_MS
        acc[k] = acc.get(k, 0) + s
        t += duraciones[i] if i < len(duraciones) else 0
    return acc


def video_stillness(path):
    """
    Mide cuanto tiempo la IMAGEN estuvo quieta (negra o congelada).

    Retorna dict con:
      · longest_still_ms : corrida continua mas larga de imagen quieta
      · still_ratio      : proporcion de la sesion que estuvo quieta (0..1)
      · mode             : "fragmentado" | "estandar"
    o None si el MP4 no se pudo leer (no bloquea la sesion por eso).
    """
    try:
        size = _os.path.getsize(path)
        with open(path, 'rb') as f:
            moov_datos, moov_fin = _find_moov(f, size)
            if moov_datos is None:
                return None
            mdia_datos, mdia_fin, track_id, timescale = _trak_video(f, moov_datos, moov_fin)
            if mdia_datos is None:
                return None

            acc  = _ventanas_fragmentado(f, size, track_id, timescale)
            modo = "fragmentado"
            if not acc:
                acc  = _ventanas_estandar(f, mdia_datos, mdia_fin, timescale)
                modo = "estandar"
        if len(acc) < 3:
            return None

        # La ultima ventana casi siempre es parcial: pesa menos solo por estar
        # cortada, y contarla inventaria una ventana quieta al final.
        lo, hi = min(acc), max(acc) - 1
        if hi <= lo:
            return None
        serie = [acc.get(i, 0) for i in range(lo, hi + 1)]

        ordenado = sorted(serie)
        p90 = ordenado[int(len(ordenado) * 0.9)]
        umbral = max(int(p90 * VIDEO_FRACCION_P90), VIDEO_PISO_BYTES)

        peor = actual = quietas = 0
        for b in serie:
            if b < umbral:
                actual  += VIDEO_VENTANA_MS
                quietas += 1
                if actual > peor:
                    peor = actual
            else:
                actual = 0

        return {
            "longest_still_ms": peor,
            "still_ratio":      round(quietas / len(serie), 3),
            "mode":             modo,
        }
    except Exception:
        return None   # si el parseo falla, no bloquear la sesion por esto


def is_video_still(stillness):
    """True si el video estuvo quieto lo suficiente como para rechazar la sesion."""
    if not stillness:
        return False
    return (stillness.get("longest_still_ms", 0) >= MAX_VIDEO_QUIETO_MS
            or stillness.get("still_ratio", 0) >= VIDEO_QUIETO_RATIO_MAX)


def activity(session_dir, start_ms, end_ms):
    """
    Mide actividad de input vs inactividad (cutscenes / menus / AFK).
    Idle = huecos >= IDLE_GAP_MS sin movimiento de mouse ni eventos de teclado.
    Usa los anchors (start/end) como bordes. Retorna dict o None.

    Vive aca —y no en pleiada_app.pyw, de donde salio— para que el gate AFK del
    uploader y el del Synch Checker corran exactamente el mismo calculo.
    `session_dir` acepta str o Path.
    """
    ts = []
    for fname, eventos in (("mouse_delta_log.csv", ("MOVE",)),
                           ("key_log.csv",         ("KEY_DOWN", "KEY_UP"))):
        try:
            with open(_os.path.join(str(session_dir), fname), encoding="utf-8") as f:
                for r in _csv.reader(f):
                    if len(r) >= 2 and r[1] in eventos:
                        try:
                            ts.append(int(r[0]))
                        except Exception:
                            pass
        except Exception:
            pass

    if not start_ms or not end_ms or end_ms <= start_ms or len(ts) < 2:
        return None

    ts.sort()
    span = end_ms - start_ms
    idle = longest = 0
    prev = start_ms
    for t in ts:
        if t < start_ms or t > end_ms:
            continue
        gap = t - prev
        if gap >= IDLE_GAP_MS:
            idle   += gap
            longest = max(longest, gap)
        prev = t
    gap = end_ms - prev
    if gap >= IDLE_GAP_MS:
        idle   += gap
        longest = max(longest, gap)

    active = span - idle
    return {
        "active_input_ratio":    round(active / span, 3),
        "active_seconds":        round(active / 1000, 1),
        "idle_seconds":          round(idle / 1000, 1),
        "longest_idle_seconds":  round(longest / 1000, 1),
        "idle_gap_threshold_ms": IDLE_GAP_MS,
    }
