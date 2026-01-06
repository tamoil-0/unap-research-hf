# 🚀 GitHub Actions - Configuración Completa

## ✅ Sistema Instalado

Tu sistema de actualización automática ya está configurado. El workflow ejecutará:

### 📋 Pipeline Automático

```
┌─────────────────────────────────────────────┐
│  CADA LUNES 3 AM UTC (Automático)           │
│  O Manual desde GitHub Actions              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  1. HARVEST (01.harvest_multi.py)           │
│     - Escanea UNAP y UNSA DSpace            │
│     - Detecta nuevos repositorios           │
│     - Guarda en PostgreSQL                  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  2. SEMANTIC INDEX (02.semantic_indexer.py) │
│     - Codifica nuevos documentos            │
│     - Actualiza índice FAISS                │
│     - Embeddings con BAAI/bge-m3            │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  3. CLUSTERING (03.build_topics_hdbscan.py) │
│     - Agrupa documentos por temas           │
│     - HDBSCAN clustering                    │
│     - Genera etiquetas automáticas          │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  4. DEPLOY                                   │
│     - Git commit con resumen                │
│     - Push a GitHub (origin/main)           │
│     - Push a Hugging Face Spaces            │
│     - Rebuild automático del container      │
└─────────────────────────────────────────────┘
```

## 🔧 Configuración Requerida

### 1️⃣ Secretos de GitHub (URGENTE)

Ve a: https://github.com/tamoil-0/unap-research-hf/settings/secrets/actions

Crea estos 2 secretos:

**`DATABASE_URL`**
```
postgresql://usuario:password@host:puerto/database
```
Ejemplo: `postgresql://postgres:mypass@db.render.com:5432/unap_research`

**`HF_TOKEN`**
1. Ve a: https://huggingface.co/settings/tokens
2. Crea "New token" con permisos de **write**
3. Copia el token completo

### 2️⃣ Verificar Estructura de Base de Datos

Asegúrate que tu PostgreSQL tiene estas tablas:

```sql
-- Items principales
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

-- Clusters de temas
CREATE TABLE clusters (
    uuid VARCHAR(255),
    model_name VARCHAR(100),
    cluster_id INTEGER,
    PRIMARY KEY (uuid, model_name),
    FOREIGN KEY (uuid) REFERENCES items(uuid) ON DELETE CASCADE
);

-- Etiquetas de clusters
CREATE TABLE cluster_labels (
    model_name VARCHAR(100),
    cluster_id INTEGER,
    label TEXT,
    PRIMARY KEY (model_name, cluster_id)
);
```

Si no existen, ejecútalas en tu base de datos Render.

## 🎮 Cómo Usar

### Ejecución Automática (Recomendado)

El workflow se ejecuta **automáticamente cada lunes a las 3 AM UTC**.

No necesitas hacer nada, solo:
1. ✅ Configurar los secretos (paso 1️⃣ arriba)
2. ✅ Esperar al próximo lunes

### Ejecución Manual

Si quieres ejecutar ahora mismo:

1. Ve a: https://github.com/tamoil-0/unap-research-hf/actions
2. Click en "Update Repositories (UNAP/UNSA)"
3. Click en "Run workflow" (botón derecho)
4. Selecciona branch: `main`
5. (Opcional) Marca "Forzar reindexación completa"
6. Click "Run workflow"

### Monitorear Ejecución

Mientras corre:
1. Ve a: https://github.com/tamoil-0/unap-research-hf/actions
2. Click en el workflow en ejecución
3. Ver logs en tiempo real

## 📊 Cambios en Frecuencia

### Cambiar a Mensual

Edita `.github/workflows/update_repositories.yml`:

```yaml
schedule:
  # Primer lunes de cada mes a las 3 AM UTC
  - cron: '0 3 1-7 * 1'
```

### Cambiar a Diario

```yaml
schedule:
  # Todos los días a las 3 AM UTC
  - cron: '0 3 * * *'
```

### Cambiar Hora

```yaml
schedule:
  # Cada lunes a las 10 PM UTC (5 PM Perú)
  - cron: '0 22 * * 1'
```

## 🐛 Troubleshooting

### Error: "DATABASE_URL not set"
- Configuraste el secreto `DATABASE_URL` en GitHub?
- El formato es correcto? (`postgresql://...`)

### Error: "HF_TOKEN not set"
- Configuraste el secreto `HF_TOKEN`?
- El token tiene permisos de **write**?

### No detecta nuevos items
- Los repositorios UNAP/UNSA están online?
- Verifica URLs en `scripts/01.harvest_multi.py`:
  ```python
  REPOSITORIES = {
      "UNAP": {
          "base_url": "http://repositorio.unap.edu.pe",
          ...
      }
  }
  ```

### Ver Logs del Workflow
1. https://github.com/tamoil-0/unap-research-hf/actions
2. Click en la ejecución fallida
3. Expandir los pasos para ver errores

## 📝 Archivos Creados

```
unap-research-hf/
├── .github/
│   └── workflows/
│       └── update_repositories.yml    ← Workflow principal
├── scripts/
│   ├── 01.harvest_multi.py           ← Harvesting
│   ├── 02.semantic_indexer.py        ← Indexing FAISS
│   └── 03.build_topics_hdbscan.py    ← Clustering
├── data/                              ← Archivos temporales
├── models_semantic/                   ← Índice FAISS
├── requirements.txt                   ← Dependencias (con hdbscan)
└── GITHUB_ACTIONS_SETUP.md           ← Esta guía

```

## ✅ Próximos Pasos

1. **Ahora mismo**: Configura los secretos (DATABASE_URL y HF_TOKEN)
2. **Opcional**: Ejecuta manualmente para probar
3. **Lunes próximo**: El workflow correrá automáticamente

## 🎉 ¡Listo!

Tu sistema está configurado para:
- ✅ Detectar nuevos repos automáticamente
- ✅ Actualizar el índice semántico
- ✅ Agrupar por temas
- ✅ Desplegar a producción

Todo sin intervención manual cada semana/mes.
