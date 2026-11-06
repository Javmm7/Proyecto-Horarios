# Pasos para el compañero que publica el proyecto y graba el video

Este archivo es para el integrante del equipo que recibe el proyecto y para su asistente (Claude Code u otro). Explica qué está hecho, qué falta y cómo hacerlo.

## Contexto

- El proyecto **ya está terminado y probado**: 38 pruebas pasan y la app web corre en localhost. No hay que cambiar los algoritmos.
- Todos los datos son **ficticios**, incluido el caso de la escuela en `docs/problema.md`. Se hizo así a propósito por privacidad. No hay que agregar datos reales.
- Lo que falta:
  1. Pasarlo al GitHub del compañero, **sin el historial de commits original**.
  2. Grabar el video siguiendo `docs/guion_exposicion.md`.
  3. Agregar la liga del video al README.

> **Nota para el asistente:** guía al usuario paso a paso y verifica cada paso antes de seguir. No modifiques el código en `src/` ni las pruebas, salvo que el usuario lo pida o algo falle. Todo se escribe en español.

## Paso 0. Requisitos

Revisa que estén instalados y, si falta alguno, indica dónde descargarlo:

| Herramienta | Cómo revisar | Descarga |
|---|---|---|
| Git | `git --version` | https://git-scm.com/downloads |
| Python 3.10 o más reciente | `py --version` (Windows) o `python3 --version` (Mac/Linux) | https://www.python.org/downloads (en Windows, marcar "Add Python to PATH") |

En Windows el comando de Python es `py`. Si no existe, prueba `python`. En Mac y Linux es `python3`.

## Paso 1. Quitar el historial original y crear uno propio

El proyecto se clonó de `https://github.com/Javmm7/Proyecto-Horarios`. Para que quede como repositorio propio del compañero, sin los commits anteriores, sigue estos pasos.

1. Revisa a dónde apunta el repositorio con `git remote -v`.
   - Si apunta a `Javmm7/Proyecto-Horarios`, o si `git log` muestra commits de otra persona, hay que borrar la carpeta `.git`.
   - Si ya apunta al GitHub del compañero, sáltate este paso.
2. Desde la carpeta `proyecto-horarios`, borra la carpeta `.git` con el comando de tu terminal:
   - cmd: `rmdir /s /q .git`
   - PowerShell: `Remove-Item -Recurse -Force .git`
   - Mac/Linux: `rm -rf .git`
3. Configura el nombre y el correo, solo si `git config user.name` sale vacío:
   ```
   git config --global user.name "Su Nombre"
   git config --global user.email "su_correo_de_github"
   ```
4. Crea el repositorio nuevo:
   ```
   git init -b main
   git add .
   git commit -m "Sistema experto para asignación de horarios escolares"
   ```

## Paso 2. Subirlo a su GitHub

1. En github.com: **"+" → New repository**.
   - Nombre: `proyecto-horarios`.
   - **No** marques README, .gitignore ni license; el repositorio debe quedar vacío.
   - Si lo hace privado, debe agregar al profesor en Settings → Collaborators.
2. Corre esto, cambiando `SU_USUARIO` por su usuario de GitHub:
   ```
   git remote add origin https://github.com/SU_USUARIO/proyecto-horarios.git
   git push -u origin main
   ```
   La primera vez se abre el navegador para iniciar sesión.

Errores comunes:
- **"not a git repository":** la terminal no está dentro de `proyecto-horarios`. Corre `cd proyecto-horarios`.
- **"remote origin already exists":** corre `git remote set-url origin https://github.com/SU_USUARIO/proyecto-horarios.git`.
- **"rejected" o "fetch first":** el repositorio de GitHub no estaba vacío. Lo más fácil es borrarlo y crearlo de nuevo sin README.

## Paso 3. Instalar y probar

Desde `proyecto-horarios`:

```
py -m pip install -r requirements.txt
py -m unittest discover tests
py -m streamlit run app.py
```

- La segunda línea corre las pruebas: deben ser **38 y terminar en OK**.
- La tercera abre la app en http://localhost:8501. Para detenerla, presiona Ctrl + C en la terminal.

Pruebas rápidas por terminal (opcional):
```
py -m src.main comparar --datos data/ejemplo_mini.json
py -m src.main explicar --clase 1A-MAT-1
```

## Paso 4. Grabar el video (5 a 7 minutos)

El guion completo, con las frases a decir, está en `docs/guion_exposicion.md`, en la sección "Guion del video". Resumen:

| Tiempo | Qué mostrar en la app |
|---|---|
| 0:00 | Introducción: qué hace el sistema |
| 0:30 | Pestaña 1, problema y reglas: datos, reglas duras R1–R6 y suaves S1–S6 |
| 1:30 | Pestaña 2, diagnóstico y flujo: árbol de decisión y flujo máximo |
| 2:15 | Pestaña 3, resolver: generar un horario y explicar por qué una clase quedó ahí |
| 3:45 | Pestaña 4, árbol: ejemplo mini, dibujar el árbol y explicar los recorridos |
| 4:30 | Pestaña 5, comparar: ejemplo mediano (tarda unos 30 s; se puede pausar o cortar) |
| 5:30 | Pestaña 6, aprendizaje: simular 40 rondas y elegir 2 o 3 pares a mano |

Consejos:
- **Para grabar:** en Windows sirve la barra de Xbox (Win + G) u OBS (https://obsproject.com). En Mac, Cmd + Shift + 5.
- **Antes de grabar:** recorre cada pestaña una vez para comprobar que todo responde.
- **Datos ficticios:** si alguien pregunta, los datos de la escuela son un caso ilustrativo ficticio, por privacidad.
- **Preguntas del profesor:** al final de `docs/guion_exposicion.md` vienen las preguntas probables con su respuesta.
- **Resultados clave:** están en `docs/reporte.md`. Por ejemplo, en el ejemplo mini A* llega al óptimo con 31 nodos y la exhaustiva necesita 4 054. En el mediano la exhaustiva no encuentra solución y el recocido baja el costo de 84 a 28.

## Paso 5. Agregar la liga del video

1. Sube el video a YouTube (puede ser "No listado") o a Google Drive con acceso por enlace.
2. En `README.md`, debajo del primer párrafo, agrega:
   ```
   **Video de demostración:** <liga del video>
   ```
3. En `CLAUDE.md`, marca el paso 15 como terminado (`[x]`).
4. Sube los cambios:
   ```
   git add .
   git commit -m "Liga del video"
   git push
   ```

## Lista final

- [ ] El repositorio está en el GitHub del compañero, con su commit.
- [ ] Las 38 pruebas pasan en su computadora.
- [ ] La app abre en http://localhost:8501.
- [ ] El video está grabado y subido.
- [ ] La liga del video está en el README y subida a GitHub.
