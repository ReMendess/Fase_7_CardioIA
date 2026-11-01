"""Erros padronizados da API do CardioIA (Fase 7).

Procedencia dos codigos (nenhum foi inventado do zero — ver ``CONTRATOS_API.md`` §3.2):

- **herdados da Fase 5**: a Fase 5 ja expunha codigos nomeados no cliente HTTP
  (``watsonApi.js`` -> ``statusToCode``): ``not-configured`` (501), ``auth-failed``,
  ``quota`` (429), ``timeout`` (504), ``watson-error`` (502). **Excecao declarada:** o
  ``auth-failed`` herdado usava **507** — que significa ``Insufficient Storage``
  (RFC 4918, WebDAV) e nada tem a ver com autenticacao. Mantivemos o **codigo**
  (``FALHA_DE_AUTENTICACAO_EXTERNA``, que e util) e corrigimos o **transporte** para
  ``502`` — ver :data:`HTTP_POR_CODIGO` e ``CONTRATOS_API.md`` §3.2.1;
- **derivados das excecoes tipadas da Fase 6**: ``PacienteInvalidoError``,
  ``ModeloNaoEncontradoError``, ``ModeloIncompativelError``, ``ErroDePrevisao``,
  ``BaseDeConhecimentoInvalidaError``, ``DadosDoPacienteInvalidosError``;
- **novos da Fase 7**: autenticacao/autorizacao, recursos, limites e configuracao.

Regra do contrato: **falha nunca vira sucesso** — todo erro carrega um codigo estavel,
uma mensagem legivel e, quando aplicavel, o campo culpado.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CodigoDeErro(str, Enum):
    """Codigos de erro estaveis expostos pela API."""

    # --- herdados da Fase 5 (contrato real ja existente) ------------------ #
    NAO_CONFIGURADO = "NAO_CONFIGURADO"
    FALHA_DE_AUTENTICACAO_EXTERNA = "FALHA_DE_AUTENTICACAO_EXTERNA"
    COTA_EXCEDIDA = "COTA_EXCEDIDA"
    TIMEOUT_EXTERNO = "TIMEOUT_EXTERNO"
    ERRO_DE_SERVICO_EXTERNO = "ERRO_DE_SERVICO_EXTERNO"

    # --- derivados das excecoes tipadas da Fase 6 ------------------------- #
    CONTRATO_VIOLADO = "CONTRATO_VIOLADO"
    PACIENTE_INVALIDO = "PACIENTE_INVALIDO"
    DADOS_DO_PACIENTE_INVALIDOS = "DADOS_DO_PACIENTE_INVALIDOS"
    MODELO_INDISPONIVEL = "MODELO_INDISPONIVEL"
    MODELO_INCOMPATIVEL = "MODELO_INCOMPATIVEL"
    FALHA_DE_PREVISAO = "FALHA_DE_PREVISAO"
    BASE_DE_PROTOCOLOS_INVALIDA = "BASE_DE_PROTOCOLOS_INVALIDA"

    # --- novos (Fase 7) --------------------------------------------------- #
    ERRO_DE_SERVICO_DE_VISAO = "ERRO_DE_SERVICO_DE_VISAO"
    NAO_AUTENTICADO = "NAO_AUTENTICADO"
    NAO_AUTORIZADO = "NAO_AUTORIZADO"
    NAO_ENCONTRADO = "NAO_ENCONTRADO"
    CONFLITO = "CONFLITO"
    LIMITE_EXCEDIDO = "LIMITE_EXCEDIDO"
    TAXA_EXCEDIDA = "TAXA_EXCEDIDA"
    ERRO_DE_CONFIGURACAO = "ERRO_DE_CONFIGURACAO"
    ERRO_INTERNO = "ERRO_INTERNO"


#: Codigo HTTP canonico de cada codigo de erro (``CONTRATOS_API.md`` §3.2).
HTTP_POR_CODIGO: dict[CodigoDeErro, int] = {
    # Fase 5 — o codigo e herdado; o transporte de FALHA_DE_AUTENTICACAO_EXTERNA foi
    # corrigido de 507 para 502 (507 = "Insufficient Storage", RFC 4918). Ver §3.2.1.
    CodigoDeErro.NAO_CONFIGURADO: 501,
    CodigoDeErro.FALHA_DE_AUTENTICACAO_EXTERNA: 502,
    CodigoDeErro.COTA_EXCEDIDA: 429,
    CodigoDeErro.TIMEOUT_EXTERNO: 504,
    CodigoDeErro.ERRO_DE_SERVICO_EXTERNO: 502,
    # Fase 6
    CodigoDeErro.CONTRATO_VIOLADO: 422,
    CodigoDeErro.PACIENTE_INVALIDO: 422,
    CodigoDeErro.DADOS_DO_PACIENTE_INVALIDOS: 422,
    CodigoDeErro.MODELO_INDISPONIVEL: 503,
    CodigoDeErro.MODELO_INCOMPATIVEL: 500,
    CodigoDeErro.FALHA_DE_PREVISAO: 500,
    CodigoDeErro.BASE_DE_PROTOCOLOS_INVALIDA: 500,
    # Fase 7
    CodigoDeErro.ERRO_DE_SERVICO_DE_VISAO: 502,
    CodigoDeErro.NAO_AUTENTICADO: 401,
    CodigoDeErro.NAO_AUTORIZADO: 403,
    CodigoDeErro.NAO_ENCONTRADO: 404,
    CodigoDeErro.CONFLITO: 409,
    CodigoDeErro.LIMITE_EXCEDIDO: 413,
    CodigoDeErro.TAXA_EXCEDIDA: 429,
    CodigoDeErro.ERRO_DE_CONFIGURACAO: 500,
    CodigoDeErro.ERRO_INTERNO: 500,
}


class ErroDaAPI(BaseModel):
    """Erro estruturado — nunca apenas texto livre.

    Attributes:
        codigo: codigo estavel (:class:`CodigoDeErro`).
        mensagem: texto legivel (idealmente o da excecao de origem).
        campo: campo culpado, quando aplicavel.
        detalhe: informacao adicional (**nunca** segredo).
    """

    model_config = ConfigDict(extra="forbid")

    codigo: CodigoDeErro
    mensagem: str = Field(min_length=1)
    campo: str | None = None
    detalhe: str | None = None


def http_do_codigo(codigo: CodigoDeErro) -> int:
    """Codigo HTTP canonico de um :class:`CodigoDeErro`."""
    return HTTP_POR_CODIGO[codigo]


#: Tabela de **normalizacao** de um codigo HTTP recebido (ex.: do Starlette) para o
#: codigo de dominio correspondente.
#:
#: Nao e o inverso de :data:`HTTP_POR_CODIGO` — e uma relacao **muitos-para-um**:
#:
#: - ``400`` e ``422`` normalizam para ``CONTRATO_VIOLADO`` (que emitimos como 422);
#: - ``404`` e ``405`` normalizam para ``NAO_ENCONTRADO`` (que emitimos como 404);
#: - ``429`` cobre tanto ``TAXA_EXCEDIDA`` (limite interno) quanto ``COTA_EXCEDIDA``
#:   (cota de servico externo) — o codigo emitido depende de quem detectou a falha.
#:
#: ``507`` **nao** aparece aqui de proposito: a Fase 7 nao o emite (ver §3.2.1) e nenhum
#: componente do Starlette o produz — um 507 inesperado normaliza para ``ERRO_INTERNO``
#: pelo fallback de classe, que e o comportamento correto.
#:
#: Propriedade garantida: a **classe** do status e preservada (4xx continua 4xx,
#: 5xx continua 5xx) — verificado por ``tests/test_contratos_erros.py``.
MAPA_HTTP_PARA_CODIGO: dict[int, CodigoDeErro] = {
    400: CodigoDeErro.CONTRATO_VIOLADO,
    401: CodigoDeErro.NAO_AUTENTICADO,
    403: CodigoDeErro.NAO_AUTORIZADO,
    404: CodigoDeErro.NAO_ENCONTRADO,
    405: CodigoDeErro.NAO_ENCONTRADO,
    409: CodigoDeErro.CONFLITO,
    413: CodigoDeErro.LIMITE_EXCEDIDO,
    422: CodigoDeErro.CONTRATO_VIOLADO,
    429: CodigoDeErro.TAXA_EXCEDIDA,
    501: CodigoDeErro.NAO_CONFIGURADO,
    502: CodigoDeErro.ERRO_DE_SERVICO_EXTERNO,
    503: CodigoDeErro.MODELO_INDISPONIVEL,
    504: CodigoDeErro.TIMEOUT_EXTERNO,
}


def codigo_do_http(status: int) -> CodigoDeErro:
    """Codigo de dominio correspondente a um status HTTP.

    Status nao mapeados caem em :attr:`CodigoDeErro.ERRO_INTERNO` (5xx) ou
    :attr:`CodigoDeErro.CONTRATO_VIOLADO` (4xx).
    """
    if status in MAPA_HTTP_PARA_CODIGO:
        return MAPA_HTTP_PARA_CODIGO[status]
    return CodigoDeErro.ERRO_INTERNO if status >= 500 else CodigoDeErro.CONTRATO_VIOLADO


class ErroDaAPIException(Exception):
    """Excecao de transporte: carrega um :class:`ErroDaAPI` e o codigo HTTP.

    E levantada pelas camadas internas e convertida em envelope pelo handler
    registrado em :mod:`app.main`.
    """

    def __init__(
        self,
        codigo: CodigoDeErro,
        mensagem: str,
        *,
        campo: str | None = None,
        detalhe: str | None = None,
        http: int | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.erro = ErroDaAPI(
            codigo=codigo, mensagem=mensagem, campo=campo, detalhe=detalhe
        )
        self.http = http if http is not None else http_do_codigo(codigo)

    @property
    def codigo(self) -> CodigoDeErro:
        return self.erro.codigo

    @property
    def mensagem(self) -> str:
        return self.erro.mensagem


__all__ = [
    "HTTP_POR_CODIGO",
    "MAPA_HTTP_PARA_CODIGO",
    "CodigoDeErro",
    "ErroDaAPI",
    "ErroDaAPIException",
    "codigo_do_http",
    "http_do_codigo",
]
