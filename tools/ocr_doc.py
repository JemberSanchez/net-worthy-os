"""Dónde está una FRASE dentro de un documento real (periódico, certificado) -> caja para subrayarla.

    python tools/ocr_doc.py <imagen> "<frase>"

Por qué: el movimiento de documental que más "pesa" es enseñar la PRUEBA — la cámara entra en el
periódico de 1929 hasta "BILLIONS LOST AS STOCKS CRASH" y un subrayador lo marca mientras la voz
dice "collapse". Eso no se puede hacer a ojo en cada vídeo: el OCR da la caja exacta.

Motor: RapidOCR (ONNX, Apache-2.0, CPU). Por TIRAS horizontales solapadas: a imagen completa el
detector reduce el periódico (1920x2541) y se salta el titular grande (medido 1-oct); por tiras
de 520 px lo lee con confianza 0,96. Las líneas se cachean en <imagen>.ocr.json (OCR = segundos).
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

TIRA, SOLAPE = 520, 140
CONF_MIN = 0.6


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def lineas(img: Path) -> list[dict]:
    """Todas las líneas del documento [{texto, conf, caja:[x0,y0,x1,y1] px}], cacheadas junto a la imagen."""
    cache = img.with_suffix(".ocr.json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))["lineas"]
    from PIL import Image
    from rapidocr_onnxruntime import RapidOCR
    import numpy as np
    motor = RapidOCR()
    im = Image.open(img).convert("RGB")
    W, H = im.size
    out: list[dict] = []
    y = 0
    while True:
        y1 = min(H, y + TIRA)
        res, _ = motor(np.asarray(im.crop((0, y, W, y1))))
        for caja, texto, conf in res or []:
            xs, ys = [p[0] for p in caja], [p[1] + y for p in caja]
            c = [round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys))]
            # misma línea vista en dos tiras: se queda la de más confianza
            dup = next((o for o in out if _norm(o["texto"]) == _norm(texto) and abs(o["caja"][1] - c[1]) < 30), None)
            if dup is None:
                out.append({"texto": texto, "conf": round(float(conf), 3), "caja": c})
            elif conf > dup["conf"]:
                dup.update(conf=round(float(conf), 3), caja=c)
        if y1 >= H:
            break
        y = y1 - SOLAPE
    cache.write_text(json.dumps({"tam": [W, H], "lineas": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def buscar(img: Path, frase: str, lin: list[dict] | None = None) -> dict | None:
    """La caja (px) que cubre `frase` (sin distinguir mayúsculas ni puntuación). Si la frase es parte
    de una línea, la caja se recorta a sus caracteres (proporcional: los titulares van en caja fija).
    Devuelve {caja, texto, conf, parecido} o None si nada se parece lo bastante."""
    q = _norm(frase)
    mejor = None
    for l in lin if lin is not None else lineas(img):
        t = _norm(l["texto"])
        if not t or l["conf"] < CONF_MIN:
            continue
        i = t.find(q)
        if i >= 0:
            p, ini = 1.0, i
        else:                                    # OCR con erratas: mejor ventana del largo de la frase
            p, ini = max((difflib.SequenceMatcher(None, t[k:k + len(q)], q).ratio(), k)
                         for k in range(max(1, len(t) - len(q) + 1)))
        fin = min(len(t), ini + len(q))
        if p < 0.8:
            continue
        x0, y0, x1, y1 = l["caja"]
        a, b = x0 + (x1 - x0) * ini / len(t), x0 + (x1 - x0) * fin / len(t)
        cand = {"caja": [round(a), y0, round(b), y1], "texto": l["texto"], "conf": l["conf"], "parecido": round(p, 3)}
        if mejor is None or (cand["parecido"], cand["caja"][3] - cand["caja"][1]) > (mejor["parecido"], mejor["caja"][3] - mejor["caja"][1]):
            mejor = cand
    return mejor


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    r = buscar(Path(sys.argv[1]), sys.argv[2])
    print(json.dumps(r, ensure_ascii=False) if r else "✗ no encontrada")


if __name__ == "__main__":
    main()
