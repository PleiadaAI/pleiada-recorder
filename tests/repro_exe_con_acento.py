"""Reproduce el bug de Martin: un exe con acento en el nombre.

Crea un proceso que se llama de verdad "Malon.exe" con tilde, lo deja corriendo,
y le pregunta a _exe_corriendo() si lo ve.
"""
import importlib.util
import locale
import shutil
import subprocess
import sys
import time
from pathlib import Path

FILES = Path(r"C:\Users\mspin\Documents\pleiada-recorder\pleiada_installer\files")
TMP = Path(__file__).parent / "fakeproc"
TMP.mkdir(exist_ok=True)
sys.path.insert(0, str(FILES))

spec = importlib.util.spec_from_file_location("pleiada_app", FILES / "pleiada_app.pyw")
app = importlib.util.module_from_spec(spec)
sys.modules["pleiada_app"] = app
spec.loader.exec_module(app)

NOMBRE = "Mal\u00f3n.exe"                      # Malón.exe
falso = TMP / NOMBRE
shutil.copy(sys.executable.replace("python.exe", "pythonw.exe"), falso)

print("encoding que usa text=True :", locale.getpreferredencoding(False))
try:
    cp = subprocess.run(["chcp"], capture_output=True, text=True, shell=True).stdout.strip()
    print("codepage de la consola    :", cp)
except Exception as e:
    print("chcp fallo:", e)

p = subprocess.Popen([str(falso), "-c", "import time; time.sleep(25)"])
time.sleep(2.5)
print(f"\nproceso {NOMBRE} corriendo, pid {p.pid}")

try:
    # 1. Lo que hace el Recorder hoy
    r = app._exe_corriendo(NOMBRE)
    print(f"\n_exe_corriendo({NOMBRE!r}) -> {r}   <-- deberia ser True")

    # 2. Qué devuelve tasklist crudo, decodificado de las dos maneras
    raw = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {NOMBRE}", "/FO", "CSV", "/NH"],
        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=8).stdout
    print("\nbytes crudos de tasklist:", raw[:70])
    for enc in ("utf-8", "cp1252", "cp850", "cp437", "mbcs"):
        try:
            print(f"   decodificado {enc:8}: {raw.decode(enc, 'replace').strip()[:60]!r}")
        except Exception as e:
            print(f"   decodificado {enc:8}: ERROR {e}")

    # 3. Un exe sin acento, de control
    r2 = app._exe_corriendo("pythonw.exe")
    print(f"\ncontrol: _exe_corriendo('pythonw.exe') -> {r2}")
finally:
    p.terminate()
    p.wait(timeout=10)
    try:
        falso.unlink()
    except Exception:
        pass
