<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 6aac03c (x4)
# PROYECTO DE APRENDIZAJE DE MÁQUINA – UNA PUNO

## 👥 Integrantes del equipo
- **Jhon Aracayo**
- **Juan Diego Canaza**
- **Ximara Aquino**
- **Vanessa Castro**

<<<<<<< HEAD
---

## 📝 Descripción
Este proyecto desarrolla **sistemas de recomendación y análisis de datos** utilizando técnicas de **aprendizaje de máquina**.  
Incluye scripts de procesamiento, modelos de lenguaje, una aplicación principal y una extensión para navegador, orientados a la experimentación y despliegue académico.

---

## 🗂️ Estructura del proyecto
```
📦 app/                         # Código principal de la aplicación
 ├── pipelines/                # Pipelines de procesamiento
 ├── recommendation_engine.py  # Motor de recomendación
 └── database.py               # Conexión y manejo de base de datos

📦 MODELOSIMPLE_minilm-l2/      # Modelado avanzado
 └── scripts/                  # Scripts asociados al modelo

📦 scripts/                    # Scripts de procesamiento de datos
 ├── 01.harvest_multi.py       # Recolección de datos
 ├── 02.preprocessing.py      # Preprocesamiento
 └── 03.clustering.py          # Clustering y análisis

🧩 extension/                  # Extensión para navegador
 ├── manifest.json
 ├── popup.html
 ├── background.js
 └── icons/
```

---

## ⚙️ Instalación

### 1️⃣ Requisitos generales
- Python **3.8+**
- Docker (para PostgreSQL)
- Navegador **Chrome** o **Edge** (para la extensión)

---

### 2️⃣ Instalar dependencias de Python
Si existe `requirements.txt`:
```bash
pip install -r requirements.txt
```

Si no existe:
```bash
pip install psycopg2 pandas scikit-learn hdbscan sentence-transformers flask
```

---

### 3️⃣ Configurar la base de datos
```bash
docker-compose up -d
```

---

### 4️⃣ Instalar la extensión
1. Ir a `chrome://extensions/`
2. Activar **Modo desarrollador**
3. Seleccionar **Cargar extensión sin empaquetar**
4. Cargar la carpeta `extension/`

---

## 🚀 Ejecución de scripts
```bash
python scripts/01.harvest_multi.py
python scripts/02.preprocessing.py
python scripts/03.embedding_generator.py
```

---

## 📝 Notas importantes
- ✅ Verificar que todas las dependencias estén instaladas antes de ejecutar los scripts.
- 📖 Revisar la documentación interna de cada archivo para comprender su funcionamiento.
- 🔄 Mantener la base de datos activa mediante Docker durante la ejecución.

---

## 📬 Contacto
Para dudas o soporte, contactar a cualquiera de los integrantes del equipo.

---

📌 *Proyecto académico – Universidad Nacional del Altiplano (UNA) – Puno*
=======
---
title: Unap Research Ml
emoji: 🐢
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
license: mit
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference
>>>>>>> 0229c24 (initial commit)
=======
---

## 📝 Descripción
Este proyecto desarrolla **sistemas de recomendación y análisis de datos** utilizando técnicas de **aprendizaje de máquina**.  
Incluye scripts de procesamiento, modelos de lenguaje, una aplicación principal y una extensión para navegador, orientados a la experimentación y despliegue académico.

---

## 🗂️ Estructura del proyecto
```
📦 app/                         # Código principal de la aplicación
 ├── pipelines/                # Pipelines de procesamiento
 ├── recommendation_engine.py  # Motor de recomendación
 └── database.py               # Conexión y manejo de base de datos

📦 MODELOSIMPLE_minilm-l2/      # Modelado avanzado
 └── scripts/                  # Scripts asociados al modelo

📦 scripts/                    # Scripts de procesamiento de datos
 ├── 01.harvest_multi.py       # Recolección de datos
 ├── 02.preprocessing.py      # Preprocesamiento
 └── 03.clustering.py          # Clustering y análisis

🧩 extension/                  # Extensión para navegador
 ├── manifest.json
 ├── popup.html
 ├── background.js
 └── icons/
```

---

## ⚙️ Instalación

### 1️⃣ Requisitos generales
- Python **3.8+**
- Docker (para PostgreSQL)
- Navegador **Chrome** o **Edge** (para la extensión)

---

### 2️⃣ Instalar dependencias de Python
Si existe `requirements.txt`:
```bash
pip install -r requirements.txt
```

Si no existe:
```bash
pip install psycopg2 pandas scikit-learn hdbscan sentence-transformers flask
```

---

### 3️⃣ Configurar la base de datos
```bash
docker-compose up -d
```

---

### 4️⃣ Instalar la extensión
1. Ir a `chrome://extensions/`
2. Activar **Modo desarrollador**
3. Seleccionar **Cargar extensión sin empaquetar**
4. Cargar la carpeta `extension/`

---

## 🚀 Ejecución de scripts
```bash
python scripts/01.harvest_multi.py
python scripts/02.preprocessing.py
python scripts/03.embedding_generator.py
```

---

## 📝 Notas importantes
- ✅ Verificar que todas las dependencias estén instaladas antes de ejecutar los scripts.
- 📖 Revisar la documentación interna de cada archivo para comprender su funcionamiento.
- 🔄 Mantener la base de datos activa mediante Docker durante la ejecución.

---

## 📬 Contacto
Para dudas o soporte, contactar a cualquiera de los integrantes del equipo.

---

📌 *Proyecto académico – Universidad Nacional del Altiplano (UNA) – Puno*
>>>>>>> 6aac03c (x4)
