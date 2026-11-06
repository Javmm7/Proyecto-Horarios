"""Motor de inferencia y módulo de explicación del sistema experto (Paso 10).

Dos funciones principales:

1. explicar(inst, horario, clase): responde "¿por qué se asignó X aquí?"
   - qué reglas duras se cumplen,
   - qué penalizaciones suaves tiene la opción elegida,
   - cuántas alternativas se descartaron y por qué regla.

2. diagnosticar(inst): árbol de decisión de reglas que revisa ANTES de buscar
   si el problema puede tener solución, y si no, dice la causa.
   El árbol se recorre de la raíz a una hoja respondiendo preguntas SI/NO
   (encadenamiento hacia adelante).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from src.flujo import asignar_maestros
from src.modelos import Clase, Horario, Instancia
from src.reglas import (
    REGLAS_DURAS,
    Ocupacion,
    Pesos,
    costo_local,
    primera_violacion,
    todas_las_opciones,
)


# ---------------------------------------------------------------------------
# 1. Explicación de una asignación
# ---------------------------------------------------------------------------

def explicar(inst: Instancia, horario: Horario, clase: Clase, pesos: Pesos | None = None) -> str:
    """Explica en texto por qué la clase quedó donde quedó."""
    pesos = pesos or Pesos()
    elegida = next((a for a in horario.asignaciones if a.clase == clase), None)
    if elegida is None:
        return f"La clase {clase.id} no está en el horario."

    # Estado "todo el horario menos esta clase"
    resto = Horario([a for a in horario.asignaciones if a.clase != clase])
    ocup = Ocupacion.desde_horario(resto)
    materia = inst.materias[clase.materia]
    maestro = inst.maestros[elegida.maestro]
    salon = inst.salones[elegida.salon]
    grupo = inst.grupos[clase.grupo]

    lineas = [
        f"Clase {clase.id}: {materia.nombre} del grupo {grupo.id} (sesión {clase.sesion})",
        f"Asignada a: {elegida.bloque}, salón {salon.id}, maestro(a) {maestro.nombre}",
        "",
        "Reglas duras que se cumplen:",
        f"  R1  {maestro.nombre} no tiene otra clase el {elegida.bloque}.",
        f"  R2  El salón {salon.id} está libre el {elegida.bloque}.",
        f"  R3  El grupo {grupo.id} no tiene otra clase el {elegida.bloque}.",
        f"  R4  {salon.id} es {salon.tipo} con {salon.capacidad} lugares (el grupo tiene {grupo.alumnos} alumnos).",
        f"  R5  {maestro.nombre} imparte {materia.id} y está disponible el {elegida.bloque}.",
        f"  R6  {maestro.nombre} queda con {ocup.horas_dia[(maestro.id, elegida.bloque.dia)] + 1}/"
        f"{maestro.max_horas_dia} h ese día y {ocup.horas_semana[maestro.id] + 1}/{maestro.max_horas_semana} h en la semana.",
        "",
    ]

    penalizacion = costo_local(inst, ocup, elegida, pesos)
    lineas.append(f"Penalización de calidad de esta opción: {penalizacion}")
    if elegida.bloque.hora in (inst.horas[0], inst.horas[-1]):
        lineas.append("  S2  Es la primera o la última hora del día.")
    if maestro.preferencias and elegida.bloque not in maestro.preferencias:
        lineas.append(f"  S5  No es un horario preferido de {maestro.nombre}.")

    # Alternativas: por qué no se eligió otra opción
    rechazos: Counter = Counter()
    validas_mejores = 0
    for alternativa in todas_las_opciones(inst, clase):
        if alternativa == elegida:
            continue
        violacion = primera_violacion(inst, ocup, alternativa)
        if violacion:
            rechazos[violacion[0]] += 1
        elif costo_local(inst, ocup, alternativa, pesos) < penalizacion:
            validas_mejores += 1

    lineas.append("")
    lineas.append(f"Alternativas descartadas por reglas duras: {sum(rechazos.values())}")
    descripciones = {codigo: texto for codigo, texto, _ in REGLAS_DURAS}
    for codigo, n in sorted(rechazos.items()):
        lineas.append(f"  {codigo} ({descripciones[codigo]}): {n}")
    if validas_mejores:
        lineas.append(
            f"Hay {validas_mejores} alternativas válidas con menor penalización local; no se eligieron "
            "porque empeoraban el costo total (huecos, desbalance) o el algoritmo no las exploró."
        )
    else:
        lineas.append("Ninguna alternativa válida tenía menor penalización: la elección es localmente óptima.")
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# 2. Árbol de decisión de diagnóstico
# ---------------------------------------------------------------------------

@dataclass
class NodoDecision:
    """Nodo del árbol de decisión. Si es hoja, solo tiene 'conclusion'."""

    pregunta: str = ""
    prueba: Callable[[Instancia], tuple[bool, str]] | None = None
    si: NodoDecision | None = None
    no: NodoDecision | None = None
    conclusion: str = ""

    @property
    def es_hoja(self) -> bool:
        return self.prueba is None


@dataclass
class Diagnostico:
    factible: bool
    conclusion: str
    camino: list[str] = field(default_factory=list)   # preguntas y respuestas recorridas


def _horas_grupo_caben(inst: Instancia) -> tuple[bool, str]:
    exceso = []
    for g in inst.grupos.values():
        horas = sum(inst.materias[m].horas_semana for m in g.materias)
        if horas > len(inst.bloques):
            exceso.append(f"{g.id} necesita {horas} h y solo hay {len(inst.bloques)} bloques")
    return not exceso, "; ".join(exceso) or "todos los grupos caben en la semana"


def _hay_salon_para_cada_clase(inst: Instancia) -> tuple[bool, str]:
    sin_salon = sorted({
        f"{c.grupo}-{c.materia}" for c in inst.generar_clases()
        if not any(
            s.tipo == inst.materias[c.materia].salon_requerido() and s.capacidad >= inst.grupos[c.grupo].alumnos
            for s in inst.salones.values()
        )
    })
    return not sin_salon, ("sin salón adecuado: " + ", ".join(sin_salon)) if sin_salon else "toda clase tiene salón"


def _salones_alcanzan(inst: Instancia) -> tuple[bool, str]:
    problemas = []
    for tipo in ("aula", "laboratorio"):
        horas = sum(1 for c in inst.generar_clases() if inst.materias[c.materia].salon_requerido() == tipo)
        capacidad = len(inst.bloques) * sum(1 for s in inst.salones.values() if s.tipo == tipo)
        if horas > capacidad:
            problemas.append(f"{tipo}: se necesitan {horas} h y hay {capacidad} h de salón")
    return not problemas, "; ".join(problemas) or "hay horas de salón suficientes"


def _hay_maestro_para_cada_materia(inst: Instancia) -> tuple[bool, str]:
    sin_maestro = sorted({
        m for g in inst.grupos.values() for m in g.materias
        if not any(p.puede_impartir(m) for p in inst.maestros.values())
    })
    return not sin_maestro, ("nadie imparte: " + ", ".join(sin_maestro)) if sin_maestro else "toda materia tiene maestro"


def _flujo_cubre_demanda(inst: Instancia) -> tuple[bool, str]:
    a = asignar_maestros(inst)
    detalle = f"flujo máximo {a.flujo_maximo} de {a.demanda} h"
    if not a.factible:
        detalle += " -> " + "; ".join(a.faltantes)
    return a.factible, detalle


def construir_arbol_diagnostico() -> NodoDecision:
    """Árbol de decisión de reglas (de lo más barato de revisar a lo más caro)."""
    return NodoDecision(
        "¿Las horas de cada grupo caben en los bloques de la semana?", _horas_grupo_caben,
        si=NodoDecision(
            "¿Cada clase tiene al menos un salón del tipo y tamaño correctos?", _hay_salon_para_cada_clase,
            si=NodoDecision(
                "¿Las horas de salón (aulas y laboratorios) alcanzan?", _salones_alcanzan,
                si=NodoDecision(
                    "¿Cada materia tiene al menos un maestro que la imparta?", _hay_maestro_para_cada_materia,
                    si=NodoDecision(
                        "¿El flujo máximo cubre todas las horas de clase?", _flujo_cubre_demanda,
                        si=NodoDecision(conclusion="Posiblemente factible: ejecutar la búsqueda heurística."),
                        no=NodoDecision(conclusion="No factible: faltan horas de maestro (contratar o ampliar disponibilidad)."),
                    ),
                    no=NodoDecision(conclusion="No factible: hay materias sin maestro."),
                ),
                no=NodoDecision(conclusion="No factible: faltan salones (agregar salones o bloques)."),
            ),
            no=NodoDecision(conclusion="No factible: algún grupo no cabe en ningún salón adecuado."),
        ),
        no=NodoDecision(conclusion="No factible: hay grupos con más horas que bloques disponibles."),
    )


def diagnosticar(inst: Instancia, arbol: NodoDecision | None = None) -> Diagnostico:
    """Recorre el árbol desde la raíz hasta una hoja (una pregunta por nivel)."""
    nodo = arbol or construir_arbol_diagnostico()
    camino = []
    while not nodo.es_hoja:
        respuesta, detalle = nodo.prueba(inst)
        camino.append(f"{nodo.pregunta} -> {'SÍ' if respuesta else 'NO'} ({detalle})")
        nodo = nodo.si if respuesta else nodo.no
    return Diagnostico(nodo.conclusion.startswith("Posiblemente"), nodo.conclusion, camino)


def arbol_diagnostico_dot(arbol: NodoDecision | None = None) -> str:
    """Exporta el árbol de diagnóstico a Graphviz DOT."""
    arbol = arbol or construir_arbol_diagnostico()
    lineas = ["digraph Diagnostico {", "  node [fontsize=10];"]
    contador = [0]

    def visitar(nodo: NodoDecision) -> str:
        nid = f"d{contador[0]}"
        contador[0] += 1
        if nodo.es_hoja:
            color = "palegreen" if nodo.conclusion.startswith("Posiblemente") else "lightcoral"
            lineas.append(f'  {nid} [label="{nodo.conclusion}", shape=box, style=filled, fillcolor={color}];')
        else:
            lineas.append(f'  {nid} [label="{nodo.pregunta}", shape=diamond, style=filled, fillcolor=lightyellow];')
            si = visitar(nodo.si)
            no = visitar(nodo.no)
            lineas.append(f'  {nid} -> {si} [label="sí"];')
            lineas.append(f'  {nid} -> {no} [label="no"];')
        return nid

    visitar(arbol)
    lineas.append("}")
    return "\n".join(lineas)
