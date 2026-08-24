"""
Tests del gate de input vacio (pleiada_sync_limits, v0.9.0).

Lo que importa de verdad: que una sesion sin registro de input NO se declare
buena. Es el caso que mas limpio pasaba todos los checks —el gate AFK mide
huecos entre eventos y con cero eventos no mide nada, asi que devolvia None y
`bool(act and ...)` daba False— y llego al cliente: 925 sesiones / 645 h del
bucket, el 13% de las horas subidas.

El segundo tema es no barrer sesiones sanas. Los tests de margen usan las
sesiones reales de Documents\\Pleiada Recordings cuando estan disponibles, y se
saltean solas si no estan (por ejemplo en una maquina de CI).
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

FILES = Path(r"C:\Users\mspin\Documents\pleiada-recorder\pleiada_installer\files")
sys.path.insert(0, str(FILES))

import pleiada_sync_limits as sl  # noqa: E402

GRABACIONES = Path.home() / "Documents" / "Pleiada Recordings"

# Cabeceras reales que escribe input_logger.ahk.
CABECERAS = {
    "key_log.csv":         "timestamp_ms,event_type,key,vk_code",
    "mouse_delta_log.csv": "timestamp_ms,event_type,dx,dy",
    "mouse_log.csv":       "timestamp_ms,event_type,x,y,button",
    "video_timeline.csv":  "timestamp_ms,event_type",
}
T0 = 1_787_000_000_000


def _sesion(dirpath, teclas=0, deltas=0, botones=0, posiciones=0, dur_ms=3_600_000):
    """Arma una carpeta de sesion sintetica con los 4 CSV y sus anchors."""
    fin = T0 + dur_ms
    filas = {k: [v] for k, v in CABECERAS.items()}
    filas["key_log.csv"].append(f"{T0},ANCHOR_START,,")
    filas["mouse_delta_log.csv"].append(f"{T0},ANCHOR_START,,")
    filas["mouse_log.csv"].append(f"{T0},ANCHOR_START,,,")
    filas["video_timeline.csv"].append(f"{T0},ANCHOR_START")

    paso = max(dur_ms // max(teclas + deltas + botones + posiciones, 1), 1)
    for i in range(teclas):
        filas["key_log.csv"].append(f"{T0 + i * paso},KEY_DOWN,W,57")
    for i in range(deltas):
        filas["mouse_delta_log.csv"].append(f"{T0 + i * paso},MOVE,3,-2")
    for i in range(botones):
        filas["mouse_log.csv"].append(f"{T0 + i * paso},BUTTON_DOWN,900,540,LEFT")
    for i in range(posiciones):
        filas["mouse_log.csv"].append(f"{T0 + i * paso},MOVE,{900 + i % 40},540,")

    filas["key_log.csv"].append(f"{fin},ANCHOR_END,,")
    filas["mouse_delta_log.csv"].append(f"{fin},ANCHOR_END,,")
    filas["mouse_log.csv"].append(f"{fin},ANCHOR_END,,,")
    filas["video_timeline.csv"].append(f"{fin},ANCHOR_END")

    for nombre, lineas in filas.items():
        (Path(dirpath) / nombre).write_text("\r\n".join(lineas) + "\r\n", encoding="utf-8")
    return dirpath


class TestConteo(unittest.TestCase):
    def test_cuenta_cada_csv_por_separado(self):
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, teclas=10, deltas=200, botones=5, posiciones=1000)
            c = sl.contar_eventos_input(d)
            self.assertEqual(c["teclado"], 10)
            self.assertEqual(c["mouse_crudo"], 200)
            self.assertEqual(c["botones"], 5)
            self.assertEqual(c["mouse_posicion"], 1000)

    def test_los_anchors_no_cuentan_como_input(self):
        with tempfile.TemporaryDirectory() as d:
            _sesion(d)   # solo header + los dos anchors
            c = sl.contar_eventos_input(d)
            self.assertEqual(sl.eventos_accionables(c), 0)

    def test_carpeta_inexistente_no_explota(self):
        c = sl.contar_eventos_input(r"C:\no\existe\esta\carpeta")
        self.assertEqual(sl.eventos_accionables(c), 0)


class TestGate(unittest.TestCase):
    def test_csv_vacios_se_rechazan(self):
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, posiciones=20_000)   # una hora de cursor, cero eventos
            c = sl.contar_eventos_input(d)
            self.assertTrue(sl.is_sin_input(c, 3_600_000))

    def test_un_solo_evento_tambien_se_rechaza(self):
        """El caso que se le escapaba a activity(): con 1 evento devuelve None."""
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, deltas=1, posiciones=20_000)
            c = sl.contar_eventos_input(d)
            self.assertIsNone(sl.activity(d, T0, T0 + 3_600_000),
                              "activity() deberia seguir sin poder medir con 1 evento")
            self.assertTrue(sl.is_sin_input(c, 3_600_000),
                            "pero el gate nuevo tiene que rechazarla igual")

    def test_brazo_relativo_agarra_la_sesion_casi_vacia(self):
        """20 eventos en una hora pasan el piso absoluto pero no son gameplay."""
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, teclas=20, posiciones=20_000)
            c = sl.contar_eventos_input(d)
            self.assertTrue(sl.is_sin_input(c, 3_600_000))

    def test_gameplay_normal_pasa(self):
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, teclas=3_000, deltas=50_000, botones=800, posiciones=20_000)
            c = sl.contar_eventos_input(d)
            self.assertFalse(sl.is_sin_input(c, 3_600_000))

    def test_solo_mouse_sin_teclado_pasa(self):
        """Un juego que se juega solo con mouse no es una sesion rota."""
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, deltas=40_000, botones=1_200, posiciones=20_000)
            c = sl.contar_eventos_input(d)
            self.assertFalse(sl.is_sin_input(c, 3_600_000))

    def test_solo_teclado_sin_mouse_pasa(self):
        """Side-scroller jugado con teclado y la mano nunca en el mouse: valido.
        Son las 4 sesiones que Troveo reporto como 'rawmouse only' y no son
        defecto nuestro."""
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, teclas=8_000, posiciones=5)
            c = sl.contar_eventos_input(d)
            self.assertFalse(sl.is_sin_input(c, 3_600_000))


class TestSesionCorta(unittest.TestCase):
    """Regresion del 24-08-2026: el gate fallaba ABIERTO en sesiones cortas.

    Con los dos brazos sueltos (piso 2 + 1 evento/min) el brazo relativo pedia
    menos que el piso para toda sesion de menos de 2 min, asi que dos eventos
    alcanzaban para pasar. El peor caso posible era el que pasaba mas limpio,
    igual que en el bug original.
    """

    def test_la_sesion_de_65s_con_2_eventos_se_rechaza(self):
        """Caso real: Hollow_Knight_30_07_26__20_17_15 (GA-2026-008), orden
        GA-2026-008, 65,4 s. Medida contra produccion: teclado=0, mouse_crudo=1,
        botones=1, mouse_posicion=24. Daba sin_input=False y qa_status la
        clasificaba como `aprobado`."""
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, deltas=1, botones=1, posiciones=24, dur_ms=65_400)
            c = sl.contar_eventos_input(d)
            self.assertEqual(sl.eventos_accionables(c), 2)
            self.assertTrue(sl.is_sin_input(c, 65_400),
                            "la sesion de 65 s con 2 eventos tiene que caer")

    def test_el_umbral_no_baja_por_debajo_del_piso(self):
        """Una sesion mas corta no puede comprar un umbral mas barato: abajo de
        MIN_MINUTOS_GATE el corte se queda clavado en MIN_EVENTOS_INPUT."""
        piso = sl.MIN_EVENTOS_INPUT
        for dur_ms in (30_000, 45_000, 65_400, 90_000, 119_000):
            with tempfile.TemporaryDirectory() as d:
                _sesion(d, teclas=piso - 1, dur_ms=dur_ms)
                c = sl.contar_eventos_input(d)
                self.assertTrue(sl.is_sin_input(c, dur_ms),
                                f"{piso - 1} eventos en {dur_ms} ms deberian caer")
            with tempfile.TemporaryDirectory() as d:
                _sesion(d, teclas=piso, dur_ms=dur_ms)
                c = sl.contar_eventos_input(d)
                self.assertFalse(sl.is_sin_input(c, dur_ms),
                                 f"{piso} eventos en {dur_ms} ms deberian pasar")

    def test_el_piso_es_derivado_de_la_tasa(self):
        """Si alguien toca una constante y no la otra, los dos brazos vuelven a
        quedar descalibrados. El piso tiene que salir de la tasa."""
        self.assertEqual(sl.MIN_EVENTOS_INPUT,
                         int(sl.MIN_EVENTOS_POR_MIN * sl.MIN_MINUTOS_GATE))

    def test_sin_duracion_se_aplica_el_piso(self):
        """run_sync_check puede no tener csv_dur si los anchors estan rotos."""
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, teclas=sl.MIN_EVENTOS_INPUT - 1)
            c = sl.contar_eventos_input(d)
            self.assertTrue(sl.is_sin_input(c, None))

    def test_el_goteo_de_input_tambien_cae(self):
        """Caso real: Crimson_Desert_15_08_26__04_59_11, 70 eventos en 6,9 min
        (10,1/min, active_input_ratio 0,016). El gate viejo la dejaba pasar
        —tiene input— y troveo/armar_lote.py tuvo que rechazarla con una regla
        aparte de ratio < 0,30. El gate AFK no la agarra: los huecos son cortos.
        """
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, teclas=70, posiciones=400, dur_ms=414_000)
            c = sl.contar_eventos_input(d)
            self.assertTrue(sl.is_sin_input(c, 414_000))

    def test_una_sesion_corta_pero_jugada_pasa(self):
        """El otro lado: 31 s de gameplay real (MIN_SESSION_MS es 30 s) trae
        cientos de eventos y no la puede barrer el piso."""
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, teclas=40, deltas=900, botones=15, posiciones=500,
                    dur_ms=31_000)
            c = sl.contar_eventos_input(d)
            self.assertFalse(sl.is_sin_input(c, 31_000))


class TestDiagnostico(unittest.TestCase):
    def test_mouse_moviendose_es_captura_bloqueada(self):
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, posiciones=20_000)
            c = sl.contar_eventos_input(d)
            self.assertEqual(sl.diagnostico_sin_input(c, 3_600_000), "captura_bloqueada")

    def test_sin_movimiento_es_sin_teclado_ni_mouse(self):
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, posiciones=3)
            c = sl.contar_eventos_input(d)
            self.assertEqual(sl.diagnostico_sin_input(c, 3_600_000), "sin_teclado_ni_mouse")

    def test_es_una_tasa_y_no_un_total(self):
        """163 filas de posicion son 'quieto' en una hora y 'mano en el mouse' en
        91 s. Caso real: Euro Truck Simulator 2_30_05_26__18_38_18."""
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, posiciones=163, dur_ms=90_952)
            c = sl.contar_eventos_input(d)
            self.assertEqual(sl.diagnostico_sin_input(c, 90_952), "captura_bloqueada")
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, posiciones=163, dur_ms=3_600_000)
            c = sl.contar_eventos_input(d)
            self.assertEqual(sl.diagnostico_sin_input(c, 3_600_000), "sin_teclado_ni_mouse")

    def test_sesion_sana_no_tiene_diagnostico(self):
        with tempfile.TemporaryDirectory() as d:
            _sesion(d, teclas=3_000, deltas=50_000, posiciones=20_000)
            c = sl.contar_eventos_input(d)
            self.assertIsNone(sl.diagnostico_sin_input(c, 3_600_000))


@unittest.skipUnless(GRABACIONES.is_dir(), "sin corpus local de sesiones")
class TestCorpusLocal(unittest.TestCase):
    """Margen real: el gate no puede barrer sesiones sanas."""

    @classmethod
    def setUpClass(cls):
        cls.sesiones = []
        for d in sorted(GRABACIONES.iterdir()):
            if not (d / "key_log.csv").is_file():
                continue
            ts = []
            try:
                for linea in (d / "key_log.csv").read_text(encoding="utf-8-sig").splitlines():
                    p = linea.split(",")
                    if len(p) >= 2 and p[1] in ("ANCHOR_START", "ANCHOR_END"):
                        ts.append(int(p[0]))
            except Exception:
                pass
            dur = (max(ts) - min(ts)) if len(ts) >= 2 else None
            cls.sesiones.append((d.name, sl.contar_eventos_input(d), dur))

    def test_las_rechazadas_no_son_gameplay(self):
        """Antes del 24-08-2026 esto exigia que toda rechazada tuviera input en
        CERO, porque el gate solo disparaba con `n < 2`. Con un gate de tasa esa
        afirmacion es falsa por construccion: el punto es agarrar tambien el
        goteo. La invariante que queda —y que sigue siendo real— es que ninguna
        sesion de duracion valida con algo de input se cae.

        Medido sobre el corpus local: la unica rechazada con input es un stub de
        0,9 s (2026-05-16 17-15-03), que MIN_SESSION_MS ya descarta por su lado.
        """
        for nombre, c, dur in self.sesiones:
            if not sl.is_sin_input(c, dur):
                continue
            if sl.eventos_accionables(c) == 0:
                continue
            self.assertLess(dur or 0, sl.MIN_SESSION_MS,
                            f"{nombre} tiene input, dura lo suficiente, "
                            f"y aun asi la rechaza el gate")

    def test_las_sanas_quedan_lejos_del_corte(self):
        """La sesion sana mas quieta del corpus tiene que quedar con margen sobre
        el corte, o el umbral esta comiendo gameplay real.

        El factor era 10 cuando el corte estaba en 1 ev/min. Con el corte en 20
        (recalibrado 24-08-2026) el margen real medido es: 163 ev/min en el
        corpus local = 8x, y 84,9 ev/min en la sesion sana mas quieta de
        produccion = 4x. Se exige 4x, que es el peor de los dos.
        """
        peor = None
        for nombre, c, dur in self.sesiones:
            if sl.is_sin_input(c, dur) or not dur:
                continue
            por_min = sl.eventos_accionables(c) / (dur / 60_000)
            if peor is None or por_min < peor[1]:
                peor = (nombre, por_min)
        if peor:
            self.assertGreater(peor[1], 4 * sl.MIN_EVENTOS_POR_MIN,
                               f"margen flaco: {peor[0]} con {peor[1]:.1f} ev/min")


if __name__ == "__main__":
    unittest.main(verbosity=2)
