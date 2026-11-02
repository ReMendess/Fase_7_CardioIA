# CardioIA — frontend web (Fase 7 · Etapa D)

Frontend **React + Vite** integrado ao backend central da Fase 7. Substitui o login
simulado e os dados de `jsonplaceholder` do app da Fase 2 por autenticação **JWT** real e
pelos endpoints do contrato `CONTRATOS_API.md` §8.

> ⚠️ **De onde veio este código.** A estrutura visual, o CSS, os assets e o roteamento
> vêm do app da **Fase 2** (`Fase_2/Cap2_Desafio_Integrador/Ir_Alem/my-react-app`). Ele foi
> **copiado** para cá e integrado; **a Fase 2 permanece intacta**. É o mesmo padrão do
> `backend/`, que consome as Fases 3–6 sem modificá-las.

> ⚠️ **Aviso acadêmico.** Os dados do projeto são **sintéticos** e não há validação
> clínica. Nenhum resultado constitui diagnóstico, prescrição ou recomendação médica.

---

## 1. Requisitos

| Item | Versão usada |
|---|---|
| Node.js | 22.17.0 |
| npm | 10.9.2 |
| Backend da Fase 7 | rodando em `http://127.0.0.1:8000` |

**Nenhuma dependência nova foi adicionada.** O app usa apenas `react`, `react-dom` e
`react-router-dom` — as mesmas do app da Fase 2. Não há biblioteca de gráficos: os
indicadores são **barras e medidores em CSS puro**, sobre as variáveis de cor que já
existiam.

---

## 2. Como rodar

### 2.1 Backend (primeiro)

```powershell
cd backend
python -m app.dados.esquema            # cria o esquema

# semeie ao menos um usuario (nao existe endpoint de cadastro — ver §8)
python -c "
from app.config import obter_configuracoes
from app.dados.base import criar_engine, criar_fabrica_de_sessoes
from app.dados.enums import PapelDoUsuario
from app.dados.repositorios.identidade import UsuarioRepositorio
from app.seguranca.senhas import gerar_hash
engine = criar_engine(obter_configuracoes().url_do_banco)
with criar_fabrica_de_sessoes(engine)() as sessao:
    UsuarioRepositorio(sessao).criar(
        nome='Dra. Exemplo', email='medico@exemplo.local',
        senha_hash=gerar_hash('troque-esta-senha'), papel=PapelDoUsuario.MEDICO,
    )
"

$env:JWT_SECRET = python -c "import secrets; print(secrets.token_urlsafe(48))"
python -m uvicorn app.main:app --reload --port 8000
```

> O `IOT_DEVICE_KEY` é opcional: sem ele, a ingestão de telemetria passa a exigir um
> usuário `OPERADOR`.

### 2.2 Frontend

```powershell
cd frontend
npm install
npm run dev            # http://localhost:5173
```

Abra **`http://localhost:5173`** e entre com o usuário semeado.

> ⚠️ **Use `localhost`, não `127.0.0.1`.** O navegador trata os dois como **origens
> diferentes**; o backend já libera as duas no CORS por padrão, mas se você mudar
> `CORS_ORIGENS`, mantenha o host que aparece na barra de endereços.

### 2.3 Build de produção

```powershell
npm run build          # gera dist/
npm run preview        # serve o dist/ localmente
```

---

## 3. Variáveis de ambiente

Copie `.env.example` para `.env.local`:

| Variável | Padrão | Para que |
|---|---|---|
| `VITE_API_URL` | `http://127.0.0.1:8000/api/v1` | URL base da API (inclui o prefixo `/api/v1`) |

🔒 **Nenhuma credencial vive no código.** O que fica no `localStorage` é o par de tokens
emitido pelo backend (`cardioia.sessao`); a senha nunca é armazenada.

---

## 4. Telas

| Rota | Tela | O que mostra |
|---|---|---|
| `/` | **Acesso** | login real, estado do backend (`GET /health`) e o aviso acadêmico |
| `/dashboard` | **Visão geral** | risco do paciente em foco, resumo, indicadores do dispositivo, avisos e limitações |
| `/pacientes` | **Pacientes** | lista, cadastro (só `MEDICO`), seleção do paciente em foco |
| `/avaliacao` | **Avaliação** | formulário das **10 features**, modo `simulado`/`real`, resultado com protocolos e trilha |
| `/historico` | **Histórico** | lista de execuções e o detalhe auditável (resposta persistida da Fase 6) |
| `/monitoramento` | **Monitoramento** | leituras dos dispositivos |
| `/assistente` | **Assistente** | chat (Watson), com os estados `501` e `403` explicados |
| `/agenda` | **Agenda** | ⚠️ **demonstrativa** — não existe endpoint de agenda no contrato |

