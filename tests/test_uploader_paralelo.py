"""
Tests del uploader en paralelo (session_uploader v0.8.11) contra un sink HTTP
local. Lo que importa de verdad: que los bytes lleguen COMPLETOS y en el offset
correcto — con lectura por rangos y 8 threads, un off-by-one corrompe el MP4 en
silencio y recién se nota cuando el cliente abre el dataset.
"""
import hashlib
import importlib.util
import json
import os
import sys
import threading
import time
import types
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FILES = Path(r"C:\Users\mspin\Documents\pleiada-recorder\pleiada_installer\files")

# ── Stub de pleiada_api (session_uploader lo importa a nivel módulo) ──────────
api = types.ModuleType("pleiada_api")


class ApiError(Exception):
    def __init__(self, message, code=""):
        super().__init__(message)
        self.code = code


api.ApiError = ApiError
sys.modules["pleiada_api"] = api

spec = importlib.util.spec_from_file_location("su", FILES / "session_uploader.py")
su = importlib.util.module_from_spec(spec)
spec.loader.exec_module(su)


# ── Sink: guarda el cuerpo de cada parte ──────────────────────────────────────
RECIBIDO = {}
FALLAR_UNA_VEZ = set()
LENTO = []          # si tiene algo, el sink demora cada parte (para cancelar)
_lock = threading.Lock()


class Sink(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_PUT(self):
        n = int(self.path.strip("/").split("part")[-1])
        largo = int(self.headers.get("Content-Length", 0))
        cuerpo = b""
        while len(cuerpo) < largo:
            c = self.rfile.read(largo - len(cuerpo))
            if not c:
                break
            cuerpo += c
        with _lock:
            reventar = n in FALLAR_UNA_VEZ
            if reventar:
                FALLAR_UNA_VEZ.discard(n)
        if reventar:
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if LENTO:
            time.sleep(0.4)
        with _lock:
            RECIBIDO[n] = cuerpo
        self.send_response(200)
        self.send_header("ETag", f'"etag-{n}"')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *a):
        pass


