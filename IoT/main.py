"""CardioIA — no MicroPython (ESP32 simulado no Wokwi).

Le temperatura corporal (DHT22) e frequencia cardiaca (**simulada por botao**), avalia os
sinais **no proprio dispositivo** e envia a leitura para o backend central da Fase 7.

Por que MicroPython: a captura e o processamento sairam de C/C++ (Fase 3) para MicroPython,
que roda em microcontroladores de alto desempenho (ESP32 / Raspberry Pi Pico) com o mesmo
codigo — sem toolchain de compilacao e sem regravar o firmware para cada ajuste.

Arquitetura do fluxo:

    DHT22 + botao  ->  MicroPython (avalia)  ->  HTTP POST  ->  Backend Fase 7
                            |                                        |
                            v                                        v
                     OLED + LED (feedback)                  modelo + assistente

Pinos (batem com o `diagram.json`):

    GPIO 15  DHT22 (dados)      GPIO  2  LED vermelho (alerta)
    GPIO 18  botao (batimento)  GPIO 21  OLED SDA
    GPIO 22  OLED SCL

Os limiares sao **os mesmos** de `backend/app/regras_iot.py` — literalmente 38 °C e
120 bpm, estritamente maior. Manter os dois lados iguais evita que o dispositivo e o
servidor discordem sobre o que e um alerta.
"""

import json
import time

import dht
import network
import urequests
from machine import I2C, Pin

# --------------------------------------------------------------------------- #
# Configuracao — ajuste antes de rodar
# --------------------------------------------------------------------------- #

#: Rede do simulador. No Wokwi a internet sai por um gateway proprio, com esta rede.
WIFI_SSID = "Wokwi-GUEST"
WIFI_SENHA = ""

#: Endereco do backend central (o mesmo que o frontend e o app usam).
URL_DO_BACKEND = "http://SEU-BACKEND.onrender.com/api/v1/iot/leituras"

#: Chave compartilhada do dispositivo (equivale a `IOT_DEVICE_KEY` no backend).
CHAVE_DO_DISPOSITIVO = "SUA_CHAVE_DE_DISPOSITIVO"

#: Identificador deste dispositivo. O firmware da Fase 3 nao enviava identificador —
#: a API exige, e por isso ele e definido aqui.
ID_DO_DISPOSITIVO = "esp32-wokwi-01"

#: Intervalo entre envios ao backend, em segundos.
INTERVALO_DE_ENVIO = 10

# --------------------------------------------------------------------------- #
# Limiares — identicos a `backend/app/regras_iot.py`
# --------------------------------------------------------------------------- #

LIMIAR_DE_TEMPERATURA = 38
LIMIAR_DE_BPM = 120

ALERTA_DE_FEBRE = "FEBRE DETECTADA"
ALERTA_DE_TAQUICARDIA = "TAQUICARDIA DETECTADA"

# --------------------------------------------------------------------------- #
# Pinos
# --------------------------------------------------------------------------- #

PINO_DHT = 15
PINO_BOTAO = 18
PINO_LED = 2
PINO_SDA = 21
PINO_SCL = 22

#: Frequencia em repouso usada quando ninguem aperta o botao (bpm).
BPM_DE_REPOUSO = 72


# --------------------------------------------------------------------------- #
# Hardware
# --------------------------------------------------------------------------- #

sensor = dht.DHT22(Pin(PINO_DHT))
botao = Pin(PINO_BOTAO, Pin.IN, Pin.PULL_UP)
led = Pin(PINO_LED, Pin.OUT)

# O OLED e opcional: se a biblioteca nao estiver disponivel, o programa continua e o
# feedback visual fica por conta do LED. Um display ausente nao pode derrubar a coleta.
oled = None


