"""Mitad DETERMINISTA de la producción: de storyboard.json validado a MP4 con QA, sin juicio humano.

    python video-v2/motor/producir.py video-v2/<proyecto>

Encadena (cada paso es una puerta: si falla, se para y sale con código 1):
  1. construir --validar          storyboard correcto (anclas, catálogo, fuentes, aviso)
  2. voz.py                       solo si falta assets/voice.mp3 (voz + words.json medidos)
  3. construir                    imágenes, música, HTML, ducking
  4. hyperframes lint             0 errores
  5. render                       H.264+AAC 1080x1920
  6. loudnorm -> medir_loudness   -14 ±1 LUFS, pico < -1 dBTP
  7. medir_ritmo --max 2.5        el cuadro nunca muerto más de 2,5 s
  8. preview <30 MB + publish_<ref>.json (PRIVADO) + adn.json
  9. si hay token de YouTube: sube el MP4 como PRIVADO (borrador; `--sin-subir` lo evita)
Escribe `renders/qa.json` con cada puerta. NO publica: aprobar = `python -m omega.cli programar <ref>`
(hora pico de EE. UU.) — publicar exige una persona (política del canal).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parent
RAIZ = MOTOR.parents[1]
HF = "hyperframes@0.8.62"
PY = sys.executable


def _run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env={**os.environ, **(env or {})})


def _entorno() -> dict:
    out = _run(["bash", str(RAIZ / "tools" / "setup_nube.sh"), "--env"]).stdout
    return dict(re.findall(r"export (\w+)=(\S+)", out))


def descripcion(sb: dict, proy: Path) -> str:
    """Descripción para YouTube: la del storyboard + aviso YMYL + fuentes + créditos de imagen
    (CC BY los EXIGE; PD se cita igual). Función pura salvo la lectura de creditos.json."""
    pub = sb.get("publicacion") or {}
    partes = [pub.get("descripcion", "").strip()]
    if (sb.get("aviso") or {}).get("lineas"):
        partes.append(" · ".join(sb["aviso"]["lineas"]))
    fuentes = [c["fuente"] for c in sb.get("cifras") or [] if c.get("fuente")]
    if fuentes:
        partes.append("Sources:\n" + "\n".join(f"- {u}" for u in dict.fromkeys(fuentes)))
    cred = proy / "assets" / "img" / "creditos.json"
    if cred.exists():
        sys.path.insert(0, str(RAIZ / "tools"))
        import imagenes_libres
        partes.append(imagenes_libres.texto_creditos(json.loads(cred.read_text(encoding="utf-8"))))
    hashtags = " ".join(pub.get("hashtags", []))
    if hashtags:
        partes.append(hashtags)
    return "\n\n".join(p for p in partes if p)[:5000]


def subir_borrador(publish: dict, ref: str) -> str:
    """Sube el MP4 final a YouTube como PRIVADO (no es publicar: nadie lo ve) para que no se pierda
    si el contenedor se recicla antes de la aprobación. Aprobar = `omega.cli programar <ref>`.
    Sin token o con --sin-subir se salta; un fallo aquí NO invalida el QA (el vídeo es bueno)."""
    if "--sin-subir" in sys.argv:
        return "omitido (--sin-subir)"
    if not (RAIZ / "data" / "youtube_token.json").exists():
        return "omitido: no hay data/youtube_token.json (YOUTUBE_TOKEN_JSON en el entorno)"
    sys.path.insert(0, str(RAIZ))
    from omega import publish as pub
    try:
        res = pub.upload_video(Path(publish["video_path"]), publish["title"], publish["description"],
                               tags=publish["tags"], privacy_status="private")
    except Exception as e:                       # noqa: BLE001 - se reporta, no se aborta el QA
        return f"FALLÓ: {e}"
    publish["video_id"] = res["video_id"]
    (RAIZ / "data" / f"publish_{ref}.json").write_text(json.dumps(publish, ensure_ascii=False, indent=2), encoding="utf-8")
    try:                                         # a la BASE: viaja al repo de estado (sesión de mañana)
        from omega.cli import _registrar_video
        _registrar_video(ref, res["video_id"])
    except Exception as e:                       # noqa: BLE001
        return f"privado en {res['url']} · ⚠ no quedó en la base ({e}): vincular {ref} {res['video_id']}"
    return f"privado en {res['url']} · aprobar: python -m omega.cli programar {ref}"


def producir(proy: Path) -> dict:
    proy = proy.resolve()
    sb = json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    ref = sb.get("ref") or proy.name
    env = _entorno()
    qa: dict = {"ref": ref, "puertas": []}
    renders = proy / "renders"
    renders.mkdir(exist_ok=True)

    def puerta(nombre: str, ok: bool, detalle: str) -> None:
        qa["puertas"].append({"puerta": nombre, "ok": ok, "detalle": detalle.strip()[-600:]})
        print(f"{'✓' if ok else '✗'} {nombre}: {detalle.strip().splitlines()[-1] if detalle.strip() else ''}")
        (renders / "qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
        if not ok:
            raise SystemExit(f"✗ puerta '{nombre}' fallida — ver {renders / 'qa.json'}")

    r = _run([PY, str(MOTOR / "construir.py"), str(proy), "--validar"])
    puerta("storyboard", r.returncode == 0, r.stdout + r.stderr)
    if not (proy / "assets" / "voice.mp3").exists():
        r = _run([PY, str(MOTOR / "voz.py"), str(proy)])
        puerta("voz", r.returncode == 0, r.stdout + r.stderr)
    r = _run([PY, str(MOTOR / "construir.py"), str(proy)], env=env)
    puerta("build", r.returncode == 0 and "carve (ducking)" in r.stdout, r.stdout + r.stderr)
    r = _run(["npx", "--yes", HF, "lint"], cwd=proy, env=env)
    m = re.search(r"(\d+) error\(s\)", r.stdout + r.stderr)
    puerta("lint", bool(m) and m.group(1) == "0", m.group(0) if m else r.stdout[-300:] + r.stderr[-300:])
    crudo, final, prev = renders / f"{ref}.mp4", renders / f"{ref}-final.mp4", renders / f"{ref}-preview.mp4"
    r = _run(["npx", "--yes", HF, "render", "--quality", "high", "--output", str(crudo)], cwd=proy, env=env)
    puerta("render", r.returncode == 0 and crudo.exists(), (re.findall(r"rendered in [^\n]+", r.stdout) or [r.stderr[-300:]])[0])
    r = _run(["ffmpeg", "-v", "error", "-y", "-i", str(crudo), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
              "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(final)])
    puerta("loudnorm", r.returncode == 0, r.stderr or "ok")
    r = _run([PY, str(RAIZ / "tools" / "medir_loudness.py"), str(final)])
    lufs = re.search(r"integrado\s*:\s*(-?[\d.]+)", r.stdout)
    pico = re.search(r"Pico real\s*:\s*(-?[\d.]+)", r.stdout)
    ok = bool(lufs and pico) and abs(float(lufs.group(1)) + 14) <= 1 and float(pico.group(1)) < -1
    puerta("loudness", ok, f"{lufs.group(1) if lufs else '?'} LUFS, pico {pico.group(1) if pico else '?'} dBTP")
    r = _run([PY, str(RAIZ / "tools" / "medir_ritmo.py"), str(final), "--max", "2.5"])
    puerta("ritmo", r.returncode == 0 and "✓" in r.stdout, r.stdout)
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(final), "-c:v", "libx264", "-preset", "slow", "-crf", "24",
          "-c:a", "copy", "-movflags", "+faststart", str(prev)])
    pub = sb.get("publicacion") or {}
    publish = {"production_ref": ref, "video_path": str(final), "title": pub.get("titulo", ref)[:100],
               "description": descripcion(sb, proy), "tags": pub.get("tags", []), "category_id": "27",
               "privacy_status": "private", "made_for_kids": False}
    (RAIZ / "data").mkdir(exist_ok=True)
    (RAIZ / "data" / f"publish_{ref}.json").write_text(json.dumps(publish, ensure_ascii=False, indent=2), encoding="utf-8")
    # El ADN se escribe solo si no existe: uno hecho a mano (técnica por bloque) vale más que este
    # genérico, y producir no debe destruir instrumentación (pasó en la 1ª prueba con el #7).
    if sb.get("adn") and not (proy / "adn.json").exists():
        W = json.loads((proy / "assets" / "words.json").read_text())
        dur = round(W[-1]["end"] + float(sb.get("cola_s", 3.0)))
        (proy / "adn.json").write_text(json.dumps({"production_ref": ref, **sb["adn"], "length_s": dur,
                                                   "blocks": [{"block": g["id"], "technique": "v2-storyboard"} for g in sb.get("guion", [])]},
                                                  ensure_ascii=False, indent=2), encoding="utf-8")
    qa["borrador_youtube"] = subir_borrador(publish, ref)
    qa.update(final=str(final), preview=str(prev), preview_mb=round(prev.stat().st_size / 2**20, 1) if prev.exists() else None)
    (renders / "qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ TODAS LAS PUERTAS OK · final {final.name} · preview {qa['preview_mb']} MB · data/publish_{ref}.json (privado)")
    print(f"  YouTube: {qa['borrador_youtube']}")
    return qa


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    producir(Path(sys.argv[1]))
