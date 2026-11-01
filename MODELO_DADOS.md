# CardioIA — Fase 7 · Modelo de Dados

> **Especificação da persistência e da autenticação**
> Documentos relacionados: [`DECISOES_ARQUITETURAIS.md`](DECISOES_ARQUITETURAIS.md) · [`CONTRATOS_API.md`](CONTRATOS_API.md)
>
> **Decisão de base:** **SQLite** via **SQLAlchemy 2.0.49** (já instalado), encapsulado por uma
> **porta de repositório** que permita migrar para PostgreSQL sem tocar nos serviços.
>
> 🔒 Nenhum valor de credencial aparece neste documento. **Nenhum dado real de paciente é modelado**
> — os dados do projeto são sintéticos.

---

## 1. Escopo e justificativa

| Item | Decisão |
|---|---|
| SGBD do MVP | **SQLite** (arquivo local, sem servidor) |
| Camada de acesso | **SQLAlchemy 2.0.49** (ORM + Core) |
| Migrations | ❌ **`alembic` não está instalado** → `Base.metadata.create_all()` + script versionado de migrações simples |
| Porta de abstração | **Repositórios** (um por agregado) — os serviços nunca escrevem SQL direto |
| Concorrência | `PRAGMA journal_mode=WAL` + `check_same_thread=False`; **worker único** no MVP |
| Criptografia em repouso | ❌ **não disponível** (SQLCipher não instalado) — **limitação declarada** |

**Por que SQLite no MVP:** nenhuma instalação nova; integridade transacional real (FK, constraints,
rollback); adequado a um projeto acadêmico demonstrativo single-node; a porta de repositório evita
dívida técnica.

**Por que não PostgreSQL agora:** exigiria servidor + driver (instalação) sem benefício no escopo atual.

**Por que não arquivos JSON/CSV:** sem integridade referencial, sem consultas e sem histórico
confiável — incompatível com o requisito de auditoria das decisões.

> ⚠️ **Não usar SQLite para dados reais de pacientes.** Com dados reais, migrar para PostgreSQL com
> criptografia em repouso e política de retenção formal.

---

## 2. Diagrama de entidades

```text
                        ┌──────────────┐
                        │  usuarios    │
                        └──┬────┬───┬──┘
        criado_por ┌───────┘    │   └────────┐
                   ▼            │            ▼
        ┌────────────────────┐  │   ┌──────────────────┐
        │  pacientes         │  │   │ eventos_de_      │
        │  (identidade)      │  │   │ auditoria        │
        └──┬──────────┬──────┘  │   └──────────────────┘
           │          │         │
           │          │         ▼
           │          │   ┌───────────────┐   ┌────────────────┐
           │          │   │  conversas    │──▶│   mensagens    │
           │          │   └───────────────┘   └────────────────┘
           │          │
           │          │        ┌──────────────────┐
           │          └───────▶│ analises_de_     │
           │                   │ imagem           │
           │                   └──────────────────┘
           │
           ▼
  ┌────────────────────────────────────────┐
  │  avaliacoes_de_risco                   │
  │   ◀── id_execucao (UUID da Fase 6)     │
  │   ◀── + as 10 FEATURES (estado clínico)│
  └──┬───────────┬───────────┬─────────────┘
     │           │           │
     ▼           ▼           ▼
┌──────────┐ ┌────────────┐ ┌──────────────────┐
│protocolos│ │indicadores_│ │ passos_da_       │
│_aplicados│ │deterministi│ │ execucao         │
└──────────┘ └────────────┘ └──────────────────┘

        ┌──────────────────┐        ┌──────────────┐
        │  monitoramentos  │        │   sessoes    │
        └──────────────────┘        └──────────────┘
             (IoT, independente)      (refresh tokens)
```

**Leitura (atualizada pelas respostas Q1/Q2):**
- **`pacientes`** guarda **apenas a identidade** — não o estado clínico.
- **`avaliacoes_de_risco`** é o agregado central e concentra **as 10 features** (estado do paciente no
  momento da avaliação), além de decompô-las em 3 tabelas-filhas e preservar o contrato original em
  `resposta_json`.
