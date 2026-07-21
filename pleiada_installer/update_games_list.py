"""
update_games_list.py — regenera files/games_list.json desde Airtable.

PASO DE BUILD: correr ANTES de compilar el instalador para que el fallback
bundleado salga con la lista viva (mismo filtro "Publicado" que usa la app
y que usa el catálogo público). Sin argumentos:

    python update_games_list.py

Usa el propio código de descarga de la app (files/pleiada_app.pyw), así el
bundle y el caché runtime son SIEMPRE el mismo dataset con el mismo filtro.
"""

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "files", "pleiada_app.pyw")
OUT = os.path.join(HERE, "files", "games_list.json")


def main():
    # la app importa módulos hermanos (session_uploader, pleiada_api)
    sys.path.insert(0, os.path.join(HERE, "files"))
    spec = importlib.util.spec_from_file_location("papp", APP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    version = m._airtable_remote_version()
    games = m._airtable_download_games()
    if not games:
        print("ERROR: la descarga no devolvió juegos — no se toca el bundle")
        return 1

    games.sort(key=lambda g: g["game"].lower())
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(games, f, ensure_ascii=False, indent=1)

    print(f"OK: {len(games)} juegos publicados escritos en {OUT}")
    print(f"    list_version remota al momento del build: {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
