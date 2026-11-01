/**
 * Smoke test da integracao frontend -> backend (Etapa D, item 5).
 *
 * Roda em Node e exercita **a mesma camada de API que a interface usa**
 * (`src/api/cliente.js` + `src/api/endpoints.js`) contra o backend real. Nao e um mock:
 * se o envelope mudar de forma, este script quebra — que e exatamente o ponto.
 *
 * Uso (com o backend no ar):
 *
 *     npm run smoke
 *
 * Variaveis de ambiente:
 *
 * | Variavel | Padrao | Para que |
 * |---|---|---|
 * | `VITE_API_URL` | `http://127.0.0.1:8000/api/v1` | onde o backend esta |
 * | `SMOKE_EMAIL` | — (**obrigatorio**) | usuario semeado no banco |
 * | `SMOKE_SENHA` | — (**obrigatorio**) | senha do usuario |
 *
 * 🔒 Nenhuma credencial fica no codigo: as duas vem do ambiente.
 */

import {
  analisarImagem,
  criarAvaliacao,
  criarPaciente,
  enviarMensagem,
  listarAvaliacoes,
  listarLeituras,
  listarPacientes,
  meuUsuario,
  obterAvaliacao,
  saude,
  entrar,
  sair,
} from "../src/api/endpoints.js";
import {
  ErroDaAPI,
  ErroDeRede,
  definirTokens,
  mensagemDoErro,
  requisitar,
} from "../src/api/cliente.js";
import { URL_DA_API } from "../src/api/configuracao.js";

const EMAIL = process.env.SMOKE_EMAIL;
const SENHA = process.env.SMOKE_SENHA;

const resultados = [];
let papel = null;

/** As 10 features, com valores FICTICIOS (as mesmas do "Preencher exemplo"). */
const FEATURES_FICTICIAS = {
  idade_media: 62,
  carga_sistema: 92,
  tempo_espera: 75,
  fc_media: 118,
  spo2_media: 89,
  pa_sistolica: 100,
  temperatura: 37.5,
  densidade_eventos: 7,
  eventos_24h: 5,
  disponibilidade_recursos: 0.4,
};

/** Registra um passo e imprime o resultado. */
function passo(nome, ok, detalhe = "") {
  resultados.push({ nome, ok, detalhe });
  console.log(`  [${ok ? "OK   " : "FALHA"}] ${nome}${detalhe ? `  -- ${detalhe}` : ""}`);
  return ok;
}

function secao(titulo) {
  console.log(`\n${"=".repeat(74)}\n${titulo}\n${"=".repeat(74)}`);
}

/**
 * Executa um passo que deve **falhar** com um codigo especifico.
 * Usado para provar os caminhos de erro (501 do Watson, 403 do RBAC, etc.).
 */
async function passoQueFalha(nome, promessa, codigosEsperados, httpEsperado = null) {
  try {
    await promessa();
    return passo(nome, false, "esperava falha, mas a chamada passou");
  } catch (falha) {
    if (falha instanceof ErroDeRede) {
      return passo(nome, false, `erro de rede: ${falha.message}`);
    }
    if (falha instanceof ErroDaAPI) {
      const codigoOk = codigosEsperados.includes(falha.codigo);
      const httpOk = httpEsperado === null || falha.http === httpEsperado;
      return passo(
        nome,
        codigoOk && httpOk,
        `HTTP ${falha.http} · ${falha.codigo} · ${falha.mensagem}`
      );
    }
    return passo(nome, false, `erro inesperado: ${falha.message}`);
  }
}

