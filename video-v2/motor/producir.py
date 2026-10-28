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
    """Descripción para YouTube: la del storyboard + aviso YMYL + fuentes + créditos de imagen y
    de metraje (CC BY los EXIGE; PD y Pexels se citan igual). Función pura salvo la lectura de creditos.json."""
    pub = sb.get("publicacion") or {}
    sr = sb.get("serie")
    partes = [(f'{sr["nombre"]} · Ep. {sr["ep"]}' if sr else ""), pub.get("descripcion", "").strip()]
    if (sb.get("aviso") or {}).get("lineas"):
        partes.append(" · ".join(sb["aviso"]["lineas"]))
    hashtags = " ".join(pub.get("hashtags", []) + ([serie_hashtag(sr)] if sr else []))
    partes.append(hashtags)                      # ANTES de los créditos: son lo que YouTube lee
    fuentes = [c["fuente"] for c in sb.get("cifras") or [] if c.get("fuente")]
    if fuentes:
        partes.append("Sources:\n" + "\n".join(f"- {u}" for u in dict.fromkeys(fuentes)))
    cred = proy / "assets" / "img" / "creditos.json"
    if cred.exists():
        sys.path.insert(0, str(RAIZ / "tools"))
        import imagenes_libres
        partes.append(imagenes_libres.texto_creditos(json.loads(cred.read_text(encoding="utf-8"))))
    cred_v = proy / "assets" / "clips" / "creditos.json"
    usados = {f"{k}.src" for k in sb.get("clips") or {}}
    if cred_v.exists() and usados:                   # solo los clips que el storyboard usa hoy
        sys.path.insert(0, str(RAIZ / "tools"))
        import broll
        fichas = [f for f in json.loads(cred_v.read_text(encoding="utf-8")) if f["archivo"] in usados]
        if fichas:
            partes.append(broll.texto_creditos(fichas))
    cred_m = proy / "assets" / "musica" / "creditos.json"
    if cred_m.exists() and ((sb.get("musica") or {}).get("pista")):   # CC BY exige citar la música
        sys.path.insert(0, str(RAIZ / "tools"))
        import musica_libre
        fichas = [f for f in json.loads(cred_m.read_text(encoding="utf-8")) if f["archivo"] == "pista.src"]
        if fichas:
            partes.append(musica_libre.texto_creditos(fichas))
    cred_s = proy / "assets" / "sfx" / "creditos.json"
    usados_s = {f"{n}.src" for n in sfx_usados(sb)}
    if cred_s.exists() and usados_s:                 # efectos reales: CC BY exige citarlos igual
        sys.path.insert(0, str(RAIZ / "tools"))
        import sfx_libre
        fichas = [f for f in json.loads(cred_s.read_text(encoding="utf-8")) if f["archivo"] in usados_s]
        if fichas:
            partes.append(sfx_libre.texto_creditos(fichas))
    return ajustar_limite([p for p in partes if p])


LIMITE_DESC = 5000   # YouTube rechaza/corta más allá: nunca a costa de una atribución obligatoria


def ajustar_limite(partes: list[str], limite: int = LIMITE_DESC) -> str:
    """Une la descripción sin pasar de `limite`. Si no cabe, acorta los TÍTULOS de los créditos
    (autor, licencia y enlace se quedan: son lo que exige CC BY) antes que cortar nada. Si ni así
    cabe, falla: un recorte a ciegas se comía los hashtags y, con un vídeo más, las atribuciones."""
    t = "\n\n".join(partes)
    for n in (80, 50, 30):
        if len(t) <= limite:
            return t
        t = "\n\n".join(re.sub(r"(?m)^- (.+?) — ", lambda m: f"- {m.group(1)[:n].rstrip()}{'…' if len(m.group(1)) > n else ''} — ", x)
                        for x in partes)
    if len(t) > limite:
        raise ValueError(f"descripción de {len(t)} caracteres (> {limite}) aun acortando títulos: quita créditos de recursos no usados")
    return t


