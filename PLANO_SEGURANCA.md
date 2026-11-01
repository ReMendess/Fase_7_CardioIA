# CardioIA — Fase 7 · Plano de Segurança

> **Plano de tratamento de credenciais e proteção de dados**
> Documentos relacionados: [`DECISOES_ARQUITETURAIS.md`](DECISOES_ARQUITETURAIS.md) · [`MODELO_DADOS.md`](MODELO_DADOS.md) · [`CONTRATOS_API.md`](CONTRATOS_API.md)
>
> ## 🔒 Regra deste documento
>
> **Nenhum valor de credencial é reproduzido aqui.** Onde existe segredo, há **referência mascarada**
> no formato `<arquivo>:<constante>` + o **tipo** de credencial. Os valores estão nos repositórios das
> fases anteriores e **devem ser considerados comprometidos**.
>
> **Nenhuma alteração foi feita nos repositórios anteriores nesta etapa.**

---

## 1. Princípio norteador

> **Um segredo que já foi versionado deve ser tratado como comprometido.**
> Removê-lo do histórico **não** desfaz a exposição: o valor pode ter sido copiado, indexado, clonado
> ou coletado por varreduras automáticas. Por isso a **ordem de prioridade** é:

| Ordem | Ação | Natureza |
|---|---|---|
| **1** | **Rotacionar/revogar** a credencial no provedor | **Obrigatória** — ✅ **autorizada (Q8)** |
| **2** | Externalizar para variável de ambiente | Obrigatória |
| **3** | Limpar o histórico do Git | 🚫 **NÃO AUTORIZADA (Q9)** — ver seção 6 |
| **4** | Prevenir recorrência (varredura + teste) | Obrigatória — ✅ instalação autorizada (Q10) |
| **5** | Governança e política de segredos | Contínua |

**Consequência prática:** com Q9 não aprovada, o plano definitivo é a **alternativa mínima** —
as etapas 1, 2, 4 e 5 **já neutralizam o risco**, pois tornam o valor exposto **inútil**. A exposição
remanescente no histórico passa a ser apenas **registro de um valor sem validade**.

---

## 2. Inventário de exposições

> Referências mascaradas — sem valores.

| ID | Arquivo afetado | Constante(s) | Tipo de credencial | Repositório |
|---|---|---|---|---|
| **S1** | `Fase_5/Fase5_CardioAssist/Backend/IBM_API.py` | `API_KEY` (default no `os.getenv`) | 🔴 **API key IAM** do IBM Cloud (chave privada) | `Fase5_CardioAssist` |
| **S2** | `Fase_5/Fase5_CardioAssist/Backend/IBM_API.py` | `SERVICE_URL`, `ASSISTANT_ID`, `ENVIRONMENT_ID` | Identificadores de instância/serviço (não são chaves, mas são reconhecíveis) | `Fase5_CardioAssist` |
| **S3** | `Fase_3/Cap_1_CardioIA_Conectada/Parte2/codigo_parte2.c` | `mqtt_user`, `mqtt_pass` | 🔴 **Usuário + senha MQTT** (HiveMQ Cloud) | `Cap_1_CardioIA_Conectada` |
| **S4** | `Fase_3/Cap_1_CardioIA_Conectada/Parte2/codigo_parte2.c` | `mqtt_server` | Host do cluster do broker | `Cap_1_CardioIA_Conectada` |
| **S5** | `Fase_3/Cap_1_CardioIA_Conectada/Ir_Alem1/server.py` | `EMAIL_REMETENTE`, `EMAIL_DESTINO` | Endereço de e-mail pessoal | `Cap_1_CardioIA_Conectada` |
| **S6** | `Fase_3/Cap_1_CardioIA_Conectada/Ir_Alem1/server.py` | `EMAIL_SENHA` | ⚠️ Senha SMTP — **o valor é o placeholder `"SECRET"`** | `Cap_1_CardioIA_Conectada` |
| **S7** | `Fase_2/Cap2_Desafio_Integrador/Ir_Alem/my-react-app/src/contexts/AuthContext.jsx` | credenciais do `login()` + token fake | 🟢 Credenciais **fictícias** de demonstração (não são segredos reais) | `Cap2_Desafio_Integrador` |
| **S8** | `Fase_5/.../Backend/.env.example` · `Fase_5/.../CardioAssist/.env.example` | nomes das variáveis | ✅ **Correto** — apenas nomes, sem valores | — |
| **S9** | `Fase_6/cardioia_Fase6/.env.example` | `OPENAI_API_KEY` (vazio), `OPENAI_MODEL` | ✅ **Correto** — **padrão de referência** | — |
| **S10** | `Fase_6/cardioia_Fase6/.gitignore` | regras `*.key`, `.env`, `!.env.example` | ✅ **Correto** — **padrão de referência** | — |

