"""Resultado común de todos los algoritmos y contador de métricas.

Todos los algoritmos devuelven lo mismo (solución, costo, nodos, tiempo),
así se pueden comparar en una sola tabla.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from src.modelos import Asignacion, Horario, Instancia
from src.reglas import Ocupacion, primera_violacion


class Metricas:
    """Cuenta nodos y verificaciones de reglas, y mide el tiempo."""

    def __init__(self) -> None:
        self.nodos = 0            # estados válidos generados (nodos del árbol)
        self.verificaciones = 0   # veces que se revisaron las reglas duras
        self.inicio = time.perf_counter()

    def verificar(self, inst: Instancia, ocup: Ocupacion, a: Asignacion) -> tuple[str, str] | None:
        self.verificaciones += 1
        return primera_violacion(inst, ocup, a)

    def tiempo(self) -> float:
        return time.perf_counter() - self.inicio


@dataclass
class Resultado:
    algoritmo: str
    horario: Horario | None
    costo: float | None
    desglose: dict
    nodos: int
    verificaciones: int
    tiempo: float
    completo: bool            # True si recorrió TODO el espacio (garantiza el óptimo)
    historial: list[float] = field(default_factory=list)   # costo por iteración (aprendizaje/SA)
    arbol: object | None = None                             # ArbolBusqueda si se registró
    notas: str = ""

    @property
    def encontro_solucion(self) -> bool:
        return self.horario is not None

    def fila(self) -> dict:
        """Fila para la tabla comparativa."""
        return {
            "algoritmo": self.algoritmo,
            "solución": "sí" if self.encontro_solucion else "no",
            "costo": self.costo if self.costo is not None else "-",
            "nodos": self.nodos,
            "verificaciones": self.verificaciones,
            "tiempo (s)": round(self.tiempo, 4),
            "exploró todo": "sí" if self.completo else "no",
        }
