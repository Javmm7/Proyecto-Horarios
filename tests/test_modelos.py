"""Pruebas mínimas del Paso 2 (modelos y carga de datos).

Ejecutar desde proyecto-horarios:  py -m unittest discover tests -v
"""
import copy
import json
import unittest
from pathlib import Path

from src.modelos import Bloque, Clase, cargar_instancia, instancia_desde_dict

RUTA_EJEMPLO = Path(__file__).resolve().parent.parent / "data" / "ejemplo_pequeno.json"


class TestCargaEjemplo(unittest.TestCase):
    def setUp(self):
        self.inst = cargar_instancia(RUTA_EJEMPLO)

    def test_tamanos(self):
        self.assertEqual(len(self.inst.bloques), 12)  # 3 días x 4 horas
        self.assertEqual(len(self.inst.grupos), 3)
        self.assertEqual(len(self.inst.maestros), 3)
        self.assertEqual(len(self.inst.salones), 3)

    def test_generar_clases(self):
        clases = self.inst.generar_clases()
        # 1A: MAT 2 + PRO 2, 1B: MAT 2 + FIS 1, 2A: PRO 2 + FIS 1
        self.assertEqual(len(clases), 10)
        self.assertIn(Clase("1A", "PRO", 2), clases)

    def test_laboratorio_requiere_laboratorio(self):
        self.assertEqual(self.inst.materias["PRO"].salon_requerido(), "laboratorio")
        self.assertEqual(self.inst.materias["MAT"].salon_requerido(), "aula")

    def test_disponibilidad_y_preferencias(self):
        m2 = self.inst.maestros["M2"]
        self.assertTrue(m2.disponible_en(Bloque("Lunes", 9)))
        self.assertFalse(m2.disponible_en(Bloque("Lunes", 7)))
        self.assertIn(Bloque("Lunes", 8), self.inst.maestros["M1"].preferencias)


class TestValidacion(unittest.TestCase):
    def setUp(self):
        self.datos = json.loads(RUTA_EJEMPLO.read_text(encoding="utf-8"))

    def test_materia_inexistente(self):
        datos = copy.deepcopy(self.datos)
        datos["grupos"][0]["materias"].append("QUI")
        with self.assertRaises(ValueError):
            instancia_desde_dict(datos)

    def test_tipo_salon_invalido(self):
        datos = copy.deepcopy(self.datos)
        datos["salones"][0]["tipo"] = "auditorio"
        with self.assertRaises(ValueError):
            instancia_desde_dict(datos)

    def test_bloque_fuera_de_rango(self):
        datos = copy.deepcopy(self.datos)
        datos["maestros"][0]["disponibilidad"]["Viernes"] = [7]
        with self.assertRaises(ValueError):
            instancia_desde_dict(datos)


if __name__ == "__main__":
    unittest.main()
