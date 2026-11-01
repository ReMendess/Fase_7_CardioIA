"""Testes dos repositorios (``app/dados/repositorios/``).

Cobrem: contrato de features, transacao unica do agregado, traducao de violacao de
integridade para ``CONFLITO``, campo desconhecido para ``CONTRATO_VIOLADO`` e as
operacoes de leitura de cada agregado.
"""

from __future__ import annotations

import math
from datetime import timedelta

import pytest

from app.contratos.erros import CodigoDeErro, ErroDaAPIException
from app.dados.base import agora_utc
from app.dados.enums import PapelDoUsuario
from app.dados.modelos import COLUNAS_DE_FEATURE, PassoDaExecucao, ProtocoloAplicado
from app.dados.repositorios.assistencial import normalizar_features
from app.dados.repositorios.base import validar_chaves
from app.dados.repositorios.identidade import UsuarioRepositorio


# --------------------------------------------------------------------------- #
# normalizar_features — espelha o contrato fechado da Fase 6
# --------------------------------------------------------------------------- #


def test_normalizar_features_aceita_exatamente_as_dez(features_validas) -> None:
    valores = normalizar_features(features_validas)
    assert set(valores) == set(COLUNAS_DE_FEATURE)
    assert all(isinstance(valor, float) for valor in valores.values())
    assert valores["carga_sistema"] == 92.0


def test_normalizar_features_rejeita_campo_ausente(features_validas) -> None:
    features_validas.pop("spo2_media")
    with pytest.raises(ErroDaAPIException) as capturado:
        normalizar_features(features_validas)
    assert capturado.value.codigo is CodigoDeErro.PACIENTE_INVALIDO
    assert "spo2_media" in capturado.value.mensagem


def test_normalizar_features_rejeita_campo_desconhecido(features_validas) -> None:
    """Nao ha mapeamento implicito: ``bpm`` nao e feature do modelo."""
    features_validas["bpm"] = 118.0
    with pytest.raises(ErroDaAPIException) as capturado:
        normalizar_features(features_validas)
    assert capturado.value.codigo is CodigoDeErro.PACIENTE_INVALIDO
    assert "bpm" in capturado.value.mensagem


@pytest.mark.parametrize("valor_invalido", [True, "92", None, math.nan, math.inf, -1.0])
def test_normalizar_features_rejeita_valor_invalido(features_validas, valor_invalido) -> None:
    features_validas["carga_sistema"] = valor_invalido
    with pytest.raises(ErroDaAPIException) as capturado:
        normalizar_features(features_validas)
    assert capturado.value.codigo is CodigoDeErro.PACIENTE_INVALIDO
    assert capturado.value.erro.campo == "carga_sistema"


def test_normalizar_features_nao_preenche_default() -> None:
    """Decisao D4: nenhum valor e inventado para completar o conjunto."""
    with pytest.raises(ErroDaAPIException):
        normalizar_features({"carga_sistema": 92.0})


# --------------------------------------------------------------------------- #
# validar_chaves
# --------------------------------------------------------------------------- #


def test_validar_chaves_aceita_coluna_existente() -> None:
    dados = validar_chaves(
        ProtocoloAplicado, {"ordem": 1, "identificador": "x"}, "protocolos"
    )
    assert dados == {"ordem": 1, "identificador": "x"}


def test_validar_chaves_rejeita_coluna_inexistente() -> None:
    with pytest.raises(ErroDaAPIException) as capturado:
        validar_chaves(PassoDaExecucao, {"ordem": 1, "inexistente": "x"}, "passos[0]")
    assert capturado.value.codigo is CodigoDeErro.CONTRATO_VIOLADO
    assert "inexistente" in capturado.value.mensagem


# --------------------------------------------------------------------------- #
# UsuarioRepositorio
# --------------------------------------------------------------------------- #


def test_usuario_criado_normaliza_o_email(usuario_repositorio: UsuarioRepositorio) -> None:
    usuario = usuario_repositorio.criar(
        nome="  Dra. Teste  ",
        email="  MEDICO@Teste.LOCAL  ",
        senha_hash="h",
        papel=PapelDoUsuario.MEDICO,
    )
    assert usuario.email == "medico@teste.local"
    assert usuario.nome == "Dra. Teste"
    assert usuario.ativo is True
    assert usuario.criado_em.tzinfo is not None


