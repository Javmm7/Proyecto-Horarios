# CLAUDE.md — Sistema Experto para Asignación de Horarios Escolares

> Este archivo da contexto a Claude (Claude Code o chat) para continuar el proyecto sin perder el hilo. Léelo completo antes de escribir código.

## 1. Contexto del proyecto

Proyecto final de un curso de **Inteligencia Artificial / Sistemas Expertos**. Idioma de trabajo: **español** (código en inglés o español, pero comentarios, documentación y explicaciones en español).

**Requisitos de la tarea (textual, resumido):**
- Diseñar un **sistema experto** definiendo un problema detectado.
- Elaborar el **árbol de decisión** del sistema.
- Programa de **búsqueda exhaustiva o heurística** que optimice la toma de decisiones.
- Aplicar algoritmos de: búsqueda **exhaustiva y heurística**, **recorridos de árbol**, **ordenamiento** y **teoremas de flujo**.
- Incluir: análisis de estados / árbol de decisión, soluciones a presentarse, reglas o condiciones del problema, **optimización de la búsqueda** y **simulación del proceso de aprendizaje**.
- Exposición oral para retroalimentación sobre el diseño y las técnicas.
- **Entregables:** código anexo + liga de video (ejecución y explicación).

## 2. Problema elegido

**Asignación automática de horarios de clases** en una escuela/facultad.

**Problema detectado (redactar con datos reales de la escuela):** la creación manual de horarios genera traslapes de maestros, salones saturados, huecos excesivos para los alumnos y mucho tiempo invertido por coordinación. Se busca un sistema que genere horarios válidos y de buena calidad de forma automática, explicando sus decisiones.

### Entradas
- Lista de **materias/grupos** (horas por semana, tipo: teoría/laboratorio).
- Lista de **maestros** (materias que pueden impartir, disponibilidad horaria, máximo de horas).
- Lista de **salones** (capacidad, tipo: aula/laboratorio).
- **Bloques horarios** (ej. lunes a viernes, 7:00–15:00 en bloques de 1 h).

### Restricciones duras (reglas obligatorias)
1. Un maestro no puede estar en dos grupos al mismo tiempo.
2. Un salón no puede tener dos clases al mismo tiempo.
3. Un grupo no puede tener dos materias al mismo tiempo.
4. El salón debe tener capacidad suficiente y ser del tipo adecuado (laboratorio para prácticas).
5. Respetar la disponibilidad del maestro.
6. No exceder el máximo de horas diarias/semanales del maestro.

### Restricciones suaves (optimización)
- Minimizar **huecos** en el horario de cada grupo.
- Evitar clases muy tempranas o muy tarde cuando sea posible.
- Distribuir las horas de una materia en días distintos.
- Balancear la carga de los maestros.
- Preferencias de maestros (horarios favoritos).

**Función objetivo:** minimizar `costo = w1·huecos + w2·horarios_malos + w3·desbalance + w4·preferencias_incumplidas`.

## 3. Arquitectura y mapeo a la rúbrica

| Requisito de la rúbrica | Cómo se cubre en el proyecto |
|---|---|
| Sistema experto | Base de conocimiento con reglas SI–ENTONCES (restricciones y recomendaciones) + motor de inferencia + módulo de explicación ("¿por qué se asignó X aquí?") |
| Árbol de decisión | Árbol de estados de la asignación (cada nivel = una clase por asignar, cada rama = una opción de bloque/salón/maestro). Además, un árbol de decisión de reglas para el diagnóstico de conflictos |
| Búsqueda exhaustiva | **Backtracking** puro (DFS) sobre el árbol de estados; también BFS en instancias pequeñas para comparar |
| Búsqueda heurística | Backtracking con **MRV** (variable más restringida) + forward checking; **greedy**; **A\*** con heurística de costo; **hill climbing / simulated annealing** para mejorar horarios |
| Recorridos de árbol | DFS, BFS y recorrido en orden/preorden del árbol de decisión; visualización del recorrido |
| Ordenamiento | Ordenar clases por dificultad/restricción (MRV), ordenar candidatos por costo (merge sort / quicksort implementado a mano) |
| Teoremas de flujo | **Flujo máximo (Ford-Fulkerson / Edmonds-Karp)** para asignar maestros a materias respetando capacidades; **flujo de costo mínimo** opcional para preferencias |
| Optimización de la búsqueda | Poda, forward checking, orden de variables/valores, comparación de nodos explorados y tiempo |
| Simulación del aprendizaje | El sistema ajusta los **pesos (w1..w4)** o prioriza reglas a partir de retroalimentación (horarios aceptados/rechazados por el usuario) y/o mejora entre iteraciones de simulated annealing; graficar la mejora del costo por iteración |

## 4. Estructura de carpetas sugerida

