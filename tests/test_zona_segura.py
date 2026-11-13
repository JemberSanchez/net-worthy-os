"""Captions must stay clear of the Shorts UI by construction, not be found there by the critic's OCR.

142 of 229 round-0 faults in 20 critic reports (13-nov) were L1 "under the Shorts UI"; the captions box
reached x=1030 (default) and x=930 (editorial), inside the like/comment column that starts at x=0.86."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "tools")]

import medir_texto

W, H = 1080, 1920
TPL = (RAIZ / "video-v2" / "motor" / "plantilla.tpl").read_text(encoding="utf-8")
# OCR boxes run a few px wide and editorial lines carry 16 px of background: keep 2 % of the frame spare
MARGEN = 0.02


def regla(selector: str) -> dict[str, int]:
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", TPL)
    assert m, selector
    return {k: int(v) for k, v in re.findall(r"([a-z]+):\s*(-?\d+)px", m.group(1))}


class SubtitulosFueraDeLaUITest(unittest.TestCase):
    def setUp(self):
        self.base = regla("      #caps")
        self.der = (medir_texto.UMBRALES["zona_derecha"] - MARGEN) * W
        self.abajo = (medir_texto.UMBRALES["zona_inferior"] - MARGEN) * H

    def test_base(self):
        b = self.base
        self.assertLessEqual(W - b["right"], self.der)
        self.assertLessEqual(b["top"] + b["height"], self.abajo)

    def test_claro(self):
        top = regla("#root.claro #caps")["top"]
        self.assertLessEqual(top + self.base["height"], self.abajo)

    def test_editorial(self):
        e = regla("#root.editorial #caps")
        self.assertLessEqual(
            e["left"] + e["width"] + 16, self.der
        )  # + the .ln background padding
        self.assertLessEqual(e["top"] + e["height"], self.abajo)


if __name__ == "__main__":
    unittest.main()
