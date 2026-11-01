"""Rotas HTTP do backend CardioIA (Fase 7).

Etapa C: ``saude`` (item 1), ``auth`` (item 3), ``pacientes`` e ``avaliacoes`` (item 4),
``iot`` (item 5). Os demais routers (imagens, chat) entram nos itens 6 e 7. ``apoio`` nao
e um router: reune os helpers compartilhados (metadados, IP, papeis e auditoria).
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "apoio",
    "assistente",
    "auth",
    "avaliacoes",
    "imagens",
    "iot",
    "pacientes",
    "saude",
]

_SUBMODULOS = (
    "apoio",
    "assistente",
    "auth",
    "avaliacoes",
    "imagens",
    "iot",
    "pacientes",
    "saude",
)


def __getattr__(nome: str) -> Any:
    """Importa submódulos sob demanda (PEP 562)."""
    if nome in _SUBMODULOS:
        modulo = import_module(f".{nome}", __name__)
        globals()[nome] = modulo
        return modulo
    raise AttributeError(f"module {__name__!r} has no attribute {nome!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
