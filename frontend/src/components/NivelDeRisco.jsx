import { CLASSIFICACOES_DE_RISCO } from "../dominio/catalogo";

/**
 * Resultado de risco do paciente.
 *
 * ⚠️ **A classificacao vem do backend**, nao de um limiar calculado aqui. O contrato
 * da Fase 6 ja decide `sem_pico_de_risco` / `pico_de_risco` com o limiar do proprio
 * modelo; recalcular no frontend criaria uma segunda fonte de verdade — exatamente o
 * que o projeto proibe.
 *
 * A barra apenas **visualiza** a probabilidade crua (0–1), sem arredondar na origem.
 */
export default function NivelDeRisco({ diagnostico, compacto = false }) {
  if (!diagnostico) {
    return (
      <div className="estado estado--vazio">
        <div className="estadoTitulo">Sem resultado de risco</div>
        <p>Este paciente ainda nao tem avaliacao registrada.</p>
      </div>
    );
  }

  const probabilidade = diagnostico.probabilidade_risco;
  const classificacao = CLASSIFICACOES_DE_RISCO[diagnostico.classificacao_risco];
  const tom = classificacao?.tom ?? "neutro";
  const pico = diagnostico.pico_risco_previsto === 1;

  const percentual = typeof probabilidade === "number" ? probabilidade * 100 : null;

  return (
    <div className={`risco risco--${tom} ${compacto ? "risco--compacto" : ""}`}>
      <div className="riscoTopo">
        <div>
          <div className="riscoRotulo">Probabilidade de pico de risco</div>
          <div className="riscoValor">
            {percentual === null ? "--" : `${percentual.toFixed(1)}%`}
          </div>
        </div>
        <span className={`selo selo--${tom}`}>{classificacao?.rotulo ?? diagnostico.classificacao_risco}</span>
      </div>

      <div className="medidor" aria-hidden="true">
        <div className={`medidorPreenchimento medidorPreenchimento--${tom}`} style={{ width: `${percentual ?? 0}%` }} />
      </div>

      {!compacto && (
        <details className="bloco bloco--limitacoes" style={{ marginTop: 12 }}>
          <summary>Detalhes do modelo</summary>
          <div className="riscoDetalhes">
            <Linha rotulo="Pico previsto" valor={pico ? "sim" : "nao"} />
            <Linha rotulo="Modelo" valor={diagnostico.modelo_utilizado} />
            <Linha rotulo="Limiar de decisao" valor={diagnostico.limiar_decisao} />
            <Linha rotulo="Regra de decisao" valor={diagnostico.regra_de_decisao} />
            <Linha rotulo="Estimador" valor={diagnostico.classe_do_estimador} />
            <Linha rotulo="Origem do modelo" valor={diagnostico.origem_do_modelo} />
          </div>
        </details>
      )}
    </div>
  );
}

function Linha({ rotulo, valor }) {
  if (valor === null || valor === undefined || valor === "") return null;
  return (
    <div className="linhaChaveValor">
      <span className="helper">{rotulo}</span>
      <span className="mono">{String(valor)}</span>
    </div>
  );
}
