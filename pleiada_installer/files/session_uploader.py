"""
Pleiada Recorder — S3 Session Uploader

Sube los archivos de una sesión a S3 usando presigned URLs que entrega el
backend (ver pleiada_api). El backend deriva la carpeta del usuario a partir
del token, así que un usuario solo puede subir a su propia carpeta.
"""
import http.client
import json
import os
import time
import hashlib
import threading
import urllib.request
from collections import deque
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from pathlib import Path

import pleiada_api

_EXCLUDE = {"pleiada_stop.txt", ".pleiada_upload.json"}

# Reintentos por archivo (v0.8.8): redes hogareñas (router/AV/ISP) a veces matan
# conexiones TLS largas a mitad del PUT — el síntoma clásico es
# "<urlopen error EOF occurred in violation of protocol>". Un PUT interrumpido
# no deja nada en S3 (es atómico), así que reintentar con conexión nueva es seguro.
UPLOAD_RETRIES  = 3        # intentos por archivo (o por PARTE, en multipart)
RETRY_BACKOFF_S = (2, 5)   # espera antes del 2º y 3º intento

# Multipart (v0.8.8): S3 rechaza PUTs simples > 5 GiB (EntityTooLarge) y los MP4
# de sesiones largas lo superan (30 min ≈ 6,6 GB al bitrate actual). Los archivos
# grandes van en partes con URL presignada cada una y reintento POR PARTE — un
# corte de red a los 5 GB ya no tira toda la subida, repite una sola parte.
# v0.8.11: umbral 200 MB -> 64 MB. Todo lo que pase por multipart sube en
# paralelo, así que conviene que caiga acá todo lo que tarde algo; además saca
# a los archivos medianos del PUT simple, cuya URL vence a los 15 min.
MULTIPART_THRESHOLD = 64 * 1024 * 1024

# Subida en PARALELO (v0.8.11). OJO: el paralelismo NO es el fix principal del
# problema de velocidad — el fix es _UPLOAD_BLOCKSIZE (ver más abajo). Medido
# contra producción el 05/08/2026 con el blocksize ya arreglado:
#   1 stream 16,0 MB/s · 2 streams 24,4 · 4 streams 22,0 · 8 streams 18,8
# O sea que a partir de 2-4 streams la línea ya está llena y sumar más solo
# agrega contención (con 8 rinde MENOS que con 2). El paralelismo se queda igual
# porque sí ayuda donde un stream solo no llega —conexiones con más latencia o
# pérdida, que son justo las de los miembros que se quejaron— y porque una parte
# que se cuelga deja de frenar a todas las demás. 4 es el default: da margen sin
# comerle la conexión al miembro mientras juega.
UPLOAD_CONCURRENCY     = 4     # partes en vuelo a la vez
UPLOAD_CONCURRENCY_MAX = 16
URL_BATCH              = 100   # URLs presignadas por pedido al backend

_SETTINGS_FILE = (Path(os.environ.get("APPDATA", "")) / "Pleiada" / "settings.json")


def _concurrency() -> int:
    """
    Partes en paralelo. Se puede pisar con `upload_concurrency` en settings.json
    (sin UI: es una válvula para soporte, no una opción de producto) — por
    ejemplo bajarla a 1 si a alguien el router no le banca 8 conexiones.
    """
    try:
        v = int(json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
                .get("upload_concurrency", UPLOAD_CONCURRENCY))
        return max(1, min(UPLOAD_CONCURRENCY_MAX, v))
    except Exception:
        return UPLOAD_CONCURRENCY


_DIAG_LOG = Path.home() / "Documents" / "Pleiada Logs" / "upload.log"

def _diag(text):
    """Log de diagnóstico de subidas (misma carpeta visible que el crash log)."""
    try:
        _DIAG_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(_DIAG_LOG, "a", encoding="utf-8") as f:
            f.write(f"{ts}  {text}\n")
    except Exception:
        pass


