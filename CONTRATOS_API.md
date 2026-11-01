# CardioIA — Fase 7 · Contratos de API

> **Especificação do contrato comum de comunicação**
> Documentos relacionados: [`DECISOES_ARQUITETURAIS.md`](DECISOES_ARQUITETURAIS.md) · [`MODELO_DADOS.md`](MODELO_DADOS.md)
>
> **Princípio deste documento:** todo campo declarado como "existente" foi verificado no código das
> Fases 1 a 6. Todo campo marcado como "novo" é **introduzido** pela Fase 7. **Nenhuma compatibilidade
> entre contratos é presumida** — as incompatibilidades estão listadas na seção 7.
>
> 🔒 Nenhum valor de credencial aparece neste documento.

---

## 1. Convenções gerais

| Item | Convenção |
|---|---|
| Base URL | `/api/v1` |
| Transporte | HTTPS (produção) / HTTP local (dev) |
| Formato | `application/json` (exceto upload de imagem: `multipart/form-data`) |
| Autenticação | `Authorization: Bearer <JWT>` — **exceto** `/health` e ingestão IoT |
| Charset | UTF-8 |
| Datas | ISO-8601 com timezone UTC (`2026-10-31T12:00:00Z`) |
| Identificadores | UUID v4 em texto (minúsculo) |
| Números decimais | JSON number; **probabilidade nunca arredondada na origem** |
| Nomes de campo | `snake_case` (segue o padrão da Fase 6) |
| Idempotência | `POST /iot/leituras` aceita `id_dispositivo` + `recebido_em` como chave de deduplicação |
| Paginação | `?limite=` (padrão 50, máx. 200) e `?deslocamento=` |

### 1.1 Regras transversais

| # | Regra | Origem |
|---|---|---|
| R1 | **Falha nunca vira sucesso** — `status=CONCLUIDO` exige `dados` presente e `erros` vazio | Fase 6 (`risk_result.py`) |
| R2 | **`limitacoes` e `avisos` sempre presentes** nas respostas que envolvem decisão automatizada | Fase 6 (`LIMITACOES_PADRAO`, `AVISO_DE_USO`) |
| R3 | **Nenhum campo de feature é preenchido por padrão** — as 10 são obrigatórias na entrada do modelo | Fase 6 (`validar_paciente`) + Decisão D4 |
| R4 | **Campos desconhecidos são rejeitados** (`extra="forbid"`) | Fase 6 (contratos Pydantic) |
| R5 | **Erros trazem código estável** (não só texto livre) | Fase 5 (`statusToCode`) |
| R6 | **O `session_id` do provedor LLM nunca é exposto ao cliente** | Decisão D2 |

---

## 2. Envelope comum — `RespostaAPI[T]`

Generalização do `RespostaDaExecucao` da Fase 6 para todas as respostas.

```text
RespostaAPI[T]
├── id_execucao      : str (UUID4)          # EXISTE na Fase 6
├── gerado_em        : datetime (UTC)       # EXISTE na Fase 6
├── status           : StatusDaResposta     # EXISTE na Fase 6 (StatusDaExecucao)
├── dados            : T | None             # NOVO (generalização)
├── avisos           : list[str]            # EXISTE na Fase 6
├── limitacoes       : list[str]            # EXISTE na Fase 6
├── erros            : list[ErroDaAPI]      # PARCIAL (Fase 6 tem list[str] → estrutura nova)
└── metadados        : dict[str, Any]       # NOVO
```

| Campo | Obrigatório | Observação |
|---|---|---|
| `id_execucao` | ✅ | UUID4. **Nas avaliações de risco é o MESMO `id_execucao` gerado pela Fase 6** — chave de correlação com a trilha e com o banco |
| `gerado_em` | ✅ | UTC |
| `status` | ✅ | Ver 2.1 |
| `dados` | ⚠️ condicional | Obrigatório quando `status=CONCLUIDO`; `null` em `ERRO`/`INCOMPLETO` |
| `avisos` | ✅ (pode ser `[]`) | Avisos de faixa do modelo, de sessão, etc. |
| `limitacoes` | ✅ | Padrão: `LIMITACOES_PADRAO` da Fase 6 |
| `erros` | ✅ (pode ser `[]`) | Obrigatório **não vazio** quando `status ∈ {ERRO, INCOMPLETO}` |
| `metadados` | ✅ (pode ser `{}`) | `versao_api`, `origem`, `duracao_segundos`, `id_paciente`, `id_usuario` |

### 2.1 `StatusDaResposta` (enum — **idêntico** ao da Fase 6)

| Valor | Significado | HTTP típico |
|---|---|---|
| `CONCLUIDO` | Sucesso com dados válidos | 200 / 201 |
| `CONCLUIDO_COM_RESSALVAS` | Sucesso, porém com avisos relevantes (ex.: narrativa divergente) | 200 |
| `INCOMPLETO` | Executou parcialmente; **exige** ao menos um erro | 200 ou 422 |
| `ERRO` | Falhou; **exige** ao menos um erro | 4xx / 5xx |

> ⚠️ **Não existe** um segundo eixo de status. Os códigos HTTP são o transporte; `status` é a
> semântica do domínio. O mapeamento entre os dois está na seção 3.2.

---

## 3. Erros

### 3.1 `ErroDaAPI`

```text
ErroDaAPI
├── codigo    : str (enum estável)   # ex.: "PACIENTE_INVALIDO"
├── mensagem  : str                  # texto legível (do próprio erro da origem)
├── campo     : str | None           # campo culpado, quando aplicável
└── detalhe   : str | None           # informação adicional (nunca segredo)
```

### 3.2 Enum de códigos e mapeamento

