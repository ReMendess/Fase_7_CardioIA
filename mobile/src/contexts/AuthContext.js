/**
 * Sessao do usuario no app.
 *
 * Mesmo fluxo do frontend web: `POST /auth/login` → tokens em memoria → `GET /auth/me`
 * confirma a sessao. A senha nunca e armazenada, e os tokens vivem apenas enquanto o app
 * esta aberto.
 */

import { createContext, useCallback, useContext, useMemo, useState } from "react";

import {
  definirTokens,
  definirTratadorDeExpiracao,
  limparTokens,
  mensagemDoErro,
} from "../api/cliente.js";
import { entrar, meuUsuario, sair } from "../api/endpoints.js";

export const AuthContext = createContext(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de AuthProvider");
  return ctx;
}

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);

  const encerrarLocalmente = useCallback(() => {
    limparTokens();
    setUsuario(null);
  }, []);

  // Quando o refresh falha, a sessao acabou.
  useMemo(() => definirTratadorDeExpiracao(encerrarLocalmente), [encerrarLocalmente]);

  const login = useCallback(
    async (email, senha) => {
      setErro(null);
      setCarregando(true);
      try {
        const sessao = await entrar(String(email).trim(), senha);
        definirTokens(sessao.dados);
        const perfil = await meuUsuario();
        setUsuario(perfil.dados);
        return perfil.dados;
      } catch (falha) {
        encerrarLocalmente();
        setErro(mensagemDoErro(falha));
        throw falha;
      } finally {
        setCarregando(false);
      }
    },
    [encerrarLocalmente]
  );

  const logout = useCallback(async () => {
    try {
      await sair();
    } catch {
      // Backend fora do ar nao pode impedir o usuario de sair.
    } finally {
      encerrarLocalmente();
    }
  }, [encerrarLocalmente]);

  const valor = useMemo(
    () => ({
      usuario,
      carregando,
      erro,
      login,
      logout,
      papel: usuario?.papel ?? null,
    }),
    [usuario, carregando, erro, login, logout]
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}
