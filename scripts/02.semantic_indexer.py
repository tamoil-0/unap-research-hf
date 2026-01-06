#!/usr/bin/env python3
"""
02. Semantic Indexer - FAISS Index Builder
Builds/updates semantic search index using sentence-transformers and FAISS.
Handles incremental updates efficiently.
"""

import os
import json
import time
import numpy as np
import faiss
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
import psycopg2

# Configuration
MODEL_NAME = "BAAI/bge-m3"
MODEL_DIR = "models_semantic"
INDEX_PATH = os.path.join(MODEL_DIR, "faiss.index")
UUID_MAP_PATH = os.path.join(MODEL_DIR, "uuid_map.json")
META_PATH = os.path.join(MODEL_DIR, "meta.json")

os.makedirs(MODEL_DIR, exist_ok=True)

def get_db_connection():
    """Get PostgreSQL connection"""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set")
    return psycopg2.connect(database_url)

def load_existing_index() -> Tuple[faiss.Index, Dict[int, str], set]:
    """
    Load existing FAISS index and mappings
    
    Returns:
        Tuple of (index, uuid_map, indexed_uuids)
    """
    if not os.path.exists(INDEX_PATH):
        print("  ℹ️ No existing index found, creating new one")
        return None, {}, set()
    
    print("  📂 Loading existing index...")
    index = faiss.read_index(INDEX_PATH)
    
    with open(UUID_MAP_PATH, "r") as f:
        uuid_map = json.load(f)
    
    indexed_uuids = set(uuid_map.values())
    
    print(f"  ✓ Loaded index with {index.ntotal} vectors")
    return index, uuid_map, indexed_uuids

def fetch_items_to_index(conn, indexed_uuids: set) -> List[Dict]:
    """
    Fetch items that need indexing
    
    Args:
        conn: Database connection
        indexed_uuids: Set of already indexed UUIDs
    
    Returns:
        List of items to index
    """
    with conn.cursor() as cur:
        if indexed_uuids:
            cur.execute(
                """
                SELECT uuid, title_norm, abstract_norm 
                FROM items 
                WHERE uuid NOT IN %s
                AND abstract_norm IS NOT NULL
                AND abstract_norm != ''
                """,
                (tuple(indexed_uuids),)
            )
        else:
            cur.execute(
                """
                SELECT uuid, title_norm, abstract_norm 
                FROM items
                WHERE abstract_norm IS NOT NULL
                AND abstract_norm != ''
                """
            )
        
        rows = cur.fetchall()
    
    items = [
        {
            "uuid": row[0],
            "title": row[1] or "",
            "abstract": row[2] or ""
        }
        for row in rows
    ]
    
    return items

def build_or_update_index(
    model: SentenceTransformer,
    items: List[Dict],
    existing_index: faiss.Index = None,
    existing_uuid_map: Dict[int, str] = None
) -> Tuple[faiss.Index, Dict[int, str]]:
    """
    Build new index or update existing one
    
    Args:
        model: Sentence transformer model
        items: Items to index
        existing_index: Existing FAISS index (optional)
        existing_uuid_map: Existing UUID mapping (optional)
    
    Returns:
        Tuple of (updated_index, updated_uuid_map)
    """
    if not items:
        print("  ℹ️ No new items to index")
        return existing_index, existing_uuid_map
    
    print(f"  🧠 Encoding {len(items)} items...")
    
    # Prepare texts (title + abstract)
    texts = [f"{item['title']} {item['abstract']}" for item in items]
    
    # Encode in batches
    batch_size = 32
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = model.encode(
            batch,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=batch_size
        )
        embeddings.append(batch_embeddings)
        
        if (i // batch_size + 1) % 10 == 0:
            print(f"    ✓ Processed {i + len(batch)}/{len(texts)} items")
    
    embeddings = np.vstack(embeddings).astype("float32")
    print(f"  ✅ Embeddings shape: {embeddings.shape}")
    
    # Create or update index
    dim = embeddings.shape[1]
    
    if existing_index is None:
        # Create new index
        print("  🔧 Creating new FAISS index...")
        index = faiss.IndexFlatIP(dim)  # Inner product (cosine similarity)
        uuid_map = {}
        start_idx = 0
    else:
        # Use existing index
        print("  🔧 Updating existing FAISS index...")
        index = existing_index
        uuid_map = existing_uuid_map.copy()
        start_idx = index.ntotal
    
    # Add new vectors
    index.add(embeddings)
    
    # Update UUID mapping
    for i, item in enumerate(items):
        uuid_map[str(start_idx + i)] = item["uuid"]
    
    print(f"  ✅ Index now contains {index.ntotal} vectors")
    return index, uuid_map

def save_index(index: faiss.Index, uuid_map: Dict[int, str]):
    """Save FAISS index and mappings"""
    print("  💾 Saving index...")
    
    faiss.write_index(index, INDEX_PATH)
    
    with open(UUID_MAP_PATH, "w") as f:
        json.dump(uuid_map, f, indent=2)
    
    # Save metadata
    meta = {
        "model": MODEL_NAME,
        "dimension": index.d,
        "total_vectors": index.ntotal,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }
    
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)
    
    print(f"  ✅ Saved: {INDEX_PATH}")
    print(f"  ✅ Saved: {UUID_MAP_PATH}")
    print(f"  ✅ Saved: {META_PATH}")

def main():
    """Main indexing process"""
    print("=" * 60)
    print("🧠 SEMANTIC INDEXER - FAISS Index Builder")
    print("=" * 60)
    
    start_time = time.time()
    
    # Load model
    print(f"\n📥 Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print(f"✅ Model loaded (dim: {model.get_sentence_embedding_dimension()})")
    
    # Load existing index
    print("\n📂 Loading existing index...")
    existing_index, existing_uuid_map, indexed_uuids = load_existing_index()
    
    # Connect to database and fetch new items
    print("\n🔍 Fetching items to index...")
    conn = get_db_connection()
    items_to_index = fetch_items_to_index(conn, indexed_uuids)
    conn.close()
    
    print(f"  ✓ Found {len(items_to_index)} new items to index")
    
    if not items_to_index and existing_index is not None:
        print("\n✅ Index is up to date, nothing to do")
        return
    
    # Build/update index
    print("\n🔧 Building/updating index...")
    index, uuid_map = build_or_update_index(
        model, items_to_index, existing_index, existing_uuid_map
    )
    
    # Save index
    print("\n💾 Saving index...")
    save_index(index, uuid_map)
    
    elapsed_time = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("✅ INDEXING COMPLETED")
    print("=" * 60)
    print(f"📊 Total vectors: {index.ntotal}")
    print(f"🆕 New vectors: {len(items_to_index)}")
    print(f"⏱️  Time: {elapsed_time:.2f}s")

if __name__ == "__main__":
    main()
