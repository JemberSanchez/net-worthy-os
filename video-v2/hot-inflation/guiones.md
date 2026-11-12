# Guiones — crítico de guion (PROVISIONAL)

**Ganador:** `misterio`

> The government agency that tracks your prices just released an inflation report with a hole in it.
> Prices rose zero point four percent in one month.
> But the yearly inflation rate everyone quotes isn't there.
> Not late. Missing.
> Last October, the government shut down, and nobody collected prices.
> So this October has nothing to compare against.
> The Fed reads the short trend instead: core prices near three point seven percent a year.
> That's why officials talk about a December hike.
> Honest part: one hot month is noisy, and today's yearly figures are estimates.
> For you, borrowing could get pricier first.
> Watch next month's report: the hole closes.

## Etapa 1 — estructura

| candidato | fallos de puerta | juicio | por qué |
|---|---|---|---|
| `misterio` | 0 (—) | 13/15 | Una idea: falta el dato anual. El agujero se plantea a 3 s y la causa llega a los 12 s; cierre retoma 'hole' y 'report' |
| `error` | 0 (—) | 10/15 | Da la ausencia en el gancho y la causa enseguida; el bucle dura poco |

## Etapa 2 — gancho sobre `misterio`

| candidato | fallos de puerta | juicio | por qué |
|---|---|---|---|
| `misterio` | 0 (—) | 13/15 | Una idea: falta el dato anual. El agujero se plantea a 3 s y la causa llega a los 12 s; cierre retoma 'hole' y 'report' |
| `misterio+g1` | 0 (—) | 13/15 | Agujero concreto a 3 s; causa a los 12 s; cierre retoma hole/report |
| `misterio+g2` | 0 (—) | 12/15 | Dice 'missing' en el gancho: adelanta el giro de los 8 s |
| `misterio+g3` | 1 (G-BUCLE) | 10/15 | Da la causa (mes no contado) en el gancho: mata el bucle |

## Puertas del ganador

- ✓ G-GANCHO: se entiende sin contexto
- ✓ G-TU: espectador en la palabra 6 (≤19)
- ✓ G-CIFRAS: 2 cifras dichas (≤3): zero point four; three point seven
- ✓ G-COMODIN: sin frases comodín
- ✓ G-CIERRE: cierre «imperativo»
- ✓ G-LARGO: 107 palabras (85-110) ≈ 34.5 s
- ✓ G-RELLENO: sin relleno
- ✓ G-GIRO: hueco máx. sin giro 8.7 s (≤10 s)
- ✓ G-BUCLE: enlaza por: hole, report

## Descartadas (texto completo)

### `error`

> Most people check one inflation number, the yearly rate, and this month it simply does not exist.
> The Bureau of Labor Statistics said prices rose zero point four percent in October.
> Your headline yearly rate? Blank.
> A year ago, a government shutdown stopped the price collectors cold.
> No prices then means no comparison now.
> So the Fed watches the three-month trend: core near three point seven percent a year.
> That keeps a December rate hike on the table.
> The honest part: one month can mislead, and every yearly number you read today is an estimate.
> Next month the yearly inflation number returns. Check it before you borrow.

### `misterio+g1`

> The government agency that tracks your prices just released an inflation report with a hole in it.
> Prices rose zero point four percent in one month.
> But the yearly inflation rate everyone quotes isn't there.
> Not late. Missing.
> Last October, the government shut down, and nobody collected prices.
> So this October has nothing to compare against.
> The Fed reads the short trend instead: core prices near three point seven percent a year.
> That's why officials talk about a December hike.
> Honest part: one hot month is noisy, and today's yearly figures are estimates.
> For you, borrowing could get pricier first.
> Watch next month's report: the hole closes.

### `misterio+g2`

> Your government just published an inflation report with its most important number missing.
> Prices rose zero point four percent in one month.
> But the yearly inflation rate everyone quotes isn't there.
> Not late. Missing.
> Last October, the government shut down, and nobody collected prices.
> So this October has nothing to compare against.
> The Fed reads the short trend instead: core prices near three point seven percent a year.
> That's why officials talk about a December hike.
> Honest part: one hot month is noisy, and today's yearly figures are estimates.
> For you, borrowing could get pricier first.
> Watch next month's report: the hole closes.

### `misterio+g3`

> The agency behind your inflation number just admitted one month of prices never got counted.
> Prices rose zero point four percent in one month.
> But the yearly inflation rate everyone quotes isn't there.
> Not late. Missing.
> Last October, the government shut down, and nobody collected prices.
> So this October has nothing to compare against.
> The Fed reads the short trend instead: core prices near three point seven percent a year.
> That's why officials talk about a December hike.
> Honest part: one hot month is noisy, and today's yearly figures are estimates.
> For you, borrowing could get pricier first.
> Watch next month's report: the hole closes.
