# Cero errores: qué caza cada puerta y qué no

> 6-nov-2026. **PROVISIONAL**: umbrales sin calibrar hasta ~10 notas a ciegas del usuario (`docs/POLITICA.md`).
> Esto no garantiza cero errores: dice qué detecta cada puerta y qué queda para el juicio humano.
> El último paso sigue siendo que el usuario apruebe la vista previa.

**Hallazgo principal.** El `average-401k` publicado está mal maquetado en todos sus fotogramas: 300 px de franja verde
arriba, contenido desplazado y marca cortada en el borde izquierdo. Causa: `"tema": "average 401(k) vs median"`; `tema` es
una clase CSS y no el asunto, y `aspecto: cine` necesita `editorial`. Pasó todas las puertas. Con `tema: "editorial"` un
snapshot sale bien (1, 10 y 20 s). El storyboard está corregido en esta rama; el vídeo publicado no se ha tocado.

## Inventario

Puerta: **P** = plan (`construir --validar`, <1 s) · **M** = medida sobre el MP4 (crítico) · **J** = solo juicio · **—** = no se caza.
"Bloquea" = severidad `alta` o error de validación. Evidencia: `tests/fixtures/average401k/v1`, render real de ese v1, informes del crítico.

| Clase | Defecto | Puerta | Dónde | ¿Bloquea? |
| --- | --- | --- | --- | --- |
| Visual | Maqueta descolocada | P + M | `puertas.tema_valido`, `medir_cuadros.banda_vacia` | sí |
| Visual | Negro | M | `medir_cuadros.negros` | sí |
| Visual | Imagen congelada | M | `medir_cuadros.congelados`, R1 | sí |
| Visual | Gancho oscuro o plano | M | `medir_cuadros.gancho` | sí |
| Visual | Pantalla vacía | P + M | `puertas.pantalla_vacia`, `medir_cuadros.planos` + OCR | sí |
| Visual | Imagen equivocada para la palabra | J | `imagen_es_la_palabra` por escena | sí, si se responde que no |
| Visual | Plano feo, encuadre pobre | J | J6 | según severidad |
| Texto | Texto ilegible, poco contraste | M | L1 | sí en parte (`alta`) |
| Texto | Dos rótulos en el mismo sitio | P | `puertas.rotulos_solapados` | sí |
| Texto | Rótulos que se pisan en cajas separadas | M | `medir_cuadros.colisiones` | sí |
| Texto | Rótulos coincidentes leídos como una línea rota | **—** en OCR | solo el plan, si comparten `top` y tiempo | ver límites |
| Texto | Texto cortado o al borde | M avisa + J | `cortados` | **no**: `media`, 2 de 2 falsos |
| Texto | Bajo la interfaz de Shorts | M | L1 `zona_ui` | no: `baja` |
| Texto | Texto de diseño (subtítulo, rótulo, marca) sobre el del documento | previo + M | `pf.sobre_documento` | sí |
| Texto | Rótulo ilegible | previo avisa + M | L1 (`critico.revisar_previo`) | previo no: 4 avisos en 98 textos de 4 vídeos, el MP4 confirma como mucho 1; MP4 sí |
| Visual | Clip sin mirar, o texto ajeno dentro del clip | P | `broll.hoja_clip` + `puertas.clips_sin_ver` | sí; `visto` es una declaración, no prueba que se mirara |
| Texto | Faltas de ortografía | J | `texto_completo` | sí, si se responde que no |
| Texto | Voz sin subtítulo, texto fugaz | P | `puertas.voz_sin_subtitulo`, `texto_breve` | sí |
| Audio | Pronunciación medida ("401k") | P | `puertas.pronunciacion` | sí |
| Audio | Palabra desconocida o sigla leída como palabra | antes de sintetizar | `puertas.g2p_dudosas` en `voz.py` | sí, salvo `pronuncia_ok` |
| Audio | El audio no dice el guion | M | `medir_guion_audio` + voz limpia (A1) | sí, con dos medidas de acuerdo |
| Audio | Mezcla que hace perder una palabra | M | transcripción + `medir_mezcla` (M1) | sí |
| Audio | Mezcla con % de ventanas bajo 10 dB | M | M1 | no salvo >15 % de un culpable |
| Audio | Loudness y pico | M | M1 | LUFS sí, pico no |
| Audio | Pausa sin puntuación | antes de construir + M | `voz.mejor_toma`, puerta `pausas`, V1 | sí |
| Audio | Pausa tras coma | M | V1 | no: `media` |
| Audio | Voz poco natural, música inadecuada | J / — | sin medidor | no |
| Sincronía | Subtítulos contra voz | M | S1, `alinear_voz` | según severidad |
| Sincronía | Contador antes de la cifra | P | `puertas.contador_adelantado` | sí |
| Sincronía | Documento demasiado breve | P | `puertas.prueba_breve` | sí |
| Datos | Cifra hablada o en pantalla fuera de `cifras` | P | `trazabilidad.sin_fuente` | sí |
| Datos | `cifras` no coincide con su fuente | **J** | `coincide_con_fuente`, sin automatizar | sí, si se responde que no |
| Datos | Fuente poco fiable, cifra sacada de contexto | J | J3, J4 | según severidad |
| Publicación | Cifra del texto fuera de `cifras` | P | `puertas.publicacion` | sí |
| Publicación | "four-oh-one-k" escrito | P | `puertas.forma_hablada_escrita` | sí |
| Publicación | Título poco claro o engañoso | J | J1, J4 | según severidad |
| Social | Título de diapositiva no leído, texto al borde | previo + M | `social.revisar_activos` | sí |
| Social | Historia cortada a media frase | P | `puertas.historia_corte` | sí |
| Social | Historia en negro o congelada | M | `social.revisar_activos` | sí |
| Social | Diseño feo del carrusel | — | nadie lo mira de forma obligatoria | no |

