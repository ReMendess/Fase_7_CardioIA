import { createContext, useContext, useEffect, useState } from "react";

export const AuthContext = createContext();

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de AuthProvider");
  return ctx;
}

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      setUsuario({
        nome: "Usuário Fictício",
        email: "teste@email.com",
      });
    }
    setLoading(false);
  }, [token]);

  function login(email, senha) {
    // simulação de validação
    if (email === "admin@email.com" && senha === "123") {
      const fakeToken = "fake-jwt-token-123";
      localStorage.setItem("token", fakeToken);

      setToken(fakeToken);
      setUsuario({
        nome: "Administrador",
        email,
      });

      return true;
    }

    return false;
  }

  function logout() {
    localStorage.removeItem("token");
    setToken(null);
    setUsuario(null);
  }

  return (
    <AuthContext.Provider value={{ usuario, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}