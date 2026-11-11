# Guiones — crítico de guion (PROVISIONAL)

**Ganador:** `error`

> Half of America says inflation will ruin the holidays. You might be blaming the wrong villain.
> In a new WalletHub survey, fifty-two percent said exactly that.
> But the same survey hid a scarier answer.
> One in four people are still paying off last year's holidays.
> That debt usually lives on a credit card.
> And the Fed says cards that charge interest now average over twenty-two percent.
> Inflation raises the price once.
> A balance you carry raises it again, every single month.
> To be fair, prices really are higher, and a survey measures fears, not receipts.
> Inflation might dent these holidays. So which villain is still sitting on your card?

## Etapa 1 — estructura

| candidato | fallos de puerta | juicio | por qué |
|---|---|---|---|
| `error` | 0 (—) | 13/15 | 'wrong villain' abre a 0 s y se resuelve tarde (~14 s, 22%); un solo villano: la deuda vieja |
| `misterio` | 0 (—) | 11/15 | el misterio se resuelve a ~6 s; despues no queda bucle |

## Etapa 2 — gancho sobre `error`

| candidato | fallos de puerta | juicio | por qué |
|---|---|---|---|
| `error` | 0 (—) | 13/15 | 'wrong villain' abre a 0 s y se resuelve tarde (~14 s, 22%); un solo villano: la deuda vieja |
| `error+g1` | 0 (—) | 13/15 | dato de la noticia + 'wrong villain' sin revelar cual |
| `error+g2` | 0 (—) | 11/15 | 'on your card' revela la respuesta en el gancho |
| `error+g3` | 0 (—) | 11/15 | 'Last Christmas is' da la respuesta; sin el 52% de la noticia |
| `error+g4` | 0 (—) | 10/15 | no casa con 'said exactly that' de la frase 2 |

## Puertas del ganador

- ✓ G-GANCHO: se entiende sin contexto
- ✓ G-TU: espectador en la palabra 10 (≤19)
- ✓ G-CIFRAS: 2 cifras dichas (≤3): fifty-two; twenty-two
- ✓ G-COMODIN: sin frases comodín
- ✓ G-CIERRE: cierre «pregunta»
- ✓ G-LARGO: 109 palabras (85-110) ≈ 35.2 s
- ✓ G-RELLENO: sin relleno
- ✓ G-GIRO: hueco máx. sin giro 9.0 s (≤10 s)
- ✓ G-BUCLE: enlaza por: holiday, inflation, might, villain

## Descartadas (texto completo)

### `misterio`

> A holiday bill could be hiding on your credit card. It isn't for this year.
> A new WalletHub survey says fifty-two percent fear inflation will ruin the holidays.
> But one in four are still paying for last year's.
> On a card charging interest, the Fed's average is over twenty-two percent.
> So the gift you bought last December may still be getting more expensive.
> Inflation raises a price once. Interest keeps raising it.
> To be fair, prices really are higher, and a survey measures fears, not receipts.
> This year's gifts cost more. Is last year's bill still on your card?

### `error+g1`

> Half of America says inflation will ruin the holidays. You might be blaming the wrong villain.
> In a new WalletHub survey, fifty-two percent said exactly that.
> But the same survey hid a scarier answer.
> One in four people are still paying off last year's holidays.
> That debt usually lives on a credit card.
> And the Fed says cards that charge interest now average over twenty-two percent.
> Inflation raises the price once.
> A balance you carry raises it again, every single month.
> To be fair, prices really are higher, and a survey measures fears, not receipts.
> Inflation might dent these holidays. So which villain is still sitting on your card?

### `error+g2`

> Half of Americans fear inflation will ruin the holidays. The real threat is already on your card.
> In a new WalletHub survey, fifty-two percent said exactly that.
> But the same survey hid a scarier answer.
> One in four people are still paying off last year's holidays.
> That debt usually lives on a credit card.
> And the Fed says cards that charge interest now average over twenty-two percent.
> Inflation raises the price once.
> A balance you carry raises it again, every single month.
> To be fair, prices really are higher, and a survey measures fears, not receipts.
> Inflation might dent these holidays. So which villain is still sitting on your card?

### `error+g3`

> Inflation isn't the worst part of your holiday shopping. Last Christmas is.
> In a new WalletHub survey, fifty-two percent said exactly that.
> But the same survey hid a scarier answer.
> One in four people are still paying off last year's holidays.
> That debt usually lives on a credit card.
> And the Fed says cards that charge interest now average over twenty-two percent.
> Inflation raises the price once.
> A balance you carry raises it again, every single month.
> To be fair, prices really are higher, and a survey measures fears, not receipts.
> Inflation might dent these holidays. So which villain is still sitting on your card?

### `error+g4`

> A holiday bill could be hiding on your credit card. It isn't for this year.
> In a new WalletHub survey, fifty-two percent said exactly that.
> But the same survey hid a scarier answer.
> One in four people are still paying off last year's holidays.
> That debt usually lives on a credit card.
> And the Fed says cards that charge interest now average over twenty-two percent.
> Inflation raises the price once.
> A balance you carry raises it again, every single month.
> To be fair, prices really are higher, and a survey measures fears, not receipts.
> Inflation might dent these holidays. So which villain is still sitting on your card?
