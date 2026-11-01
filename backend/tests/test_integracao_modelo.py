"""Testes do cache do artefato do modelo (``app/integracao/modelo.py``)."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.config import Configuracoes
from app.contratos.erros import CodigoDeErro, ErroDaAPIException
from app.dados.modelos import COLUNAS_DE_FEATURE
from app.integracao.modelo import ArtefatoDoModelo, CacheDoModelo
from tests.conftest import _configuracao_base


def _escrever_artefato_invalido(pasta: Path) -> None:
    """Metadata minimo valido + ``.pkl`` corrompido (simula incompatibilidade real)."""
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "modelo_pico_risco_metadata.json").write_text(
        json.dumps({"features": list(COLUNAS_DE_FEATURE)}), encoding="utf-8"
    )
    (pasta / "modelo_pico_risco.pkl").write_bytes(b"isto-nao-e-um-pickle-joblib")


# --------------------------------------------------------------------------- #
# Carga e cache
# --------------------------------------------------------------------------- #


def test_obter_carrega_uma_unica_vez(
    configuracao_com_fase_6_real: Configuracoes, artefato_do_modelo: ArtefatoDoModelo
) -> None:
    """Segunda chamada devolve o **mesmo** objeto: o ``.pkl`` nao e relido."""
    cache = CacheDoModelo()
    assert cache.carregado is False

    primeiro = cache.obter(configuracao_com_fase_6_real)
    assert cache.carregado is True
    assert cache.obter(configuracao_com_fase_6_real) is primeiro

    # O artefato da fixture de sessao tambem vem do mesmo arquivo.
    assert primeiro.caminho == artefato_do_modelo.caminho


def test_artefato_traz_o_contrato_do_modelo(artefato_do_modelo: ArtefatoDoModelo) -> None:
    assert artefato_do_modelo.features == COLUNAS_DE_FEATURE
    assert artefato_do_modelo.nome_do_modelo == "Random Forest"
    assert artefato_do_modelo.classe_do_estimador == "RandomForestClassifier"
    assert artefato_do_modelo.limiar_decisao == 0.5
    assert artefato_do_modelo.caminho.endswith("modelo_pico_risco.pkl")
    assert artefato_do_modelo.sha256_da_base is not None
    assert len(artefato_do_modelo.sha256_da_base) == 64
    assert artefato_do_modelo.carregado_em.tzinfo is not None


def test_limpar_descarta_o_artefato(
    configuracao_com_fase_6_real: Configuracoes,
) -> None:
    cache = CacheDoModelo()
    cache.obter(configuracao_com_fase_6_real)
    cache.limpar()
    assert cache.carregado is False


def test_obter_e_seguro_com_chamadas_concorrentes(
    configuracao_com_fase_6_real: Configuracoes,
) -> None:
    """Duas requisicoes simultaneas nao podem carregar dois estimadores distintos."""
    cache = CacheDoModelo()
    with ThreadPoolExecutor(max_workers=8) as executor:
        artefatos = list(
            executor.map(lambda _: cache.obter(configuracao_com_fase_6_real), range(16))
        )
    assert all(item is artefatos[0] for item in artefatos)


# --------------------------------------------------------------------------- #
# Falhas traduzidas para o contrato
# --------------------------------------------------------------------------- #


def test_artefato_ausente_devolve_503(tmp_path: Path) -> None:
    with pytest.raises(ErroDaAPIException) as capturado:
        CacheDoModelo().obter(_configuracao_base(str(tmp_path)))

    assert capturado.value.codigo is CodigoDeErro.MODELO_INDISPONIVEL
    assert capturado.value.http == 503
    assert "Treine o modelo" in (capturado.value.erro.detalhe or "")


def test_artefato_corrompido_devolve_500_com_a_causa(tmp_path: Path) -> None:
    """Caso real documentado na Fase 6: pickle recusado por outra versao do sklearn."""
    _escrever_artefato_invalido(tmp_path / "models")

    with pytest.raises(ErroDaAPIException) as capturado:
        CacheDoModelo().obter(_configuracao_base(str(tmp_path)))

    assert capturado.value.codigo is CodigoDeErro.MODELO_INCOMPATIVEL
    assert capturado.value.http == 500
    assert "carregando o artefato" in (capturado.value.erro.detalhe or "")


# --------------------------------------------------------------------------- #
# Aquecimento (M3 x M1)
# --------------------------------------------------------------------------- #


def test_aquecer_carrega_o_artefato(configuracao_com_fase_6_real: Configuracoes) -> None:
    cache = CacheDoModelo()
    assert cache.aquecer(configuracao_com_fase_6_real) is True
    assert cache.carregado is True


def test_aquecer_nao_derruba_o_boot_sem_artefato(tmp_path: Path) -> None:
    """M1: o servidor sobe mesmo sem artefato — o aviso fica no log."""
    cache = CacheDoModelo()
    assert cache.aquecer(_configuracao_base(str(tmp_path))) is False
    assert cache.carregado is False
