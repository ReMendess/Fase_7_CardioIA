"""Rotas de diagnostico por imagem (``CONTRATOS_API.md`` §8) — Fase 4 via HTTP.

| Metodo | Rota | Papel minimo | `dados` |
|---|---|---|---|
| `POST` | `/imagens` | `MEDICO` | `ResultadoDeDiagnostico` |

Decisoes que importam:

- **Servico isolado** (``DECISOES_ARQUITETURAIS.md`` §3.4, alternativa **C**): a Fase 4 roda
  em **processo separado** na porta **5001** e e consumida por HTTP. O backend **nao** importa
  TensorFlow (risco **R8**). Servico fora do ar → `502 ERRO_DE_SERVICO_DE_VISAO`.
- **A imagem nao e persistida** (``MODELO_DADOS.md`` §3.9): guardam-se o `hash_sha256`, o
  `mime`, o tamanho e o nome. Isso e dito ao cliente em `limitacoes`.
- **Endurecimento na borda** (``CONTRATOS_API.md`` §4.6): a Fase 4 aceita "qualquer arquivo
  que o Keras abra"; aqui o `content_type` e validado contra uma lista e o tamanho tem teto
  (`413 LIMITE_EXCEDIDO`).
- **`{class, confidence}` -> `{classe, confianca}` na borda** (nota **N4**), e os campos que
  a Fase 4 nao informa sao acrescentados a partir do conhecimento do artefato (nota **I9**).
"""

from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from ..config import Configuracoes
from ..contratos.envelope import RespostaAPI, resposta_de_sucesso
from ..contratos.erros import CodigoDeErro, ErroDaAPIException
from ..contratos.visao import LIMITACOES_DA_VISAO, MIMES_ACEITOS, ResultadoDeDiagnostico
from ..dados.base import get_sessao
from ..dados.enums import ClasseDeDiagnosticoDeImagem
from ..dados.repositorios.analises import AnaliseDeImagemRepositorio
from ..integracao.fase_4 import (
    AVISO_DE_USO_DA_VISAO,
    DIMENSOES_ESPERADAS_DA_IMAGEM,
    LIMIAR_DE_DECISAO_DA_VISAO,
    NOME_DO_MODELO_DA_VISAO,
    chamar_previsao,
)
from .apoio import (
    SomenteMedico,
    ip_do_cliente,
    metadados_da_resposta,
    registrar_auditoria,
)
from .pacientes import buscar_paciente_ou_falhar

__all__ = ["router"]

router = APIRouter(prefix="/imagens", tags=["visao-computacional"])

ACAO_ANALISE = "analisar_imagem"
ENTIDADE = "analises_de_imagem"

#: Margem sobre o limite de bytes para o *overhead* do ``multipart`` (cabecalhos + boundary).
#: Usada apenas na checagem previa por ``Content-Length``.
MARGEM_DO_MULTIPART_EM_BYTES = 1024 * 1024


def _limite_em_bytes(config: Configuracoes) -> int:
    """Teto de upload em bytes, a partir da configuracao."""
    return config.limite_de_upload_mb * 1024 * 1024


def _erro_de_limite(limite: int, config: Configuracoes) -> ErroDaAPIException:
    """Erro padronizado de upload grande demais (``413``)."""
    return ErroDaAPIException(
        CodigoDeErro.LIMITE_EXCEDIDO,
        "A imagem excede o limite de upload.",
        campo="imagem",
        detalhe=f"limite configurado: {config.limite_de_upload_mb} MB ({limite} bytes).",
    )


def _ler_imagem(
    arquivo: UploadFile, request: Request, config: Configuracoes
) -> tuple[bytes, str]:
    """Valida o tipo declarado e le a imagem respeitando o teto de tamanho.

    O endurecimento pedido em ``CONTRATOS_API.md`` §4.6 existe porque a Fase 4 aceita
    "qualquer arquivo que o Keras abra" — ou seja, nao valida nada.

    Returns:
        ``(conteudo, mime)`` — bytes da imagem e o tipo normalizado.

    Raises:
        ErroDaAPIException: tipo nao aceito, arquivo vazio (``CONTRATO_VIOLADO``) ou acima
            do limite (``LIMITE_EXCEDIDO``).
    """
    mime = (arquivo.content_type or "").lower().strip()
    if mime not in MIMES_ACEITOS:
        raise ErroDaAPIException(
            CodigoDeErro.CONTRATO_VIOLADO,
            "Tipo de arquivo nao suportado.",
            campo="imagem",
            detalhe=(
                f"recebido: {mime or 'ausente'}; aceitos: {', '.join(MIMES_ACEITOS)}."
            ),
        )

    limite = _limite_em_bytes(config)

    # Checagem previa por Content-Length: evita bufferizar um upload enorme so para recusa-lo.
    declarado = request.headers.get("content-length")
    if declarado is not None and declarado.isdigit():
        if int(declarado) > limite + MARGEM_DO_MULTIPART_EM_BYTES:
            raise _erro_de_limite(limite, config)

    # Le no maximo `limite + 1`: se o byte extra vier, o arquivo e grande demais.
    conteudo = arquivo.file.read(limite + 1)
    if not conteudo:
        raise ErroDaAPIException(
            CodigoDeErro.CONTRATO_VIOLADO,
            "O arquivo enviado esta vazio.",
            campo="imagem",
        )
    if len(conteudo) > limite:
        raise _erro_de_limite(limite, config)

    return conteudo, mime


