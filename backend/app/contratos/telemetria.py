"""Contratos de telemetria IoT (``CONTRATOS_API.md`` §4.2).

Dois cuidados de tipagem, pelo mesmo motivo que em ``assistencial.py``: o pydantic
converte ``true`` em ``1``/``1.0`` **silenciosamente**. Como ``temperatura`` e ``bpm``
alimentam as regras de risco, aceitar um booleano como sinal vital seria aceitar um valor
que ninguem mediu — por isso os campos numericos rejeitam ``bool`` explicitamente.

**Nao exposto de proposito:** a coluna ``monitoramentos.id_paciente`` existe no banco
(vinculacao **opcional**, ``MODELO_DADOS.md`` §4.5) mas o contrato §4.2 nao a lista.
Como o DTO e fechado (``extra="forbid"``), aceita-la aqui seria divergir do contrato
aprovado; a vinculacao fica registrada como gancho futuro.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from ..dados.enums import OrigemDoTransporte

__all__ = ["LeituraDeMonitoramento", "PedidoDeLeitura"]

#: Tamanho maximo do identificador de dispositivo (mesmo limite da coluna).
TAMANHO_MAXIMO_DO_ID_DISPOSITIVO = 64


class _ContratoFechado(BaseModel):
    """Base dos DTOs: proibe campos desconhecidos (postura do projeto)."""

    model_config = ConfigDict(extra="forbid")


class PedidoDeLeitura(_ContratoFechado):
    """Leitura de telemetria enviada por um dispositivo ou por um operador.

    Pelo menos **um sinal vital** (``temperatura`` ou ``bpm``) e obrigatorio — a mesma
    regra existe no banco (``CHECK``) e no repositorio; aqui ela falha antes, com o campo
    identificado.
    """

    id_dispositivo: str = Field(
        min_length=1,
        max_length=TAMANHO_MAXIMO_DO_ID_DISPOSITIVO,
        description="O firmware nao envia identificador — o campo e obrigatorio na API.",
    )
    origem_transporte: OrigemDoTransporte = Field(
        description="Como a leitura chegou: 'mqtt', 'rest' ou 'simulado'."
    )
    temperatura: float | None = Field(
        default=None, description="Temperatura corporal em graus Celsius."
    )
    bpm: int | None = Field(default=None, description="Frequencia cardiaca (batimentos/min).")
    umidade: float | None = Field(default=None, description="Nao e feature do modelo.")
    luminosidade: float | None = Field(default=None, description="Nao e feature do modelo.")
    movimento: bool | None = Field(
        default=None, description="Existe apenas no payload REST da Fase 3."
    )
    payload_json: dict[str, Any] | None = Field(
        default=None, description="Payload bruto, para auditoria."
    )

    @field_validator("temperatura", "bpm", "umidade", "luminosidade", mode="before")
    @classmethod
    def _rejeita_booleano(cls, valor: Any, info: ValidationInfo) -> Any:
        """Impede que ``true`` vire ``1``/``1.0`` em um sinal vital."""
        if isinstance(valor, bool):
            raise ValueError(
                f"'{info.field_name}' deve ser numerico; recebido booleano "
                "(o pydantic converteria silenciosamente em 1)."
            )
        return valor

    @field_validator("id_dispositivo")
    @classmethod
    def _normaliza_id_dispositivo(cls, valor: str) -> str:
        """Remove espacos e recusa identificador vazio."""
        limpo = valor.strip()
        if not limpo:
            raise ValueError("'id_dispositivo' nao pode ser vazio ou apenas espacos.")
        return limpo

    @model_validator(mode="after")
    def _exige_ao_menos_um_sinal_vital(self) -> PedidoDeLeitura:
        if self.temperatura is None and self.bpm is None:
            raise ValueError(
                "Informe ao menos um sinal vital: 'temperatura' ou 'bpm'."
            )
        return self


class LeituraDeMonitoramento(_ContratoFechado):
    """Leitura persistida, como devolvida pela API (``CONTRATOS_API.md`` §4.2).

    O **alerta** das regras da Fase 3 nao esta aqui de proposito: ele e **derivado** dos
    sinais e nao existe coluna para ele. Na ingestao ele vai em ``avisos`` do envelope (e
    a trilha de auditoria registra o evento); quem consome o historico pode recomputa-lo
    com :func:`app.regras_iot.avaliar_sinais`.
    """

    id_leitura: str = Field(min_length=8)
    id_dispositivo: str = Field(min_length=1, max_length=TAMANHO_MAXIMO_DO_ID_DISPOSITIVO)
    recebido_em: datetime = Field(
        description="Carimbado pelo backend — o firmware nao envia timestamp."
    )
    origem_transporte: OrigemDoTransporte
    temperatura: float | None = None
    bpm: int | None = None
    umidade: float | None = None
    luminosidade: float | None = None
    movimento: bool | None = None
    payload_json: dict[str, Any] | None = None
