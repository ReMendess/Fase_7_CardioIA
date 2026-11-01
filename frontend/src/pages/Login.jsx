import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { saude } from "../api/endpoints";
import { useAuth } from "../contexts/AuthContext";

/**
 * Tela de acesso.
 *
 * Substitui o `PainelLogin` de exemplo da Fase 2, que validava `admin@email.com`/`123`
 * **no navegador**. Agora a credencial vai para `POST /auth/login` e o que volta e um
 * par de tokens emitido pelo backend.
 *
 * 🔒 Nenhuma credencial de teste aparece no codigo: o usuario e criado no banco
 * (procedimento no `README.md` do backend).
 */
export default function Login() {
  const { login, erro } = useAuth();
  const navegar = useNavigate();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [falhaLocal, setFalhaLocal] = useState(null);
  const [saudeDoBackend, setSaudeDoBackend] = useState(null);

  // Verifica o backend assim que a tela abre: se estiver fora do ar, o usuario
  // descobre antes de tentar entrar.
  useEffect(() => {
    let cancelado = false;
    saude()
      .then((envelope) => {
        if (!cancelado) setSaudeDoBackend({ ok: true, dados: envelope.dados });
      })
      .catch((falha) => {
        if (!cancelado) setSaudeDoBackend({ ok: false, mensagem: falha.message });
      });
    return () => {
      cancelado = true;
    };
  }, []);

  async function enviar(evento) {
    evento.preventDefault();
    setFalhaLocal(null);
    setEnviando(true);
    try {
      await login(email.trim(), senha);
      navegar("/dashboard", { replace: true });
    } catch (falha) {
      setFalhaLocal(falha);
    } finally {
      setEnviando(false);
    }
  }

  const mensagem = falhaLocal ? erro || falhaLocal.message : null;

  return (
    <section className="panel" aria-label="Area de login">
      <h2 className="panelTitle">Acesso clinico</h2>

      <form className="stack" onSubmit={enviar}>
        <div>
          <label className="seletorRotulo" htmlFor="email">
            E-mail
          </label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            placeholder="seu.email@exemplo.local"
            value={email}
            onChange={(evento) => setEmail(evento.target.value)}
            required
          />
        </div>

        <div>
          <label className="seletorRotulo" htmlFor="senha">
            Senha
          </label>
          <input
            id="senha"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={senha}
            onChange={(evento) => setSenha(evento.target.value)}
            required
          />
        </div>

        <div className="row">
          <button type="submit" disabled={enviando}>
            {enviando ? "Entrando..." : "Entrar"}
          </button>
        </div>

        {mensagem && <p className="errorText">{mensagem}</p>}
      </form>

      <div className="mutedBox" style={{ marginTop: 14 }}>
        <strong>Usuario de teste:</strong> nao ha cadastro pela interface — a API nao
        expoe criacao de usuarios. Semeie um usuario no banco seguindo o procedimento do
        <code> README.md </code> do backend (papeis: <code>MEDICO</code>,{" "}
        <code>OPERADOR</code>, <code>ADMIN</code>).
      </div>

      <div className="linhaChaveValor" style={{ marginTop: 12 }}>
        <span className="helper">Backend</span>
        {saudeDoBackend === null && <span className="etiqueta">verificando...</span>}
        {saudeDoBackend?.ok && (
          <span className="etiqueta etiqueta--api">
            online · {saudeDoBackend.dados?.ambiente ?? "?"}
          </span>
        )}
        {saudeDoBackend && !saudeDoBackend.ok && (
          <span className="etiqueta etiqueta--fora">fora do ar</span>
        )}
      </div>

      {saudeDoBackend && !saudeDoBackend.ok && (
        <p className="errorText">{saudeDoBackend.mensagem}</p>
      )}
    </section>
  );
}
