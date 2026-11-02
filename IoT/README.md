
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


## 4. Regras de alerta

Os limiares são **os mesmos** de `backend/app/regras_iot.py`:

| Condição | Alerta | Prioridade |
|---|---|---|
| `temperatura > 38` | `FEBRE DETECTADA` | 1ª |
| `bpm > 120` | `TAQUICARDIA DETECTADA` | 2ª |

Manter os dois lados iguais evita que o dispositivo e o servidor discordem sobre o que é um
alerta. O dispositivo decide **para reagir na hora** (LED/OLED sem esperar a rede); o
backend reavalia e é quem persiste.

---

## 5. Como rodar no Wokwi

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
