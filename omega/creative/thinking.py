"""Creative Thinking — el director PIENSA, no solo coordina.

Un pipeline coordina (idea→hook→script). Pensar es un proceso largo: generar, juzgar "esto es
mediocre", DESCARTAR todo, combinar, descubrir, y sostenerlo muchas iteraciones antes de
comprometerse. Esta es la estructura que faltaba — el orquestador que hace pensar juntas a las
piezas ya construidas (combinator, CKB, trade-offs), con memoria de proceso y capacidad de
empezar de cero.

HONESTIDAD BRUTAL: el verdadero "pensar" (proponer un ángulo extraordinario, juzgar que algo es
mediocre y exigir empezar de nuevo) lo hace un LLM. Aquí está la ESTRUCTURA; `think_fn` es el hook
al modelo. A coste $0, think_fn = None y cada paso creativo queda PENDIENTE (modo export-prompt).
Sin modelo, este orquestador es INERTE — y eso, a propósito, demuestra que la profundidad del
pensamiento depende del modelo, no de más heurísticas. Construir aquí heurísticas y llamarlas
"pensar" sería el teatro que el resto del sistema existe para evitar.
"""
from __future__ import annotations
import sqlite3
from typing import Callable

from . import combinator


class ThinkingSession:
    def __init__(self, con: sqlite3.Connection, think_fn: Callable[[str], str | None] | None = None):
        self.con = con
        self.think_fn = think_fn          # callable(prompt)->str ; None => $0 export-prompt
        self.trace: list[dict] = []
        self.pending: list[str] = []      # prompts que requieren un modelo
        combinator.init(con)

    def _think(self, kind: str, prompt: str) -> str | None:
        out = self.think_fn(prompt) if self.think_fn else None
        if out is None:
            self.pending.append(prompt)
            self.trace.append({"kind": kind, "status": "pending-LLM", "prompt": prompt})
            return None
        self.trace.append({"kind": kind, "status": "done", "prompt": prompt, "output": out})
        return out

    def run(self, subject: str, *, max_rounds: int = 3) -> dict:
        """Sostiene un proceso creativo: entender → divergir → imaginar → juzgar → (descartar) → repetir."""
        self._think("understand",
                    f"¿Qué hace ABURRIDA la idea '{subject}'? ¿Qué versión ya se ha hecho mil veces?")
        best = None
        for _ in range(max_rounds):
            framings = [f["treatment"] for f in combinator.generate(self.con, subject, k=5)]
            self.trace.append({"kind": "diverge", "status": "done", "framings": framings})
            angle = self._think(
                "imagine",
                f"Combina '{subject}' con encuadres inesperados {framings} y propón UN ángulo "
                f"extraordinario, no uno normal.")
            verdict = self._think(
                "judge",
                "¿Ese ángulo es extraordinario o sigue siendo mediocre? Si es mediocre, di por qué "
                "y exige empezar de cero con una dirección distinta.")
            if verdict is None:
                break  # sin modelo no puede juzgar -> seguir iterando sería ciego
            best = angle
            # (con un modelo real: parsear el veredicto -> aceptar, combinar o descartar-y-reiniciar)
        executed = sum(1 for t in self.trace if t.get("status") == "done" and t["kind"] != "diverge")
        inert = self.think_fn is None
        return {
            "subject": subject,
            "trace": self.trace,
            "executed_think_steps": executed,
            "pending_llm_steps": len(self.pending),
            "best": best,
            "note": ("ESTRUCTURA construida, 0 pasos de pensamiento ejecutados: SIN UN MODELO, "
                     "esto es inerte. La profundidad del pensar la pone el LLM, no más código."
                     if inert else "sesión ejecutada con un modelo"),
        }