| Código | HTTP | Origem real no código | Situação |
|---|---|---|---|
| `CONTRATO_VIOLADO` | 422 | `pydantic.ValidationError` | novo |
| `PACIENTE_INVALIDO` | 422 | `cardioia.ml.predict.PacienteInvalidoError` | novo (exceção já existe) |
| `DADOS_DO_PACIENTE_INVALIDOS` | 422 | `cardioia.knowledge.protocols.DadosDoPacienteInvalidosError` | novo (exceção já existe) |
| `MODELO_INDISPONIVEL` | 503 | `cardioia.ml.predict.ModeloNaoEncontradoError` | novo (exceção já existe) |
| `MODELO_INCOMPATIVEL` | 500 | `cardioia.ml.predict.ModeloIncompativelError` | novo (exceção já existe) |
| `FALHA_DE_PREVISAO` | 500 | `cardioia.ml.predict.ErroDePrevisao` | novo (exceção já existe) |
| `BASE_DE_PROTOCOLOS_INVALIDA` | 500 | `cardioia.knowledge.protocols.BaseDeConhecimentoInvalidaError` | novo (exceção já existe) |
| `NAO_CONFIGURADO` | 501 | Fase 5: `watson_configured=false` | ✅ **já existe** |
| `FALHA_DE_AUTENTICACAO_EXTERNA` | **502** | Fase 5: `auth-failed` | código herdado · **transporte corrigido** (§3.2.1) |
| `COTA_EXCEDIDA` | 429 | Fase 5: `quota` | ✅ **já existe** |
| `TIMEOUT_EXTERNO` | 504 | Fase 5: `timeout` | ✅ **já existe** |
| `ERRO_DE_SERVICO_EXTERNO` | 502 | Fase 5: `watson-error` | ✅ **já existe** |
| `ERRO_DE_SERVICO_DE_VISAO` | 502 | Fase 4: HTTP 500 do `/predict` | novo |
| `NAO_AUTENTICADO` | 401 | JWT ausente/inválido/expirado | novo |
| `NAO_AUTORIZADO` | 403 | RBAC | novo |
| `NAO_ENCONTRADO` | 404 | recurso inexistente | novo |
| `CONFLITO` | 409 | e-mail duplicado, `id_execucao` repetido | novo |
| `LIMITE_EXCEDIDO` | 413 | upload de imagem | novo |
| `TAXA_EXCEDIDA` | 429 | rate limit de login | novo |
| `ERRO_INTERNO` | 500 | falha inesperada | novo |

> **Nota:** os 5 códigos marcados como "✅ já existem" são herdados da Fase 5 — **não foram inventados**.

### 3.2.1 Correção declarada: `FALHA_DE_AUTENTICACAO_EXTERNA` não usa mais `507`

A Fase 5 usava **507** para `auth-failed` — nos **dois lados** do seu contrato
(`Backend/app.py` → `friendly_watson_error` devolve 507; `watsonApi.js` → `statusToCode`
lê 507). O valor foi herdado fielmente na Etapa C e a auditoria o reprovou:

| | |
|---|---|
| **Problema** | `507` significa **`Insufficient Storage`** (RFC 4918 §11.5, família WebDAV). Nada tem a ver com autenticação. Um cliente que respeite a RFC interpretaria "falha de credencial do Watson" como "o servidor não consegue *armazenar* a representação" |
| **Correção** | o **código** `FALHA_DE_AUTENTICACAO_EXTERNA` é mantido (é útil e é o que o operador precisa distinguir); o **transporte** passa a **`502`** |
| **Por que `502` e não `401`/`403`** | `401`/`403` significam "**você** (o cliente) não está autenticado/autorizado". Uma credencial inválida **do backend** não pode ser confundida com isso: um cliente bem-comportado encerraria a sessão do usuário por um problema que não é dele |
| **Por que não `500`** | `500` sugere defeito não diagnosticado; este caso é **conhecido e acionável** ("revise `WATSON_API_KEY`"), e o código estável já o distingue |
| **Efeito no cliente** | nenhum. A Fase 5 (app Expo) fala com o backend Flask da Fase 5, em `/api/chat` — **rotas e porta diferentes** das da Fase 7. Nenhum consumidor depende de a Fase 7 emitir 507 |

Os cinco códigos de origem externa ficam assim:

| Código | HTTP | Justificativa |
|---|---|---|
| `NAO_CONFIGURADO` | `501` | **mantido**: "a funcionalidade não existe nesta implantação" é a leitura corrente de 501 e é o que a Fase 5 já usava |
| `FALHA_DE_AUTENTICACAO_EXTERNA` | `502` | **corrigido** (era 507) |
| `COTA_EXCEDIDA` | `429` | **mantido**: o 429 do provedor tem semântica idêntica ("excedeu a cota, tente mais tarde") |
| `TIMEOUT_EXTERNO` | `504` | **mantido**: `Gateway Timeout` é exatamente o caso |
| `ERRO_DE_SERVICO_EXTERNO` | `502` | **mantido**: `Bad Gateway` é exatamente o caso |

> 🔒 **Propriedade verificada por teste** (`test_contratos_erros.py`): nenhum código de
> origem externa pode usar `401`/`403`, e `507` não aparece em nenhum mapa da Fase 7.


### 3.3 Exemplo de resposta de erro

```json
{
  "id_execucao": "3f2b9c1e-8a4d-4c77-9e10-5b6a7c8d9e0f",
  "gerado_em": "2026-10-31T12:00:00Z",
  "status": "ERRO",
  "dados": null,
  "avisos": [],
  "limitacoes": [],
  "erros": [
    {
      "codigo": "PACIENTE_INVALIDO",
      "mensagem": "Campos obrigatorios ausentes: spo2_media, pa_sistolica.",
      "campo": null,
      "detalhe": "O modelo espera exatamente: idade_media, carga_sistema, ..."
    }
  ],
  "metadados": { "versao_api": "v1" }
}
```

