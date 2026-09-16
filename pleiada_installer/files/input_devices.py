"""
input_devices.py — metadata y calibración de los dispositivos de entrada (v0.9.18)

Cierra el gate T0 `input.device_metadata` de AI Ranch ("Input device mapping and
calibration"): sin esto el cliente no puede reconstruir acciones desde los counts
del mouse. Lo que se lee del sistema sin preguntarle nada al usuario:

  - SPI_GETMOUSESPEED (1..20, 10 = default) y SPI_GETMOUSE ("Mejorar la
    precisión del puntero" = aceleración del SO);
  - layout de teclado activo (KLID + locale, p. ej. 0000080A / es-AR);
  - dispositivos Raw Input con VID/PID (USB y Bluetooth) y fabricante por tabla;
  - tasa de sondeo del mouse estimada desde mouse_delta_log.csv (moda del
    intervalo entre MOVE consecutivos).

Lo que NO se puede leer del SO: el DPI del mouse. Se toma de Ajustes si el usuario
lo declaró (`mouse_dpi`), y se marca como declarado, no medido. La sensibilidad
del juego sale del config del título por el camino de key-mapping, no de acá.

Todo es best-effort y NUNCA lanza: es metadata, no puede tumbar una sesión.
"""
import csv
import ctypes
import ctypes.wintypes as W
import re
from collections import Counter
from pathlib import Path

# Vendors más comunes en la comunidad. Lo que no esté acá queda como VID en hex.
VENDORS = {
    "046D": "Logitech", "1532": "Razer", "1038": "SteelSeries", "045E": "Microsoft",
    "1B1C": "Corsair", "3434": "Keychron", "0C45": "Microdia/generic", "1EA7": "SHARKOON/generic",
    "24AE": "RAPOO", "04D9": "Holtek/generic", "2516": "Cooler Master", "0B05": "ASUS",
    "1044": "Gigabyte", "195D": "Itron/generic", "093A": "Pixart/generic", "3938": "MOSART/generic",
    "0951": "HyperX", "03F0": "HP", "413C": "Dell", "17EF": "Lenovo", "258A": "SINO WEALTH/generic",
    "320F": "Compx/generic", "30FA": "generic", "25A7": "Areson/generic", "2EA8": "generic",
    "3554": "Compx/generic", "1D57": "Xenta/generic", "0A5C": "Broadcom", "062A": "MosArt/generic",
}

_VIDPID = re.compile(r"VID[&_](?:[0-9A-Fa-f]{2})?([0-9A-Fa-f]{4}).*?PID[&_]([0-9A-Fa-f]{4})")


def os_mouse_settings():
    out = {"os_sensitivity": None, "os_acceleration": "unknown", "os_thresholds": None}
    try:
        user32 = ctypes.windll.user32
        speed = ctypes.c_int(0)
        if user32.SystemParametersInfoW(0x0070, 0, ctypes.byref(speed), 0):     # SPI_GETMOUSESPEED
            out["os_sensitivity"] = speed.value
        arr = (ctypes.c_int * 3)()
        if user32.SystemParametersInfoW(0x0003, 0, arr, 0):                     # SPI_GETMOUSE
            out["os_acceleration"] = "enabled" if arr[2] else "disabled"
            out["os_thresholds"] = [arr[0], arr[1]]
    except Exception:
        pass
    return out


def keyboard_layout():
    out = {"klid": None, "locale": None}
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        buf = ctypes.create_unicode_buffer(9)
        if user32.GetKeyboardLayoutNameW(buf):
            out["klid"] = buf.value
        hkl = user32.GetKeyboardLayout(0)
        name = ctypes.create_unicode_buffer(85)
        if kernel32.LCIDToLocaleName(hkl & 0xFFFF, name, 85, 0):
            out["locale"] = name.value
    except Exception:
        pass
    return out


class _RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [("hDevice", W.HANDLE), ("dwType", W.DWORD)]


def parse_vid_pid(path):
    m = _VIDPID.search(path or "")
    return (m.group(1).upper(), m.group(2).upper()) if m else (None, None)


