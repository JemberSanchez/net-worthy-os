"""Shorts must stay byte-identical while the long-form format is added (F1, 18-nov-2026).

The fixture holds the sha256 of every published Short's page as built before `formato` existed.
motor.js / motor3d.js are inlined in the page; they are masked here because their geometry is
covered by the frame comparison of read-janitor (see docs/LONGFORM-PLAN.md F1).
Regenerate only on a deliberate Short change: python tests/test_formato_regresion.py --regenerar
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / "video-v2" / "motor"), str(RAIZ / "tools")]

import construir as c

FIX = Path(__file__).parent / "fixtures" / "formato_regresion.json"


def hashes() -> dict[str, str]:
    scripts = [
        (c.MOTOR / f).read_text(encoding="utf-8") for f in ("motor.js", "motor3d.js")
    ]
    out = {}
    for sb in sorted((RAIZ / "video-v2").glob("*/storyboard.json")):
        w = sb.parent / "assets" / "words.json"
        if not w.exists():
            continue
        h = c._html(
            c.plan(
                json.loads(sb.read_text(encoding="utf-8")),
                json.loads(w.read_text(encoding="utf-8")),
            )
        )
        for s in scripts:
            h = h.replace(s, "<script-masked>")
        out[sb.parent.name] = hashlib.sha256(h.encode()).hexdigest()
    return out


class ShortsIdenticos(unittest.TestCase):
    def test_paginas_de_shorts_sin_cambio(self):
        esperado = json.loads(FIX.read_text(encoding="utf-8"))
        actual = hashes()
        distintos = sorted(k for k in esperado if actual.get(k) != esperado[k])
        self.assertEqual(distintos, [], "Short pages changed")


if __name__ == "__main__" and "--regenerar" in sys.argv:
    FIX.write_text(json.dumps(hashes(), indent=1) + "\n", encoding="utf-8")
elif __name__ == "__main__":
    unittest.main()
