"""Spike T0 · input.device_metadata: ¿qué calibración de dispositivos podemos
leer del sistema sin preguntarle nada al usuario?

Lee con ctypes (sin dependencias):
  - SPI_GETMOUSESPEED (1..20, 10 = default) y SPI_GETMOUSE (aceleración /
    "Mejorar la precisión del puntero");
  - layout de teclado activo (GetKeyboardLayoutName + LCID);
  - lista de dispositivos Raw Input con su ruta HID → VID/PID, y el nombre de
    producto/fabricante por hid.dll;
  - tasa de sondeo (polling) del mouse estimada desde un mouse_delta_log.csv
    real (moda del intervalo entre MOVE consecutivos).

Uso: python tests/spike_device_metadata.py ["<carpeta de sesión>"]
"""
import ctypes
import ctypes.wintypes as W
import csv
import re
import sys
from collections import Counter
from pathlib import Path

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def os_mouse():
    speed = ctypes.c_int(0)
    user32.SystemParametersInfoW(0x0070, 0, ctypes.byref(speed), 0)          # SPI_GETMOUSESPEED
    arr = (ctypes.c_int * 3)()
    user32.SystemParametersInfoW(0x0003, 0, arr, 0)                          # SPI_GETMOUSE
    return {"os_sensitivity": speed.value,
            "os_acceleration": "enabled" if arr[2] else "disabled",
            "mouse_thresholds": [arr[0], arr[1]]}


def keyboard_layout():
    buf = ctypes.create_unicode_buffer(9)
    user32.GetKeyboardLayoutNameW(buf)
    hkl = user32.GetKeyboardLayout(0)
    lcid = hkl & 0xFFFF
    name = ctypes.create_unicode_buffer(85)
    kernel32.LCIDToLocaleName(lcid, name, 85, 0)
    return {"klid": buf.value, "locale": name.value}


class RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [("hDevice", W.HANDLE), ("dwType", W.DWORD)]


def raw_devices():
    n = W.UINT(0)
    user32.GetRawInputDeviceList(None, ctypes.byref(n), ctypes.sizeof(RAWINPUTDEVICELIST))
    arr = (RAWINPUTDEVICELIST * n.value)()
    user32.GetRawInputDeviceList(arr, ctypes.byref(n), ctypes.sizeof(RAWINPUTDEVICELIST))
    out = []
    for d in arr:
        size = W.UINT(0)
        user32.GetRawInputDeviceInfoW(d.hDevice, 0x20000007, None, ctypes.byref(size))   # RIDI_DEVICENAME
        buf = ctypes.create_unicode_buffer(size.value + 1)
        user32.GetRawInputDeviceInfoW(d.hDevice, 0x20000007, buf, ctypes.byref(size))
        path = buf.value
        kind = {0: "mouse", 1: "keyboard", 2: "hid"}.get(d.dwType, "?")
        m = re.search(r"VID_([0-9A-Fa-f]{4}).*PID_([0-9A-Fa-f]{4})", path)
        vid, pid = (m.group(1).upper(), m.group(2).upper()) if m else (None, None)
        out.append({"type": kind, "path": path, "vid": vid, "pid": pid,
                    **hid_strings(path)})
    return out


def hid_strings(path):
    """Producto y fabricante por hid.dll. Muchos dispositivos no lo exponen."""
    res = {"manufacturer": None, "product": None}
    try:
        hid = ctypes.windll.hid
        h = kernel32.CreateFileW(path, 0, 3, None, 3, 0x80, None)   # sin acceso, solo query
        if h == W.HANDLE(-1).value or h == -1:
            return res
        try:
            for key, fn in (("manufacturer", hid.HidD_GetManufacturerString),
                            ("product", hid.HidD_GetProductString)):
                buf = ctypes.create_unicode_buffer(127)
                if fn(h, buf, 254):
                    res[key] = buf.value or None
        finally:
            kernel32.CloseHandle(h)
    except Exception:
        pass
    return res


def polling_rate(session_dir):
    p = Path(session_dir) / "mouse_delta_log.csv"
    if not p.exists():
        return None
    ts = []
    with open(p, encoding="utf-8-sig") as f:
        for r in csv.reader(f):
            if len(r) >= 2 and r[1] == "MOVE" and r[0].isdigit():
                ts.append(int(r[0]))
    d = Counter(b - a for a, b in zip(ts, ts[1:]) if 0 < b - a <= 50)
    if not d:
        return None
    moda_ms, cnt = d.most_common(1)[0]
    return {"interval_mode_ms": moda_ms, "estimated_hz": round(1000 / moda_ms) if moda_ms else None,
            "share_of_mode": round(cnt / sum(d.values()), 2), "samples": len(ts)}


def main():
    print("OS mouse:", os_mouse())
    print("keyboard:", keyboard_layout())
    print("raw devices:")
    for d in raw_devices():
        if d["type"] in ("mouse", "keyboard"):
            print(f"  {d['type']:8} VID={d['vid']} PID={d['pid']} {d['manufacturer']!r} {d['product']!r}")
            print(f"           {d['path']}")
    if len(sys.argv) > 1:
        print("polling:", polling_rate(sys.argv[1]))


if __name__ == "__main__":
    main()
