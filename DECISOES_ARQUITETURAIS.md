# CardioIA — Fase 7 · Decisões Arquiteturais

> **Documento de decisões — Etapa B da Fase 7**
> Etapa anterior: análise das Fases 1 a 6 → [`ANALISE_ARQUITETURA.md`](ANALISE_ARQUITETURA.md)
> Documentos derivados: [`CONTRATOS_API.md`](CONTRATOS_API.md) · [`MODELO_DADOS.md`](MODELO_DADOS.md) · [`PLANO_SEGURANCA.md`](PLANO_SEGURANCA.md)
>
> **Esta etapa NÃO implementa código.** O objetivo é fixar as decisões técnicas e apresentar a
> arquitetura definitiva para aprovação.
>
> 🔒 **Nenhum valor de credencial aparece neste documento.** Onde havia segredo, há referência
> mascarada (`<arquivo>:<campo>`) — ver [`PLANO_SEGURANCA.md`](PLANO_SEGURANCA.md).

---

## 1. Escopo e critérios de decisão

### 1.1 Escopo

Quatro decisões estruturais, mais a seleção de frontends e o plano de segurança:

| # | Decisão | Pergunta |
|---|---|---|
| D1 | **Estratégia de integração da Fase 6** | Import direto, subprocesso ou serviço independente? |
| D2 | **Contrato comum de API** | Qual o padrão de comunicação e os schemas entre web, mobile, IoT, backend, modelos e LLM? |
| D3 | **Banco de dados e autenticação** | O que usar no MVP e como estruturar? |
| D4 | **Gap IoT ↔ Fase 6** | Como resolver as 8 features ausentes sem inventar dados? |
| D5 | **Seleção de frontends** | Qual web, qual mobile, o que reaproveitar? |
| D6 | **Segurança** | Como tratar as credenciais expostas? |

### 1.2 Critérios de avaliação adotados

1. **Restrições do projeto** — não modificar as Fases 1 a 6; não instalar dependências; escopo acadêmico/demonstrativo.
2. **Reutilização real** — preferir o que já existe e está testado a reescrever.
3. **Honestidade técnica** — não inventar compatibilidade, unidade, valor ou capacidade preditiva.
4. **Rastreabilidade** — toda decisão aponta para a evidência que a sustenta.
5. **Segurança por padrão** — segredos fora do código, avisos clínicos sempre visíveis.
6. **Reversibilidade** — preferir escolhas que possam ser trocadas (ex.: SQLite → PostgreSQL) sem redesenho.

---

## 2. Achados que fundamentam as decisões

### 2.1 Ambiente já instalado (verificado)

| Pacote | Versão | Situação |
|---|---|---|
| Python | 3.13.5 | igual ao validado na Fase 6 |
| Node / npm | v22.17.0 / 10.9.2 | compatível com Vite 8 e Expo |
| `fastapi` | 0.119.0 | ✅ disponível |
| `uvicorn` | 0.37.0 | ✅ disponível |
| `starlette` | 0.48.0 | ✅ compatível com FastAPI 0.119 (`<0.49.0`) e com a restrição da Fase 6 |
| `pydantic` | 2.14.1 | ✅ o mesmo da Fase 6 → contratos interoperáveis |
| `sqlalchemy` | 2.0.49 | ✅ disponível |
| `PyJWT` | 2.13.0 | ✅ disponível |
| `bcrypt` | 5.0.0 | ✅ disponível |
| `httpx` · `python-multipart` · `python-dotenv` | 0.28.1 · 0.0.20 · 1.2.2 | ✅ disponíveis |
| `openai-agents` · `scikit-learn` · `pandas` · `joblib` | 0.18.1 · 1.8.0 · 2.3.2 · 1.5.3 | ✅ as mesmas da Fase 6 |
| `tensorflow` | 2.20.0 | ⚠️ instalado, porém pesado |
| `python-jose` | **AUSENTE** | ❌ não usar para JWT |
| `passlib` | **AUSENTE** | ❌ não usar para hash |
| `alembic` | **AUSENTE** | ❌ sem migrations automáticas |

**Consequência:** é possível montar backend, banco, JWT e hash **sem instalar nada** — respeitando a
restrição "não instalar dependências".

### 2.2 Contrato exato do modelo (verificado em `predict.validar_paciente`)

| Regra | Comportamento |
|---|---|
| Campos ausentes | ❌ `PacienteInvalidoError` |
| Campos **desconhecidos** | ❌ `PacienteInvalidoError` (`permitir_campos_extras=False`) |
| `bool` | ❌ rejeitado explicitamente |
| `str` | ❌ rejeitado — *"a conversão não é feita silenciosamente"* |
| `NaN` / `inf` | ❌ rejeitado |
| Valores negativos | ❌ rejeitado |
| Fora da faixa de treino | ⚠️ apenas **aviso** (não erro) |
| Ordem das colunas | reordenada conforme o metadata |
| `limiar` fora de [0, 1] | ❌ `ErroDePrevisao` |

### 2.3 Achados semânticos — ✅ **RESOLVIDOS pelo autor**

| # | Achado original | **Resposta do autor** | Consequência adotada |
|---|---|---|---|
| **A1** | **`temperatura` era ambígua** — o gerador usa `np.random.normal(24, 5).clip(10, 40)` (média 24 °C, típica de **ambiente**), enquanto o **protocolo 7** diz *"Se temperatura > 38°C média → iniciar protocolo infeccioso"* (leitura **corporal**) | ✅ **`temperatura` é CORPORAL** | (a) o **DHT22 da Fase 3 mede temperatura ambiente** → **não pode** alimentar esta feature; (b) o protocolo 7 passa a ser coerente; (c) ⚠️ **inconsistência remanescente** documentada no achado **A3** abaixo |
| **A2** | **O alvo parecia ser risco de sobrecarga assistencial** — 5 features são operacionais (`carga_sistema`, `tempo_espera`, `disponibilidade_recursos`, `densidade_eventos`, `eventos_24h`) e 3 têm sufixo `_media` (populacional); os protocolos 2, 5 e 6 mandam *"abrir unidades temporárias"*, *"redistribuir insumos"*, *"priorizar triagem emergencial"* | ✅ **`pico_risco` é CLÍNICO INDIVIDUAL** | (a) a entidade do domínio passa a ser **`pacientes`** (não mais `snapshots_assistenciais`); (b) ⚠️ **tensão semântica remanescente** documentada no achado **A4** abaixo |

