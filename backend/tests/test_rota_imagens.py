"""Testes da rota de diagnostico por imagem (``app/rotas/imagens.py``).

Usam o **servico de visao falso** (``tests/conftest.py``): o servico real da Fase 4 exige
TensorFlow, que nao esta instalado — a ausencia dele e a razao da Decisao 1-C (servico
isolado). O falso reproduz o contrato do ``app.py`` (campo ``image``, chaves
``class``/``confidence``, regra ``probability > 0.5``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator

import pytest
from sqlalchemy import select

from app.dados.enums import ClasseDeDiagnosticoDeImagem, PapelDoUsuario
from app.dados.modelos import AnaliseDeImagem, EventoDeAuditoria
from app.integracao.fase_4 import (
    AVISO_DE_USO_DA_VISAO,
    DIMENSOES_ESPERADAS_DA_IMAGEM,
    LIMIAR_DE_DECISAO_DA_VISAO,
    NOME_DO_MODELO_DA_VISAO,
)
from app.contratos.visao import LIMITACOES_DA_VISAO
from tests.conftest import (
    AmbienteClinico,
    ServicoDeVisaoFalso,
    _app_de_teste,
    _configuracao_base,
    analisar_imagem,
    cabecalho,
    criar_paciente,
    imagem_de_teste,
    token_com_papel,
)

ROTA = "/api/v1/imagens"
ACAO_ANALISE = "analisar_imagem"


# --------------------------------------------------------------------------- #
# Ambientes dedicados (limite, timeout, servico fora do ar)
# --------------------------------------------------------------------------- #


@pytest.fixture
def ambiente_de_visao_com_limite_pequeno(
    tmp_path_factory: pytest.TempPathFactory,
    servico_de_visao_falso: ServicoDeVisaoFalso,
) -> Iterator[AmbienteClinico]:
    """App com teto de upload de 1 MB (evita trafegar 10 MB so para testar o 413)."""
    pasta = tmp_path_factory.mktemp("fase7_visao_limite")
    config = _configuracao_base(
        str(pasta),
        servico_visao_url=servico_de_visao_falso.url,
        limite_de_upload_mb=1,
    )
    with _app_de_teste(config) as ambiente:
        yield ambiente


@pytest.fixture
def ambiente_de_visao_lento(
    tmp_path_factory: pytest.TempPathFactory,
    servico_de_visao_falso: ServicoDeVisaoFalso,
) -> Iterator[AmbienteClinico]:
    """App com prazo curto (0,4 s) para exercitar o timeout sem esperar 30 s."""
    pasta = tmp_path_factory.mktemp("fase7_visao_lento")
    config = _configuracao_base(
        str(pasta),
        servico_visao_url=servico_de_visao_falso.url,
        servico_visao_timeout_segundos=0.4,
    )
    with _app_de_teste(config) as ambiente:
        yield ambiente


@pytest.fixture
def ambiente_de_visao_fora_do_ar(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[AmbienteClinico]:
    """App apontando para um host que **nao resolve**: servico inalcancavel.

    Por que um host ``.invalid`` (RFC 2606) e nao uma porta fechada: neste ambiente
    (Windows) conectar a ``127.0.0.1:<porta livre>`` **nao e recusado** — o firewall
    descarta o pacote e a tentativa so termina no *timeout* de conexao. Isso faria o teste
    medir o comportamento do sistema operacional em vez do mapeamento de erro do adapter.
    Um host que nao resolve falha em ~0,4 s, de forma deterministica.
    """
    pasta = tmp_path_factory.mktemp("fase7_visao_morta")
    config = _configuracao_base(
        str(pasta),
        servico_visao_url="http://servico-de-visao-inexistente.invalid:5001",
        servico_visao_timeout_segundos=5.0,
    )
    with _app_de_teste(config) as ambiente:
        yield ambiente


# --------------------------------------------------------------------------- #
# Apoio
# --------------------------------------------------------------------------- #


def _analises_no_banco(ambiente: AmbienteClinico) -> list[AnaliseDeImagem]:
    with ambiente.fabrica_de_sessoes() as sessao:
        return list(sessao.scalars(select(AnaliseDeImagem)))


def _auditorias(ambiente: AmbienteClinico) -> list[EventoDeAuditoria]:
    with ambiente.fabrica_de_sessoes() as sessao:
        return list(
            sessao.scalars(
                select(EventoDeAuditoria).where(EventoDeAuditoria.acao == ACAO_ANALISE)
            )
        )


# --------------------------------------------------------------------------- #
# Caminho feliz
# --------------------------------------------------------------------------- #


def test_analise_de_pneumonia(
    ambiente_de_visao: AmbienteClinico, servico_de_visao_falso: ServicoDeVisaoFalso
) -> None:
    servico_de_visao_falso.responder(probabilidade=0.93)
    resultado = analisar_imagem(ambiente_de_visao)

    assert resultado["status_code"] == 201
    corpo = resultado["corpo"]
    assert corpo["status"] == "CONCLUIDO"
    assert corpo["erros"] == []

    dados = corpo["dados"]
    assert set(dados) == {
        "classe",
        "confianca",
        "modelo_utilizado",
        "limiar_decisao",
        "dimensoes_da_imagem",
        "hash_sha256",
        "aviso_de_uso",
    }
    assert dados["classe"] == "Pneumonia"
    assert dados["confianca"] == 93.0
    assert dados["modelo_utilizado"] == NOME_DO_MODELO_DA_VISAO
    assert dados["limiar_decisao"] == LIMIAR_DE_DECISAO_DA_VISAO
    assert dados["dimensoes_da_imagem"] == list(DIMENSOES_ESPERADAS_DA_IMAGEM)
    assert dados["aviso_de_uso"] == AVISO_DE_USO_DA_VISAO


def test_analise_de_classe_normal(
    ambiente_de_visao: AmbienteClinico, servico_de_visao_falso: ServicoDeVisaoFalso
) -> None:
    servico_de_visao_falso.responder(probabilidade=0.1)
    resultado = analisar_imagem(ambiente_de_visao)

    assert resultado["corpo"]["dados"]["classe"] == "Normal"
    assert resultado["corpo"]["dados"]["confianca"] == 90.0


def test_hash_corresponde_ao_arquivo_enviado(ambiente_de_visao: AmbienteClinico) -> None:
    conteudo = imagem_de_teste(tamanho=1024)
    resultado = analisar_imagem(ambiente_de_visao, conteudo=conteudo)

    assert resultado["corpo"]["dados"]["hash_sha256"] == hashlib.sha256(conteudo).hexdigest()


def test_imagem_nao_e_persistida(
    ambiente_de_visao: AmbienteClinico, servico_de_visao_falso: ServicoDeVisaoFalso
) -> None:
    """🔒 Privacidade (MODELO_DADOS.md §3.9): guardam-se apenas hash e metadados."""
    servico_de_visao_falso.responder(probabilidade=0.93)
    conteudo = imagem_de_teste(tamanho=1024)
    resultado = analisar_imagem(
        ambiente_de_visao, conteudo=conteudo, nome="rx-torax.png", mime="image/png"
    )

    analise = _analises_no_banco(ambiente_de_visao)[0]
    assert analise.hash_sha256 == resultado["corpo"]["dados"]["hash_sha256"]
    assert analise.nome_arquivo == "rx-torax.png"
    assert analise.mime == "image/png"
    assert analise.tamanho_bytes == 1024
    assert analise.classe is ClasseDeDiagnosticoDeImagem.PNEUMONIA
    assert analise.confianca == 93.0
    assert analise.modelo_utilizado == NOME_DO_MODELO_DA_VISAO
    assert analise.limiar_decisao == LIMIAR_DE_DECISAO_DA_VISAO

    # A tabela nao tem coluna de binario, e o contrato salvo nao carrega a imagem.
    colunas = {coluna.name for coluna in AnaliseDeImagem.__table__.columns}
    assert not {nome for nome in colunas if "imagem" in nome or "binario" in nome}
    assert analise.resposta_json is not None
    assert "imagem" not in analise.resposta_json


def test_envelope_aponta_para_a_analise_persistida(ambiente_de_visao: AmbienteClinico) -> None:
    resultado = analisar_imagem(ambiente_de_visao)
    analise = _analises_no_banco(ambiente_de_visao)[0]

    assert resultado["corpo"]["id_execucao"] == analise.id
    assert analise.id_usuario == ambiente_de_visao.id_usuario


def test_avisos_e_limitacoes_nunca_vazios(ambiente_de_visao: AmbienteClinico) -> None:
    """Contrato §8.1: resposta de decisao automatizada sempre traz avisos e limitacoes."""
    corpo = analisar_imagem(ambiente_de_visao)["corpo"]

    assert AVISO_DE_USO_DA_VISAO in corpo["avisos"]
    assert corpo["limitacoes"] == list(LIMITACOES_DA_VISAO)
    assert any("NAO e persistida" in item or "NAO e persistida" in item for item in corpo["limitacoes"])


def test_analise_registra_auditoria_sem_dado_clinico(ambiente_de_visao: AmbienteClinico) -> None:
    """🔒 O diagnostico e dado clinico: a trilha registra a acao, nao o resultado."""
    resultado = analisar_imagem(ambiente_de_visao)
    id_analise = resultado["corpo"]["id_execucao"]

    eventos = _auditorias(ambiente_de_visao)
    assert len(eventos) == 1
    assert eventos[0].id_entidade == id_analise
    assert eventos[0].id_usuario == ambiente_de_visao.id_usuario
    assert eventos[0].detalhe_json == {"mime": "image/jpeg", "tamanho_bytes": 512}
    assert "classe" not in (eventos[0].detalhe_json or {})
    assert "confianca" not in (eventos[0].detalhe_json or {})


# --------------------------------------------------------------------------- #
# Vinculacao opcional a paciente
# --------------------------------------------------------------------------- #


def test_analise_vinculada_a_paciente(ambiente_de_visao: AmbienteClinico) -> None:
    id_paciente = criar_paciente(ambiente_de_visao, nome="Maria Souza")
    analisar_imagem(ambiente_de_visao, id_paciente=id_paciente)

    assert _analises_no_banco(ambiente_de_visao)[0].id_paciente == id_paciente


def test_analise_sem_paciente_e_permitida(ambiente_de_visao: AmbienteClinico) -> None:
    """`id_paciente` e opcional (CONTRATOS_API.md §4.6)."""
    resultado = analisar_imagem(ambiente_de_visao)
    assert resultado["status_code"] == 201
    assert _analises_no_banco(ambiente_de_visao)[0].id_paciente is None


def test_analise_de_paciente_inexistente_devolve_404(ambiente_de_visao: AmbienteClinico) -> None:
    resultado = analisar_imagem(ambiente_de_visao, id_paciente="paciente-que-nao-existe")

    assert resultado["status_code"] == 404
    assert resultado["corpo"]["erros"][0]["codigo"] == "NAO_ENCONTRADO"
    assert _analises_no_banco(ambiente_de_visao) == []


def test_analise_de_paciente_inativo_devolve_409(ambiente_de_visao: AmbienteClinico) -> None:
    from app.dados.modelos import Paciente

    id_paciente = criar_paciente(ambiente_de_visao)
    with ambiente_de_visao.fabrica_de_sessoes() as sessao:
        paciente = sessao.get(Paciente, id_paciente)
        assert paciente is not None
        paciente.ativo = False
        sessao.commit()

    resultado = analisar_imagem(ambiente_de_visao, id_paciente=id_paciente)
    assert resultado["status_code"] == 409
    assert resultado["corpo"]["erros"][0]["codigo"] == "CONFLITO"
    assert _analises_no_banco(ambiente_de_visao) == []


# --------------------------------------------------------------------------- #
# Endurecimento da borda (CONTRATOS_API.md §4.6)
# --------------------------------------------------------------------------- #


def test_tipo_de_arquivo_nao_suportado_devolve_422(ambiente_de_visao: AmbienteClinico) -> None:
    """A Fase 4 aceita 'qualquer arquivo que o Keras abra'; aqui o tipo e validado."""
    resultado = analisar_imagem(ambiente_de_visao, mime="application/pdf", nome="laudo.pdf")

    assert resultado["status_code"] == 422
    assert resultado["corpo"]["erros"][0]["codigo"] == "CONTRATO_VIOLADO"
    assert resultado["corpo"]["erros"][0]["campo"] == "imagem"
    assert _analises_no_banco(ambiente_de_visao) == []


def test_png_e_aceito(ambiente_de_visao: AmbienteClinico) -> None:
    resultado = analisar_imagem(ambiente_de_visao, mime="image/png", nome="rx.png")
    assert resultado["status_code"] == 201


def test_arquivo_vazio_devolve_422(ambiente_de_visao: AmbienteClinico) -> None:
    resultado = analisar_imagem(ambiente_de_visao, conteudo=b"")

    assert resultado["status_code"] == 422
    assert resultado["corpo"]["erros"][0]["codigo"] == "CONTRATO_VIOLADO"


def test_arquivo_acima_do_limite_devolve_413(
    ambiente_de_visao_com_limite_pequeno: AmbienteClinico,
) -> None:
    """O teto existe porque a Fase 4 nao limita nada (CONTRATOS_API.md §4.6)."""
    grande = imagem_de_teste(tamanho=1024 * 1024 + 1024)
    resultado = analisar_imagem(ambiente_de_visao_com_limite_pequeno, conteudo=grande)

    assert resultado["status_code"] == 413
    assert resultado["corpo"]["erros"][0]["codigo"] == "LIMITE_EXCEDIDO"
    assert resultado["corpo"]["erros"][0]["campo"] == "imagem"


def test_arquivo_dentro_do_limite_e_aceito(
    ambiente_de_visao_com_limite_pequeno: AmbienteClinico,
) -> None:
    resultado = analisar_imagem(
        ambiente_de_visao_com_limite_pequeno, conteudo=imagem_de_teste(tamanho=2048)
    )
    assert resultado["status_code"] == 201


def test_sem_o_campo_imagem_devolve_422(ambiente_de_visao: AmbienteClinico) -> None:
    resposta = ambiente_de_visao.cliente.post(
        ROTA, headers=cabecalho(ambiente_de_visao.token)
    )
    assert resposta.status_code == 422
    assert resposta.json()["erros"][0]["codigo"] == "CONTRATO_VIOLADO"


# --------------------------------------------------------------------------- #
# Falha do servico externo
# --------------------------------------------------------------------------- #


def test_servico_fora_do_ar_devolve_502(ambiente_de_visao_fora_do_ar: AmbienteClinico) -> None:
    resultado = analisar_imagem(ambiente_de_visao_fora_do_ar)

    assert resultado["status_code"] == 502
    assert resultado["corpo"]["erros"][0]["codigo"] == "ERRO_DE_SERVICO_DE_VISAO"
    assert _analises_no_banco(ambiente_de_visao_fora_do_ar) == []


def test_servico_lento_devolve_504(
    ambiente_de_visao_lento: AmbienteClinico, servico_de_visao_falso: ServicoDeVisaoFalso
) -> None:
    servico_de_visao_falso.demorar(2.0)
    resultado = analisar_imagem(ambiente_de_visao_lento)

    assert resultado["status_code"] == 504
    assert resultado["corpo"]["erros"][0]["codigo"] == "TIMEOUT_EXTERNO"


def test_erro_do_servico_devolve_502(
    ambiente_de_visao: AmbienteClinico, servico_de_visao_falso: ServicoDeVisaoFalso
) -> None:
    servico_de_visao_falso.falhar_com(500, {"error": "Falha ao processar imagem"})
    resultado = analisar_imagem(ambiente_de_visao)

    assert resultado["status_code"] == 502
    assert resultado["corpo"]["erros"][0]["codigo"] == "ERRO_DE_SERVICO_DE_VISAO"


def test_resposta_fora_do_contrato_devolve_502(
    ambiente_de_visao: AmbienteClinico, servico_de_visao_falso: ServicoDeVisaoFalso
) -> None:
    """Um servico que responde algo inesperado nao vira diagnostico silencioso."""
    servico_de_visao_falso.falhar_com(200, {"class": "Covid", "confidence": 99.0})
    resultado = analisar_imagem(ambiente_de_visao)

    assert resultado["status_code"] == 502
    assert resultado["corpo"]["erros"][0]["campo"] == "class"
    assert _analises_no_banco(ambiente_de_visao) == []


# --------------------------------------------------------------------------- #
# RBAC
# --------------------------------------------------------------------------- #


def test_analise_exige_autenticacao(ambiente_de_visao: AmbienteClinico) -> None:
    resposta = ambiente_de_visao.cliente.post(
        ROTA, files={"imagem": ("rx.jpg", imagem_de_teste(), "image/jpeg")}
    )
    assert resposta.status_code == 401


def test_analise_exige_papel_medico(ambiente_de_visao: AmbienteClinico) -> None:
    """Interpretar imagem e ato clinico: nem ADMIN nem OPERADOR podem."""
    for papel in (PapelDoUsuario.ADMIN, PapelDoUsuario.OPERADOR):
        token = token_com_papel(ambiente_de_visao, papel)
        resultado = analisar_imagem(ambiente_de_visao, token=token)
        assert resultado["status_code"] == 403, papel
        assert resultado["corpo"]["erros"][0]["codigo"] == "NAO_AUTORIZADO"


def test_analise_permitida_para_medico(ambiente_de_visao: AmbienteClinico) -> None:
    assert analisar_imagem(ambiente_de_visao)["status_code"] == 201