import "./App.css";
import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { PacienteProvider } from "./contexts/PacienteContext";
import Agenda from "./pages/Agenda";
import Assistente from "./pages/Assistente";
import Avaliacao from "./pages/Avaliacao";
import Dashboard from "./pages/Dashboard";
import Historico from "./pages/Historico";
import Login from "./pages/Login";
import Monitoramento from "./pages/Monitoramento";
import Pacientes from "./pages/Pacientes";

/**
 * Aplicacao integrada ao backend da Fase 7 (Etapa D).
 *
 * A estrutura visual, o CSS e os assets continuam os do app da Fase 2 — o que mudou foi
 * a origem dos dados: antes `jsonplaceholder` e um login simulado, agora a API da Fase 7
 * com JWT.
 *
 * Toda rota clinica passa por `ProtectedRoute`, que confirma a sessao com
 * `GET /auth/me` antes de renderizar.
 */

/** Pagina inicial: manda para o dashboard quem ja tem sessao. */
function Inicio() {
  const { usuario, carregando } = useAuth();

  if (carregando) {
    return (
      <div className="appShell appShell--landing">
        <div className="card">
          <main className="content">
            <section className="panel">
              <h2 className="panelTitle">Carregando</h2>
              <p>Verificando a sessao...</p>
            </section>
          </main>
        </div>
      </div>
    );
  }

  if (usuario) return <Navigate to="/dashboard" replace />;

  return (
    <div className="appShell appShell--landing">
      <div className="card">
        <header className="cardHeader">
          <div className="brand">
            <h1 className="brandTitle">CardioIA</h1>
            <p className="brandSubtitle">
              Portal clinico · Fase 7 · backend central integrado
            </p>
          </div>
          <div className="badge">
            <span className="badgeDot" />
            Sistema online
          </div>
        </header>

        <main className="cardBody">
          <Login />
          <Sobre />
        </main>
      </div>
    </div>
  );
}

/** Texto de contexto da tela de acesso — uma linha, sem repetir o README. */
function Sobre() {
  return (
    <section className="panel" aria-label="Sobre o sistema">
      <h2 className="panelTitle">Sobre</h2>
      <p className="helper">
        Plataforma CardioIA. Os dados sao sinteticos, sem validacao clinica, e nenhum
        resultado e diagnostico, prescricao ou recomendacao medica.
      </p>
    </section>
  );
}

/** Itens de navegacao (o backend continua sendo a autoridade de cada um). */
const NAVEGACAO = [
  { rota: "/dashboard", rotulo: "Dashboard" },
  { rota: "/pacientes", rotulo: "Pacientes" },
  { rota: "/avaliacao", rotulo: "Avaliacao" },
  { rota: "/historico", rotulo: "Historico" },
  { rota: "/monitoramento", rotulo: "Monitoramento" },
  { rota: "/assistente", rotulo: "Assistente" },
  { rota: "/agenda", rotulo: "Agenda" },
];

function Layout({ children, titulo }) {
  const { usuario, logout } = useAuth();

  return (
    <div className="appShell">
      <div className="card">
        <header className="topbar">
          <div className="brand">
            <div className="brandTitle">CardioIA</div>
            <div className="brandSubtitle">
              {titulo ?? "Area clinica"}
              {usuario ? ` · ${usuario.nome} (${usuario.papel})` : ""}
            </div>
          </div>

          <nav className="nav" aria-label="Navegacao">
            {NAVEGACAO.map((item) => (
              <NavLink
                key={item.rota}
                to={item.rota}
                className={({ isActive }) => `navLink ${isActive ? "navLinkActive" : ""}`}
              >
                {item.rotulo}
              </NavLink>
            ))}
            <button type="button" className="logoutBtn" onClick={logout}>
              Sair
            </button>
          </nav>
        </header>

        <main className="content">{children}</main>
      </div>
    </div>
  );
}

/** Rota protegida dentro do layout. */
function Protegida({ titulo, children }) {
  return (
    <ProtectedRoute>
      <Layout titulo={titulo}>{children}</Layout>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <PacienteProvider>
          <Routes>
            <Route path="/" element={<Inicio />} />

            <Route
              path="/dashboard"
              element={
                <Protegida titulo="Visao geral">
                  <Dashboard />
                </Protegida>
              }
            />
            <Route
              path="/pacientes"
              element={
                <Protegida titulo="Pacientes">
                  <Pacientes />
                </Protegida>
              }
            />
            <Route
              path="/avaliacao"
              element={
                <Protegida titulo="Avaliacao de risco">
                  <Avaliacao />
                </Protegida>
              }
            />
            <Route
              path="/historico"
              element={
                <Protegida titulo="Historico de avaliacoes">
                  <Historico />
                </Protegida>
              }
            />
            <Route
              path="/monitoramento"
              element={
                <Protegida titulo="Monitoramento IoT">
                  <Monitoramento />
                </Protegida>
              }
            />
            <Route
              path="/assistente"
              element={
                <Protegida titulo="Assistente">
                  <Assistente />
                </Protegida>
              }
            />
            <Route
              path="/agenda"
              element={
                <Protegida titulo="Agenda">
                  <Agenda />
                </Protegida>
              }
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </PacienteProvider>
      </BrowserRouter>
    </AuthProvider>
  );
}

