"""Testes das rotas de avaliacao de risco (``app/rotas/avaliacoes.py``).

Exercitam o **pipeline real da Fase 6** em modo ``simulado``: o SDK, os handoffs e as
tools rodam de verdade; apenas as decisoes de rota do LLM sao substituidas por um roteiro
deterministico. Nenhuma chamada a API externa.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.dados.enums import ModoDoPipeline, OrigemDosDados, PapelDoUsuario
from app.dados.modelos import AvaliacaoDeRisco, EventoDeAuditoria
from app.integracao.fase_6 import ModulosDaFase6
from app.integracao.mapeador import AVISOS_DE_CONFIABILIDADE
from tests.conftest import (
    FEATURES_DO_PACIENTE_DA_AULA,
    AmbienteClinico,
    avaliar_paciente,
    cabecalho,
    criar_paciente,
    token_com_papel,
)

ROTA = "/api/v1/avaliacoes"


def _avaliacoes_no_banco(ambiente: AmbienteClinico) -> list[AvaliacaoDeRisco]:
    with ambiente.fabrica_de_sessoes() as sessao:
        return list(sessao.scalars(select(AvaliacaoDeRisco)))


def _acao_auditada(ambiente: AmbienteClinico, acao: str) -> list[EventoDeAuditoria]:
    with ambiente.fabrica_de_sessoes() as sessao:
        return list(
            sessao.scalars(select(EventoDeAuditoria).where(EventoDeAuditoria.acao == acao))
        )


# --------------------------------------------------------------------------- #
# POST /avaliacoes — caminho feliz
# --------------------------------------------------------------------------- #


def test_avaliacao_concluida_devolve_o_contrato_da_fase_6(
    ambiente_clinico: AmbienteClinico,
) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    resultado = avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)

    assert resultado["status_code"] == 200
    corpo = resultado["corpo"]
    assert corpo["status"] == "CONCLUIDO"
    assert corpo["erros"] == []

    # `dados` e a RespostaDaExecucao integral da Fase 6 (nao um resumo).
    dados = corpo["dados"]
    assert dados["status"] == "CONCLUIDO"
    assert dados["modo"] == "simulado"
    assert dados["diagnostico"]["modelo_utilizado"] == "Random Forest"
    assert dados["diagnostico"]["probabilidade_risco"] == pytest.approx(0.99, abs=0.02)
    assert dados["diagnostico"]["pico_risco_previsto"] == 1
    assert len(dados["protocolos"]) > 0
    assert len(dados["passos"]) > 0
    assert dados["agente_final"] == "Planejador de Resposta"


def test_id_execucao_do_envelope_e_o_mesmo_da_fase_6(
    ambiente_clinico: AmbienteClinico,
) -> None:
    """N2: o `id_execucao` e a chave de correlacao entre API, banco e pipeline."""
    id_paciente = criar_paciente(ambiente_clinico)
    corpo = avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)[
        "corpo"
    ]

    assert corpo["id_execucao"] == corpo["dados"]["id_execucao"]
    registrados = {item.id_execucao for item in _avaliacoes_no_banco(ambiente_clinico)}
    assert corpo["id_execucao"] in registrados


def test_avisos_incluem_o_modo_simulado_e_os_achados_a3_a4(
    ambiente_clinico: AmbienteClinico,
) -> None:
    """N9 + contrato §8.1: `avisos` nunca vazio em resposta de decisao automatizada."""
    id_paciente = criar_paciente(ambiente_clinico)
    corpo = avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)[
        "corpo"
    ]

    assert any("SIMULADO" in aviso for aviso in corpo["avisos"])
    for aviso in AVISOS_DE_CONFIABILIDADE:
        assert aviso in corpo["avisos"]


def test_limitacoes_vem_da_fase_6(
    ambiente_clinico: AmbienteClinico, modulos_da_fase_6: ModulosDaFase6
) -> None:
    """N8: o texto clinico e reaproveitado, nunca reescrito no backend."""
    id_paciente = criar_paciente(ambiente_clinico)
    corpo = avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)[
        "corpo"
    ]

    assert corpo["limitacoes"] == list(modulos_da_fase_6.risk_result.LIMITACOES_PADRAO)


def test_avaliacao_persiste_o_agregado_completo(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    corpo = avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)[
        "corpo"
    ]
    contrato = corpo["dados"]

    with ambiente_clinico.fabrica_de_sessoes() as sessao:
        avaliacao = sessao.scalar(
            select(AvaliacaoDeRisco).where(
                AvaliacaoDeRisco.id_execucao == corpo["id_execucao"]
            )
        )
        assert avaliacao is not None
        assert avaliacao.id_paciente == id_paciente
        assert avaliacao.id_usuario == ambiente_clinico.id_usuario
        assert avaliacao.modo is ModoDoPipeline.SIMULADO
        assert avaliacao.origem_dos_dados is OrigemDosDados.MANUAL
        assert avaliacao.probabilidade_risco == contrato["diagnostico"]["probabilidade_risco"]
        assert avaliacao.sha256_da_base_usada is not None

        # As 10 features ficaram no estado clinico datado (resposta Q1).
        assert avaliacao.idade_media == 62.0
        assert avaliacao.temperatura == 37.5
        assert avaliacao.disponibilidade_recursos == 25.0

        # As tres tabelas-filhas foram gravadas na mesma transacao.
        assert len(avaliacao.protocolos) == len(contrato["protocolos"])
        assert len(avaliacao.indicadores) == len(contrato["indicadores"])
        assert len(avaliacao.passos) == len(contrato["passos"])

        # Contrato integral guardado para auditoria, sem reexecutar o modelo.
        assert avaliacao.resposta_json is not None
        assert avaliacao.resposta_json["id_execucao"] == corpo["id_execucao"]
        assert avaliacao.features_json is not None
        assert avaliacao.features_json["origem_dos_dados"] == "manual"


def test_origem_dos_dados_e_registrada(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    avaliar_paciente(
        ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA, origem_dos_dados="iot"
    )
    assert _avaliacoes_no_banco(ambiente_clinico)[0].origem_dos_dados is OrigemDosDados.IOT


def test_avaliacao_registra_auditoria(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    corpo = avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)[
        "corpo"
    ]

    eventos = _acao_auditada(ambiente_clinico, "avaliar_risco")
    assert len(eventos) == 1
    assert eventos[0].id_entidade == corpo["id_execucao"]
    assert eventos[0].detalhe_json == {
        "status": "CONCLUIDO",
        "modo": "simulado",
        "origem_dos_dados": "manual",
    }


# --------------------------------------------------------------------------- #
# POST /avaliacoes — falhas de contrato
# --------------------------------------------------------------------------- #


def test_avaliacao_exige_autenticacao(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    resposta = ambiente_clinico.cliente.post(
        ROTA,
        json={
            "id_paciente": id_paciente,
            "features": FEATURES_DO_PACIENTE_DA_AULA,
            "origem_dos_dados": "manual",
        },
    )
    assert resposta.status_code == 401


def test_avaliacao_exige_papel_medico(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    for papel in (PapelDoUsuario.ADMIN, PapelDoUsuario.OPERADOR):
        token = token_com_papel(ambiente_clinico, papel)
        resultado = avaliar_paciente(
            ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA, token=token
        )
        assert resultado["status_code"] == 403, papel


def test_avaliacao_de_paciente_inexistente_devolve_404(
    ambiente_clinico: AmbienteClinico,
) -> None:
    resultado = avaliar_paciente(
        ambiente_clinico, "paciente-que-nao-existe", FEATURES_DO_PACIENTE_DA_AULA
    )

    assert resultado["status_code"] == 404
    assert resultado["corpo"]["erros"][0]["codigo"] == "NAO_ENCONTRADO"


def test_avaliacao_de_paciente_inativo_devolve_409(
    ambiente_clinico: AmbienteClinico,
) -> None:
    """Inativo nao recebe avaliacao nova; 409 diz que o estado atual impede a operacao."""
    from app.dados.modelos import Paciente

    id_paciente = criar_paciente(ambiente_clinico)
    with ambiente_clinico.fabrica_de_sessoes() as sessao:
        paciente = sessao.get(Paciente, id_paciente)
        assert paciente is not None
        paciente.ativo = False
        sessao.commit()

    resultado = avaliar_paciente(
        ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA
    )
    assert resultado["status_code"] == 409
    assert resultado["corpo"]["erros"][0]["codigo"] == "CONFLITO"
    assert _avaliacoes_no_banco(ambiente_clinico) == []


def test_feature_ausente_devolve_422(ambiente_clinico: AmbienteClinico) -> None:
    """Sem defaults: se `id_paciente` vier sem as 10 features, nada e preenchido."""
    id_paciente = criar_paciente(ambiente_clinico)
    incompletas = dict(FEATURES_DO_PACIENTE_DA_AULA)
    del incompletas["spo2_media"]

    resultado = avaliar_paciente(ambiente_clinico, id_paciente, incompletas)

    assert resultado["status_code"] == 422
    assert resultado["corpo"]["erros"][0]["codigo"] == "PACIENTE_INVALIDO"
    assert "spo2_media" in resultado["corpo"]["erros"][0]["mensagem"]
    assert _avaliacoes_no_banco(ambiente_clinico) == []


def test_feature_desconhecida_devolve_422(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    extras = {**FEATURES_DO_PACIENTE_DA_AULA, "pressao_diastolica": 80.0}

    resultado = avaliar_paciente(ambiente_clinico, id_paciente, extras)
    assert resultado["status_code"] == 422
    assert resultado["corpo"]["erros"][0]["codigo"] == "PACIENTE_INVALIDO"


def test_booleano_em_feature_e_recusado(ambiente_clinico: AmbienteClinico) -> None:
    """Por que o DTO usa ``dict[str, Any]``: com ``dict[str, float]`` o pydantic
    converteria ``true`` em ``1.0`` e o booleano passaria como valor clinico."""
    id_paciente = criar_paciente(ambiente_clinico)
    invalidas: dict[str, object] = dict(FEATURES_DO_PACIENTE_DA_AULA)
    invalidas["temperatura"] = True

    resultado = avaliar_paciente(
        ambiente_clinico, id_paciente, invalidas  # type: ignore[arg-type]
    )

    assert resultado["status_code"] == 422
    assert resultado["corpo"]["erros"][0]["codigo"] == "PACIENTE_INVALIDO"
    assert resultado["corpo"]["erros"][0]["campo"] == "temperatura"


def test_valor_negativo_em_feature_e_recusado(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    invalidas = {**FEATURES_DO_PACIENTE_DA_AULA, "tempo_espera": -1.0}

    resultado = avaliar_paciente(ambiente_clinico, id_paciente, invalidas)
    assert resultado["status_code"] == 422
    assert resultado["corpo"]["erros"][0]["campo"] == "tempo_espera"


def test_origem_dos_dados_invalida_devolve_422(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    resultado = avaliar_paciente(
        ambiente_clinico,
        id_paciente,
        FEATURES_DO_PACIENTE_DA_AULA,
        origem_dos_dados="inventado",
    )
    assert resultado["status_code"] == 422
    assert resultado["corpo"]["erros"][0]["codigo"] == "CONTRATO_VIOLADO"


def test_modo_real_sem_chave_devolve_501(
    ambiente_clinico: AmbienteClinico, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M4: o modo real e explicito e falha claro — nao cai silenciosamente no simulado."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    id_paciente = criar_paciente(ambiente_clinico)

    resultado = avaliar_paciente(
        ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA, modo="real"
    )

    assert resultado["status_code"] == 501
    assert resultado["corpo"]["erros"][0]["codigo"] == "NAO_CONFIGURADO"
    assert _avaliacoes_no_banco(ambiente_clinico) == []


def test_modo_invalido_devolve_422(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    resultado = avaliar_paciente(
        ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA, modo="magico"
    )
    assert resultado["status_code"] == 422


# --------------------------------------------------------------------------- #
# Falha do pipeline: a Fase 6 devolve conteudo, nao excecao
# --------------------------------------------------------------------------- #


def _contrato_com_falha(modulos: ModulosDaFase6, motivo: str):
    """Contrato da Fase 6 com status ERRO (o validador exige ao menos um erro)."""
    return modulos.risk_result.RespostaDaExecucao(
        id_execucao=str(uuid4()),
        status=modulos.risk_result.StatusDaExecucao.ERRO,
        modo=modulos.risk_result.ModoDeExecucao.SIMULADO,
        erros=[motivo],
    )


def test_falha_do_pipeline_preserva_o_contrato_e_o_motivo(
    ambiente_clinico: AmbienteClinico,
    modulos_da_fase_6: ModulosDaFase6,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Capturar excecao **nao basta**: a Fase 6 reporta falha como conteudo.

    A resposta tem HTTP 200 (a execucao rodou e foi registrada), `status=ERRO`, o motivo
    em `erros` e o contrato integral em `dados` — a trilha explica onde quebrou.
    """
    id_paciente = criar_paciente(ambiente_clinico)
    contrato = _contrato_com_falha(modulos_da_fase_6, "falha simulada no pipeline")
    monkeypatch.setattr(
        modulos_da_fase_6.orchestrator, "executar_pipeline", lambda *_, **__: contrato
    )

    resultado = avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)

    assert resultado["status_code"] == 200
    corpo = resultado["corpo"]
    assert corpo["status"] == "ERRO"
    assert corpo["erros"][0]["mensagem"] == "falha simulada no pipeline"
    assert corpo["erros"][0]["codigo"] == "FALHA_DE_PREVISAO"
    assert corpo["dados"]["id_execucao"] == contrato.id_execucao
    assert corpo["id_execucao"] == contrato.id_execucao
    assert corpo["avisos"]  # falha tambem informa avisos e limitacoes