def test_busca_de_usuario_por_email_e_case_insensitive(
    usuario_repositorio: UsuarioRepositorio, usuario_criado
) -> None:
    assert usuario_repositorio.buscar_por_email("MEDICO@TESTE.LOCAL") is not None
    assert usuario_repositorio.buscar_por_email("nao-existe@teste.local") is None


def test_email_duplicado_levanta_conflito(usuario_repositorio: UsuarioRepositorio) -> None:
    usuario_repositorio.criar(
        nome="A", email="a@teste.local", senha_hash="h", papel=PapelDoUsuario.ADMIN
    )
    with pytest.raises(ErroDaAPIException) as capturado:
        usuario_repositorio.criar(
            nome="B", email="a@teste.local", senha_hash="h", papel=PapelDoUsuario.ADMIN
        )
    assert capturado.value.codigo is CodigoDeErro.CONFLITO
    assert capturado.value.http == 409


def test_usuario_pode_ser_desativado_e_reativado(
    usuario_repositorio: UsuarioRepositorio, usuario_criado
) -> None:
    usuario_repositorio.definir_ativo(usuario_criado, False)
    assert usuario_repositorio.buscar_por_id(usuario_criado.id).ativo is False
    assert usuario_repositorio.listar(apenas_ativos=True) == []
    usuario_repositorio.definir_ativo(usuario_criado, True)
    assert len(usuario_repositorio.listar(apenas_ativos=True)) == 1


def test_registrar_acesso_preenche_o_ultimo_acesso(
    usuario_repositorio: UsuarioRepositorio, usuario_criado
) -> None:
    assert usuario_criado.ultimo_acesso is None
    usuario_repositorio.registrar_acesso(usuario_criado)
    assert usuario_criado.ultimo_acesso is not None
    assert usuario_criado.ultimo_acesso.tzinfo is not None


# --------------------------------------------------------------------------- #
# SessaoRepositorio
# --------------------------------------------------------------------------- #


def test_sessao_e_criada_e_encontrada_pelo_hash(sessao, usuario_criado) -> None:
    from app.dados.repositorios.identidade import SessaoRepositorio

    repositorio = SessaoRepositorio(sessao)
    criada = repositorio.criar(
        id_usuario=usuario_criado.id,
        token_hash="a" * 64,
        expira_em=agora_utc() + timedelta(days=7),
    )
    assert criada.vigente is True
    assert repositorio.buscar_por_hash("a" * 64).id == criada.id
    assert repositorio.buscar_por_hash("b" * 64) is None


def test_sessao_expirada_nao_e_vigente(sessao, usuario_criado) -> None:
    from app.dados.repositorios.identidade import SessaoRepositorio

    repositorio = SessaoRepositorio(sessao)
    antiga = repositorio.criar(
        id_usuario=usuario_criado.id,
        token_hash="c" * 64,
        expira_em=agora_utc() - timedelta(minutes=1),
    )
    assert antiga.vigente is False


def test_revogar_sessao_a_torna_invativa(sessao, usuario_criado) -> None:
    from app.dados.repositorios.identidade import SessaoRepositorio

    repositorio = SessaoRepositorio(sessao)
    criada = repositorio.criar(
        id_usuario=usuario_criado.id,
        token_hash="d" * 64,
        expira_em=agora_utc() + timedelta(days=7),
    )
    repositorio.revogar(criada)
    assert criada.revogado_em is not None
    assert criada.vigente is False


def test_revogar_todas_as_sessoes_do_usuario(sessao, usuario_criado) -> None:
    from app.dados.repositorios.identidade import SessaoRepositorio

    repositorio = SessaoRepositorio(sessao)
    for indice in range(3):
        repositorio.criar(
            id_usuario=usuario_criado.id,
            token_hash=str(indice) * 64,
            expira_em=agora_utc() + timedelta(days=7),
        )
    assert repositorio.revogar_todas_do_usuario(usuario_criado.id) == 3
    assert repositorio.revogar_todas_do_usuario(usuario_criado.id) == 0


