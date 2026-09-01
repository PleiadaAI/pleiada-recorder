# -*- coding: utf-8 -*-
"""
medir_calidad.py  —  v1.0  (27-08-2026)

Mide dos cosas sobre grabaciones ya hechas, SIN necesitar un archivo de
referencia y SIN modificar nada:

  1. PERFIL DE BITRATE segundo a segundo.
     Responde: la grabacion, ¿reparte los bits segun lo que pasa en pantalla,
     o gasta siempre lo mismo? Si el techo configurado no se usa NUNCA, la
     calidad en las escenas dificiles no es la que esperabamos.

  2. FRAMES UNICOS vs DUPLICADOS.
     Responde: el archivo dice 60 fps, ¿pero cuantas imagenes distintas por
     segundo hay realmente? Si el titulo corrio a 10 fps, el archivo igual
     sale a 60 porque los frames se repiten — y eso hoy no lo detecta nada.

No escribe ni borra ningun video. Solo lee y produce un CSV.

USO
---
    python medir_calidad.py --carpeta "C:\\ruta\\a\\las\\grabaciones"

    python medir_calidad.py --carpeta "C:\\ruta" --minutos 10
        Analiza solo los primeros 10 minutos de cada archivo. Util para
        sesiones largas: el paso 2 tiene que decodificar el video entero y
        eso tarda.

    python medir_calidad.py --carpeta "C:\\ruta" --salida "C:\\ruta\\resultado.csv"

REQUISITOS
----------
Necesita ffmpeg y ffprobe en el PATH. Si no estan, el script lo avisa y sale
sin hacer nada.
"""

import argparse
import collections
import csv
import os
import re
import shutil
import subprocess
import sys

VERSION = "1.0"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def correr(cmd, timeout=7200):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def hay_herramientas():
    faltan = [x for x in ("ffmpeg", "ffprobe") if not shutil.which(x)]
    if faltan:
        print("FALTA: %s no esta instalado (o no esta en el PATH)." % " y ".join(faltan))
        print()
        print("Para instalarlo, abri PowerShell y corre:")
        print("    winget install Gyan.FFmpeg")
        print()
        print("Despues CERRA y VOLVE A ABRIR PowerShell, y probá:")
        print("    ffmpeg -version")
        return False
    return True


def frac(txt):
    try:
        a, b = txt.split("/")
        return float(a) / float(b)
    except Exception:
        try:
            return float(txt)
        except Exception:
            return 0.0


def info_basica(mp4):
    """codec, resolucion, fps declarado, duracion y tamaño."""
    r = correr(["ffprobe", "-v", "error", "-print_format", "json",
                "-show_format", "-show_streams", mp4])
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200] or "ffprobe fallo")
    import json
    d = json.loads(r.stdout)
    vs = [s for s in d["streams"] if s.get("codec_type") == "video"]
    if not vs:
        raise RuntimeError("el archivo no tiene stream de video")
    v = vs[0]
    dur = float(d["format"].get("duration") or 0)
    size = int(d["format"].get("size") or 0)
    return {
        "codec": v.get("codec_name", ""),
        "ancho": int(v.get("width") or 0),
        "alto": int(v.get("height") or 0),
        "fps_declarado": round(frac(v.get("avg_frame_rate") or "0/1"), 3),
        "dur_s": round(dur, 2),
        "tamano_MB": round(size / (1024 * 1024), 1),
        "bitrate_medio_kbps": round(size * 8 / dur / 1000) if dur else 0,
    }


def perfil_bitrate(mp4, limite_s):
    """kbps por cada segundo de video. No decodifica: solo lee los paquetes."""
    r = correr(["ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "packet=pts_time,size",
                "-of", "csv=p=0", mp4])
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200] or "ffprobe -show_entries fallo")

    por_seg = collections.defaultdict(int)
    for linea in r.stdout.splitlines():
        partes = linea.strip().split(",")
        if len(partes) < 2:
            continue
        try:
            t = float(partes[0])
            b = int(partes[1])
        except ValueError:
            continue
        if limite_s and t > limite_s:
            break
        por_seg[int(t)] += b

    if not por_seg:
        return {}

    # El ultimo segundo suele estar incompleto y ensucia el minimo. Se descarta.
    claves = sorted(por_seg)[:-1] or sorted(por_seg)
    kbps = sorted(por_seg[k] * 8 / 1000.0 for k in claves)
    n = len(kbps)

    def pct(p):
        return round(kbps[min(int(n * p), n - 1)])

    return {
        "seg_analizados": n,
        "kbps_p05": pct(0.05),
        "kbps_p50": pct(0.50),
        "kbps_p95": pct(0.95),
        "kbps_max": round(kbps[-1]),
        "seg_sobre_8000": sum(1 for x in kbps if x > 8000),
        "seg_sobre_12000": sum(1 for x in kbps if x > 12000),
        "pct_seg_sobre_12000": round(100.0 * sum(1 for x in kbps if x > 12000) / n, 2),
    }


