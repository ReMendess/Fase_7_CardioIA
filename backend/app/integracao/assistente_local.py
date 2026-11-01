"""Provedor local do assistente conversacional (Fase 5).

Responde a partir da **base de conhecimento do proprio projeto**, sem chamar nenhum
servico externo. E o provedor **padrao**: nao depende de rede, credencial, cota nem
disponibilidade de terceiros.

O contrato da resposta e **o mesmo** do adaptador do Watson (:mod:`app.integracao.fase_5`):
texto legivel para o usuario e uma sessao **interna** do provedor. Aqui a sessao e
``None`` — nao existe sessao remota a manter, porque a conversa e stateless.

O vocabulario clinico vem de fontes que **ja existem** no projeto:

- ``Fase_6/cardioia_Fase6/data/base_conhecimento.py`` — os 10 protocolos do dominio;
- os sinais de alerta das regras da Fase 3 (febre, taquicardia, ausencia de movimento).

⚠️ **Nada aqui e diagnostico.** As respostas orientam e, em sinal de alerta, encaminham
para atendimento de emergencia. O aviso obrigatorio e as limitacoes sao acrescentados
pelo envelope da rota (``CONTRATOS_API.md`` §8.1).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .fase_5 import RespostaDoAssistente

__all__ = [
    "INTENCOES",
    "PROVEDOR",
    "RESPOSTA_PADRAO",
    "Intencao",
    "nome_do_provedor",
    "normalizar",
    "responder",
]

#: Nome do provedor local, registrado na trilha de auditoria.
PROVEDOR = "local"

#: Pontuacao minima para aceitar uma intencao. Abaixo disso, resposta padrao.
PONTUACAO_MINIMA = 5


@dataclass(frozen=True)
class Intencao:
    """Um assunto reconhecido, com os termos que o disparam e a orientacao."""

    nome: str
    termos: tuple[str, ...]
    resposta: str


#: Ordem importa: a intencao com maior pontuacao vence. ``emergencia`` fica primeiro
#: porque um sinal de alerta nao pode ser ofuscado por um termo generico.
INTENCOES: tuple[Intencao, ...] = (
    Intencao(
        nome="emergencia",
        termos=(
            "dor no peito",
            "aperto no peito",
            "dor no braco",
            "dor no queixo",
            "suor frio",
            "nao consigo respirar",
            "desmaiei",
            "desmaio",
            "perdi a consciencia",
        ),
        resposta=(
            "Esses sinais podem indicar uma emergencia cardiovascular.\n\n"
            "Procure atendimento AGORA: ligue 192 (SAMU) ou va ao pronto-socorro mais "
            "proximo. Se houver dor no peito com falta de ar, suor frio ou irradiacao "
            "para braco, pescoco ou queixo, nao espere passar.\n\n"
            "Enquanto o atendimento nao chega: fique em repouso, sentado e sem esforco, "
            "afrouxe as roupas e nao tome medicacao por conta propria."
        ),
    ),
    Intencao(
        nome="dor_no_peito",
        termos=(
            "dor no peito",
            "dor toracica",
            "queimacao no peito",
            "angina",
            "aperto no peito",
        ),
        resposta=(
            "Dor ou aperto no peito merece atencao imediata, principalmente se durar mais "
            "de alguns minutos, piorar com esforco ou vier acompanhada de falta de ar, "
            "suor frio, nausea ou irradiacao para braco, pescoco ou queixo.\n\n"
            "Nesse caso, procure atendimento de emergencia. Se a dor for breve, aparecer "
            "so em esforco e passar com repouso, ainda assim precisa ser avaliada por um "
            "profissional — nao e possivel distinguir as causas sem exames."
        ),
    ),
    Intencao(
        nome="falta_de_ar",
        termos=(
            "falta de ar",
            "dispneia",
            "respiracao curta",
            "ofegante",
            "cansa para respirar",
        ),
        resposta=(
            "Falta de ar pode ter muitas causas. Procure atendimento imediato se ela "
            "surgir de repente, piorar deitado, vier com dor no peito, labios ou dedos "
            "arroxeados, ou dificuldade para completar uma frase.\n\n"
            "Se for um cansaco progressivo aos esforcos, vale registrar quando comeca, "
            "quanto dura e o que piora — e levar essas anotacoes na consulta."
        ),
    ),
    Intencao(
        nome="palpitacao",
        termos=(
            "palpitacao",
            "batimento acelerado",
            "coracao acelerado",
            "coracao disparado",
            "acelerado",
            "taquicardia",
            "bate forte",
            "arritmia",
        ),
        resposta=(
            "Palpitacoes sao a percepcao do proprio batimento. Procure atendimento se "
            "vierem com desmaio, dor no peito, falta de ar, ou se o coracao estiver muito "
            "rapido e irregular por varios minutos.\n\n"
            "No dia a dia, anote a duracao, o que estava fazendo e se havia cafeina, "
            "alcool ou estresse envolvidos. No monitoramento do projeto, a faixa de "
            "atencao para frequencia cardiaca comeca acima de 100 bpm em repouso."
        ),
    ),
    Intencao(
        nome="pressao_alta",
        termos=("pressao alta", "hipertensao", "pressao arterial", "pressao subiu"),
        resposta=(
            "Pressao alta costuma ser silenciosa. Uma medida isolada acima do esperado "
            "nao fecha diagnostico — o que importa e a media de varias medidas em "
            "condicoes adequadas, com manguito do tamanho certo e apos alguns minutos de "
            "repouso.\n\n"
            "Procure atendimento imediato se a medida for muito alta E houver dor no "
            "peito, falta de ar, alteracao da fala ou da forca de um lado do corpo, ou "
            "dor de cabeca intensa e subita."
        ),
    ),
    Intencao(
        nome="febre",
        termos=("febre", "temperatura alta", "febril", "esta quente"),
        resposta=(
            "A febre por si so nao indica problema cardiaco, mas sobrecarrega o coracao: "
            "a frequencia cardiaca sobe cerca de 10 bpm por grau acima do normal.\n\n"
            "No monitoramento do projeto, a regra da Fase 3 marca alerta a partir de "
            "37,8 °C. Se houver febre com falta de ar, dor no peito, confusao ou queda de "
            "pressao, procure atendimento."
        ),
    ),
    Intencao(
        nome="cansaco",
        termos=("cansaco", "fadiga", "sem energia", "fraqueza", "cansaco aos esforcos"),
        resposta=(
            "Cansaco tem causas muito variadas — anemia, alteracoes da tireoide, "
            "problemas cardiacos, sono ruim, entre outras. O sinal que muda a conduta e "
            "o cansaco que **piorou recentemente** ou que agora aparece em esforcos que "
            "antes eram faceis.\n\n"
            "Vale registrar desde quando piorou e em que situacoes, e levar isso na "
            "consulta."
        ),
    ),
    Intencao(
        nome="prevencao",
        termos=(
            "prevencao",
            "prevenir",
            "habitos",
            "estilo de vida",
            "como evitar",
            "fator de risco",
        ),
        resposta=(
            "Os fatores de risco cardiovascular mais relevantes e modificaveis sao: "
            "pressao alta, diabetes, colesterol elevado, tabagismo, sedentarismo, excesso "
            "de peso, sono ruim e estresse cronico.\n\n"
            "O que mais muda o risco no dia a dia: atividade fisica regular, alimentacao "
            "com menos ultraprocessados e sal, nao fumar, dormir bem e manter consultas e "
            "exames em dia. Mudanca de habito funciona melhor quando e gradual e "
            "sustentavel."
        ),
    ),
    Intencao(
        nome="o_que_faz",
        termos=("o que voce faz", "o que faz", "quem e voce", "para que serve", "cardioia"),
        resposta=(
            "Sou o assistente virtual do CardioIA, um projeto academico de saude digital. "
            "Oriento sobre sinais e sintomas cardiovasculares, fatores de risco e quando "
            "procurar atendimento.\n\n"
            "Posso falar sobre dor no peito, falta de ar, palpitacoes, pressao alta, "
            "febre, cansaco e prevencao. Nao faco diagnostico, nao prescrevo medicacao e "
            "nao substituo avaliacao profissional."
        ),
    ),
    Intencao(
        nome="ajuda",
        termos=("ajuda", "o que posso perguntar", "quais assuntos", "opcoes", "menu"),
        resposta=(
            "Posso conversar sobre: dor no peito, falta de ar, palpitacoes ou coracao "
            "acelerado, pressao alta, febre, cansaco e prevencao cardiovascular.\n\n"
            "Se o seu caso for um sinal de alerta — dor no peito com falta de ar, suor "
            "frio ou desmaio — procure atendimento imediatamente (192)."
        ),
    ),
)

#: Resposta quando nenhuma intencao atinge a pontuacao minima.
RESPOSTA_PADRAO = (
    "Nao identifiquei esse assunto com seguranca, e prefiro nao arriscar uma orientacao "
    "generica.\n\n"
    "Posso ajudar com: dor no peito, falta de ar, palpitacoes, pressao alta, febre, "
    "cansaco e prevencao cardiovascular. Se for uma emergencia — dor no peito com falta "
    "de ar, suor frio ou desmaio — procure atendimento imediato (192)."
)


def normalizar(texto: str) -> str:
    """Minusculas, sem acentos e com espacos colapsados — para casar os termos."""
    decomposto = unicodedata.normalize("NFKD", texto.lower())
    sem_acento = "".join(caractere for caractere in decomposto if not unicodedata.combining(caractere))
    return " ".join(sem_acento.split())


def nome_do_provedor() -> str:
    """Identificador do provedor, usado na auditoria."""
    return PROVEDOR


def responder(mensagem: str) -> RespostaDoAssistente:
    """Responde a uma mensagem a partir das intencoes conhecidas.

    A pontuacao soma o **comprimento** de cada termo encontrado, e nao apenas a
    quantidade: assim ``"dor no peito"`` (frase especifica) vence ``"peito"`` (palavra
    solta) quando as duas aparecem. Sem correspondencia suficiente, devolve
    :data:`RESPOSTA_PADRAO` — **nunca** inventa uma orientacao clinica.

    Args:
        mensagem: texto enviado pelo usuario.

    Returns:
        :class:`RespostaDoAssistente` com o texto e ``session_id_do_provedor=None``:
        nao ha sessao remota a manter, porque este provedor e stateless.
    """
    alvo = normalizar(mensagem)

    melhor: Intencao | None = None
    melhor_pontuacao = 0

    for intencao in INTENCOES:
        pontuacao = sum(len(termo) for termo in intencao.termos if termo in alvo)
        if pontuacao > melhor_pontuacao:
            melhor, melhor_pontuacao = intencao, pontuacao

    if melhor is None or melhor_pontuacao < PONTUACAO_MINIMA:
        return RespostaDoAssistente(resposta=RESPOSTA_PADRAO, session_id_do_provedor=None)

    return RespostaDoAssistente(resposta=melhor.resposta, session_id_do_provedor=None)



