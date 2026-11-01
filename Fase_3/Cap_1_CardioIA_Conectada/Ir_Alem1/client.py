import requests
import random
import time

URL = "http://127.0.0.1:5000/sinais"

while True:

    dados = {

        "temperatura": round(random.uniform(35, 40), 1),

        "bpm": random.randint(60, 140),

        "movimento": random.choice([True, True, True, False])
    }

    resposta = requests.post(URL, json=dados)

    print("\nSINAIS ENVIADOS")

    print(dados)

    print("Resposta API:")

    print(resposta.json())

    time.sleep(5)