async function principal() {
  console.log("=".repeat(74));
  console.log("SMOKE TEST — integracao frontend (Fase 7 / Etapa D) x backend");
  console.log("=".repeat(74));
  console.log(`API: ${URL_DA_API}`);
  console.log(`Usuario: ${EMAIL ?? "(nao informado)"}`);

  if (!EMAIL || !SENHA) {
    console.error(
      "\n[erro] Defina SMOKE_EMAIL e SMOKE_SENHA antes de rodar.\n" +
        '  PowerShell:  $env:SMOKE_EMAIL="medico@exemplo.local"; $env:SMOKE_SENHA="..."\n'
    );
    process.exit(2);
  }

  // --- 1. health (rota publica) ----------------------------------------- #
  secao("1. Health check e disponibilidade");
  try {
    const envelope = await saude();
    const dados = envelope.dados ?? {};
    passo("GET /health responde com envelope", envelope.status === "CONCLUIDO");
    passo(
      "dados traz 'ambiente' e 'versao_do_backend'",
      Boolean(dados.ambiente && dados.versao_do_backend),
      `${dados.servico} · ${dados.ambiente} · ${dados.versao_do_backend}`
    );
    const modelo = dados.artefato_do_modelo ?? {};
    passo(
      "o artefato do modelo esta presente",
      modelo.presente !== false,
      `arquivo=${modelo.nome_do_arquivo ?? "?"}`
    );
  } catch (falha) {
    passo("GET /health", false, mensagemDoErro(falha));
    console.log("\n[abortado] sem backend no ar o restante nao faz sentido.");
    return resumo();
  }

  // --- 2. autenticacao --------------------------------------------------- #
  secao("2. Autenticacao JWT");
  try {
    const sessao = await entrar(EMAIL, SENHA);
    const tokens = sessao.dados;
    definirTokens(tokens);
    passo(
      "POST /auth/login devolve par de tokens",
      Boolean(tokens.access_token && tokens.refresh_token)
    );
    passo(
      "o access token e um JWT (3 segmentos)",
      String(tokens.access_token).split(".").length === 3
    );

    const perfil = await meuUsuario();
    papel = perfil.dados.papel;
    passo("GET /auth/me confirma a sessao", Boolean(perfil.dados.email));
    passo(
      "o usuario NAO traz 'senha_hash'",
      !("senha_hash" in perfil.dados),
      `${perfil.dados.nome} · ${papel}`
    );
  } catch (falha) {
    passo("login", false, mensagemDoErro(falha));
    console.log("\n[abortado] sem sessao nao ha como seguir.");
    return resumo();
  }

  // --- 3. credencial invalida -------------------------------------------- #
  secao("3. Tratamento de credencial invalida");
  await passoQueFalha(
    "login com senha errada devolve 401 NAO_AUTENTICADO",
    () =>
      requisitar("POST", "/auth/login", {
        corpo: { email: EMAIL, senha: "senha-completamente-errada" },
        autenticado: false,
      }),
    ["NAO_AUTENTICADO"],
    401
  );

  // --- capacidades do papel (matriz do contrato §8) ---------------------- #
  //   clinico (ler)      : MEDICO | ADMIN
  //   clinico (escrever) : MEDICO
  //   telemetria (ler)   : OPERADOR | MEDICO
  //   assistente         : OPERADOR | MEDICO
  const PODE_LER_CLINICO = papel === "MEDICO" || papel === "ADMIN";
  const PODE_ESCREVER_CLINICO = papel === "MEDICO";
  const PODE_LER_TELEMETRIA = papel === "OPERADOR" || papel === "MEDICO";
  const PODE_USAR_ASSISTENTE = papel === "OPERADOR" || papel === "MEDICO";

  // --- 4. pacientes ------------------------------------------------------ #
  secao("4. Cadastro e consulta de pacientes");
  let pacientes = [];

  if (!PODE_LER_CLINICO) {
    await passoQueFalha(
      `${papel} nao pode listar pacientes (403)`,
      () => listarPacientes(),
      ["NAO_AUTORIZADO"],
      403
    );
  } else {
    try {
      const envelope = await listarPacientes();
      pacientes = Array.isArray(envelope.dados) ? envelope.dados : [];
      passo(
        "GET /pacientes devolve uma LISTA em 'dados'",
        Array.isArray(envelope.dados),
        `${pacientes.length} paciente(s)`
      );
    } catch (falha) {
      passo("GET /pacientes", false, mensagemDoErro(falha));
    }

    if (PODE_ESCREVER_CLINICO) {
      try {
        const criado = await criarPaciente(
          `Paciente Smoke ${new Date().toISOString().slice(11, 19)}`
        );
        passo(
          "POST /pacientes (MEDICO) cria o paciente",
          Boolean(criado.dados?.id_paciente),
          criado.dados?.id_paciente
        );
        pacientes = [criado.dados, ...pacientes];
      } catch (falha) {
        passo("POST /pacientes", false, mensagemDoErro(falha));
      }
    } else {
      await passoQueFalha(
        `${papel} nao pode cadastrar paciente (403)`,
        () => criarPaciente("Nao deve criar"),
        ["NAO_AUTORIZADO"],
        403
      );
    }
  }

  // --- 5. capacidades do papel ------------------------------------------- #
  secao("5. Capacidades do papel autenticado (matriz do contrato §8)");
  console.log(`  papel autenticado: ${papel}`);
  console.log(`    ler dado clinico ......... ${PODE_LER_CLINICO ? "sim" : "NAO (403)"}`);
  console.log(`    escrever dado clinico .... ${PODE_ESCREVER_CLINICO ? "sim" : "NAO (403)"}`);
  console.log(`    ler telemetria IoT ....... ${PODE_LER_TELEMETRIA ? "sim" : "NAO (403)"}`);
  console.log(`    usar o assistente ........ ${PODE_USAR_ASSISTENTE ? "sim" : "NAO (403)"}`);
  passo(
    "as capacidades foram deduzidas do papel devolvido por /auth/me",
    Boolean(papel),
    "as secoes 4, 6, 7, 8 e 9 verificam cada negativa com HTTP 403"
  );

  // --- 6. avaliacao de risco --------------------------------------------- #
  secao("6. Avaliacao de risco (pipeline da Fase 6)");
  const paciente = pacientes[0];
  if (!PODE_ESCREVER_CLINICO) {
    await passoQueFalha(
      `${papel} nao pode registrar avaliacoes (403)`,
      () =>
        criarAvaliacao({
          idPaciente: paciente?.id_paciente ?? "pac-inexistente-0000",
          features: FEATURES_FICTICIAS,
        }),
      ["NAO_AUTORIZADO"],
      403
    );
  } else if (!paciente) {
    passo("avaliacao", false, "nenhum paciente disponivel para avaliar");
  } else {
    try {
      const envelope = await criarAvaliacao({
        idPaciente: paciente.id_paciente,
        features: FEATURES_FICTICIAS,
        origemDosDados: "manual",
        modo: "simulado",
      });
      const contrato = envelope.dados ?? {};
      const diagnostico = contrato.diagnostico ?? {};
      passo(
        "POST /avaliacoes conclui",
        String(envelope.status).startsWith("CONCLUIDO"),
        `status=${envelope.status}`
      );
      passo(
        "o diagnostico traz probabilidade e classificacao",
        typeof diagnostico.probabilidade_risco === "number" &&
          Boolean(diagnostico.classificacao_risco),
        `prob=${diagnostico.probabilidade_risco} · ${diagnostico.classificacao_risco}`
      );
      passo(
        "o modelo utilizado e informado",
        Boolean(diagnostico.modelo_utilizado),
        diagnostico.modelo_utilizado
      );
      passo(
        "as 10 features usadas voltam em diagnostico.features_utilizadas",
        Array.isArray(diagnostico.features_utilizadas) &&
          diagnostico.features_utilizadas.length === 10,
        `${diagnostico.features_utilizadas?.length ?? 0} nome(s)`
      );
      passo(
        "a execucao traz justificativas e narrativa",
        Array.isArray(contrato.justificativas) && Boolean(contrato.narrativa),
        `${contrato.justificativas?.length ?? 0} justificativa(s)`
      );
      passo(
        "'limitacoes' vem preenchida (contrato R2)",
        Array.isArray(envelope.limitacoes) && envelope.limitacoes.length > 0,
        `${envelope.limitacoes?.length} limitacao(oes)`
      );
    } catch (falha) {
      passo("avaliacao", false, mensagemDoErro(falha));
    }

    await passoQueFalha(
      "modo 'real' sem OPENAI_API_KEY devolve 501",
      () =>
        criarAvaliacao({
          idPaciente: paciente.id_paciente,
          features: FEATURES_FICTICIAS,
          modo: "real",
        }),
      ["NAO_CONFIGURADO"],
      501
    );

    await passoQueFalha(
      "feature booleana e recusada (422)",
      () =>
        criarAvaliacao({
          idPaciente: paciente.id_paciente,
          features: { ...FEATURES_FICTICIAS, idade_media: true },
        }),
      ["PACIENTE_INVALIDO", "CONTRATO_VIOLADO"],
      422
    );
  }

  // --- 7. historico ------------------------------------------------------ #
  secao("7. Historico de avaliacoes");
  if (!PODE_LER_CLINICO) {
    await passoQueFalha(
      `${papel} nao pode ler o historico clinico (403)`,
      () => listarAvaliacoes(),
      ["NAO_AUTORIZADO"],
      403
    );
  } else {
    try {
      const lista = await listarAvaliacoes({ limite: 5 });
      const itens = Array.isArray(lista.dados) ? lista.dados : [];
      passo(
        "GET /avaliacoes devolve lista",
        Array.isArray(lista.dados),
        `${itens.length} item(ns)`
      );
      if (itens.length) {
        const primeiro = itens[0];
        passo(
          "o resumo traz id_execucao, status e criado_em",
          Boolean(primeiro.id_execucao && primeiro.status && primeiro.criado_em),
          primeiro.id_execucao
        );
        const detalhe = await obterAvaliacao(primeiro.id_execucao);
        passo(
          "GET /avaliacoes/{id} traz a resposta persistida",
          Boolean(detalhe.dados?.resposta?.diagnostico),
          `sha256=${String(detalhe.dados?.sha256_da_base_usada).slice(0, 12)}...`
        );
      }
    } catch (falha) {
      passo("historico", false, mensagemDoErro(falha));
    }
  }

  // --- 8. telemetria IoT ------------------------------------------------- #
  secao("8. Telemetria IoT");
  if (!PODE_LER_TELEMETRIA) {
    await passoQueFalha(
      "ADMIN nao le telemetria (403)",
      () => listarLeituras(),
      ["NAO_AUTORIZADO"],
      403
    );
  } else {
    try {
      const envelope = await listarLeituras({ limite: 5 });
      const itens = Array.isArray(envelope.dados) ? envelope.dados : [];
      passo(
        "GET /iot/leituras devolve lista",
        Array.isArray(envelope.dados),
        `${itens.length} leitura(s)`
      );
      passo(
        "'limitacoes' explica o escopo da telemetria",
        Array.isArray(envelope.limitacoes) && envelope.limitacoes.length > 0
      );
      if (itens.length) {
        const leitura = itens[0];
        passo(
          "a leitura traz id_dispositivo e recebido_em",
          Boolean(leitura.id_dispositivo && leitura.recebido_em),
          `${leitura.id_dispositivo} · ${leitura.recebido_em}`
        );
        passo(
          "a leitura NAO traz id_paciente (contrato §4.2)",
          !("id_paciente" in leitura)
        );
      }
    } catch (falha) {
      passo("telemetria", false, mensagemDoErro(falha));
    }
  }

  // --- 9. assistente conversacional -------------------------------------- #
  secao("9. Assistente conversacional");
  if (!PODE_USAR_ASSISTENTE) {
    await passoQueFalha(
      "ADMIN nao usa o assistente (403)",
      () => enviarMensagem("Ola"),
      ["NAO_AUTORIZADO"],
      403
    );
  } else {
    // O provedor local responde sempre; o Watson entra quando configurado. O contrato
    // da resposta e o mesmo nos dois casos.
    try {
      const envelope = await enviarMensagem("Estou com dor no peito");
      const dados = envelope.dados ?? {};
      passo("POST /chat responde", String(envelope.status).startsWith("CONCLUIDO"),
        `status=${envelope.status}`);
      passo("a resposta traz id_conversa e texto",
        Boolean(dados.id_conversa && dados.resposta),
        `conversa=${dados.id_conversa}`);
      passo("`fontes` e sempre [] (nota N6)", Array.isArray(dados.fontes) && dados.fontes.length === 0);
      passo("sinal de alerta encaminha para emergencia",
        String(dados.resposta).includes("192"));
      passo("'limitacoes' vem preenchida",
        Array.isArray(envelope.limitacoes) && envelope.limitacoes.length > 0);
    } catch (falha) {
      passo("POST /chat", false, mensagemDoErro(falha));
    }
  }

  // --- 10. visao computacional ------------------------------------------- #
  secao("10. Diagnostico por imagem (Fase 4)");
  if (papel === "MEDICO") {
    const bytes = new Uint8Array([
      0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0xff, 0xd9,
    ]);
    const arquivo = new File([bytes], "radiografia-smoke.jpg", { type: "image/jpeg" });
    // O servico da Fase 4 roda em processo separado e exige TensorFlow: se estiver
    // fora do ar, a API responde 502 — o mesmo caminho que a tela mostra ao usuario.
    await passoQueFalha(
      "servico de visao indisponivel devolve 502 (ou 504 se demorar)",
      () => analisarImagem(arquivo, paciente?.id_paciente),
      ["ERRO_DE_SERVICO_DE_VISAO"],
      502
    );
  } else {
    passo(`/imagens nao se aplica ao papel ${papel}`, true, "pulado (exige MEDICO)");
  }

  // --- 11. encerramento -------------------------------------------------- #
  secao("11. Encerramento de sessao");
  try {
    const resposta = await sair();
    passo(
      "POST /auth/logout revoga as sessoes",
      typeof resposta.dados?.sessoes_revogadas === "number",
      `${resposta.dados?.sessoes_revogadas} sessao(oes)`
    );
  } catch (falha) {
    passo("logout", false, mensagemDoErro(falha));
  }

  return resumo();
}

/** Imprime o resumo e devolve o codigo de saida. */
function resumo() {
  const total = resultados.length;
  const falhas = resultados.filter((r) => !r.ok);
  console.log(`\n${"=".repeat(74)}\nRESUMO\n${"=".repeat(74)}`);
  console.log(`  aprovados: ${total - falhas.length}/${total}`);
  if (falhas.length) {
    console.log("\n  REPROVADOS:");
    for (const falha of falhas) console.log(`    - ${falha.nome} -- ${falha.detalhe}`);
  }
  console.log("");
  return falhas.length ? 1 : 0;
}

principal()
  .then((codigo) => process.exit(codigo))
  .catch((erro) => {
    console.error("\n[erro inesperado no smoke test]", erro);
    process.exit(1);
  });



