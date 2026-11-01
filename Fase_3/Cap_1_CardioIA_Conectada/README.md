# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href= "https://www.fiap.com.br/"><img src="assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Admnistração Paulista" border="0" width=40% height=40%></a>
</p>

<br>

# Cap 1 - CardioIA Conectada: IoT e Visualização de Dados para a Saúde Digital

# Integrante: 
- <a href="https://www.linkedin.com/in/renanmendes26/">Renan de Oliveira Mendes - RM563145</a>


# Descrição
Nessa terceira fase, com foco em Edge, Fog e Cloud Computing, desenvolvi e implementei aplicações que capturam dados em tempo real de sensores, armazenam e se conectam com a nuvem.
Na segunda parte principalmente, foi construida uma solução de monitoramento até a visualização de dados, voltado para a área da saúde. Abrangendo todas as fases, ferramentas e camadas de IOT conectada a nuvem.
Indo além, criei uma solução em python, com API REST e o protocolo SMTP, conectado ao Gmail para envio de alertas.
No segundo indo além, em um notebook python treinei dois modelos, um de regrssão logística e um LIF (Leaky Integrate-and-Fire), sendo o segundo um modelo baseado em uma arquitetura neuromórfica.
Fiz um ajuste e análise comparativa de ambos os modelos.


## Parte 1
Criei uma solução que utiliza Edge Computing com ESP32 para monitoramento em aplicações críticas de saúde. O sistema coleta dados localmente através de sensores e continua funcionando mesmo sem conexão com a internet.

**Link do projeto no Wokwi: https://wokwi.com/projects/463496096459659265**

**Relatório com mais detalhes dentro da pasta "Parte1"**

<img src="assets/Parte1_wokwi.png" widht="150">

##### Sensores utilizados

 - Sensor DHT22 para temperatura e umidade 
 - Sensor LDR para luminosidade 

#### Funcionamento
O ESP32 realiza leituras periódicas dos sensores e armazena os dados localmente em memória. Uma variável booleana simula a conectividade Wi-Fi.


Quando o sistema está offline:
-	os dados continuam sendo armazenados localmente 


Quando a conexão retorna:
-	os dados armazenados são enviados para a “nuvem” utilizando o Monitor Serial 
- 	após o envio, os dados locais são apagados 



##### Resiliência Offline


Foi implementada uma estratégia FIFO com capacidade máxima de 10 registros. Quando o armazenamento atinge o limite, os dados mais antigos são removidos automaticamente.
Essa abordagem garante:
- continuidade operacional 
-	tolerância à falha de rede 
-	baixo consumo de memória

<img src="assets/Parte1_wokwiII.png" widht="150">


## Parte 2
Na segunda parte desenvolvi e implementei um sistema completo de monitoramento, distribuição e visualização de dados, usando MQTT, HiveMQ e Node-RED.

**Link do projeto non Wokwi: https://wokwi.com/projects/463502084128323585**

**Link do vídeo: https://youtu.be/qpGmhhiO1mw**

**Relatório com mais detalhes dentro da pasta "Parte2"**

<img src="assets/wokwi.png" widht="150">


O projeto implementa uma arquitetura IoT utilizando Edge, Fog e Cloud Computing para monitoramento de sinais vitais em tempo real.

O ESP32 realiza coleta de dados locais e transmite informações via protocolo MQTT para um broker em nuvem.

##### Tecnologias utilizadas
- ESP32
- Wokwi
- MQTT
- HiveMQ Cloud
- Node-RED
- Dashboard IoT
- Fluxo MQTT

O ESP32 conecta-se ao Wi-Fi e estabelece comunicação MQTT com o broker HiveMQ Cloud.

<img src="assets/wokwi.png" widht="150">

<img src="assets/HiveMQ.png" widht="150">

Os dados são publicados nos tópicos:

- hospital/temperatura
- hospital/bpm

<img src="assets/NODE_RED.png" widht="150">

O Node-RED atua como camada Fog Computing:

