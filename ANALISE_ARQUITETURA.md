# CardioIA — Análise de Arquitetura das Fases 1 a 6

> **Documento de análise técnica — Fase 7**
> Objetivo: compreender integralmente a solução construída nas Fases 1 a 6 para preparar sua
> integração na Fase 7.
>
> **Método de levantamento:** leitura direta dos arquivos do workspace (`README.md`, código-fonte,
> notebooks, `requirements.txt`, `package.json`, `.env.example`, metadados de modelo e listagens
> de diretório). **Nada foi executado, instalado, alterado ou criado nas fases anteriores.**
>
> **Regra de honestidade deste documento:** toda afirmação é rastreável a um arquivo presente no
> workspace. O que não pôde ser confirmado está marcado explicitamente como
> **[DESCONHECIDO]** na seção 18.

---

## 1. Escopo e restrições desta etapa

| Item | Situação |
|---|---|
| Análise das Fases 1 a 6 | Concluída (somente leitura) |
| Alteração de código das fases anteriores | **Não realizada** (restrição respeitada) |
| Criação de novas aplicações | **Não realizada** (restrição respeitada) |
| Instalação de dependências | **Não realizada** (restrição respeitada) |
| Implementação de funcionalidades da Fase 7 | **Não realizada** (restrição respeitada) |
| Documentação produzida | `ANALISE_ARQUITETURA.md` e `PROGRESSO_FASE7.md` (raiz da Fase 7) |

Estrutura do workspace analisado:

```text
Fase_7/
├── Fase_1/Cap1_Busca_de_Dados/
├── Fase_2/Cap2_Desafio_Integrador/
├── Fase_3/Cap_1_CardioIA_Conectada/
├── Fase_4/Fase_4_Cap1/
├── Fase_5/Fase5_CardioAssist/
└── Fase_6/cardioia_Fase6/
```

Cada pasta é um **repositório Git independente** (com `.git/` próprio):

| Fase | Repositório remoto (`git config`) |
|---|---|
| 1 | `https://github.com/ReMendess/Cap1_Busca_de_Dados.git` |
| 2 | `https://github.com/ReMendess/Cap2_Desafio_Integrador.git` |
| 3 | `https://github.com/ReMendess/Cap_1_CardioIA_Conectada.git` |
| 4 | `https://github.com/ReMendess/Fase_4_Cap1.git` |
| 5 | `https://github.com/ReMendess/Fase5_CardioAssist.git` |
| 6 | `https://github.com/ReMendess/cardioia_Fase6.git` |

---

## 2. Sumário executivo

O **CardioIA** é um projeto acadêmico (FIAP) construído em seis fases incrementais, com um autor
recorrente nas Fases 3 a 6 (**Renan de Oliveira Mendes — RM563145**) e quatro integrantes nas
Fases 1 e 2. A solução evolui de **curadoria de dados** (Fase 1) para **NLP** (Fase 2), **IoT**
(Fase 3), **visão computacional** (Fase 4), **assistente conversacional** (Fase 5) e, por fim,
**sistema multiagentes com ML tabular** (Fase 6).

Pontos-chave para a integração na Fase 7:

1. **A Fase 6 é o núcleo mais maduro e reutilizável.** É o único módulo com pacote Python
   estruturado (`src/cardioia/`), contrato Pydantic de entrada/saída, camada determinística de
   protocolos, contexto tipado, testes automatizados (290 testes) e artefato de modelo versionado
   com metadados de rastreabilidade. Porém **não expõe API HTTP** — só linha de comando.
2. **Existem três backends Flask independentes** (Fases 3, 4 e 5) que **conflitam na porta 5000**.
3. **Existem dois frontends** com stacks distintas: um **portal web** React + Vite (Fase 2) e
   **dois apps Expo/React Native** (Fases 4 e 5).
4. **Não existe banco de dados** em nenhuma fase (apenas CSV, JSON, `localStorage` e sessão em
   memória).
5. **Não existe autenticação real** em nenhuma fase (a da Fase 2 é simulada no cliente).
6. **Há segredos reais versionados** (Fase 5: API key do IBM Watson; Fase 3: credenciais MQTT e
   SMTP) — risco de segurança a tratar na Fase 7.

---

## 3. Resumo de cada fase

### 3.1 Fase 1 — `Cap1_Busca_de_Dados`

**Título:** *Cap 1 — A Busca de Dados: Preparando o Terreno para a Inteligência Cardiológica*

**Objetivo declarado no README:** levantar e organizar dados cardiológicos que alimentarão os
módulos inteligentes do CardioIA, com foco em **governança de dados envolvendo IA**.

**Integrantes:** Renan de Oliveira Mendes (RM563145), Ricardo Batah Leone (RM563382),
Yuki Watanabe Kuramoto (RM565164), Rodrigo De Melo Reinaux Porto (RM564242).

**Três tipos de dados coletados:**

| Tipo | Arquivo / pasta | Detalhes |
|---|---|---|
| Numérico | `Dataset/heart_disease_uci.csv` | Dataset multivariado de doença cardíaca. Fonte declarada: Kaggle — `redwankarimsony/heart-disease-data`. 76 atributos no banco original; os estudos publicados usam um subconjunto de **14**. Colunas documentadas: `id`, `age`, `origin`, `sex`, `cp`, `trestbps`, `chol`, `fbs`, `restecg`, `thalach`, `exang`, `oldpeak`, `slope`, `ca`, `thal`, `num` (alvo). |
| Imagem | `Imagens/chest_xray_proportional/` (200 PNGs) + `Imagens/Cap1_Dados_Imagens_Selecao.ipynb` | Notebook que capturou **somente 200 imagens** de raio-X de tórax, **mantendo a distribuição original por tipo de doença**. |
| Texto | `Textos/*.pdf` | 2 artigos do SciELO: *"O Impacto Das Doenças Cardiovasculares Nas Perdas Econômicas"* (Fátima Marinho) e *"A Promoção da Saúde e a Prevenção Integrada dos Fatores de Risco para Doenças Cardiovasculares"* (Ribeiro; Cotta; Ribeiro). |

**Governança e tratamento declarados:** documentar origem, verificar licenças, registrar etapas de
tratamento, considerar vieses (exames coletados em contexto hospitalar específico) e garantir
anonimização das imagens. O README propõe, para as imagens, o uso de **CNNs ou modelos
pré-treinados**.

**Tecnologias:** Python + Jupyter Notebook; dados estáticos (CSV/PNG/PDF).

**O que NÃO existe nesta fase:** backend, API, endpoint, banco de dados, autenticação, modelo
treinado ou persistido.

**Reutilização potencial:** dataset tabular, as 200 imagens de raio-X e o corpus textual em
português — porém **nenhum deles foi efetivamente consumido** pelas fases seguintes (ver seção 16).

---

### 3.2 Fase 2 — `Cap2_Desafio_Integrador`

**Título:** *Cap 1 — Desafio Integrador: IA entre Robôs, Sinapses e Medicina*

**Objetivo:** automatizar triagem e diagnóstico médico com **NLP** e **Machine Learning**,
usando duas técnicas de NLP — **baseada em regras** e **estatística** — e, no "Ir Além", uma
**interface web moderna com React e Vite**.

**Vídeos declarados:** Parte 1 e 2 — `https://youtu.be/x02ARFNEPwI`; Ir Além —
`https://youtu.be/Ef4Oz--yt_8`.

#### Parte 1 — NLP baseado em regras

| Arquivo | Papel |
|---|---|
| `Parte_1/Criar_Dados.py` | Gera a base simulada `mapa_sintomas_doencas.csv` com 25 registros e as colunas `Sintoma 1`, `Sintoma 2`, `Intensidade`, `Duração`, `Doença Associada`. Doenças incluem Infarto, Angina, Insuficiência Cardíaca, Doença Pulmonar, Asma, Dengue, etc. |
| `Parte_1/mapa_sintomas_doencas.csv` | Base de conhecimento (saída do script acima). |
| `Parte_1/Identificar_Sintomas.py` | Lê o CSV e o `sintomas_pacientes.txt`. Normaliza o texto (minúsculas + remoção de pontuação via regex `[^\w\s]`), procura `sintoma1`/`sintoma2` por **substring** e pontua cada doença; devolve a de maior pontuação ou `"Diagnóstico não identificado"`. |
| `Parte_1/sintomas_pacientes.txt` | Entrada nova (frases de pacientes). |
| `Parte_1/Visualizar_Ontologia.py` | Monta um grafo (`networkx`) sintomas → doenças e desenha com `matplotlib` (`spring_layout`, `seed=42`). |

**Técnica declarada:** abordagem **baseada em regras**, com análises léxica, morfológica e
sintática (conforme o README, "como visto em aula").

#### Parte 2 — NLP estatístico (TF-IDF + ML)

| Arquivo | Papel |
|---|---|
| `Parte_2/Gerar_Dataset.py` | Gera `frases_risco.csv` (colunas `frase`, `situacao`) com 40 frases rotuladas como `alto risco` / `baixo risco`. |
| `Parte_2/Classificador_TF_IDF.ipynb` | `TfidfVectorizer` + **LogisticRegression** e **DecisionTreeClassifier**; avalia com `accuracy_score` e `classification_report`. |
| `Parte_2/frases_risco.csv` | Dataset textual gerado. |

**Resultados registrados (notebook + README):**

| Modelo | Acurácia (notebook) |
|---|---|
| Regressão Logística | **0,8333** (83%) |
| Árvore de Decisão | **0,6667** (~63–67%) |

O README afirma que o melhor modelo (regressão logística) classificou corretamente 4 novas frases
de "Alto Risco" em teste. **Nenhum modelo é persistido em arquivo** (não há `.pkl`/`.joblib`).

#### Ir Além — Portal web (React + Vite)

Stack declarada no README e confirmada no `package.json`:
React **19.2.4**, react-dom **19.2.4**, react-router-dom **7.13.2**, Vite **8.0.1**,
`@vitejs/plugin-react` **6.0.1**, ESLint **9.39.4**.

| Arquivo | Papel |
|---|---|
| `src/App.jsx` | `BrowserRouter` + rotas `/` (AuthGate), `/dashboard`, `/patients`, `/schedule`, `*` (redirect). |
| `src/contexts/AuthContext.jsx` | `AuthProvider` com `usuario`, `token`, `login()`, `logout()`, `loading`. Token em **`localStorage`**. |
| `src/components/ProtectedRoute.jsx` | Guarda de rota. |
| `src/pages/Dashboard.jsx`, `Patients.jsx`, `Schedule.jsx`, `Login.jsx` | 4 páginas. |
| `src/services/api.js` | `fetchPatients()` → `fetch("https://jsonplaceholder.typicode.com/users")`. |
| `src/hooks-examples/PainelLogin.jsx`, `AreaRestrita.jsx` | Exemplos de hooks. |

**Autenticação (simulada, client-side):** `login(email, senha)` valida **hardcoded**
`<email-fixo>` / `<senha-fixa>` e grava um token fictício previsível (`"<token-fake>"`) no `localStorage`.
Ao restaurar o token, cria um usuário fictício (`nome: "Usuário Fictício"`, `email: "<email-fictício>"`).

**Dados de pacientes:** a listagem consome a API pública **jsonplaceholder.typicode.com** —
explicitamente rotulada no próprio código como *"somente demonstração"*.

**Dependências (`requirements.txt` da fase):** `pandas>=2.1,<3`, `scikit-learn>=1.4,<2`,
`numpy>=1.26,<3`, `jupyterlab>=4,<5`. O arquivo também documenta o ambiente Node (20.x/22.x LTS).
Observação: `networkx` e `matplotlib` (usados por `Visualizar_Ontologia.py`) **não** constam do
`requirements.txt`.

**Problemas específicos:** todos os scripts Python usam **caminho absoluto hardcoded**
(`C:\Users\Pichau\OneDrive\Área de Trabalho\Cap2_Desafio_Integrador\...`), que **não corresponde**
à localização atual (`Fase_7\Fase_2\Cap2_Desafio_Integrador\...`). Existe ainda um
`Ir_Alem/package.json` duplicado (só `react-router-dom`) e `node_modules/` versionado.

---

### 3.3 Fase 3 — `Cap_1_CardioIA_Conectada`

**Título:** *Cap 1 — CardioIA Conectada: IoT e Visualização de Dados para a Saúde Digital*

**Autor:** Renan de Oliveira Mendes (RM563145).

**Objetivo:** com foco em **Edge, Fog e Cloud Computing**, implementar aplicações que capturam
dados em tempo real de sensores, armazenam localmente e se conectam com a nuvem, cobrindo todo o
fluxo até a visualização. No "Ir Além", uma solução em Python com **API REST + SMTP (Gmail)** para
alertas e o treino/comparação de dois modelos (**Regressão Logística** e **LIF** neuromórfico).

**Links declarados:** Wokwi Parte 1 — `https://wokwi.com/projects/463496096459659265`;
Wokwi Parte 2 — `https://wokwi.com/projects/463502084128323585`;
vídeo Parte 2 — `https://youtu.be/qpGmhhiO1mw`; vídeo Ir Além 2 — `https://youtu.be/rRensd7oCjk`.

#### Parte 1 — Edge Computing com ESP32 (resiliência offline)

Arquivo: `Parte1/codigo_ESP32.c` (relatório em `Parte1/Relatorio_parte1.pdf`).

| Elemento | Detalhe |
|---|---|
| Sensores | **DHT22** (temperatura e umidade, pino `DHT_PIN 15`) e **LDR** (luminosidade, pino `LDR_PIN 34`) |
| Estrutura de dados | `struct SensorData { float temperatura; float umidade; int luminosidade; }` |
| Buffer local | `const int MAX_STORAGE = 10;` → `SensorData storage[10]` + contador `storedCount` |
| Estratégia de resiliência | **FIFO**: quando cheio, desloca os registros (`for i=1..MAX_STORAGE`) e descarta o mais antigo |
| Conectividade | Booleano `wifiConnected` **simulado** (alterna a cada ciclo com `wifiConnected = !wifiConnected`) |
| Sincronização | `sendStoredData()` imprime os registros no **Monitor Serial** e zera `storedCount` |
| Loop | Leitura a cada **5 s** (`delay(5000)`), baudrate `115200` |

O README justifica a escolha: continuidade operacional, tolerância à falha de rede e baixo consumo
de memória.

#### Parte 2 — Edge → Fog → Cloud (MQTT + HiveMQ + Node-RED)

Arquivo: `Parte2/codigo_parte2.c` (relatório em `Parte2/Relatorio_parte2.pdf`).

| Elemento | Detalhe |
|---|---|
| Wi-Fi | `ssid = "Wokwi-GUEST"`, senha vazia |
| Broker MQTT | host do cluster HiveMQ Cloud (formato `<cluster-id>.s1.eu.hivemq.cloud`), porta **8883** (TLS) — valor literal no firmware |
| Credenciais MQTT | `mqtt_user` e `mqtt_pass` **literais no código** — 🔒 **valores mascarados neste documento** (ver `PLANO_SEGURANCA.md`) |
| Cliente | `WiFiClientSecure` + `PubSubClient` + `espClient.setInsecure()` |
| Tópicos publicados | `hospital/temperatura` e `hospital/bpm` |
| BPM | Simulado por botão (`BUTTON_PIN 18`, `INPUT_PULLUP`) → `random(60, 140)` |
| Loop | Publicação a cada **3 s** |
| Reconexão | `reconnect()` com `client.connect("ESP32Client", mqtt_user, mqtt_pass)` |

**Tecnologias declaradas no README:** ESP32, Wokwi, MQTT, **HiveMQ Cloud**, **Node-RED**,
Dashboard IoT, fluxo MQTT.

**Conceitos aplicados (conforme o README):** 1) Edge Computing; 2) coleta local no ESP32;
3) Fog Computing; 4) processamento intermediário no Node-RED; 5) Cloud Computing; 6) broker
MQTT HiveMQ Cloud.

#### Ir Além 1 — API REST de sinais vitais + alerta por e-mail

Arquivos: `Ir_Alem1/server.py` e `Ir_Alem1/client.py` (relatório em `Ir_Alem1/Relatorio_Ir_Alem.pdf`).

