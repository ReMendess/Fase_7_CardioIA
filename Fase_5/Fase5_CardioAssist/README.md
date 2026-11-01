# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href= "https://www.fiap.com.br/"><img src="assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Admnistração Paulista" border="0" width=40% height=40%></a>
</p>

<br>

# Fase 5 - Assistente Cardiológico Inteligente: Experiência do Paciente

## Autor: 
- <a href="https://www.linkedin.com/in/renanmendes26/">Renan de Oliveira Mendes - RM563145</a>

# CardioAssist — Chat com IBM Watson Assistant

O **CardioAssist** é um assistente virtual  para orientação inicial sobre saúde cardiovascular, construído com:

- **Backend Python (Flask)** em `Backend/` — integra a API do **IBM watsonx Assistant v2**.
- **App mobile em React Native / Expo** em `CardioAssist/` — interface de chat simples, moderna e responsiva, com estado de carregamento, indicador de digitação, sugestões rápidas e tratamento de erros.


# Descrição

Nessa quinta fase desenvolvemos um assistente conversacional, usando a estrutura do IBM Watson. Utilizando ferramentas de NLU, entitys, actions e skills nosso assistente consegue entender linguagem humana e prover ajuda customizada ao usuário.


Criamos uma interface interativa com React Native, disponibilizando o agente  de forma responsiva atráves de um app, mas também podendo ser utilizado via web.

### Link Videos:
#### Parte 1 e Parte 2: https://youtu.be/t3lXi1qCfM4

# Parte 1

Conforme requisitado, na primeira etapa do projeto criamos e desenvolvemos todo o assistente virtual dentro do IBM Watsonx. Modelamos as entidades, ações e fluxos conversacionais.


<img src="/assets/Watsonx.png" widht="150">

<img src="/assets/editor.png" widht="150">

<img src="/assets/Dor no peito.png" widht="150">

Utilizando variáveis, regras de condições e modelos de textos, foi possível criar um assistente que consegue entender, analisar e sugerir ações para o usuário.

<img src="/assets/chat.png" widht="150">

<img src="/assets/chat2.png" widht="150">

# Parte 2

Após testar e validar o assistente mergulhamos em como aprofundar a experiência do usuário com o chatbot.
Criamos então um aplicativo mobile com React Native e Expo para distribuição.

Estruturamos o backend com Flask, criando uma porta de comunicação com o serviço da IBM Watson criado e disponibilizando através de APIs formas de comunicação com o assistente.

Em seguida criamos o app, que consome o serviço do backend para uma interface amigável e simples. Também incluimos icónes, tratamentos de erros, logs e alertas para uma melhor experiência do usuário.

<img src="/assets/cardio_cel.png" widht="60">

<img src="/assets/cardio_web.png" widht="150">

### Como executar

#### 1. Backend (API Flask)

```powershell
Dentro da pasta Backend
pip install -r requirements.txt
python app.py
```

O servidor sobe em `http://localhost:5000`.

- `GET  /health` → estado do serviço e da configuração com Watson.
- `POST /api/chat` → envio de mensagem: `{ "message": "...", "session_id": "..." }`.

As credenciais do Watson ficam em `Backend/IBM_API.py` e podem ser sobrescritas no arquivo `.env` (veja `Backend/.env.example`).

#### 2. App (Expo)

```powershell
Dentro da pasta CardioAssist
npm install
npx expo start
```

| Ambiente | URL do backend |
|---|---|
| Web / iOS simulador | `http://localhost:5000` (automático) |
| Emulador Android | `http://10.0.2.2:5000` (fallback automático) |
| Celular físico | `http://<IP-da-máquina>:5000` (**detectado automaticamente** pelo host do Metro) |

O app detecta o IP do servidor do Expo (`exp://...`) e usa a mesma máquina na porta `5000`, então em **celular físico não é preciso configurar nada**. Se precisar sobrescrever manualmente (ex.: backend em outra máquina), crie um `.env` na raiz do app:


>  **Dica de firewall**: se o celular não conectar, libere a porta 5000 no Windows:
> ```powershell
> netsh advfirewall firewall add rule name="CardioAssist 5000" dir=in action=allow protocol=TCP localport=5000


### Estrutura

```
Fase5_CardioAssist/
├── Backend/
│   ├── app.py           # API Flask (GET /health e POST /api/chat)
│   ├── IBM_API.py       # Cliente e credenciais do IBM Watson Assistant
│   ├── requirements.txt
│   └── .env.example     # Modelo para sobrescrever credenciais
└── CardioAssist/        # App Expo (React Native)
    ├── App.js
    ├── .env.example     # Modelo para EXPO_PUBLIC_API_URL
    └── src/
        ├── constants/api.js       # Detecção da URL do backend
        ├── services/watsonApi.js  # Chamadas HTTP com timeout e erros amigáveis
        ├── theme.js               # Paleta, tipografia e espaçamentos
        ├── components/            # ChatHeader, MessageBubble, ChatInput,
        │                          # TypingIndicator e ErrorBanner
        └── screens/ChatScreen.js  # Tela principal do chat
```

