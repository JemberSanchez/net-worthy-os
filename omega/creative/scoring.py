"""Cómo se calcula el ÉXITO de un video. Una sola definición, versionada, auditable.

POR QUÉ EXISTE ESTE MÓDULO
--------------------------
Hasta ahora el `success` se tecleaba a mano con la regla `vistas_totales(FB+YT) / 750`. Dos
problemas, y el primero invalida el dataset:

1. **La "vista" de Shorts dejó de significar lo que creíamos.** Desde el 31-mar-2025 YouTube
   cuenta como vista *cualquier reproducción, repetición o scroll-by, sin mínimo de tiempo*. Lo que
   antes era una vista pasó a llamarse **engaged view**. O sea que `success` mezclaba a quien vio
   el video con quien pasó por encima — y `decide` aprendía de esa mezcla.
2. **El alcance es el RESULTADO, no la causa.** Lo que decide si un Short se distribuye es si la
   gente no lo salta: la retención. El alcance que sale de ahí depende además de la lotería del
   seed, así que como señal de aprendizaje con n bajo es mucho más ruidoso.

Benchmark 2026 (referencia externa, no invención): para que el algoritmo empuje un Short de 30-60 s
hace falta ~50 % de retención media. El canal va por 6-16 %.

LA FÓRMULA (v2)
---------------
    success = 0.70 · min(1, retención / 0.50)  +  0.30 · min(1, alcance / 750)

- **70 % retención**: es la palanca y es lo que el canal puede controlar con el guion.
- **30 % alcance**: sigue contando, porque un video que retiene mucho y no llega a nadie tampoco
  sirve — pero no manda.
- Los topes evitan que un outlier de alcance tape una retención mala (justo lo que pasaba antes).

v3 (5-nov-2026): MISMA fórmula, otros datos
-------------------------------------------
- **Mínimo de vistas:** una plataforma solo aporta retención con `MIN_VISTAS`. Con menos, unas
  pocas repeticiones daban 130 % visto y un score alto (housing-turn: 13 vistas -> 0,705). Sin
  ninguna plataforma con el mínimo NO hay score: `MuestraInsuficiente`.
- **Todas las plataformas:** alcance = suma; retención = media ponderada por vistas. En Facebook e
  Instagram es tiempo medio / duración. v2 solo veía YouTube (binance-heist: 0,002 con 195 vistas
  en Meta).
- `score_parts["plataformas"]` guarda cada plataforma por separado, con `se_quedaron` de YouTube
  (engaged views / vistas: 37,5 % frente al 37,9 % de Studio en aws-profit, 33 % frente a 38,5 % en
  gdp-annualized, así que es una aproximación).

QUÉ *NO* HACE
-------------
No convierte v1 en v2. Un `success` v1 y uno v2 **no son comparables**, así que cada outcome guarda
su `score_version`. Comparar entre versiones sin darse cuenta es el mismo fallo que ya se documentó
con `extractor_version` en las predicciones (docs/ESTADO.md).
"""
from __future__ import annotations

import sqlite3

SCORE_VERSION = "v3-plataformas"

# Retención media que el algoritmo pide para empujar un Short de 30-60 s (benchmark 2026).
UMBRAL_RETENCION = 0.50
# Alcance de referencia del canal. Es el 750 de siempre: se conserva para que la parte de alcance
# siga siendo comparable con la intuición acumulada.
ALCANCE_REF = 750

PESO_RETENCION = 0.70
PESO_ALCANCE = 0.30

# PROVISIONAL: por debajo, un par de personas en bucle mueven la media. Sin calibrar (n bajo).
MIN_VISTAS = 30


class MuestraInsuficiente(ValueError):
    """Ninguna plataforma llega a MIN_VISTAS: el vídeo no tiene score, no un score malo."""


