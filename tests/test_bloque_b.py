"""Pruebas del Bloque B: flujo máximo, motor de inferencia y aprendizaje.

Ejecutar desde proyecto-horarios:  py -m unittest discover tests -v
"""
import copy
import json
import unittest
from pathlib import Path

from src import busqueda_heuristica as he
from src.aprendizaje import Aprendiz, UsuarioSimulado, simular_aprendizaje
from src.flujo import RedFlujo, asignar_maestros
from src.modelos import cargar_instancia, instancia_desde_dict
from src.motor_inferencia import arbol_diagnostico_dot, diagnosticar, explicar
from src.reglas import Pesos, validar_horario

DATA = Path(__file__).resolve().parent.parent / "data"
PEQUENO = cargar_instancia(DATA / "ejemplo_pequeno.json")
MEDIANO = cargar_instancia(DATA / "ejemplo_mediano.json")


def datos_pequeno():
    return json.loads((DATA / "ejemplo_pequeno.json").read_text(encoding="utf-8"))


class TestFlujo(unittest.TestCase):
    def test_red_clasica(self):
        # Ejemplo de libro: el flujo máximo es 23 (CLRS, figura 26.1)
        red = RedFlujo()
        for u, v, c in [("s", "v1", 16), ("s", "v2", 13), ("v1", "v3", 12), ("v2", "v1", 4),
                        ("v2", "v4", 14), ("v3", "v2", 9), ("v3", "t", 20), ("v4", "v3", 7), ("v4", "t", 4)]:
            red.agregar_arista(u, v, c)
        valor, _ = red.edmonds_karp("s", "t")
        self.assertEqual(valor, 23)

    def test_cubre_demanda(self):
        for inst in (PEQUENO, MEDIANO):
            a = asignar_maestros(inst)
            self.assertTrue(a.factible)
            # Ningún maestro recibe más horas de las que puede dar
            for maestro in inst.maestros.values():
                horas = sum(r.get(maestro.id, 0) for r in a.reparto.values())
                self.assertLessEqual(horas, maestro.max_horas_semana)

    def test_detecta_faltante(self):
        datos = datos_pequeno()
        for m in datos["maestros"]:
            if m["id"] == "M2":
                m["max_horas_semana"] = 1
            if m["id"] == "M3":
                m["materias"] = ["MAT"]  # nadie más da PRO
        a = asignar_maestros(instancia_desde_dict(datos))
        self.assertFalse(a.factible)
        self.assertEqual(a.demanda - a.flujo_maximo, 3)  # PRO necesita 4 h, solo hay 1
        self.assertTrue(a.faltantes)

    def test_busqueda_con_flujo_valida(self):
        r = he.backtracking_mrv(MEDIANO, usar_flujo=True)
        self.assertEqual(validar_horario(MEDIANO, r.horario), [])


class TestMotorInferencia(unittest.TestCase):
    def test_diagnostico_factible(self):
        d = diagnosticar(PEQUENO)
        self.assertTrue(d.factible)
        self.assertEqual(len(d.camino), 5)  # recorrió las 5 preguntas

    def test_diagnostico_sin_laboratorio(self):
        datos = datos_pequeno()
        datos["salones"] = [s for s in datos["salones"] if s["tipo"] != "laboratorio"]
        d = diagnosticar(instancia_desde_dict(datos))
        self.assertFalse(d.factible)
        self.assertIn("salón", d.conclusion)
        self.assertEqual(len(d.camino), 2)  # se detuvo en la segunda pregunta

    def test_diagnostico_sin_maestros(self):
        datos = copy.deepcopy(datos_pequeno())
        datos["maestros"] = [m for m in datos["maestros"] if "PRO" not in m["materias"]]
        self.assertFalse(diagnosticar(instancia_desde_dict(datos)).factible)

    def test_explicacion(self):
        r = he.backtracking_mrv(PEQUENO)
        clase = r.horario.asignaciones[0].clase
        texto = explicar(PEQUENO, r.horario, clase)
        for codigo in ("R1", "R4", "R6", "Alternativas descartadas"):
            self.assertIn(codigo, texto)

    def test_dot(self):
        self.assertTrue(arbol_diagnostico_dot().startswith("digraph"))


class TestAprendizaje(unittest.TestCase):
    def test_corrige_cuando_se_equivoca(self):
        aprendiz = Aprendiz(pesos=Pesos(1, 1, 1, 1), tasa=0.5)
        aceptado, rechazado = [3, 0, 0, 0], [0, 0, 0, 3]  # el usuario tolera huecos, no preferencias
        self.assertEqual(aprendiz.prefiere(aceptado, rechazado), "A")  # empate -> A
        self.assertTrue(aprendiz.retroalimentar(aceptado, rechazado))
        self.assertGreater(aprendiz.pesos.w4, aprendiz.pesos.w1)

    def test_usuario_simulado(self):
        u = UsuarioSimulado(Pesos(0, 0, 0, 1))
        self.assertEqual(u.elegir([9, 9, 9, 0], [0, 0, 0, 1]), "A")

    def test_simulacion_mejora(self):
        r = simular_aprendizaje(PEQUENO, rondas=30)
        self.assertGreater(r.concordancia[-1], r.concordancia[0])
        self.assertLessEqual(r.costo_usuario_despues, r.costo_usuario_antes)


if __name__ == "__main__":
    unittest.main()
