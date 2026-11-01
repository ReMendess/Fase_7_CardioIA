# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href= "https://www.fiap.com.br/"><img src="assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Admnistração Paulista" border="0" width=40% height=40%></a>
</p>

<br>

# Cap 1 - A Busca de Dados: Preparando o Terreno para a Inteligência Cardiológica

## Nome do grupo

# 👨‍🎓 Integrantes: 
- <a href="https://www.linkedin.com/in/renanmendes26/">Renan de Oliveira Mendes - RM563145</a>
- <a href="https://www.linkedin.com/in/ricaleone/">Ricardo Batah Leone - RM563382</a>
- <a href="https://www.linkedin.com/in/yuki-watanabe-kuramoto-858856146/">Yuki Watanabe Kuramoto  - RM565164</a>
- <a href="https://br.linkedin.com/in/rodrigoreinaux/">Rodrigo De Melo Reinaux Porto  - RM564242</a>


# 📜 Descrição
Para essa entrega, buscamos e separamos diferentes tipos de dados.
Levantamos e organizamos dados cardiológicos que no futuro usaremos para alimentar os módulos inteligentes do CardioIA. Focando em governança de dados envolvendo IA.


Os tipos de dados:

1. Dados numéricos relacionados a pacientes cardíacos;
2. Textos médicos ou literários relacionados à saúde cardiovascular;
3. Imagens de raio-x do toráx.

Esses dados serão utilizados nas fases seguintes do projeto para alimentar algoritmos, treinar modelos de IA, fazer análises comparativas e gerar soluções inovadoras

## Dataset

Pegamos um conjunto de dados multivariado, envolvendo variáveis ​​matemáticas. O dataset é composto por:

- id - Identificador único de cada paciente.
- age -Idade do paciente em anos.
- origin - Local onde o estudo foi realizado.
- sex - Sexo do paciente (Masculino / Feminino).
- cp - Tipo de dor no peito.
- trestbps - Pressão arterial em repouso, medida na admissão hospitalar (mm Hg).
- chol - Nível de colesterol no sangue (mg/dl).
- fbs - Indica se o nível de glicose em jejum é maior que 120 mg/dl.
- restecg - Resultado do eletrocardiograma em repouso.
- thalach - Frequência cardíaca máxima atingida durante o teste.
- exang - Indica se o exercício físico provocou angina.
- oldpeak - Depressão do segmento ST causada por exercício em comparação com o estado de repouso.
- slope - Inclinação do segmento ST no pico do exercício.
- ca - Número de grandes vasos sanguíneos (0 a 3).
- thal - Resultado do exame de perfusão miocárdica (thalium test).
- num - Variável alvo do dataset. Indica a presença ou gravidade da doença cardíaca (resultado predito).

<img src="assets/Dataset.png" widht="150">

Fonte: https://www.kaggle.com/datasets/redwankarimsony/heart-disease-data
Criadores:
- Hungarian Institute of Cardiology. Budapest: Andras Janosi, M.D.
- University Hospital, Zurich, Switzerland: William Steinbrunn, M.D.
- University Hospital, Basel, Switzerland: Matthias Pfisterer, M.D.
- V.A. Medical Center, Long Beach and Cleveland Clinic Foundation: Robert Detrano, M.D., Ph.D.

Este banco de dados tem 76 atributos, mas todos os estudos publicados se referem ao uso de um subconjunto de 14 deles. O banco de dados de Cleveland é o único utilizado por pesquisadores de aprendizado de máquina até o momento. Uma das principais tarefas com este conjunto de dados é prever, com base nos atributos fornecidos de um paciente, se essa pessoa tem ou não doença cardíaca. Outra tarefa experimental é diagnosticar e obter diversas informações a partir deste conjunto de dados que possam ajudar a compreender melhor o problema.

Em estudos clínicos e em modelos de machine learning aplicados a cardiologia, as variáveis mais informativas costumam ser idade, que é um dos principais fatores de risco para doenças cardiovasculares.
Sintomas de dor torácica são fortemente associados à doença arterial coronariana. Trestbps (pressão arterial em repouso), hipertensão é um dos principais fatores de risco cardíaco e 
altos níveis de colesterol, que estão relacionados à formação de placas nas artérias.

Essas variáveis combinam fatores de risco, sintomas clínicos e exames cardiológicos, formando uma base adequada para treinar modelos de classificação de doença cardiovascular.

### Governança e Tratamento

Para utilizar o dataset em um projeto de Inteligência Artificial na área da saúde, precisamos aplicar algumas estratégias de governança e tratamento de dados para garantir qualidade e uso ético das informações.

Primeiramente, deve-se realizar a verificação e limpeza dos dados. Isso inclui identificar valores ausentes, inconsistências ou registros duplicados.
Padronização e normalização das variáveis.
Codificação de variáveis categóricas. Campos como sexo, tipo de dor no peito e resultados de exames precisam ser convertidos para formato numérico.

Do ponto de vista de governança, deve-se considerar o controle de viés e representatividade dos dados. É importante avaliar se há equilíbrio entre grupos demográficos, como sexo ou faixa etária, pois desequilíbrios podem levar a modelos que apresentem desempenho diferente para determinados grupos de pessoas.

