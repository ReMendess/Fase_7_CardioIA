# CardioIA — Fase 7 · Registro de Progresso

> **Documento de acompanhamento da Fase 7**
>
> | Etapa | Situação |
> |---|---|
> | **Etapa A** — Análise das Fases 1 a 6 + documentação da arquitetura | ✅ **CONCLUÍDA** |
> | **Etapa B** — Decisões arquiteturais | ✅ **CONCLUÍDA E APROVADA** |
> | **Etapa C** — Implementação do backend | 🔄 **EM ANDAMENTO** — 2 de 7 itens concluídos |
>
> Documentos produzidos:
> [`ANALISE_ARQUITETURA.md`](ANALISE_ARQUITETURA.md) ·
> [`DECISOES_ARQUITETURAIS.md`](DECISOES_ARQUITETURAIS.md) ·
> [`CONTRATOS_API.md`](CONTRATOS_API.md) ·
> [`MODELO_DADOS.md`](MODELO_DADOS.md) ·
> [`PLANO_SEGURANCA.md`](PLANO_SEGURANCA.md)

---

## 1. Status geral

| Item | Status |
|---|---|
| **Etapa A** — Análise das Fases 1 a 6 | ✅ **Concluída** |
| Documentação da arquitetura (`ANALISE_ARQUITETURA.md`) | ✅ **Criado** (1.977 linhas) |
| **Etapa B** — Decisão 1: estratégia de integração | ✅ **Decidida** |
| **Etapa B** — Decisão 2: contrato comum de API | ✅ **Decidida** |
| **Etapa B** — Decisão 3: banco de dados e autenticação | ✅ **Decidida** |
| **Etapa B** — Decisão 4: gap IoT ↔ Fase 6 | ✅ **Decidida** |
| **Etapa B** — Decisão 5: seleção de frontends | ✅ **Decidida** |
| **Etapa B** — Decisão 6: segurança | ✅ **Decidida** (Q8 autorizado · Q9 não aprovado) |
| **Etapa B** — Arquitetura definitiva | ✅ **APROVADA pelo autor** |
| **Etapa B** — Resoluções Q1–Q10 | ✅ **Todas respondidas** (seção 9.5) |
| `DECISOES_ARQUITETURAIS.md` | ✅ **Criado** |
| `CONTRATOS_API.md` | ✅ **Criado** |
| `MODELO_DADOS.md` | ✅ **Criado** |
| `PLANO_SEGURANCA.md` | ✅ **Criado** |
| Sanitização do `ANALISE_ARQUITETURA.md` (remoção de valores literais) | ✅ **Executada** |
| Propagação das respostas Q1/Q2/Q9 nos 4 documentos | ✅ **Executada** |
| **Etapa C** — item 1 (esqueleto + envelope + erros + `/health`) | ✅ **Concluído** (73 testes) |
| **Etapa C** — item 2 (persistência: SQLAlchemy + SQLite) | ✅ **Concluído** (175 testes) |
| **Etapa C** — item 3 (autenticação: PyJWT + bcrypt + RBAC) | ✅ **Concluído** (275 testes) |
| **Etapa C** — item 4 (integração da Fase 6 + rotas clínicas) | ✅ **Concluído** (409 testes) |
| **Etapa C** — item 5 (`regras_iot` + ingestão de telemetria) | ✅ **Concluído** (470 testes) |
| **Etapa C** — item 6 (adapter da Fase 4 — visão computacional) | ✅ **Concluído** (516 testes) |
| **Etapa C** — item 7 (assistente conversacional — Fase 5) | ✅ **Concluído** (586 testes) |
| **Etapa C** — **todos os 7 itens concluídos** | ✅ |
| **Etapa D** — diagnóstico do frontend da Fase 2 | ✅ **Executado** |
| **Etapa D** — integração Web + Backend | ✅ **Concluída** (65 verificações de smoke, 3 papéis) |
| **Etapa D** — frontend em `frontend/` (cópia integrada do app da Fase 2) | ✅ **Criado** (8 telas, lint e build limpos) |
| **Etapa D** — ajuste no backend (`CORS_ORIGENS` padrão) | ⚠️ **1 alteração justificada** (ver §11.6) |
| Alterações nas Fases 1 a 6 | 🚫 **Nenhuma** (restrição respeitada — verificado com `git status`) |
| Instalação de dependências | 🚫 **Nenhuma nova** (`npm install` do frontend usa o `package.json` herdado da Fase 2) |
| Criação de novas aplicações | 🚫 **Nenhuma** (restrição respeitada) |

### Escopo das etapas concluídas

| Etapa | Escopo |
|---|---|
| **A** | Realizar uma **análise completa das seis fases anteriores** e produzir dois documentos na raiz da Fase 7, sem tocar no código existente |
| **B** | Transformar o diagnóstico em **decisões arquiteturais definitivas**, produzir quatro documentos técnicos e atualizar este registro — **sem implementar código** |

---

## 2. Checklist das atividades solicitadas

| # | Atividade | Status | Resultado |
|---|---|:---:|---|
| 1 | Ler todos os `README.md` das seis fases | ✅ | 6 READMEs lidos integralmente (o da Fase 6 em duas passagens, por tamanho) |
| 2 | Explorar diretórios e arquivos de código-fonte | ✅ | Árvores completas levantadas, excluindo `node_modules/`, `.git/`, `__pycache__/` e `venv/` |
| 3 | Identificar as tecnologias utilizadas | ✅ | Seção 5 do `ANALISE_ARQUITETURA.md` (linguagens, runtimes, IoT, serviços externos) |
| 4 | Identificar frameworks e bibliotecas | ✅ | Seções 5.2 a 5.7 (com versões quando declaradas) |
| 5 | Identificar os backends existentes | ✅ | 3 backends Flask (Fases 3, 4, 5) + 1 núcleo CLI Python (Fase 6) |
| 6 | Identificar os frontends existentes | ✅ | 1 portal web React + Vite (Fase 2) e 2 apps Expo/React Native (Fases 4 e 5) |
| 7 | Identificar os bancos de dados | ✅ | **Nenhum banco em nenhuma fase** — apenas CSV, JSON, `localStorage` e sessão em memória |
| 8 | Identificar APIs e endpoints | ✅ | Seção 8: 5 endpoints implementados + MQTT/SMTP/Serial + 3 APIs externas |
| 9 | Identificar modelos de Machine Learning | ✅ | Seção 9.1: 10 entradas de modelo/técnica, com métricas e status de persistência |
| 10 | Identificar os agentes e LLMs | ✅ | Seção 10: 4 agentes (OpenAI Agents SDK) + Watson (Fase 5) + LLM opcional (Fase 6) |
| 11 | Identificar a implementação IoT da Fase 3 | ✅ | Seção 11: Edge (ESP32/DHT22/LDR/FIFO), Fog (Node-RED), Cloud (HiveMQ), REST+SMTP, LIF |
| 12 | Identificar mecanismos de autenticação | ✅ | Seção 12: nenhum real; 1 simulação (Fase 2) e 1 IAM com chave versionada (Fase 5) |
| 13 | Identificar como cada módulo pode ser executado | ✅ | Seção 13: comandos por fase + tabela resumo com portas e pré-requisitos |
| 14 | Identificar dependências, credenciais e configurações | ✅ | Seção 14: manifestos, variáveis de ambiente, `.env.example` e conflitos conhecidos |

### Entregáveis produzidos

| Arquivo | Caminho | Conteúdo |
|---|---|---|
| `ANALISE_ARQUITETURA.md` | raiz da Fase 7 | 19 seções + apêndice: resumo por fase, tabela Fase × Componentes, tecnologias, estruturas, funcionalidades, APIs, modelos de IA, agentes/LLMs, IoT, autenticação, execução, dependências, reutilização, problemas, limitações, informações desconhecidas e visão de integração |
| `PROGRESSO_FASE7.md` | raiz da Fase 7 | este documento: status, checklist, matriz por fase, decisões, backlog, riscos e pendências |

### Tabela Fase × Componentes (entregável exigido)

Criada na **seção 4** do `ANALISE_ARQUITETURA.md`, com duas visões:
- **4.1** — visão consolidada (foco, backend, frontend, modelos, dados, persistência, autenticação);
- **4.2** — matriz de componentes técnicos (✅/— por fase).

---

## 3. Matriz de progresso por fase

| Fase | Analisada | Documentada | Reutilizável na Fase 7 | Observação principal |
|---|:---:|:---:|:---:|---|
| **1** — Curadoria de dados | ✅ | ✅ | 🟠 parcialmente | Dados existem, mas **nunca foram consumidos** pelas fases seguintes |
| **2** — NLP + portal web | ✅ | ✅ | 🟡 sim | Portal e NLP reaproveitáveis; scripts com caminhos absolutos e modelos não persistidos |
| **3** — IoT Edge/Fog/Cloud | ✅ | ✅ | 🟡 sim | API REST e telemetria úteis; credenciais expostas e gap de 8 features para o modelo |
| **4** — Visão computacional | ✅ | ✅ | 🟡 sim | Modelo `.keras` presente e API funcional; requer TensorFlow e ajuste de porta |
| **5** — Assistente conversacional | ✅ | ✅ | 🟡 sim | API e app bem estruturados; **credenciais Watson versionadas** (risco crítico) |
| **6** — Multiagentes + ML | ✅ | ✅ | 🟢 **sim (núcleo)** | Módulo mais maduro: pacote, contrato, protocolos, testes e artefatos versionados |

### Legenda de reutilização

| Símbolo | Significado |
|---|---|
| 🟢 | Pronto para uso direto |
| 🟡 | Reutilizável com adaptações pequenas/médias |
| 🟠 | Reutilizável apenas com refatoração relevante |

---

## 4. Registro de decisões e restrições respeitadas

### 4.1 Restrições impostas pelo autor e cumprimento

