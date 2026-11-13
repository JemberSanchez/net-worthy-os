# Qué genera vistas extraordinarias y seguidores (13-nov-2026)

Complementa `docs/VIRALIDAD.md` (estudio de 39 despegues del nicho). Aquí: fuentes externas + datos
propios de `data/omega.sqlite`. Etiqueta: **[oficial]** = YouTube/Meta, **[blog]** = marketing sin
método publicado (orientativo), **[propio]** = nuestra DB, n pequeño → PROVISIONAL.

## 1. Lo que dicen las plataformas

- **[oficial] YouTube Shorts:** señales publicadas = clics, tiempo visto, encuestas, compartidos,
  likes, dislikes. Studio muestra "Viewed vs swiped away" (nuestro `se_quedaron`). Los seguidores NO
  están en la lista de señales del feed: un canal de 0 subs puede explotar.
- **[oficial] Instagram (Mosseri, ene-2025):** top 3 señales = tiempo visto, likes/alcance,
  **envíos (DM)/alcance**. Los envíos pesan algo más para llegar a NO seguidores. El "3-5×" que
  circula no tiene fuente primaria.
- **[oficial] YouTube "inauthentic content" (15-jul-2025):** renombra la regla de contenido repetitivo;
  afecta a la **monetización**, no prohíbe. Riesgo: vídeos de una sola plantilla con cambios mínimos.
  Nuestro `medir_parecido` (< 0,6) ya apunta aquí: mantenerlo.
- **[blog]** 50-60 % del abandono en los 3 primeros s; objetivo > 70 % al segundo 1. Sin muestra publicada.

## 2. Lo que dicen NUESTROS datos (lo más útil del documento)

### 2.1 El gancho NO es nuestro problema; el medio sí [propio, n=7 con curva]

Retención relativa de YouTube (`production_retention`, 1.0 = media de Shorts de esa duración):

| Vídeo           | 10 % | 50 %     | 100 % | Score |
| --------------- | ---- | -------- | ----- | ----- |
| gdp-annualized  | 1,38 | **0,94** | 0,62  | 0,67  |
| buffett-deficit | 1,13 | **0,83** | 0,30  | 0,64  |
| midterm-rally   | 1,23 | **0,80** | 0,45  | 0,97  |
| jesse-livermore | 1,27 | 0,64     | 0,45  | 0,82  |
| ronald-wayne    | 1,14 | 0,63     | 0,34  | 0,86  |
| aws-profit      | 1,05 | **0,27** | 0,18  | 0,62  |
| average-401k    | 1,00 | **0,25** | 0,08  | 0,42  |

Todos arrancan ≥ 1,0 al 10 %: el gancho funciona. Los que pierden **se desploman a mitad** (0,25)
mientras los buenos aguantan ≥ 0,63. Hipótesis: falta un segundo giro/pregunta abierta hacia el 40-60 %.
La rúbrica pide "giro cada 8-10 s" pero nadie lo MIDE sobre la curva real.

### 2.2 Nadie comparte ni comenta [propio]

Facebook + Instagram, totales: **3.817 vistas → 2 compartidos, 3 guardados, 0 comentarios**.
Likes/vista: FB 0,37 %, IG 1,6 %. Benchmark de despegues (VIRALIDAD §3.3): 1-3,7 %.
Compartir es la señal que lleva a NO seguidores (§1). **Este es el cuello de botella de la viralidad**:
el vídeo informa, pero no da motivo para mandárselo a alguien.

### 2.3 Seguidores: no lo medimos

`production_analytics` no guarda `subscribersGained`. Sin eso no se puede saber qué formato convierte.

## 3. Seguidores [blog, orientativo]

- Shorts convierten 0,1-0,3 subs por cada 100 vistas; > 0,5 % es bueno, > 1 % fuerte.
- Formato **serie** (mismo título reconocible, episodio N) convierte más que vídeos sueltos
  (cifra "+67 %" sin verificar). Lógica: seguir solo tiene sentido si esperas el siguiente.
