# CardioIA — Backend central (Fase 7)

Backend **FastAPI** que integra os módulos das Fases 3 (IoT), 4 (visão computacional),
5 (assistente) e 6 (pipeline multiagentes + modelo de risco) sob um **contrato único**.

> 📄 Documentação de referência (na pasta acima):
> [`DECISOES_ARQUITETURAIS.md`](../DECISOES_ARQUITETURAIS.md) ·
> [`CONTRATOS_API.md`](../CONTRATOS_API.md) ·
> [`MODELO_DADOS.md`](../MODELO_DADOS.md) ·
> [`PLANO_SEGURANCA.md`](../PLANO_SEGURANCA.md)

> ⚠️ **Aviso:** os dados do projeto são **sintéticos** e **não há validação clínica**.
> Nenhum resultado constitui diagnóstico, prescrição ou recomendação médica.

---

## Estado atual — Etapa C

| Item | Entrega | Status |
|---|---|---|
| **1** | Esqueleto FastAPI + envelope `RespostaAPI[T]` + enum de erros + `GET /api/v1/health` | ✅ **Concluído** |
| **2** | Persistência (SQLAlchemy 2.0 + SQLite): 12 tabelas de domínio + controle de versão | ✅ **Concluído** |
| **3** | Autenticação (PyJWT + bcrypt + RBAC de 3 papéis) | ✅ **Concluído** |
| **4** | Integração da Fase 6 (import direto + cache + mapeador) + rotas clínicas | ✅ **Concluído** |
| **5** | Módulo `regras_iot` + ingestão de telemetria | ✅ **Concluído** |
| **6** | Adapter da Fase 4 (visão computacional) | ✅ **Concluído** |
| **7** | Assistente conversacional (Fase 5) | ✅ **Concluído** |

**A Fase 6 já é importada** pela camada `app/integracao/` (item 4) — mas **somente sob
demanda**: importar `app.main` **não** carrega `cardioia`, `pandas` nem `scikit-learn`. O
`/health` continua barato porque usa `find_spec` (localiza sem executar).

**Estado do cadastro de usuários:** as rotas de `/auth` e o fluxo clínico estão completos.
Ainda **não** existe endpoint de criação de usuários — para testar manualmente, semeie um
usuário no banco:

```powershell
cd backend
python -m app.dados.esquema            # garante o esquema

python -c "
from app.config import obter_configuracoes
from app.dados.base import criar_engine, criar_fabrica_de_sessoes
from app.dados.enums import PapelDoUsuario
from app.dados.repositorios.identidade import UsuarioRepositorio
from app.seguranca.senhas import gerar_hash

engine = criar_engine(obter_configuracoes().url_do_banco)
with criar_fabrica_de_sessoes(engine)() as sessao:
    UsuarioRepositorio(sessao).criar(
        nome='Dra. Exemplo',
        email='medico@hospital.local',
        senha_hash=gerar_hash('troque-esta-senha'),
        papel=PapelDoUsuario.MEDICO,
    )
"
```

> Um endpoint `POST /api/v1/usuarios` (apenas `ADMIN`) fica para um incremento seguinte —
> até lá, o cadastro é feito direto no banco, como nos testes
> (`tests/conftest.py::semear_usuario`).

---

## Estrutura

