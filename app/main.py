#app/main.py
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.db import get_conn
from app.recommender import Recommender

app = FastAPI(title="UNAP Recommender API", version="2.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

rec = Recommender()


class RecommendRequest(BaseModel):
    text: str
    k: int = 10
    include_abstract: bool = True
    same_topic: bool = True
    same_topic_k: int = 10


class RecommendItem(BaseModel):
    uuid: str
    title: str
    url: Optional[str] = None
    score: float
    cluster_id: Optional[int] = None
    label: Optional[str] = None
    abstract_norm: Optional[str] = None
    university: Optional[str] = None 


class RecommendResponse(BaseModel):
    model_name: str
    k: int
    inferred_topic: Optional[Dict[str, Any]] = None
    results: List[RecommendItem]
    same_topic: Optional[List[RecommendItem]] = None


@app.on_event("startup")
def startup():
    import threading
    threading.Thread(target=rec.load, daemon=True).start()


@app.get("/health")
def health():
    return {"ok": True, "model": rec.model_name, "device": rec.device}


def fetch_items_by_uuids(uuids: List[str], model_name: str, include_abstract: bool):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT
                  i.uuid,
                  i.title,
                  i.url,
                  {"i.abstract_norm," if include_abstract else "NULL::text as abstract_norm,"}
                  i.university,               -- ✅ NUEVO
                  c.cluster_id,
                  cl.label
                FROM items i
                LEFT JOIN clusters c
                  ON c.uuid = i.uuid AND c.model_name = %s
                LEFT JOIN cluster_labels cl
                  ON cl.model_name = %s AND cl.cluster_id = c.cluster_id
                WHERE i.uuid = ANY(%s)
            """, (model_name, model_name, uuids))
            rows = cur.fetchall()
    finally:
        conn.close()

    out = {}
    for r in rows:
        out[r[0]] = {
            "uuid": r[0],
            "title": r[1] or "",
            "url": r[2],
            "abstract_norm": r[3] if include_abstract else None,
            "university": r[4],           
            "cluster_id": r[5],
            "label": r[6] or "(sin etiqueta)",
        }
    return out


def fetch_same_topic_items(model_name: str, cluster_id: int, exclude_uuid: str, limit: int, include_abstract: bool):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT i.uuid, i.title, i.url,
                       {"i.abstract_norm," if include_abstract else "NULL::text as abstract_norm,"}
                       i.university,            -- ✅ NUEVO
                       c.cluster_id, cl.label
                FROM clusters c
                JOIN items i ON i.uuid = c.uuid
                LEFT JOIN cluster_labels cl
                  ON cl.model_name = %s AND cl.cluster_id = c.cluster_id
                WHERE c.model_name = %s
                  AND c.cluster_id = %s
                  AND i.uuid <> %s
                ORDER BY i.updated_at DESC
                LIMIT %s
            """, (model_name, model_name, int(cluster_id), exclude_uuid, int(limit)))
            rows = cur.fetchall()
    finally:
        conn.close()

    return [{
        "uuid": r[0],
        "title": r[1] or "",
        "url": r[2],
        "abstract_norm": r[3] if include_abstract else None,
        "university": r[4],              # ✅ NUEVO
        "score": 0.0,
        "cluster_id": r[5],
        "label": r[6] or "(sin etiqueta)",
    } for r in rows]


@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    if rec.model is None or rec.index is None:
        raise HTTPException(503, "Modelo cargando, intente en unos segundos")

    q = (req.text or "").strip()
    if not q:
        raise HTTPException(400, "text vacío")

    model_name = rec.model_name

    pairs = rec.search(q, k=req.k)  
    uuids = [u for u, _ in pairs]
    enriched = fetch_items_by_uuids(uuids, model_name, include_abstract=req.include_abstract)

    results = []
    top1 = None

    for i, (uuid, score) in enumerate(pairs):
        it = enriched.get(uuid, {})
        row = {
            "uuid": uuid,
            "title": (it.get("title") or "").strip(),
            "url": it.get("url"),
            "abstract_norm": it.get("abstract_norm"),
            "university": it.get("university"),      # ✅ NUEVO
            "score": float(score),
            "cluster_id": it.get("cluster_id"),
            "label": it.get("label") or "(sin etiqueta)",
        }
        results.append(row)
        if i == 0:
            top1 = row

    inferred_topic = None
    same_topic = None
    if top1 and top1.get("cluster_id") is not None and int(top1["cluster_id"]) != -1:
        inferred_topic = {
            "cluster_id": int(top1["cluster_id"]),
            "label": top1.get("label") or "(sin etiqueta)"
        }

        if req.same_topic:
            same_topic = fetch_same_topic_items(
                model_name,
                int(top1["cluster_id"]),
                top1["uuid"],
                req.same_topic_k,
                include_abstract=req.include_abstract
            )

    return {
        "model_name": model_name,
        "k": req.k,
        "inferred_topic": inferred_topic,
        "results": results,
        "same_topic": same_topic,
    }


@app.get("/items/{uuid}")
def get_item(uuid: str):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT uuid, title, url, abstract_norm, date_issued, authors, advisors, keywords, university
                FROM items
                WHERE uuid = %s
            """, (uuid,))
            r = cur.fetchone()
    finally:
        conn.close()

    if not r:
        raise HTTPException(404, "uuid no encontrado")

    return {
        "uuid": r[0],
        "title": r[1],
        "url": r[2],
        "abstract_norm": r[3],
        "date_issued": r[4],
        "authors": r[5],
        "advisors": r[6],
        "keywords": r[7],
        "university": r[8],   # ✅ NUEVO
    }


@app.get("/topics/top")
def topics_top(n: int = 200):
    model_name = rec.model_name
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cluster_id, label, size, keywords
                FROM cluster_labels
                WHERE model_name = %s
                ORDER BY size DESC
                LIMIT %s
            """, (model_name, int(n)))
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {"cluster_id": r[0], "label": r[1], "size": r[2], "keywords": r[3]}
        for r in rows
    ]


@app.get("/topics/{cluster_id}")
def topics_cluster(cluster_id: int, limit: int = 80):
    model_name = rec.model_name
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT i.uuid, i.title, i.url, i.abstract_norm, i.university
                FROM clusters c
                JOIN items i ON i.uuid = c.uuid
                WHERE c.model_name = %s AND c.cluster_id = %s
                ORDER BY i.updated_at DESC
                LIMIT %s
            """, (model_name, int(cluster_id), int(limit)))
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {"uuid": r[0], "title": r[1], "url": r[2], "abstract_norm": r[3], "university": r[4]}
        for r in rows
    ]
