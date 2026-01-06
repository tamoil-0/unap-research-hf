#!/usr/bin/env python3
"""
Script de verificación pre-push para Hugging Face Spaces
Verifica que todos los archivos necesarios estén listos antes de hacer push
"""

import os
import subprocess
import json
from pathlib import Path

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def check(condition, message, fix_hint=None):
    """Verifica una condición y muestra el resultado"""
    if condition:
        print(f"{Colors.GREEN}✓{Colors.END} {message}")
        return True
    else:
        print(f"{Colors.RED}✗{Colors.END} {message}")
        if fix_hint:
            print(f"  {Colors.YELLOW}→ {fix_hint}{Colors.END}")
        return False

def main():
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}  VERIFICACIÓN PRE-PUSH - HUGGING FACE SPACES{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    all_ok = True
    
    # 1. Verificar que models_semantic existe
    print(f"{Colors.BLUE}[1] Archivos FAISS{Colors.END}")
    models_dir = Path("models_semantic")
    
    all_ok &= check(
        models_dir.exists(),
        "Carpeta models_semantic/ existe",
        "Crea la carpeta: mkdir models_semantic"
    )
    
    # 2. Verificar archivos individuales
    faiss_index = models_dir / "faiss.index"
    uuid_map = models_dir / "uuid_map.json"
    meta_json = models_dir / "meta.json"
    
    all_ok &= check(
        faiss_index.exists(),
        f"faiss.index existe ({faiss_index.stat().st_size / (1024**2):.1f} MB)" if faiss_index.exists() else "faiss.index NO existe",
        "Ejecuta scripts/02.semantic_indexer.py"
    )
    
    all_ok &= check(
        uuid_map.exists(),
        f"uuid_map.json existe ({uuid_map.stat().st_size / 1024:.1f} KB)" if uuid_map.exists() else "uuid_map.json NO existe",
        "Ejecuta scripts/02.semantic_indexer.py"
    )
    
    all_ok &= check(
        meta_json.exists(),
        "meta.json existe",
        "Ejecuta scripts/02.semantic_indexer.py"
    )
    
    # 3. Verificar contenido de meta.json
    if meta_json.exists():
        try:
            with open(meta_json) as f:
                meta = json.load(f)
            all_ok &= check(
                meta.get("count", 0) > 0,
                f"meta.json tiene {meta.get('count', 0)} vectores indexados",
                "Verifica que el índice se construyó correctamente"
            )
        except Exception as e:
            all_ok &= check(False, f"Error leyendo meta.json: {e}")
    
    # 4. Verificar Git LFS
    print(f"\n{Colors.BLUE}[2] Git LFS{Colors.END}")
    
    try:
        result = subprocess.run(
            ["git", "lfs", "ls-files"],
            capture_output=True,
            text=True,
            check=True
        )
        lfs_files = result.stdout
        
        all_ok &= check(
            "faiss.index" in lfs_files,
            "faiss.index está tracked por Git LFS",
            "Ejecuta: git lfs track 'models_semantic/*.index'"
        )
        
        all_ok &= check(
            "uuid_map.json" in lfs_files,
            "uuid_map.json está tracked por Git LFS",
            "Ejecuta: git lfs track 'models_semantic/*'"
        )
    except subprocess.CalledProcessError:
        all_ok &= check(False, "Git LFS no está disponible", "Instala Git LFS: git lfs install")
    
    # 5. Verificar .gitattributes
    print(f"\n{Colors.BLUE}[3] Configuración Git{Colors.END}")
    
    gitattributes = Path(".gitattributes")
    if gitattributes.exists():
        content = gitattributes.read_text()
        all_ok &= check(
            "<<<<<<< HEAD" not in content,
            ".gitattributes NO tiene conflictos de merge",
            "Resuelve el conflicto en .gitattributes"
        )
        
        all_ok &= check(
            "*.index filter=lfs" in content or "models_semantic/*" in content,
            ".gitattributes configura LFS para índices",
            "Agrega: *.index filter=lfs diff=lfs merge=lfs -text"
        )
    else:
        all_ok &= check(False, ".gitattributes NO existe", "Ejecuta: git lfs track 'models_semantic/*'")
    
    # 6. Verificar .gitignore
    gitignore = Path(".gitignore")
    if gitignore.exists():
        content = gitignore.read_text()
        all_ok &= check(
            "extension/icons" in content or "*.png" in content,
            ".gitignore excluye archivos PNG problemáticos",
            "Agrega a .gitignore: extension/icons/*.png"
        )
    
    # 7. Verificar estado de Git
    print(f"\n{Colors.BLUE}[4] Estado Git{Colors.END}")
    
    try:
        # Archivos sin commit
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        uncommitted = result.stdout.strip()
        
        if uncommitted:
            print(f"{Colors.YELLOW}⚠{Colors.END} Hay cambios sin commitear:")
            lines = uncommitted.split('\n')
            for line in lines[:5]:
                print(f"    {line}")
            if len(lines) > 5:
                remaining = len(lines) - 5
                print(f"    ... y {remaining} más")
        else:
            all_ok &= check(True, "No hay cambios sin commitear")
    except subprocess.CalledProcessError:
        pass
    
    # 8. Verificar archivos esenciales para HF Spaces
    print(f"\n{Colors.BLUE}[5] Archivos esenciales para HF Spaces{Colors.END}")
    
    all_ok &= check(Path("Dockerfile").exists(), "Dockerfile existe")
    all_ok &= check(Path("requirements.txt").exists(), "requirements.txt existe")
    all_ok &= check(Path("app/main.py").exists(), "app/main.py existe")
    all_ok &= check(Path("app/recommender.py").exists(), "app/recommender.py existe")
    
    # Resultado final
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    if all_ok:
        print(f"{Colors.GREEN}✓ TODO OK - LISTO PARA PUSH{Colors.END}")
        print(f"\n{Colors.BLUE}Siguiente paso:{Colors.END}")
        print(f"  git push origin hf")
    else:
        print(f"{Colors.RED}✗ HAY PROBLEMAS - ARREGLA ANTES DE HACER PUSH{Colors.END}")
        return 1
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    return 0

if __name__ == "__main__":
    exit(main())
