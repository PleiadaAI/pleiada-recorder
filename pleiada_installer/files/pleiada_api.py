"""
Pleiada Recorder — cliente HTTP del backend (Lambda Function URL).

Login OTP + Open Calls + presigned URLs de upload a S3. Solo usa stdlib (urllib).
Lo comparten el login (pleiada_app.pyw) y el uploader (session_uploader.py).
"""
import json
import urllib.request
import urllib.error

ENDPOINT = "https://hdk2i43wuiw3272mtnjgwwsaby0bkood.lambda-url.sa-east-1.on.aws/"


class ApiError(Exception):
    """Error con mensaje legible para mostrar al usuario.

    `code` trae el código de máquina del backend cuando existe (p. ej.
    "no_enrolled", "game_not_eligible", "user_quota_exceeded") — permite a la
    UI distinguir el motivo sin parsear texto.
    """

    def __init__(self, message, code=""):
        super().__init__(message)
        self.code = code


def _call(action, payload, timeout=15):
    body = dict(payload)
    body["action"] = action
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        code, msg = "", ""
        try:
            err_body = json.loads(e.read())
            # Errores nuevos: {"error": <código>, "message": <humano>}.
            # Errores viejos: {"error": <humano>}. `message` manda si está.
            code = err_body.get("error", "")
            msg = err_body.get("message") or code
        except Exception:
            pass
        raise ApiError(msg or f"Error del servidor ({e.code})", code)
    except urllib.error.URLError:
        raise ApiError("Sin conexión. Revisá tu internet.")
    except Exception:
        raise ApiError("No se pudo contactar al servidor.")


def request_otp(email):
    """Pide que se envíe un código OTP al email. Lanza ApiError si falla."""
    _call("request_otp", {"email": email})


def verify_otp(email, code):
    """Verifica el código. Devuelve el token de sesión. Lanza ApiError si falla."""
    r = _call("verify_otp", {"email": email, "code": code})
    return r["token"]


def resolve_game(token, exe, window_title, timeout=30):
    """
    Identifica qué juego está capturando OBS, a partir del ejecutable y el
    título de ventana. TODO el criterio vive en el backend: acá no se clasifica
    nada, ni se decide qué entra en qué orden.

    Devuelve el dict del backend, con `estado`:
      resuelto        -> identificado; `calls` dice si hay orden o va libre
      candidatos      -> más de un título posible; `candidatos` para elegir
      admitido        -> título nuevo que entró solo porque una orden lo pedía
      no_identificado -> ÚNICO caso en que no se puede grabar
      no_disponible   -> rechazado por regla interna, sin explicación al usuario

    Timeout más largo que el resto: puede haber una consulta a IGDB en el medio,
    y cortar antes deja al usuario con el juego abierto y sin respuesta.
    """
    return _call("resolve_game", {
        "token": token, "exe": exe or "", "window_title": window_title or "",
    }, timeout=timeout)


def calls_for_game(token, game_name):
    """
    Órdenes abiertas del usuario que aceptan un juego ya identificado. La usan
    la pantalla de candidatos y la lista de grabaciones, para saber si una
    sesión libre ya se puede subir.
    """
    r = _call("calls_for_game", {"token": token, "game_name": game_name})
    return r.get("calls") or []


def my_calls(token):
    """Inscripciones del usuario (calls, horas usadas/restantes, subidas)."""
    r = _call("my_calls", {"token": token})
    return r.get("enrollments", [])


def get_upload_urls(token, session_name, filenames, dataset_hash=None,
                    call_id="", game_name="", duration_seconds=0):
    """
    Devuelve el dict del backend: {"urls": {...}} o {"already_uploaded": True}.
    El backend valida el gate del call (inscripción + juego elegible + cupos)
    antes de emitir URLs. Lanza ApiError si el token no vale o el gate rechaza.
    """
    return _call("get_upload_urls", {
        "token": token,
        "session_name": session_name,
        "filenames": filenames,
        "dataset_hash": dataset_hash or "",
        "call_id": call_id,
        "game_name": game_name,
        "duration_seconds": duration_seconds,
    })


def start_multipart(token, call_id, session_name, filename, filesize,
                    dataset_hash="", game_name="", duration_seconds=0, batch=0):
    """
    Inicia la subida multipart de UN archivo grande (S3 rechaza PUTs > 5 GiB).
    El backend corre el mismo gate del call y devuelve
    {s3_upload_id, part_size, n_parts, part_urls: {"1": url, ...}} — o
    {already_uploaded: True}. Lanza ApiError si el gate rechaza.

    `batch` > 0 pide el protocolo por lotes: partes adaptativas al tamaño del
    archivo y solo las primeras `batch` URLs; las que siguen se piden con
    more_part_urls recién cuando se van a usar, así el vencimiento de la URL
    no corre durante horas. Sin `batch`, el backend responde como antes.
    """
    return _call("start_multipart", {
        "token": token, "call_id": call_id, "session_name": session_name,
        "filename": filename, "filesize": int(filesize),
        "dataset_hash": dataset_hash or "", "game_name": game_name,
        "duration_seconds": duration_seconds, "batch": int(batch),
    })


def more_part_urls(token, call_id, session_name, filename, s3_upload_id,
                   from_part, count):
    """Siguiente lote de URLs presignadas de un multipart ya iniciado."""
    r = _call("more_part_urls", {
        "token": token, "call_id": call_id, "session_name": session_name,
        "filename": filename, "s3_upload_id": s3_upload_id,
        "from_part": int(from_part), "count": int(count),
    })
    return r.get("part_urls") or {}


def complete_multipart(token, call_id, session_name, filename, s3_upload_id, parts):
    """Ensambla las partes en el objeto final. parts = [{part_number, etag}]."""
    return _call("complete_multipart", {
        "token": token, "call_id": call_id, "session_name": session_name,
        "filename": filename, "s3_upload_id": s3_upload_id, "parts": parts,
    })


def abort_multipart(token, call_id, session_name, filename, s3_upload_id):
    """Cancela un multipart (libera las partes en S3). Best-effort e idempotente."""
    return _call("abort_multipart", {
        "token": token, "call_id": call_id, "session_name": session_name,
        "filename": filename, "s3_upload_id": s3_upload_id,
    })


def finalize_upload(token, dataset_hash, session_name, call_id="", game_name="",
                    duration_seconds=0, session_id="", files=None, bytes_total=0):
    """
    Registra la subida en el backend (log legal + horas del call).
    Idempotente por dataset_hash.
    """
    _call("finalize_upload", {
        "token": token,
        "dataset_hash": dataset_hash,
        "session_name": session_name,
        "call_id": call_id,
        "game_name": game_name,
        "duration_seconds": duration_seconds,
        "session_id": session_id,
        "files": files or [],
        "bytes_total": bytes_total,
    })