### Densidade da informação

Princípio que orienta as telas: **o dado primeiro, a ressalva a um clique.**

| Elemento | Como aparece | Por quê |
|---|---|---|
| Avisos do envelope | `<details>` recolhido, com a contagem | o contrato exige que **existam** na resposta, não que ocupem a tela |
| Limitações declaradas | `<details>` recolhido | idem |
| Narrativa, justificativas e trilha do pipeline | `<details>` recolhido | texto de auditoria, não de leitura clínica |
| Detalhes do modelo (limiar, regra, estimador) | `<details>` recolhido | contexto técnico |
| Protocolos e indicadores deterministas | **visíveis** | é o conteúdo acionável da resposta |
| Risco e sinais vitais | **visíveis** | é o motivo de a tela existir |

Três ajustes acompanham esse princípio:

- **Selos de origem removidos.** Cada bloco trazia um selo "Dado da API" / "Resultado
  preditivo". A informação continua no README e em `CONTRATOS_API.md`; na tela, o rótulo da
  própria seção já diz de onde vem o número. Repetir o selo em cada painel era ruído.
- **A origem do transporte permanece visível** (`REST`, `MQTT`, `Simulado`) no Dashboard e
  no Monitoramento. Diferente do selo anterior, esta **muda a leitura do número**: uma
  leitura semeada para demonstração chega com `origem_transporte = "simulado"` e não pode
  ser lida como medição de dispositivo real (ver `backend/README.md`).
- **Sinais de escala e confiança das features** (8 das 10 não são medições individuais do
  paciente) passaram para o **tooltip** do cartão. O selo `fora da faixa` permanece visível,
  porque esse muda a leitura do número.

---

## 5. Endpoints consumidos

| Método | Rota | Onde na interface |
|---|---|---|
| `GET` | `/health` | selo "Backend online" no acesso e no dashboard |
| `POST` | `/auth/login` | tela de acesso |
| `POST` | `/auth/refresh` | **transparente** — o cliente renova em `401` e repete a chamada |
| `POST` | `/auth/logout` | botão "Sair" |
| `GET` | `/auth/me` | valida a sessão ao abrir o app |
| `GET` `POST` | `/pacientes` | lista e cadastro |
| `GET` | `/pacientes/{id}` | disponível no cliente; a tela usa a lista |
| `POST` | `/avaliacoes` | formulário de avaliação |
| `GET` | `/avaliacoes` | dashboard e histórico |
| `GET` | `/avaliacoes/{id}` | detalhe do histórico |
| `GET` | `/iot/leituras` | indicadores cardíacos e monitoramento |
| `POST` | `/chat` | assistente |
| `GET` | `/conversas/{id}` | botão "Recarregar histórico" do assistente |
| `POST` | `/imagens` | cliente pronto; **sem tela** (ver §7) |

**Não consumido:** `POST /iot/leituras`. A interface **não** ingere telemetria — quem
ingere é o dispositivo (firmware da Fase 3 / `IoT/main.py`). O `curl` de exemplo está em
`IoT/README.md` §7.1.

---

## 6. Estrutura

```text
frontend/
├── .env.example                 # VITE_API_URL (SEM valores reais)
├── index.html                   # titulo e meta description do CardioIA
├── vite.config.js               # herdado da Fase 2
├── scripts/
│   └── smoke.mjs                # smoke test contra o backend real (item 5)
└── src/
    ├── api/
    │   ├── configuracao.js      # URL da API centralizada (funciona em Vite E em Node)
    │   ├── cliente.js           # envelope, erros por codigo, JWT, refresh automatico
    │   └── endpoints.js         # uma funcao por rota do contrato §8
    ├── contexts/
    │   ├── AuthContext.jsx      # login/me/refresh/logout REAIS + persistencia
    │   └── PacienteContext.jsx  # paciente em foco, compartilhado entre as telas
    ├── components/
    │   ├── ProtectedRoute.jsx   # exige sessao confirmada
    │   ├── Estado.jsx           # carregando · falha · vazio · avisos · limitacoes
    │   ├── Indicador.jsx        # barra de feature (faixa do contrato)
    │   ├── NivelDeRisco.jsx     # medidor de risco (classificacao vem do BACKEND)
    │   ├── ResultadoDaAvaliacao.jsx  # contrato da Fase 6: protocolos, trilha, narrativa
    │   ├── SeletorDePaciente.jsx
    │   └── JanelaDoChat.jsx
    ├── dominio/
    │   └── catalogo.js          # rotulos, faixas e enums (valores do BACKEND)
    ├── pages/                   # Login, Dashboard, Pacientes, Avaliacao,
    │                            # Historico, Monitoramento, Assistente, Agenda
    ├── App.jsx                  # rotas + provedores
    ├── App.css                  # design system da Fase 2 + acrescimos da Etapa D
    └── index.css                # herdado da Fase 2
```