```text
backend/
├── .env.example                 # nomes das variáveis (SEM valores)
├── .gitignore                   # exclui .env, banco local, caches
├── requirements.txt             # versões fixadas (nenhuma dependência nova)
├── pytest.ini
├── app/
│   ├── __init__.py              # __versao__
│   ├── config.py                # configuração + falha rápida (JWT_SECRET)
│   ├── main.py                  # aplicação + handlers de erro + CORS + lifespan
│   ├── regras_iot.py            # ⬅ item 5: regras de risco da Fase 3 (fonte: server.py)
│   ├── contratos/
│   │   ├── envelope.py          # RespostaAPI[T], StatusDaResposta
│   │   ├── erros.py             # CodigoDeErro, ErroDaAPI, mapeamento HTTP
│   │   ├── paginacao.py         # limite padrão/máximo das listagens
│   │   ├── autenticacao.py      # DTOs de login/refresh/logout/usuário
│   │   ├── assistencial.py      # DTOs de paciente e avaliação
│   │   ├── telemetria.py        # ⬅ item 5: DTOs de telemetria
│   │   ├── visao.py             # ⬅ item 6: DTOs de diagnóstico por imagem
│   │   └── assistente.py        # ⬅ item 7: DTOs do assistente conversacional
│   ├── dados/                   # ⬅ item 2
│   │   ├── base.py              # DatetimeUTC, engine + PRAGMAs, sessão, dependência
│   │   ├── enums.py             # enums persistidos (TEXT + CHECK)
│   │   ├── modelos.py           # 12 tabelas de domínio + versoes_do_esquema
│   │   ├── esquema.py           # create_all + versão do esquema (CLI)
│   │   └── repositorios/        # um repositório por agregado (6 módulos)
│   ├── seguranca/               # ⬅ item 3
│   │   ├── senhas.py            # bcrypt (hash, verificação, custo, tempo constante)
│   │   ├── tokens.py            # access JWT (PyJWT) + refresh opaco (SHA-256)
│   │   ├── limite_de_tentativas.py  # limitador de login (em memória)
│   │   └── dependencias.py      # usuario_atual + exigir_papeis (RBAC)
│   ├── integracao/              # ⬅ itens 4, 6 e 7 (camada de integração)
│   │   ├── fase_6.py            # sys.path.append + import tardio + disponibilidade
│   │   ├── traducao.py          # exceções da Fase 6 → CodigoDeErro
│   │   ├── modelo.py            # CacheDoModelo (o .pkl é lido uma única vez)
│   │   ├── mapeador.py          # features: contrato fechado, sem defaults
│   │   ├── fase_4.py            # ⬅ item 6: adapter HTTP do serviço de visão
│   │   └── fase_5.py            # ⬅ item 7: cliente do Watson (sem importar IBM_API)
│   └── rotas/
│       ├── apoio.py             # helpers: metadados, IP, papéis (RBAC) e auditoria
│       ├── saude.py             # GET /api/v1/health
│       ├── auth.py              # login · refresh · logout · me
│       ├── pacientes.py         # ⬅ item 4: cadastro e consulta de pacientes
│       ├── avaliacoes.py        # ⬅ item 4: avaliação de risco (pipeline da Fase 6)
│       ├── iot.py               # ⬅ item 5: ingestão e histórico de telemetria
│       ├── imagens.py           # ⬅ item 6: diagnóstico por imagem (Fase 4)
│       └── assistente.py        # ⬅ item 7: chat e histórico de conversas (Fase 5)
└── tests/                       # 586 testes
    ├── conftest.py
    ├── test_config.py
    ├── test_contratos_envelope.py
    ├── test_contratos_erros.py
    ├── test_rota_saude.py
    ├── test_dados_tipos.py
    ├── test_dados_esquema.py
    ├── test_dados_modelos.py
    ├── test_dados_repositorios.py
    ├── test_seguranca_senhas.py
    ├── test_seguranca_tokens.py
    ├── test_seguranca_limite.py
    ├── test_seguranca_rbac.py
    ├── test_rota_auth.py
    ├── test_rota_pacientes.py
    ├── test_rota_avaliacoes.py
    ├── test_rota_iot.py
    ├── test_regras_iot.py
    ├── test_rota_imagens.py
    ├── test_integracao_fase_4.py
    ├── test_rota_assistente.py
    ├── test_integracao_fase_5.py
    ├── test_integracao_fase_6.py
    ├── test_integracao_modelo.py
    ├── test_integracao_mapeador.py
    ├── test_integracao_traducao.py
    └── test_integracao_pipeline.py
```

---

## Como executar

### 1. Configurar o segredo (obrigatório)

```powershell
cd backend
Copy-Item .env.example .env
# gere um valor e cole em JWT_SECRET:
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> ⚠️ **Sem `JWT_SECRET` válido o serviço NÃO sobe** — falha rápida por decisão de
> segurança (`PLANO_SEGURANCA.md`). O segredo precisa de **≥ 32 caracteres** (HS256 = 256 bits).
> O arquivo `.env` está no `.gitignore`: **nunca** versione segredos.

### 2. Subir o servidor

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

| Endereço | Descrição |
|---|---|
| `http://127.0.0.1:8000/api/v1/health` | estado do serviço |
| `http://127.0.0.1:8000/docs` | Swagger UI |
| `http://127.0.0.1:8000/openapi.json` | especificação OpenAPI |

### 3. Testar

```powershell
cd backend
python -m pytest
```

---

## Banco de dados (item 2)

**Decisão aprovada:** SQLite via SQLAlchemy 2.0, encapsulado por **repositórios** — trocar
para PostgreSQL é mudar `DATABASE_URL` (`MODELO_DADOS.md` §7).

### Criar / validar o esquema

```powershell
cd backend
python -m app.dados.esquema              # cria o que faltar (idempotente)
python -m app.dados.esquema --verificar  # falha se a versão divergir
python -m app.dados.esquema --recriar    # ⚠️ APAGA e recria (desenvolvimento)
```

O servidor **também** prepara o banco no `startup` (lifespan). Importar `app.main` **não**
cria arquivo algum — o efeito em disco só ocorre quando o servidor sobe.

### Tabelas

| Domínio | Tabelas |
|---|---|
| Identidade | `usuarios`, `sessoes` |
| Assistencial | `pacientes`, `avaliacoes_de_risco`, `protocolos_aplicados`, `indicadores_deterministicos`, `passos_da_execucao` |
| Telemetria | `monitoramentos` |
| Visão | `analises_de_imagem` |
| Conversa | `conversas`, `mensagens` |
| Auditoria | `eventos_de_auditoria` |
| **Controle técnico** | `versoes_do_esquema` |

> As **10 features** ficam em `avaliacoes_de_risco` (estado clínico **datado**), **não** no
> cadastro do paciente — consequência da resposta Q1 (risco clínico individual).

### Controle de versão do esquema

Como **`alembic` não está instalado**, a versão aplicada fica registrada na tabela
`versoes_do_esquema` e o histórico vive em código (`app/dados/esquema.py::HISTORICO`). Um
banco em versão diferente da esperada faz o servidor **não subir** (`EsquemaIncompativelError`).

### Garantias implementadas

