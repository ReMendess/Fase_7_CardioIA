"""Repositorios do backend CardioIA — um por agregado (``MODELO_DADOS.md`` §9, C1).

| Agregado | Repositorio | Modulo |
|---|---|---|
| Conta de acesso | ``UsuarioRepositorio`` | :mod:`~app.dados.repositorios.identidade` |
| Sessao (refresh token) | ``SessaoRepositorio`` | :mod:`~app.dados.repositorios.identidade` |
| Paciente | ``PacienteRepositorio`` | :mod:`~app.dados.repositorios.assistencial` |
| Avaliacao de risco | ``AvaliacaoRepositorio`` | :mod:`~app.dados.repositorios.assistencial` |
| Telemetria IoT | ``MonitoramentoRepositorio`` | :mod:`~app.dados.repositorios.telemetria` |
| Analise de imagem | ``AnaliseDeImagemRepositorio`` | :mod:`~app.dados.repositorios.analises` |
| Conversa | ``ConversaRepositorio`` | :mod:`~app.dados.repositorios.conversas` |
| Auditoria | ``AuditoriaRepositorio`` | :mod:`~app.dados.repositorios.auditoria` |
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "analises",
    "assistencial",
    "auditoria",
    "base",
    "conversas",
    "identidade",
    "telemetria",
]

_SUBMODULOS = (
    "base",
    "identidade",
    "assistencial",
    "telemetria",
    "analises",
    "conversas",
    "auditoria",
)


def __getattr__(nome: str) -> Any:
    """Importa submodulos sob demanda (PEP 562)."""
    if nome in _SUBMODULOS:
        modulo = import_module(f".{nome}", __name__)
        globals()[nome] = modulo
        return modulo
    raise AttributeError(f"module {__name__!r} has no attribute {nome!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