def sfx_usados(sb: dict) -> set[str]:
    """Nombres de efectos que el storyboard usa (clips, imágenes y `sonidos`)."""
    n = {c.get("sfx") for c in (sb.get("clips") or {}).values()}
    n |= {i.get("sfx") for i in (sb.get("imagenes") or {}).values()}
    n |= {x.get("sfx") for x in sb.get("sonidos") or [] if isinstance(x, dict)}
    return {x for x in n if x}


def serie_hashtag(sr: dict) -> str:
    return "#" + re.sub(r"[^A-Za-z0-9]", "", sr["nombre"].title())


def comentario(sb: dict) -> str | None:
    """Comentario para FIJAR: la pregunta del CTA como votación (más comentarios = más señal) + el
    gancho del siguiente episodio si hay serie. `publicacion.comentario` manda si existe."""
    pub = sb.get("publicacion") or {}
    if pub.get("comentario"):
        return pub["comentario"].strip()
    cta = next((e for e in sb.get("escenas") or [] if e.get("tipo") == "cta"), None)
    if not cta or not (cta.get("a") and cta.get("b")):
        return None
    a, b = cta["a"]["texto"].strip("*"), cta["b"]["texto"].strip("*")
    txt = f"{a} or {b}? Reply with one word 👇"
    sr = sb.get("serie")
    if sr:
        txt += f'\n\n{sr["nombre"]} · Ep. {sr["ep"] + 1} is next — follow so you don\'t miss it.'
    return txt


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
    from omega.cli import _video_id
    if (previo := _video_id(ref)) and "--forzar" not in sys.argv:   # reintento de la rutina: no duplicar
        return f"ya subido antes: https://youtu.be/{previo} (no se sube otra vez)"
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


LUFS_OBJ, TP_OBJ = -14.0, -2.0   # -2 (no -1.5): la codificación AAC posterior sube el pico ~0,5 dB


LIMITES_DB = (-2.0, -2.5, -3.0, -3.5, -4.0, -5.0)   # techo del limitador, de menos a más agresivo


