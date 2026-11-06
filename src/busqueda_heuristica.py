"""Búsqueda heurística (Pasos 7 y 8).

Técnicas para explorar menos nodos que la búsqueda exhaustiva:

1. Dominio estático: R4 y R5 se revisan una sola vez al inicio
   (un laboratorio nunca servirá para Matemáticas, no hay que volver a probarlo).
2. MRV (Minimum Remaining Values): asignar primero la clase con MENOS opciones.
   Si algo va a fallar, que falle pronto y se pode arriba en el árbol.
3. Forward checking: después de cada asignación, si alguna clase pendiente
   se quedó sin opciones, se poda de inmediato.
4. Orden de valores: probar primero las opciones más baratas (quicksort por costo).
5. Greedy: elegir siempre la opción más barata, sin regresar.
6. A*: expandir el estado con menor f = g + h (costo acumulado + estimación).
7. Recocido simulado / ascenso de colina: mejorar un horario completo
   haciendo cambios pequeños.
"""
from __future__ import annotations

import heapq
import itertools
import math
import random

from src.arbol_decision import ArbolBusqueda, etiqueta
from src.modelos import Asignacion, Clase, Horario, Instancia
from src.ordenamiento import merge_sort, quicksort
from src.reglas import Ocupacion, Pesos, costo, costo_local, dominio_estatico
from src.resultado import Metricas, Resultado


def _dominios(inst: Instancia, usar_flujo: bool = False) -> dict[Clase, list[Asignacion]]:
    dominios = {c: dominio_estatico(inst, c) for c in inst.generar_clases()}
    if usar_flujo:
        # Importación local para evitar dependencias circulares
        from src.flujo import asignar_maestros, restringir_dominios
        dominios = restringir_dominios(dominios, asignar_maestros(inst))
    return dominios


def _validas(inst: Instancia, ocup: Ocupacion, dominio: list[Asignacion], m: Metricas) -> list[Asignacion]:
    """Opciones del dominio que cumplen las reglas duras en el estado actual."""
    return [a for a in dominio if m.verificar(inst, ocup, a) is None]


def _resultado(nombre: str, inst: Instancia, horario: Horario | None, pesos: Pesos, m: Metricas, **extra) -> Resultado:
    c, d = costo(inst, horario, pesos) if horario else (None, {})
    return Resultado(nombre, horario, c, d, m.nodos, m.verificaciones, m.tiempo(),
                     completo=extra.pop("completo", False), **extra)


# ---------------------------------------------------------------------------
# Backtracking con MRV (+ forward checking)
# ---------------------------------------------------------------------------

