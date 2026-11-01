"""Tipos, engine, sessao e dependencia de banco (``MODELO_DADOS.md`` §1, §9).

Decisoes desta camada:

- **sincrono**: SQLAlchemy 2.0 no modo classico sincrono. Os endpoints usam ``def``
  (FastAPI executa em threadpool). Justificativa: o MVP e single-node com SQLite e
  "worker unico" (``MODELO_DADOS.md`` §1); sincrono evita complexidade sem ganho.
- **PRAGMAs obrigatorias no SQLite**: ``foreign_keys=ON`` (sem isso as FKs declaradas
  sao ignoradas!) e ``journal_mode=WAL`` para leitura concorrente.
- **datas sempre em UTC**: o tipo :class:`DatetimeUTC` normaliza na escrita e devolve
  com timezone na leitura — o SQLite nao armazena timezone (regra C3 do modelo).
- **commit e responsabilidade do repositorio/servico** (regra C2), nunca do endpoint.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import TypeDecorator
from starlette.requests import Request

from ..contratos.erros import CodigoDeErro, ErroDaAPIException

__all__ = [
    "Base",
    "DatetimeUTC",
    "criar_engine",
    "criar_fabrica_de_sessoes",
    "enum_coluna",
    "get_sessao",
    "novo_identificador",
]


# --------------------------------------------------------------------------- #
# Primitivos
# --------------------------------------------------------------------------- #


def novo_identificador() -> str:
    """UUID4 em texto (mesmo primitivo de ``contratos.envelope.novo_id_execucao``)."""
    return str(uuid.uuid4())


def agora_utc() -> datetime:
    """Instante atual com timezone UTC (regra C3 do modelo de dados)."""
    return datetime.now(timezone.utc)


class DatetimeUTC(TypeDecorator[datetime]):
    """``DATETIME`` que **sempre** grava e devolve UTC com timezone.

    Por que existe: o SQLite nao tem tipo com timezone. Sem este decorador, um valor
    gravado como ``2026-10-31T12:00:00+00:00`` voltaria **naive** e qualquer comparacao
    com um datetime aware falharia. Aqui:

    - na **escrita**: exige timezone e converte para UTC (falha rapida em valor naive);
    - na **leitura**: anexa ``UTC`` quando o driver devolve naive.

    O comportamento e identico em SQLite e PostgreSQL, o que sustenta a migracao.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(  # noqa: D102 - contrato do TypeDecorator
        self, value: datetime | None, dialect: Any
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(
                "DatetimeUTC exige datetime com timezone (regra C3: datas sempre em UTC); "
                f"recebido {value!r}."
            )
        return value.astimezone(timezone.utc)

    def process_result_value(  # noqa: D102 - contrato do TypeDecorator
        self, value: datetime | None, dialect: Any
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def enum_coluna(enum_classe: type[Enum], nome: str) -> TypeEngine[Any]:
    """Coluna de enum como **TEXT + CHECK** (regra C6), gravando o ``value``.

    ``native_enum=False`` evita o tipo ENUM nativo (que o SQLite nao tem) e
    ``values_callable`` garante que o banco guarde o valor legivel (ex.: ``"manual"``)
    em vez do nome do membro (ex.: ``"MANUAL"``).
    """
    from sqlalchemy import Enum as EnumSQL

    return EnumSQL(
        enum_classe,
        name=nome,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda classe: [membro.value for membro in classe],
    )


# --------------------------------------------------------------------------- #
# Base declarativa
# --------------------------------------------------------------------------- #


class Base(DeclarativeBase):
    """Base declarativa do projeto."""


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #


def _registrar_pragmas(engine: Engine) -> None:
    """Aplica as PRAGMAs obrigatorias em **toda** conexao SQLite.

    Sem ``foreign_keys=ON`` o SQLite **ignora** as chaves estrangeiras declaradas —
    as regras ``ON DELETE RESTRICT/CASCADE/SET NULL`` deixariam de valer em silencio.
    """

    @event.listens_for(engine, "connect")
    def _configurar_conexao(dbapi_connection: Any, _registro: Any) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()


def criar_engine(url: str, *, para_testes: bool = False) -> Engine:
    """Cria o engine, aplicando as PRAGMAs quando o banco for SQLite.

    Args:
        url: URL do SQLAlchemy (ex.: ``sqlite:///./cardioia.db``).
        para_testes: quando ``True`` e o banco for em memoria, usa ``StaticPool``
            para que todas as conexoes compartilhem **o mesmo** banco — sem isso,
            cada conexao criaria um banco em memoria vazio e distinto.
    """
    argumentos: dict[str, Any] = {"echo": False}

    if url.startswith("sqlite"):
        argumentos["connect_args"] = {"check_same_thread": False}
        if para_testes or ":memory:" in url:
            argumentos["poolclass"] = StaticPool

    engine = create_engine(url, **argumentos)

    if url.startswith("sqlite"):
        _registrar_pragmas(engine)

    return engine


def criar_fabrica_de_sessoes(engine: Engine) -> sessionmaker[Session]:
    """Fabrica de sessoes.

    ``expire_on_commit=False`` mantem os objetos utilizaveis depois do ``commit``
    (o repositorio devolve a entidade recem-criada). ``autoflush=False`` evita
    consultas surpresa no meio de uma transacao.
    """
    return sessionmaker(
        bind=engine, class_=Session, expire_on_commit=False, autoflush=False
    )


# --------------------------------------------------------------------------- #
# Dependencia do FastAPI
# --------------------------------------------------------------------------- #


def get_sessao(request: Request) -> Iterator[Session]:
    """Dependencia que entrega uma sessao por requisicao.

    **Nao** faz ``commit``: por decisao de arquitetura (regra C2), quem confirma a
    transacao e o repositorio/servico. A sessao e sempre fechada ao final.

    Nota sobre o tipo: o parametro precisa ser anotado como :class:`Request` (do
    Starlette, o mesmo objeto que o FastAPI usa). Se for anotado como ``Any``, o
    FastAPI **nao** reconhece o objeto de requisicao e passa a exigir um parametro de
    query chamado ``request`` — o que quebraria toda rota que depende do banco.
    Starlette ja e dependencia obrigatoria do FastAPI, entao isto nao adiciona pacote.

    Raises:
        ErroDaAPIException: se a aplicacao nao tiver sido montada com banco
            (``ERRO_DE_CONFIGURACAO``).
    """
    fabrica: sessionmaker[Session] | None = getattr(
        request.app.state, "fabrica_de_sessoes", None
    )
    if fabrica is None:
        raise ErroDaAPIException(
            CodigoDeErro.ERRO_DE_CONFIGURACAO,
            "Banco de dados nao configurado na aplicacao.",
            detalhe="A aplicacao foi montada sem engine; verifique DATABASE_URL.",
        )

    sessao = fabrica()
    try:
        yield sessao
    finally:
        sessao.close()