### 2.1 Dados sensíveis não-secretos também expostos

| ID | Dado | Onde | Observação |
|---|---|---|---|
| D1 | Endereço de e-mail pessoal | `Ir_Alem1/server.py` | Dado pessoal (LGPD), não credencial |
| D2 | Host/identificadores de infraestrutura | Fases 3 e 5 | Facilita reconhecimento e ataques direcionados |
| D3 | Regras de negócio com limiares clínicos | Fase 3 (`38`, `120`) | Não é segredo, mas é informação de domínio |

---

## 3. Classificação de risco

| ID | Exposição | Confidencialidade | Integridade | Disponibilidade | Risco global |
|---|---|---|---|---|---|
| S1 | API key IAM (Watson) | 🔴 Alta (acesso a serviço pago) | 🔴 Alta | 🔴 Alta (cota consumida) | 🔴 **CRÍTICO** |
| S3 | Usuário + senha MQTT | 🔴 Alta (publicar/assinar tópicos) | 🔴 Alta (injeção de dados falsos) | 🟡 Média | 🔴 **ALTO** |
| S4 | Host do broker | 🟡 Média | 🟡 Média | 🟡 Média | 🟡 Médio |
| S5 | E-mail pessoal | 🟡 Média (dado pessoal) | 🟢 Baixa | 🟢 Baixa | 🟡 Médio |
| S6 | Senha SMTP (placeholder) | 🟢 Baixa (valor não é real) | 🟢 Baixa | 🟢 Baixa | 🟢 Baixo |
| S2 | IDs de instância | 🟡 Média | 🟢 Baixa | 🟢 Baixa | 🟡 Médio |
| S7 | Credenciais fictícias | 🟢 Baixa | 🟡 Média (**padrão ruim**) | 🟢 Baixa | 🟢 Baixo |

**Impacto real de S1/S3 se explorados:** consumo da cota paga do Watson, injeção de telemetria falsa
no broker (que, na Fase 7, poderia alimentar o painel de monitoramento) e custo/abuso.

---

## 4. Plano de contenção — rotação (obrigatória)

> ⚠️ **Estas ações ocorrem nos provedores, fora do Git.** Não alteram os repositórios das fases
> anteriores.

| Passo | Ação | Provedor / onde | Resultado esperado |
|---|---|---|---|
| **R1** | Gerar **nova API key** do Watson e **revogar** a antiga | IBM Cloud → IAM → API keys | Valor antigo inutilizado |
| **R2** | Atualizar `WATSON_SERVICE_URL`, `ASSISTANT_ID`, `ENVIRONMENT_ID` se houver reinstância | IBM Cloud → Watson Assistant | IDs novos |
| **R3** | **Trocar a senha** do usuário MQTT (ou criar credencial nova e desativar a antiga) | HiveMQ Cloud → Access Management | Senha antiga inutilizada |
| **R4** | Considerar **rotacionar o cluster** se ele tiver sido exposto além do necessário | HiveMQ Cloud | Reduz superfície |
| **R5** | **Revogar a senha de app** do Gmail e gerar outra | Conta Google → Segurança → Senhas de app | Credencial antiga inutilizada |
| **R6** | Avaliar se o e-mail pessoal exposto deve continuar sendo o remetente | — | Evita exposição contínua de dado pessoal |
| **R7** | Registrar data, responsável e evidência de cada rotação | Documento interno | Auditabilidade |

### 4.1 Checklist de rotação