def iniciar_oled():
    """Liga o display. Tenta a biblioteca embutida e, se faltar, instala pelo `mip`.

    Chamado **depois** de a rede subir: o `mip` baixa da internet, e sem rede ele
    falharia. Se ainda assim nao for possivel, o programa segue com o LED.
    """
    global oled

    if oled is not None:
        return oled

    try:
        import ssd1306
    except ImportError:
        try:
            import mip

            print("instalando a biblioteca do display...")
            mip.install("ssd1306")
            import ssd1306
        except Exception as erro:  # noqa: BLE001
            print("[aviso] display indisponivel:", erro)
            return None

    try:
        oled = ssd1306.SSD1306_I2C(128, 64, I2C(0, scl=Pin(PINO_SCL), sda=Pin(PINO_SDA)))
        oled.fill(0)
        oled.text("CardioIA", 0, 0)
        oled.text("iniciando...", 0, 20)
        oled.show()
    except Exception as erro:  # noqa: BLE001 - I2C ausente nao e fatal
        print("[aviso] display nao respondeu:", erro)
        oled = None

    return oled


# --------------------------------------------------------------------------- #
# Frequencia cardiaca simulada
# --------------------------------------------------------------------------- #
#
# O enunciado pede **batimentos simulados**: nao ha sensor de pulso. Cada toque no botao
# representa um batimento, e o intervalo entre toques define o BPM — a mesma conta que um
# oxímetro faz. Sem toques recentes, a frequencia volta ao repouso.

_ultimo_batimento = 0
_bpm_atual = BPM_DE_REPOUSO

#: Toques mais rapidos que isso sao tratados como repique do contato, nao como batimento.
INTERVALO_MINIMO_DE_REPIQUE = 120

#: Depois disso sem toques, a frequencia volta ao repouso.
TEMPO_ATE_O_REPOUSO = 6000


