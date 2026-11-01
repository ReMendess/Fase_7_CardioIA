"""Fixtures compartilhadas dos testes do backend (Etapa C, itens 1 a 3).

Regras:

- o **segredo de teste nao e um segredo real** e existe apenas para permitir a
  falha rapida da configuracao durante a suite;
- as fixtures usam ``_env_file=None`` para **nao depender do ``.env``** do
  desenvolvedor — o resultado do teste nao muda conforme a maquina;
- a pasta da Fase 6 e substituida por um diretorio temporario, de modo que a
  presenca/ausencia do artefato do modelo seja **deterministica**;
- o banco e **em memoria** (``sqlite+pysqlite:///:memory:`` com ``StaticPool``):
  nenhum arquivo e criado no disco e cada teste comeca limpo.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

RAIZ_DO_BACKEND = Path(__file__).resolve().parents[1]
if str(RAIZ_DO_BACKEND) not in sys.path:
    sys.path.insert(0, str(RAIZ_DO_BACKEND))

#: Segredo de teste (NAO e um segredo real). Definido antes de importar ``app.main``.
SEGREDO_DE_TESTE = "segredo-de-teste-" + "0" * 24  # 40 caracteres

#: URL do banco de teste — em memoria, isolado por engine.
URL_DE_BANCO_DE_TESTE = "sqlite+pysqlite:///:memory:"

os.environ.setdefault("JWT_SECRET", SEGREDO_DE_TESTE)
os.environ.setdefault("AMBIENTE", "teste")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.config import CANDIDATO_FASE_6, Configuracoes  # noqa: E402
from app.dados.base import criar_engine, criar_fabrica_de_sessoes  # noqa: E402
from app.dados.enums import PapelDoUsuario  # noqa: E402
from app.dados.esquema import criar_esquema  # noqa: E402
from app.dados.modelos import Paciente, Usuario  # noqa: E402
from app.dados.repositorios.assistencial import (  # noqa: E402
    AvaliacaoRepositorio,
    PacienteRepositorio,
)
from app.dados.repositorios.identidade import UsuarioRepositorio  # noqa: E402
from app.integracao.fase_6 import ModulosDaFase6, importar  # noqa: E402
from app.integracao.modelo import ArtefatoDoModelo, CacheDoModelo  # noqa: E402
from app.main import criar_app  # noqa: E402
from app.seguranca.senhas import gerar_hash  # noqa: E402

NOME_DO_MODELO = "modelo_pico_risco.pkl"
NOME_DOS_METADADOS = "modelo_pico_risco_metadata.json"

#: As 10 features — **valores do paciente da aula** (``Fase_6/data/novo_paciente.py``).
#: A unica diferenca: aqui o nome da ultima coluna ja vem normalizado
#: (``disponibilidade_recursos``), porque o modelo exige exatamente esse nome.
FEATURES_DO_PACIENTE_DA_AULA: dict[str, float] = {
    "idade_media": 62.0,
    "carga_sistema": 92.0,
    "tempo_espera": 75.0,
    "fc_media": 118.0,
    "spo2_media": 89.0,
    "pa_sistolica": 100.0,
    "temperatura": 37.5,
    "densidade_eventos": 7.0,
    "eventos_24h": 5.0,
    "disponibilidade_recursos": 25.0,
}



def _configuracao_base(pasta_fase_6: str, **extras: object) -> Configuracoes:
    """Configuracao de teste isolada do ambiente do desenvolvedor."""
    parametros: dict[str, object] = {
        "_env_file": None,
        "ambiente": "teste",
        "jwt_secret": SEGREDO_DE_TESTE,
        "pasta_fase_6": pasta_fase_6,
        "cors_origens": "http://localhost:5173",
        "database_url": URL_DE_BANCO_DE_TESTE,
        # Nao aquecer o modelo no startup: cada aplicacao de teste pagaria ~5 s de import
        # da Fase 6. Os testes que precisam do pipeline aquecem o cache explicitamente.
        "aquecer_modelo_no_startup": False,
        # Nenhum teste deve receber a conta de demonstracao: os ambientes de teste
        # criam os proprios usuarios e varios deles contam registros.
        "semear_usuario_inicial": False,
    }
    parametros.update(extras)
    return Configuracoes(**parametros)  # type: ignore[arg-type]


@pytest.fixture(scope="session")
def configuracoes_sem_modelo(tmp_path_factory: pytest.TempPathFactory) -> Configuracoes:
    """Configuracao apontando para uma pasta da Fase 6 **sem** artefato."""
    pasta = tmp_path_factory.mktemp("fase6_sem_modelo")
    return _configuracao_base(str(pasta))


@pytest.fixture(scope="session")
def configuracoes_com_modelo(tmp_path_factory: pytest.TempPathFactory) -> Configuracoes:
    """Configuracao apontando para uma pasta com **artefato simulado** presente."""
    pasta = tmp_path_factory.mktemp("fase6_com_modelo")
    modelos = pasta / "models"
    modelos.mkdir(parents=True, exist_ok=True)
    (modelos / NOME_DO_MODELO).write_bytes(b"artefato-simulado-de-teste")
    (modelos / NOME_DOS_METADADOS).write_text('{"features": []}', encoding="utf-8")
    return _configuracao_base(str(pasta))


@pytest.fixture(scope="session")
def cliente_sem_modelo(configuracoes_sem_modelo: Configuracoes) -> Iterator[TestClient]:
    """Cliente HTTP do servico **sem** artefato do modelo.

    Usa o gerenciador de contexto para disparar o ``lifespan`` (que prepara o banco).
    """
    with TestClient(criar_app(configuracoes_sem_modelo)) as cliente:
        yield cliente


@pytest.fixture(scope="session")
def cliente_com_modelo(configuracoes_com_modelo: Configuracoes) -> Iterator[TestClient]:
    """Cliente HTTP do servico **com** artefato do modelo."""
    with TestClient(criar_app(configuracoes_com_modelo)) as cliente:
        yield cliente


# --------------------------------------------------------------------------- #
# Banco de dados (item 2)
# --------------------------------------------------------------------------- #


@pytest.fixture
def engine_de_teste() -> Iterator[Engine]:
    """Engine SQLite **em memoria** com o esquema criado (isolado por teste)."""
    engine = criar_engine(URL_DE_BANCO_DE_TESTE, para_testes=True)
    criar_esquema(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def fabrica_de_sessoes(engine_de_teste: Engine) -> sessionmaker[Session]:
    """Fabrica de sessoes ligada ao banco de teste."""
    return criar_fabrica_de_sessoes(engine_de_teste)


@pytest.fixture
def sessao(fabrica_de_sessoes: sessionmaker[Session]) -> Iterator[Session]:
    """Sessao unica para o teste (fechada ao final)."""
    with fabrica_de_sessoes() as sessao_aberta:
        yield sessao_aberta


# --------------------------------------------------------------------------- #
# Repositorios e entidades
# --------------------------------------------------------------------------- #


@pytest.fixture
def usuario_repositorio(sessao: Session) -> UsuarioRepositorio:
    return UsuarioRepositorio(sessao)


@pytest.fixture
def paciente_repositorio(sessao: Session) -> PacienteRepositorio:
    return PacienteRepositorio(sessao)


@pytest.fixture
def avaliacao_repositorio(sessao: Session) -> AvaliacaoRepositorio:
    return AvaliacaoRepositorio(sessao)


@pytest.fixture
def usuario_criado(usuario_repositorio: UsuarioRepositorio) -> Usuario:
    """Usuario ``MEDICO`` pronto para uso nos testes."""
    return usuario_repositorio.criar(
        nome="Dra. Teste",
        email="medico@teste.local",
        senha_hash="$2b$12$hash-de-teste-nao-real",
        papel=PapelDoUsuario.MEDICO,
    )


@pytest.fixture
def paciente_criado(
    paciente_repositorio: PacienteRepositorio, usuario_criado: Usuario
) -> Paciente:
    """Paciente pronto para uso nos testes."""
    return paciente_repositorio.criar(
        nome="Paciente de Teste", criado_por=usuario_criado.id
    )


@pytest.fixture
def features_validas() -> dict[str, float]:
    """Copia das 10 features do paciente da aula (mutavel pelo teste)."""
    return dict(FEATURES_DO_PACIENTE_DA_AULA)


# --------------------------------------------------------------------------- #
# Autenticacao (item 3)
# --------------------------------------------------------------------------- #

#: Custo do bcrypt nos testes: **4** (minimo do algoritmo) para a suite ficar rapida.
#: Producao usa ``app.seguranca.senhas.CUSTO_PADRAO`` (12).
CUSTO_DE_TESTE = 4

SENHA_DE_TESTE = "SenhaDeTeste123"
EMAIL_DE_TESTE = "medico@teste.local"


class _AmbienteComBanco(Protocol):
    """Contrato minimo dos ambientes de teste: cliente HTTP + banco do **mesmo** app.

    Existe para que `semear_usuario` e `fazer_login` sirvam tanto ao ambiente de
    autenticacao quanto ao ambiente clinico, sem duplicar codigo.
    """

    cliente: TestClient
    fabrica_de_sessoes: sessionmaker[Session]


@dataclass
class AmbienteDeAutenticacao:
    """Aplicacao, cliente HTTP e fabrica de sessoes **do mesmo banco**.

    O app e criado por teste, com banco em memoria proprio — assim cada teste comeca
    limpo e a sessao usada para semear dados e a mesma que as rotas usam.
    """

    app: Any
    cliente: TestClient
    fabrica_de_sessoes: sessionmaker[Session]


@pytest.fixture
def ambiente_de_autenticacao(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[AmbienteDeAutenticacao]:
    """Ambiente isolado para exercitar as rotas de autenticacao."""
    pasta = tmp_path_factory.mktemp("fase6_autenticacao")
    config = _configuracao_base(str(pasta))
    app = criar_app(config)

    with TestClient(app) as cliente:
        yield AmbienteDeAutenticacao(
            app=app, cliente=cliente, fabrica_de_sessoes=app.state.fabrica_de_sessoes
        )


def semear_usuario(
    ambiente: _AmbienteComBanco,
    *,
    email: str = EMAIL_DE_TESTE,
    senha: str = SENHA_DE_TESTE,
    papel: PapelDoUsuario = PapelDoUsuario.MEDICO,
    ativo: bool = True,
) -> dict[str, str]:
    """Grava um usuario com senha real (bcrypt de custo baixo) e devolve os dados.

    Returns:
        ``{"id", "email", "senha", "papel"}`` — dicionario simples para evitar objeto
        ORM desanexado da sessao.
    """
    with ambiente.fabrica_de_sessoes() as sessao:
        usuario = UsuarioRepositorio(sessao).criar(
            nome="Dra. Teste",
            email=email,
            senha_hash=gerar_hash(senha, custo=CUSTO_DE_TESTE),
            papel=papel,
            ativo=ativo,
        )
        return {
            "id": usuario.id,
            "email": usuario.email,
            "senha": senha,
            "papel": usuario.papel.value,
        }


def fazer_login(
    ambiente: _AmbienteComBanco,
    *,
    email: str = EMAIL_DE_TESTE,
    senha: str = SENHA_DE_TESTE,
) -> dict[str, Any]:
    """Executa ``POST /auth/login`` e devolve ``{status_code, corpo}``."""
    resposta = ambiente.cliente.post(
        "/api/v1/auth/login", json={"email": email, "senha": senha}
    )
    return {"status_code": resposta.status_code, "corpo": resposta.json()}


# --------------------------------------------------------------------------- #
# Fluxo clinico (item 4, bloco 2): pacientes e avaliacoes
# --------------------------------------------------------------------------- #


@dataclass
class AmbienteClinico:
    """App com a **Fase 6 real**, banco proprio e um usuario ``MEDICO`` autenticado.

    Diferente de :class:`AmbienteDeAutenticacao`, a configuracao aponta para a pasta real
    da Fase 6 — o pipeline roda de verdade (em modo ``simulado``, sem API externa).
    """

    app: Any
    cliente: TestClient
    fabrica_de_sessoes: sessionmaker[Session]
    config: Configuracoes
    token: str
    id_usuario: str


def cabecalho(token: str) -> dict[str, str]:
    """Header de autenticacao no formato ``Bearer``."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def cache_do_modelo_aquecido(configuracao_com_fase_6_real: Configuracoes) -> CacheDoModelo:
    """Cache do modelo **já carregado**, compartilhado pelos apps de teste.

    O cache é por aplicação; em teste, reler 4,7 MB em cada teste não agrega nada — o
    comportamento do cache (carregar uma vez, ser seguro em concorrência, aquecer sem
    derrubar o boot) é verificado em `test_integracao_modelo.py`.
    """
    cache = CacheDoModelo()
    assert cache.obter(configuracao_com_fase_6_real) is not None
    return cache


