"""Reasoning Engine — el KERNEL domain-agnostic de OMEGA.

No sabe nada de video, YouTube ni "contenido". Manipula creencias, predicciones,
evidencia y resultados. Es lo que se reutiliza si el sistema pasa a otro dominio.

Materializa las dos reglas transversales (ver docs/VISION.md):
  - "Every belief is a prediction": toda creencia consecuente se prueba con una
    predicción falsable que tiene método de verificación, criterio de refutación
    y fecha esperada de verificación.
  - "No Silent Learning": la confianza de una creencia SOLO cambia a través de
    update_belief(), que exige una causa y deja un registro append-only.
"""
