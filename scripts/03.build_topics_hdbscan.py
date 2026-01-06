#!/usr/bin/env python3
"""
Script para clustering incremental con HDBSCAN.

Uso:
    python 03.build_topics_hdbscan.py --incremental
    python 03.build_topics_hdbscan.py --full-rebuild
"""
import argparse
import sys
import json
import numpy as np
import faiss
from sklearn.cluster import HDBSCAN
from typing import List

sys.path.insert(0, ".")
from app.db import get_conn

INDEX_PATH = "models_semantic/faiss.index"
UUID_MAP_PATH = "models_semantic/uuid_map.json"
MODEL_NAME = "BAAI/bge-m3"


def load_embeddings():
    """Cargar embeddings desde FAISS index."""
    index = faiss.read_index(INDEX_PATH)
    
    # Extraer todos los vectores
    vectors = np.zeros((index.ntotal, index.d), dtype='float32')
    for i in range(index.ntotal):
        vectors[i] = index.reconstruct(int(i))
    
    return vectors, index.ntotal


def load_uuid_map():
    """Cargar mapeo UUID -> índice."""
    with open(UUID_MAP_PATH) as f:
        uuid_map = json.load(f)
    
    # Invertir el mapeo: índice -> UUID
    idx_to_uuid = {v: k for k, v in uuid_map.items()}
    return idx_to_uuid


def cluster_embeddings(embeddings: np.ndarray, min_cluster_size: int = 5):
    """Aplicar HDBSCAN clustering."""
    print(f"🔬 Aplicando HDBSCAN (min_cluster_size={min_cluster_size})...")
    
    clusterer = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=3,
        metric='euclidean',
        cluster_selection_method='eom',
        prediction_data=True
    )
    
    labels = clusterer.fit_predict(embeddings)
    
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    
    print(f"✅ Clusters encontrados: {n_clusters}")
    print(f"   Ruido: {n_noise} items ({n_noise/len(labels)*100:.1f}%)")
    
    return labels


def update_cluster_assignments(conn, idx_to_uuid: dict, labels: np.ndarray):
    """Actualizar asignaciones de cluster en la DB."""
    print("💾 Actualizando asignaciones en la base de datos...")
    
    with conn.cursor() as cur:
        # Limpiar clusters anteriores
        cur.execute(
            "DELETE FROM clusters WHERE model_name = %s",
            (MODEL_NAME,)
        )
        
        # Insertar nuevas asignaciones
        inserted = 0
        for idx, label in enumerate(labels):
            if label == -1:  # Skip noise
                continue
            
            uuid = idx_to_uuid.get(idx)
            if not uuid:
                continue
            
            cur.execute(
                """
                INSERT INTO clusters (uuid, cluster_id, model_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (uuid, model_name) 
                DO UPDATE SET cluster_id = EXCLUDED.cluster_id
                """,
                (uuid, int(label), MODEL_NAME)
            )
            inserted += 1
        
        conn.commit()
        print(f"✅ Actualizadas {inserted} asignaciones")


def generate_cluster_labels(conn):
    """
    Generar etiquetas automáticas para clusters basándose en términos frecuentes.
    
    NOTA: Implementación simplificada. 
    Idealmente usarías TF-IDF o extracción de keywords.
    """
    print("🏷️  Generando etiquetas de clusters...")
    
    with conn.cursor() as cur:
        # Obtener clusters únicos
        cur.execute(
            """
            SELECT DISTINCT cluster_id
            FROM clusters
            WHERE model_name = %s
            ORDER BY cluster_id
            """,
            (MODEL_NAME,)
        )
        cluster_ids = [row[0] for row in cur.fetchall()]
        
        # Para cada cluster, generar label basado en títulos comunes
        for cluster_id in cluster_ids:
            cur.execute(
                """
                SELECT i.title
                FROM items i
                JOIN clusters c ON c.uuid = i.uuid
                WHERE c.cluster_id = %s AND c.model_name = %s
                LIMIT 10
                """,
                (cluster_id, MODEL_NAME)
            )
            titles = [row[0] for row in cur.fetchall() if row[0]]
            
            # Generar label simple (primeras palabras del título más común)
            if titles:
                # Tomar palabras más frecuentes (implementación simple)
                words = []
                for title in titles:
                    words.extend(title.lower().split()[:3])
                
                # Contar frecuencias
                from collections import Counter
                common = Counter(words).most_common(3)
                label = " ".join([w for w, _ in common if len(w) > 3])[:50]
                
                if not label:
                    label = f"Cluster {cluster_id}"
            else:
                label = f"Cluster {cluster_id}"
            
            # Guardar label
            cur.execute(
                """
                INSERT INTO cluster_labels (model_name, cluster_id, label)
                VALUES (%s, %s, %s)
                ON CONFLICT (model_name, cluster_id)
                DO UPDATE SET label = EXCLUDED.label
                """,
                (MODEL_NAME, cluster_id, label)
            )
        
        conn.commit()
        print(f"✅ Generadas {len(cluster_ids)} etiquetas")


def main():
    parser = argparse.ArgumentParser(description="Build topic clusters with HDBSCAN")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Reclustear con nuevos items"
    )
    parser.add_argument(
        "--full-rebuild",
        action="store_true",
        help="Reconstruir clusters completamente"
    )
    parser.add_argument(
        "--min-cluster-size",
        type=int,
        default=5,
        help="Tamaño mínimo de cluster"
    )
    
    args = parser.parse_args()
    
    if not args.incremental and not args.full_rebuild:
        print("❌ Debes especificar --incremental o --full-rebuild")
        return 1
    
    print("🚀 Iniciando clustering...")
    
    # Cargar embeddings
    print("📥 Cargando embeddings desde FAISS...")
    embeddings, n_vectors = load_embeddings()
    print(f"✅ Cargados {n_vectors} vectores")
    
    # Cargar UUID map
    idx_to_uuid = load_uuid_map()
    
    # Aplicar clustering
    labels = cluster_embeddings(embeddings, args.min_cluster_size)
    
    # Conectar a DB
    conn = get_conn()
    
    try:
        # Actualizar asignaciones
        update_cluster_assignments(conn, idx_to_uuid, labels)
        
        # Generar labels
        generate_cluster_labels(conn)
        
        print("✅ Clustering completado exitosamente")
    
    finally:
        conn.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
