"""Testes do pipeline da Fase 6 executado **de verdade** pela camada de integracao.

Diferente dos testes de unidade, aqui o pipeline roda em modo ``simulado``: o SDK, os
handoffs e as tools sao os reais — apenas as decisoes de rota do LLM sao substituidas por
um roteiro deterministico. Nenhuma chamada a API da OpenAI.

Este arquivo tambem cumpre a promessa registrada em ``app/dados/enums.py``: a
**equivalencia dos valores** dos enums com os da Fase 6 e verificada, nao presumida.
"""

from __future__ import annotations

import pytest

from app.config import Configuracoes
from app.contratos.envelope import StatusDaResposta
from app.dados.enums import ClassificacaoDeRisco, ModoDoPipeline, OperadorDeComparacao, TipoDePasso
from app.dados.modelos import COLUNAS_DE_FEATURE
from app.integracao import fase_6
from app.integracao.fase_6 import ModulosDaFase6
from app.integracao.mapeador import montar_caso_para_o_pipeline
from app.integracao.modelo import ArtefatoDoModelo


def _executar(
    config: Configuracoes, modulos: ModulosDaFase6, features: dict[str, float]
) -> object:
    """Roda o pipeline pelo mesmo caminho que o endpoint usara."""
    return modulos.orchestrator.executar_pipeline(
        montar_caso_para_o_pipeline(features),
        raiz=str(fase_6.raiz_do_projeto_da_fase_6(config)),
        pasta_modelos=str(fase_6.pasta_de_artefatos(config)),
    )


# --------------------------------------------------------------------------- #
# Execucao ponta a ponta
# --------------------------------------------------------------------------- #


def test_pipeline_conclui_em_modo_simulado(
    configuracao_com_fase_6_real: Configuracoes,
    modulos_da_fase_6: ModulosDaFase6,
    features_do_paciente_da_aula: dict[str, float],
) -> None:
    resposta = _executar(
        configuracao_com_fase_6_real, modulos_da_fase_6, features_do_paciente_da_aula
    )

    assert resposta.status.value == "CONCLUIDO"
    assert resposta.modo.value == "simulado"
    assert resposta.erros == []
    assert resposta.diagnostico is not None
    assert resposta.diagnostico.probabilidade_risco is not None
    assert resposta.diagnostico.pico_risco_previsto in (0, 1)


def test_paciente_da_aula_e_classificado_como_pico_de_risco(
    configuracao_com_fase_6_real: Configuracoes,
    modulos_da_fase_6: ModulosDaFase6,
    features_do_paciente_da_aula: dict[str, float],
) -> None:
    """Valor de referencia documentado no material da aula: probabilidade ~0,99."""
    resposta = _executar(
        configuracao_com_fase_6_real, modulos_da_fase_6, features_do_paciente_da_aula
    )

    assert resposta.diagnostico.probabilidade_risco == pytest.approx(0.99, abs=0.02)
    assert resposta.diagnostico.pico_risco_previsto == 1
    assert resposta.diagnostico.classificacao_risco == "pico_de_risco"
    assert resposta.diagnostico.limiar_decisao == 0.5


def test_pipeline_aciona_protocolos_e_indicadores(
    configuracao_com_fase_6_real: Configuracoes,
    modulos_da_fase_6: ModulosDaFase6,
    features_do_paciente_da_aula: dict[str, float],
) -> None:
    resposta = _executar(
        configuracao_com_fase_6_real, modulos_da_fase_6, features_do_paciente_da_aula
    )

    assert len(resposta.protocolos) > 0
    assert all(protocolo.texto_oficial for protocolo in resposta.protocolos)
    assert len(resposta.indicadores) == 6
    assert resposta.agente_final == "Planejador de Resposta"
    assert len(resposta.handoffs_realizados) == 3


def test_pipeline_registra_a_trilha_de_execucao(
    configuracao_com_fase_6_real: Configuracoes,
    modulos_da_fase_6: ModulosDaFase6,
    features_do_paciente_da_aula: dict[str, float],
) -> None:
    resposta = _executar(
        configuracao_com_fase_6_real, modulos_da_fase_6, features_do_paciente_da_aula
    )

    assert len(resposta.passos) > 0
    assert all(passo.sucesso for passo in resposta.passos)
    assert [passo.ordem for passo in resposta.passos] == list(
        range(1, len(resposta.passos) + 1)
    )
    assert resposta.versao_do_sdk
    assert resposta.duracao_segundos is not None and resposta.duracao_segundos >= 0


def test_resultado_e_serializavel_em_json(
    configuracao_com_fase_6_real: Configuracoes,
    modulos_da_fase_6: ModulosDaFase6,
    features_do_paciente_da_aula: dict[str, float],
) -> None:
    """O contrato precisa ser persistivel em ``resposta_json`` (coluna JSON)."""
    resposta = _executar(
        configuracao_com_fase_6_real, modulos_da_fase_6, features_do_paciente_da_aula
    )
    dicionario = resposta.model_dump(mode="json")

    assert dicionario["status"] == "CONCLUIDO"
    assert dicionario["diagnostico"]["modelo_utilizado"] == "Random Forest"
    assert dicionario["diagnostico"]["origem_do_modelo"]["sha256_da_base_usada"]
    assert isinstance(dicionario["protocolos"], list)
    assert isinstance(dicionario["passos"], list)


