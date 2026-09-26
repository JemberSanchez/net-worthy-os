"""Páginas vivas: de cada Short, un CARRUSEL (Instagram/Facebook), una HISTORIA y los TEXTOS.

    python video-v2/motor/social.py video-v2/<proyecto>          # genera social/ (no publica nada)

Sale en `video-v2/<proyecto>/social/`:
    carrusel/01.jpg … NN.jpg   1080x1350 (4:5, lo que más ocupa en el feed), JPEG (Instagram lo exige)
    historia.mp4               1080x1920, el gancho REAL del Short + tarjeta final de marca
    textos.json                {caption_ig, caption_fb, alt}  (fuentes y aviso YMYL incluidos)

Por qué así (26-sep, el usuario: "páginas más vivas"):
  - Un carrusel es contenido NUEVO para la red (se guarda, se comparte, Instagram lo recomienda a
    no seguidores); una historia solo llega a quien ya sigue. Por eso el carrusel lleva el peso y
    la historia es reutilización barata del gancho.
  - Mismo sistema visual que el vídeo: se renderiza con HyperFrames (mismas fuentes, CSS y
    duotono/grado), no con una plantilla aparte que se vería "de otra marca".
  - Nada genérico: cada diapositiva va sobre una imagen REAL del proyecto (foto de archivo en
    duotono o fotograma del metraje con el grado de marca).

El contenido lo escribe quien hace el storyboard, en `social`:
    "social": {
      "carrusel": [{"fondo": "img:<clave>" | "clip:<clave>@<segundo>", "kicker": "...",
                    "titulo": "...", "texto": "..."}, ...],          # 3-10 diapositivas
      "caption": "texto del pie (sin hashtags ni fuentes: se añaden solos)",
      "historia": {"hasta": "<ancla frase:palabra$>", "cierre": "Full story in Reels"}
    }
"""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parent
RAIZ = MOTOR.parents[1]
sys.path.insert(0, str(MOTOR))
sys.path.insert(0, str(RAIZ / "tools"))
HF = "hyperframes@0.8.62"
W, H = 1080, 1350          # 4:5
MAX_SLIDES = 10            # límite de Instagram


class SocialError(ValueError):
    pass


def validar(sb: dict) -> list[str]:
    so = sb.get("social") or {}
    err, car = [], so.get("carrusel") or []
    if not 3 <= len(car) <= MAX_SLIDES:
        err.append(f"`social.carrusel` necesita 3-{MAX_SLIDES} diapositivas (hay {len(car)})")
    imgs, clips = set(sb.get("imagenes") or {}), set(sb.get("clips") or {})
    for k, d in enumerate(car):
        f = str(d.get("fondo", ""))
        tipo, _, ref = f.partition(":")
        ref = ref.split("@")[0]
        if tipo not in ("img", "clip") or not ref:
            err.append(f"diapositiva {k + 1}: `fondo` debe ser \"img:<clave>\" o \"clip:<clave>@<s>\" (es {f!r})")
        elif tipo == "img" and ref not in imgs:
            err.append(f"diapositiva {k + 1}: imagen {ref!r} no declarada en `imagenes`")
        elif tipo == "clip" and ref not in clips:
            err.append(f"diapositiva {k + 1}: clip {ref!r} no declarado en `clips`")
        if not d.get("titulo"):
            err.append(f"diapositiva {k + 1}: falta `titulo`")
        if len(d.get("texto", "")) > 170:
            err.append(f"diapositiva {k + 1}: `texto` de {len(d['texto'])} caracteres (máx. 170: se lee en 3 s)")
    if not so.get("caption"):
        err.append("falta `social.caption`")
    return err


def _t(s: str) -> str:
    """Texto seguro para HTML con *énfasis* dorado (misma convención que el vídeo)."""
    return re.sub(r"\*(.+?)\*", r'<span class="gold">\1</span>', html.escape(s or ""))


