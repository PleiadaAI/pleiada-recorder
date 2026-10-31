"""
Tests de la v0.9.24 (pleiada_sync_limits): minimo de sesion de 5 min con la
excepcion de 30 s para lo grabado antes, y spec de video antes de subir.

Los casos de spec arman un MP4 fragmentado sintetico con las mismas cajas que
escribe OBS. La comparacion contra ffprobe sobre grabaciones reales queda fuera
de este archivo porque depende de la maquina.
"""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

FILES = Path(__file__).resolve().parents[1] / "pleiada_installer" / "files"
sys.path.insert(0, str(FILES))

import pleiada_sync_limits as sl  # noqa: E402


def _box(tipo, *partes):
    cuerpo = b"".join(partes)
    return struct.pack(">I", len(cuerpo) + 8) + tipo + cuerpo


def _mp4(ancho, alto, fps, muestras=600, timescale=90_000, por_muestra=True):
    dur = round(timescale / fps)
    tkhd = _box(b"tkhd", bytes(4), bytes(8), struct.pack(">I", 1), bytes(64))
    mdhd = _box(b"mdhd", bytes(4), bytes(8), struct.pack(">II", timescale, 0), bytes(4))
    hdlr = _box(b"hdlr", bytes(8), b"vide", bytes(12))
    entrada = bytes(24) + struct.pack(">HH", ancho, alto) + bytes(50)
    stsd = _box(b"stsd", bytes(4), struct.pack(">I", 1), _box(b"avc1", entrada))
    stts = _box(b"stts", bytes(4), struct.pack(">I", 0))
    minf = _box(b"minf", _box(b"stbl", stsd, stts))
    trak = _box(b"trak", tkhd, _box(b"mdia", mdhd, hdlr, minf))
    trex = _box(b"trex", bytes(4), struct.pack(">IIIII", 1, 1, dur, 0, 0))
    moov = _box(b"moov", trak, _box(b"mvex", trex))
    tfhd = _box(b"tfhd", bytes(4), struct.pack(">I", 1))
    if por_muestra:
        filas = struct.pack(">I", dur) * muestras
        trun = _box(b"trun", b"\0\0\x01\0", struct.pack(">I", muestras), filas)
    else:
        trun = _box(b"trun", bytes(4), struct.pack(">I", muestras))
    moof = _box(b"moof", _box(b"traf", tfhd, trun))
    return _box(b"ftyp", b"isom") + moov + moof + _box(b"mdat", bytes(32))


class MinimoDeSesion(unittest.TestCase):
    def test_build_actual_pide_5_minutos(self):
        self.assertTrue(sl.is_short_session(299_999))
        self.assertFalse(sl.is_short_session(300_000))
        self.assertEqual(sl.min_session_texto(), "5 minutos")

    def test_excepcion_para_versiones_anteriores(self):
        for version in ("v0.9.23", "v0.8.11", ""):
            self.assertFalse(sl.is_short_session(30_000, version), version)
            self.assertTrue(sl.is_short_session(29_999, version), version)
            self.assertEqual(sl.min_session_texto(version), "30 segundos")

    def test_la_excepcion_no_alcanza_a_la_v0_9_24(self):
        for version in ("v0.9.24", "v0.9.100", "v0.10.0"):
            self.assertTrue(sl.is_short_session(60_000, version), version)

    def test_version_desde_el_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(sl.session_recorder_version(d))
            meta = Path(d) / "session_metadata.json"
            meta.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")
            self.assertEqual(sl.session_recorder_version(d), "")
            meta.write_text(json.dumps({"recorder_version": "v0.9.23"}), encoding="utf-8")
            self.assertEqual(sl.session_recorder_version(d), "v0.9.23")


class SpecDeVideo(unittest.TestCase):
    def _medir(self, *args, **kw):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "video.mp4"
            p.write_bytes(_mp4(*args, **kw))
            return sl.mp4_video_info(str(p))

    def test_lee_ancho_alto_y_fps(self):
        info = self._medir(1920, 1080, 60)
        self.assertEqual((info["ancho"], info["alto"]), (1920, 1080))
        self.assertAlmostEqual(info["fps"], 60, places=1)

    def test_duracion_por_defecto_del_trex(self):
        self.assertAlmostEqual(self._medir(1920, 1080, 60, por_muestra=False)["fps"], 60, places=1)

    def test_casos_de_la_spec(self):
        casos = {
            (1920, 1080, 60): [],
            (2560, 1440, 60): [],
            (2560, 1600, 60): [],          # 16:10 entra
            (1920, 1080, 59): [],
            (1280, 720, 60): ["resolution"],
            (2560, 1080, 60): ["aspect_ratio"],
            (1920, 1080, 30): ["fps"],
            (1280, 720, 30): ["resolution", "fps"],
        }
        for (ancho, alto, fps), esperado in casos.items():
            self.assertEqual(sl.fallas_spec_video(self._medir(ancho, alto, fps)), esperado,
                             (ancho, alto, fps))

    def test_lo_que_no_se_midio_no_rechaza(self):
        self.assertEqual(sl.fallas_spec_video(None), [])
        self.assertEqual(sl.fallas_spec_video({"ancho": None, "alto": None, "fps": None}), [])

    def test_archivo_invalido_devuelve_none(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "roto.mp4"
            p.write_bytes(b"no es un mp4")
            self.assertIsNone(sl.mp4_video_info(str(p)))

    def test_todo_fallo_tiene_texto(self):
        for falla in ("resolution", "aspect_ratio", "fps"):
            self.assertTrue(sl.mensaje_spec_video([falla]))


if __name__ == "__main__":
    unittest.main()