# ESTA es la causa raíz de las subidas lentas (05/08/2026), no el paralelismo.
#
# http.client manda el body en bloques de `blocksize`, 8192 bytes por default:
# le pasa 8 KB al kernel, espera, le pasa otros 8 KB. Con eso el socket nunca
# tiene datos suficientes en vuelo y la conexión queda limitada por la
# aplicación, no por la red: el throughput se vuelve SO_SNDBUF / RTT.
# Medido en la máquina de Martín: SO_SNDBUF = 64 KB, RTT a S3 São Paulo = 44 ms
# -> 64 KB / 0,044 s = 1,42 MB/s de techo. Medido real con 8 KiB: 1,33 MB/s.
# La fórmula explica por qué el número era parejo entre miembros con conexiones
# muy distintas — no depende del ancho de banda, solo del RTT:
#     RTT  44 ms -> 1,42 MB/s   (Martín)
#     RTT 160 ms -> 0,39 MB/s   (el 0,4 MB/s que reportaron los miembros)
# Mismo archivo, misma ruta, alternando A/B/A/B: 8 KiB da 1,33 MB/s y 256 KiB da
# 20,3 MB/s. 1 MiB no mejora nada sobre 256 KiB (ambos ya llenan la línea).
#
# CUIDADO: NO setear SO_SNDBUF a mano para esto. En Windows, fijarlo explícito
# APAGA el autotuning del buffer de envío, que es justo lo que hace que esto
# funcione: con bloques de 256 KiB el kernel agranda el buffer solo.
#
# Se pasa por http_conn_args en vez de parchear http.client, que es global al
# proceso (y el Recorder hace otras llamadas HTTP que no tienen por qué cambiar).
_UPLOAD_BLOCKSIZE = 256 * 1024


class _BigBlockHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(http.client.HTTPSConnection, req,
                            context=self._context,
                            blocksize=_UPLOAD_BLOCKSIZE)


try:
    _OPENER = urllib.request.build_opener(_BigBlockHTTPSHandler())
except Exception:      # ante cualquier cambio de stdlib, seguir como antes
    _OPENER = None


def _open(req, timeout=600):
    """urlopen para los PUT a S3, con el blocksize grande si se pudo armar."""
    if _OPENER is not None:
        return _OPENER.open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout)


def session_info(session_dir: Path) -> dict:
    """Metadatos de la sesión para mostrar en el dialog de confirmación."""
    files = _list_files(session_dir)
    total = sum(f.stat().st_size for f in files)
    return {
        "files": files,
        "count": len(files),
        "size_label": _fmt_size(total),
    }


def session_meta(session_dir: Path) -> dict:
    """
    Juego, duración y session_id desde session_metadata.json.
    Los usa el gate de Open Calls (matching cliente + declaración al backend).
    """
    out = {"game_title": "", "duration_seconds": 0, "session_id": ""}
    try:
        meta = json.loads((Path(session_dir) / "session_metadata.json")
                          .read_text(encoding="utf-8"))
        out["game_title"] = (meta.get("game", {}) or {}).get("title") or ""
        out["session_id"] = meta.get("session_id") or ""
        # La duración vive bajo "timing" en el metadata (schema 1.1), NO bajo
        # "session". Leerla mal daba duration_seconds=0 -> el gate rechazaba con
        # 400 "falta duration_seconds" -> "No se pudo subir la sesión". (bug QA)
        timing = meta.get("timing", {}) or {}
        dur_ms = timing.get("duration_ms")
        if not dur_ms:   # fallback: calcular de start/end si faltara
            s, e = timing.get("start_unix_ms"), timing.get("end_unix_ms")
            if s and e and e > s:
                dur_ms = e - s
        if dur_ms:
            out["duration_seconds"] = max(1, int(round(float(dur_ms) / 1000.0)))
    except Exception:
        pass
    return out


# Códigos del gate del backend → el upload fue RECHAZADO por reglas del call
# (no es un error técnico: no tiene sentido reintentar sin cambiar algo).
_GATE_CODES = {"no_enrolled", "call_closed", "game_not_in_catalog",
               "game_not_eligible", "user_quota_exceeded", "call_quota_exceeded"}