- recebe dados
- processa alertas
- atualiza dashboard em tempo real

##### Dashboard

A dashboard apresenta:

- gráfico de BPM
- gauge de temperatura
- alertas críticos

<img src="assets/Dashboard.png" widht="150">

Os alertas são ativados quando:

- BPM > 120
- temperatura > 38°C

##### Conceitos aplicados
1. Edge Computing; 
2. Coleta local no ESP32;
3. Fog Computing;
4. Processamento intermediário no Node-RED;
5. Cloud Computing
6. Broker MQTT HiveMQ Cloud.


## Ir Além

Para o Ir Além implementei um sistema de monitoramento de sinais vitais utilizando comunicação REST em Python.
O sistema simula sensores médicos enviando dados para uma API REST responsável pela análise dos sinais e detecção de riscos.

**Relatório com mais detalhes dentro da pasta "Ir_Alem1"**

### Fluxo da solução

O cliente Python gera sinais vitais simulados:

- temperatura
- batimentos cardíacos
- movimento

<img src="assets/client.png" widht="150">

Esses dados são enviados via HTTP POST para a API Flask.

A API processa os sinais e aplica regras de negócio para identificar:

- febre
- taquicardia
- ausência de movimento

<img src="assets/server.png" widht="150">

Quando uma condição crítica é detectada:

- um e-mail automático é enviado.

<img src="assets/email.png" widht="150">

### Comunicação REST

A comunicação utiliza:

- protocolo HTTP
- formato JSON
- Endpoint
- Método POST
- Automação de e-mail

A automação utiliza:

- protocolo SMTP
- servidor Gmail

O sistema envia alertas automaticamente para profissionais responsáveis.

<img src="assets/email2.png" widht="150">


## Ir Além 2

No Ir Além 2 realizei o treinamento de dois modelos. O objetivo é comparar técnicas tradicionais de aprendizado de máquina com modelos neuromórficos aplicados à análise de séries temporais de sinais vitais.

**Relatório com mais detalhes dentro da pasta Ir_Alem2**


**Link do vídeo: https://youtu.be/rRensd7oCjk**

Foi utilizada uma base sintética de batimentos cardíacos para classificação entre estados normais e taquicardia.

### Modelos utilizados

- Regressão Logística

Modelo supervisionado tradicional amplamente utilizado para classificação binária.

- Modelo LIF

Modelo neuromórfico inspirado em neurônios biológicos, baseado em acúmulo de potencial elétrico e disparo de spikes.


### Resultados

A regressão logística apresentou maior estabilidade e facilidade de treinamento.

O modelo LIF demonstrou comportamento biologicamente inspirado e boa capacidade de detectar padrões temporais simples.

<img src="assets/modelos_comp.png" widht="150">

O projeto demonstra como modelos neuromórficos podem ser aplicados em séries temporais de saúde, embora modelos tradicionais ainda apresentem vantagens em simplicidade e desempenho geral.


# 📁 Estrutura de pastas

Dentre os arquivos e pastas presentes na raiz do projeto, definem-se:

- <b>Ir_Alem1</b>: Códigos do sistema de monmitoramento API REST com Python e relatório descritivo.

- <b>Ir_Alem_2</b>: Notebook python com o treinamento do modelo de Regressão e LIF, e relatório descritivo.

- <b>Parte1</b>: Código C do ESP32 que coleta dados localmente e relatório descritivo.
  
- <b>Parte2</b>: Código C do ESP32 que se conecta via MQTT ao broker e relatório descritivo.

- <b>assets</b>: Imagens relevantes para documentação desse repositório.


  
## Requisitos

- Node.js 20.x ou 22.x LTS (recomendado para Vite 8) + npm
- Python 3.10–3.12 
- Arduino IDE ou Wokwi
- Node-RED
- Conta no HiveMQ Cloud
- Notebook: Python 3.10–12
- Node-red-dashboard
- Flask
- Requests
- SMTP