def test_remover_sessoes_expiradas_e_revogadas(sessao, usuario_criado) -> None:
    from app.dados.repositorios.identidade import SessaoRepositorio

    repositorio = SessaoRepositorio(sessao)
    repositorio.criar(
        id_usuario=usuario_criado.id,
        token_hash="e" * 64,
        expira_em=agora_utc() - timedelta(days=1),  # expirada
    )
    vigente = repositorio.criar(
        id_usuario=usuario_criado.id,
        token_hash="f" * 64,
        expira_em=agora_utc() + timedelta(days=7),
    )
    assert repositorio.remover_expiradas() == 1
    assert repositorio.buscar_por_hash(vigente.token_hash) is not None


# --------------------------------------------------------------------------- #
# PacienteRepositorio
# --------------------------------------------------------------------------- #


def test_paciente_e_criado_com_identidade_apenas(
    paciente_repositorio, usuario_criado
) -> None:
    paciente = paciente_repositorio.criar(
        nome="  Paciente Teste  ", criado_por=usuario_criado.id
    )
    assert paciente.nome == "Paciente Teste"
    assert paciente.ativo is True
    assert paciente.criado_em.tzinfo is not None
    # As 10 features NAO ficam no cadastro (resposta Q1).
    assert not hasattr(paciente, "carga_sistema")


def test_paciente_aceita_soft_delete(paciente_repositorio, paciente_criado) -> None:
    paciente_repositorio.definir_ativo(paciente_criado, False)
    assert paciente_repositorio.listar(apenas_ativos=True) == []
    assert paciente_repositorio.buscar_por_id(paciente_criado.id) is not None


def test_paciente_com_usuario_inexistente_viola_integridade(
    paciente_repositorio,
) -> None:
    with pytest.raises(ErroDaAPIException) as capturado:
        paciente_repositorio.criar(nome="X", criado_por="usuario-inexistente")
    assert capturado.value.codigo is CodigoDeErro.CONFLITO


# --------------------------------------------------------------------------- #
# AvaliacaoRepositorio — o agregado central
# --------------------------------------------------------------------------- #


def _criar(
    repositorio,
    *,
    id_execucao: str = "3f2b9c1e-8a4d-4c77-9e10-5b6a7c8d9e0f",
    features: dict | None = None,
    dados: dict | None = None,
    status: str | None = None,
    id_paciente: str = "p",
    id_usuario: str = "u",
):
    """Atalho de criacao com os valores padrao do contrato."""
    from app.contratos.envelope import StatusDaResposta
    from app.dados.enums import ModoDoPipeline, OrigemDosDados

    return repositorio.criar(
        id_execucao=id_execucao,
        id_paciente=id_paciente,
        id_usuario=id_usuario,
        features=features if features is not None else {},
        origem_dos_dados=OrigemDosDados.MANUAL,
        status=StatusDaResposta(status) if status else StatusDaResposta.CONCLUIDO,
        modo=ModoDoPipeline.SIMULADO,
        **(dados or {}),
    )


def test_avaliacao_grava_o_agregado_completo(
    avaliacao_repositorio,
    paciente_criado,
    usuario_criado,
    features_validas,
    dados_do_pipeline,
) -> None:
    """Avaliacao + protocolos + indicadores + passos entram em uma transacao."""
    avaliacao = _criar(
        avaliacao_repositorio,
        features=features_validas,
        dados=dados_do_pipeline,
        id_paciente=paciente_criado.id,
        id_usuario=usuario_criado.id,
    )

    assert avaliacao.status.value == "CONCLUIDO"
    assert avaliacao.features == features_validas
    assert len(avaliacao.protocolos) == 1
    assert len(avaliacao.indicadores) == 1
    assert len(avaliacao.passos) == 1
    assert avaliacao.criado_em.tzinfo is not None


