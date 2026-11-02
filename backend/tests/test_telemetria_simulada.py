"""Testes da telemetria simulada semeada no startup (``app/main.py``).

Por que a funcionalidade existe: em hospedagem gratuita o SQLite volta vazio a cada
reinicio e **nao ha dispositivo publicando na nuvem** — sem leituras, a aba Monitoramento
e o painel de indicadores do dashboard ficariam vazios na aplicacao publicada.

O que estes testes fixam:

- a semeadura so acontece com a tabela **vazia** (idempotencia);
- todas as leituras entram com ``origem_transporte = "simulado"``, para nenhuma ser
  apresentada como medicao de dispositivo real;
- o alerta **nao** reaparece no historico — nao ha coluna para ele, e isso e do contrato.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.dados.base import criar_engine, criar_fabrica_de_sessoes
from app.dados.enums import OrigemDoTransporte
from app.dados.modelos import Monitoramento
from app.main import LEITURAS_SIMULADAS, criar_app
from tests.conftest import _configuracao_base

ROTA = "/api/v1/iot/leituras"
ROTA_LOGIN = "/api/v1/auth/login"
EMAIL = "teste"
SENHA = "senhaTeste23@"


def _url(pasta: Path) -> str:
    """Banco isolado por teste (o padrao da suite e compartilhado)."""
    return f"sqlite:///{(pasta / 'telemetria.db').as_posix()}"


def _configuracao(pasta: Path, **extras: object):
    """Conta de demonstracao ligada: e por ela que o teste le a telemetria."""
    extras.setdefault("semear_usuario_inicial", True)
    extras.setdefault("semear_telemetria_simulada", True)
    return _configuracao_base(str(pasta), database_url=_url(pasta), **extras)


def _leituras(url: str) -> list[Monitoramento]:
    """Leituras direto do banco, mais recentes primeiro."""
    engine = criar_engine(url)
    with criar_fabrica_de_sessoes(engine)() as sessao:
        leituras = list(
            sessao.scalars(
                select(Monitoramento).order_by(Monitoramento.recebido_em.desc())
            )
        )
    engine.dispose()
    return leituras


def _token(cliente: TestClient) -> str:
    """Token da conta de demonstracao (papel MEDICO le telemetria)."""
    resposta = cliente.post(ROTA_LOGIN, json={"email": EMAIL, "senha": SENHA})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["dados"]["access_token"]


def _listar(cliente: TestClient) -> dict:
    """`GET /iot/leituras` autenticado."""
    resposta = cliente.get(ROTA, headers={"Authorization": f"Bearer {_token(cliente)}"})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_telemetria_e_semeada_quando_o_banco_esta_vazio(tmp_path: Path) -> None:
    """Servidor novo, banco vazio: a aba Monitoramento ja tem o que mostrar."""
    with TestClient(criar_app(_configuracao(tmp_path))) as cliente:
        corpo = _listar(cliente)

    assert corpo["status"] == "CONCLUIDO"
    assert len(corpo["dados"]) == len(LEITURAS_SIMULADAS)


def test_semeadura_e_idempotente(tmp_path: Path) -> None:
    """Dois startups no mesmo banco nao duplicam as leituras."""
    config = _configuracao(tmp_path)

    with TestClient(criar_app(config)):
        pass
    with TestClient(criar_app(config)):
        pass

    assert len(_leituras(_url(tmp_path))) == len(LEITURAS_SIMULADAS)


def test_semeadura_desligada_nao_cria_nada(tmp_path: Path) -> None:
    """`SEMEAR_TELEMETRIA_SIMULADA=false` deixa a tabela vazia."""
    config = _configuracao(tmp_path, semear_telemetria_simulada=False)

    with TestClient(criar_app(config)):
        pass

    assert _leituras(_url(tmp_path)) == []


def test_banco_com_leitura_nao_recebe_a_semeadura(tmp_path: Path) -> None:
    """Se ja existe uma leitura, o startup nao acrescenta nada.

    E o que impede misturar dado semeado com o de um dispositivo de verdade.
    """
    from app.dados.repositorios.telemetria import MonitoramentoRepositorio

    url = _url(tmp_path)

    # Primeiro startup cria o esquema **sem** semear.
    with TestClient(criar_app(_configuracao(tmp_path, semear_telemetria_simulada=False))):
        pass

    engine = criar_engine(url)
    with criar_fabrica_de_sessoes(engine)() as sessao:
        MonitoramentoRepositorio(sessao).registrar(
            id_dispositivo="esp32-de-verdade",
            origem_transporte=OrigemDoTransporte.REST,
            temperatura=36.5,
            bpm=80,
        )
    engine.dispose()

    with TestClient(criar_app(_configuracao(tmp_path))):
        pass

    leituras = _leituras(url)
    assert len(leituras) == 1
    assert leituras[0].id_dispositivo == "esp32-de-verdade"


def test_toda_leitura_semeada_e_marcada_como_simulada(tmp_path: Path) -> None:
    """Nenhuma leitura semeada pode se passar por medicao de dispositivo real.

    O rotulo na interface vem de `origem_transporte` (`catalogo.js` o exibe como
    "Simulado"), entao o valor precisa ser exatamente este.
    """
    with TestClient(criar_app(_configuracao(tmp_path))):
        pass

    origens = {leitura.origem_transporte for leitura in _leituras(_url(tmp_path))}
    assert origens == {OrigemDoTransporte.SIMULADO}


def test_serie_cobre_dois_dispositivos_e_vem_em_ordem_decrescente(tmp_path: Path) -> None:
    """Dois dispositivos: sem isso o filtro da tela nao teria o que filtrar."""
    with TestClient(criar_app(_configuracao(tmp_path))):
        pass

    leituras = _leituras(_url(tmp_path))
    dispositivos = {leitura.id_dispositivo for leitura in leituras}

    assert len(dispositivos) == 2
    assert "esp32-wokwi-01" in dispositivos

    momentos = [leitura.recebido_em for leitura in leituras]
    assert momentos == sorted(momentos, reverse=True)


def test_leitura_semeada_traz_os_sinais_do_contrato(tmp_path: Path) -> None:
    """A leitura chega completa na API — nao so o minimo exigido pelo CHECK do banco."""
    with TestClient(criar_app(_configuracao(tmp_path))) as cliente:
        primeira = _listar(cliente)["dados"][0]

    campos = (
        "id_leitura",
        "id_dispositivo",
        "recebido_em",
        "temperatura",
        "bpm",
        "umidade",
        "luminosidade",
    )
    for campo in campos:
        assert primeira[campo] is not None, campo

    # O contrato §4.2 fecha o DTO: a telemetria nao e vinculada a paciente.
    assert "id_paciente" not in primeira


def test_recebido_em_e_anterior_ao_boot(tmp_path: Path) -> None:
    """As leituras sao posicionadas no passado, formando uma serie temporal.

    Sem isso todas cairiam no mesmo segundo e a lista nao mostraria evolucao.
    """
    antes = datetime.now(timezone.utc)

    with TestClient(criar_app(_configuracao(tmp_path))):
        pass

    leituras = _leituras(_url(tmp_path))
    assert all(leitura.recebido_em < antes for leitura in leituras)
    # E espalhadas: a mais recente e a mais antiga nao coincidem.
    assert leituras[0].recebido_em > leituras[-1].recebido_em


def test_alerta_nao_e_persistido_nem_reaparece_no_historico(tmp_path: Path) -> None:
    """O alerta da regra da Fase 3 e derivado — nao ha coluna para ele.

    A serie semeada inclui uma leitura febril de proposito. O `GET` devolve os **sinais
    brutos** e um envelope sem `avisos`: quem le o historico nao recebe o alerta. Isso e
    do contrato, e o teste existe para que uma mudanca futura seja uma decisao, nao um
    efeito colateral.
    """
    from app.regras_iot import ALERTA_DE_FEBRE, avaliar_sinais

    febris = [
        leitura
        for leitura in LEITURAS_SIMULADAS
        if avaliar_sinais(
            temperatura=leitura["temperatura"],
            bpm=leitura["bpm"],
            movimento=leitura.get("movimento"),
        ).alerta
        == ALERTA_DE_FEBRE
    ]
    assert febris, "a serie semeada precisa exercitar o caminho do alerta"

    with TestClient(criar_app(_configuracao(tmp_path))) as cliente:
        corpo = _listar(cliente)

    assert corpo["avisos"] == []
    assert corpo["status"] == "CONCLUIDO"
    # A limitacao que explica o escopo da telemetria vem em toda resposta (Decisao D4).
    assert corpo["limitacoes"]
