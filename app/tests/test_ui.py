"""Verificações estáticas de identidade visual, acessibilidade e JavaScript da UI."""
from html.parser import HTMLParser
from pathlib import Path
import re
import json
from xml.etree import ElementTree as ET
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


def test_custom_sphere_dropdown():
    """Menu customizado preserva os valores da API e acesso por teclado."""
    from html.parser import HTMLParser

    class DropdownParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.options = []
            self.elements = {}

        def handle_starttag(self, tag, attrs):
            props = dict(attrs)
            if props.get("id") in {"sphere", "sphere-trigger", "sphere-menu"}:
                self.elements[props["id"]] = (tag, props)
            if props.get("role") == "option":
                self.options.append(props)

    parsed = DropdownParser()
    parsed.feed(HTML)
    assert parsed.elements["sphere"][0] == "input"
    assert parsed.elements["sphere"][1].get("type") == "hidden"
    trigger = parsed.elements["sphere-trigger"][1]
    assert trigger["aria-haspopup"] == "listbox"
    assert trigger["aria-expanded"] == "false"
    assert trigger["aria-controls"] == "sphere-menu"
    menu = parsed.elements["sphere-menu"][1]
    assert menu["role"] == "listbox"
    assert "hidden" in menu
    assert [item["data-value"] for item in parsed.options] == [
        "", "federal", "estadual", "municipal", "regulador",
        "jurisprudencia", "tratado"
    ]
    for behavior in ("openSphereMenu", "closeSphereMenu", "setSphere",
                     "focusSphereOption", 'event.key === "Escape"',
                     'event.key === "Home"', 'event.key === "End"',
                     'event.key === "ArrowDown"', 'event.key === "ArrowUp"'):
        assert behavior in HTML
    assert ".filter-dropdown-menu[hidden]{display:none}" in HTML
    assert ".filter-dropdown.opens-up .filter-dropdown-menu" in HTML


def test_uf_and_law_type_are_accessible_dropdowns():
    for field in ("uf", "law_type"):
        assert f'id="{field}" type="text"' not in HTML
        assert f'id="{field}" name="{field}" value=""' in HTML
        assert f'id="{field}-trigger"' in HTML
        assert f'aria-controls="{field}-menu"' in HTML
        assert f'id="{field}-query"' in HTML
        assert f'id="{field}-menu" role="listbox"' in HTML
        assert f'id="{field}-popover" hidden' in HTML
    assert 'function setupFilterDropdown(' in HTML
    assert 'function loadLawTypes()' in HTML
    assert 'fetch("/api/filter-options")' in HTML
    assert 'focusOption(' in HTML
    assert 'closeSphereMenu();' in HTML
    assert 'window.LEIS_UF_FLAGS' in HTML
    assert '.filter-dropdown-popover[hidden]' in HTML


def test_all_27_flags_are_bundled_locally():
    static_dir = PAGE.parent
    flags = {}
    for idx in (1, 2, 3):
        relative = f"uf-flags-{idx}.js"
        source = (static_dir / relative).read_text(encoding="utf-8")
        assert f'src="/assets/{relative}"' in HTML
        match = re.search(
            r"Object\.assign\(window\.LEIS_UF_FLAGS \|\| \{\}, (\{.*\})\);", source
        )
        assert match
        for uf, svg in json.loads(match.group(1)).items():
            assert uf not in flags, "Bandeira duplicada"
            ET.fromstring(svg)
            assert "<svg" in svg and "<script" not in svg
            flags[uf] = svg
    assert len(flags) == 27
    states = re.search(r"const UF_REGIONS = \[(.*?)\]\.map", HTML, re.S)
    assert states
    codes = set(re.findall(r'\["([A-Z]{2})","[^"]+"\]', states.group(1)))
    assert len(codes) == 27
    assert codes == set(flags)
    assert "DF" in flags and "SP" in flags


def test_dropdowns_stack_above_following_filters():
    # Em mobile o campo Tipo não pode cobrir a lista aberta da UF.
    assert '.fields>div:has(.filter-dropdown.is-open){position:relative;z-index:100}' in HTML
    assert '.filter-dropdown.is-open{z-index:101}' in HTML
    assert 'wrapper.classList.add("is-open")' in HTML
    assert 'wrapper.classList.remove("opens-up", "is-open")' in HTML
    assert 'sphereDropdown.classList.add("is-open")' in HTML
    assert 'sphereDropdown.classList.remove("is-open")' in HTML
    assert 'ufDropdown.close();' in HTML
    assert 'lawTypeDropdown.close();' in HTML


def test_javascript_parses(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js não instalado, teste de sintaxe não executado")
    scripts = re.findall(r"<script>(.*?)</script>", HTML, re.S)
    assert len(scripts) == 1
    js = tmp_path / "site.js"
    js.write_text(scripts[0], encoding="utf-8")
    result = subprocess.run([node, "--check", str(js)], text=True,
                            capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
