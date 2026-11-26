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
Por defecto (`--auto`, implícito desde el 18-nov; `--sin-auto` lo apaga): antes de cada repetición aplica
SOLO arreglos mecánicos (autoarreglo.py) y vuelve a pasar las MISMAS puertas, hasta RONDAS_AUTO veces;
para e imprime lo que no es mecánico.
`--boceto`: puertas + build + render a 10 fps (draft) + loudnorm, sin contraste: lo que mide el crítico
antes del render final (`critico.py`). Nunca se publica.
`--previo` para antes del render: puertas + una hoja de contactos por escena (<1 min). Sin `--sin-critico`,
al final corre los medidores del crítico. Solo imprime fallos, con segundo y escena; todo queda en
`renders/qa.json` (puertas, con su duración) y `renders/corridas.jsonl` (una línea por corrida).
Escribe `renders/qa.json` con cada puerta. NO publica: aprobar = `python -m omega.cli programar <ref>`
(hora pico de EE. UU.) — publicar exige una persona (política del canal).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import hfversion
import puertas
from construir import COLA_S

MOTOR = Path(__file__).resolve().parent
RAIZ = MOTOR.parents[1]
PY = sys.executable
RONDAS_AUTO = 3  # --auto: fix-and-retry rounds; each later one may cost a render
DETALLES: dict[
    str, tuple[bool, str]
] = {}  # last run, full gate detail (qa.json keeps 600 chars)
PENDIENTES: list = []  # --auto: what autoarreglo could not fix, for corridas.jsonl
RONDAS: list = []  # --auto: seconds of each round; qa.json only keeps the last one


def _run(
    cmd: list[str], cwd: Path | None = None, env: dict | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        check=False,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={
            **os.environ,
            "PYTHONUTF8": "1",
            **(env or {}),
        },  # the tools print ✓/≈: cp1252 would crash them
    )


def _entorno() -> dict:
    """Cloud defaults (HF_CORE, browser path). The user's own environment wins, and a default path
    that does not exist here (the Linux container paths on the Windows PC) is dropped."""
    # a bare "bash" resolves to System32 (WSL) on Windows whatever PATH says, and WSL leaves HF_CORE empty
    bash = shutil.which("bash") or "bash"
    out = _run([bash, str(RAIZ / "tools" / "setup_nube.sh"), "--env"]).stdout
    pares = re.findall(r"export (\w+)=(\S+)", out)
    if os.name == "nt":  # Git Bash prints MSYS paths: /c/Users/... -> C:/Users/...
        pares = [(k, re.sub(r"^/([a-zA-Z])/", r"\1:/", v)) for k, v in pares]
    return {k: v for k, v in pares if k not in os.environ and Path(v).exists()}


RE_DVIDS = re.compile(
    r"\b(DVIDS|DOD|DoW|U\.S\. Navy|USN|Navy Medicine|Department of War)\b"
)
AVISO_DVIDS = (
    "The appearance of U.S. Department of War (DoW) visual information does not imply or "
    "constitute DoW endorsement."
)


def _mmss(t: float) -> str:
    h, r = divmod(int(t), 3600)
    return f"{h}:{r // 60:02d}:{r % 60:02d}" if h else f"{r // 60}:{r % 60:02d}"


def lista_capitulos(sb: dict, words: list[dict]) -> str:
    """YouTube chapters ("0:00 Title" per line) from the first word of each chapter's sentence.
    YouTube ignores the list unless it starts at 0:00 and every chapter lasts >= 10 s: refuse instead."""
    caps = sb.get("capitulos") or []
    if not caps:
        return ""
    inicio, i = [], 0
    for g in sb["guion"]:
        inicio.append(i)
        i += len(g["texto"].split())
    ts = [0.0] + [words[inicio[c["desde"]]]["start"] for c in caps[1:]]
    cortos = [
        c["titulo"]
        for c, a, b in zip(caps, ts, [*ts[1:], words[-1]["end"]])
        if b - a < 10
    ]
    if cortos:
        raise ValueError(f"capítulos de menos de 10 s: {cortos}")
    return "\n".join(f"{_mmss(t)} {c['titulo']}" for c, t in zip(caps, ts))


def descripcion(sb: dict, proy: Path) -> str:
    """Descripción para YouTube: la del storyboard + aviso YMYL + fuentes + créditos de imagen y
    de metraje (CC BY los EXIGE; PD y Pexels se citan igual). Función pura salvo la lectura de creditos.json."""
    pub = sb.get("publicacion") or {}
    sr = sb.get("serie")
    partes = [
        (f"{sr['nombre']} · Ep. {sr['ep']}" if sr else ""),
        pub.get("descripcion", "").strip(),
    ]
    if sb.get("capitulos"):
        words = json.loads((proy / "assets" / "words.json").read_text(encoding="utf-8"))
        partes.append(lista_capitulos(sb, words))
    if (sb.get("aviso") or {}).get("lineas"):
        partes.append(" · ".join(sb["aviso"]["lineas"]))
    hashtags = " ".join(pub.get("hashtags", []) + ([serie_hashtag(sr)] if sr else []))
    partes.append(hashtags)  # ANTES de los créditos: son lo que YouTube lee
    fuentes = [c["fuente"] for c in sb.get("cifras") or [] if c.get("fuente")]
    if fuentes:
        partes.append(
            "Sources:\n" + "\n".join(f"- {u}" for u in dict.fromkeys(fuentes))
        )
    cred = proy / "assets" / "img" / "creditos.json"
    if cred.exists():
        sys.path.insert(0, str(RAIZ / "tools"))
        import imagenes_libres

        partes.append(
            imagenes_libres.texto_creditos(json.loads(cred.read_text(encoding="utf-8")))
        )
    cred_v = proy / "assets" / "clips" / "creditos.json"
    usados = {f"{k}.src" for k in sb.get("clips") or {}}
    if cred_v.exists() and usados:  # solo los clips que el storyboard usa hoy
        sys.path.insert(0, str(RAIZ / "tools"))
        import broll

        fichas = [
            f
            for f in json.loads(cred_v.read_text(encoding="utf-8"))
            if f["archivo"] in usados
        ]
        if fichas:
            partes.append(broll.texto_creditos(fichas))
    cred_m = proy / "assets" / "musica" / "creditos.json"
    if cred_m.exists() and (
        (sb.get("musica") or {}).get("pista")
    ):  # CC BY exige citar la música
        sys.path.insert(0, str(RAIZ / "tools"))
        import musica_libre

        fichas = [
            f
            for f in json.loads(cred_m.read_text(encoding="utf-8"))
            if f["archivo"] == "pista.src"
        ]
        if fichas:
            partes.append(musica_libre.texto_creditos(fichas))
    cred_s = proy / "assets" / "sfx" / "creditos.json"
    usados_s = {f"{n}.src" for n in sfx_usados(sb)}
    if cred_s.exists() and usados_s:  # efectos reales: CC BY exige citarlos igual
        sys.path.insert(0, str(RAIZ / "tools"))
        import sfx_libre

        fichas = [
            f
            for f in json.loads(cred_s.read_text(encoding="utf-8"))
            if f["archivo"] in usados_s
        ]
        if fichas:
            partes.append(sfx_libre.texto_creditos(fichas))
    if RE_DVIDS.search(
        "\n".join(p for p in partes[3:] if p)
    ):  # DVIDS requires this line from every user of its material
        partes.append(AVISO_DVIDS)
    return ajustar_limite([p for p in partes if p])


LIMITE_DESC = (
    5000  # YouTube rechaza/corta más allá: nunca a costa de una atribución obligatoria
)


