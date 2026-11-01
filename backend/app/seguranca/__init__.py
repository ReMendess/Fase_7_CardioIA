"""Camada de seguranca do backend CardioIA (Fase 7).

Modulos:

- :mod:`~app.seguranca.senhas` — hash e verificacao com **bcrypt**;
- :mod:`~app.seguranca.tokens` — **access token JWT** (PyJWT) e **refresh opaco**;
- :mod:`~app.seguranca.limite_de_tentativas` — limitador de tentativas de login;
- :mod:`~app.seguranca.dependencias` — dependencias do FastAPI (autenticacao e RBAC).

Decisao de bibliotecas (``DECISOES_ARQUITETURAIS.md``, D3): **PyJWT + bcrypt**, ambas ja
instaladas. ``python-jose`` e ``passlib`` **nao** estao disponiveis neste ambiente.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["dependencias", "limite_de_tentativas", "senhas", "tokens"]

_SUBMODULOS = ("senhas", "tokens", "limite_de_tentativas", "dependencias")


def __getattr__(nome: str) -> Any:
    """Importa submodulos sob demanda (PEP 562)."""
    if nome in _SUBMODULOS:
        modulo = import_module(f".{nome}", __name__)
        globals()[nome] = modulo
        return modulo
    raise AttributeError(f"module {__name__!r} has no attribute {nome!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