- Justificativa: com `pico_risco` **clínico individual**, cada avaliação é um **evento clínico
  datado**; manter as features no cadastro perderia o histórico e impediria comparar evoluções.

---

## 3. Tabelas

### 3.1 `usuarios`

| Coluna | Tipo | Restrições | Observação |
|---|---|---|---|
| `id` | UUID (TEXT 36) | PK | gerado pela aplicação |
| `nome` | TEXT(120) | NOT NULL | |
| `email` | TEXT(254) | NOT NULL, **UNIQUE**, índice | normalizado em minúsculas |
| `senha_hash` | TEXT | NOT NULL | **bcrypt**; nunca exposto em resposta |
| `papel` | TEXT | NOT NULL, CHECK IN (`ADMIN`,`MEDICO`,`OPERADOR`) | RBAC |
| `ativo` | BOOLEAN | NOT NULL, DEFAULT 1 | desativação sem exclusão |
| `criado_em` | DATETIME | NOT NULL | UTC |
| `ultimo_acesso` | DATETIME | NULL | atualizado no login |

### 3.2 `sessoes` (refresh tokens)

| Coluna | Tipo | Restrições | Observação |
|---|---|---|---|
| `id` | UUID | PK | |
| `id_usuario` | UUID | FK → `usuarios.id`, ON DELETE CASCADE | |
| `token_hash` | TEXT | NOT NULL, UNIQUE | **hash** do refresh token (nunca o valor) |
| `criado_em` | DATETIME | NOT NULL | |
| `expira_em` | DATETIME | NOT NULL | |
| `revogado_em` | DATETIME | NULL | logout / rotação |

### 3.3 `pacientes` (identidade)

> ✅ **Renomeada** de `snapshots_assistenciais` pela resposta **Q1** (`pico_risco` é **clínico
> individual**). Guarda **apenas a identidade** — o estado clínico fica na avaliação.

| Coluna | Tipo | Restrições | Observação |
|---|---|---|---|
| `id` | UUID | PK | |
| `nome` | TEXT(120) | NOT NULL | identificação do paciente |
| `ativo` | BOOLEAN | NOT NULL, DEFAULT 1 | desativação sem exclusão |
| `criado_em` | DATETIME | NOT NULL | UTC |
| `criado_por` | UUID | FK → `usuarios.id`, ON DELETE RESTRICT | |

> **Por que as 10 features NÃO ficam aqui:** cada avaliação captura um **estado clínico datado**.
> Mantê-las no cadastro sobrescreveria o histórico e impediria comparar a evolução do paciente.

### 3.4 `avaliacoes_de_risco` (agregado central)

**Identificação e estado clínico avaliado:**

| Coluna | Tipo | Restrições | Observação |
|---|---|---|---|
| `id` | UUID | PK | interno |
| **`id_execucao`** | UUID | **UNIQUE**, índice | ⚠️ **o MESMO UUID gerado pela Fase 6** — chave de correlação com a trilha |
| `id_paciente` | UUID | FK → `pacientes.id`, ON DELETE RESTRICT | |
| `id_usuario` | UUID | FK → `usuarios.id`, ON DELETE RESTRICT | quem solicitou |
| `criado_em` | DATETIME | NOT NULL, índice | momento da avaliação |
| **`idade_media`** | REAL | NOT NULL, CHECK ≥ 0 | ⚠️ **idade do paciente** (nome fixado pelo contrato) |
| **`carga_sistema`** | REAL | NOT NULL, CHECK ≥ 0 | contexto do episódio |
| **`tempo_espera`** | REAL | NOT NULL, CHECK ≥ 0 | tempo de espera do paciente |
| **`fc_media`** | REAL | NOT NULL, CHECK ≥ 0 | FC média do paciente |
| **`spo2_media`** | REAL | NOT NULL, CHECK ≥ 0 | SpO₂ média do paciente |
| **`pa_sistolica`** | REAL | NOT NULL, CHECK ≥ 0 | PA sistólica do paciente |
| **`temperatura`** | REAL | NOT NULL, CHECK ≥ 0 | ⚠️ **corporal** (Q2) — feature de **baixa confiança** (achado A3) |
| **`densidade_eventos`** | REAL | NOT NULL, CHECK ≥ 0 | contexto do episódio |
| **`eventos_24h`** | REAL | NOT NULL, CHECK ≥ 0 | eventos do paciente em 24 h |
| **`disponibilidade_recursos`** | REAL | NOT NULL, CHECK ≥ 0 | contexto do episódio |
| `origem_dos_dados` | TEXT | NOT NULL, CHECK IN (`manual`,`iot`,`importado`) | rastreabilidade |

