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
