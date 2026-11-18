"""Voz + tiempos medidos de un proyecto v2, desde su storyboard.json (no desde el motor v1).

    python video-v2/motor/voz.py video-v2/<proyecto> [--motor kokoro|piper] [--voz am_adam] [--forzar]
    python video-v2/motor/voz.py video-v2/<proyecto> --alinear      # solo realinea la voz existente

Sale con `assets/voice.mp3` + `assets/words.json` ({text,start,end} por palabra del GUION), que es
justo lo que necesita `construir.py`. Reutiliza sin duplicar: síntesis de `tools/generar_voz.py`
(Kokoro am_adam por defecto, la voz elegida a ciego el 30-jul) y alineamiento de
`tools/alinear_voz.py` (Whisper + programación dinámica + validación por energía).
No sobrescribe una voz existente sin --forzar: la de un Short ya revisado no se toca sola.
Una toma entera; cada frase con un silencio V1 dentro (regla del crítico) se re-sintetiza sola, hasta 3
intentos; si queda una pausa rota sin puntuación, sale con código 1 y dice qué frase reescribir.
"""

from __future__ import annotations

import itertools
import json
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ / "tools"), str(Path(__file__).resolve().parent)]
PAUSA_CAPITULO_S = 0.9  # long-form: silence before each chapter (F1 decision 7)
MAX_TOMAS = 3  # each extra take costs one synthesis + one alignment: measured in docs/CERO-ERRORES.md


def frases_del_storyboard(sb: dict) -> list[str]:
    guion = sb.get("guion") or []
    if not guion:
        raise SystemExit("storyboard sin `guion` ([{id, texto}])")
    return [g["texto"].strip() for g in guion]


def tomas(sb: dict) -> list:
    """Plan de síntesis por frase: [(texto, speed) | segundos de silencio]. `voz.cortes[id]` parte una
    frase e inserta silencio ("the lines", 0.7, "crossed."), que Kokoro no puede hacer solo: la
    puntuación añade como mucho 0,26 s (medido 3-nov). `voz.speed` = número o {id: número, "*": número}."""
    cfg = sb.get("voz") or {}
    sp = cfg.get("speed", 1.0)
    pausa = float(cfg.get("pausa_s", 0.3))
    capitulos = {c["desde"] for c in sb.get("capitulos") or []}
    out: list = []
    for k, g in enumerate(sb.get("guion") or []):
        v = (
            sp
            if isinstance(sp, (int, float))
            else sp.get(g.get("id"), sp.get("*", 1.0))
        )
        if k:
            out.append(PAUSA_CAPITULO_S if k in capitulos else pausa)
        for t in (cfg.get("cortes") or {}).get(g.get("id")) or [g["texto"].strip()]:
            out.append(float(t) if isinstance(t, (int, float)) else (t, float(v)))
    return out


def recortar(m, sr: int, umbral: float = 0.01, margen_s: float = 0.03):
    """Quita el silencio de relleno de Kokoro en los extremos de una toma."""
    import numpy as np

    i = np.flatnonzero(np.abs(m) > umbral)
    if not len(i):
        return m
    g = int(margen_s * sr)
    return m[max(0, i[0] - g) : i[-1] + g + 1]


def sintetizar_por_tomas(sb: dict, voz: str, gv):
    import numpy as np

    trozos, sr = [], 24000
    for t in tomas(sb):
        if isinstance(t, float):
            trozos.append(np.zeros(int(t * sr), dtype="float32"))
        else:
            m, sr = gv.sintetizar_kokoro(t[0], voz, t[1])
            trozos.append(recortar(m, sr))
    return np.concatenate(trozos), sr


def _a_words(palabras: list[dict]) -> list[dict]:
    return [
        {"text": p["w"], "start": round(p["t0"], 3), "end": round(p["t1"], 3)}
        for p in palabras
    ]