def test_avaliacao_guarda_o_resultado_do_diagnostico(
    avaliacao_repositorio,
    paciente_criado,
    usuario_criado,
    features_validas,
    dados_do_pipeline,
) -> None:
    avaliacao = _criar(
        avaliacao_repositorio,
        features=features_validas,
        dados=dados_do_pipeline,
        id_paciente=paciente_criado.id,
        id_usuario=usuario_criado.id,
    )
    assert avaliacao.probabilidade_risco == 0.9900
    assert avaliacao.pico_risco_previsto == 1
    assert avaliacao.classificacao_risco.value == "pico_de_risco"
    assert avaliacao.modelo_utilizado == "Random Forest"
    assert avaliacao.limiar_decisao == 0.5
    assert avaliacao.sha256_da_base_usada == "a" * 64
    assert avaliacao.agente_final == "Planejador de Resposta"
    assert avaliacao.versao_do_sdk == "0.18.1"


def test_avaliacao_preserva_o_contrato_integral_para_auditoria(
    avaliacao_repositorio, paciente_criado, usuario_criado, features_validas
) -> None:
    """``resposta_json`` e ``features_json`` guardam o que foi avaliado."""
    contrato = {"id_execucao": "x", "status": "CONCLUIDO", "dados": {"protocolos": []}}
    avaliacao = _criar(
        avaliacao_repositorio,
        features=features_validas,
        dados={"resposta": contrato},
        id_paciente=paciente_criado.id,
        id_usuario=usuario_criado.id,
    )
    assert avaliacao.resposta_json == contrato
    assert avaliacao.features_json["carga_sistema"] == 92.0
    assert avaliacao.features_json["origem_dos_dados"] == "manual"


def test_avaliacao_rejeita_features_fora_do_contrato(
    avaliacao_repositorio, paciente_criado, usuario_criado, features_validas
) -> None:
    features_validas.pop("temperatura")
    with pytest.raises(ErroDaAPIException) as capturado:
        _criar(
            avaliacao_repositorio,
            features=features_validas,
            id_paciente=paciente_criado.id,
            id_usuario=usuario_criado.id,
        )
    assert capturado.value.codigo is CodigoDeErro.PACIENTE_INVALIDO


def test_avaliacao_rejeita_campo_desconhecido_nas_filhas(
    avaliacao_repositorio, paciente_criado, usuario_criado, features_validas
) -> None:
    """Postura ``extra='forbid'`` tambem nas tabelas-filhas."""
    with pytest.raises(ErroDaAPIException) as capturado:
        _criar(
            avaliacao_repositorio,
            features=features_validas,
            dados={"protocolos": [{"ordem": 1, "campo_inventado": "x"}]},
            id_paciente=paciente_criado.id,
            id_usuario=usuario_criado.id,
        )
    assert capturado.value.codigo is CodigoDeErro.CONTRATO_VIOLADO


def test_avaliacao_com_id_execucao_repetido_levanta_conflito(
    avaliacao_repositorio, paciente_criado, usuario_criado, features_validas
) -> None:
    _criar(
        avaliacao_repositorio,
        features=features_validas,
        id_paciente=paciente_criado.id,
        id_usuario=usuario_criado.id,
    )
    with pytest.raises(ErroDaAPIException) as capturado:
        _criar(
            avaliacao_repositorio,
            features=features_validas,
            id_paciente=paciente_criado.id,
            id_usuario=usuario_criado.id,
        )
    assert capturado.value.codigo is CodigoDeErro.CONFLITO


def test_falha_na_transacao_nao_deixa_registro_parcial(
    avaliacao_repositorio, paciente_criado, usuario_criado, features_validas, sessao
) -> None:
    """Transacao unica: erro nas filhas nao grava a avaliacao."""
    from sqlalchemy import func, select

    from app.dados.modelos import AvaliacaoDeRisco

    with pytest.raises(ErroDaAPIException) as capturado:
        _criar(
            avaliacao_repositorio,
            features=features_validas,
            dados={"passos": [{"ordem": 1, "tipo": "tipo_invalido"}]},
            id_paciente=paciente_criado.id,
            id_usuario=usuario_criado.id,
        )
    assert capturado.value.codigo is CodigoDeErro.CONTRATO_VIOLADO

    total = sessao.scalar(select(func.count()).select_from(AvaliacaoDeRisco))
    assert total == 0