| Restrição | Cumprida? | Como foi verificada |
|---|:---:|---|
| Não modificar os códigos das fases anteriores | ✅ | Nenhum `editor`/comando de escrita foi executado sobre arquivos das Fases 1–6; todas as leituras foram somente-leitura |
| Não criar novas aplicações | ✅ | Apenas dois arquivos de documentação foram criados, na raiz da Fase 7 |
| Não instalar dependências | ✅ | Nenhum `pip install`, `npm install` ou similar foi executado |
| Não implementar funcionalidades | ✅ | Nenhum código de Fase 7 foi escrito |
| Não inventar informações | ✅ | Toda afirmação é rastreável a um arquivo lido; o que não foi encontrado está na seção 18 do `ANALISE_ARQUITETURA.md` como **desconhecido** |
| Identificar como desconhecido o que não estiver disponível | ✅ | 16 itens listados como `[DESCONHECIDO]` / "Informações desconhecidas" |

### 4.2 Decisões tomadas durante a análise

| # | Decisão | Justificativa |
|---|---|---|
| 1 | Excluir `node_modules/`, `.git/`, `__pycache__/` e `venv/` do inventário de código | Não são código-fonte do projeto; inflavam a listagem sem agregar informação arquitetural |
| 2 | Não abrir os arquivos `.pdf` (relatórios das Fases 3–6) | São binários; seu conteúdo foi registrado como desconhecido (item U1) |
| 3 | Citar **literalmente** as credenciais encontradas no documento | São **problemas identificados** que precisam ser visíveis para serem corrigidos — e já estão publicamente versionadas nos repositórios das fases |
| 4 | Não executar nenhum código das fases anteriores | Executar alteraria estado (criar `models/`, subir servidores, escrever CSVs com caminhos absolutos) e violaria a restrição de não modificar |
| 5 | Documentar a arquitetura da Fase 6 com maior profundidade | É o módulo mais maduro e o candidato natural a núcleo de integração |
| 6 | Separar "funcional" de "simulado" na seção 7 | Evita que protótipos (login fake, Wi-Fi simulado, base sintética) sejam confundidos com produto |
| 7 | Manter o documento em português (pt-BR) | Idioma predominante dos READMEs e definido pelo autor |

### 4.3 O que **não** foi feito nesta etapa (e por quê)

| Não feito | Motivo |
|---|---|
| Corrigir portas, caminhos ou credenciais nas fases anteriores | Restrição explícita: não modificar as fases anteriores |
| Treinar/reexecutar modelos das Fases 2, 3 e 4 | Exigiria execução e instalação de dependências |
| Validar se os serviços externos (Watson, HiveMQ) estão ativos | Exigiria rede e credenciais em execução |
| Definir a arquitetura da Fase 7 | É uma decisão de projeto que pertence à etapa seguinte |
| Criar API gateway, backend unificado ou frontend | Fora do escopo desta etapa |

---

## 5. Próximos passos sugeridos (backlog da Fase 7)

> ⚠️ **Nada abaixo foi executado.** É uma proposta de sequência de trabalho, ordenada por dependência
> técnica, derivada das conclusões do `ANALISE_ARQUITETURA.md`. Cada item depende do anterior.

### 5.1 Etapa A — Decisões de arquitetura (antes de qualquer código)

| # | Passo | Entregável esperado |
|---|---|---|
| A1 | Definir o **modelo de integração** (gateway único com *path prefixes* vs. serviços independentes) | Documento de arquitetura da Fase 7 |
| A2 | Definir o **envelope de resposta comum** das APIs | Especificação JSON (inspirada em `RespostaDaExecucao`) |
| A3 | Definir a **estratégia de autenticação/autorização** (papéis, tokens) | Especificação de segurança |
| A4 | Definir a **persistência** (banco de dados e modelo de dados) | Diagrama de dados |
| A5 | Definir como resolver o **gap de 8 features IoT → modelo de risco** (seção 15.4 do documento de análise) | Tabela de mapeamento explícita |
| A6 | Definir o **destino do frontend** (unificar portal + app ou manter dois clientes) | Decisão arquitetural de UX |
| A7 | Definir a **estratégia de empacotamento** (venv por serviço, containers, monorepo) | Plano de ambientes |

### 5.2 Etapa B — Integração técnica (depende da Etapa A)

| # | Passo | Depende de |
|---|---|---|
| B1 | Criar o **gateway / API unificada** | A1, A2 |
| B2 | Expor a **Fase 6 via HTTP** (`/risco/avaliar`) reutilizando `executar_pipeline` e `como_dicionario()` | B1 |
| B3 | Padronizar **erros e códigos HTTP** nos serviços das Fases 3, 4 e 5 | A2 |
| B4 | Resolver o **conflito da porta 5000** (portas distintas ou proxy reverso) | B1 |
| B5 | Integrar a **Fase 4** (`/predict`) como *tool*/serviço | B2, B4 |
| B6 | Integrar a **Fase 5** (`/api/chat`) como camada conversacional | B4 |
| B7 | Integrar a **Fase 3** (`/sinais`) como fonte de telemetria | A5, B2 |
| B8 | Integrar a **Fase 2** (NLP) após refatorar caminhos absolutos | B1 |

### 5.3 Etapa C — Segurança e qualidade (paralela à Etapa B)

| # | Passo | Prioridade |
|---|---|---|
| C1 | **Rotacionar** a API key do Watson e externalizá-la para `.env` | 🔴 Crítica |
| C2 | Externalizar credenciais MQTT e SMTP (Fase 3) | 🔴 Alta |
| C3 | Remover `debug=True` das execuções de produção | ⚠️ Média |
| C4 | Implementar autenticação real e autorização por papel | 🔴 Alta |
| C5 | Fixar versões nos `requirements.txt` das Fases 4 e 5 | ⚠️ Média |
| C6 | Adicionar testes de integração ponta a ponta | ⚠️ Média |
| C7 | Adicionar logs estruturados e observabilidade | 🟢 Desejável |

### 5.4 Etapa D — Produto (depende de B e C)

| # | Passo |
|---|---|
| D1 | Unificar o frontend e conectar ao gateway |
| D2 | Implementar histórico clínico e auditoria das decisões |
| D3 | Preparar build/deploy (containers, variáveis de ambiente, documentação de operação) |
| D4 | Documentar a API (OpenAPI) e versioná-la |

---

## 6. Riscos e bloqueios conhecidos

| # | Risco | Fase(s) | Impacto | Mitigação sugerida |
|---|---|---|---|---|
| R1 | **Credenciais de produção expostas** (Watson, HiveMQ, Gmail) | 3, 5 | 🔴 Alto — uso indevido e custos | Rotacionar todas as chaves; mover para `.env` (padrão já usado na Fase 6) |
| R2 | **Conflito de porta 5000** | 3, 4, 5 | 🔴 Alto — impede execução conjunta | Portas distintas ou gateway com proxy reverso |
| R3 | **Gap de 8 features IoT → modelo** | 3 → 6 | 🔴 Alto — integração falha por contrato | Definir origem explícita de cada feature antes de integrar |
| R4 | **Contrato rígido da Fase 6** (`extra="forbid"`, sem negativos/NaN) | 6 | ⚠️ Médio — rejeição de payloads | Validação e normalização na borda do gateway |
| R5 | **Conflito de versões Python/sklearn/TensorFlow** | 2, 4, 6 | ⚠️ Médio — ambientes incompatíveis | Um ambiente isolado por serviço (venv/container) |
| R6 | **Caminhos absolutos nos scripts da Fase 2** | 2 | ⚠️ Médio — scripts não executam | Refatorar para caminhos relativos (na Fase 7) |
| R7 | **Modelos das Fases 2 e 3 não persistidos** | 2, 3 | ⚠️ Médio — reuso exige retreino | Retreinar e versionar artefatos |
| R8 | **Dependência de serviços externos** (Watson, HiveMQ, OpenAI) | 3, 5, 6 | ⚠️ Médio — indisponibilidade/cota | Prever *fallbacks* e modo simulado (a Fase 6 já tem) |
| R9 | **Base sintética e alvo determinístico** | 6 | ⚠️ Médio — risco de interpretação clínica indevida | Manter os avisos de uso visíveis em toda a UI |
| R10 | **Ausência de banco de dados e de autenticação real** | 1–6 | 🔴 Alto — sem histórico nem controle de acesso | Implementar na Fase 7 |
| R11 | **Frontends em stacks diferentes** | 2, 4, 5 | ⚠️ Médio — duplicação de esforço | Decisão arquitetural explícita (Etapa A6) |
| R12 | **Documentos referenciados e ausentes na Fase 6** | 6 | 🟢 Baixo — perda de rastreabilidade | Recuperar os arquivos ou ajustar o README |

---

## 7. Pendências de informação

Itens que dependem de confirmação do autor ou de verificação em tempo de execução (detalhamento na
seção 18 do `ANALISE_ARQUITETURA.md`):

| # | Pendência | Necessária para |
|---|---|---|
| 1 | Enunciado/requisitos oficiais da Fase 7 | Definir escopo e entregáveis |
| 2 | Estratégia de integração pretendida pelo autor | Etapa A1 |
| 3 | Confirmação de que a instância Watson está ativa e se a chave deve ser rotacionada | Etapa C1 |
| 4 | Confirmação de que o broker HiveMQ está ativo | Integração da Fase 3 |
| 5 | Decisão sobre a origem das 8 features ausentes (IoT → modelo) | Etapa A5 |
| 6 | Disponibilização dos documentos ausentes da Fase 6 (`plano_implementacao.md`, `relatorio_tecnico.md`, `arquitetura_multiagente.pdf`) | Rastreabilidade |
| 7 | Decisão sobre manter ou descartar o corpus/dataset da Fase 1 | Reuso de dados |
| 8 | Decisão sobre a stack de frontend final (portal web, app ou ambos) | Etapa A6 |
| 9 | Decisão sobre banco de dados | Etapa A4 |

---

## 8. Histórico de entregas

