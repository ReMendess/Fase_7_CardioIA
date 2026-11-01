"""Testes das rotas de autenticacao (``app/rotas/auth.py``)."""

from __future__ import annotations

from sqlalchemy import select

from app.dados.enums import PapelDoUsuario
from app.dados.modelos import EventoDeAuditoria, Sessao
from app.dados.repositorios.identidade import UsuarioRepositorio
from app.seguranca.tokens import hash_do_refresh_token
from tests.conftest import (
    EMAIL_DE_TESTE,
    SENHA_DE_TESTE,
    AmbienteDeAutenticacao,
    fazer_login,
    semear_usuario,
)

ROTA_LOGIN = "/api/v1/auth/login"
ROTA_REFRESH = "/api/v1/auth/refresh"
ROTA_LOGOUT = "/api/v1/auth/logout"
ROTA_ME = "/api/v1/auth/me"


# --------------------------------------------------------------------------- #
# Apoio
# --------------------------------------------------------------------------- #


def _sessoes_no_banco(ambiente: AmbienteDeAutenticacao) -> list[dict[str, object]]:
    """Sessoes gravadas, em formato simples (evita objeto ORM desanexado)."""
    with ambiente.fabrica_de_sessoes() as sessao:
        return [
            {
                "token_hash": item.token_hash,
                "revogada": item.revogado_em is not None,
                "id_usuario": item.id_usuario,
            }
            for item in sessao.scalars(select(Sessao))
        ]


def _acoes_auditadas(ambiente: AmbienteDeAutenticacao) -> list[tuple[str, dict]]:
    """Pares ``(acao, detalhe_json)`` dos eventos registrados."""
    with ambiente.fabrica_de_sessoes() as sessao:
        return [
            (item.acao, item.detalhe_json or {})
            for item in sessao.scalars(select(EventoDeAuditoria))
        ]


