"""Repositorios de identidade: ``usuarios`` e ``sessoes``."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from ..base import agora_utc
from ..enums import PapelDoUsuario
from ..modelos import Sessao, Usuario
from .base import RepositorioBase

__all__ = ["SessaoRepositorio", "UsuarioRepositorio"]


def _normalizar_email(email: str) -> str:
    """E-mail sempre em minusculas e sem espacos (chave de login)."""
    return email.strip().lower()


class UsuarioRepositorio(RepositorioBase):
    """Acesso a ``usuarios``."""

    def criar(
        self,
        *,
        nome: str,
        email: str,
        senha_hash: str,
        papel: PapelDoUsuario,
        ativo: bool = True,
    ) -> Usuario:
        """Cria um usuario. O e-mail e normalizado antes de gravar."""
        return self._adicionar_e_confirmar(
            Usuario(
                nome=nome.strip(),
                email=_normalizar_email(email),
                senha_hash=senha_hash,
                papel=papel,
                ativo=ativo,
            )
        )

    def buscar_por_email(self, email: str) -> Usuario | None:
        """Busca pelo e-mail (normalizado). ``None`` se nao existir."""
        return self.sessao.scalar(
            select(Usuario).where(Usuario.email == _normalizar_email(email))
        )

    def buscar_por_id(self, id_usuario: str) -> Usuario | None:
        """Busca pela chave primaria."""
        return self.sessao.get(Usuario, id_usuario)

    def listar(
        self, *, apenas_ativos: bool = False, limite: int = 50, deslocamento: int = 0
    ) -> list[Usuario]:
        """Lista usuarios ordenados por nome."""
        consulta = select(Usuario)
        if apenas_ativos:
            consulta = consulta.where(Usuario.ativo.is_(True))
        consulta = consulta.order_by(Usuario.nome).limit(limite).offset(deslocamento)
        return list(self.sessao.scalars(consulta))

    def registrar_acesso(self, usuario: Usuario, quando: datetime | None = None) -> None:
        """Atualiza o ultimo acesso do usuario."""
        usuario.ultimo_acesso = quando or agora_utc()
        self._confirmar()

    def definir_ativo(self, usuario: Usuario, ativo: bool) -> None:
        """Ativa/desativa o usuario (**soft delete** — nunca excluimos)."""
        usuario.ativo = ativo
        self._confirmar()


class SessaoRepositorio(RepositorioBase):
    """Acesso a ``sessoes`` (refresh tokens).

    Guarda **apenas o hash** do token: um vazamento do banco nao expoe o token
    utilizavel (``PLANO_SEGURANCA.md`` §6).
    """

    def criar(
        self, *, id_usuario: str, token_hash: str, expira_em: datetime
    ) -> Sessao:
        """Registra um refresh token."""
        return self._adicionar_e_confirmar(
            Sessao(id_usuario=id_usuario, token_hash=token_hash, expira_em=expira_em)
        )

    def buscar_por_hash(self, token_hash: str) -> Sessao | None:
        """Busca a sessao pelo hash do token."""
        return self.sessao.scalar(select(Sessao).where(Sessao.token_hash == token_hash))

    def revogar(self, sessao: Sessao, quando: datetime | None = None) -> None:
        """Revoga a sessao (usado no logout e na rotacao de refresh token)."""
        sessao.revogado_em = quando or agora_utc()
        self._confirmar()

    def revogar_todas_do_usuario(self, id_usuario: str) -> int:
        """Revoga todas as sessoes vigentes de um usuario.

        Returns:
            Quantidade de sessoes revogadas.
        """
        vigentes = list(
            self.sessao.scalars(
                select(Sessao).where(
                    Sessao.id_usuario == id_usuario, Sessao.revogado_em.is_(None)
                )
            )
        )
        momento = agora_utc()
        for item in vigentes:
            item.revogado_em = momento
        self._confirmar()
        return len(vigentes)

    def remover_expiradas(self, momento: datetime | None = None) -> int:
        """Apaga sessoes expiradas ou revogadas.

        Returns:
            Quantidade de registros removidos.
        """
        referencia = momento or agora_utc()
        antigas = list(
            self.sessao.scalars(
                select(Sessao).where(
                    (Sessao.expira_em < referencia) | (Sessao.revogado_em.is_not(None))
                )
            )
        )
        for item in antigas:
            self.sessao.delete(item)
        self._confirmar()
        return len(antigas)
