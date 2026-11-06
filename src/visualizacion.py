"""Visualización: horario en texto, tablas y gráficas (matplotlib).

Las funciones de gráficas devuelven una figura de matplotlib, que se puede
guardar como PNG (experimentos) o mostrar en la interfaz web (Streamlit).
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # dibujar sin abrir ventanas
import matplotlib.pyplot as plt  # noqa: E402

from src.modelos import Horario, Instancia  # noqa: E402
from src.resultado import Resultado  # noqa: E402

COLORES_NODO = {"raiz": "#8ecae6", "valido": "#ffffff", "podado": "#f4a3a3", "solucion": "#9be39b"}


def horario_texto(inst: Instancia, horario: Horario) -> str:
    """Una tabla por grupo: filas = horas, columnas = días."""
    ancho = 18
    salida = []
    for grupo_id in inst.grupos:
        celdas = {
            (a.bloque.dia, a.bloque.hora): f"{a.clase.materia} {a.salon} {a.maestro}"
            for a in horario.por_grupo(grupo_id)
        }
        salida.append(f"\nGrupo {grupo_id}")
        salida.append("Hora  | " + " | ".join(d.ljust(ancho) for d in inst.dias))
        salida.append("-" * (8 + (ancho + 3) * len(inst.dias)))
        for hora in inst.horas:
            fila = [celdas.get((dia, hora), "").ljust(ancho) for dia in inst.dias]
            salida.append(f"{hora:>2}:00 | " + " | ".join(fila))
    return "\n".join(salida)


def tabla(filas: list[dict]) -> str:
    """Tabla de texto simple a partir de una lista de diccionarios."""
    if not filas:
        return ""
    columnas = list(filas[0])
    anchos = {c: max(len(str(c)), *(len(str(f[c])) for f in filas)) for c in columnas}
    linea = " | ".join(str(c).ljust(anchos[c]) for c in columnas)
    salida = [linea, "-" * len(linea)]
    for f in filas:
        salida.append(" | ".join(str(f[c]).ljust(anchos[c]) for c in columnas))
    return "\n".join(salida)


def tabla_resultados(resultados: list[Resultado]) -> str:
    return tabla([r.fila() for r in resultados])


def horario_matriz(inst: Instancia, horario: Horario, grupo_id: str) -> list[list[str]]:
    """Matriz [hora][día] con el texto de cada celda (para tablas en la interfaz)."""
    celdas = {(a.bloque.dia, a.bloque.hora): f"{a.clase.materia} | {a.salon} | {a.maestro}"
              for a in horario.por_grupo(grupo_id)}
    return [[celdas.get((dia, hora), "") for dia in inst.dias] for hora in inst.horas]


# ---------------------------------------------------------------------------
# Gráficas
# ---------------------------------------------------------------------------

def grafica_costo(historiales: dict[str, list[float]], titulo: str = "Costo por iteración"):
    """Curva de costo de la búsqueda local (recocido / ascenso de colina)."""
    fig, ax = plt.subplots(figsize=(8, 4))
    for nombre, valores in historiales.items():
        ax.plot(valores, label=nombre, linewidth=1.2)
    ax.set_xlabel("Iteración")
    ax.set_ylabel("Costo del horario (menor es mejor)")
    ax.set_title(titulo)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    return fig


def grafica_comparacion(resultados: list[Resultado], titulo: str = ""):
    """Barras: nodos explorados (escala log), tiempo y costo de cada algoritmo."""
    nombres = [r.algoritmo.replace(" (", "\n(").replace(" + ", "\n+ ") for r in resultados]
    fig, ejes = plt.subplots(1, 3, figsize=(15, 4.8))
    datos = [
        ("Nodos explorados (log)", [max(r.nodos, 1) for r in resultados], True),
        ("Tiempo (s, log)", [max(r.tiempo, 1e-4) for r in resultados], True),
        ("Costo (menor es mejor)", [r.costo if r.costo is not None else 0 for r in resultados], False),
    ]
    for ax, (etiqueta_y, valores, log) in zip(ejes, datos):
        colores = ["#d62828" if not r.encontro_solucion else "#457b9d" for r in resultados]
        ax.bar(range(len(valores)), valores, color=colores)
        if log:
            ax.set_yscale("log")
        ax.set_title(etiqueta_y)
        ax.set_xticks(range(len(nombres)))
        ax.set_xticklabels(nombres, rotation=60, ha="right", fontsize=7)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle(titulo + "   (rojo = no encontró solución)")
    fig.tight_layout()
    return fig


def grafica_aprendizaje(concordancia: list[float], pesos: list[list[float]], pesos_ocultos: list[float]):
    """Evolución de la concordancia con el usuario y de los pesos w1..w4."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    ax1.plot(concordancia, marker="o", markersize=3, color="#2a9d8f")
    ax1.set_ylim(0, 105)
    ax1.set_xlabel("Ronda de retroalimentación")
    ax1.set_ylabel("% de coincidencia con el usuario")
    ax1.set_title("El sistema aprende las preferencias")
    ax1.grid(alpha=0.3)

    nombres = ["w1 huecos", "w2 horarios malos", "w3 desbalance", "w4 preferencias"]
    total_oculto = sum(pesos_ocultos)
    for i, nombre in enumerate(nombres):
        serie = [p[i] / sum(p) for p in pesos]
        linea, = ax2.plot(serie, label=nombre)
        ax2.axhline(pesos_ocultos[i] / total_oculto, color=linea.get_color(), linestyle=":", alpha=0.7)
    ax2.set_xlabel("Ronda")
    ax2.set_ylabel("Peso relativo")
    ax2.set_title("Pesos aprendidos (punteado = preferencia real)")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def dibujar_arbol(arbol, titulo: str = "Árbol de búsqueda"):
    """Dibuja el árbol registrado: raíz arriba, cada nivel una fila.

    La posición horizontal se calcula con un recorrido postorden: las hojas se
    colocan de izquierda a derecha y cada padre queda al centro de sus hijos.
    """
    posiciones: dict[int, tuple[float, float]] = {}
    siguiente_x = [0]

    def ubicar(nodo_id: int) -> float:
        nodo = arbol.nodos[nodo_id]
        if not nodo.hijos:
            x = siguiente_x[0]
            siguiente_x[0] += 1
        else:
            xs = [ubicar(h) for h in nodo.hijos]
            x = (xs[0] + xs[-1]) / 2
        posiciones[nodo_id] = (x, -nodo.nivel)
        return x

    ubicar(0)
    ancho = max(8, siguiente_x[0] * 0.35)
    alto = max(4, (arbol.profundidad() + 1) * 1.1)
    fig, ax = plt.subplots(figsize=(min(ancho, 30), alto))
    for nodo in arbol.nodos.values():
        x, y = posiciones[nodo.id]
        for h in nodo.hijos:
            hx, hy = posiciones[h]
            ax.plot([x, hx], [y, hy], color="#999999", linewidth=0.6, zorder=1)
    for tipo, color in COLORES_NODO.items():
        puntos = [posiciones[n.id] for n in arbol.nodos.values() if n.tipo == tipo]
        if puntos:
            ax.scatter(*zip(*puntos), s=60, color=color, edgecolors="#333333", linewidths=0.6, zorder=2, label=tipo)
    if len(arbol.nodos) <= 25:
        for nodo in arbol.nodos.values():
            x, y = posiciones[nodo.id]
            ax.annotate(nodo.etiqueta.split(" -> ")[-1], (x, y), fontsize=6, ha="center", va="bottom",
                        xytext=(0, 5), textcoords="offset points")
    ax.set_title(f"{titulo} ({len(arbol.nodos)} nodos)")
    ax.set_ylabel("Nivel (clases asignadas)")
    ax.set_xticks([])
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    return fig