## Resultado por vídeo

Sobre `renders/<ref>-final.mp4`. `alta` = bloquearía. `average-401k` entra en las puertas de plan; el resto está en
`puertas.ANTERIORES` y queda exento al validar, pero el crítico sí lo mediría.

| Vídeo | `alta` en MP4 | ¿Real? | Avisos `media` | Cifras sin trazar (plan) |
| --- | --- | --- | --- | --- |
| average-401k | franja vacía | **real** (visto) | "four oh" oído "for a" | 0 |
| aws-profit | — | | "AWS" oído "oz": **real**, G2P `ˈɔz` | "eight point seven" |
| binance-heist | gancho luma 16 · pausa 0,74 s | gancho visto oscuro, decide el usuario · pausa sin escuchar | 2 palabras | "233" |
| fed-vs-card | — | | cifra del gancho no transcrita, voz a 22 dB: error del reconocedor | "0.25", "82" |
| gdp-annualized | — | | | 0 |
| housing-turn | — | | borde: falso, visto | "417 mil", "thirteen fifty", "4.6" |
| interest-outran-defense | — | | | "1.3 trillion" (x2) |
| interest-vs-defense | pausa 1,08 s | sin escuchar | borde: falso, visto | "twenty", "1.3 trillion" |
| midterm-rally | pausa 0,54 s | sin escuchar | 1 palabra | 0 |
| ronald-wayne | — | | | 0 |
| saving-rate | — | | | "eighty" (x2) |
| **v1** (render real del fixture) | franja, gancho contraste 24,3, pantalla vacía 29,6-30,8 s | reales | | con `cifras` del publicado, 0 |

Sin MP4: `grace-groner`, `read-janitor`. Sin puertas de MP4 medidas allí; su plan da "200 mil" y "1921", "122,400".

**Falsos positivos que bloquearían:** 0 confirmados sobre 11 vídeos. Las 3 pausas y el gancho de `binance-heist` son detecciones
sin escuchar o sin nota del usuario, así que no están confirmadas como defecto. Carrusel e historia: 0 fallos en los 8 vídeos que los tienen.

Plan por vídeo: contador adelantado en `binance-heist` (0,54 s), `fed-vs-card` (0,69), `housing-turn` (1,79), `read-janitor`
(1,03), v1 (0,69); corregido 0,09. Documento breve en `interest-outran-defense`, `midterm-rally`, `ronald-wayne`, v1 (0,90 s).
Palabras desconocidas por Kokoro: Binance, Groner, Ronald. Texto escrito con cifras fuera de `cifras`: 9 de 13 vídeos.

## Validación de cada instrumento

- **Audio contra guion.** Whisper libre escribe "401k" para las dos lecturas y oculta el defecto; con dígitos y símbolos suprimidos
  transcribe "four hundred one K" en una toma real y "four-o-one K" en la publicada. Toma real marcada 2 veces; 0 graves en 11 publicados.
- **Dos medidas antes de bloquear.** Whisper se saltó 1,7 s en la mezcla de `fed-vs-card` y oyó "to" por "two" en limpio. Por eso una
  diferencia solo bloquea si también está en la voz limpia, o si la voz está bajo el fondo en ese punto.
- **Cajas OCR.** RapidOCR infla las cajas grandes: sin recorte daba 18 "choques" en 11 vídeos, 7 mirados y todos falsos
  (título sobre número). Con recorte del 20 %, 0.