### 2.4 ⚠️ Achados remanescentes após as respostas

> Registrados por honestidade técnica: as respostas resolvem a **intenção de projeto**, mas não
> eliminam duas inconsistências internas do material da Fase 6. **Nenhuma delas foi "corrigida"
> nesta etapa** (é proibido alterar a Fase 6).

| # | Achado remanescente | Evidência | Impacto | Mitigação adotada |
|---|---|---|---|---|
| **A3** | **A distribuição de `temperatura` no gerador não corresponde a temperatura corporal** | `data/base_dados.py`: `np.random.normal(24, 5).clip(10, 40)` → média **24 °C**. Temperatura corporal humana real fica em ~36–38 °C, ou seja, na **cauda superior** da distribuição de treino | O modelo aprendeu a fronteira de decisão de `temperatura` sobre uma distribuição de **ambiente**. Qualquer valor corporal real cai na cauda → a contribuição dessa feature é **pouco confiável** | (a) documentar como **limitação**; (b) marcar `temperatura` como feature de **baixa confiança**; (c) **não** retreinar (exigiria alterar a Fase 6); (d) exibir aviso quando o valor estiver fora da faixa típica observada |
| **A4** | **8 das 10 features não são medições individuais** | `carga_sistema`, `tempo_espera`, `disponibilidade_recursos`, `densidade_eventos`, `eventos_24h` são métricas de **operação/contexto**; `idade_media`, `fc_media`, `spo2_media` têm nome de **média** | Na leitura "clínico individual", é preciso definir o que cada feature significa **para um paciente** | Interpretação adotada e documentada (ver 2.5) — **sem alterar nomes**, pois o contrato do modelo é fechado |

### 2.5 Interpretação adotada das 10 features na leitura "clínico individual"

> Os **nomes não podem mudar** (o contrato do modelo é fechado: `extra="forbid"`). O que se define
> abaixo é o **significado** de cada campo para um paciente individual.

| Feature | Leitura individual adotada | Grau de aderência |
|---|---|---|
| `idade_media` | ⚠️ **Idade do paciente** (o nome contém `_media`, mas o contrato exige esse nome) | 🟡 nome diverge da semântica |
| `carga_sistema` | Carga da unidade/ala **durante o episódio** do paciente (contexto assistencial) | 🟡 contextual, não clínico |
| `temperatura` | **Temperatura corporal** do paciente (confirmado pelo autor) | 🟡 ver achado **A3** |
| `fc_media` | **Frequência cardíaca média** do paciente na janela de monitoramento | 🟢 aderente |
| `spo2_media` | **SpO₂ média** do paciente na janela de monitoramento | 🟢 aderente |
| `pa_sistolica` | **Pressão arterial sistólica** do paciente | 🟢 aderente |
| `tempo_espera` | **Tempo de espera do paciente** até o atendimento | 🟢 aderente |
| `densidade_eventos` | Densidade de eventos **relacionados ao paciente** | 🟡 ambíguo |
| `eventos_24h` | **Eventos do paciente** nas últimas 24 h | 🟢 aderente |
| `disponibilidade_recursos` | Recursos disponíveis **para o atendimento** do paciente | 🟡 contextual |

**Balanço:** 5 features claramente individuais · 4 contextuais/ambíguas · 1 com nome divergente.
A entidade do domínio é **`paciente`**; as features contextuais ficam registradas como **contexto do
episódio** dentro da avaliação, não como atributos permanentes do paciente.

> ⚠️ **A resposta A4 (nome `idade_media` para a idade de um paciente) fica registrada como
> observação**, sem alterar o contrato. Se o autor quiser, isso pode ser reavaliado em etapa futura.

### 2.4 Contrato de erro já existente (reaproveitado)

A Fase 5 já define códigos nomeados no cliente HTTP (`watsonApi.js` → `statusToCode`):
`not-configured` (501), `auth-failed` (507), `quota` (429), `timeout` (504), `watson-error` (502),
`server-error`. **Este é um contrato real** e é a base do enum de erros de `CONTRATOS_API.md` — não
foi criado um vocabulário do zero.

---

## 3. DECISÃO 1 — Estratégia de integração da Fase 6

### 3.1 Alternativas

| ID | Alternativa | Como funciona |
|---|---|---|
| **A** | **Importação direta do pacote Python dentro do FastAPI** | O backend adiciona `Fase_6/cardioia_Fase6/src` ao `sys.path` e chama `orchestrator.executar_pipeline(paciente, ...)` em processo |
| **B** | **Execução do CLI por subprocesso** | `subprocess.run(["python","-m","src.cardioia.main","--json","--paciente", ...])` e parse do JSON |
| **C** | **Fase 6 como serviço independente** | Um serviço próprio (FastAPI) importa o pacote e expõe `/risco/avaliar`; o backend central consome por HTTP |

### 3.2 Comparação