@router.post(
    "",
    response_model=RespostaAPI[ResultadoDeDiagnostico],
    status_code=201,
    summary="Analisa uma radiografia pelo servico de visao (Fase 4)",
    description=(
        "Envia a imagem ao servico da Fase 4 (porta 5001) e devolve o diagnostico no "
        "contrato da Fase 7. **A imagem nao e armazenada**: guardam-se apenas o hash "
        "SHA-256 e os metadados. Servico fora do ar → `502`; sem resposta no prazo → `504`."
    ),
)
def analisar(
    request: Request,
    sessao: Annotated[Session, Depends(get_sessao)],
    usuario: SomenteMedico,
    imagem: Annotated[UploadFile, File(description="Radiografia de torax (JPEG ou PNG).")],
    id_paciente: Annotated[
        str | None, Form(description="Vinculacao opcional a um paciente.")
    ] = None,
) -> RespostaAPI[ResultadoDeDiagnostico]:
    """Encaminha a imagem, traduz o resultado e registra a analise."""
    config: Configuracoes = request.app.state.configuracoes
    conteudo, mime = _ler_imagem(imagem, request, config)

    paciente = None
    if id_paciente:
        paciente = buscar_paciente_ou_falhar(sessao, id_paciente)
        if not paciente.ativo:
            raise ErroDaAPIException(
                CodigoDeErro.CONFLITO,
                "Paciente inativo nao pode receber novas analises.",
                campo="id_paciente",
                detalhe="Reative o paciente antes de analisar.",
            )

    # Servico isolado por HTTP (Decisao 1-C): 502 quando fora do ar, 504 quando lento.
    resposta = chamar_previsao(
        conteudo,
        nome_arquivo=imagem.filename or "imagem",
        mime=mime,
        config=config,
    )

    # N4: traducao de nomes na borda. I9: os campos que a Fase 4 nao informa vem do
    # conhecimento do artefato — nunca de adivinhacao sobre o modelo.
    resultado = ResultadoDeDiagnostico(
        classe=ClasseDeDiagnosticoDeImagem(resposta.classe),
        confianca=resposta.confianca,
        modelo_utilizado=NOME_DO_MODELO_DA_VISAO,
        limiar_decisao=LIMIAR_DE_DECISAO_DA_VISAO,
        dimensoes_da_imagem=list(DIMENSOES_ESPERADAS_DA_IMAGEM),
        hash_sha256=hashlib.sha256(conteudo).hexdigest(),
        aviso_de_uso=AVISO_DE_USO_DA_VISAO,
    )

    analise = AnaliseDeImagemRepositorio(sessao).registrar(
        id_usuario=usuario.id,
        id_paciente=paciente.id if paciente is not None else None,
        nome_arquivo=(imagem.filename or "imagem")[:255],
        mime=mime,
        tamanho_bytes=len(conteudo),
        hash_sha256=resultado.hash_sha256,
        classe=resultado.classe,
        confianca=resultado.confianca,
        modelo_utilizado=resultado.modelo_utilizado,
        limiar_decisao=resultado.limiar_decisao,
        resposta=resultado.model_dump(mode="json"),
    )

    # 🔒 Sem a classe nem a confianca no `detalhe`: diagnostico e dado clinico e a trilha
    # nao precisa dele — o resultado ja esta em `analises_de_imagem`.
    registrar_auditoria(
        sessao,
        acao=ACAO_ANALISE,
        entidade=ENTIDADE,
        id_usuario=usuario.id,
        id_entidade=analise.id,
        ip=ip_do_cliente(request),
        detalhe={"mime": mime, "tamanho_bytes": len(conteudo)},
    )

    return resposta_de_sucesso(
        resultado,
        avisos=[AVISO_DE_USO_DA_VISAO],
        limitacoes=list(LIMITACOES_DA_VISAO),
        metadados=metadados_da_resposta(config),
        id_execucao=analise.id,
    )
