import Constants from "expo-constants";
import { Platform } from "react-native";

function getDevServerHost(): string | null {
  const debuggerHost =
    Constants.expoGoConfig?.debuggerHost ??
    Constants.expoConfig?.hostUri ??
    null;

  if (!debuggerHost) {
    return null;
  }

  return debuggerHost.split(":")[0] ?? null;
}

function getDefaultApiUrl(): string {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL.replace(/\/$/, "");
  }

  if (Platform.OS === "web") {
    return "http://localhost:5000";
  }

  const devHost = getDevServerHost();
  if (devHost && devHost !== "localhost" && devHost !== "127.0.0.1") {
    return `http://${devHost}:5000`;
  }

  if (Platform.OS === "android") {
    return "http://10.0.2.2:5000";
  }

  return "http://localhost:5000";
}

export const API_URL = getDefaultApiUrl();
