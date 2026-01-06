# GitHub Actions Setup - Automated Repository Updates

Este documento explica cómo configurar GitHub Actions para actualizar automáticamente los repositorios UNAP/UNSA.

## 🎯 Funcionalidad

El workflow automático ejecuta:

1. **Harvest** - Busca nuevos repositorios en UNAP/UNSA
2. **Semantic Indexing** - Actualiza el índice FAISS
3. **Topic Clustering** - Agrupa documentos por temas
4. **Deploy** - Push automático a GitHub y Hugging Face Spaces

## ⚙️ Configuración

### 1. Secretos de GitHub

Ve a: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

Crea estos secretos:

- **`DATABASE_URL`**: URL de conexión PostgreSQL
  ```
  postgresql://usuario:password@host:puerto/database
  ```

- **`HF_TOKEN`**: Token de Hugging Face
  - Ve a: https://huggingface.co/settings/tokens
  - Crea un token con permisos de `write`

### 2. Estructura de Base de Datos

El workflow requiere estas tablas en PostgreSQL:

```sql
-- Tabla principal de items
CREATE TABLE items (
    uuid VARCHAR(255) PRIMARY KEY,
    handle VARCHAR(255),
    title TEXT,
    title_norm TEXT,
    abstract TEXT,
    abstract_norm TEXT,
    authors JSONB,
    subjects JSONB,
    date_issued VARCHAR(50),
    url TEXT,
    university VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de clusters
CREATE TABLE clusters (
    uuid VARCHAR(255),
    model_name VARCHAR(100),
    cluster_id INTEGER,
    PRIMARY KEY (uuid, model_name),
    FOREIGN KEY (uuid) REFERENCES items(uuid) ON DELETE CASCADE
);

-- Tabla de etiquetas de clusters
CREATE TABLE cluster_labels (
    model_name VARCHAR(100),
    cluster_id INTEGER,
    label TEXT,
    PRIMARY KEY (model_name, cluster_id)
);

-- Índices para mejor rendimiento
CREATE INDEX idx_items_university ON items(university);
CREATE INDEX idx_items_date ON items(date_issued);
CREATE INDEX idx_clusters_model ON clusters(model_name);
```

### 3. Dependencias Python

El archivo `requirements.txt` debe incluir:

```txt
# Ya existentes
fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg2-binary==2.9.9
sentence-transformers==2.2.2
huggingface-hub==0.16.4
numpy==1.24.3
faiss-cpu==1.7.4
scikit-learn==1.3.2
pandas==2.1.3
pydantic==2.5.0
python-dotenv==1.0.0
requests==2.31.0

# Nuevas para clustering
hdbscan==0.8.33