**Resultado da execução (decomposto do `RespostaDaExecucao`):**

| Coluna | Tipo | Restrições | Observação |
|---|---|---|---|
| `status` | TEXT | NOT NULL, CHECK IN (`CONCLUIDO`,`CONCLUIDO_COM_RESSALVAS`,`INCOMPLETO`,`ERRO`) | **os 4 valores da Fase 6** |
| `modo` | TEXT | NOT NULL, CHECK IN (`simulado`,`real`) | |
| `agente_final` | TEXT | NULL | da Fase 6 |
| `versao_do_sdk` | TEXT | NULL | da Fase 6 |
| `duracao_segundos` | REAL | NULL, CHECK ≥ 0 | da Fase 6 |
| `probabilidade_risco` | REAL | NULL, CHECK 0–1 | valor **cru**, sem arredondamento |
| `pico_risco_previsto` | INTEGER | NULL, CHECK IN (0,1) | |
| `classificacao_risco` | TEXT | NULL, CHECK IN (`sem_pico_de_risco`,`pico_de_risco`) | |
| `modelo_utilizado` | TEXT | NULL | ex.: `Random Forest` |
| `classe_do_estimador` | TEXT | NULL | ex.: `RandomForestClassifier` |
| `limiar_decisao` | REAL | NULL, CHECK 0–1 | 0.5 (operacional) |
| `regra_de_decisao` | TEXT | NULL | |
| `sha256_da_base_usada` | TEXT | NULL | de `origem_do_modelo` — **qual** base treinou |
| **`resposta_json`** | JSON/TEXT | NULL | **contrato `RespostaDaExecucao` completo** (`como_dicionario()`) |
| `features_json` | JSON/TEXT | NULL | cópia serializada das 10 features + `origem_dos_dados` |
| `avisos_json` | JSON/TEXT | NULL | `avisos` da Fase 6 |
| `erros_json` | JSON/TEXT | NULL | `erros` da Fase 6 |

**Por que `resposta_json` além das colunas decompostas:** permite **auditar a decisão original** sem
depender de a Fase 6 ser reexecutável no futuro. As colunas decompostas existem para **consulta e
relatório**; `features_json` preserva exatamente o que foi enviado ao modelo.

> **Nota de modelagem:** as 10 features são **NOT NULL sem default** — a mesma regra do contrato do
> modelo (nenhum valor inventado).

### 3.5 `protocolos_aplicados`

| Coluna | Tipo | Restrições | Origem (1:1 com `ProtocoloAplicavel`) |
|---|---|---|---|
| `id` | UUID | PK | — |
| `id_avaliacao` | UUID | FK → `avaliacoes_de_risco.id`, ON DELETE CASCADE | — |
| `ordem` | INTEGER | NOT NULL, CHECK 1–10 | `ordem` |
| `identificador` | TEXT | NOT NULL | `identificador` |
| `texto_oficial` | TEXT | NOT NULL | `texto_oficial` |
| `acao` | TEXT | NOT NULL | `acao` |
| `condicao_satisfeita` | TEXT | NOT NULL | `condicao_satisfeita` |
| `operador` | TEXT | NOT NULL, CHECK IN (`<`,`>`,`==`) | `operador` |
| `limiar` | REAL | NOT NULL | `limiar` |
| `valor_observado` | REAL | NOT NULL | `valor_observado` |
| `origem_do_valor` | TEXT | NOT NULL | `origem_do_valor` |
| `usa_modelo` | BOOLEAN | NOT NULL, DEFAULT 0 | `usa_modelo` |

