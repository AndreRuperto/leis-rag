# Leis RAG · primeira versão funcional

Esta versão adiciona **uma aplicação local de pesquisa jurídica** à base de Markdown. A pasta dados/ continua intacta e com os créditos do projeto de origem.

## Funcionalidades

- Importação incremental de normas Markdown, incluindo YAML e a Constituição sem frontmatter.
- Divisão preferencial por artigos; textos grandes são particionados sem descarte.
- Metadados (UF, esfera, título, número, situação informada, versão do texto e fonte oficial).
- Busca textual em português com índice GIN do PostgreSQL.
- Busca semântica opcional com modelo multilíngue e pgvector (384 dimensões).
- Fusão dos resultados, filtros por esfera/UF/tipo e links para verificar as evidências.
- Síntese opcional via OpenAI API, usando os trechos recuperados.
- Interface responsiva, endpoints REST e documentação Swagger.

**Importante:** a versão sem chave de IA já permite procurar e consultar leis. A ausência de resultados não comprova ausência de legislação. Os textos são informativos; é necessário verificar publicação, vigência, revogações e aplicação ao caso concreto.

## Iniciar com Docker (recomendado)

Na raiz do repositório:

~~~bash
cp .env.example .env
docker compose up --build -d
docker compose run --rm api python -m app.ingest --path dados/constituicao.md --limit 1
~~~

No PowerShell, copie o .env com:

~~~powershell
Copy-Item .env.example .env
~~~

Abra **http://localhost:8000**. A documentação da API está em **http://localhost:8000/docs**.

Inicialmente, a aplicação indexa **somente os arquivos solicitados**, evitando carregar mais de um milhão de documentos de uma vez.

Para importar um lote de leis federais:

~~~bash
docker compose run --rm api python -m app.ingest --path dados/federal/leis-ordinarias --limit 250
~~~

Para reindexar sem verificar alterações, acrescente --force. Sem ele, o importador compara SHA-256 e pula arquivos idênticos. A exclusão de arquivos na fonte ainda **não** remove documentos já indexados.

## API

- GET /api/health — verifica o banco e o número de normas.
- GET /api/stats — contagens do índice.
- GET /api/search?q=liberdade%20de%20expressao&sphere=federal — trechos e fontes.
- POST /api/ask — pergunta e síntese, quando a chave de IA estiver configurada.

Exemplo:

~~~bash
curl "http://localhost:8000/api/search?q=direitos%20fundamentais"
~~~

## IA opcional

No .env, coloque OPENAI_API_KEY com uma chave válida (não a envie ao Git). OPENAI_MODEL pode escolher um modelo disponível na sua conta. A consulta sem chave retorna as fontes, sem inventar uma resposta. O uso de API pode gerar custos, separados de qualquer assinatura do ChatGPT.

## Respostas jurídicas: acervo e pesquisa externa

A opção **Consultar com IA** usa o conteúdo da base local como evidência. O texto
apresentado pelo modelo não comprova a vigência de uma norma.

O comportamento do endpoint `POST /api/ask` agora diferencia:
- **Sem chave:** nenhum texto jurídico gerado por IA; o acervo continua disponível.
- **Com ou sem chave, pesquisa externa desativada:** para alguns temas, um guia
  editorial com fontes oficiais já conferidas pode contextualizar a pergunta;
  esse conteúdo é identificado como guia, nunca como geração por IA ou busca
  feita em tempo real. Fora dos guias, a síntese depende de documentos locais
  e da chave da API. Se não houver evidência, o sistema explica a limitação.
- **Com chave e acervo local:** quando não houver guia, sintetiza os dispositivos
  recuperados; o modelo não deve inventar normas que não foram fornecidas.
- **Com chave e `LEGAL_WEB_SEARCH_ENABLED=1`:** pesquisa obrigatória em sites oficiais
  (Planalto, STF, STJ, Senado, Câmara, CNJ e gov.br), permite relacionar
  Constituição, leis e jurisprudência, e devolve `web_sources` com URLs citadas
  pelo provedor, além de `sources` locais. Sem citações oficiais verificáveis,
  o servidor não apresenta conclusão jurídica derivada da busca.

Para a modalidade exclusivamente documental, envie `research_mode: "acervo"` no
corpo da requisição (padrão `"hybrid"`). O endpoint `GET /api/capabilities`
indica se IA e pesquisa externa estão configuradas; a interface desabilita
a aba de IA quando não há chave configurada.

**Muito importante:** **não configure uma chave paga no serviço público do MVP**
antes de implementar controle de acesso, limites de uso e observabilidade de custos.
A busca web gera cobrança adicional por chamadas. O modelo pode ter limitações
de cobertura, mesmo com filtros de domínio.

A prévia `leis-preview-visual-production.up.railway.app` serve apenas para avaliar
a interface e tem poucos exemplos da Constituição; não é uma resposta jurídica.

## Vetores opcionais

No .env, defina:

~~~dotenv
INSTALL_EMBEDDINGS=1
EMBEDDINGS_ENABLED=1
~~~

Depois reconstrua e **reindexe os documentos existentes** para gerar embeddings:

~~~bash
docker compose up --build -d
docker compose run --rm api python -m app.ingest --path dados/constituicao.md --force --limit 1
~~~

A primeira execução baixa o modelo de embeddings, exigindo memória e espaço. O container do banco já tem a extensão pgvector. Um índice ANN (HNSW) passa a ser importante quando o volume de trechos crescer; crie-o após dimensionar e importar o conjunto de dados.

## Cuidados antes de publicar

A aplicação está configurada para desenvolvimento local (porta vinculada a 127.0.0.1). **Ainda não há autenticação, limite de uso ou proteção contra custos abusivos.** Não disponibilize publicamente o endpoint de IA sem adicionar autorização, limites de taxa e observabilidade. Evite enviar documentos sigilosos ou dados pessoais para terceiros sem autorização e política adequada.

A busca não certifica vigência ou completude. O campo status é o conteúdo do metadado original, quando disponível. A síntese usa textos que podem conter erros de OCR, conversão e atualização.

## Próximos passos

1. Conjunto de avaliação jurídica e testes de qualidade de recuperação/citações.
2. Importação em lotes com fila, monitoramento e reconciliação de exclusões.
3. HNSW, reclassificação dos resultados e filtros de vigência com fontes históricas.
4. Login, permissões, rate limit e proteção contra abuso.
5. Análise de documentos PDF e acompanhamento automático de alterações legislativas.


## URL de produção

Aplicativo com FastAPI/PostgreSQL: **https://leis-web.up.railway.app/**.
A prévia **https://leis-preview-visual-production.up.railway.app/** serve somente
para revisar a interface e não executa IA nem corresponde ao acervo completo.

## Guia editorial de temas

Os guias em `app/legal_guides.py` contêm respostas de referência e URLs
institucionais previamente verificadas. Não há busca web em tempo real quando
esses guias são apresentados. O primeiro guia cobre a distinção entre
Constituição, Código Penal e ADPF 54 no tema do aborto, com referências ao
Planalto, Senado, STF e Ministério da Saúde (revisão: 09/11/2026). Outros
temas precisam de pesquisa, revisão e testes antes de entrar no catálogo.

A busca tenta recuperar artigos constitucionais relevantes ao assunto e
rotula o texto editorial separadamente das fontes do banco. Essa etapa não
deve ser confundida com uma busca semântica completa. A cobertura do
catálogo é deliberadamente limitada: o objetivo continua sendo integrar
mais normas ao banco e habilitar RAG com atualização controlada.
