# CardioIA — Fase 7

MVP final e funcional da plataforma **CardioIA**: um ecossistema que vai do **sinal captado
no dispositivo** até a **recomendação clínica exibida na interface**, integrando os módulos
desenvolvidos nas fases anteriores sob um contrato único.

> ⚠️ **Aviso acadêmico.** Os dados do projeto são **sintéticos** e não há validação clínica.
> Nenhum resultado constitui diagnóstico, prescrição ou recomendação médica.

---

## 1. Links da entrega

| Item | Endereço |
|---|---|
| **Aplicação Web (Vercel)** | _preencher após o deploy_ → ver [`DEPLOY.md`](DEPLOY.md) §2 |
| **Backend (Render)** | _preencher após o deploy_ → ver [`DEPLOY.md`](DEPLOY.md) §1 |
| **APK (Expo / EAS)** | _preencher com o link ou QR Code_ → ver [`DEPLOY.md`](DEPLOY.md) §3 |
| **Projeto Wokwi (MicroPython)** | _preencher com o link público_ → ver [`IoT/README.md`](IoT/README.md) §6 |
| **Relatório técnico (PDF)** | [`docs/RELATORIO_FASE7.html`](docs/RELATORIO_FASE7.html) → imprimir em PDF |

> Os campos acima são preenchidos **após** a execução do `DEPLOY.md`. Nenhum deles exige
> chave de API — veja a seção 3.

### Conta de demonstração

| Campo | Valor |
|---|---|
| E-mail | `teste` |
| Senha | `senhaTeste23@` |
| Papel | `MEDICO` |

---

## 2. Arquitetura final

```
  ┌──────────────────┐
  │  SENSOR          │  DHT22 (temperatura) + botão (BPM simulado)
  │  ESP32 / Wokwi   │
  └────────┬─────────┘
           │
  ┌────────▼─────────┐
  │  MICROPYTHON     │  avalia os sinais NA BORDA  ->  OLED + LED
  │  IoT/main.py     │  (38 °C / 120 bpm, os mesmos limiares do backend)
  └────────┬─────────┘
           │  HTTP POST  /api/v1/iot/leituras   (X-Device-Key)
  ┌────────▼─────────────────────────────────────────┐
  │  BACKEND PYTHON  (FastAPI)                       │
  │  ┌────────────┬────────────┬────────────┐        │
  │  │ Fase 3     │ Fase 4     │ Fase 5     │ Fase 6 │
  │  │ regras IoT │ visão      │ assistente │ risco  │
  │  └────────────┴────────────┴────────────┴────────┘
  │  auth JWT · RBAC · SQLite · auditoria · envelope │
  └────────┬──────────────────────────────┬──────────┘
           │  JSON (RespostaAPI[T])       │
  ┌────────▼─────────┐          ┌─────────▼──────────┐
  │  UI WEB          │          │  UI MOBILE         │
  │  React + Vite    │          │  React Native/Expo │
  │  (Vercel)        │          │  (APK via EAS)     │
  └──────────────────┘          └────────────────────┘
```

| Camada | Tecnologia | Onde |
|---|---|---|
| Sensor | ESP32 simulado no Wokwi (DHT22 + botão) | `IoT/` |
| Borda | **MicroPython** — avalia e sinaliza localmente | `IoT/main.py` |
| Integrador | **Python / FastAPI** — orquestra todos os módulos | `backend/` |
| IA | Fase 6 (modelo de risco) · Fase 5 (assistente) · Fase 4 (visão) | `backend/app/integracao/` |
| UI Web | React + Vite | `frontend/` |
| UI Mobile | React Native + Expo | `mobile/` |

---

## 3. Nenhuma chave de API

O projeto **não depende de nenhum serviço de terceiro com credencial**. O que normalmente
exigiria uma conta foi resolvido por um provedor equivalente dentro do próprio projeto:

| O que exigiria credencial | Como está resolvido |
|---|---|
| **IBM Watson Assistant** (Fase 5) | **Provedor local** — responde da base de conhecimento do projeto, em Python puro. O adaptador do Watson continua disponível e é usado quando configurado |
| **OpenAI** (pipeline da Fase 6) | **Modo simulado** (padrão): o pipeline executa com o modelo treinado, sem provedor de linguagem |
| **TensorFlow / serviço da Fase 4** | O endpoint existe e responde `502` quando o serviço não está no ar; a UI não o expõe |
| **Broker MQTT (HiveMQ)** | O dispositivo envia por **HTTP direto** ao backend |
| **SMTP** (Fase 3) | Fora de escopo |
| **Banco gerenciado** | **SQLite** no próprio serviço, com a conta de demonstração semeada no startup |

Os únicos valores obrigatórios são segredos que **você gera** no deploy: `JWT_SECRET` e
`IOT_DEVICE_KEY`.

---

## 4. Como executar localmente

### 4.1 Backend

```powershell
cd backend
python -m pip install -r requirements.txt
python -m app.dados.esquema          # cria o esquema

$env:JWT_SECRET = python -c "import secrets; print(secrets.token_urlsafe(48))"
python -m uvicorn app.main:app --reload --port 8000
```

A **conta de demonstração é criada automaticamente** no primeiro boot. Verificação:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Documentação interativa da API: `http://127.0.0.1:8000/docs`