```
proyecto-horarios/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── data/
│   ├── ejemplo_pequeno.json      # 3-4 grupos, para probar exhaustiva
│   ├── ejemplo_mediano.json
│   └── ejemplo_real.json         # datos de la escuela real
├── src/
│   ├── modelos.py                # clases: Materia, Maestro, Salon, Bloque, Horario
│   ├── reglas.py                 # base de conocimiento (restricciones duras/suaves)
│   ├── motor_inferencia.py       # evaluación de reglas + explicaciones
│   ├── arbol_decision.py         # construcción y recorridos (DFS, BFS)
│   ├── busqueda_exhaustiva.py    # backtracking puro
│   ├── busqueda_heuristica.py    # MRV, greedy, A*, simulated annealing
│   ├── flujo.py                  # Edmonds-Karp para asignar maestros
│   ├── ordenamiento.py           # merge sort / quicksort propios
│   ├── aprendizaje.py            # ajuste de pesos con retroalimentación
│   ├── visualizacion.py          # árbol, horario en tabla, gráficas
│   └── main.py                   # CLI / punto de entrada
├── tests/
├── docs/
│   ├── arbol_decision.png
│   └── reporte.md
└── resultados/                   # tablas y gráficas comparativas
```

## 5. Stack y convenciones

- **Lenguaje:** Python 3.10+ (confirmar con el equipo; si cambian, actualizar este archivo).
- **Librerías permitidas:** estándar de Python, `matplotlib`, `networkx` (solo para visualizar, los algoritmos de flujo y búsqueda deben **implementarse a mano** para demostrar dominio), `pandas` opcional, `streamlit` o `tkinter` opcional para interfaz.
- Estilo: PEP 8, funciones cortas, docstrings en español, type hints.
- Cada algoritmo debe ser **medible**: devolver solución, costo, nodos explorados y tiempo.
- No usar librerías de scheduling listas (OR-Tools, etc.) como solución principal; pueden servir solo como referencia para validar resultados.
- Datos de ejemplo en JSON; nunca incluir datos personales reales de maestros o alumnos (usar nombres ficticios).

## 6. Plan de trabajo (marcar al avanzar)

- [x] 1. Redactar el problema detectado con datos reales de la escuela
- [x] 2. Definir modelos de datos y cargar `ejemplo_pequeno.json`
- [x] 3. Implementar base de conocimiento (restricciones duras y suaves)
- [x] 4. Implementar backtracking exhaustivo + contador de nodos
- [x] 5. Dibujar y documentar el árbol de decisión
- [x] 6. Implementar recorridos DFS/BFS sobre el árbol
- [x] 7. Implementar ordenamiento propio y MRV
- [x] 8. Implementar heurísticas (greedy, forward checking, A\*, simulated annealing)
- [x] 9. Implementar flujo máximo para asignación maestro–materia
- [x] 10. Módulo de explicación del sistema experto
- [x] 11. Módulo de aprendizaje (ajuste de pesos con retroalimentación)
- [x] 12. Experimentos: exhaustiva vs. heurística (tiempo, nodos, costo) con tablas y gráficas
- [x] 13. Interfaz simple (CLI o Streamlit) y visualización del horario
- [~] 14. Reporte final, presentación oral y **video de ejecución y explicación**
- [ ] 15. Anexar código y liga del video

> **Estado actual (2026-11-06):** Pasos 1-13 terminados; 37 pruebas pasan. Paso 14: reporte (docs/reporte.md) y guion de exposición/video (docs/guion_exposicion.md) listos; falta grabar el video y agregar datos reales de la escuela en docs/problema.md. Paso 15: falta subir a GitHub y anexar la liga del video. Python 3.14 (`py`), interfaz Streamlit (`py -m streamlit run app.py`). networkx no se usa (el árbol se dibuja con matplotlib).

## 7. Cómo quiero que trabaje Claude

- **Explica antes de codificar:** primero un resumen breve de qué hará el módulo y por qué, después el código. El equipo debe poder **explicar cada línea en la exposición**.
- Avanza **un paso del plan a la vez** y pide confirmación antes de pasar al siguiente.
- Prefiere código claro sobre código "ingenioso".
- Al terminar cada módulo: genera pruebas mínimas y un ejemplo de ejecución.
- Si una decisión de diseño tiene alternativas (por ejemplo, A\* vs. simulated annealing), presenta pros y contras en pocas líneas y recomienda una.
- Ayuda también con el **material de exposición**: guion, diapositivas, preguntas probables del profesor y guion del video.
- Si algo en este archivo es ambiguo o falta información (datos reales, lenguaje, límites de tiempo), **pregunta** en lugar de suponer.

## 8. Criterios de calidad / qué verá el profesor

- El problema está **justificado** con un caso real.
- Se ven claramente las **reglas**, el **árbol de decisión** y los **estados**.
- Hay **comparación cuantitativa** entre búsqueda exhaustiva y heurística.
- Se demuestra la **optimización** (poda, heurísticas, menos nodos explorados).
- Hay evidencia de **aprendizaje** (los resultados mejoran con retroalimentación o iteraciones).
- El código corre, está comentado y se entrega con video.
