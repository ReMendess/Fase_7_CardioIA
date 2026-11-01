"""Dependencias do FastAPI: autenticacao e autorizacao (RBAC).

Decisoes:

- ``HTTPBearer(auto_error=False)`` — sem isso o FastAPI devolveria **403** para
  credencial ausente; o correto e **401** (``NAO_AUTENTICADO``). O erro e levantado por
  nos, no formato do envelope comum.
- **o banco e a fonte da verdade do papel.** Se o papel do token divergir do papel
  atual do usuario, a requisicao e recusada com 401: mudar o papel de alguem
  **invalida** os tokens ja emitidos, em vez de o token antigo continuar valendo.
- usuario **inativo** e tratado como nao autenticado.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..config import Configuracoes
from ..contratos.erros import CodigoDeErro, ErroDaAPIException
from ..dados.base import get_sessao
from ..dados.enums import PapelDoUsuario
from ..dados.modelos import Usuario
from ..dados.repositorios.identidade import UsuarioRepositorio
from .tokens import decodificar_access_token

__all__ = [
    "ESQUEMA_DE_AUTENTICACAO",
    "OrigemDaTelemetria",
    "UsuarioAutenticado",
    "exigir_papeis",
    "obter_configuracoes_do_request",
    "obter_origem_da_telemetria",
    "obter_usuario_atual",
]

ESQUEMA_DE_AUTENTICACAO = HTTPBearer(
    auto_error=False,
    scheme_name="Bearer",
    description="Informe o access token: 'Authorization: Bearer <token>'.",
)

#: Cabecalho com a chave compartilhada do dispositivo IoT
#: (``DECISOES_ARQUITETURAIS.md`` §4.1: "IoT -> Backend ... chave de dispositivo").
CABECALHO_DA_CHAVE_DE_DISPOSITIVO = "X-Device-Key"


def obter_configuracoes_do_request(request: Request) -> Configuracoes:
    """Configuracao ligada a aplicacao que atendeu a requisicao."""
    return request.app.state.configuracoes


def obter_usuario_atual(
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    credenciais: Annotated[
        HTTPAuthorizationCredentials | None, Depends(ESQUEMA_DE_AUTENTICACAO)
    ],
) -> Usuario:
    """Resolve o usuario autenticado a partir do header ``Authorization``.

    Raises:
        ErroDaAPIException: token ausente, invalido, expirado, de outro tipo, com papel
            divergente do banco, ou usuario inexistente/inativo
            (``NAO_AUTENTICADO``, HTTP 401).
    """
    if credenciais is None or not credenciais.credentials:
        raise ErroDaAPIException(
            CodigoDeErro.NAO_AUTENTICADO,
            "Credencial de acesso ausente.",
            detalhe="Envie o header 'Authorization: Bearer <access_token>'.",
        )

    config = obter_configuracoes_do_request(request)
    conteudo = decodificar_access_token(
        credenciais.credentials,
        segredo=config.jwt_secret,
        algoritmo=config.jwt_algoritmo,
    )

    usuario = UsuarioRepositorio(sessao).buscar_por_id(conteudo.id_usuario)
    if usuario is None:
        raise ErroDaAPIException(
            CodigoDeErro.NAO_AUTENTICADO,
            "Usuario do token nao existe mais.",
        )
    if not usuario.ativo:
        raise ErroDaAPIException(
            CodigoDeErro.NAO_AUTENTICADO,
            "Usuario inativo.",
            detalhe="Contas desativadas nao autenticam; procure um administrador.",
        )
    if usuario.papel is not conteudo.papel:
        # O papel mudou depois da emissao: o token esta desatualizado de proposito.
        raise ErroDaAPIException(
            CodigoDeErro.NAO_AUTENTICADO,
            "O papel do usuario mudou desde a emissao do token.",
            detalhe="Faca login novamente para obter um token atualizado.",
        )

    return usuario


#: Atalho de anotacao para rotas que exigem apenas autenticacao.
UsuarioAutenticado = Annotated[Usuario, Depends(obter_usuario_atual)]


def exigir_papeis(
    *papeis: PapelDoUsuario,
) -> Callable[[Usuario], Usuario]:
    """Cria uma dependencia que exige um dos papeis informados.

    Args:
        *papeis: papeis aceitos (``MODELO_DADOS.md`` §6.3).

    Returns:
        Dependencia do FastAPI que devolve o usuario autenticado quando autorizado.

    Raises:
        ValueError: nenhum papel informado (erro de programacao, nao de requisicao).
        ErroDaAPIException: papel insuficiente (``NAO_AUTORIZADO``, HTTP 403).
    """
    if not papeis:
        raise ValueError("exigir_papeis exige ao menos um papel.")

    aceitos = tuple(papeis)

    def _verificar(usuario: Annotated[Usuario, Depends(obter_usuario_atual)]) -> Usuario:
        if usuario.papel not in aceitos:
            raise ErroDaAPIException(
                CodigoDeErro.NAO_AUTORIZADO,
                "Seu papel nao permite esta operacao.",
                detalhe=(
                    f"Papeis aceitos: {', '.join(papel.value for papel in aceitos)}; "
                    f"seu papel: {usuario.papel.value}."
                ),
            )
        return usuario

    return _verificar


# --------------------------------------------------------------------------- #
# Telemetria IoT (item 5)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class OrigemDaTelemetria:
    """Quem enviou a leitura de telemetria.

    Duas formas de autenticacao sao aceitas na ingestao (``CONTRATOS_API.md`` §8):
    a **chave de dispositivo** (``X-Device-Key``) ou um usuario com papel ``OPERADOR``.
    """

    usuario: Usuario | None = None

    @property
    def e_dispositivo(self) -> bool:
        """``True`` quando a origem foi a chave de dispositivo (sem usuario)."""
        return self.usuario is None

    @property
    def id_usuario(self) -> str | None:
        """Id do usuario, quando a origem foi um usuario autenticado."""
        return self.usuario.id if self.usuario is not None else None


def obter_origem_da_telemetria(
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    credenciais: Annotated[
        HTTPAuthorizationCredentials | None, Depends(ESQUEMA_DE_AUTENTICACAO)
    ],
) -> OrigemDaTelemetria:
    """Autentica a origem de uma leitura de telemetria.

    Aceita, nesta ordem:

    1. **chave de dispositivo** no cabecalho ``X-Device-Key``, comparada em **tempo
       constante** com ``IOT_DEVICE_KEY``. Se a chave nao estiver configurada no servidor,
       este caminho e recusado — nao ha o que comparar, e aceitar qualquer valor seria
       pior do que recusar;
    2. **usuario** com papel ``OPERADOR`` (Bearer JWT).

    Raises:
        ErroDaAPIException: ``NAO_AUTENTICADO`` (401) para chave ausente/invalida ou
            credencial de usuario ausente/invalida; ``NAO_AUTORIZADO`` (403) quando o
            usuario autenticado nao e ``OPERADOR``.
    """
    config = obter_configuracoes_do_request(request)
    chave = request.headers.get(CABECALHO_DA_CHAVE_DE_DISPOSITIVO)

    if chave:
        if not config.iot_device_key:
            raise ErroDaAPIException(
                CodigoDeErro.NAO_AUTENTICADO,
                "O servidor nao tem chave de dispositivo configurada.",
                detalhe=(
                    "Defina IOT_DEVICE_KEY no .env para habilitar dispositivos, ou "
                    "autentique com um usuario de papel OPERADOR."
                ),
            )
        # compare_digest: comparacao em tempo constante (nao vaza o prefixo correto).
        if not secrets.compare_digest(chave, config.iot_device_key):
            raise ErroDaAPIException(
                CodigoDeErro.NAO_AUTENTICADO, "Chave de dispositivo invalida."
            )
        return OrigemDaTelemetria()

    usuario = obter_usuario_atual(request, sessao, credenciais)
    if usuario.papel is not PapelDoUsuario.OPERADOR:
        raise ErroDaAPIException(
            CodigoDeErro.NAO_AUTORIZADO,
            "A ingestao de telemetria exige papel OPERADOR ou chave de dispositivo.",
            detalhe=f"Seu papel: {usuario.papel.value}.",
        )
    return OrigemDaTelemetria(usuario=usuario)