def backtracking_mrv(
    inst: Instancia,
    pesos: Pesos | None = None,
    forward_checking: bool = True,
    max_nodos: int = 500_000,
    arbol_limite: int = 0,
    usar_flujo: bool = False,
) -> Resultado:
    """Backtracking con heurísticas. Se detiene en el primer horario válido.

    - forward_checking=False: MRV "estático": las clases se ordenan UNA vez por
      tamaño de su dominio (merge sort).
    - forward_checking=True: MRV "dinámico": en cada paso se recalculan las
      opciones válidas de todas las clases pendientes, se elige la que tenga
      menos y, si alguna tiene cero, se poda (forward checking).
    En ambos casos los valores se prueban del más barato al más caro (quicksort).
    - usar_flujo=True: antes de buscar, el flujo máximo decide qué maestro da
      cada materia a cada grupo; así el árbol solo decide bloque y salón.
    """
    pesos = pesos or Pesos()
    dominios = _dominios(inst, usar_flujo)
    m = Metricas()
    arbol = ArbolBusqueda(arbol_limite) if arbol_limite else None
    horario = Horario()
    ocup = Ocupacion()
    orden_estatico = merge_sort(list(dominios), clave=lambda c: len(dominios[c]))
    cortado = False

    def elegir_clase(pendientes: list[Clase]) -> tuple[Clase | None, list[Asignacion]]:
        if not forward_checking:
            clase = pendientes[0]
            return clase, _validas(inst, ocup, dominios[clase], m)
        opciones = {c: _validas(inst, ocup, dominios[c], m) for c in pendientes}
        if any(len(v) == 0 for v in opciones.values()):
            return None, []  # forward checking: alguna clase se quedó sin opciones
        clase = merge_sort(pendientes, clave=lambda c: len(opciones[c]))[0]
        return clase, opciones[clase]

    def buscar(pendientes: list[Clase], nodo_id: int | None) -> bool:
        nonlocal cortado
        if not pendientes:
            if arbol:
                arbol.marcar(nodo_id, "solucion")
            return True
        clase, candidatos = elegir_clase(pendientes)
        if clase is None:
            if arbol:
                arbol.agregar(nodo_id, "una clase pendiente se quedó sin opciones", "podado", "FC")
            return False
        candidatos = quicksort(candidatos, clave=lambda a: costo_local(inst, ocup, a, pesos))
        resto = [c for c in pendientes if c != clase]
        for a in candidatos:
            if m.nodos >= max_nodos:
                cortado = True
                return False
            m.nodos += 1
            hijo = arbol.agregar(nodo_id, etiqueta(a), "valido") if arbol else None
            horario.agregar(a)
            ocup.agregar(a)
            if buscar(resto, hijo):
                return True
            horario.quitar_ultima()
            ocup.quitar(a)
        return False

    encontrado = buscar(orden_estatico, 0)
    nombre = "MRV + forward checking" if forward_checking else "MRV estático"
    if usar_flujo:
        nombre = "Flujo máximo + " + nombre
    notas = "Se alcanzó el límite de nodos." if cortado else ""
    return _resultado(nombre, inst, horario if encontrado else None, pesos, m, arbol=arbol, notas=notas)


# ---------------------------------------------------------------------------
# Greedy (voraz)
# ---------------------------------------------------------------------------

def greedy(inst: Instancia, pesos: Pesos | None = None) -> Resultado:
    """Asigna cada clase (en orden MRV) a la opción válida de menor costo total.

    Es muy rápido pero nunca regresa: si una clase se queda sin opciones, falla.
    """
    pesos = pesos or Pesos()
    dominios = _dominios(inst)
    m = Metricas()
    horario = Horario()
    ocup = Ocupacion()

    for clase in merge_sort(list(dominios), clave=lambda c: len(dominios[c])):
        validas = _validas(inst, ocup, dominios[clase], m)
        if not validas:
            return _resultado("Greedy", inst, None, pesos, m,
                              notas=f"Falló: {clase.id} se quedó sin opciones (greedy no regresa).")

        def costo_si_asigno(a: Asignacion) -> float:
            horario.agregar(a)
            c, _ = costo(inst, horario, pesos)
            horario.quitar_ultima()
            return c

        mejor = quicksort(validas, clave=costo_si_asigno)[0]
        m.nodos += 1
        horario.agregar(mejor)
        ocup.agregar(mejor)

    return _resultado("Greedy", inst, horario, pesos, m)


# ---------------------------------------------------------------------------
# A*
# ---------------------------------------------------------------------------