def test_avaliacao_pode_ser_encontrada_pela_chave_de_correlacao(
    avaliacao_repositorio, paciente_criado, usuario_criado, features_validas
) -> None:
    criada = _criar(
        avaliacao_repositorio,
        features=features_validas,
        id_paciente=paciente_criado.id,
        id_usuario=usuario_criado.id,
    )
    encontrada = avaliacao_repositorio.buscar_por_id_execucao(criada.id_execucao)
    assert encontrada is not None
    assert encontrada.id == criada.id
    assert avaliacao_repositorio.buscar_por_id_execucao("inexistente") is None
    assert avaliacao_repositorio.buscar_por_id(criada.id) is not None


def test_historico_do_paciente_vem_do_mais_recente_para_o_mais_antigo(
    avaliacao_repositorio, paciente_criado, usuario_criado, features_validas
) -> None:
    base = agora_utc() - timedelta(days=2)
    for indice in range(3):
        _criar(
            avaliacao_repositorio,
            id_execucao=f"execucao-{indice}",
            features=features_validas,
            dados={"criado_em": base + timedelta(days=indice)},
            id_paciente=paciente_criado.id,
            id_usuario=usuario_criado.id,
        )

    historico = avaliacao_repositorio.listar_por_paciente(paciente_criado.id)
    assert [item.id_execucao for item in historico] == [
        "execucao-2",
        "execucao-1",
        "execucao-0",
    ]


def test_listar_avaliacoes_permite_filtrar_por_status(
    avaliacao_repositorio, paciente_criado, usuario_criado, features_validas
) -> None:
    from app.contratos.envelope import StatusDaResposta

    _criar(
        avaliacao_repositorio,
        id_execucao="ok",
        features=features_validas,
        id_paciente=paciente_criado.id,
        id_usuario=usuario_criado.id,
    )
    _criar(
        avaliacao_repositorio,
        id_execucao="falhou",
        features=features_validas,
        status="ERRO",
        dados={"erros": ["falha simulada"]},
        id_paciente=paciente_criado.id,
        id_usuario=usuario_criado.id,
    )

    assert len(avaliacao_repositorio.listar()) == 2
    concluidas = avaliacao_repositorio.listar(status=StatusDaResposta.CONCLUIDO)
    assert [item.id_execucao for item in concluidas] == ["ok"]


# --------------------------------------------------------------------------- #
# MonitoramentoRepositorio (telemetria IoT)
# --------------------------------------------------------------------------- #


def test_registrar_telemetria_com_bpm(sessao) -> None:
    from app.dados.enums import OrigemDoTransporte
    from app.dados.repositorios.telemetria import MonitoramentoRepositorio

    leitura = MonitoramentoRepositorio(sessao).registrar(
        id_dispositivo="esp32-sala-1", origem_transporte=OrigemDoTransporte.MQTT, bpm=118
    )
    assert leitura.id_dispositivo == "esp32-sala-1"
    assert leitura.bpm == 118
    assert leitura.temperatura is None
    assert leitura.recebido_em.tzinfo is not None


def test_telemetria_exige_ao_menos_um_sinal(sessao) -> None:
    from app.dados.enums import OrigemDoTransporte
    from app.dados.repositorios.telemetria import MonitoramentoRepositorio

    with pytest.raises(ErroDaAPIException) as capturado:
        MonitoramentoRepositorio(sessao).registrar(
            id_dispositivo="esp32-sala-1", origem_transporte=OrigemDoTransporte.REST
        )
    assert capturado.value.codigo is CodigoDeErro.CONTRATO_VIOLADO