class UploadCancelled(Exception):
    """El usuario canceló la subida: abortar YA, sin finalize."""


class _AlreadyFinalized(Exception):
    """El backend informó que este dataset ya estaba subido."""


def upload_session(session_dir: Path, token: str, call_id: str = "",
                   on_progress=None, on_done=None, cancel_event=None):
    """
    Sube todos los archivos de la sesión a S3, asociados a un Open Call.
    on_progress(sent_bytes, total_bytes, filename, speed_bps, eta_seconds)
        progreso global por bytes con velocidad y ETA, desde el thread worker.
    on_done("ok" | "already" | "error" | "auth" | "gate" | "cancelled", message)
        "auth" = token vencido → re-login. "gate" = el backend rechazó por
        reglas del Open Call (message trae el motivo para mostrar).
    cancel_event (threading.Event): al setearse, el worker aborta el PUT en
        curso y NUNCA llama a finalize (bug QA issue 7: el botón Cancelar solo
        silenciaba la UI, el thread seguía y registraba la subida igual).
        Un PUT abortado a mitad no deja objeto en S3 (el PUT es atómico).
    """
    def _check_cancel():
        if cancel_event is not None and cancel_event.is_set():
            raise UploadCancelled()

    try:
        files = _list_files(session_dir)
        if not files:
            if on_done:
                on_done("error", "No hay archivos para subir.")
            return

        meta = session_meta(session_dir)

        # 1. Pedir presigned URLs al backend (acotadas a la carpeta del token).
        #    dataset_hash identifica el dataset → el backend rechaza la re-subida.
        #    El backend valida acá el gate del call (fail-closed).
        dataset_hash = _dataset_hash(session_dir)
        resp = pleiada_api.get_upload_urls(
            token, session_dir.name, [f.name for f in files], dataset_hash,
            call_id=call_id, game_name=meta["game_title"],
            duration_seconds=meta["duration_seconds"])
        if resp.get("already_uploaded"):
            if on_done:
                on_done("already", "")
            return
        urls = resp.get("urls", {})

        total = sum(f.stat().st_size for f in files)
        samples = deque()   # (tiempo, bytes globales) para velocidad/ETA

        def _report(global_sent, fn):
            if not on_progress:
                return
            now = time.monotonic()
            samples.append((now, global_sent))
            while len(samples) > 1 and now - samples[0][0] > 3.0:
                samples.popleft()
            speed = 0.0
            if len(samples) >= 2:
                dt = samples[-1][0] - samples[0][0]
                db = samples[-1][1] - samples[0][1]
                # db puede dar <= 0: con partes en paralelo, un intento fallido
                # descuenta lo que no llegó a S3. No es velocidad negativa.
                if dt > 0 and db > 0:
                    speed = db / dt
            eta = ((total - global_sent) / speed) if speed > 0 else None
            on_progress(global_sent, total, fn, speed, eta)

        # 2. PUT cada archivo directo a S3, reportando bytes globales.
        #    Archivos > MULTIPART_THRESHOLD van por multipart (S3 no acepta
        #    PUTs simples > 5 GiB); el resto por PUT simple con reintentos.
        sent_before = 0
        for f in files:
            _check_cancel()
            fsize = f.stat().st_size
            if fsize > MULTIPART_THRESHOLD:
                def _mp_report(file_sent, _sb=sent_before, _fn=f.name):
                    _check_cancel()
                    _report(_sb + file_sent, _fn)
                _upload_multipart_file(token, call_id, session_dir, f,
                                       dataset_hash, meta, _mp_report,
                                       _check_cancel)
                sent_before += fsize
                continue
            url = urls.get(f.name)
            if not url:
                raise RuntimeError(f"Sin URL para {f.name}")

            def _cb(file_sent, _sb=sent_before, _fn=f.name):
                _check_cancel()   # corta el PUT en curso (aborta el body)
                _report(_sb + file_sent, _fn)

            # v0.8.8: hasta UPLOAD_RETRIES intentos por archivo, con backoff.
            # La cancelación NO se reintenta; el resto de los errores sí.
            size_mb = f.stat().st_size / (1024 * 1024)
            for intento in range(1, UPLOAD_RETRIES + 1):
                t0 = time.monotonic()
                try:
                    _put_file(url, f, _cb)
                    if intento > 1:
                        _diag(f"OK  {f.name} ({size_mb:.1f} MB) en intento {intento}")
                    break
                except UploadCancelled:
                    raise
                except Exception as e:
                    elapsed = time.monotonic() - t0
                    _diag(f"FALLO  {f.name} ({size_mb:.1f} MB) intento {intento}/"
                          f"{UPLOAD_RETRIES} tras {elapsed:.0f}s: {e!r}")
                    if intento >= UPLOAD_RETRIES:
                        raise
                    time.sleep(RETRY_BACKOFF_S[min(intento - 1, len(RETRY_BACKOFF_S) - 1)])
                    _check_cancel()
            sent_before += f.stat().st_size

        if on_progress:
            on_progress(total, total, files[-1].name, 0.0, 0)   # asegura 100%

        # Registrar la subida en el backend. Ya NO es best-effort: este registro
        # es el que computa las horas del call (compromiso de pago) — si falla,
        # se reporta error y el reintento vuelve a intentar (es idempotente).
        _check_cancel()   # último chequeo: cancelado = NO se registra nada
        if dataset_hash:
            total_bytes = sum(f.stat().st_size for f in files)
            pleiada_api.finalize_upload(
                token, dataset_hash, session_dir.name,
                call_id=call_id, game_name=meta["game_title"],
                duration_seconds=meta["duration_seconds"],
                session_id=meta["session_id"],
                files=[f.name for f in files], bytes_total=total_bytes)

        if on_done:
            on_done("ok", "")

    except UploadCancelled:
        if on_done:
            on_done("cancelled", "")
    except _AlreadyFinalized:
        if on_done:
            on_done("already", "")
    except pleiada_api.ApiError as e:
        if cancel_event is not None and cancel_event.is_set():
            if on_done:
                on_done("cancelled", "")
            return
        msg = str(e)
        if getattr(e, "code", "") in _GATE_CODES:
            status = "gate"
        elif "sesión" in msg.lower() or "token" in msg.lower():
            status = "auth"
        else:
            status = "error"
        if on_done:
            on_done(status, msg)
    except Exception as e:
        # Un PUT abortado por la cancelación puede salir como error de red:
        # si la cancelación está pedida, es una cancelación, no un error.
        if cancel_event is not None and cancel_event.is_set():
            if on_done:
                on_done("cancelled", "")
            return
        if on_done:
            on_done("error", str(e))


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _dataset_hash(session_dir: Path):
    """
    Hash único del dataset, derivado de integrity.files del metadata (SHA-256 por
    archivo que ya calcula la sesión). Identifica el contenido: la misma data, aunque
    se copie o renombre la carpeta, da el mismo hash. None si no hay metadata.
    """
    try:
        meta = json.loads((Path(session_dir) / "session_metadata.json")
                          .read_text(encoding="utf-8"))
        files = meta.get("integrity", {}).get("files", {})
        if not files:
            return None
        blob = "\n".join(f"{name}:{h}" for name, h in sorted(files.items()))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
    except Exception:
        return None