def ajustar_limite(partes: list[str], limite: int = LIMITE_DESC) -> str:
    """Une la descripción sin pasar de `limite`. Si no cabe, acorta los TÍTULOS de los créditos
    (autor, licencia y enlace se quedan: son lo que exige CC BY) antes que cortar nada. Si ni así
    cabe, falla: un recorte a ciegas se comía los hashtags y, con un vídeo más, las atribuciones."""
    t = "\n\n".join(partes)
    for n in (80, 50, 30):
        if len(t) <= limite:
            return t
        t = "\n\n".join(
            re.sub(
                r"(?m)^- (.+?) — ",
                lambda m, n=n: (
                    f"- {m.group(1)[:n].rstrip()}{'…' if len(m.group(1)) > n else ''} — "
                ),
                x,
            )
            for x in partes
        )
    if len(t) > limite:
        raise ValueError(
            f"descripción de {len(t)} caracteres (> {limite}) aun acortando títulos: quita créditos de recursos no usados"
        )
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
        txt += f"\n\n{sr['nombre']} · Ep. {sr['ep'] + 1} is next — follow so you don't miss it."
    return txt


def subir_borrador(publish: dict, ref: str) -> str:
    """Sube el MP4 final a YouTube como PRIVADO (no es publicar: nadie lo ve) para que no se pierda
    si el contenedor se recicla antes de la aprobación. Aprobar = `omega.cli programar <ref>`.
    Sin token o con --sin-subir se salta; un fallo aquí NO invalida el QA (el vídeo es bueno)."""
    if "--sin-subir" in sys.argv:
        return "omitido (--sin-subir)"
    if not (RAIZ / "data" / "youtube_token.json").exists():
        return (
            "omitido: no hay data/youtube_token.json (YOUTUBE_TOKEN_JSON en el entorno)"
        )
    sys.path.insert(0, str(RAIZ))
    from omega import publish as pub
    from omega.cli import _video_id

    if (
        previo := _video_id(ref)
    ) and "--forzar" not in sys.argv:  # reintento de la rutina: no duplicar
        return f"ya subido antes: https://youtu.be/{previo} (no se sube otra vez)"
    try:
        res = pub.upload_video(
            Path(publish["video_path"]),
            publish["title"],
            publish["description"],
            tags=publish["tags"],
            privacy_status="private",
        )
    except Exception as e:  # noqa: BLE001 - se reporta, no se aborta el QA
        return f"FALLÓ: {e}"
    publish["video_id"] = res["video_id"]
    publish.setdefault("subido", {})["youtube"] = pub.sha256_de(
        Path(publish["video_path"])
    )
    (RAIZ / "data" / f"publish_{ref}.json").write_text(
        json.dumps(publish, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    try:  # a la BASE: viaja al repo de estado (sesión de mañana)
        from omega.cli import _registrar_video

        _registrar_video(ref, res["video_id"])
    except Exception as e:  # noqa: BLE001
        return f"privado en {res['url']} · ⚠ no quedó en la base ({e}): vincular {ref} {res['video_id']}"
    return f"privado en {res['url']} · aprobar: python -m omega.cli programar {ref}"


LUFS_OBJ, TP_OBJ = (
    -14.0,
    -2.0,
)  # -2 (no -1.5): la codificación AAC posterior sube el pico ~0,5 dB


LIMITES_DB = (
    -2.0,
    -2.5,
    -3.0,
    -3.5,
    -4.0,
    -5.0,
)  # techo del limitador, de menos a más agresivo


def loudnorm_2pasos(crudo: Path, final: Path) -> tuple[bool, str]:
    """Volumen a -14 LUFS con el pico garantizado, MEDIDO sobre el archivo ya codificado.

    1) loudnorm mide la entrada; 2) ganancia lineal hasta el objetivo; 3) limitador con 4x de
    sobremuestreo para los picos; 4) AAC; 5) se mide el resultado y se acepta el primer techo que
    cumpla pico <= TP_MAX y -14 ±0,8 LUFS. Por qué no loudnorm solo: si subir linealmente pasa el
    techo, cae a modo DINÁMICO aunque se pida linear=true (#7: -17,71 LUFS / -1,66 dBTP de entrada)
    y la corrección de pico posterior dejaba el #8 en -15,06 LUFS (28-oct). Y el limitador de
    ffmpeg no es true-peak: el AAC rebota por encima del techo (-2,5 dB -> +0,37 dBTP medido), por
    eso se prueba y se mide en vez de fijar un techo a ojo."""
    r = _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(crudo),
            "-af",
            f"loudnorm=I={LUFS_OBJ}:TP={TP_OBJ}:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ]
    )
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr)
    if not m:
        return False, "no se pudo medir el audio: " + r.stderr[-300:]
    med = json.loads(m.group(0))
    ganancia = LUFS_OBJ - float(med["input_i"])
    probado = []
    for lim in LIMITES_DB:
        g = ganancia
        for _ in range(
            3
        ):  # limitar picos BAJA el volumen medido: se suma lo que falta y se repite
            af = (
                f"volume={g:.2f}dB,aresample=192000,"
                f"alimiter=limit={10 ** (lim / 20):.4f}:attack=0.5:release=40:level=false,aresample=48000"
            )
            r = _run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(crudo),
                    "-af",
                    af,
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    str(final),
                ]
            )
            if r.returncode != 0:
                return False, r.stderr[-300:]
            lufs, tp = lufs_y_pico(final)
            probado.append(f"{lim:g}dB/+{g:.1f}->{lufs}/{tp}")
            if lufs is None or tp is None or tp > TP_MAX:
                break  # este techo no aguanta el pico: siguiente
            if abs(lufs - LUFS_OBJ) <= 0.8:
                return True, (
                    f"entrada {med['input_i']} LUFS / {med['input_tp']} dBTP · +{g:.2f} dB, "
                    f"techo {lim:g} dB -> {lufs} LUFS / {tp} dBTP"
                )
            g += LUFS_OBJ - lufs
    return False, "ningún techo cumple pico y loudness a la vez: " + "; ".join(probado)


def lufs_y_pico(mp4: Path) -> tuple[float | None, float | None]:
    """(LUFS integrado, true peak dBTP) del audio de un archivo, con el ebur128 de ffmpeg."""
    r = _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(mp4),
            "-map",
            "0:a",
            "-af",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ]
    )
    i = re.findall(r"I:\s*(-?[\d.]+) LUFS", r.stderr)
    pk = re.findall(r"Peak:\s*(-?[\d.]+|-inf)\s*dBFS", r.stderr)
    return (
        float(i[-1]) if i else None,
        float(pk[-1]) if pk and pk[-1] != "-inf" else None,
    )


TP_MAX = (
    -1.2
)  # pico real máximo del archivo FINAL (la puerta exige < -1; 0,2 dB de margen)


def pico_real(mp4: Path) -> float | None:
    """True peak (dBTP) del audio de un archivo, con el ebur128 de ffmpeg (solo audio: <2 s)."""
    r = _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(mp4),
            "-map",
            "0:a",
            "-af",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ]
    )
    m = re.findall(r"Peak:\s*(-?[\d.]+|-inf)\s*dBFS", r.stderr)
    return float(m[-1]) if m and m[-1] != "-inf" else None


def asegurar_pico(
    final: Path, tp_max: float = TP_MAX, intentos: int = 3
) -> tuple[bool, str]:
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
        r = _run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(final),
                "-af",
                f"volume={tp_max - tp - 0.1:.2f}dB",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(tmp),
            ]
        )
        if r.returncode != 0:
            return False, r.stderr[-300:]
        tmp.replace(final)
    tp = pico_real(final)
    return (
        tp is not None and tp <= tp_max,
        f"pico real {tp} dBTP tras {intentos} correcciones",
    )


def bloques_adn(sb: dict, words: list[dict]) -> list[dict]:
    """Bloques del ADN con su duración REAL (voz medida) y la técnica = tipos de escena que lo
    componen. Sin `length_s` por bloque, analytics-sync no puede decir en qué parte del guion se
    va la gente (solo 3s/10s/20s). Cada `guion[i]` son N frases: se cuentan con la MISMA regla que
    anclas.frases (. ? ! al final de palabra) para no depender del texto exacto de la voz."""
    sys.path.insert(0, str(MOTOR))
    import anclas

    fr = anclas.frases(words)
    fin = words[-1]["end"] + float(sb.get("cola_s", COLA_S))
    n_frases = [
        max(1, len(re.findall(r"[.?!](?=\s|$)", g["texto"].strip())))
        for g in sb.get("guion", [])
    ]
    inicios, k = [], 0
    for n in n_frases:
        inicios.append(k)
        k += n
    if k != len(fr):  # guion y voz no casan: no inventar duraciones
        return [
            {"block": g["id"], "technique": "v2-storyboard"}
            for g in sb.get("guion", [])
        ]
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
        out.append(
            {
                "block": g["id"],
                "technique": ",".join(tipos) or "v2-storyboard",
                "length_s": round(t1 - t0s[i], 2),
            }
        )
    return out


