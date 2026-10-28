"""Referencia del nicho (bloque 3.1 del PLAN): Shorts de finanzas EN con muchas vistas.

    python research/referencia_nicho.py        # reescribe research/referencia_nicho.json

Solo metadatos de la YouTube Data API (duración, vistas, título). NO baja audio ni vídeo: los
Términos de YouTube prohíben descargar sin permiso de YouTube y del titular, y la API de subtítulos
(`captions.download`) solo deja bajar los del canal propio con OAuth. Por eso el dataset no trae
transcripción: segundo de la 1.ª cifra, palabras/min, frases, giros y bucle quedan SIN medir.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from omega.sources.youtube import _get, _is_english

SALIDA = Path(__file__).with_name("referencia_nicho.json")
# explicadores (el formato de Net Worthy), no "saving money" a secas: ahí ganan sketches y mascotas
QUERIES = [
    "stock market explained",
    "how inflation works",
    "mortgage rates explained",
    "compound interest explained",
    "housing market crash",
    "federal reserve interest rates",
    "index fund investing",
    "warren buffett advice",
    "recession explained",
    "bitcoin explained",
    "dividend investing",
    "credit score explained",
]
# el título tiene que ser de finanzas y no de comedia/hindi romanizado: filtro explícito, no a ojo
FINANZAS = re.compile(
    r"\b(invest\w*|stocks?|market|inflation|mortgage|interest|rates?|fed|recession|bitcoin|"
    r"crypto|dividends?|index|etf|401k|ira|retire\w*|wealth\w*|money|debt|credit|housing|home|"
    r"rich|buffett|economy|banks?|tax\w*|income|budget\w*|compound)\b",
    re.IGNORECASE,
)
FUERA = re.compile(
    # memes y mercado indio (mutual fund/SIP/Nifty): otra audiencia que la EN/US del canal
    r"#fyp|#?meme|funny|prank|couple|comedy|skit|kitten|\b(hai|ke|ki|kya|me)\b|"
    r"mutual fund|\bsip\b|nifty|sensex",
    re.IGNORECASE,
)
DESDE = (
    "2025-01-01T00:00:00Z"  # era actual de Shorts (vista = scroll-by desde mar-2025)
)
N, POR_CANAL, MAX_S = 30, 2, 180


def dur_s(iso: str) -> int:
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return sum(int(g or 0) * k for g, k in zip(m.groups(), (3600, 60, 1))) if m else 0


def elegir(filas: list[dict], n: int = N, por_canal: int = POR_CANAL) -> list[dict]:
    """Los n más vistos, con tope por canal para que uno solo no defina la referencia."""
    out, cuenta = [], {}
    for f in sorted(filas, key=lambda f: -f["views"]):
        if cuenta.get(f["channel_id"], 0) < por_canal:
            out.append(f)
            cuenta[f["channel_id"]] = cuenta.get(f["channel_id"], 0) + 1
        if len(out) == n:
            break
    return out


def main() -> None:
    for linea in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        if linea.startswith("YOUTUBE_API_KEY"):
            os.environ.setdefault("YOUTUBE_API_KEY", linea.split("=", 1)[1].strip())
    ids = {}
    for q in QUERIES:
        r = _get(
            "search",
            {
                "part": "id",
                "q": q,
                "type": "video",
                "videoDuration": "short",
                "order": "viewCount",
                "maxResults": 50,
                "relevanceLanguage": "en",
                "regionCode": "US",
                "publishedAfter": DESDE,
            },
        )
        for it in r.get("items", []):
            ids.setdefault(it["id"]["videoId"], q)
    filas, lista = [], list(ids)
    for i in range(0, len(lista), 50):
        d = _get(
            "videos",
            {
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(lista[i : i + 50]),
            },
        )
        for v in d.get("items", []):
            sn = v["snippet"]
            f = {
                "id": v["id"],
                "url": f"https://youtube.com/shorts/{v['id']}",
                "title": sn["title"],
                "channel": sn["channelTitle"],
                "channel_id": sn["channelId"],
                "query": ids[v["id"]],
                "language": sn.get("defaultAudioLanguage") or "",
                "published": sn["publishedAt"][:10],
                "views": int(v["statistics"].get("viewCount", 0)),
                "dur_s": dur_s(v["contentDetails"]["duration"]),
            }
            if (
                _is_english(f)
                and 0 < f["dur_s"] <= MAX_S
                and FINANZAS.search(f["title"])
                and not FUERA.search(f["title"])
            ):
                filas.append(f)
    ref = elegir(filas)
    for f in ref:
        del f["language"]
    SALIDA.write_text(
        json.dumps(
            {
                "medido": date.today().isoformat(),
                "fuente": "YouTube Data API v3 (search+videos)",
                "metodo": f"top {N} por vistas, Shorts <= {MAX_S} s, EN, desde {DESDE[:10]}, "
                f"máx. {POR_CANAL} por canal, título con término de finanzas y sin marcas de "
                f"comedia/hindi; queries: {', '.join(QUERIES)}",
                "sin_medir": "transcripción (no se puede bajar legalmente): 1.ª cifra, palabras/min, "
                "frases, pregunta, giros/10 s, bucle",
                "shorts": ref,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"{len(ref)} Shorts de {len(filas)} candidatos -> {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
