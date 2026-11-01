"""Repositorio de auditoria (``eventos_de_auditoria``).

🔒 ``detalhe`` **nao** pode conter payload clinico nem token — a responsabilidade de
nao vazar dado sensivel para a trilha de auditoria e de quem chama
(``PLANO_SEGURANCA.md`` §7.2).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ..modelos import EventoDeAuditoria
from .base import RepositorioBase

__all__ = ["AuditoriaRepositorio"]


class AuditoriaRepositorio(RepositorioBase):
    """Acesso a ``eventos_de_auditoria``."""

    def registrar(
        self,
        *,
        acao: str,
        entidade: str,
        id_usuario: str | None = None,
        id_entidade: str | None = None,
        ip: str | None = None,
        detalhe: dict[str, Any] | None = None,
    ) -> EventoDeAuditoria:
        """Registra um evento de auditoria.

        Args:
            detalhe: contexto adicional **sem** payload clinico e **sem** token.
        """
        return self._adicionar_e_confirmar(
            EventoDeAuditoria(
                acao=acao.strip(),
                entidade=entidade.strip(),
                id_usuario=id_usuario,
                id_entidade=id_entidade,
                ip=ip,
                detalhe_json=detalhe,
            )
        )

    def listar(
        self,
        *,
        acao: str | None = None,
        id_usuario: str | None = None,
        limite: int = 100,
    ) -> list[EventoDeAuditoria]:
        """Eventos mais recentes primeiro, com filtros opcionais."""
        consulta = select(EventoDeAuditoria)
        if acao is not None:
            consulta = consulta.where(EventoDeAuditoria.acao == acao)
        if id_usuario is not None:
            consulta = consulta.where(EventoDeAuditoria.id_usuario == id_usuario)
        consulta = consulta.order_by(EventoDeAuditoria.criado_em.desc()).limit(limite)
        return list(self.sessao.scalars(consulta))