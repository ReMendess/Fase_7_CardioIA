import { usePacientes } from "../contexts/PacienteContext";

/**
 * Seletor do paciente ativo.
 *
 * Fica no topo das telas clinicas para que o paciente em foco esteja **sempre visivel**
 * — a alternativa (contexto implicito) e o caminho classico para alguem ler o
 * resultado do paciente errado.
 */
export default function SeletorDePaciente({ compacto = false }) {
  const { pacientes, selecionado, selecionar, carregando } = usePacientes();

  if (carregando) {
    return <div className="seletorPaciente helper">Carregando pacientes...</div>;
  }

  if (!pacientes.length) {
    return (
      <div className="seletorPaciente helper">
        Nenhum paciente cadastrado — cadastre um na aba <strong>Pacientes</strong>.
      </div>
    );
  }

  return (
    <div className={`seletorPaciente ${compacto ? "seletorPaciente--compacto" : ""}`}>
      <label className="seletorRotulo" htmlFor="seletor-paciente">
        Paciente em foco
      </label>
      <select
        id="seletor-paciente"
        value={selecionado?.id_paciente ?? ""}
        onChange={(evento) =>
          selecionar(pacientes.find((p) => p.id_paciente === evento.target.value) ?? null)
        }
      >
        {pacientes.map((paciente) => (
          <option key={paciente.id_paciente} value={paciente.id_paciente}>
            {paciente.nome}
          </option>
        ))}
      </select>

      {selecionado && (
        <div className="seletorDetalhe">
          <span className="mono helper">{selecionado.id_paciente}</span>
          {!selecionado.ativo && <span className="etiqueta etiqueta--fora">inativo</span>}
        </div>
      )}
    </div>
  );
}
