# HDBSCAN - Dependencia Opcional

## ⚠️ Por qué NO está en requirements.txt

`hdbscan` NO está incluido en `requirements.txt` porque:

1. **No compila en Hugging Face Spaces** - Requiere compilación C++ que falla en el entorno Docker de HF
2. **Solo necesario para clustering de tópicos** - La funcionalidad principal (búsqueda semántica) NO lo requiere
3. **GitHub Actions tampoco lo ejecuta** - El paso de clustering está comentado en el workflow

## ✅ Funcionalidad Principal (SIN hdbscan)

El sistema funciona perfectamente **sin hdbscan** con:
- ✅ Harvesting de repositorios (DSpace 7+ API)
- ✅ Indexación semántica con FAISS
- ✅ API de recomendaciones `/recommend`
- ✅ Extensión Chrome funcionando

## 📊 Clustering de Tópicos (OPCIONAL)

Si quieres ejecutar clustering **localmente**, instala manualmente:

```bash
pip install hdbscan==0.8.38
```

Luego ejecuta:
```bash
python scripts/03.build_topics_hdbscan.py
```

## 🚀 Deployment

**Hugging Face Spaces**: Deploy normal, clustering se omite automáticamente
**GitHub Actions**: Paso de clustering comentado en `.github/workflows/update_repositories.yml`
**Local**: Instala hdbscan si necesitas clustering

## 🔍 Archivos Afectados

- `requirements.txt` - NO incluye hdbscan
- `.github/workflows/update_repositories.yml` - Clustering comentado (líneas 71-77)
- `scripts/03.build_topics_hdbscan.py` - Detecta si hdbscan está disponible, sale gracefully si no

## ✨ Resultado

Sistema funcional en HF Spaces y GitHub Actions **sin errores de compilación**.
