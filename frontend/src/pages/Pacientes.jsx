import { useState } from "react";
import { Link } from "react-router-dom";
import { Carregando, Falha, Vazio } from "../components/Estado";
import { useAuth } from "../contexts/AuthContext";
import { usePacientes } from "../contexts/PacienteContext";
import { mensagemDoErro } from "../api/cliente";

/**
 * Cadastro e consulta de pacientes.
 *
 * ⚠️ O cadastro guarda **apenas a identidade** (resposta Q1): as 10 features do modelo
 * sao estado clinico **datado** e vivem em cada avaliacao. Por isso esta tela nao tem
 * nenhum campo clinico — e nao e uma omissao.
 *
 * `POST /pacientes` exige papel `MEDICO`; `ADMIN` e `OPERADOR` recebem `403`. O
 * formulario so aparece para quem pode usar (o backend continua sendo a autoridade).
 */
export default function Pacientes() {
  const { podeEscreverClinico } = useAuth();
  const { pacientes, selecionado, selecionar, carregando, erro, recarregar, cadastrar } =
    usePacientes();

  const [nome, setNome] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [falha, setFalha] = useState(null);

  async function enviar(evento) {
    evento.preventDefault();
    setFalha(null);
    setSalvando(true);
    try {
      await cadastrar(nome);
      setNome("");
    } catch (problema) {
      setFalha(problema);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="stack" style={{ gap: 18 }}>
      {podeEscreverClinico && (
        <section className="panel">
          <h3 className="panelTitle">Novo paciente</h3>
          <form className="stack" onSubmit={enviar}>
            <div>
              <label className="seletorRotulo" htmlFor="nome-paciente">
                Nome
              </label>
              <input
                id="nome-paciente"
                placeholder="Ex.: Maria Silva (dado ficticio)"
                value={nome}
                onChange={(evento) => setNome(evento.target.value)}
                maxLength={120}
                required
              />
              <div className="helper">
                Somente identidade. Os dados clinicos entram na avaliacao, um por vez.
              </div>
            </div>
            <div className="row">
              <button type="submit" disabled={salvando || !nome.trim()}>
                {salvando ? "Cadastrando..." : "Cadastrar"}
              </button>
            </div>
            {falha && <p className="errorText">{mensagemDoErro(falha)}</p>}
          </form>
        </section>
      )}

      {!podeEscreverClinico && (
        <section className="panel">
          <p className="helper">Sua conta pode consultar pacientes, mas nao cadastrar.</p>
        </section>
      )}

      <section className="panel">
        <div className="painelTopo">
          <h3 className="panelTitle">Pacientes ({pacientes.length})</h3>
          <button type="button" className="logoutBtn" onClick={recarregar}>
            Atualizar
          </button>
        </div>

        {carregando ? (
          <Carregando texto="Carregando pacientes..." />
        ) : erro ? (
          <Falha erro={erro} aoTentarDeNovo={recarregar} />
        ) : !pacientes.length ? (
          <Vazio titulo="Nenhum paciente cadastrado">
            {podeEscreverClinico
              ? "Use o formulario acima para cadastrar o primeiro."
              : "Peca a um usuario MEDICO para cadastrar."}
          </Vazio>
        ) : (
          <div className="list">
            {pacientes.map((paciente) => (
              <div
                className={`listItem ${selecionado?.id_paciente === paciente.id_paciente ? "listItem--ativo" : ""}`}
                key={paciente.id_paciente}
              >
                <div>
                  <div className="listItemTitle">{paciente.nome}</div>
                  <div className="mono helper">{paciente.id_paciente}</div>
                  <div className="helper">Cadastrado em {formatarData(paciente.criado_em)}</div>
                </div>
                <div className="row">
                  <span className={`pill ${paciente.ativo ? "" : "pill--inativo"}`}>
                    {paciente.ativo ? "Ativo" : "Inativo"}
                  </span>
                  {selecionado?.id_paciente === paciente.id_paciente ? (
                    <span className="etiqueta etiqueta--api">em foco</span>
                  ) : (
                    <button type="button" className="logoutBtn" onClick={() => selecionar(paciente)}>
                      Selecionar
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {pacientes.length > 0 && (
          <p className="helper" style={{ marginTop: 12 }}>
            O paciente em foco alimenta o <Link to="/dashboard">Dashboard</Link>, o{" "}
            <Link to="/historico">Historico</Link> e a{" "}
            <Link to="/avaliacao">Avaliacao</Link>.
          </p>
        )}
      </section>
    </div>
  );
}

function formatarData(iso) {
  if (!iso) return "--";
  const data = new Date(iso);
  return Number.isNaN(data.getTime()) ? String(iso) : data.toLocaleString("pt-BR");
}
