/**
 * Sessao do usuario — versao integrada (Etapa D).
 *
 * O que mudou em relacao ao app da Fase 2:
 *
 * | Antes (Fase 2) | Agora |
 * |---|---|
 * | `login` comparava `admin@email.com`/`123` **no cliente** | `POST /auth/login` no backend |
 * | gravava `fake-jwt-token-123` | guarda o par real (`access_token` + `refresh_token`) |
 * | `usuario` era reconstruido do token sem validar | `GET /auth/me` confirma a sessao ao abrir |
 * | `logout` so apagava o localStorage | `POST /auth/logout` revoga as sessoes no servidor |
 *
 * 🔒 **Nenhuma credencial vive no codigo.** O que fica no `localStorage` e o token
 * emitido pelo backend; a senha nunca e armazenada.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  definirTokens,
  definirTratadorDeExpiracao,
  limparTokens,
  mensagemDoErro,
} from "../api/cliente";
import { entrar, meuUsuario, sair } from "../api/endpoints";

/* `react-refresh/only-export-components` exige que um arquivo exporte APENAS
   componentes, por causa do Fast Refresh. Este arquivo exporta o contexto, o hook e o
   provedor — que e o padrao que a propria documentacao do React mostra. Separar em tres
   arquivos nao traria beneficio real para este MVP, entao a regra fica desligada aqui
   (e so aqui). */
/* eslint-disable react-refresh/only-export-components */

export const AuthContext = createContext(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de AuthProvider");
  return ctx;
}

/** Chave do par de tokens no `localStorage`. */
const CHAVE_DE_SESSAO = "cardioia.sessao";

function lerSessaoGravada() {
  try {
    const bruto = localStorage.getItem(CHAVE_DE_SESSAO);
    return bruto ? JSON.parse(bruto) : null;
  } catch {
    return null;
  }
}

function gravarSessao(tokens) {
  try {
    if (tokens?.access_token) {
      localStorage.setItem(CHAVE_DE_SESSAO, JSON.stringify(tokens));
    } else {
      localStorage.removeItem(CHAVE_DE_SESSAO);
    }
  } catch {
    // Modo privado / storage bloqueado: a sessao continua valida em memoria.
  }
}

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);

  /** Encerra a sessao local (sem chamar o backend). */
  const encerrarLocalmente = useCallback(() => {
    limparTokens();
    gravarSessao(null);
    setUsuario(null);
  }, []);

  // Quando o refresh falha, a sessao acabou: limpa e o ProtectedRoute reage.
  useEffect(() => {
    definirTratadorDeExpiracao(encerrarLocalmente);
  }, [encerrarLocalmente]);

  // Ao abrir a aplicacao: restaura os tokens e confirma a sessao no backend.
  useEffect(() => {
    let cancelado = false;

    async function restaurar() {
      const gravada = lerSessaoGravada();
      if (!gravada?.access_token) {
        setCarregando(false);
        return;
      }
      definirTokens(gravada);
      try {
        const envelope = await meuUsuario();
        if (!cancelado) setUsuario(envelope.dados);
      } catch {
        // Token invalido/expirado e sem refresh utilizavel: comeca limpo.
        if (!cancelado) encerrarLocalmente();
      } finally {
        if (!cancelado) setCarregando(false);
      }
    }

    restaurar();
    return () => {
      cancelado = true;
    };
  }, [encerrarLocalmente]);

  /** Autentica no backend e carrega o usuario real. */
  const login = useCallback(
    async (email, senha) => {
      setErro(null);
      try {
        const sessao = await entrar(email, senha);
        definirTokens(sessao.dados);
        gravarSessao(sessao.dados);

        const perfil = await meuUsuario();
        setUsuario(perfil.dados);
        return perfil.dados;
      } catch (falha) {
        encerrarLocalmente();
        setErro(mensagemDoErro(falha));
        throw falha;
      }
    },
    [encerrarLocalmente]
  );

  /** Revoga as sessoes no backend e limpa o estado local. */
  const logout = useCallback(async () => {
    try {
      await sair();
    } catch {
      // Backend fora do ar nao pode impedir o usuario de sair localmente.
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
      /** Papel do RBAC, para a UI esconder o que o backend recusaria. */
      papel: usuario?.papel ?? null,
      podeEscreverClinico: usuario?.papel === "MEDICO",
    }),
    [usuario, carregando, erro, login, logout]
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}
