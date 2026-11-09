"""API FastAPI e interface do Leis RAG."""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAIError
from pydantic import BaseModel, Field

from .db import connection, init_db
from .search import answer_with_evidence, search
from .usage_guard import ai_configured, web_configured, authorize_paid_ai


@asynccontextmanager
async def lifespan(_app):
    with connection() as conn:
        init_db(conn)
    yield


app = FastAPI(
    title="Leis RAG",
    description="Pesquisa jurídica com fontes auditáveis e RAG opcional.",
    version="0.1.0",
    lifespan=lifespan,
)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    sphere: str | None = None
    uf: str | None = Field(default=None, max_length=2)
    law_type: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=6, ge=1, le=12)
    research_mode: Literal["auto", "hybrid", "web", "acervo"] = "auto"


STATIC_DIR = Path(__file__).parent / "static"
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


@app.get("/favicon.svg", include_in_schema=False)
def favicon():
    return FileResponse(
        STATIC_DIR / "brand-icon.svg", media_type="image/svg+xml"
    )


@app.get("/")
def home():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/health")
def health():
    with connection() as conn:
        count = conn.execute("SELECT count(*) FROM laws").fetchone()[0]
    return {"status": "ok", "indexed_laws": count}


@app.get("/api/stats")
def stats():
    with connection() as conn:
        laws = conn.execute("SELECT count(*) FROM laws").fetchone()[0]
        passages = conn.execute("SELECT count(*) FROM passages").fetchone()[0]
    return {"laws": laws, "passages": passages}


@app.get("/api/capabilities")
def capabilities():
    """Informa capacidades sem revelar chaves ou senhas do provedor."""
    ai = ai_configured()
    return {
        "ai_available": ai,
        "ai_requires_access_code": ai,
        "official_web_search_available": web_configured(),
        "external_research_available": web_configured(),
        "editorial_guides_available": True,
        "default_research_mode": "auto",
    }


@app.get("/api/filter-options")
def filter_options():
    """Oferece tipos de norma realmente presentes na base indexada."""
    with connection() as conn:
        rows = conn.execute("""
            SELECT btrim(law_type) AS value, count(*) AS count
            FROM laws
            WHERE law_type IS NOT NULL AND btrim(law_type) <> ''
            GROUP BY btrim(law_type)
            ORDER BY count(*) DESC, btrim(law_type) ASC
            LIMIT 200
        """).fetchall()
    return {
        "law_types": [{"value": value, "count": count} for value, count in rows],
    }


@app.get("/api/search")
def search_api(
    q: str = Query(min_length=2, max_length=500),
    sphere: str | None = None,
    uf: str | None = Query(default=None, max_length=2),
    law_type: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=8, ge=1, le=20),
):
    items = search(q, sphere=sphere, uf=uf, law_type=law_type, limit=limit)
    return {"query": q, "count": len(items), "sources": items}


@app.post("/api/ask")
def ask_api(
    body: AskRequest,
    request: Request,
    access_token: str | None = Header(default=None, alias="X-Leis-Access-Token"),
):
    # Nunca chamar o provedor pago sem as duas credenciais de backend.
    # Caso o serviço não esteja configurado, guias gratuitos continuam
    # funcionando de forma transparente, sem simular pesquisa ao vivo.
    can_use_ai = ai_configured()
    if can_use_ai:
        authorize_paid_ai(request, access_token)

    sources = [] if body.research_mode == "web" else search(
        body.question, sphere=body.sphere, uf=body.uf,
        law_type=body.law_type, limit=body.limit,
    )
    try:
        evidence = answer_with_evidence(
            body.question, sources, research_mode=body.research_mode,
            allow_ai=can_use_ai,
        )
    except OpenAIError as exc:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível consultar o provedor de IA. A pesquisa segue disponível.",
        ) from exc
    return {"question": body.question, "sources": sources, **evidence}
