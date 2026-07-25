# SHORT #7 — RONALD READ: "The janitor who died with $8 million"

> **Secuela de Buffett, elegida por DATOS.** `warren buffett` ganó `decide` y funcionó (record del
> canal). Buffett dijo *"nunca tendrás mi 20%, pero no lo necesitas — es el reloj"*. **Ronald Read lo
> DEMUESTRA:** un conserje sin talento, sin sueldo alto, llegó a $8M solo con tiempo + dividendos
> reinvertidos. `series_potential` del CKB.

## Por qué es MEJOR que Buffett (en los ejes medidos)
- **Personaje más relatable.** Buffett es intocable (genio, billonario) → su CTA "drop your number" no
  generó comentarios (enganche = 0, el problema #1). Read es un **don nadie** → *"¿podría YO?"* = debate.
- **Contraste más visceral:** `A JANITOR.` → `$8 MILLION.` (trabajo vs fortuna).
- **CTA de DEBATE** (mecanismo del tribunal, para comentarios): *"Skill, or just time? Team skill,
  or team time?"* — ataca directamente el enganche 0 de Buffett (1 interacción en 245 vistas).
  ⚠ **Una SOLA dicotomía en voz y pantalla.** Hasta el 25-jul la voz decía *"team discipline or team
  luck"* y la pantalla *"team luck or team time"*: tres etiquetas para dos bandos en los últimos 5s.
  Si le pides a alguien que elija bando y le das tres nombres, no elige — y este CTA existe
  precisamente para generar comentarios.
- **Motor de ritmo (Motion Budget v1) desde el frame 1** (`docs/EXPERIMENTO-RITMO.md`): el hueco del
  gancho lleva la línea de tiempo `0→60 YEARS` entre `A JANITOR.` y `$8 MILLION.`.

## Demanda (2026-07-18, `youtube-scan` / `youtube <q>`)
`ronald read` → top 59k + un **racimo de Shorts de canales PEQUEÑOS** (2.1k / 1.7k / 1.1k / 1.1k / 1.0k…).
Evergreen, personaje, **formato ya probado a nuestro tamaño**. (Descartados: `mike tyson broke` =
demanda de BOXEO, nicho equivocado; `compound interest` = abstracto, sin cara.)

## CIFRAS — TODAS VERIFICADAS (Wikipedia + CNBC, 2026-07-18)
| Dato | Valor | Fuente |
|---|---|---|
| Ronald Read | n. 23-oct-1921, m. 2-jun-2014, **92 años**, Dummerston/Brattleboro VT | Wikipedia |
| Trabajos | gasolinera/mecánico ~25 años + **conserje JCPenney 17 años (1980–1997)** | Wikipedia |
| Fortuna | **~$8 millones**, casi todo en acciones | Wikipedia/CNBC |
| Cartera | **~95 blue-chips** con dividendos (J&J, P&G, CVS, JPMorgan, GE, Dow, Smucker…), multi-sector | Wikipedia |
| Método | **dividendos REINVERTIDOS**, buy-and-hold **décadas**, evitó TECH (círculo de competencia) | Wikipedia |
| Ejemplo real | $2.380 en PG&E (13-ene-1959) → $10.735 al morir (solo el precio; el motor fue reinvertir) | Wikipedia |
| Legados | **$4.8M al Brattleboro Memorial Hospital + $1.2M a la Brooks Memorial Library** + $2M a allegados | Wikipedia |
| Frugalidad | chaqueta con imperdible, Toyota Yaris usado, aparcaba sin parquímetro | Wikipedia |

**Fuentes:** https://en.wikipedia.org/wiki/Ronald_Read_(philanthropist) ·
https://www.cnbc.com/2016/08/29/janitor-secretly-amassed-an-8-million-fortune.html

## La curva (ILUSTRATIVA, como el $100 de Buffett)
NO es su cartera real (desconocida): es la **mecánica** (reinvertir + tiempo). `pmt: 170/mes`,
`years: 60`, `rate: 0.10` (retorno total del S&P con dividendos, NOMINAL) → la serie aterriza en
**$8,007,457** (verificado en `series()`), y la voz dice "eight million". `YOU PAID IN $122,400`
(= $170×12×60) cuenta el "poco a poco". Aviso YMYL declarado en `CFG.aviso`.

## YMYL — lo que este guion hace bien (bloque `honesty`, obligatorio)
- **Survivorship, dicho explícito:** tuvo **60 años sin emergencia** que le obligara a vender — *"that
  is the rare part, not the picking"*. La mayoría con sueldo bajo SÍ tiene que vender.
- **Las blue-chips fallan:** *"some did cut their dividends"* (GE recortó el suyo ~96% en 2018). Por eso
  **diversificó en 95** — no fue una apuesta.
- **Tasa NOMINAL, "before inflation"** en el aviso. No promete replicar; niega la necesidad del $8M.
- **No humilla:** el sujeto es el TIEMPO + el hábito, no el sueldo del espectador.

## Producción
- **Escena PROPIA `portfolio`** (NO la curva de Buffett — [[cada-short-necesita-diferenciador]]): un
  tablero de **95 casillas, una por empresa**, que se van encendiendo con un tick verde a lo largo de
  los 60 años. Cada ~1.15s un dividendo (punto verde) sale de una posición y se ABSORBE en el
  contador = reinvertir. El contador es el HÉROE (el número subiendo es lo que engancha a una
  audiencia de finanzas) y sigue la serie D → aterriza en $8M. Gancho de contraste 2 líneas
  (compartido). Montado en `SHORTS['read-janitor']` + `SCENES.portfolio` + `drawPortfolio()`.
  > Este doc describía una escena `snowball` (bola rodando) hasta el 25-jul: se reemplazó por el
  > tablero en el commit `61cb745` (22-jul) y el doc no se actualizó. Quien lo leyera se imaginaba
  > otro video.
  > **Dos correcciones del 25-jul:** la rejilla era de 7×4=**28** casillas mientras el rótulo decía
  > "95 COMPANIES" (ahora son 19×5=95 reales), y el contador remataba en **$8,007,457** —precisión
  > del modelo, no de la realidad: su cartera real es desconocida y lo documentado es "~$8 millones".
  > Ahora remata en `$8,000,000` vía `CFG.valorFinal`, que además es lo que dice la voz y lo que ya
  > había en `guion.cifras` (antes subtítulo y contador mostraban dos números distintos).
- **Le falta SOLO la VOZ:** `docs/guiones/TTS-read.txt` → CapCut Firme Pilot → `data/voz-short-read.mp3`.
  Al cargarla, el motor calibra todo y la línea de tiempo del ritmo se adapta al timing real.
- Verificado a ojo (gancho + curva + timeline, frames por POST-server). 23 tests del motor verdes.
