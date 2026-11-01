/**
 * Cliente HTTP do app — o mesmo contrato do frontend web.
 *
 * Responsabilidades:
 *
 * 1. **desembrulhar o envelope** `RespostaAPI[T]` (`status`, `dados`, `erros`, ...);
 * 2. **transformar falha em erro tipado** com o `codigo` estavel do contrato;
 * 3. **anexar o JWT** nas rotas protegidas;
 * 4. **renovar o token uma vez** em `401` (o backend tem `/auth/refresh` com rotacao);
 * 5. **distinguir backend fora do ar** de erro de negocio.
 *
 * Os tokens ficam **em memoria**: o app nao persiste sessao entre aberturas. Para um MVP
 * academico isso e suficiente e evita guardar token no armazenamento do aparelho.
 */

import { TEMPO_LIMITE_MS, URL_DA_API } from "./configuracao.js";

let acesso = null;
let renovacao = null;
let aoExpirar = null;

export function definirTokens({ access_token, refresh_token } = {}) {
  acesso = access_token ?? null;
  renovacao = refresh_token ?? null;
}

export function limparTokens() {
  acesso = null;
  renovacao = null;
}

export function definirTratadorDeExpiracao(tratador) {
  aoExpirar = tratador;
}

/** Erro devolvido pela API, com o codigo estavel do contrato. */
export class ErroDaAPI extends Error {
  constructor({ codigo, mensagem, campo = null, detalhe = null, http = null }) {
    super(mensagem || "A API recusou a requisicao.");
    this.name = "ErroDaAPI";
    this.codigo = codigo || "ERRO_INTERNO";
    this.mensagem = mensagem || "A API recusou a requisicao.";
    this.campo = campo;
    this.detalhe = detalhe;
    this.http = http;
  }

  get semPermissao() {
    return this.http === 403;
  }

  get naoConfigurado() {
    return this.codigo === "NAO_CONFIGURADO";
  }

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
    this.tempoEsgotado = causa?.mensagem === "tempo esgotado";
  }
}

/** Corrida entre a promessa e um prazo (o `fetch` do RN nao tem `AbortSignal.timeout`). */
function comTempoLimite(promessa, ms) {
  let temporizador;
  const prazo = new Promise((_, rejeitar) => {
    temporizador = setTimeout(() => rejeitar(new Error("tempo esgotado")), ms);
  });
  return Promise.race([promessa, prazo]).finally(() => clearTimeout(temporizador));
}

function codigoDoHttp(status) {
  if (status === 401) return "NAO_AUTENTICADO";
  if (status === 403) return "NAO_AUTORIZADO";
  if (status === 404) return "NAO_ENCONTRADO";
  if (status === 409) return "CONFLITO";
  if (status === 422) return "CONTRATO_VIOLADO";
  if (status === 429) return "TAXA_EXCEDIDA";
  return status >= 500 ? "ERRO_INTERNO" : "CONTRATO_VIOLADO";
}

async function umaVez(metodo, caminho, opcoes = {}) {
  const { corpo, autenticado = true, timeout = TEMPO_LIMITE_MS } = opcoes;

  const cabecalhos = {};
  if (corpo !== undefined) cabecalhos["Content-Type"] = "application/json";
  if (autenticado && acesso) cabecalhos.Authorization = `Bearer ${acesso}`;

  let resposta;
  try {
    resposta = await comTempoLimite(
      fetch(URL_DA_API + caminho, {
        method: metodo,
        headers: cabecalhos,
        body: corpo === undefined ? undefined : JSON.stringify(corpo),
      }),
      timeout
    );
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
  if (!resposta.ok || status === "ERRO" || status === "INCOMPLETO") {
    const primeiro = Array.isArray(envelope?.erros) ? envelope.erros[0] : null;
    throw new ErroDaAPI({
      codigo: primeiro?.codigo ?? codigoDoHttp(resposta.status),
      mensagem: primeiro?.mensagem ?? `Falha HTTP ${resposta.status}.`,
      campo: primeiro?.campo,
      detalhe: primeiro?.detalhe,
      http: resposta.status,
    });
  }

  return envelope ?? { status: "CONCLUIDO", dados: null };
}

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
    return false;
  }
}

/** Executa uma chamada e devolve o envelope. Em `401`, renova uma vez e repete. */
export async function requisitar(metodo, caminho, opcoes = {}) {
  try {
    return await umaVez(metodo, caminho, opcoes);
  } catch (erro) {
    if (erro instanceof ErroDaAPI && erro.http === 401 && renovacao) {
      if (await renovarSessao()) return umaVez(metodo, caminho, opcoes);
      limparTokens();
      aoExpirar?.();
    }
    throw erro;
  }
}

/** Mensagem amigavel para exibir na tela. */
export function mensagemDoErro(erro) {
  if (erro instanceof ErroDeRede) {
    return erro.tempoEsgotado
      ? "O backend demorou demais para responder. Tente novamente."
      : erro.mensagem;
  }
  if (erro instanceof ErroDaAPI) return erro.mensagem;
  return erro?.message || "Erro inesperado.";
}
