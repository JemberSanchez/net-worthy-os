"""The visual judgment as a checklist per scene: a vague `{"fallos": []}` no longer approves a video.

critico.preparar_juicio writes `checklist.json` next to the frames; `juicio.json` must answer every item in
`revision`. A "no" needs a matching failure in `fallos`. What this proves: every item got an answer on this
file. What it cannot prove: that the answer is right; the user's approval of the preview stays the last step.
"""

from __future__ import annotations

import json
from pathlib import Path

PREGUNTAS_ESCENA = {
    "imagen_es_la_palabra": "¿la imagen muestra lo que dice la voz en este tramo, sin plano viejo de otra frase?",
    "texto_completo": "¿los textos se leen enteros, sin cortar, sin pisarse y sin faltas?",
}


def checklist(sb: dict, plan: dict) -> dict:
    ws = plan.get("words") or []
    escenas = [
        {
            "escena": k,
            "t0": s["t0"],
            "t1": s["t1"],
            "tipo": s.get("tipo"),
            "voz": " ".join(
                w["text"]
                for w in ws
                if s["t0"] <= (w["start"] + w["end"]) / 2 < s["t1"]
            )[:90],
        }
        for k, s in enumerate(plan.get("escenas") or [])
    ]
    return {
        "escenas": escenas,
        "cifras": [
            {"i": i, "dato": c.get("dato", "")}
            for i, c in enumerate(sb.get("cifras") or [])
        ],
    }


def faltan(juicio: dict, lista: dict) -> list[str]:
    """What is unanswered. Empty = the judgment covers the whole video."""
    rev = juicio.get("revision") or {}
    fallos = juicio.get("fallos") or []
    esc = {x.get("escena"): x for x in rev.get("escenas") or []}
    cif = {x.get("i"): x for x in rev.get("cifras") or []}
    out = []
    for e in lista["escenas"]:
        r = esc.get(e["escena"])
        for clave in PREGUNTAS_ESCENA:
            if r is None or not isinstance(r.get(clave), bool):
                out.append(f"escena {e['escena']}: falta {clave}")
            elif r[clave] is False and not any(
                f.get("escena") == e["escena"] for f in fallos
            ):
                out.append(
                    f"escena {e['escena']}: {clave} = no, sin su fallo en `fallos`"
                )
    for c in lista["cifras"]:
        r = cif.get(c["i"])
        if r is None or not isinstance(r.get("coincide_con_fuente"), bool):
            out.append(f"cifra {c['i']}: falta coincide_con_fuente")
        elif r["coincide_con_fuente"] is False and not any(
            f.get("criterio") == "J3" for f in fallos
        ):
            out.append(f"cifra {c['i']}: no coincide, sin fallo J3 en `fallos`")
    return out


def juicio_completo(dir_ronda: Path) -> list[str]:
    """Reasons this round's judgment does not count. A round with no checklist predates this gate."""
    lista = dir_ronda / "checklist.json"
    j = dir_ronda / "juicio.json"
    if not lista.exists():
        return ["falta checklist.json: vuelve a correr el crítico"]
    if not j.exists():
        return ["falta juicio.json"]
    return faltan(
        json.loads(j.read_text(encoding="utf-8")),
        json.loads(lista.read_text(encoding="utf-8")),
    )


def texto_para_juicio(lista: dict) -> str:
    esc = "\n".join(
        f"- {e['escena']} `{e['tipo']}` {e['t0']:.1f}-{e['t1']:.1f}s: {e['voz']}"
        for e in lista["escenas"]
    )
    preg = "\n".join(f"- `{k}`: {v}" for k, v in PREGUNTAS_ESCENA.items())
    return (
        "## Checklist obligatorio (sin todas las respuestas no se puede publicar)\n"
        'En `juicio.json`, además de `fallos`: `"revision": {"escenas": [{"escena": N, '
        + ", ".join(f'"{k}": true|false' for k in PREGUNTAS_ESCENA)
        + '}], "cifras": [{"i": N, "coincide_con_fuente": true|false}]}`. '
        "Un false lleva su fallo en `fallos`. Para `coincide_con_fuente` abre la fuente: ningún medidor lo comprueba.\n"
        f"{preg}\n\n{esc}\n"
    )
