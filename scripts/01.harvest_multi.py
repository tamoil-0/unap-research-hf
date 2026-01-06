#!/usr/bin/env python3
"""
01. Harvest Multi - DSpace Repository Harvester
Harvests metadata from UNAP and UNSA DSpace repositories.
Incrementally adds new items to PostgreSQL database.
"""

import os
import json
import time
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import execute_values

# Configuration
REPOSITORIES = {
    "UNAP": {
        "base_url": "http://repositorio.unap.edu.pe",
        "api_endpoint": "/rest/items",
        "university": "UNAP"
    },
    "UNSA": {
        "base_url": "http://repositorio.unsa.edu.pe",
        "api_endpoint": "/rest/items",
        "university": "UNSA"
    }
}

OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_db_connection():
    """Get PostgreSQL connection from environment variable"""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(database_url)

def harvest_repository(repo_name: str, config: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Harvest items from a DSpace repository
    
    Args:
        repo_name: Repository name (UNAP/UNSA)
        config: Repository configuration
    
    Returns:
        List of harvested items
    """
    print(f"\n🔍 Harvesting {repo_name}...")
    
    base_url = config["base_url"]
    api_endpoint = config["api_endpoint"]
    university = config["university"]
    
    items = []
    offset = 0
    limit = 100
    
    while True:
        url = f"{base_url}{api_endpoint}?offset={offset}&limit={limit}"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            batch = response.json()
            
            if not batch:
                break
            
            for item in batch:
                # Extract metadata
                metadata = {}
                for field in item.get("metadata", []):
                    key = field.get("key", "")
                    value = field.get("value", "")
                    
                    if key not in metadata:
                        metadata[key] = []
                    metadata[key].append(value)
                
                # Build structured item
                structured_item = {
                    "uuid": item.get("uuid"),
                    "handle": item.get("handle"),
                    "title": " ".join(metadata.get("dc.title", [])),
                    "abstract": " ".join(metadata.get("dc.description.abstract", [])),
                    "authors": metadata.get("dc.contributor.author", []),
                    "subjects": metadata.get("dc.subject", []),
                    "date": metadata.get("dc.date.issued", [None])[0],
                    "url": f"{base_url}/handle/{item.get('handle', '')}",
                    "university": university
                }
                
                items.append(structured_item)
            
            print(f"  ✓ Processed {len(items)} items (offset: {offset})")
            
            offset += limit
            time.sleep(1)  # Be nice to the server
            
        except Exception as e:
            print(f"  ⚠️ Error at offset {offset}: {e}")
            break
    
    print(f"✅ {repo_name}: {len(items)} items harvested")
    return items

def get_existing_uuids(conn) -> set:
    """Get set of existing UUIDs from database"""
    with conn.cursor() as cur:
        cur.execute("SELECT uuid FROM items")
        return {row[0] for row in cur.fetchall()}

def insert_new_items(conn, items: List[Dict[str, Any]], existing_uuids: set) -> int:
    """
    Insert new items into database
    
    Args:
        conn: Database connection
        items: List of items to insert
        existing_uuids: Set of existing UUIDs
    
    Returns:
        Number of new items inserted
    """
    new_items = [item for item in items if item["uuid"] not in existing_uuids]
    
    if not new_items:
        print("  ℹ️ No new items to insert")
        return 0
    
    # Prepare data for insertion
    values = []
    for item in new_items:
        # Normalize text (simple version)
        title_norm = item["title"].lower().strip()
        abstract_norm = item["abstract"].lower().strip()
        
        values.append((
            item["uuid"],
            item["handle"],
            item["title"],
            title_norm,
            item["abstract"],
            abstract_norm,
            json.dumps(item["authors"]),
            json.dumps(item["subjects"]),
            item["date"],
            item["url"],
            item["university"]
        ))
    
    # Insert into database
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO items (
                uuid, handle, title, title_norm, abstract, abstract_norm,
                authors, subjects, date_issued, url, university
            ) VALUES %s
            ON CONFLICT (uuid) DO NOTHING
            """,
            values
        )
    
    conn.commit()
    print(f"  ✅ Inserted {len(new_items)} new items")
    return len(new_items)

def main():
    """Main harvesting process"""
    print("=" * 60)
    print("🌾 HARVEST MULTI - DSpace Repository Harvester")
    print("=" * 60)
    
    start_time = time.time()
    
    # Connect to database
    conn = get_db_connection()
    existing_uuids = get_existing_uuids(conn)
    print(f"📊 Existing items in DB: {len(existing_uuids)}")
    
    # Harvest each repository
    all_items = []
    total_new = 0
    
    for repo_name, config in REPOSITORIES.items():
        items = harvest_repository(repo_name, config)
        all_items.extend(items)
        
        new_count = insert_new_items(conn, items, existing_uuids)
        total_new += new_count
        existing_uuids.update(item["uuid"] for item in items)
    
    conn.close()
    
    # Save summary
    elapsed_time = time.time() - start_time
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "elapsed_seconds": round(elapsed_time, 2),
        "total_harvested": len(all_items),
        "new_items": total_new,
        "repositories": {
            repo: len([i for i in all_items if i["university"] == config["university"]])
            for repo, config in REPOSITORIES.items()
        }
    }
    
    summary_path = os.path.join(OUTPUT_DIR, "harvest_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("✅ HARVEST COMPLETED")
    print("=" * 60)
    print(f"📊 Total harvested: {len(all_items)}")
    print(f"🆕 New items: {total_new}")
    print(f"⏱️  Time: {elapsed_time:.2f}s")
    print(f"💾 Summary: {summary_path}")

if __name__ == "__main__":
    main()
