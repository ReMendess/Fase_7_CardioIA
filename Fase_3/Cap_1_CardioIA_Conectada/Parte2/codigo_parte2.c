#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "DHTesp.h"

// WIFI

const char* ssid = "Wokwi-GUEST";
const char* password = "";

// MQTT HIVEMQ

const char* mqtt_server = "SEU_CLUSTER.s1.eu.hivemq.cloud";
const char* mqtt_user   = "SEU_USUARIO";
const char* mqtt_pass   = "SUA_SENHA";
const int mqtt_port = 8883;


WiFiClientSecure espClient;
PubSubClient client(espClient);

DHTesp dhtSensor;

#define DHT_PIN 15
#define BUTTON_PIN 18

int bpm = 70;


void setup_wifi() {

  delay(10);

  Serial.println();
  Serial.print("Conectando ao WiFi");

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi conectado");
}


void reconnect() {

  while (!client.connected()) {

    Serial.print("Conectando MQTT...");

    if (client.connect("ESP32Client", mqtt_user, mqtt_pass)) {

      Serial.println("conectado");

    } else {

      Serial.print("erro=");
      Serial.print(client.state());

      delay(2000);
    }
  }
}


void setup() {

  Serial.begin(115200);

  pinMode(BUTTON_PIN, INPUT_PULLUP);

  dhtSensor.setup(DHT_PIN, DHTesp::DHT22);

  setup_wifi();

  espClient.setInsecure();

  client.setServer(mqtt_server, mqtt_port);
}

// =======================

void loop() {

  if (!client.connected()) {
    reconnect();
  }

  client.loop();


  // DHT22
  TempAndHumidity data = dhtSensor.getTempAndHumidity();

  float temperatura = data.temperature;

  // SIMULAÇÃO BPM

  if (digitalRead(BUTTON_PIN) == LOW) {

    bpm = random(60, 140);

    delay(300);
  }

  // PUBLICAR MQTT


  char tempString[8];
  dtostrf(temperatura, 1, 2, tempString);

  char bpmString[8];
  itoa(bpm, bpmString, 10);

  client.publish("hospital/temperatura", tempString);
  client.publish("hospital/bpm", bpmString);

  // ===================
  
  Serial.print("Temperatura: ");
  Serial.println(tempString);

  Serial.print("BPM: ");
  Serial.println(bpmString);

  delay(3000);
}