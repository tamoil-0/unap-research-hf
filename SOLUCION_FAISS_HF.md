# SOLUCIÓN: SUBIR ÍNDICE FAISS A HUGGING FACE SPACES

## 🔴 PROBLEMA IDENTIFICADO

El índice FAISS (150 MB) nunca llegó a Hugging Face Spaces porque:
1. El archivo `.gitattributes` tenía un conflicto de merge sin resolver
2. Git LFS rechazó el push por archivos binarios no permitidos (extension/icons/icono.png)
3. Como resultado, la carpeta `models_semantic/` nunca se subió al Space
4. El backend responde "Modelo cargando" pero nunca se completa

## ✅ SOLUCIÓN APLICADA

### 1. Conflicto Resuelto
- Se limpió el conflicto en `.gitattributes`
- Se configuró correctamente el tracking de `*.index` y `models_semantic/*`

### 2. Archivos Binarios Excluidos
- El `.gitignore` ya excluye `extension/icons/*.png`
- Estos archivos NO se subirán al Space

### 3. Verificación de LFS
```
✅ faiss.index está tracked por Git LFS (150 MB)
✅ uuid_map.json está tracked por Git LFS (1.4 MB)
✅ meta.json está tracked por Git LFS (140 bytes)
```

## 🚀 PASOS PARA SUBIR A HUGGING FACE

### Opción A: Push Directo (RECOMENDADO)

```bash
# 1. Verificar estado
git status
git lfs ls-files

# 2. Asegurarse de estar en la rama correcta
git branch

# 3. Si necesitas agregar más archivos
git add app/ models_semantic/ Dockerfile requirements.txt

# 4. Commit de todo lo necesario
git commit -m "feat: agregar índice FAISS y configuración completa para HF Spaces"

# 5. Push a Hugging Face (con LFS)
git push origin hf
```

**IMPORTANTE**: Si el push falla por "file size exceeded", verifica:
```bash
# Ver qué archivos se están intentando subir
git diff --name-only origin/hf..HEAD

# Si extension/icons/icono.png aparece, removerlo del historio:
git rm --cached extension/icons/*.png
git commit --amend
```

### Opción B: Push Forzado (Solo si hay conflictos)

Si hay conflictos con commits previos en HF:

```bash
# 1. Asegurarse de tener todo commiteado localmente
git status

# 2. Backup de seguridad
git branch backup-$(date +%Y%m%d)

# 3. Push forzado (CUIDADO: sobrescribe el remoto)
git push origin hf --force
```

### Opción C: Subida Manual Alternativa

Si Git LFS sigue fallando, usa la interfaz web de Hugging Face:

1. Ve a tu Space: https://huggingface.co/spaces/TU_USUARIO/unap-research-hf
2. Click en "Files" → "Upload files"
3. Arrastra toda la carpeta `models_semantic/`
4. Hugging Face detectará automáticamente que son archivos grandes

## 📊 VERIFICACIÓN POST-PUSH

Una vez que el push sea exitoso:

### 1. Verificar que los archivos llegaron
```bash
# Desde terminal local
curl -s https://huggingface.co/spaces/TU_USUARIO/unap-research-hf/tree/main | grep -o "faiss.index"
```

O directamente en el navegador:
- https://huggingface.co/spaces/TU_USUARIO/unap-research-hf/tree/main/models_semantic

Deberías ver:
- ✅ faiss.index (150 MB)
- ✅ uuid_map.json (1.4 MB)  
- ✅ meta.json (140 bytes)

### 2. Verificar logs del contenedor

En HF Spaces, ve a "Logs" y busca:

```
✅ ÉXITO:
Loading FAISS index from models_semantic/faiss.index...
✓ FAISS index loaded: 36756 vectors, dim=1024

❌ ERROR (si aún falla):
RuntimeError: FAISS index not found.
```

### 3. Probar el endpoint

```bash
# Test básico
curl https://TU_USUARIO-unap-research-hf.hf.space/health

# Debería responder:
{
  "ok": true,
  "model": "BAAI/bge-m3",
  "device": "cpu",
  "index_loaded": true,  # ← Este debe ser true
  "index_count": 36756
}

# Test de recomendación
curl -X POST https://TU_USUARIO-unap-research-hf.hf.space/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning en procesamiento de lenguaje natural",
    "top_k": 5
  }'

# Debería responder con 5 tesis relacionadas
```

## 🔧 TROUBLESHOOTING

### Error: "remote: error: File extension/icons/icono.png is 2.50 MB; this exceeds GitHub's file size limit of 100.00 MB"

**Causa**: El archivo PNG está en el historial de Git.

**Solución**:
```bash
# Remover del staging
git rm --cached extension/icons/*.png

# Verificar que .gitignore lo excluye
cat .gitignore | grep "extension/icons"

# Commit
git commit -m "chore: excluir archivos binarios de extension"

# Retry push
git push origin hf
```

### Error: "batch response: This repository is over its data quota"

**Causa**: El Space excedió su límite de almacenamiento (50 GB gratuito).

**Solución**:
1. Ve a Settings del Space
2. Upgrade a plan persistente ($5/mes para 200 GB)
3. O limpia archivos antiguos del historial

### Error: "Error uploading objects: Git LFS is not enabled"

**Causa**: El Space no tiene LFS habilitado.

**Solución**:
```bash
# Verificar que LFS está instalado localmente
git lfs version

# Re-instalar LFS hooks
git lfs install --force

# Verificar tracking
git lfs track

# Retry push
git push origin hf
```

## 📋 CHECKLIST FINAL

Antes de declarar victoria, verifica:

- [ ] `.gitattributes` sin conflictos
- [ ] `extension/icons/*.png` en `.gitignore`
- [ ] `git lfs ls-files` muestra faiss.index
- [ ] `git status` está limpio
- [ ] Commit realizado con éxito
- [ ] Push a HF sin errores
- [ ] Archivos visibles en HF web interface
- [ ] Logs del contenedor muestran "FAISS index loaded"
- [ ] `/health` responde `"index_loaded": true`
- [ ] `/recommend` devuelve resultados (no 503)

## 🎯 RESULTADO ESPERADO

Una vez completado:

```json
// GET /health
{
  "ok": true,
  "model": "BAAI/bge-m3",
  "device": "cpu",
  "index_loaded": true,
  "index_count": 36756,
  "faiss_path": "models_semantic/faiss.index"
}

// POST /recommend
{
  "results": [
    {
      "uuid": "abc123",
      "title": "Machine Learning aplicado a...",
      "score": 0.89,
      "university": "UNAP",
      "year": 2023
    },
    // ... 4 más
  ]
}
```

## 📞 SOPORTE ADICIONAL

Si el problema persiste después de estos pasos:

1. **Revisa logs del Space**: Settings → Logs → Busca "RuntimeError"
2. **Verifica tamaño real del archivo**:
   ```bash
   ls -lh models_semantic/faiss.index
   ```
3. **Contacta soporte de HF**: https://huggingface.co/support (si es problema de cuota/LFS)

## 🔗 RECURSOS

- [HF Spaces - Git LFS](https://huggingface.co/docs/hub/repositories-getting-started#git-lfs)
- [HF Spaces - Storage Limits](https://huggingface.co/docs/hub/spaces-storage)
- [Git LFS Documentation](https://git-lfs.com/)