def pausas_rotas(words: list[dict]) -> list[dict]:
    """V1 over the aligned words: the same function the critic runs, here before anything is built."""
    import medir_voz
    import puertas_final as pf

    u = _v1()
    rv = medir_voz.medir(
        words, pausa_dentro=u["pausa_dentro_s"], pausa_entre=u["pausa_entre_s"]
    )
    return pf.pausas_sin_puntuacion(
        rv, [], u, lambda _c, _s, d, **k: {"detalle": d, **k}, lambda _t, _vs: None
    )


def _v1() -> dict:
    return json.loads(
        (Path(__file__).parent / "rubrica.json").read_text(encoding="utf-8")
    )["criterios"]["V1"]


def pausas_v1(words: list[dict]) -> list[dict]:
    """The pauses the critic flags as V1 (critico.revisar_voz): commas included, unlike `pausas_rotas`."""
    import medir_voz

    u = _v1()
    return medir_voz.medir(
        words, pausa_dentro=u["pausa_dentro_s"], pausa_entre=u["pausa_entre_s"]
    )["pausas"]


def silencios_internos(m, sr: int, min_s: float) -> list[tuple[float, float]]:
    """[(t, dur)] silences longer than `min_s` between the first and last voiced 20 ms frame of a clip.
    Threshold as tools/medir_voz.detector_voz: 5 % of the loudest frame or 2.5x the p10 floor."""
    import numpy as np

    w = int(0.02 * sr)
    x = np.asarray(m[: len(m) // w * w], dtype="float64").reshape(-1, w)
    rms = np.sqrt((x**2).mean(axis=1)) if len(x) else np.zeros(0)
    if not len(rms):
        return []
    voz = rms > max(float(rms.max()) * 0.05, float(np.percentile(rms, 10)) * 2.5)
    out, k = [], 0
    for on, grupo in itertools.groupby(voz):
        n = len(list(grupo))
        if not on and k and k + n < len(voz) and n * 0.02 > min_s:
            out.append((round(k * 0.02, 2), round(n * 0.02, 2)))
        k += n
    return out


def _rms_voz(m, sr: int) -> float:
    """RMS of the voiced 20 ms frames only: a long silence inside must not lower the level."""
    import numpy as np

    w = int(0.02 * sr)
    x = np.asarray(m[: len(m) // w * w], dtype="float64").reshape(-1, w)
    if not len(x):
        return 0.0
    rms = np.sqrt((x**2).mean(axis=1))
    on = rms > float(rms.max()) * 0.05
    return float(np.sqrt((x[on] ** 2).mean())) if on.any() else 0.0


def _tramos_guion(sb: dict) -> list[tuple[int, int, dict]]:
    """(first, last) word index of each `guion` sentence: aligned words come from the script, in order."""
    out, i = [], 0
    for g in sb["guion"]:
        n = len(g["texto"].split())
        out.append((i, i + n - 1, g))
        i += n
    return out


def reparar_frases(
    sb: dict, toma, palabras: list[dict], sintetizar_frase, alinear, n: int = MAX_TOMAS
) -> dict:
    """Kokoro is not deterministic: a silence inside a sentence (V1, 34 faults in ~12 videos) goes away by
    re-synthesizing THAT sentence, not the whole voice. Up to `n` tries per sentence, each measured on its own
    clip (no alignment); the best one replaces the sentence only if it is better than the original; one
    alignment at the end. `quedan` = the V1 pauses inside a sentence that are still there."""
    import numpy as np

    m, sr = toma
    lim = _v1()["pausa_dentro_s"]

    def dentro(ps: list[dict]) -> list[dict]:
        return [p for p in pausas_v1(_a_words(ps)) if p["tipo"] == "dentro"]

    rotas = dentro(palabras)
    if not rotas:
        return {"toma": toma, "palabras": palabras, "quedan": [], "rehechas": []}
    tramos, malas = _tramos_guion(sb), {}
    for p in rotas:
        i = next((k for k, w in enumerate(palabras) if round(w["t1"], 2) >= p["t"]), 0)
        t = next((t for t in tramos if t[0] <= i <= t[1]), tramos[-1])
        malas[t[0]] = t
    cortes, rehechas = (sb.get("voz") or {}).get("cortes") or {}, []
    for i0, i1, g in sorted(
        malas.values(), key=lambda t: -t[0]
    ):  # last first: earlier times stay valid
        if g.get("id") in cortes:  # an intended silence: re-synthesis cannot remove it
            continue
        i1 = min(i1, len(palabras) - 1)
        prev = palabras[i0 - 1]["t1"] if i0 else 0.0
        sig = palabras[i1 + 1]["t0"] if i1 + 1 < len(palabras) else len(m) / sr
        a = int(max(prev, palabras[i0]["t0"] - 0.03) * sr)  # never into the neighbour sentence
        b = min(len(m), int(min(sig, palabras[i1]["t1"] + 0.03) * sr))
        sil = silencios_internos(m[a:b], sr, lim)
        mejor = ((len(sil), sum(d for _, d in sil)), None)
        for k in range(n):
            x, sr2 = sintetizar_frase(g)
            if sr2 != sr:
                raise ValueError(
                    f"frase {g.get('id')}: {sr2} Hz, la toma es de {sr} Hz"
                )
            x = recortar(np.asarray(x, dtype="float32"), sr)
            sil = silencios_internos(x, sr, lim)
            clave = (len(sil), sum(d for _, d in sil))
            print(
                f"frase {g.get('id')} intento {k + 1}/{n}: {len(sil)} silencio(s) dentro"
            )
            if clave < mejor[0]:
                mejor = (clave, x)
            if not sil:
                break
        if mejor[1] is not None:
            x, seg = mejor[1], m[a:b]
            rx = _rms_voz(x, sr)
            x = x * (_rms_voz(seg, sr) / rx if rx else 1.0)  # same level, silences excluded
            m = np.concatenate([m[:a], x.astype(m.dtype), m[b:]])
            rehechas.append(g.get("id"))
    if rehechas:
        palabras = alinear((m, sr))
    return {
        "toma": (m, sr),
        "palabras": palabras,
        "quedan": dentro(palabras),
        "rehechas": rehechas,
    }


def mejor_toma(sintetizar, alinear, n: int = MAX_TOMAS) -> dict:
    """Kokoro is not deterministic between syntheses: a take with a broken pause may have a clean sibling.
    Stops at the first clean one; if none, the one with fewest and shortest broken pauses."""
    mejor = None
    for k in range(n):
        toma = sintetizar()
        palabras = alinear(toma)
        rotas = pausas_rotas(_a_words(palabras))
        print(f"toma {k + 1}/{n}: {len(rotas)} pausa(s) rota(s)")
        clave = (len(rotas), sum(r["t_fin"] - r["t"] for r in rotas))
        if mejor is None or clave < mejor["clave"]:
            mejor = {"clave": clave, "toma": toma, "palabras": palabras, "rotas": rotas}
        if not rotas:
            break
    return mejor


def frases_a_reescribir(sb: dict, palabras: list[dict], rotas: list[dict]) -> list[str]:
    """Each broken pause with the `guion` sentence it falls in: words come from the script, in order."""
    fin, por_palabra = 0, []
    for g in sb["guion"]:
        fin += len(g["texto"].split())
        por_palabra.append((fin, g))
    out = []
    for r in rotas:
        i = next((k for k, p in enumerate(palabras) if round(p["t1"], 2) >= r["t"]), 0)
        g = next((g for f, g in por_palabra if i < f), sb["guion"][-1])
        out.append(f'frase {g.get("id")} "{g["texto"].strip()}": {r["detalle"]}')
    return out


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    import generar_voz as gv
    from alinear_voz import alinear_audio

    proy = Path(sys.argv[1]).resolve()
    sb = json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    cfg = sb.get("voz") or {}
    motor = gv._valor_de("--motor") or cfg.get("motor", gv.MOTOR_DEFECTO)
    voz = (
        gv._valor_de("--voz")
        or cfg.get("voz")
        or (gv.VOZ_KOKORO_DEFECTO if motor == "kokoro" else None)
    )
    audio = proy / "assets" / "voice.mp3"
    if "--alinear" in sys.argv:  # solo realinear la voz que ya existe (no re-sintetiza)
        _escribir_words(proy, alinear_audio(audio, frases_del_storyboard(sb)))
        return
    if audio.exists() and "--forzar" not in sys.argv:
        raise SystemExit(
            f"{audio} ya existe. No se sobrescribe sola; usa --forzar si de verdad quieres regenerarla."
        )

    if motor == "kokoro":
        import puertas

        dudas = puertas.g2p_dudosas(
            sb, gv.PYTHON_KOKORO, RAIZ / "tools" / "_g2p_kokoro.py"
        )
        if dudas:
            raise SystemExit(
                "Pronunciación sin revisar, no se sintetiza:\n  - "
                + "\n  - ".join(dudas)
            )
    frases = frases_del_storyboard(sb)
    texto = " ".join(frases)
    print(
        f"Proyecto: {proy.name} · motor {motor} ({voz}) · {len(texto)} caracteres\nSintetizando…"
    )

    def sintetizar():
        if motor == "kokoro" and (
            cfg.get("speed")
            or cfg.get("cortes")
            or cfg.get("por_frase")
            or sb.get("capitulos")
        ):
            return sintetizar_por_tomas(sb, voz, gv)
        return (
            gv.sintetizar_kokoro(texto, voz)
            if motor == "kokoro"
            else gv.sintetizar_piper(texto, gv.VOZ_PIPER)
        )

    def alinear(toma):
        with tempfile.TemporaryDirectory() as d:
            prueba = Path(d) / "toma.mp3"
            gv.guardar(*toma, prueba)
            return alinear_audio(prueba, frases)

    def sintetizar_frase(g):
        if motor != "kokoro":
            return gv.sintetizar_piper(g["texto"].strip(), gv.VOZ_PIPER)
        return sintetizar_por_tomas({"guion": [g], "voz": cfg}, voz, gv)

    # one whole take, then only the sentences with a V1 silence inside are re-synthesized
    r = mejor_toma(sintetizar, alinear, n=1)
    rep = reparar_frases(sb, r["toma"], r["palabras"], sintetizar_frase, alinear)
    r = {
        "toma": rep["toma"],
        "palabras": rep["palabras"],
        "rotas": pausas_rotas(_a_words(rep["palabras"])),
    }
    if rep["rehechas"]:
        print(f"re-sintetizadas: frase(s) {', '.join(map(str, rep['rehechas']))}")
    for p in rep[
        "quedan"
    ]:  # after a comma: the critic reports it (media), it does not block
        print(f'⚠ V1 queda: silencio de {p["dur"]}s tras "{p["tras"]}" (t={p["t"]}s)')
    muestras, sr = r["toma"]
    audio.parent.mkdir(parents=True, exist_ok=True)
    gv.guardar(muestras, sr, audio)
    print(f"✓ {audio.name} ({len(muestras) / sr:.2f}s)\n")
    _escribir_words(proy, r["palabras"])
    if r["rotas"]:
        raise SystemExit(
            f"✗ {MAX_TOMAS} intentos por frase y sigue la pausa rota (queda la mejor). Reescribe:\n  - "
            + "\n  - ".join(frases_a_reescribir(sb, r["palabras"], r["rotas"]))
        )


def _escribir_words(proy: Path, palabras: list[dict]) -> None:
    (proy / "assets" / "words.json").write_text(
        json.dumps(_a_words(palabras)), encoding="utf-8"
    )
    print("✓ words.json")


if __name__ == "__main__":
    main()
