/**
 * Endpoints do contrato (`CONTRATOS_API.md` §8) usados pelo app.
 *
 * Todas as funcoes devolvem o **envelope** — assim a tela tem acesso a `dados` e tambem
 * a `avisos` e `limitacoes`.
 */

import { requisitar } from "./cliente.js";

/** `GET /health` — estado do servico. */
export function saude() {
  return requisitar("GET", "/health", { autenticado: false });
}

/** `POST /auth/login` — devolve `{access_token, refresh_token, expira_em}`. */
export function entrar(email, senha) {
  return requisitar("POST", "/auth/login", {
    corpo: { email, senha },
    autenticado: false,
  });
}

/** `POST /auth/logout` — revoga as sessoes do usuario. */
export function sair() {
  return requisitar("POST", "/auth/logout");
}

/** `GET /auth/me` — usuario do token (**sem** `senha_hash`). */
export function meuUsuario() {
  return requisitar("GET", "/auth/me");
}

/** `GET /pacientes` — `dados` e uma **lista**. */
export function listarPacientes({ limite = 50 } = {}) {
  return requisitar("GET", `/pacientes?limite=${limite}`);
}

/** `GET /avaliacoes` — resumos, mais recentes primeiro. */
export function listarAvaliacoes({ limite = 20, idPaciente = null } = {}) {
  const filtro = idPaciente ? `&id_paciente=${encodeURIComponent(idPaciente)}` : "";
  return requisitar("GET", `/avaliacoes?limite=${limite}${filtro}`);
}

/** `GET /avaliacoes/{id}` — historico auditavel (traz o contrato da Fase 6). */
export function obterAvaliacao(idExecucao) {
  return requisitar("GET", `/avaliacoes/${encodeURIComponent(idExecucao)}`);
}

/** `GET /iot/leituras` — exige `OPERADOR` ou `MEDICO`. */
export function listarLeituras({ limite = 10 } = {}) {
  return requisitar("GET", `/iot/leituras?limite=${limite}`);
}

/** `POST /chat` — exige `OPERADOR` ou `MEDICO`. */
export function enviarMensagem(mensagem, idConversa = null) {
  const corpo = { mensagem };
  if (idConversa) corpo.id_conversa = idConversa;
  return requisitar("POST", "/chat", { corpo, timeout: 60000 });
}

/** `GET /conversas/{id}` — `dados` e a **lista** de mensagens. */
export function historicoDaConversa(idConversa) {
  return requisitar("GET", `/conversas/${encodeURIComponent(idConversa)}`);
}
