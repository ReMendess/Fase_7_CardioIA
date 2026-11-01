"""Criacao e versionamento do esquema do banco (``MODELO_DADOS.md`` §7, §9 C10).

**Por que nao ha ``alembic``:** ele nao esta instalado neste ambiente (verificado).
A estrategia aprovada e ``create_all()`` + **controle de versao em tabela**, com o
historico registrado em codigo (:data:`HISTORICO`) e um ponto de entrada executavel::

    python -m app.dados.esquema                 # cria o que faltar
    python -m app.dados.esquema --recriar       # APAGA e recria (desenvolvimento)
    python -m app.dados.esquema --verificar     # falha se a versao divergir

Quando o projeto avancar, a migracao para ``alembic`` e direta: o metadata ja esta
centralizado em :class:`app.dados.base.Base`.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import Engine, func, inspect, select

from . import modelos  # noqa: F401 - importa as tabelas para registra-las no metadata
from .base import Base, agora_utc, criar_engine, criar_fabrica_de_sessoes
from .modelos import VersaoDoEsquema

__all__ = [
    "HISTORICO",
    "VERSAO_ATUAL",
    "EsquemaIncompativelError",
    "criar_esquema",
    "preparar_banco",
    "recriar_esquema",
    "versao_registrada",
]

#: Versao corrente do esquema.
VERSAO_ATUAL = 1

#: Historico das versoes (versao, descricao). Anexar ao evoluir o esquema.
HISTORICO: tuple[tuple[int, str], ...] = (
    (1, "Esquema inicial: 12 tabelas de dominio + 1 de controle tecnico (Etapa C, item 2)"),
)


class EsquemaIncompativelError(Exception):
    """O banco esta em uma versao de esquema diferente da esperada."""


def _descricao(versao: int) -> str:
    return dict(HISTORICO).get(versao, f"versao {versao} (sem descricao registrada)")


def versao_registrada(engine: Engine) -> int | None:
    """Maior versao registrada na tabela de controle.

    Returns:
        A versao, ou ``None`` quando a tabela ainda nao existe (banco novo).
    """
    if VersaoDoEsquema.__tablename__ not in inspect(engine).get_table_names():
        return None

    fabrica = criar_fabrica_de_sessoes(engine)
    with fabrica() as sessao:
        return sessao.scalar(select(func.max(VersaoDoEsquema.versao)))


def _registrar_versao(engine: Engine, versao: int) -> None:
    """Grava a versao na tabela de controle (idempotente)."""
    fabrica = criar_fabrica_de_sessoes(engine)
    with fabrica() as sessao:
        if sessao.get(VersaoDoEsquema, versao) is None:
            sessao.add(
                VersaoDoEsquema(
                    versao=versao, descricao=_descricao(versao), aplicada_em=agora_utc()
                )
            )
            sessao.commit()


def criar_esquema(engine: Engine) -> int:
    """Cria as tabelas que faltarem e registra a versao corrente.

    Idempotente: ``create_all`` nao altera tabelas existentes.
    """
    Base.metadata.create_all(engine)
    _registrar_versao(engine, VERSAO_ATUAL)
    return VERSAO_ATUAL


def recriar_esquema(engine: Engine) -> int:
    """**Apaga** todas as tabelas e recria do zero.

    ⚠️ Destrutivo — uso exclusivo em desenvolvimento/testes.
    """
    Base.metadata.drop_all(engine)
    return criar_esquema(engine)


def preparar_banco(engine: Engine) -> int:
    """Cria o esquema e valida a versao — chamado na inicializacao do servico.

    Raises:
        EsquemaIncompativelError: o banco esta em versao diferente da esperada
            (ex.: arquivo antigo que precisa de migracao).
    """
    registrada = versao_registrada(engine)
    Base.metadata.create_all(engine)

    if registrada is None:
        _registrar_versao(engine, VERSAO_ATUAL)
        return VERSAO_ATUAL

    if registrada != VERSAO_ATUAL:
        raise EsquemaIncompativelError(
            f"Banco na versao {registrada}, esperada {VERSAO_ATUAL}. "
            "Este MVP nao aplica migracoes automaticas: recrie o banco de "
            "desenvolvimento com 'python -m app.dados.esquema --recriar' ou "
            "escreva um script de migracao versionado."
        )

    return registrada


# --------------------------------------------------------------------------- #
# Ponto de entrada executavel
# --------------------------------------------------------------------------- #


def construir_analisador_de_argumentos() -> argparse.ArgumentParser:
    """Argumentos da CLI de esquema."""
    analisador = argparse.ArgumentParser(
        prog="python -m app.dados.esquema",
        description=(
            "Cria/valida o esquema do banco do CardioIA (Fase 7). "
            "Sem 'alembic': a versao fica registrada na tabela 'versoes_do_esquema'."
        ),
    )
    analisador.add_argument(
        "--database-url",
        default=None,
        help="URL do SQLAlchemy. Padrao: DATABASE_URL do ambiente/.env.",
    )
    analisador.add_argument(
        "--recriar",
        action="store_true",
        help="APAGA todas as tabelas e recria do zero (destrutivo).",
    )
    analisador.add_argument(
        "--verificar",
        action="store_true",
        help="Apenas verifica a versao registrada, sem criar nada.",
    )
    return analisador


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI. Retorna 0 em sucesso, 1 em falha."""
    argumentos = construir_analisador_de_argumentos().parse_args(argv)

    from ..config import Configuracoes, ErroDeConfiguracao

    try:
        config = Configuracoes()
        config.validar()
    except ErroDeConfiguracao as erro:
        print(f"[erro] {erro}", file=sys.stderr)
        return 1

    url = argumentos.database_url or config.url_do_banco
    engine = criar_engine(url)

    try:
        if argumentos.verificar:
            registrada = versao_registrada(engine)
            if registrada is None:
                print("[erro] esquema nao criado (tabela de controle ausente).", file=sys.stderr)
                return 1
            if registrada != VERSAO_ATUAL:
                print(
                    f"[erro] banco na versao {registrada}; esperada {VERSAO_ATUAL}.",
                    file=sys.stderr,
                )
                return 1
            print(f"[ok] esquema na versao {registrada}.")
            return 0

        if argumentos.recriar:
            versao = recriar_esquema(engine)
            print(f"[ok] esquema recriado na versao {versao} ({url}).")
            return 0

        versao = preparar_banco(engine)
        print(f"[ok] esquema pronto na versao {versao} ({url}).")
        return 0
    except EsquemaIncompativelError as erro:
        print(f"[erro] {erro}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":  # pragma: no cover - execucao via linha de comando
    raise SystemExit(main())