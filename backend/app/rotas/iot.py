"""Rotas de telemetria IoT (``CONTRATOS_API.md`` §8) — Fase 3 integrada.

| Metodo | Rota | Papel minimo | `dados` |
|---|---|---|---|
| `POST` | `/iot/leituras` | `OPERADOR` \\| **chave de dispositivo** | `DadosDeMonitoramento` persistido |
| `GET` | `/iot/leituras` | `OPERADOR` \\| `MEDICO` | lista de leituras |

Decisoes que importam:

- **A telemetria NAO alimenta o modelo** (Decisao D4). Isso e declarado em ``limitacoes``
  em **toda** resposta: o operador precisa saber que a leitura nao entra na predicao.
- **Alerta em ``avisos``, nao em ``dados``**: o contrato define ``dados`` como o
  ``DadosDeMonitoramento`` persistido; o alerta das regras da Fase 3 e **derivado** e nao
  tem coluna. Ele vai para ``avisos``, com ``status=CONCLUIDO_COM_RESSALVAS``.
- **Auditoria apenas quando ha alerta**: a telemetria chega a cada poucos segundos —
  gravar todo evento encheria a trilha sem valor. A leitura em si ja e o registro.
- **O ``recebido_em`` e carimbado pelo backend** — o firmware da Fase 3 nao envia
  timestamp nem identificador (``MODELO_DADOS.md`` §4.5).
- **A regra de risco e ``app/regras_iot.py``**, com limiares identicos aos do servico
  Flask legado, que fica **desativado** (``DECISOES_ARQUITETURAIS.md`` §3.4).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..config import Configuracoes
from ..contratos.envelope import RespostaAPI, StatusDaResposta, resposta_de_sucesso
from ..contratos.paginacao import LIMITE_MAXIMO_DE_PAGINA, LIMITE_PADRAO_DE_PAGINA
from ..contratos.telemetria import LeituraDeMonitoramento, PedidoDeLeitura
from ..dados.base import get_sessao
from ..dados.enums import PapelDoUsuario
from ..dados.modelos import Monitoramento, Usuario
from ..dados.repositorios.telemetria import MonitoramentoRepositorio
from ..regras_iot import avaliar_sinais
from ..seguranca.dependencias import (
    OrigemDaTelemetria,
    exigir_papeis,
    obter_origem_da_telemetria,
)
from .apoio import ip_do_cliente, metadados_da_resposta, registrar_auditoria

__all__ = ["router"]

router = APIRouter(prefix="/iot", tags=["telemetria"])

#: Acao registrada na trilha quando a leitura aciona uma regra de risco.
ACAO_ALERTA = "alerta_de_telemetria"
ENTIDADE = "monitoramentos"

#: Limitacao declarada em toda resposta de telemetria (Decisao D4).
LIMITACAO_DA_TELEMETRIA = (
    "A telemetria NAO alimenta o modelo preditivo (Decisao D4): as leituras sao "
    "persistidas para visualizacao e auditoria. Das 10 features do modelo, apenas "
    "'fc_media' tem correspondencia na telemetria ('bpm', de origem simulada) — as outras "
    "9 nao vem de sensor. Avaliacoes de risco usam as features informadas em "
    "POST /avaliacoes."
)

#: Dependencia: leitura do historico de telemetria.
LeituraDeTelemetria = Annotated[
    Usuario, Depends(exigir_papeis(PapelDoUsuario.OPERADOR, PapelDoUsuario.MEDICO))
]

#: Dependencia: ingestao (chave de dispositivo **ou** usuario ``OPERADOR``).
IngestaoDeTelemetria = Annotated[OrigemDaTelemetria, Depends(obter_origem_da_telemetria)]


def _publica(leitura: Monitoramento) -> LeituraDeMonitoramento:
    """Converte o modelo persistido para o contrato publico."""
    return LeituraDeMonitoramento(
        id_leitura=leitura.id,
        id_dispositivo=leitura.id_dispositivo,
        recebido_em=leitura.recebido_em,
        origem_transporte=leitura.origem_transporte,
        temperatura=leitura.temperatura,
        bpm=leitura.bpm,
        umidade=leitura.umidade,
        luminosidade=leitura.luminosidade,
        movimento=leitura.movimento,
        payload_json=leitura.payload_json,
    )


@router.post(
    "/leituras",
    response_model=RespostaAPI[LeituraDeMonitoramento],
    status_code=201,
    summary="Ingere uma leitura de telemetria",
    description=(
        "Aceita `X-Device-Key` (chave de dispositivo) ou Bearer JWT com papel `OPERADOR`. "
        "Pelo menos um sinal vital (`temperatura` ou `bpm`) e obrigatorio. Se alguma regra "
        "de risco da Fase 3 for acionada, o envelope vem com "
        "`status=CONCLUIDO_COM_RESSALVAS` e o alerta em `avisos`."
    ),
)
def ingerir(
    pedido: PedidoDeLeitura,
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    origem: IngestaoDeTelemetria,
) -> RespostaAPI[LeituraDeMonitoramento]:
    """Avalia as regras de risco, persiste a leitura e informa o alerta."""
    config: Configuracoes = request.app.state.configuracoes

    resultado = avaliar_sinais(
        temperatura=pedido.temperatura, bpm=pedido.bpm, movimento=pedido.movimento
    )

    leitura = MonitoramentoRepositorio(sessao).registrar(
        id_dispositivo=pedido.id_dispositivo,
        origem_transporte=pedido.origem_transporte,
        temperatura=pedido.temperatura,
        bpm=pedido.bpm,
        umidade=pedido.umidade,
        luminosidade=pedido.luminosidade,
        movimento=pedido.movimento,
        payload=pedido.payload_json,
    )

    if resultado.houve_alerta:
        # So o alerta entra na trilha: a leitura ja e o registro persistido, e a
        # telemetria chega em alta frequencia.
        registrar_auditoria(
            sessao,
            acao=ACAO_ALERTA,
            entidade=ENTIDADE,
            id_usuario=origem.id_usuario,
            id_entidade=leitura.id,
            ip=ip_do_cliente(request),
            detalhe={
                "alerta": resultado.alerta,
                "id_dispositivo": leitura.id_dispositivo,
                "autenticacao": "dispositivo" if origem.e_dispositivo else "usuario",
            },
        )

    return resposta_de_sucesso(
        _publica(leitura),
        status=(
            StatusDaResposta.CONCLUIDO_COM_RESSALVAS
            if resultado.houve_alerta
            else StatusDaResposta.CONCLUIDO
        ),
        avisos=[resultado.alerta] if resultado.alerta else [],
        limitacoes=[LIMITACAO_DA_TELEMETRIA],
        metadados=metadados_da_resposta(config),
        id_execucao=leitura.id,
    )


@router.get(
    "/leituras",
    response_model=RespostaAPI[list[LeituraDeMonitoramento]],
    summary="Lista leituras de telemetria (paginado)",
    description=(
        "Mais recentes primeiro. Se `len(dados) < limite`, nao ha proxima pagina. "
        "O alerta das regras nao e persistido — recompute-o com `app.regras_iot` se "
        "precisar saber quais leituras teriam alertado."
    ),
)
def listar(
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    usuario: LeituraDeTelemetria,
    id_dispositivo: Annotated[
        str | None, Query(description="Filtra por dispositivo.")
    ] = None,
    limite: Annotated[int, Query(ge=1, le=LIMITE_MAXIMO_DE_PAGINA)] = LIMITE_PADRAO_DE_PAGINA,
    deslocamento: Annotated[int, Query(ge=0)] = 0,
) -> RespostaAPI[list[LeituraDeMonitoramento]]:
    """Lista as leituras registradas, em formato paginado."""
    config: Configuracoes = request.app.state.configuracoes
    leituras = MonitoramentoRepositorio(sessao).ultimas(
        id_dispositivo=id_dispositivo, limite=limite, deslocamento=deslocamento
    )
    return resposta_de_sucesso(
        [_publica(leitura) for leitura in leituras],
        limitacoes=[LIMITACAO_DA_TELEMETRIA],
        metadados=metadados_da_resposta(config),
    )