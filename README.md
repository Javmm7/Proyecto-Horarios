# Sistema experto para asignación de horarios escolares

Proyecto final de Inteligencia Artificial / Sistemas Expertos. El sistema genera horarios de clase que cumplen las reglas obligatorias (sin traslapes, salón adecuado, disponibilidad y carga de los maestros) y optimiza su calidad (menos huecos, carga balanceada, preferencias). También explica sus decisiones y aprende de la retroalimentación del usuario.

Incluye búsqueda exhaustiva (DFS y BFS), búsqueda heurística (MRV, forward checking, greedy, A\*, ascenso de colina, recocido simulado), recorridos de árbol, ordenamiento propio (merge sort y quicksort), flujo máximo (Edmonds-Karp) y simulación de aprendizaje.

- Definición del problema: [docs/problema.md](docs/problema.md)
- Reporte con resultados: [docs/reporte.md](docs/reporte.md)
- Guion de exposición, video y preguntas probables: [docs/guion_exposicion.md](docs/guion_exposicion.md)

## Instalación

Requiere Python 3.10 o más reciente. En Windows se usa el comando `py`.

```bash
py -m pip install -r requirements.txt
```

## Interfaz web (localhost)

```bash
py -m streamlit run app.py
```

Se abre en http://localhost:8501 y tiene seis pestañas: problema y reglas, diagnóstico y flujo, resolver (con explicación de cada clase), árbol de búsqueda, comparación de algoritmos y aprendizaje.

## Terminal

Todos los comandos se ejecutan desde la carpeta `proyecto-horarios`:

```bash
py -m src.main resumen                                     # datos de la instancia
py -m src.main resolver --algoritmo recocido               # resolver con un algoritmo
py -m src.main resolver --algoritmo exhaustiva --arbol 40  # ver el árbol de búsqueda
py -m src.main comparar --datos data/ejemplo_mini.json     # tabla comparativa
py -m src.main diagnosticar --datos data/ejemplo_mediano.json
py -m src.main explicar --clase 1A-MAT-1                   # ¿por qué se asignó así?
py -m src.main flujo                                       # flujo máximo maestro-materia
py -m src.main aprender                                    # simulación del aprendizaje
py -m src.main experimentos                                # tablas y gráficas en resultados/ (~1 min)
py -m unittest discover tests -v                           # 38 pruebas
```

Algoritmos: `exhaustiva`, `exhaustiva-optima`, `bfs`, `mrv`, `mrv-fc`, `flujo-mrv`, `greedy`, `a-estrella`, `colina`, `recocido`.

Instancias (todas con datos ficticios):

| Archivo | Clases | Para qué sirve |
|---|---|---|
| `data/ejemplo_mini.json` | 5 | La búsqueda exhaustiva sí termina; sirve para comprobar el óptimo |
| `data/ejemplo_pequeno.json` | 10 | La exhaustiva ya no termina; A\* y el recocido sí |
| `data/ejemplo_mediano.json` | 62 | Semana completa; la exhaustiva y greedy fallan, MRV no |

## Estructura

```
app.py                     interfaz web (Streamlit)
data/                      instancias de entrada en JSON
src/
  modelos.py               clases: Materia, Maestro, Salon, Bloque, Horario, Instancia
  reglas.py                base de conocimiento: reglas duras R1-R6, suaves S1-S6, costo
  motor_inferencia.py      explicación de decisiones y árbol de decisión de diagnóstico
  arbol_decision.py        árbol de búsqueda y recorridos (preorden, inorden, postorden, BFS)
  busqueda_exhaustiva.py   backtracking DFS y BFS
  busqueda_heuristica.py   MRV, forward checking, greedy, A*, ascenso de colina, recocido simulado
  flujo.py                 Edmonds-Karp para asignar maestros a materias
  ordenamiento.py          merge sort y quicksort propios
  aprendizaje.py           ajuste de pesos con retroalimentación (usuario simulado o real)
  experimentos.py          comparación exhaustiva vs. heurística con tablas y gráficas
  visualizacion.py         horarios en texto, gráficas y dibujo del árbol
  main.py                  terminal
tests/                     pruebas unitarias
docs/                      problema, reporte, guion e imagen del árbol
resultados/                CSV, gráficas PNG y pesos aprendidos
```

Si existe `resultados/pesos_aprendidos.json`, la interfaz arranca con esos pesos. El botón "Restaurar pesos de fábrica" vuelve a los valores iniciales.
