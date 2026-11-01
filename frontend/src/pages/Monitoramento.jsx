import { useEffect, useState } from "react";
import { listarLeituras } from "../api/endpoints";
import { Carregando, Falha, Limitacoes, Origem, Vazio } from "../components/Estado";
import { useAuth } from "../contexts/AuthContext";
import { ORIGENS_DO_TRANSPORTE } from "../dominio/catalogo";

/**
 * Telemetria IoT (Fase 3).
 *
 * Duas limitacoes do contrato que a tela **nao** esconde:
 *
 * 1. `DadosDeMonitoramento` **nao tem `id_paciente`** — as leituras sao dos
 *    dispositivos, nao de um paciente. Amostra-las sob o nome de alguem seria mentir;
 * 2. o alerta das regras da Fase 3 (`FEBRE DETECTADA`, `TAQUICARDIA DETECTADA`,
 *    `AUSENCIA DE MOVIMENTO`) **nao e persistido** — ele so aparece em `avisos` na
 *    resposta da ingestao. No historico, a tela mostra os sinais brutos e diz isso.
 *
 * A tela tambem **nao recalcula** a regra: duplicar o limiar aqui criaria uma segunda
 * fonte de verdade clinica.
 */
export default function Monitoramento() {
  const { papel } = useAuth();
  const [dispositivo, setDispositivo] = useState("");
  const [estado, setEstado] = useState({
    carregando: true,
    erro: null,
    itens: [],
    limitacoes: [],
  });

  const filtro = dispositivo.trim() || null;

  // O efeito so dispara a busca; o estado e atualizado no callback (sem render em cascata).
  useEffect(() => {
    let cancelado = false;
    buscarLeituras(filtro)
      .then((proximo) => {
        if (!cancelado) setEstado(proximo);
      })
      .catch((falha) => {
        if (!cancelado) setEstado(estadoDeFalha(falha));
      });
    return () => {
      cancelado = true;
    };
  }, [filtro]);

  /** Recarrega sob demanda (botao). */
  async function carregar() {
    setEstado((atual) => ({ ...atual, carregando: true, erro: null }));
    try {
      setEstado(await buscarLeituras(filtro));
    } catch (falha) {
      setEstado(estadoDeFalha(falha));
    }
  }

  const podeLer = papel === "OPERADOR" || papel === "MEDICO";

  return (
    <div className="stack" style={{ gap: 18 }}>
      <section className="panel">
        <div className="painelTopo">
          <div>
            <h2 className="pageTitle">Monitoramento IoT</h2>
            <p className="helper">
              Leituras recebidas por <span className="mono">POST /iot/leituras</span>{" "}
              (firmware da Fase 3 via MQTT ou REST).
            </p>
          </div>
          <Origem tipo="api" />
        </div>

        <div className="bloco bloco--aviso" style={{ marginTop: 12 }}>
          <div className="blocoTitulo">Antes de ler os numeros</div>
          <ul className="listaSimples">
            <li>
              ⚠️ As leituras <strong>nao sao vinculadas a paciente</strong> no contrato
              §4.2 — sao de dispositivos.
            </li>
            <li>
              ⚠️ O alerta das regras da Fase 3 <strong>nao e persistido</strong>. Ele so
              vem em <code>avisos</code> na resposta da ingestao; aqui aparecem os sinais
              brutos.
            </li>
            <li>
              ⚠️ O firmware <strong>nao envia</strong> identificador nem timestamp:{" "}
              <code>id_dispositivo</code> e exigido pela API e <code>recebido_em</code> e
              carimbado pelo backend.
            </li>
          </ul>
        </div>

        <div className="row" style={{ marginTop: 12 }}>
          <input
            placeholder="Filtrar por id_dispositivo (ex.: esp32-01)"
            value={dispositivo}
            onChange={(evento) => setDispositivo(evento.target.value)}
            maxLength={64}
          />
          <button type="button" className="logoutBtn" onClick={carregar}>
            Atualizar
          </button>
        </div>
      </section>

      {!podeLer ? (
        <section className="panel">
          <p className="helper">
            Seu papel (<span className="mono">{papel}</span>) nao pode ler telemetria — o
            contrato §8 exige <span className="mono">OPERADOR</span> ou{" "}
            <span className="mono">MEDICO</span>.
          </p>
        </section>
      ) : (
        <section className="panel">
          <h3 className="panelTitle">
            Leituras ({estado.itens.length})
            <Origem tipo="api" />
          </h3>

          {estado.carregando ? (
            <Carregando texto="Carregando telemetria..." />
          ) : estado.erro ? (
            <Falha erro={estado.erro} aoTentarDeNovo={carregar} />
          ) : !estado.itens.length ? (
            <Vazio titulo="Nenhuma leitura encontrada">
              Nada recebido ainda. A ingestao e <code>POST /iot/leituras</code>, aceitando
              a chave de dispositivo (<code>X-Device-Key</code>) ou um usuario{" "}
              <span className="mono">OPERADOR</span>. Use o exemplo abaixo.
            </Vazio>
          ) : (
            <div className="list">
              {estado.itens.map((leitura) => (
                <LinhaDeLeitura key={leitura.id_leitura} leitura={leitura} />
              ))}
            </div>
          )}
        </section>
      )}

      <Limitacoes itens={estado.limitacoes} />

      <section className="panel">
        <h3 className="panelTitle">Enviar uma leitura de teste</h3>
        <p className="helper">
          A ingestao aceita a chave de dispositivo ou um usuario{" "}
          <span className="mono">OPERADOR</span> (<span className="mono">MEDICO</span> e{" "}
          <span className="mono">ADMIN</span> recebem <span className="mono">403</span> —
          ingestao nao e ato clinico). Exemplo com <code>curl</code>:
        </p>
        <pre className="blocoCodigo">{`curl -X POST "$API/api/v1/iot/leituras" \\
  -H "X-Device-Key: $IOT_DEVICE_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"id_dispositivo":"esp32-teste","origem_transporte":"rest","temperatura":38.9,"bpm":132}'`}</pre>
        <p className="helper">
          A resposta traz <code>avisos</code> com o alerta das regras da Fase 3, se houver.
          Depois de enviar, clique em <strong>Atualizar</strong>.
        </p>
      </section>
    </div>
  );
}