def a_estrella(inst: Instancia, pesos: Pesos | None = None, max_nodos: int = 5_000,
               ancho_haz: int | None = 100) -> Resultado:
    """A* sobre el árbol de estados.

    - g(n): suma del costo local de las asignaciones hechas (reglas S2, S3, S5, S6).
    - h(n): para cada clase pendiente, el costo local MÁS BAJO entre sus opciones
      válidas. Nunca sobreestima (las opciones solo pueden empeorar), por lo que
      h es ADMISIBLE y A* encuentra el mínimo de esa parte del costo.
      Si una clase pendiente no tiene opciones, h = infinito (se poda).
    - Los huecos (S1) y el desbalance (S4) no son aditivos; se evalúan al final
      y el recocido simulado se encarga de mejorarlos.
    - ancho_haz: optimización de memoria. Si la frontera crece más de este número,
      se conservan solo los mejores estados (A* con haz / beam search). Con
      ancho_haz=None es A* puro (óptimo, pero puede explotar en memoria y tiempo).
    """
    pesos = pesos or Pesos()
    dominios = _dominios(inst)
    orden = merge_sort(list(dominios), clave=lambda c: len(dominios[c]))  # orden fijo (MRV)
    m = Metricas()
    desempate = itertools.count()
    nombre = "A*" if ancho_haz is None else f"A* (haz {ancho_haz})"

    def heuristica(estado: tuple) -> float:
        ocup = Ocupacion.desde_horario(Horario(list(estado)))
        total = 0.0
        for clase in orden[len(estado):]:
            validas = _validas(inst, ocup, dominios[clase], m)
            if not validas:
                return math.inf
            total += min(costo_local(inst, ocup, a, pesos) for a in validas)
        return total

    # Cola de prioridad: (f, -profundidad, desempate, g, estado)
    frontera = [(heuristica(()), 0, next(desempate), 0.0, ())]
    recortes = 0
    while frontera:
        f, _, _, g, estado = heapq.heappop(frontera)
        if len(estado) == len(orden):
            garantia = "óptimo" if recortes == 0 else f"sin garantía de óptimo, {recortes} recortes del haz"
            return _resultado(nombre, inst, Horario(list(estado)), pesos, m,
                              notas=f"Costo local g = {g} ({garantia}).")
        if m.nodos >= max_nodos:
            break
        m.nodos += 1
        ocup = Ocupacion.desde_horario(Horario(list(estado)))
        clase = orden[len(estado)]
        for a in _validas(inst, ocup, dominios[clase], m):
            g_hijo = g + costo_local(inst, ocup, a, pesos)
            hijo = estado + (a,)
            h_hijo = heuristica(hijo)
            if h_hijo < math.inf:
                heapq.heappush(frontera, (g_hijo + h_hijo, -len(hijo), next(desempate), g_hijo, hijo))
        if ancho_haz and len(frontera) > ancho_haz:
            frontera = heapq.nsmallest(ancho_haz, frontera)  # sigue siendo un heap válido
            recortes += 1

    return _resultado(nombre, inst, None, pesos, m, notas="Sin solución o se alcanzó el límite de nodos.")


# ---------------------------------------------------------------------------
# Recocido simulado y ascenso de colina (búsqueda local)
# ---------------------------------------------------------------------------

def _vecino_mover(inst, actual, ocup, dominios, azar, m) -> list | None:
    """Vecino tipo 1: mover UNA clase a otra opción válida (bloque, salón o maestro)."""
    i = azar.randrange(len(actual))
    viejo = actual.asignaciones[i]
    ocup.quitar(viejo)
    alternativas = [a for a in _validas(inst, ocup, dominios[viejo.clase], m) if a != viejo]
    if not alternativas:
        ocup.agregar(viejo)
        return None
    nuevo = azar.choice(alternativas)
    actual.asignaciones[i] = nuevo
    ocup.agregar(nuevo)
    return [(i, viejo, nuevo)]


def _vecino_intercambiar(inst, actual, ocup, azar, m) -> list | None:
    """Vecino tipo 2: intercambiar las horas de dos clases del mismo grupo (cierra huecos)."""
    i = azar.randrange(len(actual))
    a = actual.asignaciones[i]
    otros = [j for j, b in enumerate(actual.asignaciones) if b.clase.grupo == a.clase.grupo and b.bloque != a.bloque]
    if not otros:
        return None
    j = azar.choice(otros)
    b = actual.asignaciones[j]
    nuevo_a = Asignacion(a.clase, b.bloque, a.salon, a.maestro)
    nuevo_b = Asignacion(b.clase, a.bloque, b.salon, b.maestro)
    ocup.quitar(a)
    ocup.quitar(b)
    if m.verificar(inst, ocup, nuevo_a) is None:
        ocup.agregar(nuevo_a)
        if m.verificar(inst, ocup, nuevo_b) is None:
            ocup.agregar(nuevo_b)
            actual.asignaciones[i], actual.asignaciones[j] = nuevo_a, nuevo_b
            return [(i, a, nuevo_a), (j, b, nuevo_b)]
        ocup.quitar(nuevo_a)
    ocup.agregar(a)
    ocup.agregar(b)
    return None


