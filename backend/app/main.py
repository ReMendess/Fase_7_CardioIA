"""Aplicacao FastAPI do backend central do CardioIA (Fase 7).

Responsabilidades deste modulo (Etapa C, item 1):

1. **falha rapida** de configuracao — o servico nao sobe sem ``JWT_SECRET`` valido
   (``PLANO_SEGURANCA.md``);
2. registrar o **envelope unico** ``RespostaAPI[T]`` em toda resposta, inclusive
   nos erros (nada de ``{"detail": ...}`` fora do contrato);
3. traduzir excecoes para o **enum de erros** com o codigo HTTP canonico;
4. montar o CORS a partir da configuracao (nunca aberto por padrao).

Execucao local (a partir da pasta ``backend``)::

    python -m uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import NOME_DO_SERVICO, __versao__
from .config import Configuracoes, obter_configuracoes
from .contratos.envelope import RespostaAPI, StatusDaResposta, resposta_de_erro
from .contratos.erros import (
    CodigoDeErro,
    ErroDaAPI,
    ErroDaAPIException,
    codigo_do_http,
)
from .dados.base import criar_engine, criar_fabrica_de_sessoes
from .dados.esquema import EsquemaIncompativelError, preparar_banco
from .integracao.modelo import CacheDoModelo
from .rotas import assistente, auth, avaliacoes, imagens, iot, pacientes, saude
from .seguranca.limite_de_tentativas import LimitadorDeTentativas

registrador = logging.getLogger("cardioia.backend")

DESCRICAO = (
    "Backend central do CardioIA (Fase 7). Integra as Fases 3 (IoT), 4 (visao "
    "computacional), 5 (assistente) e 6 (pipeline multiagente + modelo de risco) "
    "sob um contrato unico.\n\n"
    "**Aviso:** os dados do projeto sao SINTETICOS e nao ha validacao clinica. "
    "Nenhum resultado constitui diagnostico, prescricao ou recomendacao medica."
)


# --------------------------------------------------------------------------- #
# Utilitarios de resposta
# --------------------------------------------------------------------------- #


def _metadados(config: Configuracoes, origem: str) -> dict[str, Any]:
    """Metadados padrao do envelope (sem segredos)."""
    return {"versao_api": config.versao_api, "origem": origem}


def _resposta_json(
    envelope: RespostaAPI[Any], http: int, *, cabecalhos: dict[str, str] | None = None
) -> JSONResponse:
    """Serializa o envelope no codigo HTTP indicado."""
    return JSONResponse(
        status_code=http, content=envelope.como_dicionario(), headers=cabecalhos
    )


def _campo_do_erro(exc: RequestValidationError) -> str | None:
    """Extrai o nome do campo culpado a partir do primeiro erro de validacao."""
    for erro in exc.errors():
        local = [
            parte for parte in erro.get("loc", ()) if parte not in ("body", "query", "path")
        ]
        if local:
            return ".".join(str(parte) for parte in local)
    return None


def _config_do_request(request: Request) -> Configuracoes:
    """Configuracao associada a aplicacao (com fallback seguro)."""
    config = getattr(request.app.state, "configuracoes", None)
    return config if isinstance(config, Configuracoes) else obter_configuracoes()


# --------------------------------------------------------------------------- #
# Handlers de erro — todos devolvem o envelope comum
# --------------------------------------------------------------------------- #


def _registrar_handlers(app: FastAPI) -> None:
    """Registra os handlers que mantem o contrato de erro uniforme."""

    @app.exception_handler(ErroDaAPIException)
    async def _tratar_erro_da_api(request: Request, exc: ErroDaAPIException) -> JSONResponse:
        """Excecao de dominio ja tipada (codigo + mensagem originais)."""
        config = _config_do_request(request)
        registrador.warning("ErroDaAPIException: %s (%s)", exc.codigo.value, exc.mensagem)
        # 401 exige o cabecalho WWW-Authenticate (RFC 9110) para o cliente saber o esquema.
        cabecalhos = (
            {"WWW-Authenticate": "Bearer"}
            if exc.http == 401
            else None
        )
        return _resposta_json(
            resposta_de_erro([exc.erro], metadados=_metadados(config, NOME_DO_SERVICO)),
            exc.http,
            cabecalhos=cabecalhos,
        )

    @app.exception_handler(RequestValidationError)
    async def _tratar_contrato_violado(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Payload/parametro fora do contrato -> ``CONTRATO_VIOLADO`` (422)."""
        config = _config_do_request(request)
        erros = exc.errors()
        erro = ErroDaAPI(
            codigo=CodigoDeErro.CONTRATO_VIOLADO,
            mensagem="Requisicao fora do contrato da API.",
            campo=_campo_do_erro(exc),
            detalhe=str(erros[0].get("msg")) if erros else None,
        )
        return _resposta_json(
            resposta_de_erro([erro], metadados=_metadados(config, NOME_DO_SERVICO)), 422
        )

    @app.exception_handler(StarletteHTTPException)
    async def _tratar_http_do_starlette(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Erros do proprio framework (404, 405, ...) no envelope comum."""
        config = _config_do_request(request)
        erro = ErroDaAPI(
            codigo=codigo_do_http(exc.status_code),
            mensagem=str(exc.detail) if exc.detail else "Falha no processamento da requisicao.",
        )
        return _resposta_json(
            resposta_de_erro([erro], metadados=_metadados(config, NOME_DO_SERVICO)),
            exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _tratar_inesperado(request: Request, exc: Exception) -> JSONResponse:
        """Falha nao prevista -> ``ERRO_INTERNO`` (nunca falha silenciosa)."""
        config = _config_do_request(request)
        registrador.exception("Falha inesperada: %s", type(exc).__name__)
        erro = ErroDaAPI(
            codigo=CodigoDeErro.ERRO_INTERNO,
            mensagem="Falha inesperada no servidor.",
            detalhe=type(exc).__name__,
        )
        return _resposta_json(
            resposta_de_erro(
                [erro],
                status=StatusDaResposta.ERRO,
                metadados=_metadados(config, NOME_DO_SERVICO),
            ),
            500,
        )


# --------------------------------------------------------------------------- #
# Fabrica da aplicacao
# --------------------------------------------------------------------------- #


def _semear_conta_de_demonstracao(app: FastAPI, config: Configuracoes) -> None:
    """Cria a conta de demonstracao quando o banco ainda nao tem nenhum usuario.

    Por que existe: hospedagem gratuita costuma ter sistema de arquivos **efemero** — o
    SQLite volta vazio a cada reinicio, e sem usuario nao ha como entrar na aplicacao
    publicada. Semear aqui torna o servico auto-suficiente.

    E **idempotente**: se ja houver qualquer usuario, nao faz nada. Assim nao sobrescreve
    senha nem recria conta removida de proposito.
    """
    if not config.semear_usuario_inicial:
        return

    fabrica = getattr(app.state, "fabrica_de_sessoes", None)
    if fabrica is None:
        return

    # Import tardio: mantem o import de `app.main` barato.
    from .dados.enums import PapelDoUsuario
    from .dados.repositorios.identidade import UsuarioRepositorio
    from .seguranca.senhas import gerar_hash

    try:
        papel = PapelDoUsuario(config.usuario_inicial_papel.strip().upper())
    except ValueError:
        registrador.error(
            "USUARIO_INICIAL_PAPEL invalido (%r) — conta de demonstracao nao criada",
            config.usuario_inicial_papel,
        )
        return

    with fabrica() as sessao:
        repositorio = UsuarioRepositorio(sessao)
        if repositorio.listar(limite=1):
            return
        try:
            usuario = repositorio.criar(
                nome=config.usuario_inicial_nome,
                email=config.usuario_inicial_email,
                senha_hash=gerar_hash(config.usuario_inicial_senha),
                papel=papel,
            )
        except ErroDaAPIException as erro:
            # Conta ja existe com outro formato de e-mail, por exemplo: nao derruba o boot.
            registrador.warning("conta de demonstracao nao criada: %s", erro.mensagem)
            return

    registrador.info(
        "conta de demonstracao criada | email=%s | papel=%s | id=%s",
        usuario.email,
        usuario.papel.value,
        usuario.id,
    )


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    """Prepara o banco na inicializacao e libera o engine no encerramento.

    A criacao do esquema fica **aqui** (e nao no import do modulo) de proposito:
    importar ``app.main`` nao deve ter efeito colateral em disco — do contrario, um
    simples ``import`` criaria o arquivo do banco. A preparacao roda quando o servidor
    sobe (e nos testes, ao usar ``with TestClient(app)``).

    Raises:
        EsquemaIncompativelError: banco em versao diferente da esperada — o servidor
            **nao sobe** em vez de operar com esquema divergente.
    """
    engine: Engine | None = getattr(app.state, "engine", None)
    config: Configuracoes = app.state.configuracoes

    if engine is not None:
        try:
            versao = preparar_banco(engine)
        except EsquemaIncompativelError as erro:
            registrador.error("esquema incompativel — servidor nao iniciado: %s", erro)
            raise
        registrador.info(
            "banco preparado | versao_do_esquema=%s | url=%s", versao, config.url_do_banco
        )
        _semear_conta_de_demonstracao(app, config)

    # Cache do modelo (M3). Best-effort de proposito: se o artefato ou o SDK falharem, o
    # servidor **sobe** (M1) e a requisicao que precisar do modelo reporta o erro.
    # Executado em thread (`to_thread`): o import do pipeline leva ~6 s e bloquearia o
    # event loop se rodasse direto no lifespan.
    cache: CacheDoModelo | None = getattr(app.state, "cache_do_modelo", None)
    if cache is not None and config.aquecer_modelo_no_startup:
        if await asyncio.to_thread(cache.aquecer, config):
            registrador.info("cache do modelo aquecido | pasta=%s", config.pasta_da_fase_6)
    elif cache is not None:
        registrador.info(
            "cache do modelo NAO aquecido no startup (AQUECER_MODELO_NO_STARTUP=false)"
        )

    try:
        yield
    finally:
        if engine is not None:
            engine.dispose()


def criar_app(configuracoes: Configuracoes | None = None) -> FastAPI:
    """Monta a aplicacao FastAPI.

    Args:
        configuracoes: configuracao explicita (util em testes). Quando ``None``,
            le do ambiente/``.env`` via :func:`obter_configuracoes`.

    Raises:
        ErroDeConfiguracao: configuracao obrigatoria ausente ou insegura.
    """
    config = configuracoes if configuracoes is not None else obter_configuracoes()
    config.validar()  # falha rapida: sem JWT_SECRET valido o servico nao sobe

    app = FastAPI(
        title="CardioIA — backend central (Fase 7)",
        version=__versao__,
        description=DESCRICAO,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=_ciclo_de_vida,
    )
    app.state.configuracoes = config
    app.state.nome_do_servico = NOME_DO_SERVICO

    # Banco: o engine e criado agora (nao abre conexao nem cria arquivo); o esquema
    # e preparado no lifespan.
    engine = criar_engine(config.url_do_banco)
    app.state.engine = engine
    app.state.fabrica_de_sessoes = criar_fabrica_de_sessoes(engine)

    # Limitador de tentativas de login (em memoria — limitacao declarada no modulo).
    app.state.limitador_de_tentativas = LimitadorDeTentativas()

    # Cache do artefato do modelo da Fase 6 (item 4). Criado aqui — **sem carregar
    # nada**; a carga acontece no lifespan ou na primeira requisicao que precisar.
    app.state.cache_do_modelo = CacheDoModelo()

    # CORS restrito. Credenciais desabilitadas: o token viaja no header
    # Authorization, nao em cookie (ver MODELO_DADOS.md §6).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.origens_cors,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    _registrar_handlers(app)
    app.include_router(saude.router, prefix=config.prefixo_das_rotas)
    app.include_router(auth.router, prefix=config.prefixo_das_rotas)
    app.include_router(pacientes.router, prefix=config.prefixo_das_rotas)
    app.include_router(avaliacoes.router, prefix=config.prefixo_das_rotas)
    app.include_router(iot.router, prefix=config.prefixo_das_rotas)
    app.include_router(imagens.router, prefix=config.prefixo_das_rotas)
    app.include_router(assistente.router, prefix=config.prefixo_das_rotas)

    registrador.info(
        "backend iniciado | ambiente=%s | prefixo=%s | pasta_fase_6=%s | integracoes=%s",
        config.ambiente,
        config.prefixo_das_rotas,
        config.pasta_da_fase_6,
        config.integracoes_configuradas,
    )
    return app


#: Instancia usada pelo servidor ASGI (``uvicorn app.main:app``).
app = criar_app()


__all__ = ["DESCRICAO", "NOME_DO_SERVICO", "app", "criar_app"]
