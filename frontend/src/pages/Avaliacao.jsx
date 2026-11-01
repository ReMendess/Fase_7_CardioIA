import { useState } from "react";
import { Link } from "react-router-dom";
import { criarAvaliacao } from "../api/endpoints";
import { Carregando, Origem, Vazio } from "../components/Estado";
import { ResultadoDaAvaliacao, ResultadoDaFalha } from "../components/ResultadoDaAvaliacao";
import SeletorDePaciente from "../components/SeletorDePaciente";
import { useAuth } from "../contexts/AuthContext";
import { usePacientes } from "../contexts/PacienteContext";
import {
  FEATURES_DO_MODELO,
  MODOS_DO_PIPELINE,
  ORIGENS_DOS_DADOS,
  exemploPreenchido,
  foraDaFaixa,
  formularioVazio,
} from "../dominio/catalogo";

/**
 * Avaliacao de risco — executa o pipeline da Fase 6 pelo backend.
 *
 * Regra R3 do contrato: **nenhuma das 10 features tem valor padrao**. Por isso o
 * formulario comeca vazio e o botao so libera com as 10 preenchidas — mandar menos
 * devolveria `422 PACIENTE_INVALIDO`, e preencher por conta propria seria inventar
 * dado clinico.
 *
 * O modo `real` chama o provedor LLM e exige `OPENAI_API_KEY` no servidor; sem a
 * chave, a API responde `501 NAO_CONFIGURADO` — o que a tela explica em vez de esconder.
 */
export default function Avaliacao() {
  const { podeEscreverClinico } = useAuth();
  const { selecionado, carregando: carregandoPacientes } = usePacientes();

  const [valores, setValores] = useState(formularioVazio);
  const [origem, setOrigem] = useState("manual");
  const [modo, setModo] = useState("simulado");
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [falha, setFalha] = useState(null);

  const preenchidas = FEATURES_DO_MODELO.filter((f) => valores[f.nome] !== "").length;
  const completo = preenchidas === FEATURES_DO_MODELO.length;

  function atualizar(nome, valor) {
    setValores((atuais) => ({ ...atuais, [nome]: valor }));
  }

  async function enviar(evento) {
    evento.preventDefault();
    setFalha(null);
    setResultado(null);
    setEnviando(true);
    try {
      // Converte para numero: string vazia viraria 0, e o contrato rejeita nao-numerico.
      const features = Object.fromEntries(
        FEATURES_DO_MODELO.map((f) => [f.nome, Number(valores[f.nome])])
      );
      const envelope = await criarAvaliacao({
        idPaciente: selecionado.id_paciente,
        features,
        origemDosDados: origem,
        modo,
      });
      // Guarda tambem o que foi enviado: a API devolve os NOMES das features, nao os
      // valores, entao as barras so podem ser desenhadas com o que o usuario digitou.
      setResultado({ envelope, features });
    } catch (problema) {
      setFalha(problema);
    } finally {
      setEnviando(false);
    }
  }

  if (carregandoPacientes) return <Carregando texto="Carregando pacientes..." />;

  if (!selecionado) {
    return (
      <Vazio titulo="Selecione um paciente">
        A avaliacao precisa de um paciente. Cadastre em{" "}
        <Link to="/pacientes">Pacientes</Link>.
      </Vazio>
    );
  }

  return (
    <div className="stack" style={{ gap: 18 }}>
      <section className="panel">
        <div className="painelTopo">
          <h2 className="pageTitle">Nova avaliacao de risco</h2>
          <SeletorDePaciente compacto />
        </div>
        <p className="helper">
          Executa o pipeline multiagente da Fase 6 sobre o modelo de pico de risco. As 10
          features sao o <strong>estado clinico do paciente neste momento</strong>.
        </p>
      </section>

      {!podeEscreverClinico ? (
        <section className="panel">
          <p className="helper">
            Seu papel nao permite registrar avaliacoes — o contrato exige{" "}
            <span className="mono">MEDICO</span>.
          </p>
        </section>
      ) : (
        <Formulario
          valores={valores}
          atualizar={atualizar}
          substituir={setValores}
          origem={origem}
          setOrigem={setOrigem}
          modo={modo}
          setModo={setModo}
          completo={completo}
          preenchidas={preenchidas}
          enviando={enviando}
          enviar={enviar}
        />
      )}

      {enviando && <Carregando texto="Executando o pipeline da Fase 6..." linhas={2} />}
      {falha && <ResultadoDaFalha falha={falha} />}
      {resultado && (
        <ResultadoDaAvaliacao
          envelope={resultado.envelope}
          featuresEnviadas={resultado.features}
        />
      )}
    </div>
  );
}

