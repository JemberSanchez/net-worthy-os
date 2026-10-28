"""Crítico de GUION (bloque 1.1 del PLAN): elige entre alternativas ANTES de renderizar nada.

    python video-v2/motor/guionista.py video-v2/<proyecto>            # elige y escribe el guion
    python video-v2/motor/guionista.py video-v2/<proyecto> --ciego    # + par A/B (texto + voz Kokoro)

Lee `<proyecto>/guiones.json`:
    {"estructuras": [{"id", "nombre", "frases": [{"id", "texto", "giro"?}]}],   # 2-3 completas
     "ganchos":     [{"id", "texto"}],                                          # 3-5, sustituyen la 1.ª frase
     "juicio":      {"<id candidato>": {"una_idea": 1-5, "bucle_abierto": 1-5, "giro": 1-5, "nota": ""}}}

Dos etapas: 1) gana una estructura; 2) gana un gancho sobre esa estructura (ids "estructura+gN").
Orden: primero las PUERTAS medibles (menos fallos gana), luego el juicio (lo que no se mide).
Si falta juicio de algún candidato, lo lista con sus puertas y sale con código 2: se rellena y se repite.
Sale con `guiones.md` (ganador + descartadas y por qué) y el `guion` del storyboard. PROVISIONAL:
umbrales sin calibrar con notas a ciegas del usuario (docs/RUBRICA.md).
"""

from __future__ import annotations

import itertools
import json
import random
import re
import sys
from pathlib import Path
from typing import NoReturn

RAIZ = Path(__file__).resolve().parents[2]

PALABRAS_MIN, PALABRAS_MAX = 85, 110  # producir.md: 85-110 palabras ≈ 27-35 s
PALABRAS_POR_S = 3.1  # medido 26-sep con Kokoro: 85 palabras = 27,5 s
HUECO_GIRO_MAX_S = 10.0  # re-gancho cada ~8-10 s
CRITERIOS = ("una_idea", "bucle_abierto", "giro")

NUMEROS = {
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
    "hundred",
    "thousand",
    "million",
    "billion",
    "trillion",
    "percent",
    "half",
    "double",
    "triple",
}
RELLENO = (
    "so basically",
    "basically",
    "you see",
    "let me tell you",
    "in this video",
    "today we",
    "actually",
    "literally",
    "kind of",
    "sort of",
    "you know",
)
GIROS = (
    "here's",
    "nobody",
    "but",
    "instead",
    "that's not",
    "the catch",
    "turns out",
    "except",
    "until",
)
VACIAS = {
    "this",
    "that",
    "what",
    "they",
    "them",
    "with",
    "have",
    "from",
    "your",
    "will",
    "would",
    "there",
    "their",
    "then",
    "than",
    "just",
    "into",
    "about",
    "were",
    "been",
    "when",
    "which",
    "think",
    "does",
    "these",
    "those",
    "only",
    "some",
    "more",
    "most",
    "very",
    "here",
    "it's",
    "that's",
    "here's",
}


class FaltaJuicio(Exception):
    def __init__(self, faltan: list[str]):
        super().__init__(f"falta juicio de: {', '.join(faltan)}")
        self.faltan = faltan


