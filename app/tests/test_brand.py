"""Identidade vetorial usada no cabeçalho e nos ícones do Leis RAG."""
from pathlib import Path
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient

from app.main import app

STATIC = Path(__file__).resolve().parents[1] / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
SVG_NS = "{http://www.w3.org/2000/svg}"


def test_brand_assets_are_valid_svg():
    for filename in ("brand-logo.svg", "brand-icon.svg"):
        content = (STATIC / filename).read_text(encoding="utf-8")
        root = ET.fromstring(content)
        assert root.tag == SVG_NS + "svg"
        assert root.attrib["viewBox"]
        assert content.count("Leis RAG") >= 1
        assert "§" in content
        assert "#009f80" in content


def test_html_uses_logo_and_favicon():
    assert 'src="/assets/brand-logo.svg"' in HTML
    assert 'href="/favicon.svg"' in HTML
    assert "alt=\"Leis RAG — Pesquisa Jurídica\"" in HTML
    assert "brand-identity" in HTML
    assert 'class="emblem"' not in HTML


def test_branded_static_routes():
    # Não precisa entrar no ciclo de inicialização do banco para servir SVG.
    client = TestClient(app)
    icon = client.get("/favicon.svg")
    assert icon.status_code == 200
    assert "image/svg+xml" in icon.headers["content-type"]
    assert b"<svg" in icon.content
    logo = client.get("/assets/brand-logo.svg")
    assert logo.status_code == 200
    assert "image/svg+xml" in logo.headers["content-type"]
