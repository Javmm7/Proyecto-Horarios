"""Teorema de flujo máximo (Paso 9): asignar maestros a materias con Edmonds-Karp.

Idea: antes de buscar el horario se decide QUÉ maestro da cada materia a cada
grupo, sin pasarse de las horas de nadie. Esto se modela como una red:

    FUENTE --(horas de la materia)--> [grupo, materia]
           --(horas de la materia)--> [maestro que puede darla]
           --(horas que puede dar el maestro)--> SUMIDERO

El flujo máximo dice cuántas horas de clase se pueden cubrir:
- Si el flujo máximo = total de horas -> hay maestros suficientes.
- Si es menor -> el problema NO tiene solución; el corte mínimo muestra dónde falta.

Edmonds-Karp = Ford-Fulkerson usando BFS para encontrar el camino aumentante
más corto. Complejidad O(V * E^2). Implementado a mano (sin librerías).
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

from src.modelos import Instancia

FUENTE = "FUENTE"
SUMIDERO = "SUMIDERO"


class RedFlujo:
    """Red dirigida con capacidades, guardada como diccionario de diccionarios."""

    def __init__(self) -> None:
        self.capacidad: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.flujo: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def agregar_arista(self, origen: str, destino: str, capacidad: int) -> None:
        self.capacidad[origen][destino] += capacidad
        self.capacidad[destino][origen] += 0  # arista inversa (para la red residual)

    def residual(self, u: str, v: str) -> int:
        """Capacidad que todavía se puede enviar de u a v (incluye 'regresar' flujo)."""
        return self.capacidad[u][v] - self.flujo[u][v]

    def _camino_bfs(self, s: str, t: str) -> dict[str, str] | None:
        """BFS en la red residual. Devuelve los padres del camino, o None si no hay."""
        padres = {s: s}
        cola = deque([s])
        while cola:
            u = cola.popleft()
            for v in list(self.capacidad[u]):
                if v not in padres and self.residual(u, v) > 0:
                    padres[v] = u
                    if v == t:
                        return padres
                    cola.append(v)
        return None

    def edmonds_karp(self, s: str = FUENTE, t: str = SUMIDERO) -> tuple[int, list[tuple[list[str], int]]]:
        """Calcula el flujo máximo. Devuelve (valor, caminos aumentantes usados)."""
        total = 0
        caminos = []
        while (padres := self._camino_bfs(s, t)) is not None:
            # Reconstruir el camino y su cuello de botella
            camino = [t]
            while camino[-1] != s:
                camino.append(padres[camino[-1]])
            camino.reverse()
            cuello = min(self.residual(u, v) for u, v in zip(camino, camino[1:]))
            for u, v in zip(camino, camino[1:]):
                self.flujo[u][v] += cuello
                self.flujo[v][u] -= cuello
            total += cuello
            caminos.append((camino, cuello))
        return total, caminos

    def alcanzables(self, s: str = FUENTE) -> set[str]:
        """Nodos alcanzables desde s en la red residual (lado S del corte mínimo)."""
        vistos = {s}
        cola = deque([s])
        while cola:
            u = cola.popleft()
            for v in self.capacidad[u]:
                if v not in vistos and self.residual(u, v) > 0:
                    vistos.add(v)
                    cola.append(v)
        return vistos


@dataclass
class AsignacionMaestros:
    """Resultado del flujo: qué maestro(s) da(n) cada (grupo, materia)."""

    flujo_maximo: int
    demanda: int
    reparto: dict[tuple[str, str], dict[str, int]]          # (grupo, materia) -> {maestro: horas}
    caminos: list[tuple[list[str], int]] = field(default_factory=list)
    faltantes: list[str] = field(default_factory=list)      # explicación si no alcanza

    @property
    def factible(self) -> bool:
        return self.flujo_maximo == self.demanda

    def maestros_de(self, grupo: str, materia: str) -> set[str]:
        return {m for m, h in self.reparto.get((grupo, materia), {}).items() if h > 0}


def construir_red(inst: Instancia) -> RedFlujo:
    red = RedFlujo()
    for grupo in inst.grupos.values():
        for materia_id in grupo.materias:
            nodo_gm = f"{grupo.id}|{materia_id}"
            horas = inst.materias[materia_id].horas_semana
            red.agregar_arista(FUENTE, nodo_gm, horas)
            for maestro in inst.maestros.values():
                if maestro.puede_impartir(materia_id):
                    red.agregar_arista(nodo_gm, maestro.id, horas)
    for maestro in inst.maestros.values():
        # Un maestro no puede dar más horas que su máximo ni que sus bloques disponibles
        red.agregar_arista(maestro.id, SUMIDERO, min(maestro.max_horas_semana, len(maestro.disponibilidad)))
    return red


def asignar_maestros(inst: Instancia) -> AsignacionMaestros:
    """Ejecuta Edmonds-Karp y traduce el flujo a 'qué maestro da qué'."""
    red = construir_red(inst)
    valor, caminos = red.edmonds_karp()
    demanda = sum(red.capacidad[FUENTE].values())

    reparto: dict[tuple[str, str], dict[str, int]] = {}
    for nodo_gm, horas in red.capacidad[FUENTE].items():
        if horas == 0:
            continue
        grupo, materia = nodo_gm.split("|")
        reparto[(grupo, materia)] = {
            m: red.flujo[nodo_gm][m] for m in inst.maestros if red.flujo[nodo_gm][m] > 0
        }

    faltantes = []
    if valor < demanda:
        lado_s = red.alcanzables()
        for (grupo, materia), dado in reparto.items():
            falta = inst.materias[materia].horas_semana - sum(dado.values())
            if falta > 0:
                faltantes.append(f"{grupo}-{materia}: faltan {falta} h de maestro")
        saturados = [m for m in inst.maestros if m in lado_s and red.residual(m, SUMIDERO) == 0]
        if saturados:
            faltantes.append("Maestros saturados (corte mínimo): " + ", ".join(saturados))
    return AsignacionMaestros(valor, demanda, reparto, caminos, faltantes)


def restringir_dominios(dominios: dict, asignacion: AsignacionMaestros) -> dict:
    """Deja en cada dominio solo los maestros que el flujo eligió para esa materia y grupo."""
    nuevos = {}
    for clase, opciones in dominios.items():
        permitidos = asignacion.maestros_de(clase.grupo, clase.materia)
        nuevos[clase] = [a for a in opciones if a.maestro in permitidos] if permitidos else opciones
    return nuevos
