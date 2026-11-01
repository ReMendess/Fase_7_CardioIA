import { useReducer } from "react";
import { Link } from "react-router-dom";
import { Origem } from "../components/Estado";

/**
 * Agenda — **tela demonstrativa**.
 *
 * ⚠️ **Nao existe endpoint de agenda no contrato §8.** Esta tela foi mantida do app da
 * Fase 2 (ela era um exercicio de `useReducer`) e esta rotulada como demonstrativa de
 * proposito: um botao que "agenda" sem persistir nada precisa dizer que nao persiste.
 *
 * Substituir por dado real exigiria criar recurso novo no backend — fora do escopo do
 * MVP acordado.
 */
const estadoInicial = { paciente: "", data: "", confirmado: null };

function redutor(estado, acao) {
  switch (acao.type) {
    case "CAMPO":
      return { ...estado, [acao.campo]: acao.valor };
    case "CONFIRMAR":
      return { ...estado, confirmado: { ...estado } };
    case "LIMPAR":
      return estadoInicial;
    default:
      return estado;
  }
}

export default function Agenda() {
  const [estado, despachar] = useReducer(redutor, estadoInicial);

  function enviar(evento) {
    evento.preventDefault();
    despachar({ type: "CONFIRMAR" });
  }

  return (
    <div className="stack" style={{ gap: 18 }}>
      <section className="panel">
        <div className="painelTopo">
          <div>
            <h2 className="pageTitle">Agenda</h2>
            <p className="helper">Rascunho local de agendamento.</p>
          </div>
          <Origem tipo="demonstrativo">Demonstrativo — nao persiste</Origem>
        </div>

        <div className="bloco bloco--aviso" style={{ marginTop: 12 }}>
          <div className="blocoTitulo">Esta tela nao grava nada</div>
          <p>
            A API da Fase 7 <strong>nao tem</strong> recurso de agenda. O formulario abaixo
            exercita o estado local (o mesmo <code>useReducer</code> do app da Fase 2) e o
            registro vive apenas enquanto a pagina estiver aberta. Nada e enviado ao
            backend.
          </p>
        </div>
      </section>

      <section className="panel">
        <form className="stack" onSubmit={enviar}>
          <div>
            <label className="seletorRotulo" htmlFor="agenda-paciente">
              Paciente
            </label>
            <input
              id="agenda-paciente"
              placeholder="Ex.: Maria Silva"
              value={estado.paciente}
              onChange={(evento) =>
                despachar({ type: "CAMPO", campo: "paciente", valor: evento.target.value })
              }
            />
            <div className="helper">Texto livre — nao ha vinculo com o cadastro.</div>
          </div>

          <div>
            <label className="seletorRotulo" htmlFor="agenda-data">
              Data
            </label>
            <input
              id="agenda-data"
              type="date"
              value={estado.data}
              onChange={(evento) =>
                despachar({ type: "CAMPO", campo: "data", valor: evento.target.value })
              }
            />
          </div>

          <div className="row">
            <button type="submit" disabled={!estado.paciente.trim() || !estado.data}>
              Registrar rascunho
            </button>
            <button
              type="button"
              className="logoutBtn"
              onClick={() => despachar({ type: "LIMPAR" })}
            >
              Limpar
            </button>
          </div>
        </form>

        {estado.confirmado && (
          <div className="mutedBox" style={{ marginTop: 14 }}>
            Rascunho registrado localmente: <strong>{estado.confirmado.paciente}</strong> em{" "}
            <strong>{estado.confirmado.data}</strong>. Nada foi enviado ao backend — ao
            recarregar a pagina, este registro desaparece.
          </div>
        )}
      </section>

      <section className="panel">
        <h3 className="panelTitle">Onde estao os dados de verdade</h3>
        <p className="helper">
          O que a API realmente oferece: <Link to="/pacientes">pacientes</Link>,{" "}
          <Link to="/avaliacao">avaliacoes de risco</Link>,{" "}
          <Link to="/historico">historico</Link>,{" "}
          <Link to="/monitoramento">telemetria IoT</Link> e{" "}
          <Link to="/assistente">assistente</Link>.
        </p>
      </section>
    </div>
  );
}
