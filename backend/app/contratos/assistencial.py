"""Contratos do fluxo assistencial: pacientes e avaliacoes de risco (``CONTRATOS_API.md`` §8).

Decisao de tipagem importante: ``PedidoDeAvaliacao.features`` e ``dict[str, Any]``, **nao**
``dict[str, float]``. Motivo concreto e verificado: o pydantic converte ``true`` em ``1.0``
silenciosamente, e um booleano passaria como valor clinico. Tipar como ``float`` aqui
**contornaria** a rejeicao de booleano do mapeador (Decisao D4). A validacao de valor
continua com **uma unica autoridade**: :func:`app.integracao.mapeador.montar_caso_para_o_pipeline`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..dados.enums import ClassificacaoDeRisco, ModoDoPipeline, OrigemDosDados
from .envelope import StatusDaResposta

__all__ = [
    "PacientePublico",
    "PedidoDeAvaliacao",
    "PedidoDePaciente",
    "ResultadoDeAvaliacao",
    "ResumoDeAvaliacao",
]


class _ContratoFechado(BaseModel):
    """Base dos DTOs: proibe campos desconhecidos (postura do projeto)."""

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# Paciente
# --------------------------------------------------------------------------- #


class PedidoDePaciente(_ContratoFechado):
    """Dados para cadastrar um paciente.

    Nota (resposta Q1): o cadastro guarda **apenas identidade**. As 10 features do modelo
    sao estado clinico **datado** e vivem em cada avaliacao, nao aqui.
    """

    nome: str = Field(min_length=1, max_length=120)

    @field_validator("nome")
    @classmethod
    def _nome_nao_pode_ser_vazio(cls, valor: str) -> str:
        """Rejeita nome so de espacos e devolve a versao normalizada.

        Sem isso, ``"   "`` passaria no ``min_length=1`` e chegaria ao banco como string
        vazia — um paciente sem nome, impossivel de identificar na lista.
        """
        limpo = valor.strip()
        if not limpo:
            raise ValueError("'nome' nao pode ser vazio ou conter apenas espacos.")
        return limpo


class PacientePublico(_ContratoFechado):
    """Paciente exposto pela API (identidade, sem dado clinico)."""

    id_paciente: str = Field(min_length=8)
    nome: str = Field(min_length=1)
    ativo: bool
    criado_em: datetime
    criado_por: str = Field(min_length=8, description="Usuario que cadastrou.")


# --------------------------------------------------------------------------- #
# Avaliacao
# --------------------------------------------------------------------------- #


class PedidoDeAvaliacao(_ContratoFechado):
    """Pedido de avaliacao de risco de pico.

    As **10 features sao obrigatorias** e nenhum valor e preenchido por padrao: se
    ``id_paciente`` vier sem as features, a resposta e ``422 PACIENTE_INVALIDO``.
    """

    id_paciente: str = Field(min_length=8)
    features: dict[str, Any] = Field(
        description=(
            "As 10 features do modelo. Nomes exatamente como no contrato "
            "(ex.: 'disponibilidade_recursos'). A validacao de valor e do mapeador."
        )
    )
    origem_dos_dados: OrigemDosDados = Field(
        description="Procedencia das features: 'manual', 'iot' ou 'importado'."
    )
    modo: ModoDoPipeline = Field(
        default=ModoDoPipeline.SIMULADO,
        description="'simulado' (padrao, sem API) ou 'real' (exige OPENAI_API_KEY).",
    )


class ResumoDeAvaliacao(_ContratoFechado):
    """Item da listagem — sem a trilha completa (que fica em ``GET /avaliacoes/{id}``)."""

    id_execucao: str = Field(min_length=8)
    id_paciente: str = Field(min_length=8)
    status: StatusDaResposta
    modo: ModoDoPipeline
    origem_dos_dados: OrigemDosDados
    criado_em: datetime
    probabilidade_risco: float | None = None
    pico_risco_previsto: int | None = None
    classificacao_risco: ClassificacaoDeRisco | None = None
    modelo_utilizado: str | None = None


class ResultadoDeAvaliacao(_ContratoFechado):
    """Historico auditavel: metadados da execucao + contrato integral da Fase 6.

    O campo ``resposta`` e o ``resposta_json`` **persistido** — devolvido sem reexecutar o
    modelo, para que a decisao registrada seja exatamente a que foi tomada.
    """

    id_execucao: str = Field(min_length=8)
    id_paciente: str = Field(min_length=8)
    id_usuario: str = Field(min_length=8)
    status: StatusDaResposta
    modo: ModoDoPipeline
    origem_dos_dados: OrigemDosDados
    criado_em: datetime
    sha256_da_base_usada: str | None = Field(
        default=None, description="SHA-256 da base sintetica usada no treino do modelo."
    )
    resposta: dict[str, Any] = Field(
        description="RespostaDaExecucao persistido (contrato integral da Fase 6)."
    )