| Critério | **A. Import direto** | **B. Subprocesso** | **C. Serviço independente** |
|---|---|---|---|
| **Complexidade** | 🟢 **Baixa** — `sys.path.append` (padrão já usado no `conftest.py` da Fase 6) + chamada de função | 🟡 Média/Alta — montar `cwd`, serializar paciente, parsear `stdout`, tratar exit codes 0/1/2, timeout, encoding | 🔴 Alta — 2 serviços, 2 deploys, 2 ambientes, contrato HTTP, indisponibilidade, observabilidade distribuída |
| **Desempenho** | 🟢 **Melhor** — sem IPC. Ressalva: `prever_pico_risco` recarrega o `.pkl` (4,7 MB) a cada chamada → exige cache; a assinatura aceita `modelo=`/`metadados=` e `prever_varios` já reaproveita | 🔴 **Pior** — novo interpretador + `import pandas/sklearn` + `joblib.load` a cada requisição (≈1–2 s) | 🟡 Intermediário — melhor que B, pior que A (rede + serialização) |
| **Manutenção** | 🟡 Acopla o release do backend ao da Fase 6 — mitigado: a Fase 6 é estável (290 testes, artefatos versionados, contrato Pydantic) | 🔴 **Frágil** — qualquer mudança na saída textual do CLI quebra o parser; erros viram texto em `stderr` | 🟡 Fronteira limpa, mas dobra a superfície operacional e a matriz de testes |
| **Reutilização do código** | 🟢 **Total** — chama as funções testadas; zero duplicação | 🟢 Total em lógica; 🟡 perde os tipos (interface por processo) | 🟢 Total (o serviço importa o pacote) |
| **Tratamento de erros** | 🟢 **Excelente** — captura direta das exceções tipadas (`ModeloNaoEncontradoError`, `PacienteInvalidoError`, `ModeloIncompativelError`, `ErroDePrevisao`) e do `ValidationError` → mapeamento 1:1 para HTTP | 🔴 **Pior** — só exit code + texto; distinguir "modelo ausente" de "paciente inválido" exige parsing de string | 🟡 Bom, porém com **dupla tradução** (exceção→HTTP→exceção) |
| **Facilidade de deploy** | 🟢 **Alta** — 1 processo, 1 porta, 1 container; ambiente já compatível e instalado | 🟡 Isolamento de dependências bom; operação ruim (spawn, órfãos, timeouts, caminhos) | 🟡 Bom para escalar isolado; ruim para o MVP (2 processos, 2 portas) |

### 3.3 ✅ Decisão adotada

> **A — importação direta do pacote `cardioia` dentro do backend FastAPI (monólito modular).**

**Fundamentos:**

1. **Zero duplicação de lógica** — usa exatamente as funções cobertas por 290 testes.
2. **Preserva o contrato e as exceções tipadas** — `RespostaDaExecucao` é validado em processo; nenhum detalhe de erro se perde.
3. **Melhor desempenho** com cache do artefato no `startup` (o `.pkl` é lido uma vez, não por requisição).
4. **Ambiente já compatível e instalado** — `fastapi 0.119.0` + `starlette 0.48.0` + `pydantic 2.14.1` + `openai-agents 0.18.1` convivem hoje.
5. **Um único deploy** — adequado ao escopo acadêmico/demonstrativo.

**Mitigações obrigatórias:**

| # | Mitigação | Motivo |
|---|---|---|
| M1 | **Import tardio (lazy)** de `cardioia.agents.orchestrator` | Ele importa o SDK `agents` no topo; se o SDK falhar, o backend **sobe** e o endpoint responde `503 MODELO_INDISPONIVEL`, em vez de derrubar o processo |
| M2 | **`sys.path.append` (não `insert`)** | Exatamente como o `conftest.py` da Fase 6 documenta: a pasta `src/agents/` do repositório não pode sombrear o pacote `agents` do SDK |
| M3 | **Cache do modelo** no `startup` | Evita reler 4,7 MB por requisição |
| M4 | **Modo `simulado` por padrão**; `real` atrás de flag explícita | A latência do LLM é de segundos e bloqueia o worker |
| M5 | **`raiz` e `pasta_modelos` resolvidos uma única vez** | Consistência e portabilidade (sem caminho absoluto da máquina) |

**Quando usar cada alternativa:**

| Alternativa | Uso aprovado |
|---|---|
| **A** | ✅ **Caminho quente** — avaliação de risco (Fase 6) e assistente (Fase 5) |
| **C** | ✅ **Somente para a Fase 4** (TensorFlow 2.20 pesado e isolado) |
| **B** | ✅ **Somente para operação** — ex.: `python -m src.cardioia.ml.train` como tarefa administrativa. ❌ **Nunca** no caminho quente |

### 3.4 Incorporação das Fases 3, 4 e 5 sem duplicar lógica

**Investigação do que é realmente importável:**

| Fase | Arquivo | Lógica importável? | Detalhe |
|---|---|---|---|
| **5** | `Backend/IBM_API.py` | ✅ **Sim** | `get_assistant()` é função pura, sem Flask |
| **5** | `Backend/app.py` | ⚠️ Parcial | `_extract_reply`, `_status_of`, `friendly_watson_error`, `_visible_config`, `_send_and_reply`, `_recover_session_and_send` são funções de módulo, **mas** o import executa `Flask(__name__)` e `assistant = get_assistant()` |
| **4** | `backend/app.py` | ❌ **Não** | `load_model` no import + **pré-processamento inline no handler** (`target_size=(128,128)`, `/255.0`, `expand_dims`, corte 0.5) |
| **3** | `Ir_Alem1/server.py` | ⚠️ Parcial | `enviar_email()` é função de módulo, **mas** as 3 regras de risco estão inline no handler, com limiares literais (`38`, `120`) |
| **2** | `Parte_1/Identificar_Sintomas.py` | ⚠️ Parcial | `normalizar_texto()`, `carregar_mapa_conhecimento()`, `identificar_diagnostico()` existem, mas o módulo tem **caminhos absolutos** em constantes de topo |

**Estratégia adotada:**

| Origem | Estratégia | Justificativa |
|---|---|---|
| **Fase 6** | **Import direto** do pacote `cardioia` | Já é módulo de domínio puro, com contrato e testes |
| **Fase 5** | **Import direto** de `IBM_API.py` + camada de tradução fina | Cliente puro; a tradução de erro já existe e é reaproveitável |
| **Fase 4** | **Serviço separado (C)** em porta própria, consumido por HTTP | Isola o TensorFlow 2.20 e **evita duplicar** o pré-processamento de imagem |
| **Fase 3** | **Extração controlada** para um módulo de domínio no backend | São ~6 linhas de regra; um adapter HTTP para 6 linhas custa mais que o benefício |
| **Fase 2 (NLP)** | **Fora do MVP** (extração controlada só após refatorar os caminhos absolutos) | Sem artefato persistido; não é requisito das decisões atuais |

