"""Hash e verificacao de senhas com **bcrypt**.

Decisoes:

- **bcrypt 5.0.0** (instalada) — ``passlib`` **nao** esta disponivel neste ambiente;
- *cost* configuravel, padrao :data:`CUSTO_PADRAO` (12 = 2^12 rodadas);
- **limite de 72 bytes**: e uma restricao do proprio bcrypt. Em vez de truncar em
  silencio, a senha e **recusada** — truncamento silencioso faria duas senhas
  diferentes autenticarem entre si;
- **tempo de resposta constante no login**: quando o e-mail nao existe, o endpoint
  executa um bcrypt de referencia (:func:`consumir_tempo_de_verificacao`) para que o
  tempo de resposta nao revele se a conta existe.
"""

from __future__ import annotations

import secrets
from functools import lru_cache

import bcrypt

from ..contratos.erros import CodigoDeErro, ErroDaAPIException

__all__ = [
    "CUSTO_MAXIMO",
    "CUSTO_MINIMO",
    "CUSTO_PADRAO",
    "TAMANHO_MAXIMO_EM_BYTES",
    "TAMANHO_MINIMO",
    "ErroDeSenhaLonga",
    "consumir_tempo_de_verificacao",
    "gerar_hash",
    "senha_confere",
    "senha_precisa_de_rehash",
]

#: Custo do bcrypt (numero de rodadas = 2^custo). 12 e o padrao recomendado.
CUSTO_PADRAO = 12

#: Menor custo aceito — o **proprio bcrypt** define 4 como minimo. Valores baixos
#: existem para **teste** (a suite ficaria lenta com custo 12).
CUSTO_MINIMO = 4

#: Maior custo aceito (acima disso o login fica lento demais para o MVP).
CUSTO_MAXIMO = 16

#: Comprimento minimo aceito na **criacao** de senha (politica do projeto).
TAMANHO_MINIMO = 8

#: Limite do proprio bcrypt: ele considera apenas os primeiros 72 bytes.
TAMANHO_MAXIMO_EM_BYTES = 72


class ErroDeSenhaLonga(ErroDaAPIException):
    """Senha acima do limite do bcrypt (72 bytes em UTF-8)."""

    def __init__(self) -> None:
        super().__init__(
            CodigoDeErro.CONTRATO_VIOLADO,
            f"A senha excede o limite de {TAMANHO_MAXIMO_EM_BYTES} bytes do bcrypt.",
            campo="senha",
            detalhe=(
                "O bcrypt considera apenas os primeiros 72 bytes. Truncar em silencio "
                "faria duas senhas diferentes autenticarem entre si, por isso o valor e "
                "recusado."
            ),
        )


def _para_bytes(senha: str) -> bytes:
    return senha.encode("utf-8")


def _validar_para_criacao(senha: str) -> bytes:
    """Valida a senha na **criacao**. Levanta erro explicito (nunca trunca)."""
    if not isinstance(senha, str) or not senha:
        raise ErroDaAPIException(
            CodigoDeErro.CONTRATO_VIOLADO, "A senha e obrigatoria.", campo="senha"
        )
    if len(senha) < TAMANHO_MINIMO:
        raise ErroDaAPIException(
            CodigoDeErro.CONTRATO_VIOLADO,
            f"A senha deve ter ao menos {TAMANHO_MINIMO} caracteres.",
            campo="senha",
        )

    em_bytes = _para_bytes(senha)
    if len(em_bytes) > TAMANHO_MAXIMO_EM_BYTES:
        raise ErroDeSenhaLonga()
    return em_bytes


def gerar_hash(senha: str, *, custo: int = CUSTO_PADRAO) -> str:
    """Gera o hash bcrypt de uma senha.

    Args:
        senha: senha em texto claro (>= 8 caracteres, <= 72 bytes em UTF-8).
        custo: numero de rodadas (2^custo). Padrao :data:`CUSTO_PADRAO`.

    Raises:
        ErroDaAPIException: senha ausente, curta demais ou acima de 72 bytes.
    """
    if not CUSTO_MINIMO <= custo <= CUSTO_MAXIMO:
        raise ErroDaAPIException(
            CodigoDeErro.ERRO_DE_CONFIGURACAO,
            f"custo do bcrypt fora da faixa aceita "
            f"({CUSTO_MINIMO} a {CUSTO_MAXIMO}); recebido {custo}.",
        )
    em_bytes = _validar_para_criacao(senha)
    return bcrypt.hashpw(em_bytes, bcrypt.gensalt(rounds=custo)).decode("utf-8")


def senha_confere(senha: str, hash_armazenado: str | None) -> bool:
    """Confere a senha contra o hash armazenado.

    **Nunca levanta excecao** por hash malformado ou senha acima do limite: devolve
    ``False``. O login deve falhar fechado (401), nao estourar erro interno.

    Returns:
        ``True`` somente quando a senha corresponde ao hash.
    """
    if not isinstance(senha, str) or not senha:
        return False
    if not isinstance(hash_armazenado, str) or not hash_armazenado:
        return False
    try:
        return bcrypt.checkpw(_para_bytes(senha), hash_armazenado.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def senha_precisa_de_rehash(hash_armazenado: str, *, custo: int = CUSTO_PADRAO) -> bool:
    """Indica se o hash foi gerado com custo diferente do atual.

    Util para elevar o custo gradualmente sem exigir troca de senha: no proximo login
    bem-sucedido, o hash pode ser regravado.

    Returns:
        ``True`` quando o hash e invalido ou usa outro custo.
    """
    partes = hash_armazenado.split("$")
    if len(partes) < 4 or not partes[2].isdigit():
        return True
    return int(partes[2]) != custo


@lru_cache(maxsize=1)
def _hash_de_referencia() -> bytes:
    """Hash bcrypt de um valor aleatorio, usado apenas para consumir tempo.

    Criado sob demanda (nao no import) para nao atrasar a inicializacao do servidor.
    """
    return bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt(rounds=CUSTO_PADRAO))


def consumir_tempo_de_verificacao(senha: str) -> None:
    """Executa um bcrypt de referencia, igualando o tempo de resposta do login.

    Chamado quando o e-mail informado **nao existe**: sem isso, a resposta voltaria
    muito mais rapido e revelaria, por diferenca de tempo, se a conta existe.
    """
    try:
        bcrypt.checkpw(_para_bytes(senha)[:TAMANHO_MAXIMO_EM_BYTES], _hash_de_referencia())
    except (ValueError, TypeError):
        pass
