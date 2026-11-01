"""Tabelas do backend CardioIA (Fase 7) — implementa ``MODELO_DADOS.md`` §3.

Convencoes aplicadas (``MODELO_DADOS.md`` §9):

- **C1/C2**: o acesso passa por repositorios; aqui ha apenas o mapeamento.
- **C3**: toda data usa :class:`~app.dados.base.DatetimeUTC` (sempre UTC).
- **C6**: enums como TEXT + CHECK via :func:`~app.dados.base.enum_coluna`.
- **C7**: as 10 features sao ``NOT NULL`` **sem default** — ausencia e erro, nao
  valor implicito.
- FKs com a regra de exclusao declarada (``RESTRICT``/``CASCADE``/``SET NULL``)
  conforme a tabela de integridade do modelo.

A tabela ``versoes_do_esquema`` e **de controle tecnico** (nao pertence ao dominio):
registra qual versao do esquema esta aplicada, ja que ``alembic`` nao esta instalado.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..contratos.envelope import StatusDaResposta
from .base import Base, DatetimeUTC, agora_utc, enum_coluna, novo_identificador
from .enums import (
    CanalDaConversa,
    ClasseDeDiagnosticoDeImagem,
    ClassificacaoDeRisco,
    ModoDoPipeline,
    OperadorDeComparacao,
    OrigemDoTransporte,
    OrigemDosDados,
    PapelDaMensagem,
    PapelDoUsuario,
    TipoDePasso,
)

__all__ = [
    "COLUNAS_DE_FEATURE",
    "AnaliseDeImagem",
    "AvaliacaoDeRisco",
    "Conversa",
    "EventoDeAuditoria",
    "IndicadorDeterministico",
    "Mensagem",
    "Monitoramento",
    "Paciente",
    "PassoDaExecucao",
    "ProtocoloAplicado",
    "Sessao",
    "Usuario",
    "VersaoDoEsquema",
]

#: As 10 features do modelo de risco da Fase 6 — nomes **fixados pelo contrato**.
#: Ordem identica a ``metadata.features`` / ``COLUNAS_PREDITORAS``.
COLUNAS_DE_FEATURE: tuple[str, ...] = (
    "idade_media",
    "carga_sistema",
    "tempo_espera",
    "fc_media",
    "spo2_media",
    "pa_sistolica",
    "temperatura",
    "densidade_eventos",
    "eventos_24h",
    "disponibilidade_recursos",
)


# --------------------------------------------------------------------------- #
# 3.1 usuarios
# --------------------------------------------------------------------------- #


class Usuario(Base):
    """Conta de acesso ao sistema (RBAC)."""

    __tablename__ = "usuarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_identificador)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    papel: Mapped[PapelDoUsuario] = mapped_column(
        enum_coluna(PapelDoUsuario, "papel_do_usuario"), nullable=False
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DatetimeUTC, nullable=False, default=agora_utc
    )
    ultimo_acesso: Mapped[datetime | None] = mapped_column(DatetimeUTC, nullable=True)

    sessoes: Mapped[list[Sessao]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - conveniencia de depuracao
        return f"Usuario(id={self.id!r}, email={self.email!r}, papel={self.papel.value!r})"


# --------------------------------------------------------------------------- #
# 3.2 sessoes (refresh tokens)
# --------------------------------------------------------------------------- #


class Sessao(Base):
    """Refresh token de uma sessao. Guarda apenas o **hash** do token."""

    __tablename__ = "sessoes"
    __table_args__ = (Index("ix_sessoes_usuario_expira", "id_usuario", "expira_em"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_identificador)
    id_usuario: Mapped[str] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    criado_em: Mapped[datetime] = mapped_column(
        DatetimeUTC, nullable=False, default=agora_utc
    )
    expira_em: Mapped[datetime] = mapped_column(DatetimeUTC, nullable=False)
    revogado_em: Mapped[datetime | None] = mapped_column(DatetimeUTC, nullable=True)

    usuario: Mapped[Usuario] = relationship(back_populates="sessoes")

    @property
    def vigente(self) -> bool:
        """``True`` quando a sessao nao foi revogada nem expirou."""
        return self.revogado_em is None and self.expira_em > agora_utc()

    def __repr__(self) -> str:  # pragma: no cover - conveniencia de depuracao
        return f"Sessao(id={self.id!r}, id_usuario={self.id_usuario!r})"


# --------------------------------------------------------------------------- #
# 3.3 pacientes (identidade)
# --------------------------------------------------------------------------- #


class Paciente(Base):
    """Paciente — **apenas identidade** (resposta Q1: risco clinico individual).

    As 10 features **nao** ficam aqui: elas representam o estado clinico **no momento
    da avaliacao** e vivem em :class:`AvaliacaoDeRisco`.
    """

    __tablename__ = "pacientes"
    __table_args__ = (Index("ix_pacientes_criado_em", "criado_em"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_identificador)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DatetimeUTC, nullable=False, default=agora_utc
    )
    criado_por: Mapped[str] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )

    avaliacoes: Mapped[list[AvaliacaoDeRisco]] = relationship(
        back_populates="paciente", cascade="all, delete-orphan"
    )
    monitoramentos: Mapped[list[Monitoramento]] = relationship(back_populates="paciente")

    def __repr__(self) -> str:  # pragma: no cover - conveniencia de depuracao
        return f"Paciente(id={self.id!r}, nome={self.nome!r})"


# --------------------------------------------------------------------------- #
# 3.4 avaliacoes_de_risco (agregado central)
# --------------------------------------------------------------------------- #

_RESTRICOES_DE_FEATURE = tuple(
    CheckConstraint(f"{coluna} >= 0", name=f"ck_avaliacoes_{coluna}_nao_negativa")
    for coluna in COLUNAS_DE_FEATURE
)


class AvaliacaoDeRisco(Base):
    """Agregado central: estado clinico avaliado + resultado do pipeline da Fase 6.

    Concentra as **10 features** (estado do paciente no momento da avaliacao) e o
    resultado decomposto do ``RespostaDaExecucao``. O contrato original completo
    tambem e preservado em ``resposta_json``, para auditoria.
    """

    __tablename__ = "avaliacoes_de_risco"
    __table_args__ = (
        *_RESTRICOES_DE_FEATURE,
        CheckConstraint(
            "pico_risco_previsto IS NULL OR pico_risco_previsto IN (0, 1)",
            name="ck_avaliacoes_pico_risco_binario",
        ),
        Index("ix_avaliacoes_paciente_criado", "id_paciente", "criado_em"),
        Index("ix_avaliacoes_status", "status"),
        Index("ix_avaliacoes_criado_em", "criado_em"),
    )

    # --- identificacao --------------------------------------------------- #
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_identificador)
    #: UUID gerado pela Fase 6 — chave de correlacao com a trilha de execucao.
    id_execucao: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    id_paciente: Mapped[str] = mapped_column(
        ForeignKey("pacientes.id", ondelete="RESTRICT"), nullable=False
    )
    id_usuario: Mapped[str] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    criado_em: Mapped[datetime] = mapped_column(
        DatetimeUTC, nullable=False, default=agora_utc
    )

    # --- as 10 features (NOT NULL, sem default — regra C7) --------------- #
    idade_media: Mapped[float] = mapped_column(Float, nullable=False)
    carga_sistema: Mapped[float] = mapped_column(Float, nullable=False)
    tempo_espera: Mapped[float] = mapped_column(Float, nullable=False)
    fc_media: Mapped[float] = mapped_column(Float, nullable=False)
    spo2_media: Mapped[float] = mapped_column(Float, nullable=False)
    pa_sistolica: Mapped[float] = mapped_column(Float, nullable=False)
    temperatura: Mapped[float] = mapped_column(Float, nullable=False)
    densidade_eventos: Mapped[float] = mapped_column(Float, nullable=False)
    eventos_24h: Mapped[float] = mapped_column(Float, nullable=False)
    disponibilidade_recursos: Mapped[float] = mapped_column(Float, nullable=False)
    origem_dos_dados: Mapped[OrigemDosDados] = mapped_column(
        enum_coluna(OrigemDosDados, "origem_dos_dados"), nullable=False
    )

    # --- resultado da execucao ------------------------------------------- #
    #: Reutiliza o enum do envelope — fonte unica dos 4 estados (Fase 6).
    status: Mapped[StatusDaResposta] = mapped_column(
        enum_coluna(StatusDaResposta, "status_da_resposta"), nullable=False
    )
    modo: Mapped[ModoDoPipeline] = mapped_column(
        enum_coluna(ModoDoPipeline, "modo_do_pipeline"), nullable=False
    )
    agente_final: Mapped[str | None] = mapped_column(String(80), nullable=True)
    versao_do_sdk: Mapped[str | None] = mapped_column(String(40), nullable=True)
    duracao_segundos: Mapped[float | None] = mapped_column(Float, nullable=True)
    probabilidade_risco: Mapped[float | None] = mapped_column(Float, nullable=True)
    pico_risco_previsto: Mapped[int | None] = mapped_column(Integer, nullable=True)
    classificacao_risco: Mapped[ClassificacaoDeRisco | None] = mapped_column(
        enum_coluna(ClassificacaoDeRisco, "classificacao_de_risco"), nullable=True
    )
    modelo_utilizado: Mapped[str | None] = mapped_column(String(80), nullable=True)
    classe_do_estimador: Mapped[str | None] = mapped_column(String(80), nullable=True)
    limiar_decisao: Mapped[float | None] = mapped_column(Float, nullable=True)
    regra_de_decisao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sha256_da_base_usada: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # --- contrato integral (auditoria) ----------------------------------- #
    resposta_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    features_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    avisos_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    erros_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # --- relacionamentos -------------------------------------------------- #
    paciente: Mapped[Paciente] = relationship(back_populates="avaliacoes")
    protocolos: Mapped[list[ProtocoloAplicado]] = relationship(
        back_populates="avaliacao", cascade="all, delete-orphan"
    )
    indicadores: Mapped[list[IndicadorDeterministico]] = relationship(
        back_populates="avaliacao", cascade="all, delete-orphan"
    )
    passos: Mapped[list[PassoDaExecucao]] = relationship(
        back_populates="avaliacao", cascade="all, delete-orphan"
    )

    @property
    def features(self) -> dict[str, float]:
        """As 10 features na ordem do contrato do modelo."""
        return {coluna: float(getattr(self, coluna)) for coluna in COLUNAS_DE_FEATURE}

    def __repr__(self) -> str:  # pragma: no cover - conveniencia de depuracao
        return f"AvaliacaoDeRisco(id_execucao={self.id_execucao!r}, status={self.status!r})"


# --------------------------------------------------------------------------- #
# 3.5 protocolos_aplicados
# --------------------------------------------------------------------------- #


class ProtocoloAplicado(Base):
    """Protocolo oficial acionado + justificativa objetiva (1:1 ``ProtocoloAplicavel``)."""

    __tablename__ = "protocolos_aplicados"
    __table_args__ = (
        UniqueConstraint(
            "id_avaliacao", "identificador", name="uq_protocolos_avaliacao_identificador"
        ),
        CheckConstraint("ordem >= 1 AND ordem <= 10", name="ck_protocolos_ordem_entre_1_e_10"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_identificador)
    id_avaliacao: Mapped[str] = mapped_column(
        ForeignKey("avaliacoes_de_risco.id", ondelete="CASCADE"), nullable=False
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    identificador: Mapped[str] = mapped_column(String(80), nullable=False)
    texto_oficial: Mapped[str] = mapped_column(Text, nullable=False)
    acao: Mapped[str] = mapped_column(Text, nullable=False)
    condicao_satisfeita: Mapped[str] = mapped_column(String(120), nullable=False)
    operador: Mapped[OperadorDeComparacao] = mapped_column(
        enum_coluna(OperadorDeComparacao, "operador_de_comparacao"), nullable=False
    )
    limiar: Mapped[float] = mapped_column(Float, nullable=False)
    valor_observado: Mapped[float] = mapped_column(Float, nullable=False)
    origem_do_valor: Mapped[str] = mapped_column(String(40), nullable=False)
    usa_modelo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    avaliacao: Mapped[AvaliacaoDeRisco] = relationship(back_populates="protocolos")


# --------------------------------------------------------------------------- #
# 3.6 indicadores_deterministicos
# --------------------------------------------------------------------------- #


class IndicadorDeterministico(Base):
    """Indicador calculado em Python (nunca pelo LLM)."""

    __tablename__ = "indicadores_deterministicos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_identificador)
    id_avaliacao: Mapped[str] = mapped_column(
        ForeignKey("avaliacoes_de_risco.id", ondelete="CASCADE"), nullable=False
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    coluna: Mapped[str | None] = mapped_column(String(60), nullable=True)
    operador: Mapped[OperadorDeComparacao] = mapped_column(
        enum_coluna(OperadorDeComparacao, "operador_de_comparacao"), nullable=False
    )
    limiar: Mapped[float] = mapped_column(Float, nullable=False)
    valor_observado: Mapped[float] = mapped_column(Float, nullable=False)
    satisfeito: Mapped[bool] = mapped_column(Boolean, nullable=False)
    origem: Mapped[str] = mapped_column(String(40), nullable=False)

    avaliacao: Mapped[AvaliacaoDeRisco] = relationship(back_populates="indicadores")


# --------------------------------------------------------------------------- #
# 3.7 passos_da_execucao
# --------------------------------------------------------------------------- #


class PassoDaExecucao(Base):
    """Trilha auditavel da execucao (handoff, tool, agente, validacao, erro)."""

    __tablename__ = "passos_da_execucao"
    __table_args__ = (
        UniqueConstraint("id_avaliacao", "ordem", name="uq_passos_avaliacao_ordem"),
        CheckConstraint("ordem >= 1", name="ck_passos_ordem_positiva"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_identificador)
    id_avaliacao: Mapped[str] = mapped_column(
        ForeignKey("avaliacoes_de_risco.id", ondelete="CASCADE"), nullable=False
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[TipoDePasso] = mapped_column(
        enum_coluna(TipoDePasso, "tipo_de_passo"), nullable=False
    )
    agente: Mapped[str] = mapped_column(String(80), nullable=False)
    detalhe: Mapped[str] = mapped_column(Text, nullable=False)
    sucesso: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    avaliacao: Mapped[AvaliacaoDeRisco] = relationship(back_populates="passos")


# --------------------------------------------------------------------------- #
# 3.8 monitoramentos (telemetria IoT)
# --------------------------------------------------------------------------- #


class Monitoramento(Base):
    """Leitura de telemetria da Fase 3.

    **Nao alimenta o modelo preditivo** no MVP (Decisao D4): fica persistida para
    visualizacao e para uso futuro. O binario/timestamp de origem nao existe no
    firmware — ``recebido_em`` e **carimbado pelo backend**.
    """

    __tablename__ = "monitoramentos"
    __table_args__ = (
        CheckConstraint(
            "temperatura IS NOT NULL OR bpm IS NOT NULL",
            name="ck_monitoramentos_ao_menos_um_sinal",
        ),
        UniqueConstraint("id_dispositivo", "recebido_em", name="uq_monitoramentos_dispositivo_em"),
        Index("ix_monitoramentos_dispositivo_recebido", "id_dispositivo", "recebido_em"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_identificador)
    id_paciente: Mapped[str | None] = mapped_column(
        ForeignKey("pacientes.id", ondelete="SET NULL"), nullable=True
    )
    id_dispositivo: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recebido_em: Mapped[datetime] = mapped_column(
        DatetimeUTC, nullable=False, default=agora_utc, index=True
    )
    temperatura: Mapped[float | None] = mapped_column(Float, nullable=True)
    umidade: Mapped[float | None] = mapped_column(Float, nullable=True)
    luminosidade: Mapped[float | None] = mapped_column(Float, nullable=True)
    bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    movimento: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    origem_transporte: Mapped[OrigemDoTransporte] = mapped_column(
        enum_coluna(OrigemDoTransporte, "origem_do_transporte"), nullable=False
    )
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    paciente: Mapped[Paciente | None] = relationship(back_populates="monitoramentos")


# --------------------------------------------------------------------------- #
# 3.9 analises_de_imagem
# --------------------------------------------------------------------------- #


class AnaliseDeImagem(Base):
    """Analise de radiografia pelo servico de visao da Fase 4.

    🔒 **Privacidade:** o binario da imagem **nao** e armazenado — apenas o
    ``hash_sha256`` (deteccao de reenvio) e os metadados (``MODELO_DADOS.md`` §3.9).
    """

    __tablename__ = "analises_de_imagem"
    __table_args__ = (
        Index("ix_analises_paciente_criado", "id_paciente", "criado_em"),
        Index("ix_analises_hash", "hash_sha256"),
        CheckConstraint("tamanho_bytes > 0", name="ck_analises_tamanho_positivo"),
        CheckConstraint(
            "confianca >= 0 AND confianca <= 100", name="ck_analises_confianca_0_100"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_identificador)
    id_paciente: Mapped[str | None] = mapped_column(
        ForeignKey("pacientes.id", ondelete="SET NULL"), nullable=True
    )
    id_usuario: Mapped[str] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    criado_em: Mapped[datetime] = mapped_column(
        DatetimeUTC, nullable=False, default=agora_utc, index=True
    )
    nome_arquivo: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    classe: Mapped[ClasseDeDiagnosticoDeImagem] = mapped_column(
        enum_coluna(ClasseDeDiagnosticoDeImagem, "classe_de_diagnostico"), nullable=False
    )
    confianca: Mapped[float] = mapped_column(Float, nullable=False)
    modelo_utilizado: Mapped[str] = mapped_column(String(120), nullable=False)
    limiar_decisao: Mapped[float] = mapped_column(Float, nullable=False)
    resposta_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)


# --------------------------------------------------------------------------- #
# 3.10 conversas e mensagens
# --------------------------------------------------------------------------- #


class Conversa(Base):
    """Sessao de conversa com o assistente (Fase 5)."""

    __tablename__ = "conversas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_identificador)
    id_usuario: Mapped[str] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    id_paciente: Mapped[str | None] = mapped_column(
        ForeignKey("pacientes.id", ondelete="SET NULL"), nullable=True
    )
    canal: Mapped[CanalDaConversa] = mapped_column(
        enum_coluna(CanalDaConversa, "canal_da_conversa"), nullable=False
    )
    iniciada_em: Mapped[datetime] = mapped_column(
        DatetimeUTC, nullable=False, default=agora_utc
    )
    encerrada_em: Mapped[datetime | None] = mapped_column(DatetimeUTC, nullable=True)

    mensagens: Mapped[list[Mensagem]] = relationship(
        back_populates="conversa", cascade="all, delete-orphan"
    )


class Mensagem(Base):
    """Turno de uma conversa.

    🔒 ``session_id_do_provedor`` e **interno** (continuidade no Watson) e **nunca**
    e devolvido ao cliente (``CONTRATOS_API.md`` §4.5, R6).
    """

    __tablename__ = "mensagens"
    __table_args__ = (Index("ix_mensagens_conversa_criado", "id_conversa", "criado_em"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_identificador)
    id_conversa: Mapped[str] = mapped_column(
        ForeignKey("conversas.id", ondelete="CASCADE"), nullable=False
    )
    papel: Mapped[PapelDaMensagem] = mapped_column(
        enum_coluna(PapelDaMensagem, "papel_da_mensagem"), nullable=False
    )
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DatetimeUTC, nullable=False, default=agora_utc
    )
    session_id_do_provedor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)

    conversa: Mapped[Conversa] = relationship(back_populates="mensagens")


# --------------------------------------------------------------------------- #
# 3.11 eventos_de_auditoria
# --------------------------------------------------------------------------- #


class EventoDeAuditoria(Base):
    """Registro de auditoria.

    🔒 ``detalhe_json`` **nao** pode conter payload clinico nem token
    (``PLANO_SEGURANCA.md`` §7.2).
    """

    __tablename__ = "eventos_de_auditoria"
    __table_args__ = (
        Index("ix_eventos_criado_em", "criado_em"),
        Index("ix_eventos_acao", "acao"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_identificador)
    id_usuario: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    acao: Mapped[str] = mapped_column(String(60), nullable=False)
    entidade: Mapped[str] = mapped_column(String(60), nullable=False)
    id_entidade: Mapped[str | None] = mapped_column(String(36), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DatetimeUTC, nullable=False, default=agora_utc
    )
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    detalhe_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


# --------------------------------------------------------------------------- #
# Controle tecnico do esquema
# --------------------------------------------------------------------------- #


class VersaoDoEsquema(Base):
    """Versao do esquema aplicada (tabela de **controle tecnico**, nao de dominio).

    Existe porque ``alembic`` **nao esta instalado** neste ambiente: a estrategia
    aprovada e ``create_all()`` + **script de migracao versionado**
    (``MODELO_DADOS.md`` §7). Sem esta tabela nao haveria como saber qual versao
    esta aplicada no arquivo do banco.
    """

    __tablename__ = "versoes_do_esquema"

    versao: Mapped[int] = mapped_column(Integer, primary_key=True)
    descricao: Mapped[str] = mapped_column(String(200), nullable=False)
    aplicada_em: Mapped[datetime] = mapped_column(
        DatetimeUTC, nullable=False, default=agora_utc
    )