> ⚠️ **Declaração honesta de duplicação controlada:** para as **Fases 3 e 4 não existe** camada de
> domínio importável — a lógica está dentro dos *route handlers*. Como é proibido modificar as fases
> anteriores, "não duplicar lógica" é **parcialmente** alcançável. Cada ponto de duplicação deve ser
> registrado com: (i) o arquivo-fonte normativo, (ii) o trecho replicado, (iii) um teste que compare o
> comportamento novo com o da origem.
>
> **Decisão sobre a Fase 3:** manter as regras em **um único módulo de domínio** no backend
> (`regras_iot`), com limiares e lógica idênticos aos do `Ir_Alem1/server.py`, e **desativar** o
> serviço Flask legado — a rota `POST /sinais` passa a ser servida pelo backend central.

### 3.5 Mapa de portas (resolve o conflito da porta 5000)

| Serviço | Porta | Processo | Situação |
|---|---|---|---|
| **Backend central (FastAPI)** | **8000** | único processo principal | ✅ a criar na Fase 7 |
| Fase 4 (Flask + TensorFlow) | **5001** | processo isolado | ✅ legado consumido por HTTP |
| Fase 3 (Flask) | — | — | 🚫 desativado (regras extraídas para o backend) |
| Fase 5 (Flask) | — | — | 🚫 desativado (import direto de `IBM_API`) |
| Vite (dev) | 5173 | frontend web | ✅ existente |
| Expo (dev) | 8081 | app mobile | ✅ existente |

---

## 4. DECISÃO 2 — Contrato comum de API (síntese)

> 📄 **Especificação completa:** [`CONTRATOS_API.md`](CONTRATOS_API.md)

### 4.1 Decisão

Adotar **um envelope único** (`RespostaAPI[T]`) para **todos** os canais, **generalizando o
`RespostaDaExecucao`** da Fase 6 — que já é um contrato Pydantic validado, testado e serializável
(`como_dicionario()`).

| Elemento | Decisão |
|---|---|
| Versionamento | prefixo **`/api/v1/...`** |
| Formato | JSON; upload de imagem em `multipart/form-data` |
| Envelope | `RespostaAPI[T]` — `id_execucao`, `gerado_em`, `status`, `dados`, `avisos`, `limitacoes`, `erros`, `metadados` |
| Status | **exatamente** os 4 valores da Fase 6 (`CONCLUIDO`, `CONCLUIDO_COM_RESSALVAS`, `INCOMPLETO`, `ERRO`) |
| Erros | `ErroDaAPI` estruturado (`codigo`, `mensagem`, `campo`, `detalhe`) — enum **derivado** do que já existe |
| Autenticação | `Authorization: Bearer <JWT>` (exceto ingestão IoT e `/health`) |
| **Não fazer** | ❌ não criar um segundo eixo de status; ❌ não unificar `{class, confidence}` da Fase 4 com `DiagnosticoDaPredicao` da Fase 6; ❌ não expor o `session_id` do Watson ao cliente |

### 4.2 Justificativa

1. **Reaproveita um contrato testado** em vez de inventar um novo.
2. **Cobre os 6 clientes** (web, mobile, IoT, backend, modelos, LLM) com um só formato.
3. **Preserva a semântica de falha** da Fase 6 — "falha nunca vira sucesso".
4. **Permite auditoria**: `id_execucao` é o UUID da Fase 6 → liga API, banco e trilha de execução.

### 4.3 Canal × transporte

| Canal | Transporte | Autenticação |
|---|---|---|
| Web ↔ Backend | HTTPS/JSON | Bearer JWT |
| Mobile ↔ Backend | HTTPS/JSON | Bearer JWT |
| IoT → Backend | **MQTT** (tópicos existentes, inalterados) **+** rota HTTP alternativa | chave de dispositivo (a introduzir) |
| Backend → Modelo preditivo | chamada de função em processo (Decisão 1-A) | — |
| Backend → LLM (Fase 6) | Agents SDK em processo | `OPENAI_API_KEY` (env) |
| Backend → LLM (Fase 5) | SDK `ibm-watson` em processo | `WATSON_API_KEY` (env) |
| Backend → Fase 4 | HTTP interno (`:5001`) | rede interna + token de serviço |

---

## 5. DECISÃO 3 — Banco de dados e autenticação (síntese)

> 📄 **Especificação completa:** [`MODELO_DADOS.md`](MODELO_DADOS.md)

### 5.1 Comparação para o MVP

| Critério | **SQLite + SQLAlchemy 2.0** | PostgreSQL | Sem banco (JSON/CSV) |
|---|---|---|---|
| Instalação | 🟢 **zero** — `sqlalchemy 2.0.49` já presente | 🔴 exige servidor + driver | 🟢 zero |
| Adequação (acadêmico/demonstrativo, single-node) | 🟢 **Alta** | 🟡 superdimensionado | 🔴 sem consultas nem integridade |
| Concorrência | 🟡 escrita serializada (lock global) — ok para demo | 🟢 alta | 🔴 nenhuma |
| Integridade referencial / transações | 🟢 **sim** | 🟢 sim | 🔴 não |
| Migrations | 🔴 **`alembic` AUSENTE** → `create_all()` + script versionado | 🟢 alembic | — |
| Criptografia em repouso | 🔴 **não** (SQLCipher não instalado) | 🟡 configurável | 🔴 não |
| Portabilidade futura | 🟢 trocando a URL do SQLAlchemy | — | 🔴 retrabalho total |

### 5.2 ✅ Decisão adotada

> **SQLite via SQLAlchemy 2.0 no MVP**, encapsulado por uma **porta de repositório** que permita
> migrar para PostgreSQL sem tocar nos serviços.

**Justificativa:** nenhuma instalação nova; integridade transacional real; adequado ao escopo
demonstrativo; sem dívida técnica estrutural (a abstração de repositório isola o dialeto).

**Limitações declaradas:** concorrência de escrita limitada; **sem criptografia em repouso**; sem
migrations automáticas. **Não usar SQLite para dados reais de pacientes.**

### 5.3 Autenticação — decisão