def _cabecalho(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _logar(ambiente: AmbienteDeAutenticacao) -> dict[str, str]:
    """Faz login e devolve o ``dados`` (par de tokens) da resposta."""
    resultado = fazer_login(ambiente)
    assert resultado["status_code"] == 200, resultado["corpo"]
    return resultado["corpo"]["dados"]


# --------------------------------------------------------------------------- #
# POST /auth/login
# --------------------------------------------------------------------------- #


def test_login_com_sucesso_devolve_envelope_e_tokens(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    semear_usuario(ambiente_de_autenticacao)
    resposta = ambiente_de_autenticacao.cliente.post(
        ROTA_LOGIN, json={"email": EMAIL_DE_TESTE, "senha": SENHA_DE_TESTE}
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "CONCLUIDO"
    assert corpo["erros"] == []
    assert corpo["metadados"]["origem"] == "cardioia-backend"
    assert corpo["metadados"]["versao_api"] == "v1"

    dados = corpo["dados"]
    assert set(dados) == {"access_token", "refresh_token", "expira_em"}
    assert dados["access_token"] != dados["refresh_token"]
    assert dados["expira_em"]


def test_login_aceita_email_em_maiusculas_e_com_espacos(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """O e-mail e a chave de login: normalizamos antes de comparar."""
    semear_usuario(ambiente_de_autenticacao)
    resultado = fazer_login(
        ambiente_de_autenticacao, email=f"  {EMAIL_DE_TESTE.upper()}  "
    )
    assert resultado["status_code"] == 200


def test_login_grava_apenas_o_hash_do_refresh(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """O refresh token em claro **nunca** vai para o banco."""
    semear_usuario(ambiente_de_autenticacao)
    dados = _logar(ambiente_de_autenticacao)

    sessoes = _sessoes_no_banco(ambiente_de_autenticacao)
    assert len(sessoes) == 1
    assert sessoes[0]["token_hash"] == hash_do_refresh_token(dados["refresh_token"])
    assert sessoes[0]["token_hash"] != dados["refresh_token"]
    assert sessoes[0]["revogada"] is False


def test_login_atualiza_o_ultimo_acesso(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    criado = semear_usuario(ambiente_de_autenticacao)
    token = _logar(ambiente_de_autenticacao)["access_token"]

    resposta = ambiente_de_autenticacao.cliente.get(ROTA_ME, headers=_cabecalho(token))
    assert resposta.status_code == 200
    assert resposta.json()["dados"]["id_usuario"] == criado["id"]
    assert resposta.json()["dados"]["ultimo_acesso"] is not None


def test_login_registra_auditoria_de_sucesso(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    semear_usuario(ambiente_de_autenticacao)
    _logar(ambiente_de_autenticacao)

    eventos = _acoes_auditadas(ambiente_de_autenticacao)
    assert ("login", {"resultado": "sucesso", "papel": "MEDICO"}) in eventos


# --------------------------------------------------------------------------- #
# POST /auth/login — falhas
# --------------------------------------------------------------------------- #


def test_login_com_email_desconhecido_devolve_401(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    resultado = fazer_login(ambiente_de_autenticacao, email="ninguem@teste.local")

    assert resultado["status_code"] == 401
    corpo = resultado["corpo"]
    assert corpo["status"] == "ERRO"
    assert corpo["dados"] is None
    assert corpo["erros"][0]["codigo"] == "NAO_AUTENTICADO"


def test_login_com_senha_errada_devolve_401(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    semear_usuario(ambiente_de_autenticacao)
    resultado = fazer_login(ambiente_de_autenticacao, senha="senha-errada-123")

    assert resultado["status_code"] == 401
    assert resultado["corpo"]["erros"][0]["codigo"] == "NAO_AUTENTICADO"


def test_login_nao_revela_se_o_email_existe(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """E-mail inexistente e senha errada devem ser indistinguiveis para o cliente."""
    semear_usuario(ambiente_de_autenticacao)

    desconhecido = fazer_login(ambiente_de_autenticacao, email="ninguem@teste.local")
    senha_errada = fazer_login(ambiente_de_autenticacao, senha="senha-errada-123")

    assert desconhecido["status_code"] == senha_errada["status_code"] == 401
    assert (
        desconhecido["corpo"]["erros"][0]["mensagem"]
        == senha_errada["corpo"]["erros"][0]["mensagem"]
    )


def test_login_audita_email_desconhecido_sem_id_de_usuario(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    fazer_login(ambiente_de_autenticacao, email="ninguem@teste.local")
    eventos = _acoes_auditadas(ambiente_de_autenticacao)
    assert ("login", {"resultado": "email_desconhecido"}) in eventos


def test_login_audita_senha_incorreta(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    semear_usuario(ambiente_de_autenticacao)
    fazer_login(ambiente_de_autenticacao, senha="senha-errada-123")
    eventos = _acoes_auditadas(ambiente_de_autenticacao)
    assert ("login", {"resultado": "senha_incorreta"}) in eventos


def test_login_de_conta_inativa_devolve_403(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """Conta desativada e um caso de autorizacao, nao de credencial invalida."""
    semear_usuario(ambiente_de_autenticacao, ativo=False)
    resultado = fazer_login(ambiente_de_autenticacao)

    assert resultado["status_code"] == 403
    assert resultado["corpo"]["erros"][0]["codigo"] == "NAO_AUTORIZADO"


def test_login_de_conta_inativa_nao_cria_sessao(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    semear_usuario(ambiente_de_autenticacao, ativo=False)
    fazer_login(ambiente_de_autenticacao)
    assert _sessoes_no_banco(ambiente_de_autenticacao) == []


def test_login_bloqueia_apos_cinco_tentativas(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """5 falhas em 5 minutos bloqueiam a chave ``email|ip`` (429)."""
    semear_usuario(ambiente_de_autenticacao)

    for _ in range(5):
        resultado = fazer_login(ambiente_de_autenticacao, senha="senha-errada-123")
        assert resultado["status_code"] == 401

    bloqueado = fazer_login(ambiente_de_autenticacao, senha="senha-errada-123")
    assert bloqueado["status_code"] == 429
    assert bloqueado["corpo"]["erros"][0]["codigo"] == "TAXA_EXCEDIDA"


def test_login_bem_sucedido_limpa_o_contador_de_falhas(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """O usuario que acerta a senha nao deve ficar marcado pelas falhas anteriores."""
    semear_usuario(ambiente_de_autenticacao)

    for _ in range(4):
        fazer_login(ambiente_de_autenticacao, senha="senha-errada-123")

    assert fazer_login(ambiente_de_autenticacao)["status_code"] == 200
    assert fazer_login(ambiente_de_autenticacao)["status_code"] == 200


def test_login_com_corpo_invalido_devolve_422(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    resposta = ambiente_de_autenticacao.cliente.post(ROTA_LOGIN, json={"email": "a@b.c"})
    assert resposta.status_code == 422
    assert resposta.json()["erros"][0]["codigo"] == "CONTRATO_VIOLADO"


def test_login_rejeita_campo_desconhecido(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """Contrato fechado: campo extra e recusado, nao ignorado."""
    resposta = ambiente_de_autenticacao.cliente.post(
        ROTA_LOGIN,
        json={"email": EMAIL_DE_TESTE, "senha": SENHA_DE_TESTE, "admin": True},
    )
    assert resposta.status_code == 422


# --------------------------------------------------------------------------- #
# POST /auth/refresh
# --------------------------------------------------------------------------- #


def test_refresh_rotaciona_e_devolve_novo_par(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    semear_usuario(ambiente_de_autenticacao)
    primeiro = _logar(ambiente_de_autenticacao)

    resposta = ambiente_de_autenticacao.cliente.post(
        ROTA_REFRESH, json={"refresh_token": primeiro["refresh_token"]}
    )
    assert resposta.status_code == 200
    segundo = resposta.json()["dados"]

    assert set(segundo) == {"access_token", "refresh_token", "expira_em"}
    assert segundo["refresh_token"] != primeiro["refresh_token"]
    assert segundo["access_token"] != primeiro["access_token"]


def test_refresh_revoga_o_token_utilizado(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """Rotacao: o token apresentado deixa de valer, mesmo apos o sucesso."""
    semear_usuario(ambiente_de_autenticacao)
    primeiro = _logar(ambiente_de_autenticacao)

    ambiente_de_autenticacao.cliente.post(
        ROTA_REFRESH, json={"refresh_token": primeiro["refresh_token"]}
    )
    sessoes = _sessoes_no_banco(ambiente_de_autenticacao)

    hash_antigo = hash_do_refresh_token(primeiro["refresh_token"])
    antigo = next(item for item in sessoes if item["token_hash"] == hash_antigo)
    assert antigo["revogada"] is True
    assert len(sessoes) == 2


def test_refresh_reutilizado_devolve_401(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    semear_usuario(ambiente_de_autenticacao)
    primeiro = _logar(ambiente_de_autenticacao)
    ambiente_de_autenticacao.cliente.post(
        ROTA_REFRESH, json={"refresh_token": primeiro["refresh_token"]}
    )

    repetido = ambiente_de_autenticacao.cliente.post(
        ROTA_REFRESH, json={"refresh_token": primeiro["refresh_token"]}
    )
    assert repetido.status_code == 401
    assert repetido.json()["erros"][0]["codigo"] == "NAO_AUTENTICADO"


def test_refresh_com_token_inexistente_devolve_401(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    resposta = ambiente_de_autenticacao.cliente.post(
        ROTA_REFRESH, json={"refresh_token": "token-que-nunca-existiu-na-base"}
    )
    assert resposta.status_code == 401


def test_access_token_nao_serve_como_refresh(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """Tipos diferentes de token nao sao intercambiaveis."""
    semear_usuario(ambiente_de_autenticacao)
    dados = _logar(ambiente_de_autenticacao)

    resposta = ambiente_de_autenticacao.cliente.post(
        ROTA_REFRESH, json={"refresh_token": dados["access_token"]}
    )
    assert resposta.status_code == 401


def test_refresh_de_usuario_desativado_revoga_a_sessao(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    criado = semear_usuario(ambiente_de_autenticacao)
    dados = _logar(ambiente_de_autenticacao)

    with ambiente_de_autenticacao.fabrica_de_sessoes() as sessao:
        repositorio = UsuarioRepositorio(sessao)
        usuario = repositorio.buscar_por_id(criado["id"])
        assert usuario is not None
        repositorio.definir_ativo(usuario, False)

    resposta = ambiente_de_autenticacao.cliente.post(
        ROTA_REFRESH, json={"refresh_token": dados["refresh_token"]}
    )
    assert resposta.status_code == 401
    assert all(item["revogada"] for item in _sessoes_no_banco(ambiente_de_autenticacao))


def test_refresh_com_token_curto_devolve_422(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    resposta = ambiente_de_autenticacao.cliente.post(
        ROTA_REFRESH, json={"refresh_token": "curto"}
    )
    assert resposta.status_code == 422


# --------------------------------------------------------------------------- #
# POST /auth/logout
# --------------------------------------------------------------------------- #


def test_logout_revoga_as_sessoes(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    semear_usuario(ambiente_de_autenticacao)
    dados = _logar(ambiente_de_autenticacao)

    resposta = ambiente_de_autenticacao.cliente.post(
        ROTA_LOGOUT, headers=_cabecalho(dados["access_token"])
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "CONCLUIDO"
    assert corpo["dados"] == {"encerrado": True, "sessoes_revogadas": 1}

    sessoes = _sessoes_no_banco(ambiente_de_autenticacao)
    assert all(item["revogada"] for item in sessoes)


def test_logout_revoga_todas_as_sessoes_do_usuario(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """Varios dispositivos: o logout encerra todos (comportamento documentado)."""
    semear_usuario(ambiente_de_autenticacao)
    primeiro = _logar(ambiente_de_autenticacao)
    segundo = _logar(ambiente_de_autenticacao)

    resposta = ambiente_de_autenticacao.cliente.post(
        ROTA_LOGOUT, headers=_cabecalho(segundo["access_token"])
    )
    assert resposta.json()["dados"]["sessoes_revogadas"] == 2
    assert all(item["revogada"] for item in _sessoes_no_banco(ambiente_de_autenticacao))
    assert primeiro["refresh_token"] != segundo["refresh_token"]


def test_logout_impede_a_renovacao(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    semear_usuario(ambiente_de_autenticacao)
    dados = _logar(ambiente_de_autenticacao)

    ambiente_de_autenticacao.cliente.post(
        ROTA_LOGOUT, headers=_cabecalho(dados["access_token"])
    )
    renovacao = ambiente_de_autenticacao.cliente.post(
        ROTA_REFRESH, json={"refresh_token": dados["refresh_token"]}
    )
    assert renovacao.status_code == 401


def test_logout_sem_token_devolve_401(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    resposta = ambiente_de_autenticacao.cliente.post(ROTA_LOGOUT)
    assert resposta.status_code == 401
    assert resposta.json()["erros"][0]["codigo"] == "NAO_AUTENTICADO"


def test_logout_registra_auditoria(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    semear_usuario(ambiente_de_autenticacao)
    dados = _logar(ambiente_de_autenticacao)
    ambiente_de_autenticacao.cliente.post(
        ROTA_LOGOUT, headers=_cabecalho(dados["access_token"])
    )

    eventos = _acoes_auditadas(ambiente_de_autenticacao)
    assert ("logout", {"sessoes_revogadas": 1}) in eventos


# --------------------------------------------------------------------------- #
# GET /auth/me
# --------------------------------------------------------------------------- #


def test_me_devolve_o_usuario_autenticado(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    criado = semear_usuario(ambiente_de_autenticacao, papel=PapelDoUsuario.ADMIN)
    dados = _logar(ambiente_de_autenticacao)

    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_ME, headers=_cabecalho(dados["access_token"])
    )
    assert resposta.status_code == 200
    usuario = resposta.json()["dados"]

    assert usuario["id_usuario"] == criado["id"]
    assert usuario["email"] == EMAIL_DE_TESTE
    assert usuario["papel"] == "ADMIN"
    assert usuario["ativo"] is True


def test_me_nunca_expoe_o_hash_da_senha(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """🔒 ``senha_hash`` nao pode sair em nenhuma resposta da API."""
    semear_usuario(ambiente_de_autenticacao)
    dados = _logar(ambiente_de_autenticacao)

    corpo = ambiente_de_autenticacao.cliente.get(
        ROTA_ME, headers=_cabecalho(dados["access_token"])
    ).text
    assert "senha_hash" not in corpo
    assert "$2b$" not in corpo


def test_me_sem_token_devolve_401_com_cabecalho_www_authenticate(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    resposta = ambiente_de_autenticacao.cliente.get(ROTA_ME)
    assert resposta.status_code == 401
    assert resposta.headers.get("WWW-Authenticate") == "Bearer"
    assert resposta.json()["erros"][0]["codigo"] == "NAO_AUTENTICADO"


def test_me_com_token_invalido_devolve_401(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_ME, headers=_cabecalho("token.completamente.invalido")
    )
    assert resposta.status_code == 401


def test_me_com_esquema_diferente_de_bearer_devolve_401(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    semear_usuario(ambiente_de_autenticacao)
    dados = _logar(ambiente_de_autenticacao)

    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_ME, headers={"Authorization": f"Basic {dados['access_token']}"}
    )
    assert resposta.status_code == 401