import { useEffect, useState } from "react";
import { fetchPatients } from "../services/api";

export default function Patients() {
  const [patients, setPatients] = useState([]);

  useEffect(() => {
    fetchPatients().then(setPatients);
  }, []);

  return (
    <section className="panel" aria-label="Lista de pacientes">
      <h2 className="pageTitle">Pacientes</h2>
      <p className="helper">
        Lista carregada de `jsonplaceholder.typicode.com` (somente demonstração).
      </p>

      <div style={{ height: 10 }} />

      <div className="list">
        {patients.map((p) => (
          <div className="listItem" key={p.id}>
            <div>
              <div className="listItemTitle">{p.name}</div>
              <div className="helper">{p.email}</div>
            </div>
            <span className="pill">Ativo</span>
          </div>
        ))}
      </div>

      {patients.length === 0 && (
        <div style={{ marginTop: 12 }} className="mutedBox">
          Carregando pacientes...
        </div>
      )}
    </section>
  );
}