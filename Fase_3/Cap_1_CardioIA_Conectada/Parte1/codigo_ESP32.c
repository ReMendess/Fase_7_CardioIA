#include <WiFi.h>
#include "DHTesp.h"


// CONFIGURAÇÕES

#define DHT_PIN 15
#define LDR_PIN 34

DHTesp dhtSensor;

// Simulação de conexão
bool wifiConnected = false;

// armazenar dados
struct SensorData {
  float temperatura;
  float umidade;
  int luminosidade;
};

// Buffer local (resiliência offline)
const int MAX_STORAGE = 10;
SensorData storage[MAX_STORAGE];

int storedCount = 0;


// FUNÇÃO PARA SALVAR DADOS

void saveLocally(float temp, float hum, int lum) {

  if (storedCount < MAX_STORAGE) {

    storage[storedCount].temperatura = temp;
    storage[storedCount].umidade = hum;
    storage[storedCount].luminosidade = lum;

    storedCount++;

    Serial.println("Dados armazenados localmente.");
  }
  else {

    // Estratégia de resiliência:
    // remove o dado mais antigo
    for (int i = 1; i < MAX_STORAGE; i++) {
      storage[i - 1] = storage[i];
    }

    storage[MAX_STORAGE - 1].temperatura = temp;
    storage[MAX_STORAGE - 1].umidade = hum;
    storage[MAX_STORAGE - 1].luminosidade = lum;

    Serial.println("Memória cheia. Dado mais antigo removido.");
  }
}

//Enviando os dados

void sendStoredData() {

  Serial.println("\n=== ENVIANDO DADOS PARA NUVEM ===");

  for (int i = 0; i < storedCount; i++) {

    Serial.print("Temperatura: ");
    Serial.print(storage[i].temperatura);
    Serial.print(" °C | Umidade: ");
    Serial.print(storage[i].umidade);
    Serial.print(" % | Luminosidade: ");
    Serial.println(storage[i].luminosidade);

    delay(500);
  }

  Serial.println("Sincronização concluída.");

  // Limpa armazenamento local
  storedCount = 0;
}

// Setup

void setup() {

  Serial.begin(115200);

  dhtSensor.setup(DHT_PIN, DHTesp::DHT22);

  pinMode(LDR_PIN, INPUT);

  Serial.println("Sistema iniciado.");
}


void loop() {

  // Leitura DHT22
  TempAndHumidity data = dhtSensor.getTempAndHumidity();

  // Leitura LDR
  int luminosidade = analogRead(LDR_PIN);

  float temperatura = data.temperature;
  float umidade = data.humidity;

  // leitura atual
  Serial.println("\n===== NOVA LEITURA =====");

  Serial.print("Temperatura: ");
  Serial.print(temperatura);
  Serial.println(" °C");

  Serial.print("Umidade: ");
  Serial.print(umidade);
  Serial.println(" %");

  Serial.print("Luminosidade: ");
  Serial.println(luminosidade);

  // Salvando localmente
  saveLocally(temperatura, umidade, luminosidade);

  // Simulação de Wifi

  wifiConnected = !wifiConnected;

  if (wifiConnected) {

    Serial.println("\nWi-Fi conectado.");

    sendStoredData();
  }
  else {

    Serial.println("\nWi-Fi desconectado.");
    Serial.println("Sistema operando em modo offline.");
  }

  delay(5000);
}