**Restrição:** `UNIQUE (id_avaliacao, identificador)` — garante o princípio "sem duplicatas" da
camada de protocolos da Fase 6.

### 3.6 `indicadores_deterministicos`

| Coluna | Tipo | Restrições |
|---|---|---|
| `id` | UUID | PK |
| `id_avaliacao` | UUID | FK → `avaliacoes_de_risco.id`, ON DELETE CASCADE |
| `nome` | TEXT | NOT NULL |
| `coluna` | TEXT | NULL (NULL na regra que usa o modelo) |
| `operador` | TEXT | NOT NULL, CHECK IN (`<`,`>`,`==`) |
| `limiar` | REAL | NOT NULL |
| `valor_observado` | REAL | NOT NULL |
| `satisfeito` | BOOLEAN | NOT NULL |
| `origem` | TEXT | NOT NULL |

### 3.7 `passos_da_execucao`

| Coluna | Tipo | Restrições |
|---|---|---|
| `id` | UUID | PK |
| `id_avaliacao` | UUID | FK → `avaliacoes_de_risco.id`, ON DELETE CASCADE |
| `ordem` | INTEGER | NOT NULL, CHECK ≥ 1 |
| `tipo` | TEXT | NOT NULL, CHECK IN (`handoff`,`tool`,`agente`,`validacao`,`erro`) |
| `agente` | TEXT | NOT NULL |
| `detalhe` | TEXT | NOT NULL |
| `sucesso` | BOOLEAN | NOT NULL, DEFAULT 1 |

**Restrição:** `UNIQUE (id_avaliacao, ordem)`.
**Nota:** os handoffs ficam registrados aqui (`tipo='handoff'`) — é a **trilha auditável** da Fase 6.

### 3.8 `monitoramentos` (telemetria IoT)

| Coluna | Tipo | Restrições | Observação |
|---|---|---|---|
| `id` | UUID | PK | |
| `id_paciente` | UUID | FK → `pacientes.id`, **NULL**, ON DELETE SET NULL | vinculação **opcional** |
| `id_dispositivo` | TEXT(64) | NOT NULL, índice | o firmware não envia — o backend exige |
| `recebido_em` | DATETIME | NOT NULL, índice | **carimbado pelo backend** |
| `temperatura` | REAL | NULL | Fase 3 |
| `umidade` | REAL | NULL | Fase 3 (Parte 1) |
| `luminosidade` | REAL | NULL | Fase 3 (Parte 1) |
| `bpm` | INTEGER | NULL, CHECK ≥ 0 | Fase 3 (simulado) |
| `movimento` | BOOLEAN | NULL | Fase 3 (apenas REST) |
| `origem_transporte` | TEXT | NOT NULL, CHECK IN (`mqtt`,`rest`,`simulado`) | |
| `payload_json` | JSON/TEXT | NULL | bruto, para auditoria |

**Restrição:** `CHECK (temperatura IS NOT NULL OR bpm IS NOT NULL)` — pelo menos um sinal vital.
**Deduplicação:** `UNIQUE (id_dispositivo, recebido_em)` (idempotência da ingestão).
**⚠️ Nota:** esta tabela **não** alimenta o modelo preditivo no MVP (Decisão D4).

### 3.9 `analises_de_imagem`

| Coluna | Tipo | Restrições | Observação |
|---|---|---|---|
| `id` | UUID | PK | |
| `id_paciente` | UUID | FK → `pacientes.id`, NULL | vinculação opcional |
| `id_usuario` | UUID | FK → `usuarios.id`, ON DELETE RESTRICT | |
| `criado_em` | DATETIME | NOT NULL, índice | |
| `nome_arquivo` | TEXT(255) | NOT NULL | metadado do upload |
| `mime` | TEXT(100) | NOT NULL | validado na borda |
| `tamanho_bytes` | INTEGER | NOT NULL, CHECK > 0 | validado na borda |
| **`hash_sha256`** | TEXT(64) | NOT NULL, índice | ⚠️ **o binário NÃO é armazenado** |
| `classe` | TEXT | NOT NULL, CHECK IN (`Normal`,`Pneumonia`) | da Fase 4 |
| `confianca` | REAL | NOT NULL, CHECK 0–100 | da Fase 4 |
| `modelo_utilizado` | TEXT | NOT NULL | acrescentado pela Fase 7 |
| `limiar_decisao` | REAL | NOT NULL, CHECK 0–1 | 0.5 |
| `resposta_json` | JSON/TEXT | NULL | contrato completo |
| `erro` | TEXT | NULL | quando a análise falha |

