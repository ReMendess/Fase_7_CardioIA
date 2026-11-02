import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";

import { AuthProvider, useAuth } from "./src/contexts/AuthContext";
import ChatScreen from "./src/screens/ChatScreen";
import IndicadoresScreen from "./src/screens/IndicadoresScreen";
import LoginScreen from "./src/screens/LoginScreen";
import { colors, fonts, spacing } from "./src/theme";

/**
 * App CardioIA — Fase 7.
 *
 * Tres telas, cobrindo o fluxo exigido: **login** → **indicadores cardiacos** →
 * **assistente**. A navegacao e por estado local, sem biblioteca de rotas: sao poucas
 * telas e isso evita mais uma dependencia.
 *
 * ⚠️ **Por que `react-native-safe-area-context` e nao o `SafeAreaView` do `react-native`:**
 * no Android, o do core **e literalmente um `View`** — a implementacao e
 * `Platform.select({ ios: <nativo>, default: View })`. Ele nao aplica recuo nenhum.
 *
 * Isso passou a importar quando o edge-to-edge virou obrigatorio: o SDK 57 avisa que
 * "Android 16 makes edge-to-edge mandatory" e nem aceita desligar. Com o app desenhando
 * atras das barras do sistema, o cabecalho (com o botao **Sair**) caia sob a barra de
 * status e a barra de abas caia sob a de navegacao — e **essas regioes pertencem ao
 * sistema, que nao repassa toque ao app**. O sintoma era exatamente esse: nao dava para
 * sair nem trocar de aba.
 */

const ABAS = [
  { chave: "indicadores", rotulo: "Indicadores" },
  { chave: "assistente", rotulo: "Assistente" },
];

function Conteudo() {
  const { usuario } = useAuth();
  const [aba, setAba] = useState("indicadores");

  if (!usuario) return <LoginScreen />;

  return (
    <View style={styles.tela}>
      <View style={styles.conteudo}>
        {aba === "indicadores" ? <IndicadoresScreen /> : <ChatScreen />}
      </View>

      <View style={styles.abas}>
        {ABAS.map((item) => {
          const ativa = aba === item.chave;
          return (
            <Pressable
              key={item.chave}
              style={styles.aba}
              onPress={() => setAba(item.chave)}
              accessibilityRole="tab"
              accessibilityState={{ selected: ativa }}
            >
              <Text style={[styles.abaTexto, ativa && styles.abaTextoAtiva]}>
                {item.rotulo}
              </Text>
              {ativa && <View style={styles.marcador} />}
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      {/* `edges` explicito: sem ele o app volta a desenhar atras das barras do sistema. */}
      <SafeAreaView style={styles.segura} edges={["top", "bottom", "left", "right"]}>
        <StatusBar style="dark" />
        <AuthProvider>
          <Conteudo />
        </AuthProvider>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  segura: { flex: 1, backgroundColor: colors.background },
  tela: { flex: 1 },
  conteudo: { flex: 1 },
  abas: {
    flexDirection: "row",
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.surface,
  },
  aba: { flex: 1, alignItems: "center", paddingVertical: spacing.md },
  abaTexto: { fontSize: fonts.small, fontWeight: "600", color: colors.textMuted },
  abaTextoAtiva: { color: colors.primary },
  marcador: {
    marginTop: spacing.xs,
    width: 28,
    height: 3,
    borderRadius: 999,
    backgroundColor: colors.primary,
  },
});