def instantes_escena(html: str) -> list[float]:
    """Un instante por escena (al 60 % de su ventana, cuando sus textos ya han entrado), FUERA de las
    pruebas documentales: el periódico a pantalla completa tapa la escena y la auditoría del DOM no
    ve oclusiones (28-oct: "stocks" del #7 a 2,95:1 en t=18,37, debajo de la prueba de 17,80-18,98;
    tres rondas del crítico atacando un texto que nadie veía)."""
    xs = re.findall(
        r'<section id="s\d+" class="clip scene" data-start="([\d.]+)" data-duration="([\d.]+)"',
        html,
    )
    m = re.search(r"window\.PLAN = (\{.*?\});</script>", html, re.DOTALL)
    tapas = (
        [
            (p["t0"], p["t1"])
            for p in (json.loads(m.group(1).replace("<\\/", "</")).get("pruebas") or [])
        ]
        if m
        else []
    )
    out = []
    for a, b in ((float(a), float(b)) for a, b in xs):
        t = a + min(b * 0.6, b - 0.1)
        for t0, t1 in tapas:
            if (
                t0 - 0.2 <= t <= t1 + 0.2
            ):  # tapado: el tramo visible más largo de la escena
                antes, despues = t0 - 0.2 - a, a + b - (t1 + 0.2)
                t = (
                    (a + antes * 0.8)
                    if antes >= despues
                    else (t1 + 0.2 + despues * 0.5)
                )
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
            if (
                f.get("ratio") is not None
                and f.get("requiredRatio")
                and f["ratio"] < f["requiredRatio"]
            ):
                out.append(
                    f'"{f.get("text", "")[:30]}" {f["ratio"]}:1 (< {f["requiredRatio"]}) en t≈{f.get("time", "?")}s'
                )
    return out


def fallos_layout(informes: list[dict]) -> list[str]:
    """Layout errors of `hyperframes check` (clipped, overflowing, occluded or unpainted text, covered canvas):
    broken output, so they block. Its warnings and info (safe zone, overlaps) carry the decorative-layer false
    positives measured on Grace (25-sep) and only inform."""
    return [
        f"{f.get('code')} {f.get('selector', '')} en t≈{f.get('time', '?')}s: {str(f.get('message', ''))[:80]}"
        for d in informes
        for f in (d.get("layout") or {}).get("findings") or []
        if f.get("severity") == "error"
    ]


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


# NVENC encoding: 84 vs 134 s on huang-exit, SSIM 0.992 / PSNR 49.6 dB against the CPU encode, above the
# 0.986 of two CPU renders of the same page (22-nov). Without an NVIDIA GPU, PRODUCIR_SIN_GPU=1.
RENDER_GPU = () if os.environ.get("PRODUCIR_SIN_GPU") else ("--gpu",)
# auto drops to 1 worker when its calibration sees slow frames: huang-exit-largo 1680 s with 1, 846 s with 4,
# same SSIM vs CPU but 6 of 13288 frames caught an animation one step late (user accepted, 23-nov)
RENDER_GPU += ("--workers", "4")


def gpu_render(log: str) -> str | None:
    """GPU Chrome rendered on, from HyperFrames' probe line (renderer vendor="Google Inc. (NVIDIA)")."""
    m = re.search(r'renderer vendor="Google Inc\. \(([^)]+)\)', log)
    return m.group(1) if m else None


def fotogramas(salida: Path, instantes: list[float]) -> dict[float, Path]:
    """{t: snapshot frame} for the wanted instants (the file name carries the second)."""
    out = {}
    for f in sorted(salida.glob("frame-*.png")):
        t = float(re.search(r"-at-([\d.]+)s", f.name).group(1))
        if any(abs(t - x) < 0.011 for x in instantes):
            out[t] = f
    return out


