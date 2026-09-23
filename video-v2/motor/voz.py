"""Voz + tiempos medidos de un proyecto v2, desde su storyboard.json (no desde el motor v1).

    python video-v2/motor/voz.py video-v2/<proyecto> [--motor kokoro|piper] [--voz am_adam] [--forzar]

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
    if audio.exists() and "--forzar" not in sys.argv:
        raise SystemExit(f"{audio} ya existe. No se sobrescribe sola; usa --forzar si de verdad quieres regenerarla.")

    frases = frases_del_storyboard(sb)
    texto = " ".join(frases)
    print(f"Proyecto: {proy.name} · motor {motor} ({voz}) · {len(texto)} caracteres\nSintetizando…")
    muestras, sr = gv.sintetizar_kokoro(texto, voz) if motor == "kokoro" else gv.sintetizar_piper(texto, gv.VOZ_PIPER)
    audio.parent.mkdir(parents=True, exist_ok=True)
    gv.guardar(muestras, sr, audio)
    print(f"✓ {audio.name} ({len(muestras) / sr:.2f}s)\n")

    palabras = alinear_audio(audio, frases)
    (proy / "assets" / "words.json").write_text(json.dumps(
        [{"text": p["w"], "start": round(p["t0"], 3), "end": round(p["t1"], 3)} for p in palabras]), encoding="utf-8")
    print("✓ words.json")


if __name__ == "__main__":
    main()
