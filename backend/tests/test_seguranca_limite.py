"""Testes do limitador de tentativas (``app/seguranca/limite_de_tentativas.py``)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.seguranca.limite_de_tentativas import (
    JANELA_PADRAO_EM_SEGUNDOS,
    TENTATIVAS_PADRAO,
    LimitadorDeTentativas,
)

CHAVE = "medico@teste.local|127.0.0.1"
AGORA = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


def test_chave_desconhecida_nao_esta_bloqueada() -> None:
    limitador = LimitadorDeTentativas()
    assert limitador.esta_bloqueado(CHAVE, agora=AGORA) is False
    assert limitador.segundos_restantes(CHAVE, agora=AGORA) == 0


def test_bloqueia_ao_atingir_o_maximo() -> None:
    limitador = LimitadorDeTentativas(maximo=3)

    for indice in range(1, 4):
        total = limitador.registrar_falha(CHAVE, agora=AGORA)
        assert total == indice
        assert limitador.esta_bloqueado(CHAVE, agora=AGORA) is (indice >= 3)


def test_abaixo_do_maximo_nao_bloqueia() -> None:
    limitador = LimitadorDeTentativas(maximo=5)
    for _ in range(4):
        limitador.registrar_falha(CHAVE, agora=AGORA)
    assert limitador.esta_bloqueado(CHAVE, agora=AGORA) is False


def test_janela_deslizante_libera_apos_o_tempo() -> None:
    limitador = LimitadorDeTentativas(maximo=2, janela_em_segundos=300)
    limitador.registrar_falha(CHAVE, agora=AGORA)
    limitador.registrar_falha(CHAVE, agora=AGORA)
    assert limitador.esta_bloqueado(CHAVE, agora=AGORA) is True

    depois = AGORA + timedelta(seconds=301)
    assert limitador.esta_bloqueado(CHAVE, agora=depois) is False


def test_falhas_antigas_saem_da_janela() -> None:
    """A janela e deslizante: falhas antigas nao contam para o limite."""
    limitador = LimitadorDeTentativas(maximo=2, janela_em_segundos=300)
    limitador.registrar_falha(CHAVE, agora=AGORA)
    limitador.registrar_falha(CHAVE, agora=AGORA + timedelta(seconds=400))
    assert limitador.esta_bloqueado(CHAVE, agora=AGORA + timedelta(seconds=400)) is False


def test_limpar_zera_o_contador() -> None:
    limitador = LimitadorDeTentativas(maximo=1)
    limitador.registrar_falha(CHAVE, agora=AGORA)
    assert limitador.esta_bloqueado(CHAVE, agora=AGORA) is True

    limitador.limpar(CHAVE)
    assert limitador.esta_bloqueado(CHAVE, agora=AGORA) is False


def test_chaves_sao_independentes() -> None:
    """Bloquear um e-mail/IP nao pode bloquear outro usuario."""
    limitador = LimitadorDeTentativas(maximo=1)
    limitador.registrar_falha("a@teste.local|10.0.0.1", agora=AGORA)

    assert limitador.esta_bloqueado("a@teste.local|10.0.0.1", agora=AGORA) is True
    assert limitador.esta_bloqueado("b@teste.local|10.0.0.1", agora=AGORA) is False
    assert limitador.esta_bloqueado("a@teste.local|10.0.0.2", agora=AGORA) is False


def test_segundos_restantes_diminuem_com_o_tempo() -> None:
    limitador = LimitadorDeTentativas(maximo=1, janela_em_segundos=300)
    limitador.registrar_falha(CHAVE, agora=AGORA)

    assert limitador.segundos_restantes(CHAVE, agora=AGORA) == 300
    assert limitador.segundos_restantes(CHAVE, agora=AGORA + timedelta(seconds=100)) == 200
    assert limitador.segundos_restantes(CHAVE, agora=AGORA + timedelta(seconds=400)) == 0


def test_segundos_restantes_zero_quando_nao_bloqueado() -> None:
    limitador = LimitadorDeTentativas(maximo=3)
    limitador.registrar_falha(CHAVE, agora=AGORA)
    assert limitador.segundos_restantes(CHAVE, agora=AGORA) == 0


def test_limpar_tudo_remove_todos_os_registros() -> None:
    limitador = LimitadorDeTentativas(maximo=1)
    limitador.registrar_falha("a|1", agora=AGORA)
    limitador.registrar_falha("b|1", agora=AGORA)
    assert limitador.chaves_rastreadas == 2

    limitador.limpar_tudo()
    assert limitador.chaves_rastreadas == 0


def test_limpar_chave_inexistente_nao_falha() -> None:
    LimitadorDeTentativas().limpar("nao-existe")


@pytest.mark.parametrize(("maximo", "janela"), [(0, 300), (-1, 300), (5, 0), (5, -1)])
def test_parametros_invalidos_sao_rejeitados(maximo: int, janela: int) -> None:
    with pytest.raises(ValueError):
        LimitadorDeTentativas(maximo=maximo, janela_em_segundos=janela)


def test_valores_padrao_do_projeto() -> None:
    """5 falhas em 5 minutos (``PLANO_SEGURANCA.md``)."""
    assert TENTATIVAS_PADRAO == 5
    assert JANELA_PADRAO_EM_SEGUNDOS == 300
