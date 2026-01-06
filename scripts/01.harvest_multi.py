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
        "url": "https://repositorio.unap.edu.pe/server/api/discover/search/objects",
        "base_url": "https://repositorio.unap.edu.pe",
        "university": "UNAP"
    },
    "UNSA": {
        "url": "https://repositorio.unsa.edu.pe/server/api/discover/search/objects",
        "base_url": "https://repositorio.unsa.edu.pe",
        "university": "UNSA"
    }
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ResearchHarvester/1.0)",
    "Accept": "application/json",
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
    Harvest items from a DSpace 7+ repository
    
    Args:
        repo_name: Repository name (UNAP/UNSA)
        config: Repository configuration
    
    Returns:
        List of harvested items
    """
    print(f"\n🔍 Harvesting {repo_name}...")
    
    api_url = config["url"]
    base_url = config["base_url"]
    university = config["university"]
    
    items = []
    page = 0
    size = 100
    
    while True:
        params = {
            "page": page,
            "size": size,
            "sort": "dc.date.accessioned,DESC"
        }
        
        try:
            response = requests.get(api_url, params=params, headers=HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # DSpace 7+ structure: data._embedded.searchResult._embedded.objects
            search_result = data.get("_embedded", {}).get("searchResult", {})
            objects = search_result.get("_embedded", {}).get("objects", [])
            
            if not objects:
                break
            
            for obj in objects:
                item_data = obj.get("_embedded", {}).get("indexableObject", {})
                
                # Extract metadata
                metadata = item_data.get("metadata", {})
                
                # Helper to get first value from metadata
                def get_first(key):
                    values = metadata.get(key, [])
                    return values[0].get("value", "") if values else ""
                
                # Helper to get all values from metadata
                def get_all(key):
                    values = metadata.get(key, [])
                    return [v.get("value", "") for v in values]
                
                # Build structured item
                structured_item = {
                    "uuid": item_data.get("uuid"),
                    "handle": item_data.get("handle"),
                    "title": get_first("dc.title"),
                    "abstract": get_first("dc.description.abstract") or get_first("dc.description"),
                    "authors": get_all("dc.contributor.author"),
                    "subjects": get_all("dc.subject"),
                    "date": get_first("dc.date.issued") or get_first("dc.date.accessioned"),
                    "url": f"{base_url}/handle/{item_data.get('handle', '')}",
                    "university": university
                }
                
                items.append(structured_item)
            
            print(f"  ✓ Processed {len(items)} items (page: {page})")
            
            # Check if there are more pages
            page_info = data.get("page", {})
            total_pages = page_info.get("totalPages", 1)
            
            page += 1
            if page >= total_pages:
                break
            
            time.sleep(1)  # Be nice to the server
            
        except Exception as e:
            print(f"  ⚠️ Error at page {page}: {e}")
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
