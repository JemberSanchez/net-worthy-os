"""What this Claude Code session cost, measured from its transcript (PLAN 4.2: cost per video).

    python tools/costo_sesion.py video-v2/<ref>     # writes <ref>/renders/costo.json and prints it

Reads the newest transcript of this project (the running session). A transcript repeats the usage of
one API message on every content block, so messages are counted once by id: counting lines doubled
the turns and the cache reads (11-nov).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def medir(transcript: Path) -> dict:
    usos, t0, t1 = {}, None, None
    for linea in transcript.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            o = json.loads(linea)
        except ValueError:
            continue
        if o.get("timestamp"):
            t0, t1 = t0 or o["timestamp"], o["timestamp"]
        m = o.get("message")
        if isinstance(m, dict) and m.get("usage") and m.get("id"):
            usos[m["id"]] = m["usage"]

    def suma(k: str) -> int:
        return sum(u.get(k) or 0 for u in usos.values())

    def seg(t: str) -> float:
        return datetime.fromisoformat(t).timestamp()

    return {
        "turnos": len(usos),
        "cache_leida": suma("cache_read_input_tokens"),
        "cache_escrita": suma("cache_creation_input_tokens"),
        "salida": suma("output_tokens"),
        "minutos": round((seg(t1) - seg(t0)) / 60) if t0 and t1 else None,
    }


def transcript_actual() -> Path:
    carpeta = (
        Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(RAIZ))
    )
    return max(carpeta.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    try:
        costo = medir(transcript_actual())
    except ValueError:  # max() of no transcripts: cloud run or another machine
        raise SystemExit(
            "sin transcript de Claude Code para este proyecto: coste no medido"
        ) from None
    salida = Path(sys.argv[1]) / "renders" / "costo.json"
    if salida.parent.exists():
        salida.write_text(json.dumps(costo, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(costo))
