#!/usr/bin/env python3
"""
Script para harvesting de repositorios UNAP/UNSA con soporte incremental.

Uso:
    python 01.harvest_multi.py --university UNAP --check-new
    python 01.harvest_multi.py --university UNSA --full-sync
"""
import argparse
import sys
import psycopg2
from datetime import datetime
import requests
from typing import List, Dict, Set

# Importar desde app
sys.path.insert(0, ".")
from app.db import get_conn

# URLs base de DSpace (ajusta según tu caso)
DSPACE_URLS = {
    "UNAP": "https://repositorio.unap.edu.pe/rest",
    "UNSA": "https://repositorio.unsa.edu.pe/rest"
}


def get_existing_uuids(conn, university: str) -> Set[str]:
    """Obtener UUIDs ya existentes en la base de datos."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT uuid FROM items WHERE university = %s",
            (university,)
        )
        return {row[0] for row in cur.fetchall()}


def fetch_items_from_dspace(university: str) -> List[Dict]:
    """
    Fetch items desde el API REST de DSpace.
    
    NOTA: Esta es una implementación de ejemplo.
    Debes adaptarla según el API real de UNAP/UNSA.
    """
    base_url = DSPACE_URLS.get(university)
    if not base_url:
        raise ValueError(f"Universidad no soportada: {university}")
    
    # Ejemplo de endpoint (ajusta según el API real)
    # Posibles endpoints: /items, /collections/{id}/items, etc.
    all_items = []
    
    try:
        # PLACEHOLDER: Implementa la lógica real de harvesting
        # Ejemplo con paginación:
        offset = 0
        limit = 100
        
        while True:
            response = requests.get(
                f"{base_url}/items",
                params={"offset": offset, "limit": limit},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            items = data.get("items", []) or data  # Ajustar según estructura
            
            if not items:
                break
            
            for item in items:
                # Extraer datos relevantes
                all_items.append({
                    "uuid": item.get("uuid") or item.get("id"),
                    "title": item.get("name") or item.get("title"),
                    "abstract": item.get("metadata", {}).get("dc.description.abstract"),
                    "url": item.get("link") or f"{base_url}/items/{item.get('uuid')}",
                    "date": item.get("lastModified") or datetime.now().isoformat(),
                })
            
            offset += limit
            
            # Evitar loops infinitos
            if len(items) < limit:
                break
    
    except requests.RequestException as e:
        print(f"❌ Error fetching from {university}: {e}")
        return []
    
    return all_items


def insert_new_items(conn, university: str, items: List[Dict]) -> int:
    """Insertar nuevos items en la base de datos."""
    inserted = 0
    
    with conn.cursor() as cur:
        for item in items:
            try:
                cur.execute(
                    """
                    INSERT INTO items (uuid, title, abstract_norm, url, university, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (uuid) DO NOTHING
                    """,
                    (
                        item["uuid"],
                        item["title"],
                        item["abstract"],
                        item["url"],
                        university,
                        datetime.now()
                    )
                )
                if cur.rowcount > 0:
                    inserted += 1
            except psycopg2.Error as e:
                print(f"⚠️  Error insertando {item['uuid']}: {e}")
                conn.rollback()
                continue
    
    conn.commit()
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Harvest UNAP/UNSA repositories")
    parser.add_argument(
        "--university",
        choices=["UNAP", "UNSA"],
        required=True,
        help="Universidad a procesar"
    )
    parser.add_argument(
        "--check-new",
        action="store_true",
        help="Solo verificar nuevos items (para CI/CD)"
    )
    parser.add_argument(
        "--full-sync",
        action="store_true",
        help="Sincronización completa (no incremental)"
    )
    
    args = parser.parse_args()
    
    print(f"🔍 Harvesting {args.university}...")
    
    # Conectar a la base de datos
    conn = get_conn()
    
    try:
        # Obtener items existentes
        existing = get_existing_uuids(conn, args.university)
        print(f"📊 Items existentes: {len(existing)}")
        
        # Fetch items desde DSpace
        all_items = fetch_items_from_dspace(args.university)
        print(f"📥 Items obtenidos del repositorio: {len(all_items)}")
        
        # Filtrar nuevos items
        new_items = [
            item for item in all_items
            if item["uuid"] not in existing
        ]
        print(f"✨ Nuevos items encontrados: {len(new_items)}")
        
        # Si solo queremos verificar (para CI/CD)
        if args.check_new:
            # Escribir count para GitHub Actions
            with open("/tmp/new_items_count.txt", "w") as f:
                f.write(str(len(new_items)))
            
            if len(new_items) == 0:
                print("✅ No hay nuevos items")
                return 0
            else:
                print(f"🆕 Se encontraron {len(new_items)} nuevos items")
                # Mostrar primeros 5 títulos
                for item in new_items[:5]:
                    print(f"  - {item['title'][:80]}")
                return 0
        
        # Insertar nuevos items
        if new_items:
            inserted = insert_new_items(conn, args.university, new_items)
            print(f"✅ Insertados {inserted} nuevos items")
        else:
            print("ℹ️  No hay nuevos items para insertar")
    
    finally:
        conn.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
