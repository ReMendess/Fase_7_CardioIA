# CardioIA — app mobile (Fase 7)

Aplicativo **React Native + Expo** da plataforma CardioIA. Consome o backend central da
Fase 7 e entrega o fluxo exigido: **login** → **indicadores cardíacos** → **assistente**.

> **De onde veio.** A base é o app da **Fase 5** (`Fase5_CardioAssist/CardioAssist`), que
> tinha apenas a tela de chat. Ele foi **copiado** para cá e ampliado — a Fase 5 permanece
> intacta. É o mesmo padrão do `frontend/` e do `backend/`.

---

## 1. Telas

| Tela | O que faz | Endpoints |
|---|---|---|
| **Login** | autentica e confirma a sessão | `POST /auth/login`, `GET /auth/me`, `GET /health` |
| **Indicadores** | paciente em foco, risco de pico, sinais vitais e qualidade da resposta | `GET /pacientes`, `GET /avaliacoes`, `GET /avaliacoes/{id}`, `GET /iot/leituras` |
| **Assistente** | chat com o assistente | `POST /chat` |

A navegação é por **estado local** (duas abas), sem biblioteca de rotas: são poucas telas e
isso evita mais uma dependência.

---

## 2. Requisitos

| Item | Versão |
|---|---|
| Node.js | 20 ou 22 LTS |
| Expo SDK | 57 (`expo ~57.0.20`, React Native 0.86) |
| Conta Expo | necessária **apenas** para o build na nuvem (EAS) |

**Uma dependência nova** em relação ao app da Fase 5: `react-native-safe-area-context` — e
o motivo está em §6. As demais são as mesmas: `expo`, `expo-constants`, `expo-status-bar`,
`react`, `react-dom`, `react-native`, `react-native-web`.

---

## 3. Rodar em desenvolvimento

```powershell
cd mobile
npm install
npx expo start
```

O app descobre o backend sozinho:

| Ambiente | URL usada |
|---|---|
| Emulador Android | `http://10.0.2.2:8000/api/v1` |
| Celular físico | `http://<IP-da-máquina>:8000/api/v1` (host do Metro) |
| Web | `http://localhost:8000/api/v1` |

Para apontar para outro endereço (o backend publicado, por exemplo), crie um `.env`:

```
EXPO_PUBLIC_API_URL=https://cardioia-backend.onrender.com/api/v1
```

> ⚠️ O backend precisa estar no ar e com a origem liberada no CORS. Em celular físico, o
> aparelho e o computador têm de estar na **mesma rede**.

---

## 4. Gerar o APK (EAS Build)

### 4.1 Configuração já pronta

| Arquivo | O que define |
|---|---|
| `app.json` | `android.package = br.com.fiap.cardioiarenan` e `ios.bundleIdentifier` |
| `eas.json` | perfil **`preview`** com `buildType: "apk"` |

> ⚠️ **O identificador é tudo minúsculo** (`cardioiarenan`). O Android exige *application
> ID* em minúsculas — o Google Play rejeita maiúsculas, e o `expo prebuild` gera caminhos
> de pasta a partir dele, o que quebra em sistemas de arquivos sensíveis a maiúsculas.

### 4.2 O endereço do backend já está fixado

O perfil `preview` define `EXPO_PUBLIC_API_URL` no **próprio `eas.json`**:

```json
"env": { "EXPO_PUBLIC_API_URL": "https://cardioia-backend-z8pz.onrender.com/api/v1" }
```

Isso é proposital. Sem essa variável, o app cairia no padrão `http://10.0.2.2:8000` — que é o
alias do **emulador** para a máquina host. Num celular real esse endereço não existe, e o
APK instalaria, abriria e falharia no login **sem dizer por quê**. Fixar no `eas.json` torna
o build determinístico: o APK sai com o endereço certo mesmo que ninguém crie um `.env`.

> ⚠️ Se o serviço do Render for recriado com outro nome, atualize a URL aqui **e** o
> `VITE_API_URL` da Vercel. São dois clientes, um backend só.

> ℹ️ **O APK não depende de CORS.** CORS é um mecanismo do navegador: um app nativo não envia
> `Origin` nem é bloqueado por ele. A Vercel precisa do domínio em `CORS_ORIGENS`; o APK não.

### 4.3 Comandos

```powershell
cd mobile
npm install
npx eas-cli login          # conta Expo gratuita — passo INTERATIVO
npx eas-cli build --platform android --profile preview
```

