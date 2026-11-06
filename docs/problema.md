# Paso 1 — Definición formal del problema

## 1. Problema detectado

En muchas escuelas, los horarios de clase los arma a mano la coordinación académica, normalmente en una hoja de cálculo. Este proceso:

- **Tarda mucho:** la coordinación dedica varios días por semestre a armar y corregir el horario.
- **Genera conflictos:** un maestro queda en dos grupos a la misma hora, se reserva el mismo salón dos veces o una práctica queda en un aula sin equipo.
- **Da horarios de mala calidad:** los alumnos tienen huecos largos entre clases, una materia queda acumulada en un solo día y la carga de los maestros queda desbalanceada.
- **No se explica:** cuando alguien pregunta por qué una clase quedó en cierto lugar, no hay una justificación clara.

### Caso ilustrativo

> Por privacidad no usamos datos de una escuela real. El siguiente caso es **ficticio**, pero refleja una situación típica de una preparatoria o facultad mediana.

La *Preparatoria Técnica Valle Norte* (nombre inventado) tiene:

- **18 grupos** repartidos en 3 semestres, **42 maestros** (la mitad de asignatura, con disponibilidad limitada) y **24 salones**, de los cuales 4 son laboratorios de cómputo.
- Unas **620 clases de 1 hora por semana** que hay que acomodar en 5 días × 7 bloques.
- La coordinación tarda **unas 3 semanas** cada semestre en armar el horario en Excel, y en las dos primeras semanas de clases se hacen **alrededor de 15 correcciones**.
- **Ejemplo de conflicto:** el lunes a las 10:00 dos grupos de 3.er semestre quedaron asignados al mismo laboratorio de cómputo. Uno de ellos tuvo que dar la práctica en un aula sin computadoras y se perdió la sesión (violación de las reglas R2 y R4).
- **Ejemplo de mala calidad:** un grupo tenía clase de 7:00 a 8:00 y la siguiente hasta las 12:00, con 3 horas libres en medio (regla suave S1).

Con esos números el espacio de búsqueda es enorme. Por eso el proyecto prueba los algoritmos en tres tamaños: mini (5 clases), pequeño (10) y mediano (62, una semana completa de 6 grupos).

## 2. Objetivo del sistema experto

Generar automáticamente un horario semanal que:

1. **Cumpla todas las reglas obligatorias** (restricciones duras).
2. **Sea lo mejor posible** según los criterios de calidad (restricciones suaves).
3. **Explique sus decisiones** (por ejemplo, "¿por qué Matemáticas del 1A quedó el lunes a las 8?").
4. **Aprenda** de la retroalimentación del usuario (horarios aceptados o rechazados).

## 3. Entradas y salidas

| Entradas | Salida |
|---|---|
| Materias (horas por semana, tipo teoría/laboratorio) | Horario: para cada clase, un **bloque**, un **salón** y un **maestro** |
| Grupos (número de alumnos, materias que cursan) | Costo del horario y desglose de penalizaciones |
| Maestros (materias que imparten, disponibilidad, máximo de horas por día y por semana, preferencias) | Explicación de las decisiones |
| Salones (capacidad, tipo aula/laboratorio) | Métricas: nodos explorados y tiempo |
| Bloques horarios (días × horas) | |

## 4. Formulación como problema de búsqueda

| Elemento | Definición en este proyecto |
|---|---|
| **Variables** | Cada *clase* = una sesión de 1 hora de una materia para un grupo. Ejemplo: `1A-MAT-1`, `1A-MAT-2` |
| **Dominio de cada variable** | Todas las ternas (bloque, salón, maestro) posibles |
| **Estado** | Un horario parcial: la lista de clases ya asignadas |
| **Estado inicial** | Horario vacío (ninguna clase asignada) |
| **Operador / acción** | Asignar a la siguiente clase pendiente una terna (bloque, salón, maestro) que no viole ninguna regla dura |
| **Prueba de meta** | Todas las clases están asignadas y no se viola ninguna regla dura |
| **Costo** | Función objetivo de las restricciones suaves (sección 6) |

**Árbol de estados:** la raíz es el horario vacío. Cada nivel del árbol corresponde a una clase por asignar, y cada rama corresponde a una opción (bloque, salón, maestro). Una hoja a profundidad *n* (con *n* = número de clases) es un horario completo.

