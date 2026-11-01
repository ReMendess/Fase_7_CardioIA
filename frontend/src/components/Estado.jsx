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

/**
 * Avisos do envelope (faixas do modelo, confiabilidade, alertas das regras da Fase 3).
 *
 * **Recolhido por padrao.** O aviso continua a um clique, mas nao ocupa a tela: quem
 * abre a pagina quer o dado, nao a lista de ressalvas. O contrato exige que os avisos
 * existam na resposta — e existem, apenas sob demanda.
 */
export function Avisos({ itens, titulo = "Avisos" }) {
  if (!itens?.length) return null;
  return (
    <details className="bloco bloco--aviso">
      <summary>
        {titulo} ({itens.length})
      </summary>
      <ul className="listaSimples">
        {itens.map((texto, indice) => (
          <li key={indice}>{texto}</li>
        ))}
      </ul>
    </details>
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