- Enlazar a vídeo largo ("related video") convierte mejor que pedir "suscríbete".
- Volumen: se citan 220-300 Shorts antes de despegar en serio. Llevamos ~19.

## 4. Qué haría (por orden, cada uno con su métrica)

1. **Diseñar para compartir.** Cada guion cierra con algo que se manda: cifra "no me lo creo",
   comparación con el espectador ("tu 401k vs el suyo"), o pregunta polémica que pide comentario.
   Métrica: compartidos/alcance y comentarios en Meta (ya se miden en `production_social`).
2. **Arreglar el medio del vídeo.** Segundo giro obligatorio entre el 40 y el 60 % (revelación,
   "pero aquí viene lo raro"). Métrica: retención relativa al 50 % ≥ 0,6 (hoy 3 de 7 la fallan).
3. **Serie de personajes con nombre fijo** (ej. "Money Ghosts #N": gente normal/olvidada con
   fortunas o ruinas). Personaje ya gana en nuestros datos (VIRALIDAD §7). Métrica: subs/1.000 vistas.
4. **Medir seguidores:** añadir `subscribersGained` a `analytics-sync` (la Analytics API lo da por vídeo).
5. **Volumen:** 1 al día. Sin intentos no hay outliers; un despegue tarda meses (VIRALIDAD §3.1:
   los despegues tenían 130-350 días).

Lo que NO haría: más producción visual, optimizar duración/título (VIRALIDAD §2), resubir el mismo vídeo.

## Fuentes

- [Everpop: Shorts algorithm, cita del soporte de YouTube](https://everpop.app/blog/youtube-shorts-algorithm-2026-what-actually-matters)
- [Social Media Today: señales de Instagram 2025 (Mosseri)](https://www.socialmediatoday.com/news/instagram-shares-algorithm-2025/738034/)
- [Uppbeat: Mosseri, carruseles y envíos](https://uppbeat.io/blog/creator-news/whats-working-on-instagram-right-now-carousels-and-sends-says-adam-mosseri)
- [Search Engine Journal: política de contenido masivo](https://www.searchenginejournal.com/youtube-targets-mass-produced-content-in-monetization-update/550337/)
- [Social Media Today: aclaración de YouTube](https://www.socialmediatoday.com/news/youtube-clarifies-monetization-update-inauthentic-repeated-content/752892/)
- [Owlclaw: benchmarks de Shorts](https://owlclaw.com/benchmarks/youtube-shorts-benchmarks/) · [Fluxnote: Shorts a suscriptores](https://fluxnote.io/guides/youtube-shorts-to-subscribers-strategy-2026) [blog]
- [BecomeViral: caso canal de finanzas](https://becomeviral.com/blog/faceless-youtube-case-study-finance) [blog]

## 5. Aplicado (13-nov)

- `guionista.py --reglas` (lo que lee el guionista antes de escribir, paso 4 de `/producir`) trae dos
  líneas nuevas: **MITAD** (retención relativa al 50 % de los 2 mejores y 2 peores, con la frase que
  sonaba, leída en vivo de `production_retention`) y **COMPARTIR** (el experimento del punto 4.1).
- Causa raíz comprobada: G-GIRO aprobaba los dos vídeos que se hundieron a mitad, y ninguna variante
  léxica probada los separa (`docs/RUBRICA.md`, 13-nov). Por eso el guionista recibe el resultado medido
  en vez de otra regla de palabras sin validar.
- `analytics-sync` guarda `subs_gained` (suscriptores por vídeo). Primera lectura: 2 en 1.068 vistas,
  los dos de personajes; midterm-rally, 496 vistas y 0 suscriptores.
- Cómo se juzga: retención al 50 % ≥ 0,6 y shares/alcance en Meta en los próximos vídeos, frente a los 7 de §2.1.
