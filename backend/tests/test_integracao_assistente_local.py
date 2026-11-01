"""Testes do provedor local do assistente (``app/integracao/assistente_local.py``).

O provedor local e o **padrao**: responde da base de conhecimento do projeto, sem rede,
credencial ou cota. Estes testes fixam o que ele garante — e o que ele **nao** faz.
"""

from __future__ import annotations

import pytest

from app.integracao.assistente_local import (
    INTENCOES,
    PONTUACAO_MINIMA,
    PROVEDOR,
    RESPOSTA_PADRAO,
    nome_do_provedor,
    normalizar,
    responder,
)


# --------------------------------------------------------------------------- #
# Normalizacao
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("Dor no Peito", "dor no peito"),
        ("  espacos   demais  ", "espacos demais"),
        ("Palpitacao", "palpitacao"),
        ("PALPITACAO", "palpitacao"),
        ("", ""),
    ],
)
def test_normalizar_padroniza_o_texto(entrada: str, esperado: str) -> None:
    assert normalizar(entrada) == esperado


def test_normalizar_remove_acentos() -> None:
    """O usuario escreve com acento; os termos do catalogo sao sem acento."""
    assert normalizar("Palpitação") == normalizar("palpitacao")
    assert normalizar("Pressão alta") == normalizar("pressao alta")
    assert normalizar("Fadiga e cansaço") == normalizar("fadiga e cansaco")


# --------------------------------------------------------------------------- #
# Casamento de intencao
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("mensagem", "trecho_esperado"),
    [
        ("Estou com dor no peito", "emergencia"),
        ("Dor no peito e suor frio, o que faco?", "emergencia"),
        ("Desmaiei ontem a noite", "emergencia"),
        ("Ando com falta de ar", "falta de ar"),
        ("Meu coracao esta acelerado", "batimento"),
        ("Minha pressao subiu", "pressao alta"),
        ("Estou com febre", "febre"),
        ("Sinto muito cansaco ultimamente", "cansaco"),
        ("Como evitar doencas do coracao?", "fatores de risco"),
        ("O que voce faz?", "assistente virtual"),
    ],
)
def test_reconhece_o_assunto_e_responde(mensagem: str, trecho_esperado: str) -> None:
    """Cada assunto conhecido devolve uma resposta que trata do assunto."""
    resposta = responder(mensagem)

    assert resposta.resposta.strip()
    assert trecho_esperado.lower() in normalizar(resposta.resposta)


def test_acento_do_usuario_nao_impede_o_casamento() -> None:
    """O termo e comparado sem acento — 'palpitação' casa com 'palpitacao'."""
    assert responder("Sinto uma palpitação forte").resposta == responder(
        "Sinto uma palpitação forte".replace("á", "a")
    ).resposta


def test_sinal_de_alerta_encaminha_para_emergencia() -> None:
    """Dor no peito com falta de ar nao pode virar uma resposta generica."""
    resposta = responder("Dor no peito e falta de ar agora")

    assert "192" in resposta.resposta
    assert "AGORA" in resposta.resposta


# --------------------------------------------------------------------------- #
# Ausencia de resposta inventada
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "mensagem",
    [
        "qual e a capital da Franca",
        "me conta uma piada",
        "a",
        "??",
        "",
        "   ",
    ],
)
def test_assunto_desconhecido_nao_inventa_orientacao(mensagem: str) -> None:
    """Fora do dominio, devolve o texto padrao — nunca uma orientacao clinica."""
    assert responder(mensagem).resposta == RESPOSTA_PADRAO


def test_pontuacao_minima_existe_e_e_positiva() -> None:
    """O piso de relevancia evita que um termo curto escolha um assunto clinico."""
    assert PONTUACAO_MINIMA > 0


# --------------------------------------------------------------------------- #
# Contrato da resposta
# --------------------------------------------------------------------------- #


def test_resposta_segue_o_contrato_do_adaptador() -> None:
    """Mesmo formato do provedor externo — a rota trata os dois igual."""
    resposta = responder("Dor no peito")

    assert isinstance(resposta.resposta, str)
    assert resposta.resposta.strip()


def test_nao_ha_sessao_de_provedor() -> None:
    """O provedor local e stateless: nao existe `session_id` a guardar (I8)."""
    assert responder("Dor no peito").session_id_do_provedor is None


def test_nome_do_provedor_e_estavel() -> None:
    """O nome vai para a trilha de auditoria; nao pode mudar sem querer."""
    assert nome_do_provedor() == PROVEDOR == "local"


# --------------------------------------------------------------------------- #
# Integridade do catalogo
# --------------------------------------------------------------------------- #


def test_catalogo_tem_intencoes() -> None:
    assert len(INTENCOES) >= 8


def test_nomes_das_intencoes_sao_unicos() -> None:
    nomes = [intencao.nome for intencao in INTENCOES]
    assert len(nomes) == len(set(nomes))


@pytest.mark.parametrize("intencao", INTENCOES, ids=lambda i: i.nome)
def test_toda_intencao_e_utilizavel(intencao) -> None:
    """Nenhuma intencao pode ficar sem termo, sem resposta ou com termo nao normalizado."""
    assert intencao.termos, f"{intencao.nome} nao tem termos"
    assert intencao.resposta.strip(), f"{intencao.nome} nao tem resposta"
    for termo in intencao.termos:
        # Termo com acento ou maiuscula nunca casaria com o texto normalizado.
        assert termo == normalizar(termo), f"{intencao.nome}: termo fora do padrao: {termo!r}"


def test_intencao_de_emergencia_vem_primeiro() -> None:
    """Ordem importa: um sinal de alerta nao pode ser ofuscado por outro assunto."""
    assert INTENCOES[0].nome == "emergencia"

