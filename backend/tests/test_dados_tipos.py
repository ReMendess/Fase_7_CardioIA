"""Testes dos tipos e utilitarios da camada de dados (``app/dados/base.py``)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Integer, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.config import RAIZ_DO_BACKEND, Configuracoes
from app.contratos.erros import CodigoDeErro, ErroDaAPIException
from app.dados.base import (
    DatetimeUTC,
    agora_utc,
    criar_engine,
    criar_fabrica_de_sessoes,
    enum_coluna,
    get_sessao,
    novo_identificador,
)
from app.dados.enums import PapelDoUsuario
from app.dados.esquema import criar_esquema
from tests.conftest import SEGREDO_DE_TESTE, URL_DE_BANCO_DE_TESTE


class _BaseDeTeste(DeclarativeBase):
    """Base **exclusiva deste teste**.

    Por que nao usar ``app.dados.base.Base``: a tabela auxiliar ficaria registrada no
    metadata de producao e apareceria em qualquer ``create_all()`` — inclusive no
    esquema real. Isolar a base evita esse efeito colateral.
    """


class _Registro(_BaseDeTeste):
    """Tabela minima para exercitar o tipo ``DatetimeUTC``."""

    __tablename__ = "registros_de_teste"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quando: Mapped[datetime] = mapped_column(DatetimeUTC, nullable=False)
    opcional: Mapped[datetime | None] = mapped_column(DatetimeUTC, nullable=True)
    rotulo: Mapped[str] = mapped_column(String(20), nullable=False)


@pytest.fixture
def engine_com_registro(engine_de_teste):
    """Engine com a tabela auxiliar criada."""
    _BaseDeTeste.metadata.create_all(engine_de_teste)
    return engine_de_teste


# --------------------------------------------------------------------------- #
# DatetimeUTC
# --------------------------------------------------------------------------- #


def test_datetime_volta_com_timezone(engine_com_registro) -> None:
    """O SQLite nao guarda timezone; o tipo reanexa UTC na leitura."""
    fabrica = criar_fabrica_de_sessoes(engine_com_registro)
    momento = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)

    with fabrica() as sessao:
        sessao.add(_Registro(id=1, quando=momento, rotulo="teste"))
        sessao.commit()

    with fabrica() as sessao:
        lido = sessao.get(_Registro, 1)
        assert lido is not None
        assert lido.quando.tzinfo is not None
        assert lido.quando == momento


def test_datetime_converte_para_utc(engine_com_registro) -> None:
    """Um instante em outro fuso e normalizado para UTC."""
    fabrica = criar_fabrica_de_sessoes(engine_com_registro)
    fuso = timezone(timedelta(hours=-3))
    momento = datetime(2026, 10, 31, 9, 0, tzinfo=fuso)  # 12:00 UTC

    with fabrica() as sessao:
        sessao.add(_Registro(id=1, quando=momento, rotulo="fuso"))
        sessao.commit()

    with fabrica() as sessao:
        lido = sessao.get(_Registro, 1)
        assert lido is not None
        assert lido.quando == datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
        assert lido.quando.utcoffset() == timedelta(0)


def test_datetime_rejeita_valor_naive(engine_com_registro) -> None:
    """Regra C3: data sem timezone e erro, nao conversao silenciosa.

    O SQLAlchemy encapsula o ``ValueError`` do tipo em ``StatementError`` — a
    mensagem original e preservada.
    """
    from sqlalchemy.exc import StatementError

    fabrica = criar_fabrica_de_sessoes(engine_com_registro)

    with fabrica() as sessao:
        sessao.add(_Registro(id=1, quando=datetime(2026, 10, 31, 12, 0), rotulo="naive"))
        with pytest.raises(StatementError, match="exige datetime com timezone"):
            sessao.commit()


def test_datetime_aceita_nulo(engine_com_registro) -> None:
    fabrica = criar_fabrica_de_sessoes(engine_com_registro)

    with fabrica() as sessao:
        sessao.add(_Registro(id=1, quando=agora_utc(), opcional=None, rotulo="nulo"))
        sessao.commit()

    with fabrica() as sessao:
        lido = sessao.get(_Registro, 1)
        assert lido is not None
        assert lido.opcional is None


def test_agora_utc_tem_timezone() -> None:
    assert agora_utc().tzinfo is not None
    assert agora_utc().utcoffset() == timedelta(0)


def test_novo_identificador_e_uuid4_em_texto() -> None:
    identificador = novo_identificador()
    assert isinstance(identificador, str)
    assert uuid.UUID(identificador).version == 4


# --------------------------------------------------------------------------- #
# enum_coluna
# --------------------------------------------------------------------------- #


def test_enum_coluna_e_text_com_check() -> None:
    """Regra C6: TEXT + CHECK, gravando o ``value`` legivel."""
    coluna = enum_coluna(PapelDoUsuario, "papel_do_usuario")
    assert coluna.native_enum is False
    assert coluna.create_constraint is True
    assert coluna.enums == ["ADMIN", "MEDICO", "OPERADOR"]


def test_enum_coluna_rejeita_valor_fora_do_dominio(engine_de_teste) -> None:
    """O CHECK do enum impede valor invalido direto no banco."""
    from sqlalchemy.exc import IntegrityError

    criar_esquema(engine_de_teste)
    with engine_de_teste.connect() as conexao:
        with pytest.raises(IntegrityError):
            conexao.execute(
                text(
                    "INSERT INTO usuarios"
                    " (id, nome, email, senha_hash, papel, ativo, criado_em)"
                    " VALUES ('x', 'n', 'e@e', 'h', 'INVALIDO', 1, '2026-10-31 12:00:00')"
                )
            )


# --------------------------------------------------------------------------- #
# Engine, PRAGMAs e sessoes
# --------------------------------------------------------------------------- #


def test_criar_engine_em_memoria_compartilha_conexao() -> None:
    """Sem ``StaticPool`` cada conexao criaria um banco em memoria distinto."""
    engine = criar_engine(URL_DE_BANCO_DE_TESTE, para_testes=True)
    try:
        assert engine.pool.__class__.__name__ == "StaticPool"
    finally:
        engine.dispose()


def test_criar_engine_de_arquivo_nao_usa_static_pool(tmp_path) -> None:
    engine = criar_engine(f"sqlite+pysqlite:///{(tmp_path / 'x.db').as_posix()}")
    try:
        assert engine.pool.__class__.__name__ != "StaticPool"
    finally:
        engine.dispose()


def test_pragmas_de_foreign_keys_estao_ativas(engine_de_teste) -> None:
    """Sem ``foreign_keys=ON`` o SQLite ignoraria as FKs declaradas."""
    with engine_de_teste.connect() as conexao:
        assert conexao.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_get_sessao_falha_sem_banco_configurado() -> None:
    """A dependencia avisa em vez de estourar um erro obscuro."""

    class _Estado:
        pass

    class _AppFalsa:
        state = _Estado()

    class _RequestFalsa:
        app = _AppFalsa()

    gerador = get_sessao(_RequestFalsa())
    with pytest.raises(ErroDaAPIException) as capturado:
        next(gerador)
    assert capturado.value.codigo is CodigoDeErro.ERRO_DE_CONFIGURACAO


def test_sessao_e_fechada_pela_dependencia(engine_de_teste) -> None:
    """A dependencia sempre fecha a sessao ao final."""
    from fastapi import FastAPI, Request

    app = FastAPI()
    app.state.fabrica_de_sessoes = criar_fabrica_de_sessoes(engine_de_teste)

    request = Request({"type": "http", "app": app})
    gerador = get_sessao(request)
    sessao = next(gerador)
    assert isinstance(sessao, Session)
    assert sessao.is_active
    with pytest.raises(StopIteration):
        next(gerador)


# --------------------------------------------------------------------------- #
# Configuracao do banco
# --------------------------------------------------------------------------- #


def test_url_do_banco_resolve_caminho_relativo() -> None:
    """Caminho relativo passa a apontar para a raiz do backend, nao para o CWD."""
    config = Configuracoes(
        _env_file=None, jwt_secret=SEGREDO_DE_TESTE, database_url="sqlite:///./cardioia.db"
    )
    url = config.url_do_banco
    assert url.startswith("sqlite:///")
    assert (RAIZ_DO_BACKEND / "cardioia.db").as_posix() in url


def test_url_do_banco_preserva_memoria(tmp_path) -> None:
    config_memoria = Configuracoes(
        _env_file=None, jwt_secret=SEGREDO_DE_TESTE, database_url=URL_DE_BANCO_DE_TESTE
    )
    assert config_memoria.url_do_banco == URL_DE_BANCO_DE_TESTE


def test_url_do_banco_preserva_caminho_absoluto(tmp_path) -> None:
    """Caminho absoluto do sistema nao e reescrito.

    Nota: usa-se um caminho absoluto **da plataforma** (``tmp_path``). Um caminho
    no estilo POSIX (``/tmp/x``) nao e absoluto no Windows e, por isso, cai na
    resolucao relativa — mesmo comportamento que o proprio SQLite teria.
    """
    caminho = (tmp_path / "outro.db").as_posix()
    url = f"sqlite:///{caminho}"
    config = Configuracoes(_env_file=None, jwt_secret=SEGREDO_DE_TESTE, database_url=url)
    assert config.url_do_banco == url


def test_url_do_banco_preserva_urls_nao_sqlite() -> None:
    url = "postgresql+psycopg://usuario:senha@localhost/cardioia"
    config = Configuracoes(_env_file=None, jwt_secret=SEGREDO_DE_TESTE, database_url=url)
    assert config.url_do_banco == url