def registrar_batimento(pino):
    """Conta um batimento e recalcula o BPM a partir do intervalo entre toques."""
    global _ultimo_batimento, _bpm_atual

    agora = time.ticks_ms()
    if _ultimo_batimento:
        intervalo = time.ticks_diff(agora, _ultimo_batimento)
        if intervalo >= INTERVALO_MINIMO_DE_REPIQUE:
            _bpm_atual = min(220, max(40, 60000 // intervalo))
    _ultimo_batimento = agora


botao.irq(trigger=Pin.IRQ_FALLING, handler=registrar_batimento)


def bpm_atual():
    """Frequencia cardiaca em bpm, com volta ao repouso quando ninguem toca."""
    global _bpm_atual

    if _ultimo_batimento:
        parado = time.ticks_diff(time.ticks_ms(), _ultimo_batimento)
        if parado > TEMPO_ATE_O_REPOUSO:
            _bpm_atual = BPM_DE_REPOUSO
    return _bpm_atual


def ler_temperatura():
    """Le o DHT22. Devolve ``None`` quando a leitura falha (o sensor oscila)."""
    try:
        sensor.measure()
        return round(sensor.temperature(), 1)
    except OSError:
        return None


# --------------------------------------------------------------------------- #
# Analise no proprio dispositivo (edge computing)
# --------------------------------------------------------------------------- #


def avaliar_sinais(temperatura, bpm):
    """Aplica as regras de alerta **no dispositivo**, antes de enviar.

    A ordem de prioridade e a mesma do backend: **febre antes de taquicardia**. Avaliar
    aqui permite reagir na hora (LED e OLED) sem esperar a rede — que e o ponto do edge
    computing. O backend reavalia a leitura ao receber, e e ele quem persiste o alerta.

    Returns:
        O texto do alerta, ou ``None`` quando nao ha nada a sinalizar.
    """
    if temperatura is not None and temperatura > LIMIAR_DE_TEMPERATURA:
        return ALERTA_DE_FEBRE
    if bpm is not None and bpm > LIMIAR_DE_BPM:
        return ALERTA_DE_TAQUICARDIA
    return None


# --------------------------------------------------------------------------- #
# Feedback visual
# --------------------------------------------------------------------------- #


def mostrar_no_oled(temperatura, bpm, alerta, enviado):
    """Desenha os sinais e o estado do envio no display."""
    if oled is None:
        return

    oled.fill(0)
    oled.text("CardioIA", 0, 0)

    oled.text("Temp: {} C".format("--" if temperatura is None else temperatura), 0, 16)
    oled.text("BPM : {}".format(bpm), 0, 26)

    if alerta:
        # O alerta ocupa a linha larga: e a informacao que importa a distancia.
        oled.text("!! ALERTA !!", 0, 40)
        oled.text(alerta[:16], 0, 52)
    else:
        oled.text("sinais normais", 0, 40)

    oled.text("envio: ok" if enviado else "envio: --", 88, 0)
    oled.show()


def sinalizar_no_led(alerta):
    """LED aceso durante o alerta; apagado quando os sinais estao normais."""
    led.value(1 if alerta else 0)


# --------------------------------------------------------------------------- #
# Rede
# --------------------------------------------------------------------------- #


def conectar_ao_wifi(tentativas=20):
    """Conecta a rede do simulador. Devolve ``True`` quando consegue."""
    estacao = network.WLAN(network.STA_IF)
    estacao.active(True)

    if estacao.isconnected():
        return True

    print("conectando a rede", WIFI_SSID, "...")
    estacao.connect(WIFI_SSID, WIFI_SENHA)

    for _ in range(tentativas):
        if estacao.isconnected():
            print("conectado | ip:", estacao.ifconfig()[0])
            return True
        time.sleep(0.5)

    print("nao foi possivel conectar")
    return False


def enviar_para_o_backend(temperatura, bpm, alerta):
    """Envia a leitura para ``POST /api/v1/iot/leituras``.

    O firmware da Fase 3 publicava em MQTT (broker externo). Aqui o envio e **HTTP
    direto**: elimina o broker e a conta de terceiro, e o backend da Fase 7 tem ingestao
    REST nativa.

    Returns:
        ``True`` quando o backend aceitou a leitura.
    """
    corpo = {
        "id_dispositivo": ID_DO_DISPOSITIVO,
        "origem_transporte": "rest",
        "temperatura": temperatura,
        "bpm": bpm,
        # Payload bruto fica registrado para auditoria — o backend nao interpreta.
        "payload_json": {"alerta_local": alerta, "origem": "micropython-wokwi"},
    }

    try:
        resposta = urequests.post(
            URL_DO_BACKEND,
            data=json.dumps(corpo),
            headers={
                "Content-Type": "application/json",
                "X-Device-Key": CHAVE_DO_DISPOSITIVO,
            },
        )
        aceito = resposta.status_code in (200, 201)
        if aceito:
            print("enviado | http", resposta.status_code)
        else:
            print("recusado | http", resposta.status_code, resposta.text[:120])
        resposta.close()
        return aceito
    except Exception as erro:  # noqa: BLE001 - a rede cai; a coleta nao pode parar
        print("falha no envio:", erro)
        return False


# --------------------------------------------------------------------------- #
# Laco principal
# --------------------------------------------------------------------------- #


def principal():
    """Le, avalia, mostra e envia — em ciclo."""
    print("CardioIA | MicroPython | dispositivo:", ID_DO_DISPOSITIVO)

    if not conectar_ao_wifi():
        print("[aviso] seguindo sem rede: os sinais continuam sendo mostrados no OLED")

    iniciar_oled()

    while True:
        temperatura = ler_temperatura()
        bpm = bpm_atual()
        alerta = avaliar_sinais(temperatura, bpm)

        sinalizar_no_led(alerta)
        print("temp={} bpm={} alerta={}".format(temperatura, bpm, alerta or "-"))

        enviado = enviar_para_o_backend(temperatura, bpm, alerta)
        mostrar_no_oled(temperatura, bpm, alerta, enviado)

        time.sleep(INTERVALO_DE_ENVIO)


principal()



