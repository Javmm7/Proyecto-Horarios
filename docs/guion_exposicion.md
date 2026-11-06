# Guion de exposición y video

## Antes de empezar

1. Abrir una terminal en VS Code dentro de `proyecto-horarios`.
2. `py -m streamlit run app.py` → se abre en http://localhost:8501
3. Tener abiertas `resultados/comparacion_mediano.png` y `resultados/aprendizaje.png` por si algo falla en vivo.

---

## Exposición (~10 minutos, 8 diapositivas)

| # | Diapositiva | Qué decir (idea central) | Qué mostrar |
|---|---|---|---|
| 1 | **Problema** | "Hacer los horarios a mano tarda días y genera traslapes, salones saturados y huecos para los alumnos." | Caso ilustrativo de `docs/problema.md` (3 semanas en Excel, choque en laboratorio) |
| 2 | **Por qué es difícil** | "Incluso con 10 clases hay 2.5 × 10¹⁴ combinaciones. No se pueden revisar todas." | La fórmula de `problema.md` |
| 3 | **Sistema experto** | Base de hechos, base de conocimiento (R1–R6, S1–S6), motor de inferencia, explicación y aprendizaje | Tabla de arquitectura del reporte; pestaña 1 de la app |
| 4 | **Árbol de decisión** | "Cada nivel es una clase; cada rama, una opción. Lo rojo se poda por una regla." Mencionar los 4 recorridos | `docs/arbol_decision.png`; pestaña 4 de la app |
| 5 | **Exhaustiva vs. heurística** | "En la instancia mini, A\* llega al mismo óptimo con 31 nodos en lugar de 4 054. En la mediana, la exhaustiva no encuentra solución y MRV sí, en 62 nodos." | `comparacion_mini.png`, `comparacion_mediano.png` |
| 6 | **Flujo máximo** | "Antes de buscar, Edmonds-Karp revisa si hay horas de maestro suficientes. Si el flujo máximo es menor que la demanda, no existe ningún horario." | Pestaña 2 de la app |
| 7 | **Aprendizaje** | "El sistema no sabe qué te importa más. Te muestra dos horarios, eliges uno y ajusta sus pesos. La coincidencia sube del 82 % al 91 %." | `aprendizaje.png` |
| 8 | **Conclusiones** | La heurística hace viable el problema; el recocido mejora la calidad; el sistema explica y aprende. Limitaciones | Sección 6 del reporte |

---

## Guion del video (~5–7 minutos)

**0:00 – Introducción (30 s).** "Somos [equipo]. Hicimos un sistema experto que genera horarios escolares automáticamente, explica sus decisiones y aprende de las preferencias del usuario."

**0:30 – Problema y reglas (1 min).** Pestaña 1. Mostrar los datos ficticios (grupos, maestros con disponibilidad, salones y laboratorios). Leer 2 o 3 reglas duras y explicar que las suaves suman costo.

**1:30 – Diagnóstico (45 s).** Pestaña 2. "Antes de buscar, el árbol de decisión hace cinco preguntas. La última usa flujo máximo: aquí cubre 10 de 10 horas, así que el problema puede tener solución." Abrir los caminos aumentantes.

**2:15 – Resolver (1 min 30 s).** Pestaña 3.
- Elegir "Exhaustiva DFS (1a solución)" → Generar → costo alto.
- Cambiar a "Recocido simulado" → Generar → costo más bajo y la gráfica de mejora.
- Bajar a "¿Por qué se asignó así?", elegir una clase y leer la explicación: reglas que cumple y alternativas descartadas por regla.

**3:45 – Árbol (45 s).** Pestaña 4. "Exhaustiva DFS" con 40 nodos → Construir árbol. "Las ramas rojas se podaron; cada una dice qué regla rompió." Cambiar el recorrido entre preorden y BFS.

**4:30 – Comparación (1 min).** Barra lateral → `ejemplo_mediano`. Pestaña 5 → Comparar (tarda unos 30 s; se puede pausar el video). "Las barras rojas son algoritmos que no encontraron solución: la exhaustiva y greedy. MRV la encuentra en 62 nodos y el recocido baja el costo de 84 a 28."

**5:30 – Aprendizaje (1 min).** Volver a `ejemplo_pequeno`. Pestaña 6 → Simular 40 rondas → explicar las dos gráficas. Después, en la parte B, elegir 2 o 3 pares a mano y mostrar cómo cambian los pesos.

**6:30 – Cierre (20 s).** "Gracias. El código, las pruebas y el reporte están en el repositorio [liga]."

Tip: grabar con OBS o con la Barra de juego de Windows (Win + G), en pantalla completa y con zoom del navegador al 90 %.

---

## Preguntas probables del profesor

**¿Qué hace que esto sea un sistema experto y no solo un programa de búsqueda?**
Tiene una base de conocimiento explícita (reglas SI–ENTONCES en `reglas.py`), un motor de inferencia que las aplica, un módulo de explicación (`explicar()`) que justifica cada decisión, y aprende de la retroalimentación.

**¿Cuál es la diferencia entre búsqueda exhaustiva y heurística en su código?**
La exhaustiva prueba todas las combinaciones en orden fijo. La heurística usa conocimiento del problema para decidir el orden (MRV: primero la clase más difícil), para descartar opciones antes de intentarlas (forward checking, dominio estático) y para estimar cuánto falta (la h de A\*).

**¿Por qué la h de A\* es admisible?**
Para cada clase pendiente suma la penalización mínima entre sus opciones válidas en este momento. Conforme se asignan clases, las opciones solo disminuyen y las penalizaciones solo aumentan, así que la estimación nunca supera al costo real.

**¿Entonces por qué usan un haz en A\*?**
Porque la h es demasiado optimista y hay miles de estados con el mismo f. El haz limita la memoria a cambio de perder la garantía de óptimo, y el programa lo avisa. En la instancia mini, A\* puro sí da el óptimo.

**¿Cómo usan el teorema de flujo máximo?**
Se arma una red FUENTE → (grupo, materia) → maestro → SUMIDERO con las horas como capacidades. Si el flujo máximo es menor que el total de horas, por el teorema de flujo máximo y corte mínimo no existe ningún horario. Además, el flujo reparte las materias entre maestros, y eso reduce el árbol de búsqueda.

**¿Qué complejidad tiene Edmonds-Karp?**
O(V·E²). Usa BFS para encontrar siempre el camino aumentante más corto.

**¿Por qué el recocido simulado acepta soluciones peores?**
Para salir de mínimos locales. En la instancia mini, el ascenso de colina se atora en 4.5 y el recocido llega al óptimo, 3.5.

**¿Dónde está el aprendizaje? ¿No es solo un ajuste de parámetros?**
Es aprendizaje supervisado con comparaciones por pares (preference learning) y una regla tipo perceptrón. La evidencia es que la coincidencia con el usuario sube y que los horarios generados con los pesos aprendidos le cuestan menos al usuario.

**¿Por qué forward checking hace más verificaciones que MRV estático?**
Porque revisa en cada paso todas las clases pendientes. Conviene cuando el problema obliga a regresar muchas veces; en estas instancias casi no hace falta regresar. Es un costo fijo que paga para detectar callejones sin salida antes.

**¿Qué pasa si no hay solución?**
El árbol de diagnóstico dice la causa antes de buscar: grupo con demasiadas horas, sin salón adecuado, faltan laboratorios, materia sin maestro o faltan horas de maestro (flujo).

**¿Por qué implementaron los algoritmos a mano?**
Era requisito demostrar dominio de los algoritmos. Solo se usan matplotlib y Streamlit para gráficas e interfaz.
