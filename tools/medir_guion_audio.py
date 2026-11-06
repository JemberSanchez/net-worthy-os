"""Does the final MP4 say what `guion` says? Transcribes the mixed audio and aligns it with the script.

    python tools/medir_guion_audio.py video-v2/<ref> [--mp4 x.mp4]

Digits and currency tokens are suppressed in Whisper: free, it writes "401k" for both "four-oh-one-k" and
"four hundred one k" and hides exactly the defect this exists for (measured 6-nov on average-401k: real take
of "401k" -> "four hundred one K"; final mix -> "four-o-one K"). PROVISIONAL, see docs/CERO-ERRORES.md.
"""

from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

MODELO = "base.en"  # same model as alinear_voz: already downloaded
PARECIDO_MIN = (
    0.6  # below this a replaced word is not a transcription slip of the same sound
)
_UNIDADES = {
    w: i
    for i, w in enumerate(
        ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
    )
}
_DECENAS = {
    w: (i + 2) * 10
    for i, w in enumerate(
        ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    )
}
_ESCALAS = {
    "hundred": 100,
    "thousand": 10**3,
    "million": 10**6,
    "billion": 10**9,
    "trillion": 10**12,
}
NUMERICAS = (
    set(_UNIDADES)
    | set(_DECENAS)
    | set(_ESCALAS)
    | {"oh", "o", "percent", "dollars", "dollar", "cents"}
)
PARECIDO_NUMERO = 0.7  # "four oh" heard as "for a" (0.73) is a slip; "oh" heard as "hundred" (0.15) is the defect
_HOMOFONOS = {"for": "four", "to": "two", "too": "two", "won": "one", "ate": "eight"}
# never words of a figure on their own, and the same sound spelled two ways
_IGUALES = {"o": "oh", "okay": "ok", "per": "percent"}


def tokens(texto: str) -> list[str]:
    """Spoken words in lower case. Hyphens split: "four-oh-one-k" and "four oh one k" are the same audio."""
    t = (
        texto.lower()
        .replace("’", "'")
        .replace("-", " ")
        .replace("–", " ")
        .replace("—", " ")
    )
    return [
        _IGUALES.get(w, w)
        for w in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", t.replace(",", ""))
    ]


def valor(ws: list[str]) -> int | None:
    """Value of a run of number words; None if the run is not one number ("four oh one k" is not)."""
    total = actual = 0
    visto = False
    for w in ws:
        if w in ("dollars", "dollar", "percent", "and", "a"):
            continue
        if w.isdigit():
            actual += int(w)
        elif w in _UNIDADES:
            actual += _UNIDADES[w]
        elif w in _DECENAS:
            actual += _DECENAS[w]
        elif w == "hundred":
            actual = max(actual, 1) * 100
        elif w in _ESCALAS:
            total += max(actual, 1) * _ESCALAS[w]
            actual = 0
        else:
            return None
        visto = True
    return total + actual if visto else None


def _de_numero(a: list[str], b: list[str]) -> bool:
    return any(w in NUMERICAS or w.isdigit() for w in a + b)


def _parecido(a: list[str], b: list[str]) -> float:
    def f(ws: list[str]) -> str:
        return "".join(_HOMOFONOS.get(w, w) for w in ws)

    return difflib.SequenceMatcher(None, f(a), f(b)).ratio()


def _mismo_sonido(a: list[str], b: list[str]) -> bool:
    """Same audio written differently. A number word never gets the fuzzy pass: only an equal value does."""
    if _de_numero(a, b):
        va, vb = valor(a), valor(b)
        return (va is not None and va == vb) or [_HOMOFONOS.get(w, w) for w in a] == [_HOMOFONOS.get(w, w) for w in b]
    return _parecido(a, b) >= PARECIDO_MIN


def comparar(guion: str, oidas: list[dict]) -> dict:
    """Aligns script and heard words. `oidas` = [{word, start, end}]. Every difference comes with its second.

    grave: a number word differs, or 3+ words in a row are gone or are something else entirely (a dropped
    phrase). leve: one or two words that do not sound alike: Whisper also makes these on correct audio, so
    they are a reason to listen, not proof."""
    esp = tokens(guion)
    hechas = [(w, o) for o in oidas for w in tokens(o["word"])]
    oid = [w for w, _ in hechas]
    grave, leve = [], []
    sm = difflib.SequenceMatcher(None, esp, oid, autojunk=False)
    for op, i0, i1, j0, j1 in sm.get_opcodes():
        if op == "equal":
            continue
        a, b = esp[i0:i1], oid[j0:j1]
        if "".join(a) == "".join(b):
            continue
        if _mismo_sonido(a, b):
            continue
        ref = hechas[min(j0, len(hechas) - 1)][1] if hechas else {"start": 0}
        d = {
            "t": round(float(ref.get("start", 0)), 2),
            "guion": " ".join(a),
            "oido": " ".join(b),
        }
        nuevo_numero = any((w in NUMERICAS or w.isdigit()) and w not in a for w in b)
        grave_num = _de_numero(a, b) and (nuevo_numero or _parecido(a, b) < PARECIDO_NUMERO)
        (grave if grave_num or max(len(a), len(b)) >= 3 else leve).append(d)
    return {"grave": grave, "leve": leve, "n_guion": len(esp), "n_oidas": len(oid)}


def transcribir(audio: Path) -> list[dict]:
    from faster_whisper import WhisperModel

    m = WhisperModel(MODELO, device="cpu", compute_type="int8")
    tk = m.hf_tokenizer
    cifras = [
        i for i in range(tk.get_vocab_size()) if re.search(r"[0-9$%£€]", tk.decode([i]))
    ]
    segs, _ = m.transcribe(
        str(audio),
        language="en",
        beam_size=1,
        word_timestamps=True,
        condition_on_previous_text=False,
        suppress_tokens=[-1, *cifras],
    )
    return [
        {"word": w.word, "start": w.start, "end": w.end}
        for s in segs
        for w in s.words or []
    ]


def medir(proy: Path, mp4: Path, sb: dict | None = None) -> dict:
    sb = sb or json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    return comparar(" ".join(g["texto"] for g in sb["guion"]), transcribir(mp4))


def main() -> int:
    proy = Path(sys.argv[1])
    ref = proy.name
    mp4 = (
        Path(sys.argv[sys.argv.index("--mp4") + 1])
        if "--mp4" in sys.argv
        else proy / "renders" / f"{ref}-final.mp4"
    )
    r = medir(proy, mp4)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 1 if r["grave"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
