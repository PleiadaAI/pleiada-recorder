# -*- coding: utf-8 -*-
"""
medir_degradacion.py  —  v1.0  (31-08-2026)

Marca los TRAMOS de una sesion donde el video no entrego imagenes nuevas al
ritmo declarado.

Existe por un requisito literal de Troveo:

    "in the event of performance degradation, all affected time intervals
     must be explicitly flagged"

`medir_calidad.py` ya contesta "cuantas imagenes distintas por segundo hubo"
pero da UN numero por archivo. El cliente pide INTERVALOS. Esta herramienta es
ese paso: de un promedio a una lista de tramos con principio y fin.

EL PROBLEMA QUE RESUELVE, EN UNA LINEA
--------------------------------------
Hoy una sesion que corrio a 10 imagenes por segundo se entrega declarando 60 y
pasa todos los controles: OBS repite frames para sostener el ritmo constante, y
`frames_dropped` se calcula como (esperado - contados), asi que da 0.
Verificado sobre material real: `Counter-Strike 2_08_06_26__02_24_09`, 5.136
frames declarados a 60 fps, `frames_dropped: 0`, y solo 3.343 imagenes
distintas (38,9 por segundo de promedio, con segundos de 1).

LA TRAMPA, Y COMO SE RESUELVE
-----------------------------
`mpdecimate` no distingue "el juego corrio lento" de "la pantalla estuvo
quieta" (menu, pausa, inventario, plano fijo). Las dos cosas producen imagenes
repetidas y son fenomenos MUY distintos: una es un defecto que hay que
declarar, la otra es gameplay normal.

Se desempata con el input, que ya tenemos y comparte reloj con el video:

    pocas imagenes nuevas  +  el jugador ESTA jugando   -> degradacion real
    pocas imagenes nuevas  +  el jugador no toca nada   -> pantalla quieta

Un menu no se juega: el mouse se mueve en absoluto y las teclas casi no entran.
Un tramo con el jugador apretando teclas y moviendo el mouse mientras la imagen
no cambia es el sintoma de un motor que no llega.

QUE NO HACE
-----------
NO es un veredicto. Los umbrales de abajo son un punto de partida razonable, no
una calibracion: para eso hay que comparar contra fps observados por una persona
sobre un conjunto de sesiones. Por eso la salida incluye la evidencia cruda
(serie por segundo + input por segundo) y no solo la conclusion.

USO
---
    python medir_degradacion.py --sesion "C:\\ruta\\a\\una sesion recording"
    python medir_degradacion.py --carpeta "C:\\ruta\\a\\Pleiada Recordings"
    python medir_degradacion.py --carpeta "..." --salida tramos.csv --serie serie.csv

REQUISITOS
----------
ffmpeg y ffprobe en el PATH.
"""

import argparse
import collections
import csv
import json
import os
import re
import shutil
import subprocess
import sys

VERSION = "1.0"

# ── Umbrales — PROVISORIOS, ver "QUE NO HACE" arriba ─────────────────────────
# Un segundo se considera pobre si entrego menos de esta fraccion de las
# imagenes nuevas que promete el fps declarado. 0,5 = la mitad.
FRACCION_POBRE = 0.50
# Eventos de input accionable por segundo a partir de los cuales se considera
# que el jugador ESTABA jugando. Sale de la misma familia de medidas que el
# gate de input (20 ev/min de piso para una sesion entera es otro orden: aca
# se mide por segundo y sobre actividad continua).
INPUT_ACTIVO_POR_SEG = 5
# Un tramo se reporta recien a partir de esta duracion. Un bajon de un segundo
# suelto es ruido; lo que le importa al cliente son tramos que se ven.
MIN_SEG_TRAMO = 2

CSVS_INPUT = ("mouse_delta_log.csv", "key_log.csv")

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
        sys.exit("Falta en el PATH: " + ", ".join(faltan))


