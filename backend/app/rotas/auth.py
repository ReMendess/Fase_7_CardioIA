"""Rotas de autenticacao (``CONTRATOS_API.md`` §8).

| Metodo | Rota | Autenticacao | `dados` na resposta |
|---|---|---|---|
| `POST` | `/auth/login` | — | `RespostaDeSessao` (par de tokens) |
| `POST` | `/auth/refresh` | refresh token no corpo | `RespostaDeSessao` (**novo par** — ha rotacao) |
| `POST` | `/auth/logout` | access token | `RespostaDeLogout` |
| `GET` | `/auth/me` | access token | `UsuarioPublico` |

Cuidados de seguranca implementados:

- **mensagem generica** para credencial invalida (nao revela se o e-mail existe);
- **tempo de resposta igualado** quando o e-mail nao existe (bcrypt de referencia);
- **limitador de tentativas** por `email|ip` (com a limitacao declarada no modulo);
- **rotacao de refresh token**: o token usado e revogado e um novo par e emitido;
- **auditoria** de login, refresh e logout em ``eventos_de_auditoria`` — sem senha,
  sem token e sem payload clinico.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..config import Configuracoes
from ..contratos.autenticacao import (
    PedidoDeLogin,
    PedidoDeRefresh,
    RespostaDeLogout,
    RespostaDeSessao,
    UsuarioPublico,
)
from ..contratos.envelope import RespostaAPI, resposta_de_sucesso
from ..contratos.erros import CodigoDeErro, ErroDaAPIException
from ..dados.base import get_sessao
from ..dados.modelos import Usuario
from ..dados.repositorios.identidade import SessaoRepositorio, UsuarioRepositorio
from ..seguranca.dependencias import UsuarioAutenticado
from ..seguranca.limite_de_tentativas import LimitadorDeTentativas
from ..seguranca.senhas import consumir_tempo_de_verificacao, senha_confere
from ..seguranca.tokens import (
    calcular_expiracao_do_refresh,
    emitir_access_token,
    gerar_refresh_token,
    hash_do_refresh_token,
)
from .apoio import ip_do_cliente as _ip_do_cliente
from .apoio import metadados_da_resposta as _metadados
from .apoio import registrar_auditoria

__all__ = ["router"]

router = APIRouter(prefix="/auth", tags=["autenticacao"])

#: Mensagem **unica** para qualquer falha de credencial (nao revela se a conta existe).
MENSAGEM_DE_CREDENCIAL_INVALIDA = "E-mail ou senha invalidos."

ACAO_LOGIN = "login"
ACAO_REFRESH = "refresh"
ACAO_LOGOUT = "logout"
ENTIDADE = "usuarios"


# --------------------------------------------------------------------------- #
# Apoio
# --------------------------------------------------------------------------- #
# `_metadados` e `_ip_do_cliente` sao os helpers compartilhados de `apoio` (importados
# com alias para manter os nomes usados neste modulo); `_auditar` e o atalho local que
# fixa a entidade auditada.


def _chave_do_limite(email: str, ip: str | None) -> str:
    """Chave do limitador: combina e-mail e IP para nao bloquear terceiros."""
    return f"{email}|{ip or 'sem-ip'}"


def _publico(usuario: Usuario) -> UsuarioPublico:
    """Converte o modelo para o contrato publico (**sem** ``senha_hash``)."""
    return UsuarioPublico(
        id_usuario=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        papel=usuario.papel,
        ativo=usuario.ativo,
        criado_em=usuario.criado_em,
        ultimo_acesso=usuario.ultimo_acesso,
    )


def _auditar(
    sessao: Session,
    *,
    acao: str,
    id_usuario: str | None,
    ip: str | None,
    detalhe: dict[str, object] | None = None,
) -> None:
    """Registra o evento de auditoria (sem senha, sem token, sem dado clinico)."""
    registrar_auditoria(
        sessao,
        acao=acao,
        entidade=ENTIDADE,
        id_usuario=id_usuario,
        id_entidade=id_usuario,
        ip=ip,
        detalhe=detalhe,
    )


def _emitir_par_de_tokens(
    usuario: Usuario, config: Configuracoes, sessao: Session
) -> RespostaDeSessao:
    """Emite o access token (JWT) e o refresh token (opaco) e grava a sessao.

    O banco guarda **apenas o hash** do refresh token (``MODELO_DADOS.md`` §6.1).
    """
    access_token, expira_em = emitir_access_token(
        id_usuario=usuario.id,
        papel=usuario.papel,
        segredo=config.jwt_secret,
        minutos=config.access_token_minutos,
        algoritmo=config.jwt_algoritmo,
    )
    refresh_token = gerar_refresh_token()

    SessaoRepositorio(sessao).criar(
        id_usuario=usuario.id,
        token_hash=hash_do_refresh_token(refresh_token),
        expira_em=calcular_expiracao_do_refresh(config.refresh_token_dias),
    )
    return RespostaDeSessao(
        access_token=access_token, refresh_token=refresh_token, expira_em=expira_em
    )


def _limitador(request: Request) -> LimitadorDeTentativas:
    return request.app.state.limitador_de_tentativas


# --------------------------------------------------------------------------- #
# Rotas
# --------------------------------------------------------------------------- #


@router.post(
    "/login",
    response_model=RespostaAPI[RespostaDeSessao],
    summary="Autentica e devolve o par de tokens",
    description=(
        "Valida as credenciais e devolve access token (JWT, vida curta) e refresh token "
        "(opaco, vida longa). A mensagem de erro e sempre generica."
    ),
)
def login(
    pedido: PedidoDeLogin,
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
) -> RespostaAPI[RespostaDeSessao]:
    """Autentica o usuario."""
    config: Configuracoes = request.app.state.configuracoes
    limitador = _limitador(request)
    ip = _ip_do_cliente(request)
    email = pedido.email.strip().lower()
    chave = _chave_do_limite(email, ip)

    if limitador.esta_bloqueado(chave):
        raise ErroDaAPIException(
            CodigoDeErro.TAXA_EXCEDIDA,
            "Muitas tentativas de login. Tente novamente em instantes.",
            detalhe=f"Liberacao estimada em {limitador.segundos_restantes(chave)}s.",
        )

    usuarios = UsuarioRepositorio(sessao)
    usuario = usuarios.buscar_por_email(email)

    if usuario is None:
        # Consome tempo equivalente a um bcrypt real: sem isso a resposta voltaria mais
        # rapido e revelaria, por diferenca de tempo, que a conta nao existe.
        consumir_tempo_de_verificacao(pedido.senha)
        limitador.registrar_falha(chave)
        _auditar(
            sessao,
            acao=ACAO_LOGIN,
            id_usuario=None,
            ip=ip,
            detalhe={"resultado": "email_desconhecido"},
        )
        raise ErroDaAPIException(CodigoDeErro.NAO_AUTENTICADO, MENSAGEM_DE_CREDENCIAL_INVALIDA)

    if not senha_confere(pedido.senha, usuario.senha_hash):
        limitador.registrar_falha(chave)
        _auditar(
            sessao,
            acao=ACAO_LOGIN,
            id_usuario=usuario.id,
            ip=ip,
            detalhe={"resultado": "senha_incorreta"},
        )
        raise ErroDaAPIException(CodigoDeErro.NAO_AUTENTICADO, MENSAGEM_DE_CREDENCIAL_INVALIDA)

    if not usuario.ativo:
        limitador.registrar_falha(chave)
        _auditar(
            sessao,
            acao=ACAO_LOGIN,
            id_usuario=usuario.id,
            ip=ip,
            detalhe={"resultado": "inativo"},
        )
        raise ErroDaAPIException(
            CodigoDeErro.NAO_AUTORIZADO,
            "Conta desativada.",
            detalhe="Contas desativadas nao autenticam; procure um administrador.",
        )

    limitador.limpar(chave)
    usuarios.registrar_acesso(usuario)

    resposta = _emitir_par_de_tokens(usuario, config, sessao)
    _auditar(
        sessao,
        acao=ACAO_LOGIN,
        id_usuario=usuario.id,
        ip=ip,
        detalhe={"resultado": "sucesso", "papel": usuario.papel.value},
    )
    return resposta_de_sucesso(resposta, metadados=_metadados(config))


@router.post(
    "/refresh",
    response_model=RespostaAPI[RespostaDeSessao],
    summary="Renova o acesso (com rotacao do refresh token)",
    description=(
        "Revoga o refresh token usado e devolve um **novo par**. O cliente deve "
        "substituir o refresh token anterior pelo novo."
    ),
)
def renovar(
    pedido: PedidoDeRefresh,
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
) -> RespostaAPI[RespostaDeSessao]:
    """Troca um refresh token vigente por um novo par."""
    config: Configuracoes = request.app.state.configuracoes
    sessoes = SessaoRepositorio(sessao)

    registro = sessoes.buscar_por_hash(hash_do_refresh_token(pedido.refresh_token))
    if registro is None or not registro.vigente:
        raise ErroDaAPIException(
            CodigoDeErro.NAO_AUTENTICADO,
            "Refresh token invalido, expirado ou revogado.",
            detalhe="Faca login novamente para obter um novo par de tokens.",
        )

    usuario = UsuarioRepositorio(sessao).buscar_por_id(registro.id_usuario)
    if usuario is None or not usuario.ativo:
        sessoes.revogar(registro)
        raise ErroDaAPIException(
            CodigoDeErro.NAO_AUTENTICADO,
            "Usuario do refresh token indisponivel.",
            detalhe="A sessao foi revogada.",
        )

    # ROTACAO: o token apresentado deixa de valer, mesmo que o novo nao seja usado.
    sessoes.revogar(registro)
    resposta = _emitir_par_de_tokens(usuario, config, sessao)
    _auditar(
        sessao,
        acao=ACAO_REFRESH,
        id_usuario=usuario.id,
        ip=_ip_do_cliente(request),
        detalhe={"rotacao": True},
    )
    return resposta_de_sucesso(resposta, metadados=_metadados(config))


@router.post(
    "/logout",
    response_model=RespostaAPI[RespostaDeLogout],
    summary="Encerra as sessoes do usuario autenticado",
    description=(
        "Revoga **todas** as sessoes vigentes do usuario. O access token continua "
        "assinado ate expirar, mas as renovacoes deixam de funcionar."
    ),
)
def sair(
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    usuario: UsuarioAutenticado,
) -> RespostaAPI[RespostaDeLogout]:
    """Revoga as sessoes do usuario."""
    config: Configuracoes = request.app.state.configuracoes
    revogadas = SessaoRepositorio(sessao).revogar_todas_do_usuario(usuario.id)

    _auditar(
        sessao,
        acao=ACAO_LOGOUT,
        id_usuario=usuario.id,
        ip=_ip_do_cliente(request),
        detalhe={"sessoes_revogadas": revogadas},
    )
    return resposta_de_sucesso(
        RespostaDeLogout(sessoes_revogadas=revogadas), metadados=_metadados(config)
    )


@router.get(
    "/me",
    response_model=RespostaAPI[UsuarioPublico],
    summary="Dados do usuario autenticado",
    description="Devolve o usuario do access token (**sem** `senha_hash`).",
)
def quem_sou_eu(
    request: Request,
    usuario: UsuarioAutenticado,
) -> RespostaAPI[UsuarioPublico]:
    """Devolve o usuario autenticado no contrato publico."""
    config: Configuracoes = request.app.state.configuracoes
    return resposta_de_sucesso(_publico(usuario), metadados=_metadados(config))