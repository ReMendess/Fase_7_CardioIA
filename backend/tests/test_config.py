"""Testes da configuracao e da falha rapida (``app/config.py``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import (
    TAMANHO_MINIMO_DO_SEGREDO,
    CANDIDATO_FASE_6,
    Configuracoes,
    ErroDeConfiguracao,
)
from app.main import criar_app
from tests.conftest import SEGREDO_DE_TESTE


def _config(**extras: object) -> Configuracoes:
    parametros: dict[str, object] = {"_env_file": None, "ambiente": "teste"}
    parametros.update(extras)
    return Configuracoes(**parametros)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Falha rapida
# --------------------------------------------------------------------------- #


def test_validar_rejeita_segredo_ausente() -> None:
    """Sem JWT_SECRET o servico NAO sobe."""
    with pytest.raises(ErroDeConfiguracao, match="JWT_SECRET nao definida"):
        _config(jwt_secret="").validar()


def test_validar_rejeita_segredo_curto() -> None:
    """HS256 exige 256 bits: segredo curto e recusado."""
    with pytest.raises(ErroDeConfiguracao, match="o minimo e 32"):
        _config(jwt_secret="curto-demais").validar()


def test_validar_rejeita_algoritmo_diferente_de_hs256() -> None:
    with pytest.raises(ErroDeConfiguracao, match="nao suportado"):
        _config(jwt_secret=SEGREDO_DE_TESTE, jwt_algoritmo="RS256").validar()


def test_validar_rejeita_cors_vazio_em_producao() -> None:
    with pytest.raises(ErroDeConfiguracao, match="CORS_ORIGENS vazio em producao"):
        _config(
            jwt_secret=SEGREDO_DE_TESTE, ambiente="producao", cors_origens=""
        ).validar()


def test_validar_aceita_configuracao_correta() -> None:
    _config(jwt_secret=SEGREDO_DE_TESTE).validar()  # nao deve levantar


def test_validar_agrega_multiplos_problemas() -> None:
    """A mensagem lista todos os problemas de uma vez."""
    with pytest.raises(ErroDeConfiguracao) as capturado:
        _config(jwt_secret="", jwt_algoritmo="none").validar()
    mensagem = str(capturado.value)
    assert "JWT_SECRET nao definida" in mensagem
    assert "nao suportado" in mensagem


def test_tamanho_minimo_do_segredo_corresponde_a_256_bits() -> None:
    assert TAMANHO_MINIMO_DO_SEGREDO == 32
    assert len(SEGREDO_DE_TESTE) >= TAMANHO_MINIMO_DO_SEGREDO


# --------------------------------------------------------------------------- #
# Derivados
# --------------------------------------------------------------------------- #


def test_prefixo_das_rotas_usa_a_versao() -> None:
    assert _config().prefixo_das_rotas == "/api/v1"
    assert _config(versao_api="v2").prefixo_das_rotas == "/api/v2"


def test_origens_cors_ignora_espacos_e_vazios() -> None:
    config = _config(cors_origens=" http://a , ,http://b ,")
    assert config.origens_cors == ["http://a", "http://b"]


def test_pasta_da_fase_6_usa_o_caminho_candidato_por_padrao() -> None:
    assert _config(pasta_fase_6="").pasta_da_fase_6 == CANDIDATO_FASE_6


def test_pasta_da_fase_6_respeita_o_valor_informado() -> None:
    config = _config(pasta_fase_6=str(Path("C:/tmp/fase6")))
    assert config.pasta_da_fase_6 == Path("C:/tmp/fase6")


def test_caminhos_do_artefato_derivam_da_pasta() -> None:
    config = _config(pasta_fase_6=str(Path("C:/tmp/fase6")))
    assert config.caminho_do_modelo == Path("C:/tmp/fase6/models/modelo_pico_risco.pkl")
    assert (
        config.caminho_dos_metadados
        == Path("C:/tmp/fase6/models/modelo_pico_risco_metadata.json")
    )


# --------------------------------------------------------------------------- #
# Integracoes — apenas presenca, nunca valores
# --------------------------------------------------------------------------- #


def test_integracoes_reportam_apenas_presenca() -> None:
    config = _config()
    integracoes = config.integracoes_configuradas
    assert set(integracoes) == {"openai", "watson", "servico_de_visao"}
    assert integracoes["openai"] is False
    assert integracoes["watson"] is False
    assert integracoes["servico_de_visao"] is True  # a URL tem default


def test_watson_exige_as_quatro_variaveis() -> None:
    """Com uma variavel faltando, a integracao nao e considerada configurada."""
    config = _config(
        watson_api_key="x",
        watson_service_url="https://exemplo",
        watson_assistant_id="y",
    )
    assert config.integracoes_configuradas["watson"] is False

    completa = _config(
        watson_api_key="x",
        watson_service_url="https://exemplo",
        watson_assistant_id="y",
        watson_environment_id="z",
    )
    assert completa.integracoes_configuradas["watson"] is True


def test_integracoes_nao_expoem_valores() -> None:
    """O dicionario devolve booleanos — nenhum segredo vaza pelo /health."""
    config = _config(openai_api_key="sk-nao-e-real")
    valores = config.integracoes_configuradas
    assert all(isinstance(valor, bool) for valor in valores.values())
    assert "sk-nao-e-real" not in repr(valores)


# --------------------------------------------------------------------------- #
# Fabrica da aplicacao
# --------------------------------------------------------------------------- #


def test_criar_app_falha_com_configuracao_invalida() -> None:
    """A fabrica aplica a falha rapida antes de montar a aplicacao."""
    with pytest.raises(ErroDeConfiguracao):
        criar_app(_config(jwt_secret=""))