### 4.2 Frontend web

```powershell
cd frontend
npm install
npm run dev            # http://localhost:5173
```

### 4.3 App mobile

```powershell
cd mobile
npm install
npx expo start
```

### 4.4 Firmware (Wokwi)

Abra o projeto no Wokwi e substitua `main.py` e `diagram.json` pelos arquivos de `IoT/`.
Instruções completas em [`IoT/README.md`](IoT/README.md).

---

## 5. Estrutura do repositório

```text
Fase_7/
├── backend/     FastAPI — o integrador em Python (636 testes)
├── frontend/    React + Vite — aplicação web            → Vercel
├── mobile/      React Native + Expo — aplicativo        → APK (EAS)
├── IoT/         MicroPython + circuito Wokwi            → link público
├── docs/        Relatório técnico (imprimir em PDF)
├── Fase_1…6/    módulos das fases anteriores (sanitizados)
├── render.yaml  blueprint do backend no Render
├── DEPLOY.md    guia de publicação, passo a passo
├── CONTRATOS_API.md · MODELO_DADOS.md · DECISOES_ARQUITETURAIS.md
├── PLANO_SEGURANCA.md · ANALISE_ARQUITETURA.md · PROGRESSO_FASE7.md
└── README.md
```

---

## 6. Entregáveis × requisitos do enunciado

| # | Requisito | Onde | Estado |
|---|---|---|---|
| 1 | Web publicada na Vercel, com CI/CD | `frontend/vercel.json` + `DEPLOY.md` §2 | ⬜ publicar |
| 2 | `vercel.json` com rotas SPA | `frontend/vercel.json` | ✅ |
| 3 | `app.json` com `android.package` em domínio invertido | `mobile/app.json` → `br.com.fiap.cardioiarenan` | ✅ |
| 4 | `eas.json` com perfil `preview` | `mobile/eas.json` | ✅ |
| 5 | `.apk` funcional | `npm run build:apk` em `mobile/` | ⬜ buildar |
| 6 | Repositório privado compartilhado com o tutor | GitHub `ReMendess/Fase_7_CardioIA` | ⬜ conceder acesso |
| 7 | Pasta `Backend/` com os scripts Python de integração | `backend/` | ✅ |
| 8 | Pasta `IoT/` com o script `.py` MicroPython | `IoT/main.py` | ✅ |
| 9 | Projeto Wokwi público em MicroPython com LED/OLED | `IoT/diagram.json` | ⬜ publicar |
| 10 | `README.md` com URL, QR do APK, prints e instruções | este arquivo + `DEPLOY.md` | ⬜ preencher |
| 11 | Relatório técnico PDF (≤ 5 páginas) com o diagrama | `docs/RELATORIO_FASE7.html` | ✅ imprimir |
| 12 | Refino de UX dos indicadores de risco | `frontend/` + `mobile/` | ✅ |
| 13 | Validação do login e dos dados cardíacos | `frontend/` · `mobile/` · `IoT/` | ✅ local |

> **Legenda:** ✅ pronto no repositório · ⬜ depende de uma ação de publicação (não exige
> código).

---

## 7. Validação

| Verificação | Comando | Resultado |
|---|---|---|
| Suíte do backend | `cd backend && python -m pytest` | **636 testes** |
| Lint do frontend | `cd frontend && npm run lint` | 0 erros, 0 avisos |
| Build do frontend | `cd frontend && npm run build` | 46 módulos |
| Smoke da integração | `cd frontend && npm run smoke` | 65 verificações (3 papéis) |
| Bundle do app | `cd mobile && npx expo export --platform web` | 219 módulos, 413 KB |
| Sintaxe do firmware | `python -c "import ast; ast.parse(open('IoT/main.py').read())"` | OK |

O **smoke test** exercita a mesma camada de API que a interface usa, contra o backend real —
não é um mock. Ele cobre health, JWT, credencial inválida, pacientes, RBAC por papel,
avaliação de risco (pipeline real da Fase 6), histórico, telemetria, assistente, visão e
logout.

---

## 8. Documentação

| Documento | Conteúdo |
|---|---|
| [`DEPLOY.md`](DEPLOY.md) | publicação no Render, Vercel e EAS + checklist |
| [`docs/RELATORIO_FASE7.html`](docs/RELATORIO_FASE7.html) | relatório técnico (imprimir em PDF) |
| [`CONTRATOS_API.md`](CONTRATOS_API.md) | envelope, códigos de erro e rotas do MVP |
| [`MODELO_DADOS.md`](MODELO_DADOS.md) | tabelas, tipos e decisões de persistência |
| [`DECISOES_ARQUITETURAIS.md`](DECISOES_ARQUITETURAIS.md) | as 6 decisões da Etapa B |
| [`PLANO_SEGURANCA.md`](PLANO_SEGURANCA.md) | achados, correções e estado das credenciais |
| [`PROGRESSO_FASE7.md`](PROGRESSO_FASE7.md) | registro de progresso por etapa |
| [`backend/README.md`](backend/README.md) | o backend em detalhe |
| [`frontend/README.md`](frontend/README.md) | a aplicação web em detalhe |
| [`mobile/README.md`](mobile/README.md) | o aplicativo em detalhe |
| [`IoT/README.md`](IoT/README.md) | o firmware e o circuito em detalhe |