| Data | Etapa | Entregável | Situação |
|---|---|---|---|
| 31/10/2026 | **Etapa A** — Análise das Fases 1 a 6 | `ANALISE_ARQUITETURA.md` | ✅ Concluído |
| 31/10/2026 | **Etapa A** — Registro de progresso | `PROGRESSO_FASE7.md` | ✅ Concluído |
| 31/10/2026 | **Etapa B** — Decisões arquiteturais | `DECISOES_ARQUITETURAIS.md` | ✅ Concluído |
| 31/10/2026 | **Etapa B** — Contratos de API | `CONTRATOS_API.md` | ✅ Concluído |
| 31/10/2026 | **Etapa B** — Modelo de dados | `MODELO_DADOS.md` | ✅ Concluído |
| 31/10/2026 | **Etapa B** — Plano de segurança | `PLANO_SEGURANCA.md` | ✅ Concluído |
| 31/10/2026 | **Etapa B** — Sanitização | `ANALISE_ARQUITETURA.md` (sem valores de credencial) | ✅ Executado |
| 31/10/2026 | **Etapa B** — Atualização | `PROGRESSO_FASE7.md` (esta seção) | ✅ Executado |
| 31/10/2026 | **Etapa B** — Resoluções do autor (Q1–Q10) | Propagação em 4 documentos + este registro | ✅ Executado |
| — | **Etapa C** — Implementação do backend | *(a definir)* | ✅ **AUTORIZADA** — a iniciar |

### Resumo do que foi analisado (Etapa A)

| Métrica | Valor |
|---|---|
| Fases analisadas | **6** |
| Repositórios Git independentes | **6** |
| READMEs lidos | **6** |
| Backends HTTP identificados | **3** (Fases 3, 4, 5) |
| Núcleos CLI/notebook | **4** (Fases 1, 2, 3, 4, 6) |
| Frontends identificados | **3** (1 portal web + 2 apps Expo) |
| Endpoints REST mapeados | **5** |
| Protocolos não-HTTP mapeados | **3** (MQTT, SMTP, Serial) |
| Modelos/técnicas de IA catalogados | **10** |
| Agentes catalogados | **4** (Fase 6) |
| Bancos de dados encontrados | **0** |
| Testes automatizados encontrados | **290** (exclusivos da Fase 6) |
| Problemas identificados | **27** (7 segurança, 8 portabilidade, 6 consistência, 6 dados) |
| Informações marcadas como desconhecidas | **16** |

---

## 9. Etapa B — Decisões arquiteturais (concluída)

### 9.1 Checklist das atividades solicitadas

| # | Atividade | Status | Resultado |
|---|---|:---:|---|
| 1 | Comparar as 3 alternativas de integração da Fase 6 (import / subprocesso / serviço) nos 6 critérios pedidos | ✅ | Seção 3 de `DECISOES_ARQUITETURAIS.md` |
| 2 | Apresentar recomendação fundamentada | ✅ | **A — import direto** (com **C** apenas para a Fase 4) |
| 3 | Definir como as Flask das Fases 3, 4 e 5 entram no backend central sem duplicar lógica | ✅ | Seção 3.4 — estratégia híbrida + declaração honesta da duplicação controlada |
| 4 | Definir o padrão de comunicação entre web, mobile, IoT, backend, modelos e LLM | ✅ | Seção 4 de `DECISOES_ARQUITETURAIS.md` + seções 1–2 de `CONTRATOS_API.md` |
| 5 | Definir schemas Pydantic (Paciente, Monitoramento, Diagnóstico, Predição, Assistente, Imagem) | ✅ | Seção 4 de `CONTRATOS_API.md` (7 schemas) |
| 6 | Identificar campos existentes × a introduzir | ✅ | Seção 5 de `CONTRATOS_API.md` (~22 reutilizados, ~14 novos) |
| 7 | Não presumir compatibilidade entre contratos | ✅ | Seção 7 de `CONTRATOS_API.md` — **9 incompatibilidades** (I1–I9) |
| 8 | Comparar alternativas de banco para o MVP (incluindo SQLite) | ✅ | Seção 5.1 de `DECISOES_ARQUITETURAIS.md` |
| 9 | Definir estrutura de dados, relacionamentos e persistência do histórico | ✅ | Seções 2–5 de `MODELO_DADOS.md` (11 tabelas) |
| 10 | Definir autenticação centralizada, JWT, hash, RBAC e proteção de dados | ✅ | Seções 5.3 e 6 de `MODELO_DADOS.md` |
| 11 | Investigar o contrato de entrada do modelo (nome, tipo, unidade, obrigatoriedade, origem) | ✅ | Seção 6.1 de `DECISOES_ARQUITETURAIS.md` |
| 12 | Montar a tabela de gap com as 5 colunas pedidas | ✅ | Seção 6.2 de `DECISOES_ARQUITETURAIS.md` |
| 13 | Avaliar as 3 alternativas (A/B/C) do gap IoT e recomendar a mais segura | ✅ | Seções 6.3–6.4 — **alternativa C adotada** |
| 14 | Não inventar valores para completar as features | ✅ | **Nenhum valor default**; as 10 features são obrigatórias sem default |
| 15 | Analisar os 3 frontends e recomendar web e mobile principais | ✅ | Seção 7 — Web = **Fase 2**; Mobile = **Fase 5**; Fase 4 = fonte de componentes |
| 16 | Definir funcionalidades reaproveitadas e as do MVP | ✅ | Seções 7.3 e 7.4 — 8 funcionalidades no MVP; **nenhum frontend novo** |
| 17 | Elaborar plano de credenciais: arquivos, tipos, rotação e remoção do histórico | ✅ | Seções 2–6 de `PLANO_SEGURANCA.md` |
| 18 | **Não expor valores das credenciais nos documentos** | ✅ | Referências mascaradas em todos os 5 documentos |
| 19 | **Não alterar os repositórios anteriores** | ✅ | `git status --porcelain` vazio nos 6 repositórios |
| 20 | Criar `DECISOES_ARQUITETURAIS.md` | ✅ | Criado |
| 21 | Criar `CONTRATOS_API.md` | ✅ | Criado |
| 22 | Criar `MODELO_DADOS.md` | ✅ | Criado |
| 23 | Criar `PLANO_SEGURANCA.md` | ✅ | Criado |
| 24 | Atualizar `PROGRESSO_FASE7.md` | ✅ | Esta seção |
| 25 | Apresentar decisões, justificativas, riscos e recomendações | ✅ | Seções 3–10 de `DECISOES_ARQUITETURAIS.md` |
| 26 | Apresentar a arquitetura definitiva para aprovação | ✅ | Seção 9 de `DECISOES_ARQUITETURAIS.md` |
| 27 | **Não implementar código** | ✅ | Nenhuma linha de código escrita |

### 9.2 Resumo das decisões

| Decisão | Escolha | Justificativa central |
|---|---|---|
| **D1 — Integração da Fase 6** | **A — import direto** no FastAPI | Zero duplicação, exceções tipadas preservadas, melhor desempenho, ambiente já compatível; **C** só para a Fase 4 (TensorFlow isolado); **B** só para operação |
| **D2 — Contrato comum** | **`RespostaAPI[T]`** generalizando o `RespostaDaExecucao` | Reaproveita contrato testado; cobre os 6 clientes; preserva "falha nunca vira sucesso" |
| **D3 — Banco e autenticação** | **SQLite + SQLAlchemy 2.0** com porta de repositório; **PyJWT + bcrypt**; RBAC de 3 papéis | Nenhuma instalação nova; integridade transacional; migração para PostgreSQL sem redesenho |
| **D4 — Gap IoT ↔ Fase 6** | **Alternativa C** — simulação IoT separada do modelo; **sem defaults** | Única opção que não inventa dados nem falsifica validade clínica; não altera a Fase 6 |
| **D5 — Frontends** | Web = **Fase 2**; Mobile = **Fase 5**; Fase 4 = fonte de componentes | Web "de verdade" única; mobile mais recente e melhor estruturado; nenhum frontend novo |
| **D6 — Segurança** | **Rotação imediata** + externalização + limpeza de histórico (coordenada) + prevenção + governança | Segredo versionado é segredo comprometido |

### 9.3 Arquitetura definitiva (resumo)

```text
Web (Fase 2) + Mobile (Fase 5)
        │ HTTPS/JSON · Bearer JWT · /api/v1/*
        ▼
BACKEND CENTRAL — FastAPI + uvicorn (:8000)
   auth (PyJWT + bcrypt + RBAC) · envelope RespostaAPI[T] · enum de erros
   ├─ import direto:  cardioia (Fase 6)  → 4 agentes + modelo + 10 protocolos
   ├─ import direto:  IBM_API (Fase 5)   → assistente conversacional
   ├─ módulo próprio: regras_iot (Fase 3, origem declarada)
   └─ adapter HTTP:   Fase 4 (Flask + TensorFlow, :5001)
        │
        ▼
PERSISTÊNCIA — SQLAlchemy 2.0 + SQLite (11 tabelas)
   histórico append-only · auditoria · id_execucao como chave de correlação

INGESTÃO IoT (inalterada): ESP32 ──MQTT/TLS 8883──▶ HiveMQ ──▶ backend
```

**Princípios inegociáveis:** Python calcula e o LLM apenas redige · contrato único de saída · falha
nunca vira sucesso · segredos só em ambiente · histórico append-only · avisos clínicos sempre
visíveis · nenhum valor de feature inventado · núcleo testável sem LLM.

### 9.4 Restrições respeitadas na Etapa B

| Restrição | Verificação |
|---|---|
| Não implementar código | Nenhum arquivo de código foi criado ou editado |
| Não expor valores de credenciais | Referências mascaradas; **sanitização executada** no `ANALISE_ARQUITETURA.md` (9 pontos corrigidos, 0 ocorrências remanescentes) |
| Não alterar repositórios anteriores | `git status --porcelain` **vazio** nos 6 repositórios |
| Não instalar dependências | Nenhuma instalação executada (apenas consulta de versões já instaladas) |
| Não criar novos frontends | Apenas recomendação documentada |
| Não inventar compatibilidade | 9 incompatibilidades explicitadas em `CONTRATOS_API.md` |
| Não inventar valores de features | 8 das 10 features declaradas **sem fonte**; nenhum default |

