# Scripts de Actualización Automática

Scripts para harvesting, indexación y clustering de repositorios UNAP/UNSA.

## 📁 Estructura

```
scripts/
├── 01.harvest_multi.py        # Extrae nuevos repos de DSpace
├── 02.semantic_indexer.py     # Genera embeddings y actualiza FAISS
└── 03.build_topics_hdbscan.py # Aplica clustering HDBSCAN
```

## 🚀 Uso Manual

### 1. Harvesting

```bash
# Verificar nuevos repos (sin insertar)
python scripts/01.harvest_multi.py --university UNAP --check-new
python scripts/01.harvest_multi.py --university UNSA --check-new

# Sincronización completa
python scripts/01.harvest_multi.py --university UNAP --full-sync
```

### 2. Indexación Semántica

```bash
# Incremental (solo nuevos items)
python scripts/02.semantic_indexer.py --incremental

# Reconstruir todo
python scripts/02.semantic_indexer.py --full-rebuild --batch-size 64
```

### 3. Clustering

```bash
# Incremental
python scripts/03.build_topics_hdbscan.py --incremental

# Reconstruir con parámetros personalizados
python scripts/03.build_topics_hdbscan.py --full-rebuild --min-cluster-size 10
```

## 🔄 Pipeline Completo

```bash
# 1. Harvest ambas universidades
python scripts/01.harvest_multi.py --university UNAP --full-sync
python scripts/01.harvest_multi.py --university UNSA --full-sync

# 2. Generar embeddings
python scripts/02.semantic_indexer.py --incremental

# 3. Aplicar clustering
python scripts/03.build_topics_hdbscan.py --incremental

# 4. Verificar resultados
python -c "
import faiss
import json

index = faiss.read_index('models_semantic/faiss.index')
with open('models_semantic/uuid_map.json') as f:
    uuid_map = json.load(f)

print(f'✅ Índice: {index.ntotal} vectores')
print(f'✅ UUID map: {len(uuid_map)} entries')
"
```

## ⚙️ Variables de Entorno

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/db"
```

## 🔧 Personalización

### Cambiar API de DSpace

Edita `scripts/01.harvest_multi.py`:

```python
DSPACE_URLS = {
    "UNAP": "https://repositorio.unap.edu.pe/rest",
    "UNSA": "https://tu-url-real.edu.pe/rest"  # Cambia aquí
}
```

### Ajustar Clustering

```bash
# Clusters más grandes (menos clusters totales)
python scripts/03.build_topics_hdbscan.py --incremental --min-cluster-size 15

# Clusters más pequeños (más clusters totales)
python scripts/03.build_topics_hdbscan.py --incremental --min-cluster-size 3
```

## 🧪 Testing Local

Antes de hacer push a GitHub:

```bash
# Test con base de datos de prueba
export DATABASE_URL="postgresql://localhost:5432/test_db"

# Ejecutar pipeline
python scripts/01.harvest_multi.py --university UNAP --check-new
python scripts/02.semantic_indexer.py --incremental
python scripts/03.build_topics_hdbscan.py --incremental
```

## 📊 Monitoreo

Verifica el estado en la base de datos:

```sql
-- Contar items por universidad
SELECT university, COUNT(*) 
FROM items 
GROUP BY university;

-- Contar items por cluster
SELECT cluster_id, COUNT(*) 
FROM clusters 
WHERE model_name = 'BAAI/bge-m3'
GROUP BY cluster_id 
ORDER BY COUNT(*) DESC 
LIMIT 10;

-- Ver etiquetas de clusters
SELECT cluster_id, label 
FROM cluster_labels 
WHERE model_name = 'BAAI/bge-m3'
ORDER BY cluster_id;
```

## ⚠️ Notas Importantes

1. **Implementar API real**: Los scripts son plantillas. Debes adaptar `fetch_items_from_dspace()` según el API real de UNAP/UNSA.

2. **Esquema de DB**: Asegúrate de que existan estas tablas:
   ```sql
   CREATE TABLE IF NOT EXISTS items (
       uuid TEXT PRIMARY KEY,
       title TEXT,
       abstract_norm TEXT,
       url TEXT,
       university TEXT,
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE TABLE IF NOT EXISTS clusters (
       uuid TEXT,
       cluster_id INTEGER,
       model_name TEXT,
       PRIMARY KEY (uuid, model_name)
   );
   
   CREATE TABLE IF NOT EXISTS cluster_labels (
       model_name TEXT,
       cluster_id INTEGER,
       label TEXT,
       PRIMARY KEY (model_name, cluster_id)
   );
   ```

3. **Git LFS**: El archivo `faiss.index` debe estar en Git LFS:
   ```bash
   git lfs track "models_semantic/faiss.index"
   git lfs track "models_semantic/uuid_map.json"
   ```

4. **GitHub Actions**: El workflow en `.github/workflows/update_repositories.yml` ejecuta estos scripts automáticamente.
