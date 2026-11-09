# Importação de códigos federais oficiais

O Leis RAG começa com a Constituição Federal e agora dispõe de um importador
independente para quatro códigos fundamentais:

| Identificador | Texto | Fonte oficial |
| --- | --- | --- |
| `penal` | Código Penal, DL 2.848/1940 | [Presidência da República](https://presidencia.gov.br/ccivil_03/decreto-lei/del2848compilado.htm) |
| `civil` | Código Civil, Lei 10.406/2002 | [Planalto](https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm) |
| `clt` | Consolidação das Leis do Trabalho, DL 5.452/1943 | [Planalto](https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452compilado.htm) |
| `cdc` | Código de Defesa do Consumidor, Lei 8.078/1990 | [Planalto](https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm) |

## Como executar

No ambiente com acesso ao PostgreSQL e às fontes oficiais:

```bash
python -m app.official_import --dry-run
python -m app.official_import --codes penal,civil,clt,cdc
python -m app.official_import --codes cdc
```

A opção `--dry-run` **baixa e valida o documento sem alterar o banco**.
O processo recusa documentos anormalmente curtos, exige um número mínimo de
artigos e limita os downloads a 18 MiB por fonte.

Após a validação, usa a mesma `index_file` transacional do importador Markdown.
Cada documento recebe uma chave estável como
`dados/federal/codigos/penal.md`, checksum SHA-256 e URL oficial. Reimportar
um documento sem mudanças não destrói nem recria os trechos anteriores. Falhas
em qualquer código não apagam os já importados.

**Atenção:** os textos são cópias do HTML oficial, não certificações da
redação vigente de cada artigo. Sites oficiais podem incluir dispositivos
revogados, anotações e redações históricas. O sistema indica que a vigência
deve ser verificada; uma data de importação **não** equivale à data de
consolidação normativa.

## Arquitetura recomendada no Railway

A API web continua na branch `deploy/railway-slim`. O importador não deve ser
executado dentro do request HTTP ou em toda inicialização da aplicação.

Para operação contínua, use um serviço/worker separado no mesmo projeto
Railway com conexão interna ao Postgres e start command:

```bash
python -m app.official_import --codes penal,civil,clt,cdc
```

Faça execução manual ou em cron semanal, acompanhando os logs. O processo
consome rede, armazenamento e CPU do projeto. **Não** coloque o enorme acervo
`dados/` no contexto de build.

Os arquivos de teste cobrem os mecanismos de extração HTML, validação do
documento, checksum estável e metadados de origem. São testes locais de
unidade; não substituem o teste real de acesso às páginas governamentais
nem a conferência jurídica das transcrições.
