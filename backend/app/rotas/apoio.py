"""Apoio comum das rotas: metadados do envelope, IP, papeis e trilha de auditoria.

Existe para nao repetir (e nao divergir) o que **toda** rota autenticada faz: montar os
``metadados`` do envelope, descobrir o IP de origem e registrar auditoria.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .. import NOME_DO_SERVICO
from ..config import Configuracoes
from ..dados.enums import PapelDoUsuario
from ..dados.modelos import Usuario
from ..dados.repositorios.auditoria import AuditoriaRepositorio
from ..seguranca.dependencias import exigir_papeis

__all__ = [
    "LeituraClinica",
    "SomenteMedico",
    "UsoDoAssistente",
    "ip_do_cliente",
    "metadados_da_resposta",
    "registrar_auditoria",
]

#: Dependencia: exige papel ``MEDICO`` (escrita clinica).
SomenteMedico = Annotated[Usuario, Depends(exigir_papeis(PapelDoUsuario.MEDICO))]

#: Dependencia: exige ``MEDICO`` ou ``ADMIN`` (leitura de dado clinico).
LeituraClinica = Annotated[
    Usuario, Depends(exigir_papeis(PapelDoUsuario.MEDICO, PapelDoUsuario.ADMIN))
]

#: Dependencia: uso do assistente conversacional (``OPERADOR`` ou ``MEDICO``).
UsoDoAssistente = Annotated[
    Usuario, Depends(exigir_papeis(PapelDoUsuario.OPERADOR, PapelDoUsuario.MEDICO))
]


def metadados_da_resposta(config: Configuracoes) -> dict[str, str]:
    """Metadados de contexto que acompanham toda resposta (``CONTRATOS_API.md`` §2)."""
    return {"versao_api": config.versao_api, "origem": NOME_DO_SERVICO}


def ip_do_cliente(request: Request) -> str | None:
    """IP de origem, quando disponivel (usado na auditoria)."""
    return request.client.host if request.client else None


def registrar_auditoria(
    sessao: Session,
    *,
    acao: str,
    entidade: str,
    id_usuario: str | None = None,
    id_entidade: str | None = None,
    ip: str | None = None,
    detalhe: dict[str, Any] | None = None,
) -> None:
    """Grava um evento em ``eventos_de_auditoria``.

    🔒 O ``detalhe`` **nao** pode conter payload clinico, dado pessoal nem token
    (``PLANO_SEGURANCA.md`` §7.2) — a responsabilidade e de quem chama.
    """
    AuditoriaRepositorio(sessao).registrar(
        acao=acao,
        entidade=entidade,
        id_usuario=id_usuario,
        id_entidade=id_entidade,
        ip=ip,
        detalhe=detalhe,
    )

