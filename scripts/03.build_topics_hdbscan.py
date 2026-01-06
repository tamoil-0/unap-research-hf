#!/usr/bin/env python3
"""
03. Build Topics HDBSCAN - Topic Clustering
Clusters documents into topics using HDBSCAN on FAISS embeddings.
Updates PostgreSQL with cluster assignments.

NOTE: This script requires hdbscan which is NOT in requirements.txt
because it can't compile on Hugging Face Spaces. Only run locally.
"""

import os
import json
import time
import sys

# Check if hdbscan is available
try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    print("⚠️ WARNING: hdbscan not installed. Clustering skipped.")
    print("   Install locally with: pip install hdbscan==0.8.38")
    HDBSCAN_AVAILABLE = False

import numpy as np
import faiss
from typing import Dict, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
import psycopg2
from psycopg2.extras import execute_values

# Configuration
MODEL_DIR = "models_semantic"
INDEX_PATH = os.path.join(MODEL_DIR, "faiss.index")
UUID_MAP_PATH = os.path.join(MODEL_DIR, "uuid_map.json")
MODEL_NAME = "BAAI/bge-m3"

# HDBSCAN parameters
MIN_CLUSTER_SIZE = 5
MIN_SAMPLES = 3
CLUSTER_SELECTION_EPSILON = 0.0

def get_db_connection():
    """Get PostgreSQL connection"""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set")
    return psycopg2.connect(database_url)

def load_index_and_mappings() -> Tuple[np.ndarray, Dict[str, str]]:
    """
    Load FAISS index and UUID mappings
    
    Returns:
        Tuple of (embeddings, uuid_map)
    """
    print("  📂 Loading FAISS index...")
    index = faiss.read_index(INDEX_PATH)
    
    # Extract all vectors
    embeddings = np.zeros((index.ntotal, index.d), dtype="float32")
    for i in range(index.ntotal):
        embeddings[i] = index.reconstruct(i)
    
    with open(UUID_MAP_PATH, "r") as f:
        uuid_map = json.load(f)
    
    print(f"  ✓ Loaded {len(embeddings)} vectors")
    return embeddings, uuid_map

def perform_clustering(embeddings: np.ndarray) -> np.ndarray:
    """
    Cluster embeddings using HDBSCAN
    
    Args:
        embeddings: Document embeddings
    
    Returns:
        Cluster labels array
    """
    print(f"  🎯 Clustering with HDBSCAN...")
    print(f"     - min_cluster_size: {MIN_CLUSTER_SIZE}")
    print(f"     - min_samples: {MIN_SAMPLES}")
    
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=MIN_CLUSTER_SIZE,
        min_samples=MIN_SAMPLES,
        cluster_selection_epsilon=CLUSTER_SELECTION_EPSILON,
        metric="cosine",
        core_dist_n_jobs=-1
    )
    
    labels = clusterer.fit_predict(embeddings)
    
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    
    print(f"  ✅ Found {n_clusters} clusters")
    print(f"     - Noise points: {n_noise}")
    
    return labels