| Garantia | Como |
|---|---|
| FKs realmente aplicadas | `PRAGMA foreign_keys=ON` em toda conexão (sem isso o SQLite as ignora) |
| Leitura concorrente | `PRAGMA journal_mode=WAL` |
| Datas sempre UTC | tipo `DatetimeUTC` (rejeita valor naive na escrita) |
| Features sem default | `NOT NULL` sem `DEFAULT` + `CHECK (coluna >= 0)` |
| Agregado atômico | avaliação + filhas em **uma transação** |
| Erro de constraint tipado | `CONFLITO` (409) para UNIQUE/FK/CHECK; `CONTRATO_VIOLADO` (422) para valor recusado |
| Imagem não persistida | apenas `hash_sha256` + metadados |

---

## Autenticação (item 3)

**Decisão aprovada:** **PyJWT** (HS256) + **bcrypt** — as duas já instaladas.
`python-jose` e `passlib` **não** existem neste ambiente e não foram adicionadas.

| Peça | Escolha | Motivo |
|---|---|---|
| Access token | **JWT** de vida curta (`ACCESS_TOKEN_MINUTOS`, padrão 30) | Validação *stateless* — sem consulta ao banco |
| Refresh token | **valor opaco aleatório** (48 bytes) | `MODELO_DADOS.md` §6.1; no banco vai **apenas o SHA-256** |
| Hash do refresh | **SHA-256** (não bcrypt) | O token tem ~384 bits de entropia: não há o que forçar por dicionário |
| Senha | **bcrypt**, custo 12 | `passlib` ausente; bcrypt é a referência para senhas |
| RBAC | `ADMIN` · `MEDICO` · `OPERADOR` | `MODELO_DADOS.md` §6.3 |

### Rotas

| Método | Rota | Autenticação | `dados` |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | — | `{access_token, refresh_token, expira_em}` |
| `POST` | `/api/v1/auth/refresh` | refresh token | `{access_token, refresh_token, expira_em}` (**novo par**) |
| `POST` | `/api/v1/auth/logout` | access token | `{encerrado, sessoes_revogadas}` |
| `GET` | `/api/v1/auth/me` | access token | usuário público (**sem** `senha_hash`) |

### Exemplo

```powershell
$corpo = @{ email = "medico@hospital.local"; senha = "<senha>" } | ConvertTo-Json
$resposta = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/auth/login" `
    -ContentType "application/json" -Body $corpo
$token = $resposta.dados.access_token

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/auth/me" `
    -Headers @{ Authorization = "Bearer $token" }
```

### Proteger uma rota nova

```python
from app.seguranca.dependencias import UsuarioAutenticado, exigir_papeis
from app.dados.enums import PapelDoUsuario

@router.get("/pacientes")
def listar(usuario: UsuarioAutenticado):        # qualquer papel autenticado
    ...

@router.post("/pacientes")
def criar(usuario: Usuario = Depends(exigir_papeis(PapelDoUsuario.MEDICO))):
    ...
