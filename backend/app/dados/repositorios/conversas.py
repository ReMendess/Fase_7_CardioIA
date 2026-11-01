"""Repositorio de conversas (``conversas`` e ``mensagens``).

🔒 ``session_id_do_provedor`` e **interno** (continuidade no Watson) e nunca e
devolvido ao cliente (``CONTRATOS_API.md`` §4.5, R6). O identificador exposto e o
``id`` da conversa, gerado por este backend.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from ..base import agora_utc
from ..enums import CanalDaConversa, PapelDaMensagem
from ..modelos import Conversa, Mensagem
from .base import RepositorioBase

__all__ = ["ConversaRepositorio"]


class ConversaRepositorio(RepositorioBase):
    """Acesso a ``conversas`` e ``mensagens``."""

    def criar(
        self, *, id_usuario: str, canal: CanalDaConversa, id_paciente: str | None = None
    ) -> Conversa:
        """Abre uma conversa."""
        return self._adicionar_e_confirmar(
            Conversa(id_usuario=id_usuario, canal=canal, id_paciente=id_paciente)
        )

    def buscar_por_id(self, id_conversa: str) -> Conversa | None:
        """Busca pela chave primaria."""
        return self.sessao.get(Conversa, id_conversa)

    def encerrar(self, conversa: Conversa, quando: datetime | None = None) -> None:
        """Marca a conversa como encerrada."""
        conversa.encerrada_em = quando or agora_utc()
        self._confirmar()

    def adicionar_mensagem(
        self,
        *,
        id_conversa: str,
        papel: PapelDaMensagem,
        conteudo: str,
        session_id_do_provedor: str | None = None,
        erro: str | None = None,
    ) -> Mensagem:
        """Registra um turno da conversa."""
        return self._adicionar_e_confirmar(
            Mensagem(
                id_conversa=id_conversa,
                papel=papel,
                conteudo=conteudo,
                session_id_do_provedor=session_id_do_provedor,
                erro=erro,
            )
        )

    def listar_mensagens(self, id_conversa: str, *, limite: int = 200) -> list[Mensagem]:
        """Mensagens da conversa em ordem cronologica."""
        consulta = (
            select(Mensagem)
            .where(Mensagem.id_conversa == id_conversa)
            .order_by(Mensagem.criado_em)
            .limit(limite)
        )
        return list(self.sessao.scalars(consulta))

    def listar_por_usuario(self, id_usuario: str, *, limite: int = 50) -> list[Conversa]:
        """Conversas do usuario (mais recentes primeiro)."""
        consulta = (
            select(Conversa)
            .where(Conversa.id_usuario == id_usuario)
            .order_by(Conversa.iniciada_em.desc())
            .limit(limite)
        )
        return list(self.sessao.scalars(consulta))