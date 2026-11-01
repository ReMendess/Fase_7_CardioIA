import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

/**
 * Bloqueia as rotas clinicas enquanto nao houver sessao confirmada.
 *
 * A diferenca em relacao ao app da Fase 2: aqui `carregando` cobre a chamada real a
 * `GET /auth/me`. Sem isso, um token expirado no `localStorage` deixaria a tela abrir
 * e so falharia na primeira requisicao.
 */
export default function ProtectedRoute({ children }) {
  const { usuario, carregando } = useAuth();
  const local = useLocation();

  if (carregando) {
    return (
      <div className="appShell appShell--landing">
        <div className="card">
          <main className="content">
            <section className="panel">
              <h2 className="panelTitle">Carregando</h2>
              <p>Verificando a sessao com o backend...</p>
            </section>
          </main>
        </div>
      </div>
    );
  }

  if (!usuario) {
    // Guarda o destino para voltar depois do login.
    return <Navigate to="/" replace state={{ de: local.pathname }} />;
  }

  return children;
}
