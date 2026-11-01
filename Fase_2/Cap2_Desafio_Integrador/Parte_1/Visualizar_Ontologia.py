import csv
import networkx as nx
import matplotlib.pyplot as plt

# Caminho do CSV
ARQUIVO_CSV = r"C:\Users\Pichau\OneDrive\Área de Trabalho\Cap2_Desafio_Integrador\Parte_1\mapa_sintomas_doencas.csv"

# Criar grafo
G = nx.Graph()

# Ler CSV e montar o grafo
with open(ARQUIVO_CSV, mode="r", encoding="utf-8") as arquivo:
    leitor = csv.DictReader(arquivo)
    
    for linha in leitor:
        sintoma1 = linha["Sintoma 1"]
        sintoma2 = linha["Sintoma 2"]
        doenca = linha["Doença Associada"]

        # Adiciona nós com tipo (para diferenciar depois)
        G.add_node(sintoma1, tipo="sintoma")
        G.add_node(sintoma2, tipo="sintoma")
        G.add_node(doenca, tipo="doenca")

        # Liga sintomas à doença
        G.add_edge(sintoma1, doenca)
        G.add_edge(sintoma2, doenca)

# Separar nós por tipo
sintomas = [n for n, attr in G.nodes(data=True) if attr["tipo"] == "sintoma"]
doencas = [n for n, attr in G.nodes(data=True) if attr["tipo"] == "doenca"]

# Layout do grafo
pos = nx.spring_layout(G, k=0.5, seed=42)

# Desenhar
plt.figure(figsize=(12, 8))

nx.draw_networkx_nodes(G, pos, nodelist=sintomas, node_size=800, label="Sintomas")
nx.draw_networkx_nodes(G, pos, nodelist=doencas, node_size=1200, label="Doenças")

nx.draw_networkx_edges(G, pos)
nx.draw_networkx_labels(G, pos, font_size=8)

plt.title("Mapa de Conhecimento: Sintomas x Doenças")
plt.legend()
plt.axis("off")
plt.show()

