# 🍴 RecetaMatch

Sistema de recomendación de recetas basado en los datos de [Food.com](https://www.food.com/).  
Desarrollado con **Flask**, **SQLite**, **TailwindCSS** y **DaisyUI**.

🔗 **Demo en vivo:** [https://brendarlq.pythonanywhere.com/](https://brendarlq.pythonanywhere.com/)

---

## 🚀 Descripción

**RecetaMatch** es un sistema interactivo que recomienda recetas a los usuarios según sus valoraciones y preferencias.  
Permite ingresar con un nombre de usuario, puntuar recetas y descubrir nuevas sugerencias basadas en comportamientos similares.

El sistema incluye:

- ✅ Login simple (crea usuario automáticamente si no existe)  
- 🔍 Buscador con autocompletado en tiempo real  
- ⭐ Puntuación de recetas (1 a 5 estrellas)  
- 🍽️ Sección “Quienes vieron esta receta también vieron…”  
- 🔁 Recomendaciones dinámicas según valoraciones previas  

El proyecto combina un backend ligero en Flask con una interfaz moderna basada en **TailwindCSS + DaisyUI**.

---

## 🧠 Tecnologías utilizadas

| Componente | Tecnología |
|-------------|-------------|
| Backend | Python + Flask |
| Base de datos | SQLite |
| Frontend | TailwindCSS + DaisyUI |
| Despliegue | PythonAnywhere |
| Entorno | Conda (Anaconda/Miniconda) |

---

## ⚙️ Instalación local (usando Conda)

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/brendarlq/recetamatch.git
   cd recetamatch

2. Crear el entorno con Conda:
    ```bash
    conda create -n recetamatch python=3.10
    conda activate recetamatch
3. Instalar dependencias:
    ```bash
    pip install -r requirements.txt
4. Ejecutar la aplicación:
   ```bash
    python app.py
5. Abrir en el navegador:
    ```bash
    http://localhost:5000

## Estructura del proyecto

```bash
sr/
├── app.py
├── recomendar.py
├── templates/
│   ├── login.html
│   ├── recomendaciones.html
│   ├── detalle.html
│   ├── _navbar.html
│   └── macros.html
├── requirements.txt
├── .gitignore
└── README.md
```

## Estructura del proyecto

```bash
Autora: Brenda Quiñónez
Dataset: Food.com Recipes and Interactions Dataset (Kaggle)
Despliegue: PythonAnywhere
```