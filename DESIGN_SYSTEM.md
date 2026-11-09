# Leis RAG — Identidade visual e design system

> Versão 1 · Protótipo funcional na interface \`app/static/index.html\`. Esta documentação é normativa para a UI; cores e estados de dispositivos legais **não** são validações de vigência.

## Direção de marca

**Institucional moderno, focado em pesquisa e evidência.** A lei e sua fonte devem ter precedência visual sobre uma resposta produzida por IA. Evitar o visual de chatbot futurista, ícones de balança da Justiça em excesso, fundos com gradientes chamativos e sinais de confiança sem lastro.

O tema **claro é padrão**. Tema escuro é escolha explícita no topo; a preferência é salva no navegador, quando disponível. Ambos compartilham a mesma semântica. O sinal § permanece como emblema visual, sem copiar marcas de órgãos públicos.

### Paleta principal

| Papel | Claro | Escuro | Semântica |
|---|---|---|---|
| Fundo | \`#F6F8FB\` | \`#0B1220\` | Canvas |
| Surface | \`#FFFFFF\` | \`#111D30\` | Painéis, documentos |
| Texto | \`#132238\` | \`#F2F7FB\` | Conteúdo primário |
| Texto secundário | \`#52677D\` | \`#B0C0D1\` | Contexto e dicas |
| Primário/marca | \`#0B4F6C\` | \`#5AD8B2\` | Botão principal, seleção |
| Link | \`#005EA8\` | \`#A8C8FF\` | Navegação e fontes |
| Borda neutra | \`#D6DEE7\` | \`#374A61\` | Agrupamento decorativo |
| Borda funcional | \`#7F91A6\` | \`#7890AA\` | Campo editável, controle |
| Foco | \`#005EA8\` | \`#5AD8B2\` | Focus ring 3px |
| Sucesso | \`#166534\` | \`#6EDC8C\` | Estado positivo, somente se comprovado |
| Atenção | \`#8A5A00\` | \`#F0C65A\` | Estado que requer verificação |
| Erro | \`#B42318\` | \`#FF8A94\` | Falha e avisos relevantes |

A implementação usa variáveis CSS e não confunde o verde da marca com a situação jurídica. A borda funcional e a tipografia buscam as razões mínimas WCAG 2.2 AA: 4,5:1 em texto normal e 3:1 nos limites visuais necessários dos controles. As razões para os pares principais são verificadas por \`app/tests/test_ui.py\`. Isso não equivale a auditoria WCAG completa em todas as resoluções, estados e zoom.

## Componentes e hierarquia

1. **Header:** emblema §, marca, navegação com âncoras verdadeiras e alternância de tema por botão nomeado.
2. **Hero:** uma proposta de valor objetiva e aviso de fonte verificável; não proclama acervo completo.
3. **Busca:** dois modos semânticos com abas acessíveis: _Buscar dispositivos_ e _Consultar com IA_. Um CTA principal por modo; Enter no formulário e Ctrl/Cmd+Enter em textarea.
4. **Filtros:** esfera, UF e tipo de norma; contagem de itens indexados, não estimativa fictícia de cobertura.
5. **Resultados:** artigo primeiro, título da norma, dados de contexto, trecho legível, número de referência e link para a fonte informada; cópia e expansão de trechos longos.
6. **Síntese de IA:** card diferenciado mas subordinado às fontes; as citações numéricas na resposta correspondem à ordem dos cards quando o provedor retorna citação. Nunca apresentar geração de texto como publicação oficial.
7. **Rodapé:** aviso permanente sobre cobertura, vigência e finalidade informativa.

### Estados obrigatórios

- **Vazio:** instrução útil sobre como começar.
- **Carregando:** mensagem de consulta e CTA desabilitado.
- **Erro:** texto de falha com distinção visual, sem mensagens do provedor potencialmente sensíveis.
- **Nenhum resultado:** não concluir que uma lei não exista.
- **Cópia:** confirmação breve e retorno automático do rótulo.
- **Resposta da IA:** sempre condicionada à API configurada; ausência de chave não permite prometer síntese automática.
- **Situação da norma:** exibir apenas se o metadado vier no resultado, com prefixo _Situação informada no acervo_. Nunca inferir “vigente” por ter sido indexado.

## Tipografia, dimensão e acessibilidade

- Fonte: pilha de sistema com Segoe UI, evitando download desnecessário.
- Título: 30–49 px com peso 800; corpo: 16 px e espaçamento 1.6; trechos jurídicos: 14 px com espaçamento 1.85.
- Escala de espaçamento: 4, 8, 12, 16, 24, 32 e 48 px; inputs e botões têm altura mínima de 44 px.
- Bordas de cards com raio de 14 px; área de busca com 20 px; sem sombras dramáticas.
- Foco visível de 3 px; rótulos explícitos; mensagens e links têm descrição e contraste; dados recebidos da API são renderizados como \`textContent\`, não como HTML.
- \`prefers-reduced-motion\` desativa transições e rolamento animado.
- Em até 780 px, filtros vão antes do formulário; abaixo de 480 px, o formulário, os filtros e o CTA ocupam a largura disponível.
- Avaliar ainda por QA humano: 320, 375, 768, 1024 e 1440 px, zoom 200%, leitor de tela, teclado, dark mode, respostas longas, estados interativos e daltonismo.

## Princípios de microcopy

| Evitar | Usar | Por quê |
|---|---|---|
| “A lei está vigente” | “Situação informada no acervo: vigente” | O dataset pode estar desatualizado |
| “Fonte oficial” para qualquer URL importada | “Ver fonte informada” | Origem da URL não prova autoridade |
| “IA jurídica responde tudo” | “Síntese assistida por fontes” | Não induz confiança excessiva |
| “Nenhuma lei existe sobre isso” | “Nenhum trecho encontrado neste recorte” | Indexação pode ser incompleta |
| “Base completa” | “Normas indexadas / Trechos consultáveis” | Contagens verificáveis pela API |

## Referências de pesquisa

A revisão considerou convenções de plataformas de pesquisa jurídica, incluindo Jusbrasil, Lexis+, Harvey e Westlaw, além do Padrão Digital de Governo e WCAG 2.2. Não há cópia de componentes ou identidade desses produtos.

- [WCAG 2.2 (W3C)](https://www.w3.org/TR/WCAG22/)
- [Contraste de elementos não textuais](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast)
- [Padrão Digital de Governo — cores](https://next-ds.estaleiro.serpro.gov.br/fundamentos/cor)
- [Material Design — color roles](https://m3.material.io/styles/color/the-color-system)

## Escopo do MVP e evolução

A página atual reúne os estados de busca e de consulta assistida; ainda **não** existem telas independentes de histórico, detalhe da norma, jurispru­dência consolidada ou análise de contratos. Não adicionar links falsos para rotas inexistentes. A evolução para essas telas deverá preservar os tokens e a hierarquia proposta.

A prévia pública de UI em Railway trabalha com **dados demonstrativos limitados**. O backend Python/PostgreSQL é um serviço separado e ainda necessita validação operacional e controles de abuso antes de expor uma API de IA pública.