def test_telemetria_duplicada_levanta_conflito(sessao) -> None:
    """Mesmo dispositivo + mesmo instante = deduplicacao (CONFLITO)."""
    from app.dados.enums import OrigemDoTransporte
    from app.dados.repositorios.telemetria import MonitoramentoRepositorio

    repositorio = MonitoramentoRepositorio(sessao)
    momento = agora_utc()
    repositorio.registrar(
        id_dispositivo="esp32-1",
        origem_transporte=OrigemDoTransporte.MQTT,
        bpm=70,
        recebido_em=momento,
    )
    with pytest.raises(ErroDaAPIException) as capturado:
        repositorio.registrar(
            id_dispositivo="esp32-1",
            origem_transporte=OrigemDoTransporte.MQTT,
            bpm=72,
            recebido_em=momento,
        )
    assert capturado.value.codigo is CodigoDeErro.CONFLITO


def test_ultimas_leituras_e_contagem_de_24h(sessao, paciente_criado) -> None:
    from app.dados.enums import OrigemDoTransporte
    from app.dados.repositorios.telemetria import MonitoramentoRepositorio

    repositorio = MonitoramentoRepositorio(sessao)
    agora = agora_utc()
    repositorio.registrar(
        id_dispositivo="esp32-1",
        origem_transporte=OrigemDoTransporte.MQTT,
        bpm=70,
        recebido_em=agora - timedelta(hours=30),  # fora das 24 h
        id_paciente=paciente_criado.id,
    )
    repositorio.registrar(
        id_dispositivo="esp32-1",
        origem_transporte=OrigemDoTransporte.MQTT,
        bpm=75,
        recebido_em=agora - timedelta(hours=2),
        id_paciente=paciente_criado.id,
    )

    assert len(repositorio.ultimas()) == 2
    assert len(repositorio.ultimas(id_dispositivo="outro")) == 0
    assert len(repositorio.listar_por_paciente(paciente_criado.id)) == 2
    assert repositorio.contar_ultimas_24h() == 1
    assert repositorio.contar_ultimas_24h(id_paciente=paciente_criado.id) == 1
    assert repositorio.contar_desde(agora - timedelta(hours=48)) == 2


# --------------------------------------------------------------------------- #
# AnaliseDeImagemRepositorio
# --------------------------------------------------------------------------- #


def test_registrar_analise_de_imagem_sem_guardar_o_binario(sessao, usuario_criado) -> None:
    from app.dados.enums import ClasseDeDiagnosticoDeImagem
    from app.dados.repositorios.analises import AnaliseDeImagemRepositorio

    repositorio = AnaliseDeImagemRepositorio(sessao)
    analise = repositorio.registrar(
        id_usuario=usuario_criado.id,
        nome_arquivo="torax.png",
        mime="image/png",
        tamanho_bytes=12345,
        hash_sha256="c" * 64,
        classe=ClasseDeDiagnosticoDeImagem.PNEUMONIA,
        confianca=93.5,
        modelo_utilizado="mobilenet_pneumonia.keras",
        limiar_decisao=0.5,
    )
    assert analise.classe is ClasseDeDiagnosticoDeImagem.PNEUMONIA
    assert analise.confianca == 93.5
    assert not hasattr(analise, "conteudo")  # o binario nao existe no modelo
    assert repositorio.buscar_por_id(analise.id) is not None


def test_analise_pode_ser_encontrada_pelo_hash(sessao, usuario_criado) -> None:
    from app.dados.enums import ClasseDeDiagnosticoDeImagem
    from app.dados.repositorios.analises import AnaliseDeImagemRepositorio

    repositorio = AnaliseDeImagemRepositorio(sessao)
    for _ in range(2):
        repositorio.registrar(
            id_usuario=usuario_criado.id,
            nome_arquivo="torax.png",
            mime="image/png",
            tamanho_bytes=100,
            hash_sha256="d" * 64,
            classe=ClasseDeDiagnosticoDeImagem.NORMAL,
            confianca=88.0,
            modelo_utilizado="mobilenet_pneumonia.keras",
            limiar_decisao=0.5,
        )
    assert len(repositorio.buscar_por_hash("d" * 64)) == 2
    assert repositorio.buscar_por_hash("e" * 64) == []


