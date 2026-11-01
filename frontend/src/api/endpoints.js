/**
 * Uma funcao por rota do contrato (`CONTRATOS_API.md` §8).
 *
 * Todas devolvem o **envelope** `RespostaAPI[T]` — assim a tela tem acesso a `dados`
 * e tambem a `avisos`, `limitacoes` e `metadados` (que o contrato exige nas respostas
 * de decisao automatizada).
 *
 * Nenhuma funcao inventa dado: quando o backend nao tem a informacao, ela nao existe
 * aqui.
 */

import { corpoDeImagem, requisitar } from "./cliente.js";

// --------------------------------------------------------------------------- //
// Saude
// --------------------------------------------------------------------------- //

/** `GET /health` — estado do servico e presenca do artefato do modelo. */
export function saude() {
  return requisitar("GET", "/health", { autenticado: false });
}

// --------------------------------------------------------------------------- //
// Autenticacao
// --------------------------------------------------------------------------- //

/** `POST /auth/login` — devolve `{access_token, refresh_token, expira_em}`. */
export function entrar(email, senha) {
  return requisitar("POST", "/auth/login", {
    corpo: { email, senha },
    autenticado: false,
  });
}

/** `POST /auth/logout` — revoga as sessoes do usuario autenticado. */
export function sair() {
  return requisitar("POST", "/auth/logout");
}

/** `GET /auth/me` — usuario do token (**sem** `senha_hash`). */
export function meuUsuario() {
  return requisitar("GET", "/auth/me");
}

// --------------------------------------------------------------------------- //
// Pacientes
// --------------------------------------------------------------------------- //

/** `GET /pacientes` — `dados` e uma **lista** (paginacao por `limite`/`deslocamento`). */
export function listarPacientes({ limite = 50, deslocamento = 0, apenasAtivos = true } = {}) {
  const parametros = new URLSearchParams({
    limite: String(limite),
    deslocamento: String(deslocamento),
    apenas_ativos: String(apenasAtivos),
  });
  return requisitar("GET", `/pacientes?${parametros}`);
}

/** `POST /pacientes` — exige papel `MEDICO`. */
export function criarPaciente(nome) {
  return requisitar("POST", "/pacientes", { corpo: { nome } });
}

/** `GET /pacientes/{id}` — detalhe de um paciente. */
export function obterPaciente(idPaciente) {
  return requisitar("GET", `/pacientes/${encodeURIComponent(idPaciente)}`);
}

// --------------------------------------------------------------------------- //
// Avaliacoes
// --------------------------------------------------------------------------- //

/**
 * `POST /avaliacoes` — executa o pipeline da Fase 6.
 *
 * As **10 features sao obrigatorias**; nenhum valor e preenchido por padrao (regra R3).
 *
 * @param {object} pedido
 * @param {string} pedido.idPaciente
 * @param {Record<string, number>} pedido.features  as 10 features do contrato
 * @param {"manual"|"iot"|"importado"} pedido.origemDosDados
 * @param {"simulado"|"real"} [pedido.modo]  `real` exige `OPENAI_API_KEY` no servidor
 */
export function criarAvaliacao({
  idPaciente,
  features,
  origemDosDados = "manual",
  modo = "simulado",
}) {
  return requisitar("POST", "/avaliacoes", {
    corpo: {
      id_paciente: idPaciente,
      features,
      origem_dos_dados: origemDosDados,
      modo,
    },
    // O modo `real` chama o provedor LLM: o prazo tem de ser maior que o padrao.
    timeout: modo === "real" ? 120000 : 60000,
  });
}

/** `GET /avaliacoes` — `dados` e uma **lista** de resumos, mais recentes primeiro. */
export function listarAvaliacoes({ limite = 50, deslocamento = 0, idPaciente = null } = {}) {
  const parametros = new URLSearchParams({
    limite: String(limite),
    deslocamento: String(deslocamento),
  });
  if (idPaciente) parametros.set("id_paciente", idPaciente);
  return requisitar("GET", `/avaliacoes?${parametros}`);
}

/** `GET /avaliacoes/{id}` — historico auditavel (traz o contrato da Fase 6 persistido). */
export function obterAvaliacao(idExecucao) {
  return requisitar("GET", `/avaliacoes/${encodeURIComponent(idExecucao)}`);
}

// --------------------------------------------------------------------------- //
// Telemetria IoT
// --------------------------------------------------------------------------- //

/** `GET /iot/leituras` — exige `OPERADOR` ou `MEDICO` (`ADMIN` recebe 403). */
export function listarLeituras({ limite = 50, deslocamento = 0, idDispositivo = null } = {}) {
  const parametros = new URLSearchParams({
    limite: String(limite),
    deslocamento: String(deslocamento),
  });
  if (idDispositivo) parametros.set("id_dispositivo", idDispositivo);
  return requisitar("GET", `/iot/leituras?${parametros}`);
}

// --------------------------------------------------------------------------- //
// Assistente conversacional
// --------------------------------------------------------------------------- //

/** `POST /chat` — exige `OPERADOR` ou `MEDICO`; sem Watson configurado devolve 501. */
export function enviarMensagem(mensagem, idConversa = null) {
  const corpo = { mensagem };
  if (idConversa) corpo.id_conversa = idConversa;
  return requisitar("POST", "/chat", { corpo, timeout: 60000 });
}

/** `GET /conversas/{id}` — `dados` e a **lista** de mensagens, em ordem cronologica. */
export function historicoDaConversa(idConversa) {
  return requisitar("GET", `/conversas/${encodeURIComponent(idConversa)}`);
}

// --------------------------------------------------------------------------- //
// Visao computacional
// --------------------------------------------------------------------------- //

/**
 * `POST /imagens` — `multipart/form-data`; exige `MEDICO`.
 *
 * O servico da Fase 4 roda em processo separado e **exige TensorFlow**: se estiver
 * fora do ar, a API responde `502 ERRO_DE_SERVICO_DE_VISAO`.
 */
export function analisarImagem(arquivo, idPaciente = null) {
  return requisitar("POST", "/imagens", {
    corpo: corpoDeImagem(arquivo, idPaciente),
    multipart: true,
    timeout: 60000,
  });
}
