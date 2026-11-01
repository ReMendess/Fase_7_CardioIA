"""Testes do CORS (``app/main.py``).

CORS passou a ser um ponto sensivel no deploy: o frontend fica na Vercel e o backend no
Render — origens diferentes. Um erro aqui faz a aplicacao abrir e **nenhuma** chamada
passar, que e exatamente o sintoma mais dificil de diagnosticar.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import criar_app
from tests.conftest import _configuracao_base

ROTA = "/api/v1/health"
CABECALHO = "access-control-allow-origin"


def _cliente(tmp_path: Path, **extras: object) -> TestClient:
    pasta = tmp_path / f"cors-{len(list(tmp_path.iterdir()))}"
    pasta.mkdir(parents=True, exist_ok=True)
    config = _configuracao_base(
        str(pasta),
        database_url=f"sqlite:///{(pasta / 'cors.db').as_posix()}",
        **extras,
    )
    return TestClient(criar_app(config))


def test_origem_configurada_recebe_o_cabecalho(tmp_path: Path) -> None:
    with _cliente(tmp_path, cors_origens="http://localhost:5173") as cliente:
        resposta = cliente.get(ROTA, headers={"Origin": "http://localhost:5173"})

    assert resposta.headers.get(CABECALHO) == "http://localhost:5173"


def test_origem_desconhecida_nao_recebe_o_cabecalho(tmp_path: Path) -> None:
    """Origem fora da lista nao e liberada — e o navegador bloqueia a resposta."""
    with _cliente(tmp_path, cors_origens="http://localhost:5173") as cliente:
        resposta = cliente.get(ROTA, headers={"Origin": "http://malicioso.example"})

    assert CABECALHO not in resposta.headers


def test_cors_nao_usa_curinga(tmp_path: Path) -> None:
    """`*` liberaria qualquer site; o projeto usa lista explicita."""
    with _cliente(tmp_path, cors_origens="http://localhost:5173") as cliente:
        resposta = cliente.get(ROTA, headers={"Origin": "http://localhost:5173"})

    assert resposta.headers.get(CABECALHO) != "*"


def test_credenciais_nao_estao_habilitadas(tmp_path: Path) -> None:
    """O token viaja no header `Authorization`, nao em cookie — cookie seria CSRF."""
    with _cliente(tmp_path, cors_origens="http://localhost:5173") as cliente:
        resposta = cliente.get(ROTA, headers={"Origin": "http://localhost:5173"})

    assert resposta.headers.get("access-control-allow-credentials") in (None, "false")


def test_regex_de_origem_libera_preview_da_vercel(tmp_path: Path) -> None:
    """A Vercel cria um dominio novo a cada deploy; o regex cobre todos de uma vez."""
    with _cliente(
        tmp_path,
        cors_origens="http://localhost:5173",
        cors_origem_regex=r"^https://.*\.vercel\.app$",
    ) as cliente:
        resposta = cliente.get(
            ROTA, headers={"Origin": "https://cardioia-fase7.vercel.app"}
        )

    assert resposta.headers.get(CABECALHO) == "https://cardioia-fase7.vercel.app"


def test_regex_nao_libera_origem_parecida(tmp_path: Path) -> None:
    """O regex e ancorado: um dominio que apenas *contem* vercel.app nao passa."""
    with _cliente(
        tmp_path,
        cors_origens="http://localhost:5173",
        cors_origem_regex=r"^https://.*\.vercel\.app$",
    ) as cliente:
        resposta = cliente.get(
            ROTA, headers={"Origin": "https://vercel.app.malicioso.example"}
        )

    assert CABECALHO not in resposta.headers


def test_regex_vazio_nao_libera_nada_alem_da_lista(tmp_path: Path) -> None:
    """Padrao seguro: sem `CORS_ORIGEM_REGEX`, nada fora da lista entra."""
    with _cliente(tmp_path, cors_origens="http://localhost:5173", cors_origem_regex="") as cliente:
        resposta = cliente.get(ROTA, headers={"Origin": "https://qualquer.vercel.app"})

    assert CABECALHO not in resposta.headers


@pytest.mark.parametrize("origem", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_os_dois_nomes_de_host_local_sao_aceitos(tmp_path: Path, origem: str) -> None:
    """`localhost` e `127.0.0.1` sao origens diferentes para o navegador."""
    with _cliente(
        tmp_path,
        cors_origens="http://localhost:5173,http://127.0.0.1:5173",
    ) as cliente:
        resposta = cliente.get(ROTA, headers={"Origin": origem})

    assert resposta.headers.get(CABECALHO) == origem


def test_preflight_anuncia_metodo_e_cabecalho(tmp_path: Path) -> None:
    """O navegador envia OPTIONS antes de um POST com `Authorization`."""
    with _cliente(tmp_path, cors_origens="http://localhost:5173") as cliente:
        resposta = cliente.options(
            "/api/v1/pacientes",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    assert resposta.status_code in (200, 204)
    assert "POST" in resposta.headers.get("access-control-allow-methods", "")
    assert "authorization" in resposta.headers.get("access-control-allow-headers", "").lower()