| Elemento | Detalhe |
|---|---|
| Endpoint | **`POST /sinais`** (Flask) |
| Payload | `{ "temperatura": float, "bpm": int, "movimento": bool }` |
| Regras de risco | `temperatura > 38` → `"FEBRE DETECTADA"`; `elif bpm > 120` → `"TAQUICARDIA DETECTADA"`; `elif movimento == False` → `"AUSÊNCIA DE MOVIMENTO"` |
| Resposta | `{"status": "ALERTA", "mensagem": <alerta>}` ou `{"status": "NORMAL", "mensagem": "Paciente estável"}` |
| Notificação | E-mail via **SMTP Gmail** (`smtplib.SMTP("smtp.gmail.com", 587)` + `starttls()`), assunto `"ALERTA MÉDICO"` |
| Credenciais | `EMAIL_REMETENTE`, `EMAIL_DESTINO` (mesmo endereço Gmail pessoal) e `EMAIL_SENHA` (placeholder `"SECRET"`) — **hardcoded no código**; 🔒 **valores mascarados neste documento** |
| Cliente | `client.py` gera sinais aleatórios (`temperatura` 35–40, `bpm` 60–140, `movimento` 3:1 verdadeiro) e faz `POST` a `http://127.0.0.1:5000/sinais` a cada **5 s** |
| Servidor | `app.run(debug=True)` → porta padrão **5000** |

#### Ir Além 2 — Modelos de ML em séries temporais de sinais vitais

Arquivo: `Ir_Alem2/Cap1CardioIA_Ir_Alem2ipynb.ipynb` (relatório em `Ir_Alem2/Relatorio_Ir_AlemII.pdf`).

- Base **sintética** de batimentos cardíacos, classificação binária entre **normal** e **taquicardia**.
- **Modelo 1 — Regressão Logística** (`sklearn.linear_model.LogisticRegression`, `train_test_split`,
  `accuracy_score`): declarado no README como mais estável e simples de treinar.
- **Modelo 2 — LIF (Leaky Integrate-and-Fire)**: classe `LIFNeuron` com `threshold=25`, acúmulo de
  potencial e disparo de *spikes*; regra de decisão no notebook: `if spikes >= 2 or media > 100`.
  Acúmulo de acurácia registrado no notebook: **0,985**.
- Conclusão declarada: modelos neuromórficos são aplicáveis a séries temporais de saúde, embora
  modelos tradicionais ainda apresentem vantagens em simplicidade e desempenho geral.

**Requisitos declarados no README:** Node.js 20/22 LTS + npm, Python 3.10–3.12, Arduino IDE ou
Wokwi, Node-RED, conta no HiveMQ Cloud, `node-red-dashboard`, Flask, Requests, SMTP.

**Observações:** o README cita a pasta `Ir_Alem_2`, mas a pasta real é `Ir_Alem2`. Os modelos desta
fase **não são persistidos** em arquivo.

---

### 3.4 Fase 4 — `Fase_4_Cap1`

**Título:** *Fase 4 — Cap 1 — Visão Computacional na Clínica*

**Autor:** Renan de Oliveira Mendes (RM563145).

**Objetivo:** aprofundar em visão computacional com **CNNs**, pré-processando e treinando dois
modelos (**CNN do zero** e **MobileNetV2 / Transfer Learning**) sobre um dataset de raio-X,
analisando vieses/desbalanceamento; no "Ir Além", uma **aplicação mobile com React Native**
para envio e classificação de imagens de raio-X.

**Vídeos declarados:** Ir Além — `https://youtu.be/1NBNX88V1-0`; App —
`https://youtube.com/shorts/XTpQ_kAq_G8`.

#### Parte 1 e 2 — Pipeline de visão computacional

Notebook: `Parte1e2/Fase4_Cap1 (1).ipynb` (889 KB, com saídas/imagens embutidas).

**Dataset:** *Chest X-Ray Images (Pneumonia)* — `https://www.kaggle.com/datasets/paultimothymooney/chest-xray-pneumonia`.
Duas classes: **Normal** e **Pneumonia**, já separadas em treino/validação/teste.

**Pré-processamento (conforme README):**
- redimensionamento para **128 pixels**;
- normalização dos pixels para **[0, 1]**;
- *data augmentation* (rotação, zoom, espelhamento horizontal);
- organização em conjuntos de treino, validação e teste.

**Desbalanceamento identificado:** conjunto de treino com **1.341 Normal** vs **3.875 Pneumonia**.
Mitigação declarada: *data augmentation* e **ponderação de classes** durante o treinamento.

**Modelos treinados:**

| Modelo | Descrição declarada |
|---|---|
| **CNN do zero** | **3.304.769 parâmetros**, **10 camadas**: 3× `Conv2D`, 3× `MaxPooling`, `Flatten`, `Dropout` e 2× `Dense`. |
| **MobileNetV2 (Transfer Learning)** | Modelo pré-treinado adaptado para classificação binária. |

**Critério de escolha declarado:** o assistente roda o **MobileNet**, por apresentar melhores
resultados na identificação de **casos positivos** — o que o README justifica como essencial em
modelos de saúde.

**Ir Além (ética):** `Ir_Alem/Relatorio_Etica_Govern.pdf` — relatório de análise de ética e
governança do dataset e dos modelos.

#### Ir Além 2 — Aplicação (backend Flask + app Expo/React Native)

**Estrutura declarada no README:**

```text
Ir_Alem2/
├── backend/                     # API Flask com modelo MobileNet (TensorFlow/Keras)
│   ├── app.py
│   ├── mobilenet_pneumonia.keras   # 11.589.128 bytes (~11,5 MB) — presente no workspace
│   └── requirements.txt
├── cardio-assistant/            # App mobile/web com Expo (React Native)
│   ├── app/                     # Rotas Expo Router
│   ├── screens/                 # Tela principal de análise
│   └── constants/api.ts         # URL da API
└── venv/                        # Ambiente Python  ← NÃO presente no workspace
```

**Backend — `backend/app.py`:**

| Elemento | Detalhe |
|---|---|
| Stack | Flask + **flask-cors** + **TensorFlow/Keras** + NumPy |
| Carregamento | `load_model(BASE_DIR / "mobilenet_pneumonia.keras")` no import; se ausente, `raise FileNotFoundError` |
| `GET /health` | → `{"status": "ok", "model": "mobilenet_pneumonia.keras"}` |
| `POST /predict` | multipart, campo **`image`**; valida presença e conteúdo; redimensiona para **(128, 128)**, normaliza `/255.0`, `expand_dims`; retorna `{"class": "Pneumonia"\|"Normal", "confidence": <float em %>}` com corte em `probability > 0.5` |
| Erros | `400` se `image` ausente/vazio; `500` em falha de processamento |
| Execução | `app.run(host="0.0.0.0", port=5000, debug=True)` |

**Frontend — `cardio-assistant/` (Expo / React Native):**

| Elemento | Detalhe |
|---|---|
| Stack (`package.json`) | `expo ~54.0.34`, `expo-router ~6.0.23`, `react-native 0.81.5`, `react 19.1.0`, `expo-image-picker ~17.0.8`, `@react-navigation/*`, `react-native-reanimated ~4.1.1`, TypeScript ~5.9.2 |
| `screens/HomeScreen.js` | Seleção de imagem (`ImagePicker.launchImageLibraryAsync`), `fetch(\`${API_URL}/predict\`, { method: "POST", body: formData })`, exibe `class` + `confidence` |
| `constants/api.ts` | Resolução da URL: `EXPO_PUBLIC_API_URL` → web `http://localhost:5000` → host do Metro `http://<host>:5000` → Android emulador `http://10.0.2.2:5000` → fallback `localhost` |
| `utils/uploadImage.ts` | Monta `FormData` compatível com web (Blob) e nativo (`{uri, type, name}`) |
| Rotas | `app/_layout.tsx`, `app/(tabs)/index.tsx`, `app/(tabs)/explore.tsx`, `app/(tabs)/_layout.tsx`, `app/modal.tsx` |
| Componentes | `external-link`, `haptic-tab`, `hello-wave`, `parallax-scroll-view`, `themed-text`, `themed-view`, `ui/collapsible`, `ui/icon-symbol(.ios)` |

**Como executar (conforme README da fase):**

```powershell
# 1) Backend
cd "...\Ir_Alem2\backend"
..\venv\Scripts\Activate.ps1
python app.py                       # http://localhost:5000
Invoke-RestMethod http://localhost:5000/health
# esperado: {"status":"ok","model":"mobilenet_pneumonia.keras"}

# 2) App
cd "...\Ir_Alem2\cardio-assistant"
npm install
npx expo start                      # 'w' web | 'a' Android | QR code no Expo Go
```

**Fluxo de uso declarado:** backend rodando → app aberto → aba **Análise** → **Selecionar
Imagem** → **Analisar** → resultado `Normal`/`Pneumonia` + confiança (%).

**Dependências do backend:** `flask`, `flask-cors`, `tensorflow`, `pillow`, `numpy` — **sem
versões fixadas**.

**Observações:** o README referencia o caminho `c:\Users\Pichau\OneDrive\Área de Trabalho\Fase_4_Cap1\...`
(uma pasta acima da estrutura atual) e um `venv/` que **não existe** no workspace.

---

### 3.5 Fase 5 — `Fase5_CardioAssist`

**Título:** *Fase 5 — Assistente Cardiológico Inteligente: Experiência do Paciente*

**Autor:** Renan de Oliveira Mendes (RM563145).

**Objetivo:** criar um assistente conversacional (**CardioAssist**) para orientação inicial sobre
saúde cardiovascular, usando **IBM watsonx Assistant** (NLU, entidades, *actions* e *skills*),
exposto por um **backend Flask** e consumido por um **app Expo/React Native**.

**Vídeo declarado:** Parte 1 e 2 — `https://youtu.be/t3lXi1qCfM4`.

#### Parte 1 — Assistente no IBM Watsonx