---

## 4. Schemas

> Legenda de origem: **[E]** = existe no projeto anterior · **[N]** = novo (introduzido pela Fase 7)
> · **[P]** = parcial (existe com outra forma/semântica)

### 4.1 `Paciente` — cadastro + estado clínico avaliado

> ✅ **Nome definido** pela resposta **Q1**: `pico_risco` é **risco clínico individual** → a entidade
> é **`paciente`** (não mais a entidade neutra `SnapshotAssistencial`).
>
> **Separação adotada:** o **cadastro** guarda apenas a identidade; as **10 features** são o **estado
> clínico do paciente no momento da avaliação** e trafegam no corpo de `POST /avaliacoes`
> (ver [`MODELO_DADOS.md`](MODELO_DADOS.md) §3).

**Cadastro (`POST /pacientes`):**

| Campo | Tipo | Obrigatório | Origem | Observação |
|---|---|---|---|---|
| `id_paciente` | UUID | ✅ (gerado) | **[N]** | chave primária |
| `nome` | str (1–120) | ✅ | **[N]** | identificação do paciente |
| `ativo` | bool | ✅ (default `true`) | **[N]** | desativação sem exclusão |
| `criado_em` | datetime | ✅ (gerado) | **[N]** | UTC |
| `criado_por` | UUID | ✅ | **[N]** | usuário autenticado |

**Estado clínico (corpo de `POST /avaliacoes`) — as 10 features:**

| Campo | Tipo | Obrigatório | Origem | Significado (resposta Q1) | Aviso de faixa |
|---|---|---|---|---|---|
| `idade_media` | float ≥ 0 | ✅ | **[E]** | ⚠️ **idade do paciente** (nome fixado pelo contrato do modelo) | 18–90 |
| `carga_sistema` | float ≥ 0 | ✅ | **[E]** | carga da unidade durante o episódio (contexto) | 30,004–99,977 |
| `tempo_espera` | float ≥ 0 | ✅ | **[E]** | tempo de espera do paciente | 5,0–113,578 |
| `fc_media` | float ≥ 0 | ✅ | **[E]** | FC média do paciente na janela | 50–150 |
| `spo2_media` | float ≥ 0 | ✅ | **[E]** | SpO₂ média do paciente na janela | 83,431–100 |
| `pa_sistolica` | float ≥ 0 | ✅ | **[E]** | PA sistólica do paciente | 80–198,832 |
| `temperatura` | float ≥ 0 | ✅ | **[E]** | ⚠️ **temperatura CORPORAL** (resposta Q2) — ver achado A3 | 10–40 |
| `densidade_eventos` | float ≥ 0 | ✅ | **[E]** | densidade de eventos do paciente | 0–13 |
| `eventos_24h` | float ≥ 0 | ✅ | **[E]** | eventos do paciente em 24 h | 0–9 |
| `disponibilidade_recursos` | float ≥ 0 | ✅ | **[E]** | recursos disponíveis para o atendimento (contexto) | 20,035–99,989 |
| `origem_dos_dados` | enum: `manual` \| `iot` \| `importado` | ✅ | **[N]** | rastreabilidade (Decisão D4) | — |

> ⚠️ **`temperatura` é corporal (Q2).** Como o **DHT22 da Fase 3 mede temperatura ambiente**, ele
> **não** é fonte válida desta feature. Além disso, o gerador da Fase 6 usou uma distribuição de
> **ambiente** (média 24 °C) — ver **achado A3**: a feature é de **baixa confiança** e deve ser
> marcada como tal na apresentação.

**Validações obrigatórias** (espelham `predict.validar_paciente`):

| Regra | Comportamento |
|---|---|
| `bool` | ❌ rejeitado (não é número) |
| `str` | ❌ rejeitado (sem conversão silenciosa) |
| `NaN` / `inf` | ❌ rejeitado |
| Negativo | ❌ rejeitado |
| Fora da faixa | ⚠️ **aviso**, não erro |
| Campo extra | ❌ rejeitado (schema fechado) |

> ⚠️ **Não existe valor default** para nenhuma das 10 features. Campo ausente = `422 PACIENTE_INVALIDO`.

### 4.2 `DadosDeMonitoramento` — telemetria IoT

| Campo | Tipo | Obrigatório | Origem | Observação |
|---|---|---|---|---|
| `id_leitura` | UUID | ✅ (gerado) | **[N]** | |
| `id_dispositivo` | str (1–64) | ✅ | **[N]** | o firmware **não** envia identificador |
| `recebido_em` | datetime | ✅ (carimbado pelo backend) | **[N]** | o firmware **não** envia timestamp — **não atribuir ao dispositivo** |
| `temperatura` | float \| null | ⚠️ condicional | **[E]** | Fase 3 (DHT22 + payload REST) |
| `umidade` | float \| null | ❌ opcional | **[E]** | Fase 3 firmware (Parte 1) — **não publicada por MQTT** |
| `luminosidade` | float \| null | ❌ opcional | **[E]** | Fase 3 firmware (Parte 1) |
| `bpm` | int \| null | ⚠️ condicional | **[E]** | Fase 3 (REST + MQTT `hospital/bpm`) — **simulado por botão** |
| `movimento` | bool \| null | ❌ opcional | **[E]** | existe **apenas** no payload REST da Fase 3 |
| `origem_transporte` | enum: `mqtt` \| `rest` \| `simulado` | ✅ | **[N]** | |
| `payload_json` | dict | ❌ opcional | **[N]** | bruto, para auditoria |

**Regras:**
- Pelo menos **um** entre `temperatura` e `bpm` deve estar presente (senão `422`).
- `movimento`, `umidade` e `luminosidade` **não são features do modelo** — se enviados ao endpoint de
  avaliação, serão rejeitados como campos desconhecidos (**não** são mapeados implicitamente).
