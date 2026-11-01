"""Rotas de avaliacao de risco (``CONTRATOS_API.md`` §8).

| Metodo | Rota | Papel minimo | `dados` |
|---|---|---|---|
| `POST` | `/avaliacoes` | `MEDICO` | `RespostaDaExecucao` (**Fase 6 integral**) |
| `GET` | `/avaliacoes` | `MEDICO` \\| `ADMIN` | lista resumida |
| `GET` | `/avaliacoes/{id_execucao}` | `MEDICO` \\| `ADMIN` | `ResultadoDeAvaliacao` |

Decisoes que importam:

- **N2** — o `id_execucao` do envelope **e** o da Fase 6 (chave de correlacao API ↔ banco).
- **A Fase 6 nao levanta excecao quando a execucao falha**: devolve `status=ERRO` com o
  motivo em `erros` e a trilha em `passos`. Capturar excecao **nao basta** — o endpoint
  traduz o `status` e repassa `erros`, preservando o contrato integral em `dados`, porque
  a trilha e o que explica *onde* quebrou.
- **HTTP 200 mesmo com envelope `ERRO`**: o HTTP responde "a avaliacao rodou e foi
  registrada"; o campo `status` do envelope responde "qual foi o resultado". Mesma logica
  de `/health` quando devolve `CONCLUIDO_COM_RESSALVAS`.
- **M4** — modo `simulado` por padrao; `real` exige `OPENAI_API_KEY`, senao `501`.
- **M3** — o artefato vem do cache do `state`: o `.pkl` nao e relido por requisicao.
"""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..config import Configuracoes
from ..contratos.assistencial import (
    PedidoDeAvaliacao,
    ResultadoDeAvaliacao,
    ResumoDeAvaliacao,
)
from ..contratos.envelope import (
    STATUS_COM_SUCESSO,
    RespostaAPI,
    StatusDaResposta,
    resposta_de_erro,
    resposta_de_sucesso,
)
from ..contratos.erros import CodigoDeErro, ErroDaAPI, ErroDaAPIException
from ..contratos.paginacao import LIMITE_MAXIMO_DE_PAGINA, LIMITE_PADRAO_DE_PAGINA
from ..dados.base import get_sessao
from ..dados.enums import ModoDoPipeline
from ..dados.modelos import AvaliacaoDeRisco
from ..dados.repositorios.assistencial import AvaliacaoRepositorio
from ..integracao.fase_6 import importar, pasta_de_artefatos, raiz_do_projeto_da_fase_6
from ..integracao.mapeador import (
    avisos_de_confiabilidade,
    montar_caso_para_o_pipeline,
    verificar_aderencia_ao_contrato,
)
from ..integracao.modelo import CacheDoModelo
from ..integracao.traducao import traduzir
from .apoio import (
    LeituraClinica,
    SomenteMedico,
    ip_do_cliente,
    metadados_da_resposta,
    registrar_auditoria,
)
from .pacientes import buscar_paciente_ou_falhar

__all__ = ["router"]

router = APIRouter(prefix="/avaliacoes", tags=["avaliacoes"])

ACAO_AVALIACAO = "avaliar_risco"
ENTIDADE = "avaliacoes_de_risco"

#: Variavel de ambiente exigida pelo modo real (mesmo nome usado pela Fase 6).
VARIAVEL_DA_CHAVE = "OPENAI_API_KEY"

_MENSAGEM_SEM_CHAVE = (
    "O modo real exige OPENAI_API_KEY configurada no ambiente. "
    "Sem a chave, use o modo 'simulado' (padrao)."
)


# --------------------------------------------------------------------------- #
# Apoio
# --------------------------------------------------------------------------- #


