"""Camada de persistencia do backend CardioIA (Fase 7).

Implementa a decisao **D3** aprovada: **SQLite + SQLAlchemy 2.0**, encapsulado por
repositorios, de modo que a troca para PostgreSQL seja uma mudanca de
``DATABASE_URL`` (``MODELO_DADOS.md`` §7).

Modulos:

- :mod:`~app.dados.base` — tipos, engine, sessao e a dependencia do FastAPI;
- :mod:`~app.dados.enums` — enums persistidos;
- :mod:`~app.dados.modelos` — as tabelas;
- :mod:`~app.dados.esquema` — criacao do esquema e controle de versao;
- :mod:`~app.dados.repositorios` — acesso a dados por agregado.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["base", "enums", "esquema", "modelos", "repositorios"]

_SUBMODULOS = ("base", "enums", "modelos", "esquema", "repositorios")


def __getattr__(nome: str) -> Any:
    """Importa submodulos sob demanda (PEP 562), como no pacote ``cardioia``."""
    if nome in _SUBMODULOS:
        modulo = import_module(f".{nome}", __name__)
        globals()[nome] = modulo
        return modulo
    raise AttributeError(f"module {__name__!r} has no attribute {nome!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
