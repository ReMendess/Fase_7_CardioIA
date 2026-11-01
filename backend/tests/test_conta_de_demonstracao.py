"""Testes da conta de demonstracao semeada no startup (``app/main.py``).

Por que a funcionalidade existe: em hospedagem gratuita o sistema de arquivos e
**efemero** — o SQLite volta vazio a cada reinicio, e sem usuario nao ha como entrar na
aplicacao publicada. Semear no startup torna o servico auto-suficiente.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.dados.base import criar_engine, criar_fabrica_de_sessoes
from app.dados.modelos import Usuario
from app.main import criar_app
from tests.conftest import _configuracao_base

ROTA_LOGIN = "/api/v1/auth/login"


def _url(pasta: Path) -> str:
    """Banco isolado por teste (o padrao da suite e compartilhado)."""
    return f"sqlite:///{(pasta / 'demo.db').as_posix()}"


def _usuarios(url: str) -> list[Usuario]:
    engine = criar_engine(url)
    with criar_fabrica_de_sessoes(engine)() as sessao:
        usuarios = list(sessao.scalars(select(Usuario)))
    engine.dispose()
    return usuarios


def test_conta_de_demonstracao_e_criada_quando_o_banco_esta_vazio(tmp_path: Path) -> None:
    """Servidor novo, banco vazio: a conta existe e da para entrar."""
    url = _url(tmp_path)
    app = criar_app(_configuracao_base(str(tmp_path), database_url=url, semear_usuario_inicial=True))

    with TestClient(app) as cliente:
        resposta = cliente.post(
            ROTA_LOGIN, json={"email": "teste", "senha": "senhaTeste23@"}
        )

    assert resposta.status_code == 200
    assert resposta.json()["dados"]["access_token"]

    usuarios = _usuarios(url)
    assert len(usuarios) == 1
    assert usuarios[0].email == "teste"
    assert usuarios[0].papel.value == "MEDICO"
    # A senha nunca e gravada em claro.
    assert "senhaTeste23@" not in usuarios[0].senha_hash


def test_semeadura_e_idempotente(tmp_path: Path) -> None:
    """Dois startups no mesmo banco nao criam a conta duas vezes."""
    url = _url(tmp_path)
    config = _configuracao_base(str(tmp_path), database_url=url, semear_usuario_inicial=True)

    with TestClient(criar_app(config)):
        pass
    with TestClient(criar_app(config)):
        pass

    assert len(_usuarios(url)) == 1


def test_banco_com_usuario_nao_recebe_a_conta_de_demonstracao(tmp_path: Path) -> None:
    """Se ja existe alguem, o startup nao acrescenta nada — nem sobrescreve senha."""
    from app.dados.enums import PapelDoUsuario
    from app.dados.repositorios.identidade import UsuarioRepositorio
    from app.seguranca.senhas import gerar_hash

    url = _url(tmp_path)
    config = _configuracao_base(str(tmp_path), database_url=url, semear_usuario_inicial=True)

    # Primeiro startup cria o esquema; o segundo encontra o banco ja povoado.
    with TestClient(criar_app(config)):
        pass

    engine = criar_engine(url)
    with criar_fabrica_de_sessoes(engine)() as sessao:
        UsuarioRepositorio(sessao).criar(
            nome="Outro Usuario",
            email="outro@exemplo.local",
            senha_hash=gerar_hash("outraSenha123"),
            papel=PapelDoUsuario.OPERADOR,
        )
    engine.dispose()

    with TestClient(criar_app(config)):
        pass

    emails = sorted(u.email for u in _usuarios(url))
    assert emails == ["outro@exemplo.local", "teste"]


def test_semeadura_desligada_nao_cria_nada(tmp_path: Path) -> None:
    """`SEMEAR_USUARIO_INICIAL=false` deixa o banco vazio (ambiente de teste)."""
    url = _url(tmp_path)
    config = _configuracao_base(
        str(tmp_path), database_url=url, semear_usuario_inicial=False
    )

    with TestClient(criar_app(config)):
        pass

    assert _usuarios(url) == []


@pytest.mark.parametrize("papel", ["MEDICO", "OPERADOR", "ADMIN"])
def test_papel_da_conta_e_configuravel(tmp_path: Path, papel: str) -> None:
    """O papel vem da configuracao — o mesmo codigo serve para qualquer perfil."""
    url = _url(tmp_path)
    config = _configuracao_base(
        str(tmp_path),
        database_url=url,
        semear_usuario_inicial=True,
        usuario_inicial_papel=papel,
    )

    with TestClient(criar_app(config)):
        pass

    assert _usuarios(url)[0].papel.value == papel


def test_papel_invalido_nao_derruba_o_startup(tmp_path: Path) -> None:
    """Configuracao errada vira log, nao indisponibilidade do servico."""
    url = _url(tmp_path)
    config = _configuracao_base(
        str(tmp_path),
        database_url=url,
        semear_usuario_inicial=True,
        usuario_inicial_papel="SUPERUSUARIO",
    )

    with TestClient(criar_app(config)) as cliente:
        assert cliente.get("/api/v1/health").status_code == 200

    assert _usuarios(url) == []
