"""Cache do artefato do modelo da Fase 6 (mitigacao **M3**).

Por que existe: ``predict.carregar_modelo`` faz ``joblib.load`` de um ``.pkl`` de ~4,7 MB.
Medicao neste ambiente: ~0,8 s na primeira carga (inclui importar scikit-learn/pandas) e
~0,17 s por avaliacao **depois de quente**. Sem cache, cada requisicao pagaria a carga.

Sobre "cache no startup" (M3) x "o backend sobe sempre" (M1): as duas exigencias convivem
porque :meth:`CacheDoModelo.aquecer` e **best-effort** — tenta carregar no boot e apenas
registra um aviso se falhar. O boot **nunca** e abortado por causa do artefato, e a
primeira requisicao carrega o que faltar.

Seguranca de concorrencia: os endpoints sincronos do FastAPI rodam em *threadpool*, entao
o carregamento usa *double-checked locking* — duas requisicoes simultaneas nao carregam
dois estimadores.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..config import Configuracoes
from ..contratos.erros import ErroDaAPIException
from .fase_6 import (
    importar,
    pasta_de_artefatos,
    raiz_do_projeto_da_fase_6,
)
from .traducao import traduzir

__all__ = ["ArtefatoDoModelo", "CacheDoModelo"]

registrador = logging.getLogger("cardioia.backend.integracao")

#: Nome do arquivo do estimador (mesmo valor de ``cardioia.config``).
NOME_DO_ARQUIVO_DO_MODELO = "modelo_pico_risco.pkl"


@dataclass(frozen=True)
class ArtefatoDoModelo:
    """Artefato carregado: metadados + estimador + o contrato de entrada do modelo."""

    metadados: dict[str, Any]
    estimador: Any
    features: tuple[str, ...]
    nome_do_modelo: str
    classe_do_estimador: str
    limiar_decisao: float
    sha256_da_base: str | None
    caminho: str
    carregado_em: datetime


class CacheDoModelo:
    """Cache de processo do artefato — carregado no maximo uma vez."""

    def __init__(self) -> None:
        self._artefato: ArtefatoDoModelo | None = None
        self._trava = threading.Lock()

    # ------------------------------------------------------------------ #
    # Estado
    # ------------------------------------------------------------------ #

    @property
    def carregado(self) -> bool:
        """``True`` quando o artefato ja esta em memoria."""
        return self._artefato is not None

    def limpar(self) -> None:
        """Descarta o artefato (usado em teste)."""
        with self._trava:
            self._artefato = None

    # ------------------------------------------------------------------ #
    # Carga
    # ------------------------------------------------------------------ #

    def obter(self, config: Configuracoes) -> ArtefatoDoModelo:
        """Devolve o artefato, carregando-o na primeira chamada.

        Raises:
            ErroDaAPIException: ``MODELO_INDISPONIVEL`` (503) se o artefato ou o codigo
                da Fase 6 nao existirem; ``MODELO_INCOMPATIVEL`` (500) se o ``.pkl`` nao
                puder ser desserializado neste ambiente.
        """
        pronto = self._artefato
        if pronto is not None:
            return pronto

        with self._trava:
            # Segunda checagem: outra thread pode ter carregado enquanto esperavamos.
            if self._artefato is None:
                self._artefato = self._carregar(config)
            return self._artefato

    def aquecer(self, config: Configuracoes) -> bool:
        """Tenta carregar o artefato antecipadamente (M3) — **nunca** levanta.

        Returns:
            ``True`` se o artefato ficou em memoria; ``False`` se algo falhou (o motivo
            vai para o log e a requisicao que precisar do modelo reportara o erro).
        """
        try:
            self.obter(config)
        except ErroDaAPIException as erro:
            registrador.warning(
                "Nao foi possivel aquecer o cache do modelo (%s): %s",
                erro.codigo.value,
                erro.mensagem,
            )
            return False
        except Exception as erro:  # pragma: no cover - salvaguarda
            registrador.warning("Falha inesperada ao aquecer o cache: %s", erro)
            return False
        return True

    def _carregar(self, config: Configuracoes) -> ArtefatoDoModelo:
        """Carrega metadados e estimador usando as funcoes da propria Fase 6."""
        modulos = importar(config)  # traduz ImportError -> MODELO_INDISPONIVEL (M1)
        predict = modulos.predict

        pasta = pasta_de_artefatos(config)
        raiz = raiz_do_projeto_da_fase_6(config)
        try:
            metadados = predict.carregar_metadados(pasta_modelos=pasta, raiz=raiz)
            estimador = predict.carregar_modelo(pasta_modelos=pasta, raiz=raiz)
        except Exception as erro:
            raise traduzir(
                erro, modulos=modulos, contexto=f"carregando o artefato de '{pasta}'"
            ) from erro

        features = tuple(
            str(coluna) for coluna in predict.features_do_modelo(metadados, estimador)
        )
        classe = type(estimador).__name__
        return ArtefatoDoModelo(
            metadados=metadados,
            estimador=estimador,
            features=features,
            nome_do_modelo=str(metadados.get("nome_do_modelo") or classe),
            classe_do_estimador=str(metadados.get("classe_do_estimador") or classe),
            limiar_decisao=float(
                metadados.get("limiar_de_decisao") or getattr(predict, "LIMIAR_DE_DECISAO", 0.5)
            ),
            sha256_da_base=metadados.get("sha256_da_base_usada"),
            caminho=str(pasta / NOME_DO_ARQUIVO_DO_MODELO),
            carregado_em=datetime.now(timezone.utc),
        )
