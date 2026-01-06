# 🚨 PROBLEMA CRÍTICO: HF SPACES NO SINCRONIZADO CON GITHUB

## ✅ SITUACIÓN ACTUAL

1. **GitHub tiene el código correcto**:
   - ✅ `faiss.index` (nombre correcto)
   - ✅ `/health` con `index_loaded` y `index_count`
   - ✅ `rec.ready` implementado
   - Ver: https://github.com/tamoil-0/unap-research-hf/blob/main/app/main.py

2. **Hugging Face tiene código DESACTUALIZADO**:
   - ❌ `/ health` sin `index_loaded`
   - ❌ Versión antigua del código
   - Ver: https://huggingface.co/spaces/tamoil13/unap-research-ml/blob/main/app/main.py

3. **Consecuencia**:
   - El API funciona pero NO podemos verificar si el índice está cargado
   - `/recommend` podría dar 503 si el índice no carga
   - No hay forma de debuggear el problema real

## 🔧 SOLUCIÓN: RESINCRONIZAR HF SPACES CON GITHUB

### Opción 1: Desde la UI de Hugging Face (RECOMENDADO)

1. **Ve a Settings del Space**:
   https://huggingface.co/spaces/tamoil13/unap-research-ml/settings

2. **Busca la sección "Repository"**

3. **Si está configurado como mirror de GitHub**:
   - Click en "Force Sync" o "Refresh from GitHub"
   - Espera 2-3 minutos

4. **Si NO está configurado como mirror**:
   - Ir a "Files and versions"
   - Click en "Upload files"
   - Sube manualmente `app/main.py` y `app/recommender.py` desde tu local

### Opción 2: Push directo a HF con Git

Si HF Spaces tiene su propio repositorio Git (no espejo):

```bash
# 1. Agregar HF como remote (si no existe)
git remote add huggingface https://huggingface.co/spaces/tamoil13/unap-research-ml

# 2. Push forzado
git push huggingface main --force

# 3. Verificar en navegador que los archivos se actualizaron
# https://huggingface.co/spaces/tamoil13/unap-research-ml/tree/main/app
```

### Opción 3: Subida Manual por UI

Si todo lo demás falla:

1. Ve a: https://huggingface.co/spaces/tamoil13/unap-research-ml/tree/main/app

2. Click en `main.py` → "Edit file" (ícono de lápiz)

3. Copia el contenido desde:
   https://raw.githubusercontent.com/tamoil-0/unap-research-hf/main/app/main.py

4. Pega en el editor de HF

5. Commit: "fix: sync main.py from GitHub"

6. Repite para `recommender.py`:
   https://raw.githubusercontent.com/tamoil-0/unap-research-hf/main/app/recommender.py

## 📊 VERIFICACIÓN POST-SINCRONIZACIÓN

Una vez que HF se sincronice y el contenedor reconstruya:

```bash
curl https://tamoil13-unap-research-ml.hf.space/health
```

**Respuesta esperada**:
```json
{
  "ok": true,
  "ready": true,
  "model": "BAAI/bge-m3",
  "device": "cpu",
  "index_loaded": true,
  "index_count": 36756,
  "error": null
}
```

**Si aún muestra código antiguo**:
```json
{
  "ok": true,
  "model": "BAAI/bge-m3",
  "device": "cpu"
}
```
→ Significa que el contenedor no se rebuild con el nuevo código.

## 🔍 DIAGNÓSTICO ADICIONAL

### Verificar qué versión está corriendo

```bash
# Ver el código actual en HF Spaces
curl https://huggingface.co/spaces/tamoil13/unap-research-ml/raw/main/app/main.py | grep "index_loaded"

# Ver el código en GitHub
curl https://raw.githubusercontent.com/tamoil-0/unap-research-hf/main/app/main.py | grep "index_loaded"
```

Si GitHub tiene `index_loaded` pero HF no → Problema de sincronización
Si ambos lo tienen → Problema de caché o rebuild

### Forzar Rebuild del Contenedor

Después de sincronizar el código:

1. Ve a: https://huggingface.co/spaces/tamoil13/unap-research-ml/settings
2. Sección "Factory Reboot"
3. Click "Restart this Space"
4. Espera 3-5 minutos
5. Verifica con `curl /health`

## 🎯 CHECKLIST COMPLETO

- [ ] Confirmar que GitHub tiene `index_loaded` en `main.py`
- [ ] Confirmar que GitHub tiene `faiss.index` (no `index.faiss`) en `recommender.py`
- [ ] Resincronizar HF Spaces con GitHub (UI o Git)
- [ ] Verificar en UI de HF que los archivos se actualizaron
- [ ] Forzar Factory Reboot del Space
- [ ] Esperar 3-5 minutos para rebuild
- [ ] Test `/health` → debe tener `index_loaded`
- [ ] Test `/recommend` → debe devolver resultados (no 503)
- [ ] Test extensión Chrome → debe funcionar sin errores

## ⚠️ SI NADA FUNCIONA

**Plan B**: Crear nuevo Space desde cero

1. Backup del Space actual (si tiene datos)
2. Crear nuevo Space: https://huggingface.co/new-space
3. Configurar como Docker Space
4. Push desde GitHub:
   ```bash
   git remote add hf-new https://huggingface.co/spaces/tamoil13/NUEVO-NOMBRE
   git push hf-new main
   ```
5. Actualizar URL en la extensión Chrome

---

**PRÓXIMO PASO INMEDIATO**:
1. Ve a https://huggingface.co/spaces/tamoil13/unap-research-ml/settings
2. Force Sync o Restart Space
3. Espera 3 minutos
4. Ejecuta: `curl https://tamoil13-unap-research-ml.hf.space/health`
5. Verifica que aparezca `"index_loaded": true`
