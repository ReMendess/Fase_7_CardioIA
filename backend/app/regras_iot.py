"""Regras de risco da telemetria IoT (Fase 3) — modulo de dominio do backend.

**Fonte normativa:** ``Fase_3/Cap_1_CardioIA_Conectada/Ir_Alem1/server.py`` (funcao
``receber_sinais``, linhas 58-96). A Fase 3 nao tem camada de dominio importavel — as
regras estao *inline* no *route handler* do Flask —, portanto esta e uma
**duplicacao controlada e declarada** (``DECISOES_ARQUITETURAIS.md`` §3.4):

| Item | Valor |
|---|---|
| Arquivo-fonte | ``Ir_Alem1/server.py`` |
| Trecho replicado | a cadeia ``if/elif/elif`` de ``receber_sinais`` |
| Verificacao | ``tests/test_regras_iot.py`` executa o **handler legado de verdade** (Flask) e compara o resultado com o desta funcao, sobre uma grade de entradas |

**Comportamento preservado (nao "melhorado"):**

- os limiares sao **literais da origem**: ``38`` e ``120`` (estritamente **maior**);
- a cadeia e ``if/elif/elif``: **apenas um** alerta por leitura, na ordem
  febre > taquicardia > imobilidade. Trocar por checagens independentes mudaria o
  resultado quando mais de uma condicao vale — e isso seria uma divergencia silenciosa.

**Divergencia declarada (unica):** a origem faz ``if temperatura > 38`` **sem** tratar
ausencia. Em Python, ``None > 38`` levanta ``TypeError`` — ou seja, a origem respondia
**500** a um payload sem ``temperatura``. Como o contrato da Fase 7
(``CONTRATOS_API.md`` §4.2) permite que ``temperatura`` **ou** ``bpm`` esteja ausente
("pelo menos um"), aqui a regra e **pulada** quando o sinal nao veio. Sem isso, o
endpoint herdaria o defeito.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ALERTA_DE_FEBRE",
    "ALERTA_DE_IMOBILIDADE",
    "ALERTA_DE_TAQUICARDIA",
    "LIMIAR_DE_BPM",
    "LIMIAR_DE_TEMPERATURA",
    "MENSAGEM_ESTAVEL",
    "ResultadoDosSinais",
    "avaliar_sinais",
]

#: Limiar de temperatura corporal, em graus Celsius (literal da origem).
LIMIAR_DE_TEMPERATURA = 38

#: Limiar de frequencia cardiaca, em batimentos por minuto (literal da origem).
LIMIAR_DE_BPM = 120

#: Textos **exatamente** como na origem (inclusive acentuacao) — fazem parte do
#: comportamento observavel replicado e sao comparados por teste.
ALERTA_DE_FEBRE = "FEBRE DETECTADA"
ALERTA_DE_TAQUICARDIA = "TAQUICARDIA DETECTADA"
ALERTA_DE_IMOBILIDADE = "AUSÊNCIA DE MOVIMENTO"
MENSAGEM_ESTAVEL = "Paciente estável"

#: Ordem de prioridade da cadeia ``if/elif`` da origem.
ORDEM_DE_PRIORIDADE: tuple[str, ...] = (
    ALERTA_DE_FEBRE,
    ALERTA_DE_TAQUICARDIA,
    ALERTA_DE_IMOBILIDADE,
)


@dataclass(frozen=True)
class ResultadoDosSinais:
    """Resultado da avaliacao de uma leitura de telemetria."""

    alerta: str | None
    mensagem: str

    @property
    def houve_alerta(self) -> bool:
        """``True`` quando alguma regra de risco foi acionada."""
        return self.alerta is not None


def avaliar_sinais(
    *,
    temperatura: float | None = None,
    bpm: int | None = None,
    movimento: bool | None = None,
) -> ResultadoDosSinais:
    """Aplica as regras de risco da Fase 3 a uma leitura.

    Args:
        temperatura: temperatura corporal em graus Celsius (``None`` = nao medida).
        bpm: frequencia cardiaca em batimentos por minuto (``None`` = nao medida).
        movimento: ``False`` indica ausencia de movimento (``None`` = nao medido).

    Returns:
        :class:`ResultadoDosSinais` — **no maximo um** alerta, na ordem de prioridade
        da origem (febre > taquicardia > imobilidade).

    Nota sobre ``movimento``: usa ``is False`` (e nao ``== False``). Para os valores
    ``bool``/``None`` do contrato o resultado e identico ao da origem; a diferenca
    apareceria apenas com ``0``, que na origem satisfaria ``0 == False``.
    """
    if temperatura is not None and temperatura > LIMIAR_DE_TEMPERATURA:
        return ResultadoDosSinais(ALERTA_DE_FEBRE, ALERTA_DE_FEBRE)

    if bpm is not None and bpm > LIMIAR_DE_BPM:
        return ResultadoDosSinais(ALERTA_DE_TAQUICARDIA, ALERTA_DE_TAQUICARDIA)

    if movimento is False:
        return ResultadoDosSinais(ALERTA_DE_IMOBILIDADE, ALERTA_DE_IMOBILIDADE)

    return ResultadoDosSinais(None, MENSAGEM_ESTAVEL)
