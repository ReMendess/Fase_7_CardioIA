/**
 * Cliente HTTP reutilizavel (item 4 da Etapa D).
 *
 * Responsabilidades:
 *
 * 1. **desembrulhar o envelope** `RespostaAPI[T]` — nenhuma tela precisa saber que
 *    existe `status`/`dados`/`erros` por fora;
 * 2. **transformar falha em excecao tipada** com o `codigo` estavel do contrato
 *    (`NAO_AUTENTICADO`, `NAO_AUTORIZADO`, `NAO_CONFIGURADO`, ...), nunca em texto solto;
 * 3. **anexar o JWT** nas rotas protegidas;
 * 4. **renovar o token uma unica vez** quando o acesso expira (o backend tem
 *    `POST /auth/refresh` com rotacao);
 * 5. **distinguir backend fora do ar** (`ErroDeRede`) de erro de negocio (`ErroDaAPI`).
 *
 * Os tokens ficam **em memoria** aqui. Quem persiste e o `AuthContext` — assim este
 * modulo nao depende de `localStorage` e pode ser executado em Node (script de smoke
 * test), o que permite validar a integracao sem navegador.
 */

import { TEMPO_LIMITE_MS, URL_DA_API } from "./configuracao.js";

// --------------------------------------------------------------------------- //
// Estado dos tokens (em memoria)
// --------------------------------------------------------------------------- //

let acesso = null;
let renovacao = null;
let aoExpirar = null;

/** Guarda o par de tokens recebido do backend. */
export function definirTokens({ access_token, refresh_token } = {}) {
  acesso = access_token ?? null;
  renovacao = refresh_token ?? null;
}

/** Devolve o access token atual (para diagnostico/exibicao). */
export function tokenAtual() {
  return acesso;
}

/** Descarta os tokens em memoria. */
export function limparTokens() {
  acesso = null;
  renovacao = null;
}

/** Registra o que fazer quando a sessao nao pode mais ser renovada. */
export function definirTratadorDeExpiracao(tratador) {
  aoExpirar = tratador;
}

// --------------------------------------------------------------------------- //
// Erros
// --------------------------------------------------------------------------- //

/** Falha devolvida pela API, com o codigo estavel do contrato. */
export class ErroDaAPI extends Error {
  constructor({
    codigo,
    mensagem,
    campo = null,
    detalhe = null,
    http = null,
    envelope = null,
  }) {
    super(mensagem || "A API recusou a requisicao.");
    this.name = "ErroDaAPI";
    this.codigo = codigo || "ERRO_INTERNO";
    /** Texto legivel vindo do envelope (mesmo conteudo de `Error.message`). */
    this.mensagem = mensagem || "A API recusou a requisicao.";
    this.campo = campo;
    this.detalhe = detalhe;
    this.http = http;
    /** Envelope cru: em `INCOMPLETO` o `dados` ainda traz a trilha da Fase 6. */
    this.envelope = envelope;
  }

  /** `true` quando o token esta ausente/expirado (a UI deve voltar ao login). */
  get exigeLogin() {
    return this.http === 401;
  }

  /** `true` quando o papel do usuario nao permite a operacao. */
  get semPermissao() {
    return this.http === 403;
  }

  /** `true` quando falta configuracao no servidor (ex.: Watson sem credencial). */
  get naoConfigurado() {
    return this.codigo === "NAO_CONFIGURADO";
  }

  /** `true` quando um servico externo esta fora do ar ou demorou demais. */
  get servicoExternoIndisponivel() {
    return this.http === 502 || this.http === 504;
  }
}

/** Backend inalcancavel: nao houve resposta HTTP alguma. */
export class ErroDeRede extends Error {
  constructor(causa) {
    super(
      "Nao foi possivel falar com o backend. Confirme que a API da Fase 7 esta no ar " +
        `em ${URL_DA_API}.`
    );
    this.name = "ErroDeRede";
    this.causa = causa;
    this.tempoEsgotado = causa?.name === "TimeoutError";
  }
}

// --------------------------------------------------------------------------- //
// Transporte
// --------------------------------------------------------------------------- //

