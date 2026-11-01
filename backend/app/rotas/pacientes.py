"""Rotas de pacientes (``CONTRATOS_API.md`` §8).

| Metodo | Rota | Papel minimo | `dados` |
|---|---|---|---|
| `POST` | `/pacientes` | `MEDICO` | `PacientePublico` |
| `GET` | `/pacientes` | `MEDICO` \\| `ADMIN` | lista de `PacientePublico` |
| `GET` | `/pacientes/{id_paciente}` | `MEDICO` \\| `ADMIN` | `PacientePublico` |

Escopo do cadastro (resposta **Q1**): **apenas identidade**. As 10 features do modelo sao
estado clinico **datado** e vivem em `avaliacoes_de_risco` — nunca no cadastro.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..config import Configuracoes
from ..contratos.assistencial import (
    PacientePublico,
    PedidoDePaciente,
)
from ..contratos.envelope import RespostaAPI, resposta_de_sucesso
from ..contratos.erros import CodigoDeErro, ErroDaAPIException
from ..contratos.paginacao import LIMITE_MAXIMO_DE_PAGINA, LIMITE_PADRAO_DE_PAGINA
from ..dados.base import get_sessao
from ..dados.modelos import Paciente
from ..dados.repositorios.assistencial import PacienteRepositorio
from .apoio import (
    LeituraClinica,
    SomenteMedico,
    ip_do_cliente,
    metadados_da_resposta,
    registrar_auditoria,
)

__all__ = ["buscar_paciente_ou_falhar", "router"]

router = APIRouter(prefix="/pacientes", tags=["pacientes"])

#: Acoes registradas na trilha de auditoria.
ACAO_CRIACAO = "criar_paciente"
ENTIDADE = "pacientes"


def _publico(paciente: Paciente) -> PacientePublico:
    """Converte o modelo para o contrato publico."""
    return PacientePublico(
        id_paciente=paciente.id,
        nome=paciente.nome,
        ativo=paciente.ativo,
        criado_em=paciente.criado_em,
        criado_por=paciente.criado_por,
    )


def buscar_paciente_ou_falhar(sessao: Session, id_paciente: str) -> Paciente:
    """Busca o paciente e levanta ``404`` quando nao existe.

    Raises:
        ErroDaAPIException: ``NAO_ENCONTRADO`` (HTTP 404).
    """
    paciente = PacienteRepositorio(sessao).buscar_por_id(id_paciente)
    if paciente is None:
        raise ErroDaAPIException(
            CodigoDeErro.NAO_ENCONTRADO,
            "Paciente nao encontrado.",
            campo="id_paciente",
            detalhe=f"Nenhum paciente cadastrado com o id '{id_paciente}'.",
        )
    return paciente


@router.post(
    "",
    response_model=RespostaAPI[PacientePublico],
    status_code=201,
    summary="Cadastra um paciente (apenas identidade)",
    description=(
        "Guarda **somente** o nome e quem cadastrou. As 10 features do modelo sao estado "
        "clinico datado e entram em cada avaliacao (resposta Q1)."
    ),
)
def criar(
    pedido: PedidoDePaciente,
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    usuario: SomenteMedico,
) -> RespostaAPI[PacientePublico]:
    """Cadastra um paciente."""
    config: Configuracoes = request.app.state.configuracoes
    paciente = PacienteRepositorio(sessao).criar(nome=pedido.nome, criado_por=usuario.id)

    # 🔒 Sem o nome do paciente no detalhe: a trilha de auditoria nao precisa de dado
    # pessoal para cumprir seu papel (minimizacao, LGPD).
    registrar_auditoria(
        sessao,
        acao=ACAO_CRIACAO,
        entidade=ENTIDADE,
        id_usuario=usuario.id,
        id_entidade=paciente.id,
        ip=ip_do_cliente(request),
    )
    return resposta_de_sucesso(_publico(paciente), metadados=metadados_da_resposta(config))


@router.get(
    "",
    response_model=RespostaAPI[list[PacientePublico]],
    summary="Lista pacientes (paginado)",
    description=(
        "Mais recentes primeiro. Por padrao lista apenas **ativos** (soft delete nao polui "
        "a lista); use `apenas_ativos=false` para ver todos."
    ),
)
def listar(
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    usuario: LeituraClinica,
    limite: Annotated[int, Query(ge=1, le=LIMITE_MAXIMO_DE_PAGINA)] = LIMITE_PADRAO_DE_PAGINA,
    deslocamento: Annotated[int, Query(ge=0)] = 0,
    apenas_ativos: bool = True,
) -> RespostaAPI[list[PacientePublico]]:
    """Lista pacientes com paginacao."""
    config: Configuracoes = request.app.state.configuracoes
    pacientes = PacienteRepositorio(sessao).listar(
        apenas_ativos=apenas_ativos, limite=limite, deslocamento=deslocamento
    )
    return resposta_de_sucesso(
        [_publico(paciente) for paciente in pacientes],
        metadados=metadados_da_resposta(config),
    )


@router.get(
    "/{id_paciente}",
    response_model=RespostaAPI[PacientePublico],
    summary="Detalhe de um paciente",
)
def obter(
    id_paciente: str,
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    usuario: LeituraClinica,
) -> RespostaAPI[PacientePublico]:
    """Devolve um paciente pelo id."""
    config: Configuracoes = request.app.state.configuracoes
    paciente = buscar_paciente_ou_falhar(sessao, id_paciente)
    return resposta_de_sucesso(_publico(paciente), metadados=metadados_da_resposta(config))
