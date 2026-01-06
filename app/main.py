# app/main.py
import threading
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.db import get_conn
from app.recommender import Recommender

# =========================
# APP
# =========================

app = FastAPI(title="UNAP Recommender API", version="2.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# RECOMMENDER (GLOBAL)
# =========================

rec = Recommender()

# =========================
# STARTUP
# =========================

@app.on_event("startup")
def startup():
    # carga en background (HF-safe)
    threading.Thread(target=rec.load, daemon=True).start()

# =========================
# MODELS
# =========================

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

# =========================
# ROOT / HEALTH
# =========================

@app.get("/")
def root():
    return {
        "service": "UNAP Recommender API",
        "status": "running",
        "model": rec.model_name,
        "device": rec.device,
        "ready": rec.ready,
        "endpoints": {
            "health": "/health",
            "recommend": "/recommend",
            "item": "/items/{uuid}",
            "topics_top": "/topics/top",
            "topics_cluster": "/topics/{cluster_id}",
        },
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "ready": rec.ready,
        "model": rec.model_name,
        "device": rec.device,
        "index_loaded": rec.ready,
        "index_count": len(rec.uuid_map) if rec.uuid_map else 0,
        "error": rec.load_error,
    }

# =========================
# DB HELPERS
# =========================

def fetch_items_by_uuids(uuids: List[str], model_name: str, include_abstract: bool):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                  i.uuid,
                  i.title,
                  i.url,
                  {"i.abstract_norm," if include_abstract else "NULL::text as abstract_norm,"}
                  i.university,
                  c.cluster_id,
                  cl.label
                FROM items i
                LEFT JOIN clusters c
                  ON c.uuid = i.uuid AND c.model_name = %s
                LEFT JOIN cluster_labels cl
                  ON cl.model_name = %s AND cl.cluster_id = c.cluster_id
                WHERE i.uuid = ANY(%s)
                """,
                (model_name, model_name, uuids),
            )
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


def fetch_same_topic_items(
    model_name: str,
    cluster_id: int,
    exclude_uuid: str,
    limit: int,
    include_abstract: bool,
):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT i.uuid, i.title, i.url,
                       {"i.abstract_norm," if include_abstract else "NULL::text as abstract_norm,"}
                       i.university,
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
                """,
                (model_name, model_name, cluster_id, exclude_uuid, limit),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "uuid": r[0],
            "title": r[1] or "",
            "url": r[2],
            "abstract_norm": r[3] if include_abstract else None,
            "university": r[4],
            "score": 0.0,
            "cluster_id": r[5],
            "label": r[6] or "(sin etiqueta)",
        }
        for r in rows
    ]

# =========================
# RECOMMEND
# =========================

@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    if not rec.ready:
        raise HTTPException(503, rec.load_error or "Modelo cargando")

    q = (req.text or "").strip()
    if not q:
        raise HTTPException(400, "text vacío")

    model_name = rec.model_name

    pairs = rec.search(q, k=req.k)
    uuids = [u for u, _ in pairs]

    enriched = fetch_items_by_uuids(
        uuids, model_name, include_abstract=req.include_abstract
    )

    results = []
    top1 = None

    for i, (uuid, score) in enumerate(pairs):
        it = enriched.get(uuid, {})
        row = {
            "uuid": uuid,
            "title": it.get("title", ""),
            "url": it.get("url"),
            "abstract_norm": it.get("abstract_norm"),
            "university": it.get("university"),
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
            "label": top1.get("label"),
        }

        if req.same_topic:
            same_topic = fetch_same_topic_items(
                model_name,
                inferred_topic["cluster_id"],
                top1["uuid"],
                req.same_topic_k,
                include_abstract=req.include_abstract,
            )

    return {
        "model_name": model_name,
        "k": req.k,
        "inferred_topic": inferred_topic,
        "results": results,
        "same_topic": same_topic,
    }

# =========================
# EXTRA ENDPOINTS (SIN CAMBIOS)
# =========================

@app.get("/items/{uuid}")
def get_item(uuid: str):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT uuid, title, url, abstract_norm,
                       date_issued, authors, advisors, keywords, university
                FROM items
                WHERE uuid = %s
                """,
                (uuid,),
            )
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
        "university": r[8],
    }
