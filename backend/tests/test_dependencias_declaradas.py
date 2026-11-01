"""Toda dependencia de terceiro importada pelo codigo esta declarada no requirements.txt?

Por que este teste existe: localmente os pacotes ja estao instalados, entao um `import`
que funciona aqui pode **falhar no servidor**. Foi exatamente o que aconteceu —
`openai-agents` e `openai` nao estavam declarados, e `POST /avaliacoes` respondia
`503 MODELO_INDISPONIVEL` no ambiente publicado, sem nenhum teste acusar.

O teste percorre os imports reais do backend e da Fase 6 e confere cada um contra o
`requirements.txt`. Ele roda no CI/local e quebra assim que alguem adicionar um import
sem declarar o pacote.
"""

from __future__ import annotations

import ast
import pathlib
import sys
from importlib.metadata import packages_distributions

RAIZ_DO_BACKEND = pathlib.Path(__file__).resolve().parent.parent
RAIZ_DA_FASE_7 = RAIZ_DO_BACKEND.parent

#: Pastas cujo codigo roda em producao.
PASTAS = (
    RAIZ_DO_BACKEND / "app",
    RAIZ_DA_FASE_7 / "Fase_6" / "cardioia_Fase6" / "src",
)

#: Pacotes do proprio projeto (nao vem do PyPI).
LOCAIS = {"app", "cardioia", "tests", "conftest"}

#: Dependencias **transitivas**: vem junto com outro pacote declarado. Listadas aqui de
#: forma explicita para que a ausencia delas no requirements.txt seja uma decisao
#: consciente, e nao um esquecimento.
TRANSITIVAS = {
    "starlette",  # vem com o fastapi
}


def _imports_de(caminho: pathlib.Path) -> set[str]:
    """Nomes de topo importados por um arquivo (ignora imports relativos)."""
    try:
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - arquivo ilegivel
        return set()

    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(alias.name.split(".")[0] for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            nomes.add(no.module.split(".")[0])
    return nomes


def _declaradas() -> set[str]:
    """Nomes de distribuicao declarados no requirements.txt, normalizados."""
    linhas = (RAIZ_DO_BACKEND / "requirements.txt").read_text(encoding="utf-8").splitlines()
    nomes: set[str] = set()
    for linha in linhas:
        limpa = linha.strip()
        if not limpa or limpa.startswith("#") or "==" not in limpa:
            continue
        nomes.add(limpa.split("==")[0].strip().lower().replace("-", "_"))
    return nomes


def _imports_de_terceiros() -> set[str]:
    """Imports que nao sao stdlib nem pacote do proprio projeto."""
    encontrados: set[str] = set()
    for pasta in PASTAS:
        for arquivo in pasta.rglob("*.py"):
            encontrados |= _imports_de(arquivo)

    return {
        nome
        for nome in encontrados
        if nome not in sys.stdlib_module_names
        and nome not in LOCAIS
        and not nome.startswith("_")
    }


def test_todo_import_de_terceiro_esta_declarado() -> None:
    """O requirements.txt cobre tudo o que o codigo importa."""
    mapa = packages_distributions()
    declaradas = _declaradas()

    faltando: list[str] = []
    for modulo in sorted(_imports_de_terceiros()):
        if modulo in TRANSITIVAS:
            continue
        distribuidoras = mapa.get(modulo)
        if not distribuidoras:
            # Instalado de forma que o `importlib.metadata` nao mapeia: sinaliza para
            # revisao manual em vez de passar em silencio.
            faltando.append(f"{modulo} (distribuicao nao identificada)")
            continue
        if not any(d.lower().replace("-", "_") in declaradas for d in distribuidoras):
            faltando.append(f"{modulo} (pacote: {distribuidoras[0]})")

    assert not faltando, (
        "Estas dependencias sao importadas pelo codigo mas NAO estao no requirements.txt. "
        "No deploy elas faltarao:\n  - " + "\n  - ".join(faltando)
    )


def test_requirements_declara_o_pipeline_da_fase_6() -> None:
    """Regressao: sem estas, `POST /avaliacoes` responde 503 no ambiente publicado.

    O `cardioia.agents.orchestrator` importa o SDK no topo do modulo — o pipeline precisa
    dele **mesmo no modo simulado**.
    """
    declaradas = _declaradas()

    for pacote in ("openai_agents", "openai", "scikit_learn", "pandas", "numpy", "joblib"):
        assert pacote in declaradas, f"{pacote} ausente do requirements.txt"


def test_requirements_declara_o_adaptador_do_watson() -> None:
    """Sem o SDK, o caminho do Watson falharia com ImportError em vez de atender."""
    declaradas = _declaradas()

    assert "ibm_watson" in declaradas
    assert "ibm_cloud_sdk_core" in declaradas


def test_requirements_declara_o_upload_multipart() -> None:
    """`python-multipart` e exigido pelo FastAPI para `File(...)` — `POST /imagens`."""
    assert "python_multipart" in _declaradas()
