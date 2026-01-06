# GitHub Actions - Configuración de Secrets

Para que el workflow funcione, necesitas configurar estos secrets en tu repositorio de GitHub:

## 📋 Secrets Requeridos

Ve a: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

### 1. DATABASE_URL
- **Descripción**: URL de conexión a PostgreSQL en Render
- **Formato**: `postgresql://user:password@host:5432/database`
- **Obtener de**: Render Dashboard → tu servicio PostgreSQL → "Internal Database URL"

### 2. HF_TOKEN
- **Descripción**: Token de autenticación de Hugging Face
- **Obtener de**: https://huggingface.co/settings/tokens
- **Permisos necesarios**: `write` (para poder hacer push y restart)
- **Formato**: `hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## 🔧 Configuración Adicional

### Ajustar el Schedule

En el archivo `.github/workflows/update_repositories.yml`, puedes modificar el cron:

```yaml
schedule:
  - cron: '0 2 * * 0'  # Semanal: Domingos a las 2 AM UTC
  # - cron: '0 2 1 * *'  # Mensual: Día 1 de cada mes a las 2 AM UTC
  # - cron: '0 */6 * * *'  # Cada 6 horas
```

**Sintaxis cron**: `minuto hora día_mes mes día_semana`
- Ejemplo: `0 2 * * 0` = Minuto 0, Hora 2, Todos los días del mes, Todos los meses, Domingo

### Ejecutar Manualmente

El workflow incluye `workflow_dispatch`, lo que permite ejecutarlo manualmente:
1. Ve a: `Actions` → `Update UNAP/UNSA Repositories`
2. Click en "Run workflow"
3. Selecciona la rama `main`
4. Click en "Run workflow" verde

## 📝 Notas Importantes

1. **Git LFS**: El workflow maneja automáticamente Git LFS para el archivo `faiss.index`
2. **Incremental**: Los scripts deben soportar el flag `--incremental` para solo procesar nuevos items
3. **Error Handling**: Si falla, revisa los logs en la pestaña "Actions" de GitHub
4. **Costos**: GitHub Actions es gratis para repos públicos (2000 minutos/mes en privados)

## 🧪 Probar Localmente

Antes de hacer push, prueba el workflow localmente:

```bash
# Simular el proceso
export DATABASE_URL="postgresql://..."
python scripts/01.harvest_multi.py --university UNAP --check-new
python scripts/02.semantic_indexer.py --incremental
python scripts/03.build_topics_hdbscan.py --incremental
```

## ✅ Verificación Post-Deploy

Después de que el workflow se ejecute:

1. Verifica el commit en GitHub (debe tener el mensaje "chore: update repositories index")
2. Verifica que HF Spaces se reinició
3. Prueba el endpoint: `https://tamoil13-unap-research-ml.hf.space/health`
4. Revisa `index_count` en el health endpoint

## 🔔 Monitoreo

GitHub te enviará un email si el workflow falla. También puedes:
- Ver el historial en: `Actions` → `Update UNAP/UNSA Repositories`
- Ver el summary con estadísticas de cada ejecución