/** Busca as leituras. **Nao** mexe em estado (seguro dentro de efeito). */
async function buscarLeituras(idDispositivo) {
  const envelope = await listarLeituras({ limite: 50, idDispositivo });
  return {
    carregando: false,
    erro: null,
    itens: Array.isArray(envelope.dados) ? envelope.dados : [],
    limitacoes: envelope.limitacoes ?? [],
  };
}

function estadoDeFalha(falha) {
  return { carregando: false, erro: falha, itens: [], limitacoes: [] };
}

function LinhaDeLeitura({ leitura }) {
  return (
    <div className="listItem">
      <div>
        <div className="listItemTitle">{leitura.id_dispositivo}</div>
        <div className="helper">
          recebido em {formatarData(leitura.recebido_em)} ·{" "}
          {ORIGENS_DO_TRANSPORTE[leitura.origem_transporte] ?? leitura.origem_transporte}
        </div>
        <div className="mono helper">{leitura.id_leitura}</div>
      </div>
      <div className="row" style={{ flexWrap: "wrap" }}>
        <Sinal rotulo="Temp." valor={leitura.temperatura} unidade="°C" />
        <Sinal rotulo="BPM" valor={leitura.bpm} unidade="bpm" />
        <Sinal rotulo="Umid." valor={leitura.umidade} unidade="%" />
        <Sinal rotulo="Luz" valor={leitura.luminosidade} unidade="lx" />
        {leitura.movimento != null && (
          <span className={`pill ${leitura.movimento ? "" : "pill--inativo"}`}>
            movimento: {leitura.movimento ? "sim" : "nao"}
          </span>
        )}
      </div>
    </div>
  );
}

function Sinal({ rotulo, valor, unidade }) {
  if (valor === null || valor === undefined) return null;
  return (
    <span className="pill">
      {rotulo} {valor} {unidade}
    </span>
  );
}

function formatarData(iso) {
  if (!iso) return "--";
  const data = new Date(iso);
  return Number.isNaN(data.getTime()) ? String(iso) : data.toLocaleString("pt-BR");
}

