import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listarAvaliacoes, obterAvaliacao } from "../api/endpoints";
import { Carregando, Falha, Origem, Vazio } from "../components/Estado";
import NivelDeRisco from "../components/NivelDeRisco";
import { DetalhesDoContrato } from "../components/ResultadoDaAvaliacao";
import SeletorDePaciente from "../components/SeletorDePaciente";
import { usePacientes } from "../contexts/PacienteContext";
import {
  CLASSIFICACOES_DE_RISCO,
  MODOS_DO_PIPELINE,
  STATUS_DA_RESPOSTA,
} from "../dominio/catalogo";

/**
 * Historico de avaliacoes.
 *
 * Duas leituras do **mesmo** endpoint (`GET /avaliacoes`):
 *
 * - **resumo** — `ResumoDeAvaliacao`, ja com probabilidade e classificacao (lista);
 * - **detalhe** — `GET /avaliacoes/{id}`, que devolve o contrato da Fase 6
 *   **persistido**, sem reexecutar o modelo. A decisao registrada e exatamente a que
 *   foi tomada na epoca.
 */
export default function Historico() {
  const { selecionado } = usePacientes();

  const [somenteDoPaciente, setSomenteDoPaciente] = useState(true);
  const [lista, setLista] = useState({ carregando: true, erro: null, itens: [] });
  const [detalhe, setDetalhe] = useState({
    carregando: false,
    erro: null,
    id: null,
    envelope: null,
  });

  const idFiltro = somenteDoPaciente && selecionado ? selecionado.id_paciente : null;

  // O efeito so dispara a busca; o estado e atualizado no callback (sem render em cascata).
  useEffect(() => {
    let cancelado = false;
    buscarHistorico(idFiltro)
      .then((proximo) => {
        if (!cancelado) setLista(proximo);
      })
      .catch((falha) => {
        if (!cancelado) setLista(estadoDeFalha(falha));
      });
    return () => {
      cancelado = true;
    };
  }, [idFiltro]);

  /** Recarrega sob demanda (botao). */
  async function carregar() {
    setLista((atual) => ({ ...atual, carregando: true, erro: null }));
    try {
      setLista(await buscarHistorico(idFiltro));
    } catch (falha) {
      setLista(estadoDeFalha(falha));
    }
  }

  async function abrir(idExecucao) {
    setDetalhe({ carregando: true, erro: null, id: idExecucao, envelope: null });
    try {
      const envelope = await obterAvaliacao(idExecucao);
      setDetalhe({ carregando: false, erro: null, id: idExecucao, envelope });
    } catch (falha) {
      setDetalhe({ carregando: false, erro: falha, id: idExecucao, envelope: null });
    }
  }

  return (
    <div className="stack" style={{ gap: 18 }}>
      <section className="panel">
        <div className="painelTopo">
          <div>
            <h2 className="pageTitle">Historico de avaliacoes</h2>
            <p className="helper">
              Cada linha e uma execucao do pipeline, com a resposta que ficou gravada.
            </p>
          </div>
          <SeletorDePaciente compacto />
        </div>

        <div className="row" style={{ marginTop: 12 }}>
          <label className="opcaoLinha">
            <input
              type="checkbox"
              checked={somenteDoPaciente}
              onChange={(evento) => setSomenteDoPaciente(evento.target.checked)}
              disabled={!selecionado}
            />
            Somente o paciente em foco
          </label>
          <button type="button" className="logoutBtn" onClick={carregar}>
            Atualizar
          </button>
        </div>
      </section>

      <section className="panel">
        <h3 className="panelTitle">
          Avaliacoes ({lista.itens.length})
          <Origem tipo="api" />
        </h3>

        {lista.carregando ? (
          <Carregando texto="Carregando historico..." />
        ) : lista.erro ? (
          <Falha erro={lista.erro} aoTentarDeNovo={carregar} />
        ) : !lista.itens.length ? (
          <Vazio titulo="Nenhuma avaliacao registrada">
            {somenteDoPaciente
              ? "Este paciente ainda nao foi avaliado."
              : "Ainda nao ha avaliacoes no sistema."}{" "}
            <Link to="/avaliacao">Fazer uma avaliacao</Link>.
          </Vazio>
        ) : (
          <div className="list">
            {lista.itens.map((item) => (
              <ItemDoHistorico
                key={item.id_execucao}
                item={item}
                ativo={detalhe.id === item.id_execucao}
                aoAbrir={abrir}
              />
            ))}
          </div>
        )}
      </section>

      {detalhe.id && (
        <section className="panel">
          <h3 className="panelTitle">
            Detalhe da execucao
            <Origem tipo="api" />
          </h3>

          {detalhe.carregando ? (
            <Carregando texto="Carregando o registro..." linhas={2} />
          ) : detalhe.erro ? (
            <Falha erro={detalhe.erro} aoTentarDeNovo={() => abrir(detalhe.id)} />
          ) : (
            <DetalheDaExecucao envelope={detalhe.envelope} />
          )}
        </section>
      )}
    </div>
  );
}

