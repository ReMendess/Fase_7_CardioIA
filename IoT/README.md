# CardioIA — IoT em MicroPython (ESP32 / Wokwi)

Nó de captura da Fase 7. Le **temperatura corporal** (DHT22) e **frequência cardíaca
simulada** (botão), avalia os sinais **no próprio dispositivo** e envia a leitura para o
backend central.

> **Por que MicroPython:** a captura e o processamento saíram de C/C++ (Fase 3) para
> MicroPython, que roda em microcontroladores de alto desempenho (ESP32, Raspberry Pi Pico)
> com o mesmo código — sem toolchain de compilação e sem regravar firmware a cada ajuste.

---

## 1. Arquitetura

```
 DHT22 + botão ──► MicroPython ──► HTTP POST ──► Backend Fase 7 ──► Frontend / App
   (sensores)       (avalia)                        (persiste)         (exibe)
                       │
                       └──► OLED + LED (feedback local, sem esperar a rede)
```

O fluxo **fecha o ciclo** da plataforma: o sinal nasce no dispositivo, é avaliado na borda,
chega ao backend e aparece na interface.

---

## 2. Arquivos

| Arquivo | O que é |
|---|---|
| `main.py` | Firmware MicroPython (nome obrigatório: o simulador executa `main.py`) |
| `diagram.json` | Circuito do Wokwi (ESP32 + DHT22 + botão + LED + OLED) |

---

## 3. Pinos

| GPIO | Componente | Observação |
|---|---|---|
| **15** | DHT22 (dados) | temperatura corporal |
| **18** | Botão | cada toque = um batimento |
| **2** | LED vermelho | aceso durante o alerta |
| **21** | OLED SDA | I²C, endereço `0x3C` |
| **22** | OLED SCL | I²C |

---

## 4. Como o BPM é simulado

Não há sensor de pulso — o enunciado pede **batimentos simulados**. Cada toque no botão
representa um batimento, e o intervalo entre toques define a frequência:

```
bpm = 60000 / intervalo_entre_toques_ms
```

É a mesma conta que um oxímetro faz. Sem toques por 6 segundos, a frequência volta ao
repouso (72 bpm). Toques mais rápidos que 120 ms são tratados como repique do contato, não
como batimento.

| Como tocar | BPM aproximado | Resultado |
|---|---|---|
| devagar | ~75 | sinais normais |
| rápido | ~150 | **TAQUICARDIA DETECTADA** |

No Wokwi o DHT22 tem um controle deslizante de temperatura. **Acima de 38 °C** dispara
**FEBRE DETECTADA** — e a febre tem prioridade sobre a taquicardia, igual ao backend.

---

## 5. Regras de alerta

Os limiares são **os mesmos** de `backend/app/regras_iot.py`:

| Condição | Alerta | Prioridade |
|---|---|---|
| `temperatura > 38` | `FEBRE DETECTADA` | 1ª |
| `bpm > 120` | `TAQUICARDIA DETECTADA` | 2ª |

Manter os dois lados iguais evita que o dispositivo e o servidor discordem sobre o que é um
alerta. O dispositivo decide **para reagir na hora** (LED/OLED sem esperar a rede); o
backend reavalia e é quem persiste.

---

## 6. Como rodar no Wokwi

1. Abra **https://wokwi.com/projects/new/esp32-micropython**.
2. Substitua o conteúdo de `main.py` pelo arquivo `IoT/main.py`.
3. Abra a aba **`diagram.json`** e substitua pelo arquivo `IoT/diagram.json`.
4. Edite a configuração no topo do `main.py`:

```python
URL_DO_BACKEND = "https://SEU-SERVICO.onrender.com/api/v1/iot/leituras"
CHAVE_DO_DISPOSITIVO = "o mesmo valor de IOT_DEVICE_KEY no backend"
```

5. **▶ Start Simulation**.
6. Toque no botão várias vezes e arraste o controle do DHT22 para cima.

**O que deve acontecer:** o OLED mostra temperatura e BPM, o LED acende no alerta, e a
leitura aparece em `GET /api/v1/iot/leituras` — e no dashboard do frontend.

> 💡 A biblioteca do display (`ssd1306`) é instalada automaticamente pelo `mip` na primeira
> execução. Se o display não aparecer, o programa continua com o LED — o OLED é opcional de
> propósito, para que um display ausente não derrube a coleta.

---

## 7. Envio ao backend

O firmware da Fase 3 publicava em **MQTT** (broker HiveMQ + Node-RED). Aqui o envio é
**HTTP direto** para o backend da Fase 7:

| Campo | Valor |
|---|---|
| Rota | `POST /api/v1/iot/leituras` |
| Autenticação | cabeçalho `X-Device-Key` |
| Corpo | `id_dispositivo`, `origem_transporte`, `temperatura`, `bpm`, `payload_json` |

Elimina o broker e a conta de terceiro, e usa a ingestão REST que o backend já expõe. O
`id_dispositivo` é obrigatório: **o firmware da Fase 3 não enviava identificador** — a API
exige, então ele é definido no dispositivo.

> ⚠️ O firmware **não envia timestamp**: o backend carimba `recebido_em`. Isso está no
> contrato (`CONTRATOS_API.md` §4.2) e evita confiar no relógio do dispositivo.

---

## 8. Verificação

```powershell
# a leitura chegou?
$h = @{ Authorization = "Bearer $token" }
Invoke-RestMethod "https://SEU-BACKEND/api/v1/iot/leituras?limite=5" -Headers $h |
  Select-Object -ExpandProperty dados | Format-Table id_dispositivo, temperatura, bpm, recebido_em
```

Se a ingestão aceitar, a resposta traz `avisos` com o alerta — por exemplo
`FEBRE DETECTADA` quando a temperatura passa de 38 °C.
