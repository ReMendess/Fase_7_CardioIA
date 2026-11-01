"""Contratos transversais da API (envelope e erros).

Reexporta os dois modulos que compoem o contrato comum:

- :mod:`app.contratos.envelope` — ``RespostaAPI[T]`` e ``StatusDaResposta``;
- :mod:`app.contratos.erros` — ``CodigoDeErro``, ``ErroDaAPI`` e o mapeamento HTTP.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "assistencial",
    "assistente",
    "autenticacao",
    "envelope",
    "erros",
    "paginacao",
    "telemetria",
    "visao",
]

_SUBMODULOS = (
    "envelope",
    "erros",
    "autenticacao",
    "assistencial",
    "assistente",
    "paginacao",
    "telemetria",
    "visao",
)


def __getattr__(nome: str) -> Any:
    """Importa submódulos sob demanda (PEP 562), como no pacote ``cardioia`` da Fase 6."""
    if nome in _SUBMODULOS:
        modulo = import_module(f".{nome}", __name__)
        globals()[nome] = modulo
        return modulo
    raise AttributeError(f"module {__name__!r} has no attribute {nome!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
