"""Storyboard -> quick preview in ONE background command, printing only what needs a decision.

    python video-v2/motor/cadena.py video-v2/<ref>      # run_in_background

1. Contact sheets the cloud queue already made (data/.estado/cola/medios, matched by clip source) are
   copied next to the clips, so `lote` skips their OCR.
2. voz.py (only if voice.mp3 is missing) and `broll.py lote` run AT THE SAME TIME: they share nothing.
3. Clips without `"visto": true` -> prints their sheet and OCR text and stops (exit 2): look, set
   `visto`, run again (voice and clips are cached, so the second run goes straight to step 4).
4. producir.py --auto --rapido (already prints only failures).
Replaces the probing turns between those steps (sondeo = 11.1 min median per session, 20-nov).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MOTOR = Path(__file__).resolve().parent
RAIZ = MOTOR.parents[1]
sys.path.insert(0, str(RAIZ))
PY = sys.executable


def _run(args: list[str]) -> tuple[int, str]:
    r = subprocess.run(
        [PY, *args],
        cwd=RAIZ,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return r.returncode, (r.stdout + r.stderr).strip()


def avisos(salida: str) -> str:
    """Only the lines a person acts on: ✗/⚠ and the list under them."""
    return "\n".join(
        x
        for x in salida.splitlines()
        if x.lstrip().startswith(("✗", "⚠", "- ", "Pronunciación"))
    )


def copiar_hojas(proy: Path, decl: dict, medios: Path) -> list[str]:
    from omega import cola

    carpeta = proy / "assets" / "clips"
    hechas = []
    for k, hoja in cola.hojas_previas(decl, medios).items():
        if not (carpeta / f"{k}.hoja.jpg").exists():
            carpeta.mkdir(parents=True, exist_ok=True)
            shutil.copy2(hoja, carpeta / f"{k}.hoja.jpg")
            shutil.copy2(hoja.with_suffix(".txt"), carpeta / f"{k}.hoja.txt")
            hechas.append(k)
    return hechas


def sin_ver(decl: dict) -> list[str]:
    return [k for k, v in decl.items() if v.get("visto") is not True]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    proy = Path(sys.argv[1]).resolve()
    decl = (
        json.loads((proy / "storyboard.json").read_text(encoding="utf-8")).get("clips")
        or {}
    )
    copiadas = copiar_hojas(proy, decl, RAIZ / "data" / ".estado" / "cola" / "medios")
    if copiadas:
        print(f"✓ hojas de la cola: {', '.join(copiadas)}")
    trabajos = {}
    with ThreadPoolExecutor(2) as ex:
        if not (proy / "assets" / "voice.mp3").exists():
            trabajos["voz"] = ex.submit(_run, [str(MOTOR / "voz.py"), str(proy)])
        if decl:
            trabajos["lote"] = ex.submit(
                _run, [str(RAIZ / "tools" / "broll.py"), "lote", str(proy)]
            )
    res = {k: f.result() for k, f in trabajos.items()}
    for k, (rc, salida) in res.items():
        if rc:
            print(f"✗ {k} (código {rc}):\n{avisos(salida) or salida[-1500:]}")
        elif avisos(salida):
            print(avisos(salida))
    if any(rc for rc, _ in res.values()):
        return 1
    faltan = sin_ver(decl)
    if faltan:
        lote = res.get("lote", (0, ""))[1].splitlines()
        print(
            'Mira estas hojas y pon `"visto": true` (sin caras, logos ni texto de otro país); luego repite:'
        )
        for k in faltan:
            print(f"  {proy / 'assets' / 'clips' / f'{k}.hoja.jpg'}")
            print(
                "    "
                + next(
                    (x for x in lote if x.startswith(f"✓ {k}:")), "(sin salida de lote)"
                ).split(" · ")[-1]
            )
        return 2
    rc, salida = _run([str(MOTOR / "producir.py"), str(proy), "--auto", "--rapido"])
    print(salida)
    return rc


if __name__ == "__main__":
    sys.exit(main())
