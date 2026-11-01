"""Rota de saude do backend — ``GET /api/v1/health``.

Contrato (``CONTRATOS_API.md`` §8): "estado do servico + presenca do modelo".

O endpoint **nao** executa o modelo nem importa o pacote ``cardioia``: verifica a
**existencia dos arquivos** do artefato e, desde o item 4, tambem se o codigo da Fase 6
e seus modulos obrigatorios seriam **localizaveis** (via ``importlib.util.find_spec``,
que nao executa nada). Por isso a resposta continua em poucos milissegundos.

Estados possiveis:

- ``CONCLUIDO`` — servico no ar e artefato do modelo presente;
- ``CONCLUIDO_COM_RESSALVAS`` — servico no ar, **artefato ausente** (com aviso
  contendo o comando de treino). O servico continua util para diagnostico.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from .. import NOME_DO_SERVICO
from .. import __versao__
from ..config import Configuracoes
from ..contratos.envelope import (
    RespostaAPI,
    StatusDaResposta,
    resposta_de_sucesso,
)
from ..integracao.fase_6 import disponibilidade

router = APIRouter(tags=["saude"])

#: Comando oficial de treino da Fase 6 (usado nas mensagens de diagnostico).
COMANDO_DE_TREINO = "python -m src.cardioia.ml.train"


class ArtefatoDoModelo(BaseModel):
    """Presenca dos arquivos do modelo de risco (Fase 6)."""

    model_config = ConfigDict(extra="forbid")

    presente: bool = Field(description="O arquivo .pkl existe?")
    metadados_presentes: bool = Field(description="O metadata .json existe?")
    pasta_da_fase_6: str = Field(description="Pasta resolvida da Fase 6.")
    caminho_do_modelo: str = Field(description="Caminho esperado do .pkl.")


class IntegracaoDaFase6(BaseModel):
    """Estado da integracao com o pacote ``cardioia`` (item 4).

    Verificacao **barata**: usa ``find_spec``, que localiza os modulos sem executa-los.
    Por isso o ``/health`` continua respondendo em poucos milissegundos, mesmo que o
    pipeline ainda nao tenha sido importado.
    """

    model_config = ConfigDict(extra="forbid")

    pasta_do_codigo: str = Field(description="Pasta onde o pacote cardioia deve estar.")
    codigo_presente: bool = Field(description="A pasta do codigo da Fase 6 existe?")
    importavel: bool = Field(
        description="O pacote e seus modulos obrigatorios foram localizados?"
    )
    modulos_encontrados: dict[str, bool] = Field(
        description="Por modulo exigido pelo pipeline (cardioia, agents, sklearn, ...)."
    )
    faltando: list[str] = Field(
        default_factory=list, description="Modulos nao localizados."
    )


class DadosDeSaude(BaseModel):
    """Conteudo do envelope em ``/health``."""

    model_config = ConfigDict(extra="forbid")

    servico: str = Field(min_length=1)
    versao_do_backend: str = Field(min_length=1)
    versao_api: str = Field(min_length=1)
    ambiente: str = Field(min_length=1)
    artefato_do_modelo: ArtefatoDoModelo
    integracao_da_fase_6: IntegracaoDaFase6
    integracoes_configuradas: dict[str, bool] = Field(
        description="Presenca de credencial/URL por integracao (nenhum valor exposto)."
    )
    rotas_registradas: list[str] = Field(
        default_factory=list, description="Caminhos registrados na aplicacao."
    )


def _coletar_dados(config: Configuracoes, request: Request) -> tuple[DadosDeSaude, list[str]]:
    """Monta os dados de saude e a lista de avisos."""
    caminho_modelo = config.caminho_do_modelo
    caminho_metadados = config.caminho_dos_metadados

    presente = caminho_modelo.is_file()
    metadados_presentes = caminho_metadados.is_file()

    avisos: list[str] = []
    if not presente:
        avisos.append(
            "Artefato do modelo ausente: "
            f"'{caminho_modelo}'. Treine com '{COMANDO_DE_TREINO}' (na Fase 6). "
            "Sem o artefato, o endpoint de avaliacao de risco respondera "
            "MODELO_INDISPONIVEL."
        )
    elif not metadados_presentes:
        avisos.append(
            "Metadata do modelo ausente: "
            f"'{caminho_metadados}'. Sem ele o contrato de features e as faixas "
            "esperadas nao podem ser validados."
        )

    estado_da_integracao = disponibilidade(config)
    dados = DadosDeSaude(
        servico=NOME_DO_SERVICO,
        versao_do_backend=__versao__,
        versao_api=config.versao_api,
        ambiente=config.ambiente,
        artefato_do_modelo=ArtefatoDoModelo(
            presente=presente,
            metadados_presentes=metadados_presentes,
            pasta_da_fase_6=str(config.pasta_da_fase_6),
            caminho_do_modelo=str(caminho_modelo),
        ),
        integracao_da_fase_6=IntegracaoDaFase6(
            pasta_do_codigo=estado_da_integracao["pasta_do_codigo"],
            codigo_presente=estado_da_integracao["codigo_presente"],
            importavel=estado_da_integracao["importavel"],
            modulos_encontrados=estado_da_integracao["modulos_encontrados"],
            faltando=estado_da_integracao["faltando"],
        ),
        integracoes_configuradas=config.integracoes_configuradas,
        rotas_registradas=sorted(
            getattr(rota, "path", "") for rota in request.app.routes if getattr(rota, "path", "")
        ),
    )
    return dados, avisos


@router.get(
    "/health",
    response_model=RespostaAPI[DadosDeSaude],
    summary="Estado do servico e presenca do artefato do modelo",
    description=(
        "Nao executa o modelo nem importa a Fase 6 — verifica apenas os arquivos. "
        "Status CONCLUIDO_COM_RESSALVAS indica artefato ausente, com o comando de treino nos avisos."
    ),
)
def saude(request: Request) -> RespostaAPI[DadosDeSaude]:
    """Devolve o estado do servico no envelope comum."""
    config: Configuracoes = request.app.state.configuracoes
    dados, avisos = _coletar_dados(config, request)

    status = (
        StatusDaResposta.CONCLUIDO if not avisos else StatusDaResposta.CONCLUIDO_COM_RESSALVAS
    )
    return resposta_de_sucesso(
        dados,
        status=status,
        avisos=avisos,
        metadados={
            "versao_api": config.versao_api,
            "origem": "cardioia-backend",
            "verificacao": "existencia_de_arquivos",
        },
    )


__all__ = ["COMANDO_DE_TREINO", "ArtefatoDoModelo", "DadosDeSaude", "router"]