def _deshacer(actual, ocup, cambios) -> None:
    # Primero quitar TODAS las nuevas y después poner las viejas: si se hace una
    # por una, en un intercambio dos clases comparten bloque un instante y los
    # conjuntos de ocupación quedan mal.
    for _, _, nuevo in cambios:
        ocup.quitar(nuevo)
    for i, viejo, _ in cambios:
        ocup.agregar(viejo)
        actual.asignaciones[i] = viejo


def recocido_simulado(
    inst: Instancia,
    pesos: Pesos | None = None,
    inicial: Horario | None = None,
    iteraciones: int = 5000,
    temp_inicial: float = 2.0,
    enfriamiento: float = 0.999,
    semilla: int = 42,
    nombre: str = "Recocido simulado",
) -> Resultado:
    """Mejora un horario completo haciendo cambios pequeños (vecinos).

    En cada iteración:
    1. Se genera un vecino: mover una clase a otra opción válida, o
       intercambiar las horas de dos clases del mismo grupo (50 % cada uno).
    2. Si el vecino es mejor, se acepta.
    3. Si es peor, se acepta con probabilidad e^(-delta/T). Al inicio T es alta
       (explora); T baja poco a poco (se vuelve exigente). Así puede salir de
       mínimos locales.
    Con temp_inicial = 0 se convierte en ascenso de colina (solo acepta mejoras).
    El historial guarda el costo en cada iteración (para graficar la mejora).
    """
    pesos = pesos or Pesos()
    azar = random.Random(semilla)
    dominios = _dominios(inst)
    m = Metricas()

    if inicial is None:
        base = backtracking_mrv(inst, pesos)
        if not base.horario:
            return _resultado(nombre, inst, None, pesos, m, notas="No hay horario inicial válido.")
        inicial = base.horario
    actual = inicial.copia()
    ocup = Ocupacion.desde_horario(actual)
    costo_actual, _ = costo(inst, actual, pesos)
    mejor, costo_mejor = actual.copia(), costo_actual
    historial = [costo_actual]
    temperatura = temp_inicial

    for _ in range(iteraciones):
        if azar.random() < 0.5:
            cambios = _vecino_mover(inst, actual, ocup, dominios, azar, m)
        else:
            cambios = _vecino_intercambiar(inst, actual, ocup, azar, m)
        if cambios:
            m.nodos += 1
            costo_nuevo, _ = costo(inst, actual, pesos)
            delta = costo_nuevo - costo_actual
            acepta = delta <= 0 or (temperatura > 0 and azar.random() < math.exp(-delta / temperatura))
            if acepta:
                costo_actual = costo_nuevo
                if costo_actual < costo_mejor:
                    mejor, costo_mejor = actual.copia(), costo_actual
            else:
                _deshacer(actual, ocup, cambios)
        historial.append(costo_actual)
        temperatura *= enfriamiento

    return _resultado(nombre, inst, mejor, pesos, m, historial=historial,
                      notas=f"Costo inicial {historial[0]} -> mejor {costo_mejor} en {iteraciones} iteraciones.")


def ascenso_colina(inst: Instancia, pesos: Pesos | None = None, inicial: Horario | None = None,
                   iteraciones: int = 5000, semilla: int = 42) -> Resultado:
    """Búsqueda local que solo acepta mejoras (se puede atorar en un mínimo local)."""
    return recocido_simulado(inst, pesos, inicial, iteraciones, temp_inicial=0.0,
                             semilla=semilla, nombre="Ascenso de colina")
