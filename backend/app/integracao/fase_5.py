"""Adapter do assistente conversacional da Fase 5 (IBM Watson Assistant).

**Divergencia declarada da Decisao 1** (que preve "import direto de ``IBM_API.py``"):
o backend **nao importa** aquele modulo. O motivo e de **seguranca**, nao de conveniencia:
``IBM_API.py`` le as credenciais com ``os.getenv(...)`` usando **a chave real do projeto como
valor default** (achado **S1**; a correcao esta em **C1**). Importar o modulo grava essa
chave nos seus constantes de topo, e ``get_assistant()`` a usaria em silencio sempre que as
variaveis de ambiente nao estivessem definidas — exatamente o que a regra de migracao proibe
("o backend da Fase 7 le **apenas** de variavel de ambiente; **nao** usa o default").

Pior: ``Backend/app.py`` executa ``assistant = get_assistant()`` **no import** — importa-lo
criaria um cliente autenticado com a chave vazada e um ``Flask(__name__)``.

O que a decisao realmente queria — **reaproveitar o cliente testado, sem duplicar logica** —
e preservado: usa-se o **mesmo SDK**, a **mesma versao de API** e o **mesmo timeout**, e as
constantes sao verificadas por teste **contra o arquivo-fonte** da Fase 5 (risco **R6**).
A "camada de traducao fina" prevista na decisao esta aqui, com o **mesmo mapeamento** de
``friendly_watson_error`` — e um teste confere as faixas de status contra o fonte.

| Constante | Valor | Origem em ``IBM_API.py`` / ``app.py`` |
|---|---|---|
| ``VERSAO_DA_API_DO_WATSON`` | ``2024-08-25`` | ``VERSION`` |
| ``TIMEOUT_PADRAO_DO_WATSON`` | ``30`` | ``WATSON_TIMEOUT`` |
| ``USUARIO_PADRAO_DO_ASSISTENTE`` | ``cardioassist-app`` | ``DEFAULT_USER_ID`` |
| ``MENSAGEM_SEM_TEXTO`` | *(texto fixo)* | fallback de ``_extract_reply`` |

⚠️ As credenciais vem **somente** de :class:`~app.config.Configuracoes` (que le o ambiente).
Nenhum valor default de credencial existe neste modulo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..config import Configuracoes
from ..contratos.erros import CodigoDeErro, ErroDaAPIException

__all__ = [
    "MENSAGEM_SEM_TEXTO",
    "TIMEOUT_PADRAO_DO_WATSON",
    "USUARIO_PADRAO_DO_ASSISTENTE",
    "VERSAO_DA_API_DO_WATSON",
    "RespostaDoAssistente",
    "configuracao_faltando",
    "conversar",
    "criar_cliente",
    "extrair_resposta",
    "traduzir_erro",
]

#: Versao da API de Watson Assistant usada pelo SDK (literal de ``IBM_API.py``).
VERSAO_DA_API_DO_WATSON = "2024-08-25"

#: Timeout de rede das chamadas ao Watson, em segundos (literal de ``IBM_API.py``).
TIMEOUT_PADRAO_DO_WATSON = 30

#: Identificador de usuario enviado ao Watson (literal de ``app.py``).
USUARIO_PADRAO_DO_ASSISTENTE = "cardioassist-app"

#: Texto devolvido quando o Watson nao manda nenhum bloco de texto (fallback de ``_extract_reply``).
MENSAGEM_SEM_TEXTO = (
    "Hmm, não recebi uma resposta de texto. Tente reformular a sua pergunta, por favor."
)

#: Variaveis de ambiente que o assistente exige (mesmos nomes da Fase 5).
VARIAVEIS_DO_WATSON: tuple[str, ...] = (
    "WATSON_API_KEY",
    "WATSON_SERVICE_URL",
    "WATSON_ASSISTANT_ID",
    "WATSON_ENVIRONMENT_ID",
)


@dataclass(frozen=True)
class RespostaDoAssistente:
    """Resultado de um turno: o texto e a sessao **interna** do provedor.

    ``session_id_do_provedor`` **nunca** vai ao cliente (achado **I8**): ele existe para dar
    continuidade a conversa no Watson e fica em ``mensagens.session_id_do_provedor``.
    """

    resposta: str
    session_id_do_provedor: str


def configuracao_faltando(config: Configuracoes) -> list[str]:
    """Variaveis do Watson ausentes — mesma checagem de ``_visible_config`` na Fase 5.

    Returns:
        Lista de nomes faltantes (vazia quando o assistente esta configurado).
    """
    valores = {
        "WATSON_API_KEY": config.watson_api_key,
        "WATSON_SERVICE_URL": config.watson_service_url,
        "WATSON_ASSISTANT_ID": config.watson_assistant_id,
        "WATSON_ENVIRONMENT_ID": config.watson_environment_id,
    }
    return [nome for nome in VARIAVEIS_DO_WATSON if not valores[nome].strip()]


def criar_cliente(config: Configuracoes) -> Any:
    """Cria o cliente ``AssistantV2`` usando **somente** a configuracao.

    O import do SDK e **tardio**: sem ``ibm-watson`` instalado o backend continua no ar e a
    requisicao responde ``501``, em vez de o processo nao subir.

    Raises:
        ErroDaAPIException: SDK ausente (``NAO_CONFIGURADO``, 501).
    """
    try:
        from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
        from ibm_watson import AssistantV2
    except ImportError as erro:
        raise ErroDaAPIException(
            CodigoDeErro.NAO_CONFIGURADO,
            "O SDK do IBM Watson nao esta instalado.",
            detalhe=f"{type(erro).__name__}: {erro}. Instale 'ibm-watson' para usar o assistente.",
        ) from erro

    autenticador = IAMAuthenticator(config.watson_api_key)
    assistente = AssistantV2(version=VERSAO_DA_API_DO_WATSON, authenticator=autenticador)
    assistente.set_service_url(config.watson_service_url)
    assistente.set_http_config({"timeout": config.watson_timeout_segundos})
    return assistente


def extrair_resposta(payload: Any) -> str:
    """Extrai o texto legivel da resposta generica do Watson.

    Replica ``_extract_reply`` da Fase 5: percorre ``output.generic``, mantem apenas os
    blocos ``response_type == "text"`` e junta com quebra de linha. Sem nenhum bloco de
    texto, devolve :data:`MENSAGEM_SEM_TEXTO` — **nunca** uma resposta inventada.
    """
    if not isinstance(payload, dict):
        return MENSAGEM_SEM_TEXTO

    saida = payload.get("output")
    generico = saida.get("generic") if isinstance(saida, dict) else None
    if not isinstance(generico, list):
        return MENSAGEM_SEM_TEXTO

    textos = [
        str(item.get("text", "")).strip()
        for item in generico
        if isinstance(item, dict)
        and item.get("response_type") == "text"
        and item.get("text")
    ]
    return "\n".join(textos) if textos else MENSAGEM_SEM_TEXTO


def _codigo_do_provedor(excecao: BaseException) -> int:
    """Codigo HTTP da ``ApiException`` do SDK (``0`` quando nao se aplica)."""
    return int(getattr(excecao, "code", 0) or 0)


def _detalhe_do_provedor(excecao: BaseException) -> str:
    """Mensagem tecnica do provedor, truncada (mesmo limite de 300 da Fase 5)."""
    mensagem = getattr(excecao, "message", None) or str(excecao)
    return str(mensagem)[:300]


def traduzir_erro(excecao: BaseException) -> ErroDaAPIException:
    """Traduz uma excecao do SDK para o contrato de erro da Fase 7.

    O **mapeamento de status e o mesmo** de ``friendly_watson_error`` (Fase 5) — verificado
    por teste contra o arquivo-fonte. A diferenca e de forma: a Fase 5 concatenava o detalhe
    tecnico na mensagem; aqui ele vai para o campo ``detalhe`` do contrato (nota **N5**), e a
    mensagem amigavel fica limpa.

    Returns:
        A excecao de API correspondente. Nunca devolve ``None``: um codigo desconhecido cai
        em ``ERRO_DE_SERVICO_EXTERNO`` (502).
    """
    codigo = _codigo_do_provedor(excecao)
    detalhe = _detalhe_do_provedor(excecao)

    if codigo in (401, 403):
        return ErroDaAPIException(
            CodigoDeErro.FALHA_DE_AUTENTICACAO_EXTERNA,
            "Nao foi possivel autenticar com o Watson Assistant. Revise WATSON_API_KEY.",
            detalhe=detalhe,
        )
    if codigo == 404:
        return ErroDaAPIException(
            CodigoDeErro.ERRO_DE_SERVICO_EXTERNO,
            "Nao foi encontrado o assistente ou a sessao no Watson. Verifique "
            "WATSON_ASSISTANT_ID / WATSON_ENVIRONMENT_ID.",
            detalhe=detalhe,
        )
    if codigo == 429:
        return ErroDaAPIException(
            CodigoDeErro.COTA_EXCEDIDA,
            "Foi alcancada a cota do plano do Watson Assistant. Espere alguns minutos.",
            detalhe=detalhe,
        )
    if codigo in (408, 504):
        return ErroDaAPIException(
            CodigoDeErro.TIMEOUT_EXTERNO,
            "O Watson Assistant demorou demais para responder. Tente novamente.",
            detalhe=detalhe,
        )
    if codigo in (400, 500, 502, 503):
        return ErroDaAPIException(
            CodigoDeErro.ERRO_DE_SERVICO_EXTERNO,
            "O Watson Assistant respondeu com um erro.",
            detalhe=detalhe,
        )
    return ErroDaAPIException(
        CodigoDeErro.ERRO_DE_SERVICO_EXTERNO,
        "Nao foi possivel contactar o Watson Assistant.",
        detalhe=detalhe or type(excecao).__name__,
    )


def _criar_sessao(assistente: Any, config: Configuracoes) -> str:
    """Abre uma sessao no Watson e devolve o identificador.

    Raises:
        ErroDaAPIException: ``ERRO_DE_SERVICO_EXTERNO`` (502) quando o Watson nao devolve
            ``session_id`` — sem ele nao ha conversa a continuar.
    """
    criada = assistente.create_session(
        assistant_id=config.watson_assistant_id,
        environment_id=config.watson_environment_id,
    ).get_result()

    identificador = criada.get("session_id") if isinstance(criada, dict) else None
    if not identificador:
        raise ErroDaAPIException(
            CodigoDeErro.ERRO_DE_SERVICO_EXTERNO,
            "O Watson nao devolveu um session_id valido.",
            detalhe="Resposta de create_session sem 'session_id'.",
        )
    return str(identificador)


def _enviar(assistente: Any, config: Configuracoes, *, mensagem: str, session_id: str) -> str:
    """Envia a mensagem em uma sessao existente e devolve o texto extraido."""
    resposta = assistente.message(
        assistant_id=config.watson_assistant_id,
        environment_id=config.watson_environment_id,
        session_id=session_id,
        input={"message_type": "text", "text": mensagem},
        user_id=USUARIO_PADRAO_DO_ASSISTENTE,
    )
    return extrair_resposta(resposta.get_result())


def conversar(
    mensagem: str,
    *,
    session_id: str | None,
    config: Configuracoes,
) -> RespostaDoAssistente:
    """Envia um turno ao Watson, criando ou recuperando a sessao conforme necessario.

    Fluxo (o mesmo de ``app.py``): sem ``session_id``, abre uma sessao; se o envio falhar com
    **404** (sessao expirada no Watson), abre outra e **reintenta uma unica vez**.

    Raises:
        ErroDaAPIException: erro traduzido do provedor (502/429/504).
    """
    assistente = criar_cliente(config)

    if not session_id:
        try:
            session_id = _criar_sessao(assistente, config)
        except ErroDaAPIException:
            raise
        except Exception as erro:  # noqa: BLE001 - o SDK levanta ApiException
            raise traduzir_erro(erro) from erro

    try:
        return RespostaDoAssistente(
            resposta=_enviar(assistente, config, mensagem=mensagem, session_id=session_id),
            session_id_do_provedor=session_id,
        )
    except Exception as erro:  # noqa: BLE001 - o SDK levanta ApiException
        if _codigo_do_provedor(erro) != 404:
            raise traduzir_erro(erro) from erro

    # Sessao expirada no Watson: recria e reintenta **uma vez** (comportamento da Fase 5).
    try:
        renovada = _criar_sessao(assistente, config)
        return RespostaDoAssistente(
            resposta=_enviar(assistente, config, mensagem=mensagem, session_id=renovada),
            session_id_do_provedor=renovada,
        )
    except Exception as erro:  # noqa: BLE001
        raise traduzir_erro(erro) from erro