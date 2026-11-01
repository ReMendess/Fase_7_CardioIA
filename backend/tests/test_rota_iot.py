"""Testes das rotas de telemetria IoT (``app/rotas/iot.py``).

Cobrem a ingestao (``POST /iot/leituras``), o historico (``GET /iot/leituras``), as duas
formas de autenticacao (chave de dispositivo e papel ``OPERADOR``) e a traducao das regras
da Fase 3 para o envelope.
"""

from __future__ import annotations

from sqlalchemy import select

from app.dados.enums import PapelDoUsuario
from app.dados.modelos import EventoDeAuditoria, Monitoramento
from app.regras_iot import ALERTA_DE_FEBRE, ALERTA_DE_IMOBILIDADE, ALERTA_DE_TAQUICARDIA
from app.rotas.iot import LIMITACAO_DA_TELEMETRIA
from tests.conftest import (
    AmbienteIoT,
    cabecalho,
    cabecalho_de_dispositivo,
    ingerir_leitura,
)

ROTA = "/api/v1/iot/leituras"
ACAO_ALERTA = "alerta_de_telemetria"


def _leituras_no_banco(ambiente: AmbienteIoT) -> list[Monitoramento]:
    with ambiente.fabrica_de_sessoes() as sessao:
        return list(sessao.scalars(select(Monitoramento)))


def _auditorias(ambiente: AmbienteIoT) -> list[EventoDeAuditoria]:
    with ambiente.fabrica_de_sessoes() as sessao:
        return list(
            sessao.scalars(
                select(EventoDeAuditoria).where(EventoDeAuditoria.acao == ACAO_ALERTA)
            )
        )


def _operador(ambiente: AmbienteIoT) -> str:
    return ambiente.token(PapelDoUsuario.OPERADOR)


# --------------------------------------------------------------------------- #
# POST /iot/leituras — caminho feliz
# --------------------------------------------------------------------------- #


