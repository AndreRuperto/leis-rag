"""Testes unitários de parsing sem depender de um PostgreSQL em execução."""
from app.ingest import parse_document, split_long, split_passages


def test_constitution_articles():
    text = (
        "# Constituição da República Federativa do Brasil de 1988\n\n"
        "## TÍTULO I\n\n"
        "**Art. 1º** A República é um Estado Democrático de Direito.\n\n"
        "I - soberania;\n\n"
        "**Art. 2º** São Poderes da União, independentes e harmônicos.\n"
    )
    doc = parse_document(text, "constituicao.md")
    assert doc["sphere"] == "federal"
    assert doc["law_type"] == "Constituição Federal"
    assert doc["passages"][1][0] == "Art. 1º"
    assert "soberania" in doc["passages"][1][1]
    assert doc["passages"][2][0] == "Art. 2º"


def test_yaml_metadata_and_state():
    text = (
        '---\ntitulo: "Lei nº 123"\ntipo: "Lei Ordinária"\n'
        'numero: "123"\nuf: DF\nfonte: "https://www.sinj.df.gov.br/"\n'
        'situacao: "Em vigor"\n---\n'
        "# Lei 123\n\nArt. 1º Esta lei define um exemplo.\n"
    )
    doc = parse_document(text, "estaduais/DF/leis-ordinarias/2026/123.md")
    assert doc["title"] == "Lei nº 123"
    assert doc["sphere"] == "estadual"
    assert doc["uf"] == "DF"
    assert doc["source_url"] == "https://www.sinj.df.gov.br/"
    assert doc["passages"][-1][0] == "Art. 1º"


def test_source_constitution_without_yaml():
    text = (
        "# Constituição da República Federativa do Brasil de 1988\n\n"
        "> Fonte: [texto compilado do Planalto]"
        "(https://www.planalto.gov.br/ccivil_03/constituicao/constituicaocompilado.htm)\n\n"
        "**Art. 5º** Todos são iguais perante a lei.\n"
    )
    doc = parse_document(text, "constituicao.md")
    assert doc["source_url"].startswith("https://www.planalto.gov.br/")
    assert doc["passages"][-1][0] == "Art. 5º"


def test_fallback_by_heading():
    sections = split_passages("# Lei\n\n## Disposições gerais\nTexto.\n\n## Regras\nOutro texto.")
    assert len(sections) == 3
    assert sections[-1][0] == "Regras"


def test_long_article_is_not_dropped():
    chunks = split_long("Art. 4º", "A" * 210, max_size=100)
    assert len(chunks) == 3
    assert "".join(text for _, text in chunks) == "A" * 210
    assert chunks[1][0] == "Art. 4º (parte 2)"


def test_empty_text():
    assert split_passages("") == []
