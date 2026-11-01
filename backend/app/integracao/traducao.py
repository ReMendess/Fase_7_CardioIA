"""Traducao das excecoes tipadas da Fase 6 para o contrato de erro da Fase 7.

Duas regras do contrato guiam este modulo:

- **N5** (``CONTRATOS_API.md`` §9): a **mensagem original** da Fase 6 e preservada em
  ``detalhe``. Sem isso, "modelo indisponivel" esconderia a causa real (ex.: pickle
  treinado em outra versao do scikit-learn).
- **falha nunca vira sucesso**: toda excecao nao mapeada vira ``ERRO_INTERNO`` (500) —
  nunca uma resposta vazia ou um resultado inventado.

Ordem das regras **importa**: as subclasses vem antes de :class:`ErroDePrevisao`, que e
a base delas.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from ..contratos.erros import CodigoDeErro, ErroDaAPIException
from .fase_6 import ModulosDaFase6

__all__ = ["RegraDeTraducao", "regras", "traduzir"]


@dataclass(frozen=True)
class RegraDeTraducao:
    """Associa um tipo de excecao da Fase 6 a um codigo de erro da API."""

    tipo: type[BaseException]
    codigo: CodigoDeErro
    mensagem: str


def regras(modulos: ModulosDaFase6) -> tuple[RegraDeTraducao, ...]:
    """Regras de traducao, na ordem em que devem ser avaliadas.

    A ordem segue a hierarquia das excecoes: as **subclasses primeiro**.
    """
    predict = modulos.predict
    protocolos = modulos.protocolos
    return (
        RegraDeTraducao(
            predict.PacienteInvalidoError,
            CodigoDeErro.PACIENTE_INVALIDO,
            "Os dados informados nao atendem ao contrato do modelo.",
        ),
        RegraDeTraducao(
            protocolos.DadosDoPacienteInvalidosError,
            CodigoDeErro.DADOS_DO_PACIENTE_INVALIDOS,
            "Os dados do paciente nao permitem avaliar os protocolos com seguranca.",
        ),
        RegraDeTraducao(
            protocolos.BaseDeConhecimentoInvalidaError,
            CodigoDeErro.BASE_DE_PROTOCOLOS_INVALIDA,
            "A base oficial de protocolos nao corresponde ao contrato esperado.",
        ),
        RegraDeTraducao(
            predict.ModeloNaoEncontradoError,
            CodigoDeErro.MODELO_INDISPONIVEL,
            "O artefato do modelo nao esta disponivel.",
        ),
        RegraDeTraducao(
            predict.ModeloIncompativelError,
            CodigoDeErro.MODELO_INCOMPATIVEL,
            "O artefato do modelo existe, mas nao pode ser lido neste ambiente.",
        ),
        RegraDeTraducao(
            predict.ErroDePrevisao,
            CodigoDeErro.FALHA_DE_PREVISAO,
            "Falha ao executar a previsao do modelo.",
        ),
        RegraDeTraducao(
            ValidationError,
            CodigoDeErro.CONTRATO_VIOLADO,
            "O pipeline da Fase 6 devolveu um contrato invalido.",
        ),
    )


def _detalhe(excecao: BaseException, contexto: str | None) -> str:
    """Mensagem de detalhe com o texto original da Fase 6 (N5)."""
    original = f"{type(excecao).__name__}: {excecao}"
    return f"{contexto} — {original}" if contexto else original


def traduzir(
    excecao: BaseException,
    *,
    modulos: ModulosDaFase6 | None = None,
    contexto: str | None = None,
) -> ErroDaAPIException:
    """Converte uma excecao em :class:`ErroDaAPIException`.

    Args:
        excecao: excecao capturada ao chamar o pipeline da Fase 6.
        modulos: modulos da Fase 6 (fornecem os tipos das excecoes). Quando ``None``,
            apenas as regras genericas (``ImportError``) se aplicam.
        contexto: o que se estava fazendo (ex.: ``"executando o pipeline"``) — entra no
            ``detalhe`` para tornar o log util.

    Returns:
        A excecao de API correspondente. Nunca devolve ``None``: uma excecao
        desconhecida vira ``ERRO_INTERNO``.
    """
    if isinstance(excecao, ErroDaAPIException):
        # Ja esta no contrato: nao traduzir de novo (evita perder codigo e mensagem).
        return excecao

    if modulos is not None:
        for regra in regras(modulos):
            if isinstance(excecao, regra.tipo):
                return ErroDaAPIException(
                    regra.codigo, regra.mensagem, detalhe=_detalhe(excecao, contexto)
                )

    if isinstance(excecao, ImportError):
        return ErroDaAPIException(
            CodigoDeErro.MODELO_INDISPONIVEL,
            "Nao foi possivel carregar o pipeline da Fase 6.",
            detalhe=_detalhe(excecao, contexto),
        )

    return ErroDaAPIException(
        CodigoDeErro.ERRO_INTERNO,
        "Falha inesperada ao executar o pipeline da Fase 6.",
        detalhe=_detalhe(excecao, contexto),
    )
