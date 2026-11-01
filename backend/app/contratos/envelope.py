"""Envelope comum de resposta da API do CardioIA (Fase 7).

Generalizacao do contrato ``RespostaDaExecucao`` da Fase 6 para **todas** as
respostas do backend, conforme ``CONTRATOS_API.md`` §2.

Campos reaproveitados da Fase 6: ``id_execucao``, ``gerado_em``, ``status``,
``avisos``, ``limitacoes``, ``erros``.
Campos introduzidos pela Fase 7: ``dados`` (generalizacao) e ``metadados``.

Regras de coerencia (``CONTRATOS_API.md`` §1.1, R1):

- ``CONCLUIDO`` / ``CONCLUIDO_COM_RESSALVAS`` exigem ``dados`` e **proibem** ``erros``;
- ``INCOMPLETO`` / ``ERRO`` exigem **ao menos um** erro — falha nunca fica muda.

Sobre ``limitacoes``: o envelope **nao** define avisos clinicos proprios. O endpoint
de risco (item 4 da Etapa C) preenche esse campo com
``cardioia.schemas.risk_result.LIMITACOES_PADRAO`` — evitando duplicar o texto da Fase 6.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .erros import ErroDaAPI

T = TypeVar("T")


class StatusDaResposta(str, Enum):
    """Estado real da execucao — os **mesmos 4 valores** da Fase 6."""

    CONCLUIDO = "CONCLUIDO"
    CONCLUIDO_COM_RESSALVAS = "CONCLUIDO_COM_RESSALVAS"
    INCOMPLETO = "INCOMPLETO"
    ERRO = "ERRO"


#: Status que representam sucesso (exigem ``dados`` e nenhum erro).
STATUS_COM_SUCESSO: tuple[StatusDaResposta, ...] = (
    StatusDaResposta.CONCLUIDO,
    StatusDaResposta.CONCLUIDO_COM_RESSALVAS,
)

#: Status que representam falha (exigem ao menos um erro).
STATUS_COM_FALHA: tuple[StatusDaResposta, ...] = (
    StatusDaResposta.INCOMPLETO,
    StatusDaResposta.ERRO,
)


def novo_id_execucao() -> str:
    """Identificador da execucao (UUID4)."""
    return str(uuid.uuid4())


def agora_utc() -> datetime:
    """Instante atual em UTC (o contrato exige timezone)."""
    return datetime.now(timezone.utc)


class RespostaAPI(BaseModel, Generic[T]):
    """Envelope unico de resposta.

    Attributes:
        id_execucao: UUID4 da execucao. Em avaliacoes de risco e o **mesmo**
            ``id_execucao`` gerado pela Fase 6 (chave de correlacao).
        gerado_em: instante UTC de geracao.
        status: :class:`StatusDaResposta`.
        dados: conteudo tipado (``None`` quando ha falha).
        avisos: avisos nao bloqueantes (ex.: valor fora da faixa de treino).
        limitacoes: limitacoes do resultado (preenchido com o texto da Fase 6
            nos endpoints de decisao).
        erros: lista de :class:`~app.contratos.erros.ErroDaAPI`.
        metadados: informacoes de contexto (``versao_api``, ``origem``, ...).
    """

    model_config = ConfigDict(extra="forbid")

    id_execucao: str = Field(default_factory=novo_id_execucao, min_length=8)
    gerado_em: datetime = Field(default_factory=agora_utc)
    status: StatusDaResposta = StatusDaResposta.CONCLUIDO
    dados: T | None = None
    avisos: list[str] = Field(default_factory=list)
    limitacoes: list[str] = Field(default_factory=list)
    erros: list[ErroDaAPI] = Field(default_factory=list)
    metadados: dict[str, Any] = Field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Coerencia
    # ------------------------------------------------------------------ #

    @model_validator(mode="after")
    def _coerencia_entre_status_e_conteudo(self) -> RespostaAPI[T]:
        """Impede resposta "bem-sucedida" sem dados e falha sem explicacao."""
        if self.status in STATUS_COM_SUCESSO:
            if self.dados is None:
                raise ValueError(
                    f"status={self.status.value} exige 'dados'; sem conteudo a "
                    "execucao nao pode ser considerada concluida."
                )
            if self.erros:
                raise ValueError(
                    f"status={self.status.value} nao pode conter 'erros'; use "
                    "INCOMPLETO ou ERRO."
                )
        elif not self.erros:
            raise ValueError(
                f"status={self.status.value} exige ao menos um item em 'erros' "
                "(nada de falha silenciosa)."
            )
        return self

    # ------------------------------------------------------------------ #
    # Conveniencias
    # ------------------------------------------------------------------ #

    @property
    def concluida(self) -> bool:
        """``True`` apenas quando o status representa sucesso."""
        return self.status in STATUS_COM_SUCESSO

    @property
    def tem_ressalvas(self) -> bool:
        """``True`` quando ha avisos ou limitacoes a exibir."""
        return bool(self.avisos or self.limitacoes)

    def como_dicionario(self) -> dict[str, Any]:
        """Serializa em tipos nativos (JSON-safe)."""
        return self.model_dump(mode="json")


def resposta_de_sucesso(
    dados: T,
    *,
    status: StatusDaResposta = StatusDaResposta.CONCLUIDO,
    avisos: list[str] | None = None,
    limitacoes: list[str] | None = None,
    metadados: dict[str, Any] | None = None,
    id_execucao: str | None = None,
) -> RespostaAPI[T]:
    """Monta um envelope de sucesso.

    Raises:
        ValueError: se ``status`` nao for de sucesso.
    """
    if status not in STATUS_COM_SUCESSO:
        raise ValueError(
            f"resposta_de_sucesso exige status de sucesso; recebido '{status.value}'."
        )
    return RespostaAPI[T](
        id_execucao=id_execucao or novo_id_execucao(),
        status=status,
        dados=dados,
        avisos=avisos or [],
        limitacoes=limitacoes or [],
        metadados=metadados or {},
    )


def resposta_de_erro(
    erros: list[ErroDaAPI] | ErroDaAPI,
    *,
    dados: Any | None = None,
    status: StatusDaResposta = StatusDaResposta.ERRO,
    avisos: list[str] | None = None,
    limitacoes: list[str] | None = None,
    metadados: dict[str, Any] | None = None,
    id_execucao: str | None = None,
) -> RespostaAPI[Any]:
    """Monta um envelope de falha (exige ao menos um erro).

    Args:
        erros: um :class:`ErroDaAPI` ou a lista deles (nunca vazia).
        dados: **conteudo opcional** da execucao que falhou. Existe porque alguns
            contratos (``RespostaDaExecucao`` da Fase 6) carregam diagnostico proprio na
            falha — a trilha de execucao e o que explica *onde* quebrou. Quando ``None``,
            o envelope fica sem conteudo (caso dos handlers de erro, em que nao houve
            execucao).

    Raises:
        ValueError: se ``status`` nao for de falha ou se a lista estiver vazia.
    """
    if status not in STATUS_COM_FALHA:
        raise ValueError(
            f"resposta_de_erro exige status de falha; recebido '{status.value}'."
        )
    lista = [erros] if isinstance(erros, ErroDaAPI) else list(erros)
    if not lista:
        raise ValueError("resposta_de_erro exige ao menos um erro.")
    return RespostaAPI[Any](
        id_execucao=id_execucao or novo_id_execucao(),
        status=status,
        dados=dados,
        avisos=avisos or [],
        limitacoes=limitacoes or [],
        erros=lista,
        metadados=metadados or {},
    )


__all__ = [
    "STATUS_COM_FALHA",
    "STATUS_COM_SUCESSO",
    "RespostaAPI",
    "StatusDaResposta",
    "agora_utc",
    "novo_id_execucao",
    "resposta_de_erro",
    "resposta_de_sucesso",
]