| Item | Decisão |
|---|---|
| Padrão | **JWT Bearer** (HS256); access token curto (15–30 min) + refresh token com rotação |
| Biblioteca JWT | **`PyJWT 2.13.0`** ✅ instalada — ❌ **não** `python-jose` (ausente) |
| Hash de senha | **`bcrypt 5.0.0`** ✅ instalada — ❌ **não** `passlib` (ausente); cost ≥ 12 |
| Segredo | `JWT_SECRET` em `.env`, **obrigatório no startup** (falha rápida se ausente) |
| Papéis (RBAC) | `ADMIN` · `MEDICO` · `OPERADOR` — papel `PACIENTE` **fora do MVP** |
| Endpoints | `POST /api/v1/auth/login` · `/refresh` · `/logout` · `GET /api/v1/auth/me` |
| CORS | restrito às origens conhecidas (hoje **aberto** nas Fases 4 e 5) |
| Rate limiting no login | contador simples (nenhuma lib instalada) — **limitação declarada** |
| Logs | nunca registrar payload clínico completo nem tokens |

### 5.4 Entidade central — decisão de nomenclatura (✅ resolvida)

Com a resposta **A2** (`pico_risco` é **clínico individual**), a entidade central passa a ser
**`pacientes`** — não mais a entidade neutra `snapshots_assistenciais` usada provisoriamente na
Etapa B.

| Aspecto | Decisão final |
|---|---|
| Entidade | **`pacientes`** (`id`, `nome`, `criado_em`, `criado_por`, `ativo`) |
| Onde ficam as 10 features | **Na avaliação**, não no cadastro — elas representam o **estado do paciente no momento da avaliação** (snapshot clínico). O cadastro guarda apenas identidade |
| Features contextuais | `carga_sistema`, `disponibilidade_recursos`, `densidade_eventos` são registradas como **contexto do episódio** dentro da avaliação |
| Justificativa | Cada avaliação é um evento com data/hora e um estado medido; guardar as features no cadastro perderia o histórico clínico |

> ⚠️ A renomeação `snapshots_assistenciais` → `pacientes` é propagada em
> [`MODELO_DADOS.md`](MODELO_DADOS.md) e [`CONTRATOS_API.md`](CONTRATOS_API.md).

---

## 6. DECISÃO 4 — Gap entre IoT e a Fase 6

### 6.1 As 10 features exigidas pelo modelo

| Feature | Tipo | Unidade | Obrigatória | Faixa esperada (metadata) |
|---|---|---|---|---|
| `idade_media` | numérico (float, ≥0, finito) | **[NÃO DECLARADA]** | ✅ Sim | 18,0 – 90,0 |
| `carga_sistema` | numérico | **[NÃO DECLARADA]** (leitura provável: %) | ✅ Sim | 30,004 – 99,977 |
| `tempo_espera` | numérico | **[NÃO DECLARADA]** (protocolo cita "min") | ✅ Sim | 5,0 – 113,578 |
| `fc_media` | numérico | **[NÃO DECLARADA]** (protocolo cita "FC" → implica bpm) | ✅ Sim | 50,0 – 150,0 |
| `spo2_media` | numérico | **[NÃO DECLARADA]** (protocolo cita "SPO2 %") | ✅ Sim | 83,431 – 100,0 |
| `pa_sistolica` | numérico | **[NÃO DECLARADA]** (protocolo cita "PA sistólica") | ✅ Sim | 80,0 – 198,832 |
| `temperatura` | numérico | **[NÃO DECLARADA]** — ⚠️ **ambígua** (ambiente × corporal) | ✅ Sim | 10,0 – 40,0 |
| `densidade_eventos` | numérico | **[NÃO DECLARADA]** | ✅ Sim | 0,0 – 13,0 |
| `eventos_24h` | numérico | **[NÃO DECLARADA]** | ✅ Sim | 0,0 – 9,0 |
| `disponibilidade_recursos` | numérico | **[NÃO DECLARADA]** (leitura provável: %) | ✅ Sim | 20,035 – 99,989 |

**Todas são obrigatórias** — `validar_paciente` levanta `PacienteInvalidoError` para qualquer
ausência. **Nenhuma unidade está declarada em nenhum arquivo do projeto.**

### 6.2 Tabela de gap

| Feature | Obrigatória | Origem atual | Disponível? | Solução proposta |
|---|---|---|---|---|
| `idade_media` | ✅ | Fase 6: gerador sintético. Fase 1: `age` **por paciente** (não média) | ❌ | Entrada manual/explícita na requisição. *(Futuro: média de idades do cadastro — exigiria data de nascimento, que não existe.)* |
| `carga_sistema` | ✅ | Fase 6: gerador sintético | ❌ | Entrada manual/explícita |
| `tempo_espera` | ✅ | Fase 6: gerador. Fase 2: tela "Agenda" é **UI sem backend nem persistência** | ❌ | Entrada manual/explícita |
| `fc_media` | ✅ | Fase 3: `bpm` (REST + MQTT `hospital/bpm`), **simulado por botão** | ⚠️ **Parcial** | **Única correspondência direta legítima**: `bpm → fc_media`. Declarar que a origem é **simulada** |
| `spo2_media` | ✅ | **Nenhuma fase** possui sensor de SpO₂ | ❌ | Entrada manual/explícita (não há sensor) |
| `pa_sistolica` | ✅ | **Nenhuma fase** possui sensor de pressão arterial | ❌ | Entrada manual/explícita |
| `temperatura` | ✅ | Fase 3: o **DHT22 mede temperatura AMBIENTE** (o payload REST carrega o mesmo sinal) | ❌ **Não** | ❌ **Descartado como fonte**: com a resposta **A1** (`temperatura` é **corporal**), o DHT22 **não** é fonte válida. Entrada manual/explícita (medição corporal). ⚠️ ver achado **A3** (distribuição do gerador) |
| `densidade_eventos` | ✅ | **Nenhuma fase** | ❌ | Entrada manual/explícita. *(Futuro: derivar de contagem de eventos — não existe tabela de eventos.)* |
| `eventos_24h` | ✅ | **Nenhuma fase** | ❌ | Entrada manual/explícita. *(Futuro: contar `monitoramentos` em 24 h — viável **após** haver histórico.)* |
| `disponibilidade_recursos` | ✅ | **Nenhuma fase** | ❌ | Entrada manual/explícita |