- `recebido_em` **não** é aceito na requisição (o backend carimba); `id_leitura` é gerado.
- `id_paciente` **não** faz parte deste contrato, embora a coluna exista no banco (vinculação
  opcional, `MODELO_DADOS.md` §4.5) — o DTO é fechado e não a expõe.

**Autenticação da ingestão** (`DECISOES_ARQUITETURAIS.md` §4.1: "chave de dispositivo a introduzir"):

| Forma | Como | Observação |
|---|---|---|
| **Chave de dispositivo** | cabeçalho `X-Device-Key` | comparada em **tempo constante** com `IOT_DEVICE_KEY`. Sem a variável configurada, o caminho é **recusado** (401) |
| **Usuário** | Bearer JWT com papel `OPERADOR` | `MEDICO` e `ADMIN` recebem `403` — ingestão não é ato clínico |

> O alerta das regras da Fase 3 (`FEBRE DETECTADA` / `TAQUICARDIA DETECTADA` / `AUSÊNCIA DE MOVIMENTO`)
> **não** é persistido: é derivado dos sinais e não há coluna para ele. Ele vai em `avisos` do envelope,
> e a trilha de auditoria registra o evento (apenas quando há alerta).

### 4.3 `ResultadoDeDiagnostico` — visão computacional (Fase 4)

| Campo | Tipo | Obrigatório | Origem | Observação |
|---|---|---|---|---|
| `classe` | enum: `Normal` \| `Pneumonia` | ✅ | **[P]** | na origem o campo chama-se **`class`** |
| `confianca` | float 0–100 | ✅ | **[P]** | na origem chama-se **`confidence`** (já em %) |
| `modelo_utilizado` | str | ✅ | **[N]** | a Fase 4 **não** informa; o backend sabe que é `mobilenet_pneumonia.keras` |
| `limiar_decisao` | float 0–1 | ✅ | **[N]** | 0.5 é literal no código da Fase 4 e **não** é exposto |
| `dimensoes_da_imagem` | [int, int] | ✅ | **[N]** | a Fase 4 redimensiona para `(128, 128)` |
| `hash_sha256` | str | ✅ | **[N]** | permite auditoria **sem armazenar o binário** |
| `aviso_de_uso` | str | ✅ | **[N]** | aviso obrigatório |

> ⚠️ **`{class, confidence}` NÃO é o `DiagnosticoDaPredicao` da Fase 6.** São contratos distintos
> (nomes, semântica e granularidade diferentes). **Não serão unificados.**

### 4.4 `ResultadoPreditivo` — **reutilização integral da Fase 6**

Os schemas abaixo **já existem** em `cardioia.schemas.risk_result` e serão usados **sem redefinição**:

| Schema | Campos | Origem |
|---|---|---|
| `DiagnosticoDaPredicao` | `probabilidade_risco` (0–1, cru), `pico_risco_previsto` (0\|1), `classificacao_risco` (`sem_pico_de_risco`\|`pico_de_risco`), `modelo_utilizado`, `classe_do_estimador`, `limiar_decisao`, `regra_de_decisao`, `features_utilizadas`, `origem_do_modelo`, `avisos` | ✅ **[E]** Fase 6 |
| `ProtocoloAplicavel` | `ordem`, `identificador`, `texto_oficial`, `acao`, `condicao_satisfeita`, `operador` (`<`\|`>`\|`==`), `limiar`, `valor_observado`, `origem_do_valor`, `usa_modelo` | ✅ **[E]** Fase 6 |
| `IndicadorDeterministico` | `nome`, `coluna`, `operador`, `limiar`, `valor_observado`, `satisfeito`, `origem` | ✅ **[E]** Fase 6 |
| `PassoDaExecucao` | `ordem`, `tipo` (handoff\|tool\|agente\|validacao\|erro), `agente`, `detalhe`, `sucesso` | ✅ **[E]** Fase 6 |

**Campos que NÃO podem entrar no contrato da Fase 6** (ele tem `extra="forbid"`) e por isso vão no
`metadados` do envelope:

| Campo | Onde fica | Origem |
|---|---|---|
| `id_paciente` | `metadados` | **[N]** |
| `id_usuario` | `metadados` | **[N]** |
| `id_monitoramento` | `metadados` | **[N]** |
| `origem_dos_dados` | `metadados` | **[N]** |

### 4.5 `MensagemDoAssistente` — conversa (Fase 5)

**Requisição:**

| Campo | Tipo | Obrigatório | Origem | Observação |
|---|---|---|---|---|
| `mensagem` | str (1–2000) | ✅ | **[P]** | na origem chama-se **`message`** |
| `id_conversa` | UUID \| null | ❌ | **[N]** | o backend gerencia; **não** expor `session_id` do Watson |

**Resposta (`dados`):**

| Campo | Tipo | Obrigatório | Origem | Observação |
|---|---|---|---|---|
| `id_conversa` | UUID | ✅ | **[N]** | identificador próprio do backend |
| `resposta` | str | ✅ | **[P]** | na origem chama-se **`reply`** |
| `criado_em` | datetime | ✅ | **[P]** | na origem `timestamp` |
| `papel` | enum: `assistant` | ✅ | **[N]** | para o histórico |
| `fontes` | list[str] | ✅ (sempre `[]`) | **[N]** | ⚠️ o Watson **não** devolve fontes — **nunca preencher com conteúdo inventado** |
| `avisos` | list[str] | ✅ | **[N]** | ex.: "não é diagnóstico" |

> ⚠️ O `session_id` do provedor (Watson) é **interno**: fica em `mensagens.session_id_do_provedor`
> no banco e **nunca** é devolvido ao cliente.

### 4.6 `AnaliseDeImagem` — requisição

