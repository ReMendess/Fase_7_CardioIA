"""Enums persistidos no banco.

Decisao de modelagem (``MODELO_DADOS.md`` §9, C6): **TEXT + CHECK** — legivel no
banco e portavel entre SQLite e PostgreSQL. Implementado com
``sqlalchemy.Enum(native_enum=False, create_constraint=True)`` via
:func:`app.dados.base.enum_coluna`.

**Sobre a relacao com a Fase 6:** alguns destes enums existem tambem no material da
Fase 6 (``cardioia.schemas.risk_result``). Eles foram **redeclarados aqui** de
proposito, para que a camada de dados do backend nao dependa do pacote da Fase 6
(isso entra no item 4 da Etapa C). A **equivalencia dos valores** sera verificada
por teste no item 4 — nao ha compatibilidade presumida.

Valores que vieram da Fase 5 (contrato de erro) **nao** sao redeclarados: os codigos
de erro vivem em :mod:`app.contratos.erros`, que e a fonte unica.
"""

from __future__ import annotations

from enum import Enum

__all__ = [
    "CanalDaConversa",
    "ClasseDeDiagnosticoDeImagem",
    "ClassificacaoDeRisco",
    "ModoDoPipeline",
    "OperadorDeComparacao",
    "OrigemDoTransporte",
    "OrigemDosDados",
    "PapelDaMensagem",
    "PapelDoUsuario",
    "TipoDePasso",
]


class PapelDoUsuario(str, Enum):
    """Papeis do RBAC (``MODELO_DADOS.md`` §6.3)."""

    ADMIN = "ADMIN"
    MEDICO = "MEDICO"
    OPERADOR = "OPERADOR"


class ModoDoPipeline(str, Enum):
    """Modo de execucao do pipeline multiagente (Fase 6)."""

    SIMULADO = "simulado"
    REAL = "real"


class OrigemDosDados(str, Enum):
    """Procedencia das 10 features de uma avaliacao (Decisao D4)."""

    MANUAL = "manual"
    IOT = "iot"
    IMPORTADO = "importado"


class ClassificacaoDeRisco(str, Enum):
    """Rotulo textual coerente com ``pico_risco_previsto`` (0/1)."""

    SEM_PICO_DE_RISCO = "sem_pico_de_risco"
    PICO_DE_RISCO = "pico_de_risco"


class OperadorDeComparacao(str, Enum):
    """Operadores estritos das 10 regras de protocolo (Fase 6)."""

    MENOR = "<"
    MAIOR = ">"
    IGUAL = "=="


class TipoDePasso(str, Enum):
    """Natureza de cada passo da trilha de execucao (Fase 6)."""

    HANDOFF = "handoff"
    TOOL = "tool"
    AGENTE = "agente"
    VALIDACAO = "validacao"
    ERRO = "erro"


class OrigemDoTransporte(str, Enum):
    """Como a telemetria chegou ao backend (Fase 3)."""

    MQTT = "mqtt"
    REST = "rest"
    SIMULADO = "simulado"


class CanalDaConversa(str, Enum):
    """Canal de origem da conversa com o assistente (Fase 5)."""

    WEB = "web"
    MOBILE = "mobile"


class PapelDaMensagem(str, Enum):
    """Autor de cada mensagem da conversa."""

    USUARIO = "user"
    ASSISTENTE = "assistant"


class ClasseDeDiagnosticoDeImagem(str, Enum):
    """Saida binaria do modelo de visao computacional da Fase 4.

    Os valores sao **exatamente** os que a Fase 4 devolve no campo ``class``
    (``"Normal"``/``"Pneumonia"``) — preservados para nao introduzir traducao
    silenciosa na borda.
    """

    NORMAL = "Normal"
    PNEUMONIA = "Pneumonia"