```

### Garantias implementadas

| Garantia | Como |
|---|---|
| Não revelar se a conta existe | mensagem **única** para e-mail inexistente e senha errada |
| Não vazar existência por tempo | bcrypt de referência no caminho de e-mail inexistente |
| Força bruta limitada | 5 falhas / 5 min por `email\|ip` → `429 TAXA_EXCEDIDA` |
| Senha nunca truncada em silêncio | senha acima de 72 bytes (limite do bcrypt) é **recusada**, não cortada |
| Token de acesso ≠ refresh | claim `tipo` verificada; tipos não são intercambiáveis |
| Assinatura não contornável | `algorithms=["HS256"]` fixo (o ataque `alg: none` é rejeitado) |
| Claims obrigatórias | `exp`, `iat`, `sub`, `jti`, `papel`, `tipo` — exigidas na leitura |
| `iss` verificado | token de outro serviço é recusado |
| Troca de senha/papel invalida tokens antigos | o **banco** é a fonte da verdade do papel; divergência → `401` |
| Sessão revogável | rotação no refresh; logout revoga todas as sessões |
| Trilha de auditoria | `login` / `refresh` / `logout` em `eventos_de_auditoria` — sem senha, sem token |
| 401 com o cabeçalho correto | `WWW-Authenticate: Bearer` |

> ⚠️ **Limitações declaradas:**
> 1. o limitador de tentativas vive **em memória** (por processo): reinicia com o servidor
>    e não é compartilhado entre workers — para produção, use Redis ou limitador na borda;
> 2. o `logout` revoga **todas** as sessões do usuário (não apenas a do dispositivo);
> 3. o access token é *stateless*: após o logout ele continua assinado até expirar
>    (mitigado pela vida curta); as **renovações** param imediatamente.

---

## Integração com a Fase 6 (item 4)

**Decisão aprovada (alternativa A):** **import direto** do pacote `cardioia` dentro do
FastAPI. Zero duplicação de lógica — as funções já cobertas por 290 testes da Fase 6 são
chamadas em processo, e as **exceções tipadas chegam intactas**.

### Mitigações obrigatórias — e como estão implementadas

| # | Mitigação | Onde |
|---|---|---|
| **M1** | Import **tardio**: se o SDK `agents` falhar, o backend **sobe** e responde `503 MODELO_INDISPONIVEL` | `integracao/fase_6.py::importar` |
| **M2** | `sys.path.append` (nunca `insert`) — `src/agents/` não pode sombrear o pacote `agents` do SDK | `integracao/fase_6.py::_garantir_caminho` |
| **M3** | Cache do artefato: o `.pkl` de 4,7 MB é lido **uma vez** | `integracao/modelo.py::CacheDoModelo` |
| **M4** | Modo `simulado` por padrão; `real` exige `OPENAI_API_KEY` | `POST /avaliacoes` (item 4, bloco 2) |
| **M5** | `raiz` e `pasta_modelos` resolvidos a partir da configuração | `integracao/fase_6.py` |

### Custos medidos neste ambiente

| Operação | Tempo |
|---|---|
| `disponibilidade()` (usada pelo `/health`) | **0,003 s** — usa `find_spec`, não importa nada |
| `GET /api/v1/health` (servidor no ar) | **0,006 – 0,047 s** |
| Import do pipeline (`agents` + pandas + sklearn) | **~5,6 s** — **uma vez por processo** |
| Carga do artefato (`.pkl` de 4,7 MB) | **~0,3 s** — uma vez, depois cacheado |
| Avaliação completa (modo simulado, cache quente) | **~0,17 s** |
| **Boot do servidor** com `AQUECER_MODELO_NO_STARTUP=true` | **~9,6 s** |
| **Boot do servidor** com `AQUECER_MODELO_NO_STARTUP=false` | **~2,7 s** |

Por isso `AQUECER_MODELO_NO_STARTUP=true` por padrão: o servidor paga o import uma vez no
boot em vez de na **primeira requisição do usuário** (que passaria de 0,17 s para ~6 s). O
aquecimento roda em *thread* (`asyncio.to_thread`) para não bloquear o event loop, e é
**best-effort** — se falhar, o servidor sobe normalmente (M1) e o erro aparece na
requisição que precisar do modelo. **Em teste a flag fica desligada**, senão cada
aplicação de teste pagaria o import.

### Mapeador: contrato fechado, sem defaults

As 10 features são obrigatórias e **nenhum valor é preenchido por padrão** (Decisão D4).
Ausente, desconhecido, `bool`, `NaN`/`inf` ou negativo → `422 PACIENTE_INVALIDO`.

Duas verificações de *drift* protegem contra divergência silenciosa:
`verificar_aderencia_ao_contrato` (o modelo carregado usa exatamente as 10 colunas) e a
ordem de features. Se a Fase 6 for retreinada com outra lista, o backend **falha alto** em
vez de reordenar errado e devolver um número plausível porém sem sentido.

### Tradução de erros

| Exceção da Fase 6 | Código | HTTP |
|---|---|---|
| `PacienteInvalidoError` | `PACIENTE_INVALIDO` | 422 |
| `DadosDoPacienteInvalidosError` | `DADOS_DO_PACIENTE_INVALIDOS` | 422 |
| `BaseDeConhecimentoInvalidaError` | `BASE_DE_PROTOCOLOS_INVALIDA` | 500 |
| `ModeloNaoEncontradoError` | `MODELO_INDISPONIVEL` | 503 |
| `ModeloIncompativelError` | `MODELO_INCOMPATIVEL` | 500 |
| `ErroDePrevisao` | `FALHA_DE_PREVISAO` | 500 |
| `ValidationError` (contrato da Fase 6) | `CONTRATO_VIOLADO` | 422 |
| `ImportError` / desconhecida | `MODELO_INDISPONIVEL` / `ERRO_INTERNO` | 503 / 500 |

A **mensagem original** vai para `detalhe` (N5) — sem isso, "modelo indisponível"
esconderia a causa real (ex.: pickle treinado em outra versão do scikit-learn).

> ⚠️ **Achado do ambiente:** neste workspace o pacote `cardioia` **também** está acessível
> por `PYTHONPATH` (aponta para `Fase_6/cardioia_Fase6/src`). Por isso `importar()` **não**
> aborta quando a pasta configurada não existe — quem decide é o import. Abortar pela
> pasta recusaria ambientes que funcionam.

> ℹ️ **`/health` informa o estado da integração** no campo `integracao_da_fase_6`
> (`codigo_presente`, `importavel`, `modulos_encontrados`, `faltando`) **sem importar** o
> pacote — a resposta continua em milissegundos.

---

## Fluxo clínico (item 4) — pacientes e avaliações

| Método | Rota | Papel mínimo | `dados` |
|---|---|---|---|
| `POST` | `/api/v1/pacientes` | `MEDICO` | `PacientePublico` (**201**) |
| `GET` | `/api/v1/pacientes` | `MEDICO` \| `ADMIN` | lista paginada |
| `GET` | `/api/v1/pacientes/{id_paciente}` | `MEDICO` \| `ADMIN` | `PacientePublico` |
| `POST` | `/api/v1/avaliacoes` | `MEDICO` | `RespostaDaExecucao` (**Fase 6 integral**) |
| `GET` | `/api/v1/avaliacoes` | `MEDICO` \| `ADMIN` | lista resumida |
| `GET` | `/api/v1/avaliacoes/{id_execucao}` | `MEDICO` \| `ADMIN` | contrato persistido |

### Exemplo completo

```powershell
$base = "http://127.0.0.1:8000/api/v1"
$h = @{ Authorization = "Bearer $token" }

