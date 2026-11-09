"""Cobertura da página Sobre, do rodapé e da navegação interna."""
from html.parser import HTMLParser
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


STATIC = Path(__file__).resolve().parents[1] / "static"
HOME = (STATIC / "index.html").read_text(encoding="utf-8")
ABOUT = (STATIC / "sobre.html").read_text(encoding="utf-8")


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs)
        if tag == "img":
            self.images.append(attrs)


def test_about_route_and_html():
    client = TestClient(app)
    for route in ("/sobre", "/sobre/"):
        response = client.get(route)
        assert response.status_code == 200
        assert 'text/html' in response.headers["content-type"]
        assert "Direito brasileiro, informação rastreável." in response.text
        assert "Pesquisa externa opcional" in response.text
        assert "Limitações e uso responsável" in response.text


def test_home_about_navigation_and_social_links():
    tree = LinkParser()
    tree.feed(HOME)
    assert '/sobre' in [link.get("href") for link in tree.links]
    assert 'https://br.linkedin.com/in/andrerup' in [link.get("href") for link in tree.links]
    assert 'https://github.com/AndreRuperto/leis-rag' in [link.get("href") for link in tree.links]
    assert 'https://github.com/AndreRuperto/leis-rag/issues' in [link.get("href") for link in tree.links]
    assert '<nav class="footer-column" aria-label="Redes e desenvolvimento">' in HOME
    assert '.footer-inner{grid-template-columns:1fr;padding:25px 16px}' in HOME


def test_about_page_sections_and_sources():
    tree = LinkParser()
    tree.feed(ABOUT)
    assert len(tree.ids) == len(set(tree.ids))
    for section in ("metodologia", "fontes", "limites", "desenvolvimento"):
        assert section in tree.ids
    for link in tree.links:
        href = link.get("href", "")
        if href.startswith("#"):
            assert href[1:] in tree.ids
        if link.get("target") == "_blank":
            assert "noopener" in link.get("rel", "")
    assert "ctresb/leis" in ABOUT
    assert "não significa que ele já foi importado" in ABOUT
    assert "não é parecer jurídico" in ABOUT
    assert 'href="/assets/brand-logo-dark.svg"' not in ABOUT
    assert any(image.get("src") == "/assets/brand-logo-dark.svg" for image in tree.images)


def test_about_page_theme_persists():
    assert 'localStorage.getItem("leisrag-theme")' in ABOUT
    assert 'localStorage.setItem("leisrag-theme",next)' in ABOUT
    assert 'data-theme="dark"' in ABOUT
    assert "aria-pressed" in ABOUT