### 9.5 Resoluções do autor (Etapa B encerrada)

| # | Questão | **Resolução** | Impacto propagado |
|---|---|---|---|
| **Q1** | `pico_risco` é risco de sobrecarga assistencial **ou** clínico individual? | ✅ **CLÍNICO INDIVIDUAL** | entidade `snapshots_assistenciais` → **`pacientes`**; features movidas do cadastro para a **avaliação**; interpretação das 10 features documentada; achado remanescente **A4** |
| **Q2** | `temperatura` é ambiente **ou** corporal? | ✅ **CORPORAL** | ❌ **DHT22 descartado** como fonte; gap IoT passa de 2/10 para **1/10**; achado remanescente **A3** (distribuição do gerador) |
| **Q3** | Alternativa **C** para o gap IoT | ✅ **APROVADA** | endpoint de avaliação exige as 10 features, **sem defaults** |
| **Q4** | **SQLite + SQLAlchemy** | ✅ **APROVADA** | `MODELO_DADOS.md` vigente |
| **Q5** | **PyJWT + bcrypt** + RBAC de 3 papéis | ✅ **APROVADA** | autenticação definida |
| **Q6** | **FastAPI + uvicorn** | ✅ **APROVADA** | Decisão D1 confirmada |
| **Q7** | Sanitizar a documentação | ✅ **EXECUTADA** | 0 valores sensíveis nos 6 documentos |
| **Q8** | **Rotacionar** as credenciais | ✅ **AUTORIZADA** | execução pelo titular das contas (IBM/HiveMQ/Google) |
| **Q9** | **Reescrever o histórico Git** | ❌ **NÃO APROVADA** | reescrita **descartada**; adotada a **alternativa mínima** (rotação + aviso) |
| **Q10** | **Instalar** ferramenta de varredura de segredos | ✅ **AUTORIZADA** | a executar na Etapa C |

> ✅ **Nenhuma questão permanece pendente.** A **Etapa C está desbloqueada**.

### 9.6 Impactos materiais das respostas Q1, Q2 e Q9

| Resposta | Documentos alterados | Mudança concreta |
|---|---|---|
| **Q1 — clínico individual** | `DECISOES_ARQUITETURAIS.md` (§2.3, §2.5, §5.4, §9, §11) · `CONTRATOS_API.md` (§4.1, §5, §6, §7, §8) · `MODELO_DADOS.md` (§2, §3.3, §3.4, §4, §5, §8) | `snapshots_assistenciais` → **`pacientes`** (identidade) + **10 features realocadas para `avaliacoes_de_risco`** |
| **Q2 — corporal** | `DECISOES_ARQUITETURAIS.md` (§2.3, §2.4, §6.2, §6.4) · `CONTRATOS_API.md` (§4.1, §6.1, §7) | **DHT22 removido** do mapeamento; gap **2/10 → 1/10**; `temperatura` marcada como **baixa confiança** |
| **Q9 — não aprovado** | `PLANO_SEGURANCA.md` (§1, §6, §9) | Reescrita do histórico **descartada**; **alternativa mínima** passa a ser o plano definitivo |

### 9.7 Achados remanescentes registrados (não bloqueiam)

| # | Achado | Situação |
|---|---|---|
| **A3** | A distribuição de `temperatura` no gerador da Fase 6 é de **ambiente** (média 24 °C), embora a semântica seja **corporal** | ⚠️ Documentado; feature marcada como **baixa confiança**; **não** corrigível sem alterar a Fase 6 |
| **A4** | **8 das 10 features** não são medições individuais (5 de contexto + 3 com nome de média) | ⚠️ Interpretação individual documentada; nomes **preservados** (contrato fechado) |

---

## 10. Etapa C — Implementação do backend

### 10.1 Progresso dos itens

| # | Item | Status | Evidência |
|---|---|:---:|---|
| **1** | Esqueleto FastAPI + envelope `RespostaAPI[T]` + enum de erros + `GET /api/v1/health` | ✅ **Concluído** | `backend/` · 73 testes · smoke test do uvicorn OK |
| **2** | Persistência (SQLAlchemy 2.0 + SQLite): 12 tabelas + controle de versão + repositórios | ✅ **Concluído** | **175 testes** · 13 tabelas criadas · CLI de esquema OK |
| 3 | Autenticação (PyJWT + bcrypt + RBAC) | ✅ **Concluído** | `backend/app/seguranca/` · `rotas/auth.py` · **275 testes** · smoke test real OK |
| 4 | Integração da Fase 6 (import direto + cache + mapeador) | ✅ **Concluído** | `backend/app/integracao/` + `rotas/{pacientes,avaliacoes}.py` · **409 testes** · smoke test do fluxo clínico OK |
| 5 | Módulo `regras_iot` + ingestão de telemetria | ✅ **Concluído** | `backend/app/regras_iot.py` + `rotas/iot.py` · **470 testes** · regras verificadas contra o serviço Flask legado |
| 6 | Adapter da Fase 4 (visão computacional) | ✅ **Concluído** | `backend/app/integracao/fase_4.py` + `rotas/imagens.py` · **516 testes** · smoke test com HTTP real entre processos |
| 7 | Assistente conversacional (Fase 5) | ✅ **Concluído** | `backend/app/integracao/fase_5.py` + `rotas/assistente.py` · **586 testes** · smoke test prova que a chave vazada **não** é herdada |

### 10.2 Entregas do item 1

| Arquivo | Conteúdo |
|---|---|
| `backend/.env.example` | nomes das variáveis, **sem valores** |
| `backend/.gitignore` | exclui `.env`, banco local, caches |
| `backend/requirements.txt` | versões fixadas — **nenhuma dependência nova** |
| `backend/README.md` | execução, contrato, erros, banco e segurança |
| `backend/app/config.py` | configuração + **falha rápida** no `JWT_SECRET` (≥ 32 chars) |
| `backend/app/contratos/envelope.py` | `RespostaAPI[T]` + `StatusDaResposta` (4 valores da Fase 6) |
| `backend/app/contratos/erros.py` | `CodigoDeErro` (21) + `ErroDaAPI` + mapeamento HTTP |
| `backend/app/rotas/saude.py` | `GET /api/v1/health` |
| `backend/app/main.py` | aplicação, CORS restrito, 4 handlers de erro e `lifespan` |

### 10.2.1 Entregas do item 2

| Arquivo | Conteúdo |
|---|---|
| `backend/app/dados/base.py` | tipo `DatetimeUTC`, `criar_engine` (PRAGMAs), fábrica de sessões, dependência `get_sessao` |
| `backend/app/dados/enums.py` | 9 enums persistidos como **TEXT + CHECK** |
| `backend/app/dados/modelos.py` | **12 tabelas de domínio** + `versoes_do_esquema` (controle técnico) |
| `backend/app/dados/esquema.py` | `create_all`, validação de versão e **CLI** (`--verificar`/`--recriar`) |
| `backend/app/dados/repositorios/` | 6 módulos: identidade, assistencial, telemetria, análises, conversas, auditoria |
| `backend/app/config.py` | nova propriedade `url_do_banco` (resolve caminho relativo contra a raiz do backend) |
| `backend/app/main.py` | engine + fábrica de sessões no `state`; **banco preparado no `lifespan`** |
| `backend/tests/test_dados_*.py` | 4 arquivos: tipos, esquema, modelos e repositórios |

### 10.2.2 Entregas do item 3

| Arquivo | Conteúdo |
|---|---|
| `backend/app/seguranca/senhas.py` | bcrypt: hash, verificação, custo configurável, recusa de senha > 72 bytes, tempo de resposta igualado |
| `backend/app/seguranca/tokens.py` | access token **JWT** (PyJWT, HS256) + refresh **opaco** (SHA-256 no banco) |
| `backend/app/seguranca/limite_de_tentativas.py` | limitador de login em memória (5 falhas / 5 min), *thread-safe* |
| `backend/app/seguranca/dependencias.py` | `obter_usuario_atual`, `exigir_papeis` (RBAC), `UsuarioAutenticado` |
| `backend/app/contratos/autenticacao.py` | DTOs de login, refresh, logout e usuário público |
| `backend/app/rotas/auth.py` | `POST /auth/login` · `/refresh` (rotação) · `/logout` · `GET /auth/me` |
| `backend/tests/test_seguranca_*.py` | 4 arquivos: senhas, tokens, limitador e RBAC |
| `backend/tests/test_rota_auth.py` | 30 testes das rotas de autenticação |

### 10.2.3 Entregas do item 4 (bloco 1 — camada de integração)

| Arquivo | Conteúdo |
|---|---|
| `backend/app/integracao/fase_6.py` | `sys.path.append` (M2) + **import tardio** (M1) + `disponibilidade()` barata via `find_spec` |
| `backend/app/integracao/traducao.py` | exceções tipadas da Fase 6 → `CodigoDeErro` (7 regras, subclasses antes da base) |
| `backend/app/integracao/modelo.py` | `CacheDoModelo` (M3): `.pkl` lido **uma vez**, *double-checked locking*, aquecimento best-effort |
| `backend/app/integracao/mapeador.py` | mapeador puro, contrato fechado **sem defaults** + avisos A3/A4 + checagem de *drift* |
| `backend/app/rotas/saude.py` | novo campo `integracao_da_fase_6` no `/health` (verificação **sem** importar o pacote) |
| `backend/app/config.py` | `AQUECER_MODELO_NO_STARTUP` (padrão ligado; desligado em teste) |
| `backend/app/main.py` | `cache_do_modelo` no `state` + aquecimento no `lifespan` (nunca derruba o boot) |
| `backend/tests/test_integracao_*.py` | 5 arquivos: ponte, cache, mapeador, tradução e pipeline real |