| Item | Tipo | Obrigatório | Origem | Observação |
|---|---|---|---|---|
| `imagem` | arquivo (`multipart/form-data`) | ✅ | **[E]** | campo `image` na Fase 4 |
| `id_paciente` | UUID \| null | ❌ | **[N]** | vinculação opcional |
| `content_type` | str | ✅ | **[N]** | ✅ **endurecimento**: hoje a Fase 4 aceita qualquer arquivo que o Keras abra |
| limite de tamanho | — | — | **[N]** | ✅ **endurecimento**: limite a definir (ex.: 10 MB) → `413 LIMITE_EXCEDIDO` |

**Resposta (`dados`):** `ResultadoDeDiagnostico` (seção 4.3).

### 4.7 `Usuario` (para `/auth/me`)

| Campo | Tipo | Obrigatório | Origem |
|---|---|---|---|
| `id_usuario` | UUID | ✅ | **[N]** |
| `nome` | str (1–120) | ✅ | **[N]** |
| `email` | str (e-mail) | ✅ | **[N]** |
| `papel` | enum: `ADMIN` \| `MEDICO` \| `OPERADOR` | ✅ | **[N]** |
| `ativo` | bool | ✅ | **[N]** |
| `criado_em` | datetime | ✅ | **[N]** |
| `ultimo_acesso` | datetime \| null | ❌ | **[N]** |

> ⚠️ **`senha_hash` nunca é exposto** em nenhuma resposta.

---

## 5. Proveniência consolidada dos campos

| Campo do contrato | Já existe? | Onde exatamente | Fase 7 faz o quê |
|---|---|---|---|
| `id_execucao` | ✅ | Fase 6 `RespostaDaExecucao.id_execucao` (UUID4) | reutiliza **literalmente** |
| `gerado_em` | ✅ | Fase 6 `RespostaDaExecucao.gerado_em` | reutiliza |
| `status` | ✅ | Fase 6 `StatusDaExecucao` (4 valores) | reutiliza |
| `avisos` | ✅ | Fase 6 `RespostaDaExecucao.avisos` | reutiliza |
| `limitacoes` | ✅ | Fase 6 `LIMITACOES_PADRAO` | reutiliza |
| `diagnostico.*` | ✅ | Fase 6 `DiagnosticoDaPredicao` | reutiliza |
| `protocolos[]` | ✅ | Fase 6 `ProtocoloAplicavel` | reutiliza |
| `indicadores[]` | ✅ | Fase 6 `IndicadorDeterministico` | reutiliza |
| `passos[]` | ✅ | Fase 6 `PassoDaExecucao` | reutiliza |
| `handoffs_realizados[]` | ✅ | Fase 6 `RespostaDaExecucao` | reutiliza |
| `agente_final`, `versao_do_sdk`, `duracao_segundos` | ✅ | Fase 6 | reutiliza |
| 10 nomes/tipos/faixas de feature | ✅ | Fase 6 `COLUNAS_PREDITORAS` + `metadata.faixas_esperadas` | reutiliza |
| `temperatura`, `bpm`, `movimento` | ✅ | Fase 3 payload REST | reutiliza como **telemetria** (não como feature) |
| `umidade`, `luminosidade` | ✅ | Fase 3 firmware Parte 1 | reutiliza como telemetria |
| `class`, `confidence` | ✅ | Fase 4 `POST /predict` | **renomeia** para `classe`, `confianca` |
| `message`, `session_id`, `user_id` | ✅ | Fase 5 request | `message` → `mensagem`; `session_id` **deixa de ser exposto** |
| `reply`, `session_id`, `timestamp` | ✅ | Fase 5 response | `reply` → `resposta`; `timestamp` → `criado_em` |
| `email` de login (fictício) | ✅ | Fase 2 `AuthContext` | substituído por autenticação real |
| `dados` (generalização) | ❌ | — | **introduzir** |
| `metadados` | ❌ | — | **introduzir** |
| `ErroDaAPI` (`codigo`/`campo`/`detalhe`) | ❌ (só texto em `erros[]`) | — | **introduzir** |
| `id_paciente`, `nome`, `criado_por`, `origem_dos_dados` | ❌ | — | **introduzir** |
| `id_dispositivo`, `recebido_em`, `origem_transporte` | ❌ | — | **introduzir** |
| `modelo_utilizado`, `limiar_decisao`, `dimensoes_da_imagem`, `hash_sha256` (imagem) | ❌ | — | **introduzir** |
| `id_conversa`, `papel`, `fontes`, `avisos` (chat) | ❌ | — | **introduzir** |
| `Usuario`, `papel`, `ativo` | ❌ | — | **introduzir** |

**Balanço:** ~22 campos/grupos **reaproveitados** (a maioria vinda da Fase 6) e ~14 **introduzidos**.
Nenhum campo foi marcado como existente sem verificação no código.

---

## 6. Mapeador `Paciente` → entrada do modelo

> ⚠️ **Etapa obrigatória.** O contrato do modelo é **fechado** (`extra="forbid"`): passar o objeto de
> cadastro direto resultaria em `422` por campos desconhecidos. O mapeador extrai **apenas** as 10
> features, na ordem do metadata.

| Entrada (API) | → | Saída (modelo) | Transformação |
|---|---|---|---|
| `idade_media` | → | `idade_media` | identidade |
| `carga_sistema` | → | `carga_sistema` | identidade |
| `tempo_espera` | → | `tempo_espera` | identidade |
| `fc_media` | → | `fc_media` | identidade |
| `spo2_media` | → | `spo2_media` | identidade |
| `pa_sistolica` | → | `pa_sistolica` | identidade |
| `temperatura` | → | `temperatura` | identidade |
| `densidade_eventos` | → | `densidade_eventos` | identidade |
| `eventos_24h` | → | `eventos_24h` | identidade |
| `disponibilidade_recursos` | → | `disponibilidade_recursos` | identidade |
| `id_paciente`, `nome`, `criado_em`, `criado_por`, `origem_dos_dados` | → | *(descartados)* | ficam no banco/metadados, **não** vão ao modelo |

