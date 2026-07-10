# Calibración del Short S3 contra `voz-short-03.mp3`

> Medido, no estimado. Reproducible: el método está aquí y el audio en `data/voz-short-03.mp3`
> (gitignored). Origen: `CapCut/Videos/0709/0709.MP3` — TTS "Firme Pilot", 24.03 s.

## Por qué hubo desfase

La primera versión del renderizador **repartía** los subtítulos proporcionalmente sobre cada tramo,
como si se hablara a ritmo de metrónomo. Y los tres cortes eran mi estimación (5.4 / 18.2 / 20.8).
Contra el audio real:

| Corte | Mi estimación | Medido | Error |
|---|---|---|---|
| Empieza la curva | 5.40 s | **5.94 s** | 0,54 s adelantada |
| Nº dorado | 18.20 s | **15.99 s** | 2,21 s tarde |
| Entra el CTA | 20.80 s | **22.44 s** | 1,64 s adelantado |

Y un fallo de narrativa peor: la curva terminaba de dibujarse en el 15,5 s, pero **la voz dice
"$610,000" en el 11,5 s**. El contador llegaba a la cifra ~4 s después de oírla. El clímax se
deshinchaba.

## Método

1. Decodificar el MP3 (`decodeAudioData`) y sacar la envolvente **RMS en ventanas de 10 ms**.
2. Segmentar: voz = RMS > 5% del pico; silencio = ≥ 250 ms por debajo.
   Resultado **estable** con cualquier umbral entre 3% y 8%: **11 bloques**.
3. **No asumir 1:1** entre bloques y frases. Se verifica por tasa de sílabas:
   el mapeo ingenuo exigía **11,1 sílabas/s** en un bloque (imposible) y 1,27 en otro.
4. Los **bordes de grupo** sí son sólidos (la tasa cuadra entre ellos). Dentro de cada grupo, las
   palabras se reparten sobre el **tiempo de voz real**, saltándose las pausas → la deriva no se
   acumula de un grupo a otro.
5. Tasa global medida: **5,50 sílabas/s** (18,00 s de voz sobre 24,03 s totales).

## Resultado

```
hook  =  5.94   "You put in..."
draw  = 12.80   la curva llega a $610k justo cuando la voz lo dice
curve = 15.99   "That gap?" -> entra el oro
cta   = 22.44   "Could you start..."
spec  = [0.00, 2.15, 4.41]   cada línea de la intro, antes de su frase
```

11 tarjetas de subtítulo, ninguna por debajo de 0,55 s (umbral de legibilidad), ninguna que termine
en palabra funcional, y las cifras fusionadas en un solo token (`$430,000`) con el tiempo del span
hablado completo ("four hundred and thirty thousand dollars").

Una tarjeta se recortó por razones de composición, no de tiempo: `"and that's in today's money,"`
medía 813 px y la curva verde cruza la banda de subtítulos por x≈853 — la cola quedaba *encima* de
la curva. Se dejó en `"in today's money,"`. Los subtítulos no tienen que ser literales; el ancho
máximo está limitado a 620 px para que ninguna futura tarjeta pueda invadir la curva.

## Verificado en el navegador

- Los 8 puntos de control caen sobre la palabra correcta (`t=6.5` → "You put in $180,000";
  `t=16.5` → "That gap? $430,000"; `t=21.4` → "it while you slept").
- El contador marca **$609,985** en `t=12.85`, cuando la voz dice la cifra.
- `drawFrame(t)` recibe exactamente `audioEl.currentTime` (monótono, error < 0,15 s).
- Ningún subtítulo desborda el lienzo (el más ancho: 813 px sobre un límite de 950 px).

## Si cambias de audio

La calibración **se descarta sola** (compara la duración con 24,03 s ± 0,35 s) y el renderizador
exige medir de nuevo: carga el `.srt` de CapCut (lo mejor) o pulsa "Detectar cortes por silencios"
(heurística: las tres pausas más largas). Grabar con los cortes sin medir **está bloqueado**.
