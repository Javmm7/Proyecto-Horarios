"""Modelos de datos del sistema experto de horarios.

Este módulo solo define las "piezas" del problema (bloque, materia, grupo,
maestro, salón, clase, asignación, horario) y cómo cargarlas desde JSON.
Las reglas (restricciones) viven en reglas.py; aquí no se decide nada.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

TIPOS_MATERIA = {"teoria", "laboratorio"}
TIPOS_SALON = {"aula", "laboratorio"}


@dataclass(frozen=True)
class Bloque:
    """Una hora de clase en un día concreto, por ejemplo Lunes a las 7:00."""

    dia: str
    hora: int

    @property
    def id(self) -> str:
        return f"{self.dia}-{self.hora}"

    def __str__(self) -> str:
        return f"{self.dia} {self.hora}:00"


@dataclass(frozen=True)
class Materia:
    """Materia del plan de estudios (horas por semana y tipo)."""

    id: str
    nombre: str
    horas_semana: int
    tipo: str  # "teoria" o "laboratorio"

    def salon_requerido(self) -> str:
        """Tipo de salón que necesita: laboratorio para prácticas, aula para teoría."""
        return "laboratorio" if self.tipo == "laboratorio" else "aula"


@dataclass(frozen=True)
class Grupo:
    """Grupo de alumnos que cursa un conjunto de materias."""

    id: str
    alumnos: int
    materias: tuple[str, ...]


@dataclass(frozen=True)
class Maestro:
    """Maestro con las materias que puede dar, su disponibilidad y sus límites."""

    id: str
    nombre: str
    materias: frozenset[str]
    disponibilidad: frozenset[Bloque]
    max_horas_dia: int
    max_horas_semana: int
    preferencias: frozenset[Bloque] = frozenset()

    def puede_impartir(self, materia_id: str) -> bool:
        return materia_id in self.materias

    def disponible_en(self, bloque: Bloque) -> bool:
        return bloque in self.disponibilidad


@dataclass(frozen=True)
class Salon:
    """Salón físico con su capacidad y tipo."""

    id: str
    capacidad: int
    tipo: str  # "aula" o "laboratorio"


@dataclass(frozen=True)
class Clase:
    """Una sesión de 1 hora que hay que colocar en el horario.

    Es la VARIABLE del problema de búsqueda: si Matemáticas tiene 2 horas
    a la semana para el grupo 1A, se generan dos clases (sesión 1 y 2).
    """

    grupo: str
    materia: str
    sesion: int

    @property
    def id(self) -> str:
        return f"{self.grupo}-{self.materia}-{self.sesion}"


@dataclass(frozen=True)
class Asignacion:
    """Decisión tomada para una clase: en qué bloque, salón y con qué maestro."""

    clase: Clase
    bloque: Bloque
    salon: str
    maestro: str


@dataclass
class Horario:
    """Horario (completo o parcial) = lista de asignaciones.

    Un horario parcial es un ESTADO del árbol de búsqueda.
    """

    asignaciones: list[Asignacion] = field(default_factory=list)

    def agregar(self, asignacion: Asignacion) -> None:
        self.asignaciones.append(asignacion)

    def quitar_ultima(self) -> Asignacion:
        """Deshace la última decisión (se usa al hacer backtracking)."""
        return self.asignaciones.pop()

    def copia(self) -> Horario:
        return Horario(list(self.asignaciones))

    def por_grupo(self, grupo_id: str) -> list[Asignacion]:
        return [a for a in self.asignaciones if a.clase.grupo == grupo_id]

    def por_maestro(self, maestro_id: str) -> list[Asignacion]:
        return [a for a in self.asignaciones if a.maestro == maestro_id]

    def por_salon(self, salon_id: str) -> list[Asignacion]:
        return [a for a in self.asignaciones if a.salon == salon_id]

    def __len__(self) -> int:
        return len(self.asignaciones)


@dataclass
class Instancia:
    """Todos los datos de entrada de un problema concreto."""

    nombre: str
    dias: list[str]
    horas: list[int]
    bloques: list[Bloque]
    materias: dict[str, Materia]
    grupos: dict[str, Grupo]
    maestros: dict[str, Maestro]
    salones: dict[str, Salon]

    def generar_clases(self) -> list[Clase]:
        """Convierte (grupo, materia, horas) en la lista de clases por asignar."""
        clases = []
        for grupo in self.grupos.values():
            for materia_id in grupo.materias:
                horas = self.materias[materia_id].horas_semana
                for sesion in range(1, horas + 1):
                    clases.append(Clase(grupo.id, materia_id, sesion))
        return clases

    def resumen(self) -> str:
        """Texto corto con el tamaño de la instancia."""
        return (
            f"Instancia: {self.nombre}\n"
            f"  Bloques:  {len(self.bloques)} ({', '.join(self.dias)}, {self.horas[0]}:00-{self.horas[-1]}:00)\n"
            f"  Materias: {len(self.materias)}\n"
            f"  Grupos:   {len(self.grupos)}\n"
            f"  Maestros: {len(self.maestros)}\n"
            f"  Salones:  {len(self.salones)}\n"
            f"  Clases por asignar: {len(self.generar_clases())}"
        )


# ---------------------------------------------------------------------------
# Carga desde JSON
# ---------------------------------------------------------------------------

def cargar_instancia(ruta: str | Path) -> Instancia:
    """Lee un archivo JSON y devuelve una Instancia validada."""
    with open(ruta, encoding="utf-8") as archivo:
        datos = json.load(archivo)
    return instancia_desde_dict(datos)


def instancia_desde_dict(datos: dict) -> Instancia:
    """Construye la Instancia a partir de un diccionario (mismo formato que el JSON).

    Lanza ValueError con un mensaje claro si los datos son inconsistentes.
    """
    dias = list(datos["dias"])
    horas = sorted(datos["horas"])
    bloques = [Bloque(dia, hora) for dia in dias for hora in horas]
    validos = set(bloques)

    materias = {}
    for m in datos["materias"]:
        if m["tipo"] not in TIPOS_MATERIA:
            raise ValueError(f"Materia {m['id']}: tipo inválido '{m['tipo']}'")
        if m["horas_semana"] <= 0:
            raise ValueError(f"Materia {m['id']}: horas_semana debe ser positiva")
        materias[m["id"]] = Materia(m["id"], m["nombre"], m["horas_semana"], m["tipo"])

    grupos = {}
    for g in datos["grupos"]:
        for materia_id in g["materias"]:
            _exigir_materia(materia_id, materias, f"Grupo {g['id']}")
        grupos[g["id"]] = Grupo(g["id"], g["alumnos"], tuple(g["materias"]))

    maestros = {}
    for p in datos["maestros"]:
        contexto = f"Maestro {p['id']}"
        for materia_id in p["materias"]:
            _exigir_materia(materia_id, materias, contexto)
        disponibilidad = (
            _leer_bloques(p["disponibilidad"], validos, contexto)
            if "disponibilidad" in p
            else frozenset(bloques)  # si no se indica, está disponible siempre
        )
        maestros[p["id"]] = Maestro(
            id=p["id"],
            nombre=p["nombre"],
            materias=frozenset(p["materias"]),
            disponibilidad=disponibilidad,
            max_horas_dia=p["max_horas_dia"],
            max_horas_semana=p["max_horas_semana"],
            preferencias=_leer_bloques(p.get("preferencias", {}), validos, contexto),
        )

    salones = {}
    for s in datos["salones"]:
        if s["tipo"] not in TIPOS_SALON:
            raise ValueError(f"Salón {s['id']}: tipo inválido '{s['tipo']}'")
        salones[s["id"]] = Salon(s["id"], s["capacidad"], s["tipo"])

    return Instancia(datos.get("nombre", "sin nombre"), dias, horas, bloques, materias, grupos, maestros, salones)


def _exigir_materia(materia_id: str, materias: dict[str, Materia], contexto: str) -> None:
    if materia_id not in materias:
        raise ValueError(f"{contexto}: la materia '{materia_id}' no existe")


def _leer_bloques(por_dia: dict[str, list[int]], validos: set[Bloque], contexto: str) -> frozenset[Bloque]:
    """Convierte {"Lunes": [7, 8]} en {Bloque("Lunes", 7), Bloque("Lunes", 8)}."""
    resultado = set()
    for dia, horas in por_dia.items():
        for hora in horas:
            bloque = Bloque(dia, hora)
            if bloque not in validos:
                raise ValueError(f"{contexto}: el bloque {bloque} no existe en la instancia")
            resultado.add(bloque)
    return frozenset(resultado)
