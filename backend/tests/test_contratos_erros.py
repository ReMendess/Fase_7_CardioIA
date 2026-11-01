"""Testes do enum de erros e do mapeamento HTTP (``app/contratos/erros.py``)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.contratos.erros import (
    HTTP_POR_CODIGO,
    MAPA_HTTP_PARA_CODIGO,
    CodigoDeErro,
    ErroDaAPI,
    ErroDaAPIException,
    codigo_do_http,
    http_do_codigo,
)


def test_todo_codigo_tem_mapeamento_http() -> None:
    """Nenhum codigo de erro pode ficar sem codigo HTTP canonico."""
    sem_mapa = [codigo.value for codigo in CodigoDeErro if codigo not in HTTP_POR_CODIGO]
    assert sem_mapa == []


def test_codigos_herdados_da_fase_5_mantem_os_status_originais() -> None:
    """Os codigos herdados preservam os HTTP da Fase 5 — **exceto** ``auth-failed``.

    A Fase 5 usava ``507`` (``Insufficient Storage``, RFC 4918) para falha de
    autenticacao no provedor. O codigo foi mantido; o transporte foi corrigido para
    ``502`` (ver ``CONTRATOS_API.md`` §3.2.1).
    """
    assert http_do_codigo(CodigoDeErro.NAO_CONFIGURADO) == 501
    assert http_do_codigo(CodigoDeErro.FALHA_DE_AUTENTICACAO_EXTERNA) == 502
    assert http_do_codigo(CodigoDeErro.COTA_EXCEDIDA) == 429
    assert http_do_codigo(CodigoDeErro.TIMEOUT_EXTERNO) == 504
    assert http_do_codigo(CodigoDeErro.ERRO_DE_SERVICO_EXTERNO) == 502


def test_507_nao_e_usado_pela_fase_7() -> None:
    """``507`` e ``Insufficient Storage``: nenhum codigo da Fase 7 pode emitir esse status.

    Regressao: a Fase 5 o usava para falha de autenticacao do provedor.
    """
    assert 507 not in HTTP_POR_CODIGO.values()
    assert 507 not in MAPA_HTTP_PARA_CODIGO


def test_falha_do_provedor_nao_usa_401_nem_403() -> None:
    """Erro do **provedor** nunca se disfarca de erro de autenticacao **do usuario**.

    Se a falha de credencial do Watson voltasse como 401/403, um cliente bem-comportado
    tentaria reautenticar o usuario (ou encerraria a sessao) por causa de um problema
    que nao e dele.

    ``COTA_EXCEDIDA`` (429) e a **unica** excecao deliberada: o 429 do provedor tem
    semantica identica ("excedeu a cota, tente mais tarde") e propaga-lo preserva o
    ``Retry-After`` implicito. Os demais codigos externos ficam em 5xx.
    """
    externos = (
        CodigoDeErro.NAO_CONFIGURADO,
        CodigoDeErro.FALHA_DE_AUTENTICACAO_EXTERNA,
        CodigoDeErro.TIMEOUT_EXTERNO,
        CodigoDeErro.ERRO_DE_SERVICO_EXTERNO,
        CodigoDeErro.ERRO_DE_SERVICO_DE_VISAO,
    )
    for codigo in externos:
        status = http_do_codigo(codigo)
        assert status >= 500, f"{codigo.value} deveria ser 5xx, veio {status}"

    # Nenhum codigo de origem externa pode colidir com a autenticacao do usuario.
    for codigo in (*externos, CodigoDeErro.COTA_EXCEDIDA):
        assert http_do_codigo(codigo) not in (401, 403), (
            f"{codigo.value} nao pode usar 401/403 — isso e do usuario, nao do provedor"
        )

    # ...e o inverso: a autenticacao do usuario continua 4xx.
    assert http_do_codigo(CodigoDeErro.NAO_AUTENTICADO) == 401
    assert http_do_codigo(CodigoDeErro.NAO_AUTORIZADO) == 403


def test_codigos_derivados_da_fase_6_tem_status_do_contrato() -> None:
    """Os codigos derivados das excecoes tipadas da Fase 6 seguem CONTRATOS_API §3.2."""
    assert http_do_codigo(CodigoDeErro.PACIENTE_INVALIDO) == 422
    assert http_do_codigo(CodigoDeErro.DADOS_DO_PACIENTE_INVALIDOS) == 422
    assert http_do_codigo(CodigoDeErro.MODELO_INDISPONIVEL) == 503
    assert http_do_codigo(CodigoDeErro.MODELO_INCOMPATIVEL) == 500
    assert http_do_codigo(CodigoDeErro.FALHA_DE_PREVISAO) == 500
    assert http_do_codigo(CodigoDeErro.BASE_DE_PROTOCOLOS_INVALIDA) == 500
    assert http_do_codigo(CodigoDeErro.CONTRATO_VIOLADO) == 422


def test_codigos_novos_tem_status_esperado() -> None:
    """Codigos introduzidos pela Fase 7."""
    assert http_do_codigo(CodigoDeErro.NAO_AUTENTICADO) == 401
    assert http_do_codigo(CodigoDeErro.NAO_AUTORIZADO) == 403
    assert http_do_codigo(CodigoDeErro.NAO_ENCONTRADO) == 404
    assert http_do_codigo(CodigoDeErro.CONFLITO) == 409
    assert http_do_codigo(CodigoDeErro.LIMITE_EXCEDIDO) == 413
    assert http_do_codigo(CodigoDeErro.TAXA_EXCEDIDA) == 429
    assert http_do_codigo(CodigoDeErro.ERRO_INTERNO) == 500


@pytest.mark.parametrize(
    ("status", "esperado"),
    [
        (401, CodigoDeErro.NAO_AUTENTICADO),
        (403, CodigoDeErro.NAO_AUTORIZADO),
        (404, CodigoDeErro.NAO_ENCONTRADO),
        (405, CodigoDeErro.NAO_ENCONTRADO),
        (422, CodigoDeErro.CONTRATO_VIOLADO),
        (503, CodigoDeErro.MODELO_INDISPONIVEL),
    ],
)
def test_codigo_do_http_mapeia_status_conhecidos(
    status: int, esperado: CodigoDeErro
) -> None:
    """A traducao HTTP -> dominio cobre os status usados pela API."""
    assert codigo_do_http(status) == esperado


def test_codigo_do_http_tem_fallback_por_classe_de_status() -> None:
    """Status nao mapeados caem em ERRO_INTERNO (5xx) ou CONTRATO_VIOLADO (4xx)."""
    assert codigo_do_http(599) == CodigoDeErro.ERRO_INTERNO
    assert codigo_do_http(418) == CodigoDeErro.CONTRATO_VIOLADO


def test_mapa_http_para_codigo_preserva_a_classe_do_status() -> None:
    """A normalizacao HTTP -> dominio preserva 4xx/5xx (nao pode "subir" a classe).

    O mapa **nao** e o inverso de ``HTTP_POR_CODIGO``: e muitos-para-um
    (``400``/``422`` -> ``CONTRATO_VIOLADO``; ``404``/``405`` -> ``NAO_ENCONTRADO``;
    ``429`` compartilhado por cota e taxa). O que se garante e que um erro de cliente
    nunca vira erro de servidor, e vice-versa.
    """
    for status, codigo in MAPA_HTTP_PARA_CODIGO.items():
        canonico = HTTP_POR_CODIGO[codigo]
        assert (status >= 500) == (canonico >= 500), (
            f"classe divergente: {status} -> {codigo.value} (canonico {canonico})"
        )


def test_todo_codigo_do_mapa_tem_http_canonico() -> None:
    """Nenhum codigo usado na normalizacao pode ficar sem status canonico."""
    for codigo in MAPA_HTTP_PARA_CODIGO.values():
        assert codigo in HTTP_POR_CODIGO


def test_erro_da_api_proibe_campo_desconhecido() -> None:
    """O contrato de erro e fechado (extra='forbid')."""
    with pytest.raises(ValidationError):
        ErroDaAPI(
            codigo=CodigoDeErro.ERRO_INTERNO,
            mensagem="falha",
            campo_inexistente="x",  # type: ignore[call-arg]
        )


def test_erro_da_api_exige_mensagem_nao_vazia() -> None:
    """Mensagem vazia nao e aceita (falha nunca fica muda)."""
    with pytest.raises(ValidationError):
        ErroDaAPI(codigo=CodigoDeErro.ERRO_INTERNO, mensagem="")


def test_excecao_usa_o_http_canonico_do_codigo() -> None:
    """Sem HTTP explicito, a excecao assume o status canonico."""
    erro = ErroDaAPIException(CodigoDeErro.NAO_ENCONTRADO, "paciente nao encontrado")
    assert erro.http == 404
    assert erro.codigo is CodigoDeErro.NAO_ENCONTRADO
    assert erro.erro.mensagem == "paciente nao encontrado"
    assert erro.erro.campo is None


def test_excecao_permite_http_e_contexto_explicitos() -> None:
    """O HTTP pode ser sobrescrito e o campo/detalhe sao propagados."""
    erro = ErroDaAPIException(
        CodigoDeErro.PACIENTE_INVALIDO,
        "campos ausentes",
        campo="spo2_media",
        detalhe="O modelo espera exatamente: ...",
        http=400,
    )
    assert erro.http == 400
    assert erro.erro.campo == "spo2_media"
    assert erro.erro.detalhe == "O modelo espera exatamente: ..."


def test_excecao_e_uma_excecao_python() -> None:
    """A excecao pode ser capturada genericamente por ``except Exception``."""
    with pytest.raises(ErroDaAPIException):
        raise ErroDaAPIException(CodigoDeErro.ERRO_INTERNO, "falha")
