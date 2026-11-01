import { useContext } from "react";
import { AuthContext } from "../contexts/AuthContext";

export function AreaRestrita() {
  const { usuario, loading } = useContext(AuthContext);

  if (loading) {
    return (
      <section className="panel" aria-label="Área restrita">
        <h2 className="panelTitle">Área restrita</h2>
        <p>Carregando...</p>
      </section>
    );
  }

  if (!usuario) {
    return (
      <section className="panel" aria-label="Área restrita">
        <h2 className="panelTitle">Área restrita</h2>
        <p className="errorText">Acesso negado. Faça login para continuar.</p>
        <div className="mutedBox" style={{ marginTop: 10 }}>
          Após autenticar, você verá aqui o conteúdo clínico (ex.: prontuários,
          agenda e alertas).
        </div>
      </section>
    );
  }

  return (
    <section className="panel" aria-label="Área restrita">
      <h2 className="panelTitle">Área restrita</h2>
      <div className="stack">
        <div className="mutedBox">
          Conteúdo exclusivo para usuários autenticados.
        </div>
        <div className="row">
          <button type="button">Ver agenda</button>
          <button type="button" className="logoutBtn">
            Pacientes
          </button>
        </div>
        <p className="helper">
          (Botões demonstrativos — aqui você pode ligar com suas páginas/rotas.)
        </p>
      </div>
    </section>
  );
}