- **Pantalla vacía.** Mínimo real de los publicados sin texto: desviación 22. v1 mide 13-15. Umbral 18.
- **Gancho.** Los publicados salvo `binance-heist` van de luma 41,9 y contraste 34,3 hacia arriba; `binance-heist` 16 y 17,4.
- **Franja.** `average-401k` y v1 100 %; el siguiente, `interest-vs-defense`, 76 % (tema de papel). Umbral 90 %: margen corto.
- **Contador y documento.** Calibrados entre v1 malo y v2 corregido, n = 1 par.

## Decisiones con evidencia

- **M1 no bloquea por porcentaje; el umbral de 10 dB no se ha tocado.** Whisper perdió 1 de 136 palabras (0,7 %) en ventanas bajo
  10 dB y 13 de 1042 (1,2 %) en el resto: no hay relación medida. Bloquear por el 5 % pararía 7 de 11 publicados. Un reconocedor
  no es un oído: por eso sigue como aviso `media`, y bloquea si desaparece una palabra que la voz limpia sí dice.
- **V1: el 0,46 s de `average-401k` no bloquea; el límite de 0,45 s sigue igual.** Tras coma: p90 0,48 s, 11 de 79 lo superan en 5 vídeos,
  es cómo Kokoro lee una coma. Sin puntuación: p99 0,15 s, y solo 3 de 945 pasan de 0,45 s. Esos sí bloquean.
- **G2P.** La pipeline real tiene espeak de respaldo: "Roth" no se pierde, se adivina y aquí acierta. Por eso se pide escucharla
  una vez (`pronuncia_ok`) o reescribirla. No es un error de síntesis.
- **`cortados` no bloquea.** Sus 2 avisos en 11 vídeos fueron falsos a la vista.

## Lo que NO se caza

- **Si `cifras` coincide con su fuente.** Ninguna máquina lo comprueba: lo responde el juicio, cifra a cifra, y puede equivocarse.
- **Que el juicio sea correcto.** El checklist prueba que se respondió todo sobre ese archivo, no que la respuesta sea buena.
- **Rótulos coincidentes que el OCR funde en una línea.** En v1, a 21 s, se lee `OFUTHERHEADLINE`; `colisiones` no lo ve. Solo lo para el plan
  si comparten `top` y tiempo. Dos rótulos con `top` distinto que se pisan por su altura y que el OCR funda: sin cubrir. Lo cerraría medir cajas en el DOM.
- **OCR a 2 fps:** un defecto de menos de 1 s de texto puede no repetirse en 2 cuadros.
- **Oído humano:** naturalidad, música, efectos molestos. Una palabra mal pronunciada que Whisper corrija por contexto tampoco salta.
- **Palabras fuera de lista medida:** `PRONUNCIACION` es lista cerrada; un término conocido por el léxico y mal leído pasa si Whisper no lo nota.
- **Vídeos en `puertas.ANTERIORES`:** exentos de las puertas de plan al re-renderizar.
- **Carrusel e historia ya generados antes de esta puerta:** `revisar_activos` corre al generar, no al publicar.
- **Orden del historial:** G-CIERRE y repetición siguen ordenando por mtime, su límite ya documentado. El test de publicados las simula por eso.

## Coste

Medido en este PC, por ronda de crítico: transcripción 3-10 s (la mezcla, y la voz limpia si hay diferencias), cuadros 1-2 s, cajas ~0 s porque
reutilizan el OCR de L1. Generar social: ~10-50 s medidos cargando el modelo por diapositiva; ahora se carga una vez, sin volver a medir.
Plan: despreciable, salvo `voz.py`, que arranca el venv de Kokoro antes de sintetizar (~10 s estimados). Tokens: 1,5 KB más en `juicio.md` en
`average-401k`, más la respuesta del checklist.

Medido el 6-nov (jesse-livermore y copias, PROVISIONAL): el previo pasa de 60-100 s a unos 3 min según carga: hoja 44 s con 31 fotogramas, OCR 61 s con 24, carrusel 20-50 s. Una toma de voz con `speed` cuesta 115-127 s de síntesis (arranca Kokoro por frase) + 5 s de alineado: la primera limpia no añade nada, 3 tomas añaden unos 4 min. Tres tomas del mismo guion difieren (huecos mayores 0,70/0,74/0,72 s), pero ninguna tenía pausa rota: no está medido que otra toma arregle una rota.

Los créditos de clips ya no declarados se quitan solo al construir de verdad un vídeo que no esté en `ANTERIORES`.

## Rondas de juicio antiguas

`juicio_de` exige ahora `checklist.json`: una ronda vieja no aprueba al volver a correr el crítico. Las `aprobacion.json` ya escritas no cambian.