**Balanço após as respostas A1/A2: 1 de 10 tem correspondência (parcial e de origem simulada —
`bpm → fc_media`); 9 não têm nenhuma fonte.** A resposta A1 (`temperatura` corporal) **removeu** a
segunda correspondência que existia provisoriamente.

### 6.3 Avaliação das alternativas

| Alternativa | Viabilidade | Veredito |
|---|---|---|
| **A. Obter as features de outras fontes existentes** | ❌ **Inviável** para 8 features — nenhuma fase as produz. As 2 parciais vêm de telemetria **simulada** | **Descartada** |
| **B. Adaptar o modelo às variáveis realmente disponíveis** | ⚠️ Tecnicamente possível (retreinar com 2 features), **mas**: (i) o alvo `pico_risco` é construído de **6 indicadores** — removê-los torna o alvo irreconstruível e o modelo sem sentido; (ii) quebraria `metadata`, `sha256_da_base_usada`, os protocolos que dependem das colunas e os **290 testes**; (iii) metodologicamente é **criar um modelo novo**, não adaptar — e o alvo continuaria sintético e determinístico (nenhum ganho de validade); (iv) **violaria a restrição de não modificar a Fase 6** | **Descartada** |
| **C. Manter a simulação IoT separada da execução do modelo até haver dados suficientes** | ✅ Única que **não inventa dados**, não falsifica validade clínica e não altera a Fase 6 | ✅ **ADOTADA** |

### 6.4 ✅ Decisão adotada — alternativa C, com três salvaguardas

1. **Sem valores default.** O endpoint de avaliação exige **todas as 10 features** explicitamente —
   espelhando `validar_paciente`. **Nenhum valor é preenchido pelo backend.**
2. **Origem registrada.** `origem_dos_dados` (`manual` | `iot` | `importado`) gravado em cada
   avaliação; a telemetria IoT é persistida em `monitoramentos` e **não** é injetada automaticamente
   no modelo.
3. **Avisos sempre visíveis.** Toda resposta carrega `AVISO_DE_USO` + `LIMITACOES_PADRAO`
   (dados sintéticos, sem validação clínica, limiar operacional).

**Preparação (sem ativar):** o mapeador `DadosDeMonitoramento → features` será documentado **como
especificação** — **1 correspondência** (`bpm → fc_media`, de origem simulada) e **9 lacunas
explícitas** — para que a ativação futura seja mudança de configuração, não redesenho. A feature
`temperatura` **não** entra nesse mapeador (resposta A1: corporal ≠ ambiente medido pelo DHT22).

---

## 7. DECISÃO 5 — Seleção dos frontends

### 7.1 Análise dos três frontends

| Frontend | Stack | Estrutura | Papel proposto |
|---|---|---|---|
| **Fase 2 — `Ir_Alem/my-react-app`** | React 19.2.4 + Vite 8 + react-router-dom 7 | `pages/`, `components/`, `contexts/`, `services/` | ✅ **Web principal** |
| **Fase 5 — `CardioAssist`** | Expo ~57.0.20 + RN 0.86.3 + React 19.2.3 | `src/{screens,components,services,constants}`, `theme.js` | ✅ **Mobile principal** |
| **Fase 4 — `cardio-assistant`** | Expo ~54.0.34 + RN 0.81.5 + React 19.1.0 | Expo Router (`app/`), `screens/`, `utils/` | 🟡 **Fonte de componentes** |

### 7.2 ✅ Decisão

| Decisão | Escolha | Justificativa |
|---|---|---|
| **Web principal** | **Fase 2** (`my-react-app`) | Único frontend web "de verdade": roteamento, `AuthContext`, `ProtectedRoute`, build de produção com Vite, 4 páginas e CSS próprio. É o esqueleto natural de um portal administrativo |
| **Mobile principal** | **Fase 5** (`CardioAssist`) | É o **mais recente** (Expo ~57 vs ~54) e o de arquitetura mais limpa: `src/` organizado, `services/` com erros tipados (`WatsonApiError`), 5 componentes separados e `theme.js`. Escolher a base mais nova evita migração de SDK |
| **Fase 4** | **Fonte de componentes**, não base | Mantê-la como base criaria um segundo app mobile com Expo/RN **desatualizados** e duplicaria infraestrutura. O caminho é **portar** a tela de análise de imagem |
| **Novos frontends** | 🚫 **Nenhum** | Reaproveitar o que existe |

**Ressalvas registradas:**
- `AuthContext` da Fase 2 é **simulado** (credenciais fixas, token fake em `localStorage`) → substituir por login real.
- `services/api.js` da Fase 2 aponta para **jsonplaceholder** → substituir pelo backend central.
- `Dashboard` e `Schedule` da Fase 2 são **UI estática** (sem persistência).
- Os dois apps Expo usam **versões diferentes** (54 vs 57) — a unificação exige escolher uma base (a mais nova) e portar telas.

### 7.3 Funcionalidades reaproveitadas

| Origem | Reaproveitado |
|---|---|
| **Fase 2 (web)** | `AuthContext` (adaptar para JWT real), `ProtectedRoute`, `AppLayout`/topbar/nav, páginas `Dashboard`/`Patients`/`Schedule` (ligar ao backend), `App.css`/`index.css` |
| **Fase 4 (mobile/web)** | `screens/HomeScreen.js` (seleção + envio + exibição), `utils/uploadImage.ts` (FormData web/nativo), lógica de detecção de host do Metro (`constants/api.ts`) — consolidar com a da Fase 5 |
| **Fase 5 (mobile)** | `ChatScreen.js`, `ChatHeader`, `ChatInput`, `MessageBubble`, `TypingIndicator`, `ErrorBanner`, `theme.js`, `watsonApi.js` (renomear para `assistantApi.js`), `constants/api.js` |

### 7.4 Funcionalidades do MVP

