#!/usr/bin/env python3
"""
Script para indexación semántica incremental usando BAAI/bge-m3.

Uso:
    python 02.semantic_indexer.py --incremental
    python 02.semantic_indexer.py --full-rebuild
"""
import argparse
import sys
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Tuple

sys.path.insert(0, ".")
from app.db import get_conn

MODEL_NAME = "BAAI/bge-m3"
INDEX_PATH = "models_semantic/faiss.index"
UUID_MAP_PATH = "models_semantic/uuid_map.json"
META_PATH = "models_semantic/meta.json"


def load_existing_index():
    """Cargar índice existente y uuid_map."""
    try:
        index = faiss.read_index(INDEX_PATH)
        with open(UUID_MAP_PATH) as f:
            uuid_map = json.load(f)
        print(f"📥 Índice existente: {index.ntotal} vectores")
        return index, uuid_map
    except FileNotFoundError:
        print("⚠️  No se encontró índice existente, creando nuevo...")
        return None, {}


def get_unindexed_items(conn, existing_uuids: List[str]) -> List[Tuple[str, str]]:
    """Obtener items que no están en el índice."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT uuid, 
                   COALESCE(title || ' ' || abstract_norm, title, abstract_norm, '') as text
            FROM items
            WHERE uuid NOT IN %s
            AND (title IS NOT NULL OR abstract_norm IS NOT NULL)
            """,
            (tuple(existing_uuids) if existing_uuids else ('',),)
        )
        return cur.fetchall()


def encode_texts(model: SentenceTransformer, texts: List[str], batch_size: int = 32):
    """Encode texts en batches."""
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    return embeddings.astype("float32")


def main():
    parser = argparse.ArgumentParser(description="Semantic indexing incremental")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Solo indexar nuevos items"
    )
    parser.add_argument(
        "--full-rebuild",
        action="store_true",
        help="Reconstruir índice completo"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size para encoding"
    )
    
    args = parser.parse_args()
    
    if not args.incremental and not args.full_rebuild:
        print("❌ Debes especificar --incremental o --full-rebuild")
        return 1
    
    print(f"🚀 Iniciando indexación {'incremental' if args.incremental else 'completa'}...")
    
    # Cargar modelo
    print(f"📦 Cargando modelo {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    dim = model.get_sentence_embedding_dimension()
    print(f"✅ Modelo cargado (dim={dim})")
    
    # Conectar a DB
    conn = get_conn()
    
    try:
        # Cargar índice existente si es incremental
        if args.incremental:
            index, uuid_map = load_existing_index()
            existing_uuids = list(uuid_map.keys())
        else:
            index = None
            uuid_map = {}
            existing_uuids = []
        
        # Obtener items no indexados
        print("🔍 Buscando items no indexados...")
        unindexed = get_unindexed_items(conn, existing_uuids)
        print(f"📊 Items para indexar: {len(unindexed)}")
        
        if not unindexed:
            print("✅ Todos los items ya están indexados")
            return 0
        
        # Extraer UUIDs y textos
        new_uuids = [row[0] for row in unindexed]
        new_texts = [row[1] for row in unindexed]
        
        # Encode
        print("🧠 Generando embeddings...")
        new_embeddings = encode_texts(model, new_texts, args.batch_size)
        
        # Crear o actualizar índice
        if index is None:
            print("🏗️  Creando nuevo índice FAISS...")
            index = faiss.IndexFlatIP(dim)  # Inner Product (cosine con vectores normalizados)
        
        # Agregar vectores
        start_idx = index.ntotal
        index.add(new_embeddings)
        print(f"✅ Agregados {len(new_embeddings)} vectores")
        
        # Actualizar uuid_map
        for i, uuid in enumerate(new_uuids):
            uuid_map[uuid] = start_idx + i
        
        # Guardar
        print("💾 Guardando índice...")
        faiss.write_index(index, INDEX_PATH)
        
        with open(UUID_MAP_PATH, "w") as f:
            json.dump(uuid_map, f)
        
        with open(META_PATH, "w") as f:
            json.dump({
                "model_name": MODEL_NAME,
                "dim": dim,
                "total_vectors": index.ntotal,
                "last_updated": str(np.datetime64('now'))
            }, f, indent=2)
        
        print(f"✅ Índice actualizado: {index.ntotal} vectores totales")
        print(f"📁 Archivos guardados:")
        print(f"  - {INDEX_PATH}")
        print(f"  - {UUID_MAP_PATH}")
        print(f"  - {META_PATH}")
    
    finally:
        conn.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
