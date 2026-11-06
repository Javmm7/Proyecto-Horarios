"""Experimentos (Paso 12): exhaustiva vs. heurística con tablas y gráficas.

Ejecutar:  py -m src.main experimentos
Genera en resultados/:
- comparacion_<instancia>.csv y .png   (nodos, tiempo, costo por algoritmo)
- recocido_<instancia>.png             (curva de costo por iteración)
- arbol_exhaustiva.png / arbol_mrv.png (árbol de búsqueda dibujado)
- arbol_diagnostico.dot                (árbol de decisión de reglas)
- aprendizaje.png y pesos_aprendidos.json
- reporte_experimentos.md              (tablas listas para el reporte)
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

from src import busqueda_exhaustiva as ex
from src import busqueda_heuristica as he
from src.aprendizaje import guardar_pesos, simular_aprendizaje
from src.modelos import Instancia, cargar_instancia
from src.motor_inferencia import arbol_diagnostico_dot, diagnosticar
from src.resultado import Resultado
from src.visualizacion import dibujar_arbol, grafica_aprendizaje, grafica_comparacion, grafica_costo

SALIDA = Path("resultados")


def algoritmos_para(inst: Instancia) -> list:
    """Qué algoritmos correr según el tamaño (los exhaustivos con límite de nodos)."""
    n = len(inst.generar_clases())
    limite = 100_000 if n <= 10 else 10_000
    lista = [
        lambda: ex.backtracking(inst, max_nodos=limite),
        lambda: ex.backtracking(inst, buscar_optimo=True, max_nodos=limite),
        lambda: ex.bfs(inst, max_nodos=200_000 if n <= 10 else 20_000),
        lambda: he.backtracking_mrv(inst, forward_checking=False),
        lambda: he.backtracking_mrv(inst, forward_checking=True),
        lambda: he.backtracking_mrv(inst, forward_checking=True, usar_flujo=True),
        lambda: he.greedy(inst),
    ]
    if n <= 10:  # A* recalcula la heurística en cada nodo: solo en instancias chicas
        lista.append(lambda: he.a_estrella(inst))
    lista += [
        lambda: he.ascenso_colina(inst),
        lambda: he.recocido_simulado(inst),
    ]
    return lista


def comparar(inst: Instancia, nombre: str) -> list[Resultado]:
    print(f"\n=== {inst.nombre} ===")
    resultados = []
    for correr in algoritmos_para(inst):
        r = correr()
        print(f"  {r.algoritmo:<40} costo={r.costo!s:<7} nodos={r.nodos:<7} t={r.tiempo:.3f}s {r.notas}")
        resultados.append(r)

    filas = [r.fila() for r in resultados]
    with open(SALIDA / f"comparacion_{nombre}.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)
    guardar(grafica_comparacion(resultados, inst.nombre), f"comparacion_{nombre}.png")

    locales = {r.algoritmo: r.historial for r in resultados if r.historial}
    if locales:
        guardar(grafica_costo(locales, f"Búsqueda local - {inst.nombre}"), f"recocido_{nombre}.png")
    return resultados


def guardar(fig, archivo: str) -> None:
    fig.savefig(SALIDA / archivo, dpi=130)
    plt.close(fig)


def correr_todo() -> None:
    SALIDA.mkdir(exist_ok=True)
    reporte = ["# Resultados de los experimentos", "", "Generado con `py -m src.main experimentos`.", ""]

    for nombre in ("mini", "pequeno", "mediano"):
        inst = cargar_instancia(f"data/ejemplo_{nombre}.json")
        d = diagnosticar(inst)
        reporte += [f"## {inst.nombre}", "", f"Diagnóstico previo: **{d.conclusion}**", ""]
        resultados = comparar(inst, nombre)
        reporte += [_markdown([r.fila() for r in resultados]), ""]
        reporte += [f"![comparación](comparacion_{nombre}.png)", ""]

    # Árboles dibujados (instancia mini, primeros nodos)
    mini = cargar_instancia("data/ejemplo_mini.json")
    r = ex.backtracking(mini, arbol_limite=60)
    guardar(dibujar_arbol(r.arbol, "Backtracking exhaustivo (instancia mini)"), "arbol_exhaustiva.png")
    r = he.backtracking_mrv(mini, arbol_limite=60)
    guardar(dibujar_arbol(r.arbol, "MRV + forward checking (instancia mini)"), "arbol_mrv.png")
    (SALIDA / "arbol_diagnostico.dot").write_text(arbol_diagnostico_dot(), encoding="utf-8")

    # Aprendizaje
    print("\n=== Simulación de aprendizaje (instancia pequeña) ===")
    inst = cargar_instancia("data/ejemplo_pequeno.json")
    a = simular_aprendizaje(inst)
    guardar(grafica_aprendizaje(a.concordancia, a.pesos, a.pesos_ocultos), "aprendizaje.png")
    guardar_pesos(a.aprendiz.pesos)
    texto = (f"Concordancia con el usuario: {a.concordancia[0]:.0f}% -> {a.concordancia[-1]:.0f}%. "
             f"Costo del horario según el usuario: {a.costo_usuario_antes} -> {a.costo_usuario_despues}. "
             f"Pesos: {a.pesos[0]} -> {a.pesos[-1]} (preferencia oculta {a.pesos_ocultos}).")
    print("  " + texto)
    reporte += ["## Aprendizaje", "", texto, "", "![aprendizaje](aprendizaje.png)", ""]

    (SALIDA / "reporte_experimentos.md").write_text("\n".join(reporte), encoding="utf-8")
    print(f"\nListo. Archivos en {SALIDA.resolve()}")


def _markdown(filas: list[dict]) -> str:
    columnas = list(filas[0])
    lineas = ["| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
    lineas += ["| " + " | ".join(str(f[c]) for c in columnas) + " |" for f in filas]
    return "\n".join(lineas)


if __name__ == "__main__":
    correr_todo()
