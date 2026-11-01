"""Contratos de diagnostico por imagem (``CONTRATOS_API.md`` §4.3 e §4.6).

⚠️ **Este contrato NAO e o `DiagnosticoDaPredicao` da Fase 6** e nunca sera unificado com
ele (nota **I3**): nomes, semantica e granularidade sao diferentes. Aqui o resultado e um
diagnostico **binario por imagem** (`Normal`/`Pneumonia`) com confianca em **0-100**; na
Fase 6 e uma probabilidade de **pico de risco** em 0-1 com trilha de execucao.

Metade dos campos e **acrescentada pelo backend** (nota **N4**/**I9**): a Fase 4 devolve
apenas `class` e `confidence`. `modelo_utilizado`, `limiar_decisao` e `dimensoes_da_imagem`
vem do **conhecimento do artefato**, declarado em :mod:`app.integracao.fase_4` e verificado
por teste contra o arquivo-fonte da Fase 4.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..dados.enums import ClasseDeDiagnosticoDeImagem

__all__ = ["LIMITACOES_DA_VISAO", "MIMES_ACEITOS", "ResultadoDeDiagnostico"]

#: Tipos de imagem aceitos na borda (endurecimento pedido em ``CONTRATOS_API.md`` §4.6).
MIMES_ACEITOS: tuple[str, ...] = ("image/jpeg", "image/png")

#: Limitacoes declaradas em toda resposta de diagnostico por imagem.
#: O contrato §8.1 exige que ``limitacoes`` nunca fique vazio em resposta de decisao
#: automatizada — e um diagnostico por imagem e exatamente isso.
LIMITACOES_DA_VISAO: tuple[str, ...] = (
    "Classificador binario (Normal/Pneumonia) treinado em base publica ACADEMICA "
    "(Chest X-Ray Pneumonia), sem validacao clinica e sem calibracao de limiar. O limiar "
    "0.5 e operacional, nao clinico.",
    "O modelo responde apenas sobre pneumonia; ele NAO avalia outras condicoes e NAO "
    "substitui leitura radiologica profissional.",
    "🔒 A imagem NAO e persistida pelo backend: guardam-se apenas o hash SHA-256 (para "
    "deteccao de reenvio) e os metadados do upload.",
)


class ResultadoDeDiagnostico(BaseModel):
    """Resultado da analise de uma radiografia pelo servico da Fase 4."""

    model_config = ConfigDict(extra="forbid")

    classe: ClasseDeDiagnosticoDeImagem = Field(
        description="Os valores sao exatamente os que a Fase 4 devolve em 'class'."
    )
    confianca: float = Field(
        ge=0.0,
        le=100.0,
        description="Confianca em porcentagem — a Fase 4 ja devolve assim ('confidence').",
    )
    modelo_utilizado: str = Field(
        min_length=1,
        description="Acrescentado pelo backend: a Fase 4 nao informa o modelo (I9).",
    )
    limiar_decisao: float = Field(
        ge=0.0,
        le=1.0,
        description="Acrescentado pelo backend: 0.5 e literal no codigo da Fase 4 (I9).",
    )
    dimensoes_da_imagem: list[int] = Field(
        min_length=2,
        max_length=2,
        description="Acrescentado pelo backend: a Fase 4 redimensiona para (128, 128).",
    )
    hash_sha256: str = Field(
        min_length=64,
        max_length=64,
        description=(
            "Permite auditoria e deteccao de reenvio **sem** armazenar o binario "
            "(a imagem nao e persistida)."
        ),
    )
    aviso_de_uso: str = Field(min_length=1)