# 1. cadastra o paciente (apenas identidade — Q1)
$paciente = Invoke-RestMethod -Method Post -Uri "$base/pacientes" -Headers $h `
    -ContentType "application/json" -Body '{"nome": "Maria Souza"}'

# 2. avalia o risco (as 10 features são obrigatórias)
$corpo = @{
    id_paciente        = $paciente.dados.id_paciente
    origem_dos_dados   = "manual"
    modo               = "simulado"
    features           = @{
        idade_media = 62; carga_sistema = 92; tempo_espera = 75; fc_media = 118
        spo2_media = 89; pa_sistolica = 100; temperatura = 37.5
        densidade_eventos = 7; eventos_24h = 5; disponibilidade_recursos = 25
    }
} | ConvertTo-Json -Depth 4

$avaliacao = Invoke-RestMethod -Method Post -Uri "$base/avaliacoes" -Headers $h `
    -ContentType "application/json" -Body $corpo

$avaliacao.status                        # CONCLUIDO
$avaliacao.dados.diagnostico.probabilidade_risco   # 0.99
$avaliacao.avisos.Count                  # 4 (Fase 6 + achados A3/A4)
$avaliacao.limitacoes.Count              # 5 (as da Fase 6)

# 3. consulta o histórico (não reexecuta o modelo)
Invoke-RestMethod -Uri "$base/avaliacoes/$($avaliacao.id_execucao)" -Headers $h
```

### Decisões que afetam o cliente

| Situação | Resposta | Por quê |
|---|---|---|
| Pipeline falha na execução | **HTTP 200** com `status=ERRO` e o contrato integral em `dados` | O HTTP diz "rodou e foi registrada"; o `status` diz o resultado. A trilha de `passos` explica **onde** quebrou. A Fase 6 também reporta falha como conteúdo, não como exceção |
| Paciente inativo | `409 CONFLITO` | O estado atual impede a operação — não é "não encontrado" |
| `modo=real` sem `OPENAI_API_KEY` | `501 NAO_CONFIGURADO` | Falha **antes** de executar; nunca cai em silêncio no simulado |
| Feature ausente/desconhecida/`bool`/`NaN`/negativa | `422 PACIENTE_INVALIDO` | Contrato fechado, **sem defaults**: nada é preenchido por padrão |
| Nome de paciente só com espaços | `422 CONTRATO_VIOLADO` | Sem isso, `"   "` passaria no `min_length` e viraria nome vazio |
| `len(dados) < limite` na listagem | Não há próxima página | A listagem devolve uma lista simples (sem contador total) |
| `GET /avaliacoes/{id}` de uma avaliação com falha | `status=ERRO` no envelope | O envelope reflete o resultado **original**; o HTTP 200 indica que a consulta ao histórico funcionou |

### Por que `features` é `dict[str, Any]` e não `dict[str, float]`

Verificado na prática: o pydantic converte `true` → `1.0` **silenciosamente**. Se o DTO
tipasse `float`, um booleano passaria como valor clínico e **contornaria** a rejeição de
booleano do mapeador (Decisão D4). A validação de valor tem **uma única autoridade**:
`app.integracao.mapeador.montar_caso_para_o_pipeline`.

> ℹ️ **RBAC clínico:** `ADMIN` **não** é superusuário. Ele lê (auditoria, histórico), mas
> não cadastra paciente nem escreve dado clínico — isso exige `MEDICO`. `OPERADOR` não
> acessa dado clínico em nenhuma dessas rotas.

---

## Telemetria IoT (item 5) — Fase 3 integrada

| Método | Rota | Papel mínimo | `dados` |
|---|---|---|---|
| `POST` | `/api/v1/iot/leituras` | `OPERADOR` \| **`X-Device-Key`** | leitura persistida (**201**) |
| `GET` | `/api/v1/iot/leituras` | `OPERADOR` \| `MEDICO` | lista paginada |

### Como o legado foi integrado (e o que mudou)

`DECISOES_ARQUITETURAIS.md` §3.4: as regras vivem em **um módulo de domínio**
(`app/regras_iot.py`), com limiares e lógica **idênticos** aos do `Ir_Alem1/server.py`, e o
serviço Flask fica **desativado**.

O requisito da decisão — *"um teste que compare o comportamento novo com o da origem"* — é
cumprido **executando o handler Flask legado de verdade**: `tests/test_regras_iot.py` carrega
`server.py`, usa o *test client* do Flask e compara a resposta de `POST /sinais` com
`avaliar_sinais` sobre uma grade de **32 combinações** (temperatura × bpm × movimento).

| Comportamento | Situação |
|---|---|
| Limiares `38` e `120`, estritamente **maior** | ✅ preservado (lidos do arquivo-fonte por teste) |
| Cadeia `if/elif/elif` — **um** alerta, prioridade febre > taquicardia > imobilidade | ✅ preservado |
| Textos com acentuação (`AUSÊNCIA DE MOVIMENTO`) | ✅ preservados |
| E-mail via SMTP | ⚠️ **não portado** — ver abaixo |
| `None > 38` levantava `TypeError` (500) | ⚠️ **divergência declarada** — a regra é pulada |

> **E-mail de alerta: não portado, e por quê.** O `server.py` tinha as credenciais SMTP
> *hardcoded*, com a senha sendo o **placeholder `"SECRET"`** — ou seja, o envio **nunca
> funcionou de fato** (`PLANO_SEGURANCA.md` S6 classifica o risco como baixo justamente
> porque "o valor não é real"). Portar essa capacidade significaria implementar algo que
> ninguém consegue usar e cujo contrato não tem campo para o resultado da notificação. O
> alerta **é** entregue — em `avisos` do envelope e na trilha de auditoria.

> **Divergência declarada do `None`.** A origem fazia `if temperatura > 38` sem tratar
> ausência: `None > 38` levanta `TypeError`, então ela respondia **500** a um payload sem
> `temperatura`. Como o contrato da Fase 7 permite enviar **apenas** `bpm` ("pelo menos um
> sinal vital"), herdar isso seria herdar um defeito. `tests/test_regras_iot.py` fixa o fato
> com um teste que verifica o 500 da origem — se a Fase 3 for corrigida, o teste falha e a
> divergência deixa de ser necessária.

### Autenticação: chave de dispositivo

`DECISOES_ARQUITETURAIS.md` §4.1 previa "chave de dispositivo (a introduzir)". A forma
adotada é um **segredo compartilhado** no cabeçalho `X-Device-Key`, comparado em **tempo
constante** (`secrets.compare_digest`) com `IOT_DEVICE_KEY`:

| Situação | Resposta |
|---|---|
| `X-Device-Key` correta | aceita, sem Bearer |
| `X-Device-Key` errada | `401 NAO_AUTENTICADO` |
| `X-Device-Key` enviada, mas `IOT_DEVICE_KEY` **não configurada** | `401` — **recusar** é melhor que aceitar qualquer valor |
| Sem cabeçalho | cai no RBAC: exige `OPERADOR` (`MEDICO`/`ADMIN` → `403`) |

> ⚠️ **Limitação declarada:** a chave é **única para todos os dispositivos** (não há
> cadastro de dispositivo por chave). Ela autentica "um dispositivo autorizado", não
> "o dispositivo X" — o `id_dispositivo` continua vindo do corpo e **não é verificado**
> contra a chave. Revogar um dispositivo exige rotacionar a chave de todos.

### Exemplo

```powershell
$base = "http://127.0.0.1:8000/api/v1"
$chave = "coloque-aqui-o-valor-de-IOT_DEVICE_KEY"

