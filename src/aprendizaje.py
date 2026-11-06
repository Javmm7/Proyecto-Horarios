"""Simulación del proceso de aprendizaje (Paso 11).

El sistema no sabe de antemano qué le importa más a la coordinación: ¿los
huecos de los alumnos? ¿las preferencias de los maestros? Eso está en los
pesos w1..w4 de la función de costo. El sistema los APRENDE con retroalimentación:

1. Se le muestran al usuario dos horarios, A y B.
2. El usuario elige el que prefiere (acepta uno, rechaza el otro).
3. Si el sistema opinaba distinto (le daba menor costo al rechazado),
   corrige los pesos con una regla tipo perceptrón:
       w_i <- w_i + tasa * (rasgo_i(rechazado) - rasgo_i(aceptado))
   Es decir: sube el peso de lo que el horario rechazado tenía DE MÁS,
   y baja el peso de lo que el aceptado tenía de más.
4. Se repite. La "concordancia" (qué tanto coincide el sistema con el
   usuario) debe subir con las rondas: eso es la evidencia de aprendizaje.

Para la demostración se usa un USUARIO SIMULADO con pesos ocultos.
En la interfaz web el usuario real puede tomar su lugar.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from itertools import combinations
from pathlib import Path

from src.modelos import Horario, Instancia
from src.reglas import Pesos, costo

NOMBRES_RASGOS = ["huecos", "horarios malos", "desbalance", "preferencias"]


def rasgos(inst: Instancia, horario: Horario) -> list[float]:
    """Vector [huecos, horarios_malos, desbalance, preferencias] de un horario (uno por peso)."""
    _, d = costo(inst, horario)
    return [
        d["huecos (S1)"],
        d["horas extremas (S2)"] + d["misma materia mismo día (S3)"],
        d["desbalance (S4)"],
        d["fuera de preferencia (S5)"] + d["maestros distintos por materia (S6)"],
    ]


def costo_con(pesos: Pesos, r: list[float]) -> float:
    return pesos.w1 * r[0] + pesos.w2 * r[1] + pesos.w3 * r[2] + pesos.w4 * r[3]


@dataclass
class Aprendiz:
    """Ajusta los pesos a partir de comparaciones (aceptado vs. rechazado)."""

    pesos: Pesos = field(default_factory=Pesos)
    tasa: float = 0.1
    margen: float = 0.5     # el aceptado debe ganar por al menos este margen
    minimo: float = 0.05
    historial_pesos: list[list[float]] = field(default_factory=list)
    actualizaciones: int = 0

    def __post_init__(self) -> None:
        self.historial_pesos.append(self.vector())
        self._suma = sum(self.vector())

    def vector(self) -> list[float]:
        return [self.pesos.w1, self.pesos.w2, self.pesos.w3, self.pesos.w4]

    def prefiere(self, rasgos_a: list[float], rasgos_b: list[float]) -> str:
        """Qué horario elegiría el sistema con sus pesos actuales ('A' o 'B')."""
        return "A" if costo_con(self.pesos, rasgos_a) <= costo_con(self.pesos, rasgos_b) else "B"

    def retroalimentar(self, aceptado: list[float], rechazado: list[float]) -> bool:
        """Aprende de una elección del usuario. Devuelve True si tuvo que corregir."""
        if costo_con(self.pesos, aceptado) + self.margen <= costo_con(self.pesos, rechazado):
            self.historial_pesos.append(self.vector())
            return False  # ya opinaba igual que el usuario (con margen): nada que corregir
        nuevos = [
            max(self.minimo, w + self.tasa * (r - a))
            for w, a, r in zip(self.vector(), aceptado, rechazado)
        ]
        # Normalizar para que la suma de pesos no crezca sin límite
        factor = self._suma / sum(nuevos)
        nuevos = [round(w * factor, 4) for w in nuevos]
        self.pesos = Pesos(*nuevos)
        self.actualizaciones += 1
        self.historial_pesos.append(nuevos)
        return True

    def concordancia(self, pares: list[tuple[list[float], list[float], str]]) -> float:
        """Porcentaje de pares en los que el sistema elige lo mismo que el usuario."""
        if not pares:
            return 0.0
        aciertos = sum(1 for a, b, elegido in pares if self.prefiere(a, b) == elegido)
        return 100 * aciertos / len(pares)


@dataclass
class UsuarioSimulado:
    """Usuario con preferencias ocultas (el sistema NO conoce estos pesos)."""

    pesos_ocultos: Pesos

    def elegir(self, rasgos_a: list[float], rasgos_b: list[float]) -> str:
        return "A" if costo_con(self.pesos_ocultos, rasgos_a) <= costo_con(self.pesos_ocultos, rasgos_b) else "B"


def generar_candidatos(inst: Instancia, cantidad: int = 16, iteraciones: int = 150, semilla: int = 7) -> list[Horario]:
    """Genera horarios variados (recocido simulado con pesos al azar) para mostrarlos al usuario."""
    from src.busqueda_heuristica import backtracking_mrv, recocido_simulado

    azar = random.Random(semilla)
    base = backtracking_mrv(inst).horario
    if base is None:
        return []
    candidatos = [base]
    vistos = {frozenset(base.asignaciones)}
    intentos = 0
    while len(candidatos) < cantidad and intentos < cantidad * 4:
        intentos += 1
        # Pesos extremos al azar: cada candidato "prioriza" cosas distintas -> horarios variados
        pesos = Pesos(*(round(azar.choice([0.05, 0.05, 1.0, 5.0]), 2) for _ in range(4)))
        r = recocido_simulado(inst, pesos, inicial=base, iteraciones=iteraciones, semilla=azar.randrange(10**6))
        clave = frozenset(r.horario.asignaciones)
        if clave not in vistos:
            vistos.add(clave)
            candidatos.append(r.horario)
    return candidatos


@dataclass
class ResultadoAprendizaje:
    concordancia: list[float]           # por ronda
    pesos: list[list[float]]            # por ronda
    pesos_ocultos: list[float]
    costo_usuario_antes: float          # qué tan bueno es, PARA EL USUARIO, el horario optimizado con pesos iniciales
    costo_usuario_despues: float        # ... y con los pesos aprendidos
    aprendiz: Aprendiz


def simular_aprendizaje(
    inst: Instancia,
    pesos_ocultos: Pesos | None = None,
    rondas: int = 40,
    semilla: int = 3,
    iteraciones_recocido: int = 3000,
    tasa: float = 0.3,
) -> ResultadoAprendizaje:
    """Simula varias rondas de retroalimentación y mide si el sistema mejora."""
    from src.busqueda_heuristica import recocido_simulado

    azar = random.Random(semilla)
    usuario = UsuarioSimulado(pesos_ocultos or Pesos(w1=1.0, w2=0.5, w3=2.5, w4=3.0))
    aprendiz = Aprendiz(tasa=tasa)
    pesos_iniciales = Pesos(*aprendiz.vector())

    candidatos = generar_candidatos(inst)
    vectores = [rasgos(inst, h) for h in candidatos]
    # Todos los pares posibles, con la respuesta del usuario (para medir concordancia)
    evaluacion = [(vectores[i], vectores[j], usuario.elegir(vectores[i], vectores[j]))
                  for i, j in combinations(range(len(vectores)), 2)]

    concordancia = [aprendiz.concordancia(evaluacion)]
    for _ in range(rondas):
        a, b, elegido = azar.choice(evaluacion)
        aceptado, rechazado = (a, b) if elegido == "A" else (b, a)
        aprendiz.retroalimentar(aceptado, rechazado)
        concordancia.append(aprendiz.concordancia(evaluacion))

    # ¿Los horarios que produce el sistema le gustan más al usuario después de aprender?
    antes = recocido_simulado(inst, pesos_iniciales, iteraciones=iteraciones_recocido, semilla=semilla).horario
    despues = recocido_simulado(inst, aprendiz.pesos, iteraciones=iteraciones_recocido, semilla=semilla).horario
    return ResultadoAprendizaje(
        concordancia=concordancia,
        pesos=aprendiz.historial_pesos,
        pesos_ocultos=[usuario.pesos_ocultos.w1, usuario.pesos_ocultos.w2,
                       usuario.pesos_ocultos.w3, usuario.pesos_ocultos.w4],
        costo_usuario_antes=round(costo_con(usuario.pesos_ocultos, rasgos(inst, antes)), 2),
        costo_usuario_despues=round(costo_con(usuario.pesos_ocultos, rasgos(inst, despues)), 2),
        aprendiz=aprendiz,
    )


def guardar_pesos(pesos: Pesos, ruta: str | Path = "resultados/pesos_aprendidos.json") -> None:
    Path(ruta).parent.mkdir(exist_ok=True)
    Path(ruta).write_text(json.dumps(asdict(pesos), indent=2), encoding="utf-8")


def cargar_pesos(ruta: str | Path = "resultados/pesos_aprendidos.json") -> Pesos:
    """Pesos aprendidos guardados, o los de fábrica si no hay archivo."""
    ruta = Path(ruta)
    if ruta.exists():
        return Pesos(**json.loads(ruta.read_text(encoding="utf-8")))
    return Pesos()