Na primeira execução o EAS pergunta se pode **criar o projeto** (o `extra.eas.projectId`
ainda não existe no `app.json`) — responda que sim. Ao final ele devolve um **link** e um
**QR Code** para baixar o `.apk`.

> ℹ️ **Por que na nuvem e não local:** o build local exige **JDK 17** e o Android SDK com
> `ANDROID_HOME`. O EAS compila nos servidores da Expo e devolve o artefato — não é preciso
> toolchain de Android na máquina.

### 4.4 Instalar no aparelho

1. Abra o link (ou leia o QR Code) no celular Android.
2. Autorize a instalação de fontes desconhecidas quando o sistema pedir.
3. Abra o app e entre com a conta de demonstração.

> ℹ️ O `buildType: "apk"` é o que gera um arquivo **instalável direto**. O perfil
> `production` gera `aab` (formato da Play Store), que **não** instala por download.

---

## 5. Conta de demonstração

O backend semeia esta conta no startup quando o banco está vazio:

| Campo | Valor |
|---|---|
| E-mail | `teste` |
| Senha | `senhaTeste23@` |
| Papel | `MEDICO` |

> O papel `MEDICO` é necessário: cadastrar paciente, registrar avaliação e analisar imagem
> exigem esse papel. `ADMIN` e `OPERADOR` recebem `403` nessas rotas.

---

## 6. Estrutura

```text
mobile/
├── app.json                  # android.package em dominio invertido
├── eas.json                  # perfil preview -> APK
├── App.js                    # login -> (indicadores | assistente)
├── .env.example              # EXPO_PUBLIC_API_URL
└── src/
    ├── api/
    │   ├── configuracao.js   # descoberta da URL do backend
    │   ├── cliente.js        # envelope, erros por codigo, JWT, refresh
    │   └── endpoints.js      # uma funcao por rota usada
    ├── contexts/
    │   └── AuthContext.js    # login / me / logout
    ├── screens/
    │   ├── LoginScreen.js
    │   ├── IndicadoresScreen.js
    │   └── ChatScreen.js
    ├── components/           # herdados da Fase 5 (bolhas, input, banners)
    └── theme.js              # paleta, tipografia e espacamentos
```

### Decisões que importam

- **A camada de API é a mesma do frontend web** — mesmo envelope, mesmos códigos de erro,
  mesmo tratamento de `401` com renovação. Um contrato, dois clientes.
- **A sessão vive em memória.** O app não persiste token entre aberturas: em um MVP
  acadêmico isso é suficiente e evita guardar credencial no aparelho.
- **O `session_id` do provedor nunca chega ao app** (achado I8): o identificador da
  conversa é o `id_conversa`, gerado pelo backend.
- **A classificação de risco não é recalculada.** O backend decide
  `sem_pico_de_risco` / `pico_de_risco`; a tela só exibe.
- **A telemetria não é vinculada a paciente** no contrato §4.2 — a tela marca os sinais
  vitais como sendo do **dispositivo**.
- **O recuo das barras do sistema vem do `react-native-safe-area-context`.** No Android, o
  `SafeAreaView` do `react-native` é **literalmente um `View`** — a implementação é
  `Platform.select({ ios: <nativo>, default: View })`. Isso passou a importar quando o
  edge-to-edge virou obrigatório: o SDK 57 avisa que *"Android 16 makes edge-to-edge
  mandatory"* e **não aceita desligar**. Com o app desenhando atrás das barras, o cabeçalho
  caía sob a barra de status e a barra de abas sob a de navegação — e **essas regiões
  pertencem ao sistema, que não repassa toque ao app**. O sintoma era não conseguir sair nem
  trocar de aba. É a única dependência acrescentada, e ela existe por isso.

---

## 7. Problemas comuns

| Sintoma | Causa provável |
|---|---|
| "Nao foi possivel falar com o backend" | backend fora do ar, ou `EXPO_PUBLIC_API_URL` errado |
| Login funciona na web mas não no celular | celular e PC em redes diferentes, ou firewall bloqueando a porta 8000 |
| `403` ao cadastrar paciente | a conta entrou com papel `ADMIN` ou `OPERADOR` — use a conta `MEDICO` |
| Build do EAS falha por `package` inválido | maiúscula no `android.package` (o Android exige minúsculas) |
| Dados não carregam após o app ficar aberto muito tempo | a sessão expira em 30 min; o cliente renova sozinho uma vez — se falhar, faça login de novo |
| Conteúdo atrás das barras do sistema, e **"Sair" e as abas não respondem ao toque** | o `SafeAreaView` foi trocado pelo do `react-native`, que no Android é um `View` puro — ver §6 |
