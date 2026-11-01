import { API_URL } from "../constants/api";

const TIMEOUT_MS = 20000;
const DEFAULT_USER_ID = "cardioassist-app";

export class WatsonApiError extends Error {
  constructor(message, { code = "unknown", status = null, retriable = true } = {}) {
    super(message);
    this.name = "WatsonApiError";
    this.code = code;
    this.status = status;
    this.retriable = Boolean(retriable);
  }
}

function createTimeoutSignal(timeoutMs) {
  return new Promise((_, reject) => {
    setTimeout(() => {
      reject(
        new WatsonApiError(
          "O assistente demorou demais para responder. Tente novamente.",
          { code: "timeout" }
        )
      );
    }, timeoutMs);
  });
}

/**
 * Envia uma mensagem para o backend e devolve { reply, sessionId, timestamp }.
 * O session_id é gerenciado pelo cliente para manter o contexto da conversa.
 *
 * @param {string} text        Texto do usuário.
 * @param {{ sessionId?: string|null }} options Sessão opcional já criada.
 */
export async function sendChatMessage(text, { sessionId = null } = {}) {
  const clean = String(text).trim();
  if (!clean) {
    throw new WatsonApiError(
      "Escreva uma mensagem antes de enviar.",
      { code: "empty", retriable: false }
    );
  }

  let response;
  try {
    response = await Promise.race([
      fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: clean,
          session_id: sessionId,
          user_id: DEFAULT_USER_ID,
        }),
      }),
      createTimeoutSignal(TIMEOUT_MS),
    ]);
  } catch (err) {
    if (err instanceof WatsonApiError) {
      throw err;
    }
    throw new WatsonApiError(
      "Não foi possível conectar com o servidor. Verifique se o backend está ativo e se a URL da API está correta.",
      { code: "network" }
    );
  }

  let body;
  try {
    body = await response.json();
  } catch {
    body = {};
  }

  if (!response.ok) {
    throw new WatsonApiError(
      body.error || "O servidor não conseguiu processar a mensagem.",
      { code: statusToCode(response.status), status: response.status }
    );
  }

  return {
    reply: body.reply ?? "",
    sessionId: body.session_id ?? sessionId,
    timestamp: body.timestamp ?? new Date().toISOString(),
  };
}

function statusToCode(status) {
  switch (status) {
    case 501:
      return "not-configured";
    case 507:
      return "auth-failed";
    case 504:
      return "timeout";
    case 429:
      return "quota";
    case 502:
      return "watson-error";
    default:
      return "server-error";
  }
}

/**
 * Converte o erro em uma mensagem amigável para o usuário final.
 */
export function friendlyErrorText(err) {
  if (err instanceof WatsonApiError) {
    switch (err.code) {
      case "not-configured":
        return "O backend não está configurado com os IDs do Watson. Verifique o arquivo .env do backend.";
      case "auth-failed":
        return "Não foi possível autenticar com o Watson. Verifique a API key no backend.";
      case "quota":
        return "A cota do plano do Watson foi atingida. Aguarde alguns minutos e tente novamente.";
      case "network":
        return "Não foi possível conectar com o servidor. Verifique se o backend está ativo (python app.py) e a URL da API.";
      case "timeout":
        return "O assistente demorou demais para responder. Toque em Tentar novamente.";
      default:
        return err.message || "O assistente não conseguiu processar a resposta.";
    }
  }
  return "Ocorreu um erro inesperado. Tente novamente em instantes.";
}