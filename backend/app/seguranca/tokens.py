"""Emissao e validacao de tokens (``MODELO_DADOS.md`` §6.1).

Dois tipos, com papeis diferentes:

- **access token** — **JWT assinado (HS256)**, de vida curta (padrao 30 min). Carrega
  ``sub`` (id do usuario), ``papel``, ``tipo``, ``iat``, ``exp``, ``jti`` e ``iss``.
  A validacao e **stateless**: confere assinatura e claims sem tocar no banco.
- **refresh token** — valor **opaco e aleatorio** (nao e JWT). O banco guarda apenas o
  **hash** (``sessoes.token_hash``), de modo que um vazamento do banco **nao** entrega
  um token utilizavel.

Por que **SHA-256** (e nao bcrypt) no refresh: bcrypt existe para segredos de **baixa
entropia** (senhas humanas). Aqui sao 48 bytes aleatorios (~384 bits) — nao ha o que
forcar por dicionario, e o hash rapido permite a busca por indice.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt

from ..contratos.erros import CodigoDeErro, ErroDaAPIException
from ..dados.enums import PapelDoUsuario

__all__ = [
    "ALGORITMO_PADRAO",
    "BYTES_DO_REFRESH",
    "EMISSOR_PADRAO",
    "TIPO_ACCESS",
    "ConteudoDoAccessToken",
    "calcular_expiracao_do_refresh",
    "decodificar_access_token",
    "emitir_access_token",
    "gerar_refresh_token",
    "hash_do_refresh_token",
]

#: Algoritmo de assinatura (unico suportado — ver ``config.validar``).
ALGORITMO_PADRAO = "HS256"

#: Emissor gravado no claim ``iss`` e exigido na leitura.
EMISSOR_PADRAO = "cardioia-backend"

#: Marca o token como token de **acesso** (impede usar outro tipo no mesmo lugar).
TIPO_ACCESS = "access"

#: Entropia do refresh token (bytes aleatorios).
BYTES_DO_REFRESH = 48

#: Claims que a leitura exige. Sem isso, um token sem ``exp`` passaria.
CLAIMS_OBRIGATORIOS = ("exp", "iat", "sub", "jti", "papel", "tipo")


@dataclass(frozen=True)
class ConteudoDoAccessToken:
    """Claims validadas do access token."""

    id_usuario: str
    papel: PapelDoUsuario
    id_token: str
    emitido_em: datetime
    expira_em: datetime


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def emitir_access_token(
    *,
    id_usuario: str,
    papel: PapelDoUsuario,
    segredo: str,
    minutos: int,
    algoritmo: str = ALGORITMO_PADRAO,
    emissor: str = EMISSOR_PADRAO,
    agora: datetime | None = None,
) -> tuple[str, datetime]:
    """Emite um access token assinado.

    Args:
        id_usuario: valor do claim ``sub``.
        papel: papel do RBAC gravado no token.
        segredo: ``JWT_SECRET`` (vem do ambiente, nunca do codigo).
        minutos: validade em minutos.
        agora: instante de referencia (util em teste).

    Returns:
        ``(token, expira_em)`` — o token e o instante UTC de expiracao.
    """
    emitido_em = agora or _agora()
    expira_em = emitido_em + timedelta(minutes=minutos)

    claims = {
        "sub": id_usuario,
        "papel": papel.value,
        "tipo": TIPO_ACCESS,
        "iss": emissor,
        "iat": int(emitido_em.timestamp()),
        "exp": int(expira_em.timestamp()),
        "jti": str(secrets.token_hex(16)),
    }
    token = jwt.encode(claims, segredo, algorithm=algoritmo)
    return token, expira_em


def decodificar_access_token(
    token: str,
    *,
    segredo: str,
    algoritmo: str = ALGORITMO_PADRAO,
    emissor: str = EMISSOR_PADRAO,
) -> ConteudoDoAccessToken:
    """Valida assinatura e claims e devolve o conteudo do token.

    Raises:
        ErroDaAPIException: token ausente/invalido/expirado, emissor errado, tipo
            diferente de ``access`` ou claim obrigatoria faltando
            (``NAO_AUTENTICADO``, HTTP 401).
    """
    if not token or not segredo:
        raise _nao_autenticado("Token de acesso ausente ou segredo nao configurado.")

    try:
        claims = jwt.decode(
            token,
            segredo,
            algorithms=[algoritmo],
            issuer=emissor,
            options={"require": list(CLAIMS_OBRIGATORIOS)},
        )
    except jwt.ExpiredSignatureError as erro:
        raise _nao_autenticado("Token de acesso expirado. Renove com o refresh token.") from erro
    except jwt.InvalidTokenError as erro:
        raise _nao_autenticado(f"Token de acesso invalido ({type(erro).__name__}).") from erro

    if claims.get("tipo") != TIPO_ACCESS:
        raise _nao_autenticado(
            "O token informado nao e um token de acesso.",
            detalhe=f"tipo recebido: {claims.get('tipo')!r}",
        )

    try:
        papel = PapelDoUsuario(str(claims["papel"]))
    except ValueError as erro:
        raise _nao_autenticado("O token carrega um papel desconhecido.") from erro

    return ConteudoDoAccessToken(
        id_usuario=str(claims["sub"]),
        papel=papel,
        id_token=str(claims["jti"]),
        emitido_em=datetime.fromtimestamp(int(claims["iat"]), tz=timezone.utc),
        expira_em=datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc),
    )


def _nao_autenticado(mensagem: str, *, detalhe: str | None = None) -> ErroDaAPIException:
    return ErroDaAPIException(CodigoDeErro.NAO_AUTENTICADO, mensagem, detalhe=detalhe)


def gerar_refresh_token() -> str:
    """Gera um refresh token opaco (alta entropia, sem estrutura)."""
    return secrets.token_urlsafe(BYTES_DO_REFRESH)


def hash_do_refresh_token(token: str) -> str:
    """SHA-256 hexadecimal do refresh token — o que vai para o banco.

    Nunca armazenamos o token em claro: um vazamento do banco nao entrega um token
    utilizavel (``PLANO_SEGURANCA.md`` §6).
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def calcular_expiracao_do_refresh(dias: int, *, agora: datetime | None = None) -> datetime:
    """Instante UTC em que o refresh token expira."""
    return (agora or _agora()) + timedelta(days=dias)
