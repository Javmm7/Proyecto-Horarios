"""Búsqueda exhaustiva (Paso 4): backtracking (DFS) y BFS.

Son búsquedas "sin inteligencia":
- Las clases se asignan en el orden en que aparecen en los datos.
- Para cada clase se prueban TODAS las combinaciones bloque x salón x maestro.
- La única optimización es la poda: si una asignación viola una regla dura,
  esa rama no se sigue (no tiene caso, ningún horario debajo será válido).

Sirven como punto de comparación para la búsqueda heurística.
"""
from __future__ import annotations

from collections import deque

from src.arbol_decision import ArbolBusqueda, etiqueta
from src.modelos import Horario, Instancia
from src.reglas import Ocupacion, Pesos, costo, todas_las_opciones
from src.resultado import Metricas, Resultado


def backtracking(
    inst: Instancia,
    pesos: Pesos | None = None,
    buscar_optimo: bool = False,
    max_nodos: int = 500_000,
    arbol_limite: int = 0,
) -> Resultado:
    """Backtracking puro con recorrido en profundidad (DFS).

    - buscar_optimo=False: se detiene en el PRIMER horario válido.
    - buscar_optimo=True: recorre todo el árbol y se queda con el de menor costo
      (solo es viable en instancias muy pequeñas).
    - max_nodos: límite de seguridad; si se alcanza, el resultado no es "completo".
    - arbol_limite: si es > 0, guarda los primeros N nodos del árbol para dibujarlo.
    """
    pesos = pesos or Pesos()
    clases = inst.generar_clases()
    opciones = [todas_las_opciones(inst, c) for c in clases]
    m = Metricas()
    arbol = ArbolBusqueda(arbol_limite) if arbol_limite else None
    horario = Horario()
    ocup = Ocupacion()
    estado = {"mejor": None, "costo": None, "desglose": {}, "cortado": False}

    def dfs(nivel: int, nodo_id: int | None) -> bool:
        """Devuelve True cuando hay que detener toda la búsqueda."""
        if nivel == len(clases):
            # Hoja: horario completo y válido
            if arbol:
                arbol.marcar(nodo_id, "solucion")
            c, d = costo(inst, horario, pesos)
            if estado["costo"] is None or c < estado["costo"]:
                estado.update(mejor=horario.copia(), costo=c, desglose=d)
            return not buscar_optimo

        for a in opciones[nivel]:
            if m.nodos >= max_nodos:
                estado["cortado"] = True
                return True
            violacion = m.verificar(inst, ocup, a)
            if violacion:
                if arbol:
                    arbol.agregar(nodo_id, etiqueta(a), "podado", violacion[0])
                continue
            m.nodos += 1
            hijo = arbol.agregar(nodo_id, etiqueta(a), "valido") if arbol else None
            horario.agregar(a)
            ocup.agregar(a)
            detener = dfs(nivel + 1, hijo)
            horario.quitar_ultima()   # deshacer = "regresar" en el árbol
            ocup.quitar(a)
            if detener:
                return True
        return False

    dfs(0, 0)
    nombre = "Exhaustiva DFS (óptimo)" if buscar_optimo else "Exhaustiva DFS (1a solución)"
    notas = "Se alcanzó el límite de nodos; puede existir un horario mejor." if estado["cortado"] else ""
    return Resultado(
        algoritmo=nombre,
        horario=estado["mejor"],
        costo=estado["costo"],
        desglose=estado["desglose"],
        nodos=m.nodos,
        verificaciones=m.verificaciones,
        tiempo=m.tiempo(),
        completo=buscar_optimo and not estado["cortado"],
        arbol=arbol,
        notas=notas,
    )


def bfs(inst: Instancia, pesos: Pesos | None = None, max_nodos: int = 200_000) -> Resultado:
    """Búsqueda en anchura (BFS): expande el árbol nivel por nivel con una cola.

    Encuentra TODOS los horarios válidos (están en el último nivel) y elige el
    de menor costo. Su problema es la memoria: guarda niveles completos del árbol.
    """
    pesos = pesos or Pesos()
    clases = inst.generar_clases()
    opciones = [todas_las_opciones(inst, c) for c in clases]
    m = Metricas()
    frontera: deque[tuple] = deque([()])  # cada estado = tupla de asignaciones
    max_frontera = 1
    cortado = False

    for nivel in range(len(clases)):
        siguiente: deque[tuple] = deque()
        while frontera and not cortado:
            estado = frontera.popleft()
            ocup = Ocupacion.desde_horario(Horario(list(estado)))
            for a in opciones[nivel]:
                if m.verificar(inst, ocup, a):
                    continue
                m.nodos += 1
                siguiente.append(estado + (a,))
                if m.nodos >= max_nodos:
                    cortado = True
                    break
        frontera = siguiente
        max_frontera = max(max_frontera, len(frontera))
        if cortado or not frontera:
            break

    mejor, mejor_costo, mejor_desglose = None, None, {}
    if not cortado:
        for estado in frontera:
            h = Horario(list(estado))
            c, d = costo(inst, h, pesos)
            if mejor_costo is None or c < mejor_costo:
                mejor, mejor_costo, mejor_desglose = h, c, d

    notas = f"Máximo de estados guardados en memoria a la vez: {max_frontera}."
    if cortado:
        notas += " Se alcanzó el límite de nodos (memoria) antes de terminar."
    return Resultado(
        algoritmo="Exhaustiva BFS (óptimo)",
        horario=mejor,
        costo=mejor_costo,
        desglose=mejor_desglose,
        nodos=m.nodos,
        verificaciones=m.verificaciones,
        tiempo=m.tiempo(),
        completo=not cortado,
        notas=notas,
    )