### Decisões que importam

- **O cliente HTTP não toca em `localStorage`.** Ele guarda os tokens em memória e recebe
  o par por parâmetro; quem persiste é o `AuthContext`. Isso mantém uma única fonte de
  verdade **e** permite executar a mesma camada em Node — é o que o smoke test faz.
- **A classificação de risco não é recalculada aqui.** O backend decide
  `sem_pico_de_risco` / `pico_de_risco` com o limiar do próprio modelo; a tela só exibe.
  Recalcular criaria uma segunda fonte de verdade clínica.
- **As regras da Fase 3 não são reimplementadas.** Os alertas (`FEBRE DETECTADA`,
  `TAQUICARDIA DETECTADA`) chegam prontos em `avisos` na resposta da ingestão.
- **O `session_id` do Watson nunca aparece.** O identificador exposto é o `id_conversa`.

---

## 7. RBAC — o que cada papel vê

A interface **reflete** o que o backend permite; ela não decide nada. O backend continua
sendo a autoridade (todo `403` é dele).

| Recurso | `MEDICO` | `OPERADOR` | `ADMIN` |
|---|---|---|---|
| Ler paciente / avaliação | ✅ | ❌ `403` | ✅ |
| Cadastrar paciente | ✅ | ❌ `403` | ❌ `403` |
| Registrar avaliação | ✅ | ❌ `403` | ❌ `403` |
| Ler telemetria IoT | ✅ | ✅ | ❌ `403` |
| Assistente (`/chat`) | ✅ | ✅ | ❌ `403` |
| Analisar imagem (`/imagens`) | ✅ | ❌ `403` | ❌ `403` |

> ⚠️ **`ADMIN` não é superusuário.** Ele lê dados clínicos, mas não escreve nem usa o
> assistente — a tela explica isso em vez de esconder o item de menu.

---

## 8. O que **não** está disponível (e a interface diz isso)

| Situação | Como aparece na tela |
|---|---|
| **Sem usuário cadastrado** | não existe `POST /usuarios`; a tela de acesso aponta o procedimento manual (§2.1) |
| **Watson não configurado** | `501 NAO_CONFIGURADO` — a tela explica que o backend lê **só** do ambiente e não usa os defaults do `IBM_API.py` da Fase 5 |
| **Serviço da Fase 4 fora do ar** | `502` — a tela informa que o serviço exige TensorFlow e roda em processo separado |
| **Modo `real` sem `OPENAI_API_KEY`** | `501` — a tela explica que o modo real exige a chave |
| **Valores das features avaliadas** | a API devolve só os **nomes** (`diagnostico.features_utilizadas`); a tela mostra os nomes e diz que os valores não são expostos |
| **Telemetria por paciente** | o contrato §4.2 não vincula leitura a paciente; a tela marca os números como **do dispositivo** |
| **Agenda** | não há endpoint; a tela é rotulada **demonstrativa** |
| **Upload de imagem** | o cliente está pronto (`analisarImagem`), mas não há tela — o serviço não é executável neste ambiente |

---

## 9. Validação executada

| Verificação | Comando | Resultado |
|---|---|---|
| Lint | `npm run lint` | **0 erros, 0 avisos** |
| Build de produção | `npm run build` | 46 módulos, ~2,9 s, sem avisos |
| Smoke contra o backend real | `npm run smoke` | ver abaixo |
| Servidor de desenvolvimento | `npm run dev` | HTTP 200 em `/` |

### Smoke test (`scripts/smoke.mjs`)

Exercita **a mesma camada de API que a interface usa** (`src/api/`) contra o backend real
— não é um mock. Se o envelope mudar de forma, ele quebra.

```powershell
# com o backend no ar
$env:SMOKE_EMAIL="medico@exemplo.local"; $env:SMOKE_SENHA="..."
npm run smoke
```