# leitura normal (febre)
$corpo = @{
    id_dispositivo     = "esp32-sala-1"
    origem_transporte  = "rest"
    temperatura        = 39.2
    bpm                = 80
    movimento          = $true
} | ConvertTo-Json

$resposta = Invoke-RestMethod -Method Post -Uri "$base/iot/leituras" `
    -ContentType "application/json" -Headers @{ "X-Device-Key" = $chave } -Body $corpo

$resposta.status     # CONCLUIDO_COM_RESSALVAS
$resposta.avisos     # FEBRE DETECTADA
$resposta.limitacoes # a telemetria NAO alimenta o modelo (Decisão D4)
```

### O que a telemetria **não** faz

`limitacoes` vem preenchida em **toda** resposta de telemetria, porque a Decisão D4 é
contraintuitiva o bastante para precisar ser repetida: **a leitura não entra na predição**.
Das 10 features do modelo, apenas `fc_media` tem correspondência na telemetria (`bpm`, de
origem **simulada**) — as outras 9 não vêm de sensor. O gap está em
`CONTRATOS_API.md` §6.1, como especificação não ativada.

---

## Visão computacional (item 6) — Fase 4 via HTTP

| Método | Rota | Papel mínimo | `dados` |
|---|---|---|---|
| `POST` | `/api/v1/imagens` | `MEDICO` | `ResultadoDeDiagnostico` (**201**) |

### Por que HTTP e não import direto

A Fase 4 é a **única** integração por serviço separado (alternativa **C**), e o motivo está
no código dela: `app.py` faz `load_model(...)` **no import**. Carregar TensorFlow dentro do
backend central criaria o conflito de dependências registrado como risco **R8** (TensorFlow
× scikit-learn da Fase 6) e faria uma falha do TF derrubar o processo. O serviço roda em
**processo isolado**, na porta **5001**.

> ⚠️ **O backend não importa TensorFlow** — nem em teste. O modelo `.keras` (11 MB) existe
> no repositório, mas o serviço não roda neste ambiente porque o TensorFlow não está
> instalado. Por isso os testes usam um **serviço falso** que reproduz o contrato real, e o
> smoke test faz a chamada HTTP **entre processos**.

### Como subir o serviço da Fase 4

```powershell
cd Fase_4/Fase_4_Cap1/Ir_Alem2/backend
pip install flask flask-cors tensorflow pillow
flask --app app run --port 5001     # o app.py declara 5000; o mapa de portas exige 5001
```

### O que a Fase 4 devolve — e o que o backend acrescenta

| Campo do contrato | Origem |
|---|---|
| `classe` · `confianca` | **Fase 4** (campos `class` e `confidence`) |
| `modelo_utilizado` · `limiar_decisao` · `dimensoes_da_imagem` | **acrescentados pelo backend** (achado I9): a Fase 4 não os informa |
| `hash_sha256` | **backend**, sobre os bytes recebidos |
| `aviso_de_uso` | **backend** |