> 🔒 **Decisão de privacidade:** a imagem **não** é persistida por padrão (dado sensível). Guarda-se
> apenas o `hash_sha256` (permite detectar reenvio/duplicidade) e os metadados. Um armazenamento
> futuro exigirá decisão explícita e política de retenção.

### 3.10 `conversas` e `mensagens`

**`conversas`:**

| Coluna | Tipo | Restrições |
|---|---|---|
| `id` | UUID | PK |
| `id_usuario` | UUID | FK → `usuarios.id`, ON DELETE CASCADE |
| `id_paciente` | UUID | FK → `pacientes.id`, NULL |
| `canal` | TEXT | NOT NULL, CHECK IN (`web`,`mobile`) |
| `iniciada_em` | DATETIME | NOT NULL |
| `encerrada_em` | DATETIME | NULL |

**`mensagens`:**

| Coluna | Tipo | Restrições | Observação |
|---|---|---|---|
| `id` | UUID | PK | |
| `id_conversa` | UUID | FK → `conversas.id`, ON DELETE CASCADE | |
| `papel` | TEXT | NOT NULL, CHECK IN (`user`,`assistant`) | |
| `conteudo` | TEXT | NOT NULL | |
| `criado_em` | DATETIME | NOT NULL | |
| **`session_id_do_provedor`** | TEXT | NULL | 🔒 **interno** — nunca devolvido ao cliente |
| `erro` | TEXT | NULL | quando o turno falha |

### 3.11 `eventos_de_auditoria`

| Coluna | Tipo | Restrições | Observação |
|---|---|---|---|
| `id` | UUID | PK | |
| `id_usuario` | UUID | FK → `usuarios.id`, NULL, ON DELETE SET NULL | NULL em eventos de sistema |
| `acao` | TEXT | NOT NULL, índice | ex.: `login`, `criar_avaliacao`, `criar_usuario` |
| `entidade` | TEXT | NOT NULL | ex.: `avaliacoes_de_risco` |
| `id_entidade` | TEXT | NULL | |
| `criado_em` | DATETIME | NOT NULL, índice | |
| `ip` | TEXT(45) | NULL | IPv4/IPv6 |
| `detalhe_json` | JSON/TEXT | NULL | **sem payload clínico nem token** |

### 3.12 `versoes_do_esquema` — tabela de **controle técnico**

> ⚠️ **Não pertence ao domínio.** É uma tabela de infraestrutura, introduzida porque
> **`alembic` não está instalado** neste ambiente (verificado). Sem ela não haveria como
> saber qual versão do esquema está aplicada no arquivo do banco — e o servidor poderia
> operar sobre um esquema divergente sem perceber.

| Coluna | Tipo | Restrições | Observação |
|---|---|---|---|
| `versao` | INTEGER | PK | versão do esquema (histórico em `app/dados/esquema.py::HISTORICO`) |
| `descricao` | TEXT(200) | NOT NULL | texto legível da versão |
| `aplicada_em` | DATETIME | NOT NULL | UTC |

**Comportamento:** `preparar_banco()` cria o que faltar e **valida** a versão; se o banco
estiver em versão diferente da esperada, levanta `EsquemaIncompativelError` e o servidor
**não sobe** (falha rápida em vez de operação silenciosa sobre esquema errado).

**Migração para `alembic`:** o `metadata` está centralizado em `app.dados.base.Base`, então
a adoção futura é direta (`alembic revision --autogenerate`), e a tabela de controle pode
ser substituída por `alembic_version`.

---

## 4. Índices e restrições

### 4.1 Índices