| # | Funcionalidade | Origem |
|---|---|---|
| 1 | Login real (JWT) + guarda de rotas + perfil do usuário | Fase 2 (adaptado) |
| 2 | Lista e cadastro de snapshots/pacientes | Fase 2 (ligado ao backend) |
| 3 | **Avaliação de risco** (formulário com as 10 features → diagnóstico + protocolos + trilha) | **nova** (consome a Fase 6) |
| 4 | Histórico de avaliações | **nova** |
| 5 | Chat com o assistente | Fase 5 (via backend central) |
| 6 | Análise de imagem de raio-X | Fase 4 (via backend central) |
| 7 | Painel de monitoramento IoT (últimas leituras) | Fase 3 — **visualização apenas**, não alimenta o modelo |
| 8 | Agenda persistida | ⚠️ **fora do MVP** (hoje é UI sem backend) |

**Fora do MVP:** agendamento persistido, notificações push, offline-first, i18n, tema escuro, papel `PACIENTE`.

---

## 8. DECISÃO 6 — Segurança (síntese)

> 📄 **Plano completo:** [`PLANO_SEGURANCA.md`](PLANO_SEGURANCA.md)

| # | Decisão | Justificativa |
|---|---|---|
| 1 | **Rotação imediata** de todas as credenciais expostas | Um segredo versionado deve ser tratado como **comprometido** — removê-lo do Git não desfaz a exposição |
| 2 | **Externalização** para variáveis de ambiente | Padrão já correto na Fase 6 (`.env` + `.env.example` sem valores) |
| 3 | **Limpeza do histórico Git** como melhoria **recomendada e coordenada** | Operação destrutiva que afeta forks e 4 integrantes nas Fases 1 e 2 — exige autorização |
| 4 | **Prevenção**: varredura de segredos + teste automatizado | Reaproveitar `tests/test_seguranca.py` da Fase 6 |
| 5 | **Governança**: política de segredos, segregação dev/prod, rotação periódica | Sustentação |
| 6 | 🚫 **Nesta etapa: nenhuma alteração** nos repositórios anteriores | Restrição vigente |

🔒 **Nenhum valor de credencial é reproduzido em nenhum dos documentos desta etapa.**

---

## 9. Arquitetura definitiva proposta (para aprovação)

```text
┌──────────────────── CLIENTES ────────────────────┐
│ Web: React 19 + Vite 8            (Fase 2)       │
│ Mobile: Expo ~57 / RN 0.86        (Fase 5)       │
└──────────────────┬───────────────────────────────┘
                   │ HTTPS/JSON · Bearer JWT · /api/v1/*
                   ▼
┌──────────── BACKEND CENTRAL (FastAPI · uvicorn · :8000) ────────────┐
│  auth: PyJWT + bcrypt · RBAC (ADMIN/MEDICO/OPERADOR)                │
│  envelope RespostaAPI[T] + enum de erros                            │
│  rotas: /auth · /snapshots · /avaliacoes · /iot · /imagens · /chat  │
│                                                                     │
│  ┌─ IMPORTAÇÃO DIRETA (em processo) ──────────────────────────┐     │
│  │  cardioia (Fase 6)  →  orchestrator.executar_pipeline       │     │
│  │     ├ 4 agentes + handoffs reais + 2 tools                  │     │
│  │     ├ modelo .pkl (cache no startup)                        │     │
│  │     ├ 10 protocolos determinísticos                         │     │
│  │     └ contrato Pydantic RespostaDaExecucao                  │     │
│  │  IBM_API (Fase 5)   →  get_assistant()                      │     │
│  │  regras_iot (Fase 3) → módulo de domínio (origem declarada) │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                     │
│  ADAPTER HTTP ──▶ Fase 4 (Flask + TensorFlow 2.20 · :5001)          │
└──────────────────┬──────────────────────────────────────────────────┘
                   ▼
┌──────── PERSISTÊNCIA (SQLAlchemy 2.0 + SQLite) ─────────────────────┐
│ usuarios · pacientes · avaliacoes_de_risco                          │
│   ├ protocolos_aplicados · indicadores_deterministicos              │
│   └ passos_da_execucao                                             │
│ monitoramentos · analises_de_imagem · conversas/mensagens           │
│ eventos_de_auditoria · sessoes                                      │
└─────────────────────────────────────────────────────────────────────┘

INGESTÃO IoT (inalterada):
  ESP32 ──MQTT/TLS 8883──▶ HiveMQ Cloud ──▶ consumidor do backend
        tópicos: hospital/temperatura · hospital/bpm
```

**Princípios inegociáveis da arquitetura:**

| # | Princípio | Origem |
|---|---|---|
| P1 | **Python calcula; o LLM apenas redige** | Fase 6 |
| P2 | **Contrato único de saída** (`RespostaDaExecucao` generalizado) | Fase 6 |
| P3 | **Falha nunca vira sucesso** (`CONCLUIDO` exige diagnóstico e proíbe erros) | Fase 6 |
| P4 | **Segredos só em variável de ambiente** | Fase 6 |
| P5 | **Histórico append-only** com `id_execucao` como chave de correlação | nova |
| P6 | **Avisos clínicos sempre visíveis** (`AVISO_DE_USO` + `LIMITACOES_PADRAO`) | Fase 6 |
| P7 | **Nenhum valor de feature inventado ou preenchido por padrão** | Decisão D4 |
| P8 | **Núcleo determinístico testável sem LLM** (modo simulado) | Fase 6 |

---

