/**
 * Configuracao da camada de API do app.
 *
 * `EXPO_PUBLIC_API_URL` e lida em tempo de build pelo Expo. Quando ausente, o app usa o
 * host do Metro (que e a mesma maquina do backend em desenvolvimento) na porta 8000.
 */

import Constants from "expo-constants";
import { Platform } from "react-native";

/** Porta do backend central da Fase 7. */
const PORTA_DO_BACKEND = 8000;

/** Prefixo versionado das rotas. */
const PREFIXO = "/api/v1";

function hostDoMetro() {
  const debuggerHost =
    Constants.expoConfig?.hostUri ?? Constants.expoGoConfig?.debuggerHost ?? null;
  if (!debuggerHost) return null;

  const host = String(debuggerHost).split(":")[0]?.replace(/^\[|\]$/g, "");
  if (!host || host === "localhost" || host === "127.0.0.1" || host === "10.0.2.2") {
    return null;
  }
  return host;
}

function urlPadrao() {
  if (Platform.OS === "web") return `http://localhost:${PORTA_DO_BACKEND}${PREFIXO}`;

  // Em celular fisico, o backend esta na mesma maquina que serve o Metro.
  const host = hostDoMetro();
  if (host) return `http://${host}:${PORTA_DO_BACKEND}${PREFIXO}`;

  if (Platform.OS === "android") {
    return `http://10.0.2.2:${PORTA_DO_BACKEND}${PREFIXO}`;
  }
  return `http://localhost:${PORTA_DO_BACKEND}${PREFIXO}`;
}

const DO_AMBIENTE = process.env.EXPO_PUBLIC_API_URL;

/** URL base da API, sem barra final. */
export const URL_DA_API = String(DO_AMBIENTE || urlPadrao()).replace(/\/+$/, "");

/** Tempo maximo de espera de uma chamada, em milissegundos. */
export const TEMPO_LIMITE_MS = 30000;
