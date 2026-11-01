"""Rotas do assistente conversacional (``CONTRATOS_API.md`` §8) — Fase 5 integrada.

| Metodo | Rota | Papel minimo | `dados` |
|---|---|---|---|
| `POST` | `/chat` | `OPERADOR` \\| `MEDICO` | `MensagemDoAssistente` |
| `GET` | `/conversas/{id_conversa}` | `OPERADOR` \\| `MEDICO` | historico de mensagens |

Decisoes que importam:

- **O `session_id` do Watson e interno** (achado **I8**): o cliente usa e recebe apenas o
  `id_conversa`, gerado aqui. A sessao do provedor fica em `mensagens.session_id_do_provedor`
  e serve para dar continuidade ao dialogo.
- **`fontes` e sempre `[]`** (nota **N6**): o Watson nao devolve fontes.
- **Sem Watson configurado → `501 NAO_CONFIGURADO`**, comportamento herdado da Fase 5.
- **O turno do usuario e persistido mesmo quando o provedor falha**, com o texto amigavel que
  o usuario viu em `conteudo` e o detalhe tecnico em `erro` — assim o historico conta o que
  aconteceu de fato, sem inventar uma resposta que nao existiu.
- **Auditoria na abertura da conversa**, nao em cada turno: uma conversa tem dezenas de
  mensagens e o proprio `mensagens` ja e o registro. O `detalhe` nao carrega o conteudo.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..config import Configuracoes
from ..contratos.assistente import (
    AVISO_DO_ASSISTENTE,
    CANAL_PADRAO,
    LIMITACOES_DO_ASSISTENTE,
    MensagemDoAssistente,
    MensagemDoHistorico,
    PedidoDeMensagem,
)
from ..contratos.envelope import RespostaAPI, resposta_de_sucesso
from ..contratos.erros import CodigoDeErro, ErroDaAPIException
from ..dados.base import get_sessao
from ..dados.enums import PapelDaMensagem
from ..dados.modelos import Conversa, Mensagem
from ..dados.repositorios.conversas import ConversaRepositorio
from ..integracao.fase_5 import configuracao_faltando
from ..integracao.fase_5 import conversar as conversar_com_o_assistente
from .apoio import (
    UsoDoAssistente,
    ip_do_cliente,
    metadados_da_resposta,
    registrar_auditoria,
)

__all__ = ["router"]

router = APIRouter(tags=["assistente"])

ACAO_ABRIR_CONVERSA = "abrir_conversa"
ENTIDADE = "conversas"


def _do_historico(mensagem: Mensagem) -> MensagemDoHistorico:
    """Converte o registro persistido no contrato publico.

    🔒 O `session_id_do_provedor` e o `erro` **nao** saem daqui: o primeiro e interno
    (achado I8) e o segundo e diagnostico tecnico. O `conteudo` ja e o texto que o usuario viu.
    """
    return MensagemDoHistorico(
        id_mensagem=mensagem.id,
        papel=mensagem.papel,
        conteudo=mensagem.conteudo,
        criado_em=mensagem.criado_em,
    )


def _buscar_conversa_ou_falhar(repositorio: ConversaRepositorio, id_conversa: str) -> Conversa:
    """Busca a conversa e levanta ``404`` quando nao existe.

    Raises:
        ErroDaAPIException: ``NAO_ENCONTRADO`` (HTTP 404).
    """
    conversa = repositorio.buscar_por_id(id_conversa)
    if conversa is None:
        raise ErroDaAPIException(
            CodigoDeErro.NAO_ENCONTRADO,
            "Conversa nao encontrada.",
            campo="id_conversa",
            detalhe=f"Nenhuma conversa registrada com o id '{id_conversa}'.",
        )
    return conversa


def _sessao_do_provedor(repositorio: ConversaRepositorio, id_conversa: str) -> str | None:
    """Ultima sessao do Watson registrada na conversa (continuidade do dialogo).

    Devolve ``None`` na primeira mensagem — nesse caso o adapter abre uma sessao nova.
    """
    for mensagem in reversed(repositorio.listar_mensagens(id_conversa)):
        if mensagem.session_id_do_provedor:
            return mensagem.session_id_do_provedor
    return None


@router.post(
    "/chat",
    response_model=RespostaAPI[MensagemDoAssistente],
    summary="Envia uma mensagem ao assistente (Fase 5)",
    description=(
        "Sem `id_conversa`, abre uma conversa nova; com `id_conversa`, continua a existente. "
        "O `session_id` do Watson **nunca** e exposto — o identificador e o `id_conversa`. "
        "Sem Watson configurado, responde `501 NAO_CONFIGURADO`."
    ),
)
def conversar(
    pedido: PedidoDeMensagem,
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    usuario: UsoDoAssistente,
) -> RespostaAPI[MensagemDoAssistente]:
    """Conversa com o assistente e registra o turno."""
    config: Configuracoes = request.app.state.configuracoes

    # 1) Configuracao primeiro: sem Watson nao ha conversa a abrir (nem linha a gravar).
    faltando = configuracao_faltando(config)
    if faltando:
        raise ErroDaAPIException(
            CodigoDeErro.NAO_CONFIGURADO,
            "O assistente nao esta configurado para o Watson Assistant.",
            campo="watson",
            detalhe=(
                f"Faltam: {', '.join(faltando)}. Preencha o .env — o backend le apenas de "
                "variavel de ambiente e NAO usa os valores default do codigo da Fase 5."
            ),
        )

    repositorio = ConversaRepositorio(sessao)

    # 2) Conversa existente ou nova.
    if pedido.id_conversa:
        conversa = _buscar_conversa_ou_falhar(repositorio, pedido.id_conversa)
    else:
        conversa = repositorio.criar(id_usuario=usuario.id, canal=CANAL_PADRAO)
        registrar_auditoria(
            sessao,
            acao=ACAO_ABRIR_CONVERSA,
            entidade=ENTIDADE,
            id_usuario=usuario.id,
            id_entidade=conversa.id,
            ip=ip_do_cliente(request),
            detalhe={"canal": conversa.canal.value},
        )

    # 3) O turno do usuario e persistido antes de chamar o provedor: ele aconteceu.
    repositorio.adicionar_mensagem(
        id_conversa=conversa.id, papel=PapelDaMensagem.USUARIO, conteudo=pedido.mensagem
    )

    # 4) Chamada ao Watson (507/429/504/502 em caso de falha).
    try:
        resultado = conversar_com_o_assistente(
            pedido.mensagem,
            session_id=_sessao_do_provedor(repositorio, conversa.id),
            config=config,
        )
    except ErroDaAPIException as erro:
        # O historico conta o que aconteceu: o texto amigavel que o usuario viu vai em
        # `conteudo`; o detalhe tecnico fica em `erro` (interno).
        repositorio.adicionar_mensagem(
            id_conversa=conversa.id,
            papel=PapelDaMensagem.ASSISTENTE,
            conteudo=erro.mensagem,
            erro=erro.erro.detalhe or erro.codigo.value,
        )
        raise

    # 5) Resposta registrada com a sessao interna (nunca exposta).
    mensagem = repositorio.adicionar_mensagem(
        id_conversa=conversa.id,
        papel=PapelDaMensagem.ASSISTENTE,
        conteudo=resultado.resposta,
        session_id_do_provedor=resultado.session_id_do_provedor,
    )

    return resposta_de_sucesso(
        MensagemDoAssistente(
            id_conversa=conversa.id,
            resposta=resultado.resposta,
            criado_em=mensagem.criado_em,
            fontes=[],  # N6: o Watson nao devolve fontes
            avisos=[AVISO_DO_ASSISTENTE],
        ),
        avisos=[AVISO_DO_ASSISTENTE],
        limitacoes=list(LIMITACOES_DO_ASSISTENTE),
        metadados=metadados_da_resposta(config),
        id_execucao=mensagem.id,
    )


@router.get(
    "/conversas/{id_conversa}",
    response_model=RespostaAPI[list[MensagemDoHistorico]],
    summary="Historico de uma conversa",
    description=(
        "Turnos em ordem cronologica. O `session_id` do provedor e o detalhe tecnico de "
        "falhas **nao** sao expostos. O contexto da conversa (canal, inicio, fim) vai em "
        "`metadados`, porque o contrato define `dados` como o historico de mensagens."
    ),
)
def historico(
    id_conversa: str,
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    usuario: UsoDoAssistente,
) -> RespostaAPI[list[MensagemDoHistorico]]:
    """Devolve as mensagens da conversa."""
    config: Configuracoes = request.app.state.configuracoes
    repositorio = ConversaRepositorio(sessao)
    conversa = _buscar_conversa_ou_falhar(repositorio, id_conversa)

    metadados: dict[str, Any] = {
        **metadados_da_resposta(config),
        "id_conversa": conversa.id,
        "id_usuario": conversa.id_usuario,
        "id_paciente": conversa.id_paciente,
        "canal": conversa.canal.value,
        "iniciada_em": conversa.iniciada_em.isoformat(),
        "encerrada_em": conversa.encerrada_em.isoformat() if conversa.encerrada_em else None,
    }

    return resposta_de_sucesso(
        [_do_historico(item) for item in repositorio.listar_mensagens(conversa.id)],
        limitacoes=list(LIMITACOES_DO_ASSISTENTE),
        metadados=metadados,
        id_execucao=conversa.id,
    )