/** Formulario das 10 features + opcoes do pipeline. */
function Formulario({
  valores,
  atualizar,
  substituir,
  origem,
  setOrigem,
  modo,
  setModo,
  completo,
  preenchidas,
  enviando,
  enviar,
}) {
  return (
    <section className="panel">
      <form className="stack" onSubmit={enviar}>
        <div className="painelTopo">
          <h3 className="panelTitle">
            Features do modelo ({preenchidas}/10)
            <Origem tipo="preditivo" />
          </h3>
          <div className="row">
            <button
              type="button"
              className="logoutBtn"
              onClick={() => substituir(exemploPreenchido())}
            >
              Preencher exemplo
            </button>
            <button
              type="button"
              className="logoutBtn"
              onClick={() => substituir(formularioVazio())}
            >
              Limpar
            </button>
          </div>
        </div>

        <p className="helper">
          ⚠️ Nao ha valor padrao: campos vazios <strong>nao</strong> sao preenchidos pelo
          backend. O botao &quot;Preencher exemplo&quot; usa valores{" "}
          <strong>ficticios</strong>, so para demonstracao.
        </p>

        <div className="gradeCampos">
          {FEATURES_DO_MODELO.map((feature) => {
            const fora = foraDaFaixa(feature, valores[feature.nome]);
            return (
              <div className="campo" key={feature.nome}>
                <label className="seletorRotulo" htmlFor={`f-${feature.nome}`}>
                  {feature.rotulo}
                  {feature.unidade && <span className="helper"> ({feature.unidade})</span>}
                </label>
                <input
                  id={`f-${feature.nome}`}
                  type="number"
                  step={feature.passo}
                  min="0"
                  required
                  value={valores[feature.nome]}
                  onChange={(evento) => atualizar(feature.nome, evento.target.value)}
                  placeholder={`${feature.minimo} – ${feature.maximo}`}
                />
                <div className="campoPes">
                  <span className="helper mono">{feature.nome}</span>
                  {feature.escala === "episodio" && (
                    <span className="etiqueta etiqueta--episodio">episodio</span>
                  )}
                  {feature.confianca === "baixa" && (
                    <span className="etiqueta etiqueta--baixa">baixa confianca</span>
                  )}
                  {fora && <span className="etiqueta etiqueta--fora">fora da faixa</span>}
                </div>
              </div>
            );
          })}
        </div>

        <div className="grid2">
          <div>
            <label className="seletorRotulo" htmlFor="origem">
              Origem dos dados
            </label>
            <select id="origem" value={origem} onChange={(e) => setOrigem(e.target.value)}>
              {Object.entries(ORIGENS_DOS_DADOS).map(([chave, rotulo]) => (
                <option key={chave} value={chave}>
                  {rotulo}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="seletorRotulo" htmlFor="modo">
              Modo do pipeline
            </label>
            <select id="modo" value={modo} onChange={(e) => setModo(e.target.value)}>
              {Object.entries(MODOS_DO_PIPELINE).map(([chave, info]) => (
                <option key={chave} value={chave}>
                  {info.rotulo} — {info.ajuda}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="row">
          <button type="submit" disabled={!completo || enviando}>
            {enviando ? "Executando o pipeline..." : "Avaliar risco"}
          </button>
          {!completo && <span className="helper">Preencha as 10 features para habilitar.</span>}
        </div>
      </form>
    </section>
  );
}

