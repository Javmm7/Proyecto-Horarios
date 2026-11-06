"""Interfaz web del sistema experto (Paso 13).

Ejecutar desde la carpeta proyecto-horarios:
    py -m streamlit run app.py
Se abre en http://localhost:8501
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import pandas as pd
import streamlit as st

from src import busqueda_exhaustiva as ex
from src import busqueda_heuristica as he
from src.aprendizaje import Aprendiz, NOMBRES_RASGOS, cargar_pesos, generar_candidatos, guardar_pesos, rasgos, simular_aprendizaje
from src.flujo import asignar_maestros
from src.modelos import Instancia, cargar_instancia, instancia_desde_dict
from src.motor_inferencia import arbol_diagnostico_dot, diagnosticar, explicar
from src.reglas import REGLAS_DURAS, Pesos, validar_horario
from src.visualizacion import dibujar_arbol, grafica_aprendizaje, grafica_comparacion, grafica_costo, horario_matriz

st.set_page_config(page_title="Sistema experto de horarios", layout="wide")

ALGORITMOS = [
    "Exhaustiva DFS (1a solución)",
    "Exhaustiva DFS (óptimo)",
    "Exhaustiva BFS (óptimo)",
    "MRV estático",
    "MRV + forward checking",
    "Flujo máximo + MRV + forward checking",
    "Greedy",
    "A* (haz)",
    "Ascenso de colina",
    "Recocido simulado",
]


def correr(nombre: str, inst: Instancia, pesos: Pesos, arbol: int = 0):
    """Ejecuta un algoritmo con límites de nodos según el tamaño de la instancia."""
    chica = len(inst.generar_clases()) <= 10
    limite = 100_000 if chica else 3_000
    opciones = {
        "Exhaustiva DFS (1a solución)": lambda: ex.backtracking(inst, pesos, max_nodos=limite, arbol_limite=arbol),
        "Exhaustiva DFS (óptimo)": lambda: ex.backtracking(inst, pesos, True, max_nodos=limite, arbol_limite=arbol),
        "Exhaustiva BFS (óptimo)": lambda: ex.bfs(inst, pesos, max_nodos=200_000 if chica else 20_000),
        "MRV estático": lambda: he.backtracking_mrv(inst, pesos, forward_checking=False, arbol_limite=arbol),
        "MRV + forward checking": lambda: he.backtracking_mrv(inst, pesos, arbol_limite=arbol),
        "Flujo máximo + MRV + forward checking": lambda: he.backtracking_mrv(inst, pesos, usar_flujo=True, arbol_limite=arbol),
        "Greedy": lambda: he.greedy(inst, pesos),
        "A* (haz)": lambda: he.a_estrella(inst, pesos, max_nodos=5_000 if chica else 200),
        "Ascenso de colina": lambda: he.ascenso_colina(inst, pesos),
        "Recocido simulado": lambda: he.recocido_simulado(inst, pesos),
    }
    return opciones[nombre]()


def color_materia(texto: str) -> str:
    if not texto:
        return ""
    tono = int(hashlib.md5(texto.split(" | ")[0].encode()).hexdigest(), 16) % 360
    return f"background-color: hsl({tono}, 65%, 85%); color: #222"


def tabla_horario(inst: Instancia, horario, grupo_id: str):
    df = pd.DataFrame(horario_matriz(inst, horario, grupo_id), columns=inst.dias,
                      index=[f"{h}:00" for h in inst.horas])
    return df.style.map(color_materia)


def mostrar_horario(inst: Instancia, horario, clave: str) -> None:
    grupos = list(inst.grupos)
    columnas = st.columns(min(3, len(grupos)))
    for i, grupo_id in enumerate(grupos):
        with columnas[i % len(columnas)]:
            st.markdown(f"**Grupo {grupo_id}** ({inst.grupos[grupo_id].alumnos} alumnos)")
            st.dataframe(tabla_horario(inst, horario, grupo_id), key=f"{clave}-{grupo_id}")


def aplicar_pesos(vector: list[float]) -> None:
    """Callback: copia pesos a los controles de la barra lateral."""
    for i, valor in enumerate(vector, start=1):
        st.session_state[f"w{i}"] = float(round(valor, 2))


# ---------------------------------------------------------------------------
# Barra lateral: datos y pesos
# ---------------------------------------------------------------------------

st.sidebar.title("Datos y pesos")
archivos = sorted(Path("data").glob("*.json"))
elegido = st.sidebar.selectbox("Instancia", archivos, format_func=lambda p: p.stem,
                               index=next((i for i, p in enumerate(archivos) if p.stem == "ejemplo_pequeno"), 0))
subido = st.sidebar.file_uploader("...o sube tu propio JSON", type="json")
try:
    inst = instancia_desde_dict(json.load(subido)) if subido else cargar_instancia(elegido)
except (ValueError, KeyError) as error:
    st.error(f"Los datos tienen un problema: {error}")
    st.stop()

st.sidebar.markdown("**Pesos de la función objetivo**")
guardados = cargar_pesos()
for i, (nombre, valor) in enumerate(zip(NOMBRES_RASGOS, [guardados.w1, guardados.w2, guardados.w3, guardados.w4]), 1):
    st.session_state.setdefault(f"w{i}", float(valor))
    st.sidebar.slider(f"w{i} · {nombre}", 0.0, 6.0, step=0.05, key=f"w{i}")
pesos = Pesos(st.session_state.w1, st.session_state.w2, st.session_state.w3, st.session_state.w4)
st.sidebar.button("Restaurar pesos de fábrica", on_click=aplicar_pesos, args=([3.0, 1.0, 0.5, 1.0],))
st.sidebar.caption("costo = w1·huecos + w2·horarios_malos + w3·desbalance + w4·preferencias")

st.title("Sistema experto para asignación de horarios escolares")
st.caption(inst.resumen().replace("\n", " · "))

tabs = st.tabs(["1. Problema y reglas", "2. Diagnóstico y flujo", "3. Resolver", "4. Árbol de búsqueda",
                "5. Comparar algoritmos", "6. Aprendizaje"])

# ---------------------------------------------------------------------------
# 1. Problema y reglas
# ---------------------------------------------------------------------------
with tabs[0]:
    st.subheader("Base de conocimiento")
    izq, der = st.columns(2)
    with izq:
        st.markdown("**Reglas duras** (SI se violan ENTONCES se rechaza la asignación)")
        st.table(pd.DataFrame([(c, d) for c, d, _ in REGLAS_DURAS], columns=["Regla", "Descripción"]))
    with der:
        st.markdown("**Reglas suaves** (suman costo)")
        st.table(pd.DataFrame([
            ("S1", "Huecos en el horario del grupo", "w1"),
            ("S2", "Primera o última hora del día", "w2"),
            ("S3", "Misma materia dos veces el mismo día", "w2"),
            ("S4", "Desbalance de carga entre maestros", "w3"),
            ("S5", "Fuera del horario preferido del maestro", "w4"),
            ("S6", "Varios maestros para la misma materia y grupo", "w4"),
        ], columns=["Regla", "Descripción", "Peso"]))

    st.subheader("Datos de entrada")
    c1, c2 = st.columns(2)
    c1.markdown("**Materias**")
    c1.dataframe(pd.DataFrame([vars(m) for m in inst.materias.values()]), hide_index=True)
    c1.markdown("**Grupos**")
    c1.dataframe(pd.DataFrame([{"id": g.id, "alumnos": g.alumnos, "materias": ", ".join(g.materias)}
                               for g in inst.grupos.values()]), hide_index=True)
    c2.markdown("**Maestros**")
    c2.dataframe(pd.DataFrame([{
        "id": p.id, "nombre": p.nombre, "materias": ", ".join(sorted(p.materias)),
        "bloques disponibles": len(p.disponibilidad), "máx día": p.max_horas_dia,
        "máx semana": p.max_horas_semana, "preferencias": len(p.preferencias),
    } for p in inst.maestros.values()]), hide_index=True)
    c2.markdown("**Salones**")
    c2.dataframe(pd.DataFrame([vars(s) for s in inst.salones.values()]), hide_index=True)

# ---------------------------------------------------------------------------
# 2. Diagnóstico y flujo
# ---------------------------------------------------------------------------
with tabs[1]:
    st.subheader("Árbol de decisión de diagnóstico")
    st.write("Antes de buscar, el sistema revisa con un árbol de decisión si el problema puede tener solución.")
    d = diagnosticar(inst)
    for paso in d.camino:
        st.write(("✅ " if "-> SÍ" in paso else "❌ ") + paso)
    (st.success if d.factible else st.error)(d.conclusion)
    st.graphviz_chart(arbol_diagnostico_dot())

    st.subheader("Flujo máximo (Edmonds-Karp): ¿qué maestro da cada materia?")
    a = asignar_maestros(inst)
    st.metric("Horas cubiertas", f"{a.flujo_maximo} de {a.demanda}")
    st.dataframe(pd.DataFrame([{"grupo": g, "materia": m, "reparto (maestro: horas)": str(r)}
                               for (g, m), r in a.reparto.items()]), hide_index=True)
    for f in a.faltantes:
        st.warning(f)
    with st.expander(f"Caminos aumentantes ({len(a.caminos)})"):
        for camino, cuello in a.caminos:
            st.text(f"{' -> '.join(camino)}   (+{cuello} h)")

# ---------------------------------------------------------------------------
# 3. Resolver
# ---------------------------------------------------------------------------
with tabs[2]:
    algoritmo = st.selectbox("Algoritmo", ALGORITMOS, index=ALGORITMOS.index("Recocido simulado"))
    if len(inst.generar_clases()) > 10 and algoritmo.startswith(("Exhaustiva", "A*")):
        st.info("En instancias grandes este algoritmo corre con un límite de nodos bajo para no tardar demasiado.")
    if st.button("Generar horario", type="primary"):
        with st.spinner("Buscando..."):
            st.session_state.resultado = (correr(algoritmo, inst, pesos), inst.nombre)

    if "resultado" in st.session_state and st.session_state.resultado[1] == inst.nombre:
        r = st.session_state.resultado[0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Costo", r.costo if r.costo is not None else "-")
        m2.metric("Nodos explorados", r.nodos)
        m3.metric("Verificaciones de reglas", r.verificaciones)
        m4.metric("Tiempo (s)", f"{r.tiempo:.3f}")
        if r.notas:
            st.info(r.notas)
        if r.horario:
            problemas = validar_horario(inst, r.horario)
            if problemas:
                st.error(problemas)
            else:
                st.success("El horario cumple las 6 reglas duras.")
            st.write("Desglose del costo:", r.desglose)
            mostrar_horario(inst, r.horario, "resolver")
            if r.historial:
                st.pyplot(grafica_costo({r.algoritmo: r.historial}))

            st.subheader("¿Por qué se asignó así? (módulo de explicación)")
            clases = [a.clase for a in r.horario.asignaciones]
            clase = st.selectbox("Clase", clases, format_func=lambda c: c.id)
            st.code(explicar(inst, r.horario, clase, pesos), language=None)
        else:
            st.error("No se encontró horario.")

# ---------------------------------------------------------------------------
# 4. Árbol de búsqueda
# ---------------------------------------------------------------------------
with tabs[3]:
    st.write("Cada nivel es una clase asignada; cada rama, una opción (bloque, salón, maestro). "
             "Rojo = podada por una regla dura, verde = horario completo.")
    c1, c2 = st.columns(2)
    tipo_arbol = c1.radio("Algoritmo", ["Exhaustiva DFS (1a solución)", "MRV + forward checking"], horizontal=True)
    limite = c2.slider("Nodos a registrar", 10, 150, 40)
    if st.button("Construir árbol", type="primary"):
        with st.spinner("Buscando y registrando el árbol..."):
            st.session_state.arbol = (correr(tipo_arbol, inst, pesos, arbol=limite).arbol, inst.nombre, tipo_arbol)
    if "arbol" in st.session_state and st.session_state.arbol[1] == inst.nombre:
        arbol, _, titulo = st.session_state.arbol
        st.write("Conteo:", arbol.conteo())
        st.graphviz_chart(arbol.a_dot())
        st.pyplot(dibujar_arbol(arbol, titulo))
        recorrido = st.radio("Recorrido", ["Preorden (DFS)", "Inorden", "Postorden", "Por niveles (BFS)"], horizontal=True)
        funciones = {"Preorden (DFS)": arbol.preorden, "Inorden": arbol.inorden,
                     "Postorden": arbol.postorden, "Por niveles (BFS)": arbol.por_niveles}
        st.text("\n".join(f"{i:>3}. [nivel {n.nivel}] {n.etiqueta} ({n.tipo})"
                          for i, n in enumerate(funciones[recorrido]()[:40], 1)))

# ---------------------------------------------------------------------------
# 5. Comparar
# ---------------------------------------------------------------------------
with tabs[4]:
    elegidos = st.multiselect("Algoritmos a comparar", ALGORITMOS, default=ALGORITMOS)
    if st.button("Comparar", type="primary"):
        resultados = []
        barra = st.progress(0.0)
        for i, nombre in enumerate(elegidos, 1):
            resultados.append(correr(nombre, inst, pesos))
            barra.progress(i / len(elegidos), text=nombre)
        st.session_state.comparacion = (resultados, inst.nombre)
    if "comparacion" in st.session_state and st.session_state.comparacion[1] == inst.nombre:
        resultados = st.session_state.comparacion[0]
        st.dataframe(pd.DataFrame([r.fila() for r in resultados]), hide_index=True)
        for r in resultados:
            if r.notas:
                st.caption(f"**{r.algoritmo}:** {r.notas}")
        st.pyplot(grafica_comparacion(resultados, inst.nombre))
        locales = {r.algoritmo: r.historial for r in resultados if r.historial}
        if locales:
            st.pyplot(grafica_costo(locales))

# ---------------------------------------------------------------------------
# 6. Aprendizaje
# ---------------------------------------------------------------------------
with tabs[5]:
    st.subheader("A) Simulación con un usuario de preferencias ocultas")
    st.write("Un usuario simulado le importan mucho las preferencias y el balance de carga. "
             "El sistema no lo sabe: aprende comparando pares de horarios.")
    if st.button("Simular 40 rondas"):
        with st.spinner("Simulando..."):
            st.session_state.simulacion = simular_aprendizaje(inst)
    if "simulacion" in st.session_state:
        s = st.session_state.simulacion
        c1, c2, c3 = st.columns(3)
        c1.metric("Coincidencia con el usuario", f"{s.concordancia[-1]:.0f}%", f"{s.concordancia[-1] - s.concordancia[0]:+.0f}%")
        c2.metric("Costo para el usuario", s.costo_usuario_despues,
                  f"{s.costo_usuario_despues - s.costo_usuario_antes:+.2f}", delta_color="inverse")
        c3.metric("Correcciones de pesos", s.aprendiz.actualizaciones)
        st.pyplot(grafica_aprendizaje(s.concordancia, s.pesos, s.pesos_ocultos))
        st.button("Usar estos pesos aprendidos", on_click=aplicar_pesos, args=(s.pesos[-1],))

    st.subheader("B) Tú eres el usuario: elige el horario que prefieras")
    if st.button("Generar horarios candidatos"):
        with st.spinner("Generando horarios candidatos..."):
            st.session_state.candidatos = (generar_candidatos(inst, cantidad=8), inst.nombre)
            st.session_state.aprendiz = Aprendiz(pesos=Pesos(pesos.w1, pesos.w2, pesos.w3, pesos.w4), tasa=0.3)
            st.session_state.par = (0, 1)
            st.session_state.mensaje = ""
    candidatos, de = st.session_state.get("candidatos", ([], None))
    if de != inst.nombre or len(candidatos) < 2:
        st.caption("Presiona el botón para generar horarios y compararlos de dos en dos.")
    else:
        aprendiz: Aprendiz = st.session_state.aprendiz
        i, j = st.session_state.par
        ra, rb = rasgos(inst, candidatos[i]), rasgos(inst, candidatos[j])
        grupo = st.selectbox("Grupo a mostrar", list(inst.grupos))
        ca, cb = st.columns(2)
        for col, etiqueta, idx, r in ((ca, "A", i, ra), (cb, "B", j, rb)):
            with col:
                st.markdown(f"**Horario {etiqueta}** · " + ", ".join(f"{n}: {v}" for n, v in zip(NOMBRES_RASGOS, r)))
                st.dataframe(tabla_horario(inst, candidatos[idx], grupo), key=f"par-{etiqueta}")
        st.caption(f"Con los pesos actuales el sistema preferiría el horario {aprendiz.prefiere(ra, rb)}.")

        def elegir(gana: str) -> None:
            aceptado, rechazado = (ra, rb) if gana == "A" else (rb, ra)
            corrigio = aprendiz.retroalimentar(aceptado, rechazado)
            st.session_state.mensaje = "El sistema corrigió sus pesos." if corrigio else "El sistema ya opinaba igual."
            st.session_state.par = tuple(random.sample(range(len(candidatos)), 2))  # siguiente par al azar

        b1, b2, b3 = st.columns(3)
        b1.button("Prefiero A", on_click=elegir, args=("A",))
        b2.button("Prefiero B", on_click=elegir, args=("B",))
        if b3.button("Guardar pesos aprendidos"):
            guardar_pesos(aprendiz.pesos)
            st.success("Guardados en resultados/pesos_aprendidos.json")
        if st.session_state.get("mensaje"):
            st.info(st.session_state.mensaje)
        st.write("Pesos actuales:", dict(zip(["w1", "w2", "w3", "w4"], aprendiz.vector())),
                 f"· correcciones: {aprendiz.actualizaciones}")
        st.button("Aplicar estos pesos a la búsqueda", on_click=aplicar_pesos, args=(aprendiz.vector(),))
