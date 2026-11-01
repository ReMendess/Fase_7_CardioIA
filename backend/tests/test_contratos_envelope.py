"""Testes do envelope comum ``RespostaAPI[T]`` (``app/contratos/envelope.py``)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from app.contratos.envelope import (
    STATUS_COM_FALHA,
    STATUS_COM_SUCESSO,
    RespostaAPI,
    StatusDaResposta,
    agora_utc,
    novo_id_execucao,
    resposta_de_erro,
    resposta_de_sucesso,
)
from app.contratos.erros import CodigoDeErro, ErroDaAPI


class DadosDeExemplo(BaseModel):
    """Payload tipado de exemplo."""

    model_config = ConfigDict(extra="forbid")

    nome: str
    valor: float


def _erro() -> ErroDaAPI:
    return ErroDaAPI(codigo=CodigoDeErro.ERRO_INTERNO, mensagem="falha de exemplo")


# --------------------------------------------------------------------------- #
# Status
# --------------------------------------------------------------------------- #


def test_status_reproduz_os_quatro_valores_da_fase_6() -> None:
    """O enum nao cria um segundo eixo: sao exatamente os 4 valores da Fase 6."""
    assert [s.value for s in StatusDaResposta] == [
        "CONCLUIDO",
        "CONCLUIDO_COM_RESSALVAS",
        "INCOMPLETO",
        "ERRO",
    ]
    assert len(STATUS_COM_SUCESSO) == 2
    assert len(STATUS_COM_FALHA) == 2


# --------------------------------------------------------------------------- #
# Coerencia status x conteudo (regra R1 do contrato)
# --------------------------------------------------------------------------- #


def test_concluido_com_dados_e_valido() -> None:
    resposta = RespostaAPI[DadosDeExemplo](
        status=StatusDaResposta.CONCLUIDO,
        dados=DadosDeExemplo(nome="exemplo", valor=0.99),
    )
    assert resposta.concluida is True
    assert resposta.dados is not None
    assert resposta.dados.nome == "exemplo"


def test_concluido_sem_dados_e_rejeitado() -> None:
    """Sucesso sem conteudo nao pode existir (falha nunca vira sucesso)."""
    with pytest.raises(ValidationError, match="exige 'dados'"):
        RespostaAPI[DadosDeExemplo](status=StatusDaResposta.CONCLUIDO, dados=None)


def test_concluido_com_erros_e_rejeitado() -> None:
    """Sucesso com erro registrado e incoerente."""
    with pytest.raises(ValidationError, match="nao pode conter 'erros'"):
        RespostaAPI[DadosDeExemplo](
            status=StatusDaResposta.CONCLUIDO,
            dados=DadosDeExemplo(nome="x", valor=1.0),
            erros=[_erro()],
        )


def test_concluido_com_ressalvas_tambem_exige_dados() -> None:
    with pytest.raises(ValidationError, match="exige 'dados'"):
        RespostaAPI[DadosDeExemplo](
            status=StatusDaResposta.CONCLUIDO_COM_RESSALVAS,
            dados=None,
            avisos=["aviso qualquer"],
        )


def test_erro_sem_erros_e_rejeitado() -> None:
    """Falha sem explicacao nao e aceita (nada de falha silenciosa)."""
    with pytest.raises(ValidationError, match="exige ao menos um item em 'erros'"):
        RespostaAPI[DadosDeExemplo](status=StatusDaResposta.ERRO, dados=None)


def test_incompleto_sem_erros_e_rejeitado() -> None:
    with pytest.raises(ValidationError, match="exige ao menos um item em 'erros'"):
        RespostaAPI[DadosDeExemplo](status=StatusDaResposta.INCOMPLETO)


def test_erro_com_erros_e_valido() -> None:
    resposta = RespostaAPI[DadosDeExemplo](status=StatusDaResposta.ERRO, erros=[_erro()])
    assert resposta.concluida is False
    assert resposta.dados is None
    assert len(resposta.erros) == 1
    assert resposta.erros[0].codigo is CodigoDeErro.ERRO_INTERNO


# --------------------------------------------------------------------------- #
# Campos obrigatorios e fechamento do contrato
# --------------------------------------------------------------------------- #


def test_envelope_proibe_campos_desconhecidos() -> None:
    with pytest.raises(ValidationError):
        RespostaAPI[DadosDeExemplo](
            status=StatusDaResposta.CONCLUIDO,
            dados=DadosDeExemplo(nome="x", valor=1.0),
            campo_inexistente="y",  # type: ignore[call-arg]
        )


def test_dados_respeitam_o_schema_tipado() -> None:
    """O ``dados`` e validado pelo tipo declarado no generico."""
    with pytest.raises(ValidationError):
        RespostaAPI[DadosDeExemplo](
            status=StatusDaResposta.CONCLUIDO,
            dados={"nome": "sem_o_campo_valor"},  # type: ignore[arg-type]
        )


def test_id_execucao_e_um_uuid4_valido() -> None:
    resposta = RespostaAPI[DadosDeExemplo](
        status=StatusDaResposta.CONCLUIDO, dados=DadosDeExemplo(nome="x", valor=1.0)
    )
    identificador = uuid.UUID(resposta.id_execucao)
    assert identificador.version == 4


def test_gerado_em_tem_timezone() -> None:
    resposta = RespostaAPI[DadosDeExemplo](
        status=StatusDaResposta.CONCLUIDO, dados=DadosDeExemplo(nome="x", valor=1.0)
    )
    assert resposta.gerado_em.tzinfo is not None
    assert resposta.gerado_em.utcoffset() == timezone.utc.utcoffset(None)


def test_avisos_e_limitacoes_nascem_vazios() -> None:
    resposta = RespostaAPI[DadosDeExemplo](
        status=StatusDaResposta.CONCLUIDO, dados=DadosDeExemplo(nome="x", valor=1.0)
    )
    assert resposta.avisos == []
    assert resposta.limitacoes == []
    assert resposta.erros == []
    assert resposta.metadados == {}
    assert resposta.tem_ressalvas is False


# --------------------------------------------------------------------------- #
# Serializacao
# --------------------------------------------------------------------------- #


def test_como_dicionario_e_json_safe() -> None:
    resposta = resposta_de_sucesso(
        DadosDeExemplo(nome="exemplo", valor=0.9900),
        avisos=["aviso de faixa"],
        metadados={"versao_api": "v1"},
    )
    dicionario = resposta.como_dicionario()
    texto = json.dumps(dicionario, ensure_ascii=False)  # nao pode levantar
    assert '"status": "CONCLUIDO"' in texto
    assert dicionario["dados"]["valor"] == 0.99
    assert dicionario["metadados"]["versao_api"] == "v1"


def test_serializacao_preserva_o_valor_cru_da_probabilidade() -> None:
    """O contrato exige probabilidade sem arredondamento na origem."""
    resposta = resposta_de_sucesso(DadosDeExemplo(nome="p", valor=0.9962406015037594))
    assert resposta.como_dicionario()["dados"]["valor"] == 0.9962406015037594


# --------------------------------------------------------------------------- #
# Construtores
# --------------------------------------------------------------------------- #


def test_resposta_de_sucesso_rejeita_status_de_falha() -> None:
    with pytest.raises(ValueError, match="exige status de sucesso"):
        resposta_de_sucesso(DadosDeExemplo(nome="x", valor=1.0), status=StatusDaResposta.ERRO)


def test_resposta_de_erro_rejeita_status_de_sucesso() -> None:
    with pytest.raises(ValueError, match="exige status de falha"):
        resposta_de_erro([_erro()], status=StatusDaResposta.CONCLUIDO)


def test_resposta_de_erro_rejeita_lista_vazia() -> None:
    with pytest.raises(ValueError, match="exige ao menos um erro"):
        resposta_de_erro([])


def test_resposta_de_erro_aceita_um_unico_erro() -> None:
    resposta = resposta_de_erro(_erro())
    assert resposta.status is StatusDaResposta.ERRO
    assert len(resposta.erros) == 1


def test_construtores_aceitam_id_execucao_explicito() -> None:
    """Permite correlacionar com o ``id_execucao`` gerado pela Fase 6."""
    identificador = "3f2b9c1e-8a4d-4c77-9e10-5b6a7c8d9e0f"
    resposta = resposta_de_sucesso(
        DadosDeExemplo(nome="x", valor=1.0), id_execucao=identificador
    )
    assert resposta.id_execucao == identificador


def test_utilitarios_de_tempo_e_id() -> None:
    assert uuid.UUID(novo_id_execucao()).version == 4
    assert agora_utc().tzinfo is not None
    assert isinstance(agora_utc(), datetime)
