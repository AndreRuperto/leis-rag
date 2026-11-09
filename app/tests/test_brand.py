"""Identidade vetorial usada no cabeçalho e nos ícones do Leis RAG."""
from pathlib import Path
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient

from app.main import app

STATIC = Path(__file__).resolve().parents[1] / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
SVG_NS = "{http://www.w3.org/2000/svg}"


def test_brand_assets_are_valid_svg():
    for filename in ("brand-logo.svg", "brand-logo-dark.svg", "brand-icon.svg"):
        content = (STATIC / filename).read_text(encoding="utf-8")
        root = ET.fromstring(content)
        assert root.tag == SVG_NS + "svg"
        assert root.attrib["viewBox"]
        assert content.count("Leis RAG") >= 1
        assert "§" in content
        assert ("#5AD8B2" if filename == "brand-logo-dark.svg" else "#009f80") in content


def test_html_uses_logo_and_favicon():
    assert 'src="/assets/brand-logo.svg"' in HTML
    assert 'src="/assets/brand-logo-dark.svg"' in HTML
    assert '.brand-identity--dark{display:none}' in HTML
    assert ':root[data-theme="dark"] .brand-identity--dark{display:block}' in HTML
    assert 'background:#f8fafc;border-radius:12px;padding:4px 7px' not in HTML
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
    dark_logo = client.get("/assets/brand-logo-dark.svg")
    assert dark_logo.status_code == 200
    assert "image/svg+xml" in dark_logo.headers["content-type"]
