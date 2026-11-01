"""Testes de autenticacao/autorizacao (``app/seguranca/dependencias.py``).

O RBAC e exercitado por meio de **rotas de teste** criadas aqui (prefixo ``/_teste``):
os endpoints reais que exigem papel entram nos itens 4 a 7 da Etapa C. As rotas de
teste nao fazem parte do produto — vivem apenas neste modulo.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends

from app.contratos.envelope import RespostaAPI
from app.dados.enums import PapelDoUsuario
from app.dados.modelos import Usuario
from app.dados.repositorios.identidade import UsuarioRepositorio
from app.seguranca.dependencias import exigir_papeis, obter_usuario_atual
from app.seguranca.tokens import emitir_access_token
from tests.conftest import (
    SEGREDO_DE_TESTE,
    AmbienteDeAutenticacao,
    fazer_login,
    semear_usuario,
)

ROTA_MEDICO = "/api/v1/_teste/apenas-medico"
ROTA_ADMIN = "/api/v1/_teste/apenas-admin"
ROTA_AMPLA = "/api/v1/_teste/medico-ou-operador"
ROTA_IDENTIDADE = "/api/v1/_teste/identidade"


def _registrar_rotas_de_teste(ambiente: AmbienteDeAutenticacao) -> None:
    """Adiciona rotas protegidas usadas apenas por estes testes.

    As rotas devolvem o **envelope comum** (``resposta_de_sucesso``), exatamente como
    os endpoints reais, para que a assercao seja a mesma em producao.

    Idempotente: registrar duas vezes criaria rotas duplicadas.
    """
    if getattr(ambiente.app.state, "rotas_de_teste_registradas", False):
        return
    ambiente.app.state.rotas_de_teste_registradas = True

    from fastapi import APIRouter

    from app.contratos.envelope import resposta_de_sucesso

    router = APIRouter(prefix="/_teste", tags=["teste-de-rbac"])

    @router.get("/apenas-medico")
    def _apenas_medico(
        usuario: Usuario = Depends(exigir_papeis(PapelDoUsuario.MEDICO)),
    ) -> RespostaAPI[dict[str, str]]:
        return resposta_de_sucesso({"papel": usuario.papel.value})

    @router.get("/apenas-admin")
    def _apenas_admin(
        usuario: Usuario = Depends(exigir_papeis(PapelDoUsuario.ADMIN)),
    ) -> RespostaAPI[dict[str, str]]:
        return resposta_de_sucesso({"papel": usuario.papel.value})

    @router.get("/medico-ou-operador")
    def _medico_ou_operador(
        usuario: Usuario = Depends(
            exigir_papeis(PapelDoUsuario.MEDICO, PapelDoUsuario.OPERADOR)
        ),
    ) -> RespostaAPI[dict[str, str]]:
        return resposta_de_sucesso({"papel": usuario.papel.value})

    @router.get("/identidade")
    def _identidade(
        usuario: Usuario = Depends(obter_usuario_atual),
    ) -> RespostaAPI[dict[str, str]]:
        return resposta_de_sucesso({"email": usuario.email})

    ambiente.app.include_router(router, prefix="/api/v1")


@pytest.fixture(autouse=True)
def _com_rotas_de_teste(ambiente_de_autenticacao: AmbienteDeAutenticacao) -> None:
    """Registra as rotas de teste em **todo** teste deste modulo."""
    _registrar_rotas_de_teste(ambiente_de_autenticacao)


def _token_de(
    ambiente: AmbienteDeAutenticacao,
    *,
    papel: PapelDoUsuario = PapelDoUsuario.MEDICO,
) -> str:
    """Faz login e devolve o access token."""
    resultado = fazer_login(ambiente)
    assert resultado["status_code"] == 200, resultado["corpo"]
    assert resultado["corpo"]["dados"]["access_token"]
    return resultado["corpo"]["dados"]["access_token"]


def _cabecalho(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------- #
# exigir_papeis
# --------------------------------------------------------------------------- #


def test_exigir_papeis_sem_papeis_e_erro_de_programacao() -> None:
    with pytest.raises(ValueError, match="ao menos um papel"):
        exigir_papeis()


def test_papel_autorizado_passa(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    _registrar_rotas_de_teste(ambiente_de_autenticacao)
    semear_usuario(ambiente_de_autenticacao, papel=PapelDoUsuario.MEDICO)

    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_MEDICO, headers=_cabecalho(_token_de(ambiente_de_autenticacao))
    )
    assert resposta.status_code == 200
    assert resposta.json()["dados"] == {"papel": "MEDICO"}


def test_papel_insuficiente_devolve_403(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    _registrar_rotas_de_teste(ambiente_de_autenticacao)
    semear_usuario(ambiente_de_autenticacao, papel=PapelDoUsuario.OPERADOR)

    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_ADMIN, headers=_cabecalho(_token_de(ambiente_de_autenticacao))
    )
    assert resposta.status_code == 403
    corpo = resposta.json()
    assert corpo["status"] == "ERRO"
    assert corpo["dados"] is None
    assert corpo["erros"][0]["codigo"] == "NAO_AUTORIZADO"


def test_mensagem_do_403_lista_os_papeis_aceitos(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    _registrar_rotas_de_teste(ambiente_de_autenticacao)
    semear_usuario(ambiente_de_autenticacao, papel=PapelDoUsuario.OPERADOR)

    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_ADMIN, headers=_cabecalho(_token_de(ambiente_de_autenticacao))
    )
    detalhe = resposta.json()["erros"][0]["detalhe"]
    assert "ADMIN" in detalhe
    assert "OPERADOR" in detalhe


def test_um_dos_papeis_aceitos_basta(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    _registrar_rotas_de_teste(ambiente_de_autenticacao)
    semear_usuario(ambiente_de_autenticacao, papel=PapelDoUsuario.OPERADOR)

    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_AMPLA, headers=_cabecalho(_token_de(ambiente_de_autenticacao))
    )
    assert resposta.status_code == 200


def test_rota_protegida_sem_token_devolve_401_antes_de_403(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """Sem autenticacao a resposta e 401 — nao 403 (ordem correta dos erros)."""
    _registrar_rotas_de_teste(ambiente_de_autenticacao)
    assert ambiente_de_autenticacao.cliente.get(ROTA_MEDICO).status_code == 401


def test_admin_nao_passa_em_rota_de_medico(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """Os papeis sao conjuntos fechados: ADMIN nao e superusuario implicito."""
    _registrar_rotas_de_teste(ambiente_de_autenticacao)
    semear_usuario(ambiente_de_autenticacao, papel=PapelDoUsuario.ADMIN)

    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_MEDICO, headers=_cabecalho(_token_de(ambiente_de_autenticacao))
    )
    assert resposta.status_code == 403


# --------------------------------------------------------------------------- #
# obter_usuario_atual
# --------------------------------------------------------------------------- #


def test_usuario_atual_e_carregado_do_banco(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    _registrar_rotas_de_teste(ambiente_de_autenticacao)
    semear_usuario(ambiente_de_autenticacao)

    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_IDENTIDADE, headers=_cabecalho(_token_de(ambiente_de_autenticacao))
    )
    assert resposta.status_code == 200
    assert resposta.json()["dados"]["email"] == "medico@teste.local"


def test_usuario_inexistente_no_banco_devolve_401(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """Token bem assinado, mas de um usuario que nao existe mais."""
    token, _ = emitir_access_token(
        id_usuario="usuario-que-nao-existe",
        papel=PapelDoUsuario.MEDICO,
        segredo=SEGREDO_DE_TESTE,
        minutos=30,
    )
    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_IDENTIDADE, headers=_cabecalho(token)
    )
    assert resposta.status_code == 401
    assert "nao existe mais" in resposta.json()["erros"][0]["mensagem"]


def test_usuario_desativado_apos_o_login_devolve_401(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """Desativar a conta invalida os tokens ja emitidos."""
    criado = semear_usuario(ambiente_de_autenticacao)
    token = _token_de(ambiente_de_autenticacao)

    with ambiente_de_autenticacao.fabrica_de_sessoes() as sessao:
        repositorio = UsuarioRepositorio(sessao)
        usuario = repositorio.buscar_por_id(criado["id"])
        assert usuario is not None
        repositorio.definir_ativo(usuario, False)

    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_IDENTIDADE, headers=_cabecalho(token)
    )
    assert resposta.status_code == 401
    assert "inativo" in resposta.json()["erros"][0]["mensagem"]


def test_mudanca_de_papel_invalida_o_token(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    """O banco e a fonte da verdade: token com papel antigo e recusado."""
    _registrar_rotas_de_teste(ambiente_de_autenticacao)
    criado = semear_usuario(ambiente_de_autenticacao, papel=PapelDoUsuario.MEDICO)
    token = _token_de(ambiente_de_autenticacao)

    with ambiente_de_autenticacao.fabrica_de_sessoes() as sessao:
        usuario = UsuarioRepositorio(sessao).buscar_por_id(criado["id"])
        assert usuario is not None
        usuario.papel = PapelDoUsuario.ADMIN
        sessao.commit()

    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_IDENTIDADE, headers=_cabecalho(token)
    )
    assert resposta.status_code == 401
    assert "papel do usuario mudou" in resposta.json()["erros"][0]["mensagem"]


def test_token_expirado_devolve_401(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    criado = semear_usuario(ambiente_de_autenticacao)
    token, _ = emitir_access_token(
        id_usuario=criado["id"],
        papel=PapelDoUsuario.MEDICO,
        segredo=SEGREDO_DE_TESTE,
        minutos=1,
        agora=datetime.now(timezone.utc) - timedelta(hours=3),
    )
    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_IDENTIDADE, headers=_cabecalho(token)
    )
    assert resposta.status_code == 401
    assert "expirado" in resposta.json()["erros"][0]["mensagem"]


def test_token_assinado_com_outro_segredo_devolve_401(
    ambiente_de_autenticacao: AmbienteDeAutenticacao,
) -> None:
    criado = semear_usuario(ambiente_de_autenticacao)
    token, _ = emitir_access_token(
        id_usuario=criado["id"],
        papel=PapelDoUsuario.MEDICO,
        segredo="segredo-de-outro-servico-" + "x" * 20,
        minutos=30,
    )
    resposta = ambiente_de_autenticacao.cliente.get(
        ROTA_IDENTIDADE, headers=_cabecalho(token)
    )
    assert resposta.status_code == 401