# Rúbrica del crítico — v0.1 · **PROVISIONAL**

> Umbrales de partida, **sin calibrar**. Se calibran con ~10 calificaciones a ciegas del usuario
> (docs/POLITICA.md, regla 1a): cada nota con su queja y su segundo se convierte en un umbral o en
> un criterio nuevo; un umbral que el usuario contradice dos veces se mueve. Hasta entonces, el
> crítico **propone**; no decide publicar.

Los números viven en `video-v2/motor/rubrica.json` (no en el código). Una marca distinta pone su
`<proyecto>/rubrica.json`. Cada fallo sale con **criterio, segundo, escena, severidad, evidencia**
y, si existe una perilla segura del motor, un **parche** (catálogo cerrado `critico.OPS`).

Severidad: **alta** = un espectador lo nota y se va o recibe un dato engañoso; **media** = baja la
calidad percibida; **baja** = pulido. Puntuación de una ronda = alta·3 + media·2 + baja·1, **solo
medidores** (el juicio se reporta aparte para que una ronda sin juicio no parezca mejor).

| Id | Criterio | Cómo se verifica | Umbral v0.1 | Parche |
|---|---|---|---|---|
| G1 | **Gancho** | voz: 1ª palabra (`words.json`); OCR de los fotogramas < 0,8 s; la frase 0 contiene una cifra | voz ≤ 0,6 s · texto antes de 0,8 s · cifra en la frase 0 | juicio: `set escenas.0.titulo.en` |
| G2 | **Re-ganchos** | huecos entre `golpes` del plan (segundos reales) | ≤ 12 s | `golpe` en la palabra del centro del hueco |
| L1 | **Legibilidad** | `tools/medir_texto.py`: cada texto que la escena promete se busca por OCR en SU ventana; tamaño, confianza, **contraste WCAG en el píxel final** y zona de la UI de Shorts — solo en texto **diseñado** (rótulos, aviso, subtítulos mientras se dicen) y en su **mejor** fotograma | 100 % leídos · alto ≥ 1,8 % del cuadro (35 px) · conf ≥ 0,80 · contraste ≥ 3:1 · fuera de y > 84 % y de la columna derecha | `fondo_suave` (escena), `aviso_placa`, `aviso_tam` |
| R1 | **Ritmo visual** | `tools/medir_ritmo.py` (tramo más largo sin cambio) | ≤ 2,5 s | `golpe` (punch-in) dentro del tramo |
| V1 | **Ritmo de voz** | `tools/medir_voz.py`: palabras/min, silencios dentro y entre frases | 150-200 ppm · ≤ 0,45 s dentro · ≤ 0,9 s entre · arranque ≤ 0,6 s | — (re-sintetizar la voz) |
| S1 | **Sincronía** | `tools/medir_voz.py`: palabras con duración 0 o medidas sobre silencio (energía real de la voz) | ≥ 95 % medidas | — (alineamiento) |
| M1 | **Mezcla voz/música** | `tools/medir_mezcla.py`: mezcla − g·voz (retardo y ganancia por mínimos cuadrados) → voz/fondo en 300-3400 Hz por ventana de 0,5 s con voz; cada ventana mala se **atribuye** al efecto que suena en ella (o a la música); `medir_loudness.py` | voz ≥ 10 dB sobre el fondo · ≤ 5 % de ventanas tapadas · −14 ±1 LUFS · pico < −1 dBTP | `musica_volumen`, `sfx_vol`; efectos del motor: se reporta |
| D1 | **Datos + aviso YMYL** | cifras del guion con `cifras[].fuente` (URL); aviso presente y legible (L1) | todas con fuente · aviso legible | `aviso_*` |
| P1 | **Parecido con vídeos previos** | `tools/medir_parecido.py` contra los proyectos de la misma `marca`: dHash por segundo, trigramas del guion, secuencia de tipos de escena, recursos con licencia compartidos | visual ≤ 0,30 · guion ≤ 0,20 · estructura ≤ 0,85 · recursos ≤ 0,25 | — (variar el storyboard) |
| J1-J6 | **Juicio** (Claude/persona sobre fotogramas clave + guion): gancho que se entiende, imagen = palabra, exactitud contra la fuente, honestidad, cierre con UNA dicotomía, acabado | `renders/critica/rN/juicio.md` → `juicio.json` | — | `set` en rutas permitidas |

