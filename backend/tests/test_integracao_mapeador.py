"""Testes do mapeador de features (``app/integracao/mapeador.py``).

O ponto central: **contrato fechado, sem defaults** (N3 / Decisao D4). Nenhum valor
clinico e inventado quando falta informacao — o pedido e recusado.
"""

from __future__ import annotations

import math

import pytest

from app.contratos.erros import CodigoDeErro, ErroDaAPIException
from app.dados.modelos import COLUNAS_DE_FEATURE
from app.integracao.mapeador import (
    AVISOS_DE_CONFIABILIDADE,
    avisos_de_confiabilidade,
    montar_caso_para_o_pipeline,
    verificar_aderencia_ao_contrato,
)


def _features() -> dict[str, float]:
    return {
        "idade_media": 62.0,
        "carga_sistema": 92.0,
        "tempo_espera": 75.0,
        "fc_media": 118.0,
        "spo2_media": 89.0,
        "pa_sistolica": 100.0,
        "temperatura": 37.5,
        "densidade_eventos": 7.0,
        "eventos_24h": 5.0,
        "disponibilidade_recursos": 25.0,
    }


# --------------------------------------------------------------------------- #
# Caminho feliz
# --------------------------------------------------------------------------- #


def test_monta_o_caso_na_ordem_canonica() -> None:
    caso = montar_caso_para_o_pipeline(_features())
    assert tuple(caso) == COLUNAS_DE_FEATURE
    assert caso["temperatura"] == 37.5


def test_monta_o_caso_na_ordem_do_modelo() -> None:
    """A ordem de entrada do chamador nao importa: vale a ordem do modelo."""
    invertidas = dict(reversed(list(_features().items())))
    caso = montar_caso_para_o_pipeline(invertidas, ordem=COLUNAS_DE_FEATURE)
    assert tuple(caso) == COLUNAS_DE_FEATURE


def test_aceita_inteiros_e_converte_para_float() -> None:
    caso = montar_caso_para_o_pipeline(_features())
    assert all(isinstance(valor, float) for valor in caso.values())


def test_nao_muta_a_entrada() -> None:
    """Funcao pura: a entrada permanece intacta."""
    original = _features()
    copia = dict(original)
    montar_caso_para_o_pipeline(original)
    assert original == copia


# --------------------------------------------------------------------------- #
# Contrato fechado — sem defaults
# --------------------------------------------------------------------------- #


def test_rejeita_feature_ausente() -> None:
    incompleto = _features()
    del incompleto["spo2_media"]

    with pytest.raises(ErroDaAPIException) as capturado:
        montar_caso_para_o_pipeline(incompleto)

    assert capturado.value.codigo is CodigoDeErro.PACIENTE_INVALIDO
    assert "spo2_media" in capturado.value.mensagem
    # Nada foi preenchido por padrao: a mensagem aponta o que falta, nao substitui.
    assert "ausentes" in capturado.value.mensagem


def test_rejeita_feature_desconhecida() -> None:
    extras = _features()
    extras["pressao_diastolica"] = 80.0

    with pytest.raises(ErroDaAPIException) as capturado:
        montar_caso_para_o_pipeline(extras)

    assert capturado.value.codigo is CodigoDeErro.PACIENTE_INVALIDO
    assert "pressao_diastolica" in capturado.value.mensagem


def test_rejeita_conjunto_vazio() -> None:
    with pytest.raises(ErroDaAPIException) as capturado:
        montar_caso_para_o_pipeline({})
    assert capturado.value.codigo is CodigoDeErro.PACIENTE_INVALIDO


@pytest.mark.parametrize("valor", [True, False])
def test_rejeita_booleano(valor: bool) -> None:
    """``True`` viraria ``1.0`` silenciosamente — e um valor clinico inventado."""
    invalido = _features()
    invalido["temperatura"] = valor  # type: ignore[assignment]

    with pytest.raises(ErroDaAPIException) as capturado:
        montar_caso_para_o_pipeline(invalido)

    assert capturado.value.erro.campo == "temperatura"
    assert "bool" in capturado.value.mensagem