def loudnorm_2pasos(crudo: Path, final: Path) -> tuple[bool, str]:
    """Volumen a -14 LUFS con el pico garantizado, MEDIDO sobre el archivo ya codificado.

    1) loudnorm mide la entrada; 2) ganancia lineal hasta el objetivo; 3) limitador con 4x de
    sobremuestreo para los picos; 4) AAC; 5) se mide el resultado y se acepta el primer techo que
    cumpla pico <= TP_MAX y -14 ±0,8 LUFS. Por qué no loudnorm solo: si subir linealmente pasa el
    techo, cae a modo DINÁMICO aunque se pida linear=true (#7: -17,71 LUFS / -1,66 dBTP de entrada)
    y la corrección de pico posterior dejaba el #8 en -15,06 LUFS (28-oct). Y el limitador de
    ffmpeg no es true-peak: el AAC rebota por encima del techo (-2,5 dB -> +0,37 dBTP medido), por
    eso se prueba y se mide en vez de fijar un techo a ojo."""
    r = _run(["ffmpeg", "-hide_banner", "-i", str(crudo), "-af",
              f"loudnorm=I={LUFS_OBJ}:TP={TP_OBJ}:LRA=11:print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr)
    if not m:
        return False, "no se pudo medir el audio: " + r.stderr[-300:]
    med = json.loads(m.group(0))
    ganancia = LUFS_OBJ - float(med["input_i"])
    probado = []
    for lim in LIMITES_DB:
        g = ganancia
        for _ in range(3):        # limitar picos BAJA el volumen medido: se suma lo que falta y se repite
            af = (f"volume={g:.2f}dB,aresample=192000,"
                  f"alimiter=limit={10 ** (lim / 20):.4f}:attack=0.5:release=40:level=false,aresample=48000")
            r = _run(["ffmpeg", "-v", "error", "-y", "-i", str(crudo), "-af", af,
                      "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(final)])
            if r.returncode != 0:
                return False, r.stderr[-300:]
            lufs, tp = lufs_y_pico(final)
            probado.append(f"{lim:g}dB/+{g:.1f}->{lufs}/{tp}")
            if lufs is None or tp is None or tp > TP_MAX:
                break                                # este techo no aguanta el pico: siguiente
            if abs(lufs - LUFS_OBJ) <= 0.8:
                return True, (f"entrada {med['input_i']} LUFS / {med['input_tp']} dBTP · +{g:.2f} dB, "
                              f"techo {lim:g} dB -> {lufs} LUFS / {tp} dBTP")
            g += LUFS_OBJ - lufs
    return False, "ningún techo cumple pico y loudness a la vez: " + "; ".join(probado)


def lufs_y_pico(mp4: Path) -> tuple[float | None, float | None]:
    """(LUFS integrado, true peak dBTP) del audio de un archivo, con el ebur128 de ffmpeg."""
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"])
    i = re.findall(r"I:\s*(-?[\d.]+) LUFS", r.stderr)
    pk = re.findall(r"Peak:\s*(-?[\d.]+|-inf)\s*dBFS", r.stderr)
    return (float(i[-1]) if i else None, float(pk[-1]) if pk and pk[-1] != "-inf" else None)


TP_MAX = -1.2   # pico real máximo del archivo FINAL (la puerta exige < -1; 0,2 dB de margen)


def pico_real(mp4: Path) -> float | None:
    """True peak (dBTP) del audio de un archivo, con el ebur128 de ffmpeg (solo audio: <2 s)."""
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"])
    m = re.findall(r"Peak:\s*(-?[\d.]+|-inf)\s*dBFS", r.stderr)
    return float(m[-1]) if m and m[-1] != "-inf" else None


def asegurar_pico(final: Path, tp_max: float = TP_MAX, intentos: int = 3) -> tuple[bool, str]:
    """Garantiza el pico real del archivo final. loudnorm NO puede hacerlo solo: si subir al objetivo
    linealmente pasaría el techo, cae a modo DINÁMICO aunque se pida linear=true, y el AAC posterior
    rebota el pico ~1 dB (medido 28-oct en el #7: entrada -17,71 LUFS / -1,66 dBTP -> 'dynamic' ->
    final -0,99 dBTP, puerta fallida). Aquí se mide el archivo y se baja la ganancia lo que falte
    (lineal, el LUFS cae lo mismo: ~0,2-0,5 dB, dentro de la tolerancia de ±1)."""
    for _ in range(intentos):
        tp = pico_real(final)
        if tp is None:
            return False, "no se pudo medir el pico real"
        if tp <= tp_max:
            return True, f"pico real {tp} dBTP"
        tmp = final.with_name(final.stem + ".pico.mp4")
        r = _run(["ffmpeg", "-v", "error", "-y", "-i", str(final), "-af", f"volume={tp_max - tp - 0.1:.2f}dB",
                  "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(tmp)])
        if r.returncode != 0:
            return False, r.stderr[-300:]
        tmp.replace(final)
    tp = pico_real(final)
    return tp is not None and tp <= tp_max, f"pico real {tp} dBTP tras {intentos} correcciones"


def bloques_adn(sb: dict, words: list[dict]) -> list[dict]:
    """Bloques del ADN con su duración REAL (voz medida) y la técnica = tipos de escena que lo
    componen. Sin `length_s` por bloque, analytics-sync no puede decir en qué parte del guion se
    va la gente (solo 3s/10s/20s). Cada `guion[i]` son N frases: se cuentan con la MISMA regla que
    anclas.frases (. ? ! al final de palabra) para no depender del texto exacto de la voz."""
    sys.path.insert(0, str(MOTOR))
    import anclas
    fr = anclas.frases(words)
    fin = words[-1]["end"] + float(sb.get("cola_s", 0.6))
    n_frases = [max(1, len(re.findall(r"[.?!](?=\s|$)", g["texto"].strip()))) for g in sb.get("guion", [])]
    inicios, k = [], 0
    for n in n_frases:
        inicios.append(k)
        k += n
    if k != len(fr):                                 # guion y voz no casan: no inventar duraciones
        return [{"block": g["id"], "technique": "v2-storyboard"} for g in sb.get("guion", [])]
    t0s = [0.0 if i == 0 else words[fr[p][0]]["start"] for i, p in enumerate(inicios)]
    out = []
    for i, g in enumerate(sb["guion"]):
        t1 = t0s[i + 1] if i + 1 < len(t0s) else fin
        rango = range(inicios[i], inicios[i] + n_frases[i])
        tipos = []
        for e in sb.get("escenas", []):
            try:
                p_ = int(str(e.get("en", "")).split(":")[0].split("+")[0].split("-")[0])
            except ValueError:
                continue
            if p_ in rango:
                tipo = e["tipo"] + ("+clip" if e.get("clip") else "")
                if tipo not in tipos:
                    tipos.append(tipo)
        out.append({"block": g["id"], "technique": ",".join(tipos) or "v2-storyboard",
                    "length_s": round(t1 - t0s[i], 2)})
    return out


def instantes_escena(html: str) -> list[float]:
    """Un instante por escena (al 60 % de su ventana, cuando sus textos ya han entrado), FUERA de las
    pruebas documentales: el periódico a pantalla completa tapa la escena y la auditoría del DOM no
    ve oclusiones (28-oct: "stocks" del #7 a 2,95:1 en t=18,37, debajo de la prueba de 17,80-18,98;
    tres rondas del crítico atacando un texto que nadie veía)."""
    xs = re.findall(r'<section id="s\d+" class="clip scene" data-start="([\d.]+)" data-duration="([\d.]+)"', html)
    m = re.search(r"window\.PLAN = (\{.*?\});</script>", html, re.S)
    tapas = [(p["t0"], p["t1"]) for p in (json.loads(m.group(1).replace("<\\/", "</")).get("pruebas") or [])] if m else []
    out = []
    for a, b in ((float(a), float(b)) for a, b in xs):
        t = a + min(b * 0.6, b - 0.1)
        for t0, t1 in tapas:
            if t0 - 0.2 <= t <= t1 + 0.2:          # tapado: el tramo visible más largo de la escena
                antes, despues = t0 - 0.2 - a, a + b - (t1 + 0.2)
                t = (a + antes * 0.8) if antes >= despues else (t1 + 0.2 + despues * 0.5)
                t = min(max(t, a + 0.05), a + b - 0.05)
        out.append(round(t, 2))
    return out


def fallos_contraste(informes: list[dict]) -> list[str]:
    """Textos por debajo de WCAG AA en los informes de `hyperframes check --json`. Solo contraste:
    la auditoría de maquetación da falsos positivos con capas decorativas (viñeta 'tapando' el
    logo, monedas del estallido 'solapadas' — medido en Grace, 25-sep), así que no es puerta."""
    out = []
    for d in informes:
        for f in (d.get("contrast") or {}).get("findings") or []:
            if f.get("ratio") is not None and f.get("requiredRatio") and f["ratio"] < f["requiredRatio"]:
                out.append(f'"{f.get("text", "")[:30]}" {f["ratio"]}:1 (< {f["requiredRatio"]}) en t≈{f.get("time", "?")}s')
    return out


def medicion_valida(d: dict) -> tuple[bool, str]:
    """¿La pasada de `check` MIDIÓ de verdad? Sin muestras, sin textos o con error de runtime, su
    'ok' no significa nada (así pasó en falso el #7: 'Navigation timeout', 0 textos, ok=True)."""
    c, rt = d.get("contrast") or {}, d.get("runtime") or {}
    if rt.get("errorCount"):
        msgs = [str(f.get("message", ""))[:120] for f in rt.get("findings") or []]
        return False, "error de runtime: " + "; ".join(msgs[:2])
    if not c.get("samples") or not c.get("checked"):
        return False, f"0 textos medidos (samples={c.get('samples')})"
    return True, "ok"


def auditar_contraste(proy: Path, env: dict) -> tuple[bool, str]:
    """WCAG AA en TODAS las escenas. `check` usa como mucho 5 instantes por pasada: se hacen varias."""
    ts = instantes_escena((proy / "index.html").read_text(encoding="utf-8"))
    informes, textos = [], 0
    for i in range(0, len(ts), 5):
        # --timeout: con 10 s (defecto) el #7 (3D + 18 capas) no llegaba a cargar y la auditoría
        # devolvía 0 textos medidos SIN fallar (25-sep). Un instrumento que no mide no aprueba.
        r = _run(["npx", "--yes", HF, "check", "--json", "--timeout", "60000",
                  "--at", ",".join(map(str, ts[i:i + 5]))], cwd=proy, env=env)
        try:
            d = json.loads(r.stdout)
        except json.JSONDecodeError:
            return False, "check no devolvió JSON: " + (r.stderr or r.stdout)[-300:]
        ok_medida, motivo = medicion_valida(d)
        if not ok_medida:
            return False, f"la auditoría NO midió (t={ts[i:i + 5]}): {motivo}"
        informes.append(d)
        textos += d["contrast"]["checked"]
    fallos = fallos_contraste(informes)
    return not fallos, (f"{textos} textos en {len(ts)} escenas, todos >= AA" if not fallos
                        else f"{len(fallos)} textos ilegibles: " + "; ".join(fallos[:5]))


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
    puerta("contraste", *auditar_contraste(proy, env))
    crudo, final, prev = renders / f"{ref}.mp4", renders / f"{ref}-final.mp4", renders / f"{ref}-preview.mp4"
    r = _run(["npx", "--yes", HF, "render", "--quality", "high", "--output", str(crudo)], cwd=proy, env=env)
    puerta("render", r.returncode == 0 and crudo.exists(), (re.findall(r"rendered in [^\n]+", r.stdout) or [r.stderr[-300:]])[0])
    ok_ln, det_ln = loudnorm_2pasos(crudo, final)
    if ok_ln:
        ok_ln, det_pico = asegurar_pico(final)
        det_ln = f"{det_ln.strip().splitlines()[-1] if det_ln.strip() else ''} · {det_pico}"
    puerta("loudnorm", ok_ln, det_ln)
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
               "privacy_status": "private", "made_for_kids": False,
               "comentario_fijado": comentario(sb), "serie": sb.get("serie")}
    (RAIZ / "data").mkdir(exist_ok=True)
    (RAIZ / "data" / f"publish_{ref}.json").write_text(json.dumps(publish, ensure_ascii=False, indent=2), encoding="utf-8")
    # El ADN se escribe solo si no existe: uno hecho a mano (técnica por bloque) vale más que este
    # genérico, y producir no debe destruir instrumentación (pasó en la 1ª prueba con el #7).
    if sb.get("adn") and not (proy / "adn.json").exists():
        W = json.loads((proy / "assets" / "words.json").read_text())
        dur = round(W[-1]["end"] + float(sb.get("cola_s", 0.6)))
        (proy / "adn.json").write_text(json.dumps({"production_ref": ref, **sb["adn"], "length_s": dur,
                                                   "blocks": bloques_adn(sb, W)},
                                                  ensure_ascii=False, indent=2), encoding="utf-8")
    if sb.get("social"):                          # páginas vivas: carrusel + historia (no publica nada)
        import social
        try:
            s = social.generar(proy, env)
            puerta("social", True, f"carrusel {len(s['carrusel'])} diapositivas · historia {'sí' if s['historia'] else 'no'}")
        except (social.SocialError, subprocess.CalledProcessError) as e:
            puerta("social", False, str(e))
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