### 10.2.4 Entregas do item 4 (bloco 2 — rotas clínicas)

| Arquivo | Conteúdo |
|---|---|
| `backend/app/contratos/assistencial.py` | DTOs de paciente e avaliação (`features` é `dict[str, Any]` de propósito) |
| `backend/app/rotas/pacientes.py` | `POST /pacientes` (201) · `GET /pacientes` · `GET /pacientes/{id}` |
| `backend/app/rotas/avaliacoes.py` | `POST /avaliacoes` · `GET /avaliacoes` · `GET /avaliacoes/{id_execucao}` |
| `backend/app/rotas/apoio.py` | helpers compartilhados: metadados, IP, papéis (`SomenteMedico`/`LeituraClinica`) e auditoria |
| `backend/app/contratos/envelope.py` | `resposta_de_erro` ganhou `dados` opcional (falha que carrega diagnóstico) |
| `backend/app/dados/repositorios/assistencial.py` | `listar` passou a aceitar `status` **e** `id_paciente` juntos |
| `backend/tests/test_rota_pacientes.py` | 21 testes |
| `backend/tests/test_rota_avaliacoes.py` | 34 testes (inclui o pipeline real em modo simulado) |

**Achado do ambiente:** neste workspace o pacote `cardioia` também está acessível por
`PYTHONPATH` (aponta para `Fase_6/cardioia_Fase6/src`). Consequência para o código:
`importar()` **não** aborta quando a pasta configurada não existe — quem decide é o
import. Os testes que precisam exercitar o caminho de falha rodam em subprocesso com
`PYTHONPATH` removido.

**Decisão de HTTP documentada:** `POST /avaliacoes` responde **HTTP 200 mesmo quando o
envelope traz `status=ERRO`**. O HTTP responde "a avaliação rodou e foi registrada"; o
campo `status` responde "qual foi o resultado". A Fase 6 também reporta falha de execução
como conteúdo (não como exceção), então o contrato integral — inclusive a trilha de
`passos`, que explica *onde* quebrou — é preservado em `dados`.

### 10.2.5 Entregas do item 5 (`regras_iot` + telemetria)

| Arquivo | Conteúdo |
|---|---|
| `backend/app/regras_iot.py` | regras de risco da Fase 3 (limiares `38`/`120`, cadeia `if/elif`), com a fonte normativa declarada |
| `backend/app/contratos/telemetria.py` | DTOs de leitura (`PedidoDeLeitura`, `LeituraDeMonitoramento`) |
| `backend/app/contratos/paginacao.py` | constantes de paginação compartilhadas (extraídas de `assistencial.py`) |
| `backend/app/rotas/iot.py` | `POST /iot/leituras` · `GET /iot/leituras` |
| `backend/app/seguranca/dependencias.py` | `obter_origem_da_telemetria` + `OrigemDaTelemetria` (chave de dispositivo ou `OPERADOR`) |
| `backend/app/config.py` | `IOT_DEVICE_KEY` + `CANDIDATO_FASE_3` (fonte normativa para o teste de comparação) |
| `backend/app/dados/repositorios/telemetria.py` | `ultimas` passou a aceitar `deslocamento` |
| `backend/tests/test_regras_iot.py` | 21 testes — **inclui a comparação contra o Flask legado** |
| `backend/tests/test_rota_iot.py` | 40 testes |

**Como a "duplicação controlada" foi verificada:** `DECISOES_ARQUITETURAIS.md` §3.4 exige,
para cada ponto de duplicação, "um teste que compare o comportamento novo com o da origem".
Isso é feito **executando o `Ir_Alem1/server.py` de verdade** (Flask 3.1.2 está instalado):
o teste carrega o módulo, substitui `enviar_email` por um *no-op* (a senha na origem é o
placeholder `"SECRET"`, então o SMTP nunca funcionou) e compara a resposta de
`POST /sinais` com `avaliar_sinais` sobre **32 combinações**.

**Divergências declaradas (duas):**

| # | Divergência | Por quê |
|---|---|---|
| 1 | Sinal ausente **não** quebra a avaliação | A origem fazia `if temperatura > 38` sem tratar `None` → `TypeError` → **500**. O contrato da Fase 7 permite enviar só `bpm`. Há teste que fixa o 500 da origem |
| 2 | E-mail de alerta **não** foi portado | As credenciais SMTP estavam *hardcoded* com senha placeholder — o envio **nunca funcionou**. O alerta é entregue em `avisos` + trilha de auditoria |

### 10.2.6 Entregas do item 6 (adapter da Fase 4)

| Arquivo | Conteúdo |
|---|---|
| `backend/app/integracao/fase_4.py` | adapter HTTP: multipart `image`, validação da resposta, mapeamento de erros, **conhecimento do artefato** (I9) |
| `backend/app/contratos/visao.py` | `ResultadoDeDiagnostico` + `MIMES_ACEITOS` + `LIMITACOES_DA_VISAO` |
| `backend/app/rotas/imagens.py` | `POST /imagens` (multipart, `MEDICO`) com endurecimento de tipo e tamanho |
| `backend/app/config.py` | `SERVICO_VISAO_TOKEN` · `SERVICO_VISAO_TIMEOUT_SEGUNDOS` · `LIMITE_DE_UPLOAD_MB` |
| `backend/tests/test_integracao_fase_4.py` | 22 testes — inclui **constantes conferidas contra o fonte da Fase 4** |
| `backend/tests/test_rota_imagens.py` | 24 testes |
| `backend/tests/conftest.py` | `ServicoDeVisaoFalso` (serviço falso compartilhado por sessão) |

**Por que um serviço falso:** o `app.py` da Fase 4 carrega TensorFlow no *import* e
**TensorFlow não está instalado** neste ambiente — a ausência dele é justamente a razão da
Decisão 1-C (serviço isolado). O falso reproduz o contrato real (campo `image`, chaves
`class`/`confidence`, regra `probability > 0.5`) e permite simular 500, corpo inválido e
lentidão, que o serviço real não produz sob demanda. O smoke test faz a chamada **entre
processos**, por HTTP real.

**Conhecimento do artefato verificado (risco R6 / achado I9):** a Fase 4 **não** informa o
nome do modelo nem o limiar; o backend os declara. Seis testes leem `Ir_Alem2/backend/app.py`
e conferem que as constantes **não divergiram** do fonte normativo.

**Duas decisões de mapeamento de erro:**

| Situação | Código | Motivo |
|---|---|---|
| Serviço inalcançável (DNS/recusa) | `ERRO_DE_SERVICO_DE_VISAO` (502) | "não foi possível falar com o serviço" |
| Serviço não responde no prazo | `TIMEOUT_EXTERNO` (504) | "não respondeu a tempo" — código herdado da Fase 5, já existente no enum |
| Serviço responde fora do contrato | `ERRO_DE_SERVICO_DE_VISAO` (502) | Um `class` desconhecido **não** pode virar diagnóstico silencioso |

**Achado do ambiente:** conectar a `127.0.0.1:<porta fechada>` **não é recusado** aqui
(Windows) — o firewall descarta o pacote e a tentativa só termina no *timeout*, o que faria o
teste medir o sistema operacional em vez do adapter. Os testes usam um host `.invalid`
(RFC 2606), que falha em ~0,4 s de forma determinística.

### 10.3 Conformidade com as decisões aprovadas

| Decisão | Verificação |
|---|---|
| **D1** — FastAPI + import direto | ✅ FastAPI 0.119.0; **nenhum** import da Fase 6 até aqui |
| **D2** — envelope `RespostaAPI[T]` | ✅ `status` com os **4 valores** da Fase 6; erro estruturado; `extra="forbid"` |
| **D2** — enum derivado do que já existe | ✅ 5 códigos **herdados da Fase 5** + 7 derivados das exceções da Fase 6 |
| **D3** — SQLite + SQLAlchemy 2.0 com porta de repositório | ✅ `sqlalchemy==2.0.49`; acesso **somente** por repositórios |
| **D3** — PyJWT + bcrypt (sem `python-jose`/`passlib`) | ✅ configurado, ainda não usado (item 3) |
| **D6** — falha rápida sem segredo | ✅ `import app.main` **falha** sem `JWT_SECRET` (exit 1) |
| **D6** — CORS restrito | ✅ origens da configuração; cookies desabilitados |
| **Q1** — clínico individual | ✅ `pacientes` = identidade; **as 10 features vivem na avaliação** (estado datado) |
| **Q2** — `temperatura` corporal | ✅ nenhuma correspondência com o DHT22 no código; telemetria persistida **sem** alimentar o modelo |
| **Q4** — SQLite aprovado | ✅ implementado, com migração para PostgreSQL como troca de `DATABASE_URL` |
| **Modelo de dados** | ✅ 12 tabelas conforme `MODELO_DADOS.md` §3, com CHECK/UNIQUE/FK e índices declarados |

### 10.4 Validações executadas

| Verificação | Resultado |
|---|---|
| Suíte de testes (`python -m pytest`) | ✅ **175 passed** em 7,75 s |
| Smoke test real do uvicorn | ✅ `GET /api/v1/health` → **HTTP 200** + envelope completo |
| Esquema criado no startup | ✅ **13 tabelas** no arquivo real (`cardioia.db`) |
| CLI de esquema | ✅ `--verificar` → `[ok] esquema na versao 1.` |
| Descoberta da Fase 6 | ✅ `presente: true` — localizou o modelo real sem caminho absoluto |
| Falha rápida sem `JWT_SECRET` | ✅ `ErroDeConfiguracao` + exit code **1** |
| FKs aplicadas | ✅ `PRAGMA foreign_keys=ON` verificado; `RESTRICT`/`CASCADE`/`SET NULL` testados |
| Transação atômica do agregado | ✅ falha nas filhas **não** grava a avaliação |
| Credenciais em `/health` | ✅ reportadas apenas como **booleano** |
| Alterações nas Fases 1 a 6 | ✅ **nenhuma** (`git status` vazio nos 6 repositórios) |

