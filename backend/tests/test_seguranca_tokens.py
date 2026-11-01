"""Testes do modulo de tokens (``app/seguranca/tokens.py``)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.contratos.erros import CodigoDeErro, ErroDaAPIException
from app.dados.enums import PapelDoUsuario
from app.seguranca.tokens import (
    ALGORITMO_PADRAO,
    EMISSOR_PADRAO,
    TIPO_ACCESS,
    calcular_expiracao_do_refresh,
    decodificar_access_token,
    emitir_access_token,
    gerar_refresh_token,
    hash_do_refresh_token,
)
from tests.conftest import SEGREDO_DE_TESTE

ID_USUARIO = "3f2b9c1e-8a4d-4c77-9e10-5b6a7c8d9e0f"


def _emitir(**extras: object) -> tuple[str, datetime]:
    parametros: dict[str, object] = {
        "id_usuario": ID_USUARIO,
        "papel": PapelDoUsuario.MEDICO,
        "segredo": SEGREDO_DE_TESTE,
        "minutos": 30,
    }
    parametros.update(extras)
    return emitir_access_token(**parametros)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Emissao e leitura
# --------------------------------------------------------------------------- #


def test_token_emitido_e_lido_de_volta() -> None:
    token, expira_em = _emitir()
    conteudo = decodificar_access_token(token, segredo=SEGREDO_DE_TESTE)

    assert conteudo.id_usuario == ID_USUARIO
    assert conteudo.papel is PapelDoUsuario.MEDICO
    assert conteudo.id_token
    assert conteudo.expira_em == expira_em.replace(microsecond=0)
    assert conteudo.emitido_em.tzinfo is not None


def test_token_carrega_os_claims_esperados() -> None:
    token, _ = _emitir()
    claims = jwt.decode(token, SEGREDO_DE_TESTE, algorithms=[ALGORITMO_PADRAO])

    assert claims["sub"] == ID_USUARIO
    assert claims["papel"] == "MEDICO"
    assert claims["tipo"] == TIPO_ACCESS
    assert claims["iss"] == EMISSOR_PADRAO
    assert isinstance(claims["exp"], int)
    assert isinstance(claims["iat"], int)
    assert claims["jti"]


def test_cada_emissao_tem_um_jti_proprio() -> None:
    """O identificador do token e unico — permite revogar por token no futuro."""
    primeiro, _ = _emitir()
    segundo, _ = _emitir()
    claims_1 = jwt.decode(primeiro, SEGREDO_DE_TESTE, algorithms=[ALGORITMO_PADRAO])
    claims_2 = jwt.decode(segundo, SEGREDO_DE_TESTE, algorithms=[ALGORITMO_PADRAO])
    assert claims_1["jti"] != claims_2["jti"]


def test_expiracao_respeita_os_minutos_informados() -> None:
    agora = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
    _, expira_em = _emitir(minutos=15, agora=agora)
    assert expira_em == agora + timedelta(minutes=15)


# --------------------------------------------------------------------------- #
# Rejeicoes
# --------------------------------------------------------------------------- #


def test_token_expirado_e_recusado() -> None:
    agora = datetime.now(timezone.utc)
    token, _ = _emitir(minutos=1, agora=agora - timedelta(hours=2))
    with pytest.raises(ErroDaAPIException) as capturado:
        decodificar_access_token(token, segredo=SEGREDO_DE_TESTE)
    assert capturado.value.codigo is CodigoDeErro.NAO_AUTENTICADO
    assert "expirado" in capturado.value.mensagem


def test_assinatura_de_outro_segredo_e_recusada() -> None:
    token, _ = _emitir(segredo="outro-segredo-completamente-diferente")
    with pytest.raises(ErroDaAPIException) as capturado:
        decodificar_access_token(token, segredo=SEGREDO_DE_TESTE)
    assert capturado.value.codigo is CodigoDeErro.NAO_AUTENTICADO


def test_token_adulterado_e_recusado() -> None:
    token, _ = _emitir()
    cabecalho, corpo, assinatura = token.split(".")
    adulterado = f"{cabecalho}.{corpo}.{assinatura[:-4]}AAAA"
    with pytest.raises(ErroDaAPIException):
        decodificar_access_token(adulterado, segredo=SEGREDO_DE_TESTE)


def test_emissor_diferente_e_recusado() -> None:
    token, _ = _emitir(emissor="outro-emissor")
    with pytest.raises(ErroDaAPIException) as capturado:
        decodificar_access_token(token, segredo=SEGREDO_DE_TESTE)
    assert capturado.value.codigo is CodigoDeErro.NAO_AUTENTICADO


def test_tipo_diferente_de_access_e_recusado() -> None:
    """Impede usar, no lugar do access, um token de outro proposito."""
    agora = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": ID_USUARIO,
            "papel": "MEDICO",
            "tipo": "refresh",
            "iss": EMISSOR_PADRAO,
            "iat": int(agora.timestamp()),
            "exp": int((agora + timedelta(minutes=5)).timestamp()),
            "jti": "x",
        },
        SEGREDO_DE_TESTE,
        algorithm=ALGORITMO_PADRAO,
    )
    with pytest.raises(ErroDaAPIException) as capturado:
        decodificar_access_token(token, segredo=SEGREDO_DE_TESTE)
    assert "nao e um token de acesso" in capturado.value.mensagem


def test_claim_obrigatoria_ausente_e_recusada() -> None:
    """Sem a exigencia de claims, um token sem ``exp`` passaria."""
    token = jwt.encode(
        {"sub": ID_USUARIO, "papel": "MEDICO", "tipo": TIPO_ACCESS, "iss": EMISSOR_PADRAO},
        SEGREDO_DE_TESTE,
        algorithm=ALGORITMO_PADRAO,
    )
    with pytest.raises(ErroDaAPIException) as capturado:
        decodificar_access_token(token, segredo=SEGREDO_DE_TESTE)
    assert capturado.value.codigo is CodigoDeErro.NAO_AUTENTICADO


def test_papel_desconhecido_e_recusado() -> None:
    agora = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": ID_USUARIO,
            "papel": "SUPERUSUARIO",
            "tipo": TIPO_ACCESS,
            "iss": EMISSOR_PADRAO,
            "iat": int(agora.timestamp()),
            "exp": int((agora + timedelta(minutes=5)).timestamp()),
            "jti": "x",
        },
        SEGREDO_DE_TESTE,
        algorithm=ALGORITMO_PADRAO,
    )
    with pytest.raises(ErroDaAPIException) as capturado:
        decodificar_access_token(token, segredo=SEGREDO_DE_TESTE)
    assert "papel desconhecido" in capturado.value.mensagem


@pytest.mark.parametrize(("token", "segredo"), [("", SEGREDO_DE_TESTE), ("abc", ""), ("", "")])
def test_token_ou_segredo_ausente_e_recusado(token: str, segredo: str) -> None:
    with pytest.raises(ErroDaAPIException) as capturado:
        decodificar_access_token(token, segredo=segredo)
    assert capturado.value.codigo is CodigoDeErro.NAO_AUTENTICADO


def test_algoritmo_none_nao_e_aceito() -> None:
    """Algoritmo 'none' nao pode ser aceito (ataque classico de JWT)."""
    token = jwt.encode({"sub": ID_USUARIO}, key="", algorithm="none")
    with pytest.raises(ErroDaAPIException):
        decodificar_access_token(token, segredo=SEGREDO_DE_TESTE)


# --------------------------------------------------------------------------- #
# Refresh token
# --------------------------------------------------------------------------- #


def test_refresh_token_e_aleatorio_e_distinto() -> None:
    tokens = {gerar_refresh_token() for _ in range(50)}
    assert len(tokens) == 50
    assert all(len(token) >= 32 for token in tokens)


def test_hash_do_refresh_e_deterministico_e_nao_revela_o_token() -> None:
    token = gerar_refresh_token()
    primeiro = hash_do_refresh_token(token)

    assert primeiro == hash_do_refresh_token(token)
    assert primeiro != token
    assert len(primeiro) == 64  # SHA-256 em hexadecimal
    assert all(caractere in "0123456789abcdef" for caractere in primeiro)


def test_tokens_diferentes_tem_hashes_diferentes() -> None:
    assert hash_do_refresh_token(gerar_refresh_token()) != hash_do_refresh_token(
        gerar_refresh_token()
    )


def test_expiracao_do_refresh_respeita_os_dias() -> None:
    agora = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
    assert calcular_expiracao_do_refresh(7, agora=agora) == agora + timedelta(days=7)