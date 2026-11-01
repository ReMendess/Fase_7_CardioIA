import { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { mensagemDoErro } from "../api/cliente.js";
import { saude } from "../api/endpoints.js";
import { useAuth } from "../contexts/AuthContext";
import { colors, fonts, radii, shadow, spacing } from "../theme";

/**
 * Tela de acesso.
 *
 * Autentica em `POST /auth/login` e confirma a sessao com `GET /auth/me`. Nenhuma
 * credencial vive no codigo — a conta e criada no backend.
 */
export default function LoginScreen() {
  const { login, carregando } = useAuth();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [falha, setFalha] = useState(null);
  const [servico, setServico] = useState(null);

  async function verificarBackend() {
    try {
      const envelope = await saude();
      setServico({ ok: true, ambiente: envelope.dados?.ambiente ?? "?" });
    } catch (erro) {
      setServico({ ok: false, texto: mensagemDoErro(erro) });
    }
  }

  async function enviar() {
    setFalha(null);
    try {
      await login(email, senha);
    } catch (erro) {
      setFalha(mensagemDoErro(erro));
    }
  }

  const podeEnviar = email.trim().length > 0 && senha.length > 0 && !carregando;

  return (
    <KeyboardAvoidingView
      style={styles.tela}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView contentContainerStyle={styles.conteudo} keyboardShouldPersistTaps="handled">
        <View style={styles.cartao}>
          <Text style={styles.titulo}>CardioIA</Text>
          <Text style={styles.subtitulo}>Portal clinico · Fase 7</Text>

          <Text style={styles.rotulo}>E-mail ou usuário</Text>
          <TextInput
            style={styles.entrada}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            placeholder="teste ou seu.email@exemplo.local"
            placeholderTextColor={colors.textMuted}
          />

          <Text style={styles.rotulo}>Senha</Text>
          <TextInput
            style={styles.entrada}
            value={senha}
            onChangeText={setSenha}
            secureTextEntry
            placeholder="••••••••"
            placeholderTextColor={colors.textMuted}
          />

          <Pressable
            style={({ pressed }) => [
              styles.botao,
              (!podeEnviar || pressed) && styles.botaoInativo,
            ]}
            onPress={enviar}
            disabled={!podeEnviar}
            accessibilityRole="button"
          >
            {carregando ? (
              <ActivityIndicator color={colors.white} />
            ) : (
              <Text style={styles.botaoTexto}>Entrar</Text>
            )}
          </Pressable>

          {falha && <Text style={styles.erro}>{falha}</Text>}

          <Pressable onPress={verificarBackend} accessibilityRole="button">
            <Text style={styles.link}>
              {servico === null
                ? "Verificar conexao com o backend"
                : servico.ok
                  ? `Backend online · ${servico.ambiente}`
                  : `Backend indisponivel — toque para tentar de novo`}
            </Text>
          </Pressable>

          {servico && !servico.ok && <Text style={styles.ajuda}>{servico.texto}</Text>}

          <Text style={styles.ajuda}>
            Os dados do projeto sao sinteticos e nao ha validacao clinica. Nenhum resultado
            constitui diagnostico, prescricao ou recomendacao medica.
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  tela: { flex: 1, backgroundColor: colors.background },
  conteudo: { flexGrow: 1, justifyContent: "center", padding: spacing.lg },
  cartao: {
    backgroundColor: colors.surface,
    borderRadius: radii.banner,
    padding: spacing.xl,
    ...shadow,
  },
  titulo: { fontSize: fonts.header, fontWeight: "700", color: colors.primary },
  subtitulo: {
    fontSize: fonts.small,
    color: colors.textMuted,
    marginBottom: spacing.xl,
  },
  rotulo: {
    fontSize: fonts.small,
    fontWeight: "600",
    color: colors.text,
    marginBottom: spacing.xs,
  },
  entrada: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.input,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    fontSize: fonts.body,
    color: colors.text,
    backgroundColor: colors.white,
    marginBottom: spacing.lg,
  },
  botao: {
    backgroundColor: colors.primary,
    borderRadius: radii.input,
    paddingVertical: spacing.lg,
    alignItems: "center",
  },
  botaoInativo: { opacity: 0.6 },
  botaoTexto: { color: colors.white, fontSize: fonts.body, fontWeight: "700" },
  erro: {
    marginTop: spacing.md,
    color: colors.error,
    backgroundColor: colors.errorBg,
    borderRadius: radii.banner,
    padding: spacing.md,
    fontSize: fonts.small,
  },
  link: {
    marginTop: spacing.lg,
    color: colors.primary,
    fontSize: fonts.small,
    fontWeight: "600",
  },
  ajuda: { marginTop: spacing.sm, color: colors.textMuted, fontSize: fonts.tiny },
});