| # | Item | Status |
|---|---|---|
| 1 | API key do Watson rotacionada e antiga revogada | ✅ autorizado (Q8) — aguardando execução pelo titular |
| 2 | Credencial MQTT trocada e antiga desativada | ✅ autorizado (Q8) — aguardando execução pelo titular |
| 3 | Senha de app do Gmail revogada e substituída | ✅ autorizado (Q8) — aguardando execução pelo titular |
| 4 | Novos valores guardados **apenas** em `.env` local ou cofre | ⏳ pendente (execução do titular) |
| 5 | Evidência das rotações registrada | ⏳ pendente |
| 6 | Confirmado que **nenhum** valor novo foi commitado | ⏳ pendente |

---

## 5. Externalização

### 5.1 Padrão adotado (copiado da Fase 6)

| Elemento | Regra |
|---|---|
| Arquivo de segredos | `.env` na raiz do serviço — **nunca** versionado |
| Arquivo de exemplo | `.env.example` com **nomes e comentários**, **sem valores** |
| `.gitignore` | `.env`, `.env.*`, `!.env.example`, `*.key` |
| Leitura | `python-dotenv` (já instalado) ou `os.environ` |
| Falha rápida | variável obrigatória ausente → serviço **não sobe** com mensagem explícita |

### 5.2 Variáveis previstas para a Fase 7

| Variável | Obrigatória | Uso | Segredo? |
|---|:---:|---|:---:|
| `DATABASE_URL` | ✅ | conexão com o banco | 🟡 pode conter senha |
| `JWT_SECRET` | ✅ | assinatura dos tokens | 🔴 **sim** |
| `JWT_ALGORITHM` | ❌ | padrão `HS256` | não |
| `ACCESS_TOKEN_MINUTOS` | ❌ | padrão 30 | não |
| `REFRESH_TOKEN_DIAS` | ❌ | padrão 7 | não |
| `OPENAI_API_KEY` | ⚠️ só no modo `real` | LLM dos agentes (Fase 6) | 🔴 **sim** |
| `OPENAI_MODEL` | ❌ | padrão `gpt-4o-mini` | não |
| `WATSON_API_KEY` | ⚠️ só para o chat | Watson (Fase 5) | 🔴 **sim** |
| `WATSON_SERVICE_URL` · `WATSON_ASSISTANT_ID` · `WATSON_ENVIRONMENT_ID` | ⚠️ idem | Watson | não (identificadores) |
| `SERVICO_VISAO_URL` | ❌ | serviço da Fase 4 (padrão `http://localhost:5001`) | não |
| `CORS_ORIGENS` | ✅ | origens permitidas (hoje **aberto** nas Fases 4 e 5) | não |
| `MQTT_HOST` · `MQTT_PORT` · `MQTT_USER` · `MQTT_PASS` | ⚠️ só se a ingestão MQTT for ativada | broker HiveMQ | 🔴 **sim** (user/pass) |
| `ARQUIVO_BANCO` | ❌ | caminho do SQLite | não |

> ⚠️ **Nenhum valor é escrito neste documento** — apenas nomes de variáveis.

### 5.3 Regra de migração dos códigos legados

| Fase | Situação atual | Ação na Fase 7 |
|---|---|---|
| 5 | Credenciais como **default** em `IBM_API.py` | ✅ **Resolvido** — ver abaixo |
| 3 | Credenciais **literais** no firmware e no `server.py` | ✅ **Resolvido** — ver abaixo |
| 4 | Sem credenciais | — |
| 6 | ✅ Já correto | Reaproveitar o padrão |

### Fase 5 — resolvida

`Backend/IBM_API.py` trazia a **chave do Watson**, o *service URL* (com o ID da instância), o
`ASSISTANT_ID` e o `ENVIRONMENT_ID` como **valores default** de `os.getenv(...)`. O arquivo
foi sanitizado: as quatro variáveis agora têm default **vazio** e vêm somente do ambiente.

**A chave foi desativada na plataforma.** Isso encerra o risco operacional: o valor exposto
não autentica mais em lugar nenhum. A correção **C1** passa de *"rotacionar"* para
*"desativada"*.

O backend da Fase 7 **nunca importou** esse módulo (ver §"Assistente conversacional" do
`backend/README.md`) — ele constrói o cliente do Watson apenas com valores do ambiente, o
que é verificado por teste.