def calcular(*, retention_avg: float | None, views: int | None) -> tuple[float, dict]:
    """Devuelve (success, partes). `partes` deja por escrito de dónde sale el número.

    Si no hay retención registrada NO se inventa: se calcula solo con alcance y se marca
    `parcial=True`, porque ese número vale menos y quien lo lea tiene que saberlo.
    """
    partes: dict = {"version": SCORE_VERSION}
    if retention_avg is not None and not (0.0 <= retention_avg <= 1.0):
        raise ValueError(f"retention_avg={retention_avg} fuera de [0,1]: es FRACCIÓN, no porcentaje.")
    if views is not None and views < 0:
        raise ValueError("views no puede ser negativo")

    r_norm = None
    if retention_avg is not None:
        r_norm = min(1.0, retention_avg / UMBRAL_RETENCION)
        partes["retencion"] = round(retention_avg, 4)
        partes["retencion_norm"] = round(r_norm, 4)

    a_norm = None
    if views is not None:
        a_norm = min(1.0, views / ALCANCE_REF)
        partes["views"] = views
        partes["alcance_norm"] = round(a_norm, 4)

    if r_norm is None and a_norm is None:
        raise ValueError("sin retention_avg ni views no hay nada que puntuar")

    if r_norm is None:
        # Solo alcance: la señal débil. Se puntúa, pero avisando.
        partes["parcial"] = True
        partes["motivo"] = "sin retención registrada: solo mide alcance, que incluye scroll-by"
        return round(a_norm, 4), partes
    if a_norm is None:
        partes["parcial"] = True
        partes["motivo"] = "sin alcance registrado"
        return round(r_norm, 4), partes

    partes["parcial"] = False
    score = PESO_RETENCION * r_norm + PESO_ALCANCE * a_norm
    return round(score, 4), partes


def desde_analytics(con: sqlite3.Connection, production_ref: str) -> tuple[float, dict]:
    """Calcula el éxito LEYENDO las analíticas ya registradas de todas las plataformas. Nada de
    teclear el número a mano: el score deja de depender de que alguien recuerde la fórmula."""
    yt = con.execute(
        "SELECT retention_avg, views, engaged_views FROM production_analytics WHERE production_ref=?",
        (production_ref,),
    ).fetchone()
    meta = con.execute(
        "SELECT platform, views, avg_watch_s FROM production_social WHERE production_ref=?",
        (production_ref,),
    ).fetchall()
    if yt is None and not meta:
        raise ValueError(f"no hay analíticas de {production_ref!r}: corre antes `record-analytics`")
    dna = con.execute(
        "SELECT length_s FROM production_dna WHERE production_ref=?", (production_ref,)
    ).fetchone()
    duracion = dna["length_s"] if dna else None

    plataformas: dict = {}
    if yt is not None:
        vistas = yt["views"] or 0
        comprometidas = yt["engaged_views"]
        plataformas["youtube"] = {
            "views": vistas,
            "retencion": yt["retention_avg"],
            "se_quedaron": comprometidas / vistas if comprometidas is not None and vistas else None,
        }
    for fila in meta:
        visto = fila["avg_watch_s"]
        plataformas[fila["platform"]] = {
            "views": fila["views"] or 0,
            "retencion": min(1.0, visto / duracion) if visto is not None and duracion else None,
        }
    for p in plataformas.values():
        p["cuenta"] = p["views"] >= MIN_VISTAS

    total = sum(p["views"] for p in plataformas.values())
    if not any(p["cuenta"] for p in plataformas.values()):
        raise MuestraInsuficiente(
            f"{production_ref}: ninguna plataforma llega a {MIN_VISTAS} vistas ({total} en total)"
        )
    medibles = [p for p in plataformas.values() if p["cuenta"] and p["retencion"] is not None]
    retencion = (
        sum(p["views"] * p["retencion"] for p in medibles) / sum(p["views"] for p in medibles)
        if medibles
        else None
    )
    score, partes = calcular(retention_avg=retencion, views=total)
    partes["plataformas"] = plataformas
    return score, partes
