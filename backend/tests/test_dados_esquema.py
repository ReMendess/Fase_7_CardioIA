"""Testes da criacao e do versionamento do esquema (``app/dados/esquema.py``)."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text

from app.dados.base import criar_engine
from app.dados.esquema import (
    HISTORICO,
    VERSAO_ATUAL,
    EsquemaIncompativelError,
    criar_esquema,
    main,
    preparar_banco,
    recriar_esquema,
    versao_registrada,
)
from app.dados.modelos import VersaoDoEsquema
from tests.conftest import URL_DE_BANCO_DE_TESTE

#: Tabelas de dominio do ``MODELO_DADOS.md`` §3.
TABELAS_DE_DOMINIO = (
    "usuarios",
    "sessoes",
    "pacientes",
    "avaliacoes_de_risco",
    "protocolos_aplicados",
    "indicadores_deterministicos",
    "passos_da_execucao",
    "monitoramentos",
    "analises_de_imagem",
    "conversas",
    "mensagens",
    "eventos_de_auditoria",
)

TABELA_DE_CONTROLE = "versoes_do_esquema"


def test_criar_esquema_cria_as_tabelas_de_dominio(engine_de_teste) -> None:
    nomes = set(inspect(engine_de_teste).get_table_names())
    assert set(TABELAS_DE_DOMINIO) <= nomes


def test_criar_esquema_cria_a_tabela_de_controle(engine_de_teste) -> None:
    assert TABELA_DE_CONTROLE in inspect(engine_de_teste).get_table_names()


def test_banco_novo_nao_tem_versao_registrada() -> None:
    """Antes de criar, a tabela de controle nem existe."""
    engine = criar_engine(URL_DE_BANCO_DE_TESTE, para_testes=True)
    try:
        assert versao_registrada(engine) is None
    finally:
        engine.dispose()


def test_criar_esquema_registra_a_versao_atual() -> None:
    engine = criar_engine(URL_DE_BANCO_DE_TESTE, para_testes=True)
    try:
        assert criar_esquema(engine) == VERSAO_ATUAL
        assert versao_registrada(engine) == VERSAO_ATUAL
    finally:
        engine.dispose()


def test_criar_esquema_e_idempotente(engine_de_teste) -> None:
    """Chamar duas vezes nao duplica nem falha."""
    assert criar_esquema(engine_de_teste) == VERSAO_ATUAL
    assert criar_esquema(engine_de_teste) == VERSAO_ATUAL

    with engine_de_teste.connect() as conexao:
        total = conexao.execute(
            text(f"SELECT COUNT(*) FROM {TABELA_DE_CONTROLE}")
        ).scalar()
    assert total == 1


def test_preparar_banco_retorna_a_versao(engine_de_teste) -> None:
    assert preparar_banco(engine_de_teste) == VERSAO_ATUAL


def test_recriar_esquema_apaga_os_dados() -> None:
    """``--recriar`` e destrutivo: a tabela volta vazia."""
    engine = criar_engine(URL_DE_BANCO_DE_TESTE, para_testes=True)
    try:
        criar_esquema(engine)
        with engine.begin() as conexao:
            conexao.execute(
                text(
                    "INSERT INTO usuarios"
                    " (id, nome, email, senha_hash, papel, ativo, criado_em)"
                    " VALUES ('u1', 'Teste', 't@t', 'h', 'MEDICO', 1, '2026-10-31 12:00:00')"
                )
            )
        assert recriar_esquema(engine) == VERSAO_ATUAL
        with engine.connect() as conexao:
            assert conexao.execute(text("SELECT COUNT(*) FROM usuarios")).scalar() == 0
    finally:
        engine.dispose()


def test_preparar_banco_recusa_versao_divergente() -> None:
    """Banco em versao diferente nao deve subir silenciosamente."""
    engine = criar_engine(URL_DE_BANCO_DE_TESTE, para_testes=True)
    try:
        criar_esquema(engine)
        with engine.begin() as conexao:
            conexao.execute(
                text(
                    f"INSERT INTO {TABELA_DE_CONTROLE} (versao, descricao, aplicada_em)"
                    " VALUES (999, 'versao futura simulada', '2026-10-31 12:00:00')"
                )
            )
        with pytest.raises(EsquemaIncompativelError, match="esperada"):
            preparar_banco(engine)
    finally:
        engine.dispose()


def test_historico_descreve_a_versao_atual() -> None:
    descricoes = dict(HISTORICO)
    assert VERSAO_ATUAL in descricoes
    assert descricoes[VERSAO_ATUAL].strip()


def test_historico_tem_versoes_unicas_e_crescentes() -> None:
    versoes = [versao for versao, _ in HISTORICO]
    assert versoes == sorted(versoes)
    assert len(versoes) == len(set(versoes))


def test_tabela_de_controle_registra_quando_foi_aplicada(engine_de_teste) -> None:
    from sqlalchemy.orm import Session

    with Session(engine_de_teste) as sessao:
        registro = sessao.get(VersaoDoEsquema, VERSAO_ATUAL)
        assert registro is not None
        assert registro.aplicada_em.tzinfo is not None


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def test_cli_cria_o_esquema(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    banco = tmp_path / "cli.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{banco.as_posix()}")

    assert main([]) == 0
    assert banco.exists()


def test_cli_verifica_a_versao(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    banco = tmp_path / "cli2.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{banco.as_posix()}")

    assert main([]) == 0
    assert main(["--verificar"]) == 0


def test_cli_verificar_falha_em_banco_novo(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    banco = tmp_path / "cli3.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{banco.as_posix()}")

    assert main(["--verificar"]) == 1


def test_cli_recriar_apaga_e_recria(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    banco = tmp_path / "cli4.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{banco.as_posix()}")

    assert main([]) == 0
    assert main(["--recriar"]) == 0

    engine = criar_engine(f"sqlite+pysqlite:///{banco.as_posix()}")
    try:
        assert versao_registrada(engine) == VERSAO_ATUAL
    finally:
        engine.dispose()


def test_cli_aceita_database_url_explicita(tmp_path) -> None:
    banco = tmp_path / "cli5.db"
    assert main(["--database-url", f"sqlite+pysqlite:///{banco.as_posix()}"]) == 0
    assert banco.exists()
