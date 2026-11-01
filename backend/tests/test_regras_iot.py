"""Testes das regras de telemetria da Fase 3 (``app/regras_iot.py``).

A peca central e a **comparacao com a origem**: ``DECISOES_ARQUITETURAIS.md`` §3.4 exige,
para cada duplicacao controlada, "um teste que compare o comportamento novo com o da
origem". Aqui isso e feito executando o **handler Flask legado de verdade**
(``Ir_Alem1/server.py``) com o *test client* do Flask, sobre uma grade de entradas, e
comparando o resultado com :func:`app.regras_iot.avaliar_sinais`.
"""

from __future__ import annotations

import importlib.util
import itertools
import sys
from pathlib import Path

import pytest

from app.config import CANDIDATO_FASE_3
from app.regras_iot import (
    ALERTA_DE_FEBRE,
    ALERTA_DE_IMOBILIDADE,
    ALERTA_DE_TAQUICARDIA,
    LIMIAR_DE_BPM,
    LIMIAR_DE_TEMPERATURA,
    MENSAGEM_ESTAVEL,
    ORDEM_DE_PRIORIDADE,
    avaliar_sinais,
)

#: Fonte normativa das regras (o servico Flask desativado).
CAMINHO_DO_LEGADO: Path = CANDIDATO_FASE_3 / "server.py"

#: Valores de temperatura da grade de comparacao (cobre os dois lados do limiar).
TEMPERATURAS: tuple[float, ...] = (36.5, 38.0, 38.1, 39.5)

#: Valores de bpm da grade.
BPM: tuple[int, ...] = (60, 120, 121, 150)

#: Valores de movimento da grade.
MOVIMENTOS: tuple[bool, ...] = (True, False)


# --------------------------------------------------------------------------- #
# A origem (Fase 3) executada de verdade
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def handler_legado():
    """Carrega ``Ir_Alem1/server.py`` e devolve uma funcao que chama ``POST /sinais``.

    O envio de e-mail e substituido por um no-op: o objetivo e exercitar **as regras**,
    nao o SMTP (cuja senha na origem e o placeholder ``"SECRET"``, ou seja, nunca
    funcionou). Sem isso o teste tentaria conectar a ``smtp.gmail.com``.
    """
    if not CAMINHO_DO_LEGADO.is_file():
        pytest.skip(f"servico legado da Fase 3 nao encontrado em '{CAMINHO_DO_LEGADO}'.")
    pytest.importorskip("flask", reason="Flask nao instalado (necessario para o legado).")

    # Nao deixar residuo em uma fase anterior: sem isto, importar o modulo grava
    # `__pycache__/server.cpython-*.pyc` dentro de `Fase_3/`.
    escrever_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        especificacao = importlib.util.spec_from_file_location(
            "fase_3_server_legado", CAMINHO_DO_LEGADO
        )
        assert especificacao is not None and especificacao.loader is not None
        modulo = importlib.util.module_from_spec(especificacao)
        especificacao.loader.exec_module(modulo)
    finally:
        sys.dont_write_bytecode = escrever_bytecode

    enviados: list[str] = []
    modulo.enviar_email = enviados.append  # type: ignore[assignment]
    cliente = modulo.app.test_client()

    def chamar(payload: dict[str, object]) -> dict[str, object]:
        resposta = cliente.post("/sinais", json=payload)
        assert resposta.status_code == 200, resposta.data
        return resposta.get_json()

    # Exposto para o teste da divergencia, que precisa ver a resposta **nao**-200.
    chamar.cliente_bruto = cliente  # type: ignore[attr-defined]
    chamar.enviados = enviados  # type: ignore[attr-defined]
    return chamar


def test_o_legado_esta_presente_e_intacto() -> None:
    """A fonte normativa precisa existir e continuar com os literais das regras.

    Detecta *drift*: se a Fase 3 fosse alterada, a comparacao abaixo perderia sentido e
    este teste avisaria em vez de deixar a divergencia passar em silencio.
    """
    if not CAMINHO_DO_LEGADO.is_file():
        pytest.skip("servico legado da Fase 3 nao encontrado.")

    fonte = CAMINHO_DO_LEGADO.read_text(encoding="utf-8")
    assert "def receber_sinais()" in fonte
    assert "if temperatura > 38:" in fonte
    assert "elif bpm > 120:" in fonte
    assert "elif movimento == False:" in fonte
    assert '"FEBRE DETECTADA"' in fonte
    assert '"TAQUICARDIA DETECTADA"' in fonte
    assert '"AUSÊNCIA DE MOVIMENTO"' in fonte


def test_limiares_batem_com_os_da_origem() -> None:
    """Os limiares sao lidos do **arquivo-fonte**, nao repetidos no teste."""
    if not CAMINHO_DO_LEGADO.is_file():
        pytest.skip("servico legado da Fase 3 nao encontrado.")

    fonte = CAMINHO_DO_LEGADO.read_text(encoding="utf-8")
    assert f"if temperatura > {LIMIAR_DE_TEMPERATURA}:" in fonte
    assert f"elif bpm > {LIMIAR_DE_BPM}:" in fonte


def test_comportamento_identico_ao_da_origem(handler_legado) -> None:
    """Grade completa: temperatura x bpm x movimento — 32 combinacoes."""
    divergencias: list[str] = []

    for temperatura, bpm, movimento in itertools.product(
        TEMPERATURAS, BPM, MOVIMENTOS
    ):
        resposta = handler_legado(
            {"temperatura": temperatura, "bpm": bpm, "movimento": movimento}
        )
        esperado_alerta = None if resposta["status"] == "NORMAL" else resposta["mensagem"]
        obtido = avaliar_sinais(temperatura=temperatura, bpm=bpm, movimento=movimento)

        if obtido.alerta != esperado_alerta or obtido.mensagem != resposta["mensagem"]:
            divergencias.append(
                f"({temperatura}, {bpm}, {movimento}): origem={resposta['mensagem']!r} "
                f"nosso={obtido.mensagem!r}"
            )

    assert not divergencias, "Divergencia em relacao a Fase 3:\n" + "\n".join(divergencias)


