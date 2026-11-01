import Constants from "expo-constants";
import { Platform } from "react-native";

/**
 * URL base do backend.
 *
 * Prioridade:
 *   1. EXPO_PUBLIC_API_URL (variável pública do Expo — override manual)
 *   2. Web                          -> http://localhost:5000
 *   3. Host do Metro (expo-constants) -> http://<IP-do-Metro>:5000
 *      (funciona em celular físico e emulador sem configuração)
 *   4. Android emulador (fallback)  -> http://10.0.2.2:5000
 *   5. iOS/fallback                 -> http://localhost:5000
 */
function getDevServerHost() {
  const debuggerHost =
    Constants.expoConfig?.hostUri ??
    Constants.expoGoConfig?.debuggerHost ??
    null;

  if (!debuggerHost) return null;

  let host = debuggerHost.split(":")[0] ?? null;
  if (!host) return null;

  // Remove colchetes de endereços IPv6, se houver
  host = host.replace(/^\[|\]$/g, "");

  if (host === "localhost" || host === "127.0.0.1" || host === "10.0.2.2") {
    return null;
  }

  return host;
}

function getDefaultApiUrl() {
  if (
    typeof process !== "undefined" &&
    process.env &&
    process.env.EXPO_PUBLIC_API_URL
  ) {
    return String(process.env.EXPO_PUBLIC_API_URL).replace(/\/+$/, "");
  }

  if (Platform.OS === "web") {
    return "http://localhost:5000";
  }

  const devHost = getDevServerHost();
  if (devHost) {
    return `http://${devHost}:5000`;
  }

  if (Platform.OS === "android") {
    return "http://10.0.2.2:5000";
  }

  return "http://localhost:5000";
}

export const API_URL = getDefaultApiUrl();

if (__DEV__) {
  console.log(`[CardioAssist] API_URL = ${API_URL}`);
}