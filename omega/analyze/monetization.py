"""Valor de monetización por sub-nicho (RPM). Reponera la demanda: no todas las vistas valen
igual en dinero. Dentro de finanzas, el RPM varía 5-10x por sub-tema (seguros/hipotecas/impuestos
pagan muchísimo más que crypto). Esto hace que 'decide' rankee por DINERO potencial, no solo vistas.

HONESTO: son PRIORES declarados, sacados de rangos públicos de RPM por keyword de anunciante —
NO una predicción de ingresos de un video no publicado (eso sería el Viral Engine). El prior se
CORRIGE cuando haya videos publicados con RPM real medido (record-outcome). Es 'source reliability'
pero para dinero: un dato honesto que se refina, no un número inventado con decimales.
"""
from __future__ import annotations
import re

# RPM estimado (USD) por sub-nicho de finanzas EN. Priores, se recalibran con datos reales.
RPM_TIERS = {
    # ultra ($30-70): productos que los anunciantes pujan más caro
    70: ["insurance", "mortgage", "refinance", "loan", "loans", "credit card", "credit cards",
         "attorney", "lawyer", "tax", "taxes", "forex", "annuity", "wealth management"],
    # alto ($15-30): inversión "seria"
    25: ["investing", "invest", "stocks", "stock market", "retirement", "401k", "roth",
         "dividends", "dividend", "index fund", "etf", "brokerage", "real estate", "reit"],
    # medio ($8-15): finanzas personales aspiracionales (baseline del nicho)
    12: ["personal finance", "budget", "budgeting", "saving", "save money", "passive income",
         "side hustle", "financial freedom", "build wealth", "money habits", "net worth"],
    # volátil/bajo + riesgo de políticas ($4-12): crypto
    8:  ["crypto", "cryptocurrency", "bitcoin", "btc", "ethereum", "eth", "altcoin", "altcoins",
         "memecoin", "nft", "defi", "xrp", "dogecoin", "solana", "ipo"],
}

# keyword -> rpm, las frases largas primero (match específico gana a palabra suelta)
_LOOKUP = sorted(((kw, rpm) for rpm, kws in RPM_TIERS.items() for kw in kws),
                 key=lambda x: -len(x[0]))
_BASELINE = 12          # nicho medio si no matchea nada
_MAX_RPM = max(RPM_TIERS)


def rpm_prior(text: str) -> int:
    """RPM $ estimado del texto (term + ejemplo): el keyword más específico que aparezca, o baseline."""
    t = (text or "").lower()
    for kw, rpm in _LOOKUP:
        if re.search(rf"\b{re.escape(kw)}\b", t):
            return rpm
    return _BASELINE


def monetization_score(text: str) -> float:
    """RPM normalizado a [0,1] como feature del Decision Engine."""
    return round(rpm_prior(text) / _MAX_RPM, 3)
