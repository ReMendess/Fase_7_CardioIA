/**
 * Catalogo de dominio do frontend: rotulos e faixas **declarados no contrato**.
 *
 * Nada aqui e inventado:
 *
 * - as 10 features, as faixas e o aviso de baixa confianca vem de
 *   `CONTRATOS_API.md` §4.1 (coluna "Aviso de faixa") e dos achados A3 e A4;
 * - os enums vem de `app/dados/enums.py` (valores reais, conferidos);
 * - o frontend **nao** recalcula regra clinica nenhuma: os alertas da Fase 3 chegam
 *   prontos em `avisos` na resposta da ingestao.
 */


// --------------------------------------------------------------------------- //
// As 10 features do modelo de risco (Fase 6)
// --------------------------------------------------------------------------- //

/**
 * Ordem identica a `COLUNAS_DE_FEATURE` do backend — o formulario envia exatamente
 * estas 10 chaves (regra R3: nenhuma tem valor por padrao).
 *
 * `escala` e `confianca` vem dos achados A3/A4 e servem para a tela **avisar** o
 * usuario do que o numero significa de fato.
 */
export const FEATURES_DO_MODELO = [
  {
    nome: "idade_media",
    rotulo: "Idade",
    unidade: "anos",
    minimo: 18,
    maximo: 90,
    passo: 1,
    escala: "paciente",
    ajuda: "Idade do paciente (nome fixado pelo contrato do modelo).",
  },
  {
    nome: "carga_sistema",
    rotulo: "Carga do sistema",
    unidade: "%",
    minimo: 30.004,
    maximo: 99.977,
    passo: 0.001,
    escala: "episodio",
    ajuda: "Carga da unidade durante o episodio — nao e medicao do paciente.",
  },
  {
    nome: "tempo_espera",
    rotulo: "Tempo de espera",
    unidade: "min",
    minimo: 5,
    maximo: 113.578,
    passo: 0.001,
    escala: "paciente",
    ajuda: "Tempo de espera do paciente ate o atendimento.",
  },
  {
    nome: "fc_media",
    rotulo: "FC media",
    unidade: "bpm",
    minimo: 50,
    maximo: 150,
    passo: 1,
    escala: "paciente",
    ajuda: "Frequencia cardiaca media do paciente na janela.",
  },
  {
    nome: "spo2_media",
    rotulo: "SpO2 media",
    unidade: "%",
    minimo: 83.431,
    maximo: 100,
    passo: 0.001,
    escala: "paciente",
    ajuda: "Saturacao de oxigenio media do paciente na janela.",
  },
  {
    nome: "pa_sistolica",
    rotulo: "PA sistolica",
    unidade: "mmHg",
    minimo: 80,
    maximo: 198.832,
    passo: 0.001,
    escala: "paciente",
    ajuda: "Pressao arterial sistolica do paciente.",
  },
  {
    nome: "temperatura",
    rotulo: "Temperatura",
    unidade: "°C",
    minimo: 10,
    maximo: 40,
    passo: 0.1,
    escala: "paciente",
    confianca: "baixa",
    ajuda:
      "Temperatura CORPORAL (resposta Q2). Achado A3: o gerador da Fase 6 usou " +
      "distribuicao de temperatura AMBIENTE (media ~24 °C) — o valor corporal cai na " +
      "cauda do treino. Feature de baixa confianca.",
  },
  {
    nome: "densidade_eventos",
    rotulo: "Densidade de eventos",
    unidade: "",
    minimo: 0,
    maximo: 13,
    passo: 0.1,
    escala: "paciente",
    ajuda: "Densidade de eventos do paciente.",
  },
  {
    nome: "eventos_24h",
    rotulo: "Eventos em 24 h",
    unidade: "",
    minimo: 0,
    maximo: 9,
    passo: 1,
    escala: "paciente",
    ajuda: "Eventos do paciente nas ultimas 24 horas.",
  },
  {
    nome: "disponibilidade_recursos",
    rotulo: "Disponibilidade de recursos",
    unidade: "%",
    minimo: 20.035,
    maximo: 99.989,
    passo: 0.001,
    escala: "episodio",
    ajuda: "Recursos disponiveis para o atendimento — nao e medicao do paciente.",
  },
];

/** Nomes das features, na ordem do contrato. */
export const NOMES_DAS_FEATURES = FEATURES_DO_MODELO.map((f) => f.nome);

/** Valores iniciais do formulario — vazios, porque **nao existe** valor padrao (R3). */
export function formularioVazio() {
  return Object.fromEntries(NOMES_DAS_FEATURES.map((nome) => [nome, ""]));
}

/** Um exemplo preenchido, para demonstracao rapida (valores ficticios). */
export function exemploPreenchido() {
  return {
    idade_media: "62",
    carga_sistema: "92",
    tempo_espera: "75",
    fc_media: "118",
    spo2_media: "89",
    pa_sistolica: "100",
    temperatura: "37.5",
    densidade_eventos: "7",
    eventos_24h: "5",
    disponibilidade_recursos: "0.4",
  };
}

/** `true` quando o valor esta fora da faixa observada no treino (vira aviso, nao erro). */
export function foraDaFaixa(feature, valor) {
  const numero = Number(valor);
  if (valor === "" || Number.isNaN(numero)) return false;
  return numero < feature.minimo || numero > feature.maximo;
}

// --------------------------------------------------------------------------- //
// Enums (valores reais do backend)
// --------------------------------------------------------------------------- //

/** `ClassificacaoDeRisco` — os dois valores do contrato da Fase 6. */
export const CLASSIFICACOES_DE_RISCO = {
  sem_pico_de_risco: { rotulo: "Sem pico de risco", tom: "ok" },
  pico_de_risco: { rotulo: "Pico de risco", tom: "alerta" },
};

/** `ModoDoPipeline`. */
export const MODOS_DO_PIPELINE = {
  simulado: { rotulo: "Simulado", ajuda: "Nao chama nenhum provedor externo." },
  real: { rotulo: "Real", ajuda: "Exige OPENAI_API_KEY no servidor." },
};

/** `OrigemDosDados`. */
export const ORIGENS_DOS_DADOS = {
  manual: "Digitado manualmente",
  iot: "Telemetria IoT",
  importado: "Importado",
};

/** `OrigemDoTransporte`. */
export const ORIGENS_DO_TRANSPORTE = {
  mqtt: "MQTT",
  rest: "REST",
  simulado: "Simulado",
};

/** `PapelDaMensagem` — atencao: o valor e `user`, nao `usuario`. */
export const PAPEIS_DA_MENSAGEM = {
  user: "Paciente/operador",
  assistant: "Assistente",
};

/** `ClasseDeDiagnosticoDeImagem` (Fase 4). */
export const CLASSES_DE_DIAGNOSTICO = {
  Normal: { rotulo: "Normal", tom: "ok" },
  Pneumonia: { rotulo: "Pneumonia", tom: "alerta" },
};

/** `PapelDoUsuario` do RBAC. */
export const PAPEIS_DE_USUARIO = {
  ADMIN: { rotulo: "Administrador", podeEscrever: false },
  MEDICO: { rotulo: "Medico", podeEscrever: true },
  OPERADOR: { rotulo: "Operador", podeEscrever: false },
};

/** Rotulo legivel de um status do envelope. */
export const STATUS_DA_RESPOSTA = {
  CONCLUIDO: "Concluido",
  CONCLUIDO_COM_RESSALVAS: "Concluido com ressalvas",
  INCOMPLETO: "Incompleto",
  ERRO: "Erro",
};

