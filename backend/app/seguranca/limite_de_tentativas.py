"""Limitador de tentativas de login (em memoria, por processo).

⚠️ **Limitacao declarada** (``MODELO_DADOS.md`` §8.1 L6): **nenhuma** biblioteca de rate
limiting esta instalada, entao o contador vive na memoria do processo. Consequencias
honestas:

- reinicia quando o servidor reinicia;
- **nao** e compartilhado entre workers.

Mesmo assim resolve o caso concreto do MVP: forca bruta por tentativa e erro. Para
producao, usar armazenamento compartilhado (Redis) ou limitar na borda.

**Thread-safety:** os endpoints sincronos do FastAPI rodam em *threadpool*, portanto o
dicionario e protegido por :class:`threading.Lock`.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

__all__ = [
    "JANELA_PADRAO_EM_SEGUNDOS",
    "TENTATIVAS_PADRAO",
    "LimitadorDeTentativas",
]

#: Numero de falhas que dispara o bloqueio dentro da janela.
TENTATIVAS_PADRAO = 5

#: Tamanho da janela deslizante, em segundos.
JANELA_PADRAO_EM_SEGUNDOS = 300


def _agora() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _Registro:
    """Instantes das falhas recentes de uma chave."""

    falhas: list[datetime] = field(default_factory=list)


class LimitadorDeTentativas:
    """Conta falhas de login por chave (ex.: ``email|ip``) em janela deslizante."""

    def __init__(
        self,
        *,
        maximo: int = TENTATIVAS_PADRAO,
        janela_em_segundos: int = JANELA_PADRAO_EM_SEGUNDOS,
    ) -> None:
        if maximo < 1:
            raise ValueError("'maximo' deve ser >= 1.")
        if janela_em_segundos < 1:
            raise ValueError("'janela_em_segundos' deve ser >= 1.")

        self.maximo = maximo
        self.janela = timedelta(seconds=janela_em_segundos)
        self._registros: dict[str, _Registro] = {}
        self._trava = threading.Lock()

    # ------------------------------------------------------------------ #
    # Internos
    # ------------------------------------------------------------------ #

    def _podar(self, registro: _Registro, agora: datetime) -> None:
        """Descarta falhas fora da janela (a janela e deslizante)."""
        limite = agora - self.janela
        registro.falhas = [quando for quando in registro.falhas if quando > limite]

    # ------------------------------------------------------------------ #
    # API
    # ------------------------------------------------------------------ #

    def registrar_falha(self, chave: str, *, agora: datetime | None = None) -> int:
        """Registra uma falha e devolve o total de falhas na janela."""
        momento = agora or _agora()
        with self._trava:
            registro = self._registros.setdefault(chave, _Registro())
            self._podar(registro, momento)
            registro.falhas.append(momento)
            return len(registro.falhas)

    def limpar(self, chave: str) -> None:
        """Zera o contador da chave (usado no login bem-sucedido)."""
        with self._trava:
            self._registros.pop(chave, None)

    def esta_bloqueado(self, chave: str, *, agora: datetime | None = None) -> bool:
        """``True`` quando a chave atingiu o maximo de falhas na janela."""
        momento = agora or _agora()
        with self._trava:
            registro = self._registros.get(chave)
            if registro is None:
                return False
            self._podar(registro, momento)
            return len(registro.falhas) >= self.maximo

    def segundos_restantes(self, chave: str, *, agora: datetime | None = None) -> int:
        """Segundos ate a falha mais antiga sair da janela (0 se nao bloqueado)."""
        momento = agora or _agora()
        with self._trava:
            registro = self._registros.get(chave)
            if registro is None:
                return 0
            self._podar(registro, momento)
            if len(registro.falhas) < self.maximo:
                return 0
            libera_em = registro.falhas[0] + self.janela
            return max(0, int((libera_em - momento).total_seconds()))

    def limpar_tudo(self) -> None:
        """Descarta todos os registros (usado em teste)."""
        with self._trava:
            self._registros.clear()

    @property
    def chaves_rastreadas(self) -> int:
        """Quantidade de chaves com registro (observabilidade simples)."""
        with self._trava:
            return len(self._registros)