def aprobados_contraste(proy: Path, env: dict) -> tuple[str, dict, set[str]]:
    """(rules key, last cache, frames that passed under these rules)."""
    reglas = (env.get("HF_VERSION") or hfversion.version()) + _sha(Path(__file__))
    try:
        viejo = json.loads(
            (proy / "renders" / "contraste.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        viejo = {}
    return (
        reglas,
        viejo,
        set(viejo.get("instantes") or []) if viejo.get("reglas") == reglas else set(),
    )


def auditar_contraste(
    proy: Path, env: dict, medir=None, cuadros: Path | None = None, hoja=None
) -> tuple[bool, str]:
    """Contrast audit, reused when page, assets, HyperFrames and these rules match the last PASS:
    --rapido then --sin-subir audited the same page twice (18.8 min over 33 Short runs, 20-nov).
    With the preview's snapshot frames (`cuadros`), each instant whose frame is byte-identical to one that
    already passed is not measured again: 5 of the 6 huang-exit-largo previews re-audited all 85 scenes after
    fixing one or two (330-1920 s each, 18/19-nov)."""
    cache = proy / "renders" / "contraste.json"
    reglas, viejo, aprobados = aprobados_contraste(proy, env)
    clave = hashlib.sha256((clave_render(proy) + reglas).encode()).hexdigest()
    if viejo.get("clave") == clave:
        return (
            True,
            "reutilizado: misma página, assets y HyperFrames que la última auditoría aprobada",
        )
    ts = instantes_escena((proy / "index.html").read_text(encoding="utf-8"))

    def huellas() -> dict[float, str]:
        # keyed by the audit's own instant: the file name's second only matches it within 0.011 s
        return (
            {
                min(ts, key=lambda x: abs(x - t)): f"{t}|{_sha(f)}"
                for t, f in fotogramas(cuadros, ts).items()
            }
            if cuadros
            else {}
        )

    # `hoja`: the snapshot still running beside the audit (nothing approved to skip yet); its frames are
    # only hashed afterwards, so the next preview can skip what passed
    antes = {} if hoja else huellas()
    ok, detalle, bien = (medir or _medir_contraste)(
        proy, env, {t for t, h in antes.items() if h in aprobados}
    )
    hu = huellas() if hoja and hoja.result()[0] else antes
    # snapshots are byte-identical for the same page (5/5 frames, 22-nov): same pixels, same verdict
    aprobados |= {hu[t] for t in bien if t in hu}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(
        json.dumps(
            {
                "clave": clave if ok else None,
                "reglas": reglas,
                "instantes": sorted(aprobados),
            }
        ),
        encoding="utf-8",
    )
    return ok, detalle


HILOS_CHECK = 3  # whole long-form audit: 622 s with 3, 631 with 6, 579 with 9 (22-nov): the CPU is the limit, not this


def _medir_contraste(
    proy: Path, env: dict, ya: set[float] | frozenset[float] = frozenset()
) -> tuple[bool, str, list[float]]:
    """WCAG AA en TODAS las escenas salvo las de `ya` (aprobadas con los mismos píxeles). `check` usa como
    mucho 5 instantes por pasada y tarda lo mismo con 1 que con 5 (59 vs 47 s, 22-nov): se hacen varias.
    Devuelve también los instantes de las pasadas aprobadas."""
    todos = instantes_escena((proy / "index.html").read_text(encoding="utf-8"))
    ts = [t for t in todos if t not in ya]
    if not ts:
        return (
            True,
            f"{len(todos)} escenas reutilizadas: mismos fotogramas ya aprobados",
            [],
        )
    informes, textos, bien = [], 0, []

    def pasada(i: int) -> subprocess.CompletedProcess:
        # --timeout: con 10 s (defecto) el #7 (3D + 18 capas) no llegaba a cargar y la auditoría
        # devolvía 0 textos medidos SIN fallar (25-sep). Un instrumento que no mide no aprueba.
        return _run(
            hfversion.npx(
                "check",
                "--json",
                # only `contrast` and `runtime` are read; the craft pass was 85 -> 27 s, same 62 texts (huang-exit)
                "--no-craft",
                "--timeout",
                "60000",
                "--at",
                ",".join(map(str, ts[i : i + 5])),
            ),
            cwd=proy,
            env=env,
        )

    with ThreadPoolExecutor(HILOS_CHECK) as ex:
        pasadas = list(ex.map(pasada, range(0, len(ts), 5)))
    for i, r in zip(range(0, len(ts), 5), pasadas, strict=True):
        try:
            d = json.loads(r.stdout)
        except json.JSONDecodeError:
            return (
                False,
                "check no devolvió JSON: " + (r.stderr or r.stdout)[-300:],
                bien,
            )
        ok_medida, motivo = medicion_valida(d)
        if not ok_medida:
            return False, f"la auditoría NO midió (t={ts[i : i + 5]}): {motivo}", bien
        informes.append(d)
        textos += d["contrast"]["checked"]
        if not fallos_contraste([d]) + fallos_layout([d]):
            bien += ts[i : i + 5]
    fallos = fallos_contraste(informes) + fallos_layout(informes)
    nuevas = f"{len(ts)} de {len(todos)} escenas medidas"
    return (
        not fallos,
        (
            f"{textos} textos en {nuevas}, todos >= AA, sin errores de maquetación"
            if not fallos
            else f"{len(fallos)} textos ilegibles o rotos ({nuevas}): "
            + "; ".join(fallos[:5])
        ),
        bien,
    )


def ocr_previo(salida: Path, instantes: list[float]) -> list[dict]:
    """OCR of the preview frames at `instantes`, in the shape of medir_texto.ocr_frames (the file name has the second)."""
    from concurrent.futures import ProcessPoolExecutor

    import medir_cuadros
    import medir_texto

    quiere = fotogramas(salida, instantes)
    if len(quiere) <= 1:  # a process pool would only add start-up
        return [{"t": t, **medir_cuadros.ocr_imagen(f)} for t, f in quiere.items()]
    # one RapidOCR per process, as the critic's ocr_frames (same model and detection limit)
    with ProcessPoolExecutor(min(medir_texto.procesos_ocr(), len(quiere))) as ex:
        lecturas = list(ex.map(medir_cuadros.ocr_imagen, quiere.values()))
    return [{"t": t, **r} for t, r in zip(quiere, lecturas, strict=True)]


def texto_previo(proy: Path, sb: dict, m: dict) -> tuple[bool, str]:
    """Text over a document stops. L1 only warns: on 4 videos with 98 texts it raised 4 "unread" and the MP4 confirmed
    at most 1, because a few sampled frames are not 2 fps (the OCR misses legible lines on busy photos). The MP4 blocks."""
    import critico

    plan = critico.plan_de_html((proy / "index.html").read_text(encoding="utf-8"))
    words = json.loads((proy / "assets" / "words.json").read_text(encoding="utf-8"))
    frames = ocr_previo(proy / "renders" / "previo", m["ocr"])
    fallos = critico.revisar_previo(
        sb, plan, words, frames, critico.cargar_rubrica(proy)
    )
    lineas = [critico.linea(f) for f in fallos if f["severidad"] != "baja"]
    if lineas:
        print("\n".join(f"⚠ {x}" for x in lineas))
    return (
        not any(f["severidad"] == "alta" and f["criterio"] != "L1" for f in fallos),
        "\n".join(lineas) or f"{len(frames)} fotogramas leídos, sin fallos",
    )


GANCHO_MARGEN_LUMA = (
    3.5  # snapshot vs MP4 luma gap measured +3.2 (huang-exit): see gancho_previo
)


def instantes_gancho(u: dict) -> list[float]:
    """The hook frames the critic reads on the MP4 (medir_cuadros.FPS over `gancho_s`)."""
    import medir_cuadros as mc

    return [round(k / mc.FPS, 2) for k in range(int(u["gancho_s"] * mc.FPS))]


def gancho_previo(salida: Path, u: dict) -> tuple[bool, str]:
    """The critic's C1 dark/flat hook on the preview frames, same function and limits, before the render.
    Measured on huang-exit (12-nov, 10 frames): the snapshot reads luma +3.2 above the MP4 and contrast 6 %
    below it. Contrast is then already stricter; luma must clear the limit by GANCHO_MARGEN_LUMA so the
    preview never passes a hook the critic fails. PROVISIONAL, n=1: re-measure on the next Shorts."""
    import medir_cuadros as mc
    import numpy as np
    from PIL import Image

    quiere = instantes_gancho(u)
    fr = {}
    for f in salida.glob("frame-*.png"):
        t = float(re.search(r"-at-([\d.]+)s", f.name).group(1))
        if any(abs(t - x) < 0.011 for x in quiere):
            g = Image.open(f).convert("L").resize(mc.TAM, Image.BILINEAR)
            fr[t] = np.asarray(g, np.float64)
    if len(fr) < len(quiere):
        return False, f"faltan fotogramas del gancho: {len(fr)} de {len(quiere)}"
    return veredicto_gancho(
        mc.gancho(np.stack([fr[t] for t in sorted(fr)]), u), u, GANCHO_MARGEN_LUMA
    )


def veredicto_gancho(g: dict, u: dict, margen: float = 0.0) -> tuple[bool, str]:
    ok = (
        g["luma"] >= u["gancho_luma_min"] + margen
        and g["contraste"] >= u["gancho_contraste_min"]
    )
    extra = f" + {margen} de margen" if margen else ""
    return ok, (
        f"luma {g['luma']}, contraste {g['contraste']}"
        if ok
        else f"gancho oscuro o plano: luma {g['luma']} (mín. {u['gancho_luma_min']}{extra}), "
        f"contraste {g['contraste']} (mín. {u['gancho_contraste_min']}): más opacidad del fondo o un clip más claro"
    )


def render_rapido(proy: Path, ref: str, env: dict, puerta) -> Path:
    """--rapido: a draft render to judge by eye while the full run (high render + critic) goes on behind.
    Draft = same 1080x1920, 30 fps and frames, 3.9 Mbps; SSIM 0.973 vs high (huang-exit). Publishing still needs
    the critic's approval of the final MP4: this file is never published."""
    import medir_cuadros as mc

    import critico

    crudo, rap = (
        proy / "renders" / f"{ref}-rapido-crudo.mp4",
        proy / "renders" / f"{ref}-rapido.mp4",
    )
    r = _run(
        hfversion.npx(
            "render", *RENDER_GPU, "--quality", "draft", "--output", str(crudo)
        ),
        cwd=proy,
        env=env,
    )
    puerta(
        "render",
        r.returncode == 0 and crudo.exists(),
        (re.findall(r"rendered in [^\n]+", r.stdout) or [r.stderr[-300:]])[0],
    )
    puerta("loudnorm", *loudnorm_2pasos(crudo, rap))
    crudo.unlink(missing_ok=True)
    rub = critico.cargar_rubrica(proy)
    u = {k: v for c in rub["criterios"].values() for k, v in c.items() if k != "nombre"}
    puerta(
        "gancho", *veredicto_gancho(mc.gancho(mc.leer_grises(rap), u), u)
    )  # the MP4: the critic's exact limits
    return rap


FPS_BOCETO = 10  # every frame the critic samples (OCR 2 fps, ritmo/cuadros 5 fps, parecido 1 fps)


def render_boceto(proy: Path, ref: str, env: dict, puerta) -> Path:
    """--boceto: the page at FPS_BOCETO plus the full, normalised mix, for the critic BEFORE the one
    final render. The meters pick frame round(i * FPS_BOCETO / fps): the same instants as at 30 fps."""
    crudo, bos = (
        proy / "renders" / f"{ref}-boceto-crudo.mp4",
        proy / "renders" / f"{ref}-boceto.mp4",
    )
    r = _run(
        hfversion.npx(
            "render",
            *RENDER_GPU,
            "--fps",
            str(FPS_BOCETO),
            "--quality",
            "draft",
            "--output",
            str(crudo),
        ),
        cwd=proy,
        env=env,
    )
    puerta(
        "render",
        r.returncode == 0 and crudo.exists(),
        (re.findall(r"rendered in [^\n]+", r.stdout) or [r.stderr[-300:]])[0],
    )
    ok, det = loudnorm_2pasos(crudo, bos)
    if ok:  # same chain as the final: the critic's loudness check must see what ships
        ok, det_pico = asegurar_pico(bos)
        det = f"{det.strip().splitlines()[-1] if det.strip() else ''} · {det_pico}"
    puerta("loudnorm", ok, det)
    crudo.unlink(missing_ok=True)
    return bos


def gancho_temprano(proy: Path, env: dict, u: dict) -> tuple[bool, str]:
    """The hook gate on its own frames only (~54 s on huang-exit-largo), before contrast and OCR."""
    salida = proy / "renders" / "gancho"
    ok, detalle = hoja_previa(proy, env, instantes_gancho(u), salida)
    return gancho_previo(salida, u) if ok else (False, detalle)


def hoja_previa(
    proy: Path, env: dict, ts: list[float] | None = None, salida: Path | None = None
) -> tuple[bool, str]:
    """Frames from the built HTML: what a render would show, without the 3-4 min render."""
    salida = salida or proy / "renders" / "previo"
    shutil.rmtree(
        salida, ignore_errors=True
    )  # frames of an older preview would be read as this one's
    ts = ts or instantes_escena((proy / "index.html").read_text(encoding="utf-8"))
    r = _run(
        hfversion.npx(
            "snapshot",
            "--json",
            "--no-end",
            "--timeout",
            "60000",
            "--at",
            ",".join(map(str, ts)),
            "--output",
            str(salida),
        ),
        cwd=proy,
        env=env,
    )
    try:
        hojas = json.loads(r.stdout).get("contactSheets") or []
    except json.JSONDecodeError:
        hojas = []
    if r.returncode != 0 or not hojas:
        return False, "snapshot sin hoja: " + (r.stderr or r.stdout)[-300:]
    return True, " ".join(hojas)


def social_previo(proy: Path, env: dict) -> tuple[bool, str]:
    """Carousel only: the story cuts the final MP4, which a preview does not have (an old one would be judged)."""
    import social

    try:
        s = social.generar(proy, env, con_historia=False)
    except (social.SocialError, subprocess.CalledProcessError) as e:
        return False, str(e)
    return True, f"carrusel {len(s['carrusel'])} diapositivas"


def fallos_critico(informe: dict, linea) -> list[str]:
    """What the critic found in the last round: alta/media one per line, baja only counted (informe.md has them)."""
    fallos = informe["rondas"][-1]["fallos"]
    bajas = sum(f["severidad"] == "baja" for f in fallos)
    out = [linea(f) for f in fallos if f["severidad"] != "baja"]
    return out + ([f"{bajas} fallos baja: renders/critica/informe.md"] if bajas else [])


def medir_critico(proy: Path, final: Path) -> list[str]:
    """The critic's meters on the final file (no rounds, no re-render)."""
    r = _run(
        [
            PY,
            str(MOTOR / "critico.py"),
            str(proy),
            "--mp4",
            str(final),
            "--solo-revisar",
        ]
    )
    if r.returncode != 0:
        return ["crítico falló: " + r.stderr[-300:]]
    import critico

    inf = json.loads(
        (proy / "renders" / "critica" / "informe.json").read_text(encoding="utf-8")
    )
    return fallos_critico(inf, critico.linea)


def _sha(ruta: Path) -> str:
    with ruta.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def huellas_assets(proy: Path) -> dict[str, str]:
    """Every asset the page can load: raw clips (*.src, up to hundreds of MB) by size, the rest by content.
    shortcut: a raw clip replaced by another of the exact same size is missed; hash it too if that bites."""
    return {
        f.relative_to(proy).as_posix(): (
            f":{f.stat().st_size}" if f.suffix == ".src" else _sha(f)
        )
        for f in sorted((proy / "assets").rglob("*"))
        if f.is_file()
    }


def clave_render(proy: Path, huellas: dict[str, str] | None = None) -> str:
    """What the render depends on: the built page and every asset it can load."""
    h = hashlib.sha256((proy / "index.html").read_bytes())
    for rel, huella in (huellas or huellas_assets(proy)).items():
        h.update((rel + huella).encode())
    return h.hexdigest()


def render_por_tramos(
    proy: Path,
    env: dict,
    final: Path,
    crudo: Path,
    cache: Path,
    huellas: dict[str, str],
) -> tuple[str, bool] | None:
    """Re-render only the scenes whose page changed since the last good render and splice them into its
    final MP4 (tramos.py). (the gate's detail, whether the audio changed) on success: with new audio the
    result is written to `crudo` for loudnorm, else straight to `final`. None (reason printed) when the
    whole film must render: no previous render, another HyperFrames, a change it cannot place in time,
    or a failed span."""
    import tramos

    previa = cache.with_name("render-index.html")
    if "--completo" in sys.argv or not (
        cache.exists() and final.exists() and previa.exists()
    ):
        return None
    c = json.loads(cache.read_text(encoding="utf-8"))
    if (
        "assets" not in c
        or c.get("final_sha") != _sha(final)
        or c.get("hf") != (env.get("HF_VERSION") or hfversion.version())
    ):
        return None
    nuevo = (proy / "index.html").read_text(encoding="utf-8")
    try:  # a page this diff does not expect must cost a whole render, never the production
        spans, motivo, audio = tramos.cambios(
            previa.read_text(encoding="utf-8"), nuevo, c["assets"], huellas
        )
        ventanas: list[tuple[float, float]] | None = None
        if spans:
            ventanas, motivo = tramos.ventanas(spans, tramos._plan(nuevo)[0])
        elif spans is not None:
            ventanas, motivo = ([], "") if audio else (None, "sin cambios visibles")
    except (KeyError, ValueError, TypeError) as e:  # JSONDecodeError is a ValueError
        ventanas, motivo, audio = None, f"diff fallido: {e!r}", False
    if ventanas is None:
        print(f"· render completo: {motivo}")
        return None
    t0, partes, fps = time.time(), [], tramos.fps_de(nuevo)
    carpeta, espejo = proy / "renders" / "tramos", tramos.espejo(proy)
    carpeta.mkdir(exist_ok=True)
    try:
        for a, b in ventanas:
            (espejo / "_tramo.html").write_text(
                tramos.recortar(nuevo, a, b), encoding="utf-8"
            )
            out = carpeta / f"{a:.3f}-{b:.3f}.mp4"
            r = _run(
                hfversion.npx(
                    "render",
                    "-c",
                    "_tramo.html",
                    *RENDER_GPU,
                    "--quality",
                    "high",
                    "--start",
                    str(a),
                    "--end",
                    str(b),
                    "--output",
                    str(out),
                ),
                cwd=espejo,
                env=env,
            )
            if r.returncode or not out.exists():
                print(
                    f"· render completo: el tramo {a}-{b} falló: {(r.stdout + r.stderr)[-400:]}"
                )
                return None
            partes.append((a, b, out))
        video, det = final, "sin cambios de imagen"
        if partes:
            video = carpeta / "empalme.mp4"
            ok, det = tramos.empalmar(final, partes, fps, video, "--gpu" in RENDER_GPU)
            if not ok:
                print(f"· render completo: empalme fallido: {det}")
                return None
        if audio:
            # the mix is time-based: 1 fps captures ~1/30 of the frames for the same track
            pista = carpeta / "audio.mp4"
            r = _run(
                hfversion.npx(
                    "render",
                    *RENDER_GPU,
                    "--fps",
                    "1",
                    "--quality",
                    "high",
                    "--output",
                    str(pista),
                ),
                cwd=espejo,
                env=env,
            )
            if r.returncode or not pista.exists():
                print(
                    f"· render completo: el audio a 1 fps falló: {(r.stdout + r.stderr)[-400:]}"
                )
                return None
            ok, det_a = tramos.con_audio(video, pista, fps, crudo)
            if not ok:
                crudo.unlink(missing_ok=True)
                print(f"· render completo: {det_a}")
                return None
            det = f"{det} + {det_a}"
        else:
            video.replace(final)
    finally:
        shutil.rmtree(espejo, ignore_errors=True)
        shutil.rmtree(carpeta, ignore_errors=True)
    lista = ", ".join(f"{a:.1f}-{b:.1f}" for a, b in ventanas) or "ninguno"
    return f"tramos {lista} s: {det} en {time.time() - t0:.0f} s", audio


def clave_critico(proy: Path, final: Path) -> str:
    """The critic reads the final MP4 and the storyboard; the carousel (`social`), the title/description/tags
    (`publicacion`, checked by the static gates) and the DNA are not part of it."""
    sb = json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    for k in ("social", "publicacion", "adn"):
        sb.pop(k, None)
    h = hashlib.sha256(json.dumps(sb, sort_keys=True).encode())
    for f in (MOTOR / "critico.py", MOTOR / "rubrica.json", proy / "rubrica.json"):
        h.update(
            f.read_bytes() if f.exists() else b"-"
        )  # a new meter or threshold = a new report
    return _sha(final) + h.hexdigest()


def render_reutilizable(cache: Path, clave: str, final: Path) -> bool:
    """--auto retries from the failed stage: same page + assets as the last good render = same video."""
    if not (cache.exists() and final.exists()):
        return False
    c = json.loads(cache.read_text(encoding="utf-8"))
    return c.get("clave") == clave and c.get("final_sha") == _sha(final)


def critico_cacheado(proy: Path, final: Path) -> list[str] | None:
    """The last critic report when it was made on this exact MP4 and storyboard (touched, so --auto reads it
    as this round's); None when the critic must run."""
    cache = proy / "renders" / "critica" / "cache.json"
    inf = proy / "renders" / "critica" / "informe.json"
    if not (cache.exists() and inf.exists()):
        return None
    if json.loads(cache.read_text(encoding="utf-8")).get("clave") != clave_critico(
        proy, final
    ):
        return None
    os.utime(inf)
    import critico

    return fallos_critico(json.loads(inf.read_text(encoding="utf-8")), critico.linea)


def critico_en_paralelo(proy: Path, final: Path) -> tuple[list[str], float, bool]:
    """(lines, seconds, reused). Runs while loudness, rhythm and social measure the same final MP4."""
    t = time.monotonic()
    if (fallos := critico_cacheado(proy, final)) is not None:
        return fallos, round(time.monotonic() - t, 1), True
    fallos = medir_critico(proy, final)
    if not any(x.startswith("crítico falló") for x in fallos):
        (proy / "renders" / "critica" / "cache.json").write_text(
            json.dumps({"clave": clave_critico(proy, final)}), encoding="utf-8"
        )
    return fallos, round(time.monotonic() - t, 1), False


def producir(proy: Path, boceto: bool = False, contraste: bool = True) -> dict:
    proy = proy.resolve()
    sb = json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    ref = sb.get("ref") or proy.name
    env = _entorno()
    env["HF_VERSION"] = (
        hfversion.version()
    )  # one production, one version: children inherit it
    todo = {**os.environ, **env}
    hfversion.alinear_core(todo.get("HF_CORE"))
    qa: dict = {
        "ref": ref,
        "hyperframes": {
            "version": env["HF_VERSION"],
            "core": hfversion.version_core(todo.get("HF_CORE")),
            "carve": hfversion.version_carve(todo.get("HF_CARVE")),
        },
        "puertas": [],
    }
    renders = proy / "renders"
    renders.mkdir(exist_ok=True)

    reloj = [time.monotonic()]
    DETALLES.clear()

    def puerta(nombre: str, ok: bool, detalle: str, seguir: bool = False) -> None:
        ahora = time.monotonic()
        qa["puertas"].append(
            {
                "puerta": nombre,
                "ok": ok,
                "s": round(ahora - reloj[0], 1),
                "detalle": detalle.strip()[-600:],
            }
        )
        reloj[0] = ahora
        DETALLES[nombre] = (ok, detalle)
        if not ok:
            print(f"✗ {nombre}: {detalle.strip()}")
        (renders / "qa.json").write_text(
            json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if not ok and not seguir:
            raise SystemExit(f"✗ puerta '{nombre}' fallida")

    # contrast keeps its own step after the build: the critic reads its patch from that gate
    r = _run(
        [PY, str(MOTOR / "construir.py"), str(proy), "--validar", "--sin-contraste"]
    )
    # the three static gates report together: each stop-at-first-failure run costs a full turn
    puerta("storyboard", r.returncode == 0, r.stdout + r.stderr, seguir=True)
    sys.path.insert(0, str(RAIZ / "tools"))
    import medir_parecido

    puerta("repeticion", *medir_parecido.puerta_repeticion(proy), seguir=True)
    import guionista

    puerta("guion", *guionista.puerta_guion(proy), seguir=True)
    import fuentes  # network: only here, never in construir --validar (tests stay offline)

    puerta("fuentes", *fuentes.puerta_fuentes(proy), seguir=True)
    if malas := [p["puerta"] for p in qa["puertas"] if not p["ok"]]:
        raise SystemExit(f"✗ puertas fallidas: {', '.join(malas)}")
    if not (proy / "assets" / "voice.mp3").exists():
        r = _run([PY, str(MOTOR / "voz.py"), str(proy)])
        puerta("voz", r.returncode == 0, r.stdout + r.stderr)
    if (
        proy.name not in puertas.ANTERIORES
    ):  # voz.py leaves its best take when none passes: it does not get built
        import voz

        rotas = voz.pausas_rotas(
            json.loads((proy / "assets" / "words.json").read_text(encoding="utf-8"))
        )
        puerta(
            "pausas",
            not rotas,
            "\n".join(r["detalle"] for r in rotas) or "sin pausas rotas",
        )
    r = _run([PY, str(MOTOR / "construir.py"), str(proy)], env=env)
    puerta(
        "build",
        r.returncode == 0 and "carve (ducking)" in r.stdout,
        r.stdout + r.stderr,
    )
    r = _run(hfversion.npx("lint"), cwd=proy, env=env)
    m = re.search(r"(\d+) error\(s\)", r.stdout + r.stderr)
    puerta(
        "lint",
        bool(m) and m.group(1) == "0",
        m.group(0) if m else r.stdout[-300:] + r.stderr[-300:],
    )
    previo = "--previo" in sys.argv
    exento = proy.name in puertas.ANTERIORES
    muestreo = None
    if previo and not exento:
        import critico

        muestreo = critico.muestreo_previo(
            sb,
            critico.plan_de_html((proy / "index.html").read_text(encoding="utf-8")),
            json.loads((proy / "assets" / "words.json").read_text(encoding="utf-8")),
            instantes_escena((proy / "index.html").read_text(encoding="utf-8")),
        )
        rub = critico.cargar_rubrica(proy)
        u = {
            k: v
            for c in rub["criterios"].values()
            for k, v in c.items()
            if k != "nombre"
        }
        # first and alone: a dark hook found after the full preview cost ~24 min (huang-exit-largo, 18-nov)
        puerta("gancho", *gancho_temprano(proy, env, u))
    if boceto or "--boceto" in sys.argv:
        # no contrast gate: the critic measures contrast on the boceto's own pixels
        bos = render_boceto(proy, ref, env, puerta)
        qa["final"] = str(bos)
        if "--sin-critico" not in sys.argv:  # --auto reads its informe.json to patch
            _, qa["critico_s"], qa["critico_reutilizado"] = critico_en_paralelo(
                proy, bos
            )
        (renders / "qa.json").write_text(
            json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"✓ boceto en {sum(p['s'] for p in qa['puertas']):.0f} s · {bos}")
        return qa
    cuadros = proy / "renders" / "previo"
    # a page the critic already measured on its boceto skips the ~5-10 min audit before the final render
    if not previo:
        if contraste and "--sin-contraste" not in sys.argv:
            puerta("contraste", *auditar_contraste(proy, env))
    elif aprobados_contraste(proy, env)[2]:
        # frames first: the audit skips every scene whose frame already passed byte for byte
        ok_hoja, detalle = hoja_previa(proy, env, muestreo and muestreo["todos"])
        puerta("hoja", ok_hoja, detalle, seguir=True)
        c = auditar_contraste(proy, env, cuadros=cuadros if ok_hoja else None)
        puerta("contraste", *c, seguir=True)
    else:  # nothing to skip: frames and audit side by side (234 + 622 s serial, 22-nov)
        with ThreadPoolExecutor(1) as ex:
            hoja = ex.submit(hoja_previa, proy, env, muestreo and muestreo["todos"])
            c = auditar_contraste(proy, env, cuadros=cuadros, hoja=hoja)
            puerta("contraste", *c, seguir=True)
            ok_hoja, detalle = hoja.result()
            puerta("hoja", ok_hoja, detalle, seguir=True)
    if previo:
        if muestreo and ok_hoja:
            puerta("texto", *texto_previo(proy, sb, muestreo), seguir=True)
        if sb.get("social") and not exento:
            puerta("social", *social_previo(proy, env), seguir=True)
        if malas := [p["puerta"] for p in qa["puertas"] if not p["ok"]]:
            raise SystemExit(f"✗ puertas fallidas: {', '.join(malas)}")
        print(f"✓ previo en {sum(p['s'] for p in qa['puertas']):.0f} s · {detalle}")
        return qa
    if "--rapido" in sys.argv:
        rap = render_rapido(proy, ref, env, puerta)
        print(f"✓ rápido en {sum(p['s'] for p in qa['puertas']):.0f} s · {rap}")
        return qa
    crudo, final, prev = (
        renders / f"{ref}.mp4",
        renders / f"{ref}-final.mp4",
        renders / f"{ref}-preview.mp4",
    )
    huellas = huellas_assets(proy)
    cache_render, clave = renders / "render.json", clave_render(proy, huellas)
    reusar = render_reutilizable(cache_render, clave, final)
    # the carousel does not need the video (only the story does): it is made while the video renders
    car_ex = ThreadPoolExecutor(1)
    car_f = car_ex.submit(social_previo, proy, env) if sb.get("social") else None
    tramo = (
        None
        if reusar
        else render_por_tramos(proy, env, final, crudo, cache_render, huellas)
    )
    if not reusar and not tramo:
        r = _run(
            hfversion.npx(
                "render", *RENDER_GPU, "--quality", "high", "--output", str(crudo)
            ),
            cwd=proy,
            env=env,
        )
    # collected before a failed render gate can end the round with the carousel still writing social/
    carrusel = car_f.result() if car_f else None
    car_ex.shutdown()
    if reusar:
        puerta("render", True, "reutilizado: mismo HTML y assets que el último render")
    elif tramo:
        puerta("render", True, tramo[0])
    else:
        puerta(
            "render",
            r.returncode == 0 and crudo.exists(),
            (re.findall(r"rendered in [^\n]+", r.stdout) or [r.stderr[-300:]])[0],
        )
    qa["hyperframes"]["gpu"] = (
        None if reusar or tramo else gpu_render(r.stdout + r.stderr)
    )
    if qa["hyperframes"]["gpu"] and "NVIDIA" not in qa["hyperframes"]["gpu"]:
        # the PC's per-app GPU preference is keyed to chrome-headless-shell.exe's path, which changes
        # with each HyperFrames Chrome update: the render then silently drops to the iGPU (~2x slower)
        print(
            f"⚠ render en {qa['hyperframes']['gpu']}, no en la NVIDIA: repetir Gráficos > Alto rendimiento "
            "para el chrome-headless-shell.exe nuevo (~/.cache/hyperframes/chrome)"
        )
    if reusar:
        ok_ln, det_ln = True, "reutilizado"
    elif tramo and not tramo[1]:
        # no audio changed: the spliced final keeps the old, already normalised track
        ok_ln, det_ln = True, "audio del render anterior"
    else:
        ok_ln, det_ln = loudnorm_2pasos(crudo, final)
        if ok_ln:
            ok_ln, det_pico = asegurar_pico(final)
            det_ln = f"{det_ln.strip().splitlines()[-1] if det_ln.strip() else ''} · {det_pico}"
    puerta("loudnorm", ok_ln, det_ln)
    crudo.unlink(missing_ok=True)  # 40-60 MB; only input of loudnorm, the final ships
    shutil.copyfile(proy / "index.html", cache_render.with_name("render-index.html"))
    cache_render.write_text(
        json.dumps(
            {
                "clave": clave,
                "final_sha": _sha(final),
                "hf": env.get("HF_VERSION") or hfversion.version(),
                "assets": huellas,
            }
        ),
        encoding="utf-8",
    )
    # the critic (~11 min) measures the final MP4 while the cheaper gates below do too
    ex = ThreadPoolExecutor(1)
    critico_f = (
        ex.submit(critico_en_paralelo, proy, final)
        if "--sin-critico" not in sys.argv
        else None
    )
    r = _run([PY, str(RAIZ / "tools" / "medir_loudness.py"), str(final)])
    lufs = re.search(r"integrado\s*:\s*(-?[\d.]+)", r.stdout)
    pico = re.search(r"Pico real\s*:\s*(-?[\d.]+)", r.stdout)
    ok = (
        bool(lufs and pico)
        and abs(float(lufs.group(1)) + 14) <= 1
        and float(pico.group(1)) < -1
    )
    puerta(
        "loudness",
        ok,
        f"{lufs.group(1) if lufs else '?'} LUFS, pico {pico.group(1) if pico else '?'} dBTP",
        seguir=True,
    )
    r = _run([PY, str(RAIZ / "tools" / "medir_ritmo.py"), str(final), "--max", "2.5"])
    puerta("ritmo", r.returncode == 0 and "✓" in r.stdout, r.stdout, seguir=True)
    _run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(final),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",  # 31 -> 10 s, SSIM 0.988 vs 0.989 against the final (huang-exit, 12-nov)
            "-crf",
            "24",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(prev),
        ]
    )
    pub = sb.get("publicacion") or {}
    publish = {
        "production_ref": ref,
        "video_path": str(final),
        "title": pub.get("titulo", ref)[:100],
        "description": descripcion(sb, proy),
        "tags": pub.get("tags", []),
        "category_id": "27",
        "privacy_status": "private",
        "made_for_kids": False,
        "comentario_fijado": comentario(sb),
        "serie": sb.get("serie"),
    }
    (RAIZ / "data").mkdir(exist_ok=True)
    previo_f = RAIZ / "data" / f"publish_{ref}.json"
    if previo_f.exists():  # what each network received outlives a re-render: omega.cli publicar compares it
        publish["subido"] = (
            json.loads(previo_f.read_text(encoding="utf-8")).get("subido") or {}
        )
    previo_f.write_text(
        json.dumps(publish, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # El ADN se escribe solo si no existe: uno hecho a mano (técnica por bloque) vale más que este
    # genérico, y producir no debe destruir instrumentación (pasó en la 1ª prueba con el #7).
    if sb.get("adn") and not (proy / "adn.json").exists():
        W = json.loads((proy / "assets" / "words.json").read_text())
        dur = round(W[-1]["end"] + float(sb.get("cola_s", COLA_S)))
        (proy / "adn.json").write_text(
            json.dumps(
                {
                    "production_ref": ref,
                    **sb["adn"],
                    "length_s": dur,
                    "blocks": bloques_adn(sb, W),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if (
        carrusel
    ):  # páginas vivas: carrusel (hecho durante el render) + historia (no publica nada)
        import social

        ok_social, det_social = carrusel
        if ok_social:
            try:
                s = social.generar(proy, env, con_carrusel=False)
                det_social += f" · historia {'sí' if s['historia'] else 'no'}"
            except (social.SocialError, subprocess.CalledProcessError) as e:
                ok_social, det_social = False, str(e)
        puerta("social", ok_social, det_social, seguir=True)

    def esperar_critico() -> list[str] | None:
        if critico_f is None:
            return None
        fallos, s, reusado = critico_f.result()
        ex.shutdown()
        qa["critico_s"], qa["critico_reutilizado"] = s, reusado
        (renders / "qa.json").write_text(
            json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return fallos

    if malas := [p["puerta"] for p in qa["puertas"] if not p["ok"]]:
        try:
            esperar_critico()  # its report feeds --auto in the same round
        except Exception as e:  # noqa: BLE001 -- the failed gate is the error to report, not the critic's
            print(f"⚠ crítico falló en paralelo: {e!r}"[:300])
        raise SystemExit(f"✗ puertas fallidas: {', '.join(malas)}")
    qa["borrador_youtube"] = subir_borrador(publish, ref)
    qa.update(
        final=str(final),
        preview=str(prev),
        preview_mb=round(prev.stat().st_size / 2**20, 1) if prev.exists() else None,
    )
    (renders / "qa.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"✓ puertas OK · {final.name} · preview {qa['preview_mb']} MB · YouTube: {qa['borrador_youtube']}"
    )
    if (fallos := esperar_critico()) is not None:
        print(
            f"crítico: {len(fallos)} líneas{' (reutilizado)' if qa['critico_reutilizado'] else ''}"
            " · hoja renders/critica/r0/hoja.jpg"
        )
        for x in fallos:
            print("  " + x)
    return qa


def reglas_fallidas(detalles: dict) -> dict[str, list[str]]:
    """Failed gate -> the exact rules that failed, one per line: "storyboard" alone (26 failed runs on
    13-nov) does not say which rule should become a default or a pre-render gate."""
    out = {}
    for n, (ok, d) in detalles.items():
        if ok:
            continue
        ls = [x.strip() for x in d.splitlines() if x.strip()]
        items = (
            [
                x[4:].strip() for x in d.splitlines() if x.startswith("  - ")
            ]  # StoryboardError list
            or [x.lstrip("✗ ") for x in ls if x.startswith("✗")]
            or ls[-1:]
        )
        out[n] = [x[:200] for x in items[:20]]
    return out


def ronda_medida(qa_f: Path, t0: float) -> dict | None:
    """Seconds of one --auto round, read before the next round overwrites qa.json."""
    if not (qa_f.exists() and qa_f.stat().st_mtime >= t0):
        return None
    q = json.loads(qa_f.read_text(encoding="utf-8"))
    return {
        "s": round(time.time() - t0),
        "puertas": {x["puerta"]: x["s"] for x in q.get("puertas") or []},
        "critico_s": q.get("critico_s"),
    }


def registrar_corrida(
    reg: Path,
    t0: float,
    fallo,
    argv: list[str],
    detalles: dict,
    pendientes: list,
    rondas: list | None = None,
) -> None:
    """One line per run in renders/corridas.jsonl (aggregate: tools/resumen_corridas.py)."""
    linea = {
        "t": int(t0),
        "s": round(time.time() - t0),
        "previo": "--previo" in argv,
        "rapido": "--rapido" in argv,
        "boceto": "--boceto" in argv,
        "auto": "--sin-auto" not in argv,
        "fallo": fallo,
    }
    if reglas := reglas_fallidas(detalles):
        linea["reglas"] = reglas
    if pendientes:
        linea["pendientes"] = [str(x)[:200] for x in pendientes[:20]]
    rondas = [r for r in rondas or [] if r] or [
        r for r in [ronda_medida(reg.parent / "qa.json", t0)] if r
    ]
    if rondas:  # seconds per gate summed over every --auto round, each round kept apart
        linea["puertas"] = {}
        for r in rondas:
            for p, s in r["puertas"].items():
                linea["puertas"][p] = round(linea["puertas"].get(p, 0) + s, 1)
        linea["critico_s"] = round(sum(r["critico_s"] or 0 for r in rondas), 1)
        if len(rondas) > 1:
            linea["rondas"] = rondas
    with reg.open("a", encoding="utf-8") as f:
        f.write(json.dumps(linea, ensure_ascii=False) + "\n")


def producir_auto(proy: Path, critico_: bool = True) -> dict:
    """--auto: mechanical fixes BEFORE the same gates, never instead of them. With the critic on, the
    rounds measure a 10 fps boceto and the full render runs ONCE at the end (each full round cost ~16 min
    on huang-exit-largo); its own critic then measures the file that ships, with no further round."""
    boceto = critico_ and not {"--rapido", "--boceto"} & set(sys.argv)
    if not boceto:
        return _rondas_auto(proy, critico_, False)
    pendiente = None
    try:
        _rondas_auto(proy, critico_, True)
    except SystemExit as e:
        if not PENDIENTES:
            raise  # a gate or a crash with nothing pending: the final would stop the same way
        pendiente = e  # left for a person: render anyway so there is a video to review
    t0 = time.time()
    try:
        qa = producir(
            proy, contraste=False
        )  # the critic measured contrast on the boceto's pixels
    finally:
        RONDAS.append(ronda_medida(proy / "renders" / "qa.json", t0))
    if pendiente is not None:
        raise pendiente
    return qa


def _rondas_auto(proy: Path, critico_: bool, boceto: bool) -> dict:
    import autoarreglo

    bloquean, voz_rehecha = ("alta",), False
    for ronda in range(RONDAS_AUTO + 1):
        t0, fallo, qa = time.time(), None, None
        try:
            qa = producir(proy, boceto=boceto)
        except SystemExit as e:
            fallo = e
        RONDAS.append(ronda_medida(proy / "renders" / "qa.json", t0))
        fallidas = {n: d for n, (ok, d) in DETALLES.items() if not ok}
        informe = None
        inf = proy / "renders" / "critica" / "informe.json"
        # the critic runs in parallel with the last gates: its report counts even when one of them failed
        if critico_ and inf.exists() and inf.stat().st_mtime >= t0:
            import critico

            informe = json.loads(inf.read_text(encoding="utf-8"))
            bloquean = tuple(
                critico.cargar_rubrica(proy).get("severidad_bloquea") or ["alta"]
            )
        if fallo is None and informe is None:
            return qa
        if fallo is not None and not fallidas:
            raise fallo  # not a gate (a crash, a missing file): nothing to fix mechanically
        hechos, pendientes, rehacer_voz = autoarreglo.arreglar(
            proy, fallidas, informe, bloquean
        )
        if fallo is None and not hechos and not pendientes and not rehacer_voz:
            return qa
        rehacer_voz = rehacer_voz and not voz_rehecha
        for h in hechos:
            print(f"🔧 auto {ronda + 1}: {h}")
        if not (hechos or rehacer_voz) or ronda == RONDAS_AUTO:
            PENDIENTES[:] = pendientes
            for x in pendientes:
                print(f"  pendiente: {x}")
            raise SystemExit(
                f"✗ --auto: {len(pendientes)} fallo(s) sin arreglo mecánico tras {ronda + 1} ronda(s)"
                + (" (el último arreglo no se volvió a medir)" if hechos else "")
            )
        if rehacer_voz:
            voz_rehecha = True
            r = _run([PY, str(MOTOR / "voz.py"), str(proy), "--forzar"])
            print(f"🔧 auto {ronda + 1}: voz re-sintetizada ({r.returncode})")
    raise AssertionError("unreachable")


if __name__ == "__main__":
    sys.stdout.reconfigure(
        encoding="utf-8"
    )  # redirected output on Windows is cp1252 (no ✓/✗)
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    t0, fallo = time.time(), None
    try:
        # E2-E5 (errores.json) failed on --sin-subir runs that never called autoarreglo
        if "--sin-auto" not in sys.argv:
            producir_auto(
                Path(sys.argv[1]).resolve(),
                "--sin-critico" not in sys.argv and "--previo" not in sys.argv,
            )
        else:
            producir(Path(sys.argv[1]))
    except SystemExit as e:
        fallo = str(e)
        raise
    finally:  # failed runs and minutes per video: the numbers docs/POLITICA.md asks to compare
        reg = Path(sys.argv[1]) / "renders" / "corridas.jsonl"
        if reg.parent.exists():
            registrar_corrida(reg, t0, fallo, sys.argv, DETALLES, PENDIENTES, RONDAS)
            if (
                fallo
            ):  # the ratchet: a new error class stops here until its cause is fixed
                import errores

                ultima = json.loads(reg.read_text(encoding="utf-8").splitlines()[-1])
                errores.avisar(errores.revisar(errores.reglas_de(ultima)))