**Regra de implementação:** o mapeador **não** aplica conversão de tipo, arredondamento, default nem
"correção" de valor. Ele apenas **seleciona** os 10 campos. Qualquer ajuste é responsabilidade de
quem informou os dados.

### 6.1 Mapeador `DadosDeMonitoramento` → features (**especificação, não ativado**)

> Conforme a Decisão D4 (alternativa C), **este mapeador não será ativado** no MVP. Ele fica
> documentado para que a ativação futura seja uma mudança de configuração.
>
> ⚠️ **Atualizado pela resposta Q2:** `temperatura` é **corporal**, portanto o **DHT22** (ambiente)
> foi **removido** deste mapeamento. Restou **1 correspondência**.

| Feature do modelo | Fonte na telemetria | Corresponde? | Motivo |
|---|---|---|---|
| `fc_media` | `bpm` | ✅ **sim** (parcial) | mesma grandeza (batimentos por minuto); origem **simulada** |
| `temperatura` | ~~`temperatura` (DHT22)~~ | ❌ **NÃO** (removido por Q2) | o DHT22 mede **ambiente**; a feature é **corporal** |
| `idade_media` | — | ❌ | não existe na telemetria |
| `carga_sistema` | — | ❌ | métrica de contexto |
| `tempo_espera` | — | ❌ | métrica de contexto |
| `spo2_media` | — | ❌ | não há sensor de SpO₂ |
| `pa_sistolica` | — | ❌ | não há sensor de PA |
| `densidade_eventos` | — | ❌ | métrica derivada |
| `eventos_24h` | — | ❌ | métrica agregada (viável **após** haver histórico) |
| `disponibilidade_recursos` | — | ❌ | métrica de contexto |

**Balanço (pós-Q2): 1 correspondência (parcial e simulada) para 10 features — 9 lacunas explícitas.**

---

## 7. Incompatibilidades entre contratos (não presumidas)

| # | Incompatibilidade | Evidência | Consequência |
|---|---|---|---|
| **I1** | Schema de cadastro ≠ entrada do modelo | `validar_paciente(permitir_campos_extras=False)` | **mapeador explícito obrigatório** (seção 6) |
| **I2** | `DadosDeMonitoramento` ≠ features do modelo | 2 de 10 features disponíveis | gap documentado; **sem defaults** |
| **I3** | `{class, confidence}` (Fase 4) ≠ `DiagnosticoDaPredicao` (Fase 6) | nomes, semântica e granularidade diferentes | **dois schemas distintos**, nunca unificados |
| **I4** | `StatusDaExecucao` (4 valores) ≠ códigos HTTP da Fase 5 (501/502/504/507/429) | eixos diferentes (domínio × transporte) | **mapeamento explícito** (seção 3.2), não fusão — e o `507` herdado foi **corrigido para `502`** (§3.2.1) |
| **I5** | `movimento`/`umidade`/`luminosidade` não são features | Fase 3 envia; o modelo não aceita | rejeitados como campos desconhecidos |
| **I6** | Unidade de `temperatura` — ✅ **RESOLVIDA** | Resposta **Q2**: é **corporal** | ✅ **Resolvida**: o DHT22 (ambiente) foi **removido** do mapeamento; a feature passa a exigir medição corporal |
| **I7** | O firmware não envia timestamp nem identificador | `codigo_parte2.c` publica apenas valor | backend carimba `recebido_em` e exige `id_dispositivo` |
| **I8** | Fase 5 expõe o `session_id` do Watson ao cliente | `POST /api/chat` devolve `session_id` | Fase 7 **não expõe**: cria `id_conversa` próprio |
| **I9** | Fase 4 não devolve `modelo_utilizado` nem `limiar` | `app.py` retorna só `class`/`confidence` | Fase 7 **acrescenta** a partir do conhecimento do artefato (não inventa do modelo) |
| **I10** | **A distribuição de `temperatura` no gerador não é corporal** | `base_dados.py`: `normal(24, 5).clip(10, 40)` (média 24 °C) vs. corpo humano ~36–38 °C | Feature de **baixa confiança**; qualquer valor corporal cai na **cauda** da distribuição de treino. **Não corrigível** sem alterar a Fase 6 |
| **I11** | **8 das 10 features não são medições individuais** | 5 são de contexto/operação; 3 têm nome de média | Interpretação individual documentada; o **nome** não pode mudar (contrato fechado) |

---

## 8. Endpoints do MVP

