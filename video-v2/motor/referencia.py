"""Distancia de un guion a la REFERENCIA DEL NICHO (bloque 3.1 del PLAN, métrica (b) de POLITICA).

    python video-v2/motor/referencia.py <guion.json>[#id_estructura] ...

`guion.json`: un storyboard / guion_plantilla ({"guion": [{texto}]}) o un guiones.json
(`#contraste` elige la estructura). Referencia: research/referencia_nicho.json.

Distancia por rasgo = |2·percentil − 1| dentro de la referencia: 0 en la mediana, 1 fuera del rango.
Solo se compara lo que la referencia mide. Hoy es la DURACIÓN (la API no da transcripción: ver
research/referencia_nicho.py); G-CIFRA/G-GIRO/G-BUCLE siguen con umbral heurístico, sin calibrar.
PROVISIONAL: n=30, muestra por búsqueda con ruido (anuncios, canales de otros mercados).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guionista as G

REF = Path(__file__).resolve().parents[2] / "research" / "referencia_nicho.json"


def cargar(ruta: Path = REF) -> list[dict]:
    return json.loads(ruta.read_text(encoding="utf-8"))["shorts"]


def percentil(x: float, valores: list[float]) -> float:
    """Rango medio: fracción por debajo + la mitad de los empates (0..1)."""
    menos = sum(v < x for v in valores)
    iguales = sum(v == x for v in valores)
    return (menos + iguales / 2) / len(valores)


def cuartiles(valores: list[float]) -> tuple[float, float]:
    v = sorted(valores)
    q = lambda p: v[round(p * (len(v) - 1))]
    return q(0.25), q(0.75)


def _textos(frases: list) -> list[str]:
    return [f["texto"] if isinstance(f, dict) else f for f in frases]


def distancia(frases: list, ref: list[dict]) -> dict:
    palabras = sum(len(t.split()) for t in _textos(frases))
    dur = palabras / G.PALABRAS_POR_S
    durs = [r["dur_s"] for r in ref]
    p = percentil(dur, durs)
    rasgos = {
        "dur_s": {
            "valor": round(dur, 1),
            "percentil": round(p, 2),
            "distancia": round(abs(2 * p - 1), 2),
        }
    }
    return {
        "palabras": palabras,
        "rasgos": rasgos,
        "distancia": round(
            sum(r["distancia"] for r in rasgos.values()) / len(rasgos), 2
        ),
    }


def puertas_calibradas(frases: list, ref: list[dict]) -> list[dict]:
    """Las puertas del guionista; G-LARGO pasa a usar el rango p25-p75 de la referencia."""
    lo, hi = (round(s * G.PALABRAS_POR_S) for s in cuartiles([r["dur_s"] for r in ref]))
    total = sum(len(t.split()) for t in _textos(frases))
    out = []
    for p in G.puertas(frases):
        if p["id"] == "G-LARGO":
            p = {
                "id": "G-LARGO",
                "ok": lo <= total <= hi,
                "calibrada": True,
                "detalle": f"{total} palabras (referencia p25-p75: {lo}-{hi})",
            }
        else:
            p = {**p, "calibrada": False}
        out.append(p)
    return out


def leer_guion(arg: str) -> list:
    ruta, _, est = arg.partition("#")
    d = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if est:
        return next(e["frases"] for e in d["estructuras"] if e["id"] == est)
    return d["guion"]


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ref = cargar()
    lo, hi = cuartiles([r["dur_s"] for r in ref])
    print(f"referencia: n={len(ref)}, duración p25-p75 {lo}-{hi} s")
    for arg in sys.argv[1:]:
        frases = leer_guion(arg)
        d = distancia(frases, ref)
        r = d["rasgos"]["dur_s"]
        fallos = [p["id"] for p in puertas_calibradas(frases, ref) if not p["ok"]]
        print(
            f"{arg}: distancia {d['distancia']} | {d['palabras']} palabras ≈ {r['valor']} s, "
            f"percentil {r['percentil']} | puertas fallidas: {', '.join(fallos) or '—'}"
        )


if __name__ == "__main__":
    main()