| Tabela | Índice | Motivo |
|---|---|---|
| `usuarios` | `UNIQUE (email)` | login e unicidade |
| `sessoes` | `UNIQUE (token_hash)`; `(id_usuario, expira_em)` | validação de refresh; limpeza de expirados |
| `pacientes` | `(criado_em DESC)` | listagem |
| `avaliacoes_de_risco` | **`UNIQUE (id_execucao)`** | correlação com a Fase 6 |
| `avaliacoes_de_risco` | `(id_paciente, criado_em DESC)` | histórico por paciente |
| `avaliacoes_de_risco` | `(status)`, `(criado_em DESC)` | filtros e relatórios |
| `protocolos_aplicados` | `UNIQUE (id_avaliacao, identificador)` | sem duplicatas |
| `passos_da_execucao` | `UNIQUE (id_avaliacao, ordem)` | ordem da trilha |
| `monitoramentos` | `(id_dispositivo, recebido_em DESC)`; `UNIQUE (id_dispositivo, recebido_em)` | consulta e deduplicação |
| `analises_de_imagem` | `(id_paciente, criado_em DESC)`; `(hash_sha256)` | histórico e detecção de reenvio |
| `mensagens` | `(id_conversa, criado_em)` | histórico da conversa |
| `eventos_de_auditoria` | `(criado_em DESC)`; `(acao)` | auditoria |

### 4.2 Regras de integridade

| Regra | Implementação |
|---|---|
| Histórico não se perde ao remover usuário | `ON DELETE RESTRICT` em `avaliacoes_de_risco.id_usuario` e `pacientes.criado_por` |
| Exclusão de avaliação remove as filhas | `ON DELETE CASCADE` nas 3 tabelas-filhas |
| Telemetria sobrevive à remoção do paciente | `ON DELETE SET NULL` em `monitoramentos.id_paciente` |
| Paciente não é excluído, é desativado | `pacientes.ativo` (soft delete) |
| Features nunca negativas | `CHECK (coluna >= 0)` nas 10 features |
| Pelo menos um sinal vital na telemetria | `CHECK (temperatura IS NOT NULL OR bpm IS NOT NULL)` |
| Nenhum valor default para features | `NOT NULL` **sem** `DEFAULT` |

---

## 5. Persistência do histórico e auditoria

### 5.1 Fluxo de uma avaliação

```text
POST /api/v1/avaliacoes   { id_paciente, <10 features>, origem_dos_dados, modo }
   │
   ├─ 1. valida o contrato (Paciente + as 10 features obrigatórias)
   ├─ 2. mapeia as 10 features (função pura, sem default)
   ├─ 3. chama cardioia.orchestrator.executar_pipeline(...)   [em processo]
   │       └─ devolve RespostaDaExecucao (id_execucao = UUID4)
   ├─ 4. abre UMA transação e grava:
   │       ├─ avaliacoes_de_risco            (10 features + colunas + resposta_json + features_json)
   │       ├─ protocolos_aplicados[]         (de resposta.protocolos)
   │       ├─ indicadores_deterministicos[]  (de resposta.indicadores)
   │       └─ passos_da_execucao[]           (de resposta.passos)
   ├─ 5. grava eventos_de_auditoria (acao='criar_avaliacao')
   └─ 6. devolve o envelope com dados = RespostaDaExecucao
```

### 5.2 Princípios

| # | Princípio | Consequência |
|---|---|---|
| 1 | **Append-only** | avaliações nunca são editadas; correção = nova avaliação |
| 2 | **Transação única** | ou o agregado inteiro é gravado, ou nada (sem avaliação "meio salva") |
| 3 | **`id_execucao` como chave de correlação** | liga API ↔ banco ↔ trilha da Fase 6 |
| 4 | **Contrato íntegro preservado** | `resposta_json` guarda o `como_dicionario()` completo |
| 5 | **Rastreabilidade do modelo** | `modelo_utilizado` + `sha256_da_base_usada` dizem **qual** modelo decidiu |
| 6 | **Falha registrada** | `status` + `erros_json`; nada de sucesso por omissão |
| 7 | **Binário de imagem fora do banco** | apenas `hash_sha256` + metadados |

---

