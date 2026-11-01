"""Testes da rota de saude e dos handlers de erro (``app/rotas/saude.py``, ``app/main.py``)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Configuracoes
from app.main import NOME_DO_SERVICO, criar_app
from app.rotas.saude import COMANDO_DE_TREINO

CAMINHO_SAUDE = "/api/v1/health"


# --------------------------------------------------------------------------- #
# /health — contrato do envelope
# --------------------------------------------------------------------------- #


def test_saude_responde_200(cliente_sem_modelo: TestClient) -> None:
    resposta = cliente_sem_modelo.get(CAMINHO_SAUDE)
    assert resposta.status_code == 200


def test_saude_devolve_o_envelope_completo(cliente_com_modelo: TestClient) -> None:
    """Todos os campos do contrato estao presentes."""
    corpo = cliente_com_modelo.get(CAMINHO_SAUDE).json()
    assert set(corpo) == {
        "id_execucao",
        "gerado_em",
        "status",
        "dados",
        "avisos",
        "limitacoes",
        "erros",
        "metadados",
    }
    assert uuid.UUID(corpo["id_execucao"]).version == 4
    assert datetime.fromisoformat(corpo["gerado_em"]).tzinfo is not None
    assert corpo["erros"] == []
    assert corpo["limitacoes"] == []
    assert corpo["metadados"]["versao_api"] == "v1"
    assert corpo["metadados"]["origem"] == NOME_DO_SERVICO


def test_saude_identifica_o_servico(cliente_com_modelo: TestClient) -> None:
    dados = cliente_com_modelo.get(CAMINHO_SAUDE).json()["dados"]
    assert dados["servico"] == NOME_DO_SERVICO
    assert dados["versao_api"] == "v1"
    assert dados["ambiente"] == "teste"
    assert dados["versao_do_backend"]


def test_saude_reporta_artefato_presente_como_concluido(
    cliente_com_modelo: TestClient,
) -> None:
    """Com o artefato presente, o status e CONCLUIDO e nao ha avisos."""
    corpo = cliente_com_modelo.get(CAMINHO_SAUDE).json()
    assert corpo["status"] == "CONCLUIDO"
    assert corpo["avisos"] == []
    assert corpo["dados"]["artefato_do_modelo"]["presente"] is True
    assert corpo["dados"]["artefato_do_modelo"]["metadados_presentes"] is True


def test_saude_reporta_artefato_ausente_como_ressalva(
    cliente_sem_modelo: TestClient,
) -> None:
    """Sem o artefato o servico continua util, mas com ressalva explicita."""
    corpo = cliente_sem_modelo.get(CAMINHO_SAUDE).json()
    assert corpo["status"] == "CONCLUIDO_COM_RESSALVAS"
    assert corpo["dados"]["artefato_do_modelo"]["presente"] is False
    assert len(corpo["avisos"]) == 1
    assert COMANDO_DE_TREINO in corpo["avisos"][0]
    assert "MODELO_INDISPONIVEL" in corpo["avisos"][0]


def test_saude_lista_as_rotas_registradas(cliente_com_modelo: TestClient) -> None:
    rotas = cliente_com_modelo.get(CAMINHO_SAUDE).json()["dados"]["rotas_registradas"]
    assert CAMINHO_SAUDE in rotas


def test_saude_nao_expoe_credenciais(cliente_com_modelo: TestClient) -> None:
    """As integracoes sao reportadas apenas como booleano."""
    integracoes = cliente_com_modelo.get(CAMINHO_SAUDE).json()["dados"][
        "integracoes_configuradas"
    ]
    assert all(isinstance(valor, bool) for valor in integracoes.values())


def test_saude_declara_que_nao_executa_o_modelo(cliente_com_modelo: TestClient) -> None:
    metadados = cliente_com_modelo.get(CAMINHO_SAUDE).json()["metadados"]
    assert metadados["verificacao"] == "existencia_de_arquivos"


# --------------------------------------------------------------------------- #
# Handlers de erro — contrato uniforme
# --------------------------------------------------------------------------- #


def test_rota_inexistente_respeita_o_envelope(cliente_com_modelo: TestClient) -> None:
    """404 do framework tambem passa pelo envelope comum."""
    resposta = cliente_com_modelo.get("/api/v1/rota-que-nao-existe")
    assert resposta.status_code == 404
    corpo = resposta.json()
    assert corpo["status"] == "ERRO"
    assert corpo["dados"] is None
    assert corpo["erros"][0]["codigo"] == "NAO_ENCONTRADO"
    assert corpo["erros"][0]["mensagem"]


def test_metodo_invalido_respeita_o_envelope(cliente_com_modelo: TestClient) -> None:
    resposta = cliente_com_modelo.delete(CAMINHO_SAUDE)
    assert resposta.status_code == 405
    assert resposta.json()["erros"][0]["codigo"] == "NAO_ENCONTRADO"


def test_contrato_violado_retorna_422_com_o_campo(
    configuracoes_com_modelo: Configuracoes,
) -> None:
    """Payload fora do contrato vira CONTRATO_VIOLADO com o campo culpado."""
    app = criar_app(configuracoes_com_modelo)

    @app.post("/api/v1/_teste/eco")
    def eco(valor: int) -> dict[str, int]:
        return {"valor": valor}

    cliente = TestClient(app, raise_server_exceptions=False)
    resposta = cliente.post("/api/v1/_teste/eco", json={"valor": "nao-e-numero"})
    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["status"] == "ERRO"
    assert corpo["erros"][0]["codigo"] == "CONTRATO_VIOLADO"
    assert corpo["erros"][0]["campo"] == "valor"
    assert corpo["erros"][0]["detalhe"]


def test_falha_inesperada_retorna_500_no_envelope(
    configuracoes_com_modelo: Configuracoes,
) -> None:
    """Excecao nao prevista vira ERRO_INTERNO — nunca falha silenciosa."""
    app = criar_app(configuracoes_com_modelo)

    @app.get("/api/v1/_teste/explode")
    def explode() -> None:
        raise RuntimeError("falha proposital do teste")

    cliente = TestClient(app, raise_server_exceptions=False)
    resposta = cliente.get("/api/v1/_teste/explode")
    assert resposta.status_code == 500
    corpo = resposta.json()
    assert corpo["status"] == "ERRO"
    assert corpo["erros"][0]["codigo"] == "ERRO_INTERNO"
    assert corpo["erros"][0]["detalhe"] == "RuntimeError"


def test_excecao_de_dominio_usa_o_http_do_codigo(
    configuracoes_com_modelo: Configuracoes,
) -> None:
    """ErroDaAPIException chega ao cliente com o codigo e o HTTP corretos."""
    from app.contratos.erros import CodigoDeErro, ErroDaAPIException

    app = criar_app(configuracoes_com_modelo)

    @app.get("/api/v1/_teste/indisponivel")
    def indisponivel() -> None:
        raise ErroDaAPIException(
            CodigoDeErro.MODELO_INDISPONIVEL,
            "modelo ausente",
            detalhe="treine com python -m src.cardioia.ml.train",
        )

    cliente = TestClient(app, raise_server_exceptions=False)
    resposta = cliente.get("/api/v1/_teste/indisponivel")
    assert resposta.status_code == 503
    erro = resposta.json()["erros"][0]
    assert erro["codigo"] == "MODELO_INDISPONIVEL"
    assert erro["mensagem"] == "modelo ausente"
    assert "src.cardioia.ml.train" in erro["detalhe"]


# --------------------------------------------------------------------------- #
# Documentacao e CORS
# --------------------------------------------------------------------------- #


def test_openapi_documenta_a_rota_de_saude(cliente_com_modelo: TestClient) -> None:
    esquema = cliente_com_modelo.get("/openapi.json").json()
    assert CAMINHO_SAUDE in esquema["paths"]
    assert "get" in esquema["paths"][CAMINHO_SAUDE]


def test_cors_nao_e_aberto(cliente_com_modelo: TestClient) -> None:
    """Origem desconhecida nao recebe cabecalho de permissao."""
    resposta = cliente_com_modelo.get(
        CAMINHO_SAUDE, headers={"Origin": "http://origem-nao-autorizada.example"}
    )
    assert "access-control-allow-origin" not in {
        chave.lower() for chave in resposta.headers
    }


def test_cors_permite_a_origem_configurada(cliente_com_modelo: TestClient) -> None:
    resposta = cliente_com_modelo.get(
        CAMINHO_SAUDE, headers={"Origin": "http://localhost:5173"}
    )
    assert resposta.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_nao_usa_credenciais_de_cookie(cliente_com_modelo: TestClient) -> None:
    """O token viaja no header Authorization — cookies desabilitados."""
    resposta = cliente_com_modelo.get(
        CAMINHO_SAUDE, headers={"Origin": "http://localhost:5173"}
    )
    assert resposta.headers.get("access-control-allow-credentials") is None


def test_aplicacao_guarda_a_configuracao_no_estado(
    configuracoes_com_modelo: Configuracoes,
) -> None:
    app: FastAPI = criar_app(configuracoes_com_modelo)
    assert app.state.configuracoes is configuracoes_com_modelo
    assert app.state.nome_do_servico == NOME_DO_SERVICO