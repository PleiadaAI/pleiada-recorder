"""
Pleiada Recorder — S3 Session Uploader

Sube los archivos de una sesión a S3 usando presigned URLs que entrega el
backend (ver pleiada_api). El backend deriva la carpeta del usuario a partir
del token, así que un usuario solo puede subir a su propia carpeta.
"""
import json
import time
import hashlib
import urllib.request
from collections import deque
from pathlib import Path

import pleiada_api

_EXCLUDE = {"pleiada_stop.txt", ".pleiada_upload.json"}

# Reintentos por archivo (v0.8.8): redes hogareñas (router/AV/ISP) a veces matan
# conexiones TLS largas a mitad del PUT — el síntoma clásico es
# "<urlopen error EOF occurred in violation of protocol>". Un PUT interrumpido
# no deja nada en S3 (es atómico), así que reintentar con conexión nueva es seguro.
UPLOAD_RETRIES  = 3        # intentos por archivo
RETRY_BACKOFF_S = (2, 5)   # espera antes del 2º y 3º intento

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
                if dt > 0:
                    speed = db / dt
            eta = ((total - global_sent) / speed) if speed > 0 else None
            on_progress(global_sent, total, fn, speed, eta)

        # 2. PUT cada archivo directo a S3, reportando bytes globales
        sent_before = 0
        for f in files:
            _check_cancel()
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


def _put_file(url: str, path: Path, on_bytes=None):
    reader = _ProgressReader(path, on_bytes)
    try:
        req = urllib.request.Request(url, data=reader, method="PUT")
        req.add_header("Content-Length", str(path.stat().st_size))
        with urllib.request.urlopen(req, timeout=600):
            pass
    finally:
        reader.close()


def _fmt_size(n: int) -> str:
    if n < 1024 ** 2:
        return f"{n / 1024:.0f} KB"
    return f"{n / 1024 ** 2:.1f} MB"
