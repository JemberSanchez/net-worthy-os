"""Aggregate renders/corridas.jsonl of every Short: failed runs, minutes, and WHICH rule fails most.

    python tools/resumen_corridas.py [--desde AAAA-MM-DD] [--top 10]

Runs logged before 13-nov only carry the gate name ("puertas fallidas: storyboard"); later ones carry
`reglas` (exact failing rules per gate) and `pendientes` (what --auto could not fix). Rules are counted
after `clase()` strips numbers and quoted values, so "escena 3" and "escena 7" add up."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def clase(regla: str) -> str:
    """'escena 3: cifra '$1.2M' sin fuente' -> 'escena N: cifra '…' sin fuente'."""
    s = re.sub(r"(['\"“]).*?(['\"”])", r"\1…\2", regla)
    return re.sub(r"\d+(?:[.,]\d+)?", "N", s)[:120]


def resumir(lineas: list[dict]) -> dict:
    malas = [x for x in lineas if x.get("fallo")]
    puertas, reglas = Counter(), Counter()
    for x in malas:
        m = re.search(r"puertas fallidas: (.+)|puerta '([^']+)' fallida", x["fallo"])
        if m:
            puertas.update(p.strip() for p in (m.group(1) or m.group(2)).split(","))
        for p, rs in (x.get("reglas") or {}).items():
            reglas.update(f"{p}: {clase(r)}" for r in rs)
        reglas.update(f"auto: {clase(r)}" for r in x.get("pendientes") or [])
    return {
        "corridas": len(lineas),
        "fallidas": len(malas),
        "min_fallidas": round(sum(x.get("s", 0) for x in malas) / 60),
        "min_total": round(sum(x.get("s", 0) for x in lineas) / 60),
        "puertas": puertas,
        "reglas": reglas,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--desde")
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()
    t0 = datetime.fromisoformat(a.desde).timestamp() if a.desde else 0
    lineas = [
        json.loads(s)
        for f in sorted((RAIZ / "video-v2").glob("*/renders/corridas.jsonl"))
        for s in f.read_text(encoding="utf-8").splitlines()
        if s.strip()
    ]
    r = resumir([x for x in lineas if x.get("t", 0) >= t0])
    print(
        f"{r['fallidas']}/{r['corridas']} corridas fallidas · {r['min_fallidas']} de {r['min_total']} min en fallidas"
    )
    print(
        "Puertas:",
        ", ".join(f"{p} {n}" for p, n in r["puertas"].most_common(a.top)) or "-",
    )
    print(
        "Reglas:"
        + (
            "".join(f"\n  {n:3d}  {x}" for x, n in r["reglas"].most_common(a.top))
            or " (sin datos aún)"
        )
    )
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
