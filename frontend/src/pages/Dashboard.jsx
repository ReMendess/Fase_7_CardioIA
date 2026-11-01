import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listarAvaliacoes, listarLeituras, obterAvaliacao, saude } from "../api/endpoints";
import { Avisos, Carregando, Falha, Limitacoes, Origem, Vazio } from "../components/Estado";
import NivelDeRisco from "../components/NivelDeRisco";
import SeletorDePaciente from "../components/SeletorDePaciente";
import { useAuth } from "../contexts/AuthContext";
import { usePacientes } from "../contexts/PacienteContext";
import { ORIGENS_DO_TRANSPORTE, STATUS_DA_RESPOSTA } from "../dominio/catalogo";

/**
 * Dashboard clinico.
 *
 * Fontes de cada bloco (item 3: separar simulado, real e preditivo):
 *
 * | Bloco | Origem |
 * |---|---|
 * | Paciente em foco | `GET /pacientes` |
 * | Risco e indicadores | `GET /avaliacoes/{id}` — **resultado preditivo** persistido |
 * | Telemetria | `GET /iot/leituras` — **dado real** do dispositivo |
 * | Estado do servico | `GET /health` |
 *
 * Nenhum numero e inventado: onde nao ha dado, a tela diz que nao ha.
 */
export default function Dashboard() {
  const { usuario } = useAuth();
  const { selecionado, pacientes, carregando: carregandoPacientes } = usePacientes();

  const [estado, setEstado] = useState({
    carregando: true,
    erro: null,
    avaliacao: null,
    resumos: [],
  });
  const [leituras, setLeituras] = useState({ carregando: true, erro: null, itens: [] });
  const [servico, setServico] = useState(null);

  // O efeito NAO chama setState de forma sincrona: ele dispara a busca e so mexe no
  // estado dentro do callback. Isso evita render em cascata a cada mudanca de paciente.
  useEffect(() => {
    let cancelado = false;
    buscarAvaliacoes(selecionado?.id_paciente)
      .then((proximo) => {
        if (!cancelado) setEstado(proximo);
      })
      .catch((falha) => {
        if (!cancelado) setEstado(estadoDeFalha(falha));
      });
    return () => {
      cancelado = true;
    };
  }, [selecionado]);

  /** Recarrega sob demanda (botao), mostrando o indicador de carregamento. */
  async function carregarAvaliacoes() {
    setEstado((atual) => ({ ...atual, carregando: true, erro: null }));
    try {
      setEstado(await buscarAvaliacoes(selecionado?.id_paciente));
    } catch (falha) {
      setEstado(estadoDeFalha(falha));
    }
  }
  useEffect(() => {
    let cancelado = false;

    async function carregarTelemetria() {
      try {
        const envelope = await listarLeituras({ limite: 5 });
        if (!cancelado) {
          setLeituras({
            carregando: false,
            erro: null,
            itens: Array.isArray(envelope.dados) ? envelope.dados : [],
          });
        }
      } catch (falha) {
        if (!cancelado) setLeituras({ carregando: false, erro: falha, itens: [] });
      }
    }

    carregarTelemetria();
    saude()
      .then((envelope) => !cancelado && setServico(envelope.dados))
      .catch(() => !cancelado && setServico(null));

    return () => {
      cancelado = true;
    };
  }, []);

  const avaliacao = estado.avaliacao;
  const contrato = avaliacao?.resposta;
  const diagnostico = contrato?.diagnostico;
  // `features_utilizadas` fica DENTRO de `diagnostico` e e a lista de NOMES (conferido
  // contra a resposta real do backend).
  const nomesDasFeatures = Array.isArray(diagnostico?.features_utilizadas)
    ? diagnostico.features_utilizadas
    : [];
  const ultimaLeitura = leituras.itens[0] ?? null;

  return (
    <div className="stack" style={{ gap: 18 }}>
      <section className="panel">
        <div className="painelTopo">
          <div>
            <h2 className="pageTitle">Visao geral</h2>
            <p className="helper">
              Bem-vindo, {usuario?.nome} · <span className="mono">{usuario?.papel}</span>
            </p>
          </div>
          <SeletorDePaciente compacto />
        </div>
      </section>

      {carregandoPacientes ? (
        <Carregando texto="Carregando pacientes..." />
      ) : !pacientes.length ? (
        <Vazio titulo="Nenhum paciente cadastrado">
          Cadastre o primeiro paciente na aba <Link to="/pacientes">Pacientes</Link> para
          ver indicadores e risco.
        </Vazio>
      ) : (
        <div className="grid2">
          <section className="panel">
            <h3 className="panelTitle">
              Resultado de risco
              <Origem tipo="preditivo" />
            </h3>

            {estado.carregando ? (
              <Carregando texto="Carregando avaliacoes..." linhas={2} />
            ) : estado.erro ? (
              <Falha erro={estado.erro} aoTentarDeNovo={carregarAvaliacoes} />
            ) : (
              <>
                <NivelDeRisco diagnostico={diagnostico} />
                {avaliacao && (
                  <p className="helper" style={{ marginTop: 10 }}>
                    Avaliacao de {formatarData(avaliacao.criado_em)} · modo{" "}
                    {avaliacao.modo} · origem {avaliacao.origem_dos_dados} ·{" "}
                    <Link to="/historico">ver historico</Link>
                  </p>
                )}
              </>
            )}
          </section>

          <section className="panel">
            <h3 className="panelTitle">Resumo</h3>
            <div className="stack">
              <Linha rotulo="Pacientes cadastrados" valor={pacientes.length} />
              <Linha rotulo="Avaliacoes deste paciente" valor={estado.resumos.length} />
              <Linha
                rotulo="Paciente em foco"
                valor={selecionado?.nome ?? "--"}
                pequeno={selecionado?.id_paciente}
              />
              <Linha
                rotulo="Servico"
                valor={servico ? `online · ${servico.ambiente}` : "indisponivel"}
                pequeno={servico?.versao_do_backend}
              />
            </div>
          </section>
        </div>
      )}

      <section className="panel">
        <h3 className="panelTitle">
          Indicadores cardiacos
          <Origem tipo="api" />
        </h3>
        <p className="helper">
          Ultima leitura recebida dos dispositivos (Fase 3). ⚠️ A telemetria{" "}
          <strong>nao e vinculada a paciente</strong> no contrato §4.2 — estes numeros sao
          do <strong>dispositivo</strong>, nao do paciente em foco.
        </p>

        {leituras.carregando ? (
          <Carregando texto="Carregando telemetria..." linhas={2} />
        ) : leituras.erro ? (
          <Falha erro={leituras.erro} />
        ) : !ultimaLeitura ? (
          <Vazio titulo="Nenhuma leitura recebida">
            O firmware da Fase 3 publica em <code>hospital/*</code>; a ingestao e{" "}
            <code>POST /iot/leituras</code>. Veja a aba{" "}
            <Link to="/monitoramento">Monitoramento</Link>.
          </Vazio>
        ) : (
          <>
            <div className="vitals">
              <Vital rotulo="Frequencia cardiaca" valor={ultimaLeitura.bpm} unidade="bpm" />
              <Vital rotulo="Temperatura" valor={ultimaLeitura.temperatura} unidade="°C" />
              <Vital rotulo="Umidade" valor={ultimaLeitura.umidade} unidade="%" />
              <Vital rotulo="Luminosidade" valor={ultimaLeitura.luminosidade} unidade="lx" />
            </div>
            <p className="helper" style={{ marginTop: 10 }}>
              {ultimaLeitura.id_dispositivo} · {formatarData(ultimaLeitura.recebido_em)} ·{" "}
              {ORIGENS_DO_TRANSPORTE[ultimaLeitura.origem_transporte] ??
                ultimaLeitura.origem_transporte}{" "}
              · <Link to="/monitoramento">ver todas as leituras</Link>
            </p>
          </>
        )}
      </section>

      {selecionado && (
        <section className="panel">
          <h3 className="panelTitle">
            Contrato do modelo
            <Origem tipo="preditivo" />
          </h3>

          {nomesDasFeatures.length === 0 ? (
            <Vazio titulo="Nenhuma avaliacao registrada">
              As 10 features so existem depois de uma avaliacao — elas sao o{" "}
              <em>estado clinico datado</em>, nao o cadastro.{" "}
              <Link to="/avaliacao">Fazer uma avaliacao</Link>.
            </Vazio>
          ) : (
            <>
              <div className="row" style={{ flexWrap: "wrap" }}>
                {nomesDasFeatures.map((nome) => (
                  <span className="etiqueta" key={nome}>
                    {nome}
                  </span>
                ))}
              </div>
              <p className="helper" style={{ marginTop: 10 }}>
                ⚠️ A API devolve os <strong>nomes</strong> das features que o modelo usou,
                nao os valores: eles ficam no registro persistido e <strong>nao sao
                expostos</strong> por nenhum endpoint. Para ver os valores, faça uma nova
                avaliacao em <Link to="/avaliacao">Avaliacao</Link> — as barras aparecem
                com o que voce digitou.
              </p>
            </>
          )}
        </section>
      )}

      {avaliacao && (
        <section className="panel">
          <h3 className="panelTitle">Qualidade da resposta</h3>
          <div className="stack">
            <div className="linhaChaveValor">
              <span className="helper">Status</span>
              <span className="etiqueta">
                {STATUS_DA_RESPOSTA[avaliacao.status] ?? avaliacao.status}
              </span>
            </div>
            <Avisos itens={avaliacao.avisos} titulo="Avisos" />
            <Limitacoes itens={contrato?.limitacoes} />
          </div>
        </section>
      )}

      <section className="panel">
        <h3 className="panelTitle">
          Monitoramento IoT
          <Origem tipo="api" />
        </h3>
        <p className="helper">
          ⚠️ A telemetria <strong>nao e vinculada a paciente</strong> no contrato §4.2 —
          estas leituras sao de todos os dispositivos.
        </p>

        {leituras.carregando ? (
          <Carregando texto="Carregando telemetria..." linhas={2} />
        ) : leituras.erro ? (
          <Falha erro={leituras.erro} />
        ) : !leituras.itens.length ? (
          <Vazio titulo="Nenhuma leitura recebida">
            O firmware da Fase 3 publica em <code>hospital/*</code>; a ingestao e{" "}
            <code>POST /iot/leituras</code>. Veja a aba{" "}
            <Link to="/monitoramento">Monitoramento</Link>.
          </Vazio>
        ) : (
          <>
            <div className="list">
              {leituras.itens.slice(0, 3).map((leitura) => (
                <div className="listItem" key={leitura.id_leitura}>
                  <div>
                    <div className="listItemTitle">{leitura.id_dispositivo}</div>
                    <div className="helper">
                      {formatarData(leitura.recebido_em)} ·{" "}
                      {ORIGENS_DO_TRANSPORTE[leitura.origem_transporte] ??
                        leitura.origem_transporte}
                    </div>
                  </div>
                  <div className="row">
                    {leitura.temperatura != null && (
                      <span className="pill">{leitura.temperatura} °C</span>
                    )}
                    {leitura.bpm != null && <span className="pill">{leitura.bpm} bpm</span>}
                  </div>
                </div>
              ))}
            </div>
            <p className="helper" style={{ marginTop: 10 }}>
              <Link to="/monitoramento">Ver todas as leituras</Link>
            </p>
          </>
        )}
      </section>
    </div>
  );
}

/**
 * Busca o que o dashboard precisa. **Nao** mexe em estado — por isso pode ser
 * chamada de dentro de um efeito sem causar render em cascata.
 */
async function buscarAvaliacoes(idPaciente) {
  if (!idPaciente) {
    return { carregando: false, erro: null, avaliacao: null, resumos: [] };
  }
  const lista = await listarAvaliacoes({ idPaciente, limite: 50 });
  const resumos = Array.isArray(lista.dados) ? lista.dados : [];
  // O detalhe traz o contrato integral da Fase 6 (com as 10 features usadas).
  const detalhe = resumos.length ? await obterAvaliacao(resumos[0].id_execucao) : null;
  return { carregando: false, erro: null, avaliacao: detalhe, resumos };
}

function estadoDeFalha(falha) {
  return { carregando: false, erro: falha, avaliacao: null, resumos: [] };
}

/** Um sinal vital da telemetria. */
function Vital({ rotulo, valor, unidade }) {
  const ausente = valor === null || valor === undefined;
  return (
    <div className={`vital ${ausente ? "vital--ausente" : ""}`}>
      <div className="vitalRotulo">{rotulo}</div>
      <div className="vitalValor">
        {ausente ? "--" : valor}
        {!ausente && <span className="vitalUnidade"> {unidade}</span>}
      </div>
    </div>
  );
}

function Linha({ rotulo, valor, pequeno }) {
  return (
    <div className="linhaChaveValor">
      <span className="helper">{rotulo}</span>
      <span style={{ textAlign: "right" }}>
        <span className="listItemTitle">{valor}</span>
        {pequeno && <div className="mono helper">{pequeno}</div>}
      </span>
    </div>
  );
}

function formatarData(iso) {
  if (!iso) return "--";
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return String(iso);
  return data.toLocaleString("pt-BR");
}

