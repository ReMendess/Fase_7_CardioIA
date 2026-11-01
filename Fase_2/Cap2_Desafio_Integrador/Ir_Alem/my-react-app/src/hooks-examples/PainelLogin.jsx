import { useContext, useState } from "react";
import { AuthContext } from "../contexts/AuthContext";

export function PainelLogin() {
  const { usuario, login, logout } = useContext(AuthContext);

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");

  function handleLogin() {
    const success = login(email, senha);

    if (!success) {
      setErro("Credenciais inválidas");
    } else {
      setErro("");
    }
  }

  return (
    <section className="panel" aria-label="Área de login">
      <h2 className="panelTitle">Acesso</h2>

      {usuario ? (
        <>
          <div className="stack">
            <div className="mutedBox">
              <strong style={{ color: "var(--text)" }}>Bem-vindo,</strong>{" "}
              {usuario.nome}
              <div className="helper">Email: {usuario.email}</div>
            </div>
            <button className="logoutBtn" onClick={logout}>
              Sair
            </button>
          </div>
        </>
      ) : (
        <>
          <div className="stack">
            <div>
              <input
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
              />
            </div>

            <div>
              <input
                type="password"
                placeholder="Senha"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                autoComplete="current-password"
              />
              <div className="helper">Dica: `admin@email.com` • senha `123`</div>
            </div>

            <div className="row">
              <button onClick={handleLogin}>Entrar</button>
            </div>

            {erro && <p className="errorText">{erro}</p>}
          </div>
        </>
      )}
    </section>
  );
}