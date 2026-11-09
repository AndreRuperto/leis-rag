"""Guias editoriais verificados para dúvidas jurídicas frequentes.

Não substituem consulta atualizada de legislação. Diferenciam conhecimento
editorial, evidência indexada e pesquisa externa em tempo real.
"""
import re
import unicodedata

REVIEWED_AT = "2026-11-09"


def normalize(text):
    value = unicodedata.normalize("NFD", text or "")
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", value.casefold()).strip()


# Catálogo extensível. Fontes oficiais conferidas em 09/11/2026.
GUIDES = {
    "aborto": {
        "terms": ("aborto", "abortamento", "abortar", "interrupcao da gravidez",
                  "interrupcao gestacional", "interrupcao voluntaria da gravidez"),
        "constitution_labels": ("Art. 1º", "Art. 5º", "Art. 6º", "Art. 196"),
        "answer": (
            "A Constituição Federal de 1988 não contém uma regra específica "
            "que autorize ou proíba o aborto em termos gerais. A análise "
            "constitucional envolve princípios como a dignidade da pessoa "
            "humana (art. 1º, III), a proteção à vida e à liberdade (art. 5º) "
            "e o direito à saúde (arts. 6º e 196). Esses dispositivos não "
            "resolvem isoladamente todas as situações.\n\n"
            "A disciplina penal está principalmente nos arts. 124 a 128 do "
            "Código Penal. O art. 128 prevê hipóteses de não punição do aborto "
            "praticado por médico: quando não houver outro meio de salvar a "
            "vida da gestante ou quando a gravidez resultar de estupro, "
            "observadas as condições legais.\n\n"
            "Além disso, em 2012, o Supremo Tribunal Federal decidiu na "
            "ADPF 54 que a interrupção da gestação de feto anencéfalo não "
            "deve ser enquadrada nos tipos penais de aborto discutidos "
            "naquele julgamento. O Ministério da Saúde reúne orientações "
            "sobre as hipóteses de interrupção gestacional previstas em lei.\n\n"
            "Portanto, a resposta exige distinguir texto constitucional, "
            "legislação penal e interpretação do STF. Este é um resumo "
            "editorial, com referências oficiais listadas abaixo, e não "
            "uma pesquisa jurisprudencial atualizada ou um parecer jurídico. "
            "Confira eventuais alterações posteriores nas fontes."
        ),
        "references": (
            {"title": "Constituição Federal de 1988 — texto compilado (Planalto)",
             "url": "https://www.planalto.gov.br/ccivil_03/constituicao/constituicaocompilado.htm"},
            {"title": "Código Penal, arts. 124 a 128 — legislação (Senado Federal)",
             "url": "https://legis.senado.gov.br/norma/527942/publicacao/39870011"},
            {"title": "ADPF 54 — julgamento (Supremo Tribunal Federal)",
             "url": "https://portal.stf.jus.br/processos/listarProcessos.asp?classe=ADPF&numeroProcesso=54"},
            {"title": "Interrupção gestacional prevista em lei — Ministério da Saúde",
             "url": "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/s/saude-da-mulher/saude-sexual-e-reprodutiva/interrupcao-gestacional-prevista-em-lei"},
        ),
    },
}


def match_guide(question):
    normalized = normalize(question)
    for guide in GUIDES.values():
        if any(term in normalized for term in guide["terms"]):
            return guide
    return None


def editorial_answer(question):
    guide = match_guide(question)
    if guide is None:
        return None
    return {
        "answer": guide["answer"],
        "web_sources": [dict(ref) for ref in guide["references"]],
        "answer_mode": "guia_editorial",
        "ai_generated": False,
        "references_checked_at": REVIEWED_AT,
    }