Cobre 11 seções: health, JWT, credencial inválida, pacientes, capacidades do papel,
avaliação (pipeline real da Fase 6), histórico, telemetria, assistente, visão e logout.

**Resultados obtidos:**

| Papel | Verificações |
|---|---|
| `MEDICO` | **33/33** |
| `OPERADOR` | **23/23** |
| `ADMIN` | **19/19** |

> As contagens diferem porque o script só executa o que o papel **pode** fazer e verifica
> `403` no que ele **não** pode — é uma matriz de RBAC, não uma lista fixa.

**Cenário de backend fora do ar:** com o servidor parado, o script aborta no primeiro
passo com mensagem acionável (`Nao foi possivel falar com o backend. Confirme que a API da
Fase 7 esta no ar em <URL>`), em vez de estourar um erro cru.

---

## 10. O que mudou em relação ao app da Fase 2

### Removido (e por quê)

| Arquivo | Motivo |
|---|---|
| `src/contexts/AuthContext.jsx` (original) | fazia login **simulado no cliente** (`admin@email.com`/`123`) — reescrito |
| `src/services/api.js` | chamava `jsonplaceholder.typicode.com` — substituído por `src/api/` |
| `src/hooks-examples/PainelLogin.jsx` | exibia a dica de credenciais falsas na tela de acesso |
| `src/hooks-examples/AreaRestrita.jsx` | material didático do Cap. 2; não é funcionalidade do app |
| `src/pages/Login.jsx` (original) | era **órfão** (nenhuma rota o usava) e chamava `login(email)` sem senha |
| `src/pages/Dashboard.jsx` · `Patients.jsx` | liam do jsonplaceholder; indicador "Consultas agendadas: 5" era **fixo no código** |

### Criado

`src/api/{configuracao,cliente,endpoints}.js` · `src/dominio/catalogo.js` ·
`src/components/{Estado,Indicador,NivelDeRisco,ResultadoDaAvaliacao,SeletorDePaciente,JanelaDoChat}.jsx` ·
`src/contexts/PacienteContext.jsx` · `src/pages/{Login,Dashboard,Pacientes,Avaliacao,Historico,Monitoramento,Assistente,Agenda}.jsx` ·
`scripts/smoke.mjs` · `.env.example`

### Mantido

`index.css` e `App.css` (design system), os assets, `vite.config.js`, `eslint.config.js`,
`main.jsx`, o roteamento por `react-router-dom`, o layout em painéis, os "pills" e o
comportamento responsivo (`880px`). `Schedule.jsx` virou `Agenda.jsx`, agora rotulada como
demonstrativa.

> **Sobre o lint:** a regra `react-refresh/only-export-components` fica **desligada** em
> `AuthContext.jsx` e `PacienteContext.jsx`, com justificativa no próprio arquivo. Ela
> exige que um arquivo exporte só componentes (por causa do HMR); o padrão
> contexto + hook + provedor no mesmo arquivo é o que a documentação do React mostra.

---

## 11. Pendências para deploy (ainda **não** iniciado)

A Vercel e o EAS Build **não foram configurados** — por instrução, primeiro se conclui e
valida a integração local.

| # | Pendência | Observação |
|---|---|---|
| 1 | **CORS em produção** | `CORS_ORIGENS` precisa receber o domínio da Vercel; hoje lista só origens locais |
| 2 | **`VITE_API_URL` em produção** | aponta para `127.0.0.1`; precisa da URL pública do backend |
| 3 | **Token em `localStorage`** | o backend não usa cookie, então o header `Authorization` é o caminho; `localStorage` é o padrão do app herdado. Migrar para memória + refresh silencioso reduz o impacto de XSS |
| 4 | **Backend em produção** | o MVP assume SQLite local; publicar exige decidir hospedagem e banco |
| 5 | **Tela de imagem** | o cliente (`analisarImagem`) está pronto, mas não há tela — depende do serviço da Fase 4 no ar |
| 6 | **Valores das features no histórico** | o contrato não expõe os valores avaliados; se o dashboard precisar deles, é preciso um campo novo na resposta de `GET /avaliacoes/{id}` |
| 7 | **Vite proxy (alternativa ao CORS)** | configurar `server.proxy` no `vite.config.js` eliminaria o CORS no desenvolvimento — não foi feito para não alterar o arquivo herdado sem necessidade |
| 8 | **Rotação da chave do Watson** | pendência do backend (`PLANO_SEGURANCA.md`, C1); não afeta o frontend |



