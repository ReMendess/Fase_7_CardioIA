"""Base comum dos repositorios (``MODELO_DADOS.md`` §9, C1/C2).

**Decisao de arquitetura sobre erros:** os repositorios levantam
:class:`~app.contratos.erros.ErroDaAPIException` em violacao de integridade
(unicidade, FK) e em contrato invalido. Justificativa: a excecao ja carrega
**codigo de dominio + HTTP canonico**, entao o erro chega ao cliente com o codigo
correto **sem** uma camada extra de traducao — e sem uma terceira familia de
excecoes no projeto.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TypeVar

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from ...contratos.erros import CodigoDeErro, ErroDaAPIException

T = TypeVar("T")

__all__ = ["RepositorioBase", "validar_chaves"]


class RepositorioBase:
    """Guarda a sessao e concentra o ``commit`` (regra C2).

    Os endpoints **nao** confirmam transacao: quem faz isso e o repositorio.
    """

    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    # ------------------------------------------------------------------ #
    # Apoio
    # ------------------------------------------------------------------ #

    def _confirmar(self) -> None:
        """Confirma a transacao, traduzindo falhas do banco em erro de dominio.

        - **violacao de constraint** (UNIQUE, FK, CHECK, NOT NULL) -> ``CONFLITO`` (409);
        - **valor recusado na ligacao** (ex.: enum fora do dominio) -> ``CONTRATO_VIOLADO``
          (422). A ordem importa: ``IntegrityError`` e subclasse de ``StatementError``.
        """
        try:
            self.sessao.commit()
        except IntegrityError as erro:
            self.sessao.rollback()
            raise ErroDaAPIException(
                CodigoDeErro.CONFLITO,
                "Violacao de integridade no banco de dados.",
                detalhe=_resumo_do_erro(erro),
            ) from erro
        except StatementError as erro:
            self.sessao.rollback()
            raise ErroDaAPIException(
                CodigoDeErro.CONTRATO_VIOLADO,
                "Valor invalido para uma coluna do banco de dados.",
                detalhe=_resumo_do_erro(erro),
            ) from erro

    def _adicionar_e_confirmar(self, entidade: T) -> T:
        """Persiste uma entidade e devolve ela (com o id gerado)."""
        self.sessao.add(entidade)
        self._confirmar()
        self.sessao.refresh(entidade)
        return entidade

    def _remover_e_confirmar(self, entidade: T) -> None:
        """Remove uma entidade e confirma."""
        self.sessao.delete(entidade)
        self._confirmar()


def _resumo_do_erro(erro: IntegrityError) -> str:
    """Mensagem curta do erro de integridade (sem despejar o SQL inteiro)."""
    texto = str(getattr(erro, "orig", erro))
    return texto[:200]


def validar_chaves(classe: type[Any], dados: Mapping[str, Any], rotulo: str) -> dict[str, Any]:
    """Confere que as chaves informadas existem como coluna do modelo.

    Postura alinhada ao contrato do projeto (``extra="forbid"``): **campo desconhecido
    e erro**, nunca ignorado em silencio — um ``typo`` viraria perda de dado.

    Raises:
        ErroDaAPIException: chave desconhecida (``CONTRATO_VIOLADO``).
    """
    colunas = {coluna.name for coluna in inspect(classe).columns}
    desconhecidas = sorted(chave for chave in dados if chave not in colunas)
    if desconhecidas:
        raise ErroDaAPIException(
            CodigoDeErro.CONTRATO_VIOLADO,
            f"Campos desconhecidos em {rotulo}: {', '.join(desconhecidas)}.",
            detalhe=f"Colunas validas: {', '.join(sorted(colunas))}.",
        )
    return dict(dados)


def montar_filhos(
    classe: type[Any], itens: Sequence[Mapping[str, Any]], rotulo: str
) -> list[Any]:
    """Instancia entidades filhas validando as chaves de cada uma."""
    return [classe(**validar_chaves(classe, item, f"{rotulo}[{indice}]")) for indice, item in enumerate(itens)]
