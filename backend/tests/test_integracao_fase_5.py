"""Testes do adapter da Fase 5 (``app/integracao/fase_5.py``).

Tres frentes:

1. **Constantes contra o arquivo-fonte** da Fase 5 (risco **R6**): versao da API, timeout,
   identificador de usuario e o texto de fallback.
2. **Mapeamento de erro contra o fonte** de ``friendly_watson_error`` — as faixas de status
   precisam ser as mesmas.
3. **Seguranca (achado S1 / correcao C1):** o adapter **nao** usa os valores default de
   ``IBM_API.py``, que contem a chave real do projeto versionada.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.config import CANDIDATO_FASE_5
from app.contratos.erros import CodigoDeErro, ErroDaAPIException
from app.integracao.fase_5 import (
    MENSAGEM_SEM_TEXTO,
    TIMEOUT_PADRAO_DO_WATSON,
    USUARIO_PADRAO_DO_ASSISTENTE,
    VERSAO_DA_API_DO_WATSON,
    configuracao_faltando,
    criar_cliente,
    extrair_resposta,
    traduzir_erro,
)
from tests.conftest import (
    ClienteFalso,
    ErroDoSdk,
    _configuracao_base,
    configuracao_do_watson as _configuracao_do_watson,
)

#: Fontes normativas da Fase 5.
CAMINHO_IBM_API: Path = CANDIDATO_FASE_5 / "IBM_API.py"
CAMINHO_APP: Path = CANDIDATO_FASE_5 / "app.py"


def _fonte(caminho: Path) -> str:
    """Le um arquivo-fonte da Fase 5, pulando o teste se ele nao existir."""
    if not caminho.is_file():
        pytest.skip(f"fonte da Fase 5 nao encontrada em '{caminho}'.")
    return caminho.read_text(encoding="utf-8")


# `_configuracao_do_watson` e `tests.conftest.configuracao_do_watson`, importada com este
# nome: os dois arquivos de teste do assistente usam a mesma configuracao.


# --------------------------------------------------------------------------- #
# Constantes contra a fonte (risco R6)
# --------------------------------------------------------------------------- #


def test_versao_da_api_bate_com_o_ibm_api() -> None:
    fonte = _fonte(CAMINHO_IBM_API)
    assert f'VERSION = "{VERSAO_DA_API_DO_WATSON}"' in fonte


def test_timeout_bate_com_o_ibm_api() -> None:
    fonte = _fonte(CAMINHO_IBM_API)
    assert f"WATSON_TIMEOUT = {TIMEOUT_PADRAO_DO_WATSON}" in fonte


def test_usuario_padrao_bate_com_o_app() -> None:
    fonte = _fonte(CAMINHO_APP)
    assert f'DEFAULT_USER_ID = "{USUARIO_PADRAO_DO_ASSISTENTE}"' in fonte


def test_texto_de_fallback_bate_com_o_app() -> None:
    """O texto devolvido quando o Watson nao manda bloco de texto e o mesmo da Fase 5."""
    fonte = _fonte(CAMINHO_APP)
    assert MENSAGEM_SEM_TEXTO in fonte


def test_mapeamento_de_status_bate_com_o_app() -> None:
    """As faixas de status de ``friendly_watson_error`` precisam ser as mesmas."""
    fonte = _fonte(CAMINHO_APP)
    assert "if code in (401, 403):" in fonte
    assert "if code == 404:" in fonte
    assert "if code == 429:" in fonte
    assert "if code in (408, 504):" in fonte
    assert "if code in (400, 500, 502, 503):" in fonte


# --------------------------------------------------------------------------- #
# Seguranca: nunca cair nos defaults do codigo da Fase 5 (S1 / C1)
# --------------------------------------------------------------------------- #


def test_fonte_da_fase_5_tem_credencial_como_default() -> None:
    """**Evidencia do achado S1:** ``IBM_API.py`` usa ``os.getenv`` **com** valor default.

    Este teste documenta o motivo de o backend nao importar aquele modulo. Se a Fase 5 for
    corrigida (defaults removidos), o teste falha e a divergencia declarada pode ser revista.
    """
    fonte = _fonte(CAMINHO_IBM_API)
    assert "os.getenv(" in fonte
    assert "API_KEY = os.getenv(" in fonte
    # O segundo argumento do getenv e o default — que no arquivo original e uma credencial.
    assert '"WATSON_API_KEY",' in fonte


def test_configuracao_vazia_nao_cai_em_default() -> None:
    """Sem variaveis de ambiente, o assistente se declara **nao configurado**.

    E a prova comportamental de que o backend nao herda as credenciais do codigo da Fase 5:
    se herdasse, a lista viria vazia e uma chamada real seria disparada com a chave vazada.
    """
    config = _configuracao_base(tempfile.mkdtemp(prefix="fase7_sem_watson_"))
    faltando = configuracao_faltando(config)
    assert faltando == [
        "WATSON_API_KEY",
        "WATSON_SERVICE_URL",
        "WATSON_ASSISTANT_ID",
        "WATSON_ENVIRONMENT_ID",
    ]


def test_configuracao_completa_nao_reporta_faltantes() -> None:
    assert configuracao_faltando(_configuracao_do_watson()) == []


def test_configuracao_parcial_reporta_apenas_o_que_falta() -> None:
    config = _configuracao_do_watson(watson_assistant_id="")
    assert configuracao_faltando(config) == ["WATSON_ASSISTANT_ID"]


# --------------------------------------------------------------------------- #
# Extracao da resposta (_extract_reply)
# --------------------------------------------------------------------------- #


def test_extrai_um_bloco_de_texto() -> None:
    payload = {"output": {"generic": [{"response_type": "text", "text": "Ola!"}]}}
    assert extrair_resposta(payload) == "Ola!"


def test_junta_varios_blocos_de_texto() -> None:
    payload = {
        "output": {
            "generic": [
                {"response_type": "text", "text": "Primeira linha"},
                {"response_type": "text", "text": "Segunda linha"},
            ]
        }
    }
    assert extrair_resposta(payload) == "Primeira linha\nSegunda linha"


def test_ignora_blocos_que_nao_sao_texto() -> None:
    payload = {
        "output": {
            "generic": [
                {"response_type": "option", "title": "Escolha"},
                {"response_type": "text", "text": "Apenas este conta"},
            ]
        }
    }
    assert extrair_resposta(payload) == "Apenas este conta"


def test_remove_espacos_das_bordas() -> None:
    payload = {"output": {"generic": [{"response_type": "text", "text": "  oi  "}]}}
    assert extrair_resposta(payload) == "oi"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"output": {}},
        {"output": {"generic": []}},
        {"output": {"generic": [{"response_type": "text", "text": ""}]}},
        {"output": {"generic": "nao-e-lista"}},
        "nao-e-dicionario",
        None,
    ],
)
def test_sem_texto_devolve_a_mensagem_de_fallback(payload: object) -> None:
    """Nunca inventar resposta: sem bloco de texto, devolve o texto fixo da Fase 5."""
    assert extrair_resposta(payload) == MENSAGEM_SEM_TEXTO


# --------------------------------------------------------------------------- #
# Traducao de erro (friendly_watson_error)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("codigo", "esperado", "http"),
    [
        (401, CodigoDeErro.FALHA_DE_AUTENTICACAO_EXTERNA, 502),
        (403, CodigoDeErro.FALHA_DE_AUTENTICACAO_EXTERNA, 502),
        (404, CodigoDeErro.ERRO_DE_SERVICO_EXTERNO, 502),
        (429, CodigoDeErro.COTA_EXCEDIDA, 429),
        (408, CodigoDeErro.TIMEOUT_EXTERNO, 504),
        (504, CodigoDeErro.TIMEOUT_EXTERNO, 504),
        (400, CodigoDeErro.ERRO_DE_SERVICO_EXTERNO, 502),
        (500, CodigoDeErro.ERRO_DE_SERVICO_EXTERNO, 502),
        (502, CodigoDeErro.ERRO_DE_SERVICO_EXTERNO, 502),
        (503, CodigoDeErro.ERRO_DE_SERVICO_EXTERNO, 502),
        (418, CodigoDeErro.ERRO_DE_SERVICO_EXTERNO, 502),
    ],
)
def test_traducao_de_erro_segue_o_mapeamento_da_fase_5(
    codigo: int, esperado: CodigoDeErro, http: int
) -> None:
    erro = traduzir_erro(ErroDoSdk(codigo, "detalhe do provedor"))
    assert erro.codigo is esperado
    assert erro.http == http


def test_detalhe_tecnico_vai_para_o_campo_detalhe() -> None:
    """A Fase 5 concatenava o detalhe na mensagem; aqui ele vai em `detalhe` (nota N5)."""
    erro = traduzir_erro(ErroDoSdk(500, "Internal Server Error do Watson"))
    assert erro.erro.detalhe == "Internal Server Error do Watson"
    assert "Internal Server Error" not in erro.mensagem


def test_detalhe_e_truncado() -> None:
    erro = traduzir_erro(ErroDoSdk(500, "x" * 1000))
    assert erro.erro.detalhe is not None
    assert len(erro.erro.detalhe) == 300


def test_excecao_sem_code_cai_em_erro_de_servico_externo() -> None:
    erro = traduzir_erro(RuntimeError("sem codigo"))
    assert erro.codigo is CodigoDeErro.ERRO_DE_SERVICO_EXTERNO
    assert erro.erro.detalhe == "sem codigo"


# --------------------------------------------------------------------------- #
# Criacao do cliente
# --------------------------------------------------------------------------- #


def test_cliente_e_criado_a_partir_da_configuracao() -> None:
    """Usa o SDK instalado, com a URL e o timeout da configuracao (nao os da Fase 5)."""
    config = _configuracao_do_watson(watson_timeout_segundos=12)
    assistente = criar_cliente(config)

    assert assistente.service_url == config.watson_service_url
    assert assistente.http_config == {"timeout": 12}
    assert assistente.version == VERSAO_DA_API_DO_WATSON


# --------------------------------------------------------------------------- #
# Fluxo de conversa (com o cliente do SDK falso — ver ``tests/conftest.py``)
# --------------------------------------------------------------------------- #


@pytest.fixture
def cliente_falso(cliente_do_watson_falso: ClienteFalso) -> ClienteFalso:
    """Alias do duble compartilhado, mantendo os nomes usados neste modulo."""
    return cliente_do_watson_falso


def test_primeiro_turno_abre_sessao(cliente_falso: ClienteFalso) -> None:
    from app.integracao.fase_5 import conversar

    resultado = conversar("Ola", session_id=None, config=_configuracao_do_watson())

    assert resultado.resposta == "Resposta do assistente"
    assert resultado.session_id_do_provedor == "sessao-1"
    assert cliente_falso.sessoes_criadas == 1


def test_turno_seguinte_reaproveita_a_sessao(cliente_falso: ClienteFalso) -> None:
    from app.integracao.fase_5 import conversar

    resultado = conversar(
        "De novo", session_id="sessao-existente", config=_configuracao_do_watson()
    )

    assert resultado.session_id_do_provedor == "sessao-existente"
    assert cliente_falso.sessoes_criadas == 0


def test_mensagem_e_enviada_com_o_contrato_do_sdk(cliente_falso: ClienteFalso) -> None:
    from app.integracao.fase_5 import conversar

    config = _configuracao_do_watson()
    conversar("Ola", session_id=None, config=config)

    enviada = cliente_falso.mensagens_enviadas[0]
    assert enviada["assistant_id"] == config.watson_assistant_id
    assert enviada["environment_id"] == config.watson_environment_id
    assert enviada["input"] == {"message_type": "text", "text": "Ola"}
    assert enviada["user_id"] == USUARIO_PADRAO_DO_ASSISTENTE


def test_sessao_expirada_e_recriada_e_o_envio_repetido(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Comportamento da Fase 5: 404 no envio -> recria a sessao e reintenta **uma vez**."""
    from app.integracao import fase_5
    from app.integracao.fase_5 import conversar

    cliente = ClienteFalso(
        sessoes=("sessao-nova",),
        falhas=(ErroDoSdk(404, "session not found"), None),
    )
    monkeypatch.setattr(fase_5, "criar_cliente", lambda config: cliente)

    resultado = conversar("Ola", session_id="sessao-antiga", config=_configuracao_do_watson())

    assert resultado.session_id_do_provedor == "sessao-nova"
    assert cliente.sessoes_criadas == 1
    assert len(cliente.mensagens_enviadas) == 2


