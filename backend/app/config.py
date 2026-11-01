"""Configuracao central do backend CardioIA (Fase 7).

Principios (ver ``PLANO_SEGURANCA.md``):

- **segredos vem SOMENTE de variavel de ambiente / arquivo ``.env``** — nenhum valor
  default de segredo e definido aqui;
- **falha rapida**: ``validar()`` levanta :class:`ErroDeConfiguracao` quando um
  parametro obrigatorio esta ausente ou invalido, de modo que o servico **nao sobe**
  com configuracao insegura;
- caminhos sao resolvidos **relativamente ao backend**, nunca por caminho absoluto
  da maquina (mesmo principio usado na Fase 6).

Nada aqui importa a Fase 6: a integracao com o pacote ``cardioia`` acontece no
item 4 da Etapa C (import tardio).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# --------------------------------------------------------------------------- #
# Caminhos base (sem caminho absoluto da maquina)
# --------------------------------------------------------------------------- #

RAIZ_DO_BACKEND: Path = Path(__file__).resolve().parent.parent
RAIZ_DA_FASE_7: Path = RAIZ_DO_BACKEND.parent

#: Caminho candidato da Fase 6 dentro da estrutura do workspace.
CANDIDATO_FASE_6: Path = RAIZ_DA_FASE_7 / "Fase_6" / "cardioia_Fase6"

#: Caminho candidato do servico de visao (Fase 4).
CANDIDATO_FASE_4: Path = (
    RAIZ_DA_FASE_7 / "Fase_4" / "Fase_4_Cap1" / "Ir_Alem2" / "backend"
)

#: Caminho candidato do servico legado da Fase 3 (``Ir_Alem1/server.py``).
#: Usado apenas como **fonte normativa** das regras de telemetria (nao e executado em
#: producao — o servico Flask foi desativado; ver ``app/regras_iot.py``).
CANDIDATO_FASE_3: Path = (
    RAIZ_DA_FASE_7 / "Fase_3" / "Cap_1_CardioIA_Conectada" / "Ir_Alem1"
)

#: Caminho candidato do backend da Fase 5 (``IBM_API.py`` e ``app.py``).
#: Usado apenas como **fonte normativa** do assistente: o backend **nao** importa esses
#: modulos (ver ``app/integracao/fase_5.py`` — eles trazem a chave real como default).
CANDIDATO_FASE_5: Path = RAIZ_DA_FASE_7 / "Fase_5" / "Fase5_CardioAssist" / "Backend"

#: Tamanho minimo do segredo de assinatura (HS256 = 256 bits).
TAMANHO_MINIMO_DO_SEGREDO = 32


class ErroDeConfiguracao(Exception):
    """Configuracao obrigatoria ausente ou invalida — o servico nao deve subir."""


class Configuracoes(BaseSettings):
    """Parametros de execucao do backend, lidos do ambiente e do ``.env``."""

    model_config = SettingsConfigDict(
        env_file=RAIZ_DO_BACKEND / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------ #
    # Identificacao
    # ------------------------------------------------------------------ #
    ambiente: str = Field(default="desenvolvimento", description="desenvolvimento|teste|producao")
    versao_api: str = Field(default="v1", description="Versao exposta no prefixo das rotas.")

    # ------------------------------------------------------------------ #
    # Servidor
    # ------------------------------------------------------------------ #
    host: str = Field(default="127.0.0.1")
    porta: int = Field(default=8000, ge=1, le=65535)

    # ------------------------------------------------------------------ #
    # Seguranca — SEM default de valor real
    # ------------------------------------------------------------------ #
    jwt_secret: str = Field(default="", description="Obrigatorio. Vazio = ausente.")
    jwt_algoritmo: str = Field(default="HS256")
    access_token_minutos: int = Field(default=30, ge=1, le=1440)
    refresh_token_dias: int = Field(default=7, ge=1, le=365)

    # ------------------------------------------------------------------ #
    # Persistencia (item 2 da Etapa C)
    # ------------------------------------------------------------------ #
    database_url: str = Field(default="sqlite:///./cardioia.db")

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #
    # Origens do frontend web (Etapa D). Os dois nomes de host entram de proposito: o
    # Vite pode servir em `localhost` **ou** em `127.0.0.1`, e o navegador trata os dois
    # como origens **diferentes** — sem ambos, o app abre mas todas as chamadas sao
    # bloqueadas pelo CORS. 5173 = Vite; 8081 = Expo web (Fase 5).
    cors_origens: str = Field(
        default=(
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:8081,http://127.0.0.1:8081"
        )
    )

    # ------------------------------------------------------------------ #
    # Integracoes (caminhos e URLs — nao sao segredos)
    # ------------------------------------------------------------------ #
    pasta_fase_6: str = Field(default="", description="Vazio = descoberta automatica.")
    servico_visao_url: str = Field(default="http://localhost:5001")
    servico_visao_token: str = Field(
        default="",
        description=(
            "Token de servico enviado como X-Service-Token ao servico da Fase 4 "
            "(DECISOES_ARQUITETURAIS.md §4.3). Opcional: o servico legado nao valida nada "
            "hoje; o cabecalho existe para quando houver proxy autenticado na frente."
        ),
    )
    servico_visao_timeout_segundos: float = Field(
        default=30.0,
        gt=0,
        le=300,
        description=(
            "Prazo da chamada ao servico de visao. Generoso de proposito: o primeiro "
            "predict carrega o TensorFlow e pode levar dezenas de segundos."
        ),
    )
    watson_timeout_segundos: float = Field(
        default=30.0,
        gt=0,
        le=300,
        description=(
            "Prazo da chamada ao Watson Assistant (mesmo valor de WATSON_TIMEOUT na Fase 5)."
        ),
    )
    limite_de_upload_mb: int = Field(
        default=10,
        ge=1,
        le=100,
        description=(
            "Tamanho maximo de upload de imagem, em MB. Exceder devolve "
            "413 LIMITE_EXCEDIDO (CONTRATOS_API.md §4.6 sugere 10 MB)."
        ),
    )

    # ------------------------------------------------------------------ #
    # Integracao com a Fase 6 (item 4 da Etapa C)
    # ------------------------------------------------------------------ #
    aquecer_modelo_no_startup: bool = Field(
        default=True,
        description=(
            "Carrega o artefato do modelo na inicializacao (M3). Best-effort: se falhar, "
            "o servidor sobe normalmente e o erro aparece na requisicao que precisar do "
            "modelo. Desligue em teste para nao pagar ~6 s de import por aplicacao."
        ),
    )

    # ------------------------------------------------------------------ #
    # Telemetria IoT (item 5 da Etapa C)
    # ------------------------------------------------------------------ #
    iot_device_key: str = Field(
        default="",
        description=(
            "Chave compartilhada dos dispositivos IoT (cabecalho X-Device-Key). Vazio = "
            "desabilitada: a ingestao passa a exigir usuario com papel OPERADOR. "
            "SEGREDO: nunca versione o valor; use IOT_DEVICE_KEY no .env."
        ),
    )

    # ------------------------------------------------------------------ #
    # Credenciais de servicos externos (sem valores default)
    # ------------------------------------------------------------------ #
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")
    watson_api_key: str = Field(default="")
    watson_service_url: str = Field(default="")
    watson_assistant_id: str = Field(default="")
    watson_environment_id: str = Field(default="")

    # ------------------------------------------------------------------ #
    # Derivados
    # ------------------------------------------------------------------ #

    @property
    def prefixo_das_rotas(self) -> str:
        """Prefixo versionado das rotas (ex.: ``/api/v1``)."""
        return f"/api/{self.versao_api}"

    @property
    def origens_cors(self) -> list[str]:
        """Origens do CORS, sem espacos e sem itens vazios."""
        return [origem.strip() for origem in self.cors_origens.split(",") if origem.strip()]

    @property
    def pasta_da_fase_6(self) -> Path:
        """Pasta da Fase 6: valor informado ou descoberta automatica."""
        if self.pasta_fase_6.strip():
            return Path(self.pasta_fase_6.strip()).expanduser()
        return CANDIDATO_FASE_6

    @property
    def url_do_banco(self) -> str:
        """``DATABASE_URL`` com caminho relativo resolvido contra a raiz do backend.

        Por que existe: ``sqlite:///./cardioia.db`` seria criado no **diretorio de
        trabalho** do processo — subir o servidor de pastas diferentes geraria bancos
        distintos, silenciosamente. Aqui o caminho relativo vira absoluto (raiz do
        backend), e URLs absolutas/nao-SQLite passam intactas.
        """
        url = self.database_url.strip()
        prefixo = "sqlite:///"
        if not url.startswith(prefixo):
            return url

        caminho = url[len(prefixo) :]
        # ':memory:' e caminhos absolutos (C:\... ou /...) nao sao reescritos.
        if not caminho or caminho.startswith(":memory:") or Path(caminho).is_absolute():
            return url

        return f"{prefixo}{(RAIZ_DO_BACKEND / caminho).resolve().as_posix()}"

    @property
    def caminho_do_modelo(self) -> Path:
        """Artefato ``.pkl`` do modelo de risco (Fase 6)."""
        return self.pasta_da_fase_6 / "models" / "modelo_pico_risco.pkl"

    @property
    def caminho_dos_metadados(self) -> Path:
        """Metadata do modelo de risco (features, faixas, versoes, SHA-256)."""
        return self.pasta_da_fase_6 / "models" / "modelo_pico_risco_metadata.json"

    @property
    def integracoes_configuradas(self) -> dict[str, bool]:
        """Quais integracoes externas possuem credencial/URL preenchida.

        Reporta apenas **presenca** — nenhum valor e exposto.
        """
        return {
            "openai": bool(self.openai_api_key.strip()),
            "watson": all(
                valor.strip()
                for valor in (
                    self.watson_api_key,
                    self.watson_service_url,
                    self.watson_assistant_id,
                    self.watson_environment_id,
                )
            ),
            "servico_de_visao": bool(self.servico_visao_url.strip()),
        }

    # ------------------------------------------------------------------ #
    # Validacao (falha rapida)
    # ------------------------------------------------------------------ #

    def validar(self) -> None:
        """Valida a configuracao. Levanta :class:`ErroDeConfiguracao` se insegura.

        Regras:

        1. ``JWT_SECRET`` **obrigatorio** — o servico nao sobe sem ele;
        2. segredo com menos de :data:`TAMANHO_MINIMO_DO_SEGREDO` caracteres e
           recusado (HS256 exige 256 bits);
        3. ``AMBIENTE=producao`` exige CORS restrito.
        """
        problemas: list[str] = []

        if not self.jwt_secret.strip():
            problemas.append(
                "JWT_SECRET nao definida. Copie '.env.example' para '.env' e gere um valor com:\n"
                '    python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        elif len(self.jwt_secret) < TAMANHO_MINIMO_DO_SEGREDO:
            problemas.append(
                f"JWT_SECRET tem {len(self.jwt_secret)} caracteres; o minimo e "
                f"{TAMANHO_MINIMO_DO_SEGREDO} (HS256 usa 256 bits)."
            )

        if self.jwt_algoritmo.strip().upper() != "HS256":
            problemas.append(
                f"JWT_ALGORITMO='{self.jwt_algoritmo}' nao suportado; use 'HS256'."
            )

        if self.ambiente.strip().lower() == "producao" and not self.origens_cors:
            problemas.append("CORS_ORIGENS vazio em producao (CORS aberto nao e permitido).")

        if problemas:
            detalhe = "\n".join(f"  - {item}" for item in problemas)
            raise ErroDeConfiguracao(
                "Configuracao invalida — o servico nao pode iniciar:\n" + detalhe
            )


@lru_cache(maxsize=1)
def obter_configuracoes() -> Configuracoes:
    """Configuracao em cache (uma leitura por processo)."""
    return Configuracoes()


__all__ = [
    "CANDIDATO_FASE_3",
    "CANDIDATO_FASE_4",
    "CANDIDATO_FASE_5",
    "CANDIDATO_FASE_6",
    "RAIZ_DA_FASE_7",
    "RAIZ_DO_BACKEND",
    "TAMANHO_MINIMO_DO_SEGREDO",
    "Configuracoes",
    "ErroDeConfiguracao",
    "obter_configuracoes",
]