## 6. Autenticação e sessões

### 6.1 Fluxo

```text
POST /auth/login  {email, senha}
   ├─ 1. busca usuario por email (normalizado)
   ├─ 2. bcrypt.checkpw(senha, usuario.senha_hash)   → 401 NAO_AUTENTICADO se falhar
   ├─ 3. verifica usuario.ativo                      → 403 NAO_AUTORIZADO se inativo
   ├─ 4. gera access_token (JWT HS256, 15–30 min) com claims:
   │       sub=id_usuario · papel · exp · iat · jti
   ├─ 5. gera refresh_token aleatório; grava APENAS o hash em `sessoes`
   └─ 6. devolve {access_token, refresh_token, expira_em}
        (registra eventos_de_auditoria: acao='login')

Requisição autenticada: Authorization: Bearer <access_token>
   └─ dependency do FastAPI valida assinatura + exp + `ativo` + papel exigido

POST /auth/refresh  {refresh_token}
   ├─ 1. calcula o hash e procura em `sessoes` (não revogado, não expirado)
   ├─ 2. ROTAÇÃO: revoga o token usado e emite um novo par
   └─ 3. devolve novo {access_token, refresh_token}

POST /auth/logout → marca `sessoes.revogado_em`
```

### 6.2 Decisões de autenticação

| Item | Decisão | Motivo |
|---|---|---|
| Biblioteca JWT | **PyJWT 2.13.0** (instalada) | ❌ `python-jose` **não** está instalada |
| Algoritmo | **HS256** com `JWT_SECRET` em `.env` | Simples e suficiente para o MVP |
| Hash de senha | **bcrypt 5.0.0** (instalada), cost ≥ 12 | ❌ `passlib` **não** está instalada |
| Access token | 15–30 min | Reduz a janela de abuso |
| Refresh token | Armazenado **só como hash**, com rotação | Um vazamento do banco não expõe o token |
| Falha rápida | `JWT_SECRET` ausente → backend **não sobe** | Evita rodar com segredo default |
| Papéis | `ADMIN`, `MEDICO`, `OPERADOR` | Menor privilégio |
| Papel `PACIENTE` | **fora do MVP** | Sem requisito que o justifique |
| Rate limiting no login | contador simples por `email` + IP | ⚠️ nenhuma lib instalada — **limitação declarada** |
| Logs | nunca registrar senha, token ou payload clínico | Minimização |

### 6.3 Matriz de permissões

| Recurso / ação | `ADMIN` | `MEDICO` | `OPERADOR` |
|---|:---:|:---:|:---:|
| Criar/listar usuários | ✅ | — | — |
| Criar/editar snapshots | ✅ | ✅ | — |
| Solicitar avaliação de risco | ✅ | ✅ | — |
| Ler histórico de avaliações | ✅ | ✅ | — |
| Registrar telemetria IoT | ✅ | ✅ | ✅ |
| Ler telemetria IoT | ✅ | ✅ | ✅ |
| Analisar imagem | ✅ | ✅ | — |
| Conversar com o assistente | ✅ | ✅ | ✅ |
| Ler eventos de auditoria | ✅ | — | — |

---

## 7. Migração SQLite → PostgreSQL

| Aspecto | Como fica preparado |
|---|---|
| URL do banco | **única variável** (`DATABASE_URL`) — troca `sqlite:///...` por `postgresql+psycopg://...` |
| Acesso a dados | **somente** pelos repositórios (nenhum SQL direto nos serviços) |
| Tipos | usados tipos portáveis do SQLAlchemy (`String`, `Float`, `Integer`, `Boolean`, `DateTime`, `JSON`) |
| UUID | armazenado como `TEXT(36)` no SQLite; migrar para `UUID` nativo no PostgreSQL |
| JSON | `JSON` do SQLAlchemy (SQLite: TEXT; PostgreSQL: `JSONB`) |
| Booleano | mapeado para `BOOLEAN` (o SQLite usa 0/1 internamente) |
| Diferenças de dialeto | ⚠️ `ON DELETE SET NULL` e `CHECK` funcionam em ambos; ⚠️ o SQLite exige `PRAGMA foreign_keys=ON` |
| Migrations | ❌ `alembic` ausente → no MVP, `create_all()` + **tabela de controle `versoes_do_esquema`** + script versionado (`app/dados/esquema.py`); adotar `alembic` se o projeto avançar |