@contextmanager
def _app_de_teste(
    config: Configuracoes, cache: CacheDoModelo | None = None
) -> Iterator[AmbienteClinico]:
    """Sobe o app, semeia um usuario ``MEDICO``, faz login e entrega o ambiente.

    Extraido para que os ambientes de teste (clinico, visao) compartilhem a mesma
    montagem sem duplicar semeadura e login.
    """
    app = criar_app(config)
    if cache is not None:
        # Injeta o cache já aquecido (o app cria o seu proprio ao ser montado).
        app.state.cache_do_modelo = cache

    with TestClient(app) as cliente:
        with app.state.fabrica_de_sessoes() as sessao:
            usuario = UsuarioRepositorio(sessao).criar(
                nome="Dra. Clinica",
                email=EMAIL_DE_TESTE,
                senha_hash=gerar_hash(SENHA_DE_TESTE, custo=CUSTO_DE_TESTE),
                papel=PapelDoUsuario.MEDICO,
            )
            id_usuario = usuario.id

        entrada = cliente.post(
            "/api/v1/auth/login", json={"email": EMAIL_DE_TESTE, "senha": SENHA_DE_TESTE}
        )
        assert entrada.status_code == 200, entrada.text

        yield AmbienteClinico(
            app=app,
            cliente=cliente,
            fabrica_de_sessoes=app.state.fabrica_de_sessoes,
            config=config,
            token=entrada.json()["dados"]["access_token"],
            id_usuario=id_usuario,
        )