def captions(sb: dict) -> dict:
    """Pies de Instagram y Facebook: texto + aviso YMYL + fuentes + hashtags. Función pura."""
    so, pub = sb.get("social") or {}, sb.get("publicacion") or {}
    base = so["caption"].strip()
    aviso = " · ".join((sb.get("aviso") or {}).get("lineas", []))
    fuentes = list(dict.fromkeys(c["fuente"] for c in sb.get("cifras") or [] if c.get("fuente")))
    tags = " ".join(pub.get("hashtags", [])).replace("#shorts", "").split()
    ig = "\n\n".join(x for x in [base, aviso, "Sources: " + " · ".join(fuentes) if fuentes else "",
                                  "Follow @networthytv for one real money story a day.", " ".join(tags[:8])] if x)
    fb = "\n\n".join(x for x in [base, aviso, "Sources:\n" + "\n".join(f"- {u}" for u in fuentes) if fuentes else ""] if x)
    alt = " / ".join(d.get("titulo", "").replace("*", "") for d in so.get("carrusel", []))
    return {"caption_ig": ig[:2200], "caption_fb": fb, "alt": alt[:1000]}


def _fondo(proy: Path, sb: dict, fondo: str, destino: Path) -> str:
    """Imagen de fondo de una diapositiva, ya tratada con la marca. Devuelve la ruta relativa."""
    tipo, _, ref = fondo.partition(":")
    if tipo == "img":
        src = proy / "assets" / "t" / f"{ref}.jpg"
        if not src.exists():
            raise SocialError(f"falta {src} (construye el vídeo antes: construir.py hornea el duotono)")
        dst = destino / f"img-{ref}.jpg"
        shutil.copyfile(src, dst)
        return dst.name
    clave, _, seg = ref.partition("@")
    import broll
    crudo = proy / "assets" / "clips" / f"{clave}.src"
    if not crudo.exists():
        raise SocialError(f"falta {crudo} (construye el vídeo antes: construir.py baja los clips)")
    decl = (sb.get("clips") or {})[clave]
    t = float(decl.get("desde", 0)) + float(seg or 1.0)
    color = broll.GRADO_MARCA if not decl.get("duotono") else "format=gray"
    dst = destino / f"clip-{clave}-{t:g}.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(crudo), "-frames:v", "1",
                    "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{color}",
                    "-q:v", "2", str(dst)], check=True)
    return dst.name


def _html_carrusel(slides: list[dict], fondos: list[str], tarjeta: bool = False) -> str:
    """`tarjeta=True`: una sola pieza de cierre (historia): sin "Swipe", sin contador ni puntos."""
    n = len(slides)
    secciones = []
    for k, (d, f) in enumerate(zip(slides, fondos)):
        ultima, primera = (k == n - 1) and not tarjeta, (k == 0) and not tarjeta
        puntos = "".join(f'<i class="{"on" if j == k else ""}"></i>' for j in range(n))
        secciones.append(f'''
      <section id="s{k}" class="clip slide{" cover" if primera else ""}{" last" if ultima else ""}" data-start="{k}" data-duration="1">
        <img class="bg" src="{f}" alt="" /><div class="scrim"></div>
        <div class="top"><span class="brand">NET WORTHY</span>{"" if tarjeta else f'<span class="num">{k + 1}/{n}</span>'}</div>
        <div class="body">
          {f'<div class="kicker">{_t(d.get("kicker"))}</div>' if d.get("kicker") else ""}
          <div class="titulo{" xl" if primera else ""}">{_t(d["titulo"])}</div>
          {f'<div class="texto">{_t(d.get("texto"))}</div>' if d.get("texto") else ""}
          {'<div class="swipe">Swipe &rarr;</div>' if primera else ""}
          {'<div class="follow">@networthytv &middot; one real money story a day</div>' if ultima else ""}
        </div>
        {"" if tarjeta else f'<div class="dots">{puntos}</div>'}
      </section>''')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width={W}, height={H}" />
