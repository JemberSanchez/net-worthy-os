"""Edit language per video: which transitions, camera moves, text entrances, effects and music it
uses, chosen so it does not repeat the last videos of the same brand.

Why: the user asked for no repeated sounds or moves between videos. Baseline in docs/RUBRICA.md
(P1, "repeticion"): the videos before this gate shared one transition cycle, one punch-in, one text
entrance and the same motor whoosh/impact/riser.

Flow (construir.py):
    preparar()  -> frozen or new choice (deterministic: sha256 of ref + last videos); swaps effects
    plan()      -> reads sb["_edicion"], puts the resolved presets into PLAN (motor.js only interprets)
    puerta()    -> blocks if the result repeats more than rubrica.json P1.repeticion allows
    registrar() -> writes it to <corpus>/usado.json (full build only, never with --validar)

Exempt: storyboards without `formato` and videos marked `legacy` in usado.json (their re-render must
not change). Manual override: `"edicion": {"transiciones": [...], "camara": [...], "punch": id,
"texto": id, "tipografia": id, "sfx": {"thud": "thud"}, "motor": {"impacto": id}}`, a scene's `cam` or `transicion`,
an explicit `musica.pista`. Overrides are still counted by the gate.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parent
sys.path.insert(0, str(MOTOR.parents[1] / "tools"))

import medir_parecido

ARCHIVO = "usado.json"
SEP_TRANS = 3.0  # s between transitions: a cut is the default, a transition has to mean something
MAX_TRANS = 5


def _tr(
    sale,
    entra,
    ds,
    de,
    es="power2.in",
    ee="power3.out",
    sobria=False,
    reflejo=None,
    reposo=None,
):
    claves = set(sale) | set(entra)
    base = {"scale": 1, "x": 0, "y": 0, "rotation": 0}
    r = {k: base[k] for k in claves if k in base}
    if "filter" in claves:
        r["filter"] = "blur(0px)" if "blur" in str(sale["filter"]) else "brightness(1)"
    return {
        "sale": sale,
        "entra": entra,
        "dur_sale": ds,
        "dur_entra": de,
        "ease_sale": es,
        "ease_entra": ee,
        "reposo": {**r, **(reposo or {})},
        "sobria": sobria,
        "reflejo": reflejo,
    }


_B = "blur(12px)"
_BW = "blur(16px)"
# A hard cut ("corte") is the default and is not listed. Push/whip hide the empty frame with
# -webkit-box-reflect (mirror tile, the classic whip technique): `reflejo` = side for [out, in].
TRANSICIONES = {
    "zoom": _tr(
        {"scale": 1.14, "filter": _B}, {"scale": 1.14, "filter": _B}, 0.12, 0.24
    ),
    "izq": _tr({"x": -150, "filter": _B}, {"x": 150, "filter": _B}, 0.12, 0.24),
    "sube": _tr({"y": -220, "filter": _B}, {"y": 220, "filter": _B}, 0.12, 0.24),
    "push_izq": _tr(
        {"x": -700},
        {"x": 700},
        0.14,
        0.3,
        ee="expo.out",
        sobria=True,
        reflejo=["right", "left"],
    ),
    "push_arriba": _tr(
        {"y": -1240},
        {"y": 1240},
        0.14,
        0.3,
        ee="expo.out",
        sobria=True,
        reflejo=["below", "above"],
    ),
    "inercia_der": _tr(
        {"x": 520},
        {"x": -520},
        0.12,
        0.46,
        es="power3.in",
        ee="power4.out",
        sobria=True,
        reflejo=["left", "right"],
    ),
    "whip_izq": _tr(
        {"x": -860, "filter": _BW},
        {"x": 860, "filter": _BW},
        0.09,
        0.2,
        reflejo=["right", "left"],
    ),
    "whip_baja": _tr(
        {"y": 1500, "filter": _BW},
        {"y": -1500, "filter": _BW},
        0.09,
        0.2,
        reflejo=["above", "below"],
    ),
    "iris": _tr(
        {"clipPath": "circle(0% at 50% 45%)"},
        {"clipPath": "circle(0% at 50% 45%)"},
        0.16,
        0.24,
        ee="power2.out",
        sobria=True,
        reposo={"clipPath": "circle(80% at 50% 45%)"},
    ),
    "cortina": _tr(
        {"clipPath": "inset(0% 0% 0% 100%)"},
        {"clipPath": "inset(0% 100% 0% 0%)"},
        0.14,
        0.26,
        sobria=True,
        reposo={"clipPath": "inset(0% 0% 0% 0%)"},
    ),
    "diagonal": _tr(
        {"clipPath": "polygon(130% 0%, 130% 0%, 130% 100%, 100% 100%)"},
        {"clipPath": "polygon(-30% 0%, 0% 0%, -30% 100%, -60% 100%)"},
        0.15,
        0.28,
        sobria=True,
        reposo={"clipPath": "polygon(-30% 0%, 130% 0%, 130% 100%, -60% 100%)"},
    ),
    "luma_alta": _tr(
        {"filter": "brightness(3.4)"},
        {"filter": "brightness(3.4)"},
        0.1,
        0.26,
        ee="power2.out",
    ),
    "luma_baja": _tr(
        {"filter": "brightness(0.04)"},
        {"filter": "brightness(0.04)"},
        0.12,
        0.26,
        ee="power2.out",
        sobria=True,
    ),
    "continuo": _tr(
        {"scale": 1.1},
        {"scale": 1.1},
        0.14,
        0.3,
        es="power1.in",
        ee="power2.out",
        sobria=True,
    ),
    "giro": _tr(
        {"rotation": -3.5, "scale": 1.22, "filter": "blur(6px)"},
        {"rotation": 3.5, "scale": 1.22, "filter": "blur(6px)"},
        0.11,
        0.24,
    ),
}
LEGADO_TRANS = (
    "zoom",
    "izq",
    "zoom",
    "sube",
)  # the fixed cycle of motor.js before this module


def _cam(mov, a, b, ease="none"):
    return {"mov": mov, "a": a, "b": b, "ease": ease}


# `mov` = closest vocabulary of tools/profundidad.py for the 2.5D clip; a/b = the frame's Ken Burns.
# Each keeps the frame covered (tests/test_edicion.py checks it). Legacy ids keep their legacy values.
CAMARA = {
    "push": _cam(
        "push", {"scale": 1.08, "x": 0, "y": 30}, {"scale": 1.26, "x": 0, "y": -30}
    ),
    "pull": _cam(
        "pull", {"scale": 1.3, "x": 0, "y": -30}, {"scale": 1.08, "x": 0, "y": 30}
    ),
    "izq": _cam(
        "izq", {"scale": 1.3, "x": 90, "y": 0}, {"scale": 1.42, "x": -90, "y": 0}
    ),
    "der": _cam(
        "der", {"scale": 1.3, "x": -90, "y": 0}, {"scale": 1.42, "x": 90, "y": 0}
    ),
    "sube": _cam(
        "sube", {"scale": 1.2, "x": -30, "y": 70}, {"scale": 1.06, "x": 20, "y": -50}
    ),
    "baja": _cam(
        "sube", {"scale": 1.08, "x": 20, "y": -60}, {"scale": 1.2, "x": -30, "y": 70}
    ),
    "diag_asc": _cam(
        "izq", {"scale": 1.24, "x": -80, "y": 100}, {"scale": 1.24, "x": 80, "y": -100}
    ),
    "diag_desc": _cam(
        "der", {"scale": 1.24, "x": 80, "y": -100}, {"scale": 1.24, "x": -80, "y": 100}
    ),
    "arco_izq": _cam(
        "izq",
        {"scale": 1.18, "x": 30, "y": 0, "rotation": -1.2},
        {"scale": 1.18, "x": -30, "y": 0, "rotation": 1.2},
    ),
    "arco_der": _cam(
        "der",
        {"scale": 1.18, "x": -30, "y": 0, "rotation": 1.2},
        {"scale": 1.18, "x": 30, "y": 0, "rotation": -1.2},
    ),
    "deriva": _cam(
        "push", {"scale": 1.1, "x": -20, "y": 10}, {"scale": 1.13, "x": 20, "y": -10}
    ),
    "tenso": _cam(
        "push",
        {"scale": 1.05, "x": 0, "y": 0},
        {"scale": 1.3, "x": 0, "y": 0},
        "power2.in",
    ),
    "asentar": _cam(
        "pull",
        {"scale": 1.32, "x": 0, "y": 0},
        {"scale": 1.08, "x": 0, "y": 0},
        "power3.out",
    ),
}

# Steps: [offset from the hit (s), level (1 = peak zoom, 0 = rest), duration, ease, rotation]
PUNCH = {
    "seco": [[-0.02, 1, 0.07, "power3.out", 0], [0.08, 0, 0.65, "power2.inOut", 0]],
    "rebote": [
        [-0.02, 1.25, 0.06, "power3.out", 0],
        [0.04, 0.85, 0.1, "power2.inOut", 0],
        [0.14, 0, 0.5, "power2.inOut", 0],
    ],
    "doble": [
        [-0.02, 0.5, 0.05, "power3.out", 0],
        [0.14, 1, 0.05, "power3.out", 0],
        [0.3, 0, 0.5, "power2.inOut", 0],
    ],
    "rampa": [[-0.24, 1, 0.24, "power2.in", 0], [0.04, 0, 0.6, "power3.out", 0]],
    "inclinado": [
        [-0.02, 1, 0.07, "power3.out", -0.9],
        [0.1, 0, 0.6, "power2.inOut", 0],
    ],
}

# None = the entrance each scene already writes (legacy). A preset replaces only the generic rises
# (opacity + small x/y) in motor.js `inn`; the special ones (scale 2.2, a card falling) are kept.
TEXTO = {
    "sube": None,
    "mascara": {
        "from": {"clipPath": "inset(0% 0% 100% 0%)", "y": 18, "opacity": 1},
        "to": {"clipPath": "inset(-20% -20% -20% -20%)"},
        "k": 1.3,
    },
    "lateral": {"from": {"x": -46, "opacity": 0}, "to": {}, "k": 1.0},
    "foco": {
        "from": {"scale": 1.05, "opacity": 0, "filter": "blur(9px)"},
        "to": {},
        "k": 1.2,
    },
    "tracking": {
        "from": {"letterSpacing": "0.12em", "opacity": 0},
        "to": {"letterSpacing": "0em"},
        "k": 1.4,
    },
    "corte": {"from": {"opacity": 0}, "to": {}, "k": 0.05},
}

N_TRANS, N_TRANS_SOBRIA, N_CAM = 3, 2, 3
# Same concept, different recording: safe to swap. Sounds with one meaning (caja, reloj) are not.
# Display typeface of the editorial theme (plantilla.tpl, `tipo-<id>`); "serif" is the look every video
# had until 11-nov. Not in DIMS_EDICION: three options cannot clear a repetition window, they only rotate.
TIPOGRAFIA = ("serif", "grotesca", "condensada")
ROLES_CAMBIABLES = ("impacto", "impacto_grande", "riser", "whoosh", "tic", "monedas")


def _clave(ref: str, dim: str, x: str) -> str:
    return hashlib.sha256(f"{ref}|{dim}|{x}".encode()).hexdigest()


def _ordenar(ref: str, dim: str, cands, previas: list[set]) -> list[str]:
    """Never used first, then the longest unused; ties by hash of the ref. `previas`: newest first."""

    def edad(x):
        return next((i for i, s in enumerate(previas) if x in s), len(previas))

    return sorted(cands, key=lambda x: (-edad(x), _clave(ref, dim, x)))


def _archivo(cat: dict, n: str) -> str:
    return cat[n]["commons"].removeprefix("File:")


def _cat_sfx() -> dict:
    import sfx_libre

    return sfx_libre.catalogo()


def cat_musica() -> dict:
    d = json.loads((MOTOR / "musica.json").read_text(encoding="utf-8"))
    return {k: v for k, v in d.items() if not k.startswith("_")}


def elegir(
    sb: dict, previas: list[dict], cat: dict | None = None, musica: dict | None = None
) -> dict:
    """Pure: storyboard + signatures of previous videos (newest first) -> choice. Same input, same output."""
    cat = cat if cat is not None else _cat_sfx()
    musica = musica if musica is not None else cat_musica()
    ref, man = sb.get("ref", ""), sb.get("edicion") or {}
    sobria = sb.get("tema") == "editorial"

    def prev(dim):
        return [set(f.get(dim) or []) for f in previas]

    trans = [k for k, v in TRANSICIONES.items() if v["sobria"] or not sobria]
    e = {
        "semilla": ref,
        "transiciones": man.get("transiciones")
        or _ordenar(ref, "trans", trans, prev("transiciones"))[
            : N_TRANS_SOBRIA if sobria else N_TRANS
        ],
        "camara": man.get("camara")
        or _ordenar(ref, "cam", CAMARA, prev("camara"))[:N_CAM],
        "punch": man.get("punch") or _ordenar(ref, "punch", PUNCH, prev("punch"))[0],
        "texto": man.get("texto") or _ordenar(ref, "texto", TEXTO, prev("texto"))[0],
        "tipografia": man.get("tipografia")
        or _ordenar(
            ref,
            "tipo",
            TIPOGRAFIA,
            [set(f.get("tipografia") or ["serif"]) for f in previas],
        )[0],
    }
    ya: set[str] = set()  # two roles of one video never land on the same recording

    def escoge(rol: str, capa: str | None = None) -> str | None:
        previos = prev("riser") if rol == "riser" else prev("efectos")
        miembros = [
            n for n in cat if cat[n].get("rol") == rol and cat[n].get("capa") == capa
        ]
        libres = [n for n in miembros if _archivo(cat, n) not in ya] or miembros
        if not libres:
            return None
        por_archivo = {_archivo(cat, n): n for n in sorted(libres, reverse=True)}
        a = _ordenar(ref, f"sfx:{rol}", por_archivo, previos)[0]
        ya.add(a)
        return por_archivo[a]

    cambios, pares = dict(man.get("sfx") or {}), {}
    for x in sb.get("sonidos") or []:
        n = x.get("sfx")
        c = cat.get(n) or {}
        if n in cambios or c.get("rol") not in ROLES_CAMBIABLES:
            continue
        par = c.get("par")
        if par in pares:  # another layer of an already swapped recording goes with it
            cambios[n] = next(
                (
                    m
                    for m in cat
                    if cat[m].get("par") == pares[par]
                    and cat[m].get("capa") == c.get("capa")
                ),
                n,
            )
            continue
        nuevo = escoge(c["rol"], c.get("capa")) or n
        if par:
            pares[par] = cat[nuevo].get("par")
        cambios[n] = nuevo
    e["sfx"] = cambios
    mm = man.get("motor") or {}
    e["motor"] = {r: mm.get(r) or escoge(r) for r in ("whoosh", "impacto", "riser")}
    e["musica"] = _elegir_musica(sb, ref, previas, musica)
    return e


def _elegir_musica(
    sb: dict, ref: str, previas: list[dict], musica: dict
) -> dict | None:
    pista = (sb.get("musica") or {}).get("pista") or {}
    if pista.get("commons"):
        return None  # manual
    # the older gate (puerta_repeticion) also rejects the same AUTHOR within VENTANA_SELLOS videos
    recientes = [
        t
        for f in previas[: medir_parecido.VENTANA_SELLOS]
        for t in f.get("musica") or []
    ]

    def autor(titulo: str) -> str | None:
        decl = next(
            (v["autor"] for v in musica.values() if v["commons"] == "File:" + titulo),
            None,
        )
        if decl:
            return decl.lower()
        if (
            "isrc usuan" in titulo.lower()
        ):  # Incompetech's ISRC registrant: Commons omits the name
            return "kevin macleod"
        return medir_parecido._autor_musica(
            {"musica": {"pista": {"commons": "File:" + titulo}}}
        )

    autores = {autor(t) for t in recientes}
    mood = pista.get("mood")
    ok = {k: v for k, v in musica.items() if not mood or mood in v["mood"]}
    ok = {
        k: v
        for k, v in ok.items()
        if medir_parecido._autor_musica({"musica": {"pista": v}}) not in autores
    } or ok
    if not ok:
        return None
    por_titulo = {v["commons"].removeprefix("File:"): k for k, v in sorted(ok.items())}
    t = _ordenar(
        ref, "musica", por_titulo, [set(f.get("musica") or []) for f in previas]
    )[0]
    m = musica[por_titulo[t]]
    desde = int(_clave(ref, "desde", t), 16) % max(1, int(m["dur"] * 0.4))
    return {"commons": m["commons"], "desde": float(desde)}


def errores_manual(sb: dict, cat: dict) -> list[str]:
    man, err = sb.get("edicion") or {}, []
    for clave, val, valido in (
        ("transiciones", man.get("transiciones") or [], TRANSICIONES),
        ("camara", man.get("camara") or [], CAMARA),
        ("punch", [man["punch"]] if man.get("punch") else [], PUNCH),
        ("texto", [man["texto"]] if man.get("texto") else [], TEXTO),
        (
            "tipografia",
            [man["tipografia"]] if man.get("tipografia") else [],
            TIPOGRAFIA,
        ),
        ("motor", list((man.get("motor") or {}).values()), cat),
        ("sfx", list((man.get("sfx") or {}).values()), cat),
    ):
        err += [
            f"edicion.{clave}: {v!r} no existe (válidos: {', '.join(valido)})"
            for v in val
            if v not in valido
        ]
    for k, s in enumerate(sb.get("escenas") or []):
        if (
            s.get("transicion") not in (None, "corte")
            and s["transicion"] not in TRANSICIONES
        ):
            err.append(
                f"escena {k}: transicion {s['transicion']!r} no existe ({', '.join(TRANSICIONES)})"
            )
    return err


# ───────────────────────────── registry ─────────────────────────────
def registro(raiz: Path) -> dict:
    f = Path(raiz) / ARCHIVO
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"videos": []}


def entrada(reg: dict, ref: str) -> dict | None:
    return next((v for v in reg["videos"] if v["ref"] == ref), None)


previas = medir_parecido.previas_registro


def preparar(proy: Path, sb: dict, reelegir: bool = False) -> dict | None:
    """Sets sb["_edicion"] and applies the swaps. None = exempt (legacy path, nothing changes)."""
    if not sb.get("formato"):
        return None
    reg = registro(Path(proy).parent)
    sb["ref"] = sb.get("ref") or Path(proy).name
    fila = entrada(reg, sb["ref"])
    if fila and fila.get("legacy") and not reelegir:
        return None
    if fila and fila.get("eleccion") and not reelegir:
        e = fila["eleccion"]  # frozen: re-rendering must give the same video
    else:
        e = elegir(sb, [v["firma"] for v in previas(reg, sb["ref"], sb.get("marca"))])
    aplicar(sb, e)
    return e


def aplicar(sb: dict, e: dict, cat: dict | None = None) -> None:
    cat = cat if cat is not None else _cat_sfx()
    for x in sb.get("sonidos") or []:
        nuevo = e["sfx"].get(x.get("sfx"))
        if nuevo and nuevo != x["sfx"]:
            if (
                x.get("vol") is not None
            ):  # keep the level the author asked for, relative to the sample
                x["vol"] = round(
                    x["vol"]
                    * cat[nuevo].get("vol", 0.5)
                    / cat[x["sfx"]].get("vol", 0.5),
                    3,
                )
            x["sfx"] = nuevo
    if e.get("musica"):
        sb.setdefault("musica", {})["pista"] = dict(e["musica"])
    sb["_edicion"] = e


# ───────────────────────────── what plan() needs ─────────────────────────────
def _inicio_de_bloques(guion: list[dict]) -> set[int]:
    """Sentence index where each script block starts. A new block = a new idea."""
    out, n = set(), 0
    for g in guion:
        out.add(n)
        n += len(re.findall(r"[.?!]+(?=[\s\"')]|$)", g["texto"].strip()))
    return out


def transiciones(
    sb: dict, esc: list[dict], ed: dict, words: list[dict], fr: list[list[int]]
) -> list[dict]:
    """Hard cut by default. Transition only where the script changes idea (start of a `guion` block,
    >= SEP_TRANS s apart, at most MAX_TRANS) or where a scene asks for it (`transicion`)."""
    bloques = _inicio_de_bloques(sb.get("guion") or [])
    inicios = [words[fr[i][0]]["start"] for i in sorted(bloques) if i < len(fr)]
    out, ult, n = [], -99.0, 0
    for s in esc[1:]:
        pedida = s.get("transicion")
        if pedida == "corte":
            continue
        idea = any(abs(s["en"] - t) < 0.06 for t in inicios)
        if not pedida and not (idea and s["t0"] - ult >= SEP_TRANS and n < MAX_TRANS):
            continue
        tipo = pedida or ed["transiciones"][n % len(ed["transiciones"])]
        n += 0 if pedida else 1
        out.append(
            {
                "t": round(s["t0"], 3),
                "tipo": tipo,
                **{k: v for k, v in TRANSICIONES[tipo].items() if k != "sobria"},
            }
        )
        ult = s["t0"]
    return out


def asignar_camara(fotos: list[dict], esc: list[dict], ed: dict) -> None:
    """Cycles the palette over the layers. Only a scene's `cam` overrides it: `mov` is the legacy
    field, every written storyboard carries it, and honouring it would repeat by construction."""
    i = 0
    for f in fotos:
        if f.get("mov") == "final":
            continue
        s = esc[int(re.match(r"ph(\d+)", f["id"]).group(1))]
        fondo = s.get("fondo")
        manual = (
            s.get("cam")
            if f.get("primer_plano")
            else (fondo.get("cam") if isinstance(fondo, dict) else None)
        )
        cid = manual or ed["camara"][i % len(ed["camara"])]
        i += 0 if manual else 1
        c = CAMARA[cid]
        vieja = f.get("mov")
        f.update(
            cam_id=cid, cam={"a": c["a"], "b": c["b"], "ease": c["ease"]}, mov=c["mov"]
        )
        if f.get("p25d"):  # the file name carries the move
            f["src"] = f["src"].replace(f"-2p5d-{vieja}-", f"-2p5d-{c['mov']}-")


def presets(ed: dict) -> dict:
    return {"punch": PUNCH[ed["punch"]], "texto": TEXTO[ed["texto"]]}


def usos_motor(
    ed: dict, p: dict, vm: dict, base: dict, cat: dict, archivo
) -> list[dict]:
    """The motor's whoosh/impact/riser as real recordings chosen for this video, at the same relative
    level the synthetic file had (`vm` / `base`). A muted one (mezcla.* = 0) does not sound."""

    def uso(rol, t, k):
        n = ed["motor"].get(rol)
        if not n or k <= 0:
            return None
        return {
            "sfx": n,
            "tipo": "golpe",
            "t": round(max(0.0, t), 3),
            "vol": round(cat[n].get("vol", 0.5) * k, 3),
            "motor": rol,
            "archivo": archivo(n, "golpe"),
        }

    out = [uso("whoosh", t - 0.12, vm["whoosh"] / base["whoosh"]) for t in p["cortes"]]
    out += [
        uso("impacto", g - 0.02, vm["impacto"] / base["impacto"]) for g in p["golpes"]
    ]
    out += [
        uso("impacto", t, 0.75 * vm["impacto"] / base["impacto"]) for t in p["impactos"]
    ]
    n = ed["motor"].get("riser")
    if n:  # a riser ends exactly on the hit: it starts its own length before
        dur = float(cat[n].get("dur", 1.0))
        out += [
            uso("riser", g - dur, vm["riser"] / base["riser"])
            for g in p["golpes"]
            if g - dur >= 0.5
        ]
    return [u for u in out if u]


# ───────────────────────────── signature and gate ─────────────────────────────
def firma(p: dict, sb: dict, cat: dict | None = None) -> dict:
    """What the video uses, per dimension. Effects by source FILE: two cuts of one recording repeat."""
    cat = cat if cat is not None else _cat_sfx()
    ed = sb.get("_edicion")
    motor_ef, motor_ri = [], []
    if ed:
        trans = sorted({t["tipo"] for t in p.get("transiciones") or []})
        punch, texto = [ed["punch"]], [ed["texto"]]
    else:
        trans = (
            []
            if p.get("tema") == "editorial"
            else sorted({LEGADO_TRANS[i % 4] for i in range(len(p["cortes"]))})
        )
        punch, texto = ["seco"], ["sube"]
        vm = p.get("vol_motor") or {}
        if vm.get("whoosh", 1) > 0 and p["cortes"]:
            motor_ef.append("motor:whoosh")
        if vm.get("impacto", 1) > 0 and (p["golpes"] or p["impactos"]):
            motor_ef.append("motor:impact")
        if len(p["golpes"]) > 1:
            motor_ef.append("motor:ding")
        if vm.get("riser", 1) > 0 and p["golpes"]:
            motor_ri.append("motor:riser")
    camara = set()
    for f in p["fotos"]:
        if f.get("cam_id"):
            camara.add(f["cam_id"])
        elif f.get("mov") == "final":
            continue
        elif f.get("video") and not f.get(
            "p25d"
        ):  # legacy clip: motor.js only knew push/pull on clips
            camara.add("pull" if f.get("mov") == "pull" else "empuje")
        else:
            camara.add(f.get("mov"))
    sonidos = {u["sfx"] for u in p.get("sonidos") or []}
    pista = ((sb.get("musica") or {}).get("pista") or {}).get("commons")
    return {
        "transiciones": trans,
        "camara": sorted(camara),
        "punch": punch,
        "texto": texto,
        "tipografia": [(ed or {}).get("tipografia") or "serif"],
        "efectos": sorted(
            {_archivo(cat, n) for n in sonidos if cat[n].get("rol") != "riser"}
            | set(motor_ef)
        ),
        "riser": sorted(
            {_archivo(cat, n) for n in sonidos if cat[n].get("rol") == "riser"}
            | set(motor_ri)
        ),
        "musica": [pista.removeprefix("File:")] if pista else [],
    }


def puerta(proy: Path, p: dict, sb: dict) -> list[str]:
    """Reasons to block; empty = passes."""
    reg = registro(Path(proy).parent)
    prev = previas(reg, sb.get("ref") or Path(proy).name, sb.get("marca"))
    return medir_parecido.repeticion_edicion(firma(p, sb), prev)["motivos"]


def registrar(proy: Path, p: dict, sb: dict) -> None:
    raiz = Path(proy).parent
    reg = registro(raiz)
    ref = sb.get("ref") or Path(proy).name
    fila = {
        "ref": ref,
        "marca": sb.get("marca"),
        "firma": firma(p, sb),
        "eleccion": sb["_edicion"],
    }
    actual = entrada(reg, ref)
    if actual:
        reg["videos"][reg["videos"].index(actual)] = fila
    else:
        reg["videos"].append(fila)
    (raiz / ARCHIVO).write_text(
        json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