@pytest.mark.parametrize("valor", ["37.5", None, [37.5]])
def test_rejeita_valor_nao_numerico(valor: object) -> None:
    invalido = _features()
    invalido["temperatura"] = valor  # type: ignore[assignment]
    with pytest.raises(ErroDaAPIException):
        montar_caso_para_o_pipeline(invalido)


@pytest.mark.parametrize("valor", [math.nan, math.inf, -math.inf])
def test_rejeita_nan_e_infinito(valor: float) -> None:
    invalido = _features()
    invalido["fc_media"] = valor

    with pytest.raises(ErroDaAPIException) as capturado:
        montar_caso_para_o_pipeline(invalido)

    assert capturado.value.erro.campo == "fc_media"
    assert "invalido" in capturado.value.mensagem


def test_rejeita_valor_negativo() -> None:
    invalido = _features()
    invalido["tempo_espera"] = -1.0

    with pytest.raises(ErroDaAPIException) as capturado:
        montar_caso_para_o_pipeline(invalido)

    assert capturado.value.erro.campo == "tempo_espera"
    assert "negativo" in capturado.value.mensagem


def test_aceita_zero() -> None:
    """Zero e um valor legitimo (ex.: nenhum evento em 24 h)."""
    features = _features()
    features["eventos_24h"] = 0.0
    assert montar_caso_para_o_pipeline(features)["eventos_24h"] == 0.0


# --------------------------------------------------------------------------- #
# Aderencia ao contrato (drift)
# --------------------------------------------------------------------------- #


def test_aderencia_aceita_o_contrato_oficial() -> None:
    verificar_aderencia_ao_contrato(COLUNAS_DE_FEATURE)


def test_aderencia_detecta_drift() -> None:
    """Modelo retreinado com outra lista: falhar alto e melhor que reordenar errado."""
    with pytest.raises(ErroDaAPIException) as capturado:
        verificar_aderencia_ao_contrato([*COLUNAS_DE_FEATURE, "coluna_nova"])

    assert capturado.value.codigo is CodigoDeErro.CONTRATO_VIOLADO
    assert "coluna_nova" in (capturado.value.erro.detalhe or "")


def test_ordem_com_coluna_sem_valor_devolve_contrato_violado() -> None:
    with pytest.raises(ErroDaAPIException) as capturado:
        montar_caso_para_o_pipeline(_features(), ordem=[*COLUNAS_DE_FEATURE, "inexistente"])

    assert capturado.value.codigo is CodigoDeErro.CONTRATO_VIOLADO


# --------------------------------------------------------------------------- #
# Avisos de confiabilidade (achados A3 e A4)
# --------------------------------------------------------------------------- #


def test_ha_dois_avisos_de_confiabilidade() -> None:
    avisos = avisos_de_confiabilidade()
    assert len(avisos) == 2
    assert avisos == list(AVISOS_DE_CONFIABILIDADE)


def test_aviso_de_temperatura_explica_a_causa() -> None:
    texto = AVISOS_DE_CONFIABILIDADE[0]
    assert "temperatura" in texto
    assert "AMBIENTE" in texto and "CORPORAL" in texto
    assert "BAIXA CONFIANCA" in texto


def test_aviso_de_escala_lista_as_features_de_contexto() -> None:
    texto = AVISOS_DE_CONFIABILIDADE[1]
    for coluna in ("carga_sistema", "tempo_espera", "densidade_eventos", "eventos_24h"):
        assert coluna in texto
    assert "EPISODIO" in texto


def test_avisos_sao_lista_nova_a_cada_chamada() -> None:
    """Quem consumir os avisos nao pode corromper a constante do modulo."""
    primeira = avisos_de_confiabilidade()
    primeira.clear()
    assert len(avisos_de_confiabilidade()) == 2