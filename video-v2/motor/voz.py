"""Voz + tiempos medidos de un proyecto v2, desde su storyboard.json (no desde el motor v1).

    python video-v2/motor/voz.py video-v2/<proyecto> [--motor kokoro|piper] [--voz am_adam] [--forzar]
    python video-v2/motor/voz.py video-v2/<proyecto> --alinear      # solo realinea la voz existente

Sale con `assets/voice.mp3` + `assets/words.json` ({text,start,end} por palabra del GUION), que es
justo lo que necesita `construir.py`. Reutiliza sin duplicar: síntesis de `tools/generar_voz.py`
(Kokoro am_adam por defecto, la voz elegida a ciego el 30-jul) y alineamiento de
`tools/alinear_voz.py` (Whisper + programación dinámica + validación por energía).
No sobrescribe una voz existente sin --forzar: la de un Short ya revisado no se toca sola.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "tools"))


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
    out: list = []
    for k, g in enumerate(sb.get("guion") or []):
        v = sp if isinstance(sp, (int, float)) else sp.get(g.get("id"), sp.get("*", 1.0))
        if k:
            out.append(pausa)
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
    return m[max(0, i[0] - g): i[-1] + g + 1]


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


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    import generar_voz as gv
    from alinear_voz import alinear_audio

    proy = Path(sys.argv[1]).resolve()
    sb = json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    cfg = sb.get("voz") or {}
    motor = gv._valor_de("--motor") or cfg.get("motor", gv.MOTOR_DEFECTO)
    voz = gv._valor_de("--voz") or cfg.get("voz") or (gv.VOZ_KOKORO_DEFECTO if motor == "kokoro" else None)
    audio = proy / "assets" / "voice.mp3"
    if "--alinear" in sys.argv:          # solo realinear la voz que ya existe (no re-sintetiza)
        _escribir_words(proy, alinear_audio(audio, frases_del_storyboard(sb)))
        return
    if audio.exists() and "--forzar" not in sys.argv:
        raise SystemExit(f"{audio} ya existe. No se sobrescribe sola; usa --forzar si de verdad quieres regenerarla.")

    if motor == "kokoro":
        import puertas

        dudas = puertas.g2p_dudosas(sb, gv.PYTHON_KOKORO, RAIZ / "tools" / "_g2p_kokoro.py")
        if dudas:
            raise SystemExit("Pronunciación sin revisar, no se sintetiza:\n  - " + "\n  - ".join(dudas))
    frases = frases_del_storyboard(sb)
    texto = " ".join(frases)
    print(f"Proyecto: {proy.name} · motor {motor} ({voz}) · {len(texto)} caracteres\nSintetizando…")
    if motor == "kokoro" and (cfg.get("speed") or cfg.get("cortes") or cfg.get("por_frase")):
        muestras, sr = sintetizar_por_tomas(sb, voz, gv)
    else:
        muestras, sr = gv.sintetizar_kokoro(texto, voz) if motor == "kokoro" else gv.sintetizar_piper(texto, gv.VOZ_PIPER)
    audio.parent.mkdir(parents=True, exist_ok=True)
    gv.guardar(muestras, sr, audio)
    print(f"✓ {audio.name} ({len(muestras) / sr:.2f}s)\n")

    _escribir_words(proy, alinear_audio(audio, frases))


def _escribir_words(proy: Path, palabras: list[dict]) -> None:
    (proy / "assets" / "words.json").write_text(json.dumps(
        [{"text": p["w"], "start": round(p["t0"], 3), "end": round(p["t1"], 3)} for p in palabras]), encoding="utf-8")
    print("✓ words.json")


if __name__ == "__main__":
    main()
