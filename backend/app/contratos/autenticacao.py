"""Contratos de autenticacao (``CONTRATOS_API.md`` §4.7 e §8).

Campos **nunca** expostos em nenhuma resposta: ``senha_hash``, ``token_hash`` e o
``session_id`` de provedor externo (``PLANO_SEGURANCA.md`` §7.2).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..dados.enums import PapelDoUsuario

__all__ = [
    "PedidoDeLogin",
    "PedidoDeRefresh",
    "RespostaDeLogout",
    "RespostaDeSessao",
    "UsuarioPublico",
]

#: Tamanho maximo do e-mail (limite pratico do RFC 5321).
TAMANHO_MAXIMO_DO_EMAIL = 254


class _ContratoFechado(BaseModel):
    """Base dos DTOs: proibe campos desconhecidos (postura do projeto)."""

    model_config = ConfigDict(extra="forbid")


class PedidoDeLogin(_ContratoFechado):
    """Credenciais de acesso.

    Nota: ``senha`` usa ``min_length=1`` de proposito — no login o valor apenas precisa
    **conferir** com o hash existente. O comprimento minimo de senha e uma regra de
    **criacao** e vive em :func:`app.seguranca.senhas.gerar_hash`.
    """

    email: str = Field(min_length=3, max_length=TAMANHO_MAXIMO_DO_EMAIL)
    senha: str = Field(min_length=1, repr=False)


class PedidoDeRefresh(_ContratoFechado):
    """Pedido de renovacao do token de acesso."""

    refresh_token: str = Field(min_length=16, repr=False)


class RespostaDeSessao(_ContratoFechado):
    """Tokens emitidos no login e na rotacao do refresh.

    A rotacao devolve **um novo par**: o refresh token anterior e revogado, entao o
    cliente precisa do novo valor para continuar (``MODELO_DADOS.md`` §6.1).
    """

    access_token: str = Field(min_length=16, repr=False)
    refresh_token: str = Field(min_length=16, repr=False)
    expira_em: datetime = Field(
        description="Instante UTC em que o access_token expira (o refresh tem prazo proprio)."
    )


class RespostaDeLogout(_ContratoFechado):
    """Resultado do encerramento de sessao."""

    encerrado: bool = True
    sessoes_revogadas: int = Field(ge=0)


class UsuarioPublico(_ContratoFechado):
    """Dados do usuario expostos pela API (**sem** ``senha_hash``)."""

    id_usuario: str = Field(min_length=8)
    nome: str = Field(min_length=1)
    email: str = Field(min_length=3)
    papel: PapelDoUsuario
    ativo: bool
    criado_em: datetime
    ultimo_acesso: datetime | None = None
