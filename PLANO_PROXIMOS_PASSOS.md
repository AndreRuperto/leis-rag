# Leis RAG — Plano de ação e evolução

> **Versão:** 1.0 · **Atualizado em:** 09/11/2026 · **Responsável pelo projeto:** André Ruperto  
> **Repositório:** [AndreRuperto/leis-rag](https://github.com/AndreRuperto/leis-rag)  
> **Produção:** [leis-web.up.railway.app](https://leis-web.up.railway.app/) · **Sobre:** [/sobre](https://leis-web.up.railway.app/sobre)  
> **Objetivo:** transformar o MVP em uma plataforma de pesquisa jurídica com acervo verificável, respostas fundamentadas, operação observável e custos controlados.

## 1. Situação verificada e regras deste plano

### Entregas existentes

- [x] Interface responsiva com temas claro/escuro, filtros, busca, modo IA, cards de pesquisa e página **Sobre o Projeto**.
- [x] Rodapé com atribuição a **André Ruperto** e links sociais.
- [x] Backend FastAPI, PostgreSQL com pgvector, busca textual e importação incremental por checksum.
- [x] Branch de publicação enxuta `deploy/railway-slim` e workflow [`railway-slim.yml`](.github/workflows/railway-slim.yml), que elimina o acervo massivo do snapshot de build.
- [x] Serviço Railway `leis-web` publicado com sucesso e `leis-db` operacional — verificação em 09/11/2026.
- [x] Código de importação de quatro códigos federais, tratamento de falhas por fonte, retry, testes unitários e serviço `leis-indexador` configurado.
- [x] Deploy da imagem do indexador com status `SUCCESS`.

### Pendências que não devem ser confundidas com entregas

- [ ] **Importação real dos quatro códigos ainda não foi comprovada**. Houve execução anterior com `RemoteDisconnected` na fonte oficial. Status `SUCCESS` de deploy **não prova** que o job executou nem que gravou documentos.
- [ ] O serviço `leis-indexador` está programado para `0 6 * * 0` (**domingo, 06:00 UTC**). Confirmar a execução, saída do processo, cron e indicadores do banco.
- [ ] Não há evidência suficiente de testes ponta a ponta com perguntas jurídicas, comparação com textos oficiais e desempenho sob tráfego.
- [ ] O acesso à IA depende de um código privado compartilhado, sem gestão de usuários, permissões e auditoria individual.
- [ ] Não há painel administrativo de ingestão, qualidade e monitoramento integrado.

**Regra de status:** use `[x]` somente para atividade **executada e verificada**. Use `[ ]` para planejada, parcialmente feita ou não validada. Cada PR deve atualizar este arquivo com evidências: commit, teste, logs, contagens ou captura pertinente.

## 2. Ordem de prioridade

| Prioridade | Frente | Resultado esperado | Critério de saída |
| --- | --- | --- | --- |
| **P0** | Importação real e confiabilidade dos dados | Quatro códigos acessíveis no índice | Fonte validada + trechos no PostgreSQL + busca funcional |
| **P0** | Telemetria e falhas do indexador | Saber o que rodou e por que falhou | Histórico por fonte, logs e alerta |
| **P1** | Cobertura jurídica auditável | Expandir com rastreabilidade | Dashboard de cobertura e inconsistências |
| **P1** | Qualidade da busca e IA | Respostas pertinentes e citadas | Conjunto de avaliação e metas verificadas |
| **P1** | Segurança e custos | Uso controlado e protegido | Limites por usuário, testes e segredos revisados |
| **P2** | UX e acessibilidade | Interface coesa em todas as telas | Auditoria visual e testes E2E |
| **P2** | Operação e produto | Deploy sustentável e transparência | Runbooks, backup/restauração e documentação |
| **P3** | Funcionalidades avançadas | Recursos úteis sob demanda | Uso validado, sem prejudicar precisão |

---

## 3. Fase 0 — Desbloquear a importação real (P0)

**Objetivo:** provar que os dados estão chegando ao PostgreSQL, sem afetar o site.

### 0.1 Diagnóstico da conectividade às fontes

- [ ] Examinar os logs do `leis-indexador` da execução **após** o PR [#16](https://github.com/AndreRuperto/leis-rag/pull/16): registrar URL tentada, hostname, código HTTP e classe do erro, **sem expor segredos**.
- [ ] Testar `--dry-run` para **cada** código individualmente (`penal`, `civil`, `clt`, `cdc`), com tempo máximo e tentativas limitadas.
- [ ] Investigar bloqueio de tráfego/Cloudflare, DNS, TLS, redirecionamentos e restrições de rede do Railway; não tratar indisponibilidade como documento vazio.
- [ ] Caso sites oficiais continuem inacessíveis, implementar estratégia controlada de aquisição: espelho/documento derivado **com origem comprovada**, revisão da fonte e checksum; jamais mascarar uma cópia desatualizada como consulta ao vivo.
- [ ] Separar **URL oficial de referência**, **URL efetivamente utilizada para download** e **data da última verificação**.
- [ ] Testar HTML real de cada código; verificar regras de extração para artigos, parágrafos, incisos, dispositivos revogados e tabelas. Não aceitar só a contagem mínima como validação jurídica.

### 0.2 Indexar e validar no banco

- [ ] Executar em lote de **um código por vez**, iniciando por CDC; rodar modo de validação e depois importação definitiva.
- [ ] Verificar transação/rollback e idempotência: uma nova importação sem alteração deve retornar `unchanged`; documento inválido não substitui versão boa.
- [ ] Conferir via SQL quantidade de leis, trechos, artigo inicial/final, URL de fonte, checksum, data e esferas; documentar os valores reais.
- [ ] Fazer consulta de ponta a ponta (`/api/search`) de três artigos por código; garantir resultado com título, artigo e fonte correta.
- [ ] Registrar discrepâncias relevantes: títulos errados, artigos ausentes ou duplicados, caracteres corrompidos, links quebrados e versões antigas.
- [ ] Atualizar o texto da página Sobre e os indicadores conforme **dados efetivamente indexados**, nunca conforme arquivos apenas disponíveis no repositório.

### 0.3 Operação segura

- [ ] Executar a ingestão em processo/worker separado; manter `leis-web` respondendo sem depender de sites terceiros.
- [ ] Configurar timeout, retries com backoff, limites de payload, logs estruturados e saída não-zero em falhas reais.
- [ ] Manter cron **semanal** apenas depois de validar a primeira execução; evitar `*/5 * * * *` em produção.
- [ ] Garantir que não haja sobreposição de duas importações; usar trava no banco quando necessário.
- [ ] Alertar quando uma fonte falhar ou quando o índice ficar desatualizado; fornecer instrução de reprocessamento manual.

**Aceite da fase:** pelo menos os 4 documentos conferidos individualmente, todos pesquisáveis, data e fonte exibidas e execução do indexador registrada sem inconsistências graves. Falha de um código deve gerar alerta explícito e não apagar as outras fontes.

## 4. Fase 1 — Pipeline de dados e cobertura jurídica (P1)

### 1.1 Catálogo e versionamento

- [ ] Criar tabela de **fontes/documentos** com identificação, órgão, esfera, UF, tipo, URL, origem da versão, data de verificação, checksum e estado de ingestão.
- [ ] Criar tabela `import_runs` / `import_items` com início, fim, duração, totais, códigos de erro e revisão do código executado.
- [ ] Preservar **histórico de versões** quando os textos mudarem, com diferenciação entre norma revogada, redação anterior e fonte incerta.
- [ ] Modelar a relação norma–artigo–parágrafo/inciso e construir chaves estáveis para citações.
- [ ] Normalizar metadados como número, data, esfera, tipo e UF, sem inferir situação jurídica a partir da idade do documento.
- [ ] Criar reconciliação entre arquivos do repositório `ctresb/leis` e documentos efetivamente indexados.

### 1.2 Cobertura incremental

- [ ] Depois dos quatro códigos, priorizar Constituição, ECA, Lei Maria da Penha, CPC, CPP, LGPD e leis federais de alta procura.
- [ ] Ampliar por lotes pequenos com fila de trabalho, checkpoints e limite de consumo de memória/banco.
- [ ] Adicionar legislação estadual/distrital e municipal **somente quando existir fonte confiável e metadados suficientes**; começar por recortes definidos.
- [ ] Permitir revisão e reprocessamento seletivo, sem recarregar toda a base por alteração em um documento.
- [ ] Definir política de remoção/despublicação e auditoria quando uma fonte deixa de ser válida.

### 1.3 Painel de indexação

- [ ] Criar página administrativa protegida com quantidade de normas, trechos, cobertura por tipo/UF/esfera, importações recentes e fontes com erro.
- [ ] Mostrar `indexed / unchanged / failed / skipped` por lote; data da última sincronização e próxima prevista.
- [ ] Implementar ações **restritas**: validar, reindexar um documento, retentar uma falha e consultar logs (nunca revelar credenciais).
- [ ] Disponibilizar relatório CSV/JSON de cobertura e inconsistências.

**Aceite:** importações auditáveis, cobertura mensurável, recuperação de falhas sem reprocessamento completo e painel condizente com o banco.

## 5. Fase 2 — Busca jurídica, RAG e qualidade (P1)

### 2.1 Melhorar recuperação

- [ ] Criar conjunto de consultas com **gabarito de dispositivos relevantes**: número da lei, artigo, assunto e filtros; revisar com profissional jurídico.
- [ ] Avaliar a busca lexical, busca semântica opcional e fusão de rankings (Recall@k, MRR e precisão das citações).
- [ ] Melhorar tratamento de referências como `art. 5º, inciso X`, `Lei 8.078/90`, abreviações, erros de digitação e sinônimos jurídicos.
- [ ] Garantir que filtros por esfera, UF e tipo atuem igualmente na recuperação lexical e vetorial.
- [ ] Avaliar reranking e segmentação de trechos longos mantendo o encadeamento artigo/parágrafo/inciso.
- [ ] Testar consultas sem resultados e consultas fora da cobertura, sem inventar resposta jurídica.

### 2.2 Garantir fundamentação e transparência

- [ ] Exibir fontes separadas por categoria: **acervo local**, **fonte oficial na web**, **material complementar** e **guia editorial**.
- [ ] Associar cada afirmação normativa a uma fonte, trecho e URL verificável; quando não houver evidência suficiente, responder com ressalva clara.
- [ ] Mostrar **versão do texto** e **última conferência**, não confundir última importação com vigência.
- [ ] Validar URLs citadas, alertar quando a fonte estiver indisponível e reduzir conclusões baseadas só em fontes secundárias.
- [ ] Distinguir citações de jurisprudência, texto legal e interpretação; não apresentar geração de IA como parecer jurídico.

### 2.3 Testes de qualidade

- [ ] Montar benchmark de pelo menos 50 perguntas cobrindo os quatro códigos, Constituição, casos ambíguos e perguntas sem base.
- [ ] Avaliar correção jurídica, completude, qualidade das fontes, taxa de abstenção e alucinação.
- [ ] Comparar modelos/custos com avaliações reproduzíveis antes de trocar de provedor ou ativar embeddings caros.
- [ ] Criar testes automatizados de regressão para respostas e citações; casos de erro devem bloquear publicação se forem críticos.

**Aceite:** métricas de recuperação documentadas, nenhuma referência inventada nos cenários de teste, e revisão humana dos exemplos sensíveis.

## 6. Fase 3 — Segurança, privacidade e custos (P1)

- [ ] Substituir o **código compartilhado** por login ou credenciais individuais, com papéis (usuário/admin) e revogação.
- [ ] Manter chaves somente em variáveis seguras do Railway; revisar e rotacionar segredos expostos.
- [ ] Criar quotas por usuário/dia, limites de tokens e custo, além de um teto global com alerta antes de atingir o orçamento.
- [ ] Incluir proteção contra abuso, controle de requisições e limites de conteúdo; registrar eventos sem armazenar senhas ou consultas sensíveis indevidamente.
- [ ] Validar permissões dos endpoints de administração, CSRF quando aplicável, CORS e cabeçalhos de segurança.
- [ ] Estabelecer política de logs, retenção, exclusão e privacidade de consultas.
- [ ] Revisar dependências com SCA, fixar versões com política de atualizações e corrigir CVEs relevantes.
- [ ] Testar prompt injection em documentos e conteúdo web: fontes não podem alterar regras de autorização nem solicitar segredos.

**Aceite:** não há chamada paga sem autorização, quotas são cumpridas entre réplicas, credenciais não aparecem em logs e testes de autorização passam.

## 7. Fase 4 — Frontend, UX e acessibilidade (P2)

- [ ] Revisar espaçamentos e hierarquia no bloco **Consultar com IA**, especialmente tabs → aviso → `Onde pesquisar?` → opções → código de acesso.
- [ ] Auditar desktop (1280/1440/1920), tablet (768/1024) e mobile (320/360/390/430).
- [ ] Validar os dropdowns de UF/tipo, posição da lista, rolagem horizontal, bandeiras, teclado e leitores de tela.
- [ ] Garantir feedback claro: indexando, sem documentos, IA indisponível, código incorreto, limite atingido, fonte inacessível e consulta cancelada.
- [ ] Melhorar resultado jurídico: índice de artigos, expansão de trechos, copiar referência, abrir original, indicação de versão e fonte oficial.
- [ ] Revisar menu, página `/sobre`, footer, link de André Ruperto, ícones, contraste WCAG AA, estados de foco e preferência por movimento reduzido.
- [ ] Implementar teste E2E real em Playwright (tema claro/escuro, filtros, modos de pesquisa, fluxo mobile, status de erro).
- [ ] Realizar auditoria final de componentes, CSS computado, ordem de importação, especificidade e sobreposições antes de alterar visual.

**Aceite:** testes automatizados e inspeção real sem overflow, sem controles encobertos e com navegação de teclado funcional.

## 8. Fase 5 — Operação, documentação e produto (P2)

- [ ] Separar definitivamente aplicação, base de dados e worker; revisar custos e gatilhos de deploy da branch enxuta.
- [ ] Criar smoke tests após deploy para `/`, `/sobre`, `/api/health`, `/api/stats` e consultas de busca.
- [ ] Estabelecer monitoramento de disponibilidade, erros 5xx, tempo de resposta, conexões do banco e execuções do indexador.
- [ ] Documentar backup **e teste de restauração** do PostgreSQL, além de política de retenção.
- [ ] Criar runbooks de falha de build, falha de ingestão, fonte fora do ar, chave de IA inválida, banco indisponível e rollback.
- [ ] Atualizar `README.md`, `MVP.md`, `IMPORTACAO_OFICIAL.md` e a página Sobre conforme funcionalidades realmente comprovadas.
- [ ] Definir versionamento e changelog; publicar indicadores de cobertura com explicação das limitações.
- [ ] Medir uso real e acessibilidade antes de ampliar funcionalidades (histórico de pesquisa, coleção de artigos, exportação PDF e favoritos).

**Aceite:** deploy reversível, restauração ensaiada, documentação consistente e indicadores operacionais disponíveis.

## 9. Backlog futuro — somente após P0/P1

- [ ] Contas pessoais com histórico e favoritos, respeitando a privacidade.
- [ ] Comparação de redações de dispositivos ao longo do tempo.
- [ ] Exportação PDF com perguntas, respostas, trechos e fontes, preservando avisos de vigência.
- [ ] Busca por jurisprudência com filtros de tribunal e data, diferenciada do texto normativo.
- [ ] API pública com autenticação e limites por plano, caso haja demanda.
- [ ] Painel de feedback de usuários para identificar resultados ruins e fontes ausentes.
- [ ] IA especializada/fine-tuning **apenas** se benchmark comprovar ganho e custo menor; precisão vem antes de parâmetros.

## 10. Próximas execuções — ordem exata

| Ordem | Ação | Entregável | Validação |
| --- | --- | --- | --- |
| **01** | Diagnosticar conectividade externa no worker e executar validação individual do CDC | Logs e causa conhecida por hostname | Resposta válida ou bloqueio documentado |
| **02** | Corrigir aquisição/extrator, sem perder fonte verificável | Importador robusto + testes HTML reais | Artigos extraídos e metadados consistentes |
| **03** | Importar CDC com transação e verificar banco | Documento real + trechos no PostgreSQL | Busca de três artigos com URL |
| **04** | Importar Penal, Civil e CLT um por vez | Quatro conjuntos indexados | Mesma checagem individual |
| **05** | Adicionar histórico de execuções e alertas | `import_runs` + monitoramento | Falha visível e reprocessável |
| **06** | Publicar dashboard de cobertura e inconsistências | Painel administrativo protegido | Contagens batem com SQL |
| **07** | Criar benchmark e corrigir ranking/citações | Suite de qualidade jurídica | Métricas e revisão documentadas |
| **08** | Endurecer autenticação, custos e privacidade | Acesso por usuário e quotas | Testes de segurança |
| **09** | Auditar interface e fazer testes E2E | Relatório visual + correções | Mobile, desktop, teclado |
| **10** | Testar backup/restore e criar runbooks | Checklist de operação | Simulação de recuperação aprovada |

**Primeira atividade recomendada:** **01 — diagnóstico do worker**. Não aumentar a cobertura nem apresentar os quatro códigos como disponíveis antes de obter logs, contagens e resultados de busca de ponta a ponta.

## 11. Como manter o plano atualizado

Em cada ciclo:

1. Criar PR pequeno associado a uma linha da tabela de execução.
2. Executar testes pertinentes e validar o deploy correto (o status do build não equivale a sucesso da importação).
3. Registrar no PR as evidências de teste e resultados no banco, sem dados sensíveis.
4. Marcar o item como `[x]` **somente depois** de verificar; se incompleto, manter `[ ]` com observação.
5. Atualizar a tabela e os bloqueios neste arquivo no mesmo PR.
6. Em decisões de arquitetura, registrar motivação, trade-offs, risco de reversão e custo.

### Links úteis

- [Documentação técnica do MVP](MVP.md)
- [Importação oficial](IMPORTACAO_OFICIAL.md)
- [Workflow do Railway](.github/workflows/railway-slim.yml)
- [Código do importador](app/official_import.py)
- [Projeto no Railway](https://railway.com/project/565efd6a-4998-4642-8e68-26421b923334)
- [Issues do projeto](https://github.com/AndreRuperto/leis-rag/issues)

---

*Este documento distingue entrega de infraestrutura de ingestão de dados validada; não é uma afirmação de que leis ainda não conferidas já estejam disponíveis. Revisar prioridades após cada fase.*