class TestUploadParalelo(unittest.TestCase):
    PART = 1024 * 1024          # 1 MB por parte
    NPARTS = 13                 # impar y con última parte corta a propósito

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Sink)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

        cls.dir = Path(os.environ["TEMP"]) / "ab_uploader_test"
        cls.dir.mkdir(exist_ok=True)
        cls.f = cls.dir / "video.mp4"
        # Tamaño que NO es múltiplo del part_size: la última parte queda corta.
        cls.datos = os.urandom(cls.PART * (cls.NPARTS - 1) + 12345)
        cls.f.write_bytes(cls.datos)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        RECIBIDO.clear()
        FALLAR_UNA_VEZ.clear()
        LENTO.clear()
        self.completado = []
        self.abortado = []
        self.lotes = []
        n_total = (len(self.datos) + self.PART - 1) // self.PART

        def _url(n):
            return f"http://127.0.0.1:{self.port}/part{n}"

        def start_multipart(token, call_id, session_name, filename, filesize,
                            dataset_hash="", game_name="", duration_seconds=0,
                            batch=0):
            # Devuelve solo el primer lote, como el backend nuevo.
            primeras = min(batch or n_total, 5, n_total)
            return {"s3_upload_id": "MPU-1", "part_size": self.PART,
                    "n_parts": n_total,
                    "part_urls": {str(n): _url(n) for n in range(1, primeras + 1)}}

        def more_part_urls(token, call_id, session_name, filename,
                           s3_upload_id, from_part, count):
            self.lotes.append((from_part, count))
            return {str(n): _url(n) for n in range(from_part, from_part + count)}

        api.start_multipart = start_multipart
        api.more_part_urls = more_part_urls
        api.complete_multipart = lambda *a: self.completado.append(a[-1])
        api.abort_multipart = lambda *a: self.abortado.append(a)

    def _correr(self, cancel_en=None, concurrencia=8):
        su._concurrency = lambda: concurrencia
        avances = []
        cancelado = threading.Event()

        def report(sent):
            avances.append(sent)
            if cancel_en is not None and sent >= cancel_en:
                cancelado.set()

        def check_cancel():
            if cancelado.is_set():
                raise su.UploadCancelled()

        su._upload_multipart_file(
            "T", "GA-1", self.dir, self.f, "HASH",
            {"game_title": "DOOM", "duration_seconds": 600},
            report, check_cancel)
        return avances

    # ── lo que más importa: los bytes ─────────────────────────────────────
    def test_los_bytes_llegan_completos_y_en_orden(self):
        self._correr()
        rearmado = b"".join(RECIBIDO[n] for n in sorted(RECIBIDO))
        self.assertEqual(len(rearmado), len(self.datos), "faltan o sobran bytes")
        self.assertEqual(hashlib.sha256(rearmado).hexdigest(),
                         hashlib.sha256(self.datos).hexdigest(),
                         "el archivo rearmado no es el original")

    def test_ultima_parte_corta(self):
        self._correr()
        ultima = max(RECIBIDO)
        self.assertEqual(len(RECIBIDO[ultima]), 12345)

    def test_complete_recibe_las_partes_ordenadas(self):
        self._correr()
        partes = self.completado[0]
        self.assertEqual([p["part_number"] for p in partes],
                         sorted(p["part_number"] for p in partes))
        self.assertEqual(len(partes), self.NPARTS)
        self.assertEqual(partes[0]["etag"], '"etag-1"')

    # ── lotes de URLs ─────────────────────────────────────────────────────
    def test_pide_mas_urls_cuando_se_acaban(self):
        self._correr()
        self.assertTrue(self.lotes, "nunca pidió el segundo lote")
        self.assertGreaterEqual(min(f for f, _ in self.lotes), 6,
                                "el primer lote traía hasta la parte 5")

    # ── progreso ──────────────────────────────────────────────────────────
    def test_el_progreso_no_pasa_del_total(self):
        avances = self._correr()
        self.assertLessEqual(max(avances), len(self.datos),
                             "la barra reportó más bytes de los que tiene el archivo")

    def test_reintento_no_infla_el_progreso(self):
        FALLAR_UNA_VEZ.update({3, 7})
        avances = self._correr()
        self.assertLessEqual(max(avances), len(self.datos))
        rearmado = b"".join(RECIBIDO[n] for n in sorted(RECIBIDO))
        self.assertEqual(hashlib.sha256(rearmado).hexdigest(),
                         hashlib.sha256(self.datos).hexdigest())
        self.assertTrue(self.completado, "tras reintentar debía completar igual")

    # ── cancelación ───────────────────────────────────────────────────────
    def test_cancelar_aborta_y_no_completa(self):
        # El sink demora cada parte: sin eso, sobre loopback la subida entera
        # termina dentro de la ventana de 200 ms del throttle de progreso y no
        # llega a haber nada que cancelar (artefacto del test, no del producto).
        LENTO.append(True)
        with self.assertRaises(su.UploadCancelled):
            self._correr(cancel_en=1)   # cancela en el primer reporte
        self.assertTrue(self.abortado, "no abortó el multipart en S3")
        self.assertFalse(self.completado, "completó una subida cancelada")
        self.assertLess(len(RECIBIDO), self.NPARTS,
                        "siguió subiendo partes después de cancelar")

    # ── secuencial sigue andando ──────────────────────────────────────────
    def test_concurrencia_1_sigue_funcionando(self):
        self._correr(concurrencia=1)
        rearmado = b"".join(RECIBIDO[n] for n in sorted(RECIBIDO))
        self.assertEqual(hashlib.sha256(rearmado).hexdigest(),
                         hashlib.sha256(self.datos).hexdigest())


if __name__ == "__main__":
    unittest.main(verbosity=2)