Modelagem declarada no README: **entidades, ações e fluxos conversacionais**, com **variáveis**,
**regras de condição** e **modelos de texto**. Nenhum artefato de configuração do Watson
(*skill*/*workspace* JSON) está presente no repositório — a configuração vive na plataforma IBM
(ver seção 18).

#### Parte 2 — Backend Flask + app Expo

**Estrutura declarada no README:**

```text
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

**Backend — `Backend/app.py` (Flask + flask-cors):**

| Endpoint | Contrato |
|---|---|
| `GET /health` | → `{"status": "ok", "service": "cardioassist-backend", "watson_configured": bool, "missing": [nomes de variáveis ausentes]}` |
| `POST /api/chat` | Body: `{ "message": str (obrigatório), "session_id": str\|null, "user_id": str (default "cardioassist-app", máx. 64 chars) }` → `{ "reply": str, "session_id": str, "timestamp": ISO-8601 UTC }` |

Comportamentos implementados:
- **Sessão stateful:** cria sessão no primeiro turno (`assistant.create_session`) e reutiliza;
- **Recuperação de sessão expirada:** em erro `404`, recria a sessão e **reintenta uma única vez**;
- **Mensagem vazia** → `400`; **configuração ausente** → `501` com a lista de variáveis faltantes;
- **Mapa de erros amigáveis** (`friendly_watson_error`): `401/403` → `507` (autenticação),
  `404` → `502` (assistente/sessão), `429` → `429` (cota do plano), `408/504` → `504` (timeout),
  `400/500/502/503` → `502` (erro do Watson), demais → `502`;
- **Extração de texto:** `_extract_reply()` percorre `output.generic[]` e concatena os itens com
  `response_type == "text"`; fallback amigável se não houver texto;
- **Execução:** `app.run(host="0.0.0.0", port=5000, debug=True)`.

**`Backend/IBM_API.py` (cliente Watson):**

| Constante | Valor presente no código |
|---|---|
| `API_KEY` | 🔒 **chave de API IAM real presente como default no código** (sobrescrevível por `WATSON_API_KEY`) — **valor mascarado neste documento** |
| `SERVICE_URL` | 🔒 URL regional do Watson Assistant (`https://api.<região>.assistant.watson.cloud.ibm.com/instances/<id-da-instância>`) — **valor mascarado** |
| `ASSISTANT_ID` | 🔒 identificador do assistente (UUID) — **valor mascarado** |
| `ENVIRONMENT_ID` | 🔒 identificador do ambiente (UUID) — **valor mascarado** |
| `VERSION` | `2024-08-25` |
| `WATSON_TIMEOUT` | `30` segundos |

`get_assistant()` monta `AssistantV2(version, IAMAuthenticator(API_KEY))`, define `set_service_url()`
e `set_http_config({"timeout": 30})`.

> 🔴 **Alerta de segurança:** essas credenciais estão **versionadas no repositório**, apesar de
> existir `Backend/.env.example`. A Fase 7 deve tratar a rotação e a externalização desses valores.

**Frontend — `CardioAssist/` (Expo / React Native):**

| Elemento | Detalhe |
|---|---|
| Stack (`package.json`) | `expo ~57.0.20`, `expo-constants ~57.0.17`, `react 19.2.3`, `react-native 0.86.3`, `react-native-web ^0.21.2` |
| `App.js` | `SafeAreaView` + `StatusBar` + `<ChatScreen />` |
| `src/screens/ChatScreen.js` | Estado das mensagens, `sessionRef`, sugestões rápidas (`"O que você faz?"`, `"Dor no peito"`, `"Quais sintomas devo observar?"`), indicador de digitação, `ErrorBanner` com retry |
| `src/services/watsonApi.js` | `sendChatMessage(text, {sessionId})`; **timeout de 20 s** (`Promise.race`); classe `WatsonApiError` com `code` (`empty`, `network`, `timeout`, `not-configured`, `auth-failed`, `quota`, `watson-error`, `server-error`) e `retriable`; `friendlyErrorText()` traduz cada código |
| `src/constants/api.js` | Resolução da URL: `EXPO_PUBLIC_API_URL` → web `http://localhost:5000` → host do Metro (descarta `localhost`/`127.0.0.1`/`10.0.2.2` e colchetes IPv6) → Android `http://10.0.2.2:5000` → fallback `localhost`; loga `API_URL` em `__DEV__` |
| Componentes | `ChatHeader` (indicador online), `ChatInput`, `MessageBubble`, `TypingIndicator`, `ErrorBanner` |
| `src/theme.js` | Paleta, tipografia e espaçamentos (`colors`, `spacing`) |

**Como executar (conforme README da fase):**

```powershell
# Backend
cd Backend
pip install -r requirements.txt
python app.py                        # http://localhost:5000

# App
cd CardioAssist
npm install
npx expo start
```

**Tabela de URLs do backend (README):** web/iOS simulador `http://localhost:5000` (automático);
emulador Android `http://10.0.2.2:5000` (fallback automático); celular físico
`http://<IP-da-máquina>:5000` (**detectado automaticamente** pelo host do Metro).

**Dica de firewall documentada no README:**
`netsh advfirewall firewall add rule name="CardioAssist 5000" dir=in action=allow protocol=TCP localport=5000`.

**Dependências do backend:** `flask`, `flask-cors`, `python-dotenv`, `ibm-watson`,
`ibm-cloud-sdk-core` — **sem versões fixadas**.

**Variáveis de ambiente (`Backend/.env.example`):** `WATSON_API_KEY`, `WATSON_SERVICE_URL`,
`WATSON_ASSISTANT_ID`, `WATSON_ENVIRONMENT_ID` (todas vazias no exemplo).
**`CardioAssist/.env.example`:** `EXPO_PUBLIC_API_URL` (opcional — exemplo
`http://192.168.15.16:5000`).

**Artefatos adicionais:** `CardioAssist_Relatorio.pdf` (relatório da fase) e `assets/` com
capturas do Watsonx, editor de fluxo, conversas e do app.

---

### 3.6 Fase 6 — `cardioia_Fase6` ⭐ (núcleo mais maduro)

**Título:** *CardioIA — Fase 6: Sistema Multiagentes para análise de risco*

**Subtítulo declarado:** `scikit-learn + base de protocolos + OpenAI Agents SDK`.

**Autor:** Renan de Oliveira Mendes (RM563145). **Vídeo:** `https://youtu.be/v-__IQXEDMA`.

**Objetivo:** treinar um modelo de classificação para prever a variável `pico_risco` a partir de uma
base **sintética** e usá-lo dentro de um **sistema multiagentes com quatro agentes especializados**,
orquestrados pelo **OpenAI Agents SDK** com *handoffs*.

**Solução em quatro pilares (conforme README):**

1. **Machine Learning:** geração da base, treino e avaliação (acurácia, matriz de confusão,
   relatório de classificação);
2. **Protocolos determinísticos:** as **10 regras** da base de conhecimento são aplicadas em Python,
   com os limiares e operadores exatos do material — **nenhum LLM escolhe protocolo ou altera
   limite**;
3. **Multiagente:** quatro agentes com responsabilidades separadas, *handoffs*, *tools* que
   consultam o modelo e os protocolos, **contexto tipado compartilhado** e **contrato de saída**;
4. **Interface de execução:** recebe um paciente e devolve a resposta estruturada.

**Observações de honestidade declaradas no README:**
- dados **sintéticos**, gerados por regras em `data/base_dados.py` (`np.random.seed(42)`, 5.000
  registros);
- o alvo `pico_risco` é **construído deterministicamente** a partir de 6 indicadores booleanos
  (`risk_score >= 2`); um modelo que reconstrói essa regra obtém métricas altíssimas.

#### Base de dados e treinamento

`data/base_dados.py` (arquivo oficial da aula, **lido e nunca editado**):

```python
np.random.seed(42); n = 5000
idade_media            = normal(55, 12).clip(18, 90)
carga_sistema          = uniform(30, 100)
tempo_espera           = normal(45, 20).clip(5, 180)
fc_media               = normal(85, 15).clip(50, 150)
spo2_media             = normal(95, 3).clip(70, 100)
pa_sistolica           = normal(125, 20).clip(80, 200)
temperatura            = normal(24, 5).clip(10, 40)
densidade_eventos      = poisson(3)
eventos_24h            = poisson(2)
disponibilidade_recursos = uniform(20, 100)

risk_score = (carga_sistema > 80) + (tempo_espera > 60) + (spo2_media < 92)
           + (fc_media > 110) + (eventos_24h > 4) + (disponibilidade_recursos < 40)
pico_risco = 1 se risk_score >= 2, senão 0
```

Distribuição: **1.329 (26,58%) positivos** e 3.671 (73,42%) negativos.
**`risk_score` nunca é usado como variável de entrada** (proteção contra vazamento de alvo).

**Decisões de treino (de `ml/train.py`):**
- **features:** as 10 colunas originais, na ordem oficial;
- **split:** 80/20 **estratificado**, `random_state=42` → 4.000 treino / 1.000 teste (266 positivos no teste);
- **algoritmos comparados no mesmo treino/teste:** `LogisticRegression` (pipeline com
  `StandardScaler`, interpretável) e `RandomForestClassifier(n_estimators=300, random_state=42)`;
- **critério de escolha, declarado ANTES de medir:** maior *recall* da classe `pico_risco=1`;
  empate por acurácia; depois por interpretabilidade;
- **o conjunto de teste é usado uma única vez**, para medir — não para ajustar hiperparâmetros;
- **limiar de decisão:** 0,5 (operacional, igual ao `predict` padrão do scikit-learn); a
  probabilidade é devolvida **crua** — o arredondamento ocorre só na apresentação.

**Métricas registradas (`models/modelo_pico_risco_metadata.json` + README):**

| Modelo | Acurácia | Recall (classe 1) | Precisão (classe 1) | F1 (classe 1) | Matriz de confusão `[[TN,FP],[FN,TP]]` |
|---|---:|---:|---:|---:|---|
| Regressão Logística | 0,8160 | 0,5526 | 0,6934 | 0,6151 | `[[669, 65], [119, 147]]` |
| **Random Forest** (escolhido) | **0,9990** | **0,9962** | 1,0000 | 0,9981 | `[[734, 0], [1, 265]]` |
| Regra determinística (teto, por construção) | 1,0000 | 1,0000 | 1,0000 | 1,0000 | `[[734, 0], [0, 266]]` |

O único falso negativo do Random Forest tem `risk_score = 2`, exatamente na fronteira do corte do rótulo.

#### Estrutura do repositório da Fase 6

```text
cardioia_Fase6/
├── .env.example                   # nomes das variáveis (sem valores)
├── .gitignore                     # versiona data/*.py e models/*.pkl e *.json
├── conftest.py                    # adiciona src/ ao sys.path (append, não insert)
├── pytest.ini                     # testpaths = tests; marker "integracao"
├── requirements.txt               # versões fixadas
├── data/
│   ├── base_dados.py              # base sintética (5.000 registros)
│   ├── base_conhecimento.py       # 10 protocolos oficiais
│   └── novo_paciente.py           # caso de simulação da aula
├── docs/
│   ├── arquitetura.md             # diagramas Mermaid
│   └── relatorio_tecnico.pdf      # relatório técnico (PDF)
├── models/
│   ├── .gitkeep
│   ├── modelo_pico_risco.pkl          # 4.713.033 bytes (~4,7 MB)
│   └── modelo_pico_risco_metadata.json
├── notebooks/treinamento_modelo.ipynb
├── src/cardioia/                  # IMPLEMENTAÇÃO OFICIAL
│   ├── __init__.py                # __versao__ = "0.2.0"
│   ├── config.py                  # constantes compartilhadas
│   ├── main.py                    # CLI
│   ├── ml/                        # dataset.py · train.py · evaluate.py · predict.py
│   ├── knowledge/protocols.py     # protocolos oficiais + regras determinísticas
│   ├── schemas/risk_result.py     # contrato Pydantic
│   └── agents/                    # contexto.py · 4 agentes · modelo_simulado.py
└── tests/                         # 9 arquivos, 290 testes (pytest)
```

> ⚠️ O README cita em `docs/` os arquivos `plano_implementacao.md`, `relatorio_tecnico.md` e
> `arquitetura_multiagente.pdf`. **Apenas `arquitetura.md` e `relatorio_tecnico.pdf` existem.**

#### Modelo de ML — artefatos e inferência

**`models/modelo_pico_risco_metadata.json`** (rastreabilidade completa): `nome_do_modelo`
("Random Forest"), `classe_do_estimador` (`RandomForestClassifier`), `variavel_alvo` (`pico_risco`),
`features` (10), `colunas_derivadas_do_alvo_excluidas` (`risk_score`), `criterio_de_escolha`,
`parametros_do_estimador` (`random_state=42`, `n_estimators=300`, `n_jobs=-1`, `max_depth=null`),
`limiar_de_decisao` (0.5), `semente` (42), `tamanho_do_teste` (0.2), `split_estratificado` (true),
`amostras_total/treino/teste` (5000/4000/1000), `metricas_no_teste`, `acuracia_da_regra_deterministica_no_teste`
(1.0), `origem_da_base` ("arquivo oficial data/base_dados.py"), `sha256_da_base_usada`
(`89f3a65f...54275`), `faixas_esperadas` (por feature), `versoes` (Python 3.13.5, numpy 2.2.6,
pandas 2.3.2, scikit-learn 1.8.0, joblib 1.5.3), `gerado_por` (`src/cardioia/ml/train.py`), `aviso`.

**`src/cardioia/ml/predict.py` — interface de uso do modelo:**

| Função / símbolo | Papel |
|---|---|
| `prever_pico_risco(paciente, caminho_modelo=None, pasta_modelos=None, raiz=None, limiar=0.5, modelo=None, metadados=None)` | Carrega artefatos, valida, **reordena as colunas conforme o metadata**, prevê e devolve dicionário com `pico_risco_previsto`, `probabilidade_risco` (crua), `classificacao_risco`, `modelo_utilizado`, `classe_do_estimador`, `variavel_alvo`, `limiar_decisao`, `regra_de_decisao`, `features_utilizadas`, `entrada`, `classe_prevista_pelo_estimador`, `origem_do_modelo` (caminho/semente/sha256/origem da base), `avisos`, `aviso_de_uso` |
| `prever_varios(...)` | Aplica a uma lista carregando os artefatos uma única vez |
| `resumo_para_agente(resultado)` | Uma linha legível pronta para ser devolvida por uma *tool* de agente |
| `carregar_modelo` / `carregar_metadados` / `validar_paciente` / `features_do_modelo` | Utilitários de contrato |
| `ROTULOS` | `{0: "sem_pico_de_risco", 1: "pico_de_risco"}`; `CLASSE_POSITIVA = 1` |
| Exceções | `ErroDePrevisao`, `ModeloNaoEncontradoError`, `PacienteInvalidoError`, `ModeloIncompativelError` |

**Contrato de entrada:** todas as features exigidas devem estar presentes; campos desconhecidos,
valores não numéricos, `NaN`/`inf` e **valores negativos são rejeitados** com erro explícito; valores
fora das faixas observadas no treino geram **aviso** (não erro). Se o artefato não existir, o erro
traz o comando exato para treinar. **Nunca treina silenciosamente durante uma consulta.**

**`ModeloIncompativelError`** documenta um caso real: `.pkl` treinado com scikit-learn 1.2.2 e
carregado com 1.8.0 é recusado (`ValueError` do `sklearn.tree._tree` no `dtype` antigo).

**`src/cardioia/ml/train.py` — treino via CLI:**

```bash
python -m src.cardioia.ml.train
python -m src.cardioia.ml.train --pasta-modelos models --semente 42
python -m src.cardioia.ml.train --dry-run        # mede e NÃO grava artefatos
```

Flags: `--pasta-modelos`, `--semente` (default 42), `--tamanho-teste` (default 0.2),
`--n-estimators` (default 300), `--raiz`, `--dry-run`, `--quiet`.

**`src/cardioia/ml/dataset.py`** é a **autoridade única** sobre o material oficial: executa
`data/base_dados.py`, valida colunas/tipos/ausentes/alvo, separa features e alvo (garantindo que
`risk_score` não entre em `X`), reproduz a regra do rótulo, lê `data/novo_paciente.py` (corrigindo a
divergência de nome `"disponibilidade recursos"` → `disponibilidade_recursos`) e calcula o
`sha256` da base. Constantes: `VARIAVEL_ALVO`, `COLUNAS_PREDITORAS`, `COLUNAS_AUXILIARES_IGNORADAS`,
`SEMENTE=42`, `TAMANHO_TESTE=0.20`, `LIMIARES_DO_ROTULO`, `CORTE_RISK_SCORE=2`, `FAIXAS_ESPERADAS`.

**`src/cardioia/ml/evaluate.py`** calcula acurácia, precisão, recall, F1, matriz de confusão e
relatório — tudo **serializável em JSON** (sem tipos `numpy`/`NaN`), com destaque para a classe
positiva e tratamento explícito de métricas indefinidas (`None` + aviso, nunca `0.0` silencioso).

#### Protocolos determinísticos (sem LLM)

`data/base_conhecimento.py` contém a lista `protocolos` com **10 regras textuais**:

```python
protocolos = [
    "Se SPO2 < 88% → iniciar suporte respiratório imediato",
    "Se carga do sistema > 85% → abrir unidades temporárias",
    "Se FC > 120 → iniciar monitoramento intensivo",
    "Se eventos_24h > 5 → ativar equipe de resposta rápida",
    "Se disponibilidade_recursos < 30% → redistribuir insumos",
    "Se tempo_espera > 90 min → priorizar triagem emergencial",
    "Se temperatura > 38°C média → iniciar protocolo infeccioso",
    "Se densidade_eventos > 6 → ativar plano de contingência",
    "Se PA sistólica < 90 → iniciar protocolo de choque",
    "Se risco sistêmico alto → ativar estado de emergência",
]
```

`src/cardioia/knowledge/protocols.py` associa, **por posição explícita e validada**, cada protocolo
a uma regra numérica:

| # | Protocolo | Condição implementada | Limiar |
|---|---|---|---|
| 1 | SPO2 baixa | `spo2_media < 88` | 88 |
| 2 | Carga do sistema | `carga_sistema > 85` | 85 |
| 3 | FC alta | `fc_media > 120` | 120 |
| 4 | Eventos em 24 h | `eventos_24h > 5` | 5 |
| 5 | Disponibilidade de recursos | `disponibilidade_recursos < 30` | 30 |
| 6 | Tempo de espera | `tempo_espera > 90` | 90 |
| 7 | Temperatura | `temperatura > 38` | 38 |
| 8 | Densidade de eventos | `densidade_eventos > 6` | 6 |
| 9 | PA sistólica | `pa_sistolica < 90` | 90 |
| 10 | Risco sistêmico alto | `pico_risco_previsto == 1` (**classe do modelo de ML**) | — |

**Princípios declarados no módulo:**
- **operadores estritos:** `spo2_media == 88` **não** satisfaz `spo2_media < 88`;
- **sem correspondência textual aproximada:** o vínculo protocolo↔regra é uma lista fixa e ordenada,
  validada por marcadores normalizados — se o arquivo oficial mudar de ordem/tamanho, o carregamento
  **falha** em vez de casar com a regra errada;
- **sem duplicatas:** cada protocolo é avaliado exatamente uma vez;
- **somente Python decide:** o LLM nunca escolhe protocolo, altera limiar ou cria regra nova.

**API pública:** `carregar_protocolos()`, `avaliar_protocolos(paciente, pico_risco_previsto, protocolos=None, raiz=None)`
e a variante tolerante a falhas **`avaliar_protocolos_seguro(...) -> (AvaliacaoDosProtocolos | None, list[str])`**
(usada pela *tool* do agente para que a falha seja registrada em vez de derrubar o `run`).
Dataclasses: `Protocolo`, `ProtocoloAplicado`, `Condicao`, `AvaliacaoDosProtocolos`.
Exceções: `ErroDeProtocolos`, `BaseDeConhecimentoInvalidaError`, `DadosDoPacienteInvalidosError`.

#### Agentes e LLMs (OpenAI Agents SDK)

**Fluxo real de handoffs:**

```text
Orquestrador ──▶ Analista de Risco ──▶ Especialista em Protocolos ──▶ Planejador de Resposta
```

| # | Agente | Papel no SDK | Responsabilidade | Saída esperada |
|---|---|---|---|---|
| 4 | **Orquestrador** | agente inicial | validar entradas, exigir o artefato, iniciar o `run` e montar/validar o contrato — **nunca responde por conta própria** | um *handoff* |
| 1 | **Analista de Risco** | destino do handoff #1 | chamar a tool do modelo e informar o resultado | chamada de tool + handoff |
| 2 | **Especialista em Protocolos** | destino do handoff #2 | chamar a tool dos protocolos e respeitar o que ela retornar | chamada de tool + handoff |
| 3 | **Planejador de Resposta** | destino do handoff #3, com `output_type` | consolidar narrativa, justificativas e pontos de atenção | objeto estruturado (`ContribuicaoDoPlanejador`) |

**Handoffs (nomes das tools expostas ao LLM):**

| Origem | Destino | Tool |
|---|---|---|
| Orquestrador | Analista de Risco | `transfer_to_analista_de_risco` |
| Analista de Risco | Especialista em Protocolos | `transfer_to_especialista_em_protocolos` |
| Especialista em Protocolos | Planejador de Resposta | `transfer_to_planejador_de_resposta` |

**Tools (Python, executadas pelo SDK):**

| Tool | Declarada por | Implementação chamada | Efeito no contexto |
|---|---|---|---|
| `consultar_modelo_de_risco` | Analista de Risco | `cardioia.ml.predict.prever_pico_risco` | grava probabilidade, classe, modelo, limiar |
| `consultar_protocolos` | Especialista em Protocolos | `cardioia.knowledge.protocols.avaliar_protocolos_seguro` | grava protocolos, justificativas e indicadores |

> As tools **não aceitam argumentos** de propósito: se as features fossem parâmetros, o LLM poderia
> alterar os valores do paciente. Ele só decide **quando** consultar.

**Contexto tipado — `agents/contexto.py`:** `ContextoDaExecucao` (dataclass) guarda `paciente`,
`raiz`, `pasta_modelos`, `limiar`, `predicao`, `avaliacao_de_protocolos`, `passos`, `erros`,
`handoffs`. Esse objeto **nunca é enviado ao LLM** — apenas um resumo textual vai ao modelo; os
números críticos ficam no Python. `TrilhaDeExecucao(RunHooks)` sobrescreve `on_agent_start`,
`on_handoff` e `on_tool_start` para registrar a trilha observável. Nomes fixos:
`NOME_ORQUESTRADOR`, `NOME_ANALISTA_DE_RISCO`, `NOME_ESPECIALISTA_EM_PROTOCOLOS`,
`NOME_PLANEJADOR_DE_RESPOSTA`, `NOME_TOOL_MODELO`, `NOME_TOOL_PROTOCOLOS`.

**Modelo simulado — `agents/modelo_simulado.py`:** implementa `Model` e `ModelProvider` do SDK
(`ModeloComRoteiro` / `ProvedorDeModelosSimulado`) para executar o pipeline **sem a API da OpenAI**,
mantendo reais o SDK, os handoffs, as tools, o `RunHooks` e a validação do contrato. Consome
exatamente **um passo por chamada** (evita laço infinito) e valida cada passo contra as tools/handoffs
que o SDK realmente ofereceu; passos impossíveis geram `problemas` → o pipeline termina como `ERRO`.

**Verificações de integridade no orquestrador:**
- `verificar_handoffs_finais(nome_do_agente_final)` — exige que o run termine no **Planejador de
  Resposta**, senão registra aviso;
- `verificar_narrativa(narrativa, probabilidade)` — se o texto citar número divergente da
  probabilidade real, o status vira `CONCLUIDO_COM_RESSALVAS` (o valor autoritativo é o da tool);
- `versao_do_sdk()` — devolve a versão instalada do pacote `agents`.

**Detalhe técnico documentado no código:** `RunConfig.model_provider` tem *default factory*; passar
`model_provider=None` **sobrescreve** esse default e o SDK falha com
`AttributeError: 'NoneType' object has no attribute 'get_model'`. Por isso os campos só são
incluídos quando fazem sentido. O tracing fica **desativado** (`tracing_disabled=True`).

#### Contrato de saída (Pydantic) — `schemas/risk_result.py`

| Símbolo | Papel |
|---|---|
| `StatusDaExecucao` | `CONCLUIDO`, `CONCLUIDO_COM_RESSALVAS`, `INCOMPLETO`, `ERRO` |
| `TipoDePasso` | `handoff`, `tool`, `agente`, `validacao`, `erro` |
| `ModoDeExecucao` | `simulado`, `real` |
| `RespostaDaExecucao` | Contrato único de saída: `id_execucao`, `gerado_em`, `status`, `modo`, `diagnostico`, `indicadores`, `protocolos`, `justificativas`, `narrativa`, `avisos`, `erros`, `passos`, `handoffs_realizados`, `agente_final`, `versao_do_sdk`, `duracao_segundos`, `limitacoes`; métodos `como_dicionario()` (JSON-safe) e `resumo_textual()` |
| `DiagnosticoDaPredicao`, `ProtocoloAplicavel`, `PassoDaExecucao`, `IndicadorDeterministico` | Estruturas internas do contrato |
| `contrato_de_exemplo()` | Exemplo mínimo válido (usado em testes/documentação) |

**Regras do contrato:** `extra="forbid"` em todos os modelos; a probabilidade é o valor cru
(`ge=0, le=1`); a classe prevista precisa ser coerente com a classificação textual;
**falha nunca vira sucesso** — `CONCLUIDO` exige diagnóstico e proíbe erros registrados, enquanto
`INCOMPLETO`/`ERRO` exigem ao menos um erro descrito.

`SECOES_OCULTAS_NO_MODO_SIMULADO = ("LIMITACOES", "AVISOS", "ERROS")`: a supressão é **apenas de
apresentação** (decisão do autor para a demonstração); o contrato Python segue íntegro — inclusive no
`--json` — e as seções reaparecem sempre que a execução **não** conclui.

#### Interface de execução — CLI `src/cardioia/main.py`

**Uso declarado no docstring do módulo:**

```bash
python -m src.cardioia.main                          # paciente de data/novo_paciente.py
python -m src.cardioia.main --json                   # saída JSON (contrato completo)
python -m src.cardioia.main --modo real              # exige OPENAI_API_KEY no ambiente
python -m src.cardioia.main --paciente caso.json     # paciente em arquivo JSON
python -m src.cardioia.main --paciente '{"idade_media": 62, ...}'   # JSON inline
```

**Comportamento em falha:** **nunca** treina um modelo ausente, nunca inventa predição; sai com
código **1** quando o pipeline não conclui.

| Código de saída | Significado |
|---|---|
| `0` | Pipeline concluiu (`CONCLUIDO` ou `CONCLUIDO_COM_RESSALVAS`) |
| `1` | `ERRO`/`INCOMPLETO` — motivos impressos em `stderr` |
| `2` | Erro de uso da CLI (flag inválida) |

O CLI também configura a saída UTF-8 (`sys.stdout.reconfigure`) para evitar `UnicodeEncodeError` no
console cp1252 do Windows por causa do caractere `→` dos protocolos.

**Modo real:**

```powershell
$env:OPENAI_API_KEY = "sk-..."
python -m src.cardioia.main --modo real --modelo gpt-4o-mini
```

Sem a chave, o pipeline responde `status=ERRO` com a instrução e sai com código 1.
`OPENAI_MODEL` (variável de ambiente) é alternativa à flag `--modelo`.

**Saída do modo simulado (paciente da aula) — trecho do README:**

```text
status         : CONCLUIDO
modo           : simulado
agente final   : Planejador de Resposta

PREDICAO (calculada pelo modelo de ML, nunca pelo LLM)
  modelo                 : Random Forest (RandomForestClassifier)
  probabilidade de pico  : 0.9900
  pico_risco_previsto    : 1
  classificacao de risco : pico_de_risco
  limiar de decisao      : 0.5 (probabilidade_risco >= limiar (0.5))

PROTOCOLOS APLICAVEIS (4)
  - Se carga do sistema > 85% ...         [valor observado: 92]
  - Se disponibilidade_recursos < 30% ... [valor observado: 25]
  - Se densidade_eventos > 6 ...          [valor observado: 7]
  - Se risco sistemico alto ...           [classe prevista = 1]

HANDOFFS REALIZADOS
  -> Orquestrador -> Analista de Risco
  -> Analista de Risco -> Especialista em Protocolos
  -> Especialista em Protocolos -> Planejador de Resposta
```

#### Testes (pytest)

```bash
python -m pytest tests -q

python -m pytest tests/test_protocols.py -q     # 61 testes
python -m pytest tests/test_schemas.py -q       # 61 testes
python -m pytest tests/test_prediction.py -q    # 40 testes
python -m pytest tests/test_dataset.py -q       # 33 testes
python -m pytest tests/test_orchestrator.py -q  # 29 testes
python -m pytest tests/test_agents.py -q        # 26 testes
python -m pytest tests/test_seguranca.py -q     # 17 testes
python -m pytest tests/test_cli.py -q           # 14 testes

# integração (consome API paga) — PULADO sem OPENAI_API_KEY
python -m pytest tests/test_integracao_real.py -m integracao
```

| Arquivo | Cobre |
|---|---|
| `test_dataset.py` | base oficial, dimensões, alvo, `risk_score` fora das features, reprodutibilidade |
| `test_prediction.py` | contrato de entrada, probabilidade, modelo ausente, estabilidade após reload |
| `test_protocols.py` | as 10 regras, limites **estritos**, multiseleção, ausência de duplicatas, dados inválidos |
| `test_schemas.py` | contratos Pydantic: probabilidade, classes, campos obrigatórios, coerência de status |
| `test_agents.py` | tools chamando as implementações reais, configuração dos handoffs, contexto |
| `test_orchestrator.py` | fluxo completo com handoffs reais, histórico de mensagens, falhas |
| `test_cli.py` | comando real, `--json` válido, códigos de saída, flags, independência de diretório |
| `test_seguranca.py` | falha de API propagada, ausência de segredos, portabilidade dos caminhos, coerência dos protocolos com o arquivo oficial |

**Fixtures (`tests/conftest.py`):** os testes **não acessam internet nem a API da OpenAI**; nenhum
teste depende do `.pkl` versionado — a fixture `modelo_temporario` treina um Random Forest pequeno
(10 árvores, semente 42) numa amostra de 400 linhas em `tmp_path_factory`. A base oficial é carregada
uma única vez por sessão. O `conftest.py` da raiz adiciona `src/` ao `sys.path` com **`append` (não
`insert`)** de propósito: existe um pacote de topo `agents` instalado pelo SDK e a pasta
`src/agents/` (citada como placeholder da Etapa 1) não deve sombreá-lo.

#### Tecnologias e dependências (Fase 6)

| Camada | Tecnologia | Versão testada |
|---|---|---|
| Linguagem | Python | 3.13.5 |
| Dados | pandas · NumPy | 2.3.2 · 2.2.6 |
| Machine Learning | scikit-learn | 1.8.0 |
| Persistência do modelo | joblib | 1.5.3 |
| Multiagente | **openai-agents** (OpenAI Agents SDK) | **0.18.1** |
| SDK base | openai | 2.38.0 |
| Contratos | pydantic | 2.14.1 |
| Testes | pytest | 9.1.1 |
| Transitivas fixadas | starlette · sse-starlette | 0.48.0 · 2.3.5 |

**Instalação declarada no README:**

```bash
git clone https://github.com/ReMendess/cardioia_Fase6.git
cd cardioia_Fase6
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env      # Windows: Copy-Item .env.example .env
```

**Conflito de ambiente conhecido (documentado e não resolvido):** `gradio 5.49.1` declara
`pydantic<2.12`, enquanto `openai-agents 0.18.1` exige `pydantic>=2.12.2` — restrições mutuamente
insatisfazíveis no mesmo ambiente. Alternativas registradas no `requirements.txt`:
1) `openai-agents==0.4.2` (exige `pydantic>=2.10` e `openai>=2.2,<3`); 2) um **venv por projeto**
(recomendado).

**Documentação da fase:** `docs/arquitetura.md` (diagramas Mermaid de componentes, sequência, fluxo
de dados, fronteira de confiança e tratamento de falhas) e `docs/relatorio_tecnico.pdf`.
**Limitação declarada no próprio código:** *"Esta etapa não implementa API web nem interface gráfica
(não são requisitos da atividade)."*

---

## 4. Tabela: Fases × Componentes

### 4.1 Visão consolidada

| Fase | Repositório / pasta | Foco temático | Backend | Frontend | Modelos de IA | Dados / artefatos | Persistência | Autenticação |
|---|---|---|---|---|---|---|---|---|
| **1** | `Fase_1/Cap1_Busca_de_Dados` | Curadoria e governança de dados | — | — | — | `heart_disease_uci.csv`; 200 PNGs de raio-X; 2 PDFs SciELO | Arquivos versionados | — |
| **2** | `Fase_2/Cap2_Desafio_Integrador` | NLP (regras + TF-IDF) e portal web | — (somente scripts/notebook) | **React 19.2.4 + Vite 8 + react-router-dom 7** | LogisticRegression (TF-IDF) **0,833**; DecisionTree **0,667**; ontologia networkx | `mapa_sintomas_doencas.csv`; `frases_risco.csv`; `sintomas_pacientes.txt` | CSV + `localStorage` | **Simulada** (client-side, hardcoded) |
| **3** | `Fase_3/Cap_1_CardioIA_Conectada` | IoT Edge/Fog/Cloud + alertas | **Flask `POST /sinais`** | Node-RED dashboard (externo, não versionado) | LogisticRegression + **LIF** neuromórfico (**0,985**) | Séries sintéticas de sinais vitais; firmware ESP32 | Memória do ESP32 / Serial / MQTT | — (credenciais MQTT e SMTP hardcoded) |
| **4** | `Fase_4/Fase_4_Cap1` | Visão computacional (CNN) | **Flask `GET /health`, `POST /predict`** | **Expo/React Native** (web + mobile) | CNN própria (3.304.769 params); **MobileNetV2** (`.keras`, 11,5 MB) | Chest X-Ray Pneumonia (Kaggle) | Arquivo `.keras` | — |
| **5** | `Fase_5/Fase5_CardioAssist` | Assistente conversacional | **Flask `GET /health`, `POST /api/chat`** | **Expo/React Native** (web + mobile) | **IBM watsonx Assistant v2** (NLU/LLM externo) | — (configuração vive na plataforma IBM) | Sessão Watson (stateful, em memória no backend) | **IAM / API key** 🔴 versionada |
| **6** | `Fase_6/cardioia_Fase6` | Multiagentes + ML tabular | — (**CLI Python**, sem HTTP) | — (CLI) | **RandomForest 0,999** / LogReg 0,816 + **4 agentes** (OpenAI Agents SDK 0.18.1) | `base_dados.py` (5.000 sintéticos); `base_conhecimento.py` (10 protocolos); `.pkl` + metadata | `models/*.pkl` + `metadata.json` | **`OPENAI_API_KEY`** (variável de ambiente) |

### 4.2 Matriz de componentes técnicos

| Componente | Fase 1 | Fase 2 | Fase 3 | Fase 4 | Fase 5 | Fase 6 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Backend HTTP (Flask) | — | — | ✅ | ✅ | ✅ | — |
| Frontend web | — | ✅ | — | ✅ (web via Expo) | ✅ (web via Expo) | — |
| App mobile | — | — | — | ✅ | ✅ | — |
| CLI / script Python | ✅ (notebook) | ✅ | ✅ | ✅ (notebook) | — | ✅ |
| Endpoint REST próprio | — | — | ✅ | ✅ | ✅ | — |
| Consumo de API externa | — | ✅ (jsonplaceholder) | ✅ (HiveMQ/MQTT) | — | ✅ (Watson) | ✅ (OpenAI, opcional) |
| Modelo de ML persistido | — | — | — | ✅ (`.keras`) | — | ✅ (`.pkl`) |
| Notebook de treino | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| Base de conhecimento externa | — | ✅ (CSV) | — | — | ✅ (skill Watson) | ✅ (`.py` de protocolos) |
| Testes automatizados | — | — | — | — | — | ✅ (290 pytest) |
| Contrato de dados (schema) | — | — | — | — | — | ✅ (Pydantic) |
| Autenticação | — | ✅ (fake) | — | — | ✅ (IAM) | — (chave de API) |
| Banco de dados | — | — | — | — | — | — |
| Docker / orquestração | — | — | — | — | — | — |
| CI/CD | — | — | — | — | — | — |

---

## 5. Tecnologias identificadas

### 5.1 Linguagens e runtimes

| Tecnologia | Versão identificada | Onde |
|---|---|---|
| Python | **3.13.5** (Fase 6) · **3.10–3.12** recomendado (Fases 2 e 3) · **3.10+** (Fase 4) | Todas as fases |
| JavaScript / JSX | ES Modules | Fase 2 (React) |
| TypeScript / TSX | ~5.9.2 | Fase 4 (app Expo) |
| C / C++ (Arduino core) | — | Fase 3 (firmware ESP32) |
| JSON | — | Todas (configs e contratos) |
| Markdown | — | Documentação |

### 5.2 Frontend

| Tecnologia | Versão | Fase |
|---|---|---|
| React | 19.2.4 | 2 |
| React DOM | 19.2.4 | 2 |
| React Router DOM | 7.13.2 | 2 |
| Vite | 8.0.1 | 2 |
| `@vitejs/plugin-react` | 6.0.1 | 2 |
| ESLint | 9.39.4 | 2 |
| Expo | ~54.0.34 | 4 |
| Expo Router | ~6.0.23 | 4 |
| React Native | 0.81.5 | 4 |
| React | 19.1.0 | 4 |
| ESLint / `eslint-config-expo` | ^9.25.0 / ~10.0.0 | 4 |
| `expo-image-picker` | ~17.0.8 | 4 |
| `@react-navigation/*` | 7.x / 2.6.3 | 4 |
| `react-native-reanimated` | ~4.1.1 | 4 |
| Expo | ~57.0.20 | 5 |
| React Native | 0.86.3 | 5 |
| React | 19.2.3 | 5 |
| Node.js | 20.x ou 22.x LTS (recomendado) | 2, 3, 4, 5 |
| npm | incluso no Node | 2, 3, 4, 5 |

### 5.3 Backend e APIs

| Tecnologia | Versão | Fase |
|---|---|---|
| Flask | **sem versão fixada** | 3, 4, 5 |
| flask-cors | **sem versão fixada** | 4, 5 |
| python-dotenv | sem versão fixada | 5 |
| requests | sem versão fixada | 3 |
| smtplib (stdlib) | — | 3 |
| TensorFlow / Keras | sem versão fixada | 4 |
| Pillow | sem versão fixada | 4 |
| ibm-watson · ibm-cloud-sdk-core | sem versão fixada | 5 |
| OpenAI Agents SDK (`openai-agents`) | **0.18.1** | 6 |
| `openai` | **2.38.0** | 6 |
| pydantic | **2.14.1** | 6 |
| starlette · sse-starlette | 0.48.0 · 2.3.5 | 6 |

### 5.4 Ciência de dados e ML

| Tecnologia | Versão | Fase |
|---|---|---|
| pandas | 2.3.2 (Fase 6) · >=2.1 (Fase 2) | 2, 6 |
| NumPy | 2.2.6 (Fase 6) · >=1.26 (Fase 2) | 2, 6 |
| scikit-learn | **1.8.0** (Fase 6) · >=1.4 (Fase 2) | 2, 3, 6 |
| joblib | 1.5.3 | 6 |
| networkx | sem versão fixada | 2 |
| matplotlib | sem versão fixada | 2 |
| seaborn | (importado no notebook da Fase 3) | 3 |
| JupyterLab | >=4.0.0,<5 | 2, 3, 4, 6 |
| TensorFlow / Keras | sem versão fixada | 4 |

### 5.5 IoT e infraestrutura

| Tecnologia | Detalhe | Fase |
|---|---|---|
| ESP32 | microcontrolador (simulado no Wokwi) | 3 |
| DHT22 | temperatura e umidade (pino 15) | 3 |
| LDR | luminosidade (pino 34) | 3 |
| Wokwi | simulador online | 3 |
| MQTT (PubSubClient) | protocolo de mensageria | 3 |
| HiveMQ Cloud | broker MQTT (porta 8883/TLS) | 3 |
| Node-RED + node-red-dashboard | camada Fog e visualização | 3 |
| SMTP Gmail | notificação de alertas | 3 |
| Arduino IDE | ambiente de compilação alternativo | 3 |

### 5.6 Serviços externos

| Serviço | Uso | Fase |
|---|---|---|
| Kaggle | datasets (heart disease, chest x-ray pneumonia) | 1, 4 |
| SciELO | artigos científicos (corpus textual) | 1 |
| `jsonplaceholder.typicode.com` | API fake para listagem de pacientes | 2 |
| HiveMQ Cloud | broker MQTT | 3 |
| Gmail (SMTP) | envio de alertas | 3 |
| IBM Cloud (watsonx Assistant v2) | assistente conversacional | 5 |
| OpenAI API | LLM dos agentes (modo real) | 6 |

### 5.7 Testes e qualidade

| Tecnologia | Versão | Fase |
|---|---|---|
| pytest | **9.1.1** | 6 |
| pytest marker | `integracao` | 6 |
| ESLint | 9.39.4 / ^9.25.0 | 2, 4 |
| Jupyter (execução de notebooks) | 4.x | 2, 3, 4, 6 |

---

## 6. Estrutura dos projetos

Árvores levantadas diretamente do workspace (dependências instaladas como `node_modules/`, `.git/`,
`venv/` e `__pycache__/` foram omitidas da listagem por não serem código-fonte).

### 6.1 Fase 1 — `Cap1_Busca_de_Dados`

```text
Cap1_Busca_de_Dados/
├── README.md
├── assets/                       # logo-fiap, Dataset.png, RaioX.png, Redistribuir_imagens.png,
│                                 # Texto_Saude_Cardio.png
├── Dataset/
│   └── heart_disease_uci.csv
├── Imagens/
│   ├── Cap1_Dados_Imagens_Selecao.ipynb
│   └── chest_xray_proportional/  # 200 imagens .png
└── Textos/
    ├── A_Promocao_da_Saude_e_a_Prevencao_Integrada_...pdf
    ├── O_Impacto_Das_Doencas_Cardiovasculares_Nas_Perdas_Econômicas.pdf
    └── excluir.txt
```

### 6.2 Fase 2 — `Cap2_Desafio_Integrador`

```text
Cap2_Desafio_Integrador/
├── README.md
├── requirements.txt
├── assets/                                  # capturas de tela e diagramas
├── Ir_Alem/
│   ├── package.json                         # ⚠️ duplicado (só react-router-dom)
│   ├── package-lock.json
│   └── my-react-app/
│       ├── index.html
│       ├── package.json
│       ├── vite.config.js
│       ├── eslint.config.js
│       ├── README.md
│       ├── .gitignore
│       ├── public/                          # favicon.svg, icons.svg
│       └── src/
│           ├── App.jsx · App.css · index.css · main.jsx
│           ├── assets/                      # hero.png, imagem_medico.jpg, medical-bg.svg, ...
│           ├── components/ProtectedRoute.jsx
│           ├── contexts/AuthContext.jsx
│           ├── hooks-examples/              # AreaRestrita.jsx, PainelLogin.jsx
│           ├── pages/                       # Dashboard.jsx, Login.jsx, Patients.jsx, Schedule.jsx
│           └── services/api.js
├── Parte_1/
│   ├── Criar_Dados.py
│   ├── Identificar_Sintomas.py
│   ├── Visualizar_Ontologia.py
│   ├── mapa_sintomas_doencas.csv
│   └── sintomas_pacientes.txt
└── Parte_2/
    ├── Classificador_TF_IDF.ipynb
    ├── Gerar_Dataset.py
    └── frases_risco.csv
```

### 6.3 Fase 3 — `Cap_1_CardioIA_Conectada`

```text
Cap_1_CardioIA_Conectada/
├── README.md
├── assets/                                  # wokwi.png, HiveMQ.png, NODE_RED.png, client.png,
│                                            # server.png, email*.png, modelos_comp.png, ...
├── Parte1/
│   ├── codigo_ESP32.c
│   └── Relatorio_parte1.pdf
├── Parte2/
│   ├── codigo_parte2.c
│   └── Relatorio_parte2.pdf
├── Ir_Alem1/                                # ⚠️ README chama de "Ir_Alem_2" no caso do notebook
│   ├── client.py
│   ├── server.py
│   └── Relatorio_Ir_Alem.pdf
└── Ir_Alem2/
    ├── Cap1CardioIA_Ir_Alem2ipynb.ipynb
    └── Relatorio_Ir_AlemII.pdf
```

### 6.4 Fase 4 — `Fase_4_Cap1`

```text
Fase_4_Cap1/
├── README.md
├── assets/                                  # dataset.png, imagens.png, CNN.png, MobileNet.png,
│                                            # comparacao.png, distribuicao.png, predicao.png,
│                                            # pre_processamento.png, assistente*_web.png, app.jpeg
├── Parte1e2/
│   └── Fase4_Cap1 (1).ipynb                 # 889 KB
└── Ir_Alem2/
    ├── backend/
    │   ├── app.py
    │   ├── mobilenet_pneumonia.keras        # 11.589.128 bytes
    │   └── requirements.txt
    └── cardio-assistant/                    # app Expo Router (web + mobile)
        ├── App? (usa app/ + screens/) · app.json · package.json · tsconfig.json
        ├── eslint.config.js · expo-env.d.ts · AGENTS.md · CLAUDE.md · .gitignore
        ├── app/
        │   ├── _layout.tsx · modal.tsx
        │   └── (tabs)/ index.tsx · explore.tsx · _layout.tsx
        ├── components/                      # external-link, haptic-tab, hello-wave,
        │   │                                # parallax-scroll-view, themed-text, themed-view
        │   └── ui/ collapsible.tsx · icon-symbol.tsx · icon-symbol.ios.tsx
        ├── constants/ api.ts · theme.ts
        ├── hooks/ use-color-scheme.ts · use-color-scheme.web.ts · use-theme-color.ts
        ├── screens/HomeScreen.js
        ├── utils/uploadImage.ts
        ├── scripts/reset-project.js
        └── assets/images/                   # ícones, splash, logos
```

*(O relatório de ética está em `Ir_Alem/Relatorio_Etica_Govern.pdf`.)*

### 6.5 Fase 5 — `Fase5_CardioAssist`

```text
Fase5_CardioAssist/
├── README.md
├── .gitignore
├── CardioAssist_Relatorio.pdf
├── assets/                                  # Watsonx.png, editor.png, "Dor no peito.png",
│                                            # chat.png, chat2.png, cardio_cel.png, cardio_web.png
├── Backend/
│   ├── app.py                               # GET /health · POST /api/chat
│   ├── IBM_API.py                           # cliente + credenciais Watson (🔴 versionadas)
│   ├── requirements.txt
│   └── .env.example
└── CardioAssist/
    ├── App.js · index.js · app.json · package.json · LICENSE
    ├── .env.example
    ├── assets/                              # ícones e splash
    └── src/
        ├── theme.js
        ├── components/                      # ChatHeader.js, ChatInput.js, ErrorBanner.js,
        │                                    # MessageBubble.js, TypingIndicator.js
        ├── constants/api.js
        ├── screens/ChatScreen.js
        └── services/watsonApi.js
```

### 6.6 Fase 6 — `cardioia_Fase6`

Ver a árvore completa na seção 3.6. Resumo: `data/`, `docs/`, `models/`, `notebooks/`,
`src/cardioia/{ml,knowledge,schemas,agents}/`, `tests/`, mais `conftest.py`, `pytest.ini`,
`requirements.txt`, `.env.example` e `.gitignore`.

---

## 7. Funcionalidades existentes

### 7.1 O que está funcional (executável)

| Fase | Funcionalidade | Como se comprova |
|---|---|---|
| 1 | Seleção amostral de 200 imagens de raio-X preservando a proporção de classes | notebook `Cap1_Dados_Imagens_Selecao.ipynb` + pasta com 200 PNGs |
| 2 | Classificação de sintomas por regras e geração da base de conhecimento | `Criar_Dados.py` → CSV; `Identificar_Sintomas.py` → diagnóstico impresso |
| 2 | Visualização da ontologia sintomas↔doenças | `Visualizar_Ontologia.py` (networkx/matplotlib) |
| 2 | Classificação de risco em texto com TF-IDF + Regressão Logística | notebook com acurácia 0,833 e teste em 4 frases novas |
| 2 | Portal web com login simulado, dashboard, lista de pacientes e agendamento | `npm run dev` (Vite) na pasta `my-react-app` |
| 3 | Coleta local resiliente no ESP32 com FIFO de 10 registros e sincronização offline→online | firmware Parte 1 (Wokwi) |
| 3 | Telemetria MQTT publicando `hospital/temperatura` e `hospital/bpm` para HiveMQ Cloud | firmware Parte 2 + dashboard Node-RED |
| 3 | API REST de sinais vitais com detecção de febre/taquicardia/ausência de movimento e alerta por e-mail | `server.py` + `client.py` |
| 3 | Comparação Regressão Logística × modelo neuromórfico LIF (0,985) | notebook Ir_Alem2 |
| 4 | Classificação binária de radiografia (Normal/Pneumonia) via API | `POST /predict` com o `.keras` presente |
| 4 | App mobile/web para selecionar e enviar imagem de raio-X e exibir o resultado | `HomeScreen.js` + Expo |
| 5 | Conversa com o assistente Watson via API própria, com sessão e tratamento de erros | `POST /api/chat` |
| 5 | App de chat mobile/web com sugestões rápidas, indicador de digitação e retry | `ChatScreen.js` + Expo |
| 6 | Treino, avaliação e persistência do modelo `pico_risco` | `python -m src.cardioia.ml.train` |
| 6 | Inferência validada com contrato de entrada e metadados de rastreabilidade | `predict.prever_pico_risco()` |
| 6 | Aplicação determinística das 10 regras de protocolo | `protocols.avaliar_protocolos()` |
| 6 | Pipeline multiagente com 4 agentes, handoffs, tools, contexto tipado e contrato Pydantic | `python -m src.cardioia.main` (simulado ou real) |
| 6 | Suíte de 290 testes automatizados (sem internet e sem API paga) | `python -m pytest tests -q` |

### 7.2 O que é apenas simulação, protótipo ou notebook (não é produto)

| Item | Fase | Natureza |
|---|---|---|
| Login e token JWT | 2 | **Fake**: credenciais fixas no código e token previsível em `localStorage` (🔒 valores mascarados). Não há verificação no servidor. |
| Lista de pacientes | 2 | Consome `jsonplaceholder.typicode.com` (API pública de demonstração), não um prontuário. |
| Agendamento de consultas | 2 | Estado local de UI, sem persistência nem backend. |
| Wi-Fi do ESP32 (Parte 1) | 3 | `wifiConnected` é uma variável booleana alternada no loop — não há rede real. |
| BPM | 3 | Simulado por botão (`random(60,140)`) — não há sensor de batimento. |
| Envio de e-mail | 3 | Depende de `EMAIL_SENHA` (placeholder `"SECRET"`); sem credencial válida o `except` apenas imprime o erro. |
| Modelos das Fases 2 e 3 | 2, 3 | Treinados apenas em memória do notebook; **não persistidos**. |
| Base de dados da Fase 6 | 6 | 100% sintética e gerada por regras (`np.random.seed(42)`); o alvo é função determinística das features. |
| Protocolos da Fase 6 | 6 | Limiares **de projeto** (material da aula), explicitamente não validados clinicamente. |
| Modo `simulado` da Fase 6 | 6 | Substitui a decisão de rota do LLM por um roteiro determinístico (mantendo SDK, handoffs e tools reais). |
| Configuração do Watson (Fase 5) | 5 | Vive na plataforma IBM; não há artefato versionado no repositório. |

### 7.3 Funcionalidades ausentes em todas as fases

- **Autenticação/autorização reais** (nenhuma fase valida credenciais em servidor).
- **Banco de dados** (nenhuma fase usa SQL/NoSQL; tudo é arquivo, `localStorage` ou memória).
- **API unificada / gateway** entre os módulos.
- **Integração entre fases** (nenhum módulo consome outro).
- **Logs estruturados / observabilidade** (apenas `print` e `debug=True`).
- **Containerização / deploy** (nenhum `Dockerfile`, `docker-compose` ou pipeline de CI).
- **Versionamento de API / OpenAPI** (nenhum contrato formal de endpoints).
- **Testes automatizados** fora da Fase 6.

---

## 8. APIs disponíveis

### 8.1 Endpoints implementados no workspace

| Fase | Serviço | Método | Rota | Entrada | Saída | Porta |
|---|---|---|---|---|---|---|
| 3 | `Ir_Alem1/server.py` (Flask) | `POST` | `/sinais` | JSON: `{"temperatura": float, "bpm": int, "movimento": bool}` | `{"status": "ALERTA"\|"NORMAL", "mensagem": str}` | 5000 |
| 4 | `Ir_Alem2/backend/app.py` (Flask) | `GET` | `/health` | — | `{"status": "ok", "model": "mobilenet_pneumonia.keras"}` | 5000 |
| 4 | `Ir_Alem2/backend/app.py` (Flask) | `POST` | `/predict` | `multipart/form-data`, campo `image` | `{"class": "Normal"\|"Pneumonia", "confidence": float}` | 5000 |
| 5 | `Backend/app.py` (Flask) | `GET` | `/health` | — | `{"status": "ok", "service": "cardioassist-backend", "watson_configured": bool, "missing": [str]}` | 5000 |
| 5 | `Backend/app.py` (Flask) | `POST` | `/api/chat` | JSON: `{"message": str, "session_id": str\|null, "user_id": str}` | `{"reply": str, "session_id": str, "timestamp": ISO-8601}` | 5000 |

**Códigos de erro relevantes:**
- Fase 3: nenhum tratamento explícito (sem `try/except` no parsing do JSON);
- Fase 4: `400` (campo ausente/vazio), `500` (falha de processamento);
- Fase 5: `400` (mensagem vazia), `501` (não configurado), `429` (cota), `502` (erro do Watson),
  `504` (timeout), `507` (falha de autenticação).

> ⚠️ **Conflito de porta:** as três APIs sobem na **porta 5000** (`app.run(... port=5000)`). Não podem
> coexistir sem reconfiguração.

### 8.2 Protocolos de comunicação (não-HTTP)

| Fase | Protocolo | Detalhe |
|---|---|---|
| 3 | **MQTT over TLS** | Broker HiveMQ Cloud (host `<cluster-id>.s1.eu.hivemq.cloud`) na porta `8883`; tópicos `hospital/temperatura`, `hospital/bpm`; clientId `ESP32Client` |
| 3 | **SMTP** | `smtp.gmail.com:587` + `starttls()`, remetente/destino em conta Gmail pessoal (🔒 endereço mascarado) |
| 3 | **Serial (UART)** | 115200 baud — usada como "nuvem" na Parte 1 |

### 8.3 APIs externas consumidas

| Fase | Serviço | Uso | Forma |
|---|---|---|---|
| 2 | `jsonplaceholder.typicode.com` | `GET /users` para a lista de pacientes | `fetch` no browser |
| 5 | IBM watsonx Assistant v2 | `create_session`, `message` | SDK `ibm-watson` (`AssistantV2` + `IAMAuthenticator`) |
| 6 | OpenAI API | LLM dos 4 agentes (somente `--modo real`) | OpenAI Agents SDK (`Runner.run_sync`) |

### 8.4 API pública da Fase 6 (não-HTTP, mas é a interface de integração mais importante)

| Símbolo | Assinatura / forma |
|---|---|
| `orchestrator.executar_pipeline` | `executar_pipeline(paciente, modo="simulado", raiz=None, pasta_modelos=None, limiar=0.5, modelo_simulado=None, max_turnos=10, entrada=ENTRADA_PADRAO, modelo=None) -> RespostaDaExecucao` |
| `predict.prever_pico_risco` | `prever_pico_risco(paciente, caminho_modelo=None, pasta_modelos=None, raiz=None, limiar=0.5, modelo=None, metadados=None) -> dict` |
| `predict.prever_varios` | `prever_varios(pacientes, ...) -> list[dict]` |
| `predict.resumo_para_agente` | `resumo_para_agente(resultado) -> str` |
| `protocols.avaliar_protocolos` | `avaliar_protocolos(paciente, pico_risco_previsto, protocolos=None, raiz=None) -> AvaliacaoDosProtocolos` |
| `protocols.avaliar_protocolos_seguro` | `avaliar_protocolos_seguro(...) -> (AvaliacaoDosProtocolos \| None, list[str])` |
| `risk_result.RespostaDaExecucao.como_dicionario()` | Contrato JSON-safe — **o formato natural para um endpoint HTTP da Fase 7** |
| CLI | `python -m src.cardioia.main [--json] [--modo real] [--paciente ...]` |

---

## 9. Modelos de IA

### 9.1 Inventário de modelos

| Fase | Modelo / técnica | Algoritmo / arquitetura | Dataset | Métrica registrada | Artefato persistido | Reprodutível? |
|---|---|---|---|---|---|---|
| 2 | Classificador de sintomas (regras) | Busca por substring + pontuação | `mapa_sintomas_doencas.csv` (25 registros) | não declarada (saída textual) | ❌ (lógica no `.py`) | ✅ (script + CSV) |
| 2 | Classificador de risco textual | TF-IDF + **LogisticRegression** | `frases_risco.csv` (40 frases) | **acurácia 0,8333** | ❌ | ✅ (notebook + CSV) |
| 2 | Classificador de risco textual | TF-IDF + **DecisionTreeClassifier** | `frases_risco.csv` | **acurácia 0,6667** | ❌ | ✅ |
| 3 | Detector de taquicardia (série temporal) | **LogisticRegression** | série sintética de batimentos | comparada com o LIF (valor exato não declarado no README) | ❌ | ✅ (notebook) |
| 3 | Detector de taquicardia (neuromórfico) | **LIF** (`LIFNeuron`, `threshold=25`, regra `spikes>=2 or media>100`) | série sintética de batimentos | **acurácia 0,985** | ❌ | ✅ (notebook) |
| 4 | Classificador de pneumonia | **CNN do zero** (3.304.769 params, 10 camadas) | Chest X-Ray Pneumonia (Kaggle) | comparada com MobileNetV2 (valores não transcritos no README) | ❌ | ✅ (notebook) |
| 4 | Classificador de pneumonia | **MobileNetV2 (Transfer Learning)** — escolhido | Chest X-Ray Pneumonia | prioriza detecção de casos positivos | ✅ **`mobilenet_pneumonia.keras`** (11,5 MB) | ✅ (notebook + `.keras`) |
| 6 | Previsão de `pico_risco` | **LogisticRegression** (pipeline + StandardScaler) | `base_dados.py` (5.000 sintéticos) | acurácia **0,8160**, recall 0,5526, F1 0,6151 | ❌ (não escolhido) | ✅ (`python -m src.cardioia.ml.train`) |
| 6 | Previsão de `pico_risco` | **RandomForestClassifier** (300 árvores, semente 42) — escolhido | `base_dados.py` | acurácia **0,9990**, recall **0,9962**, F1 0,9981 | ✅ **`models/modelo_pico_risco.pkl`** (4,7 MB) + metadata | ✅ |
| 6 | Regra determinística (teto) | Soma booleana de 6 indicadores | `base_dados.py` | acurácia **1,0** (por construção) | ❌ (implementada em Python) | ✅ |

### 9.2 Modelos de linguagem (LLM)

| Fase | LLM / serviço | Uso | Modelo declarado |
|---|---|---|---|
| 5 | IBM watsonx Assistant v2 | Assistente conversacional (NLU, entidades, actions, skills) | configuração na plataforma IBM; modelo de linguagem não declarado **[DESCONHECIDO]** |
| 6 | OpenAI (via Agents SDK) | LLM dos 4 agentes no `--modo real` | default `gpt-4o-mini` (`.env.example`); alternável por `--modelo` ou `OPENAI_MODEL` |

### 9.3 Observações críticas sobre os modelos

1. **Os modelos das Fases 2 e 3 não existem como artefato** — só é possível reobter os resultados
   reexecutando os notebooks.
2. **Só dois modelos estão prontos para consumo direto:** `mobilenet_pneumonia.keras` (Fase 4) e
   `modelo_pico_risco.pkl` (Fase 6).
3. **As métricas da Fase 6 não medem capacidade preditiva real:** o alvo é uma função determinística
   de 6 features presentes na entrada; o Random Forest essencialmente reconstrói a regra (o próprio
   README é explícito sobre isso).
4. **Os limiares são de projeto, não clínicos** — vale para os protocolos da Fase 6 e para as regras
   da Fase 3 (`>38 °C`, `>120 bpm`).

---

## 10. Agentes e LLMs

### 10.1 Sistema multiagentes (Fase 6) — detalhamento já apresentado

O detalhamento completo (agentes, handoffs, tools, contexto tipado, modelo simulado, contrato
Pydantic e verificações de integridade) está na **seção 3.6**. Resumo executivo:

| Item | Valor |
|---|---|
| SDK | **OpenAI Agents SDK** (`openai-agents==0.18.1`, `openai==2.38.0`) |
| Nº de agentes | **4** (Orquestrador, Analista de Risco, Especialista em Protocolos, Planejador de Resposta) |
| Handoffs | 3, unidirecionais, **reais** do SDK (`transfer_to_*`) |
| Tools | 2 (`consultar_modelo_de_risco`, `consultar_protocolos`) — **sem argumentos** por decisão de segurança |
| Contexto | `ContextoDaExecucao` (tipado, **nunca** enviado ao LLM) |
| Hooks | `TrilhaDeExecucao(RunHooks)` registra agentes, handoffs e tools |
| Saída | `RespostaDaExecucao` (Pydantic, `extra="forbid"`) montada em Python após o run |
| Modo simulado | `ModeloComRoteiro` implementa `Model`/`ModelProvider` do SDK — sem API, sem custo |
| Modo real | Exige `OPENAI_API_KEY`; `tracing_disabled=True`; default `gpt-4o-mini` |
| Princípio central | **Python calcula; o LLM apenas redige** — nenhum número crítico vem do texto do modelo |

### 10.2 Papel do LLM em cada fase

| Fase | Há LLM? | Papel |
|---|---|---|
| 1 | Não | — |
| 2 | Não | NLP clássico (regras + TF-IDF + sklearn) |
| 3 | Não | Regras determinísticas + sklearn + modelo neuromórfico |
| 4 | Não | CNN / transfer learning |
| 5 | **Sim** | IBM watsonx Assistant (NLU conversacional gerenciado) |
| 6 | **Sim (opcional)** | 4 agentes do Agents SDK decidem **quando** consultar tools e **como** redigir; os valores vêm do Python |

### 10.3 LLM na Fase 6 — o que o modelo decide e o que não decide

| Decide (LLM) | **Nunca** decide (Python) |
|---|---|
| Quando fazer o handoff | A probabilidade de `pico_risco` |
| Quando chamar cada tool | A classe prevista e o limiar |
| Como redigir a narrativa final | Quais protocolos se aplicam e com quais valores |
| Preencher `pontos_de_atencao` | O status final da execução |

Se a narrativa citar um número divergente da probabilidade calculada, o orquestrador marca
`CONCLUIDO_COM_RESSALVAS` — o texto do LLM **nunca** sobrepõe o valor da tool.

---

## 11. Implementação IoT (Fase 3)

O detalhamento completo (firmware Parte 1 e Parte 2, API REST + SMTP e modelos do Ir Além 2) está na
**seção 3.3**. Resumo da arquitetura em camadas:

```text
┌──────────────────────── EDGE ────────────────────────┐
│ ESP32 + DHT22 (temp/umidade, pino 15)                │
│       + LDR   (luminosidade, pino 34)                │
│ Buffer local FIFO de 10 registros (resiliência       │
│ offline) · simulação de Wi-Fi por booleano           │
└───────────────┬──────────────────────────────────────┘
                │ Wi-Fi (Wokwi-GUEST)
                ▼
┌──────────────────────── FOG ─────────────────────────┐
│ Node-RED: processamento intermediário +              │
│ node-red-dashboard (visualização)                    │
└───────────────┬──────────────────────────────────────┘
                │ MQTT/TLS 8883
                ▼
┌─────────────────────── CLOUD ────────────────────────┐
│ HiveMQ Cloud (broker)                                │
│ tópicos: hospital/temperatura · hospital/bpm         │
└──────────────────────────────────────────────────────┘

Fluxo alternativo (Ir Além 1 — REST + SMTP):
client.py (sinais simulados) ──HTTP POST /sinais──▶ Flask ──regras──▶ smtplib/SMTP Gmail ──▶ e-mail
```

| Camada | Componente | Implementação concreta |
|---|---|---|
| Edge | ESP32 (firmware C) | `Parte1/codigo_ESP32.c`, `Parte2/codigo_parte2.c` |
| Fog | Node-RED + dashboard | fora do repositório (não versionado) |
| Cloud | Broker MQTT | HiveMQ Cloud |
| Aplicação | API REST Flask + SMTP | `Ir_Alem1/server.py`, `Ir_Alem1/client.py` |
| Analytics | sklearn + LIF | `Ir_Alem2/Cap1CardioIA_Ir_Alem2ipynb.ipynb` |

**Sensores e sinais disponíveis na Fase 3:** temperatura, umidade, luminosidade, BPM (simulado) e
movimento (presente no payload REST, ausente no firmware). **Sinais que o modelo da Fase 6 exige e
que a Fase 3 não produz:** `idade_media`, `carga_sistema`, `tempo_espera`, `spo2_media`,
`pa_sistolica`, `densidade_eventos`, `eventos_24h`, `disponibilidade_recursos` (ver seção 15.3).

---

## 12. Mecanismos de autenticação

### 12.1 Inventário

| Fase | Mecanismo | Implementação real | Força |
|---|---|---|---|
| 1 | **Nenhum** | — | — |
| 2 | **Simulação client-side** | `AuthContext.jsx`: `login(email, senha)` compara com credenciais **fixas no código** (🔒 mascaradas) e grava um token previsível no `localStorage`; `ProtectedRoute` só verifica a presença do token | ⚠️ Fraca — não há validação em servidor; token previsível |
| 3 | **Nenhum** na API REST; **credenciais de infraestrutura** hardcoded | MQTT (`mqtt_user`/`mqtt_pass`) e SMTP (`EMAIL_SENHA`) — 🔒 valores mascarados | ⚠️ Crítica — segredos no código |
| 4 | **Nenhum** | A API `/predict` é aberta (apenas CORS habilitado) | ⚠️ Sem controle de acesso |
| 5 | **IAM (API key do IBM Cloud)** | `IAMAuthenticator(API_KEY)` no `IBM_API.py`; **a chave está versionada** | 🔴 Crítica — chave real no repositório |
| 6 | **Chave de API do provedor LLM** | `OPENAI_API_KEY` **somente por variável de ambiente** (nunca em código); o `.gitignore` exclui `.env`; há teste (`test_seguranca.py`) que verifica ausência de segredos | ✅ Boa prática entre as fases |

### 12.2 Consequências para a Fase 7

1. **Não existe identidade de usuário** em nenhum módulo — não há como atribuir uma requisição a um
   médico, paciente ou operador.
2. **Não existe autorização por papel** (médico, enfermeiro, administrador).
3. **A única "autenticação" de usuário** é a simulação da Fase 2, que pode servir como **protótipo de
   UX** de login, mas **não** como base de segurança.
4. **Há credenciais de produção expostas** (Fase 5 Watson, Fase 3 HiveMQ/Gmail) que precisam ser
   **rotacionadas** e movidas para variáveis de ambiente antes de qualquer publicação.
5. **A Fase 6 é o único módulo que segue a prática correta** de manter segredo fora do código —
   pode servir de referência de padrão para as demais.

---

## 13. Como cada módulo pode ser executado

### 13.1 Fase 1 — Notebooks e arquivos de dados

```bash
# Não há aplicação executável. Uso típico:
jupyter lab            # abrir Imagens/Cap1_Dados_Imagens_Selecao.ipynb
```

Os dados (CSV/PNG/PDF) são consumidos por leitura direta de arquivo. **Não há `requirements.txt`**
nesta fase (as dependências do notebook não estão declaradas).

### 13.2 Fase 2 — Scripts Python + portal React

```powershell
# Scripts Python (Parte 1 e Parte 2)
pip install -r requirements.txt
python Parte_1\Criar_Dados.py
python Parte_1\Identificar_Sintomas.py
python Parte_1\Visualizar_Ontologia.py
jupyter lab            # Parte_2\Classificador_TF_IDF.ipynb

# Portal web (Ir Além)
cd Ir_Alem\my-react-app
npm install
npm run dev            # Vite (dev server)
npm run build          # build de produção
npm run lint
```

> ⚠️ Os scripts Python têm **caminho absoluto hardcoded** para a pasta antiga
> (`...\Área de Trabalho\Cap2_Desafio_Integrador\...`). Para executá-los a partir desta estrutura é
> necessário ajustar os caminhos — **o que não foi feito nesta etapa** (restrição: não modificar as
> fases anteriores).

### 13.3 Fase 3 — Firmware, API REST e notebook

```text
Firmware (Wokwi / Arduino IDE):
  - Parte1/codigo_ESP32.c        → Wokwi: https://wokwi.com/projects/463496096459659265
  - Parte2/codigo_parte2.c       → Wokwi: https://wokwi.com/projects/463502084128323585
  Requer: bibliotecas WiFi, WiFiClientSecure, PubSubClient, DHTesp

Node-RED (externo):
  - instalar node-red + node-red-dashboard
  - configurar o fluxo MQTT apontando para o broker HiveMQ Cloud

API REST (Ir Além 1):
  cd Ir_Alem1
  pip install flask requests
  python server.py     # http://localhost:5000  (rota POST /sinais)
  python client.py     # envia sinais a cada 5 s

Notebook (Ir Além 2):
  jupyter lab   → Ir_Alem2/Cap1CardioIA_Ir_Alem2ipynb.ipynb
```

### 13.4 Fase 4 — Backend Flask + app Expo

```powershell
# Backend
cd Ir_Alem2\backend
pip install -r requirements.txt      # flask, flask-cors, tensorflow, pillow, numpy
python app.py                        # http://localhost:5000
Invoke-RestMethod http://localhost:5000/health

# App
cd ..\cardio-assistant
npm install
npx expo start                       # 'w' web | 'a' Android | 'i' iOS | QR no Expo Go
```

> ⚠️ O README menciona ativar `..\venv\Scripts\Activate.ps1`, mas **`venv/` não existe** no
> workspace — é necessário criar o ambiente.

### 13.5 Fase 5 — Backend Flask + app Expo

```powershell
# Backend
cd Backend
pip install -r requirements.txt
python app.py                        # http://localhost:5000

# App
cd ..\CardioAssist
npm install
npx expo start
```

**Configuração opcional:** criar `Backend/.env` a partir de `Backend/.env.example` com
`WATSON_API_KEY`, `WATSON_SERVICE_URL`, `WATSON_ASSISTANT_ID`, `WATSON_ENVIRONMENT_ID`.
Sem essas variáveis, os **defaults hardcoded** em `IBM_API.py` são usados.

### 13.6 Fase 6 — CLI Python

```bash
cd cardioia_Fase6

# 1) Ambiente
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 2) (Se necessário) treinar o modelo — o artefato já está versionado
python -m src.cardioia.ml.train

# 3) Executar o pipeline
python -m src.cardioia.main                 # modo simulado (padrão)
python -m src.cardioia.main --json          # contrato completo em JSON
python -m src.cardioia.main --quiet         # apenas o status
python -m src.cardioia.main --modo real     # exige OPENAI_API_KEY
python -m src.cardioia.main --paciente '{"idade_media":62,"carga_sistema":92}'

# 4) Testes
python -m pytest tests -q
python -m pytest tests/test_integracao_real.py -m integracao   # consome API paga
```

### 13.7 Tabela resumo de execução

| Fase | Comando principal | Porta | Pré-requisito crítico |
|---|---|---|---|
| 1 | `jupyter lab` | — | Jupyter + libs do notebook (não declaradas) |
| 2 | `npm run dev` (Vite) · `python *.py` | 5173 (padrão Vite) | Node 20/22; ajustar caminhos absolutos dos scripts |
| 3 | `python server.py` · Wokwi | 5000 | Flask, requests; broker HiveMQ; credenciais de e-mail |
| 4 | `python app.py` · `npx expo start` | 5000 | TensorFlow + o `.keras`; Node; criar o venv |
| 5 | `python app.py` · `npx expo start` | 5000 | ibm-watson; credenciais Watson válidas |
| 6 | `python -m src.cardioia.main` | — (CLI) | Python 3.10+; `models/*.pkl`; `OPENAI_API_KEY` só no modo real |

---

## 14. Dependências externas, credenciais e configurações necessárias

### 14.1 Dependências declaradas por fase

| Fase | Arquivo | Conteúdo | Versões fixadas? |
|---|---|---|---|
| 1 | *(nenhum)* | — | — |
| 2 | `requirements.txt` | `pandas>=2.1,<3`; `scikit-learn>=1.4,<2`; `numpy>=1.26,<3`; `jupyterlab>=4,<5` | faixas |
| 2 | `Ir_Alem/my-react-app/package.json` | react 19.2.4 · react-dom 19.2.4 · react-router-dom 7.13.2 · vite 8.0.1 · @vitejs/plugin-react 6.0.1 · eslint 9.39.4 · globals 17.4.0 · @types/react* | ✅ |
| 3 | *(nenhum)* | README cita: Flask, Requests, SMTP, Node-RED, node-red-dashboard | — |
| 4 | `Ir_Alem2/backend/requirements.txt` | `flask`, `flask-cors`, `tensorflow`, `pillow`, `numpy` | ❌ **sem versões** |
| 4 | `cardio-assistant/package.json` | expo ~54.0.34 · expo-router ~6.0.23 · react-native 0.81.5 · react 19.1.0 · expo-image-picker ~17.0.8 · @react-navigation/* · reanimated ~4.1.1 · typescript ~5.9.2 | ✅ |
| 5 | `Backend/requirements.txt` | `flask`, `flask-cors`, `python-dotenv`, `ibm-watson`, `ibm-cloud-sdk-core` | ❌ **sem versões** |
| 5 | `CardioAssist/package.json` | expo ~57.0.20 · expo-constants ~57.0.17 · react 19.2.3 · react-native 0.86.3 · react-native-web ^0.21.2 | ✅ |
| 6 | `requirements.txt` | numpy 2.2.6 · pandas 2.3.2 · scikit-learn 1.8.0 · joblib 1.5.3 · pytest 9.1.1 · openai-agents 0.18.1 · openai 2.38.0 · pydantic 2.14.1 · starlette 0.48.0 · sse-starlette 2.3.5 | ✅ **fixadas** |

**Dependências não declaradas (usadas mas ausentes dos manifestos):** `networkx` e `matplotlib`
(Fase 2 — `Visualizar_Ontologia.py`), `seaborn` (Fase 3 — notebook), `requests` (Fase 3 — `client.py`,
apenas citado no README), `flask` (Fase 3 — sem `requirements.txt`).

### 14.2 Credenciais e variáveis de ambiente

| Fase | Nome | Onde está definida | Valor presente no repositório? | Risco |
|---|---|---|---|---|
| 2 | usuário/senha do login | `AuthContext.jsx` | 🔒 credenciais fixas + token previsível (mascarados) | Baixo (é simulação) |
| 3 | `mqtt_user` / `mqtt_pass` | `Parte2/codigo_parte2.c` | 🔒 valores literais no código (mascarados aqui) | 🔴 Alto |
| 3 | `EMAIL_REMETENTE` / `EMAIL_DESTINO` / `EMAIL_SENHA` | `Ir_Alem1/server.py` | 🔒 endereço Gmail pessoal + placeholder `"SECRET"` (mascarados aqui) | ⚠️ Médio |
| 4 | `EXPO_PUBLIC_API_URL` | `constants/api.ts` (opcional) | não | — |
| 5 | `WATSON_API_KEY` | `Backend/IBM_API.py` (default) e `.env.example` | 🔒 **chave de API real presente como default** (mascarada aqui) | 🔴 **Crítico** |
| 5 | `WATSON_SERVICE_URL` | idem | 🔒 URL regional + id da instância (mascarados) | ⚠️ Médio |
| 5 | `WATSON_ASSISTANT_ID` | idem | 🔒 UUID do assistente (mascarado) | ⚠️ Médio |
| 5 | `WATSON_ENVIRONMENT_ID` | idem | 🔒 UUID do ambiente (mascarado) | ⚠️ Médio |
| 5 | `EXPO_PUBLIC_API_URL` | `CardioAssist/.env.example` (opcional) | não (exemplo `http://192.168.15.16:5000`) | — |
| 6 | `OPENAI_API_KEY` | `.env.example` (**vazio**) | ✅ **não** — só o nome da variável | ✅ Boa prática |
| 6 | `OPENAI_MODEL` | `.env.example` | `gpt-4o-mini` (valor de exemplo) | — |

### 14.3 Arquivos de configuração presentes

| Fase | Arquivo | Observação |
|---|---|---|
| 1 | — | nenhum |
| 2 | `my-react-app/.gitignore`, `eslint.config.js`, `vite.config.js`, `index.html` | Vite sem proxy configurado |
| 3 | — | configuração estática dentro do código C |
| 4 | `cardio-assistant/app.json`, `tsconfig.json`, `eslint.config.js`, `expo-env.d.ts`, `AGENTS.md`, `CLAUDE.md` | `AGENTS.md` orienta a consultar os docs do Expo v54 |
| 5 | `Backend/.env.example`, `CardioAssist/.env.example`, `app.json`, `.gitignore` | `.gitignore` presente, mas as credenciais foram versionadas em `IBM_API.py` |
| 6 | `.env.example`, `.gitignore`, `pytest.ini`, `conftest.py` | `.gitignore` versiona explicitamente `data/*.py` e `models/*` |

### 14.4 Requisitos de ambiente por fase

| Fase | Python | Node | Outros |
|---|---|---|---|
| 1 | (não declarado) | — | Jupyter |
| 2 | 3.10–3.12 | 20.x ou 22.x LTS | — |
| 3 | 3.10–3.12 | 20.x ou 22.x LTS | Arduino IDE ou Wokwi; Node-RED; conta HiveMQ Cloud; conta Gmail com senha de app |
| 4 | 3.10+ | 18+ | Expo Go ou emulador Android/iOS; TensorFlow |
| 5 | (não declarado) | (não declarado) | instância Watson ativa; Expo Go ou emulador |
| 6 | 3.10+ (validado em 3.13.5) | — | `OPENAI_API_KEY` apenas para o modo real |

### 14.5 Conflitos de dependências já conhecidos

| Conflito | Detalhe |
|---|---|
| `gradio` × `openai-agents` | `gradio 5.49.1` declara `pydantic<2.12`; `openai-agents 0.18.1` exige `pydantic>=2.12.2` — insatisfazíveis juntos (documentado no `requirements.txt` da Fase 6) |
| `fastapi` × `sse-starlette` | `fastapi 0.119.0` exige `starlette<0.49.0`; `sse-starlette 3.x` exige `starlette>=0.49.1` — resolvido fixando `starlette 0.48.0` + `sse-starlette 2.3.5` |
| Python × scikit-learn | Fase 6 requer sklearn 1.8.0/Python 3.13.5; Fase 2 recomenda Python 3.10–3.12 com sklearn 1.4 — **ambientes incompatíveis** se compartilhados |
| pickle do modelo | `.pkl` treinado com sklearn 1.2.2 é recusado pelo 1.8.0 (`ModeloIncompativelError` documentado no código) |
| porta 5000 | Fases 3, 4 e 5 disputam a mesma porta |

---

## 15. Possibilidades de reutilização

### 15.1 Componentes reutilizáveis por grau de prontidão

| Componente | Fase | Prontidão para reuso | Forma de reuso na Fase 7 |
|---|---|---|---|
| `src/cardioia/` (pacote completo) | 6 | 🟢 **Alta** | Importar direto como biblioteca; expor `executar_pipeline` via HTTP |
| `RespostaDaExecucao` (contrato Pydantic) | 6 | 🟢 **Alta** | Usar como **schema canônico** de resposta da API unificada |
| `predict.prever_pico_risco` + `modelo_pico_risco.pkl` | 6 | 🟢 **Alta** | Motor de decisão de risco; aceita dados de qualquer fase |
| `knowledge/protocols.py` (10 regras determinísticas) | 6 | 🟢 **Alta** | Camada de protocolos reutilizável por qualquer serviço |
| Agentes + handoffs + tools | 6 | 🟢 **Alta** | Núcleo de orquestração; novas tools = novas fases integradas |
| `ContextoDaExecucao` / `TrilhaDeExecucao` | 6 | 🟢 **Alta** | Padrão de auditoria reutilizável para rastrear execuções |
| Suíte de 290 testes | 6 | 🟢 **Alta** | Base de regressão ao integrar novos módulos |
| `mobilenet_pneumonia.keras` + `POST /predict` | 4 | 🟡 **Média** | Tool/serviço de visão computacional; precisa ajustar porta |
| `GET /health` + `POST /api/chat` (Watson) | 5 | 🟡 **Média** | Camada conversacional; requer credenciais válidas |
| `watsonApi.js` (tratamento de erros) | 5 | 🟡 **Média** | Padrão reutilizável de cliente HTTP com timeout e erros amigáveis |
| `constants/api.js` / `constants/api.ts` (detecção de URL) | 4, 5 | 🟡 **Média** | Padrão de configuração de endpoint para apps Expo |
| `POST /sinais` + regras de alerta | 3 | 🟡 **Média** | Ingestão de telemetria IoT; regras podem virar indicadores |
| `AuthContext` + `ProtectedRoute` | 2 | 🟡 **Média** | Esqueleto de UX de autenticação (não de segurança) |
| Portal React (Dashboard/Patients/Schedule) | 2 | 🟡 **Média** | Base visual do painel unificado |
| `Identificar_Sintomas.py` (NLP por regras) | 2 | 🟠 **Baixa** | Candidato a tool de triagem textual; requer refatoração (caminhos absolutos, sem função isolada) |
| Classificador TF-IDF (notebook) | 2 | 🟠 **Baixa** | Sem artefato persistido; exige retreino e persistência |
| Modelos LIF / Regressão Logística | 3 | 🟠 **Baixa** | Sem artefato persistido; notebooks de estudo |
| Firmware ESP32 | 3 | 🟠 **Baixa** | Referência de arquitetura Edge; sinais não cobrem as features da Fase 6 |
| `heart_disease_uci.csv`, 200 PNGs, PDFs | 1 | 🟠 **Baixa** | Não utilizados nas fases seguintes; úteis como corpus/dataset alternativo |

### 15.2 Padrões arquiteturais que podem ser padronizados na Fase 7

| Padrão observado | Onde | Como padronizar |
|---|---|---|
| Backend Flask + CORS + porta 5000 | Fases 3, 4, 5 | Unificar sob um gateway com *path prefixes* (`/iot`, `/imagem`, `/chat`, `/risco`) |
| Resposta JSON simples | Fases 3, 4, 5 | Adotar envelope comum (`status`, `dados`, `erros`) inspirado no contrato da Fase 6 |
| Detecção de URL do backend no app | Fases 4, 5 | Extrair para um pacote compartilhado |
| Tratamento de erros com códigos nomeados | Fase 5 (`WatsonApiError`) | Replicar para todos os clientes |
| Variáveis de ambiente fora do código | Fase 6 | Aplicar retroativamente às Fases 3 e 5 |
| Contrato de dados + validação estrita | Fase 6 | Adotar como padrão de API entre módulos |
| CLI com códigos de saída semânticos | Fase 6 | Manter para tarefas de operação (treino, diagnóstico) |

### 15.3 Mapa de integração sugerido (visão de alto nível)

```text
┌──────────────────────────── Frontend unificado ────────────────────────────┐
│  Portal web (Fase 2: React + Vite, AuthContext, ProtectedRoute)            │
│  App Expo (Fases 4 e 5: análise de imagem + chat)                          │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    ▼
┌───────────────────── Gateway / API unificada (a criar na Fase 7) ──────────┐
│  /iot/sinais        → Fase 3   (Flask POST /sinais)                        │
│  /imagem/predict    → Fase 4   (Flask POST /predict, MobileNetV2)          │
│  /chat              → Fase 5   (Flask POST /api/chat, Watson)              │
│  /risco/avaliar     → Fase 6   (wrapper HTTP de orchestrator.executar_     │
│                                 pipeline → RespostaDaExecucao.como_       │
│                                 dicionario())                              │
│  /nlp/sintomas      → Fase 2   (NLP por regras + TF-IDF, a empacotar)      │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    ▼
┌───────────────────── Núcleo de decisão (Fase 6) ──────────────────────────┐
│  RandomForest pico_risco · 10 protocolos determinísticos                  │
│  4 agentes (Orquestrador → Risco → Protocolos → Planejador)               │
│  Contexto tipado · trilha de execução · contrato Pydantic                 │
└───────────────────────────────────────────────────────────────────────────┘
```

### 15.4 Gap de dados IoT → modelo de risco (ponto crítico)

| Feature exigida pela Fase 6 | Disponível na Fase 3? | Observação |
|---|---|---|
| `temperatura` | ✅ | DHT22 (Parte 2) / campo do payload REST |
| `fc_media` | ⚠️ parcial | O firmware publica `bpm` (simulado por botão); a Fase 3 não mede FC real |
| `idade_media` | ❌ | não existe no firmware nem no payload REST |
| `carga_sistema` | ❌ | métrica operacional hospitalar, não de sensor |
| `tempo_espera` | ❌ | métrica operacional |
| `spo2_media` | ❌ | não há sensor de SpO₂ |
| `pa_sistolica` | ❌ | não há sensor de pressão arterial |
| `densidade_eventos` | ❌ | métrica derivada |
| `eventos_24h` | ❌ | métrica agregada |
| `disponibilidade_recursos` | ❌ | métrica operacional |

**Consequência:** integrar a Fase 3 diretamente ao modelo da Fase 6 exige definir explicitamente
**de onde vêm as 8 features ausentes** (parametrização manual, valores default documentados ou novos
sensores) — caso contrário o `predict.validar_paciente` **rejeita** a entrada por contrato. Este é um
ponto de decisão obrigatório da Fase 7 e **não** pode ser resolvido por suposição.

---

## 16. Problemas identificados

### 16.1 Segurança

| # | Problema | Fase | Evidência | Severidade |
|---|---|---|---|---|
| S1 | **API key real do IBM Watson versionada** | 5 | `Backend/IBM_API.py` → `API_KEY = os.getenv("WATSON_API_KEY", "<chave-literal>")` — 🔒 valor mascarado | 🔴 **Crítica** |
| S2 | **Credenciais MQTT hardcoded** | 3 | `Parte2/codigo_parte2.c` → `mqtt_user` e `mqtt_pass` literais — 🔒 valores mascarados | 🔴 Alta |
| S3 | **Credenciais SMTP hardcoded** | 3 | `Ir_Alem1/server.py` → `EMAIL_REMETENTE`, `EMAIL_DESTINO`, `EMAIL_SENHA` — 🔒 valores mascarados | ⚠️ Média |
| S4 | **Login simulado com credenciais fixas** | 2 | `AuthContext.jsx` → credenciais fixas + token previsível — 🔒 valores mascarados | ⚠️ Média (é demo) |
| S5 | **APIs sem autenticação** | 3, 4, 5 | `/sinais`, `/predict`, `/api/chat` aceitam qualquer requisição (CORS aberto) | 🔴 Alta |
| S6 | **`debug=True` em todos os backends Flask** | 3, 4, 5 | `app.run(..., debug=True)` — nunca em produção | ⚠️ Média |
| S7 | **TLS sem validação de certificado** | 3 | `espClient.setInsecure()` no firmware | ⚠️ Média |

### 16.2 Portabilidade e configuração

| # | Problema | Fase | Evidência |
|---|---|---|---|
| P1 | **Caminhos absolutos hardcoded nos scripts** | 2 | `C:\Users\Pichau\...\Cap2_Desafio_Integrador\Parte_1\...` em `Criar_Dados.py`, `Identificar_Sintomas.py`, `Gerar_Dataset.py`, `Visualizar_Ontologia.py` |
| P2 | **Caminho absoluto no README** | 4 | `cd "c:\Users\Pichau\OneDrive\Área de Trabalho\Fase_4_Cap1\Ir_Alem2\backend"` (pasta diferente da estrutura atual) |
| P3 | **`venv/` documentado e ausente** | 4 | README instrui `..\venv\Scripts\Activate.ps1`; a pasta não existe no workspace |
| P4 | **Conflito de porta 5000** | 3, 4, 5 | Três backends na mesma porta — impossível rodar em paralelo |
| P5 | **Dependências sem versão** | 4, 5 | `requirements.txt` sem pinos |
| P6 | **Dependências usadas e não declaradas** | 2, 3 | `networkx`, `matplotlib` (Fase 2); `flask`, `requests`, `seaborn` (Fase 3 sem `requirements.txt`) |
| P7 | **`node_modules/` versionado** | 2 | `Ir_Alem/node_modules` presente no repositório |
| P8 | **`package.json` duplicado** | 2 | `Ir_Alem/package.json` (só `react-router-dom`) pode gerar `node_modules` duplicado — o próprio `requirements.txt` alerta sobre isso |

### 16.3 Consistência e documentação

| # | Problema | Fase | Evidência |
|---|---|---|---|
| C1 | **Documentos citados no README e ausentes** | 6 | `docs/plano_implementacao.md`, `docs/relatorio_tecnico.md`, `docs/arquitetura_multiagente.pdf` — só existem `arquitetura.md` e `relatorio_tecnico.pdf` |
| C2 | **Nomenclatura divergente de pasta** | 3 | README cita `Ir_Alem_2`; a pasta é `Ir_Alem2` |
| C3 | **Referência a pasta inexistente** | 6 | `conftest.py` justifica o `sys.path.append` citando `src/agents/` (placeholders da Etapa 1) — a pasta **não existe** no repositório |
| C4 | **Trecho do README aparentemente incompleto** | 3 | Bloco entre as linhas ~94 e ~122 do README não descreve a etapa de visualização com o detalhe das demais |
| C5 | **Contagem de testes anunciada (290) não casa exatamente com a soma por arquivo (281)** | 6 | O restante está em `test_integracao_real.py` e/ou em testes parametrizados |
| C6 | **Idioma misturado (pt-BR/es)** | 5 | `Backend/.env.example` e a docstring de `get_assistant()` em espanhol |

### 16.4 Dados e integração

| # | Problema | Fase | Evidência |
|---|---|---|---|
| D1 | **Dados da Fase 1 nunca reutilizados** | 1 → 2..6 | `heart_disease_uci.csv` e as 200 imagens não aparecem em nenhuma fase posterior |
| D2 | **Dois datasets de imagem distintos** | 1, 4 | Fase 1 usa 200 imagens próprias; Fase 4 usa o dataset Kaggle completo |
| D3 | **Gap de 8 features entre IoT e o modelo de risco** | 3 → 6 | ver seção 15.4 |
| D4 | **Nenhum módulo consome outro** | 1..6 | Não existe integração implementada |
| D5 | **Sem banco de dados** | 1..6 | Tudo em arquivo, `localStorage` ou memória |
| D6 | **Modelos das Fases 2 e 3 não persistidos** | 2, 3 | Sem `.pkl`/`.joblib`; impossível reutilizar sem retreinar |

---

## 17. Limitações técnicas

### 17.1 Limitações declaradas pelos próprios autores

| Fase | Limitação declarada |
|---|---|
| 1 | Dados coletados em contexto hospitalar específico → **risco de viés**; necessidade de verificar licenças e anonimização |
| 3 | A Parte 1 **simula** conectividade Wi-Fi e envia dados apenas ao Monitor Serial ("nuvem" simulada) |
| 3 | O BPM é **simulado** por botão, não medido |
| 3 | Conclusão do Ir Além 2: modelos tradicionais ainda superam o LIF em simplicidade e desempenho geral |
| 4 | **Desbalanceamento** do dataset (1.341 Normal vs 3.875 Pneumonia) tratado com augmentation e ponderação de classes |
| 6 | Dados **100% sintéticos**; o alvo é função determinística das features → métricas altíssimas **não** indicam capacidade preditiva real |
| 6 | O limiar 0,5 é **operacional**, não calibrado clinicamente |
| 6 | Os protocolos têm limites **de projeto**, não conduta clínica validada |
| 6 | "Esta etapa **não implementa API web nem interface gráfica**" |
| 6 | Conflito de ambiente `gradio` × `openai-agents` **não resolvido** |
| 6 | `ModeloIncompativelError`: `.pkl` de sklearn antigo é recusado pelo 1.8.0 |

### 17.2 Limitações técnicas estruturais

| Limitação | Impacto na Fase 7 |
|---|---|
| **Sem autenticação/autorização real** | Não há como proteger dados clínicos nem atribuir ações |
| **Sem banco de dados** | Sem histórico de pacientes, auditoria de decisões ou estado persistente entre sessões |
| **Sem contrato de API comum** (exceto a Fase 6) | Cada integração exige tradução manual de payloads |
| **Sem gateway / orquestração de serviços** | Cada módulo expõe porta e caminho próprios |
| **Sem containerização** | Ambientes divergentes (Python 3.10 vs 3.13; sklearn 1.4 vs 1.8) dificultam execução conjunta |
| **Sem observabilidade** | Sem logs estruturados, métricas ou tracing entre serviços |
| **Sem versionamento de API** | Mudanças quebram clientes silenciosamente |
| **Sem testes fora da Fase 6** | Regressões nas Fases 2–5 não são detectadas automaticamente |
| **Dependência de serviços externos** (HiveMQ, IBM Cloud, OpenAI) | Requer conectividade, contas ativas e cota disponível |
| **Frontends em stacks diferentes** (React web vs Expo) | Unificação exigirá decisão arquitetural (monorepo? micro-frontends? app único?) |
| **Modelos não reprodutíveis fora da Fase 6** | Fases 2 e 3 dependem de reexecução de notebooks |
| **`requirements.txt` sem versão nas Fases 4 e 5** | Builds não determinísticos |

---

## 18. Informações desconhecidas

Itens que **não** puderam ser confirmados a partir dos arquivos do workspace. Nenhuma suposição foi
feita para preenchê-los.

| # | Informação desconhecida | Motivo |
|---|---|---|
| U1 | Conteúdo dos relatórios em PDF (Fases 3, 4, 5, 6) | arquivos binários (`.pdf`) — não analisados nesta etapa |
| U2 | Conteúdo de `Fase_1/Cap1_Busca_de_Dados/Textos/excluir.txt` | arquivo auxiliar, propósito não declarado no README |
| U3 | Dependências do notebook da Fase 1 | a fase **não possui `requirements.txt`** |
| U4 | Semente aleatória / hiperparâmetros dos modelos das Fases 2 e 3 | não declarados no README; exigiria inspecionar/executar os notebooks |
| U5 | Métricas completas do notebook da Fase 4 (CNN vs MobileNetV2) | o README não transcreve os números; os valores estão dentro do `.ipynb` (889 KB) |
| U6 | Modelo de linguagem usado pelo IBM watsonx Assistant | configuração vive na plataforma IBM; não há artefato no repositório |
| U7 | Se a instância Watson, o broker HiveMQ e a chave OpenAI ainda estão **ativos** | requer teste em tempo de execução — não executado nesta etapa |
| U8 | Fluxo Node-RED (Fase 3) | não versionado no repositório |
| U9 | Datasets originais completos das Fases 1 e 4 | presentes apenas as amostras (o CSV da Fase 1 e as 200 imagens); o dataset Kaggle da Fase 4 não está no repositório |
| U10 | Atribuição de autoria por arquivo | os READMEs listam integrantes por fase, não por arquivo |
| U11 | Motivo da ausência de `docs/plano_implementacao.md`, `docs/relatorio_tecnico.md` e `docs/arquitetura_multiagente.pdf` | referenciados no README da Fase 6, inexistentes na pasta |
| U12 | Se `src/agents/` já existiu no repositório da Fase 6 | o `conftest.py` cita "placeholders da Etapa 1"; a pasta não existe hoje |
| U13 | Licenças de uso dos datasets e das imagens | o README da Fase 1 diz ser necessário "verificar as licenças de uso" — não há registro de verificação |
| U14 | Exigências formais do enunciado da Fase 7 | não estão no workspace; a Fase 7 deve ser especificada pelo autor |
| U15 | Versões exatas de Flask, TensorFlow, ibm-watson etc. nas Fases 3, 4 e 5 | manifestos sem pinos de versão |
| U16 | Estratégia pretendida de integração pelo autor | não declarada em nenhum arquivo |

---

## 19. Conclusão: visão de integração para a Fase 7

### 19.1 Diagnóstico em uma frase

As seis fases formam um **conjunto de módulos tecnicamente ricos, porém independentes**: cada uma
resolve bem o seu escopo isolado, mas **não existe nenhum ponto de integração, identidade de usuário,
persistência ou contrato comum** entre elas — e é exatamente essa camada de integração que a Fase 7
precisa construir.

### 19.2 Ordem de dependência técnica para a integração

| Ordem | Passo | Justificativa |
|---|---|---|
| 1 | **Definir a arquitetura de integração** (gateway único, *path prefixes*, envelope de resposta) | Sem isso, cada módulo mantém porta/caminho próprios e o conflito da 5000 persiste |
| 2 | **Expor a Fase 6 via HTTP** | É o único módulo sem API e o de maior valor (núcleo de decisão); o contrato Pydantic já está pronto para serialização |
| 3 | **Padronizar tratamento de erros e envelope JSON** | A Fase 6 já define o padrão; as Fases 3, 4 e 5 devem adotá-lo |
| 4 | **Resolver o conflito de porta 5000** | Bloqueio operacional imediato para rodar dois serviços juntos |
| 5 | **Resolver o gap de features IoT → modelo** | Sem definição explícita, a integração Fase 3 → Fase 6 **falha por contrato** |
| 6 | **Externalizar e rotacionar credenciais** (Watson, HiveMQ, Gmail) | Risco de segurança crítico; a Fase 6 já mostra o padrão correto |
| 7 | **Criar autenticação/autorização real** | Requisito para qualquer dado clínico; hoje só existe um mock |
| 8 | **Definir persistência** (banco de dados) | Necessário para histórico, auditoria e continuidade |
| 9 | **Empacotar os módulos** (venv/container por serviço ou monorepo) | Conflitos de versão Python/sklearn impedem um ambiente único |
| 10 | **Unificar o frontend** (portal web + app Expo) | Decisão arquitetural de UX; as duas stacks já existem |
| 11 | **Adicionar testes de integração ponta a ponta** | Hoje só a Fase 6 tem testes |
| 12 | **Observabilidade e versionamento de API** | Sustentação do sistema integrado |

### 19.3 O que a Fase 7 pode entregar com o material existente

| Entrega possível | Base reutilizada | Grau de esforço |
|---|---|---|
| API de avaliação de risco (`/risco/avaliar`) | Fase 6 (`executar_pipeline` + `como_dicionario()`) | 🟢 Baixo |
| Tool de visão computacional nos agentes | Fase 4 (`POST /predict`) + `@function_tool` da Fase 6 | 🟡 Médio |
| Tool de triagem por texto | Fase 2 (NLP por regras / TF-IDF) — requer refatoração | 🟡 Médio |
| Camada conversacional | Fase 5 (`POST /api/chat`) | 🟡 Médio |
| Ingestão de telemetria | Fase 3 (`POST /sinais`) + definição das features faltantes | 🔴 Alto |
| Portal unificado | Fase 2 (React) + Fases 4/5 (Expo) | 🔴 Alto |
| Histórico clínico e auditoria | **nada existente** — a construir | 🔴 Alto |

### 19.4 Pontos de atenção que a Fase 7 deve resolver explicitamente

1. **Nada foi alterado nas fases anteriores** — qualquer ajuste necessário (portas, caminhos,
   credenciais) será uma decisão da Fase 7 e deve ser documentada.
2. **O contrato de entrada da Fase 6 é rígido** (`extra="forbid"`, rejeita negativos/NaN/inf, exige as
   10 features) — integrações precisam respeitá-lo ou serão rejeitadas com erro explícito.
3. **O modelo da Fase 6 é sintético e determinístico** — qualquer apresentação ao usuário deve manter
   os avisos de uso (`AVISO_DE_USO`, `LIMITACOES_PADRAO`) para não sugerir validade clínica.
4. **A Fase 5 depende de um serviço externo gerenciado** — se a instância estiver inativa, a camada
   conversacional não funciona.
5. **A Fase 4 depende de TensorFlow** — dependência pesada que não convive trivialmente com o ambiente
   da Fase 6 (sklearn 1.8 / Python 3.13).
6. **A Fase 2 usa caminhos absolutos** — seus scripts não executam nesta estrutura sem ajuste.

---

## Apêndice A — Índice de arquivos relevantes por fase

| Fase | Arquivo-chave | Papel |
|---|---|---|
| 1 | `Dataset/heart_disease_uci.csv` | dados tabulares |
| 1 | `Imagens/chest_xray_proportional/` (200 PNGs) | dados de imagem |
| 1 | `Textos/*.pdf` | corpus textual |
| 2 | `Parte_1/Identificar_Sintomas.py` | NLP por regras |
| 2 | `Parte_2/Classificador_TF_IDF.ipynb` | NLP estatístico |
| 2 | `Ir_Alem/my-react-app/src/contexts/AuthContext.jsx` | autenticação simulada |
| 2 | `Ir_Alem/my-react-app/src/services/api.js` | consumo de API externa |
| 3 | `Parte1/codigo_ESP32.c` | Edge + resiliência offline |
| 3 | `Parte2/codigo_parte2.c` | MQTT / HiveMQ |
| 3 | `Ir_Alem1/server.py` | API REST + SMTP |
| 3 | `Ir_Alem2/Cap1CardioIA_Ir_Alem2ipynb.ipynb` | Regressão Logística × LIF |
| 4 | `Parte1e2/Fase4_Cap1 (1).ipynb` | CNN × MobileNetV2 |
| 4 | `Ir_Alem2/backend/app.py` | API de classificação |
| 4 | `Ir_Alem2/backend/mobilenet_pneumonia.keras` | modelo persistido |
| 4 | `Ir_Alem2/cardio-assistant/screens/HomeScreen.js` | app de análise |
| 5 | `Backend/app.py` | API de chat |
| 5 | `Backend/IBM_API.py` | cliente Watson + credenciais |
| 5 | `CardioAssist/src/services/watsonApi.js` | cliente HTTP com erros amigáveis |
| 6 | `src/cardioia/main.py` | CLI do pipeline |
| 6 | `src/cardioia/agents/orchestrator.py` | orquestração e contrato |
| 6 | `src/cardioia/ml/predict.py` | inferência validada |
| 6 | `src/cardioia/knowledge/protocols.py` | 10 regras determinísticas |
| 6 | `src/cardioia/schemas/risk_result.py` | contrato Pydantic |
| 6 | `models/modelo_pico_risco.pkl` + `..._metadata.json` | modelo + rastreabilidade |
| 6 | `docs/arquitetura.md` | diagramas da arquitetura |

---

*Documento produzido na Fase 7 como etapa de análise e documentação. Nenhum arquivo das Fases 1 a 6
foi modificado, nenhuma dependência foi instalada e nenhuma funcionalidade foi implementada.*