`{class, confidence}` → `{classe, confianca}` é tradução **de borda** (nota N4), e **não** há
unificação com o `DiagnosticoDaPredicao` da Fase 6 (achado I3: são contratos distintos).

Seis testes leem `Ir_Alem2/backend/app.py` e conferem que as constantes declaradas
(`mobilenet_pneumonia.keras`, limiar `0.5`, `target_size=(128, 128)`, campo `image`, classes
`Normal`/`Pneumonia`) **não divergiram** do fonte normativo (risco R6).

### Endurecimento da borda

O contrato §4.6 pede duas proteções que a Fase 4 não tem (ela aceita "qualquer arquivo que o
Keras abra"):

| Proteção | Comportamento |
|---|---|
| `content_type` | aceita `image/jpeg` e `image/png`; o resto → `422 CONTRATO_VIOLADO` |
| Teto de tamanho | `LIMITE_DE_UPLOAD_MB` (padrão 10) → `413 LIMITE_EXCEDIDO`. Checado **antes** de ler o corpo (via `Content-Length`) e também no `read(limite + 1)` |

### Falhas do serviço

| Situação | Resposta |
|---|---|
| Serviço inalcançável (DNS ou recusa) | `502 ERRO_DE_SERVICO_DE_VISAO` |
| Serviço não responde no prazo | `504 TIMEOUT_EXTERNO` |
| Serviço responde HTTP ≠ 200 | `502 ERRO_DE_SERVICO_DE_VISAO` |
| Resposta fora do contrato (`class` desconhecida, `confidence` não numérica) | `502` — **nunca** um diagnóstico silencioso |

> 🔒 **A imagem não é persistida.** Guardam-se o `hash_sha256` (detecção de reenvio), o
> `mime`, o tamanho e o nome. A tabela `analises_de_imagem` não tem coluna de binário, e a
> trilha de auditoria registra apenas esses metadados — **não** a classe nem a confiança,
> porque o resultado é dado clínico e já está na própria tabela.

### Exemplo

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/imagens" `
  -H "Authorization: Bearer $token" `
  -F "imagem=@radiografia.jpg;type=image/jpeg"
```

---

## Assistente conversacional (item 7) — Fase 5

| Método | Rota | Papel mínimo | `dados` |
|---|---|---|---|
| `POST` | `/api/v1/chat` | `OPERADOR` \| `MEDICO` | `MensagemDoAssistente` |
| `GET` | `/api/v1/conversas/{id_conversa}` | `OPERADOR` \| `MEDICO` | histórico de mensagens |

### ⚠️ O backend NÃO importa o `IBM_API.py` da Fase 5 — e isso é deliberado

A Decisão 1 previa *"import direto de `IBM_API.py`"*. **Não foi feito**, por segurança:

| Fato | Consequência |
|---|---|
| `IBM_API.py` lê as credenciais com `os.getenv("WATSON_API_KEY", "<chave real do projeto>")` — **a chave vazada é o default** (achado **S1**, correção **C1**) | Importar o módulo grava a chave nos seus constantes de topo, e `get_assistant()` a usaria em silêncio se o ambiente estivesse vazio |
| `app.py` executa `assistant = get_assistant()` **no import** | Importá-lo criaria um cliente autenticado com a chave vazada **e** um `Flask(__name__)` |

O **objetivo** da decisão é preservado: mesmo SDK, mesma versão de API (`2024-08-25`), mesmo
timeout, e a "camada de tradução fina" com o **mesmo mapeamento** de `friendly_watson_error`.
Cinco testes conferem essas constantes e faixas de status **contra o arquivo-fonte**.

> ✅ **Prova de que a chave vazada não é usada:** com o ambiente vazio, `POST /chat` responde
> **`501 NAO_CONFIGURADO`**. Se o backend herdasse os defaults, ele tentaria uma chamada real —
> a recusa é a evidência. Verificado em teste **e** no smoke test com o servidor de verdade.

### O `session_id` do Watson nunca sai daqui (achado I8)

| Camada | O que trafega |
|---|---|
| Cliente → backend | `mensagem` e, opcionalmente, `id_conversa` |
| Backend → Watson | a sessão do provedor (`create_session` / `message`) |
| Banco | `mensagens.session_id_do_provedor` — **interno** |
| Backend → cliente | `id_conversa` (gerado aqui), `resposta`, `criado_em`, `papel`, `fontes`, `avisos` |

O cliente **não pode** enviar `session_id`: o contrato é fechado e o campo é recusado (`422`).

### `fontes` é sempre `[]` (nota N6)

O Watson Assistant **não devolve fontes**. Preencher com conteúdo inventado seria pior do que
assumir a ausência — e a ausência está declarada em `limitacoes`.

### Erros do provedor

| Situação | Resposta |
|---|---|
| Watson **não configurado** | `501 NAO_CONFIGURADO` (com a lista do que falta) |
| Credencial inválida do Watson (401/403) | `502` + código **`FALHA_DE_AUTENTICACAO_EXTERNA`** |
| Cota do plano (429) | `429 COTA_EXCEDIDA` |
| Demora (408/504) | `504 TIMEOUT_EXTERNO` |
| Demais | `502 ERRO_DE_SERVICO_EXTERNO` |

> ⚠️ **Por que `502` e não `507`:** a Fase 5 usava **507** (`Insufficient Storage`,
> RFC 4918) para falha de autenticação — nos dois lados do seu contrato. O código foi
> mantido, mas o transporte foi corrigido na auditoria: `401`/`403` são reservados à
> autenticação **do usuário** e devolvê-los aqui faria um cliente encerrar a sessão do
> usuário por um problema do provedor. Detalhes em `CONTRATOS_API.md` §3.2.1.

A sessão expirada no Watson (404) é **recuperada**: o backend abre outra e reintenta **uma
vez** — mesmo comportamento do `app.py` da Fase 5.

### Exemplo

```powershell
# primeiro turno: abre a conversa
$r1 = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/chat" -Headers $h `
    -ContentType "application/json" -Body '{"mensagem": "O que e insuficiencia cardiaca?"}'
$r1.dados.id_conversa
$r1.dados.fontes          # [] — o Watson nao devolve fontes

# turno seguinte: continua a mesma conversa
$corpo = @{ mensagem = "E quais sao os sinais de alerta?"; id_conversa = $r1.dados.id_conversa } |
    ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/chat" -Headers $h `
    -ContentType "application/json" -Body $corpo

# historico
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/conversas/$($r1.dados.id_conversa)" -Headers $h
```

> ℹ️ **O canal não é exposto pelo contrato §4.5:** conversas são registradas como `web`. O
> valor `mobile` existe no enum e no banco, mas nenhuma rota o produz — gancho para quando o
> app Expo da Fase 5 for integrado.

---

**Toda** resposta — inclusive erros — usa o envelope comum:

```json
{
  "id_execucao": "30913f59-2512-4598-acf7-79bff2826feb",
  "gerado_em": "2026-10-31T15:56:29.110181Z",
  "status": "CONCLUIDO",
  "dados": { },
  "avisos": [],
  "limitacoes": [],
  "erros": [],
  "metadados": { "versao_api": "v1", "origem": "cardioia-backend" }
}
```

| Regra | Comportamento |
|---|---|
| `CONCLUIDO` / `CONCLUIDO_COM_RESSALVAS` | exigem `dados` e **proíbem** `erros` |
| `INCOMPLETO` / `ERRO` | exigem **ao menos um** erro — falha nunca fica muda |
| Erros | sempre `{"codigo", "mensagem", "campo", "detalhe"}` — nunca `{"detail": ...}` |
| Campos desconhecidos | rejeitados (`extra="forbid"`) |

### `GET /api/v1/health`

| Status | Quando |
|---|---|
| `CONCLUIDO` | artefato do modelo presente |
| `CONCLUIDO_COM_RESSALVAS` | artefato **ausente** — o aviso traz o comando de treino |

O endpoint **não** executa o modelo nem importa a Fase 6; reporta apenas a presença dos
arquivos. As integrações externas são reportadas **como booleano** — nenhum valor de
credencial é exposto.

---

## Erros

Os códigos são **estáveis** e têm procedência rastreável (`CONTRATOS_API.md` §3.2):

| Origem | Códigos |
|---|---|
| **Herdados da Fase 5** (contrato real já existente) | `NAO_CONFIGURADO` (501) · `FALHA_DE_AUTENTICACAO_EXTERNA` (507) · `COTA_EXCEDIDA` (429) · `TIMEOUT_EXTERNO` (504) · `ERRO_DE_SERVICO_EXTERNO` (502) |
| **Derivados das exceções da Fase 6** | `CONTRATO_VIOLADO` · `PACIENTE_INVALIDO` · `DADOS_DO_PACIENTE_INVALIDOS` · `MODELO_INDISPONIVEL` (503) · `MODELO_INCOMPATIVEL` · `FALHA_DE_PREVISAO` · `BASE_DE_PROTOCOLOS_INVALIDA` |
| **Novos (Fase 7)** | `ERRO_DE_SERVICO_DE_VISAO` · `NAO_AUTENTICADO` · `NAO_AUTORIZADO` · `NAO_ENCONTRADO` · `CONFLITO` · `LIMITE_EXCEDIDO` · `TAXA_EXCEDIDA` · `ERRO_DE_CONFIGURACAO` · `ERRO_INTERNO` |

---

## Segurança

| Controle | Situação |
|---|---|
| Segredos **apenas** em variável de ambiente / `.env` | ✅ |
| Nenhum valor default de segredo no código | ✅ |
| Falha rápida sem `JWT_SECRET` (≥ 32 caracteres) | ✅ |
| CORS restrito às origens configuradas | ✅ |
| Cookies desabilitados (token no header `Authorization`) | ✅ |
| Nenhuma credencial exposta em `/health` ou em logs | ✅ |
| `.env` no `.gitignore` | ✅ |

---

## Dependências

Todas **já instaladas** no ambiente (nenhuma instalação nova foi necessária):

| Pacote | Versão |
|---|---|
| `fastapi` | 0.119.0 |
| `uvicorn` | 0.37.0 |
| `pydantic` | 2.14.1 |
| `pydantic-settings` | 2.14.1 |
| `python-dotenv` | 1.2.2 |
| `pytest` | 9.1.1 |
| `httpx` | 0.28.1 |

A liberar nos itens seguintes (já instaladas): `sqlalchemy` 2.0.49 (item 2), `PyJWT` 2.13.0
e `bcrypt` 5.0.0 (item 3).
