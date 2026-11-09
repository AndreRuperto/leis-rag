"""Verificações estáticas de identidade visual, acessibilidade e JavaScript da UI."""
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess

import pytest


PAGE = Path(__file__).resolve().parents[1] / "static" / "index.html"
HTML = PAGE.read_text(encoding="utf-8")


class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.labels = []
        self.refs = []
        self.landmarks = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "label" and values.get("for"):
            self.labels.append(values["for"])
        if tag == "a" and values.get("href", "").startswith("#"):
            self.refs.append(values["href"][1:])
        if tag in {"main", "header", "footer", "nav", "aside"}:
            self.landmarks.append(tag)


def palette(selector):
    pattern = re.escape(selector) + r"\s*\{([^}]+)\}"
    match = re.search(pattern, HTML)
    assert match, f"Paleta ausente: {selector}"
    return dict(
        (name, value.lower()) for name, value in
        re.findall(r"(--[\w-]+)\s*:\s*(#[a-fA-F0-9]{6})\b", match.group(1))
    )


def rgb(hex_color):
    return [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def luminance(hex_color):
    parts = [x / 12.92 if x <= 0.04045 else ((x + .055) / 1.055) ** 2.4
             for x in rgb(hex_color)]
    return sum(x * weight for x, weight in zip(parts, (.2126, .7152, .0722)))


def contrast(a, b):
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + .05) / (dark + .05)


def test_structure_and_labels():
    tree = Structure()
    tree.feed(HTML)
    assert len(tree.ids) == len(set(tree.ids)), "IDs de HTML repetidos"
    assert set(tree.labels).issubset(set(tree.ids)), "Label sem controle"
    assert set(tree.refs).issubset(set(tree.ids)), "Link âncora sem destino"
    assert {"header", "main", "aside", "nav", "footer"}.issubset(set(tree.landmarks))


def test_main_ui_has_genuine_controls():
    for item in ('id="form"', 'id="question"', 'id="theme-toggle"',
                 'id="tab-search"', 'id="tab-ask"', 'id="sphere"',
                 'id="law_type"', 'id="uf"', 'id="result"'):
        assert item in HTML
    assert 'role="tablist"' in HTML
    assert 'aria-selected="true"' in HTML
    assert 'localStorage.setItem("leisrag-theme"' in HTML
    assert 'Situação informada no acervo:' in HTML
    assert 'A ausência de resultados não significa que a norma não exista' in HTML
    assert 'class="site-footer"' in HTML
    assert '@media(prefers-reduced-motion:reduce)' in HTML


@pytest.mark.parametrize("theme,primary_text", [
    (":root", "#ffffff"),
    (':root[data-theme="dark"]', "#09251d"),
])
def test_wcg_aa_text_and_controls(theme, primary_text):
    colors = palette(theme)
    assert contrast(colors["--ink"], colors["--surface"]) >= 4.5
    assert contrast(colors["--muted"], colors["--surface"]) >= 4.5
    assert contrast(colors["--link"], colors["--surface"]) >= 4.5
    assert contrast(primary_text, colors["--brand"]) >= 4.5
    assert contrast(colors["--line-strong"], colors["--surface"]) >= 3


def test_javascript_parses(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js não instalado, teste de sintaxe não executado")
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", HTML, re.S)
    assert len(scripts) == 1
    js = tmp_path / "site.js"
    js.write_text(scripts[0], encoding="utf-8")
    result = subprocess.run([node, "--check", str(js)], text=True,
                            capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
