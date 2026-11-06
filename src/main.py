"""Punto de entrada por terminal (CLI).

Uso (desde la carpeta proyecto-horarios):
    py -m src.main resumen
    py -m src.main resolver --algoritmo mrv-fc
    py -m src.main resolver --algoritmo exhaustiva --arbol 40
    py -m src.main comparar
    py -m src.main comparar --datos data/ejemplo_mini.json
    py -m src.main diagnosticar --datos data/ejemplo_mediano.json
    py -m src.main explicar --clase 1A-MAT-1
    py -m src.main flujo
    py -m src.main aprender
    py -m src.main experimentos        (genera tablas y gráficas en resultados/)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src import busqueda_exhaustiva as ex
from src import busqueda_heuristica as he
from src.aprendizaje import guardar_pesos, simular_aprendizaje
from src.flujo import asignar_maestros
from src.modelos import Instancia, cargar_instancia
from src.motor_inferencia import diagnosticar, explicar
from src.reglas import validar_horario
from src.resultado import Resultado
from src.visualizacion import horario_texto, tabla_resultados

# Nombre en la terminal -> función que ejecuta el algoritmo
ALGORITMOS = {
    "exhaustiva": lambda inst, n: ex.backtracking(inst, arbol_limite=n),
    "exhaustiva-optima": lambda inst, n: ex.backtracking(inst, buscar_optimo=True, max_nodos=100_000, arbol_limite=n),
    "bfs": lambda inst, n: ex.bfs(inst, max_nodos=200_000),
    "mrv": lambda inst, n: he.backtracking_mrv(inst, forward_checking=False, arbol_limite=n),
    "mrv-fc": lambda inst, n: he.backtracking_mrv(inst, forward_checking=True, arbol_limite=n),
    "flujo-mrv": lambda inst, n: he.backtracking_mrv(inst, usar_flujo=True, arbol_limite=n),
    "greedy": lambda inst, n: he.greedy(inst),
    "a-estrella": lambda inst, n: he.a_estrella(inst),
    "colina": lambda inst, n: he.ascenso_colina(inst),
    "recocido": lambda inst, n: he.recocido_simulado(inst),
}


def mostrar(inst: Instancia, r: Resultado, arbol_lineas: int) -> None:
    print(tabla_resultados([r]))
    if r.notas:
        print(f"Nota: {r.notas}")
    if not r.horario:
        print("No se encontró horario.")
        return
    problemas = validar_horario(inst, r.horario)
    print("Validación de reglas duras:", "OK" if not problemas else problemas)
    print("Desglose del costo:", r.desglose)
    print(horario_texto(inst, r.horario))
    if r.arbol:
        print(f"\nÁrbol de búsqueda (primeros nodos, preorden). Conteo: {r.arbol.conteo()}")
        print("  * raíz   + válido   x podado   # solución")
        print(r.arbol.a_texto(arbol_lineas))
        destino = Path("resultados") / f"arbol_{r.algoritmo.split()[0].lower()}.dot"
        destino.parent.mkdir(exist_ok=True)
        destino.write_text(r.arbol.a_dot(), encoding="utf-8")
        print(f"Árbol exportado a {destino} (formato Graphviz)")


def main() -> None:
    sys.stdout.reconfigure(errors="replace")  # evita errores de acentos en consolas antiguas
    parser = argparse.ArgumentParser(description="Sistema experto de horarios escolares")
    parser.add_argument("comando", nargs="?", default="resumen",
                        choices=["resumen", "resolver", "comparar", "diagnosticar", "explicar",
                                 "flujo", "aprender", "experimentos"])
    parser.add_argument("--datos", default="data/ejemplo_pequeno.json", help="Archivo JSON de entrada")
    parser.add_argument("--algoritmo", default="mrv-fc", choices=list(ALGORITMOS))
    parser.add_argument("--arbol", type=int, default=0, help="Guardar y mostrar los primeros N nodos del árbol")
    parser.add_argument("--clase", default=None, help="Clase a explicar, p. ej. 1A-MAT-1")
    args = parser.parse_args()

    if args.comando == "experimentos":
        from src.experimentos import correr_todo
        correr_todo()
        return

    inst = cargar_instancia(args.datos)
    print(inst.resumen())

    if args.comando == "resumen":
        print("\nClases por asignar (variables del problema):")
        for clase in inst.generar_clases():
            print(f"  - {clase.id}")
    elif args.comando == "resolver":
        print()
        mostrar(inst, ALGORITMOS[args.algoritmo](inst, args.arbol), max(args.arbol, 40))
    elif args.comando == "diagnosticar":
        d = diagnosticar(inst)
        print("\nÁrbol de decisión de diagnóstico (camino recorrido):")
        for paso in d.camino:
            print(f"  {paso}")
        print(f"Conclusión: {d.conclusion}")
    elif args.comando == "explicar":
        r = he.recocido_simulado(inst)
        if not r.horario:
            print("No hay horario que explicar.")
            return
        clases = {a.clase.id: a.clase for a in r.horario.asignaciones}
        clase = clases.get(args.clase) or r.horario.asignaciones[0].clase
        print(f"\n(Horario generado con recocido simulado, costo {r.costo})\n")
        print(explicar(inst, r.horario, clase))
    elif args.comando == "flujo":
        a = asignar_maestros(inst)
        print(f"\nFlujo máximo (Edmonds-Karp): {a.flujo_maximo} de {a.demanda} horas cubiertas")
        print(f"Caminos aumentantes encontrados: {len(a.caminos)}")
        for camino, cuello in a.caminos[:10]:
            print(f"  {' -> '.join(camino)}  (+{cuello} h)")
        print("\nReparto maestro-materia:")
        for (grupo, materia), maestros in a.reparto.items():
            print(f"  {grupo}-{materia}: {maestros}")
        for f in a.faltantes:
            print(f"  FALTA: {f}")
    elif args.comando == "aprender":
        print("\nSimulando retroalimentación de un usuario con preferencias ocultas...")
        a = simular_aprendizaje(inst)
        print(f"Coincidencia con el usuario por ronda: {[round(c) for c in a.concordancia]}")
        print(f"Pesos iniciales: {a.pesos[0]}  ->  aprendidos: {a.pesos[-1]}")
        print(f"Preferencia oculta del usuario: {a.pesos_ocultos}")
        print(f"Costo del horario según el usuario: {a.costo_usuario_antes} -> {a.costo_usuario_despues}")
        guardar_pesos(a.aprendiz.pesos)
        print("Pesos guardados en resultados/pesos_aprendidos.json")
    else:
        print("\nComparando algoritmos...\n")
        resultados = []
        for nombre, funcion in ALGORITMOS.items():
            r = funcion(inst, 0)
            resultados.append(r)
            if r.notas:
                print(f"[{r.algoritmo}] {r.notas}")
        print()
        print(tabla_resultados(resultados))


if __name__ == "__main__":
    main()