| Método | Rota | Papel mínimo | Corpo/Parâmetros | `dados` na resposta |
|---|---|---|---|---|
| `GET` | `/api/v1/health` | — | — | estado do serviço + presença do modelo |
| `POST` | `/api/v1/auth/login` | — | `{email, senha}` | `{access_token, refresh_token, expira_em}` |
| `POST` | `/api/v1/auth/refresh` | — | `{refresh_token}` | `{access_token, refresh_token, expira_em}` — **novo par** (há rotação) |
| `POST` | `/api/v1/auth/logout` | autenticado | — | `{encerrado, sessoes_revogadas}` |
| `GET` | `/api/v1/auth/me` | autenticado | — | `UsuarioPublico` (**sem** `senha_hash`) |
| `GET` | `/api/v1/pacientes` | `MEDICO` \| `ADMIN` | paginação | lista de `Paciente` |
| `POST` | `/api/v1/pacientes` | `MEDICO` | `{nome}` | `Paciente` |
| `GET` | `/api/v1/pacientes/{id}` | `MEDICO` \| `ADMIN` | — | `Paciente` |
| `POST` | `/api/v1/avaliacoes` | `MEDICO` | `{id_paciente, features (10), origem_dos_dados, modo}` | `RespostaDaExecucao` (**Fase 6 integral**) |
| `GET` | `/api/v1/avaliacoes` | `MEDICO` \| `ADMIN` | paginação, filtros | lista resumida |
| `GET` | `/api/v1/avaliacoes/{id_execucao}` | `MEDICO` \| `ADMIN` | — | `RespostaDaExecucao` do histórico |
| `POST` | `/api/v1/iot/leituras` | `OPERADOR` \| chave de dispositivo | `DadosDeMonitoramento` | `DadosDeMonitoramento` persistido |
| `GET` | `/api/v1/iot/leituras` | `OPERADOR` \| `MEDICO` | paginação, `id_dispositivo` | lista de leituras |
| `POST` | `/api/v1/imagens` | `MEDICO` | `multipart/form-data` | `ResultadoDeDiagnostico` |
| `POST` | `/api/v1/chat` | `OPERADOR` \| `MEDICO` | `MensagemDoAssistente` | `MensagemDoAssistente` |
| `GET` | `/api/v1/conversas/{id}` | `OPERADOR` \| `MEDICO` | — | histórico de mensagens |

### 8.1 Notas por endpoint

| Endpoint | Nota obrigatória |
|---|---|
| `POST /auth/login` | **Mensagem sempre genérica** ("E-mail ou senha invalidos."): a resposta não revela se a conta existe, e o tempo de resposta é igualado com um bcrypt de referência |
| `POST /auth/login` | **Limitador de tentativas**: 5 falhas em 5 min por `email\|ip` → `429 TAXA_EXCEDIDA`. ⚠️ Contador **em memória** (por processo): reinicia com o servidor e não é compartilhado entre workers |
| `POST /auth/login` | Conta **inativa** → `403 NAO_AUTORIZADO` (é autorização, não credencial inválida) |
| `POST /auth/login` | Grava `eventos_de_auditoria` (`acao='login'`, `detalhe.resultado` ∈ `sucesso`/`senha_incorreta`/`email_desconhecido`/`inativo`) — **sem** senha e **sem** token |
| `POST /auth/refresh` | **Rotação**: o refresh token apresentado é revogado e um **novo par** é devolvido. Reutilizar o token antigo → `401 NAO_AUTENTICADO` |
| `POST /auth/refresh` | O banco guarda **apenas o SHA-256** do refresh token (`sessoes.token_hash`); o valor em claro só existe na resposta |
| `POST /auth/logout` | Revoga **todas** as sessões vigentes do usuário (comportamento documentado; não é logout "só deste dispositivo") |
| `GET /auth/me` | Nunca devolve `senha_hash` nem qualquer hash |
| `POST /pacientes` | Responde **201**. Guarda apenas identidade (Q1); nome só de espaços é recusado (`422`) |
| `POST /pacientes` | O nome **não** é chave única — homônimos existem; a chave é `id_paciente` |
| `GET /pacientes` | Lista **apenas ativos** por padrão (`apenas_ativos=false` mostra todos). `limite` ≤ 200 |
| `POST /avaliacoes` | ⚠️ **HTTP 200 mesmo com `status=ERRO` no envelope**: o HTTP diz "rodou e foi registrada"; o `status` diz o resultado. O contrato integral (com a trilha de `passos`) fica em `dados` |
| `POST /avaliacoes` | Paciente **inativo** → `409 CONFLITO` (o estado atual impede a operação; não é 404) |
| `POST /avaliacoes` | `modo=real` sem `OPENAI_API_KEY` → `501 NAO_CONFIGURADO`, antes de executar |
| `POST /avaliacoes` | O `id_execucao` do envelope **é** o da Fase 6 (N2) e o mesmo que fica no banco |
| `POST /iot/leituras` | Responde **201**. Autenticação: `X-Device-Key` **ou** Bearer JWT com papel `OPERADOR` (não `MEDICO`/`ADMIN`) |
| `POST /iot/leituras` | Sem `IOT_DEVICE_KEY` no servidor, o caminho da chave é **recusado** (401) em vez de aceitar qualquer valor |
| `POST /iot/leituras` | Alerta das regras da Fase 3 → `status=CONCLUIDO_COM_RESSALVAS` e o alerta em `avisos`. **`dados` continua sendo só a leitura persistida** |
| `POST /iot/leituras` | Pelo menos um sinal vital (`temperatura` ou `bpm`) → senão `422`. O `recebido_em` é **carimbado pelo backend** (campo extra é recusado) |
| `POST /iot/leituras` | `X-Device-Key` inválida → `401`; chave válida dispensa Bearer |
| `GET /iot/leituras` | Exige **usuário** (`OPERADOR` \| `MEDICO`) — a chave de dispositivo só serve para ingerir |
| `GET /iot/leituras` | `dados` é uma **lista simples**; `len(dados) < limite` significa que não há próxima página |
| `POST /imagens` | Responde **201**. Exige `MEDICO` (interpretar imagem é ato clínico; `ADMIN`/`OPERADOR` → `403`) |
| `POST /imagens` | `content_type` validado (`image/jpeg` \| `image/png`) → senão `422`; a Fase 4 aceita "qualquer arquivo que o Keras abra" |
| `POST /imagens` | Teto de upload (`LIMITE_DE_UPLOAD_MB`, padrão 10) → `413 LIMITE_EXCEDIDO` |
| `POST /imagens` | Serviço da Fase 4 **inalcançável** → `502 ERRO_DE_SERVICO_DE_VISAO`; **sem resposta no prazo** → `504 TIMEOUT_EXTERNO` |
| `POST /imagens` | Resposta do serviço fora do contrato (ex.: `class` desconhecida) → `502`, **nunca** um diagnóstico silencioso |
| `POST /imagens` | `modelo_utilizado`, `limiar_decisao` e `dimensoes_da_imagem` são **acrescentados** pelo backend (I9): a Fase 4 não os informa |
| `POST /imagens` | Paciente **inativo** → `409 CONFLITO`; `id_paciente` é opcional |
| `POST /chat` | Sem Watson configurado → `501 NAO_CONFIGURADO` (o backend lê **só** do ambiente; **não** usa os defaults do `IBM_API.py`) |
| `POST /chat` | Sem `id_conversa` abre conversa nova; com `id_conversa` continua a existente (o backend recupera a sessão do provedor sozinho) |
| `POST /chat` | **O cliente não envia `session_id`** (I8): o campo é recusado. O identificador exposto é o `id_conversa` |
| `POST /chat` | `fontes` é **sempre `[]`** (N6): o Watson não devolve fontes |
| `POST /chat` | Erros do provedor: `502` (401/403 **do Watson**) · `429` (429) · `504` (408/504) · `502` (demais) — **nunca `401`/`403`**, que são do usuário (§3.2.1) |
| `POST /chat` | Um turno que falha **fica no histórico**: `conteudo` = o texto amigável que o usuário viu (o detalhe técnico não é exposto) |
| `POST /chat` | Exige `OPERADOR` \| `MEDICO` — `ADMIN` recebe `403` |
| `GET /conversas/{id}` | `dados` é a **lista de mensagens**; o contexto da conversa (canal, início, fim) vai em `metadados` |
| `GET /conversas/{id}` | Não expõe o `session_id` do provedor nem o detalhe técnico de falhas |
| `GET /avaliacoes` | `dados` é uma **lista simples**; `len(dados) < limite` significa que não há próxima página |
| `GET /avaliacoes/{id_execucao}` | Devolve o `resposta_json` persistido — **não** reexecuta o modelo. O `status` do envelope reflete a avaliação original (o HTTP 200 indica que a consulta ao histórico funcionou) |
| Rotas autenticadas | Token ausente/inválido/expirado → `401 NAO_AUTENTICADO` **com** cabeçalho `WWW-Authenticate: Bearer` |
| Rotas autenticadas | Papel insuficiente → `403 NAO_AUTORIZADO`. Sem autenticação, a resposta é **401**, não 403 |
| Rotas autenticadas | **O banco é a fonte da verdade do papel**: se o papel do token divergir do atual, a requisição é recusada com `401` (exige novo login) |
| `POST /avaliacoes` | ⚠️ **As 10 features são obrigatórias.** Se `id_paciente` for informado sem as features, o backend **não** preenche nada: responde `422 PACIENTE_INVALIDO` |
| `POST /avaliacoes` | ⚠️ `temperatura` é **corporal** (Q2) e é uma feature de **baixa confiança** (achado A3/I10) — a resposta deve sinalizar isso |
| `POST /avaliacoes` | `origem_dos_dados` é obrigatório: `manual` (padrão esperado no MVP), `iot` ou `importado` |
| `POST /avaliacoes` | O `modo` aceita `simulado` (padrão) e `real`. Em `real`, exige `OPENAI_API_KEY` → senão `501 NAO_CONFIGURADO` |
| `GET /avaliacoes/{id_execucao}` | Retorna o `resposta_json` **persistido** — decisão auditável, sem reexecutar o modelo |
| `POST /iot/leituras` | A telemetria **não** alimenta o modelo (Decisão D4) |
| `POST /imagens` | Encaminha para o serviço da Fase 4 (`:5001`). Falha do serviço → `502 ERRO_DE_SERVICO_DE_VISAO` |
| `POST /chat` | Requer Watson configurado → senão `501 NAO_CONFIGURADO` (comportamento herdado da Fase 5) |
| Todos | `avisos` e `limitacoes` **nunca** vazios em respostas de decisão automatizada |