def test_falha_do_pipeline_e_registrada_no_historico(
    ambiente_clinico: AmbienteClinico,
    modulos_da_fase_6: ModulosDaFase6,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falha nao some: fica no banco e no historico (``erros_json`` + ``resposta_json``)."""
    id_paciente = criar_paciente(ambiente_clinico)
    contrato = _contrato_com_falha(modulos_da_fase_6, "modelo indisponivel no momento")
    monkeypatch.setattr(
        modulos_da_fase_6.orchestrator, "executar_pipeline", lambda *_, **__: contrato
    )
    avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)

    avaliacao = _avaliacoes_no_banco(ambiente_clinico)[0]
    assert avaliacao.status.value == "ERRO"
    assert avaliacao.erros_json == ["modelo indisponivel no momento"]
    assert avaliacao.probabilidade_risco is None  # nao houve diagnostico
    assert avaliacao.resposta_json is not None


# --------------------------------------------------------------------------- #
# GET /avaliacoes
# --------------------------------------------------------------------------- #


def test_lista_avaliacoes(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    corpo = avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)[
        "corpo"
    ]

    resposta = ambiente_clinico.cliente.get(ROTA, headers=cabecalho(ambiente_clinico.token))
    assert resposta.status_code == 200
    itens = resposta.json()["dados"]
    assert len(itens) == 1

    item = itens[0]
    assert item["id_execucao"] == corpo["id_execucao"]
    assert item["id_paciente"] == id_paciente
    assert item["status"] == "CONCLUIDO"
    assert item["modo"] == "simulado"
    assert item["origem_dos_dados"] == "manual"
    assert item["modelo_utilizado"] == "Random Forest"
    # O resumo nao carrega a trilha completa.
    assert "passos" not in item
    assert "resposta" not in item


def test_lista_vazia(ambiente_clinico: AmbienteClinico) -> None:
    resposta = ambiente_clinico.cliente.get(ROTA, headers=cabecalho(ambiente_clinico.token))
    assert resposta.json()["dados"] == []


def test_lista_filtra_por_paciente(ambiente_clinico: AmbienteClinico) -> None:
    primeiro = criar_paciente(ambiente_clinico, nome="Primeiro")
    segundo = criar_paciente(ambiente_clinico, nome="Segundo")
    avaliar_paciente(ambiente_clinico, primeiro, FEATURES_DO_PACIENTE_DA_AULA)
    avaliar_paciente(ambiente_clinico, segundo, FEATURES_DO_PACIENTE_DA_AULA)

    resposta = ambiente_clinico.cliente.get(
        ROTA, params={"id_paciente": primeiro}, headers=cabecalho(ambiente_clinico.token)
    )
    itens = resposta.json()["dados"]
    assert len(itens) == 1
    assert itens[0]["id_paciente"] == primeiro


def test_lista_filtra_por_status(
    ambiente_clinico: AmbienteClinico,
    modulos_da_fase_6: ModulosDaFase6,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)

    contrato = _contrato_com_falha(modulos_da_fase_6, "falha simulada")
    monkeypatch.setattr(
        modulos_da_fase_6.orchestrator, "executar_pipeline", lambda *_, **__: contrato
    )
    avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)
    monkeypatch.undo()

    concluidas = ambiente_clinico.cliente.get(
        ROTA, params={"status": "CONCLUIDO"}, headers=cabecalho(ambiente_clinico.token)
    )
    com_erro = ambiente_clinico.cliente.get(
        ROTA, params={"status": "ERRO"}, headers=cabecalho(ambiente_clinico.token)
    )
    assert len(concluidas.json()["dados"]) == 1
    assert len(com_erro.json()["dados"]) == 1
    assert com_erro.json()["dados"][0]["id_execucao"] == contrato.id_execucao


def test_lista_rejeita_status_invalido(ambiente_clinico: AmbienteClinico) -> None:
    resposta = ambiente_clinico.cliente.get(
        ROTA, params={"status": "INVENTADO"}, headers=cabecalho(ambiente_clinico.token)
    )
    assert resposta.status_code == 422


def test_lista_exige_autenticacao(ambiente_clinico: AmbienteClinico) -> None:
    assert ambiente_clinico.cliente.get(ROTA).status_code == 401


def test_lista_negada_para_operador(ambiente_clinico: AmbienteClinico) -> None:
    token = token_com_papel(ambiente_clinico, PapelDoUsuario.OPERADOR)
    assert ambiente_clinico.cliente.get(ROTA, headers=cabecalho(token)).status_code == 403


# --------------------------------------------------------------------------- #
# GET /avaliacoes/{id_execucao}
# --------------------------------------------------------------------------- #


def test_historico_devolve_o_contrato_persistido(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    corpo = avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)[
        "corpo"
    ]

    resposta = ambiente_clinico.cliente.get(
        f"{ROTA}/{corpo['id_execucao']}", headers=cabecalho(ambiente_clinico.token)
    )
    assert resposta.status_code == 200
    envelope = resposta.json()
    assert envelope["status"] == "CONCLUIDO"
    assert envelope["id_execucao"] == corpo["id_execucao"]

    dados = envelope["dados"]
    assert dados["id_usuario"] == ambiente_clinico.id_usuario
    assert dados["origem_dos_dados"] == "manual"
    assert dados["sha256_da_base_usada"]
    # O contrato devolvido e **identico** ao da execucao original.
    assert dados["resposta"] == corpo["dados"]


def test_historico_nao_reexecuta_o_modelo(
    ambiente_clinico: AmbienteClinico,
    modulos_da_fase_6: ModulosDaFase6,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decisao auditavel: o historico le o banco, nunca roda o pipeline de novo."""
    id_paciente = criar_paciente(ambiente_clinico)
    corpo = avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)[
        "corpo"
    ]

    def _explodir(*_: object, **__: object) -> None:
        raise AssertionError("o pipeline nao pode ser reexecutado ao ler o historico")

    monkeypatch.setattr(modulos_da_fase_6.orchestrator, "executar_pipeline", _explodir)

    resposta = ambiente_clinico.cliente.get(
        f"{ROTA}/{corpo['id_execucao']}", headers=cabecalho(ambiente_clinico.token)
    )
    assert resposta.status_code == 200
    assert resposta.json()["dados"]["resposta"] == corpo["dados"]