### 10.5 Observações dos itens 1 e 2

| # | Observação |
|---|---|
| 1 | **O `/health` não executa o modelo** — apenas verifica a existência dos arquivos (`verificacao: "existencia_de_arquivos"`) |
| 2 | O mapa HTTP→código de erro é **muitos-para-um** e **não** é inverso do mapa código→HTTP; a propriedade garantida é a **preservação da classe** (4xx continua 4xx) — verificada por teste |
| 3 | `limitacoes` nasce vazio de propósito no envelope; nos endpoints de decisão (item 4) é preenchido com `LIMITACOES_PADRAO` da Fase 6, **sem duplicar** o texto |
| 4 | **Tabela de controle `versoes_do_esquema`** foi introduzida (não é de domínio) porque `alembic` não existe neste ambiente — documentada em `MODELO_DADOS.md` §3.12 |
| 5 | **Importar `app.main` não cria arquivo de banco**: o esquema é preparado no `lifespan` (startup), evitando efeito colateral em disco no import |
| 6 | O tipo `DatetimeUTC` existe porque o **SQLite não armazena timezone** — sem ele, datas voltariam *naive* e comparações falhariam |
| 7 | `PRAGMA foreign_keys=ON` é obrigatória: sem ela o SQLite **ignora** as FKs declaradas, e as regras de exclusão deixariam de valer em silêncio |
| 8 | Erros de constraint são traduzidos: **`CONFLITO`** (409) para UNIQUE/FK/CHECK e **`CONTRATO_VIOLADO`** (422) para valor recusado (ex.: enum fora do domínio) |
| 9 | O `url_do_banco` resolve caminho relativo contra a **raiz do backend** — subir o servidor de pastas diferentes não cria bancos distintos |
| 10 | As rotas de pacientes e avaliações entraram no item 4; IoT, imagens e chat entram nos itens 5 a 7 |

### 10.6 Observações do item 4

| # | Observação |
|---|---|
| 1 | **A Fase 6 não levanta exceção quando a execução falha** — devolve `status=ERRO` com o motivo em `erros` e a trilha em `passos`. Capturar exceção **não basta**: o endpoint traduz o `status` e repassa `erros`, preservando o contrato integral em `dados` |
| 2 | `POST /avaliacoes` responde **HTTP 200 mesmo com `status=ERRO`**: o HTTP diz "rodou e foi registrada", o `status` diz o resultado (mesma lógica do `/health` com `CONCLUIDO_COM_RESSALVAS`) |
| 3 | `PedidoDeAvaliacao.features` é `dict[str, Any]` **de propósito**: o pydantic converte `true` → `1.0` em silêncio, então tipar `float` contornaria a rejeição de booleano do mapeador (D4) |
| 4 | O pacote `cardioia` **também** está acessível por `PYTHONPATH` neste workspace: `importar()` não aborta quando a pasta configurada não existe — quem decide é o import |
| 5 | O aquecimento do cache no `lifespan` roda em `asyncio.to_thread`: o import do pipeline leva ~6 s e bloquearia o event loop. Boot: ~9,6 s com aquecimento, ~2,7 s sem |
| 6 | `AQUECER_MODELO_NO_STARTUP=false` nos testes: sem isso, cada aplicação de teste pagaria o import. O `.pkl` também é reaproveitado entre testes (o cache é por app) — a suíte caiu de 65 s para ~35 s |
| 7 | `ADMIN` **não** é superusuário: lê histórico e auditoria, mas não cadastra paciente nem escreve dado clínico (exige `MEDICO`) |
| 8 | Paciente **inativo** → `409 CONFLITO` (não 404): o registro existe, o estado atual é que impede a operação |
| 9 | Nome de paciente só com espaços é recusado (`422`): sem isso, `"   "` passaria no `min_length=1` e viraria nome vazio no banco |

### 10.7 Observações do item 5

| # | Observação |
|---|---|
| 1 | **A cadeia `if/elif/elif` é comportamento, não estilo**: trocá-la por checagens independentes devolveria 3 alertas onde a origem devolve 1. Verificado por teste e por comparação com o legado |
| 2 | Os **limiares não são configuráveis**: mantê-los como constantes do módulo é o que garante "limiares idênticos aos da origem" |
| 3 | O **alerta não é persistido** — é derivado dos sinais e não há coluna para ele. Ele vai em `avisos` e a **trilha de auditoria** registra o evento (só quando há alerta) |
| 4 | **Auditoria só no alerta**: a telemetria chega a cada poucos segundos; gravar toda leitura encheria a trilha sem valor. A leitura já é o registro persistido |
| 5 | `recebido_em` é **carimbado pelo backend** e o firmware não envia identificador: `id_dispositivo` é exigido na API (`MODELO_DADOS.md` §4.5) |
| 6 | A **chave de dispositivo é única** para todos os dispositivos — ela autentica "um dispositivo autorizado", não "o dispositivo X". O `id_dispositivo` vem do corpo e não é confrontado com a chave (**limitação declarada**) |
| 7 | Servidor **sem** `IOT_DEVICE_KEY` **recusa** o caminho da chave (401) em vez de aceitar qualquer valor: não há o que comparar, e aceitar seria pior |
| 8 | `features` da telemetria **não** são mapeadas para o modelo (Decisão D4). O gap (1 de 10) é declarado em `limitacoes` em toda resposta |
| 9 | A coluna `monitoramentos.id_paciente` existe (vinculação opcional) mas **não** é exposta no contrato §4.2 — o DTO é fechado e o contrato aprovado não a lista |

### 10.8 Observações do item 6

| # | Observação |
|---|---|
| 1 | **HTTP e não import direto** (Decisão 1-C): a Fase 4 carrega TensorFlow no *import* e o conflito com o `scikit-learn` da Fase 6 é o risco **R8**. O backend **não** importa TensorFlow |
| 2 | `{class, confidence}` → `{classe, confianca}` é tradução **de borda** (nota N4); o adapter devolve os nomes de origem e o contrato da Fase 7 nasce na rota |
| 3 | `modelo_utilizado`, `limiar_decisao` e `dimensoes_da_imagem` são **acrescentados** pelo backend (nota I9) — 6 testes conferem essas constantes contra o fonte da Fase 4 |
| 4 | **A imagem não é persistida**: só `hash_sha256`, `mime`, tamanho e nome. A tabela não tem coluna de binário e a trilha de auditoria registra apenas metadados |
| 5 | **Endurecimento da borda** (contrato §4.6): a Fase 4 aceita "qualquer arquivo que o Keras abra"; aqui o `content_type` é validado e há teto de tamanho (`413`) |
| 6 | O teto de upload é checado **antes** de ler o corpo (via `Content-Length`) e também no `read(limite + 1)`, para não bufferizar um upload enorme só para recusá-lo |
| 7 | `ADMIN` e `OPERADOR` recebem `403`: interpretar imagem é **ato clínico** |
| 8 | Paciente **inativo** → `409` (mesma decisão das avaliações); `id_paciente` é **opcional** no upload |
| 9 | Serviço **inalcançável** → `502`; serviço **lento** → `504`. Os dois são "falha do serviço externo", mas distinguem "não consegui falar" de "não respondeu a tempo" |
| 10 | O smoke test usa um **serviço falso** porque TensorFlow não existe neste ambiente — a chamada é HTTP real, entre processos |

### 10.9 Observações do item 7

| # | Observação |
|---|---|
| 1 | **O backend não importa `IBM_API.py`** (divergência declarada da Decisão 1): aquele módulo usa a chave real vazada como default (S1/C1) e `app.py` cria um cliente no import. O objetivo da decisão — reaproveitar o SDK sem duplicar lógica — é preservado |
| 2 | Com o ambiente vazio, `POST /chat` devolve **`501 NAO_CONFIGURADO`**: é a prova de que a chave vazada **não** é herdada |
| 3 | O `session_id` do Watson **nunca** sai daqui (I8): o cliente usa e recebe apenas o `id_conversa`. Um teste verifica que o valor não aparece em lugar nenhum da resposta e que o `dados` não tem campo de sessão |
| 4 | `fontes` é **sempre `[]`** (N6) — o Watson não devolve fontes, e preencher seria inventar |
| 5 | **O turno do usuário é persistido mesmo quando o provedor falha**, com o texto amigável em `conteudo` e o detalhe técnico em `erro` (interno): o histórico conta o que aconteceu, sem inventar resposta |
| 6 | **Auditoria na abertura da conversa**, não em cada turno: uma conversa tem dezenas de mensagens e `mensagens` já é o registro. O `detalhe` não carrega o conteúdo |
| 7 | Sessão expirada no Watson (404) → recria e **reintenta uma vez** (comportamento da Fase 5); se falhar de novo, sobe traduzido |
| 8 | `ADMIN` recebe `403` no `/chat`: o contrato §8 lista `OPERADOR` \| `MEDICO` |
| 9 | O contrato §4.5 **não expõe `canal`**: conversas são registradas como `web`. O valor `mobile` existe no enum e no banco mas nenhuma rota o produz — gancho para o app Expo da Fase 5 |
| 10 | O contexto da conversa (canal, início, fim) vai em `metadados` do envelope, porque o contrato define `dados` como o **histórico de mensagens** |

### 10.2.7 Entregas do item 7 (assistente conversacional — Fase 5)