def test_limitacoes_vem_da_fase_6(
    configuracao_com_fase_6_real: Configuracoes,
    modulos_da_fase_6: ModulosDaFase6,
    features_do_paciente_da_aula: dict[str, float],
) -> None:
    """N3/N8: o texto clinico e reaproveitado da Fase 6, nunca reescrito aqui."""
    resposta = _executar(
        configuracao_com_fase_6_real, modulos_da_fase_6, features_do_paciente_da_aula
    )
    assert list(resposta.limitacoes) == list(modulos_da_fase_6.risk_result.LIMITACOES_PADRAO)


def test_avisos_incluem_o_modo_simulado(
    configuracao_com_fase_6_real: Configuracoes,
    modulos_da_fase_6: ModulosDaFase6,
    features_do_paciente_da_aula: dict[str, float],
) -> None:
    """Transparencia: a resposta diz que nenhum LLM foi chamado."""
    resposta = _executar(
        configuracao_com_fase_6_real, modulos_da_fase_6, features_do_paciente_da_aula
    )
    assert any("SIMULADO" in aviso for aviso in resposta.avisos)


# --------------------------------------------------------------------------- #
# Comportamento em falha (o pipeline nao levanta: devolve status ERRO)
# --------------------------------------------------------------------------- #


def test_pipeline_sem_artefato_devolve_status_de_erro(
    configuracao_com_fase_6_real: Configuracoes,
    modulos_da_fase_6: ModulosDaFase6,
    features_do_paciente_da_aula: dict[str, float],
) -> None:
    """A Fase 6 **nao** levanta excecao: devolve ``ERRO`` com o motivo em ``erros``.

    Consequencia direta para o endpoint: capturar excecao **nao basta** — e preciso
    traduzir ``StatusDaExecucao`` para o envelope e repassar ``erros``. Caso contrario a
    falha viraria um sucesso aparente.
    """
    resposta = modulos_da_fase_6.orchestrator.executar_pipeline(
        montar_caso_para_o_pipeline(features_do_paciente_da_aula),
        raiz=str(fase_6.raiz_do_projeto_da_fase_6(configuracao_com_fase_6_real)),
        pasta_modelos=str(
            configuracao_com_fase_6_real.pasta_da_fase_6 / "pasta_que_nao_existe"
        ),
    )

    assert resposta.status.value == "ERRO"
    assert resposta.erros
    assert any("modelo indisponivel" in erro.lower() for erro in resposta.erros)
    assert resposta.diagnostico is None


def test_paciente_invalido_e_recusado_antes_do_pipeline(
    modulos_da_fase_6: ModulosDaFase6,
) -> None:
    """A validacao do contrato acontece na borda: nada invalido chega ao modelo."""
    from app.contratos.erros import ErroDaAPIException

    with pytest.raises(ErroDaAPIException):
        montar_caso_para_o_pipeline({"idade_media": 62.0})


# --------------------------------------------------------------------------- #
# Equivalencia dos enums com a Fase 6 (promessa de app/dados/enums.py)
# --------------------------------------------------------------------------- #


def test_modo_do_pipeline_equivale_ao_da_fase_6(modulos_da_fase_6: ModulosDaFase6) -> None:
    assert {item.value for item in ModoDoPipeline} == {
        item.value for item in modulos_da_fase_6.risk_result.ModoDeExecucao
    }


def test_tipo_de_passo_equivale_ao_da_fase_6(modulos_da_fase_6: ModulosDaFase6) -> None:
    assert {item.value for item in TipoDePasso} == {
        item.value for item in modulos_da_fase_6.risk_result.TipoDePasso
    }


def test_status_da_resposta_equivale_ao_da_fase_6(modulos_da_fase_6: ModulosDaFase6) -> None:
    """O envelope da Fase 7 usa os **mesmos 4 valores** de status da Fase 6."""
    assert {item.value for item in StatusDaResposta} == {
        item.value for item in modulos_da_fase_6.risk_result.StatusDaExecucao
    }


def test_classificacao_de_risco_equivale_aos_rotulos_da_fase_6(
    modulos_da_fase_6: ModulosDaFase6,
) -> None:
    assert {item.value for item in ClassificacaoDeRisco} == set(
        modulos_da_fase_6.risk_result.ROTULOS.values()
    )


def test_operador_de_comparacao_cobre_os_da_fase_6(modulos_da_fase_6: ModulosDaFase6) -> None:
    """``IndicadorDeterministico.operador`` e ``Literal["<", ">", "=="]`` na Fase 6."""
    assert {item.value for item in OperadorDeComparacao} == {"<", ">", "=="}


def test_features_do_modelo_batem_com_o_contrato(
    modulos_da_fase_6: ModulosDaFase6, artefato_do_modelo: ArtefatoDoModelo
) -> None:
    """O modelo carregado usa exatamente as 10 features que o backend espera."""
    features = tuple(modulos_da_fase_6.predict.features_do_modelo(artefato_do_modelo.metadados))
    assert features == COLUNAS_DE_FEATURE


def test_classe_positiva_e_rotulos_batem(modulos_da_fase_6: ModulosDaFase6) -> None:
    risk = modulos_da_fase_6.risk_result
    assert risk.CLASSE_POSITIVA == 1
    assert risk.ROTULOS[1] == ClassificacaoDeRisco.PICO_DE_RISCO.value
    assert risk.ROTULOS[0] == ClassificacaoDeRisco.SEM_PICO_DE_RISCO.value
