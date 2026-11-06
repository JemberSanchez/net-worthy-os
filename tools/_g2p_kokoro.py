"""Words Kokoro's lexicon does not know. Runs ONLY under the venv's Python 3.12, like _sintetizar_kokoro.py.

    tools/.venv-voces/Scripts/python.exe tools/_g2p_kokoro.py   (script on stdin, JSON on stdout)

With no fallback misaki marks them `❓`; in the real pipeline espeak GUESSES them (Roth -> right, Binance ->
"bin-ANCE"), so a clean run proves nothing about how they sound. Also lists all-caps tokens with the phonemes
the voice will say: "AWS" comes out as a word, not as letters.
"""

import json
import re
import sys

from kokoro import KPipeline
from misaki import en


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    texto = sys.stdin.read()
    real = KPipeline(lang_code="a", model=False).g2p
    lexico = en.G2P(trf=False, british=False, fallback=None, unk="❓")
    _, toks = lexico(texto)
    dudosas = {
        t.text for t in toks if t.phonemes is None or "❓" in t.phonemes
    }
    siglas = set(re.findall(r"\b[A-Z]{2,6}\b", texto))
    print(
        json.dumps(
            {
                "desconocidas": {w: real(w)[0] for w in sorted(dudosas) if re.search(r"[A-Za-z]", w)},
                "siglas": {w: real(w)[0] for w in sorted(siglas)},
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