<script src="gsap.min.js"></script>
<style>
  @font-face {{ font-family: "Anton"; src: url("fonts/anton.woff2") format("woff2"); }}
  @font-face {{ font-family: "Inter"; font-weight: 600; src: url("fonts/inter-latin-600-normal.woff2") format("woff2"); }}
  @font-face {{ font-family: "Inter"; font-weight: 800; src: url("fonts/inter-latin-800-normal.woff2") format("woff2"); }}
  @font-face {{ font-family: "Inter"; font-weight: 900; src: url("fonts/inter-latin-900-normal.woff2") format("woff2"); }}
  body {{ margin: 0; background: #0a1a14; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; font-family: "Inter", sans-serif; color: #f4f6f3; }}
  .slide {{ position: absolute; inset: 0; overflow: hidden; background: #0a1a14; }}
  .bg {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
  .scrim {{ position: absolute; inset: 0; background: linear-gradient(180deg, rgba(10,26,20,0.55) 0%, rgba(10,26,20,0.15) 30%,
           rgba(10,26,20,0.55) 58%, rgba(10,26,20,0.96) 100%); }}
  .top {{ position: absolute; top: 56px; left: 70px; right: 70px; display: flex; justify-content: space-between;
          font-weight: 800; font-size: 26px; letter-spacing: 0.4em; color: #d8b25a; }}
  .num {{ letter-spacing: 0.1em; color: #cfd8d3; }}
  .body {{ position: absolute; left: 70px; right: 70px; bottom: 150px; }}
  .kicker {{ font-weight: 800; font-size: 34px; letter-spacing: 0.22em; text-transform: uppercase; color: #d8b25a; margin-bottom: 18px; }}
  .titulo {{ font-family: "Anton", sans-serif; font-size: 118px; line-height: 0.98; text-transform: uppercase;
             text-shadow: 0 6px 0 rgba(0,0,0,0.35), 0 0 42px rgba(0,0,0,0.75); }}
  .titulo.xl {{ font-size: 176px; }}
  .texto {{ font-weight: 600; font-size: 40px; line-height: 1.32; margin-top: 26px; color: #e9eee9; text-shadow: 0 2px 18px rgba(0,0,0,0.8); }}
  .gold {{ color: #d8b25a; }}
  .swipe {{ margin-top: 34px; font-weight: 900; font-size: 34px; letter-spacing: 0.18em; text-transform: uppercase; color: #0a1a14;
            background: #d8b25a; display: inline-block; padding: 14px 30px; border-radius: 999px; }}
  .follow {{ margin-top: 34px; font-weight: 800; font-size: 32px; letter-spacing: 0.06em; color: #d8b25a; }}
  .dots {{ position: absolute; bottom: 70px; left: 0; right: 0; display: flex; justify-content: center; gap: 14px; }}
  .dots i {{ width: 14px; height: 14px; border-radius: 50%; background: rgba(244,246,243,0.3); }}
  .dots i.on {{ background: #d8b25a; width: 40px; border-radius: 8px; }}
</style></head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-width="{W}" data-height="{H}" data-duration="{n}">{"".join(secciones)}
  </div>
  <script>const tl = gsap.timeline({{ paused: true }}); tl.set({{}}, {{}}, {n}); window.__timelines = window.__timelines || {{}}; window.__timelines["main"] = tl;</script>
</body></html>
'''


def _html_tarjeta(titulo: str, sub: str) -> str:
    """Tarjeta final de la historia (1080x1920)."""
    return _html_carrusel([{"titulo": titulo, "texto": sub}], ["tarjeta-fondo.jpg"], tarjeta=True).replace(
        f'data-width="{W}" data-height="{H}"', 'data-width="1080" data-height="1920"').replace(
        f"width: {W}px; height: {H}px", "width: 1080px; height: 1920px").replace(
        f"width={W}, height={H}", "width=1080, height=1920")


def _snapshot(dir_: Path, tiempos: list[float], env: dict) -> list[Path]:
    salida = dir_ / "snapshots"
    if salida.exists():
        shutil.rmtree(salida)
    r = subprocess.run(["npx", "--yes", HF, "snapshot", "--at", ",".join(f"{t:g}" for t in tiempos), "--no-end",
                        "--describe", "false", "--timeout", "60000", "-o", str(salida)],
                       cwd=dir_, capture_output=True, text=True, env={**__import__("os").environ, **env})
    fotos = sorted(salida.glob("frame-*.png"))
    if len(fotos) != len(tiempos):
        raise SocialError(f"snapshot devolvió {len(fotos)}/{len(tiempos)} imágenes: {(r.stderr or r.stdout)[-400:]}")
    return fotos


def _preparar_dir(dir_: Path) -> None:
    dir_.mkdir(parents=True, exist_ok=True)
    shutil.copytree(MOTOR / "assets" / "fonts", dir_ / "fonts", dirs_exist_ok=True)
    shutil.copyfile(MOTOR / "assets" / "gsap.min.js", dir_ / "gsap.min.js")
    (dir_ / "hyperframes.json").write_text(json.dumps({"media": {"autoProxy": False}}) + "\n")


def generar(proy: Path, env: dict | None = None) -> dict:
    from PIL import Image
    proy = Path(proy).resolve()
    sb = json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    errores = validar(sb)
    if errores:
        raise SocialError("social inválido:\n  - " + "\n  - ".join(errores))
    env = env or {}
    so, out = sb["social"], proy / "social"
    # 1) carrusel
    render = out / "_render"
    _preparar_dir(render)
    fondos = [_fondo(proy, sb, d["fondo"], render) for d in so["carrusel"]]
    (render / "index.html").write_text(_html_carrusel(so["carrusel"], fondos), encoding="utf-8")
    car = out / "carrusel"
    if car.exists():
        shutil.rmtree(car)
    car.mkdir(parents=True)
    fotos = _snapshot(render, [k + 0.5 for k in range(len(fondos))], env)
    jpgs = []
    for k, png in enumerate(fotos):
        dst = car / f"{k + 1:02d}.jpg"
        Image.open(png).convert("RGB").resize((W, H), Image.LANCZOS).save(dst, quality=92, optimize=True)
        jpgs.append(dst)
    # 2) historia: gancho REAL del Short + tarjeta final
    historia = None
    h = so.get("historia") or {}
    final = next(iter(sorted((proy / "renders").glob("*-final.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)), None)
    if h and final:
        import anclas
        words = json.loads((proy / "assets" / "words.json").read_text(encoding="utf-8"))
        try:
            corte = min(anclas.t(words, h["hasta"]) + 0.35, 14.0)
        except anclas.AnclaError as e:
            raise SocialError(f"`social.historia.hasta`: {e}")
        tarjeta = out / "_tarjeta"
        _preparar_dir(tarjeta)
        shutil.copyfile(render / fondos[-1], tarjeta / "tarjeta-fondo.jpg")
        (tarjeta / "index.html").write_text(_html_tarjeta(h.get("cierre", "Full story in Reels"),
                                                          "Full story in our Reels · @networthytv"), encoding="utf-8")
        png = _snapshot(tarjeta, [0.5], env)[0]
        historia = out / "historia.mp4"
        fc = (f"[0:v]trim=0:{corte:.2f},setpts=PTS-STARTPTS,fps=30,format=yuv420p[a];"
              f"[1:v]scale=1080:1920,fps=30,format=yuv420p,trim=0:2.5,setpts=PTS-STARTPTS[b];"
              f"[a][b]xfade=transition=fade:duration=0.35:offset={corte - 0.35:.2f}[v];"
              f"[0:a]atrim=0:{corte:.2f},afade=t=out:st={corte - 0.5:.2f}:d=0.5,apad=pad_dur=2.2[au]")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(final), "-loop", "1", "-t", "2.5", "-i", str(png),
                        "-filter_complex", fc, "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-crf", "20",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
                        str(historia)], check=True)
    textos = captions(sb)
    (out / "textos.json").write_text(json.dumps(textos, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"carrusel": [str(p) for p in jpgs], "historia": str(historia) if historia else None,
            "textos": str(out / "textos.json")}


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    import producir
    try:
        r = generar(Path(sys.argv[1]), producir._entorno())
    except SocialError as e:
        raise SystemExit(f"✗ {e}")
    print(f"✓ carrusel: {len(r['carrusel'])} diapositivas · historia: {r['historia'] or '— (sin render final o sin `historia`)'}"
          f" · textos: {r['textos']}")


if __name__ == "__main__":
    main()