def test_ingere_leitura_sem_alerta(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(
        ambiente_iot, temperatura=36.5, bpm=80, movimento=True, token=_operador(ambiente_iot)
    )

    assert resultado["status_code"] == 201
    corpo = resultado["corpo"]
    assert corpo["status"] == "CONCLUIDO"
    assert corpo["erros"] == []
    assert corpo["avisos"] == []

    dados = corpo["dados"]
    assert set(dados) == {
        "id_leitura",
        "id_dispositivo",
        "recebido_em",
        "origem_transporte",
        "temperatura",
        "bpm",
        "umidade",
        "luminosidade",
        "movimento",
        "payload_json",
    }
    assert dados["id_dispositivo"] == "esp32-sala-1"
    assert dados["origem_transporte"] == "rest"
    assert dados["temperatura"] == 36.5
    assert corpo["id_execucao"] == dados["id_leitura"]


def test_leitura_e_persistida(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(
        ambiente_iot,
        temperatura=37.2,
        bpm=95,
        umidade=45.0,
        luminosidade=300.0,
        movimento=True,
        token=_operador(ambiente_iot),
    )

    registros = _leituras_no_banco(ambiente_iot)
    assert len(registros) == 1
    registro = registros[0]
    assert registro.id == resultado["corpo"]["dados"]["id_leitura"]
    assert registro.id_dispositivo == "esp32-sala-1"
    assert registro.temperatura == 37.2
    assert registro.bpm == 95
    assert registro.umidade == 45.0
    assert registro.luminosidade == 300.0
    assert registro.movimento is True
    assert registro.recebido_em is not None


def test_recebido_em_e_carimbado_pelo_backend(ambiente_iot: AmbienteIoT) -> None:
    """O firmware nao envia timestamp: o cliente nem pode escolher o instante."""
    resultado = ingerir_leitura(
        ambiente_iot, bpm=80, token=_operador(ambiente_iot), recebido_em="2020-01-01T00:00:00Z"
    )
    # `recebido_em` nao esta no DTO: campo extra e recusado (contrato fechado).
    assert resultado["status_code"] == 422


def test_payload_bruto_e_preservado(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(
        ambiente_iot,
        bpm=80,
        payload_json={"origem": "wokwi", "rssi": -62},
        token=_operador(ambiente_iot),
    )
    assert resultado["corpo"]["dados"]["payload_json"] == {"origem": "wokwi", "rssi": -62}


def test_limitacao_da_telemetria_sempre_presente(ambiente_iot: AmbienteIoT) -> None:
    """Decisao D4 declarada em toda resposta: a leitura nao alimenta o modelo."""
    resultado = ingerir_leitura(ambiente_iot, bpm=80, token=_operador(ambiente_iot))
    assert resultado["corpo"]["limitacoes"] == [LIMITACAO_DA_TELEMETRIA]
    assert "NAO alimenta o modelo" in resultado["corpo"]["limitacoes"][0]


# --------------------------------------------------------------------------- #
# POST /iot/leituras — alertas das regras da Fase 3
# --------------------------------------------------------------------------- #


def test_febre_vira_ressalva_com_aviso(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(
        ambiente_iot, temperatura=39.0, bpm=80, token=_operador(ambiente_iot)
    )

    assert resultado["status_code"] == 201
    corpo = resultado["corpo"]
    assert corpo["status"] == "CONCLUIDO_COM_RESSALVAS"
    assert corpo["avisos"] == [ALERTA_DE_FEBRE]
    assert corpo["erros"] == []


def test_taquicardia_vira_ressalva(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(
        ambiente_iot, temperatura=36.5, bpm=130, token=_operador(ambiente_iot)
    )
    assert resultado["corpo"]["status"] == "CONCLUIDO_COM_RESSALVAS"
    assert resultado["corpo"]["avisos"] == [ALERTA_DE_TAQUICARDIA]


def test_imobilidade_vira_ressalva(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(
        ambiente_iot, temperatura=36.5, bpm=80, movimento=False, token=_operador(ambiente_iot)
    )
    assert resultado["corpo"]["status"] == "CONCLUIDO_COM_RESSALVAS"
    assert resultado["corpo"]["avisos"] == [ALERTA_DE_IMOBILIDADE]


def test_prioridade_da_cadeia_aparece_no_aviso(ambiente_iot: AmbienteIoT) -> None:
    """Com as tres condicoes verdadeiras, a resposta traz **apenas** a de maior prioridade."""
    resultado = ingerir_leitura(
        ambiente_iot,
        temperatura=39.0,
        bpm=150,
        movimento=False,
        token=_operador(ambiente_iot),
    )
    assert resultado["corpo"]["avisos"] == [ALERTA_DE_FEBRE]


def test_limiar_exato_nao_gera_alerta(ambiente_iot: AmbienteIoT) -> None:
    """``> 38`` e ``> 120``: os valores exatos sao normais (como na Fase 3)."""
    resultado = ingerir_leitura(
        ambiente_iot, temperatura=38.0, bpm=120, token=_operador(ambiente_iot)
    )
    assert resultado["corpo"]["status"] == "CONCLUIDO"
    assert resultado["corpo"]["avisos"] == []


def test_apenas_bpm_e_aceito(ambiente_iot: AmbienteIoT) -> None:
    """A origem respondia 500 sem `temperatura`; aqui a leitura e aceita (divergencia declarada)."""
    resultado = ingerir_leitura(ambiente_iot, bpm=130, token=_operador(ambiente_iot))
    assert resultado["status_code"] == 201
    assert resultado["corpo"]["avisos"] == [ALERTA_DE_TAQUICARDIA]


def test_alerta_fica_na_trilha_de_auditoria(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(
        ambiente_iot, temperatura=39.0, token=_operador(ambiente_iot)
    )
    id_leitura = resultado["corpo"]["dados"]["id_leitura"]

    eventos = _auditorias(ambiente_iot)
    assert len(eventos) == 1
    assert eventos[0].id_entidade == id_leitura
    assert eventos[0].detalhe_json == {
        "alerta": ALERTA_DE_FEBRE,
        "id_dispositivo": "esp32-sala-1",
        "autenticacao": "usuario",
    }


def test_leitura_normal_nao_polui_a_trilha(ambiente_iot: AmbienteIoT) -> None:
    """Telemetria chega em alta frequencia: so o alerta vai para a auditoria."""
    for _ in range(3):
        ingerir_leitura(ambiente_iot, bpm=80, token=_operador(ambiente_iot))
    assert _auditorias(ambiente_iot) == []
    assert len(_leituras_no_banco(ambiente_iot)) == 3


def test_alerta_de_dispositivo_registra_a_autenticacao(ambiente_iot: AmbienteIoT) -> None:
    ingerir_leitura(ambiente_iot, temperatura=39.0, chave=ambiente_iot.chave)

    eventos = _auditorias(ambiente_iot)
    assert eventos[0].detalhe_json is not None
    assert eventos[0].detalhe_json["autenticacao"] == "dispositivo"
    assert eventos[0].id_usuario is None


# --------------------------------------------------------------------------- #
# POST /iot/leituras — autenticacao (chave de dispositivo x papel)
# --------------------------------------------------------------------------- #


def test_chave_de_dispositivo_valida_e_aceita(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(ambiente_iot, bpm=80, chave=ambiente_iot.chave)
    assert resultado["status_code"] == 201


def test_chave_de_dispositivo_invalida_devolve_401(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(ambiente_iot, bpm=80, chave="chave-errada")
    assert resultado["status_code"] == 401
    assert resultado["corpo"]["erros"][0]["codigo"] == "NAO_AUTENTICADO"
    assert _leituras_no_banco(ambiente_iot) == []


def test_chave_vazia_cai_na_autenticacao_por_usuario(ambiente_iot: AmbienteIoT) -> None:
    """Sem cabecalho, o caminho e o RBAC normal — nao uma chave vazia."""
    resposta = ambiente_iot.cliente.post(
        ROTA,
        json={"id_dispositivo": "d1", "origem_transporte": "rest", "bpm": 80},
        headers=cabecalho_de_dispositivo(""),
    )
    assert resposta.status_code == 401
    assert resposta.json()["erros"][0]["codigo"] == "NAO_AUTENTICADO"


def test_chave_sem_configuracao_no_servidor_devolve_401(tmp_path_factory) -> None:
    """Servidor sem ``IOT_DEVICE_KEY`` recusa o caminho da chave em vez de aceitar tudo."""
    from fastapi.testclient import TestClient

    from app.main import criar_app
    from tests.conftest import _configuracao_base

    pasta = tmp_path_factory.mktemp("fase7_iot_sem_chave")
    app = criar_app(_configuracao_base(str(pasta)))

    with TestClient(app) as cliente:
        resposta = cliente.post(
            ROTA,
            json={"id_dispositivo": "d1", "origem_transporte": "rest", "bpm": 80},
            headers=cabecalho_de_dispositivo("qualquer-coisa"),
        )

    assert resposta.status_code == 401
    assert resposta.json()["erros"][0]["codigo"] == "NAO_AUTENTICADO"
    assert "nao tem chave de dispositivo configurada" in resposta.json()["erros"][0]["mensagem"]


def test_ingestao_sem_autenticacao_devolve_401(ambiente_iot: AmbienteIoT) -> None:
    resposta = ambiente_iot.cliente.post(
        ROTA, json={"id_dispositivo": "d1", "origem_transporte": "rest", "bpm": 80}
    )
    assert resposta.status_code == 401


def test_ingestao_aceita_operador(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(
        ambiente_iot, bpm=80, token=ambiente_iot.token(PapelDoUsuario.OPERADOR)
    )
    assert resultado["status_code"] == 201


def test_ingestao_negada_para_medico_e_admin(ambiente_iot: AmbienteIoT) -> None:
    """A ingestao de telemetria nao e ato clinico: exige OPERADOR ou dispositivo."""
    for papel in (PapelDoUsuario.MEDICO, PapelDoUsuario.ADMIN):
        resultado = ingerir_leitura(ambiente_iot, bpm=80, token=ambiente_iot.token(papel))
        assert resultado["status_code"] == 403, papel
        assert resultado["corpo"]["erros"][0]["codigo"] == "NAO_AUTORIZADO"


def test_chave_tem_prioridade_sobre_token_invalido(ambiente_iot: AmbienteIoT) -> None:
    """Um dispositivo com chave valida nao precisa (nem envia) Bearer token."""
    resposta = ambiente_iot.cliente.post(
        ROTA,
        json={"id_dispositivo": "d1", "origem_transporte": "mqtt", "bpm": 80},
        headers={**cabecalho_de_dispositivo(ambiente_iot.chave), "Authorization": "Bearer lixo"},
    )
    assert resposta.status_code == 201


# --------------------------------------------------------------------------- #
# POST /iot/leituras — validacao do contrato
# --------------------------------------------------------------------------- #


def test_leitura_sem_sinal_vital_devolve_422(ambiente_iot: AmbienteIoT) -> None:
    """O CHECK do banco tambem exige um sinal vital; aqui a falha vem antes, com o motivo."""
    resultado = ingerir_leitura(
        ambiente_iot, movimento=True, umidade=45.0, token=_operador(ambiente_iot)
    )
    assert resultado["status_code"] == 422
    assert resultado["corpo"]["erros"][0]["codigo"] == "CONTRATO_VIOLADO"
    assert _leituras_no_banco(ambiente_iot) == []


def test_campo_desconhecido_devolve_422(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(
        ambiente_iot, bpm=80, token=_operador(ambiente_iot), pressao=120
    )
    assert resultado["status_code"] == 422


def test_booleano_em_sinal_vital_devolve_422(ambiente_iot: AmbienteIoT) -> None:
    """Sem a guarda, o pydantic converteria ``true`` em ``1`` e o alerta mudaria de sentido."""
    resultado = ingerir_leitura(
        ambiente_iot, temperatura=True, bpm=80, token=_operador(ambiente_iot)
    )
    assert resultado["status_code"] == 422
    assert "booleano" in resultado["corpo"]["erros"][0]["detalhe"]


def test_id_dispositivo_vazio_devolve_422(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(
        ambiente_iot, dispositivo="   ", bpm=80, token=_operador(ambiente_iot)
    )
    assert resultado["status_code"] == 422


def test_id_dispositivo_muito_longo_devolve_422(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(
        ambiente_iot, dispositivo="d" * 65, bpm=80, token=_operador(ambiente_iot)
    )
    assert resultado["status_code"] == 422


def test_origem_de_transporte_invalida_devolve_422(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(
        ambiente_iot, bpm=80, origem_transporte="pombo", token=_operador(ambiente_iot)
    )
    assert resultado["status_code"] == 422


def test_id_dispositivo_e_normalizado(ambiente_iot: AmbienteIoT) -> None:
    resultado = ingerir_leitura(
        ambiente_iot, dispositivo="  esp32-sala-9  ", bpm=80, token=_operador(ambiente_iot)
    )
    assert resultado["corpo"]["dados"]["id_dispositivo"] == "esp32-sala-9"


# --------------------------------------------------------------------------- #
# GET /iot/leituras
# --------------------------------------------------------------------------- #


def test_historico_vazio(ambiente_iot: AmbienteIoT) -> None:
    resposta = ambiente_iot.cliente.get(
        ROTA, headers=cabecalho(_operador(ambiente_iot))
    )
    assert resposta.status_code == 200
    assert resposta.json()["dados"] == []


def test_historico_lista_leituras(ambiente_iot: AmbienteIoT) -> None:
    ingerir_leitura(
        ambiente_iot, temperatura=36.5, bpm=80, token=_operador(ambiente_iot)
    )
    ingerir_leitura(
        ambiente_iot,
        temperatura=39.0,
        bpm=80,
        token=_operador(ambiente_iot),
        dispositivo="esp32-sala-2",
    )

    resposta = ambiente_iot.cliente.get(ROTA, headers=cabecalho(_operador(ambiente_iot)))
    itens = resposta.json()["dados"]
    assert len(itens) == 2
    assert {item["id_dispositivo"] for item in itens} == {"esp32-sala-1", "esp32-sala-2"}
    assert all(item["recebido_em"] for item in itens)
    # O alerta nao e persistido: nao ha campo para ele no contrato.
    assert all("alerta" not in item for item in itens)


def test_historico_mais_recentes_primeiro(ambiente_iot: AmbienteIoT) -> None:
    for indice in range(3):
        ingerir_leitura(
            ambiente_iot,
            bpm=80 + indice,
            token=_operador(ambiente_iot),
            dispositivo=f"dispositivo-{indice}",
        )

    resposta = ambiente_iot.cliente.get(ROTA, headers=cabecalho(_operador(ambiente_iot)))
    instantes = [item["recebido_em"] for item in resposta.json()["dados"]]
    assert instantes == sorted(instantes, reverse=True)


def test_historico_filtra_por_dispositivo(ambiente_iot: AmbienteIoT) -> None:
    ingerir_leitura(ambiente_iot, bpm=80, token=_operador(ambiente_iot), dispositivo="alvo")
    ingerir_leitura(ambiente_iot, bpm=80, token=_operador(ambiente_iot), dispositivo="outro")

    resposta = ambiente_iot.cliente.get(
        ROTA, params={"id_dispositivo": "alvo"}, headers=cabecalho(_operador(ambiente_iot))
    )
    itens = resposta.json()["dados"]
    assert len(itens) == 1
    assert itens[0]["id_dispositivo"] == "alvo"


def test_historico_respeita_paginacao(ambiente_iot: AmbienteIoT) -> None:
    for indice in range(5):
        ingerir_leitura(
            ambiente_iot, bpm=80, token=_operador(ambiente_iot), dispositivo=f"d{indice}"
        )

    primeira = ambiente_iot.cliente.get(
        ROTA,
        params={"limite": 2, "deslocamento": 0},
        headers=cabecalho(_operador(ambiente_iot)),
    )
    segunda = ambiente_iot.cliente.get(
        ROTA,
        params={"limite": 2, "deslocamento": 2},
        headers=cabecalho(_operador(ambiente_iot)),
    )
    ids_primeira = {item["id_leitura"] for item in primeira.json()["dados"]}
    ids_segunda = {item["id_leitura"] for item in segunda.json()["dados"]}
    assert len(ids_primeira) == 2
    assert len(ids_segunda) == 2
    assert ids_primeira.isdisjoint(ids_segunda)


def test_historico_rejeita_paginacao_invalida(ambiente_iot: AmbienteIoT) -> None:
    for parametros in ({"limite": 0}, {"limite": 999}, {"deslocamento": -1}):
        resposta = ambiente_iot.cliente.get(
            ROTA, params=parametros, headers=cabecalho(_operador(ambiente_iot))
        )
        assert resposta.status_code == 422, parametros


def test_historico_declara_a_limitacao(ambiente_iot: AmbienteIoT) -> None:
    resposta = ambiente_iot.cliente.get(ROTA, headers=cabecalho(_operador(ambiente_iot)))
    assert resposta.json()["limitacoes"] == [LIMITACAO_DA_TELEMETRIA]


def test_historico_permitido_para_medico(ambiente_iot: AmbienteIoT) -> None:
    """O medico precisa ver a telemetria (dado de monitoramento), mesmo sem ingerir."""
    ingerir_leitura(ambiente_iot, bpm=80, token=_operador(ambiente_iot))

    resposta = ambiente_iot.cliente.get(
        ROTA, headers=cabecalho(ambiente_iot.token(PapelDoUsuario.MEDICO))
    )
    assert resposta.status_code == 200
    assert len(resposta.json()["dados"]) == 1


def test_historico_negado_para_admin(ambiente_iot: AmbienteIoT) -> None:
    """``ADMIN`` administra o sistema; nao le dado de monitoramento de paciente."""
    resposta = ambiente_iot.cliente.get(
        ROTA, headers=cabecalho(ambiente_iot.token(PapelDoUsuario.ADMIN))
    )
    assert resposta.status_code == 403


def test_historico_exige_autenticacao(ambiente_iot: AmbienteIoT) -> None:
    assert ambiente_iot.cliente.get(ROTA).status_code == 401


def test_historico_nao_aceita_chave_de_dispositivo(ambiente_iot: AmbienteIoT) -> None:
    """A chave de dispositivo so serve para **ingerir**; ler historico exige usuario."""
    resposta = ambiente_iot.cliente.get(
        ROTA, headers=cabecalho_de_dispositivo(ambiente_iot.chave)
    )
    assert resposta.status_code == 401