### Tamaño del espacio de búsqueda

En `data/ejemplo_pequeno.json` hay 10 clases y 12 bloques. Si contamos para cada clase solo los salones y maestros compatibles, el número de horarios posibles es:

$$\prod_{c=1}^{10} |\text{bloques}| \times |\text{salones compatibles}_c| \times |\text{maestros capaces}_c| \approx 2.5 \times 10^{14}$$

Ni siquiera el ejemplo pequeño se puede recorrer completo. Por eso se necesitan **poda** (descartar ramas que violan reglas), **ordenamiento de variables (MRV)** y **heurísticas**, y el proyecto compara cuántos nodos explora cada método.

## 5. Base de conocimiento: reglas

### 5.1 Reglas duras (obligatorias)

Si una asignación viola alguna de estas reglas, se poda la rama.

| Regla | SI … | ENTONCES … |
|---|---|---|
| **R1** | el maestro ya tiene una clase en ese bloque | rechazar la asignación |
| **R2** | el salón ya está ocupado en ese bloque | rechazar la asignación |
| **R3** | el grupo ya tiene una clase en ese bloque | rechazar la asignación |
| **R4** | la capacidad del salón es menor al número de alumnos **o** el tipo de salón no corresponde (las prácticas van en laboratorio) | rechazar la asignación |
| **R5** | el maestro no está disponible en ese bloque, **o** no puede impartir esa materia | rechazar la asignación |
| **R6** | el maestro ya alcanzó su máximo de horas del día o de la semana | rechazar la asignación |

### 5.2 Reglas suaves (calidad)

Estas reglas no prohíben nada; solo suman penalización al costo.

| Regla | SI … | ENTONCES … |
|---|---|---|
| **S1** | un grupo tiene una hora libre entre dos clases el mismo día (hueco) | sumar penalización `w1` por cada hueco |
| **S2** | la clase cae en el primer o el último bloque del día | sumar `w2` |
| **S3** | dos sesiones de la misma materia y grupo caen el mismo día | sumar `w2` (se busca repartir en días distintos) |
| **S4** | la carga de los maestros está desbalanceada | sumar `w3 ×` desviación de horas respecto al promedio |
| **S5** | la clase no está en un horario preferido del maestro (si tiene preferencias) | sumar `w4` |
| **S6** | las sesiones de una misma materia y grupo las imparten maestros distintos | sumar `w4` (se prefiere un solo maestro por materia y grupo) |

## 6. Función objetivo

$$\text{costo} = w_1 \cdot \text{huecos} + w_2 \cdot \text{horarios\_malos} + w_3 \cdot \text{desbalance} + w_4 \cdot \text{preferencias\_incumplidas}$$

El sistema busca el horario válido de **costo mínimo**. Los pesos `w1..w4` empiezan con valores fijos, y el módulo de aprendizaje los ajusta según la retroalimentación del usuario.

## 7. Técnicas y su papel en el sistema

| Técnica | Para qué se usa |
|---|---|
| Backtracking (DFS) | Búsqueda exhaustiva sobre el árbol de estados, aplicada a la instancia pequeña |
| BFS | Comparar el recorrido por niveles con DFS (cuántos nodos explora y cuánta memoria usa) |
| MRV + forward checking | Asignar primero la clase con menos opciones y podar antes |
| Greedy, A\*, simulated annealing | Encontrar soluciones buenas rápido y después mejorarlas |
| Merge sort / quicksort propios | Ordenar clases por dificultad y candidatos por costo |
| Flujo máximo (Edmonds-Karp) | Decidir qué maestro da cada materia a cada grupo sin exceder sus horas |
| Aprendizaje | Ajustar los pesos `w1..w4` con la retroalimentación del usuario |

## 8. Soluciones que presenta el sistema

1. **Horario factible:** el primero que cumple todas las reglas duras.
2. **Horario optimizado:** el de menor costo encontrado.
3. **Comparativa:** costo, nodos explorados y tiempo de cada algoritmo.
4. **Diagnóstico:** si no existe solución, qué regla lo impide (por ejemplo, "PRO necesita 4 h de laboratorio y solo hay 3 h de maestro disponibles").
