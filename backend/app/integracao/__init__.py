"""Integracao com os modulos das Fases 3 a 6 (item 4 da Etapa C).

Submodulos:

- :mod:`~app.integracao.fase_6` — ponte com o pacote ``cardioia``: ``sys.path`` + import
  tardio + verificacao de disponibilidade;
- :mod:`~app.integracao.traducao` — excecoes tipadas da Fase 6 -> codigos de erro da API;
- :mod:`~app.integracao.modelo` — cache do artefato do modelo (evita reler 4,7 MB por
  requisicao);
- :mod:`~app.integracao.mapeador` — mapeador de features (contrato fechado, sem defaults).

Decisao estrutural (``DECISOES_ARQUITETURAIS.md`` §3.3): **import direto** do pacote
``cardioia`` dentro do backend (alternativa A). Nenhuma logica da Fase 6 e reescrita
aqui — este pacote apenas **liga** o backend ao que ja existe e foi testado.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["fase_6", "mapeador", "modelo", "traducao"]

_SUBMODULOS = ("fase_6", "traducao", "modelo", "mapeador")


def __getattr__(nome: str) -> Any:
    """Importa submodulos sob demanda (PEP 562)."""
    if nome in _SUBMODULOS:
        modulo = import_module(f".{nome}", __name__)
        globals()[nome] = modulo
        return modulo
    raise AttributeError(f"module {__name__!r} has no attribute {nome!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
