"""Repositorio de analises de imagem (``analises_de_imagem``).

🔒 **Privacidade:** o binario da imagem **nao** e armazenado — apenas o ``hash_sha256``
e os metadados (``MODELO_DADOS.md`` §3.9).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ..enums import ClasseDeDiagnosticoDeImagem
from ..modelos import AnaliseDeImagem
from .base import RepositorioBase

__all__ = ["AnaliseDeImagemRepositorio"]


class AnaliseDeImagemRepositorio(RepositorioBase):
    """Acesso a ``analises_de_imagem``."""

    def registrar(
        self,
        *,
        id_usuario: str,
        nome_arquivo: str,
        mime: str,
        tamanho_bytes: int,
        hash_sha256: str,
        classe: ClasseDeDiagnosticoDeImagem,
        confianca: float,
        modelo_utilizado: str,
        limiar_decisao: float,
        id_paciente: str | None = None,
        resposta: dict[str, Any] | None = None,
        erro: str | None = None,
    ) -> AnaliseDeImagem:
        """Registra o resultado de uma analise.

        O binario **nao** entra aqui: guarda-se o hash e os metadados.
        """
        return self._adicionar_e_confirmar(
            AnaliseDeImagem(
                id_usuario=id_usuario,
                id_paciente=id_paciente,
                nome_arquivo=nome_arquivo,
                mime=mime,
                tamanho_bytes=tamanho_bytes,
                hash_sha256=hash_sha256,
                classe=classe,
                confianca=confianca,
                modelo_utilizado=modelo_utilizado,
                limiar_decisao=limiar_decisao,
                resposta_json=dict(resposta) if resposta is not None else None,
                erro=erro,
            )
        )

    def buscar_por_id(self, id_analise: str) -> AnaliseDeImagem | None:
        """Busca pela chave primaria."""
        return self.sessao.get(AnaliseDeImagem, id_analise)

    def listar_por_paciente(
        self, id_paciente: str, *, limite: int = 50
    ) -> list[AnaliseDeImagem]:
        """Historico do paciente (mais recentes primeiro)."""
        consulta = (
            select(AnaliseDeImagem)
            .where(AnaliseDeImagem.id_paciente == id_paciente)
            .order_by(AnaliseDeImagem.criado_em.desc())
            .limit(limite)
        )
        return list(self.sessao.scalars(consulta))

    def buscar_por_hash(self, hash_sha256: str) -> list[AnaliseDeImagem]:
        """Analises do mesmo arquivo (deteccao de reenvio/duplicidade)."""
        consulta = select(AnaliseDeImagem).where(
            AnaliseDeImagem.hash_sha256 == hash_sha256
        )
        return list(self.sessao.scalars(consulta))