def test_origem_quebra_sem_temperatura(handler_legado) -> None:
    """**Evidencia da divergencia declarada:** a origem responde 500 sem `temperatura`.

    ``None > 38`` levanta ``TypeError``. O contrato da Fase 7 permite enviar apenas
    ``bpm`` ("pelo menos um sinal vital"), entao herdar esse comportamento seria herdar
    um defeito. O teste fixa o fato — se a Fase 3 for corrigida, ele falha e a divergencia
    deixa de ser necessaria.
    """
    resposta = handler_legado.cliente_bruto.post("/sinais", json={"bpm": 130})
    assert resposta.status_code == 500


# --------------------------------------------------------------------------- #
# Limiares (estritamente maior, como na origem)
# --------------------------------------------------------------------------- #


def test_temperatura_acima_do_limiar_gera_febre() -> None:
    assert avaliar_sinais(temperatura=LIMIAR_DE_TEMPERATURA + 0.1).alerta == ALERTA_DE_FEBRE


def test_temperatura_no_limiar_nao_gera_alerta() -> None:
    """``> 38`` e nao ``>= 38``: 38,0 exato e considerado normal."""
    resultado = avaliar_sinais(temperatura=LIMIAR_DE_TEMPERATURA)
    assert resultado.alerta is None
    assert resultado.mensagem == MENSAGEM_ESTAVEL


def test_bpm_acima_do_limiar_gera_taquicardia() -> None:
    assert avaliar_sinais(bpm=LIMIAR_DE_BPM + 1).alerta == ALERTA_DE_TAQUICARDIA


def test_bpm_no_limiar_nao_gera_alerta() -> None:
    """``> 120`` e nao ``>= 120``: 120 exato e considerado normal."""
    assert avaliar_sinais(bpm=LIMIAR_DE_BPM).alerta is None


def test_ausencia_de_movimento_gera_alerta() -> None:
    assert avaliar_sinais(movimento=False).alerta == ALERTA_DE_IMOBILIDADE


def test_movimento_presente_nao_gera_alerta() -> None:
    assert avaliar_sinais(movimento=True).alerta is None


def test_leitura_sem_sinais_nao_gera_alerta() -> None:
    resultado = avaliar_sinais()
    assert resultado.alerta is None
    assert resultado.houve_alerta is False


# --------------------------------------------------------------------------- #
# Prioridade da cadeia if/elif (apenas um alerta por leitura)
# --------------------------------------------------------------------------- #


def test_febre_tem_prioridade_sobre_taquicardia() -> None:
    resultado = avaliar_sinais(temperatura=39.5, bpm=150)
    assert resultado.alerta == ALERTA_DE_FEBRE


def test_taquicardia_tem_prioridade_sobre_imobilidade() -> None:
    resultado = avaliar_sinais(bpm=150, movimento=False)
    assert resultado.alerta == ALERTA_DE_TAQUICARDIA


def test_febre_tem_prioridade_sobre_todas() -> None:
    resultado = avaliar_sinais(temperatura=39.5, bpm=150, movimento=False)
    assert resultado.alerta == ALERTA_DE_FEBRE


def test_apenas_um_alerta_por_leitura() -> None:
    """A cadeia e ``if/elif/elif``: o resultado **nao** e cumulativo.

    Trocar por checagens independentes devolveria tres alertas — uma divergencia
    silenciosa em relacao a origem.
    """
    resultado = avaliar_sinais(temperatura=39.5, bpm=150, movimento=False)
    assert resultado.mensagem == ALERTA_DE_FEBRE
    assert resultado.alerta is not None
    assert resultado.alerta not in (ALERTA_DE_TAQUICARDIA, ALERTA_DE_IMOBILIDADE)


def test_ordem_de_prioridade_documenta_a_cadeia() -> None:
    assert ORDEM_DE_PRIORIDADE == (
        ALERTA_DE_FEBRE,
        ALERTA_DE_TAQUICARDIA,
        ALERTA_DE_IMOBILIDADE,
    )


# --------------------------------------------------------------------------- #
# Divergencia declarada: sinal ausente nao quebra (a origem quebrava)
# --------------------------------------------------------------------------- #


def test_apenas_bpm_e_aceito() -> None:
    """O contrato permite enviar so ``bpm`` — a origem respondia 500 nesse caso."""
    assert avaliar_sinais(bpm=130).alerta == ALERTA_DE_TAQUICARDIA


def test_apenas_temperatura_e_aceita() -> None:
    assert avaliar_sinais(temperatura=39.0).alerta == ALERTA_DE_FEBRE


def test_apenas_movimento_e_aceito() -> None:
    assert avaliar_sinais(movimento=False).alerta == ALERTA_DE_IMOBILIDADE


def test_houve_alerta_indica_o_resultado() -> None:
    assert avaliar_sinais(temperatura=39.0).houve_alerta is True
    assert avaliar_sinais(temperatura=36.0).houve_alerta is False


def test_textos_sao_identicos_aos_da_origem() -> None:
    """Acentuacao preservada: os textos fazem parte do comportamento observavel."""
    assert ALERTA_DE_FEBRE == "FEBRE DETECTADA"
    assert ALERTA_DE_TAQUICARDIA == "TAQUICARDIA DETECTADA"
    assert ALERTA_DE_IMOBILIDADE == "AUSÊNCIA DE MOVIMENTO"
    assert MENSAGEM_ESTAVEL == "Paciente estável"