"""Base de conocimiento del sistema experto (Paso 3).

Contiene:
- Reglas DURAS (R1..R6): si se violan, la asignación se rechaza (poda).
- Reglas SUAVES (S1..S6): no prohíben nada, solo suman costo.
- La función objetivo:
    costo = w1*huecos + w2*horarios_malos + w3*desbalance + w4*preferencias_incumplidas

Cada regla dura es una función pequeña que devuelve un mensaje si se viola
o None si se cumple. Así el motor de inferencia puede explicar POR QUÉ
rechazó una opción.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import product
from typing import Callable

from src.modelos import Asignacion, Clase, Horario, Instancia


@dataclass
class Pesos:
    """Pesos de la función objetivo (el módulo de aprendizaje los ajusta)."""

    w1: float = 3.0  # huecos en el horario de los grupos
    w2: float = 1.0  # horarios malos (muy temprano/tarde, misma materia el mismo día)
    w3: float = 0.5  # desbalance de carga entre maestros
    w4: float = 1.0  # preferencias de maestros incumplidas


class Ocupacion:
    """Índices de lo que ya está ocupado en un horario parcial.

    Sirven para revisar las reglas rápido: en lugar de recorrer todo el horario,
    se pregunta "¿(maestro, bloque) ya está ocupado?" en un conjunto.
    """

    def __init__(self) -> None:
        self.maestro_bloque: set = set()
        self.salon_bloque: set = set()
        self.grupo_bloque: set = set()
        self.horas_dia: Counter = Counter()        # (maestro, dia) -> horas
        self.horas_semana: Counter = Counter()     # maestro -> horas
        self.dias_materia: defaultdict = defaultdict(Counter)       # (grupo, materia) -> {dia: n}
        self.maestros_materia: defaultdict = defaultdict(Counter)   # (grupo, materia) -> {maestro: n}

    @classmethod
    def desde_horario(cls, horario: Horario) -> Ocupacion:
        ocup = cls()
        for a in horario.asignaciones:
            ocup.agregar(a)
        return ocup

    def agregar(self, a: Asignacion) -> None:
        self.maestro_bloque.add((a.maestro, a.bloque))
        self.salon_bloque.add((a.salon, a.bloque))
        self.grupo_bloque.add((a.clase.grupo, a.bloque))
        self.horas_dia[(a.maestro, a.bloque.dia)] += 1
        self.horas_semana[a.maestro] += 1
        clave = (a.clase.grupo, a.clase.materia)
        self.dias_materia[clave][a.bloque.dia] += 1
        self.maestros_materia[clave][a.maestro] += 1

    def quitar(self, a: Asignacion) -> None:
        self.maestro_bloque.discard((a.maestro, a.bloque))
        self.salon_bloque.discard((a.salon, a.bloque))
        self.grupo_bloque.discard((a.clase.grupo, a.bloque))
        self.horas_dia[(a.maestro, a.bloque.dia)] -= 1
        self.horas_semana[a.maestro] -= 1
        clave = (a.clase.grupo, a.clase.materia)
        self.dias_materia[clave][a.bloque.dia] -= 1
        self.maestros_materia[clave][a.maestro] -= 1
        # Limpiar contadores en cero para que "len()" refleje solo lo usado
        self.dias_materia[clave] += Counter()
        self.maestros_materia[clave] += Counter()


# ---------------------------------------------------------------------------
# Reglas DURAS: SI <condición> ENTONCES rechazar la asignación
# ---------------------------------------------------------------------------

def r1_maestro_libre(inst: Instancia, ocup: Ocupacion, a: Asignacion) -> str | None:
    if (a.maestro, a.bloque) in ocup.maestro_bloque:
        return f"el maestro {a.maestro} ya tiene clase el {a.bloque}"
    return None


def r2_salon_libre(inst: Instancia, ocup: Ocupacion, a: Asignacion) -> str | None:
    if (a.salon, a.bloque) in ocup.salon_bloque:
        return f"el salón {a.salon} ya está ocupado el {a.bloque}"
    return None


def r3_grupo_libre(inst: Instancia, ocup: Ocupacion, a: Asignacion) -> str | None:
    if (a.clase.grupo, a.bloque) in ocup.grupo_bloque:
        return f"el grupo {a.clase.grupo} ya tiene clase el {a.bloque}"
    return None


def r4_salon_adecuado(inst: Instancia, ocup: Ocupacion, a: Asignacion) -> str | None:
    salon = inst.salones[a.salon]
    grupo = inst.grupos[a.clase.grupo]
    requerido = inst.materias[a.clase.materia].salon_requerido()
    if salon.tipo != requerido:
        return f"{a.clase.materia} necesita {requerido} y {a.salon} es {salon.tipo}"
    if salon.capacidad < grupo.alumnos:
        return f"{a.salon} tiene {salon.capacidad} lugares y el grupo {grupo.id} tiene {grupo.alumnos} alumnos"
    return None


def r5_maestro_disponible(inst: Instancia, ocup: Ocupacion, a: Asignacion) -> str | None:
    maestro = inst.maestros[a.maestro]
    if not maestro.puede_impartir(a.clase.materia):
        return f"{maestro.nombre} no imparte {a.clase.materia}"
    if not maestro.disponible_en(a.bloque):
        return f"{maestro.nombre} no está disponible el {a.bloque}"
    return None


def r6_carga_maxima(inst: Instancia, ocup: Ocupacion, a: Asignacion) -> str | None:
    maestro = inst.maestros[a.maestro]
    if ocup.horas_dia[(a.maestro, a.bloque.dia)] >= maestro.max_horas_dia:
        return f"{maestro.nombre} ya tiene {maestro.max_horas_dia} h el {a.bloque.dia} (máximo diario)"
    if ocup.horas_semana[a.maestro] >= maestro.max_horas_semana:
        return f"{maestro.nombre} ya tiene {maestro.max_horas_semana} h en la semana (máximo semanal)"
    return None


Regla = Callable[[Instancia, Ocupacion, Asignacion], "str | None"]

# Lista ordenada de reglas duras: (código, descripción, función)
REGLAS_DURAS: list[tuple[str, str, Regla]] = [
    ("R1", "Un maestro no puede estar en dos grupos al mismo tiempo", r1_maestro_libre),
    ("R2", "Un salón no puede tener dos clases al mismo tiempo", r2_salon_libre),
    ("R3", "Un grupo no puede tener dos materias al mismo tiempo", r3_grupo_libre),
    ("R4", "El salón debe tener capacidad y tipo adecuados", r4_salon_adecuado),
    ("R5", "Respetar disponibilidad y materias del maestro", r5_maestro_disponible),
    ("R6", "No exceder el máximo de horas diarias/semanales del maestro", r6_carga_maxima),
]

# R4 y R5 no dependen del horario: se pueden revisar una sola vez al inicio
REGLAS_ESTATICAS = {"R4", "R5"}


def primera_violacion(inst: Instancia, ocup: Ocupacion, a: Asignacion) -> tuple[str, str] | None:
    """Devuelve (código, motivo) de la primera regla dura violada, o None si es válida."""
    for codigo, _, regla in REGLAS_DURAS:
        motivo = regla(inst, ocup, a)
        if motivo:
            return codigo, motivo
    return None


def violaciones(inst: Instancia, ocup: Ocupacion, a: Asignacion) -> list[tuple[str, str]]:
    """Todas las reglas duras que viola la asignación (para explicaciones)."""
    resultado = []
    for codigo, _, regla in REGLAS_DURAS:
        motivo = regla(inst, ocup, a)
        if motivo:
            resultado.append((codigo, motivo))
    return resultado


def es_valida(inst: Instancia, ocup: Ocupacion, a: Asignacion) -> bool:
    return primera_violacion(inst, ocup, a) is None


def validar_horario(inst: Instancia, horario: Horario) -> list[str]:
    """Revisa un horario completo. Devuelve la lista de problemas (vacía = válido)."""
    problemas = []
    ocup = Ocupacion()
    for a in horario.asignaciones:
        for codigo, motivo in violaciones(inst, ocup, a):
            problemas.append(f"{codigo} en {a.clase.id}: {motivo}")
        ocup.agregar(a)
    asignadas = Counter(a.clase for a in horario.asignaciones)
    for clase in inst.generar_clases():
        if asignadas[clase] != 1:
            problemas.append(f"{clase.id} asignada {asignadas[clase]} veces")
    return problemas


# ---------------------------------------------------------------------------
# Opciones (dominio) de cada clase
# ---------------------------------------------------------------------------

def todas_las_opciones(inst: Instancia, clase: Clase) -> list[Asignacion]:
    """Dominio completo: TODAS las combinaciones bloque x salón x maestro, sin filtrar."""
    return [
        Asignacion(clase, bloque, salon, maestro)
        for bloque, salon, maestro in product(inst.bloques, inst.salones, inst.maestros)
    ]


def dominio_estatico(inst: Instancia, clase: Clase) -> list[Asignacion]:
    """Dominio pre-filtrado con las reglas que no dependen del horario (R4 y R5).

    Es una forma de optimizar la búsqueda: lo imposible se descarta una sola vez.
    """
    vacio = Ocupacion()
    return [
        a for a in todas_las_opciones(inst, clase)
        if r4_salon_adecuado(inst, vacio, a) is None and r5_maestro_disponible(inst, vacio, a) is None
    ]


# ---------------------------------------------------------------------------
# Reglas SUAVES y función objetivo
# ---------------------------------------------------------------------------

def costo_local(inst: Instancia, ocup: Ocupacion, a: Asignacion, pesos: Pesos) -> float:
    """Penalización que agrega UNA asignación sobre el horario parcial actual.

    Cubre S2, S3, S5 y S6. Su suma sobre todas las asignaciones es exactamente
    esa parte del costo total (sirve como costo g(n) en A*).
    """
    total = 0.0
    if a.bloque.hora in (inst.horas[0], inst.horas[-1]):                  # S2
        total += pesos.w2
    clave = (a.clase.grupo, a.clase.materia)
    if ocup.dias_materia[clave][a.bloque.dia] > 0:                        # S3
        total += pesos.w2
    maestro = inst.maestros[a.maestro]
    if maestro.preferencias and a.bloque not in maestro.preferencias:      # S5
        total += pesos.w4
    usados = ocup.maestros_materia[clave]
    if usados and a.maestro not in usados:                                 # S6
        total += pesos.w4
    return total


def contar_huecos(inst: Instancia, horario: Horario) -> int:
    """S1: horas libres entre la primera y la última clase del día de cada grupo."""
    posiciones = defaultdict(list)  # (grupo, dia) -> índices de hora
    for a in horario.asignaciones:
        posiciones[(a.clase.grupo, a.bloque.dia)].append(inst.horas.index(a.bloque.hora))
    huecos = 0
    for indices in posiciones.values():
        huecos += (max(indices) - min(indices) + 1) - len(indices)
    return huecos


def desbalance(inst: Instancia, horario: Horario) -> float:
    """S4: suma de |horas del maestro - promedio| entre los maestros que dan clase."""
    horas = Counter(a.maestro for a in horario.asignaciones)
    if not horas:
        return 0.0
    promedio = sum(horas.values()) / len(horas)
    return sum(abs(h - promedio) for h in horas.values())


def costo(inst: Instancia, horario: Horario, pesos: Pesos | None = None) -> tuple[float, dict]:
    """Función objetivo. Devuelve (costo_total, desglose por regla suave)."""
    pesos = pesos or Pesos()
    extremos = sum(1 for a in horario.asignaciones if a.bloque.hora in (inst.horas[0], inst.horas[-1]))

    dias_materia = Counter((a.clase.grupo, a.clase.materia, a.bloque.dia) for a in horario.asignaciones)
    mismo_dia = sum(n - 1 for n in dias_materia.values())

    pref = 0
    for a in horario.asignaciones:
        maestro = inst.maestros[a.maestro]
        if maestro.preferencias and a.bloque not in maestro.preferencias:
            pref += 1

    maestros_por_materia = defaultdict(set)
    for a in horario.asignaciones:
        maestros_por_materia[(a.clase.grupo, a.clase.materia)].add(a.maestro)
    distintos = sum(len(m) - 1 for m in maestros_por_materia.values())

    huecos = contar_huecos(inst, horario)
    desb = desbalance(inst, horario)

    total = (
        pesos.w1 * huecos
        + pesos.w2 * (extremos + mismo_dia)
        + pesos.w3 * desb
        + pesos.w4 * (pref + distintos)
    )
    desglose = {
        "huecos (S1)": huecos,
        "horas extremas (S2)": extremos,
        "misma materia mismo día (S3)": mismo_dia,
        "desbalance (S4)": round(desb, 2),
        "fuera de preferencia (S5)": pref,
        "maestros distintos por materia (S6)": distintos,
    }
    return round(total, 2), desglose