def test_analise_vinculada_ao_paciente_aparece_no_historico(
    sessao, usuario_criado, paciente_criado
) -> None:
    from app.dados.enums import ClasseDeDiagnosticoDeImagem
    from app.dados.repositorios.analises import AnaliseDeImagemRepositorio

    repositorio = AnaliseDeImagemRepositorio(sessao)
    repositorio.registrar(
        id_usuario=usuario_criado.id,
        id_paciente=paciente_criado.id,
        nome_arquivo="torax.png",
        mime="image/png",
        tamanho_bytes=100,
        hash_sha256="f" * 64,
        classe=ClasseDeDiagnosticoDeImagem.NORMAL,
        confianca=88.0,
        modelo_utilizado="mobilenet_pneumonia.keras",
        limiar_decisao=0.5,
    )
    assert len(repositorio.listar_por_paciente(paciente_criado.id)) == 1


# --------------------------------------------------------------------------- #
# ConversaRepositorio
# --------------------------------------------------------------------------- #


def test_conversa_registra_mensagens_e_encerra(
    sessao, usuario_criado, paciente_criado
) -> None:
    from app.dados.enums import CanalDaConversa, PapelDaMensagem
    from app.dados.repositorios.conversas import ConversaRepositorio

    repositorio = ConversaRepositorio(sessao)
    conversa = repositorio.criar(
        id_usuario=usuario_criado.id,
        canal=CanalDaConversa.MOBILE,
        id_paciente=paciente_criado.id,
    )
    repositorio.adicionar_mensagem(
        id_conversa=conversa.id, papel=PapelDaMensagem.USUARIO, conteudo="dor no peito"
    )
    repositorio.adicionar_mensagem(
        id_conversa=conversa.id,
        papel=PapelDaMensagem.ASSISTENTE,
        conteudo="Vou te ajudar.",
        session_id_do_provedor="sessao-interna-do-provedor",
    )

    mensagens = repositorio.listar_mensagens(conversa.id)
    assert [item.papel for item in mensagens] == [
        PapelDaMensagem.USUARIO,
        PapelDaMensagem.ASSISTENTE,
    ]
    # O session_id do provedor fica no banco (nao e exposto ao cliente).
    assert mensagens[1].session_id_do_provedor == "sessao-interna-do-provedor"

    repositorio.encerrar(conversa)
    assert conversa.encerrada_em is not None
    assert len(repositorio.listar_por_usuario(usuario_criado.id)) == 1
    assert repositorio.buscar_por_id(conversa.id) is not None


def test_mensagem_com_conversa_inexistente_viola_integridade(sessao) -> None:
    from app.dados.enums import PapelDaMensagem
    from app.dados.repositorios.conversas import ConversaRepositorio

    with pytest.raises(ErroDaAPIException) as capturado:
        ConversaRepositorio(sessao).adicionar_mensagem(
            id_conversa="inexistente",
            papel=PapelDaMensagem.USUARIO,
            conteudo="ola",
        )
    assert capturado.value.codigo is CodigoDeErro.CONFLITO


# --------------------------------------------------------------------------- #
# AuditoriaRepositorio
# --------------------------------------------------------------------------- #


def test_auditoria_registra_e_filtra(sessao, usuario_criado) -> None:
    from app.dados.repositorios.auditoria import AuditoriaRepositorio

    repositorio = AuditoriaRepositorio(sessao)
    repositorio.registrar(
        acao="login",
        entidade="usuarios",
        id_usuario=usuario_criado.id,
        id_entidade=usuario_criado.id,
        ip="127.0.0.1",
        detalhe={"canal": "web"},
    )
    repositorio.registrar(acao="criar_avaliacao", entidade="avaliacoes_de_risco")

    assert len(repositorio.listar()) == 2
    assert len(repositorio.listar(acao="login")) == 1
    assert len(repositorio.listar(id_usuario=usuario_criado.id)) == 1

    registro = repositorio.listar(acao="login")[0]
    assert registro.criado_em.tzinfo is not None
    assert registro.detalhe_json == {"canal": "web"}


def test_auditoria_aceita_evento_de_sistema_sem_usuario(sessao) -> None:
    from app.dados.repositorios.auditoria import AuditoriaRepositorio

    registro = AuditoriaRepositorio(sessao).registrar(
        acao="inicializacao", entidade="sistema"
    )
    assert registro.id_usuario is None
    assert registro.id_entidade is None