## 10. Riscos consolidados

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|---|
| R1 | **Credenciais comprometidas em uso** | Alta (já expostas) | 🔴 Alto | Rotação imediata (Decisão 6) |
| R2 | **Import do SDK `agents` falha no startup** | Média | 🔴 Alto (backend não sobe) | Import tardio (M1) + resposta `503` explícita |
| R3 | **Conflito de porta 5000** | Alta (existe hoje) | 🔴 Alto | Mapa de portas (seção 3.5) |
| R4 | **Gap de 8 features** | Certeza | 🔴 Alto | Alternativa C, sem defaults (D4) |
| R5 | **Ambiguidade semântica de `temperatura` e do alvo** | Certeza | 🟡 Médio | Entidade neutra + confirmação do autor (achados A1/A2) |
| R6 | **Duplicação controlada nas Fases 3 e 4** | Certeza | 🟡 Médio | Registrar origem normativa + teste de equivalência |
| R7 | **Contrato rígido da Fase 6 rejeita payloads** | Alta | 🟡 Médio | Mapeador explícito + erro `422` com campo |
| R8 | **Conflito de dependências** (TF 2.20 × sklearn 1.8) | Média | 🟡 Médio | Serviço isolado para a Fase 4 (Decisão 1-C) |
| R9 | **SQLite sem criptografia em repouso** | Certeza | 🟡 Médio | Limitação declarada + minimização + LGPD |
| R10 | **Ausência de migrations (`alembic`)** | Certeza | 🟡 Médio | `create_all()` + script versionado |
| R11 | **Latência do LLM bloqueia o worker** | Média | 🟡 Médio | Modo simulado por padrão; `real` sob flag |
| R12 | **Dois apps Expo em versões diferentes** | Certeza | 🟡 Médio | Escolher a base mais nova (Fase 5) e portar telas |
| R13 | **Interpretação clínica indevida do resultado** | Média | 🔴 Alto | Avisos obrigatórios em toda resposta (P6) |

---

## 11. Resoluções do autor (Etapa B — fechada)

> ✅ Todas as questões abertas da Etapa B foram **respondidas**. Nenhuma permanece pendente.

| # | Questão | **Resolução** | Impacto |
|---|---|---|---|
| **Q1** | `pico_risco` é risco de sobrecarga assistencial **ou** clínico individual? | ✅ **CLÍNICO INDIVIDUAL** | entidade = **`pacientes`**; interpretação das 10 features documentada (seção 2.5); achado remanescente **A4** registrado |
| **Q2** | `temperatura` é ambiente **ou** corporal? | ✅ **CORPORAL** | ❌ **DHT22 descartado** como fonte; gap passa de 2/10 para **1/10**; achado remanescente **A3** registrado |
| **Q3** | Aprovação da alternativa **C** para o gap IoT | ✅ **APROVADA** | endpoint de avaliação exige as 10 features, **sem defaults** |
| **Q4** | Aprovação de **SQLite + SQLAlchemy** | ✅ **APROVADA** | `MODELO_DADOS.md` vigente |
| **Q5** | Aprovação de **PyJWT + bcrypt** e RBAC de 3 papéis | ✅ **APROVADA** | autenticação definida |
| **Q6** | Aprovação de **FastAPI + uvicorn** | ✅ **APROVADA** | Decisão D1 confirmada |
| **Q7** | Autorização para **sanitizar** a documentação | ✅ **EXECUTADA** | 0 valores sensíveis nos 6 documentos |
| **Q8** | Autorização para **rotacionar credenciais** | ✅ **APROVADA** | execução pelo titular das contas (ver `PLANO_SEGURANCA.md` §4) |
| **Q9** | Autorização para **reescrever o histórico Git** | ❌ **NÃO APROVADA** | **descartada**; adota-se a **alternativa mínima** (rotação + aviso) — `PLANO_SEGURANCA.md` §6.3 |
| **Q10** | Autorização para **instalar** ferramenta de varredura de segredos | ✅ **APROVADA** | a executar na Etapa C |

### 11.1 Consequência de Q9 (histórico Git)

| Item | Decisão |
|---|---|
| Reescrita do histórico (`git filter-repo`/BFG) | 🚫 **NÃO será executada** |
| Motivo | Não aprovada pelo autor (operação destrutiva que afeta forks e 4 integrantes) |
| Plano adotado | ✅ **Alternativa mínima**: rotação das credenciais + aviso documentado nos repositórios afetados |
| Eficácia | ✅ O valor exposto torna-se **inútil** após a rotação; a exposição histórica permanece apenas como registro |

---

## 12. Status e próximos passos

| Item | Status |
|---|---|
| Decisão 1 — Estratégia de integração | ✅ **Decidida** (A, com C apenas para a Fase 4) |
| Decisão 2 — Contrato comum de API | ✅ **Decidida** → [`CONTRATOS_API.md`](CONTRATOS_API.md) |
| Decisão 3 — Banco de dados e autenticação | ✅ **Decidida** → [`MODELO_DADOS.md`](MODELO_DADOS.md) |
| Decisão 4 — Gap IoT ↔ Fase 6 | ✅ **Decidida** (alternativa C) |
| Decisão 5 — Seleção de frontends | ✅ **Decidida** |
| Decisão 6 — Segurança | ✅ **Decidida** → [`PLANO_SEGURANCA.md`](PLANO_SEGURANCA.md) |
| Arquitetura definitiva | ✅ **Aprovada** (seção 9) |
| Questões abertas (Q1–Q10) | ✅ **Todas resolvidas** (seção 11) |
| Implementação do backend (Etapa C) | ✅ **AUTORIZADA** |

### Próxima etapa (Etapa C — implementação)

| Ordem | Entrega | Depende de |
|---|---|---|
| 1 | Esqueleto do backend FastAPI + envelope + enum de erros + `/health` | ✅ Q6 |
| 2 | Camada de persistência (SQLAlchemy + SQLite) + `create_all` | ✅ Q4 |
| 3 | Autenticação (JWT + bcrypt + RBAC) | ✅ Q5 |
| 4 | Integração da Fase 6 (import direto + cache + mapeador) | ✅ Q3 |
| 5 | Módulo `regras_iot` + rota de ingestão (telemetria **não** alimenta o modelo) | ✅ Q2 |
| 6 | Adapter da Fase 4 (`:5001`) + rota de imagem | — |
| 7 | Integração do assistente (Fase 5 via `IBM_API`) | — |
| 8 | Frontend web (Fase 2 adaptado) | 3, 4 |
| 9 | App mobile (Fase 5 + tela portada da Fase 4) | 3, 4, 6 |
| 10 | Testes de integração ponta a ponta + varredura de segredos | ✅ Q10 |

---

*Documento de decisões da Fase 7. Nenhuma linha de código foi escrita e nenhum arquivo das Fases 1 a 6
foi modificado. **Etapa B encerrada** — todas as decisões aprovadas pelo autor; a Etapa C
(implementação do backend) está **autorizada**.*