def frames_unicos(mp4, limite_s):
    """
    Cuenta cuantas imagenes DISTINTAS hay, descartando las repetidas.

    `-fps_mode passthrough` es obligatorio: sin eso ffmpeg vuelve a rellenar
    los frames descartados para sostener los 60 fps de salida, y el conteo
    daria siempre el numero nominal.
    """
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", mp4]
    if limite_s:
        cmd += ["-t", str(limite_s)]
    cmd += ["-map", "0:v:0", "-vf", "mpdecimate", "-fps_mode", "passthrough",
            "-f", "null", "-"]
    r = correr(cmd)
    salida = (r.stderr or "") + (r.stdout or "")
    marcas = re.findall(r"frame=\s*(\d+)", salida)
    if not marcas:
        raise RuntimeError("ffmpeg no reporto cantidad de frames")
    return int(marcas[-1])


def frames_totales(mp4, limite_s):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-count_packets", "-show_entries", "stream=nb_read_packets",
           "-of", "csv=p=0"]
    if limite_s:
        cmd += ["-read_intervals", "%%+%d" % limite_s]
    cmd += [mp4]
    r = correr(cmd)
    try:
        return int((r.stdout or "0").strip().split(",")[0])
    except ValueError:
        return 0


COLUMNAS = ["archivo", "carpeta", "codec", "ancho", "alto", "fps_declarado",
            "dur_s", "tamano_MB", "bitrate_medio_kbps",
            "seg_analizados", "kbps_p05", "kbps_p50", "kbps_p95", "kbps_max",
            "seg_sobre_8000", "seg_sobre_12000", "pct_seg_sobre_12000",
            "frames_totales", "frames_unicos", "fps_unicos", "pct_duplicados",
            "error"]


def main():
    ap = argparse.ArgumentParser(
        description="Perfil de bitrate y conteo de frames unicos sobre grabaciones ya hechas.")
    ap.add_argument("--carpeta", required=True,
                    help="carpeta con los .mp4 (busca tambien en subcarpetas)")
    ap.add_argument("--minutos", type=float, default=0,
                    help="analizar solo los primeros N minutos de cada archivo (0 = todo)")
    ap.add_argument("--salida", default="",
                    help="ruta del CSV de salida (por defecto: medicion_calidad.csv "
                         "dentro de la carpeta analizada)")
    args = ap.parse_args()

    print("medir_calidad.py v%s" % VERSION)

    if not hay_herramientas():
        return 1

    if not os.path.isdir(args.carpeta):
        print("FALTA: no encuentro la carpeta %s" % args.carpeta)
        return 1

    limite_s = int(args.minutos * 60) if args.minutos else 0

    archivos = []
    for raiz, _dirs, files in os.walk(args.carpeta):
        for f in files:
            if f.lower().endswith(".mp4"):
                archivos.append(os.path.join(raiz, f))
    archivos.sort()

    if not archivos:
        print("No encontre ningun .mp4 dentro de %s" % args.carpeta)
        return 1

    salida = args.salida or os.path.join(args.carpeta, "medicion_calidad.csv")
    print("%d archivos a analizar%s" % (
        len(archivos), " (primeros %g min de cada uno)" % args.minutos if limite_s else ""))
    print("resultado -> %s\n" % salida)

    filas = []
    for i, mp4 in enumerate(archivos, 1):
        nombre = os.path.basename(mp4)
        print("[%d/%d] %s" % (i, len(archivos), nombre[:70]), flush=True)
        fila = {c: "" for c in COLUMNAS}
        fila["archivo"] = nombre
        fila["carpeta"] = os.path.basename(os.path.dirname(mp4))
        try:
            fila.update(info_basica(mp4))
            print("        bitrate medio %s kbps · %s · %.1f min"
                  % (fila["bitrate_medio_kbps"], fila["codec"], fila["dur_s"] / 60))

            fila.update(perfil_bitrate(mp4, limite_s))
            print("        por segundo: p05 %s · p50 %s · p95 %s · max %s kbps"
                  % (fila.get("kbps_p05"), fila.get("kbps_p50"),
                     fila.get("kbps_p95"), fila.get("kbps_max")))

            print("        contando frames unicos (esto tarda)...", flush=True)
            tot = frames_totales(mp4, limite_s)
            uni = frames_unicos(mp4, limite_s)
            ventana = limite_s or fila["dur_s"]
            fila["frames_totales"] = tot
            fila["frames_unicos"] = uni
            fila["fps_unicos"] = round(uni / ventana, 2) if ventana else ""
            fila["pct_duplicados"] = round(100.0 * (tot - uni) / tot, 1) if tot else ""
            print("        %s frames -> %s unicos = %s fps reales (%s%% repetidos)"
                  % (tot, uni, fila["fps_unicos"], fila["pct_duplicados"]))
        except Exception as e:
            fila["error"] = "%s: %s" % (type(e).__name__, str(e)[:150])
            print("        ERROR: %s" % fila["error"])
        filas.append(fila)
        print()

    with open(salida, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)

    ok = [r for r in filas if not r["error"]]
    print("=" * 62)
    print("Listo: %d de %d archivos analizados sin error." % (len(ok), len(filas)))
    if ok:
        techo = sum(r.get("seg_sobre_12000") or 0 for r in ok)
        print("Segundos que superaron los 12.000 kbps en todo el set: %d" % techo)
        peor = min(ok, key=lambda r: r.get("fps_unicos") or 999)
        print("fps reales mas bajo: %s en %s" % (peor.get("fps_unicos"), peor["archivo"]))
    print("Mandanos este archivo: %s" % salida)
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