Documentação da origem e das transformações dos dados. Registrar de onde o dataset foi obtido, quais variáveis foram utilizadas e quais etapas de limpeza e transformação foram aplicadas garantindo transparência.

Princípios de privacidade e anonimização, mesmo que o dataset já seja público. A ausência de dados pessoais identificáveis deve ser verificada.

## Imagens

Pegamos um conjunto de imagens de Raio-x (radriografia) do toráx

<img src="assets/RaioX.png" widht="150">

Radiografias de tórax são um dos exames de imagem médica mais frequentes e econômicos disponíveis. 
O conjunto de dados de radiografias de tórax do NIH é composto por 112.120 imagens de raios X com rótulos de doenças de 30.805 pacientes únicos. Para criar esses rótulos, os autores utilizaram Processamento de Linguagem Natural para extrair classificações de doenças dos laudos radiológicos associados.

Fonte: https://www.kaggle.com/datasets/khanfashee/nih-chest-x-ray-14-224x224-resized

As imagens do dataset podem ser utilizadas para treinar modelos de Visão Computacional capazes de identificar padrões associados a doenças pulmonares e cardíacas em exames de raio-X torácico. Esses modelos podem ser aplicados em tarefas como classificação de doenças, detecção de anomalias e apoio ao diagnóstico médico.

Pensando em selecionar somente uma amostra de imagens, criamos um programa python (Cap1_Dados_Imagens_Selecao.ipynb) que fez a captura de somente 200 imagens, mantendo a distruibuição original de imagens por tipo de doença detectada.

<img src="assets/Redistribuir_imagens.png" widht="150">

### Governança e Tratamento
Antes do treinamento, é necessário realizar um tratamento das imagens. Isso inclui selecionar um subconjunto representativo do dataset, organizar as imagens por classe de doença, padronizar o tamanho e o formato das imagens e remover arquivos corrompidos ou duplicados.
Vamos usar arquiteturas de redes neurais convolucionais (CNNs) ou modelos pré-treinados para aprender padrões visuais presentes nos exames.

Em relação à governança de dados, é importante documentar a origem do dataset, verificar as licenças de uso e registrar todas as etapas de tratamento realizadas nas imagens. Também é necessário considerar possíveis viéses do dataset, já que os exames foram coletados em um contexto hospitalar específico. Além disso, deve-se garantir que as imagens estejam anonimizadas, sem informações que possam identificar pacientes.


## Textos
Focando em captar dados textuais exploramos diversos artigos científicos e acadêmicos na https://www.scielo.br
Escolhemos os dois artigos:
- O Impacto Das Doenças Cardiovasculares Nas Perdas Econômicas

Autora: Fátima Marinho
- A Promoção da Saúde e a Prevenção Integrada dos Fatores de Risco para Doenças Cardiovasculares
- 
Autores: Amanda Gomes Ribeiro; Rosângela Minardi Mitre Cotta e Sônia Machado Rocha Ribeiro.

<img src="assets/Texto_Saude_Cardio.png" widht="150">

Podemos utilizar esses dois artigos para treinar ou adaptar um modelo de NLP em saúde cardiovascular.
Os dois artigos trazem vocabulário típico de epidemiologia, economia da saúde, promoção da saúde, atenção primária, fatores de risco, políticas públicas, etc., o que 
ajuda o modelo a aprender termos técnicos em português neste domínio. 
Podemos extrair entidades que identifiquem diferentes doenças (cardiopatia isquêmica, AVC, hipertensão) e extrair indicadores (AVPP, PIB, mortalidade, internações, custos), além de fatores de risco (tabagismo, 
sedentarismo, dieta). 

Os textos também apresentam um vocabulário técnico para profissionais de saúde. Enquanto um é um mini editorial focado em impacto econômico e o outro é um artigo de revisão amplo sobre promoção da saúde, o corpus permite nos treinar o modelo a reconhecer diferentes estilos (editorial, revisão teórica, relato de experiência), o que é útil para recomendar material adequado ao tipo de público. 

Para médicos, esses textos podem alimentar ferramentas de apoio à decisão e educação  continuada. Um modelo treinado nesse texto pode gerar respostas rápidas para justificar programas de prevenção, prescrição de atividade física, controle de fatores de risco, e auxiliar em relatórios para gestores. 

Para a população, podemos criar um modelo que transforme o conteúdo técnico em informação acessível, personalizada e persuasiva. 


# 📁 Estrutura de pastas

Dentre os arquivos e pastas presentes na raiz do projeto, definem-se:

- <b>Dataset</b>: Nesta pasta está o arquivo .CSV escolhido, representando os dados númericos.

- <b>Imagens</b>: Aqui estão as 200 imagens de Raio-x do toráx e o programa "Cap1_Dados_Imagens_Selecao.ipynb" usado para selecionar essas imagens.

- <b>Textos</b>: Aqui estão os textos escolhidos para treinamento de um modelo NLP.
  
- <b>assets</b>: Imagens relevantes para documentação desse repositório.
  


