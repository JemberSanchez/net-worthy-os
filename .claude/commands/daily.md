---
description: Corre el pipeline diario del sistema (observar + demanda + decidir tema por dinero)
---

Corre el ciclo de observación diario y muéstrame el tema que el sistema recomienda hoy:

1. `python -m omega.cli ingest`        (captura RSS → baseline)
2. `python -m omega.cli youtube-scan`  (demanda real de YouTube → snapshot + historial)
3. `python -m omega.cli signals`        (refresca señales para prevalencia)
4. `python -m omega.cli decide`         (decide el tema ponderando demanda + RPM)

Después de correrlos:
- Muéstrame la decisión (tema ganador, score y por qué) y las 3 descartadas.
- Recuérdame la regla: el término crudo es un QUÉ, no un video — hay que estructurarlo en un CÓMO.
- Si quiero, ofréceme estructurar el tema ganador en un ángulo/guion (o correr `related <tema>`
  para ver la adyacencia).

No cambies código. Esto es solo observación + decisión.
