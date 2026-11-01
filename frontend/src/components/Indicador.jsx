import { foraDaFaixa } from "../dominio/catalogo";

/**
 * Indicador de uma feature do modelo.
 *
 * A barra mostra o valor **dentro da faixa observada no treino**. Um valor fora da faixa
 * nao e erro: gera aviso, nao recusa — e o selo "fora da faixa" existe para o numero nao
 * parecer mais confiavel do que e.
 *
 * As observacoes de escala e confianca (8 das 10 features nao sao medicoes individuais do
 * paciente) ficam no **tooltip**, nao na tela: sao contexto, e repeti-las em cada um dos
 * 10 cartoes virava ruido.
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
    <div className="indicador" title={dicaDaFeature(feature)}>
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
        {fora && <span className="etiqueta etiqueta--fora">fora da faixa</span>}
      </div>
    </div>
  );
}

/** Contexto da feature, exibido no tooltip: descricao + escala + confianca. */
function dicaDaFeature(feature) {
  const partes = [feature.ajuda];

  if (feature.escala === "episodio") {
    partes.push("Descreve o episodio assistencial, nao o paciente.");
  }
  if (feature.confianca === "baixa") {
    partes.push("Feature de baixa confianca no modelo.");
  }

  return partes.filter(Boolean).join(" ");
}

/** Numero curto: inteiro sem casas, fracionario com ate 3. */
function formatar(valor) {
  if (Number.isInteger(valor)) return String(valor);
  return valor.toFixed(3).replace(/\.?0+$/, "");
}