def _resumo(avaliacao: AvaliacaoDeRisco) -> ResumoDeAvaliacao:
    """Item da listagem a partir do registro persistido."""
    return ResumoDeAvaliacao(
        id_execucao=avaliacao.id_execucao,
        id_paciente=avaliacao.id_paciente,
        status=avaliacao.status,
        modo=avaliacao.modo,
        origem_dos_dados=avaliacao.origem_dos_dados,
        criado_em=avaliacao.criado_em,
        probabilidade_risco=avaliacao.probabilidade_risco,
        pico_risco_previsto=avaliacao.pico_risco_previsto,
        classificacao_risco=avaliacao.classificacao_risco,
        modelo_utilizado=avaliacao.modelo_utilizado,
    )


def _resultado(avaliacao: AvaliacaoDeRisco) -> ResultadoDeAvaliacao:
    """Historico auditavel: metadados + contrato integral persistido."""
    return ResultadoDeAvaliacao(
        id_execucao=avaliacao.id_execucao,
        id_paciente=avaliacao.id_paciente,
        id_usuario=avaliacao.id_usuario,
        status=avaliacao.status,
        modo=avaliacao.modo,
        origem_dos_dados=avaliacao.origem_dos_dados,
        criado_em=avaliacao.criado_em,
        sha256_da_base_usada=avaliacao.sha256_da_base_usada,
        resposta=dict(avaliacao.resposta_json or {}),
    )


def _erros_do_contrato(textos: list[str]) -> list[ErroDaAPI]:
    """Converte os erros textuais da Fase 6 em erros do contrato.

    O contrato da Fase 6 carrega erros como **texto** (``erros: list[str]``), sem codigo.
    Por isso o codigo emitido e generico (``FALHA_DE_PREVISAO``) e a mensagem e preservada
    na integra — inventar um codigo por analise de texto seria fragil.
    """
    return [
        ErroDaAPI(codigo=CodigoDeErro.FALHA_DE_PREVISAO, mensagem=texto) for texto in textos
    ]


def _envelope(
    *,
    status: StatusDaResposta,
    contrato: dict[str, Any],
    dados: Any,
    config: Configuracoes,
    id_execucao: str,
) -> RespostaAPI[Any]:
    """Monta o envelope de uma avaliacao, com sucesso **ou** falha.

    Regras aplicadas aqui (uma unica vez, para `POST` e `GET` nao divergirem):

    - ``avisos`` = avisos da Fase 6 **+** os achados A3/A4 (N9);
    - ``limitacoes`` = as da Fase 6, nunca reescritas (N8);
    - ``id_execucao`` = o mesmo da Fase 6 (N2);
    - em falha, o contrato integral continua em ``dados`` (a trilha explica *onde*
      quebrou) e os motivos vao para ``erros``.
    """
    comuns: dict[str, Any] = {
        "avisos": [*contrato.get("avisos", []), *avisos_de_confiabilidade()],
        "limitacoes": list(contrato.get("limitacoes") or []),
        "metadados": metadados_da_resposta(config),
        "id_execucao": id_execucao,
    }

    if status in STATUS_COM_SUCESSO:
        return resposta_de_sucesso(dados, status=status, **comuns)

    erros = _erros_do_contrato(list(contrato.get("erros") or []))
    if not erros:
        # Salvaguarda do historico: um registro antigo pode nao ter o contrato salvo. O
        # envelope **nao pode** ficar sem erro (R1: falha nunca fica muda).
        erros = [
            ErroDaAPI(
                codigo=CodigoDeErro.FALHA_DE_PREVISAO,
                mensagem=(
                    "A avaliacao foi registrada com falha, mas o detalhe nao esta "
                    "disponivel no historico."
                ),
            )
        ]
    return resposta_de_erro(erros, dados=dados, status=status, **comuns)


# --------------------------------------------------------------------------- #
# POST /avaliacoes
# --------------------------------------------------------------------------- #


