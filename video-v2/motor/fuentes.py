"""Figure-vs-source gate (F1 decision 5, docs/LONGFORM-PLAN.md): every number in `cifras[].dato` must be on the
page its `fuente` URL serves, within the precision the figure is stated in. A page that cannot be read blocks too:
an unchecked figure on a YMYL channel is not published. Pages are cached as text in data/fuentes/<sha1(url)>.txt;
a site that refuses scripts (SEC without a declared contact, Forbes: 403) needs another source, or its page text
saved there by hand from a browser.

Clauses marked as the channel's own work ("own calculation", "own illustration", "model", ...) are not looked up;
a parenthetical "(shown on screen as ...)" only explains the display and is ignored.

    python video-v2/motor/fuentes.py video-v2/<ref>
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CACHE = RAIZ / "data" / "fuentes"
APROX_TOL = (
    0.05  # "~", "about", "over"...: the figure is rounded by the writer, 5 % either way
)

MAG = {
    "%": 1,
    "percent": 1,
    "k": 1e3,
    "thousand": 1e3,
    "m": 1e6,
    "million": 1e6,
    "b": 1e9,
    "bn": 1e9,
    "billion": 1e9,
    "t": 1e12,
    "tn": 1e12,
    "trillion": 1e12,
}
RE_NUM = re.compile(
    r"(?<![\w.])[$€£]?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?"
    r"(?:\s*(%|percent\b|trillion\b|billion\b|million\b|thousand\b|tn\b|bn\b)|([TBMKk])\b)?",
    re.IGNORECASE,
)
RE_APROX = re.compile(
    r"(~|\babout|\bover|\bnearly|\baround|\broughly|\balmost|\bmore than)\s*$",
    re.IGNORECASE,
)
RE_PROPIA = re.compile(
    r"own (calculation|illustration|comparison)|\bmodel\b|illustrative", re.IGNORECASE
)
RE_PANTALLA = re.compile(r"\((?:shown )?on screen[^)]*\)", re.IGNORECASE)


def numeros(texto: str) -> list[dict]:
    """[{v: value, res: stated precision, aprox, txt}] of every number, magnitudes applied ($64.16B = 64.16e9)."""
    out = []
    for m in RE_NUM.finditer(texto):
        ent, dec, mag = (
            m.group(1).replace(",", ""),
            m.group(2) or "",
            (m.group(3) or m.group(4) or "").lower(),
        )
        k = MAG.get(mag, 1)
        out.append(
            {
                "v": float(f"{ent}.{dec}" if dec else ent) * k,
                "res": 10.0 ** -len(dec) * k,
                "aprox": bool(
                    RE_APROX.search(texto[max(0, m.start() - 12) : m.start()])
                ),
                "txt": m.group(0).strip(),
            }
        )
    return out


def numeros_a_verificar(dato: str) -> list[dict]:
    texto = RE_PANTALLA.sub("", dato)
    return [n for c in texto.split(";") if not RE_PROPIA.search(c) for n in numeros(c)]


def encontrada(n: dict, pagina: list[dict]) -> bool:
    tol = max(
        n["res"] / 2, APROX_TOL * abs(n["v"]) if n["aprox"] else 0.0
    ) + 1e-9 * abs(n["v"])
    return any(abs(p["v"] - n["v"]) <= tol for p in pagina)


def texto_de_html(h: str) -> str:
    h = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", h)
    t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", h))
    return re.sub(
        r"\s+", " ", t.replace(" ", " ").replace(" ", " ").replace(" ", " ")
    ).strip()


def _bajar(url: str) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; source-check/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        datos, tipo = r.read(), r.headers.get("Content-Type", "")
    if "pdf" in tipo or datos[:5] == b"%PDF-":
        import io

        from pypdf import PdfReader

        return " ".join(
            p.extract_text() or "" for p in PdfReader(io.BytesIO(datos)).pages
        )
    return datos.decode("utf-8", errors="replace")


def lector(
    cache: Path = CACHE, bajar: Callable[[str], str] = _bajar
) -> Callable[[str], str]:
    """url -> page text, cached on disk by URL hash (failures are not cached: the next run retries)."""

    def leer(url: str) -> str:
        f = cache / f"{hashlib.sha1(url.encode()).hexdigest()}.txt"
        if f.exists():
            return f.read_text(encoding="utf-8")
        t = texto_de_html(bajar(url))
        cache.mkdir(parents=True, exist_ok=True)
        f.write_text(t, encoding="utf-8")
        return t

    return leer


def revisar(cifras: list[dict], leer: Callable[[str], str]) -> list[str]:
    malos, paginas, caidas = [], {}, set()
    for c in cifras:
        url = c.get("fuente", "")
        if url not in paginas:
            try:
                paginas[url] = numeros(leer(url))
            except Exception as e:  # noqa: BLE001 -- any fetch/parse failure (urllib, pypdf) means not checked
                paginas[url] = e
        p = paginas[url]
        if isinstance(p, Exception):
            if url in caidas:
                continue
            caidas.add(url)
            malos.append(f"{url}: no se pudo leer ({type(p).__name__}: {str(p)[:80]})")
            continue
        faltan = [
            n["txt"]
            for n in numeros_a_verificar(c.get("dato", ""))
            if not encontrada(n, p)
        ]
        if faltan:
            malos.append(
                f"{c.get('dato', '')[:60]!r}: {', '.join(faltan)} no está en {url}"
            )
    return malos


def puerta_fuentes(proy: Path, publicados: list[str] | None = None) -> tuple[bool, str]:
    """Gate for producir.py: new videos only, like the script gate."""
    import guionista

    pub = guionista.refs_publicadas() if publicados is None else publicados
    if proy.name in pub or list((proy / "renders").glob("*-final.mp4")):
        return True, "exento: vídeo anterior a la puerta o ya publicado"
    sb = json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    cifras = sb.get("cifras") or []
    malos = revisar(cifras, lector())
    return not malos, " · ".join(
        malos
    ) or f"{len(cifras)} cifras encontradas en su fuente"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    ok, det = puerta_fuentes(Path(sys.argv[1]).resolve(), publicados=[])
    print(("✓ " if ok else "✗ ") + det)
    raise SystemExit(0 if ok else 1)
