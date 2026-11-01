import csv
from os import sep

# Caminho do arquivo
arquivo_csv = "C:\\Users\\Pichau\\OneDrive\\Área de Trabalho\\Cap2_Desafio_Integrador\\Parte_1\\mapa_sintomas_doencas.csv"

# Estrutura: Sintoma 1 | Sintoma 2 | Intensidade | Duração | Diagnóstico
dados = [
    ["dor no peito", "aperto no tórax", "alta", "2 dias", "Infarto"],
    ["dor no peito ao esforço", "pressão no peito", "média", "1 semana", "Angina"],
    ["cansaço constante", "fadiga", "média", "1 semana", "Insuficiência Cardíaca"],
    ["falta de ar", "dificuldade para respirar", "alta", "3 dias", "Doença Pulmonar"],
    ["falta de ar ao esforço", "cansaço ao subir escadas", "média", "1 semana", "Angina"],
    ["dor de cabeça forte", "sensibilidade à luz", "alta", "1 dia", "Enxaqueca"],
    ["febre", "dor no corpo", "média", "3 dias", "Infecção Viral"],
    ["febre alta", "calafrios", "alta", "2 dias", "Infecção Bacteriana"],
    ["dor abdominal", "dor após refeições", "média", "2 dias", "Gastrite"],
    ["dor no abdômen", "queimação estomacal", "baixa", "1 semana", "Refluxo Gastroesofágico"],
    ["tosse persistente", "tosse seca", "média", "5 dias", "Bronquite"],
    ["tosse noturna", "falta de ar à noite", "média", "5 dias", "Asma"],
    ["tontura ao levantar", "queda de pressão", "baixa", "2 dias", "Hipotensão"],
    ["tontura frequente", "desequilíbrio", "média", "2 dias", "Distúrbio Vestibular"],
    ["dores nas articulações", "rigidez matinal", "média", "1 semana", "Artrite"],
    ["náusea", "vontade de vomitar", "baixa", "1 dia", "Gastrite"],
    ["náusea constante", "perda de apetite", "média", "2 dias", "Infecção Gastrointestinal"],
    ["cansaço prolongado", "fraqueza", "média", "2 semanas", "Anemia"],
    ["dor no peito", "falta de ar", "alta", "2 dias", "Infarto"],
    ["febre", "tosse", "média", "3 dias", "Gripe"],
    ["dor de cabeça", "febre", "alta", "4 dias", "Dengue"],
    ["dor no corpo", "cansaço", "baixa", "3 dias", "Virose"],
    ["falta de ar", "chiado no peito", "alta", "3 dias", "Asma"],
    ["dor abdominal", "diarreia", "média", "2 dias", "Infecção Intestinal"],
    ["náusea", "dor abdominal", "alta", "1 dia", "Intoxicação Alimentar"]
]

# Criando o arquivo CSV
with open(arquivo_csv, mode="w", newline="", encoding="utf-8") as arquivo:
    escritor = csv.writer(arquivo)
    
    # Cabeçalho atualizado
    escritor.writerow(["Sintoma 1", "Sintoma 2", "Intensidade", "Duração", "Doença Associada"])
    
    # Dados
    escritor.writerows(dados)

print(f"Arquivo '{arquivo_csv}' criado com sucesso.")