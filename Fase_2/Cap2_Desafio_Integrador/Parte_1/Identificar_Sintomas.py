import csv
import re
from collections import defaultdict

# Configurações de arquivo
ARQUIVO_TXT = r"C:\Users\Pichau\OneDrive\Área de Trabalho\Cap2_Desafio_Integrador\Parte_1\sintomas_pacientes.txt"
ARQUIVO_CSV = r"C:\Users\Pichau\OneDrive\Área de Trabalho\Cap2_Desafio_Integrador\Parte_1\mapa_sintomas_doencas.csv"

# Funções auxiliares
def normalizar_texto(texto):
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', '', texto)  # remove pontuação
    return texto

def carregar_mapa_conhecimento(caminho_csv):
    mapa = []
    with open(caminho_csv, mode="r", encoding="utf-8") as arquivo:
        leitor = csv.DictReader(arquivo)
        for linha in leitor:
            mapa.append({
                "sintoma1": normalizar_texto(linha["Sintoma 1"]),
                "sintoma2": normalizar_texto(linha["Sintoma 2"]),
                "intensidade": linha["Intensidade"],
                "duracao": linha["Duração"],
                "doenca": linha["Doença Associada"]
            })
    return mapa

def identificar_diagnostico(frase, mapa):
    frase_norm = normalizar_texto(frase)
    pontuacao = defaultdict(int)

    for entrada in mapa:
        if entrada["sintoma1"] in frase_norm:
            pontuacao[entrada["doenca"]] += 1
        if entrada["sintoma2"] in frase_norm:
            pontuacao[entrada["doenca"]] += 1

    if not pontuacao:
        return "Diagnóstico não identificado"

    # retorna a doença com maior pontuação
    return max(pontuacao, key=pontuacao.get)

# Main Code
def processar_pacientes():
    mapa = carregar_mapa_conhecimento(ARQUIVO_CSV)

    with open(ARQUIVO_TXT, mode="r", encoding="utf-8") as arquivo:
        frases = arquivo.readlines()

    print("=== RESULTADOS ===\n")

    for i, frase in enumerate(frases, 1):
        frase = frase.strip()
        diagnostico = identificar_diagnostico(frase, mapa)

        print(f"Paciente {i}:")
        print(f"Frase: {frase}")
        print(f"Diagnóstico sugerido: {diagnostico}")
        print("-" * 50)

#Execution
if __name__ == "__main__":
    processar_pacientes()