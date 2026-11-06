"""Prueba que cada comando de la terminal corra y diga lo que debe decir.

Ejecutar desde proyecto-horarios:  py -m unittest discover tests -v
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# (argumentos, texto que debe aparecer en la salida)
CASOS = [
    (["resumen"], "Clases por asignar"),
    (["resolver", "--algoritmo", "mrv-fc"], "Validación de reglas duras: OK"),
    (["resolver", "--algoritmo", "exhaustiva", "--datos", "data/ejemplo_mini.json", "--arbol", "15"], "Árbol de búsqueda"),
    (["diagnosticar", "--datos", "data/ejemplo_mediano.json"], "Conclusión: Posiblemente factible"),
    (["explicar", "--clase", "1A-MAT-1"], "Alternativas descartadas"),
    (["flujo"], "Flujo máximo (Edmonds-Karp): 10 de 10"),
    (["comparar", "--datos", "data/ejemplo_mini.json"], "Recocido simulado"),
]


class TestTerminal(unittest.TestCase):
    def test_comandos(self):
        entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        for argumentos, esperado in CASOS:
            with self.subTest(comando=" ".join(argumentos)):
                salida = subprocess.run(
                    [sys.executable, "-m", "src.main", *argumentos],
                    cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", timeout=120, env=entorno,
                )
                self.assertEqual(salida.returncode, 0, salida.stderr)
                self.assertIn(esperado, salida.stdout)


if __name__ == "__main__":
    unittest.main()