/** Codigo de dominio para um status HTTP que nao veio no envelope. */
function codigoDoHttp(status) {
  if (status === 401) return "NAO_AUTENTICADO";
  if (status === 403) return "NAO_AUTORIZADO";
  if (status === 404) return "NAO_ENCONTRADO";
  if (status === 409) return "CONFLITO";
  if (status === 413) return "LIMITE_EXCEDIDO";
  if (status === 422) return "CONTRATO_VIOLADO";
  if (status === 429) return "TAXA_EXCEDIDA";
  return status >= 500 ? "ERRO_INTERNO" : "CONTRATO_VIOLADO";
}

/** Uma chamada HTTP, sem tratamento de renovacao. */
async function umaVez(metodo, caminho, opcoes = {}) {
  const {
    corpo,
    autenticado = true,
    multipart = false,
    timeout = TEMPO_LIMITE_MS,
  } = opcoes;

  const cabecalhos = {};
  let carga;

  if (multipart) {
    // `FormData` define o proprio Content-Type (com o boundary) — nao sobrescrever.
    carga = corpo;
  } else if (corpo !== undefined) {
    cabecalhos["Content-Type"] = "application/json";
    carga = JSON.stringify(corpo);
  }

  if (autenticado && acesso) {
    cabecalhos.Authorization = `Bearer ${acesso}`;
  }

  let resposta;
  try {
    resposta = await fetch(URL_DA_API + caminho, {
      method: metodo,
      headers: cabecalhos,
      body: carga,
      signal: AbortSignal.timeout(timeout),
    });
  } catch (erro) {
    throw new ErroDeRede(erro);
  }

  let envelope = null;
  try {
    envelope = await resposta.json();
  } catch {
    envelope = null;
  }

  const status = envelope?.status;
  const falhou = !resposta.ok || status === "ERRO" || status === "INCOMPLETO";

  if (falhou) {
    const primeiro = Array.isArray(envelope?.erros) ? envelope.erros[0] : null;
    throw new ErroDaAPI({
      // Fallback por status: cobre uma resposta que nao veio no envelope (proxy, 502 cru).
      codigo: primeiro?.codigo ?? codigoDoHttp(resposta.status),
      mensagem: primeiro?.mensagem ?? `Falha HTTP ${resposta.status}.`,
      campo: primeiro?.campo,
      detalhe: primeiro?.detalhe,
      http: resposta.status,
      envelope,
    });
  }

  return envelope ?? { status: "CONCLUIDO", dados: null };
}

/** Renova o par de tokens. Devolve `true` se conseguiu. */
async function renovarSessao() {
  if (!renovacao) return false;
  try {
    const envelope = await umaVez("POST", "/auth/refresh", {
      corpo: { refresh_token: renovacao },
      autenticado: false,
    });
    definirTokens(envelope.dados);
    return true;
  } catch {
    // Refresh invalido/expirado: a sessao acabou. Nao propaga o erro daqui —
    // quem decide o que fazer e o chamador original (que tem o erro 401 real).
    return false;
  }
}

/**
 * Executa uma chamada a API e devolve o **envelope** validado.
 *
 * Em `401` tenta renovar o token **uma vez** e repete a chamada original.
 *
 * @throws {ErroDeRede} backend inalcancavel ou tempo esgotado.
 * @throws {ErroDaAPI} a API respondeu com falha (traz `codigo`, `campo`, `http`).
 */
export async function requisitar(metodo, caminho, opcoes = {}) {
  try {
    return await umaVez(metodo, caminho, opcoes);
  } catch (erro) {
    if (erro instanceof ErroDaAPI && erro.http === 401 && renovacao) {
      if (await renovarSessao()) {
        return umaVez(metodo, caminho, opcoes);
      }
      limparTokens();
      aoExpirar?.();
    }
    throw erro;
  }
}

/** Monta o corpo `multipart/form-data` de `POST /imagens`. */
export function corpoDeImagem(arquivo, idPaciente) {
  const dados = new FormData();
  dados.append("imagem", arquivo);
  if (idPaciente) dados.append("id_paciente", idPaciente);
  return dados;
}

/** Mensagem amigavel para exibir na tela, a partir de qualquer erro. */
export function mensagemDoErro(erro) {
  if (erro instanceof ErroDeRede) {
    return erro.tempoEsgotado
      ? "O backend demorou demais para responder. Tente novamente."
      : erro.message;
  }
  if (erro instanceof ErroDaAPI) {
    if (erro.servicoExternoIndisponivel) {
      return `${erro.mensagem} (servico externo indisponivel)`;
    }
    return erro.mensagem;
  }
  return erro?.message || "Erro inesperado.";
}