def generate_cluster_labels(conn, uuid_map: Dict[str, str], labels: np.ndarray) -> Dict[int, str]:
    """
    Generate human-readable labels for clusters using TF-IDF
    
    Args:
        conn: Database connection
        uuid_map: Mapping from index to UUID
        labels: Cluster labels
    
    Returns:
        Dictionary mapping cluster_id to label
    """
    print("  🏷️  Generating cluster labels...")
    
    # Group UUIDs by cluster
    clusters = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue
        
        uuid = uuid_map[str(idx)]
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(uuid)
    
    # Fetch texts for each cluster
    cluster_labels = {}
    
    for cluster_id, uuids in clusters.items():
        # Fetch titles for this cluster
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT title_norm
                FROM items
                WHERE uuid = ANY(%s)
                """,
                (uuids,)
            )
            texts = [row[0] for row in cur.fetchall() if row[0]]
        
        if not texts:
            cluster_labels[cluster_id] = f"Cluster {cluster_id}"
            continue
        
        # Use TF-IDF to find representative terms
        try:
            vectorizer = TfidfVectorizer(
                max_features=10,
                stop_words=None,
                ngram_range=(1, 2)
            )
            vectorizer.fit(texts)
            
            # Get top 3 terms
            feature_names = vectorizer.get_feature_names_out()
            top_terms = feature_names[:3]
            label = " + ".join(top_terms)
            
            cluster_labels[cluster_id] = label
        except:
            cluster_labels[cluster_id] = f"Cluster {cluster_id}"
    
    print(f"  ✅ Generated {len(cluster_labels)} cluster labels")
    return cluster_labels

def save_clusters_to_db(conn, uuid_map: Dict[str, str], labels: np.ndarray, cluster_labels: Dict[int, str]):
    """
    Save cluster assignments to database
    
    Args:
        conn: Database connection
        uuid_map: Mapping from index to UUID
        labels: Cluster labels
        cluster_labels: Human-readable cluster labels
    """
    print("  💾 Saving clusters to database...")
    
    # Clear existing clusters for this model
    with conn.cursor() as cur:
        cur.execute("DELETE FROM clusters WHERE model_name = %s", (MODEL_NAME,))
        cur.execute("DELETE FROM cluster_labels WHERE model_name = %s", (MODEL_NAME,))
    
    # Insert cluster assignments
    cluster_values = []
    for idx, label in enumerate(labels):
        if label == -1:
            continue
        
        uuid = uuid_map[str(idx)]
        cluster_values.append((uuid, MODEL_NAME, int(label)))
    
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO clusters (uuid, model_name, cluster_id)
            VALUES %s
            ON CONFLICT (uuid, model_name) DO UPDATE
            SET cluster_id = EXCLUDED.cluster_id
            """,
            cluster_values
        )
    
    # Insert cluster labels
    label_values = [
        (MODEL_NAME, cluster_id, label)
        for cluster_id, label in cluster_labels.items()
    ]
    
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO cluster_labels (model_name, cluster_id, label)
            VALUES %s
            ON CONFLICT (model_name, cluster_id) DO UPDATE
            SET label = EXCLUDED.label
            """,
            label_values
        )
    
    conn.commit()
    print(f"  ✅ Saved {len(cluster_values)} cluster assignments")
    print(f"  ✅ Saved {len(label_values)} cluster labels")

def main():
    """Main clustering process"""
    print("=" * 60)
    print("📊 BUILD TOPICS HDBSCAN - Topic Clustering")
    print("=" * 60)
    
    # Check if hdbscan is available
    if not HDBSCAN_AVAILABLE:
        print("\n❌ ERROR: hdbscan not installed")
        print("   This script is skipped in production (HF Spaces)")
        print("   To run locally: pip install hdbscan==0.8.38")
        sys.exit(0)  # Exit gracefully, not an error
    
    start_time = time.time()
    
    # Load index and mappings
    print("\n📂 Loading data...")
    embeddings, uuid_map = load_index_and_mappings()
    
    # Perform clustering
    print("\n🎯 Clustering...")
    labels = perform_clustering(embeddings)
    
    # Connect to database
    conn = get_db_connection()
    
    # Generate cluster labels
    print("\n🏷️  Generating labels...")
    cluster_labels = generate_cluster_labels(conn, uuid_map, labels)
    
    # Save to database
    print("\n💾 Saving to database...")
    save_clusters_to_db(conn, uuid_map, labels, cluster_labels)
    
    conn.close()
    
    elapsed_time = time.time() - start_time
    
    # Print summary
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    
    print("\n" + "=" * 60)
    print("✅ CLUSTERING COMPLETED")
    print("=" * 60)
    print(f"📊 Total documents: {len(labels)}")
    print(f"🎯 Clusters found: {n_clusters}")
    print(f"🔇 Noise points: {n_noise}")
    print(f"⏱️  Time: {elapsed_time:.2f}s")

if __name__ == "__main__":
    main()
