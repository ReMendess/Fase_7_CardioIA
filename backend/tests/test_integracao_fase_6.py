"""Testes da ponte com o pacote da Fase 6 (``app/integracao/fase_6.py``).

Cobrem as mitigacoes obrigatorias da Decisao 1: **M1** (import tardio — o backend sobe
mesmo sem o SDK) e **M2** (``sys.path.append``, nunca ``insert``).

Nota sobre o ambiente: neste workspace o pacote ``cardioia`` tambem esta acessivel por
``PYTHONPATH`` (apontando para ``Fase_6/cardioia_Fase6/src``). Por isso os testes que
precisam exercitar o **caminho de falha** do import rodam em subprocesso com a variavel
removida — dentro do processo principal o import sempre teria sucesso.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Configuracoes
from app.contratos.erros import CodigoDeErro, ErroDaAPIException
from app.integracao import fase_6
from tests.conftest import RAIZ_DO_BACKEND, _configuracao_base


# --------------------------------------------------------------------------- #
# Caminhos (M5)
# --------------------------------------------------------------------------- #


def test_pastas_sao_derivadas_da_configuracao(
    configuracao_com_fase_6_real: Configuracoes, pasta_da_fase_6_real: Path
) -> None:
    """Nenhum caminho absoluto e escrito no codigo: tudo sai da configuracao."""
    assert fase_6.pasta_do_codigo(configuracao_com_fase_6_real) == pasta_da_fase_6_real / "src"
    assert (
        fase_6.pasta_de_artefatos(configuracao_com_fase_6_real)
        == pasta_da_fase_6_real / "models"
    )
    assert fase_6.raiz_do_projeto_da_fase_6(configuracao_com_fase_6_real) == pasta_da_fase_6_real


def test_pastas_acompanham_pasta_fase_6_alternativa(tmp_path: Path) -> None:
    config = _configuracao_base(str(tmp_path))
    assert fase_6.pasta_do_codigo(config) == tmp_path / "src"
    assert fase_6.pasta_de_artefatos(config) == tmp_path / "models"


# --------------------------------------------------------------------------- #
# sys.path (M2)
# --------------------------------------------------------------------------- #


def test_caminho_e_adicionado_no_fim_do_sys_path(tmp_path: Path) -> None:
    """``append`` e nao ``insert``: ``src/agents/`` nao pode sombrear o SDK ``agents``.

    Testar a funcao privada aqui e proposital: ela e a implementacao da mitigacao M2,
    uma exigencia documentada — nao um detalhe interno.
    """
    pasta = tmp_path / "src"
    pasta.mkdir()
    fase_6._garantir_caminho(pasta)
    try:
        assert sys.path[-1] == str(pasta)
    finally:
        sys.path.remove(str(pasta))


def test_caminho_nao_e_adicionado_duas_vezes(tmp_path: Path) -> None:
    pasta = tmp_path / "src"
    pasta.mkdir()
    fase_6._garantir_caminho(pasta)
    fase_6._garantir_caminho(pasta)
    try:
        assert sys.path.count(str(pasta)) == 1
    finally:
        sys.path.remove(str(pasta))


def test_importar_coloca_o_src_da_fase_6_no_sys_path(
    configuracao_com_fase_6_real: Configuracoes, modulos_da_fase_6: fase_6.ModulosDaFase6
) -> None:
    assert str(fase_6.pasta_do_codigo(configuracao_com_fase_6_real)) in sys.path


# --------------------------------------------------------------------------- #
# disponibilidade (barata — sem importar)
# --------------------------------------------------------------------------- #


def test_disponibilidade_com_a_fase_6_real(
    configuracao_com_fase_6_real: Configuracoes, pasta_da_fase_6_real: Path
) -> None:
    estado = fase_6.disponibilidade(configuracao_com_fase_6_real)

    assert estado["codigo_presente"] is True
    assert estado["importavel"] is True
    assert estado["faltando"] == []
    assert estado["pasta_do_codigo"] == str(pasta_da_fase_6_real / "src")
    assert all(estado["modulos_encontrados"].values())


def test_disponibilidade_sem_a_pasta_do_codigo(tmp_path: Path) -> None:
    """Nunca levanta excecao: reporta o que falta para o operador decidir.

    Nao afirmamos nada sobre ``faltando`` aqui: ele responde "o **processo** consegue
    localizar o modulo?", e neste ponto da suite o pacote ``cardioia`` pode ja ter sido
    importado por outro teste. O invariante que vale sempre e o de baixo.
    """
    estado = fase_6.disponibilidade(_configuracao_base(str(tmp_path)))

    assert estado["codigo_presente"] is False
    assert estado["importavel"] is False  # sem o codigo, nunca e importavel
    assert estado["pasta_do_codigo"] == str(tmp_path / "src")


def test_disponibilidade_nao_importa_o_pacote(
    configuracao_com_fase_6_real: Configuracoes,
) -> None:
    """O ``/health`` precisa continuar barato: ``find_spec`` nao executa o modulo.

    Verificado em **subprocesso** de proposito: dentro da suite o pacote ``cardioia`` ja
    pode ter sido importado por outro teste, o que tornaria a assercao inutil.
    """
    codigo = (
        "import sys\n"
        "from app.config import CANDIDATO_FASE_6, Configuracoes\n"
        "from app.integracao.fase_6 import disponibilidade\n"
        "config = Configuracoes(_env_file=None, ambiente='teste', jwt_secret='x' * 40,\n"
        "    database_url='sqlite+pysqlite:///:memory:', pasta_fase_6=str(CANDIDATO_FASE_6))\n"
        "estado = disponibilidade(config)\n"
        "print('importavel=', estado['importavel'])\n"
        "print('cardioia_importado=', 'cardioia' in sys.modules)\n"
        "print('agents_importado=', 'agents' in sys.modules)\n"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=str(RAIZ_DO_BACKEND),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert "importavel= True" in resultado.stdout
    assert "cardioia_importado= False" in resultado.stdout
    assert "agents_importado= False" in resultado.stdout


# --------------------------------------------------------------------------- #
# import tardio (M1)
# --------------------------------------------------------------------------- #


def test_importar_devolve_os_modulos_da_fase_6(
    modulos_da_fase_6: fase_6.ModulosDaFase6,
) -> None:
    assert modulos_da_fase_6.predict.__name__ == "cardioia.ml.predict"
    assert modulos_da_fase_6.risk_result.__name__ == "cardioia.schemas.risk_result"
    assert modulos_da_fase_6.orchestrator.__name__ == "cardioia.agents.orchestrator"
    assert modulos_da_fase_6.protocolos.__name__ == "cardioia.knowledge.protocols"


def test_importar_reporta_as_versoes(modulos_da_fase_6: fase_6.ModulosDaFase6) -> None:
    assert modulos_da_fase_6.versao_do_pacote == "0.2.0"
    assert modulos_da_fase_6.versao_do_sdk
    assert modulos_da_fase_6.versao_do_sdk.split(".")[0].isdigit()


def test_importar_usa_cache(
    configuracao_com_fase_6_real: Configuracoes, modulos_da_fase_6: fase_6.ModulosDaFase6
) -> None:
    """Segunda chamada devolve o **mesmo** objeto: nao reimporta."""
    assert fase_6.importar(configuracao_com_fase_6_real) is modulos_da_fase_6


def test_limpar_cache_forca_nova_importacao(
    configuracao_com_fase_6_real: Configuracoes, modulos_da_fase_6: fase_6.ModulosDaFase6
) -> None:
    fase_6.limpar_cache()
    # O pacote continua em ``sys.modules`` (o Python nao "desimporta"), mas o cache do
    # backend e reconstruido — e os modulos devolvidos sao os mesmos objetos.
    recarregado = fase_6.importar(configuracao_com_fase_6_real)
    assert recarregado.predict is modulos_da_fase_6.predict
    assert recarregado.versao_do_pacote == modulos_da_fase_6.versao_do_pacote


def test_importar_sem_o_pacote_disponivel_devolve_503(tmp_path: Path) -> None:
    """M1: a falha vira resposta 503, nao derrubada do processo.

    Roda em **subprocesso com ``PYTHONPATH`` removido**. Neste workspace o pacote
    ``cardioia`` tambem esta acessivel por ``PYTHONPATH`` (apontando para o ``src`` da
    Fase 6), entao sem limpar a variavel o caminho de falha nunca seria exercitado.
    """
    (tmp_path / "src").mkdir()
    ambiente = dict(os.environ)
    ambiente.pop("PYTHONPATH", None)

    codigo = (
        "from app.config import Configuracoes\n"
        "from app.contratos.erros import ErroDaAPIException\n"
        "from app.integracao.fase_6 import importar\n"
        "config = Configuracoes(_env_file=None, ambiente='teste', jwt_secret='x' * 40,\n"
        f"    database_url='sqlite+pysqlite:///:memory:', pasta_fase_6=r'{tmp_path}')\n"
        "try:\n"
        "    importar(config)\n"
        "except ErroDaAPIException as erro:\n"
        "    print('codigo=', erro.codigo.value)\n"
        "    print('http=', erro.http)\n"
        "    print('detalhe=', erro.erro.detalhe)\n"
        "else:\n"
        "    print('NAO_LEVANTOU')\n"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=str(RAIZ_DO_BACKEND),
        env=ambiente,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert "codigo= MODELO_INDISPONIVEL" in resultado.stdout
    assert "http= 503" in resultado.stdout
    # A causa original e preservada no detalhe (N5): nome do tipo + mensagem do Python.
    assert "ModuleNotFoundError: No module named 'cardioia'" in resultado.stdout
    assert str(tmp_path) in resultado.stdout


def test_falha_de_import_nao_envenena_o_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Depois de uma falha, a proxima chamada tenta de novo (nao guarda erro no cache)."""

    def _falhar(nome: str) -> object:
        raise ModuleNotFoundError(f"simulado: '{nome}' indisponivel")

    fase_6.limpar_cache()
    monkeypatch.setattr(fase_6, "import_module", _falhar)
    config = _configuracao_base(str(tmp_path))

    with pytest.raises(ErroDaAPIException) as primeira:
        fase_6.importar(config)
    assert primeira.value.codigo is CodigoDeErro.MODELO_INDISPONIVEL

    with pytest.raises(ErroDaAPIException) as segunda:
        fase_6.importar(config)
    assert segunda.value.codigo is CodigoDeErro.MODELO_INDISPONIVEL

    monkeypatch.undo()
    fase_6.limpar_cache()
    # Com o import restaurado, a mesma configuracao volta a funcionar.
    assert fase_6.importar(config).versao_do_pacote == "0.2.0"