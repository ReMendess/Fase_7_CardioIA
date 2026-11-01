import { useEffect, useRef, useState } from "react";
import { enviarMensagem, historicoDaConversa } from "../api/endpoints";
import { ErroDaAPI, mensagemDoErro } from "../api/cliente";
import { Limitacoes, Origem } from "../components/Estado";
import { BolhasDoChat, AvisoDeNaoConfigurado, AvisoDePermissao } from "../components/JanelaDoChat";
import { useAuth } from "../contexts/AuthContext";

/**
 * Assistente conversacional (Fase 5).
 *
 * Pontos que a tela precisa deixar claros:
 *
 * - o Watson Assistant pode **nao estar configurado** no servidor. Nesse caso a API
 *   responde `501 NAO_CONFIGURADO` — e isso **nao e um bug**: e um estado declarado,
 *   porque o backend recusa usar as credenciais default do codigo da Fase 5;
 * - `ADMIN` recebe `403` (o contrato exige `OPERADOR` ou `MEDICO`);
 * - `fontes` e **sempre vazio** (nota N6) — a tela nao inventa fontes;
 * - o `session_id` do Watson nunca chega aqui: o identificador e o `id_conversa`.
 */
export default function Assistente() {
  const { usuario } = useAuth();

  const [mensagens, setMensagens] = useState([]);
  const [texto, setTexto] = useState("");
  const [idConversa, setIdConversa] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [falha, setFalha] = useState(null);
  const [limitacoes, setLimitacoes] = useState([]);
  const fimDaLista = useRef(null);

  useEffect(() => {
    fimDaLista.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensagens]);

  async function enviar(evento, sugestao) {
    evento?.preventDefault();
    const conteudo = (sugestao ?? texto).trim();
    if (!conteudo || enviando) return;

    setFalha(null);
    setTexto("");
    setMensagens((atuais) => [...atuais, { papel: "user", conteudo }]);
    setEnviando(true);

    try {
      const envelope = await enviarMensagem(conteudo, idConversa);
      const resposta = envelope.dados;
      setIdConversa(resposta.id_conversa);
      setLimitacoes(envelope.limitacoes ?? []);
      setMensagens((atuais) => [
        ...atuais,
        {
          papel: "assistant",
          conteudo: resposta.resposta,
          criadoEm: resposta.criado_em,
          // `fontes` e sempre [] — mantido explicito para a tela nao sugerir o contrario.
          fontes: resposta.fontes ?? [],
        },
      ]);
    } catch (problema) {
      setFalha(problema);
      // O turno falhou: devolve o texto ao campo para o usuario nao perder o que escreveu.
      setTexto(conteudo);
    } finally {
      setEnviando(false);
    }
  }

  /** Recarrega o historico da conversa atual a partir do backend. */
  async function recarregarHistorico() {
    if (!idConversa) return;
    try {
      const envelope = await historicoDaConversa(idConversa);
      const turnos = Array.isArray(envelope.dados) ? envelope.dados : [];
      setMensagens(
        turnos.map((turno) => ({
          papel: turno.papel,
          conteudo: turno.conteudo,
          criadoEm: turno.criado_em,
        }))
      );
      setLimitacoes(envelope.limitacoes ?? []);
      setFalha(null);
    } catch (problema) {
      setFalha(problema);
    }
  }

  const naoConfigurado = falha instanceof ErroDaAPI && falha.naoConfigurado;
  const semPermissao = falha instanceof ErroDaAPI && falha.semPermissao;

  return (
    <div className="stack" style={{ gap: 18 }}>
      <section className="panel">
        <div className="painelTopo">
          <div>
            <h2 className="pageTitle">Assistente CardioIA</h2>
            <p className="helper">
              Assistente virtual (IBM Watson Assistant) · papel{" "}
              <span className="mono">{usuario?.papel}</span>
            </p>
          </div>
          <Origem tipo="api" />
        </div>
      </section>

      {semPermissao && <AvisoDePermissao mensagem={falha.mensagem} />}

      {!semPermissao && (
        <section className="panel painelChat">
          <BolhasDoChat
            mensagens={mensagens}
            enviando={enviando}
            falha={falha}
            fimDaLista={fimDaLista}
            aoSugerir={(sugestao) => enviar(null, sugestao)}
          />

          {naoConfigurado && <AvisoDeNaoConfigurado falha={falha} />}

          {falha && !naoConfigurado && !semPermissao && (
            <div className="estado estado--falha" role="alert">
              <div className="estadoTitulo">Falha ao falar com o assistente</div>
              <p>{mensagemDoErro(falha)}</p>
              {falha.codigo && (
                <span className="etiqueta etiqueta--codigo">{falha.codigo}</span>
              )}
            </div>
          )}

          <form className="row" onSubmit={enviar} style={{ marginTop: 12 }}>
            <input
              placeholder="Escreva sua pergunta..."
              value={texto}
              onChange={(evento) => setTexto(evento.target.value)}
              maxLength={2000}
              disabled={enviando}
            />
            <button type="submit" disabled={enviando || !texto.trim()}>
              Enviar
            </button>
          </form>

          {idConversa && (
            <div className="row" style={{ marginTop: 10 }}>
              <span className="helper">
                conversa <span className="mono">{idConversa}</span>
              </span>
              <button type="button" className="logoutBtn" onClick={recarregarHistorico}>
                Recarregar historico
              </button>
            </div>
          )}
        </section>
      )}

      <Limitacoes itens={limitacoes} />
    </div>
  );
}
