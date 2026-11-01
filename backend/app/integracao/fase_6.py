"""Ponte com o pacote da Fase 6 (``cardioia``): caminho, import tardio e disponibilidade.

Decisao estrutural (``DECISOES_ARQUITETURAIS.md`` §3.3, alternativa **A**): **import
direto** do pacote ``cardioia`` dentro do backend, em processo. Consequencias que
importam: zero duplicacao de logica e as **excecoes tipadas da Fase 6 chegam intactas**
(mapa 1:1 para HTTP, feito em :mod:`app.integracao.traducao`).

Mitigacoes obrigatorias implementadas **aqui**:

- **M1 — import tardio.** ``cardioia.agents.orchestrator`` importa o SDK ``agents`` no
  topo do modulo. Se o SDK falhar, o backend **sobe** e a requisicao responde
  ``503 MODELO_INDISPONIVEL`` — em vez de derrubar o processo no import.
- **M2 — ``sys.path.append`` (nunca ``insert``).** A pasta ``src/agents/`` do repositorio
  nao pode sombrear o pacote ``agents`` do SDK. Mesma razao documentada no
  ``conftest.py`` da Fase 6.
- **M5 — caminhos resolvidos a partir da configuracao**, sem caminho absoluto da maquina.

Nota sobre ``disponibilidade``: usa ``importlib.util.find_spec``, que **localiza** o
modulo sem executa-lo. Assim o ``/health`` informa o estado da integracao sem pagar o
custo de importar pandas/scikit-learn/agents.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from types import ModuleType
from typing import Any

from ..config import Configuracoes
from ..contratos.erros import CodigoDeErro, ErroDaAPIException

__all__ = [
    "ModulosDaFase6",
    "disponibilidade",
    "importar",
    "limpar_cache",
    "pasta_de_artefatos",
    "pasta_do_codigo",
    "raiz_do_projeto_da_fase_6",
]

#: Subpasta do repositorio da Fase 6 que contem o pacote ``cardioia``.
SUBPSTA_DO_CODIGO = "src"

#: Subpasta com o artefato do modelo (mesmo nome de ``cardioia.config``).
SUBPSTA_DOS_ARTEFATOS = "models"

#: Modulos de terceiros exigidos pelo pipeline — checados **sem** importar.
MODULOS_EXIGIDOS: tuple[str, ...] = ("cardioia", "agents", "sklearn", "pandas", "joblib")


@dataclass(frozen=True)
class ModulosDaFase6:
    """Modulos da Fase 6 ja importados e prontos para uso."""

    predict: ModuleType
    risk_result: ModuleType
    orchestrator: ModuleType
    protocolos: ModuleType
    versao_do_pacote: str
    versao_do_sdk: str | None


#: Cache de modulos por caminho de ``src/`` (o pacote e um singleton do processo).
_CACHE_DE_MODULOS: dict[str, ModulosDaFase6] = {}


# --------------------------------------------------------------------------- #
# Caminhos (M5)
# --------------------------------------------------------------------------- #


def pasta_do_codigo(config: Configuracoes) -> Path:
    """``<fase_6>/src`` — onde vive o pacote ``cardioia``."""
    return config.pasta_da_fase_6 / SUBPSTA_DO_CODIGO


def pasta_de_artefatos(config: Configuracoes) -> Path:
    """``<fase_6>/models`` — onde ficam o ``.pkl`` e o metadata."""
    return config.pasta_da_fase_6 / SUBPSTA_DOS_ARTEFATOS


def raiz_do_projeto_da_fase_6(config: Configuracoes) -> Path:
    """Raiz do repositorio da Fase 6 (onde ficam ``data/`` e ``models/``).

    Passada explicitamente ao pipeline para que a Fase 6 **nao** precise adivinhar a
    raiz pelo diretorio de trabalho do processo (M5).
    """
    return config.pasta_da_fase_6


def _garantir_caminho(pasta: Path) -> None:
    """Coloca ``src/`` no **fim** do ``sys.path``, uma unica vez (M2).

    ``append`` (e nao ``insert``) porque ``src/`` contem uma pasta ``agents/`` que, se
    viesse primeiro, sombrearia o pacote ``agents`` do OpenAI Agents SDK.
    """
    texto = str(pasta)
    if texto not in sys.path:
        sys.path.append(texto)


# --------------------------------------------------------------------------- #
# Disponibilidade (barata — nao importa nada de pesado)
# --------------------------------------------------------------------------- #


def _tem_modulo(nome: str) -> bool:
    """``True`` se o modulo puder ser **localizado** (sem executa-lo)."""
    try:
        return find_spec(nome) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def disponibilidade(config: Configuracoes) -> dict[str, Any]:
    """Estado da integracao com a Fase 6 — **nunca** levanta excecao.

    Usa ``find_spec``: responde "daria para importar?" sem pagar o custo do import.
    """
    pasta = pasta_do_codigo(config)
    codigo_presente = pasta.is_dir()
    if codigo_presente:
        _garantir_caminho(pasta)

    modulos = {nome: _tem_modulo(nome) for nome in MODULOS_EXIGIDOS}
    faltando = [nome for nome, achado in modulos.items() if not achado]

    return {
        "pasta_do_codigo": str(pasta),
        "codigo_presente": codigo_presente,
        "modulos_encontrados": modulos,
        "faltando": faltando,
        "importavel": codigo_presente and not faltando,
    }


# --------------------------------------------------------------------------- #
# Import tardio (M1)
# --------------------------------------------------------------------------- #


def _versao_do_sdk(orchestrator: ModuleType) -> str | None:
    """Versao do OpenAI Agents SDK, quando a funcao da Fase 6 estiver disponivel."""
    funcao = getattr(orchestrator, "versao_do_sdk", None)
    if not callable(funcao):
        return None
    try:
        return str(funcao())
    except Exception:  # pragma: no cover - informacao acessoria
        return None


def importar(config: Configuracoes) -> ModulosDaFase6:
    """Importa os modulos da Fase 6 (uma vez por processo) e devolve-os.

    A pasta configurada entra no ``sys.path`` quando existe (M2), mas **nao** e
    pre-requisito: o pacote ``cardioia`` pode ja estar visivel de outra forma (instalado
    no ambiente ou por ``PYTHONPATH``). Quem decide e o **import** — abortar pela pasta
    recusaria ambientes que funcionam.

    Returns:
        :class:`ModulosDaFase6` com ``predict``, ``risk_result``, ``orchestrator`` e
        ``protocolos``.

    Raises:
        ErroDaAPIException: ``MODELO_INDISPONIVEL`` (HTTP 503) quando o import falha
            (codigo da Fase 6 ausente ou dependencia nao instalada). **O backend continua
            no ar**: a falha e reportada na requisicao (M1).
    """
    pasta = pasta_do_codigo(config)
    if pasta.is_dir():
        _garantir_caminho(pasta)

    chave = str(pasta)
    pronto = _CACHE_DE_MODULOS.get(chave)
    if pronto is not None:
        return pronto

    try:
        pacote = import_module("cardioia")
        predict = import_module("cardioia.ml.predict")
        risk_result = import_module("cardioia.schemas.risk_result")
        protocolos = import_module("cardioia.knowledge.protocols")
        orchestrator = import_module("cardioia.agents.orchestrator")
    except ImportError as erro:
        raise ErroDaAPIException(
            CodigoDeErro.MODELO_INDISPONIVEL,
            "Nao foi possivel carregar o pipeline da Fase 6.",
            detalhe=(
                f"{type(erro).__name__}: {erro}. Pasta configurada (PASTA_FASE_6): "
                f"'{pasta}'. Verifique se o codigo da Fase 6 esta la e se as dependencias "
                "estao instaladas (openai-agents, scikit-learn, pandas, joblib)."
            ),
        ) from erro

    modulos = ModulosDaFase6(
        predict=predict,
        risk_result=risk_result,
        orchestrator=orchestrator,
        protocolos=protocolos,
        versao_do_pacote=str(getattr(pacote, "__versao__", "") or ""),
        versao_do_sdk=_versao_do_sdk(orchestrator),
    )
    _CACHE_DE_MODULOS[chave] = modulos
    return modulos


def limpar_cache() -> None:
    """Descarta o cache de modulos (usado em teste; o ``sys.path`` nao e revertido)."""
    _CACHE_DE_MODULOS.clear()