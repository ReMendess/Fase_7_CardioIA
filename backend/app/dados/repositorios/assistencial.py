"""Repositorios do agregado assistencial: ``pacientes`` e ``avaliacoes_de_risco``.

Este e o agregado central do sistema. ``AvaliacaoRepositorio.criar`` grava, em **uma
unica transacao**, a avaliacao e as tres tabelas-filhas que decompõem o
``RespostaDaExecucao`` da Fase 6 — ou o agregado inteiro entra, ou nada entra
(``MODELO_DADOS.md`` §5.2).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select

from ...contratos.envelope import StatusDaResposta
from ...contratos.erros import CodigoDeErro, ErroDaAPIException
from ..enums import ClassificacaoDeRisco, ModoDoPipeline, OrigemDosDados
from ..modelos import (
    COLUNAS_DE_FEATURE,
    AvaliacaoDeRisco,
    IndicadorDeterministico,
    Paciente,
    PassoDaExecucao,
    ProtocoloAplicado,
)
from .base import RepositorioBase, montar_filhos

__all__ = ["AvaliacaoRepositorio", "PacienteRepositorio", "normalizar_features"]


def normalizar_features(features: Mapping[str, Any]) -> dict[str, float]:
    """Confere que o conjunto e **exatamente** as 10 features do modelo.

    Espelha a postura de ``predict.validar_paciente`` (Fase 6): campo ausente e campo
    desconhecido sao **erro**, nao aviso — e **nenhum valor e preenchido por padrao**
    (Decisao D4, salvaguarda 1).

    Raises:
        ErroDaAPIException: campo ausente/desconhecido ou valor invalido
            (``PACIENTE_INVALIDO``).
    """
    esperadas = set(COLUNAS_DE_FEATURE)
    informadas = set(features)

    ausentes = sorted(esperadas - informadas)
    desconhecidas = sorted(informadas - esperadas)

    if ausentes or desconhecidas:
        problemas: list[str] = []
        if ausentes:
            problemas.append(f"ausentes: {', '.join(ausentes)}")
        if desconhecidas:
            problemas.append(f"desconhecidos: {', '.join(desconhecidas)}")
        raise ErroDaAPIException(
            CodigoDeErro.PACIENTE_INVALIDO,
            "Conjunto de features invalido (" + "; ".join(problemas) + ").",
            detalhe="O modelo espera exatamente: " + ", ".join(COLUNAS_DE_FEATURE) + ".",
        )

    valores: dict[str, float] = {}
    for coluna in COLUNAS_DE_FEATURE:
        bruto = features[coluna]
        if isinstance(bruto, bool) or not isinstance(bruto, (int, float)):
            raise ErroDaAPIException(
                CodigoDeErro.PACIENTE_INVALIDO,
                f"'{coluna}' deve ser numerico; recebido {type(bruto).__name__}.",
                campo=coluna,
            )
        numero = float(bruto)
        if math.isnan(numero) or math.isinf(numero):
            raise ErroDaAPIException(
                CodigoDeErro.PACIENTE_INVALIDO,
                f"'{coluna}' recebeu um valor invalido ({numero}).",
                campo=coluna,
            )
        if numero < 0:
            raise ErroDaAPIException(
                CodigoDeErro.PACIENTE_INVALIDO,
                f"'{coluna}' nao pode ser negativo ({numero}).",
                campo=coluna,
            )
        valores[coluna] = numero
    return valores


class PacienteRepositorio(RepositorioBase):
    """Acesso a ``pacientes`` (apenas identidade)."""

    def criar(self, *, nome: str, criado_por: str, ativo: bool = True) -> Paciente:
        """Cadastra um paciente."""
        return self._adicionar_e_confirmar(
            Paciente(nome=nome.strip(), criado_por=criado_por, ativo=ativo)
        )

    def buscar_por_id(self, id_paciente: str) -> Paciente | None:
        """Busca pela chave primaria."""
        return self.sessao.get(Paciente, id_paciente)

    def listar(
        self, *, apenas_ativos: bool = False, limite: int = 50, deslocamento: int = 0
    ) -> list[Paciente]:
        """Lista pacientes por ordem de cadastro (mais recentes primeiro)."""
        consulta = select(Paciente)
        if apenas_ativos:
            consulta = consulta.where(Paciente.ativo.is_(True))
        consulta = (
            consulta.order_by(Paciente.criado_em.desc()).limit(limite).offset(deslocamento)
        )
        return list(self.sessao.scalars(consulta))

    def definir_ativo(self, paciente: Paciente, ativo: bool) -> None:
        """Ativa/desativa o paciente (**soft delete**)."""
        paciente.ativo = ativo
        self._confirmar()


def _como_classificacao(valor: Any) -> ClassificacaoDeRisco | None:
    """Converte o texto vindo do pipeline para o enum persistido."""
    if valor is None:
        return None
    return ClassificacaoDeRisco(str(valor))


class AvaliacaoRepositorio(RepositorioBase):
    """Acesso a ``avaliacoes_de_risco`` e suas tres tabelas-filhas."""

    # ------------------------------------------------------------------ #
    # Escrita (agregado completo, em uma transacao)
    # ------------------------------------------------------------------ #

    def criar(
        self,
        *,
        id_execucao: str,
        id_paciente: str,
        id_usuario: str,
        features: Mapping[str, Any],
        origem_dos_dados: OrigemDosDados,
        status: StatusDaResposta,
        modo: ModoDoPipeline,
        diagnostico: Mapping[str, Any] | None = None,
        protocolos: Sequence[Mapping[str, Any]] = (),
        indicadores: Sequence[Mapping[str, Any]] = (),
        passos: Sequence[Mapping[str, Any]] = (),
        resposta: Mapping[str, Any] | None = None,
        avisos: Sequence[str] = (),
        erros: Sequence[str] = (),
        agente_final: str | None = None,
        versao_do_sdk: str | None = None,
        duracao_segundos: float | None = None,
        criado_em: datetime | None = None,
    ) -> AvaliacaoDeRisco:
        """Grava a avaliacao e as filhas em **uma unica transacao**.

        Args:
            id_execucao: UUID gerado pela Fase 6 (chave de correlacao).
            features: as 10 features do modelo — validadas por
                :func:`normalizar_features` (sem defaults).
            diagnostico: ``DiagnosticoDaPredicao`` da Fase 6 (opcional em falha).
            protocolos/indicadores/passos: itens da ``RespostaDaExecucao``.
            resposta: contrato integral (``como_dicionario()``) para auditoria.

        Raises:
            ErroDaAPIException: features fora do contrato, campo desconhecido nas
                filhas ou violacao de integridade (``CONFLITO``).
        """
        valores = normalizar_features(features)
        dados_do_diagnostico = dict(diagnostico or {})
        origem_do_modelo = dados_do_diagnostico.get("origem_do_modelo") or {}

        avaliacao = AvaliacaoDeRisco(
            id_execucao=id_execucao,
            id_paciente=id_paciente,
            id_usuario=id_usuario,
            origem_dos_dados=origem_dos_dados,
            status=status,
            modo=modo,
            agente_final=agente_final,
            versao_do_sdk=versao_do_sdk,
            duracao_segundos=duracao_segundos,
            probabilidade_risco=dados_do_diagnostico.get("probabilidade_risco"),
            pico_risco_previsto=dados_do_diagnostico.get("pico_risco_previsto"),
            classificacao_risco=_como_classificacao(
                dados_do_diagnostico.get("classificacao_risco")
            ),
            modelo_utilizado=dados_do_diagnostico.get("modelo_utilizado"),
            classe_do_estimador=dados_do_diagnostico.get("classe_do_estimador"),
            limiar_decisao=dados_do_diagnostico.get("limiar_decisao"),
            regra_de_decisao=dados_do_diagnostico.get("regra_de_decisao"),
            sha256_da_base_usada=origem_do_modelo.get("sha256_da_base_usada"),
            resposta_json=dict(resposta) if resposta is not None else None,
            features_json={**valores, "origem_dos_dados": origem_dos_dados.value},
            avisos_json=list(avisos) or None,
            erros_json=list(erros) or None,
            **valores,
        )
        if criado_em is not None:
            avaliacao.criado_em = criado_em

        avaliacao.protocolos = montar_filhos(ProtocoloAplicado, protocolos, "protocolos")
        avaliacao.indicadores = montar_filhos(
            IndicadorDeterministico, indicadores, "indicadores"
        )
        avaliacao.passos = montar_filhos(PassoDaExecucao, passos, "passos")

        self.sessao.add(avaliacao)
        self._confirmar()
        self.sessao.refresh(avaliacao)
        return avaliacao

    # ------------------------------------------------------------------ #
    # Leitura
    # ------------------------------------------------------------------ #

    def buscar_por_id_execucao(self, id_execucao: str) -> AvaliacaoDeRisco | None:
        """Busca pela chave de correlacao com a Fase 6."""
        return self.sessao.scalar(
            select(AvaliacaoDeRisco).where(AvaliacaoDeRisco.id_execucao == id_execucao)
        )

    def buscar_por_id(self, id_avaliacao: str) -> AvaliacaoDeRisco | None:
        """Busca pela chave primaria interna."""
        return self.sessao.get(AvaliacaoDeRisco, id_avaliacao)

    def listar_por_paciente(
        self, id_paciente: str, *, limite: int = 50, deslocamento: int = 0
    ) -> list[AvaliacaoDeRisco]:
        """Historico do paciente (mais recentes primeiro)."""
        consulta = (
            select(AvaliacaoDeRisco)
            .where(AvaliacaoDeRisco.id_paciente == id_paciente)
            .order_by(AvaliacaoDeRisco.criado_em.desc())
            .limit(limite)
            .offset(deslocamento)
        )
        return list(self.sessao.scalars(consulta))

    def listar(
        self,
        *,
        status: StatusDaResposta | None = None,
        id_paciente: str | None = None,
        limite: int = 50,
        deslocamento: int = 0,
    ) -> list[AvaliacaoDeRisco]:
        """Lista avaliacoes (mais recentes primeiro), com filtros opcionais.

        Args:
            status: filtra pelo status do envelope.
            id_paciente: filtra pelo paciente (historico). Os dois filtros **combinam** —
                nao sao mutuamente exclusivos, para que a API nao precise recusar um deles.
        """
        consulta = select(AvaliacaoDeRisco)
        if status is not None:
            consulta = consulta.where(AvaliacaoDeRisco.status == status)
        if id_paciente is not None:
            consulta = consulta.where(AvaliacaoDeRisco.id_paciente == id_paciente)
        consulta = (
            consulta.order_by(AvaliacaoDeRisco.criado_em.desc())
            .limit(limite)
            .offset(deslocamento)
        )
        return list(self.sessao.scalars(consulta))