def _tokens(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9$%.']+(?:-[a-z0-9]+)*", texto.lower())


def tiene_cifra(texto: str) -> bool:
    if re.search(r"\d", texto):
        return True
    return any(p in NUMEROS for t in _tokens(texto) for p in t.split("-"))


def _contiene(texto: str, frase: str) -> bool:
    return (
        re.search(rf"(?<![a-z']){re.escape(frase)}(?![a-z'])", texto.lower())
        is not None
    )


def _es_giro(f: dict) -> bool:
    return (
        bool(f.get("giro"))
        or tiene_cifra(f["texto"])
        or any(_contiene(f["texto"], g) for g in GIROS)
    )


def _raiz(t: str) -> str:
    t = t.strip(".'")
    return t[:-1] if len(t) > 4 and t.endswith("s") else t


def _contenido(texto: str) -> set[str]:
    return {
        _raiz(t)
        for t in _tokens(texto)
        if len(t) >= 4 and t not in VACIAS and not tiene_cifra(t)
    }


def puertas(frases: list) -> list[dict]:
    """Criterios que se miden sin juicio. `frases`: textos o dicts {texto, giro?}."""
    fs = [f if isinstance(f, dict) else {"texto": f} for f in frases]
    n = [len(f["texto"].split()) for f in fs]
    total = sum(n)
    out = []

    out.append(
        {
            "id": "G-CIFRA",
            "ok": tiene_cifra(fs[0]["texto"]),
            "detalle": "cifra en la 1.ª frase"
            if tiene_cifra(fs[0]["texto"])
            else "la 1.ª frase no tiene cifra",
        }
    )
    out.append(
        {
            "id": "G-LARGO",
            "ok": PALABRAS_MIN <= total <= PALABRAS_MAX,
            "detalle": f"{total} palabras ({PALABRAS_MIN}-{PALABRAS_MAX}) ≈ {total / PALABRAS_POR_S:.1f} s",
        }
    )

    hallado = sorted({r for f in fs for r in RELLENO if _contiene(f["texto"], r)})
    out.append(
        {
            "id": "G-RELLENO",
            "ok": not hallado,
            "detalle": ", ".join(hallado) or "sin relleno",
        }
    )

    # inicio estimado de cada frase giro (la 1.ª siempre cuenta: es el gancho) + el final del guion
    marcas, acum = [], 0
    for i, f in enumerate(fs):
        if i == 0 or _es_giro(f):
            marcas.append(acum / PALABRAS_POR_S)
        acum += n[i]
    marcas.append(total / PALABRAS_POR_S)
    huecos = [b - a for a, b in itertools.pairwise(marcas)]
    peor = max(huecos, default=0.0)
    out.append(
        {
            "id": "G-GIRO",
            "ok": peor <= HUECO_GIRO_MAX_S,
            "detalle": f"hueco máx. sin giro {peor:.1f} s (≤{HUECO_GIRO_MAX_S:.0f} s)",
        }
    )

    comun = (
        sorted(_contenido(fs[0]["texto"]) & _contenido(fs[-1]["texto"]))
        if len(fs) > 1
        else []
    )
    out.append(
        {
            "id": "G-BUCLE",
            "ok": bool(comun),
            "detalle": f"enlaza por: {', '.join(comun)}"
            if comun
            else "la última frase no retoma la primera",
        }
    )
    return out


def candidatos_gancho(estructura: dict, ganchos: list[dict]) -> list[dict]:
    """La estructura tal cual + una variante por gancho (sustituye la 1.ª frase). No muta la entrada."""
    out = [{"id": estructura["id"], "frases": [dict(f) for f in estructura["frases"]]}]
    for g in ganchos:
        frases = [dict(f) for f in estructura["frases"]]
        frases[0] = {**frases[0], "texto": g["texto"]}
        out.append({"id": f"{estructura['id']}+{g['id']}", "frases": frases})
    return out


def _nota(j: dict) -> int:
    for c in CRITERIOS:
        if not isinstance(j.get(c), int) or not 1 <= j[c] <= 5:
            raise ValueError(f"juicio.{c} debe ser un entero 1-5 (es {j.get(c)!r})")
    return sum(j[c] for c in CRITERIOS)


def elegir(cands: list[dict], juicio: dict) -> tuple[dict, list[dict]]:
    """Menos fallos de puerta primero; a igualdad, más juicio. Cada candidato: {id, fallos, ...}."""
    faltan = [c["id"] for c in cands if c["id"] not in juicio]
    if faltan:
        raise FaltaJuicio(faltan)
    ranking = sorted(cands, key=lambda c: (c["fallos"], -_nota(juicio[c["id"]])))
    return ranking[0], ranking


def evaluar(cands: list[dict]) -> list[dict]:
    for c in cands:
        c["puertas"] = puertas(c["frases"])
        c["fallos"] = sum(not p["ok"] for p in c["puertas"])
    return cands


def par_ciego(
    dir_: Path,
    plantilla: list[str],
    elegido: list[str],
    semilla: int | None = None,
    audio: bool = True,
) -> dict:
    """A/B sin etiquetas: A.txt/B.txt (+ A.mp3/B.mp3 con Kokoro). La correspondencia va en .clave.json."""
    dir_.mkdir(parents=True, exist_ok=True)
    lados = [("plantilla", plantilla), ("elegido", elegido)]
    random.Random(semilla).shuffle(lados)
    clave = {}
    for letra, (nombre, frases) in zip("AB", lados):
        clave[nombre] = letra
        (dir_ / f"{letra}.txt").write_text("\n".join(frases), encoding="utf-8")
        if audio:
            sys.path.insert(0, str(RAIZ / "tools"))
            import generar_voz as gv

            muestras, sr = gv.sintetizar_kokoro(" ".join(frases), gv.VOZ_KOKORO_DEFECTO)
            gv.guardar(muestras, sr, dir_ / f"{letra}.mp3")
    (dir_ / ".clave.json").write_text(json.dumps(clave), encoding="utf-8")
    return clave


def _fila(c: dict, juicio: dict) -> str:
    j = juicio.get(c["id"], {})
    fallan = ", ".join(p["id"] for p in c["puertas"] if not p["ok"]) or "—"
    nota = _nota(j) if j else "?"
    return (
        f"| `{c['id']}` | {c['fallos']} ({fallan}) | {nota}/15 | {j.get('nota', '')} |"
    )


def informe(etapas: list[tuple[str, list[dict]]], juicio: dict, ganador: dict) -> str:
    ls = [
        "# Guiones — crítico de guion (PROVISIONAL)",
        "",
        f"**Ganador:** `{ganador['id']}`",
        "",
        *[f"> {f['texto']}" for f in ganador["frases"]],
        "",
    ]
    for titulo, ranking in etapas:
        ls += [
            f"## {titulo}",
            "",
            "| candidato | fallos de puerta | juicio | por qué |",
            "|---|---|---|---|",
            *[_fila(c, juicio) for c in ranking],
            "",
        ]
    ls += [
        "## Puertas del ganador",
        "",
        *[
            f"- {'✓' if p['ok'] else '✗'} {p['id']}: {p['detalle']}"
            for p in ganador["puertas"]
        ],
        "",
        "## Descartadas (texto completo)",
        "",
    ]
    vistos = {ganador["id"]}
    for _, ranking in etapas:
        for c in ranking:
            if c["id"] in vistos:
                continue
            vistos.add(c["id"])
            ls += [
                f"### `{c['id']}`",
                "",
                *[f"> {f['texto']}" for f in c["frases"]],
                "",
            ]
    return "\n".join(ls)


def _pedir_juicio(e: FaltaJuicio, cands: list[dict]) -> NoReturn:
    print(f"Falta juicio (1-5: {', '.join(CRITERIOS)}) en guiones.json para:")
    for c in cands:
        if c["id"] in e.faltan:
            print(f"\n- {c['id']}  ({c['fallos']} fallos de puerta)")
            for p in c["puertas"]:
                print(f"    {'✓' if p['ok'] else '✗'} {p['id']}: {p['detalle']}")
    raise SystemExit(2)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows en cp1252: ✓/✗/≈
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    proy = Path(sys.argv[1]).resolve()
    datos = json.loads((proy / "guiones.json").read_text(encoding="utf-8"))
    juicio = datos.get("juicio") or {}

    ests = evaluar(
        [{"id": e["id"], "frases": e["frases"]} for e in datos["estructuras"]]
    )
    try:
        mejor_est, rank1 = elegir(ests, juicio)
    except FaltaJuicio as e:
        _pedir_juicio(e, ests)
    est = next(e for e in datos["estructuras"] if e["id"] == mejor_est["id"])
    variantes = evaluar(candidatos_gancho(est, datos.get("ganchos") or []))
    try:
        ganador, rank2 = elegir(variantes, juicio)
    except FaltaJuicio as e:
        _pedir_juicio(e, variantes)

    (proy / "guiones.md").write_text(
        informe(
            [
                ("Etapa 1 — estructura", rank1),
                (f"Etapa 2 — gancho sobre `{est['id']}`", rank2),
            ],
            juicio,
            ganador,
        ),
        encoding="utf-8",
    )
    sb_ruta = proy / "storyboard.json"
    sb: dict = (
        json.loads(sb_ruta.read_text(encoding="utf-8"))
        if sb_ruta.exists()
        else {"ref": proy.name}
    )
    sb["guion"] = [{"id": f["id"], "texto": f["texto"]} for f in ganador["frases"]]
    sb_ruta.write_text(
        json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"✓ ganador {ganador['id']} ({ganador['fallos']} fallos de puerta) → {sb_ruta.name}, guiones.md"
    )

    if "--ciego" in sys.argv:
        base = json.loads((proy / "guion_plantilla.json").read_text(encoding="utf-8"))[
            "guion"
        ]
        par_ciego(
            proy / "renders" / "ciego",
            [f["texto"] for f in base],
            [f["texto"] for f in ganador["frases"]],
        )
        print(
            "✓ par ciego en renders/ciego/ (A/B .txt + .mp3; la clave en .clave.json, no la abras)"
        )


if __name__ == "__main__":
    main()