def raw_input_devices():
    """[{type, vid, pid, vendor, bus, path}] solo mouse y teclado."""
    out = []
    try:
        user32 = ctypes.windll.user32
        n = W.UINT(0)
        user32.GetRawInputDeviceList(None, ctypes.byref(n), ctypes.sizeof(_RAWINPUTDEVICELIST))
        arr = (_RAWINPUTDEVICELIST * n.value)()
        user32.GetRawInputDeviceList(arr, ctypes.byref(n), ctypes.sizeof(_RAWINPUTDEVICELIST))
        for d in arr:
            kind = {0: "mouse", 1: "keyboard"}.get(d.dwType)
            if not kind:
                continue
            size = W.UINT(0)
            user32.GetRawInputDeviceInfoW(d.hDevice, 0x20000007, None, ctypes.byref(size))
            buf = ctypes.create_unicode_buffer(size.value + 1)
            user32.GetRawInputDeviceInfoW(d.hDevice, 0x20000007, buf, ctypes.byref(size))
            path = buf.value
            vid, pid = parse_vid_pid(path)
            bus = ("bluetooth" if "{00001812-0000-1000-8000-00805f9b34fb}" in path.lower()
                   else "usb" if "vid" in path.lower() else "virtual/unknown")
            # dispositivos virtuales de RDP / drivers sin VID: no aportan
            if not vid and "root#rdp" in path.lower():
                continue
            out.append({"type": kind, "vid": vid, "pid": pid,
                        "vendor": VENDORS.get(vid) if vid else None, "bus": bus, "path": path})
    except Exception:
        pass
    return out


_POLL_MIN_SAMPLES = 200


def _sin_estimacion(reason, samples=0):
    """v0.9.21 (PLE-188): antes devolvía None en silencio y QA lo leyó como un dato
    que faltaba. Ahora dice por qué no se pudo estimar."""
    return {"interval_mode_ms": None, "estimated_hz": None, "share_of_mode": None,
            "samples": samples, "reason": reason}


def mouse_polling_estimate(session_dir):
    """Moda del intervalo entre MOVE del Raw Input → Hz aproximados.
    Siempre devuelve un dict; `estimated_hz` es None con `reason` cuando no se pudo."""
    if not session_dir:
        return _sin_estimacion("no session directory")
    try:
        p = Path(session_dir) / "mouse_delta_log.csv"
        ts = []
        with open(p, encoding="utf-8-sig") as f:
            for r in csv.reader(f):
                if len(r) >= 2 and r[1] == "MOVE" and r[0].isdigit():
                    ts.append(int(r[0]))
        if not ts:
            return _sin_estimacion("no raw mouse movement in this session")
        if len(ts) < _POLL_MIN_SAMPLES:
            return _sin_estimacion(f"too few raw mouse samples (need {_POLL_MIN_SAMPLES})",
                                   len(ts))
        d = Counter(b - a for a, b in zip(ts, ts[1:]) if 0 < b - a <= 50)
        if not d:
            return _sin_estimacion("no consecutive samples within 50 ms", len(ts))
        mode_ms, cnt = d.most_common(1)[0]
        return {"interval_mode_ms": mode_ms,
                "estimated_hz": round(1000.0 / mode_ms) if mode_ms else None,
                "share_of_mode": round(cnt / sum(d.values()), 2),
                "samples": len(ts),
                "notes": "Mode of the interval between consecutive WM_INPUT MOVE events; "
                         "1 ms timestamp resolution, so 125 Hz reads as 8 ms and 1000 Hz as 1 ms."}
    except Exception as e:
        return _sin_estimacion(f"could not read mouse_delta_log.csv ({type(e).__name__})")


def collect(session_dir=None, mouse_dpi_declared=None):
    """Bloque `input.device_metadata` para session_metadata.json."""
    devs = raw_input_devices()
    mice = [d for d in devs if d["type"] == "mouse"]
    kbs = [d for d in devs if d["type"] == "keyboard"]
    dpi = None
    try:
        dpi = int(mouse_dpi_declared) if mouse_dpi_declared else None
        if dpi is not None and not (100 <= dpi <= 50000):
            dpi = None
    except Exception:
        dpi = None
    # El `path` del dispositivo NO va al metadata: en Bluetooth trae la dirección
    # del dispositivo (identificador persistente de la persona). Solo VID/PID/bus.
    def _pub(d):
        return {k: v for k, v in d.items() if k in ("vid", "pid", "vendor", "bus")}
    return {
        "mouse": {
            **os_mouse_settings(),
            "counts_per_inch": dpi,
            "counts_per_inch_source": "user_declared" if dpi else "unknown",
            "polling": mouse_polling_estimate(session_dir),
            "devices": [_pub(d) for d in mice],
        },
        "keyboard": {
            **keyboard_layout(),
            "devices": [_pub(d) for d in kbs],
        },
        "notes": ("OS pointer speed/acceleration and keyboard layout read from Windows at session "
                  "close; VID/PID from Raw Input device paths; mouse DPI only if the member declared "
                  "it in Settings (not measurable from the OS); in-game sensitivity comes from the "
                  "title's config file when available (key_mapping path), not from here."),
    }
