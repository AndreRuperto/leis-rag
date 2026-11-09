"""Teste real de PostgreSQL + indexação + busca + endpoint.

Habilitado somente se TEST_DATABASE_URL estiver definido.
"""
import os

import pytest
from fastapi.testclient import TestClient

from app.db import connection, init_db
from app.ingest import index_file
from app.main import app

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="Requer TEST_DATABASE_URL apontando para PostgreSQL com pgvector",
)


def test_ingest_and_query_postgresql(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.setenv("EMBEDDINGS_ENABLED", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    data_root = tmp_path / "dados"
    source = data_root / "federal" / "leis-ordinarias" / "2026" / "lei-teste.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        '---\ntitulo: "Lei de Exemplo do Teste"\ntipo: "Lei Ordinária"\n'
        'numero: "999001"\nfonte: "https://www.planalto.gov.br/"\n---\n'
        "# Lei de Exemplo do Teste\n\n"
        "Art. 1º O direito informacional é garantido nesta norma de teste.\n"
        "Art. 2º São permitidos documentos públicos.\n",
        encoding="utf-8",
    )

    db_path = "dados/federal/leis-ordinarias/2026/lei-teste.md"
    try:
        with connection() as conn:
            init_db(conn)
            state, count = index_file(conn, source, data_root)
            assert state == "indexed"
            assert count >= 2
            conn.commit()
            same_state, same_count = index_file(conn, source, data_root)
            assert (same_state, same_count) == ("unchanged", 0)

        with TestClient(app) as client:
            health = client.get("/api/health")
            assert health.status_code == 200
            results = client.get("/api/search", params={"q": "direito informacional"})
            assert results.status_code == 200
            sources = results.json()["sources"]
            assert any(item["number"] == "999001" for item in sources)
            assert any("Art. 1º" in item["article"] for item in sources)

            answer = client.post("/api/ask", json={"question": "direito informacional"})
            assert answer.status_code == 200
            assert answer.json()["sources"]
            assert "Encontrei" in answer.json()["answer"]
    finally:
        with connection() as conn:
            conn.execute("DELETE FROM laws WHERE path = %s", (db_path,))