**Procedimento de migração (futuro):** exportar por tabela em ordem topológica → carregar no
PostgreSQL → validar contagens e integridade → trocar `DATABASE_URL` → executar a suíte de testes de
integração.

---

## 8. Limitações, retenção e LGPD

### 8.1 Limitações declaradas

| # | Limitação | Impacto |
|---|---|---|
| L1 | **Sem criptografia em repouso** (SQLCipher não instalado) | Dado sensível legível no arquivo do banco |
| L2 | **Concorrência de escrita limitada** (lock global do SQLite) | Adequado só a single-node/baixa carga |
| L3 | **Sem migrations automáticas** (`alembic` ausente) | Mudança de schema exige script manual; a versão aplicada fica em `versoes_do_esquema` |
| L4 | **Worker único recomendado** | Sem escalabilidade horizontal |
| L5 | **Sem versionamento de esquema em runtime** | Necessário controle manual de versão do banco |
| L6 | **Rate limiting de login rudimentar** | Proteção parcial contra força bruta |
| L7 | **Backup manual** | Sem rotina automática no MVP |

### 8.2 Minimização e retenção

| Dado | Decisão |
|---|---|
| **Imagem de raio-X** | ❌ **não persistida** — apenas `hash_sha256` + metadados |
| **Senha** | apenas hash bcrypt |
| **Refresh token** | apenas hash |
| **`session_id` do provedor LLM** | armazenado para continuidade, **nunca** exposto |
| **Payload clínico em logs** | ❌ proibido |
| **Auditoria** | `detalhe_json` **sem** payload clínico nem token |
| **Retenção** | ⏳ a definir pelo autor — recomendação: avaliações e auditoria mantidas; telemetria com retenção limitada |

### 8.3 Aviso LGPD

| Item | Situação |
|---|---|
| Dados atuais | **100% sintéticos** (`np.random.seed(42)`, base gerada por regras) — **não há titular de dados** |
| Titular | Com a resposta **Q1** (risco **clínico individual**), em cenário real o **paciente é o titular** dos dados |
| Avisos obrigatórios | Toda resposta de risco carrega `AVISO_DE_USO` + `LIMITACOES_PADRAO` |
| Se houver dados reais | ⚠️ exigirá: base legal, consentimento, finalidade, criptografia em repouso, política de retenção, controle de acesso auditável e DPIA |
| Anonimização | ⚠️ com a leitura individual, os dados são **pessoais** (não agregados) → a minimização no cadastro (apenas `nome`) reduz a superfície |
| Feature sensível | ⚠️ `temperatura` **corporal** (Q2) é dado de saúde — mesmo rigor das demais |
| Direito do titular | ⏳ a definir (não há titular hoje); o histórico append-only exigirá política de retenção |

---

## 9. Convenções de implementação

| # | Convenção |
|---|---|
| C1 | Um **repositório por agregado** (`UsuarioRepositorio`, `SnapshotRepositorio`, `AvaliacaoRepositorio`, …) |
| C2 | **Nenhum** `commit()` fora da camada de repositório/serviço |
| C3 | Datas sempre em **UTC** |
| C4 | `PRAGMA foreign_keys=ON` em toda conexão (obrigatório no SQLite) |
| C5 | `PRAGMA journal_mode=WAL` para concorrência de leitura |
| C6 | Enumerações como `TEXT` + `CHECK` (legível e portável) |
| C7 | Nada de `DEFAULT` para features — a ausência é erro, não valor implícito |
| C8 | Testes usam **banco em memória** (`sqlite:///:memory:`) |
| C9 | Seeds de desenvolvimento **nunca** em produção |
| C10 | Toda migração de schema entra em script versionado com data |

---

*Especificação de dados da Fase 7. Nenhum valor de credencial é reproduzido neste documento.
Nenhuma linha de código foi escrita nesta etapa.*