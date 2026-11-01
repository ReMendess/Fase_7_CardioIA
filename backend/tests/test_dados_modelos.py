"""Testes do esquema fisico: colunas, CHECKs, UNIQUEs e comportamento das FKs.

Verifica no **banco** o que o ``MODELO_DADOS.md`` §3 e §4 declara — inclusive as
regras de exclusao (``RESTRICT``/``CASCADE``/``SET NULL``), que o SQLite so respeita
porque a PRAGMA ``foreign_keys=ON`` e aplicada em toda conexao.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.contratos.envelope import StatusDaResposta
from app.dados.modelos import COLUNAS_DE_FEATURE

TABELAS_ESPERADAS = {
    "usuarios",
    "sessoes",
    "pacientes",
    "avaliacoes_de_risco",
    "protocolos_aplicados",
    "indicadores_deterministicos",
    "passos_da_execucao",
    "monitoramentos",
    "analises_de_imagem",
    "conversas",
    "mensagens",
    "eventos_de_auditoria",
    "versoes_do_esquema",
}

INSERT_USUARIO = (
    "INSERT INTO usuarios (id, nome, email, senha_hash, papel, ativo, criado_em)"
    " VALUES (:id, 'Nome', :email, 'hash', 'MEDICO', 1, '2026-10-31 12:00:00')"
)
INSERT_PACIENTE = (
    "INSERT INTO pacientes (id, nome, ativo, criado_em, criado_por)"
    " VALUES (:id, 'Paciente', 1, '2026-10-31 12:00:00', :usuario)"
)
INSERT_AVALIACAO = (
    "INSERT INTO avaliacoes_de_risco"
    " (id, id_execucao, id_paciente, id_usuario, criado_em,"
    "  idade_media, carga_sistema, tempo_espera, fc_media, spo2_media, pa_sistolica,"
    "  temperatura, densidade_eventos, eventos_24h, disponibilidade_recursos,"
    "  origem_dos_dados, status, modo)"
    " VALUES (:id, :id_execucao, :paciente, :usuario, '2026-10-31 12:00:00',"
    "  62, 92, 75, 118, 89, 100, 37.5, 7, 5, 25, 'manual', 'CONCLUIDO', 'simulado')"
)


def _executar(engine, sql: str, **parametros: object) -> None:
    with engine.begin() as conexao:
        conexao.execute(text(sql), parametros)


def _contar(engine, tabela: str) -> int:
    with engine.connect() as conexao:
        return int(conexao.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar() or 0)


@pytest.fixture
def cenario(engine_de_teste):
    """Usuario + paciente + avaliacao (o minimo para exercitar as FKs)."""
    _executar(engine_de_teste, INSERT_USUARIO, id="u1", email="u1@teste.local")
    _executar(engine_de_teste, INSERT_PACIENTE, id="p1", usuario="u1")
    _executar(
        engine_de_teste,
        INSERT_AVALIACAO,
        id="a1",
        id_execucao="e1",
        paciente="p1",
        usuario="u1",
    )
    return engine_de_teste


# --------------------------------------------------------------------------- #
# Estrutura
# --------------------------------------------------------------------------- #


def test_todas_as_tabelas_esperadas_existem(engine_de_teste) -> None:
    assert set(inspect(engine_de_teste).get_table_names()) == TABELAS_ESPERADAS


def test_as_dez_features_sao_not_null_sem_default(engine_de_teste) -> None:
    """Regra C7: ausencia de feature e erro — nao ha valor implicito."""
    colunas = {coluna["name"]: coluna for coluna in inspect(engine_de_teste).get_columns(
        "avaliacoes_de_risco"
    )}
    assert len(COLUNAS_DE_FEATURE) == 10
    for nome in COLUNAS_DE_FEATURE:
        assert nome in colunas, f"feature ausente: {nome}"
        assert colunas[nome]["nullable"] is False, f"'{nome}' deveria ser NOT NULL"
        assert colunas[nome]["default"] is None, f"'{nome}' nao pode ter default"


def test_status_reutiliza_os_quatro_valores_da_fase_6(engine_de_teste) -> None:
    """O enum do banco e o mesmo do envelope (fonte unica)."""
    coluna = next(
        coluna
        for coluna in inspect(engine_de_teste).get_columns("avaliacoes_de_risco")
        if coluna["name"] == "status"
    )
    assert coluna["nullable"] is False
    assert [estado.value for estado in StatusDaResposta] == [
        "CONCLUIDO",
        "CONCLUIDO_COM_RESSALVAS",
        "INCOMPLETO",
        "ERRO",
    ]


def test_indices_de_avaliacoes_cobrem_a_correlacao_e_o_historico(engine_de_teste) -> None:
    nomes = {indice["name"] for indice in inspect(engine_de_teste).get_indexes(
        "avaliacoes_de_risco"
    )}
    assert "ix_avaliacoes_paciente_criado" in nomes
    assert "ix_avaliacoes_status" in nomes
    assert "ix_avaliacoes_criado_em" in nomes


# --------------------------------------------------------------------------- #
# CHECKs
# --------------------------------------------------------------------------- #


def test_feature_negativa_e_rejeitada(engine_de_teste) -> None:
    _executar(engine_de_teste, INSERT_USUARIO, id="u1", email="u1@teste.local")
    _executar(engine_de_teste, INSERT_PACIENTE, id="p1", usuario="u1")
    with pytest.raises(IntegrityError):
        _executar(
            engine_de_teste,
            INSERT_AVALIACAO.replace("62, 92", "-1, 92"),
            id="a1",
            id_execucao="e1",
            paciente="p1",
            usuario="u1",
        )


def test_pico_risco_aceita_apenas_0_ou_1(cenario) -> None:
    _executar(
        cenario,
        "UPDATE avaliacoes_de_risco SET pico_risco_previsto = 1 WHERE id = 'a1'",
    )
    with pytest.raises(IntegrityError):
        _executar(
            cenario,
            "UPDATE avaliacoes_de_risco SET pico_risco_previsto = 2 WHERE id = 'a1'",
        )


def test_ordem_de_protocolo_respeita_1_a_10(cenario) -> None:
    sql = (
        "INSERT INTO protocolos_aplicados"
        " (id, id_avaliacao, ordem, identificador, texto_oficial, acao,"
        "  condicao_satisfeita, operador, limiar, valor_observado, origem_do_valor, usa_modelo)"
        " VALUES (:id, 'a1', :ordem, 'x', 't', 'a', 'c', '>', 1, 2, 'paciente', 0)"
    )
    _executar(cenario, sql, id="pr1", ordem=1)
    with pytest.raises(IntegrityError):
        _executar(cenario, sql, id="pr2", ordem=11)
    with pytest.raises(IntegrityError):
        _executar(cenario, sql, id="pr3", ordem=0)


def test_ordem_de_passo_precisa_ser_positiva(cenario) -> None:
    sql = (
        "INSERT INTO passos_da_execucao"
        " (id, id_avaliacao, ordem, tipo, agente, detalhe, sucesso)"
        " VALUES (:id, 'a1', :ordem, 'handoff', 'Orquestrador', 'd', 1)"
    )
    _executar(cenario, sql, id="pa1", ordem=1)
    with pytest.raises(IntegrityError):
        _executar(cenario, sql, id="pa2", ordem=0)


def test_monitoramento_exige_ao_menos_um_sinal_vital(engine_de_teste) -> None:
    sql = (
        "INSERT INTO monitoramentos"
        " (id, id_dispositivo, recebido_em, temperatura, bpm, origem_transporte)"
        " VALUES (:id, 'esp32-1', :quando, :temperatura, :bpm, 'mqtt')"
    )
    with pytest.raises(IntegrityError):
        _executar(
            engine_de_teste,
            sql,
            id="m1",
            quando="2026-10-31 12:00:00",
            temperatura=None,
            bpm=None,
        )
    _executar(
        engine_de_teste, sql, id="m2", quando="2026-10-31 12:00:00", temperatura=36.5, bpm=None
    )


def test_confianca_de_imagem_limitada_a_0_100(engine_de_teste) -> None:
    _executar(engine_de_teste, INSERT_USUARIO, id="u1", email="u1@teste.local")
    sql = (
        "INSERT INTO analises_de_imagem"
        " (id, id_usuario, criado_em, nome_arquivo, mime, tamanho_bytes, hash_sha256,"
        "  classe, confianca, modelo_utilizado, limiar_decisao)"
        " VALUES (:id, 'u1', '2026-10-31 12:00:00', 'x.png', 'image/png', 10, :hash,"
        "  'Normal', :confianca, 'mobilenet', 0.5)"
    )
    _executar(engine_de_teste, sql, id="i1", hash="a" * 64, confianca=99.0)
    with pytest.raises(IntegrityError):
        _executar(engine_de_teste, sql, id="i2", hash="b" * 64, confianca=101.0)


def test_tamanho_de_imagem_precisa_ser_positivo(engine_de_teste) -> None:
    _executar(engine_de_teste, INSERT_USUARIO, id="u1", email="u1@teste.local")
    with pytest.raises(IntegrityError):
        _executar(
            engine_de_teste,
            "INSERT INTO analises_de_imagem"
            " (id, id_usuario, criado_em, nome_arquivo, mime, tamanho_bytes, hash_sha256,"
            "  classe, confianca, modelo_utilizado, limiar_decisao)"
            " VALUES ('i1', 'u1', '2026-10-31 12:00:00', 'x.png', 'image/png', 0,"
            "  :hash, 'Normal', 50, 'mobilenet', 0.5)",
            hash="a" * 64,
        )


# --------------------------------------------------------------------------- #
# UNIQUEs
# --------------------------------------------------------------------------- #


def test_email_de_usuario_e_unico(engine_de_teste) -> None:
    _executar(engine_de_teste, INSERT_USUARIO, id="u1", email="mesmo@teste.local")
    with pytest.raises(IntegrityError):
        _executar(engine_de_teste, INSERT_USUARIO, id="u2", email="mesmo@teste.local")


def test_id_execucao_e_unico(cenario) -> None:
    with pytest.raises(IntegrityError):
        _executar(
            cenario,
            INSERT_AVALIACAO,
            id="a2",
            id_execucao="e1",  # mesmo UUID da Fase 6
            paciente="p1",
            usuario="u1",
        )


def test_token_hash_e_unico(engine_de_teste) -> None:
    _executar(engine_de_teste, INSERT_USUARIO, id="u1", email="u1@teste.local")
    sql = (
        "INSERT INTO sessoes (id, id_usuario, token_hash, criado_em, expira_em)"
        " VALUES (:id, 'u1', :hash, '2026-10-31 12:00:00', '2026-11-07 12:00:00')"
    )
    _executar(engine_de_teste, sql, id="s1", hash="h" * 64)
    with pytest.raises(IntegrityError):
        _executar(engine_de_teste, sql, id="s2", hash="h" * 64)


def test_protocolo_nao_repete_na_mesma_avaliacao(cenario) -> None:
    sql = (
        "INSERT INTO protocolos_aplicados"
        " (id, id_avaliacao, ordem, identificador, texto_oficial, acao,"
        "  condicao_satisfeita, operador, limiar, valor_observado, origem_do_valor, usa_modelo)"
        " VALUES (:id, 'a1', :ordem, :identificador, 't', 'a', 'c', '>', 1, 2, 'p', 0)"
    )
    _executar(cenario, sql, id="pr1", ordem=1, identificador="carga")
    with pytest.raises(IntegrityError):
        _executar(cenario, sql, id="pr2", ordem=2, identificador="carga")


def test_passo_nao_repete_ordem_na_mesma_avaliacao(cenario) -> None:
    sql = (
        "INSERT INTO passos_da_execucao"
        " (id, id_avaliacao, ordem, tipo, agente, detalhe, sucesso)"
        " VALUES (:id, 'a1', :ordem, 'tool', 'Analista de Risco', 'd', 1)"
    )
    _executar(cenario, sql, id="pa1", ordem=1)
    with pytest.raises(IntegrityError):
        _executar(cenario, sql, id="pa2", ordem=1)


def test_monitoramento_e_deduplicado_por_dispositivo_e_instante(engine_de_teste) -> None:
    """Idempotencia da ingestao (``MODELO_DADOS.md`` §3.8)."""
    sql = (
        "INSERT INTO monitoramentos"
        " (id, id_dispositivo, recebido_em, temperatura, origem_transporte)"
        " VALUES (:id, 'esp32-1', :quando, 36.5, 'mqtt')"
    )
    _executar(engine_de_teste, sql, id="m1", quando="2026-10-31 12:00:00")
    with pytest.raises(IntegrityError):
        _executar(engine_de_teste, sql, id="m2", quando="2026-10-31 12:00:00")


# --------------------------------------------------------------------------- #
# Regras de exclusao (FKs)
# --------------------------------------------------------------------------- #


def test_restrict_impede_excluir_usuario_com_avaliacao(cenario) -> None:
    """O historico clinico nao pode ser apagado por exclusao de usuario."""
    with pytest.raises(IntegrityError):
        _executar(cenario, "DELETE FROM usuarios WHERE id = 'u1'")
    assert _contar(cenario, "avaliacoes_de_risco") == 1


def test_cascade_remove_filhas_ao_excluir_avaliacao(cenario) -> None:
    _executar(
        cenario,
        "INSERT INTO protocolos_aplicados"
        " (id, id_avaliacao, ordem, identificador, texto_oficial, acao,"
        "  condicao_satisfeita, operador, limiar, valor_observado, origem_do_valor, usa_modelo)"
        " VALUES ('pr1', 'a1', 1, 'x', 't', 'a', 'c', '>', 1, 2, 'p', 0)",
    )
    _executar(
        cenario,
        "INSERT INTO passos_da_execucao"
        " (id, id_avaliacao, ordem, tipo, agente, detalhe, sucesso)"
        " VALUES ('pa1', 'a1', 1, 'tool', 'A', 'd', 1)",
    )
    assert _contar(cenario, "protocolos_aplicados") == 1

    _executar(cenario, "DELETE FROM avaliacoes_de_risco WHERE id = 'a1'")

    assert _contar(cenario, "protocolos_aplicados") == 0
    assert _contar(cenario, "passos_da_execucao") == 0


def test_set_null_preserva_telemetria_ao_excluir_paciente(cenario) -> None:
    """A telemetria sobrevive: o vinculo vira nulo, o dado nao se perde.

    Usa um paciente **sem** avaliacoes: ``avaliacoes_de_risco.id_paciente`` e
    ``RESTRICT``, entao um paciente com historico clinico nao pode ser excluido
    (comportamento desejado e testado em ``test_restrict_...``).
    """
    _executar(cenario, INSERT_PACIENTE, id="p2", usuario="u1")
    _executar(
        cenario,
        "INSERT INTO monitoramentos"
        " (id, id_paciente, id_dispositivo, recebido_em, temperatura, origem_transporte)"
        " VALUES ('m1', 'p2', 'esp32-1', '2026-10-31 12:00:00', 36.5, 'mqtt')",
    )
    _executar(cenario, "DELETE FROM pacientes WHERE id = 'p2'")

    with cenario.connect() as conexao:
        vinculo = conexao.execute(
            text("SELECT id_paciente FROM monitoramentos WHERE id = 'm1'")
        ).scalar()
    assert vinculo is None
    assert _contar(cenario, "monitoramentos") == 1


def test_restrict_impede_excluir_paciente_com_historico(cenario) -> None:
    """O historico do paciente bloqueia a exclusao (integridade do agregado)."""
    with pytest.raises(IntegrityError):
        _executar(cenario, "DELETE FROM pacientes WHERE id = 'p1'")


def test_cascade_remove_mensagens_ao_excluir_conversa(cenario) -> None:
    _executar(
        cenario,
        "INSERT INTO conversas (id, id_usuario, canal, iniciada_em)"
        " VALUES ('c1', 'u1', 'web', '2026-10-31 12:00:00')",
    )
    _executar(
        cenario,
        "INSERT INTO mensagens (id, id_conversa, papel, conteudo, criado_em)"
        " VALUES ('ms1', 'c1', 'user', 'ola', '2026-10-31 12:00:00')",
    )
    _executar(cenario, "DELETE FROM conversas WHERE id = 'c1'")
    assert _contar(cenario, "mensagens") == 0


def test_set_null_preserva_auditoria_ao_excluir_usuario(cenario) -> None:
    """Auditoria nao se perde: ao remover o usuario, ``id_usuario`` vira nulo.

    Usa um usuario **sem** avaliacoes, porque ``avaliacoes_de_risco.id_usuario`` e
    ``RESTRICT`` (o historico clinico bloqueia a exclusao — testado acima).
    """
    _executar(cenario, INSERT_USUARIO, id="u2", email="u2@teste.local")
    _executar(
        cenario,
        "INSERT INTO eventos_de_auditoria (id, id_usuario, acao, entidade, criado_em)"
        " VALUES ('ev1', 'u2', 'login', 'usuarios', '2026-10-31 12:00:00')",
    )

    _executar(cenario, "DELETE FROM usuarios WHERE id = 'u2'")

    with cenario.connect() as conexao:
        vinculo = conexao.execute(
            text("SELECT id_usuario FROM eventos_de_auditoria WHERE id = 'ev1'")
        ).scalar()
    assert vinculo is None
    assert _contar(cenario, "eventos_de_auditoria") == 1
