"""Guias revisados: reconhecem perguntas temáticas sem simular uso de IA."""
from app.legal_guides import editorial_answer, match_guide, normalize
from app.search import answer_with_evidence


def test_normalizes_portuguese_and_matches_synonyms():
    assert normalize(" Interrupção gestacional ") == "interrupcao gestacional"
    assert match_guide("O que a Constituição fala sobre Aborto?")
    assert match_guide("Dúvidas sobre interrupção da gravidez")
    assert match_guide("Abortamento previsto em lei")
    assert match_guide("Meu contrato de locação") is None


def test_guide_includes_distinct_norms_and_official_references():
    answer = editorial_answer("O que a Constituição fala sobre aborto?")
    assert answer["answer_mode"] == "guia_editorial"
    assert answer["ai_generated"] is False
    assert "não contém uma regra específica" in answer["answer"]
    assert "art. 128" in answer["answer"]
    assert "ADPF 54" in answer["answer"]
    assert len(answer["web_sources"]) == 4
    assert all(item["url"].startswith("https://") for item in answer["web_sources"])
    assert answer["references_checked_at"] == "2026-11-09"


def test_hybrid_without_web_returns_verified_guide_even_with_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "placeholder")
    monkeypatch.setenv("LEGAL_WEB_SEARCH_ENABLED", "0")
    result = answer_with_evidence("O que a Constituição fala sobre aborto?", [])
    assert result["answer_mode"] == "guia_editorial"
    assert not result["ai_generated"]
    assert result["web_sources"]


def test_acervo_only_mode_does_not_implicitly_use_editorial_guide(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "placeholder")
    monkeypatch.setenv("LEGAL_WEB_SEARCH_ENABLED", "0")
    result = answer_with_evidence(
        "O que a Constituição fala sobre aborto?", [], research_mode="acervo"
    )
    assert result["answer_mode"] == "acervo"
    assert not result["web_sources"]


def test_without_api_key_editorial_guide_still_works(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LEGAL_WEB_SEARCH_ENABLED", raising=False)
    result = answer_with_evidence("O que a Constituição diz sobre aborto?", [])
    assert result["answer_mode"] == "guia_editorial"
