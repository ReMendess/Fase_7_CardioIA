import { PAPEIS_DA_MENSAGEM } from "../dominio/catalogo";

/** Sugestoes iniciais (as mesmas do app da Fase 5). */
const SUGESTOES = [
  "O que voce faz?",
  "Dor no peito",
  "Quais sintomas devo observar?",
];

/** A janela de conversa: mensagens, indicador de digitacao e o estado vazio. */
export function BolhasDoChat({ mensagens, enviando, falha, fimDaLista, aoSugerir }) {
  return (
    <div className="janelaChat" role="log" aria-live="polite">
      {mensagens.length === 0 && !falha && (
        <div className="estado estado--vazio">
          <div className="estadoTitulo">Comece a conversa</div>
          <p>
            Perguntas sobre saude cardiovascular. As respostas <strong>nao</strong> sao
            diagnostico, prescricao ou recomendacao medica.
          </p>
          <div className="row" style={{ flexWrap: "wrap", marginTop: 10 }}>
            {SUGESTOES.map((sugestao) => (
              <button
                key={sugestao}
                type="button"
                className="logoutBtn"
                onClick={() => aoSugerir(sugestao)}
              >
                {sugestao}
              </button>
            ))}
          </div>
        </div>
      )}

      {mensagens.map((mensagem, indice) => (
        <div className={`bolha bolha--${mensagem.papel}`} key={indice}>
          <div className="bolhaAutor">
            {PAPEIS_DA_MENSAGEM[mensagem.papel] ?? mensagem.papel}
          </div>
          <div className="bolhaTexto">{mensagem.conteudo}</div>
          {mensagem.papel === "assistant" && mensagem.fontes?.length > 0 && (
            <div className="bolhaFontes helper">fontes: {mensagem.fontes.join(", ")}</div>
          )}
        </div>
      ))}

      {enviando && (
        <div className="bolha bolha--assistant bolha--digitando">
          <span className="pontos" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          <span className="helper">consultando o assistente...</span>
        </div>
      )}

      <div ref={fimDaLista} />
    </div>
  );
}

/**
 * `501 NAO_CONFIGURADO` — estado declarado, nao defeito.
 *
 * Explica **por que** o backend recusa: ele nao usa os valores default do `IBM_API.py`
 * da Fase 5 (que traz a chave do projeto versionada).
 */
export function AvisoDeNaoConfigurado({ falha }) {
  return (
    <div className="estado estado--aviso" role="status">
      <div className="estadoTitulo">Assistente nao configurado neste servidor</div>
      <p>{falha.mensagem}</p>
      {falha.detalhe && <p className="helper">{falha.detalhe}</p>}
      <p className="helper">
        Defina <span className="mono">WATSON_API_KEY</span>,{" "}
        <span className="mono">WATSON_SERVICE_URL</span>,{" "}
        <span className="mono">WATSON_ASSISTANT_ID</span> e{" "}
        <span className="mono">WATSON_ENVIRONMENT_ID</span> no ambiente do backend.
      </p>
    </div>
  );
}

/** `403` — o papel do usuario nao permite usar o assistente. */
export function AvisoDePermissao({ mensagem }) {
  return (
    <section className="panel">
      <div className="estado estado--falha" role="alert">
        <div className="estadoTitulo">Seu papel nao permite usar o assistente</div>
        <p>{mensagem}</p>
      </div>
    </section>
  );
}
