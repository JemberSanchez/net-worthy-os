"""Delivery of a finished Short in one background command, with no Claude turn per step.

    python tools/entregar.py video-v2/<ref>      # run_in_background; prints only failures + the plan

produccion-guardar -> estado-subir -> `publicar <ref>` WITHOUT --publicar (the plan: crítico and the
state of each network). It never publishes: going live needs the user's yes in the chat (Meta always).
Medido 20-nov: entregar = 6.8 min de mediana en 7 sesiones, 6.0 de ellos esperando herramientas.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def pasos(proy: Path) -> list[list[str]]:
    # publicar has no --publicar here on purpose: a test pins it.
    return [
        ["produccion-guardar", str(proy)],
        ["estado-subir"],
        ["publicar", proy.name],
    ]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    proy = Path(sys.argv[1])
    fallos = 0
    for p in pasos(proy):
        r = subprocess.run(
            [sys.executable, "-m", "omega.cli", *p],
            cwd=RAIZ,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        salida = (r.stdout + r.stderr).strip()
        if p[0] == "publicar" or r.returncode:
            print(f"{'✗' if r.returncode else '·'} {p[0]}:\n{salida}")
        fallos += r.returncode != 0
    print("✓ entregado" if not fallos else f"✗ {fallos} paso(s) fallaron")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
