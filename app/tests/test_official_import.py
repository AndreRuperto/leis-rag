"""Validação da importação incremental de textos oficiais sem rede nem DB real."""
from pathlib import Path
from email.message import Message

import pytest

from app import official_import as importer
from app.ingest import parse_document, split_passages


def example_html(articles=85):
    paragraphs = "".join(
        f"<p><span>Art. {i}º</span> - Regra jurídica de exemplo número {i} "
        "sobre direitos e deveres da legislação brasileira.</p>"
        for i in range(1, articles + 1)
    )
    return f"""<html><head><meta charset="utf-8"/></head><body>
      <script>window.fake = "Art. 999";</script>
      <h2>Código de exemplo</h2>{paragraphs}
      <style>p{{display:block}}</style>
    </body></html>"""


def test_official_sources_are_https_and_approved():
    assert set(importer.SOURCES) == {"penal", "civil", "clt", "cdc"}
    for code, source in importer.SOURCES.items():
        assert importer._is_official(source["url"])
        assert source["title"] and source["number"]
        assert source["minimum_articles"] >= 55
    assert not importer._is_official("http://www.planalto.gov.br/page")
    assert not importer._is_official("https://www.planalto.gov.br.evil.example")
    assert not importer._is_official("https://example.com/page")


def test_extracts_article_lines_without_scripts():
    text = importer.extract_articles(example_html())
    assert "Art. 1º" in text
    assert "Art. 85º" in text
    assert "window.fake" not in text
    assert len([p for p in split_passages(text) if p[0].lower().startswith("art")]) == 85


def test_prepare_rejects_truncated_download(monkeypatch):
    monkeypatch.setattr(importer, "download_official", lambda url: example_html(6))
    with pytest.raises(ValueError, match="possivelmente incompleto"):
        importer.prepare("cdc", importer.SOURCES["cdc"])


def test_yaml_metadata_and_hash_are_stable():
    spec = importer.SOURCES["cdc"]
    text = importer.extract_articles(example_html(85))
    doc = importer.document(spec, text)
    assert doc == importer.document(spec, text)
    parsed = parse_document(doc, "federal/codigos/cdc.md")
    assert parsed["sphere"] == "federal"
    assert parsed["law_type"] == "Lei Ordinária"
    assert parsed["title"] == "Código de Defesa do Consumidor (CDC)"
    assert parsed["source_url"] == spec["url"]
    assert len(parsed["passages"]) >= 85
    assert parsed["status"] == "Vigência deve ser conferida no texto oficial"


def test_download_rejects_unapproved_host():
    with pytest.raises(ValueError, match="domínios oficiais"):
        importer.download_official("https://untrusted.example/codigo")


def test_dry_run_does_not_write_database(monkeypatch):
    monkeypatch.setattr(importer, "prepare", lambda code, spec: ("X" * 12000, 105))
    result = importer.run(["cdc"], dry_run=True)
    assert result == [{"code": "cdc", "status": "validated",
                       "articles": 105, "chars": 12000}]


def test_unsupported_code_is_rejected():
    with pytest.raises(ValueError, match="Fonte desconhecida"):
        importer.run(["unknown"], dry_run=True)