| Arquivo | Conteúdo |
|---|---|
| `backend/app/integracao/fase_5.py` | cliente do Watson a partir da **configuração**, extração da resposta, tradução de erros, fluxo com recuperação de sessão |
| `backend/app/contratos/assistente.py` | `PedidoDeMensagem`, `MensagemDoAssistente`, `MensagemDoHistorico` + avisos e limitações |
| `backend/app/rotas/assistente.py` | `POST /chat` · `GET /conversas/{id_conversa}` |
| `backend/app/config.py` | `WATSON_TIMEOUT_SEGUNDOS` + `CANDIDATO_FASE_5` (fonte normativa) |
| `backend/tests/test_integracao_fase_5.py` | 43 testes — inclui as constantes e o **mapeamento de erro** conferidos contra o fonte |
| `backend/tests/test_rota_assistente.py` | 25 testes |
| `backend/tests/conftest.py` | `ClienteFalso` (dublê do SDK) + `ambiente_do_assistente` |

**⚠️ Divergência declarada da Decisão 1 (segurança):** a decisão previa *"import direto de
`IBM_API.py`"*, mas **o backend não importa aquele módulo**. Motivo:

- `IBM_API.py` lê as credenciais com `os.getenv(...)` usando **a chave real do projeto como
  valor default** (achado **S1**; correção **C1**). Importá-lo grava essa chave nos seus
  constantes de topo, e `get_assistant()` a usaria em silêncio sempre que as variáveis de
  ambiente não estivessem definidas — exatamente o que a regra de migração proíbe;
- `app.py` executa `assistant = get_assistant()` **no import** — importá-lo criaria um
  cliente autenticado com a chave vazada e um `Flask(__name__)`.

O **objetivo** da decisão é preservado: usa-se o **mesmo SDK**, a **mesma versão de API** e o
**mesmo timeout**, e a "camada de tradução fina" prevista está em `fase_5.py` com o **mesmo
mapeamento** de `friendly_watson_error`. Cinco testes conferem essas constantes e faixas de
status **contra o arquivo-fonte** da Fase 5 (risco **R6**).

**Prova comportamental (no smoke test e em teste):** com o ambiente vazio, `POST /chat`
responde **`501 NAO_CONFIGURADO`**. Se o backend herdasse os defaults, ele tentaria uma
chamada real — a recusa é a evidência de que a chave vazada não é usada.

**Decisões de contrato aplicadas:**

| Decisão | Implementação |
|---|---|
| **I8** — o `session_id` do Watson não vai ao cliente | `id_conversa` próprio; a sessão fica em `mensagens.session_id_do_provedor` e é recuperada a cada turno |
| **N6** — `fontes` sempre `[]` | preenchido literalmente; o Watson não devolve fontes |
| Contrato §8.1 | sem Watson configurado → `501`; 401/403 **do Watson** → `502`; 429 → `429`; 408/504 → `504`; demais → `502` |
| Turno falho | persistido: `conteudo` = o texto amigável que o usuário viu, `erro` = o detalhe técnico (interno) |

---

*Documento de acompanhamento da Fase 7. Nenhum arquivo das Fases 1 a 6 foi modificado. **Etapa B
encerrada e aprovada**; a **Etapa C está em andamento** (2 de 7 itens concluídos).*

---

*Documento de acompanhamento da Fase 7. Nenhum arquivo das Fases 1 a 6 foi modificado nesta etapa.*

---

## 11. Etapa D — Integração Web + Backend (concluída)

### 11.1 Escopo

Integrar o frontend **React + Vite** da Fase 2 ao backend FastAPI da Fase 7, entregando o
MVP demonstrável: login real, pacientes, avaliação de risco, histórico, indicadores,
telemetria IoT e assistente — com tratamento de erro e estados de carregamento.

> **Instrução respeitada:** a configuração da **Vercel** e do **EAS Build** **não** foi
> iniciada. As pendências de publicação estão em §11.9.

### 11.2 Diagnóstico (item 1 — executado antes de qualquer alteração)

| Item | Achado |
|---|---|
| **Localização** | `Fase_2/Cap2_Desafio_Integrador/Ir_Alem/my-react-app/` |
| **Stack** | Vite 8 · React 19.2 · react-router-dom 7.13 · ESLint 9 |
| **Telas existentes** | `/` (login), `/dashboard`, `/patients`, `/schedule` |
| **Login atual** | **simulado no cliente**: comparava `admin@email.com`/`123` e gravava `fake-jwt-token-123` |
| **Gráficos** | ❌ **não havia** — e não há biblioteca de gráficos no `package.json` |
| **Cliente HTTP** | `src/services/api.js` com **uma** função chamando `jsonplaceholder.typicode.com` |
| **Componentes** | `ProtectedRoute`, `AuthContext` e 2 exemplos didáticos em `hooks-examples/` |
| **Assets** | `imagem_medico.jpg` (fundo do `body`), `hero.png`, `medical-bg.svg`, `icons.svg` |

### 11.3 Decisão estrutural: **cópia**, não edição in loco

O enunciado pede duas coisas que se contradizem se o app for editado onde está:

- **"Integrar o frontend React + Vite da Fase 2"** → exige modificar arquivos do frontend;
- **"Não modificar as Fases 1–6"** → a Fase 2 é uma delas.

**Solução adotada (aprovada pelo autor):** copiar o app para **`Fase_7/frontend/`** e
integrar a cópia. Reaproveita 100% do CSS, layout, assets, roteamento e configuração; a
**Fase 2 permanece intacta**. É o mesmo padrão do `backend/`, que consome as Fases 3–6 sem
tocá-las.

### 11.4 Entregas

| Área | Arquivos |
|---|---|
| **Camada de API** | `src/api/configuracao.js` · `src/api/cliente.js` · `src/api/endpoints.js` |
| **Sessão** | `src/contexts/AuthContext.jsx` (reescrito) · `src/contexts/PacienteContext.jsx` |
| **Componentes** | `Estado.jsx` · `Indicador.jsx` · `NivelDeRisco.jsx` · `ResultadoDaAvaliacao.jsx` · `SeletorDePaciente.jsx` · `JanelaDoChat.jsx` · `ProtectedRoute.jsx` (reescrito) |
| **Telas** | `Login.jsx` · `Dashboard.jsx` · `Pacientes.jsx` · `Avaliacao.jsx` · `Historico.jsx` · `Monitoramento.jsx` · `Assistente.jsx` · `Agenda.jsx` |
| **Domínio** | `src/dominio/catalogo.js` (as 10 features com as faixas do contrato §4.1 e os enums reais do backend) |
| **Infra** | `src/App.jsx` · `src/App.css` (acréscimos) · `index.html` · `package.json` · `.env.example` · `.gitignore` · `README.md` |
| **Validação** | `scripts/smoke.mjs` |

**Telas implementadas (8):** Acesso · Visão geral · Pacientes · Avaliação · Histórico ·
Monitoramento IoT · Assistente · Agenda (demonstrativa).

### 11.5 Incompatibilidades tratadas

| # | Fase 2 | Contrato da Fase 7 | Tratamento |
|---|---|---|---|
| F1 | login fake no cliente | `POST /auth/login` | `AuthContext` reescrito; senha nunca armazenada |
| F2 | `usuario` reconstruído do token sem validar | `GET /auth/me` | sessão confirmada ao abrir o app |
| F3 | `fetchPatients` no jsonplaceholder | `GET /pacientes` com `Bearer` | cliente HTTP único |
| F4 | esperava `array` | **`dados` das listagens é uma lista** | consumido direto (não há `{itens: []}`) |
| F5 | resposta crua | envelope `{status, dados, erros, avisos, limitacoes, metadados}` | desembrulhado no cliente |
| F6 | `response.ok` | erros com `codigo` estável | UI reage ao `codigo` (`NAO_CONFIGURADO`, `NAO_AUTORIZADO`, …) |
| F7 | token eterno | JWT de 30 min + refresh com rotação | renovação transparente em `401`, uma vez |
| F8 | sem lib de gráficos | — | barras/medidores em **CSS puro** (nenhuma dependência nova) |
| F9 | rota `/schedule` | **não há endpoint de agenda** | mantida e **rotulada como demonstrativa** |
| F10 | — | **não há `POST /usuarios`** | tela de acesso aponta o procedimento manual |
| F11 | — | `/chat` recusa `ADMIN` (`403`) | a tela explica em vez de esconder o menu |
| F12 | — | `POST /avaliacoes` exige as **10 features** | formulário com as 10, sem valor padrão (R3) |
| F13 | — | serviço da Fase 4 fora do ar (`502`) | mensagem explica que ele exige TensorFlow |

### 11.6 Ajuste no backend (única alteração, justificada)

**`app/config.py` — default de `CORS_ORIGENS`** e `.env.example`.

O padrão listava só `http://localhost:5173`. Como o **Vite pode servir em `localhost` OU em
`127.0.0.1`**, e o navegador trata os dois como **origens diferentes**, abrir o app em
`127.0.0.1:5173` fazia **todas** as chamadas serem bloqueadas pelo CORS — o app abria, mas
nenhum dado carregava.

Verificado empiricamente antes e depois:

| Origem | Antes | Depois |
|---|---|---|
| `http://localhost:5173` | ✅ permitida | ✅ permitida |
| `http://127.0.0.1:5173` | ❌ **bloqueada** | ✅ permitida |
| `http://malicioso.example` | ✅ bloqueada | ✅ bloqueada |

O enunciado autoriza o ajuste ("Configurar CORS no backend conforme necessário"). Nenhum
teste existente afirmava o valor padrão; os **586 testes do backend continuam passando**.

### 11.7 Validações executadas (item 5)

