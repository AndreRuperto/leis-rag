"""Testes do modo de pesquisa web do Leis RAG."""
from types import SimpleNamespace

from app.search import _source_kind, answer_with_evidence


def test_public_source_classification():
    assert _source_kind("https://portal.stf.jus.br") == "oficial"
    assert _source_kind("https://example.edu/paper") == "academica"
    assert _source_kind("https://example.com/article") == "complementar"
    assert _source_kind("http://example.com/article") is None


def test_web_research_when_database_is_empty(monkeypatch):
    import openai

    options = {}
    citation = SimpleNamespace(
        type="url_citation",
        url="https://www.planalto.gov.br/ccivil_03/",
        title="Constituição",
    )

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = self

        def create(self, **kwargs):
            options.update(kwargs)
            return SimpleNamespace(
                output_text="Resposta com fontes externas.",
                output=[SimpleNamespace(content=[
                    SimpleNamespace(annotations=[citation]),
                ])],
            )

    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    monkeypatch.setenv("OPENAI_API_KEY", "placeholder")
    monkeypatch.setenv("LEGAL_WEB_SEARCH_ENABLED", "1")
    result = answer_with_evidence(
        "O que a Constituição determina?", [], research_mode="auto"
    )
    assert result["web_search_performed"]
    assert result["ai_generated"]
    assert result["web_sources"][0]["kind"] == "oficial"
    assert options["tools"] == [{
        "type": "web_search", "search_context_size": "medium"
    }]
    assert options["tool_choice"] == "required"


def test_web_only_ignores_local_snippets(monkeypatch):
    import openai

    seen = {}

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = self

        def create(self, **kwargs):
            seen.update(kwargs)
            return SimpleNamespace(
                output_text="Resposta sobre a questão.",
                output=[SimpleNamespace(content=[SimpleNamespace(
                    annotations=[SimpleNamespace(
                        type="url_citation",
                        url="https://www.gov.br/pt-br/servicos",
                        title="Portal Gov",
                    )]
                )])],
            )

    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    monkeypatch.setenv("OPENAI_API_KEY", "placeholder")
    monkeypatch.setenv("LEGAL_WEB_SEARCH_ENABLED", "1")
    result = answer_with_evidence("Questão", [
        {"title": "Base local", "text": "Conteúdo não relevante"},
    ], research_mode="web")
    assert result["answer_mode"] == "pesquisa_web"
    assert "Conteúdo não relevante" not in seen["input"]
