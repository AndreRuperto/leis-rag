# leis-rag

Base de legislação brasileira para um sistema de RAG (Retrieval-Augmented Generation) especializado em legislação.

## Origem dos dados

Todo o conteúdo da pasta [`dados/`](dados/) é uma cópia do repositório **[ctresb/leis](https://github.com/ctresb/leis)**, de João Davi ([@ctresb](https://github.com/ctresb)), que reúne a Constituição Federal e normas federais, estaduais, distritais, municipais, atos de órgãos reguladores, tratados e jurisprudência vinculante, convertidas de fontes oficiais para Markdown com cabeçalho YAML.

- Repositório original: https://github.com/ctresb/leis
- Commit de referência: [`15eb09b618f`](https://github.com/ctresb/leis/commit/15eb09b618f) ("Acrescenta 4138 atos priorizando series com metas abertas")
- Data da cópia: 24/10/2026

O crédito pela coleta, conversão, OCR, normalização e auditoria do acervo é integralmente do projeto original. A documentação dele foi mantida sem alterações em [`dados/README.md`](dados/README.md), [`dados/COBERTURA.md`](dados/COBERTURA.md) e [`dados/PROGRESSO.md`](dados/PROGRESSO.md).

O histórico do git do repositório original (uma norma por commit, assinada por quem a promulgou) não foi copiado. Para consultá-lo, use o repositório original.

## Licença

- **Textos das normas:** atos oficiais do poder público, sem proteção autoral (art. 8º, I, da Lei nº 9.610/98).
- **Scripts em `dados/scripts/`:** licença MIT do projeto original, mantida em [`dados/LICENSE`](dados/LICENSE).

## Aviso

Os textos têm caráter informativo e **não substituem a publicação no Diário Oficial**. São conversões automáticas e, em parte, OCR de documentos escaneados. Confira sempre a fonte indicada no cabeçalho de cada arquivo antes de citar.
