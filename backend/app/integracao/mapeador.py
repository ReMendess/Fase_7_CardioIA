"""Mapeador de features: contrato fechado, **sem defaults** (N3, Decisao D4).

Funcao pura e testavel: nao acessa banco, nao chama o modelo, nao tem efeito colateral.

O contrato de entrada do modelo e **fechado**: exatamente as 10 colunas, com valores
numericos nao negativos. Campo ausente e campo desconhecido sao **erro** — nunca
preenchidos por padrao (Decisao D4, salvaguarda 1: o backend nao inventa valor clinico).

Por que esta funcao **delega** a validacao: ela ja existe em
:func:`app.dados.repositorios.assistencial.normalizar_features`, que espelha
``predict.validar_paciente`` da Fase 6. Reimplementar aqui criaria uma segunda fonte de
verdade — exatamente o que a Decisao D4 evita.

Os avisos de confiabilidade abaixo registram os achados **A3** e **A4** da Etapa A:
o backend precisa ser honesto sobre o que o modelo realmente mede.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..contratos.erros import CodigoDeErro, ErroDaAPIException
from ..dados.modelos import COLUNAS_DE_FEATURE
from ..dados.repositorios.assistencial import normalizar_features

__all__ = [
    "AVISO_DE_BAIXA_CONFIANCA_DE_TEMPERATURA",
    "AVISO_DE_ESCALA_AGREGADA",
    "AVISOS_DE_CONFIABILIDADE",
    "avisos_de_confiabilidade",
    "montar_caso_para_o_pipeline",
    "verificar_aderencia_ao_contrato",
]

#: Achado **A3**: a `temperatura` do gerador da Fase 6 e **ambiente** (media 24 C), mas a
#: semantica esperada da feature e **corporal** (~36-38 C). Um valor corporal cai na
#: **cauda** da distribuicao de treino. Nao e corrigivel sem alterar a Fase 6.
AVISO_DE_BAIXA_CONFIANCA_DE_TEMPERATURA = (
    "Feature de BAIXA CONFIANCA: 'temperatura'. O gerador da Fase 6 usa distribuicao de "
    "temperatura AMBIENTE (media ~24 C), embora a feature deva representar temperatura "
    "CORPORAL (~36-38 C). Um valor corporal cai na cauda da distribuicao de treino, e o "
    "modelo pode reagir de forma nao representativa."
)

#: Achado **A4**: 8 das 10 features nao sao medicoes individuais.
AVISO_DE_ESCALA_AGREGADA = (
    "Escala dos dados: 8 das 10 features NAO sao medicoes individuais. Cinco descrevem o "
    "contexto do episodio ('carga_sistema', 'tempo_espera', 'densidade_eventos', "
    "'eventos_24h', 'disponibilidade_recursos') e tres tem nome de media ('idade_media', "
    "'fc_media', 'spo2_media'). Leia o resultado como risco do EPISODIO assistencial, "
    "nao como prognostico individual."
)

#: Avisos acrescentados a **toda** resposta de decisao (N9 + contrato §8.1).
AVISOS_DE_CONFIABILIDADE: tuple[str, ...] = (
    AVISO_DE_BAIXA_CONFIANCA_DE_TEMPERATURA,
    AVISO_DE_ESCALA_AGREGADA,
)


def avisos_de_confiabilidade() -> list[str]:
    """Copia dos avisos de confiabilidade (lista nova a cada chamada)."""
    return list(AVISOS_DE_CONFIABILIDADE)


def montar_caso_para_o_pipeline(
    features: Mapping[str, Any], *, ordem: Sequence[str] | None = None
) -> dict[str, float]:
    """Valida as features e devolve o caso na **ordem do modelo**.

    Args:
        features: as 10 features informadas pela API (nomes do contrato).
        ordem: ordem esperada pelo modelo (``ArtefatoDoModelo.features``). Quando
            ``None``, usa a ordem canonica de :data:`COLUNAS_DE_FEATURE`.

    Returns:
        ``dict`` com exatamente as 10 features, numericas e nao negativas.

    Raises:
        ErroDaAPIException: campo ausente/desconhecido ou valor invalido
            (``PACIENTE_INVALIDO``); ordem do modelo incompativel com o contrato
            (``CONTRATO_VIOLADO``).
    """
    valores = normalizar_features(features)

    colunas = tuple(ordem) if ordem is not None else COLUNAS_DE_FEATURE
    inesperadas = [coluna for coluna in colunas if coluna not in valores]
    if inesperadas:
        # Acontece se o modelo for retreinado com outras colunas: falhar alto e melhor
        # do que reordenar errado e devolver um numero plausivel porem sem sentido.
        raise ErroDaAPIException(
            CodigoDeErro.CONTRATO_VIOLADO,
            "A ordem de features do modelo nao corresponde ao contrato da API.",
            detalhe=(
                "Colunas do modelo sem valor validado: "
                + ", ".join(inesperadas)
                + ". O contrato da API espera: "
                + ", ".join(COLUNAS_DE_FEATURE)
                + "."
            ),
        )

    return {coluna: valores[coluna] for coluna in colunas}


def verificar_aderencia_ao_contrato(features_do_modelo: Sequence[str]) -> None:
    """Confere se o modelo carregado usa **exatamente** as 10 features do contrato.

    Verificacao de *drift*: se a Fase 6 for retreinada com outra lista de features, o
    backend precisa falhar com mensagem clara em vez de alimentar o modelo errado.

    Raises:
        ErroDaAPIException: conjuntos de features diferentes (``CONTRATO_VIOLADO``).
    """
    esperadas = set(COLUNAS_DE_FEATURE)
    encontradas = {str(coluna) for coluna in features_do_modelo}
    if encontradas != esperadas:
        raise ErroDaAPIException(
            CodigoDeErro.CONTRATO_VIOLADO,
            "O modelo carregado nao usa o mesmo conjunto de features do contrato.",
            detalhe=(
                f"Somente no modelo: {sorted(encontradas - esperadas) or 'nada'}; "
                f"somente no contrato: {sorted(esperadas - encontradas) or 'nada'}."
            ),
        )
