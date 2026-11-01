import { foraDaFaixa } from "../dominio/catalogo";

/**
 * Indicador de uma feature do modelo.
 *
 * A barra mostra o valor **dentro da faixa observada no treino** (declarada em
 * `CONTRATOS_API.md` §4.1). Um valor fora da faixa **nao** e erro: o contrato diz que
 * isso gera aviso, nao recusa — e a tela precisa deixar isso visivel, senao o numero
 * parece mais confiavel do que e.
 *
 * Os selos de escala/confianca existem por causa dos achados A3 e A4: 8 das 10
 * features nao sao medicoes individuais do paciente.
 */
export default function Indicador({ feature, valor }) {
  const numero = Number(valor);
  const preenchido = valor !== "" && !Number.isNaN(numero);

  const amplitude = feature.maximo - feature.minimo || 1;
  const proporcao = preenchido
    ? Math.min(100, Math.max(0, ((numero - feature.minimo) / amplitude) * 100))
    : 0;

  const fora = foraDaFaixa(feature, valor);

  return (
    <div className="indicador" title={feature.ajuda}>
      <div className="indicadorTopo">
        <span className="indicadorRotulo">{feature.rotulo}</span>
        <span className={`indicadorValor ${fora ? "indicadorValor--fora" : ""}`}>
          {preenchido ? formatar(numero) : "--"}
          {feature.unidade && <span className="indicadorUnidade"> {feature.unidade}</span>}
        </span>
      </div>

      <div className="barra" aria-hidden="true">
        <div
          className={`barraPreenchimento ${fora ? "barraPreenchimento--fora" : ""}`}
          style={{ width: `${proporcao}%` }}
        />
      </div>

      <div className="indicadorPes">
        <span className="helper">
          faixa {formatar(feature.minimo)}–{formatar(feature.maximo)}
        </span>
        <span className="indicadorSelos">
          {feature.escala === "episodio" && (
            <span className="etiqueta etiqueta--episodio" title="Descreve o episodio assistencial, nao o paciente">
              episodio
            </span>
          )}
          {feature.confianca === "baixa" && (
            <span className="etiqueta etiqueta--baixa" title={feature.ajuda}>
              baixa confianca
            </span>
          )}
          {fora && <span className="etiqueta etiqueta--fora">fora da faixa</span>}
        </span>
      </div>
    </div>
  );
}

/** Numero curto: inteiro sem casas, fracionario com ate 3. */
function formatar(valor) {
  if (Number.isInteger(valor)) return String(valor);
  return valor.toFixed(3).replace(/\.?0+$/, "");
}