def test_404_persistente_devolve_erro_de_servico_externo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Se a recuperacao tambem falhar, o erro sobe traduzido (502)."""
    from app.integracao import fase_5
    from app.integracao.fase_5 import conversar

    cliente = ClienteFalso(
        sessoes=("sessao-nova",),
        falhas=(ErroDoSdk(404, "session not found"), ErroDoSdk(404, "ainda nao existe")),
    )
    monkeypatch.setattr(fase_5, "criar_cliente", lambda config: cliente)

    with pytest.raises(ErroDaAPIException) as capturado:
        conversar("Ola", session_id="sessao-antiga", config=_configuracao_do_watson())

    assert capturado.value.codigo is CodigoDeErro.ERRO_DE_SERVICO_EXTERNO


def test_sessao_sem_identificador_devolve_502(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem ``session_id`` nao ha conversa a continuar — melhor falhar do que seguir sem ele."""
    from app.integracao import fase_5
    from app.integracao.fase_5 import conversar

    cliente = ClienteFalso(sessoes=(None,))
    monkeypatch.setattr(fase_5, "criar_cliente", lambda config: cliente)

    with pytest.raises(ErroDaAPIException) as capturado:
        conversar("Ola", session_id=None, config=_configuracao_do_watson())

    assert capturado.value.codigo is CodigoDeErro.ERRO_DE_SERVICO_EXTERNO
    assert "session_id" in capturado.value.mensagem


def test_falha_ao_abrir_sessao_e_traduzida(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.integracao import fase_5
    from app.integracao.fase_5 import conversar

    cliente = ClienteFalso()

    def _falhar(**kwargs: object) -> None:
        raise ErroDoSdk(401, "bad key")

    monkeypatch.setattr(fase_5, "criar_cliente", lambda config: cliente)
    monkeypatch.setattr(cliente, "create_session", _falhar)

    with pytest.raises(ErroDaAPIException) as capturado:
        conversar("Ola", session_id=None, config=_configuracao_do_watson())

    assert capturado.value.codigo is CodigoDeErro.FALHA_DE_AUTENTICACAO_EXTERNA
    assert capturado.value.http == 502


def test_falha_no_envio_e_traduzida(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.integracao import fase_5
    from app.integracao.fase_5 import conversar

    cliente = ClienteFalso(falhas=(ErroDoSdk(429, "quota"),))
    monkeypatch.setattr(fase_5, "criar_cliente", lambda config: cliente)

    with pytest.raises(ErroDaAPIException) as capturado:
        conversar("Ola", session_id="sessao-existente", config=_configuracao_do_watson())

    assert capturado.value.codigo is CodigoDeErro.COTA_EXCEDIDA
    assert capturado.value.http == 429