def test_historico_de_falha_mantem_o_status_erro(
    ambiente_clinico: AmbienteClinico,
    modulos_da_fase_6: ModulosDaFase6,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O envelope do historico reflete o resultado original, nao um sucesso de leitura."""
    id_paciente = criar_paciente(ambiente_clinico)
    contrato = _contrato_com_falha(modulos_da_fase_6, "falha registrada")
    monkeypatch.setattr(
        modulos_da_fase_6.orchestrator, "executar_pipeline", lambda *_, **__: contrato
    )
    avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)
    monkeypatch.undo()

    resposta = ambiente_clinico.cliente.get(
        f"{ROTA}/{contrato.id_execucao}", headers=cabecalho(ambiente_clinico.token)
    )
    assert resposta.status_code == 200
    envelope = resposta.json()
    assert envelope["status"] == "ERRO"
    assert envelope["erros"][0]["mensagem"] == "falha registrada"
    assert envelope["dados"]["resposta"]["erros"] == ["falha registrada"]


def test_historico_sem_contrato_salvo_ainda_explica_a_falha(
    ambiente_clinico: AmbienteClinico,
) -> None:
    """Registro sem `resposta_json`: os motivos vem de `erros_json` (falha nunca muda)."""
    id_paciente = criar_paciente(ambiente_clinico)
    id_execucao = str(uuid4())

    from app.contratos.envelope import StatusDaResposta
    from app.dados.repositorios.assistencial import AvaliacaoRepositorio

    with ambiente_clinico.fabrica_de_sessoes() as sessao:
        AvaliacaoRepositorio(sessao).criar(
            id_execucao=id_execucao,
            id_paciente=id_paciente,
            id_usuario=ambiente_clinico.id_usuario,
            features=FEATURES_DO_PACIENTE_DA_AULA,
            origem_dos_dados=OrigemDosDados.MANUAL,
            status=StatusDaResposta.ERRO,
            modo=ModoDoPipeline.SIMULADO,
            resposta=None,
            erros=["motivo guardado apenas na coluna de erros"],
        )

    resposta = ambiente_clinico.cliente.get(
        f"{ROTA}/{id_execucao}", headers=cabecalho(ambiente_clinico.token)
    )
    assert resposta.status_code == 200
    envelope = resposta.json()
    assert envelope["status"] == "ERRO"
    assert envelope["erros"][0]["mensagem"] == "motivo guardado apenas na coluna de erros"


def test_avaliacao_inexistente_devolve_404(ambiente_clinico: AmbienteClinico) -> None:
    resposta = ambiente_clinico.cliente.get(
        f"{ROTA}/nao-existe", headers=cabecalho(ambiente_clinico.token)
    )
    assert resposta.status_code == 404
    assert resposta.json()["erros"][0]["codigo"] == "NAO_ENCONTRADO"
    assert resposta.json()["erros"][0]["campo"] == "id_execucao"


def test_historico_exige_autenticacao(ambiente_clinico: AmbienteClinico) -> None:
    assert ambiente_clinico.cliente.get(f"{ROTA}/qualquer").status_code == 401


def test_historico_negado_para_operador(ambiente_clinico: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_clinico)
    corpo = avaliar_paciente(ambiente_clinico, id_paciente, FEATURES_DO_PACIENTE_DA_AULA)[
        "corpo"
    ]
    token = token_com_papel(ambiente_clinico, PapelDoUsuario.OPERADOR)

    resposta = ambiente_clinico.cliente.get(
        f"{ROTA}/{corpo['id_execucao']}", headers=cabecalho(token)
    )
    assert resposta.status_code == 403