"""
CardioAssist — API de chat com IBM Watson Assistant.

Endpoints:
  GET  /health     -> estado do serviço e da configuração com Watson.
  POST /api/chat   -> envia uma mensagem ao assistente e devolve a resposta.
"""

from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from IBM_API import (
    API_KEY,
    ASSISTANT_ID,
    ENVIRONMENT_ID,
    SERVICE_URL,
    get_assistant,
)

app = Flask(__name__)
CORS(app)

# Cliente compartilhado para todas as requisições
assistant = get_assistant()

DEFAULT_USER_ID = "cardioassist-app"


def _extract_reply(payload: dict) -> str:
    """Extrai o texto legível da resposta genérica de Watson."""
    output = payload.get("output", {})
    generic = output.get("generic", [])
    texts = [
        item.get("text", "").strip()
        for item in generic
        if isinstance(item, dict)
        and item.get("response_type") == "text"
        and item.get("text")
    ]
    if not texts:
        return "Hmm, não recebi uma resposta de texto. Tente reformular a sua pergunta, por favor."
    return "\n".join(texts)


def _status_of(exc) -> int:
    """Código HTTP de uma ApiException (0 se não aplica)."""
    return int(getattr(exc, "code", 0) or 0)


def friendly_watson_error(exc) -> tuple:
    """Devolve (mensagem amigável, código HTTP) para uma exceção de Watson."""
    code = _status_of(exc)
    msg = (getattr(exc, "message", None) or str(exc))

    if code in (401, 403):
        return (
            "Não foi possível autenticar com Watson Assistant. Revise WATSON_API_KEY.",
            507,
        )
    if code == 404:
        return (
            "Não foi encontrado o assistente ou a sessão de Watson. "
            "Verifique WATSON_ASSISTANT_ID / WATSON_ENVIRONMENT_ID no backend.",
            502,
        )
    if code == 429:
        return (
            "Foi alcançada a cota do plano de Watson Assistant. "
            "Espere alguns minutos e tente novamente.",
            429,
        )
    if code in (408, 504):
        return (
            "Watson Assistant demorou demasiado a responder. Tente novamente.",
            504,
        )
    if code in (400, 500, 502, 503):
        return (
            "Watson Assistant respondeu com um erro. "
            f"Detalhe: {msg[:300]}",
            502,
        )
    return (
        f"Não foi possível contactar com Watson Assistant. Detalhe: {msg[:300]}",
        502,
    )


def _visible_config() -> dict:
    missing = []
    if not API_KEY:
        missing.append("WATSON_API_KEY")
    if not SERVICE_URL:
        missing.append("WATSON_SERVICE_URL")
    if not ASSISTANT_ID:
        missing.append("WATSON_ASSISTANT_ID")
    if not ENVIRONMENT_ID:
        missing.append("WATSON_ENVIRONMENT_ID")
    return {"missing": missing}


@app.route("/health", methods=["GET"])
def health():
    cfg = _visible_config()
    return jsonify(
        {
            "status": "ok",
            "service": "cardioassist-backend",
            "watson_configured": not cfg["missing"],
            **cfg,
        }
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    session_id = (data.get("session_id") or "").strip() or None
    user_id = (
        (data.get("user_id") or DEFAULT_USER_ID).strip()[:64] or DEFAULT_USER_ID
    )

    if not message:
        return jsonify({"error": "O campo 'message' é obrigatório."}), 400

    cfg = _visible_config()
    if cfg["missing"]:
        return jsonify(
            {
                "error": (
                    "O backend não está configurado para Watson. "
                    f"Faltam: {', '.join(cfg['missing'])}. "
                    "Revise 'Backend/.env.example'."
                )
            }
        ), 501

    try:
        # 1) Criar sessão no primeiro turno (stateful) e reutilizá-la
        if not session_id:
            created = assistant.create_session(
                assistant_id=ASSISTANT_ID,
                environment_id=ENVIRONMENT_ID,
            ).get_result()
            session_id = created.get("session_id")
            if not session_id:
                return jsonify(
                    {"error": "Watson não devolveu um session_id válido."}
                ), 502

        return _send_and_reply(message, session_id, user_id)

    except Exception as exc:  # noqa: BLE001 - reporte amigable
        code = _status_of(exc)
        # Sessão expirada (404): recriá-la e reintentar uma só vez
        if code == 404 and session_id:
            return _recover_session_and_send(message, user_id)

        msg, http = friendly_watson_error(exc)
        return jsonify({"error": msg}), http


def _send_and_reply(message, session_id, user_id):
    """Envia a mensagem ao Watson e devolve a resposta com a sessão."""
    try:
        response = assistant.message(
            assistant_id=ASSISTANT_ID,
            environment_id=ENVIRONMENT_ID,
            session_id=session_id,
            input={"message_type": "text", "text": message},
            user_id=user_id,
        )
        payload = response.get_result()
        return jsonify(
            {
                "reply": _extract_reply(payload),
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:  # noqa: BLE001
        if _status_of(exc) == 404:
            raise  # sessão expirada -> recuperada pelo chamador
        msg, http = friendly_watson_error(exc)
        return jsonify({"error": msg}), http


def _recover_session_and_send(message, user_id):
    """Recria a sessão expirada e reintenta o envio uma vez só."""
    try:
        created = assistant.create_session(
            assistant_id=ASSISTANT_ID,
            environment_id=ENVIRONMENT_ID,
        ).get_result()
        new_session_id = created.get("session_id")
        if not new_session_id:
            return jsonify(
                {"error": "Watson não devolveu um session_id válido ao renovar a sessão."}
            ), 502
        return _send_and_reply(message, new_session_id, user_id)
    except Exception as exc:  # noqa: BLE001
        msg, http = friendly_watson_error(exc)
        return jsonify({"error": msg}), http


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)