@router.post(
    "",
    response_model=RespostaAPI[dict[str, Any]],
    summary="Executa o pipeline da Fase 6 e registra a avaliacao",
    description=(
        "As 10 features sao **obrigatorias** e nenhum valor e preenchido por padrao. "
        "O `dados` devolve o contrato integral da Fase 6, com o mesmo `id_execucao` "
        "persistido. O envelope pode vir com `status=ERRO` e HTTP 200: nesse caso a "
        "execucao rodou, falhou e foi registrada — o motivo esta em `erros`."
    ),
)
def avaliar(
    pedido: PedidoDeAvaliacao,
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    usuario: SomenteMedico,
) -> RespostaAPI[dict[str, Any]]:
    """Executa o pipeline multiagente e persiste o agregado da avaliacao."""
    config: Configuracoes = request.app.state.configuracoes

    # 1) M1: import tardio — se o SDK/codigo faltar, e 503 e o servidor continua no ar.
    modulos = importar(config)

    # 2) M4: o modo real precisa da chave. Falhar aqui da um 501 claro — e antes de gastar
    #    tempo no pipeline, que reportaria o mesmo problema como texto em `erros`.
    if pedido.modo is ModoDoPipeline.REAL and not os.environ.get(VARIAVEL_DA_CHAVE):
        raise ErroDaAPIException(
            CodigoDeErro.NAO_CONFIGURADO,
            _MENSAGEM_SEM_CHAVE,
            campo="modo",
            detalhe=f"Variavel de ambiente ausente: {VARIAVEL_DA_CHAVE}.",
        )

    # 3) O paciente precisa existir e estar ativo.
    paciente = buscar_paciente_ou_falhar(sessao, pedido.id_paciente)
    if not paciente.ativo:
        raise ErroDaAPIException(
            CodigoDeErro.CONFLITO,
            "Paciente inativo nao pode receber novas avaliacoes.",
            campo="id_paciente",
            detalhe="Reative o paciente antes de avaliar.",
        )

    # 4) M3: artefato do cache. Levanta 503/500 quando indisponivel ou incompativel.
    cache: CacheDoModelo = request.app.state.cache_do_modelo
    artefato = cache.obter(config)
    verificar_aderencia_ao_contrato(artefato.features)

    # 5) Contrato fechado, sem defaults: nada invalido chega ao modelo.
    caso = montar_caso_para_o_pipeline(pedido.features, ordem=artefato.features)

    # 6) Execucao. A Fase 6 devolve falha como conteudo (nao como excecao); excecoes
    #    inesperadas sao traduzidas para o contrato de erro (N5).
    try:
        resposta = modulos.orchestrator.executar_pipeline(
            caso,
            modo=pedido.modo.value,
            raiz=str(raiz_do_projeto_da_fase_6(config)),
            pasta_modelos=str(pasta_de_artefatos(config)),
        )
    except Exception as erro:
        raise traduzir(erro, modulos=modulos, contexto="executando o pipeline") from erro

    contrato: dict[str, Any] = resposta.model_dump(mode="json")
    status = StatusDaResposta(resposta.status.value)

    # 7) Persistencia do agregado (avaliacao + filhas em uma transacao).
    AvaliacaoRepositorio(sessao).criar(
        id_execucao=resposta.id_execucao,
        id_paciente=paciente.id,
        id_usuario=usuario.id,
        features=caso,
        origem_dos_dados=pedido.origem_dos_dados,
        status=status,
        modo=pedido.modo,
        diagnostico=contrato.get("diagnostico"),
        protocolos=contrato.get("protocolos") or [],
        indicadores=contrato.get("indicadores") or [],
        passos=contrato.get("passos") or [],
        resposta=contrato,
        avisos=contrato.get("avisos") or [],
        erros=contrato.get("erros") or [],
        agente_final=contrato.get("agente_final"),
        versao_do_sdk=contrato.get("versao_do_sdk"),
        duracao_segundos=contrato.get("duracao_segundos"),
    )
    registrar_auditoria(
        sessao,
        acao=ACAO_AVALIACAO,
        entidade=ENTIDADE,
        id_usuario=usuario.id,
        id_entidade=resposta.id_execucao,
        ip=ip_do_cliente(request),
        detalhe={
            "status": status.value,
            "modo": pedido.modo.value,
            "origem_dos_dados": pedido.origem_dos_dados.value,
        },
    )

    # 8) Envelope unico para sucesso e falha (ver `_envelope`).
    return _envelope(
        status=status,
        contrato=contrato,
        dados=contrato,
        config=config,
        id_execucao=resposta.id_execucao,
    )


