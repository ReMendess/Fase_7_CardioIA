"""Adapter HTTP do servico de visao computacional da Fase 4.

**Por que HTTP e nao import direto** (``DECISOES_ARQUITETURAIS.md`` §3.4, alternativa **C**):
o ``app.py`` da Fase 4 carrega TensorFlow no *import* (``load_model`` no topo) e o conflito
de dependencias com o ``scikit-learn`` da Fase 6 esta registrado como risco **R8**. Manter o
servico em **processo separado** (porta **5001**, mapa de portas §3.5) isola esse custo e
impede que uma falha do TensorFlow derrube o backend. **Aqui nao se importa TensorFlow.**

**Nao ha duplicacao de logica:** o pre-processamento da imagem (``target_size=(128, 128)``,
``/255.0``, ``expand_dims``) e a decisao (``probability > 0.5``) continuam **dentro** do
servico da Fase 4. Este modulo apenas **envia a imagem e le a resposta** — a unica
"duplicacao" e o *conhecimento* declarado abaixo.

**Conhecimento do artefato (achado I9):** a Fase 4 **nao** informa o nome do modelo nem o
limiar. O backend os acrescenta a partir do que **sabe** do artefato — nao inventa a partir
do modelo. As constantes abaixo sao verificadas por teste **contra o arquivo-fonte** da
Fase 4 (``Ir_Alem2/backend/app.py``), que e a fonte normativa (risco **R6**).

| Constante | Valor | Origem |
|---|---|---|
| ``NOME_DO_MODELO_DA_VISAO`` | ``mobilenet_pneumonia.keras`` | ``MODEL_PATH`` no fonte |
| ``LIMIAR_DE_DECISAO_DA_VISAO`` | ``0.5`` | literal no fonte |
| ``DIMENSOES_ESPERADAS_DA_IMAGEM`` | ``(128, 128)`` | ``target_size`` no fonte |
| ``CAMPO_DO_ARQUIVO`` | ``image`` | ``request.files["image"]`` no fonte |
| ``CLASSES_POSSIVEIS`` | ``Normal`` / ``Pneumonia`` | literais no fonte |
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from ..config import Configuracoes
from ..contratos.erros import CodigoDeErro, ErroDaAPIException

__all__ = [
    "AVISO_DE_USO_DA_VISAO",
    "CAMPO_DO_ARQUIVO",
    "CLASSES_POSSIVEIS",
    "DIMENSOES_ESPERADAS_DA_IMAGEM",
    "LIMIAR_DE_DECISAO_DA_VISAO",
    "NOME_DO_MODELO_DA_VISAO",
    "RespostaDaVisao",
    "chamar_previsao",
    "url_da_previsao",
]

#: Nome do artefato carregado pelo servico (``MODEL_PATH.name`` na Fase 4).
NOME_DO_MODELO_DA_VISAO = "mobilenet_pneumonia.keras"

#: Limiar de decisao literal no servico da Fase 4 (``probability > 0.5``).
LIMIAR_DE_DECISAO_DA_VISAO = 0.5

#: Dimensoes para as quais o servico redimensiona antes de prever.
DIMENSOES_ESPERADAS_DA_IMAGEM = (128, 128)

#: Nome do campo do arquivo no ``multipart/form-data`` (o servico exige ``image``).
CAMPO_DO_ARQUIVO = "image"

#: Classes que o servico pode devolver no campo ``class``.
CLASSES_POSSIVEIS = ("Normal", "Pneumonia")

#: Aviso obrigatorio em toda resposta de diagnostico por imagem.
AVISO_DE_USO_DA_VISAO = (
    "Resultado de modelo de visao computacional treinado em base publica SINTETICA e "
    "academica, sem validacao clinica. NAO e diagnostico, NAO e prescricao e NAO substitui "
    "avaliacao medica. A imagem nao e armazenada pelo backend: guarda-se apenas o hash."
)

#: Caminho do endpoint de previsao no servico da Fase 4.
CAMINHO_DA_PREVISAO = "/predict"


@dataclass(frozen=True)
class RespostaDaVisao:
    """Resposta **crua** do servico, ja validada contra o contrato dele.

    Mantem os nomes de origem (``class``/``confidence``) — a traducao para os nomes da
    Fase 7 acontece na borda (``CONTRATOS_API.md`` §9, nota **N4**).
    """

    classe: str
    confianca: float


def url_da_previsao(config: Configuracoes) -> str:
    """URL completa do endpoint de previsao (sem barra duplicada)."""
    return f"{config.servico_visao_url.rstrip('/')}{CAMINHO_DA_PREVISAO}"


def _cabecalhos(config: Configuracoes) -> dict[str, str]:
    """Cabecalhos da chamada interna.

    O ``X-Service-Token`` e enviado **apenas** quando configurado. O servico da Fase 4 nao
    valida nada hoje (achado S5: APIs legadas sem autenticacao) — o cabecalho existe para
    quando houver um proxy autenticado na frente, como preve o mapa de canais
    (``DECISOES_ARQUITETURAIS.md`` §4.3: "rede interna + token de servico").
    """
    if not config.servico_visao_token.strip():
        return {}
    return {"X-Service-Token": config.servico_visao_token}


def _validar_resposta(corpo: Any) -> RespostaDaVisao:
    """Confere que a resposta do servico respeita o contrato dele.

    Raises:
        ErroDaAPIException: corpo nao e objeto, ``class`` desconhecida ou ``confidence``
            nao numerica/fora de 0-100 (``ERRO_DE_SERVICO_DE_VISAO``). Um servico que
            responde algo fora do contrato nao pode virar diagnostico silencioso.
    """
    if not isinstance(corpo, dict):
        raise ErroDaAPIException(
            CodigoDeErro.ERRO_DE_SERVICO_DE_VISAO,
            "O servico de visao devolveu uma resposta que nao e um objeto JSON.",
            detalhe=f"tipo recebido: {type(corpo).__name__}",
        )

    classe = corpo.get("class")
    confianca = corpo.get("confidence")

    if classe not in CLASSES_POSSIVEIS:
        raise ErroDaAPIException(
            CodigoDeErro.ERRO_DE_SERVICO_DE_VISAO,
            "O servico de visao devolveu uma classe desconhecida.",
            campo="class",
            detalhe=f"recebido: {classe!r}; esperado um de {CLASSES_POSSIVEIS}.",
        )

    # `isinstance(True, int)` e True: sem a guarda, `true` passaria como confianca 1.
    if isinstance(confianca, bool) or not isinstance(confianca, (int, float)):
        raise ErroDaAPIException(
            CodigoDeErro.ERRO_DE_SERVICO_DE_VISAO,
            "O servico de visao devolveu uma confianca nao numerica.",
            campo="confidence",
            detalhe=f"recebido: {confianca!r}",
        )

    valor = float(confianca)
    if not 0.0 <= valor <= 100.0:
        raise ErroDaAPIException(
            CodigoDeErro.ERRO_DE_SERVICO_DE_VISAO,
            "O servico de visao devolveu uma confianca fora de 0-100.",
            campo="confidence",
            detalhe=f"recebido: {valor}",
        )

    return RespostaDaVisao(classe=str(classe), confianca=valor)


def chamar_previsao(
    conteudo: bytes,
    *,
    nome_arquivo: str,
    mime: str,
    config: Configuracoes,
) -> RespostaDaVisao:
    """Envia a imagem ao servico da Fase 4 e devolve a resposta validada.

    Args:
        conteudo: bytes da imagem (nunca persistidos pelo backend).
        nome_arquivo: nome original, usado apenas no ``multipart``.
        mime: tipo do arquivo, ja validado na borda.
        config: configuracao com URL, token e timeout do servico.

    Returns:
        :class:`RespostaDaVisao` com os nomes de origem (``class``/``confidence``).

    Raises:
        ErroDaAPIException: ``TIMEOUT_EXTERNO`` (504) quando o servico nao responde no
            prazo; ``ERRO_DE_SERVICO_DE_VISAO`` (502) quando ele esta inacessivel, devolve
            status diferente de 200 ou responde fora do contrato.
    """
    url = url_da_previsao(config)
    limite = config.servico_visao_timeout_segundos

    try:
        # Cliente por chamada: simples e sem estado global a gerenciar. O servico e interno
        # e a chamada e sequencial por requisicao; pool de conexoes nao agrega aqui.
        with httpx.Client(timeout=limite) as cliente:
            resposta = cliente.post(
                url,
                files={CAMPO_DO_ARQUIVO: (nome_arquivo, conteudo, mime)},
                headers=_cabecalhos(config),
            )
    except httpx.TimeoutException as erro:
        raise ErroDaAPIException(
            CodigoDeErro.TIMEOUT_EXTERNO,
            "O servico de visao nao respondeu no prazo.",
            detalhe=f"{url} apos {limite}s ({type(erro).__name__}).",
        ) from erro
    except httpx.HTTPError as erro:
        raise ErroDaAPIException(
            CodigoDeErro.ERRO_DE_SERVICO_DE_VISAO,
            "Nao foi possivel falar com o servico de visao.",
            detalhe=(
                f"{type(erro).__name__} em {url}. Confirme que o servico da Fase 4 esta no ar "
                "(porta 5001) — ele exige TensorFlow, que nao faz parte do backend central."
            ),
        ) from erro

    if resposta.status_code != 200:
        raise ErroDaAPIException(
            CodigoDeErro.ERRO_DE_SERVICO_DE_VISAO,
            f"O servico de visao respondeu HTTP {resposta.status_code}.",
            detalhe=f"corpo: {resposta.text[:300]!r}",
        )

    try:
        corpo = resposta.json()
    except ValueError as erro:
        raise ErroDaAPIException(
            CodigoDeErro.ERRO_DE_SERVICO_DE_VISAO,
            "O servico de visao devolveu um corpo que nao e JSON.",
            detalhe=f"corpo: {resposta.text[:300]!r}",
        ) from erro

    return _validar_resposta(corpo)