---

## 9. Notas de implementação

| # | Nota | Motivo |
|---|---|---|
| N1 | Reutilizar **literalmente** `cardioia.schemas.risk_result` — não criar schemas paralelos | Evita divergência entre contrato e implementação |
| N2 | O `id_execucao` do envelope **é** o da Fase 6 | Correlação API ↔ banco ↔ trilha |
| N3 | Mapeador de features como **função pura e testável**, sem defaults | R3 / I1 |
| N4 | Conversão de `class`→`classe` e `reply`→`resposta` na **borda** (adapter), não no domínio | Preserva o domínio com nomes consistentes |
| N5 | Erros das exceções da Fase 6 **propagados com a mensagem original** em `detalhe` | Rastreabilidade e depuração |
| N6 | `fontes` do chat sempre `[]` | O Watson não devolve fontes — preencher seria inventar |
| N7 | Nenhum endpoint devolve `session_id` de provedor, `senha_hash` ou chave de API | R6 / segurança |
| N8 | `limitacoes` usa `LIMITACOES_PADRAO` da Fase 6 por padrão | Consistência dos avisos clínicos |
| N9 | `temperatura` entra em `avisos` como **feature de baixa confiança** (achado A3) | Honestidade sobre a distribuição de treino |
| N10 | A feature `idade_media` carrega a **idade do paciente**, apesar do nome (contrato fechado) | Documentar no Swagger/descrição do campo |
| N11 | As 3 features de **contexto** (`carga_sistema`, `disponibilidade_recursos`, `densidade_eventos`) ficam registradas como contexto do episódio | Preserva a leitura "clínico individual" sem alterar o contrato |

---

*Especificação de contratos da Fase 7. Nenhum valor de credencial é reproduzido neste documento.
Nenhuma linha de código foi escrita nesta etapa.*