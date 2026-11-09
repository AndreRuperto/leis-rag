"""Conexão e esquema mínimo de pesquisa jurídica em PostgreSQL/pgvector."""
import os
from contextlib import contextmanager

import psycopg

DEFAULT_DATABASE_URL = "postgresql://leis:leis@localhost:5432/leis"


@contextmanager
def connection():
    conn = psycopg.connect(
        os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        connect_timeout=10,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(conn):
    """Extensão vector precisa estar instalada no servidor Postgres."""
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS laws (
            id BIGSERIAL PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            sphere TEXT NOT NULL,
            uf TEXT,
            law_type TEXT,
            number TEXT,
            law_date TEXT,
            status TEXT,
            text_version TEXT,
            source_url TEXT,
            checksum TEXT NOT NULL,
            indexed_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS passages (
            id BIGSERIAL PRIMARY KEY,
            law_id BIGINT NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
            ordinal INTEGER NOT NULL,
            label TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding vector(384),
            search_vector TSVECTOR GENERATED ALWAYS AS (
                to_tsvector('portuguese', coalesce(content, ''))
            ) STORED,
            UNIQUE (law_id, ordinal)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_passages_fts "
        "ON passages USING GIN (search_vector)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_laws_filters "
        "ON laws (sphere, uf, law_type)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_passages_law_id "
        "ON passages (law_id)"
    )
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_daily_usage (
            day DATE PRIMARY KEY,
            requests INTEGER NOT NULL DEFAULT 0
        )
    """)
    # O índice HNSW de vetores é criado manualmente após indexação em grande escala,
    # para evitar custo e memória elevados durante a importação inicial.