### Fase 3 — resolvida

| Arquivo | O que trazia | Situação |
|---|---|---|
| `Parte2/codigo_parte2.c` | `mqtt_server`, `mqtt_user`, `mqtt_pass` **literais** | substituídos por marcadores (`SEU_CLUSTER`, `SEU_USUARIO`, `SUA_SENHA`) |
| `Ir_Alem1/server.py` | `EMAIL_SENHA = "SECRET"` (já era placeholder) + **e-mails pessoais** | e-mails trocados por `seu.email@exemplo.com` / `destino@exemplo.com` |

> ℹ️ O `EMAIL_SENHA` **já era** o placeholder `"SECRET"` — o envio nunca funcionou de fato.
> A troca dos endereços é por **privacidade**, não por vazamento de credencial.

### Varredura executada antes do commit

| Padrão | Ocorrências |
|---|---|
| chave do Watson | **0** |
| cluster do HiveMQ | **0** |
| senha do broker | **0** |
| e-mails pessoais | **0** |
| pastas `__pycache__` | **0** (o `.pyc` do `IBM_API` continha a chave compilada) |

**Como a Fase 5 foi resolvida (item 7):** o backend **não importa** `IBM_API.py` nem `app.py`.
O módulo `app/integracao/fase_5.py` constrói o cliente do Watson **apenas** com valores de
`Configuracoes` (que lê o ambiente) — nenhum valor default de credencial existe no código.

| Credencial legada | Situação |
|---|---|
| `WATSON_API_KEY` (chave **real** como default em `IBM_API.py`) | **Não usada.** Com o ambiente vazio, `POST /chat` responde `501 NAO_CONFIGURADO` em vez de tentar a chamada. Há teste e verificação no smoke test |
| `WATSON_SERVICE_URL` · `WATSON_ASSISTANT_ID` · `WATSON_ENVIRONMENT_ID` (IDs reais como default) | **Não usados** — vêm apenas do ambiente |
| *(nova)* `WATSON_TIMEOUT_SEGUNDOS` | Prazo da chamada, configurável (padrão 30 s, o mesmo `WATSON_TIMEOUT` da Fase 5) |

> ✅ **Correção C1 — encerrada:** a chave foi **desativada** na plataforma IBM. O valor exposto
> não autentica mais em lugar nenhum, e o arquivo de origem foi **sanitizado** (sem default).
> Não é preciso rotacionar. A reescrita do histórico do Git continua **não autorizada** (Q9) —
> e agora é irrelevante, porque o valor não tem mais utilidade.

**Como a Fase 3 foi resolvida (item 5):** o serviço Flask `Ir_Alem1/server.py` fica
**desativado**; as regras passam a viver em `backend/app/regras_iot.py` e a ingestão em
`POST /api/v1/iot/leituras`. Consequências para as credenciais legadas:

| Credencial legada | Situação |
|---|---|
| `EMAIL_REMETENTE` · `EMAIL_DESTINO` · `EMAIL_SENHA` (SMTP Gmail, *hardcoded*) | **Não portadas.** A senha na origem é o placeholder `"SECRET"` — o envio nunca funcionou de fato. O alerta é entregue em `avisos` e na trilha de auditoria |
| `MQTT_HOST` · `MQTT_USER` · `MQTT_PASS` (firmware) | **Sanitizados**: os três viraram marcadores (`SEU_CLUSTER`, `SEU_USUARIO`, `SUA_SENHA`). O backend **não** consome MQTT; a ingestão é HTTP |
| *(nova)* `IOT_DEVICE_KEY` | Chave compartilhada dos dispositivos (`X-Device-Key`), **somente em variável de ambiente**, comparada em tempo constante. Sem ela configurada, o caminho da chave é recusado |

> ⚠️ **Limitação declarada:** a chave é única para todos os dispositivos — não há cadastro
> por dispositivo. Ela autentica "um dispositivo autorizado", não "o dispositivo X", e o
> `id_dispositivo` do corpo não é confrontado com a chave. Revogar um dispositivo exige
> rotacionar a chave de todos.

