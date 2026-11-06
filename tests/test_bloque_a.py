"""Pruebas del Bloque A: reglas, ordenamiento, árbol y algoritmos de búsqueda.

Ejecutar desde proyecto-horarios:  py -m unittest discover tests -v
"""
import random
import unittest
from pathlib import Path

from src import busqueda_exhaustiva as ex
from src import busqueda_heuristica as he
from src.arbol_decision import ArbolBusqueda
from src.modelos import Asignacion, Bloque, Clase, Horario, cargar_instancia
from src.ordenamiento import merge_sort, quicksort
from src.reglas import Ocupacion, costo, contar_huecos, primera_violacion, validar_horario

DATA = Path(__file__).resolve().parent.parent / "data"
MINI = cargar_instancia(DATA / "ejemplo_mini.json")
PEQUENO = cargar_instancia(DATA / "ejemplo_pequeno.json")


def asig(grupo, materia, sesion, dia, hora, salon, maestro):
    return Asignacion(Clase(grupo, materia, sesion), Bloque(dia, hora), salon, maestro)


class TestReglasDuras(unittest.TestCase):
    def setUp(self):
        self.ocup = Ocupacion()
        self.ocup.agregar(asig("1A", "MAT", 1, "Lunes", 8, "A101", "M1"))

    def codigo(self, a):
        v = primera_violacion(PEQUENO, self.ocup, a)
        return v[0] if v else None

    def test_valida(self):
        self.assertIsNone(self.codigo(asig("1A", "MAT", 2, "Martes", 8, "A101", "M1")))

    def test_r1_maestro_ocupado(self):
        self.assertEqual(self.codigo(asig("1B", "MAT", 1, "Lunes", 8, "A102", "M1")), "R1")

    def test_r2_salon_ocupado(self):
        self.assertEqual(self.codigo(asig("1B", "MAT", 1, "Lunes", 8, "A101", "M3")), "R2")

    def test_r3_grupo_ocupado(self):
        self.assertEqual(self.codigo(asig("1A", "PRO", 1, "Lunes", 8, "LAB1", "M2")), "R3")

    def test_r4_tipo_y_capacidad(self):
        self.assertEqual(self.codigo(asig("1A", "PRO", 1, "Martes", 9, "A102", "M2")), "R4")  # aula para lab
        self.assertEqual(self.codigo(asig("1A", "MAT", 2, "Martes", 9, "A102", "M1")), "R4")  # 25 < 30 alumnos

    def test_r5_disponibilidad(self):
        self.assertEqual(self.codigo(asig("2A", "PRO", 1, "Lunes", 7, "LAB1", "M2")), "R5")
        self.assertEqual(self.codigo(asig("2A", "PRO", 1, "Martes", 7, "LAB1", "M1")), "R5")  # no imparte PRO

    def test_r6_maximo_diario(self):
        self.ocup.agregar(asig("1B", "MAT", 1, "Lunes", 9, "A101", "M1"))
        self.ocup.agregar(asig("1B", "FIS", 1, "Lunes", 10, "A101", "M1"))
        self.assertEqual(self.codigo(asig("2A", "FIS", 1, "Lunes", 7, "A102", "M1")), "R6")


class TestCosto(unittest.TestCase):
    def test_huecos(self):
        h = Horario([
            asig("1A", "MAT", 1, "Lunes", 7, "A101", "M1"),
            asig("1A", "MAT", 2, "Lunes", 10, "A101", "M1"),
        ])
        self.assertEqual(contar_huecos(PEQUENO, h), 2)  # 8:00 y 9:00 libres

    def test_costo_vacio(self):
        self.assertEqual(costo(PEQUENO, Horario())[0], 0)


class TestOrdenamiento(unittest.TestCase):
    def test_contra_sorted(self):
        azar = random.Random(1)
        for _ in range(50):
            lista = [azar.randint(-20, 20) for _ in range(azar.randint(0, 30))]
            self.assertEqual(merge_sort(lista), sorted(lista))
            self.assertEqual(quicksort(lista), sorted(lista))

    def test_clave_y_estabilidad(self):
        datos = [("b", 2), ("a", 1), ("c", 2), ("d", 1)]
        self.assertEqual(merge_sort(datos, clave=lambda x: x[1]), [("a", 1), ("d", 1), ("b", 2), ("c", 2)])


class TestArbol(unittest.TestCase):
    def setUp(self):
        #        0
        #      /   \
        #     1     2
        #    / \
        #   3   4
        self.arbol = ArbolBusqueda()
        a = self.arbol.agregar(0, "A", "valido")
        self.arbol.agregar(0, "B", "podado", "R1")
        self.arbol.agregar(a, "C", "valido")
        self.arbol.agregar(a, "D", "solucion")

    def ids(self, nodos):
        return [n.id for n in nodos]

    def test_recorridos(self):
        self.assertEqual(self.ids(self.arbol.preorden()), [0, 1, 3, 4, 2])
        self.assertEqual(self.ids(self.arbol.postorden()), [3, 4, 1, 2, 0])
        self.assertEqual(self.ids(self.arbol.inorden()), [3, 1, 4, 0, 2])
        self.assertEqual(self.ids(self.arbol.por_niveles()), [0, 1, 2, 3, 4])

    def test_limite(self):
        arbol = ArbolBusqueda(limite=2)
        self.assertIsNotNone(arbol.agregar(0, "A", "valido"))
        self.assertIsNone(arbol.agregar(0, "B", "valido"))


class TestAlgoritmos(unittest.TestCase):
    def comprobar(self, inst, r):
        self.assertTrue(r.encontro_solucion, r.notas)
        self.assertEqual(validar_horario(inst, r.horario), [])

    def test_todos_dan_horarios_validos(self):
        for inst in (MINI, PEQUENO):
            self.comprobar(inst, ex.backtracking(inst))
            self.comprobar(inst, he.backtracking_mrv(inst, forward_checking=False))
            self.comprobar(inst, he.backtracking_mrv(inst, forward_checking=True))
            self.comprobar(inst, he.greedy(inst))
            self.comprobar(inst, he.recocido_simulado(inst, iteraciones=300))
        self.comprobar(MINI, he.a_estrella(MINI, ancho_haz=None))

    def test_exhaustivas_coinciden_en_el_optimo(self):
        dfs = ex.backtracking(MINI, buscar_optimo=True)
        bfs = ex.bfs(MINI)
        self.assertTrue(dfs.completo and bfs.completo)
        self.assertEqual(dfs.costo, bfs.costo)
        self.assertEqual(dfs.nodos, bfs.nodos)  # mismo árbol, distinto orden

    def test_heuristicas_no_superan_al_optimo(self):
        optimo = ex.backtracking(MINI, buscar_optimo=True).costo
        for r in (he.a_estrella(MINI, ancho_haz=None), he.recocido_simulado(MINI)):
            self.assertGreaterEqual(r.costo, optimo)

    def test_recocido_no_empeora(self):
        inicial = he.backtracking_mrv(PEQUENO)
        r = he.recocido_simulado(PEQUENO, inicial=inicial.horario, iteraciones=500)
        self.assertLessEqual(r.costo, inicial.costo)
        self.assertEqual(len(r.historial), 501)

    def test_arbol_registrado(self):
        r = ex.backtracking(MINI, arbol_limite=50)
        self.assertLessEqual(len(r.arbol.nodos), 50)
        self.assertIn("podado", r.arbol.conteo())


if __name__ == "__main__":
    unittest.main()
