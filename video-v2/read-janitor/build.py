"""Genera index.html del Short #7 (Ronald Read) v2 a partir de los tiempos MEDIDOS de la voz.

    python build.py        # lee assets/words.json -> escribe index.html

Por qué un generador y no el HTML a mano
----------------------------------------
Las ventanas de escena (`data-start`/`data-duration`) tienen que ser LITERALES en el HTML (el
runtime las lee al cargar), y cada una nace de una palabra del guion: la escena cambia cuando la
voz empieza la frase. Escritas a mano, cada re-alineamiento de la voz obligaría a recalcular ~40
números. Aquí se referencian por ÍNDICE de palabra (`w(47)` = "Sixty" de "Sixty years later"), así
que mismo guion + voz nueva = `python tools/alinear_voz.py` + `python build.py` y listo.

El guion es EXACTAMENTE el del #7 publicado (SHORTS['read-janitor'] en short-renderer.html) y la
voz el mismo Kokoro am_adam: la única variable que cambia frente al #7 es el renderer (v1 -> v2).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

AQUI = Path(__file__).resolve().parent
WORDS = json.loads((AQUI / "assets" / "words.json").read_text())
END = 49.8


def w(i: int) -> float:
    return WORDS[i]["start"]


def e(i: int) -> float:
    return WORDS[i]["end"]


# ── ventanas de escena: (inicio, fin), ancladas a la palabra que abre cada frase ──────────────
S = {
    "gas":     (0.0,          w(4) - 0.02),
    "sweep":   (w(4) - 0.04,  w(7) - 0.10),
    "bratt":   (w(7) - 0.12,  w(9) - 0.06),
    "reveal":  (w(9) - 0.08,  w(15) - 0.12),
    "no":      (w(15) - 0.14, w(24) - 0.12),
    "habits":  (w(24) - 0.14, w(31) - 0.14),
    "certs":   (w(31) - 0.16, w(46) + 0.22),
    "coins3d": (w(46) + 0.20, w(61) - 0.12),
    "chart":   (w(61) - 0.14, w(70) - 0.12),
    "machine": (w(70) - 0.14, w(75) - 0.12),
    "nobody":  (w(75) - 0.14, w(80) - 0.14),
    "n95":     (w(80) - 0.16, w(96) - 0.12),
    "sell":    (w(96) - 0.14, w(102) - 0.12),
    "years":   (w(102) - 0.14, w(111) - 0.12),
    "rare":    (w(111) - 0.14, w(119) - 0.10),
    "need":    (w(119) - 0.12, w(125) - 0.10),
    "engine":  (w(125) - 0.12, w(133) - 0.10),
    "own":     (w(133) - 0.12, w(143) - 0.10),
    "cta":     (w(143) - 0.12, END),
}
# fotos de fondo (clip propio para que Studio las muestre en su pista)
PH = {
    "ph-gas":    ("t/gas3.jpg",   S["gas"][0],   S["gas"][1] + 0.04),
    "ph-sweep":  ("t/sweep.jpg",  S["sweep"][0], S["sweep"][1] + 0.04),
    "ph-bratt":  ("t/bratt1.jpg", S["bratt"][0], S["reveal"][0] + 0.35),
    "ph-no":     ("t/bratt2.jpg", S["no"][0],    S["no"][1] + 0.04),
    "ph-n95":    ("t/nyse.jpg",   S["n95"][0],   S["n95"][1] + 0.04),
    "ph-years":  ("t/bratt2.jpg", S["years"][0], S["years"][1] + 0.04),
    "ph-rare":   ("t/bratt1.jpg", S["rare"][0],  S["rare"][1] + 0.04),
    "ph-cta":    ("t/gas3.jpg",   w(148) - 0.3,  END),
}


def clip(nombre: str, pista: int) -> str:
    a, b = S[nombre]
    return f'data-start="{a:.3f}" data-duration="{b - a:.3f}" data-track-index="{pista}"'


def serie() -> list[tuple[float, float]]:
    """La curva ILUSTRATIVA del #7: $170/mes a 10 %/año nominal, capitalización mensual, 60 años
    ($8,007,457 -> se remata en la cifra redonda, igual que CFG.valorFinal). (años, $)."""
    r, v, out = 0.10 / 12, 0.0, [(0.0, 0.0)]
    for m in range(1, 60 * 12 + 1):
        v = v * (1 + r) + 170
        if m % 6 == 0:
            out.append((m / 12, v))
    k = 8_000_000 / out[-1][1]
    return [(a, v * k) for a, v in out]


def path_curva(W: float, H: float) -> tuple[str, str]:
    pts = serie()
    xy = [(a / 60 * W, H - v / 8_000_000 * H) for a, v in pts]
    linea = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    area = linea + f" L{W:.1f},{H:.1f} L0,{H:.1f} Z"
    return linea, area


LINEA, AREA = path_curva(860, 620)
PAGADO_Y = 620 - 122_400 / 8_000_000 * 620          # la línea de "lo que puso él"

sfx = []   # (id, archivo, t, vol)
for k, t in enumerate([S["sweep"][0], S["bratt"][0], S["no"][0], S["habits"][0], S["certs"][0],
                       S["chart"][0], S["n95"][0], S["years"][0], S["engine"][0], S["cta"][0]]):
    sfx.append((f"sfx-wh{k}", "whoosh.wav", t - 0.12, 0.38))
sfx += [("sfx-hit1", "impact.wav", w(14) - 0.02, 0.6), ("sfx-hit2", "impact.wav", w(50) - 0.02, 0.6),
        ("sfx-ding", "ding.wav", w(50), 0.55), ("sfx-hit3", "impact.wav", w(101), 0.5),
        ("sfx-hit4", "impact.wav", w(86), 0.4)]
AUDIO_SFX = "\n".join(
    f'      <audio id="{i}" src="assets/{f}" data-start="{t:.3f}" data-track-index="{21 + k}" data-volume="{v}"></audio>'
    for k, (i, f, t, v) in enumerate(sfx))

FOTOS = "\n".join(
    f'      <div id="{i}" class="clip ph" data-start="{a:.3f}" data-duration="{b - a:.3f}" data-track-index="{2 + k}">'
    f'<img id="{i}-img" src="assets/{src}" alt="" /><div class="shade"></div></div>'
    for k, (i, (src, a, b)) in enumerate(PH.items()))

HTML = (AQUI / "plantilla.tpl").read_text(encoding="utf-8")
reemplazos = {
    "__END__": f"{END}",
    "__WORDS__": json.dumps(WORDS),
    "__S__": json.dumps({k: [round(a, 3), round(b, 3)] for k, (a, b) in S.items()}),
    "__FOTOS__": FOTOS,
    "__AUDIO_SFX__": AUDIO_SFX,
    "__LINEA__": LINEA, "__AREA__": AREA, "__PAGADO_Y__": f"{PAGADO_Y:.1f}",
}
for nombre in S:
    reemplazos[f"__CLIP_{nombre}__"] = clip(nombre, 30 + list(S).index(nombre))
for k, v in reemplazos.items():
    HTML = HTML.replace(k, v)
sueltos = re.findall(r"__[A-Z][A-Za-z0-9_]*__", HTML)
assert not sueltos, f"placeholder sin resolver: {sueltos}"
(AQUI / "index.html").write_text(HTML, encoding="utf-8")
print(f"✓ index.html  {len(S)} escenas, {len(PH)} fotos, {len(sfx)} sfx, {END}s")

# Ducking: carve.mjs (skill hyperframes-audio) ESCRIBE el EQ dinámico de la música dentro de
# index.html. Como index.html se regenera aquí, carve tiene que correr DESPUÉS, siempre; si no, un
# rebuild deja la música peleando con la voz sin que nada lo avise.
#   HF_CARVE = ruta a carve.mjs   ·   HF_CORE = carpeta con node_modules/@hyperframes/core@0.8.62
carve = os.environ.get("HF_CARVE", str(Path.home() / ".claude/skills/hyperframes-audio/scripts/carve.mjs"))
core = os.environ.get("HF_CORE")
if Path(carve).exists() and core:
    r = subprocess.run(["node", carve, "--comp", str(AQUI / "index.html"), "--bed", "music-bed",
                        "--voice", "vo", "--core", core], capture_output=True, text=True)
    print(("✓ carve: " + r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else "✗ carve falló:\n" + r.stderr[-800:])
else:
    print("⚠ SIN ducking: define HF_CORE (npm i @hyperframes/core@0.8.62 en otra carpeta) y la skill "
          "hyperframes-audio (npx hyperframes skills update hyperframes-audio). La música pisará la voz.")
