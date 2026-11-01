import "./App.css";
import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { AreaRestrita } from "./hooks-examples/AreaRestrita";
import { PainelLogin } from "./hooks-examples/PainelLogin";
import Dashboard from "./pages/Dashboard";
import Patients from "./pages/Patients";
import Schedule from "./pages/Schedule";

function AuthGate() {
  const { usuario, loading } = useAuth();

  if (loading) {
    return (
      <div className="appShell appShell--landing">
        <div className="card">
          <header className="cardHeader">
            <div className="brand">
              <h1 className="brandTitle">Portal Médico</h1>
              <p className="brandSubtitle">Acesso seguro • Atendimento • Prontuários</p>
            </div>
            <div className="badge">
              <span className="badgeDot" />
              Sistema online
            </div>
          </header>
          <main className="content">
            <section className="panel">
              <h2 className="panelTitle">Carregando</h2>
              <p>Verificando sessão...</p>
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
            <h1 className="brandTitle">Portal Médico</h1>
            <p className="brandSubtitle">Acesso seguro • Atendimento • Prontuários</p>
          </div>
          <div className="badge">
            <span className="badgeDot" />
            Sistema online
          </div>
        </header>

        <main className="cardBody">
          <PainelLogin />
          <AreaRestrita />
        </main>
      </div>
    </div>
  );
}

function AppLayout({ children, title }) {
  const { usuario, logout } = useAuth();

  return (
    <div className="appShell">
      <div className="card">
        <header className="topbar">
          <div className="brand">
            <div className="brandTitle">Portal Médico</div>
            <div className="brandSubtitle">
              {title ? title : "Área clínica"}
              {usuario ? ` • ${usuario.nome}` : ""}
            </div>
          </div>

          <nav className="nav" aria-label="Navegação">
            <NavLink
              to="/dashboard"
              className={({ isActive }) => `navLink ${isActive ? "navLinkActive" : ""}`}
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/patients"
              className={({ isActive }) => `navLink ${isActive ? "navLinkActive" : ""}`}
            >
              Pacientes
            </NavLink>
            <NavLink
              to="/schedule"
              className={({ isActive }) => `navLink ${isActive ? "navLinkActive" : ""}`}
            >
              Agenda
            </NavLink>
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

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AuthGate />} />

          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <AppLayout title="Visão geral">
                  <Dashboard />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/patients"
            element={
              <ProtectedRoute>
                <AppLayout title="Pacientes">
                  <Patients />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/schedule"
            element={
              <ProtectedRoute>
                <AppLayout title="Agenda">
                  <Schedule />
                </AppLayout>
              </ProtectedRoute>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;