@pytest.fixture
def ambiente_clinico(
    configuracao_com_fase_6_real: Configuracoes,
    modulos_da_fase_6: ModulosDaFase6,
    cache_do_modelo_aquecido: CacheDoModelo,
) -> Iterator[AmbienteClinico]:
    """Ambiente para exercitar as rotas de pacientes e de avaliacoes."""
    with _app_de_teste(configuracao_com_fase_6_real, cache_do_modelo_aquecido) as ambiente:
        yield ambiente


@pytest.fixture
def ambiente_de_visao(
    tmp_path_factory: pytest.TempPathFactory,
    servico_de_visao_falso: ServicoDeVisaoFalso,
) -> Iterator[AmbienteClinico]:
    """Ambiente com o servico de visao apontando para o **falso**.

    Nao precisa da Fase 6 nem do modelo: a analise de imagem nao toca no pipeline
    preditivo (sao contratos distintos, achado I3).
    """
    pasta = tmp_path_factory.mktemp("fase7_visao")
    config = _configuracao_base(
        str(pasta),
        servico_visao_url=servico_de_visao_falso.url,
        servico_visao_timeout_segundos=5.0,
    )
    with _app_de_teste(config) as ambiente:
        yield ambiente


def criar_paciente(
    ambiente: AmbienteClinico, *, nome: str = "Paciente de Teste"
) -> str:
    """Cadastra um paciente via API e devolve o ``id_paciente``."""
    resposta = ambiente.cliente.post(
        "/api/v1/pacientes", json={"nome": nome}, headers=cabecalho(ambiente.token)
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["dados"]["id_paciente"]


def token_com_papel(ambiente: AmbienteClinico, papel: PapelDoUsuario) -> str:
    """Semeia um usuario com outro papel e devolve o access token dele (testes de RBAC).

    O e-mail usa o prefixo ``usuario-`` para **nao colidir** com o usuario ja semeado pelo
    ambiente (``medico@teste.local``): sem isso, pedir o token de ``MEDICO`` daria
    violacao de UNIQUE (409) em vez de um token.
    """
    email = f"usuario-{papel.value.lower()}@teste.local"
    with ambiente.fabrica_de_sessoes() as sessao:
        UsuarioRepositorio(sessao).criar(
            nome=f"Usuario {papel.value}",
            email=email,
            senha_hash=gerar_hash(SENHA_DE_TESTE, custo=CUSTO_DE_TESTE),
            papel=papel,
        )

    entrada = ambiente.cliente.post(
        "/api/v1/auth/login", json={"email": email, "senha": SENHA_DE_TESTE}
    )
    assert entrada.status_code == 200, entrada.text
    return entrada.json()["dados"]["access_token"]


#: Chave de dispositivo usada nos testes (NAO e um segredo real).
CHAVE_DE_DISPOSITIVO_DE_TESTE = "chave-de-dispositivo-de-teste-" + "a" * 12


@dataclass
class AmbienteIoT:
    """App com a ingestao de telemetria habilitada (chave de dispositivo configurada)."""

    app: Any
    cliente: TestClient
    fabrica_de_sessoes: sessionmaker[Session]
    config: Configuracoes
    chave: str
    tokens: dict[PapelDoUsuario, str]

    def token(self, papel: PapelDoUsuario) -> str:
        """Access token do usuario semeado com o papel informado."""
        return self.tokens[papel]


def cabecalho_de_dispositivo(chave: str) -> dict[str, str]:
    """Header da chave de dispositivo IoT (``X-Device-Key``)."""
    return {"X-Device-Key": chave}


@pytest.fixture
def ambiente_iot(tmp_path_factory: pytest.TempPathFactory) -> Iterator[AmbienteIoT]:
    """Ambiente para exercitar as rotas de telemetria.

    Nao precisa da Fase 6 real: a ingestao de telemetria **nao** toca no modelo
    (Decisao D4), entao o app sobe com uma pasta temporaria e responde rapido.
    """
    pasta = tmp_path_factory.mktemp("fase7_iot")
    config = _configuracao_base(str(pasta), iot_device_key=CHAVE_DE_DISPOSITIVO_DE_TESTE)
    app = criar_app(config)

    with TestClient(app) as cliente:
        papeis = (PapelDoUsuario.OPERADOR, PapelDoUsuario.MEDICO, PapelDoUsuario.ADMIN)
        with app.state.fabrica_de_sessoes() as sessao:
            repositorio = UsuarioRepositorio(sessao)
            for papel in papeis:
                repositorio.criar(
                    nome=f"Usuario {papel.value}",
                    email=f"{papel.value.lower()}@teste.local",
                    senha_hash=gerar_hash(SENHA_DE_TESTE, custo=CUSTO_DE_TESTE),
                    papel=papel,
                )

        tokens: dict[PapelDoUsuario, str] = {}
        for papel in papeis:
            entrada = cliente.post(
                "/api/v1/auth/login",
                json={"email": f"{papel.value.lower()}@teste.local", "senha": SENHA_DE_TESTE},
            )
            assert entrada.status_code == 200, entrada.text
            tokens[papel] = entrada.json()["dados"]["access_token"]

        yield AmbienteIoT(
            app=app,
            cliente=cliente,
            fabrica_de_sessoes=app.state.fabrica_de_sessoes,
            config=config,
            chave=CHAVE_DE_DISPOSITIVO_DE_TESTE,
            tokens=tokens,
        )


def ingerir_leitura(
    ambiente: AmbienteIoT,
    *,
    dispositivo: str = "esp32-sala-1",
    origem_transporte: str = "rest",
    token: str | None = None,
    chave: str | None = None,
    **sinais: object,
) -> dict[str, Any]:
    """Executa ``POST /iot/leituras`` e devolve ``{status_code, corpo}``.

    ``sinais`` sao os campos da leitura (``temperatura``, ``bpm``, ``movimento``, ...).
    """
    corpo: dict[str, Any] = {
        "id_dispositivo": dispositivo,
        "origem_transporte": origem_transporte,
        **sinais,
    }
    cabecalhos: dict[str, str] = {}
    if chave is not None:
        cabecalhos.update(cabecalho_de_dispositivo(chave))
    elif token is not None:
        cabecalhos.update(cabecalho(token))

    resposta = ambiente.cliente.post("/api/v1/iot/leituras", json=corpo, headers=cabecalhos)
    return {"status_code": resposta.status_code, "corpo": resposta.json()}


# --------------------------------------------------------------------------- #
# Duble do SDK do Watson (item 7)
# --------------------------------------------------------------------------- #


class ErroDoSdk(Exception):
    """Imita ``ibm_cloud_sdk_core.ApiException`` (tem ``code`` e ``message``)."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class _ResultadoFalso:
    """Imita o objeto com ``get_result()`` devolvido pelo SDK."""

    def __init__(self, dados: object) -> None:
        self._dados = dados

    def get_result(self) -> object:
        return self._dados


class ClienteFalso:
    """Imita o ``AssistantV2``: registra as chamadas e permite roteirizar falhas.

    Permite testar o fluxo do assistente **sem rede**: sessao criada/reaproveitada,
    recuperacao de sessao expirada (404) e cada faixa de erro do provedor.
    """

    def __init__(
        self,
        *,
        sessoes: tuple[str | None, ...] = ("sessao-1",),
        textos: tuple[str, ...] = ("Resposta do assistente",),
        falhas: tuple[BaseException | None, ...] = (),
    ) -> None:
        self.sessoes = list(sessoes)
        self.textos = list(textos)
        self.falhas = list(falhas)
        self.sessoes_criadas = 0
        self.mensagens_enviadas: list[dict[str, object]] = []
        self.texto_atual = "Resposta do assistente"

    def create_session(self, **kwargs: object) -> _ResultadoFalso:
        """Devolve a proxima sessao roteirizada; sem roteiro, gera uma sequencial.

        O roteiro existe para **forcar** um valor (inclusive ``None``); sem ele, o duble
        precisa se comportar como o provedor real e sempre devolver uma sessao — do
        contrario, um teste que faz dois turnos quebraria por esgotar a lista.
        """
        self.sessoes_criadas += 1
        sessao = self.sessoes.pop(0) if self.sessoes else f"sessao-{self.sessoes_criadas}"
        return _ResultadoFalso({"session_id": sessao})

    def message(self, **kwargs: object) -> _ResultadoFalso:
        self.mensagens_enviadas.append(kwargs)
        if self.falhas:
            erro = self.falhas.pop(0)
            if erro is not None:
                raise erro
        if self.textos:
            self.texto_atual = self.textos.pop(0)
        return _ResultadoFalso(
            {"output": {"generic": [{"response_type": "text", "text": self.texto_atual}]}}
        )


def configuracao_do_watson(**extras: object) -> Configuracoes:
    """Configuracao de teste com o Watson preenchido (valores ficticios)."""
    import tempfile

    parametros: dict[str, object] = {
        "watson_api_key": "chave-ficticia-de-teste",
        "watson_service_url": "https://exemplo.invalid/instances/abc",
        "watson_assistant_id": "assistente-ficticio",
        "watson_environment_id": "ambiente-ficticio",
    }
    parametros.update(extras)
    return _configuracao_base(tempfile.mkdtemp(prefix="fase7_watson_"), **parametros)


@pytest.fixture
def cliente_do_watson_falso(monkeypatch: pytest.MonkeyPatch) -> ClienteFalso:
    """Substitui ``fase_5.criar_cliente`` por um cliente falso (nao toca na rede)."""
    from app.integracao import fase_5

    cliente = ClienteFalso()
    monkeypatch.setattr(fase_5, "criar_cliente", lambda config: cliente)
    return cliente


@pytest.fixture
def ambiente_do_assistente(
    tmp_path_factory: pytest.TempPathFactory,
    cliente_do_watson_falso: ClienteFalso,
) -> Iterator[AmbienteClinico]:
    """App com o Watson **configurado** (credenciais ficticias) e SDK falso.

    As credenciais sao ficticias de proposito: o backend le **apenas** do ambiente e nao
    usa os valores default do codigo da Fase 5 (achado S1).
    """
    pasta = tmp_path_factory.mktemp("fase7_assistente")
    config = _configuracao_base(
        str(pasta),
        watson_api_key="chave-ficticia-de-teste",
        watson_service_url="https://exemplo.invalid/instances/abc",
        watson_assistant_id="assistente-ficticio",
        watson_environment_id="ambiente-ficticio",
    )
    with _app_de_teste(config) as ambiente:
        yield ambiente


def conversar_com_o_assistente(
    ambiente: AmbienteClinico,
    *,
    mensagem: str = "Ola, assistente",
    id_conversa: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Executa ``POST /chat`` e devolve ``{status_code, corpo}``."""
    corpo: dict[str, Any] = {"mensagem": mensagem}
    if id_conversa is not None:
        corpo["id_conversa"] = id_conversa
    resposta = ambiente.cliente.post(
        "/api/v1/chat", json=corpo, headers=cabecalho(token or ambiente.token)
    )
    return {"status_code": resposta.status_code, "corpo": resposta.json()}


# --------------------------------------------------------------------------- #
# Servico de visao falso (item 6)
# --------------------------------------------------------------------------- #


@dataclass
class ServicoDeVisaoFalso:
    """Servico da Fase 4 **falso**, que reproduz o contrato do ``app.py`` original.

    Por que existe: o servico real carrega TensorFlow no *import* e **TensorFlow nao esta
    instalado** neste ambiente — a ausencia dele e justamente a razao da Decisao 1-C
    (servico isolado). O falso responde as **mesmas chaves** (``class``/``confidence``), no
    **mesmo campo de arquivo** (``image``) e com a **mesma regra** (``probability > 0.5``,
    ``confidence = p`` se ``p > 0.5`` senao ``1 - p``). Ele permite ainda simular falhas
    (HTTP 500, corpo invalido, lentidao) que o servico real nao produz sob demanda.
    """

    url: str
    estado: dict[str, Any]
    recebidas: list[dict[str, Any]]

    def reiniciar(self) -> None:
        """Volta ao estado inicial (usado entre testes, com o servidor compartilhado)."""
        self.estado.update(
            {"status": 200, "corpo": None, "probabilidade": 0.9, "atraso": 0.0}
        )
        self.recebidas.clear()

    def responder(self, *, probabilidade: float) -> None:
        """Volta ao comportamento normal, com a probabilidade informada."""
        self.estado.update({"status": 200, "corpo": None, "probabilidade": probabilidade})

    def falhar_com(self, status: int, corpo: Any) -> None:
        """Faz o servico responder o status/corpo informados."""
        self.estado.update({"status": status, "corpo": corpo})

    def demorar(self, segundos: float) -> None:
        """Atrasa a resposta (para exercitar o timeout)."""
        self.estado["atraso"] = segundos


def porta_livre() -> int:
    """Porta TCP livre no momento da chamada."""
    import socket

    with socket.socket() as soquete:
        soquete.bind(("127.0.0.1", 0))
        return int(soquete.getsockname()[1])


@pytest.fixture(scope="session")
def _servidor_de_visao_compartilhado() -> Iterator[ServicoDeVisaoFalso]:
    """Sobe o servico falso **uma vez por sessao** (subir um Flask por teste e caro)."""
    pytest.importorskip("flask", reason="Flask nao instalado (necessario para o falso).")
    from flask import Flask, jsonify
    from flask import request as requisicao_flask
    from werkzeug.serving import make_server

    app = Flask("fase_4_falsa")
    estado: dict[str, Any] = {
        "status": 200,
        "corpo": None,
        "probabilidade": 0.9,
        "atraso": 0.0,
    }
    recebidas: list[dict[str, Any]] = []

    @app.post("/predict")
    def prever():  # type: ignore[no-untyped-def]
        recebidas.append(
            {
                "campos": sorted(requisicao_flask.files),
                "cabecalhos": dict(requisicao_flask.headers),
            }
        )
        if estado["atraso"]:
            time.sleep(float(estado["atraso"]))
        if estado["corpo"] is not None:
            return estado["corpo"], estado["status"]
        if "image" not in requisicao_flask.files:
            return jsonify({"error": "Campo 'image' e obrigatorio"}), 400

        probabilidade = float(estado["probabilidade"])
        classe = "Pneumonia" if probabilidade > 0.5 else "Normal"
        confianca = probabilidade if probabilidade > 0.5 else 1 - probabilidade
        return jsonify({"class": classe, "confidence": round(confianca * 100, 2)})

    servidor = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        yield ServicoDeVisaoFalso(
            url=f"http://127.0.0.1:{servidor.server_port}",
            estado=estado,
            recebidas=recebidas,
        )
    finally:
        servidor.shutdown()
        thread.join(timeout=10)


@pytest.fixture
def servico_de_visao_falso(
    _servidor_de_visao_compartilhado: ServicoDeVisaoFalso,
) -> ServicoDeVisaoFalso:
    """Servico falso **reiniciado** para este teste (o servidor e compartilhado)."""
    _servidor_de_visao_compartilhado.reiniciar()
    return _servidor_de_visao_compartilhado


def imagem_de_teste(*, tamanho: int = 512) -> bytes:
    """Bytes deterministicos que fingem ser uma radiografia (nunca decodificados).

    Devolve **exatamente** ``tamanho`` bytes — os testes comparam o tamanho persistido.
    """
    base = b"\xff\xd8\xff\xe0" + bytes(range(256)) * (tamanho // 256 + 1)
    return base[:tamanho]


def analisar_imagem(
    ambiente: AmbienteClinico,
    *,
    conteudo: bytes | None = None,
    nome: str = "radiografia.jpg",
    mime: str = "image/jpeg",
    id_paciente: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Executa ``POST /imagens`` e devolve ``{status_code, corpo}``."""
    arquivos = {"imagem": (nome, conteudo if conteudo is not None else imagem_de_teste(), mime)}
    dados = {"id_paciente": id_paciente} if id_paciente is not None else None
    resposta = ambiente.cliente.post(
        "/api/v1/imagens",
        files=arquivos,
        data=dados,
        headers=cabecalho(token or ambiente.token),
    )
    return {"status_code": resposta.status_code, "corpo": resposta.json()}


def avaliar_paciente(
    ambiente: AmbienteClinico,
    id_paciente: str,
    features: dict[str, float],
    *,
    origem_dos_dados: str = "manual",
    modo: str = "simulado",
    token: str | None = None,
) -> dict[str, Any]:
    """Executa ``POST /avaliacoes`` e devolve ``{status_code, corpo}``."""
    resposta = ambiente.cliente.post(
        "/api/v1/avaliacoes",
        json={
            "id_paciente": id_paciente,
            "features": features,
            "origem_dos_dados": origem_dos_dados,
            "modo": modo,
        },
        headers=cabecalho(token or ambiente.token),
    )
    return {"status_code": resposta.status_code, "corpo": resposta.json()}


#: Caminho candidato da Fase 6 dentro do workspace.
PASTA_DA_FASE_6_REAL = CANDIDATO_FASE_6


@pytest.fixture(scope="session")
def pasta_da_fase_6_real() -> Path:
    """Pasta real da Fase 6 (o codigo, nao um diretorio temporario).

    Os testes de integracao precisam do pacote ``cardioia`` de verdade. Quando ele nao
    estiver presente, o teste e **pulado com motivo explicito** — em vez de falhar por
    ambiente, o que esconderia a causa.
    """
    if not (PASTA_DA_FASE_6_REAL / "src" / "cardioia").is_dir():
        pytest.skip(f"codigo da Fase 6 nao encontrado em '{PASTA_DA_FASE_6_REAL}'.")
    return PASTA_DA_FASE_6_REAL


@pytest.fixture(scope="session")
def configuracao_com_fase_6_real(pasta_da_fase_6_real: Path) -> Configuracoes:
    """Configuracao apontando para a Fase 6 real (banco em memoria, sem aquecer)."""
    return _configuracao_base(str(pasta_da_fase_6_real))


@pytest.fixture(scope="session")
def modulos_da_fase_6(configuracao_com_fase_6_real: Configuracoes) -> ModulosDaFase6:
    """Modulos da Fase 6 importados **uma vez por sessao**.

    Importar o pipeline custa ~5 s (puxa ``agents``, ``pandas`` e ``scikit-learn``).
    Sendo fixture de sessao, esse custo e pago uma unica vez, e nao por teste.
    """
    return importar(configuracao_com_fase_6_real)


@pytest.fixture(scope="session")
def artefato_do_modelo(configuracao_com_fase_6_real: Configuracoes) -> ArtefatoDoModelo:
    """Artefato do modelo carregado uma vez por sessao (~0,3 s)."""
    return CacheDoModelo().obter(configuracao_com_fase_6_real)


@pytest.fixture
def features_do_paciente_da_aula() -> dict[str, float]:
    """Features do paciente da aula (mesmos valores de ``FEATURES_DO_PACIENTE_DA_AULA``)."""
    return dict(FEATURES_DO_PACIENTE_DA_AULA)


@pytest.fixture
def dados_do_pipeline() -> dict[str, object]:
    """Itens do ``RespostaDaExecucao`` (Fase 6) no formato aceito pelo repositorio."""
    return {
        "diagnostico": {
            "probabilidade_risco": 0.9900,
            "pico_risco_previsto": 1,
            "classificacao_risco": "pico_de_risco",
            "modelo_utilizado": "Random Forest",
            "classe_do_estimador": "RandomForestClassifier",
            "limiar_decisao": 0.5,
            "regra_de_decisao": "probabilidade_risco >= limiar (0.5)",
            "origem_do_modelo": {"sha256_da_base_usada": "a" * 64},
        },
        "protocolos": [
            {
                "ordem": 2,
                "identificador": "carga_do_sistema",
                "texto_oficial": "Se carga do sistema > 85% -> abrir unidades temporarias",
                "acao": "abrir unidades temporarias",
                "condicao_satisfeita": "carga_sistema > 85",
                "operador": ">",
                "limiar": 85.0,
                "valor_observado": 92.0,
                "origem_do_valor": "paciente",
                "usa_modelo": False,
            }
        ],
        "indicadores": [
            {
                "nome": "carga_sistema > 80",
                "coluna": "carga_sistema",
                "operador": ">",
                "limiar": 80.0,
                "valor_observado": 92.0,
                "satisfeito": True,
                "origem": "paciente",
            }
        ],
        "passos": [
            {
                "ordem": 1,
                "tipo": "handoff",
                "agente": "Orquestrador",
                "detalhe": "handoff de 'Orquestrador' para 'Analista de Risco'",
                "sucesso": True,
            }
        ],
        "avisos": [],
        "erros": [],
        "agente_final": "Planejador de Resposta",
        "versao_do_sdk": "0.18.1",
        "duracao_segundos": 0.42,
    }
