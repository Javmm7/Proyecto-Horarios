"""Algoritmos de ordenamiento implementados a mano (Paso 7).

Se usan para:
- Ordenar las clases por dificultad (MRV: la de menos opciones primero) -> merge sort.
- Ordenar los candidatos de una clase por costo (el más barato primero) -> quicksort.

Ambos reciben una función `clave`, igual que sorted(..., key=...).
La clave se calcula UNA vez por elemento y se guarda junto con su posición
original; así el resultado es determinista y no se comparan objetos raros.
"""
from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar("T")


def _decorar(lista: list[T], clave: Callable[[T], object]) -> list[tuple]:
    return [(clave(x), i, x) for i, x in enumerate(lista)]


# ---------------------------------------------------------------------------
# Merge sort: divide a la mitad, ordena cada mitad y las mezcla. O(n log n), estable.
# ---------------------------------------------------------------------------

def merge_sort(lista: list[T], clave: Callable[[T], object] = lambda x: x) -> list[T]:
    """Devuelve una lista nueva ordenada por `clave` (de menor a mayor)."""
    return [x for _, _, x in _merge_sort(_decorar(lista, clave))]


def _merge_sort(a: list[tuple]) -> list[tuple]:
    if len(a) <= 1:
        return a
    mitad = len(a) // 2
    izquierda = _merge_sort(a[:mitad])
    derecha = _merge_sort(a[mitad:])
    return _mezclar(izquierda, derecha)


def _mezclar(izq: list[tuple], der: list[tuple]) -> list[tuple]:
    resultado = []
    i = j = 0
    while i < len(izq) and j < len(der):
        # Se compara (clave, posición): si las claves empatan gana el que iba antes
        if izq[i][:2] <= der[j][:2]:
            resultado.append(izq[i])
            i += 1
        else:
            resultado.append(der[j])
            j += 1
    resultado.extend(izq[i:])
    resultado.extend(der[j:])
    return resultado


# ---------------------------------------------------------------------------
# Quicksort: elige un pivote y separa en menores / iguales / mayores. O(n log n) promedio.
# ---------------------------------------------------------------------------

def quicksort(lista: list[T], clave: Callable[[T], object] = lambda x: x) -> list[T]:
    """Devuelve una lista nueva ordenada por `clave` (de menor a mayor)."""
    return [x for _, _, x in _quicksort(_decorar(lista, clave))]


def _quicksort(a: list[tuple]) -> list[tuple]:
    if len(a) <= 1:
        return a
    pivote = a[len(a) // 2][:2]
    menores = [x for x in a if x[:2] < pivote]
    iguales = [x for x in a if x[:2] == pivote]
    mayores = [x for x in a if x[:2] > pivote]
    return _quicksort(menores) + iguales + _quicksort(mayores)
