import { useEffect, useState } from "react";
import { fetchPatients } from "../services/api";

export default function Dashboard() {
  const [patients, setPatients] = useState([]);

  useEffect(() => {
    fetchPatients().then(setPatients);
  }, []);

  return (
    <div className="grid2">
      <section className="panel" aria-label="Resumo">
        <h2 className="pageTitle">Dashboard</h2>
        <div className="stack">
          <div className="listItem">
            <div>
              <div className="listItemTitle">Total de pacientes</div>
              <p className="helper">Base carregada via API (fake)</p>
            </div>
            <span className="pill">{patients.length}</span>
          </div>
          <div className="listItem">
            <div>
              <div className="listItemTitle">Consultas agendadas</div>
              <p className="helper">Indicador demonstrativo</p>
            </div>
            <span className="pill">5</span>
          </div>
          <div className="mutedBox">
            Dica: use o menu acima para navegar entre pacientes e agenda.
          </div>
        </div>
      </section>

      <section className="panel" aria-label="Atalhos">
        <h3 className="panelTitle">Ações rápidas</h3>
        <div className="stack">
          <button type="button">Novo agendamento</button>
          <button type="button" className="logoutBtn">
            Buscar paciente
          </button>
          <p className="helper">
            (Ações demonstrativas — você pode ligar com seu fluxo real.)
          </p>
        </div>
      </section>
    </div>
  );
}