| Verificação | Comando | Resultado |
|---|---|---|
| **Suíte do backend** (após o ajuste de CORS) | `python -m pytest -q` | ✅ **586 passed** |
| **Lint do frontend** | `npm run lint` | ✅ **0 erros, 0 avisos** |
| **Build de produção** | `npm run build` | ✅ 46 módulos, ~2,9 s, sem avisos |
| **Servidor de desenvolvimento** | `npm run dev` | ✅ HTTP 200 em `/` (título correto) |
| **CORS (3 origens)** | `curl -H "Origin: …"` | ✅ 2 permitidas, 1 bloqueada |
| **Smoke com backend real — `MEDICO`** | `npm run smoke` | ✅ **29/29** |
| **Smoke com backend real — `OPERADOR`** | `npm run smoke` | ✅ **17/17** |
| **Smoke com backend real — `ADMIN`** | `npm run smoke` | ✅ **19/19** |
| **Backend indisponível** | `npm run smoke` com o servidor parado | ✅ mensagem acionável, sem erro cru |
| **Pipeline real da Fase 6 pelo frontend** | `POST /avaliacoes` via `src/api/` | ✅ `prob=0.99`, `pico_de_risco`, modelo `Random Forest` |
| **Telemetria + regra da Fase 3** | `POST /iot/leituras` | ✅ `CONCLUIDO_COM_RESSALVAS` com `FEBRE DETECTADA` |
| **Fases 1 a 6 intactas** | inspeção de timestamps | ✅ **0 arquivos alterados** |

O smoke test exercita **a mesma camada de API que a interface usa** (`src/api/`) — não é um
mock. Se o envelope mudar de forma, ele quebra.

### 11.8 Achados que o smoke test revelou

| # | Achado | Correção |
|---|---|---|
| A1 | `diagnostico.features_utilizadas` é a lista de **nomes** das features, não um objeto de valores — e os valores avaliados **não são expostos** por nenhum endpoint | as barras passaram a ser desenhadas com o que o usuário digitou (tela de avaliação); no histórico/dashboard a tela mostra os **nomes** e declara a ausência |
| A2 | `ErroDaAPI` não expunha a propriedade `mensagem` (só `Error.message`) | a propriedade foi adicionada |
| A3 | **`*/` dentro de um comentário** de bloco em `catalogo.js` (`**A3**/**A4**`) fechava o comentário e gerava código inválido | reescrito — o lint pegou o erro de sintaxe |
| A4 | `setState` síncrono dentro de efeitos (3 telas) causava render em cascata | busca separada do estado; o efeito só atualiza no callback |
| A5 | o script de smoke não era sensível ao papel e reportava `403` esperados como falhas | virou uma **matriz de RBAC** explícita |

### 11.9 Pendências para deploy (Vercel / EAS — **não iniciado**)

| # | Pendência | Observação |
|---|---|---|
| 1 | **CORS em produção** | `CORS_ORIGENS` precisa do domínio da Vercel |
| 2 | **`VITE_API_URL` em produção** | hoje aponta para `127.0.0.1` |
| 3 | **Token em `localStorage`** | padrão herdado da Fase 2; o backend não usa cookie, então o header `Authorization` é o caminho. Migrar para memória + refresh silencioso reduz o impacto de XSS |
| 4 | **Backend em produção** | o MVP assume SQLite local |
| 5 | **Tela de imagem** | o cliente `analisarImagem` está pronto; falta a tela, que depende do serviço da Fase 4 no ar |
| 6 | **Valores das features no histórico** | exigiria um campo novo em `GET /avaliacoes/{id}` (ver A1) |
| 7 | **Rotação da chave do Watson** | pendência do backend (`PLANO_SEGURANCA.md`, C1) |
| 8 | **`campo` do erro de JSON malformado** | o backend devolve `campo: "1"` (índice do corpo) em vez de `null`; cosmético, fora do escopo desta etapa |

### 11.10 Estado da auditoria da Etapa C (interrompida)

A auditoria integrada da Etapa C foi **iniciada e não concluída** — a execução foi
interrompida e o foco passou para a Etapa D. O que **ficou pronto** dessa auditoria:

| Item | Situação |
|---|---|
| **Revisão do uso de HTTP 507** (item 3 da auditoria) | ✅ **Corrigido e testado** — ver abaixo |
| Demais seções (fluxos ponta a ponta, varredura de segredos, OpenAPI, provisionamento) | ⏸️ **Não concluídas** — o script de auditoria foi removido |

**A correção do `507`:** a Fase 5 usava **`507`** (*Insufficient Storage*, RFC 4918) para
falha de autenticação no Watson — nos **dois** lados do seu contrato (`Backend/app.py`
devolvia, `watsonApi.js` lia). O código `FALHA_DE_AUTENTICACAO_EXTERNA` foi **mantido** e o
transporte passou a **`502`**, porque `401`/`403` são do **usuário** — devolvê-los ali faria
um cliente encerrar a sessão por um problema do provedor. Documentado em
`CONTRATOS_API.md` §3.2.1. Isso explica a contagem ir de **584 → 586 testes**.

> A Etapa D **não** depende dessa auditoria: a integração foi validada contra o backend
> real (65 verificações de smoke nos 3 papéis), o que cobre o comportamento observado.

---

*Documento de acompanhamento da Fase 7. A **Etapa D** foi concluída: frontend integrado,
validado contra o backend real e documentado. **Nenhum arquivo das Fases 1 a 6 foi
modificado.** A única alteração no backend foi o padrão de `CORS_ORIGENS` (§11.6).*



---

## 12. Fase 7 — MVP final e funcional (entrega)

### 12.1 Escopo entregue

A Etapa D integrou web e backend. Esta seção registra a **entrega final da Fase 7**: o MVP
completo, do sinal captado no dispositivo até a recomendação clínica na interface.

| Bloco | Pasta | Estado |
|---|---|---|
| Núcleo integrador Python | `backend/` | ✅ **636 testes** |
| Aplicação web (React + Vite) | `frontend/` | ✅ lint e build limpos |
| Aplicativo (React Native + Expo) | `mobile/` | ✅ bundle validado |
| Firmware MicroPython + Wokwi | `IoT/` | ✅ sintaxe e circuito validados |
| Relatório técnico | `docs/RELATORIO_FASE7.html` | ✅ imprimível em PDF |
| Guia de publicação | `DEPLOY.md` | ✅ |

### 12.2 Decisão de arquitetura: nenhuma chave de serviço

O autor determinou que a entrega **não dependa de credenciais de terceiros**. Cada serviço
externo foi substituído por um equivalente dentro do projeto:

| Serviço | Substituto | Onde |
|---|---|---|
| IBM Watson Assistant | **Provedor local** de conhecimento (Python puro) | `app/integracao/assistente_local.py` |
| OpenAI (pipeline) | **Modo simulado** (padrão) com o modelo treinado | Fase 6 |
| Broker MQTT / HiveMQ | **HTTP direto** do dispositivo ao backend | `IoT/main.py` |
| Banco gerenciado | **SQLite** com conta semeada no startup | `app/main.py` |
| SMTP | Fora de escopo | — |

A documentação descreve o provedor local como **arquitetura padrão**, não como contorno: o
adaptador do Watson continua disponível e é usado quando configurado.

### 12.3 Bloqueadores encontrados e corrigidos

| # | Problema | Correção |
|---|---|---|
| B1 | `requirements.txt` não declarava `scikit-learn`, `pandas`, `numpy` e `joblib` — o pipeline da Fase 6 falharia no deploy | dependências declaradas |
| B2 | `python-multipart` não declarado — `POST /imagens` quebraria no deploy | declarado |
| B3 | As pastas `Fase_1`…`Fase_6` eram **repositórios git aninhados**: o `git add` criava *gitlinks* e o tutor clonaria pastas **vazias** | `.git` renomeado para `.git-backup` (reversível); o conteúdo passou a fazer parte do monorepo |
| B4 | Sem `.gitignore` na raiz, artefatos e segredos entrariam por engano | `.gitignore` criado |
| B5 | O CORS não cobria os domínios de *preview* da Vercel (que mudam a cada deploy) | `CORS_ORIGEM_REGEX` opcional |
| B6 | O assistente local citava limiares (37,8 °C / 100 bpm) diferentes dos canônicos do projeto | alinhado a **38 °C / 120 bpm** (`app/regras_iot.py`) |

### 12.4 Sanitização das fases anteriores

| Arquivo | O que trazia | Situação |
|---|---|---|
| `Fase_5/.../IBM_API.py` | chave do Watson e 3 identificadores como **default** | removidos; **chave desativada** na plataforma |
| `Fase_3/.../codigo_parte2.c` | `mqtt_server`, `mqtt_user`, `mqtt_pass` literais | substituídos por marcadores |
| `Fase_3/.../server.py` | e-mails pessoais | substituídos por endereços de exemplo |
| `__pycache__` (14 pastas) | o `.pyc` do `IBM_API` continha a chave compilada | removidas |

Varredura final: **0 ocorrências** de chave, cluster, senha de broker ou e-mail pessoal.

### 12.5 Validação

| Verificação | Resultado |
|---|---|
| Suíte do backend | **636 testes aprovados** |
| Lint do frontend | 0 erros, 0 avisos |
| Build do frontend | 46 módulos |
| Smoke da integração (3 papéis) | **65 verificações, 0 falhas** |
| Pipeline da Fase 6 pelo cliente | probabilidade 0,99 · `pico_de_risco` |
| Regra da Fase 3 na ingestão | `FEBRE DETECTADA` com 38,9 °C |
| Bundle do aplicativo | 219 módulos, 413 KB |
| Sintaxe do firmware MicroPython | OK |
| Circuito do Wokwi | 6 componentes, 14 conexões |

### 12.6 Pendências de publicação (sem código)

| # | Pendência | Onde |
|---|---|---|
| 1 | Publicar o backend no Render | `DEPLOY.md` §1 |
| 2 | Publicar o frontend na Vercel | `DEPLOY.md` §2 |
| 3 | Buildar o APK no EAS | `DEPLOY.md` §3 |
| 4 | Publicar o projeto Wokwi e obter o link | `IoT/README.md` §6 |
| 5 | Preencher os links no `README.md` raiz | §1 do README |
| 6 | Conceder acesso do repositório ao tutor | GitHub |
| 7 | Imprimir o relatório em PDF | `docs/RELATORIO_FASE7.html` |

> Nenhuma delas exige escrever código — são ações de publicação.

---

*Documento de acompanhamento da Fase 7. O **MVP final** está implementado, validado e
documentado: do sensor ao assistente, sem depender de credenciais de terceiros.*