def _list_files(session_dir: Path) -> list:
    return sorted(
        [f for f in session_dir.iterdir() if f.is_file() and f.name not in _EXCLUDE],
        key=lambda f: f.stat().st_size,
    )


class _ProgressReader:
    """Envuelve un archivo y reporta bytes leídos (≈ subidos) cada ~1 MB."""
    _STEP = 1024 * 1024

    def __init__(self, path: Path, on_bytes):
        self._f = open(path, "rb")
        self._on = on_bytes
        self._sent = 0
        self._last = 0

    def read(self, size=-1):
        chunk = self._f.read(size)
        if chunk:
            self._sent += len(chunk)
            if self._on and (self._sent - self._last) >= self._STEP:
                self._last = self._sent
                self._on(self._sent)
        return chunk

    def close(self):
        try:
            self._f.close()
        except Exception:
            pass


def _upload_multipart_file(token, call_id, session_dir, f, dataset_hash, meta,
                           report, check_cancel):
    """
    Sube UN archivo grande en partes (multipart de S3) con reintento por parte.
    report(bytes_del_archivo) reporta progreso; check_cancel() corta el ciclo.
    Si falla en serio o se cancela, aborta el multipart (libera las partes).
    """
    fsize = f.stat().st_size
    conc  = _concurrency()
    resp = pleiada_api.start_multipart(
        token, call_id, session_dir.name, f.name, fsize,
        dataset_hash=dataset_hash or "", game_name=meta["game_title"],
        duration_seconds=meta["duration_seconds"], batch=URL_BATCH)
    if resp.get("already_uploaded"):
        raise _AlreadyFinalized()
    part_size    = int(resp["part_size"])
    s3_upload_id = resp["s3_upload_id"]
    n_total      = int(resp.get("n_parts") or
                       ((fsize + part_size - 1) // part_size))
    urls         = dict(resp.get("part_urls") or {})
    urls_lock    = threading.Lock()

    def _url(n):
        """URL de la parte n, pidiendo el lote siguiente si hace falta."""
        with urls_lock:
            u = urls.get(str(n))
            if not u:
                urls.update(pleiada_api.more_part_urls(
                    token, call_id, session_dir.name, f.name, s3_upload_id,
                    n, min(URL_BATCH, n_total - n + 1)))
                u = urls.get(str(n))
        if not u:
            raise RuntimeError(f"Sin URL para la parte {n} de {f.name}")
        return u

    # Progreso global del archivo: las partes terminan desordenadas, así que se
    # acumulan deltas bajo lock en vez de posiciones absolutas.
    sent_lock, sent_total, ultimo_rep = threading.Lock(), [0], [0.0]

    def _bump(delta, check=True):
        if not check:
            # Corrección de un intento fallido: ajusta el contador y listo. No
            # reporta (el próximo delta bueno ya lleva el número corregido) ni
            # chequea cancelación, que acá vendría a pisar el error original.
            with sent_lock:
                sent_total[0] += delta
            return
        check_cancel()          # corta el PUT en curso desde adentro del body
        now = time.monotonic()
        with sent_lock:
            sent_total[0] += delta
            acumulado = sent_total[0]
            # Con 8 partes reportando cada 256 KiB, la UI recibiría >100
            # actualizaciones por segundo. El 100% final lo asegura upload_session.
            if now - ultimo_rep[0] < 0.2:
                return
            ultimo_rep[0] = now
        report(acumulado)

    etags, etags_lock, reintentos = {}, threading.Lock(), [0]

    def _subir_parte(n):
        offset = (n - 1) * part_size
        length = min(part_size, fsize - offset)
        url    = _url(n)
        for intento in range(1, UPLOAD_RETRIES + 1):
            contados = [0]

            def _on(delta, _c=contados):
                _c[0] += delta
                _bump(delta)

            t0 = time.monotonic()
            try:
                etag = _put_range(url, f, offset, length, _on)
                with etags_lock:
                    etags[n] = etag
                if intento > 1:
                    _diag(f"OK  parte {n}/{n_total} de {f.name} en intento {intento}")
                return
            except UploadCancelled:
                raise
            except Exception as e:
                # Lo transferido en el intento fallido no llegó a S3 (el PUT de
                # una parte es atómico): se descuenta para que la barra no mienta.
                _bump(-contados[0], check=False)
                with etags_lock:
                    reintentos[0] += 1
                _diag(f"FALLO  parte {n}/{n_total} de {f.name} "
                      f"({length/(1024*1024):.0f} MB) intento {intento}/"
                      f"{UPLOAD_RETRIES} tras {time.monotonic()-t0:.0f}s: {e!r}")
                if intento >= UPLOAD_RETRIES:
                    raise
                time.sleep(RETRY_BACKOFF_S[min(intento - 1, len(RETRY_BACKOFF_S) - 1)])
                check_cancel()

    t_ini = time.monotonic()
    try:
        check_cancel()
        with ThreadPoolExecutor(max_workers=conc) as pool:
            futuros = [pool.submit(_subir_parte, n) for n in range(1, n_total + 1)]
            listos, pendientes = wait(futuros, return_when=FIRST_EXCEPTION)
            for fu in pendientes:
                fu.cancel()     # las que todavía no arrancaron no arrancan
            for fu in listos:
                fu.result()     # re-lanza el primer error real, si hubo

        # Reporte final sin throttle: el último tick parcial queda comido por la
        # ventana de 200 ms y el archivo se veía terminando en 99%.
        report(fsize)

        pleiada_api.complete_multipart(
            token, call_id, session_dir.name, f.name, s3_upload_id,
            [{"part_number": n, "etag": etags[n]} for n in sorted(etags)])

        seg = max(0.001, time.monotonic() - t_ini)
        _diag(f"OK  {f.name}: {fsize/(1024*1024):.0f} MB en {seg:.0f}s = "
              f"{fsize/(1024*1024)/seg:.2f} MB/s ({n_total} partes de "
              f"{part_size/(1024*1024):.0f} MB, {conc} en paralelo, "
              f"{reintentos[0]} reintentos)")
    except BaseException:
        # Cancelación o fallo definitivo: liberar las partes ya subidas (best-effort).
        try:
            pleiada_api.abort_multipart(token, call_id, session_dir.name,
                                        f.name, s3_upload_id)
        except Exception:
            pass
        raise


class _FileRangeReader:
    """
    Lee [offset, offset+length) de un archivo y reporta DELTAS de bytes.

    Lee del disco a medida que el socket consume, así que una parte en vuelo
    ocupa _STEP de RAM y no `part_size`: con 8 partes en paralelo eso es la
    diferencia entre ~2 MB y ~500 MB (la versión vieja hacía fh.read(part_size)
    entero en memoria).
    """
    _STEP = 256 * 1024

    def __init__(self, path: Path, offset: int, length: int, on_delta):
        self._f = open(path, "rb")
        self._f.seek(offset)
        self._left = length
        self._on   = on_delta
        self._acc  = 0

    def read(self, size=-1):
        if size is None or size < 0:
            size = self._left
        size = min(size, self._left)
        if size <= 0:
            self._flush()
            return b""
        chunk = self._f.read(size)
        self._left -= len(chunk)
        self._acc  += len(chunk)
        if self._acc >= self._STEP:
            self._flush()
        return chunk

    def _flush(self):
        if self._acc and self._on:
            n, self._acc = self._acc, 0
            self._on(n)

    def close(self):
        try:
            self._f.close()
        except Exception:
            pass


def _put_range(url: str, path: Path, offset: int, length: int, on_delta=None) -> str:
    """PUT de una parte multipart leída del archivo. Devuelve el ETag."""
    reader = _FileRangeReader(path, offset, length, on_delta)
    try:
        req = urllib.request.Request(url, data=reader, method="PUT")
        req.add_header("Content-Length", str(length))
        with _open(req) as r:
            return r.headers.get("ETag", "")
    finally:
        reader.close()


def _put_file(url: str, path: Path, on_bytes=None):
    reader = _ProgressReader(path, on_bytes)
    try:
        req = urllib.request.Request(url, data=reader, method="PUT")
        req.add_header("Content-Length", str(path.stat().st_size))
        with _open(req):
            pass
    finally:
        reader.close()


def _fmt_size(n: int) -> str:
    if n < 1024 ** 2:
        return f"{n / 1024:.0f} KB"
    return f"{n / 1024 ** 2:.1f} MB"