> ✅ **Arquivos das Fases 3 e 5 sanitizados** com autorização explícita do autor (decisão **D2**):
> as credenciais literais foram substituídas por marcadores. A lógica das fases **não** foi
> alterada — só os valores.

---

## 6. Limpeza do histórico do Git — ❌ **NÃO AUTORIZADA (Q9)**

> ### 🚫 Decisão do autor: **não aprovada**
> A reescrita do histórico **não será executada**. O plano definitivo passa a ser a
> **alternativa mínima** (seção 6.3): **rotação das credenciais** + **aviso documentado**.
>
> **Justificativa registrada:** operação **destrutiva** que invalida clones e afeta **forks de
> terceiros** — as Fases 1 e 2 têm **4 integrantes**. O custo de coordenação supera o benefício, já
> que a rotação torna o valor exposto **inútil**.

### 6.1 Contexto e riscos da operação (mantido para registro histórico)

| Aspecto | Situação |
|---|---|
| Natureza | 🔴 **Destrutiva** — reescreve commits e invalida clones existentes |
| Repositórios que seriam afetados | `Cap2_Desafio_Integrador` (S7), `Cap_1_CardioIA_Conectada` (S3–S6), `Fase5_CardioAssist` (S1–S2) |
| Terceiros afetados | **Forks e clones** de todos os colaboradores — as Fases 1 e 2 têm **4 integrantes** |
| Reversibilidade | ⚠️ Parcial (somente via backup `--mirror`) |
| **Status** | 🚫 **NÃO AUTORIZADA** — não será executada |

### 6.2 Procedimento (documentado apenas para eventual uso futuro)

> ⚠️ **Não executar.** Mantido no documento para que a decisão possa ser revista com conhecimento do
> custo.

| Passo | Comando / ação | Observação |
|---|---|---|
| 1 | **Backup completo** — `git clone --mirror <repo> <repo>.backup.git` | Único ponto de recuperação |
| 2 | Ferramenta | `git filter-repo` (**recomendada**) ou `BFG Repo-Cleaner`. ❌ `git filter-branch` é a opção nativa, porém lenta e desaconselhada |
| 3 | Substituição | Trocar o **valor literal** por um placeholder (ex.: `REDACTED`) em todos os arquivos e commits |
| 4 | Expurgo local | `git reflog expire --expire=now --all` + `git gc --prune=now --aggressive` |
| 5 | Publicação | `git push --force --all` e `git push --force --tags` |
| 6 | **Todos** os colaboradores | Re-clonar (o histórico reescrito invalida clones locais) |
| 7 | Integrações | Revogar/atualizar webhooks, CI e chaves de deploy que referenciem commits antigos |
| 8 | Verificação | Rodar varredura de segredos (seção 7) no histórico reescrito |

### 6.3 ✅ Plano definitivo adotado (alternativa mínima)

| # | Ação | Efeito | Status |
|---|---|---|---|
| 1 | **Rotacionar/revogar** as credenciais nos provedores | O valor exposto torna-se **inútil** | ✅ **autorizado (Q8)** — execução pelo titular das contas |
| 2 | **Externalizar** os segredos no código novo da Fase 7 | Novos valores nunca entram no repositório | ⏳ Etapa C |
| 3 | **Aviso documentado** nos repositórios afetados | Transparência sobre a exposição histórica | 🟡 recomendado |
| 4 | **Registrar o incidente** internamente (data, causa, ação) | Rastreabilidade | 🟡 recomendado |
| 5 | Reescrita do histórico | — | 🚫 **não aprovada** |

**Eficácia do plano adotado:** ✅ as credenciais rotacionadas **não dão mais acesso a nada**; a
exposição remanescente no histórico é apenas **registro de um valor inútil**. O risco residual é
**baixo**.

---

## 7. Prevenção

### 7.1 Ferramentas de varredura

| Ferramenta | Uso | Status |
|---|---|---|
| `gitleaks` | varredura de segredos em commits e staging | ❌ **não instalada** — instalação requer autorização |
| `detect-secrets` (Yelp) | varredura + baseline | ❌ não instalada |
| `trufflehog` | varredura de histórico e entropia | ❌ não instalada |
| `git-secrets` (AWS) | hook de pre-commit | ❌ não instalada |

