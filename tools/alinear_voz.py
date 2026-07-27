"""Alineador de voz: pone TIEMPO REAL a cada palabra del guion.

    python tools/alinear_voz.py read-janitor

Por qué existe
--------------
El calibrador del motor REPARTE las palabras dentro de cada bloque de voz: mide dónde arranca y
acaba cada bloque (eso es exacto) pero dentro estima. Medido sobre el Short #7: 33 de 50 tarjetas
caían a tiempo y 13 llegaban 0,73 s TARDE — el "la voz va más rápida que los subtítulos". Los
tramos donde la voz no hace ninguna pausa no tienen nada que medir, así que la estimación es
irreducible por ese camino.

El .srt de CapCut lo resolvía, pero su plan gratuito solo deja exportarlo 2 veces al mes: inútil
para un canal. Esto hace lo mismo en local, gratis e ILIMITADO.

Cómo
----
1. `faster-whisper` (CTranslate2, sin PyTorch) transcribe el audio con timestamps por palabra.
2. Esa transcripción se alinea con el GUION REAL por programación dinámica (Needleman-Wunsch).
   No nos fiamos de lo que Whisper "entendió": solo de CUÁNDO lo oyó. El guion manda en el texto,
   el audio manda en el tiempo.
3. Sale `data/<voz>.align.json` con cada palabra del guion y su t0/t1 medidos.

El motor lo carga solo: al pulsar "Usar la voz del proyecto" busca el .align.json junto al MP3 y,
si está, usa esos tiempos en vez de estimar. Sin él, todo sigue funcionando como antes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MOTOR = RAIZ / "docs" / "guiones" / "short-renderer.html"
MODELO = "base.en"          # 74 MB. `small.en` (244 MB) afina poco más en una voz TTS limpia.


def guion_del_short(clave: str) -> tuple[str, list[str]]:
    """Saca del motor la voz y las frases del Short. La fuente de verdad del guion es el HTML."""
    html = MOTOR.read_text(encoding="utf-8")
    i = html.find(f"'{clave}': {{")
    if i < 0:
        raise SystemExit(f"No encuentro el Short '{clave}' en {MOTOR.name}")
    # hasta el arranque del siguiente Short (o el fin del objeto SHORTS)
    j = html.find("\n  '", i + 10)
    bloque = html[i: j if j > 0 else i + 40000]

    mvoz = re.search(r"voz:\s*'([^']+)'", bloque)
    if not mvoz:
        raise SystemExit(f"El Short '{clave}' no declara `voz`")

    textos = re.findall(r"texto:\s*\"([^\"]+)\"", bloque)
    if not textos:
        textos = re.findall(r"texto:\s*'([^']+)'", bloque)
    if not textos:
        raise SystemExit(f"No encuentro `guion.grupos[].texto` en '{clave}'")
    return mvoz.group(1), textos


def norm(p: str) -> str:
    return re.sub(r"[^a-z0-9']", "", p.lower())


def alinear(guion: list[str], oidas: list[dict]) -> list[dict]:
    """Needleman-Wunsch entre las palabras del GUION y las que Whisper oyó.

    Whisper se equivoca de palabra a veces, y el TTS puede comerse alguna: por eso no vale
    emparejar por índice. El alineamiento tolera sustituciones y huecos, y a una palabra del guion
    sin pareja se le interpola el tiempo entre sus vecinas emparejadas — que es lo mismo que hacía
    el motor, pero ahora solo para casos sueltos en vez de para tramos enteros.
    """
    n, m = len(guion), len(oidas)
    HUECO = -1.0
    # matriz de puntuación (n+1)x(m+1)
    D = [[0.0] * (m + 1) for _ in range(n + 1)]
    for a in range(1, n + 1):
        D[a][0] = D[a - 1][0] + HUECO
    for b in range(1, m + 1):
        D[0][b] = D[0][b - 1] + HUECO
    gn = [norm(p) for p in guion]
    on = [norm(o["word"]) for o in oidas]
    for a in range(1, n + 1):
        for b in range(1, m + 1):
            igual = 2.0 if gn[a - 1] == on[b - 1] else (
                0.5 if gn[a - 1] and on[b - 1] and (gn[a - 1][:3] == on[b - 1][:3]) else -1.0)
            D[a][b] = max(D[a - 1][b - 1] + igual, D[a - 1][b] + HUECO, D[a][b - 1] + HUECO)

    pares: dict[int, int] = {}
    a, b = n, m
    while a > 0 and b > 0:
        igual = 2.0 if gn[a - 1] == on[b - 1] else (
            0.5 if gn[a - 1] and on[b - 1] and (gn[a - 1][:3] == on[b - 1][:3]) else -1.0)
        if D[a][b] == D[a - 1][b - 1] + igual:
            pares[a - 1] = b - 1
            a, b = a - 1, b - 1
        elif D[a][b] == D[a - 1][b] + HUECO:
            a -= 1
        else:
            b -= 1

    salida: list[dict] = []
    for k, palabra in enumerate(guion):
        if k in pares:
            o = oidas[pares[k]]
            salida.append({"w": palabra, "t0": round(o["start"], 3), "t1": round(o["end"], 3),
                           "medido": True})
        else:
            salida.append({"w": palabra, "t0": None, "t1": None, "medido": False})

    # interpolar los huecos entre palabras medidas, y extrapolar en los extremos
    medidos = [i for i, x in enumerate(salida) if x["medido"]]
    if not medidos:
        raise SystemExit("Whisper no reconoció NADA que cuadre con el guion. ¿El MP3 es el correcto?")
    for i, x in enumerate(salida):
        if x["medido"]:
            continue
        izq = max((j for j in medidos if j < i), default=None)
        der = min((j for j in medidos if j > i), default=None)
        if izq is None:
            x["t0"], x["t1"] = salida[der]["t0"], salida[der]["t0"]
        elif der is None:
            x["t0"], x["t1"] = salida[izq]["t1"], salida[izq]["t1"]
        else:
            a0, b0 = salida[izq]["t1"], salida[der]["t0"]
            frac = (i - izq) / (der - izq)
            x["t0"] = round(a0 + (b0 - a0) * frac, 3)
            x["t1"] = round(a0 + (b0 - a0) * ((i + 1 - izq) / (der - izq)), 3)
    # monótono estricto (una palabra nunca empieza antes que la anterior)
    for i in range(1, len(salida)):
        if salida[i]["t0"] < salida[i - 1]["t0"]:
            salida[i]["t0"] = salida[i - 1]["t0"]
        salida[i - 1]["t1"] = min(salida[i - 1]["t1"], salida[i]["t0"])
    return salida


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    clave = sys.argv[1]
    voz, frases = guion_del_short(clave)
    mp3 = RAIZ / "data" / voz
    if not mp3.exists():
        raise SystemExit(f"No existe {mp3}")

    from faster_whisper import WhisperModel

    print(f"Short   : {clave}")
    print(f"Audio   : {mp3.name}")
    print(f"Modelo  : {MODELO} (se descarga la 1ª vez, ~74 MB)\n")

    modelo = WhisperModel(MODELO, device="cpu", compute_type="int8")
    segmentos, info = modelo.transcribe(str(mp3), word_timestamps=True, language="en",
                                        vad_filter=False)
    oidas: list[dict] = []
    for seg in segmentos:
        for w in (seg.words or []):
            oidas.append({"word": w.word.strip(), "start": w.start, "end": w.end})
    print(f"Whisper oyó {len(oidas)} palabras en {info.duration:.2f}s de audio.")

    guion = [p for f in frases for p in f.split()]
    print(f"El guion tiene {len(guion)}.\n")

    palabras = alinear(guion, oidas)
    medidas = sum(1 for p in palabras if p["medido"])
    pct = 100 * medidas / len(palabras)

    destino = mp3.with_suffix(".align.json")
    destino.write_text(json.dumps(
        {"voz": voz, "short": clave, "modelo": MODELO,
         "palabras": [{"w": p["w"], "t0": p["t0"], "t1": p["t1"], "m": p["medido"]} for p in palabras]},
        ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"✓ {destino.name}")
    print(f"  {medidas}/{len(palabras)} palabras con tiempo MEDIDO ({pct:.0f}%); el resto interpolado.")
    if pct < 80:
        print("  ⚠ Menos del 80% emparejado: revisa que el MP3 corresponda a ESTE guion.")
    print("\nAhora en el motor: «🎙 Usar la voz del proyecto» lo carga solo.")


if __name__ == "__main__":
    main()
