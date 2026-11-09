"""A síntese jurídica usa evidências e nunca inventa confirmação de fontes."""
from types import SimpleNamespace

from app.search import _official_source, _web_citations, answer_with_evidence


def test_official_url_allowlist():
    assert _official_source("https://www.planalto.gov.br/ccivil_03/")
    assert _official_source("https://portal.stf.jus.br/processos/")
    assert not _official_source("https://stf.jus.br.evil.example/processos")
    assert not _official_source("http://www.planalto.gov.br/")
    assert not _official_source("javascript:alert(1)")


def test_without_api_key_does_not_claim_no_law(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = answer_with_evidence("O que a Constituição diz sobre aborto?", [])
    assert result["ai_generated"] is False
    assert len(result["web_sources"]) == 4
    assert result["answer_mode"] == "guia_editorial"
    assert "ADPF 54" in result["answer"]
    assert len(result["web_sources"]) == 4


def test_no_evidence_fails_closed_without_web_opt_in(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.delenv("LEGAL_WEB_SEARCH_ENABLED", raising=False)
    result = answer_with_evidence("Quais são os direitos do inquilino?", [])
    assert result["ai_generated"] is False
    assert not result["web_sources"]
    assert "não permite concluir" in result["answer"]


def test_citations_extracted_only_from_verified_annotations():
    annotation = lambda url, title: SimpleNamespace(type="url_citation", url=url, title=title)
    response = SimpleNamespace(output=[SimpleNamespace(content=[
        SimpleNamespace(annotations=[
            annotation("https://www.planalto.gov.br/ccivil_03/", "Planalto"),
            annotation("https://evil.example/lei", "Não oficial"),
            annotation("https://www.planalto.gov.br/ccivil_03/", "Duplicado"),
        ])
    ])])
    assert _web_citations(response) == [
        {"url": "https://www.planalto.gov.br/ccivil_03/", "title": "Planalto", "kind": "oficial"},
        {"url": "https://evil.example/lei", "title": "Não oficial", "kind": "complementar"},
    ]


def test_hybrid_research_uses_web_and_exposes_sources(monkeypatch):
    import openai

    observed = {}
    citation = SimpleNamespace(
        type="url_citation",
        url="https://portal.stf.jus.br/processos/listarProcessos.asp?numeroProcesso=54",
        title="ADPF 54",
    )
    response = SimpleNamespace(
        output_text="A Constituição não contém disposição expressa sobre aborto.",
        output=[SimpleNamespace(content=[SimpleNamespace(annotations=[citation])])],
    )

    class FakeResponses:
        def create(self, **kwargs):
            observed.update(kwargs)
            return response

    class FakeClient:
        def __init__(self, **_kwargs):
            self.responses = FakeResponses()

    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LEGAL_WEB_SEARCH_ENABLED", "true")
    result = answer_with_evidence("O que a Constituição diz sobre aborto?", [])
    assert result["ai_generated"]
    assert result["answer_mode"] == "hibrido"
    assert result["web_sources"][0]["title"] == "ADPF 54"
    assert observed["tool_choice"] == "required"
    assert observed["tools"][0]["type"] == "web_search"
    assert observed["model"]


def test_hybrid_without_citations_does_not_publish_claims(monkeypatch):
    import openai

    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(output_text="Uma conclusão sem fontes.", output=[])

    class FakeClient:
        def __init__(self, **_kwargs):
            self.responses = FakeResponses()

    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LEGAL_WEB_SEARCH_ENABLED", "1")
    result = answer_with_evidence("teste", [])
    assert not result["ai_generated"]
    assert "não retornou referências verificáveis" in result["answer"]