/** Busca a lista de avaliacoes. **Nao** mexe em estado (seguro dentro de efeito). */
async function buscarHistorico(idPaciente) {
  const envelope = await listarAvaliacoes({ limite: 50, idPaciente });
  return {
    carregando: false,
    erro: null,
    itens: Array.isArray(envelope.dados) ? envelope.dados : [],
  };
}

function estadoDeFalha(falha) {
  return { carregando: false, erro: falha, itens: [] };
}

/** Uma linha do historico — o resumo ja traz probabilidade e classificacao. */
function ItemDoHistorico({ item, ativo, aoAbrir }) {
  const classificacao = CLASSIFICACOES_DE_RISCO[item.classificacao_risco];
  return (
    <button
      type="button"
      className={`listItem listItem--clicavel ${ativo ? "listItem--ativo" : ""}`}
      onClick={() => aoAbrir(item.id_execucao)}
    >
      <div>
        <div className="listItemTitle">
          {formatarData(item.criado_em)}
          <span className={`selo selo--${classificacao?.tom ?? "neutro"}`}>
            {classificacao?.rotulo ?? item.classificacao_risco ?? "--"}
          </span>
        </div>
        <div className="mono helper">{item.id_execucao}</div>
        <div className="helper">
          modo {MODOS_DO_PIPELINE[item.modo]?.rotulo ?? item.modo} · origem{" "}
          {item.origem_dos_dados} · {STATUS_DA_RESPOSTA[item.status] ?? item.status}
        </div>
      </div>
      <div style={{ textAlign: "right" }}>
        <div className="riscoValor riscoValor--pequeno">
          {typeof item.probabilidade_risco === "number"
            ? `${(item.probabilidade_risco * 100).toFixed(1)}%`
            : "--"}
        </div>
        <div className="helper">probabilidade</div>
      </div>
    </button>
  );
}

/** Resumo auditavel da execucao + o contrato da Fase 6 que ficou persistido. */
function DetalheDaExecucao({ envelope }) {
  const registro = envelope?.dados;
  if (!registro) return <Vazio titulo="Registro indisponivel" />;

  const erros = registro.resposta?.erros ?? [];

  return (
    <div className="stack">
      <div className="linhaChaveValor">
        <span className="helper">id_execucao</span>
        <span className="mono">{registro.id_execucao}</span>
      </div>
      <div className="linhaChaveValor">
        <span className="helper">id_paciente</span>
        <span className="mono">{registro.id_paciente}</span>
      </div>
      <div className="linhaChaveValor">
        <span className="helper">Registrado em</span>
        <span>{formatarData(registro.criado_em)}</span>
      </div>
      <div className="linhaChaveValor">
        <span className="helper">Status</span>
        <span className="etiqueta">
          {STATUS_DA_RESPOSTA[registro.status] ?? registro.status}
        </span>
      </div>
      <div className="linhaChaveValor">
        <span className="helper">SHA-256 da base de treino</span>
        <span className="mono helper">{registro.sha256_da_base_usada ?? "--"}</span>
      </div>

      <NivelDeRisco diagnostico={registro.resposta?.diagnostico} />
      <DetalhesDoContrato contrato={registro.resposta} />

      {erros.length > 0 && (
        <div className="bloco bloco--aviso">
          <div className="blocoTitulo">Erros registrados na execucao</div>
          <ul className="listaSimples">
            {erros.map((texto, indice) => (
              <li key={indice}>{typeof texto === "string" ? texto : texto.mensagem}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function formatarData(iso) {
  if (!iso) return "--";
  const data = new Date(iso);
  return Number.isNaN(data.getTime()) ? String(iso) : data.toLocaleString("pt-BR");
}