> ⚠️ Nenhuma ferramenta foi instalada (restrição vigente). A instalação é uma **decisão pendente**
> (Q10 em [`DECISOES_ARQUITETURAIS.md`](DECISOES_ARQUITETURAIS.md)).

### 7.2 Controles que **não** exigem instalação

| Controle | Implementação |
|---|---|
| `.gitignore` robusto | Replicar o padrão da Fase 6 (`!.env.example`, `*.key`) |
| **Teste automatizado de ausência de segredos** | ⭐ **Reaproveitar `tests/test_seguranca.py`** da Fase 6 — já verifica ausência de segredos e portabilidade de caminhos |
| Revisão de PR | Checklist obrigatório de segredos |
| Falha rápida no startup | Serviço não sobe sem as variáveis obrigatórias |
| `.env.example` sempre sem valores | Revisão no PR |
| Não logar segredos | Teste que verifica ausência de tokens em logs |

### 7.3 Testes de segurança previstos para a Fase 7

| # | Teste | Verifica |
|---|---|---|
| T1 | Nenhum arquivo do repositório contém padrão de chave/segredo | varredura simples por regex sobre os fontes |
| T2 | O backend **não sobe** sem `JWT_SECRET` | falha rápida |
| T3 | Nenhum endpoint devolve `senha_hash`, `session_id` de provedor ou chave | contrato de resposta |
| T4 | Nenhum log contém token nem payload clínico | captura de log em teste |
| T5 | `401` sem token; `403` com papel insuficiente | RBAC |
| T6 | `.env` não está versionado (e `.env.example` está) | `.gitignore` |
| T7 | CORS restrito às origens configuradas | cabeçalhos |

---

## 8. Governança

### 8.1 Política de segredos

| Regra | Descrição |
|---|---|
| G1 | **Nenhum** segredo em código, comentário, teste, notebook ou documentação |
| G2 | Segredos **apenas** em `.env` local ou cofre de segredos |
| G3 | `.env.example` contém **nomes e comentários**, nunca valores |
| G4 | Segregação por ambiente (dev / homologação / produção) com credenciais distintas |
| G5 | **Rotação periódica** (recomendação: 90 dias para chaves de API) |
| G6 | Menor privilégio nas credenciais (escopos mínimos) |
| G7 | Revogação imediata ao desligamento de um colaborador |
| G8 | Registro de incidentes de exposição (data, causa, ação, evidência) |
| G9 | Revisão de segurança antes de tornar qualquer repositório público |
| G10 | Nenhum dado real de paciente em ambiente de desenvolvimento |

### 8.2 Responsabilidades

| Papel | Responsabilidade |
|---|---|
| Autor/owner do projeto | Autorizar rotações, reescrita de histórico e instalação de ferramentas |
| Desenvolvedor | Cumprir a política; nunca commitar segredo; reportar exposição |
| Revisor de PR | Verificar G1–G4 em cada mudança |

---

## 9. Checklist consolidado

| # | Item | Prioridade | Status |
|---|---|---|---|
| 1 | Rotacionar/revogar API key do Watson | 🔴 Crítica | ✅ **AUTORIZADO (Q8)** — a executar pelo titular da conta IBM |
| 2 | Trocar credencial MQTT | 🔴 Alta | ✅ **AUTORIZADO (Q8)** — a executar pelo titular da conta HiveMQ |
| 3 | Revogar senha de app do Gmail | 🔴 Alta | ✅ **AUTORIZADO (Q8)** — a executar pelo titular da conta Google |
| 4 | Guardar novos valores apenas em `.env`/cofre | 🔴 Alta | ⏳ pendente (execução do titular) |
| 5 | Criar `.env.example` sem valores para o backend da Fase 7 | 🔴 Alta | ⏳ Etapa C |
| 6 | Backend falha rápido sem `JWT_SECRET` | 🔴 Alta | ⏳ Etapa C |
| 7 | Replicar `.gitignore` da Fase 6 | 🟡 Média | ⏳ Etapa C |
| 8 | Reaproveitar `tests/test_seguranca.py` | 🟡 Média | ⏳ Etapa C |
| 9 | Restringir CORS às origens conhecidas | 🟡 Média | ⏳ Etapa C |
| 10 | Implementar testes T1–T7 | 🟡 Média | ⏳ Etapa C |
| 11 | Aviso de incidente nos READMEs das fases afetadas | 🟡 Média | 🟡 recomendado (sem alterar as fases nesta etapa) |
| 12 | Instalar ferramenta de varredura de segredos | 🟡 Média | ✅ **AUTORIZADO (Q10)** — a executar na Etapa C |
| 13 | Reescrever histórico do Git (Fases 2, 3, 5) | — | 🚫 **NÃO APROVADO (Q9)** — descartado |
| 14 | Documento formal de política de segredos | 🟢 Desejável | 🟡 este documento (§8) cumpre o papel no MVP |
| 15 | Sanitizar a documentação da Fase 7 (sem valores) | ✅ Concluído | ✅ **feito** |

