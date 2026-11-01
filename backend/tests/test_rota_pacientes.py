"""Testes das rotas de pacientes (``app/rotas/pacientes.py``)."""

from __future__ import annotations

from sqlalchemy import select

from app.dados.enums import PapelDoUsuario
from app.dados.modelos import EventoDeAuditoria, Paciente
from tests.conftest import (
    AmbienteClinico,
    cabecalho,
    criar_paciente,
    token_com_papel,
)

ROTA = "/api/v1/pacientes"


def _pacientes_no_banco(ambiente: AmbienteClinico) -> list[dict[str, object]]:
    with ambiente.fabrica_de_sessoes() as sessao:
        return [
            {"id": item.id, "nome": item.nome, "ativo": item.ativo}
            for item in sessao.scalars(select(Paciente))
        ]


def _acoes_auditadas(ambiente: AmbienteClinico) -> list[str]:
    with ambiente.fabrica_de_sessoes() as sessao:
        return [item.acao for item in sessao.scalars(select(EventoDeAuditoria))]


# --------------------------------------------------------------------------- #
# POST /pacientes
# --------------------------------------------------------------------------- #


def test_cadastra_paciente(ambiente_clinico: AmbienteClinico) -> None:
    resposta = ambiente_clinico.cliente.post(
        ROTA, json={"nome": "Maria Souza"}, headers=cabecalho(ambiente_clinico.token)
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "CONCLUIDO"
    assert corpo["erros"] == []
    assert corpo["metadados"]["origem"] == "cardioia-backend"

    dados = corpo["dados"]
    assert set(dados) == {"id_paciente", "nome", "ativo", "criado_em", "criado_por"}
    assert dados["nome"] == "Maria Souza"
    assert dados["ativo"] is True
    assert dados["criado_por"] == ambiente_clinico.id_usuario


def test_cadastro_guarda_apenas_identidade(ambiente_clinico: AmbienteClinico) -> None:
    """Resposta Q1: as 10 features sao estado clinico datado, nao cadastro."""
    criar_paciente(ambiente_clinico, nome="Ana Lima")
    registro = _pacientes_no_banco(ambiente_clinico)[0]

    with ambiente_clinico.fabrica_de_sessoes() as sessao:
        paciente = sessao.get(Paciente, registro["id"])
        assert paciente is not None
        colunas = {coluna.name for coluna in Paciente.__table__.columns}
        assert "idade_media" not in colunas
        assert "temperatura" not in colunas


def test_cadastro_normaliza_espacos_do_nome(ambiente_clinico: AmbienteClinico) -> None:
    resposta = ambiente_clinico.cliente.post(
        ROTA, json={"nome": "  Joao da Silva  "}, headers=cabecalho(ambiente_clinico.token)
    )
    assert resposta.status_code == 201
    assert resposta.json()["dados"]["nome"] == "Joao da Silva"


def test_cadastro_rejeita_nome_so_de_espacos(ambiente_clinico: AmbienteClinico) -> None:
    """Sem esta guarda, ``'   '`` passaria no ``min_length`` e viraria nome vazio."""
    resposta = ambiente_clinico.cliente.post(
        ROTA, json={"nome": "   "}, headers=cabecalho(ambiente_clinico.token)
    )
    assert resposta.status_code == 422
    assert resposta.json()["erros"][0]["codigo"] == "CONTRATO_VIOLADO"


def test_cadastro_rejeita_corpo_invalido(ambiente_clinico: AmbienteClinico) -> None:
    for corpo in ({}, {"nome": ""}, {"nome": "a" * 121}, {"nome": "X", "extra": 1}):
        resposta = ambiente_clinico.cliente.post(
            ROTA, json=corpo, headers=cabecalho(ambiente_clinico.token)
        )
        assert resposta.status_code == 422, corpo


def test_cadastro_registra_auditoria_sem_dado_pessoal(
    ambiente_clinico: AmbienteClinico,
) -> None:
    """🔒 A trilha nao precisa do nome do paciente para cumprir seu papel (LGPD)."""
    id_paciente = criar_paciente(ambiente_clinico, nome="Carlos Pereira")

    with ambiente_clinico.fabrica_de_sessoes() as sessao:
        eventos = list(
            sessao.scalars(
                select(EventoDeAuditoria).where(EventoDeAuditoria.acao == "criar_paciente")
            )
        )

    assert len(eventos) == 1
    evento = eventos[0]
    assert evento.entidade == "pacientes"
    assert evento.id_entidade == id_paciente
    assert evento.id_usuario == ambiente_clinico.id_usuario
    assert evento.detalhe_json is None  # nenhum dado pessoal na trilha


def test_cadastro_sobrevive_a_nome_repetido(ambiente_clinico: AmbienteClinico) -> None:
    """Homônimos existem: o nome nao e chave unica (a chave e o id)."""
    primeiro = criar_paciente(ambiente_clinico, nome="Jose Silva")
    segundo = criar_paciente(ambiente_clinico, nome="Jose Silva")
    assert primeiro != segundo


# --------------------------------------------------------------------------- #
# RBAC
# --------------------------------------------------------------------------- #


def test_cadastro_exige_autenticacao(ambiente_clinico: AmbienteClinico) -> None:
    resposta = ambiente_clinico.cliente.post(ROTA, json={"nome": "Sem Token"})
    assert resposta.status_code == 401
    assert resposta.json()["erros"][0]["codigo"] == "NAO_AUTENTICADO"


def test_cadastro_exige_papel_medico(ambiente_clinico: AmbienteClinico) -> None:
    """``ADMIN`` administra o sistema, mas nao escreve dado clinico."""
    for papel in (PapelDoUsuario.ADMIN, PapelDoUsuario.OPERADOR):
        token = token_com_papel(ambiente_clinico, papel)
        resposta = ambiente_clinico.cliente.post(
            ROTA, json={"nome": "Nao Permitido"}, headers=cabecalho(token)
        )
        assert resposta.status_code == 403, papel
        assert resposta.json()["erros"][0]["codigo"] == "NAO_AUTORIZADO"


# --------------------------------------------------------------------------- #
# GET /pacientes
# --------------------------------------------------------------------------- #


def test_lista_vazia(ambiente_clinico: AmbienteClinico) -> None:
    resposta = ambiente_clinico.cliente.get(ROTA, headers=cabecalho(ambiente_clinico.token))
    assert resposta.status_code == 200
    assert resposta.json()["dados"] == []


def test_lista_pacientes_cadastrados(ambiente_clinico: AmbienteClinico) -> None:
    criar_paciente(ambiente_clinico, nome="Primeiro")
    criar_paciente(ambiente_clinico, nome="Segundo")

    resposta = ambiente_clinico.cliente.get(ROTA, headers=cabecalho(ambiente_clinico.token))
    nomes = [item["nome"] for item in resposta.json()["dados"]]
    assert sorted(nomes) == ["Primeiro", "Segundo"]


def test_lista_respeita_paginacao(ambiente_clinico: AmbienteClinico) -> None:
    for indice in range(5):
        criar_paciente(ambiente_clinico, nome=f"Paciente {indice}")

    resposta = ambiente_clinico.cliente.get(
        ROTA,
        params={"limite": 2, "deslocamento": 0},
        headers=cabecalho(ambiente_clinico.token),
    )
    assert len(resposta.json()["dados"]) == 2

    seguinte = ambiente_clinico.cliente.get(
        ROTA,
        params={"limite": 2, "deslocamento": 2},
        headers=cabecalho(ambiente_clinico.token),
    )
    assert len(seguinte.json()["dados"]) == 2
    ids_primeira = {item["id_paciente"] for item in resposta.json()["dados"]}
    ids_segunda = {item["id_paciente"] for item in seguinte.json()["dados"]}
    assert ids_primeira.isdisjoint(ids_segunda)


def test_lista_rejeita_paginacao_invalida(ambiente_clinico: AmbienteClinico) -> None:
    for parametros in ({"limite": 0}, {"limite": 999}, {"deslocamento": -1}):
        resposta = ambiente_clinico.cliente.get(
            ROTA, params=parametros, headers=cabecalho(ambiente_clinico.token)
        )
        assert resposta.status_code == 422, parametros


def test_lista_oculta_inativos_por_padrao(ambiente_clinico: AmbienteClinico) -> None:
    """Soft delete nao polui a lista; ``apenas_ativos=false`` mostra tudo."""
    id_ativo = criar_paciente(ambiente_clinico, nome="Ativo")
    id_inativo = criar_paciente(ambiente_clinico, nome="Inativo")

    with ambiente_clinico.fabrica_de_sessoes() as sessao:
        paciente = sessao.get(Paciente, id_inativo)
        assert paciente is not None
        paciente.ativo = False
        sessao.commit()

    padrao = ambiente_clinico.cliente.get(ROTA, headers=cabecalho(ambiente_clinico.token))
    assert [item["id_paciente"] for item in padrao.json()["dados"]] == [id_ativo]

    todos = ambiente_clinico.cliente.get(
        ROTA, params={"apenas_ativos": "false"}, headers=cabecalho(ambiente_clinico.token)
    )
    assert {item["id_paciente"] for item in todos.json()["dados"]} == {id_ativo, id_inativo}


def test_leitura_permitida_para_admin(ambiente_clinico: AmbienteClinico) -> None:
    criar_paciente(ambiente_clinico)
    token = token_com_papel(ambiente_clinico, PapelDoUsuario.ADMIN)

    resposta = ambiente_clinico.cliente.get(ROTA, headers=cabecalho(token))
    assert resposta.status_code == 200
    assert len(resposta.json()["dados"]) == 1


def test_leitura_negada_para_operador(ambiente_clinico: AmbienteClinico) -> None:
    token = token_com_papel(ambiente_clinico, PapelDoUsuario.OPERADOR)
    resposta = ambiente_clinico.cliente.get(ROTA, headers=cabecalho(token))
    assert resposta.status_code == 403


def test_lista_exige_autenticacao(ambiente_clinico: AmbienteClinico) -> None:
    assert ambiente_clinico.cliente.get(ROTA).status_code == 401


# --------------------------------------------------------------------------- #
# GET /pacientes/{id_paciente}
# --------------------------------------------------------------------------- #


def test_obtem_paciente_por_id(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico, nome="Detalhe Teste")

    resposta = ambiente_clinico.cliente.get(
        f"{ROTA}/{id_paciente}", headers=cabecalho(ambiente_clinico.token)
    )
    assert resposta.status_code == 200
    assert resposta.json()["dados"]["id_paciente"] == id_paciente
    assert resposta.json()["dados"]["nome"] == "Detalhe Teste"


def test_paciente_inexistente_devolve_404(ambiente_clinico: AmbienteClinico) -> None:
    resposta = ambiente_clinico.cliente.get(
        f"{ROTA}/nao-existe-este-id", headers=cabecalho(ambiente_clinico.token)
    )
    assert resposta.status_code == 404
    corpo = resposta.json()
    assert corpo["dados"] is None
    assert corpo["erros"][0]["codigo"] == "NAO_ENCONTRADO"
    assert corpo["erros"][0]["campo"] == "id_paciente"


def test_detalhe_permite_ver_paciente_inativo(ambiente_clinico: AmbienteClinico) -> None:
    """Inativo sai da listagem, mas o historico continua consultavel."""
    id_paciente = criar_paciente(ambiente_clinico)
    with ambiente_clinico.fabrica_de_sessoes() as sessao:
        paciente = sessao.get(Paciente, id_paciente)
        assert paciente is not None
        paciente.ativo = False
        sessao.commit()

    resposta = ambiente_clinico.cliente.get(
        f"{ROTA}/{id_paciente}", headers=cabecalho(ambiente_clinico.token)
    )
    assert resposta.status_code == 200
    assert resposta.json()["dados"]["ativo"] is False


def test_detalhe_negado_para_operador(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    token = token_com_papel(ambiente_clinico, PapelDoUsuario.OPERADOR)

    resposta = ambiente_clinico.cliente.get(
        f"{ROTA}/{id_paciente}", headers=cabecalho(token)
    )
    assert resposta.status_code == 403