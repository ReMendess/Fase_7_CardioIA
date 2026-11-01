"""Repositorio de telemetria IoT (``monitoramentos``).

⚠️ A telemetria **nao** alimenta o modelo preditivo no MVP (Decisao D4): ela e
persistida para visualizacao e para uso futuro. O ``recebido_em`` e **carimbado pelo
backend** — o firmware da Fase 3 nao envia timestamp nem identificador.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from ..base import agora_utc
from ..enums import OrigemDoTransporte
from ..modelos import Monitoramento
from .base import RepositorioBase

__all__ = ["MonitoramentoRepositorio"]


class MonitoramentoRepositorio(RepositorioBase):
    """Acesso a ``monitoramentos``."""

    def registrar(
        self,
        *,
        id_dispositivo: str,
        origem_transporte: OrigemDoTransporte,
        temperatura: float | None = None,
        bpm: int | None = None,
        umidade: float | None = None,
        luminosidade: float | None = None,
        movimento: bool | None = None,
        id_paciente: str | None = None,
        payload: dict[str, Any] | None = None,
        recebido_em: datetime | None = None,
    ) -> Monitoramento:
        """Registra uma leitura.

        Pelo menos um sinal vital (``temperatura`` ou ``bpm``) e obrigatorio — a
        restricao tambem existe no banco (``CHECK``), aqui a mensagem fica legivel.

        Raises:
            ErroDaAPIException: nenhum sinal vital informado (``CONTRATO_VIOLADO``)
                ou violacao de integridade/deduplicacao (``CONFLITO``).
        """
        from ...contratos.erros import CodigoDeErro, ErroDaAPIException

        if temperatura is None and bpm is None:
            raise ErroDaAPIException(
                CodigoDeErro.CONTRATO_VIOLADO,
                "Informe ao menos um sinal vital: 'temperatura' ou 'bpm'.",
            )

        return self._adicionar_e_confirmar(
            Monitoramento(
                id_dispositivo=id_dispositivo.strip(),
                id_paciente=id_paciente,
                origem_transporte=origem_transporte,
                temperatura=temperatura,
                bpm=bpm,
                umidade=umidade,
                luminosidade=luminosidade,
                movimento=movimento,
                payload_json=payload,
                recebido_em=recebido_em or agora_utc(),
            )
        )

    def buscar_por_id(self, id_leitura: str) -> Monitoramento | None:
        """Busca pela chave primaria."""
        return self.sessao.get(Monitoramento, id_leitura)

    def ultimas(
        self,
        *,
        id_dispositivo: str | None = None,
        limite: int = 50,
        deslocamento: int = 0,
    ) -> list[Monitoramento]:
        """Ultimas leituras (mais recentes primeiro), com filtro e paginacao."""
        consulta = select(Monitoramento)
        if id_dispositivo is not None:
            consulta = consulta.where(Monitoramento.id_dispositivo == id_dispositivo)
        consulta = (
            consulta.order_by(Monitoramento.recebido_em.desc())
            .limit(limite)
            .offset(deslocamento)
        )
        return list(self.sessao.scalars(consulta))

    def listar_por_paciente(
        self, id_paciente: str, *, limite: int = 50
    ) -> list[Monitoramento]:
        """Leituras vinculadas a um paciente (mais recentes primeiro)."""
        consulta = (
            select(Monitoramento)
            .where(Monitoramento.id_paciente == id_paciente)
            .order_by(Monitoramento.recebido_em.desc())
            .limit(limite)
        )
        return list(self.sessao.scalars(consulta))

    def contar_desde(self, inicio: datetime, *, id_paciente: str | None = None) -> int:
        """Conta leituras a partir de um instante.

        Base do indicador ``eventos_24h`` **caso** a integracao IoT->modelo venha a ser
        ativada no futuro (hoje ela nao e — Decisao D4).
        """
        consulta = select(func.count()).select_from(Monitoramento).where(
            Monitoramento.recebido_em >= inicio
        )
        if id_paciente is not None:
            consulta = consulta.where(Monitoramento.id_paciente == id_paciente)
        return int(self.sessao.scalar(consulta) or 0)

    def contar_ultimas_24h(self, *, id_paciente: str | None = None) -> int:
        """Conta leituras das ultimas 24 horas."""
        return self.contar_desde(agora_utc() - timedelta(hours=24), id_paciente=id_paciente)