## Validación de cada instrumento (antes de creerle)

| Medidor | Caso conocido | Resultado |
|---|---|---|
| `medir_texto` (OCR) | texto sintético 60 px blanco/negro · 16 px · gris 60 sobre 55 | se lee · no se lee · no se lee |
| `medir_texto` (contraste) | blanco/negro, gris 70/55, oro sobre blanco (razones WCAG teóricas 19,8 / 1,26 / 1,40) | 19,8 / 1,26 / 1,40 |
| `medir_texto` | **límite descubierto**: gris 70 sobre 55 (1,3:1, ilegible) → RapidOCR lo lee con 0,98 | el OCR lee mejor que una persona: por eso el contraste se mide aparte; "OCR lo lee" no certifica nada |
| `medir_texto` | #7 sin filtro de texto diseñado: 631 "fallos", 95 % cuerpo del periódico y certificados | con filtro (tiempo + palabras): 22, todos reales |
| `medir_mezcla` | voz y música REALES del #7 mezcladas a relación conocida, ganancia 0,7, retardo 2,3 ms, AAC 192k | retardo y ganancia exactos; mediana por ventana con error < 0,4 dB (28,0→27,8 · 18,4→18,3 · 8,0→7,8) |
| `medir_voz` | `words.json` del #7 trae "This" en 0,42-0,42 s (el alineador no lo midió) | lo encuentra; además, 5/5 palabras de duración 0 son **inicio de frase** (patrón del alineador, ver abajo) |
| `medir_mezcla` (culpable) | #7, 2,5-3,0 s: se culpó a la caja (1ª de la lista), se bajó 6 dB y la ventana no se movió (−29,9 → −30,0 dB) | ahora se culpa al efecto con más energía en banda (WAV × volumen): el whoosh del corte mete ~26.000× más que la cola de la caja |
| Crítico completo (#7) | ronda 0 → 1 con parches de medidores + juicio | 26 → 15 fallos, puntuación 39 → 22, texto esperado leído 93,5 → 96,8 %, pasa la puerta WCAG y la de pico; **falso positivo**: "SELL" (botón tachado) no lo lee el OCR y una persona sí |
| `medir_parecido` | storyboard contra sí mismo = 1; recodificación JPEG q40 del mismo fotograma ≤ 10 bits | ✓ (tests) · #7 vs #8: visual 0,14, guion 0,0, estructura 0,70, **recursos 0,29** (3 clips de Pexels y 1 certificado repetidos) |

## Lo que la rúbrica NO mide todavía
- Si la historia **engancha** (solo juicio; el medidor real es la retención publicada).
- Exactitud semántica de cada cifra contra su fuente: el juicio la revisa; no hay verificador automático.
- Calidad de la voz (naturalidad); la música como elección estética.

## Calificaciones del usuario (calibración)
| Fecha | Pieza | A/B a ciegas | Veredicto del usuario | ¿Coincide el crítico? | Comentario del usuario |
|---|---|---|---|---|---|
| 28-oct | #7 Ronald Read | A = ronda 2 del crítico (puntuación 10) · B = original (39) | **A mejor**, "sí hay mejoría" | **Sí** (1/1) | "todavía puede mejorar mucho más en temas creativos, en lo que cuenta y cómo lo cuenta" → la rúbrica no mide guion ni narrativa: hueco J1-J5 sin medidor |

n = 1: PROVISIONAL, no mueve umbrales todavía (POLITICA regla 2).

## Calibración pendiente (cómo se hace)
1. El usuario califica a ciegas (1-10 + queja con segundo) ~10 vídeos/rondas.
2. Se cruza cada queja con los fallos del crítico en ese segundo: acierto, falso positivo, omisión.
3. Se mueven umbrales/severidades; versión nueva de `rubrica.json`; se repite. La meta del
   hito (POLITICA): que el crítico coincida con el usuario en piezas que no ha visto.
