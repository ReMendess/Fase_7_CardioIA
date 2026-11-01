"""Testes da traducao de excecoes da Fase 6 (``app/integracao/traducao.py``).

Regra **N5**: a mensagem original da Fase 6 sobrevive em ``detalhe``. Regra do contrato:
**falha nunca vira sucesso** — excecao desconhecida vira ``ERRO_INTERNO`` (500).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.contratos.erros import CodigoDeErro, ErroDaAPIException
from app.integracao.fase_6 import ModulosDaFase6
from app.integracao.traducao import regras, traduzir


# --------------------------------------------------------------------------- #
# Regras
# --------------------------------------------------------------------------- #


def test_regras_cobrem_as_excecoes_tipadas_da_fase_6(
    modulos_da_fase_6: ModulosDaFase6,
) -> None:
    tipos = {regra.tipo for regra in regras(modulos_da_fase_6)}
    esperados = {
        modulos_da_fase_6.predict.PacienteInvalidoError,
        modulos_da_fase_6.predict.ModeloNaoEncontradoError,
        modulos_da_fase_6.predict.ModeloIncompativelError,
        modulos_da_fase_6.predict.ErroDePrevisao,
        modulos_da_fase_6.protocolos.DadosDoPacienteInvalidosError,
        modulos_da_fase_6.protocolos.BaseDeConhecimentoInvalidaError,
        ValidationError,
    }
    assert tipos == esperados


def test_subclasses_vem_antes_da_base(modulos_da_fase_6: ModulosDaFase6) -> None:
    """A ordem importa: ``ErroDePrevisao`` e a base das outras tres."""
    ordem = [regra.tipo for regra in regras(modulos_da_fase_6)]
    posicao_base = ordem.index(modulos_da_fase_6.predict.ErroDePrevisao)

    for subclasse in (
        modulos_da_fase_6.predict.PacienteInvalidoError,
        modulos_da_fase_6.predict.ModeloNaoEncontradoError,
        modulos_da_fase_6.predict.ModeloIncompativelError,
    ):
        assert ordem.index(subclasse) < posicao_base


# --------------------------------------------------------------------------- #
# Mapa excecao -> codigo
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("atributo", "codigo", "http"),
    [
        ("PacienteInvalidoError", CodigoDeErro.PACIENTE_INVALIDO, 422),
        ("ModeloNaoEncontradoError", CodigoDeErro.MODELO_INDISPONIVEL, 503),
        ("ModeloIncompativelError", CodigoDeErro.MODELO_INCOMPATIVEL, 500),
        ("ErroDePrevisao", CodigoDeErro.FALHA_DE_PREVISAO, 500),
    ],
)
def test_excecoes_de_previsao_sao_traduzidas(
    modulos_da_fase_6: ModulosDaFase6, atributo: str, codigo: CodigoDeErro, http: int
) -> None:
    classe = getattr(modulos_da_fase_6.predict, atributo)

    erro = traduzir(classe("mensagem original"), modulos=modulos_da_fase_6)

    assert erro.codigo is codigo
    assert erro.http == http
    assert "mensagem original" in (erro.erro.detalhe or "")


@pytest.mark.parametrize(
    ("atributo", "codigo"),
    [
        ("DadosDoPacienteInvalidosError", CodigoDeErro.DADOS_DO_PACIENTE_INVALIDOS),
        ("BaseDeConhecimentoInvalidaError", CodigoDeErro.BASE_DE_PROTOCOLOS_INVALIDA),
    ],
)
def test_excecoes_de_protocolos_sao_traduzidas(
    modulos_da_fase_6: ModulosDaFase6, atributo: str, codigo: CodigoDeErro
) -> None:
    classe = getattr(modulos_da_fase_6.protocolos, atributo)

    erro = traduzir(classe("protocolo invalido"), modulos=modulos_da_fase_6)

    assert erro.codigo is codigo
    assert "protocolo invalido" in (erro.erro.detalhe or "")


def test_subclasse_nao_cai_na_regra_da_base(modulos_da_fase_6: ModulosDaFase6) -> None:
    """``PacienteInvalidoError`` e subclasse de ``ErroDePrevisao``: vale a mais especifica."""
    erro = traduzir(
        modulos_da_fase_6.predict.PacienteInvalidoError("faltou 'spo2_media'"),
        modulos=modulos_da_fase_6,
    )
    assert erro.codigo is CodigoDeErro.PACIENTE_INVALIDO


def test_validation_error_do_contrato_vira_422(modulos_da_fase_6: ModulosDaFase6) -> None:
    """Contrato Pydantic da Fase 6 violado (o pipeline devolveu algo invalido)."""
    with pytest.raises(ValidationError) as capturado:
        modulos_da_fase_6.risk_result.DiagnosticoDaPredicao(
            probabilidade_risco=1.5,  # fora de 0..1
            pico_risco_previsto=1,
            classificacao_risco="pico_de_risco",
            modelo_utilizado="Random Forest",
            classe_do_estimador="RandomForestClassifier",
            limiar_decisao=0.5,
            regra_de_decisao="probabilidade >= 0.5",
            features_utilizadas=["idade_media"],
        )

    erro = traduzir(capturado.value, modulos=modulos_da_fase_6)
    assert erro.codigo is CodigoDeErro.CONTRATO_VIOLADO
    assert erro.http == 422


# --------------------------------------------------------------------------- #
# Fallbacks e nao-traducao
# --------------------------------------------------------------------------- #


def test_excecao_desconhecida_vira_erro_interno(modulos_da_fase_6: ModulosDaFase6) -> None:
    erro = traduzir(RuntimeError("algo deu errado"), modulos=modulos_da_fase_6)
    assert erro.codigo is CodigoDeErro.ERRO_INTERNO
    assert erro.http == 500
    assert "RuntimeError" in (erro.erro.detalhe or "")


def test_import_error_vira_503_mesmo_sem_modulos() -> None:
    erro = traduzir(ModuleNotFoundError("No module named 'agents'"))
    assert erro.codigo is CodigoDeErro.MODELO_INDISPONIVEL
    assert erro.http == 503


def test_erro_da_api_passa_intacto(modulos_da_fase_6: ModulosDaFase6) -> None:
    """Ja esta no contrato: retraduzir perderia codigo e mensagem originais."""
    original = ErroDaAPIException(CodigoDeErro.CONFLITO, "id_execucao repetido")
    assert traduzir(original, modulos=modulos_da_fase_6) is original


def test_sem_modulos_apenas_regras_genericas_se_aplicam() -> None:
    erro = traduzir(RuntimeError("x"))
    assert erro.codigo is CodigoDeErro.ERRO_INTERNO


# --------------------------------------------------------------------------- #
# Detalhe (N5)
# --------------------------------------------------------------------------- #


def test_detalhe_preserva_tipo_e_mensagem_originais(
    modulos_da_fase_6: ModulosDaFase6,
) -> None:
    erro = traduzir(
        modulos_da_fase_6.predict.ModeloIncompativelError("dtype 'int64' nao suportado"),
        modulos=modulos_da_fase_6,
    )
    detalhe = erro.erro.detalhe or ""
    assert "ModeloIncompativelError" in detalhe
    assert "dtype 'int64' nao suportado" in detalhe


def test_contexto_entra_no_detalhe(modulos_da_fase_6: ModulosDaFase6) -> None:
    erro = traduzir(
        modulos_da_fase_6.predict.ErroDePrevisao("falha"),
        modulos=modulos_da_fase_6,
        contexto="executando o pipeline",
    )
    assert (erro.erro.detalhe or "").startswith("executando o pipeline — ")


def test_nunca_devolve_none(modulos_da_fase_6: ModulosDaFase6) -> None:
    """O contrato exige erro sempre tipado: nenhuma excecao escapa sem traducao."""
    for excecao in (ValueError("a"), KeyError("b"), OSError("c"), Exception("d")):
        assert isinstance(traduzir(excecao, modulos=modulos_da_fase_6), ErroDaAPIException)