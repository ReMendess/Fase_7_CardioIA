/**
 * Estados de tela (item 3 da Etapa D): carregando, erro, vazio — e os blocos de
 * `avisos`/`limitacoes` que o contrato exige nas respostas de decisao automatizada.
 */

/** Placeholder enquanto os dados nao chegam. */
export function Carregando({ texto = "Carregando...", linhas = 3 }) {
  return (
    <div className="estado" role="status" aria-live="polite">
      <div className="estadoTitulo">
        <span className="spinner" aria-hidden="true" />
        {texto}
      </div>
      <div className="esqueleto">
        {Array.from({ length: linhas }).map((_, indice) => (
          <div className="esqueletoLinha" key={indice} />
        ))}
      </div>
    </div>
  );
}

/**
 * Falha na chamada.
 *
 * `detalhe` mostra o `codigo` estavel do contrato — e o que permite distinguir
 * "backend fora do ar" de "sem permissao" de "servico externo indisponivel".
 */
export function Falha({ erro, aoTentarDeNovo = null }) {
  const codigo = erro?.codigo;
  const detalhe = erro?.detalhe;

  return (
    <div className="estado estado--falha" role="alert">
      <div className="estadoTitulo">
        <span className="marca marca--alerta" aria-hidden="true" />
        Nao foi possivel carregar
      </div>
      <p>{erro?.mensagem || erro?.message || "Falha inesperada."}</p>
      {detalhe && <p className="helper">{detalhe}</p>}
      <div className="row" style={{ marginTop: 10 }}>
        {codigo && <span className="etiqueta etiqueta--codigo">{codigo}</span>}
        {aoTentarDeNovo && (
          <button type="button" onClick={aoTentarDeNovo}>
            Tentar de novo
          </button>
        )}
      </div>
    </div>
  );
}

/** Ausencia de dados — nunca confundir com erro. */
export function Vazio({ titulo = "Nada por aqui ainda", children }) {
  return (
    <div className="estado estado--vazio">
      <div className="estadoTitulo">{titulo}</div>
      {children && <p>{children}</p>}
    </div>
  );
}

/** Avisos do envelope (faixas do modelo, confiabilidade, alertas das regras da Fase 3). */
export function Avisos({ itens, titulo = "Avisos" }) {
  if (!itens?.length) return null;
  return (
    <div className="bloco bloco--aviso">
      <div className="blocoTitulo">{titulo}</div>
      <ul className="listaSimples">
        {itens.map((texto, indice) => (
          <li key={indice}>{texto}</li>
        ))}
      </ul>
    </div>
  );
}

/** Limitacoes declaradas — o contrato exige que nunca fiquem vazias numa decisao. */
export function Limitacoes({ itens }) {
  if (!itens?.length) return null;
  return (
    <details className="bloco bloco--limitacoes">
      <summary>Limitacoes declaradas ({itens.length})</summary>
      <ul className="listaSimples">
        {itens.map((texto, indice) => (
          <li key={indice}>{texto}</li>
        ))}
      </ul>
    </details>
  );
}

/** Selo de origem do dado — separa o que e real, simulado e preditivo (item 3). */
export function Origem({ tipo, children }) {
  const rotulos = {
    api: "Dado da API",
    simulado: "Simulado",
    preditivo: "Resultado preditivo",
    demonstrativo: "Demonstrativo",
  };
  return <span className={`etiqueta etiqueta--${tipo}`}>{children || rotulos[tipo]}</span>;
}
