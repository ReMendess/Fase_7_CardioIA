"""Testes das rotas do assistente (``app/rotas/assistente.py``).

Usam o **cliente do SDK falso** (``tests/conftest.py``): nenhuma chamada de rede. O que se
verifica e o contrato da Fase 7 — em especial que o `session_id` do Watson **nao** sai daqui
(achado **I8**) e que `fontes` e sempre `[]` (nota **N6**).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import select

from app.contratos.assistente import AVISO_DO_ASSISTENTE, LIMITACOES_DO_ASSISTENTE
from app.dados.enums import PapelDaMensagem, PapelDoUsuario
from app.dados.modelos import Conversa, EventoDeAuditoria, Mensagem
from tests.conftest import (
    AmbienteClinico,
    ClienteFalso,
    ErroDoSdk,
    _app_de_teste,
    _configuracao_base,
    cabecalho,
    conversar_com_o_assistente,
    token_com_papel,
)

ROTA_CHAT = "/api/v1/chat"
ROTA_CONVERSA = "/api/v1/conversas"
ACAO_ABRIR_CONVERSA = "abrir_conversa"
SESSAO_DO_WATSON = "sessao-interna-1"


@pytest.fixture
def ambiente_sem_watson(tmp_path_factory: pytest.TempPathFactory) -> Iterator[AmbienteClinico]:
    """App **sem** Watson configurado: a rota deve responder ``501``."""
    pasta = tmp_path_factory.mktemp("fase7_assistente_sem_watson")
    with _app_de_teste(_configuracao_base(str(pasta))) as ambiente:
        yield ambiente


# --------------------------------------------------------------------------- #
# Apoio
# --------------------------------------------------------------------------- #


def _conversas(ambiente: AmbienteClinico) -> list[Conversa]:
    with ambiente.fabrica_de_sessoes() as sessao:
        return list(sessao.scalars(select(Conversa)))


def _mensagens(ambiente: AmbienteClinico) -> list[Mensagem]:
    with ambiente.fabrica_de_sessoes() as sessao:
        return list(sessao.scalars(select(Mensagem).order_by(Mensagem.criado_em)))


def _auditorias(ambiente: AmbienteClinico, acao: str) -> list[EventoDeAuditoria]:
    with ambiente.fabrica_de_sessoes() as sessao:
        return list(
            sessao.scalars(select(EventoDeAuditoria).where(EventoDeAuditoria.acao == acao))
        )


# --------------------------------------------------------------------------- #
# POST /chat — caminho feliz
# --------------------------------------------------------------------------- #


def test_primeiro_turno_devolve_o_contrato(
    ambiente_do_assistente: AmbienteClinico, cliente_do_watson_falso: ClienteFalso
) -> None:
    cliente_do_watson_falso.textos = ["Bem-vindo ao CardioAssist."]
    resultado = conversar_com_o_assistente(ambiente_do_assistente, mensagem="Ola")

    assert resultado["status_code"] == 200
    corpo = resultado["corpo"]
    assert corpo["status"] == "CONCLUIDO"
    assert corpo["erros"] == []

    dados = corpo["dados"]
    assert set(dados) == {
        "id_conversa",
        "resposta",
        "criado_em",
        "papel",
        "fontes",
        "avisos",
    }
    assert dados["resposta"] == "Bem-vindo ao CardioAssist."
    assert dados["papel"] == "assistant"
    assert dados["fontes"] == []  # N6: o Watson nao devolve fontes
    assert dados["avisos"] == [AVISO_DO_ASSISTENTE]


def test_resposta_nunca_expoe_o_session_id(
    ambiente_do_assistente: AmbienteClinico, cliente_do_watson_falso: ClienteFalso
) -> None:
    """Achado I8: o identificador exposto e o `id_conversa`, nunca o do provedor."""
    cliente_do_watson_falso.sessoes = [SESSAO_DO_WATSON]
    resposta = ambiente_do_assistente.cliente.post(
        ROTA_CHAT, json={"mensagem": "Ola"}, headers=cabecalho(ambiente_do_assistente.token)
    )

    # O **valor** da sessao nao aparece em lugar nenhum da resposta.
    assert SESSAO_DO_WATSON not in resposta.text

    # E nao existe campo de sessao no conteudo devolvido. (O termo 'session_id' aparece
    # apenas no texto de `limitacoes`, que explica justamente que ele e interno.)
    dados = resposta.json()["dados"]
    assert "session_id" not in dados
    assert "session_id_do_provedor" not in dados
    assert set(dados) == {"id_conversa", "resposta", "criado_em", "papel", "fontes", "avisos"}


def test_conversa_e_persistida_com_as_duas_mensagens(
    ambiente_do_assistente: AmbienteClinico, cliente_do_watson_falso: ClienteFalso
) -> None:
    cliente_do_watson_falso.sessoes = [SESSAO_DO_WATSON]
    cliente_do_watson_falso.textos = ["Resposta um"]
    corpo = conversar_com_o_assistente(ambiente_do_assistente, mensagem="Pergunta um")["corpo"]

    conversas = _conversas(ambiente_do_assistente)
    assert len(conversas) == 1
    assert conversas[0].id == corpo["dados"]["id_conversa"]
    assert conversas[0].id_usuario == ambiente_do_assistente.id_usuario
    assert conversas[0].canal.value == "web"

    mensagens = _mensagens(ambiente_do_assistente)
    assert [item.papel for item in mensagens] == [
        PapelDaMensagem.USUARIO,
        PapelDaMensagem.ASSISTENTE,
    ]
    assert mensagens[0].conteudo == "Pergunta um"
    assert mensagens[1].conteudo == "Resposta um"
    # A sessao do provedor fica gravada (interna) para dar continuidade ao dialogo.
    assert mensagens[1].session_id_do_provedor == SESSAO_DO_WATSON
    assert mensagens[0].session_id_do_provedor is None


def test_segundo_turno_reaproveita_a_sessao(
    ambiente_do_assistente: AmbienteClinico, cliente_do_watson_falso: ClienteFalso
) -> None:
    cliente_do_watson_falso.sessoes = [SESSAO_DO_WATSON]
    cliente_do_watson_falso.textos = ["Primeira", "Segunda"]
    primeira = conversar_com_o_assistente(ambiente_do_assistente, mensagem="um")["corpo"]

    # Se o backend tentasse abrir sessao nova, o roteiro abaixo seria consumido.
    cliente_do_watson_falso.sessoes = ["sessao-nao-deveria-ser-criada"]
    segunda = conversar_com_o_assistente(
        ambiente_do_assistente,
        mensagem="dois",
        id_conversa=primeira["dados"]["id_conversa"],
    )["corpo"]

    assert segunda["dados"]["id_conversa"] == primeira["dados"]["id_conversa"]
    assert segunda["dados"]["resposta"] == "Segunda"
    assert cliente_do_watson_falso.sessoes_criadas == 1
    assert cliente_do_watson_falso.mensagens_enviadas[-1]["session_id"] == SESSAO_DO_WATSON
    assert len(_conversas(ambiente_do_assistente)) == 1
    assert len(_mensagens(ambiente_do_assistente)) == 4


def test_avisos_e_limitacoes_nunca_vazios(ambiente_do_assistente: AmbienteClinico) -> None:
    corpo = conversar_com_o_assistente(ambiente_do_assistente)["corpo"]

    assert AVISO_DO_ASSISTENTE in corpo["avisos"]
    assert corpo["limitacoes"] == list(LIMITACOES_DO_ASSISTENTE)
    assert any("fontes" in item for item in corpo["limitacoes"])


def test_auditoria_apenas_na_abertura_da_conversa(
    ambiente_do_assistente: AmbienteClinico, cliente_do_watson_falso: ClienteFalso
) -> None:
    """Uma conversa tem dezenas de turnos: auditar cada um encheria a trilha sem valor."""
    cliente_do_watson_falso.textos = ["a", "b"]
    primeira = conversar_com_o_assistente(ambiente_do_assistente, mensagem="um")["corpo"]
    conversar_com_o_assistente(
        ambiente_do_assistente, mensagem="dois", id_conversa=primeira["dados"]["id_conversa"]
    )

    eventos = _auditorias(ambiente_do_assistente, ACAO_ABRIR_CONVERSA)
    assert len(eventos) == 1
    assert eventos[0].id_entidade == primeira["dados"]["id_conversa"]
    assert eventos[0].detalhe_json == {"canal": "web", "provedor": "watson"}
    # O conteudo da conversa nao entra na trilha.
    assert "um" not in str(eventos[0].detalhe_json)


# --------------------------------------------------------------------------- #
# POST /chat — falhas
# --------------------------------------------------------------------------- #


def test_sem_watson_responde_pelo_provedor_local(ambiente_sem_watson: AmbienteClinico) -> None:
    """Sem Watson configurado, quem responde e o provedor local — mesmo contrato.

    O cliente nao percebe diferenca: a resposta traz `id_conversa`, `resposta`, `papel`
    e `fontes`, exatamente como a do provedor externo.
    """
    resultado = conversar_com_o_assistente(
        ambiente_sem_watson, mensagem="Estou com dor no peito e falta de ar"
    )

    assert resultado["status_code"] == 200
    dados = resultado["corpo"]["dados"]
    assert dados["papel"] == "assistant"
    assert dados["fontes"] == []  # N6: nunca ha fontes
    assert dados["resposta"].strip()
    # Sinal de alerta tem de encaminhar para atendimento de emergencia.
    assert "192" in dados["resposta"]


def test_turno_do_provedor_local_e_persistido(ambiente_sem_watson: AmbienteClinico) -> None:
    """O historico conta a conversa: os dois turnos ficam gravados."""
    resultado = conversar_com_o_assistente(ambiente_sem_watson, mensagem="O que voce faz?")

    assert resultado["status_code"] == 200
    assert len(_conversas(ambiente_sem_watson)) == 1

    mensagens = _mensagens(ambiente_sem_watson)
    assert [m.papel.value for m in mensagens] == ["user", "assistant"]
    # O provedor local e stateless: nao existe sessao remota a guardar (I8).
    assert mensagens[1].session_id_do_provedor is None


def test_provedor_local_e_registrado_na_auditoria(ambiente_sem_watson: AmbienteClinico) -> None:
    """A trilha registra QUAL provedor atendeu — sem o conteudo da conversa."""
    conversar_com_o_assistente(ambiente_sem_watson)

    eventos = _auditorias(ambiente_sem_watson, ACAO_ABRIR_CONVERSA)
    assert len(eventos) == 1
    assert eventos[0].detalhe_json == {"canal": "web", "provedor": "local"}


def test_conversa_inexistente_devolve_404(ambiente_do_assistente: AmbienteClinico) -> None:
    resultado = conversar_com_o_assistente(
        ambiente_do_assistente, id_conversa="conversa-que-nao-existe"
    )

    assert resultado["status_code"] == 404
    assert resultado["corpo"]["erros"][0]["codigo"] == "NAO_ENCONTRADO"
    assert resultado["corpo"]["erros"][0]["campo"] == "id_conversa"


def test_falha_de_autenticacao_no_watson_devolve_502(
    ambiente_do_assistente: AmbienteClinico, cliente_do_watson_falso: ClienteFalso
) -> None:
    """Credencial do provedor invalida -> 502, **nao** 401/403.

    O 401/403 e reservado a autenticacao **do usuario** no backend; devolver 401 aqui
    faria um cliente bem-comportado encerrar a sessao do usuario por um problema do
    provedor. O codigo distingue os dois casos (``FALHA_DE_AUTENTICACAO_EXTERNA``).
    """
    cliente_do_watson_falso.falhas = [ErroDoSdk(401, "invalid api key")]
    resultado = conversar_com_o_assistente(ambiente_do_assistente)

    assert resultado["status_code"] == 502
    assert resultado["corpo"]["erros"][0]["codigo"] == "FALHA_DE_AUTENTICACAO_EXTERNA"


def test_cota_excedida_devolve_429(
    ambiente_do_assistente: AmbienteClinico, cliente_do_watson_falso: ClienteFalso
) -> None:
    cliente_do_watson_falso.falhas = [ErroDoSdk(429, "quota exceeded")]
    resultado = conversar_com_o_assistente(ambiente_do_assistente)

    assert resultado["status_code"] == 429
    assert resultado["corpo"]["erros"][0]["codigo"] == "COTA_EXCEDIDA"


def test_timeout_do_watson_devolve_504(
    ambiente_do_assistente: AmbienteClinico, cliente_do_watson_falso: ClienteFalso
) -> None:
    cliente_do_watson_falso.falhas = [ErroDoSdk(504, "gateway timeout")]
    resultado = conversar_com_o_assistente(ambiente_do_assistente)

    assert resultado["status_code"] == 504
    assert resultado["corpo"]["erros"][0]["codigo"] == "TIMEOUT_EXTERNO"


def test_turno_falho_fica_no_historico(
    ambiente_do_assistente: AmbienteClinico, cliente_do_watson_falso: ClienteFalso
) -> None:
    """O historico conta o que aconteceu: a pergunta e o texto que o usuario viu."""
    cliente_do_watson_falso.falhas = [ErroDoSdk(500, "Internal Server Error do Watson")]
    corpo = conversar_com_o_assistente(ambiente_do_assistente, mensagem="Pergunta")["corpo"]
    assert corpo["dados"] is None

    mensagens = _mensagens(ambiente_do_assistente)
    assert [item.papel for item in mensagens] == [
        PapelDaMensagem.USUARIO,
        PapelDaMensagem.ASSISTENTE,
    ]
    assert mensagens[0].conteudo == "Pergunta"
    # O texto amigavel e o que o usuario viu; o detalhe tecnico fica interno em `erro`.
    assert mensagens[1].conteudo == "O Watson Assistant respondeu com um erro."
    assert mensagens[1].erro == "Internal Server Error do Watson"
    assert mensagens[1].session_id_do_provedor is None


def test_mensagem_vazia_devolve_422(ambiente_do_assistente: AmbienteClinico) -> None:
    resultado = conversar_com_o_assistente(ambiente_do_assistente, mensagem="")
    assert resultado["status_code"] == 422
    assert resultado["corpo"]["erros"][0]["codigo"] == "CONTRATO_VIOLADO"


def test_mensagem_muito_longa_devolve_422(ambiente_do_assistente: AmbienteClinico) -> None:
    resultado = conversar_com_o_assistente(ambiente_do_assistente, mensagem="x" * 2001)
    assert resultado["status_code"] == 422


def test_cliente_nao_pode_escolher_a_sessao_do_provedor(
    ambiente_do_assistente: AmbienteClinico,
) -> None:
    """Achado I8: o cliente nao envia `session_id` — o campo e recusado pelo contrato."""
    resposta = ambiente_do_assistente.cliente.post(
        ROTA_CHAT,
        json={"mensagem": "Ola", "session_id": "sessao-do-cliente"},
        headers=cabecalho(ambiente_do_assistente.token),
    )
    assert resposta.status_code == 422


# --------------------------------------------------------------------------- #
# RBAC
# --------------------------------------------------------------------------- #


def test_chat_exige_autenticacao(ambiente_do_assistente: AmbienteClinico) -> None:
    resposta = ambiente_do_assistente.cliente.post(ROTA_CHAT, json={"mensagem": "Ola"})
    assert resposta.status_code == 401


def test_chat_permitido_para_operador_e_medico(ambiente_do_assistente: AmbienteClinico) -> None:
    for papel in (PapelDoUsuario.OPERADOR, PapelDoUsuario.MEDICO):
        token = token_com_papel(ambiente_do_assistente, papel)
        resultado = conversar_com_o_assistente(ambiente_do_assistente, token=token)
        assert resultado["status_code"] == 200, papel


def test_chat_negado_para_admin(ambiente_do_assistente: AmbienteClinico) -> None:
    """O contrato §8 lista `OPERADOR` | `MEDICO` — `ADMIN` nao esta entre eles."""
    token = token_com_papel(ambiente_do_assistente, PapelDoUsuario.ADMIN)
    resultado = conversar_com_o_assistente(ambiente_do_assistente, token=token)

    assert resultado["status_code"] == 403
    assert resultado["corpo"]["erros"][0]["codigo"] == "NAO_AUTORIZADO"


# --------------------------------------------------------------------------- #
# GET /conversas/{id_conversa}
# --------------------------------------------------------------------------- #


def test_historico_devolve_as_mensagens_em_ordem(
    ambiente_do_assistente: AmbienteClinico, cliente_do_watson_falso: ClienteFalso
) -> None:
    cliente_do_watson_falso.textos = ["Resposta"]
    corpo = conversar_com_o_assistente(ambiente_do_assistente, mensagem="Pergunta")["corpo"]
    id_conversa = corpo["dados"]["id_conversa"]

    resposta = ambiente_do_assistente.cliente.get(
        f"{ROTA_CONVERSA}/{id_conversa}", headers=cabecalho(ambiente_do_assistente.token)
    )
    assert resposta.status_code == 200
    envelope = resposta.json()
    assert envelope["id_execucao"] == id_conversa

    itens = envelope["dados"]
    assert len(itens) == 2
    assert [item["papel"] for item in itens] == ["user", "assistant"]
    assert itens[0]["conteudo"] == "Pergunta"
    assert itens[1]["conteudo"] == "Resposta"
    assert all(item["criado_em"] for item in itens)
    assert itens[0]["criado_em"] <= itens[1]["criado_em"]


def test_historico_nao_expoe_a_sessao_nem_o_erro(
    ambiente_do_assistente: AmbienteClinico, cliente_do_watson_falso: ClienteFalso
) -> None:
    """🔒 `session_id_do_provedor` e o detalhe tecnico de falhas ficam internos."""
    cliente_do_watson_falso.sessoes = [SESSAO_DO_WATSON]
    cliente_do_watson_falso.falhas = [ErroDoSdk(500, "detalhe-tecnico-do-provedor")]
    conversar_com_o_assistente(ambiente_do_assistente)
    id_conversa = _conversas(ambiente_do_assistente)[0].id

    resposta = ambiente_do_assistente.cliente.get(
        f"{ROTA_CONVERSA}/{id_conversa}", headers=cabecalho(ambiente_do_assistente.token)
    )
    assert SESSAO_DO_WATSON not in resposta.text
    assert "detalhe-tecnico-do-provedor" not in resposta.text

    itens = resposta.json()["dados"]
    assert set(itens[0]) == {"id_mensagem", "papel", "conteudo", "criado_em"}


def test_historico_traz_o_contexto_da_conversa_em_metadados(
    ambiente_do_assistente: AmbienteClinico,
) -> None:
    id_conversa = conversar_com_o_assistente(ambiente_do_assistente)["corpo"]["dados"][
        "id_conversa"
    ]
    metadados = ambiente_do_assistente.cliente.get(
        f"{ROTA_CONVERSA}/{id_conversa}", headers=cabecalho(ambiente_do_assistente.token)
    ).json()["metadados"]

    assert metadados["id_conversa"] == id_conversa
    assert metadados["canal"] == "web"
    assert metadados["id_usuario"] == ambiente_do_assistente.id_usuario
    assert metadados["encerrada_em"] is None
    assert metadados["iniciada_em"]


def test_historico_de_conversa_inexistente_devolve_404(
    ambiente_do_assistente: AmbienteClinico,
) -> None:
    resposta = ambiente_do_assistente.cliente.get(
        f"{ROTA_CONVERSA}/nao-existe", headers=cabecalho(ambiente_do_assistente.token)
    )
    assert resposta.status_code == 404
    assert resposta.json()["erros"][0]["campo"] == "id_conversa"


def test_historico_exige_autenticacao(ambiente_do_assistente: AmbienteClinico) -> None:
    assert ambiente_do_assistente.cliente.get(f"{ROTA_CONVERSA}/qualquer").status_code == 401


def test_historico_negado_para_admin(ambiente_do_assistente: AmbienteClinico) -> None:
    id_conversa = conversar_com_o_assistente(ambiente_do_assistente)["corpo"]["dados"][
        "id_conversa"
    ]
    token = token_com_papel(ambiente_do_assistente, PapelDoUsuario.ADMIN)

    resposta = ambiente_do_assistente.cliente.get(
        f"{ROTA_CONVERSA}/{id_conversa}", headers=cabecalho(token)
    )
    assert resposta.status_code == 403