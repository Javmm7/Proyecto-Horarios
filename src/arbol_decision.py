"""Árbol de estados de la búsqueda y sus recorridos (Pasos 5 y 6).

Cada NODO es un estado (horario parcial):
- La raíz es el horario vacío.
- El nivel k contiene los estados con k clases asignadas.
- Cada arista es una decisión: "clase X -> bloque, salón, maestro".

Los algoritmos de búsqueda van registrando aquí lo que exploran (hasta un
límite de nodos, para que el árbol se pueda dibujar). Cada nodo se marca como:
- "raiz"      horario vacío
- "valido"    la asignación cumple las reglas duras y se sigue explorando
- "podado"    la asignación viola una regla dura (se anota cuál)
- "solucion"  horario completo y válido

Recorridos implementados: preorden y postorden (DFS), inorden (adaptado a
árboles con varios hijos) y por niveles (BFS).
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field


@dataclass
class NodoArbol:
    id: int
    padre: int | None
    nivel: int
    etiqueta: str
    tipo: str
    regla: str | None = None
    hijos: list[int] = field(default_factory=list)


class ArbolBusqueda:
    """Árbol de búsqueda registrado durante la ejecución de un algoritmo."""

    def __init__(self, limite: int = 300) -> None:
        self.limite = limite
        self.nodos: dict[int, NodoArbol] = {0: NodoArbol(0, None, 0, "Horario vacío", "raiz")}

    def agregar(self, padre: int | None, etiqueta: str, tipo: str, regla: str | None = None) -> int | None:
        """Agrega un hijo. Devuelve su id, o None si ya se llegó al límite."""
        if padre is None or padre not in self.nodos or len(self.nodos) >= self.limite:
            return None
        nuevo_id = len(self.nodos)
        nivel = self.nodos[padre].nivel + 1
        self.nodos[nuevo_id] = NodoArbol(nuevo_id, padre, nivel, etiqueta, tipo, regla)
        self.nodos[padre].hijos.append(nuevo_id)
        return nuevo_id

    def marcar(self, nodo_id: int | None, tipo: str) -> None:
        if nodo_id is not None and nodo_id in self.nodos:
            self.nodos[nodo_id].tipo = tipo

    # ------------------------------------------------------------------
    # Recorridos
    # ------------------------------------------------------------------

    def preorden(self, nodo_id: int = 0) -> list[NodoArbol]:
        """DFS preorden: primero el nodo, después sus hijos (de izquierda a derecha)."""
        nodo = self.nodos[nodo_id]
        resultado = [nodo]
        for hijo in nodo.hijos:
            resultado.extend(self.preorden(hijo))
        return resultado

    def postorden(self, nodo_id: int = 0) -> list[NodoArbol]:
        """DFS postorden: primero los hijos, al final el nodo."""
        nodo = self.nodos[nodo_id]
        resultado = []
        for hijo in nodo.hijos:
            resultado.extend(self.postorden(hijo))
        resultado.append(nodo)
        return resultado

    def inorden(self, nodo_id: int = 0) -> list[NodoArbol]:
        """Inorden generalizado: primer hijo, el nodo, y luego el resto de los hijos.

        (El inorden clásico es para árboles binarios; esta es la versión n-aria.)
        """
        nodo = self.nodos[nodo_id]
        if not nodo.hijos:
            return [nodo]
        resultado = self.inorden(nodo.hijos[0])
        resultado.append(nodo)
        for hijo in nodo.hijos[1:]:
            resultado.extend(self.inorden(hijo))
        return resultado

    def por_niveles(self) -> list[NodoArbol]:
        """BFS: recorre nivel por nivel usando una cola."""
        resultado = []
        cola = deque([0])
        while cola:
            nodo = self.nodos[cola.popleft()]
            resultado.append(nodo)
            cola.extend(nodo.hijos)
        return resultado

    # ------------------------------------------------------------------
    # Resúmenes y exportación
    # ------------------------------------------------------------------

    def conteo(self) -> dict[str, int]:
        """Cuántos nodos hay de cada tipo, y cuántas podas causó cada regla."""
        tipos = Counter(n.tipo for n in self.nodos.values())
        reglas = Counter(n.regla for n in self.nodos.values() if n.regla)
        return {**tipos, **{f"podas {r}": c for r, c in sorted(reglas.items())}}

    def profundidad(self) -> int:
        return max(n.nivel for n in self.nodos.values())

    def a_texto(self, max_lineas: int = 60) -> str:
        """Dibujo del árbol con sangrías (recorrido en preorden)."""
        simbolo = {"raiz": "*", "valido": "+", "podado": "x", "solucion": "#"}
        lineas = []
        for nodo in self.preorden():
            extra = f"  [poda {nodo.regla}]" if nodo.regla else ""
            lineas.append(f"{'  ' * nodo.nivel}{simbolo.get(nodo.tipo, '?')} {nodo.etiqueta}{extra}")
            if len(lineas) >= max_lineas:
                lineas.append(f"... ({len(self.nodos) - max_lineas} nodos más)")
                break
        return "\n".join(lineas)

    def a_dot(self) -> str:
        """Exporta a formato Graphviz DOT (se puede ver en https://dreampuf.github.io/GraphvizOnline)."""
        colores = {"raiz": "lightblue", "valido": "white", "podado": "lightcoral", "solucion": "palegreen"}
        lineas = ["digraph Arbol {", "  node [shape=box, style=filled, fontsize=10];"]
        for n in self.nodos.values():
            texto = n.etiqueta + (f"\\n(poda {n.regla})" if n.regla else "")
            lineas.append(f'  n{n.id} [label="{texto}", fillcolor={colores.get(n.tipo, "white")}];')
        for n in self.nodos.values():
            for h in n.hijos:
                lineas.append(f"  n{n.id} -> n{h};")
        lineas.append("}")
        return "\n".join(lineas)


def etiqueta(asignacion) -> str:
    """Texto corto para una arista del árbol: '1A-MAT-1 -> Lunes 7:00, A101, M1'."""
    return f"{asignacion.clase.id} -> {asignacion.bloque}, {asignacion.salon}, {asignacion.maestro}"
