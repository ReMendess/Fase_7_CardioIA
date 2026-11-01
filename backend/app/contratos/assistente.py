"""Contratos do assistente conversacional (``CONTRATOS_API.md`` §4.5).

Dois pontos do contrato que valem destacar:

- **`fontes` e sempre `[]`** (nota **N6**): o Watson **nao** devolve fontes, e preencher com
  conteudo inventado seria pior do que assumir a ausencia;
- **`session_id` do provedor nunca sai daqui** (achado **I8**): o identificador exposto e o
  `id_conversa`, gerado por este backend. O `session_id` fica em
  `mensagens.session_id_do_provedor`, interno.

**Nao exposto de proposito:** o contrato §4.5 nao lista `canal`, entao a conversa e registrada
como `web` (`CanalDaConversa`). O valor `mobile` existe no enum e no banco mas nenhuma rota o
produz hoje — gancho para quando o app Expo da Fase 5 for integrado.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..dados.enums import CanalDaConversa, PapelDaMensagem

__all__ = [
    "AVISO_DO_ASSISTENTE",
    "CANAL_PADRAO",
    "LIMITACOES_DO_ASSISTENTE",
    "MensagemDoAssistente",
    "MensagemDoHistorico",
    "PedidoDeMensagem",
]

#: Canal registrado nas conversas (o contrato §4.5 nao expoe o campo).
CANAL_PADRAO = CanalDaConversa.WEB

#: Aviso obrigatorio em toda resposta do assistente.
AVISO_DO_ASSISTENTE = (
    "Resposta gerada por assistente virtual (IBM Watson Assistant) com conteudo do projeto "
    "academico. NAO e diagnostico, NAO e prescricao e NAO substitui avaliacao profissional "
    "de saude."
)

#: Limitacoes declaradas em toda resposta do assistente.
LIMITACOES_DO_ASSISTENTE: tuple[str, ...] = (
    "`fontes` e sempre vazio: o Watson Assistant NAO devolve fontes, e preencher com "
    "conteudo inventado seria pior do que assumir a ausencia.",
    "O `session_id` do provedor e interno a este backend: o identificador exposto e o "
    "`id_conversa`. O cliente nunca recebe (nem pode escolher) a sessao do Watson.",
    "O historico nao expoe o `session_id` nem o detalhe tecnico de falhas — apenas o "
    "conteudo que o usuario viu.",
)


class _ContratoFechado(BaseModel):
    """Base dos DTOs: proibe campos desconhecidos (postura do projeto)."""

    model_config = ConfigDict(extra="forbid")


class PedidoDeMensagem(_ContratoFechado):
    """Mensagem enviada ao assistente.

    Sem `id_conversa`, uma conversa nova e aberta; com `id_conversa`, o turno entra na
    conversa existente (o backend recupera a sessao interna do Watson sozinho).
    """

    mensagem: str = Field(
        min_length=1,
        max_length=2000,
        description="Na origem (Fase 5) o campo chama-se 'message'.",
    )
    id_conversa: str | None = Field(
        default=None,
        description="Identificador da conversa neste backend. Nao e o session_id do Watson.",
    )


class MensagemDoAssistente(_ContratoFechado):
    """Resposta do assistente — o `dados` de ``POST /chat``."""

    id_conversa: str = Field(min_length=8, description="Identificador proprio do backend.")
    resposta: str = Field(min_length=1, description="Na origem chama-se 'reply'.")
    criado_em: datetime = Field(description="Na origem chama-se 'timestamp'.")
    papel: Literal["assistant"] = "assistant"
    fontes: list[str] = Field(
        default_factory=list,
        description="Sempre vazio: o Watson nao devolve fontes (nota N6).",
    )
    avisos: list[str] = Field(default_factory=list)


class MensagemDoHistorico(_ContratoFechado):
    """Um turno no historico da conversa.

    **Nao** carrega `session_id_do_provedor` (interno) nem o detalhe tecnico de falhas: o
    `conteudo` ja e exatamente o texto que o usuario viu.
    """

    id_mensagem: str = Field(min_length=8)
    papel: PapelDaMensagem
    conteudo: str = Field(min_length=1)
    criado_em: datetime
