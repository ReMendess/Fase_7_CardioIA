"""Testes do modulo de senhas (``app/seguranca/senhas.py``)."""

from __future__ import annotations

import pytest

from app.contratos.erros import CodigoDeErro, ErroDaAPIException
from app.seguranca.senhas import (
    CUSTO_MAXIMO,
    CUSTO_MINIMO,
    CUSTO_PADRAO,
    TAMANHO_MAXIMO_EM_BYTES,
    TAMANHO_MINIMO,
    ErroDeSenhaLonga,
    consumir_tempo_de_verificacao,
    gerar_hash,
    senha_confere,
    senha_precisa_de_rehash,
)
from tests.conftest import CUSTO_DE_TESTE, SENHA_DE_TESTE


# --------------------------------------------------------------------------- #
# gerar_hash
# --------------------------------------------------------------------------- #


def test_hash_tem_o_formato_do_bcrypt() -> None:
    gerado = gerar_hash(SENHA_DE_TESTE, custo=CUSTO_DE_TESTE)
    assert gerado.startswith("$2b$")
    assert f"${CUSTO_DE_TESTE:02d}$" in gerado
    assert gerado != SENHA_DE_TESTE


def test_hash_usa_salt_aleatorio() -> None:
    """Duas chamadas para a mesma senha produzem hashes diferentes."""
    primeiro = gerar_hash(SENHA_DE_TESTE, custo=CUSTO_DE_TESTE)
    segundo = gerar_hash(SENHA_DE_TESTE, custo=CUSTO_DE_TESTE)
    assert primeiro != segundo
    assert senha_confere(SENHA_DE_TESTE, primeiro)
    assert senha_confere(SENHA_DE_TESTE, segundo)


def test_hash_rejeita_senha_curta() -> None:
    with pytest.raises(ErroDaAPIException) as capturado:
        gerar_hash("a" * (TAMANHO_MINIMO - 1), custo=CUSTO_DE_TESTE)
    assert capturado.value.codigo is CodigoDeErro.CONTRATO_VIOLADO
    assert capturado.value.erro.campo == "senha"


def test_hash_rejeita_senha_vazia() -> None:
    with pytest.raises(ErroDaAPIException):
        gerar_hash("", custo=CUSTO_DE_TESTE)


def test_hash_aceita_exatamente_o_limite_do_bcrypt() -> None:
    """72 bytes e o maximo aceito — nao ha truncamento silencioso."""
    senha = "a" * TAMANHO_MAXIMO_EM_BYTES
    gerado = gerar_hash(senha, custo=CUSTO_DE_TESTE)
    assert senha_confere(senha, gerado)


def test_hash_recusa_senha_acima_do_limite() -> None:
    """O bcrypt trunca em 72 bytes; truncar em silencio seria uma falha de seguranca."""
    with pytest.raises(ErroDeSenhaLonga) as capturado:
        gerar_hash("a" * (TAMANHO_MAXIMO_EM_BYTES + 1), custo=CUSTO_DE_TESTE)
    assert capturado.value.codigo is CodigoDeErro.CONTRATO_VIOLADO
    assert "72 bytes" in capturado.value.mensagem


def test_hash_conta_bytes_e_nao_caracteres() -> None:
    """Caractere multibyte ocupa mais de um byte em UTF-8."""
    senha_multibyte = "ç" * 40  # 80 bytes em UTF-8
    with pytest.raises(ErroDeSenhaLonga):
        gerar_hash(senha_multibyte, custo=CUSTO_DE_TESTE)


def test_hash_rejeita_custo_fora_da_faixa() -> None:
    for custo_invalido in (CUSTO_MINIMO - 1, CUSTO_MAXIMO + 1):
        with pytest.raises(ErroDaAPIException) as capturado:
            gerar_hash(SENHA_DE_TESTE, custo=custo_invalido)
        assert capturado.value.codigo is CodigoDeErro.ERRO_DE_CONFIGURACAO


def test_custo_padrao_e_maior_que_o_de_teste() -> None:
    """Garante que os testes usam custo reduzido de proposito."""
    assert CUSTO_DE_TESTE < CUSTO_PADRAO


# --------------------------------------------------------------------------- #
# senha_confere
# --------------------------------------------------------------------------- #


def test_senha_confere_verdadeiro() -> None:
    gerado = gerar_hash(SENHA_DE_TESTE, custo=CUSTO_DE_TESTE)
    assert senha_confere(SENHA_DE_TESTE, gerado) is True


def test_senha_confere_falso_para_senha_errada() -> None:
    gerado = gerar_hash(SENHA_DE_TESTE, custo=CUSTO_DE_TESTE)
    assert senha_confere("outra-senha-qualquer", gerado) is False


def test_senha_confere_nao_levanta_com_hash_malformado() -> None:
    """Login deve falhar fechado (401), nunca estourar erro interno."""
    assert senha_confere(SENHA_DE_TESTE, "isto-nao-e-um-hash-bcrypt") is False
    assert senha_confere(SENHA_DE_TESTE, "") is False
    assert senha_confere(SENHA_DE_TESTE, None) is False


def test_senha_confere_nao_levanta_com_senha_longa() -> None:
    """Senha acima de 72 bytes nao deve derrubar o login com erro interno."""
    gerado = gerar_hash(SENHA_DE_TESTE, custo=CUSTO_DE_TESTE)
    assert senha_confere("a" * 200, gerado) is False


def test_senha_confere_nao_levanta_com_senha_vazia() -> None:
    gerado = gerar_hash(SENHA_DE_TESTE, custo=CUSTO_DE_TESTE)
    assert senha_confere("", gerado) is False


def test_senha_confere_rejeita_booleano_como_hash() -> None:
    assert senha_confere(SENHA_DE_TESTE, True) is False  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# senha_precisa_de_rehash
# --------------------------------------------------------------------------- #


def test_rehash_falso_quando_o_custo_confere() -> None:
    gerado = gerar_hash(SENHA_DE_TESTE, custo=CUSTO_DE_TESTE)
    assert senha_precisa_de_rehash(gerado, custo=CUSTO_DE_TESTE) is False


def test_rehash_verdadeiro_quando_o_custo_muda() -> None:
    gerado = gerar_hash(SENHA_DE_TESTE, custo=CUSTO_DE_TESTE)
    assert senha_precisa_de_rehash(gerado, custo=CUSTO_DE_TESTE + 1) is True


def test_rehash_verdadeiro_para_hash_invalido() -> None:
    assert senha_precisa_de_rehash("nao-e-hash") is True


# --------------------------------------------------------------------------- #
# consumir_tempo_de_verificacao
# --------------------------------------------------------------------------- #


def test_consumir_tempo_nao_levanta() -> None:
    """Executado no caminho de e-mail inexistente: nunca pode quebrar o login."""
    consumir_tempo_de_verificacao(SENHA_DE_TESTE)
    consumir_tempo_de_verificacao("")
    consumir_tempo_de_verificacao("a" * 500)