def info_video(mp4):
    r = correr(["ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=r_frame_rate,nb_frames,duration,width,height",
                "-of", "json", mp4])
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip()[:200] or "ffprobe fallo")
    st = (json.loads(r.stdout).get("streams") or [{}])[0]
    num, _, den = (st.get("r_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    return {
        "fps_declarado": round(fps, 3),
        "frames_declarados": int(st.get("nb_frames") or 0),
        "dur_s": float(st.get("duration") or 0),
        "ancho": st.get("width"), "alto": st.get("height"),
    }


def segundos_con_imagen_nueva(mp4):
    """
    {segundo: cuantas imagenes DISTINTAS entrego ese segundo}.

    `mpdecimate` tira las repetidas y `showinfo` deja el timestamp exacto de
    cada una de las que sobreviven. `-fps_mode passthrough` es OBLIGATORIO:
    sin eso ffmpeg vuelve a rellenar la salida hasta el fps nominal y el conteo
    da siempre el numero declarado, que es justamente el error que buscamos.

    (`metadata=print` NO sirve: mpdecimate no publica metadata, el archivo sale
    vacio. Probado el 31-08-2026.)
    """
    r = correr(["ffmpeg", "-hide_banner", "-nostats", "-loglevel", "info",
                "-i", mp4, "-map", "0:v:0", "-vf", "mpdecimate,showinfo",
                "-fps_mode", "passthrough", "-f", "null", "-"])
    salida = (r.stderr or "") + (r.stdout or "")
    tiempos = re.findall(r"pts_time:([0-9.]+)", salida)
    if not tiempos:
        raise RuntimeError("ffmpeg no reporto ningun pts_time")
    por_seg = collections.Counter()
    for t in tiempos:
        try:
            por_seg[int(float(t))] += 1
        except ValueError:
            continue
    return por_seg, len(tiempos)


def anchor_de(sesion):
    """t=0 del video en reloj epoch. Es el mismo que abre los CSV."""
    try:
        with open(os.path.join(sesion, "session_metadata.json"), encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return None, {}
    t = (meta.get("timing") or {}).get("start_unix_ms")
    return (int(t) if t else None), meta


def input_por_segundo(sesion, anchor, tope_seg):
    """
    {segundo: eventos de input accionable}. None si no se puede saber.

    Sin esto no se puede separar "corrio lento" de "pantalla quieta", y el
    tramo se reporta como indeterminado en vez de inventar una clasificacion.
    """
    if anchor is None:
        return None
    hubo_archivo = False
    act = collections.Counter()
    for fn in CSVS_INPUT:
        ruta = os.path.join(sesion, fn)
        if not os.path.exists(ruta):
            continue
        hubo_archivo = True
        try:
            with open(ruta, encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    if (r.get("event_type") or "").startswith("ANCHOR"):
                        continue
                    try:
                        s = (int(r["timestamp_ms"]) - anchor) // 1000
                    except (ValueError, TypeError, KeyError):
                        continue
                    if 0 <= s <= tope_seg:
                        act[s] += 1
        except Exception:
            continue
    return act if hubo_archivo else None


def tramos(por_seg, act, fps_declarado, dur_seg):
    """
    Agrupa segundos pobres consecutivos en tramos, y clasifica cada uno.

    Se agrupa PRIMERO y se clasifica DESPUES, sobre el promedio del tramo: un
    segundo suelto sin input dentro de un bajon largo con el jugador activo no
    parte el tramo en tres.
    """
    if not fps_declarado:
        return []
    piso = fps_declarado * FRACCION_POBRE
    pobres = [s for s in range(dur_seg) if por_seg.get(s, 0) < piso]

    grupos, actual = [], []
    for s in pobres:
        if actual and s == actual[-1] + 1:
            actual.append(s)
        else:
            if actual:
                grupos.append(actual)
            actual = [s]
    if actual:
        grupos.append(actual)

    salida = []
    for g in grupos:
        if len(g) < MIN_SEG_TRAMO:
            continue
        fps_medio = sum(por_seg.get(s, 0) for s in g) / len(g)
        if act is None:
            clase, ev_medio = "indeterminado_sin_input", ""
        else:
            ev_medio = sum(act.get(s, 0) for s in g) / len(g)
            clase = ("degradacion" if ev_medio >= INPUT_ACTIVO_POR_SEG
                     else "pantalla_quieta")
        salida.append({
            "t_inicio_s": g[0],
            "t_fin_s": g[-1] + 1,
            "duracion_s": len(g),
            "fps_unicos_medio": round(fps_medio, 1),
            "fps_declarado": fps_declarado,
            "input_ev_por_seg": (round(ev_medio, 1) if ev_medio != "" else ""),
            "clasificacion": clase,
        })
    return salida


def analizar(sesion):
    mp4s = [f for f in sorted(os.listdir(sesion)) if f.lower().endswith(".mp4")]
    if not mp4s:
        return None
    mp4 = os.path.join(sesion, mp4s[0])
    info = info_video(mp4)
    por_seg, unicos = segundos_con_imagen_nueva(mp4)
    dur_seg = int(info["dur_s"]) or (max(por_seg) + 1 if por_seg else 0)
    anchor, meta = anchor_de(sesion)
    act = input_por_segundo(sesion, anchor, dur_seg)
    lista = tramos(por_seg, act, info["fps_declarado"], dur_seg)

    seg_deg = sum(t["duracion_s"] for t in lista if t["clasificacion"] == "degradacion")
    seg_qui = sum(t["duracion_s"] for t in lista if t["clasificacion"] == "pantalla_quieta")
    seg_ind = sum(t["duracion_s"] for t in lista
                  if t["clasificacion"] == "indeterminado_sin_input")
    resumen = {
        "sesion": os.path.basename(sesion.rstrip("/\\")),
        "video": mp4s[0],
        "fps_declarado": info["fps_declarado"],
        "frames_declarados": info["frames_declarados"],
        "frames_unicos": unicos,
        "fps_unicos_medio": round(unicos / dur_seg, 1) if dur_seg else "",
        "dur_s": round(info["dur_s"], 1),
        # Lo que el Recorder declara hoy. Se lo pone al lado a proposito: es el
        # numero que dice que no paso nada.
        "frames_dropped_declarado": (meta.get("video") or {}).get("frames_dropped", ""),
        "tramos_total": len(lista),
        "seg_degradacion": seg_deg,
        "seg_pantalla_quieta": seg_qui,
        "seg_indeterminado": seg_ind,
        "pct_degradacion": round(100.0 * seg_deg / dur_seg, 2) if dur_seg else "",
        "input_disponible": "no" if act is None else "si",
    }
    serie = [{"sesion": resumen["sesion"], "segundo": s,
              "fps_unicos": por_seg.get(s, 0),
              "input_ev": ("" if act is None else act.get(s, 0))}
             for s in range(dur_seg)]
    for t in lista:
        t["sesion"] = resumen["sesion"]
    return resumen, lista, serie


def main():
    ap = argparse.ArgumentParser(
        description="Marca los tramos degradados de una sesion (requisito Troveo).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sesion", help="una carpeta de sesion")
    g.add_argument("--carpeta", help="carpeta que contiene varias sesiones")
    ap.add_argument("--salida", default="tramos_degradados.csv")
    ap.add_argument("--resumen", default="resumen_degradacion.csv")
    ap.add_argument("--serie", default="", help="CSV con la evidencia por segundo")
    ap.add_argument("--limite", type=int, default=0, help="analizar solo N sesiones")
    args = ap.parse_args()

    hay_herramientas()

    if args.sesion:
        sesiones = [args.sesion]
    else:
        sesiones = [os.path.join(args.carpeta, d)
                    for d in sorted(os.listdir(args.carpeta))
                    if os.path.isdir(os.path.join(args.carpeta, d))]
    if args.limite:
        sesiones = sesiones[:args.limite]

    resumenes, todos_tramos, toda_serie = [], [], []
    for i, s in enumerate(sesiones, 1):
        nombre = os.path.basename(s.rstrip("/\\"))
        print(f"[{i}/{len(sesiones)}] {nombre}", flush=True)
        try:
            r = analizar(s)
        except Exception as e:
            print(f"    ERROR: {e}")
            continue
        if r is None:
            print("    sin mp4, salteada")
            continue
        resumen, lista, serie = r
        resumenes.append(resumen)
        todos_tramos.extend(lista)
        toda_serie.extend(serie)
        print(f"    declarado {resumen['fps_declarado']:g} fps · reales "
              f"{resumen['fps_unicos_medio']} · frames_dropped dice "
              f"{resumen['frames_dropped_declarado']}")
        # El indeterminado VA SIEMPRE en la linea. Sin el, una sesion sin CSV de
        # input imprimia "degradacion 0 s · pantalla quieta 0 s" teniendo tramos
        # encontrados, y se leia como "no paso nada" cuando es "no se pudo saber".
        print(f"    tramos: {resumen['tramos_total']} · degradacion "
              f"{resumen['seg_degradacion']} s ({resumen['pct_degradacion']}%) · "
              f"pantalla quieta {resumen['seg_pantalla_quieta']} s · "
              f"sin clasificar {resumen['seg_indeterminado']} s")

    if not resumenes:
        sys.exit("no se pudo analizar ninguna sesion")

    def escribir(ruta, filas, campos):
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
            w.writeheader()
            w.writerows(filas)
        print(f"escrito: {ruta}  ({len(filas)} filas)")

    escribir(args.resumen, resumenes, list(resumenes[0].keys()))
    campos_t = ["sesion", "t_inicio_s", "t_fin_s", "duracion_s", "fps_unicos_medio",
                "fps_declarado", "input_ev_por_seg", "clasificacion"]
    escribir(args.salida, todos_tramos, campos_t)
    if args.serie:
        escribir(args.serie, toda_serie, ["sesion", "segundo", "fps_unicos", "input_ev"])

    print(f"\nUmbrales usados (PROVISORIOS, sin calibrar contra observacion humana):")
    print(f"  segundo pobre     : < {FRACCION_POBRE:.0%} del fps declarado")
    print(f"  jugador activo    : >= {INPUT_ACTIVO_POR_SEG} eventos de input por segundo")
    print(f"  tramo minimo      : {MIN_SEG_TRAMO} s")


if __name__ == "__main__":
    main()
