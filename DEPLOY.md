# Deploy — CardioIA Fase 7

Guia para publicar o backend (**Render**), o frontend web (**Vercel**) e o aplicativo
(**Expo / EAS Build**).

> **Nenhuma chave de API é necessária.** O backend usa SQLite, o assistente tem provedor
> local e o pipeline de risco tem modo simulado. Os únicos valores obrigatórios são
> segredos que **você gera** (`JWT_SECRET`, `IOT_DEVICE_KEY`).

---

## 1. Backend no Render

### 1.1 Por que a raiz do repositório (e não `backend/`)

O backend descobre a Fase 6 por **caminho relativo**
(`RAIZ_DA_FASE_7/Fase_6/cardioia_Fase6`). Publicar apenas a pasta `backend/` faria
`POST /avaliacoes` responder `MODELO_INDISPONIVEL`, porque o artefato `.pkl` não estaria lá.

Por isso o `render.yaml` já está configurado com o comando:

```
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 1.2 Passo a passo

1. **Render → New → Blueprint** → aponte para este repositório.
   O Render lê o `render.yaml` e cria o serviço `cardioia-backend`.
2. Aguarde o primeiro build (instala `scikit-learn`, `pandas` e `numpy` — leva alguns
   minutos).
3. Copie a URL pública gerada (ex.: `https://cardioia-backend.onrender.com`).
4. **Preencha `CORS_ORIGENS`** com essa URL da Vercel (passo 2.3). O `render.yaml` deixa
   essa variável em branco de propósito — ela só existe depois do deploy do frontend.

### 1.3 Verificação

```powershell
Invoke-RestMethod https://SEU-SERVICO.onrender.com/api/v1/health
```

Resposta esperada: `status = CONCLUIDO` com `dados.ambiente` e `dados.artefato_do_modelo`.

### 1.4 Conta de demonstração

O plano gratuito tem sistema de arquivos **efêmero**: o SQLite volta vazio a cada
reinício. Para a aplicação continuar acessível, o backend **semeia** a conta abaixo quando
o banco não tem nenhum usuário:

| Campo | Valor |
|---|---|
| E-mail | `teste` |
| Senha | `senhaTeste23@` |
| Papel | `MEDICO` |

É **idempotente**: se já houver qualquer usuário, não faz nada. Para desligar, defina
`SEMEAR_USUARIO_INICIAL=false`.

> ⚠️ O plano gratuito do Render **hiberna** após ~15 minutos sem acesso. A primeira
> requisição depois disso demora ~50 s (o frontend mostra o estado de carregamento).

---

## 2. Frontend web na Vercel

### 2.1 Importar o projeto

1. **Vercel → Add New → Project** → importe este repositório.
2. **Root Directory: `frontend`** ← obrigatório; o repositório é um monorepo.
3. Framework detectado automaticamente: **Vite**. Não altere os comandos.

### 2.2 Variável de ambiente

| Nome | Valor |
|---|---|
| `VITE_API_URL` | `https://SEU-SERVICO.onrender.com/api/v1` |

Sem isso, o build aponta para `127.0.0.1` e a aplicação publicada não carrega dado nenhum.

### 2.3 CI/CD

A integração Git da Vercel já faz o *deploy automático*: **todo push na `main` publica uma
nova versão**. Não é preciso workflow de GitHub Actions.

Cada *preview* ganha um domínio novo (`cardioia-git-branch-usuario.vercel.app`). Para não
ter de cadastrar um por um, o backend aceita `CORS_ORIGEM_REGEX`:

```
CORS_ORIGEM_REGEX=^https://.*\.vercel\.app$
```

### 2.4 O arquivo `vercel.json`

Já existe em `frontend/vercel.json` e resolve o roteamento SPA:

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

Sem ele, abrir `https://SEU-APP.vercel.app/dashboard` direto (ou dar F5 na página) devolve
**404**, porque não existe arquivo físico nesse caminho.

### 2.5 Verificação

1. Abra a URL pública.
2. Entre com `teste` / `senhaTeste23@`.
3. O selo **Backend online** deve aparecer na tela de acesso.
4. O dashboard deve mostrar o risco e os indicadores cardíacos.

> ⚠️ **Use `localhost` no desenvolvimento, não `127.0.0.1`** — o navegador trata os dois
> como origens diferentes. Em produção isso não se aplica (o domínio é único).

---

## 3. Aplicativo (Expo / EAS Build)

Instruções detalhadas em [`mobile/README.md`](mobile/README.md).

Resumo:

```powershell
cd mobile
npm install
npx eas-cli login
npx eas-cli build --platform android --profile preview
```

O perfil `preview` gera um **APK** (não AAB), instalável direto no aparelho. Ao final, o
EAS devolve um link e um QR Code para download.

| Arquivo | O que configura |
|---|---|
| `mobile/app.json` | `android.package` = `br.com.fiap.cardioiarenan` |
| `mobile/eas.json` | perfil `preview` com `buildType: apk` |
| `mobile/.env.example` | `EXPO_PUBLIC_API_URL` → URL do Render |

---

## 4. Checklist de validação

| # | Verificação | Onde |
|---|---|---|
| 1 | `/api/v1/health` responde `CONCLUIDO` | Render |
| 2 | Login funciona na URL pública | Vercel |
| 3 | Dashboard mostra risco e indicadores | Vercel |
| 4 | Avaliação de risco conclui com probabilidade | Vercel |
| 5 | Assistente responde no chat | Vercel |
| 6 | Push na `main` dispara novo deploy | Vercel |
| 7 | APK instala e faz login | Android |
| 8 | Leitura do Wokwi aparece no monitoramento | Wokwi → Render |
| 9 | Monitoramento já tem leituras, **sem** nenhum dispositivo ligado | Vercel |
| 10 | As leituras da tela aparecem marcadas como **"Simulado"** | Vercel |

---

## 5. Problemas comuns

| Sintoma | Causa provável |
|---|---|
| Página abre mas **nenhum dado carrega** | `CORS_ORIGENS` sem o domínio da Vercel, ou `VITE_API_URL` apontando para `127.0.0.1` |
| `404` ao dar F5 numa rota interna | `vercel.json` ausente ou sem os `rewrites` |
| `503 MODELO_INDISPONIVEL` na avaliação | deploy feito a partir de `backend/` em vez da raiz |
| Primeira chamada demora ~50 s | hibernação do plano gratuito do Render |
| Login falha após um tempo sem uso | o Render reiniciou e o banco foi recriado — a conta de demonstração e a telemetria simulada são semeadas de novo automaticamente |
| Monitoramento vazio com o backend no ar | `SEMEAR_TELEMETRIA_SIMULADA=false`, ou já existia leitura real no banco (a semeadura é idempotente e não se mistura com dado de dispositivo) |
| Chat responde `502` | há `WATSON_*` preenchidas apontando para um serviço indisponível — remova-as para usar o provedor local |