# --------------------------------------------------------------------------- #
# GET /avaliacoes
# --------------------------------------------------------------------------- #


@router.get(
    "",
    response_model=RespostaAPI[list[ResumoDeAvaliacao]],
    summary="Lista avaliacoes (paginado)",
    description=(
        "Mais recentes primeiro. Filtros `status` e `id_paciente` podem ser combinados. "
        "Se `len(itens) < limite`, nao ha proxima pagina."
    ),
)
def listar(
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    usuario: LeituraClinica,
    limite: Annotated[int, Query(ge=1, le=LIMITE_MAXIMO_DE_PAGINA)] = LIMITE_PADRAO_DE_PAGINA,
    deslocamento: Annotated[int, Query(ge=0)] = 0,
    status_filtro: Annotated[
        StatusDaResposta | None,
        Query(alias="status", description="Filtra pelo status do envelope."),
    ] = None,
    id_paciente: Annotated[
        str | None, Query(description="Filtra pelo paciente (historico).")
    ] = None,
) -> RespostaAPI[list[ResumoDeAvaliacao]]:
    """Lista as avaliacoes registradas, em formato resumido."""
    config: Configuracoes = request.app.state.configuracoes
    avaliacoes = AvaliacaoRepositorio(sessao).listar(
        status=status_filtro,
        id_paciente=id_paciente,
        limite=limite,
        deslocamento=deslocamento,
    )
    return resposta_de_sucesso(
        [_resumo(avaliacao) for avaliacao in avaliacoes],
        metadados=metadados_da_resposta(config),
    )


# --------------------------------------------------------------------------- #
# GET /avaliacoes/{id_execucao}
# --------------------------------------------------------------------------- #


@router.get(
    "/{id_execucao}",
    response_model=RespostaAPI[ResultadoDeAvaliacao],
    summary="Historico de uma avaliacao (sem reexecutar o modelo)",
    description=(
        "Devolve o `resposta_json` **persistido** — a decisao registrada e exatamente a "
        "que foi tomada. O status do envelope reflete a avaliacao original; o HTTP 200 "
        "indica que a consulta ao historico funcionou."
    ),
)
def obter(
    id_execucao: str,
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    usuario: LeituraClinica,
) -> RespostaAPI[ResultadoDeAvaliacao]:
    """Devolve uma avaliacao pelo ``id_execucao`` da Fase 6."""
    config: Configuracoes = request.app.state.configuracoes
    avaliacao = AvaliacaoRepositorio(sessao).buscar_por_id_execucao(id_execucao)
    if avaliacao is None:
        raise ErroDaAPIException(
            CodigoDeErro.NAO_ENCONTRADO,
            "Avaliacao nao encontrada.",
            campo="id_execucao",
            detalhe=f"Nenhuma avaliacao registrada com o id '{id_execucao}'.",
        )

    resultado = _resultado(avaliacao)
    contrato = dict(resultado.resposta)
    # Registro sem o contrato salvo (o repositorio permite `resposta=None`): recupera os
    # motivos e avisos das colunas dedicadas, para a falha nao ficar sem explicacao.
    if not contrato.get("erros") and avaliacao.erros_json:
        contrato["erros"] = list(avaliacao.erros_json)
    if not contrato.get("avisos") and avaliacao.avisos_json:
        contrato["avisos"] = list(avaliacao.avisos_json)

    return _envelope(
        status=StatusDaResposta(avaliacao.status.value),
        contrato=contrato,
        dados=resultado,
        config=config,
        id_execucao=avaliacao.id_execucao,
    )
