"""Testes do adapter da Fase 4 (``app/integracao/fase_4.py``).

Duas frentes:

1. **Constantes contra o arquivo-fonte** da Fase 4 — o risco **R6** exige registrar a origem
   normativa e comparar. A Fase 4 nao informa o nome do modelo nem o limiar (achado **I9**),
   entao o backend os declara; este teste garante que a declaracao **nao divergiu** do fonte.
2. **Contrato HTTP** contra um servico falso que reproduz o `app.py` (TensorFlow **nao** esta
   instalado aqui — a ausencia dele e a razao da Decisao 1-C).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import CANDIDATO_FASE_4, Configuracoes
from app.contratos.erros import CodigoDeErro, ErroDaAPIException
from app.integracao.fase_4 import (
    CAMPO_DO_ARQUIVO,
    CLASSES_POSSIVEIS,
    DIMENSOES_ESPERADAS_DA_IMAGEM,
    LIMIAR_DE_DECISAO_DA_VISAO,
    NOME_DO_MODELO_DA_VISAO,
    chamar_previsao,
    url_da_previsao,
)
from tests.conftest import ServicoDeVisaoFalso, _configuracao_base, imagem_de_teste

#: Fonte normativa do servico de visao (Fase 4).
CAMINHO_DA_FASE_4: Path = CANDIDATO_FASE_4 / "app.py"


def _configuracao_apontando_para(
    url: str, *, timeout: float = 5.0, token: str = ""
) -> Configuracoes:
    """Configuracao de teste apontando para o servico falso."""
    import tempfile

    return _configuracao_base(
        tempfile.mkdtemp(prefix="fase7_visao_"),
        servico_visao_url=url,
        servico_visao_timeout_segundos=timeout,
        servico_visao_token=token,
    )


# --------------------------------------------------------------------------- #
# Constantes contra a fonte da Fase 4 (risco R6 / achado I9)
# --------------------------------------------------------------------------- #


def test_fonte_da_fase_4_esta_presente() -> None:
    if not CAMINHO_DA_FASE_4.is_file():
        pytest.skip(f"servico da Fase 4 nao encontrado em '{CAMINHO_DA_FASE_4}'.")
    assert "def predict()" in CAMINHO_DA_FASE_4.read_text(encoding="utf-8")


def test_nome_do_modelo_bate_com_a_fonte() -> None:
    if not CAMINHO_DA_FASE_4.is_file():
        pytest.skip("servico da Fase 4 nao encontrado.")
    fonte = CAMINHO_DA_FASE_4.read_text(encoding="utf-8")
    assert NOME_DO_MODELO_DA_VISAO in fonte


def test_limiar_bate_com_a_fonte() -> None:
    """A Fase 4 nao expoe o limiar: o backend o declara — e aqui se confere que bate."""
    if not CAMINHO_DA_FASE_4.is_file():
        pytest.skip("servico da Fase 4 nao encontrado.")
    fonte = CAMINHO_DA_FASE_4.read_text(encoding="utf-8")
    assert f"probability > {LIMIAR_DE_DECISAO_DA_VISAO}" in fonte


def test_dimensoes_batem_com_a_fonte() -> None:
    if not CAMINHO_DA_FASE_4.is_file():
        pytest.skip("servico da Fase 4 nao encontrado.")
    fonte = CAMINHO_DA_FASE_4.read_text(encoding="utf-8")
    largura, altura = DIMENSOES_ESPERADAS_DA_IMAGEM
    assert f"target_size=({largura}, {altura})" in fonte


def test_campo_do_arquivo_bate_com_a_fonte() -> None:
    if not CAMINHO_DA_FASE_4.is_file():
        pytest.skip("servico da Fase 4 nao encontrado.")
    fonte = CAMINHO_DA_FASE_4.read_text(encoding="utf-8")
    # A fonte usa a forma negativa: `if "image" not in request.files:`.
    assert f'"{CAMPO_DO_ARQUIVO}" not in request.files' in fonte


def test_classes_batem_com_a_fonte() -> None:
    if not CAMINHO_DA_FASE_4.is_file():
        pytest.skip("servico da Fase 4 nao encontrado.")
    fonte = CAMINHO_DA_FASE_4.read_text(encoding="utf-8")
    for classe in CLASSES_POSSIVEIS:
        assert f'"{classe}"' in fonte


# --------------------------------------------------------------------------- #
# URL
# --------------------------------------------------------------------------- #


def test_url_da_previsao_nao_duplica_barra() -> None:
    com_barra = _configuracao_apontando_para("http://host:5001/")
    sem_barra = _configuracao_apontando_para("http://host:5001")
    assert url_da_previsao(com_barra) == "http://host:5001/predict"
    assert url_da_previsao(sem_barra) == "http://host:5001/predict"


# --------------------------------------------------------------------------- #
# Chamada bem-sucedida
# --------------------------------------------------------------------------- #


def test_previsao_devolve_os_nomes_de_origem(
    servico_de_visao_falso: ServicoDeVisaoFalso,
) -> None:
    """O adapter devolve `class`/`confidence` crus; a traducao (N4) e da borda."""
    servico_de_visao_falso.responder(probabilidade=0.93)
    config = _configuracao_apontando_para(servico_de_visao_falso.url)

    resposta = chamar_previsao(
        imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=config
    )

    assert resposta.classe == "Pneumonia"
    assert resposta.confianca == 93.0


def test_previsao_de_classe_normal(servico_de_visao_falso: ServicoDeVisaoFalso) -> None:
    """A Fase 4 devolve a confianca da classe **vencedora** (1 - p quando p <= 0.5)."""
    servico_de_visao_falso.responder(probabilidade=0.2)
    config = _configuracao_apontando_para(servico_de_visao_falso.url)

    resposta = chamar_previsao(
        imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=config
    )

    assert resposta.classe == "Normal"
    assert resposta.confianca == 80.0


def test_adapter_usa_o_campo_image(servico_de_visao_falso: ServicoDeVisaoFalso) -> None:
    """O servico exige o campo `image`; errar o nome daria 400."""
    config = _configuracao_apontando_para(servico_de_visao_falso.url)
    chamar_previsao(imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=config)

    assert servico_de_visao_falso.recebidas[0]["campos"] == ["image"]


def test_token_de_servico_so_e_enviado_quando_configurado(
    servico_de_visao_falso: ServicoDeVisaoFalso,
) -> None:
    sem_token = _configuracao_apontando_para(servico_de_visao_falso.url)
    chamar_previsao(imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=sem_token)
    assert "X-Service-Token" not in servico_de_visao_falso.recebidas[-1]["cabecalhos"]

    com_token = _configuracao_apontando_para(servico_de_visao_falso.url, token="segredo-interno")
    chamar_previsao(imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=com_token)
    enviado = servico_de_visao_falso.recebidas[-1]["cabecalhos"]["X-Service-Token"]
    assert enviado == "segredo-interno"


# --------------------------------------------------------------------------- #
# Falhas do servico -> contrato de erro
# --------------------------------------------------------------------------- #


def test_servico_fora_do_ar_devolve_502() -> None:
    """Servico inalcancavel -> `httpx.ConnectError` -> 502, nunca 500 cru.

    Usa um host ``.invalid`` (RFC 2606) em vez de uma porta fechada: neste ambiente
    (Windows) conectar a ``127.0.0.1:<porta livre>`` **nao e recusado** — o firewall
    descarta o pacote e a tentativa termina no *timeout*, o que mediria o comportamento do
    sistema operacional em vez do mapeamento de erro do adapter.
    """
    config = _configuracao_apontando_para(
        "http://servico-de-visao-inexistente.invalid:5001", timeout=5.0
    )

    with pytest.raises(ErroDaAPIException) as capturado:
        chamar_previsao(imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=config)

    assert capturado.value.codigo is CodigoDeErro.ERRO_DE_SERVICO_DE_VISAO
    assert capturado.value.http == 502
    assert "5001" in (capturado.value.erro.detalhe or "")


def test_servico_lento_devolve_504(servico_de_visao_falso: ServicoDeVisaoFalso) -> None:
    servico_de_visao_falso.demorar(2.0)
    config = _configuracao_apontando_para(servico_de_visao_falso.url, timeout=0.4)

    with pytest.raises(ErroDaAPIException) as capturado:
        chamar_previsao(imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=config)

    assert capturado.value.codigo is CodigoDeErro.TIMEOUT_EXTERNO
    assert capturado.value.http == 504


def test_erro_interno_do_servico_devolve_502(
    servico_de_visao_falso: ServicoDeVisaoFalso,
) -> None:
    servico_de_visao_falso.falhar_com(500, {"error": "Falha ao processar imagem"})
    config = _configuracao_apontando_para(servico_de_visao_falso.url)

    with pytest.raises(ErroDaAPIException) as capturado:
        chamar_previsao(imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=config)

    assert capturado.value.codigo is CodigoDeErro.ERRO_DE_SERVICO_DE_VISAO
    assert "500" in capturado.value.mensagem


def test_servico_recusando_o_arquivo_devolve_502(
    servico_de_visao_falso: ServicoDeVisaoFalso,
) -> None:
    """O 400 do servico tambem vira 502: o erro e do outro lado da fronteira."""
    servico_de_visao_falso.falhar_com(400, {"error": "Nenhuma imagem enviada"})
    config = _configuracao_apontando_para(servico_de_visao_falso.url)

    with pytest.raises(ErroDaAPIException) as capturado:
        chamar_previsao(imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=config)

    assert capturado.value.http == 502


def test_corpo_nao_json_devolve_502(servico_de_visao_falso: ServicoDeVisaoFalso) -> None:
    servico_de_visao_falso.falhar_com(200, "<html>proxy interceptou</html>")
    config = _configuracao_apontando_para(servico_de_visao_falso.url)

    with pytest.raises(ErroDaAPIException) as capturado:
        chamar_previsao(imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=config)

    assert capturado.value.codigo is CodigoDeErro.ERRO_DE_SERVICO_DE_VISAO
    assert "nao e JSON" in capturado.value.mensagem


def test_corpo_que_nao_e_objeto_devolve_502(
    servico_de_visao_falso: ServicoDeVisaoFalso,
) -> None:
    servico_de_visao_falso.falhar_com(200, [1, 2, 3])
    config = _configuracao_apontando_para(servico_de_visao_falso.url)

    with pytest.raises(ErroDaAPIException) as capturado:
        chamar_previsao(imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=config)

    assert "nao e um objeto JSON" in capturado.value.mensagem


def test_classe_desconhecida_devolve_502(servico_de_visao_falso: ServicoDeVisaoFalso) -> None:
    """Um servico que responde fora do contrato nao pode virar diagnostico silencioso."""
    servico_de_visao_falso.falhar_com(200, {"class": "Covid", "confidence": 90.0})
    config = _configuracao_apontando_para(servico_de_visao_falso.url)

    with pytest.raises(ErroDaAPIException) as capturado:
        chamar_previsao(imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=config)

    assert capturado.value.erro.campo == "class"


def test_confianca_booleana_devolve_502(servico_de_visao_falso: ServicoDeVisaoFalso) -> None:
    """`isinstance(True, int)` e True: sem a guarda, `true` passaria como confianca 1."""
    servico_de_visao_falso.falhar_com(200, {"class": "Normal", "confidence": True})
    config = _configuracao_apontando_para(servico_de_visao_falso.url)

    with pytest.raises(ErroDaAPIException) as capturado:
        chamar_previsao(imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=config)

    assert capturado.value.erro.campo == "confidence"


@pytest.mark.parametrize("confianca", [-1.0, 101.0, "muito"])
def test_confianca_invalida_devolve_502(
    servico_de_visao_falso: ServicoDeVisaoFalso, confianca: object
) -> None:
    servico_de_visao_falso.falhar_com(200, {"class": "Normal", "confidence": confianca})
    config = _configuracao_apontando_para(servico_de_visao_falso.url)

    with pytest.raises(ErroDaAPIException) as capturado:
        chamar_previsao(imagem_de_teste(), nome_arquivo="rx.jpg", mime="image/jpeg", config=config)

    assert capturado.value.codigo is CodigoDeErro.ERRO_DE_SERVICO_DE_VISAO