### 9.1 Resumo das autorizações

| Questão | Assunto | Resolução |
|---|---|---|
| **Q8** | Rotação de credenciais | ✅ **AUTORIZADA** |
| **Q9** | Reescrita do histórico Git | ❌ **NÃO APROVADA** |
| **Q10** | Instalação de ferramenta de varredura | ✅ **AUTORIZADA** |

> ⚠️ **Nota de execução (Q8):** a rotação ocorre nos **consoles dos provedores** (IBM Cloud, HiveMQ,
> Google). Ela **não** pode ser feita por este assistente — depende do acesso do titular das contas.
> O que a Fase 7 garante é que o **código novo** leia as credenciais **apenas** de variável de
> ambiente, sem nenhum valor default.

---

## 10. Limitações declaradas e LGPD

### 10.1 Limitações de segurança do MVP

| # | Limitação | Impacto |
|---|---|---|
| L1 | **Sem criptografia em repouso** no banco (SQLite sem SQLCipher) | Dado legível no arquivo |
| L2 | **Sem rate limiting robusto** (nenhuma lib instalada) | Proteção parcial contra força bruta |
| L3 | **Sem 2FA / MFA** | Apenas senha + JWT |
| L4 | **Sem rotação automática** de chaves | Processo manual |
| L5 | **Sem varredura de segredos automatizada** (ferramentas não instaladas) | Detecção manual |
| L6 | **Sem HTTPS no ambiente de dev** | Aceitável apenas localmente |
| L7 | **Sem WAF / proteção de borda** | Fora do escopo do MVP |
| L8 | **Sem backup automatizado** | Perda de dados em falha |

### 10.2 LGPD e dados de saúde

| Item | Situação |
|---|---|
| **Dados atuais** | **100% sintéticos** — gerados por regras (`np.random.seed(42)`); **não há titular de dados** |
| **Classificação** | Em cenário real, seriam **dados pessoais sensíveis** (dados referentes à saúde) |
| **Base legal** | ⏳ a definir quando/se houver dados reais |
| **Minimização** | ✅ imagem não persistida; apenas hash + metadados |
| **Segurança** | ⚠️ criptografia em repouso **ausente** no MVP |
| **Retenção** | ⏳ a definir pelo autor |
| **Transparência** | ✅ `AVISO_DE_USO` + `LIMITACOES_PADRAO` em toda resposta de decisão |
| **Aviso obrigatório** | ✅ o sistema **não** é diagnóstico, prescrição ou substituto de avaliação profissional |
| **DPIA/RIPD** | ⏳ necessária se houver dados reais |

### 10.3 Aviso final

> ⚠️ **O sistema CardioIA, em seu estado atual, opera exclusivamente com dados sintéticos e não
> possui validação clínica.** Nenhuma decisão do sistema constitui diagnóstico, prescrição ou
> recomendação médica. O uso com dados reais de pacientes exigirá: base legal, consentimento,
> criptografia em repouso e em trânsito, política de retenção, controle de acesso auditável, DPIA e
> validação clínica formal.

---

*Plano de segurança da Fase 7. Nenhum valor de credencial é reproduzido neste documento. Nenhum
arquivo das Fases 1 a 6 foi alterado nesta etapa.*