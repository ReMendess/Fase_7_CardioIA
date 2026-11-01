import { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { colors, fonts, radii, spacing } from "../theme";

export default function ChatInput({ disabled = false, onSend }) {
  const [text, setText] = useState("");

  const canSend = text.trim().length > 0 && !disabled;

  const submit = () => {
    const clean = text.trim();
    if (!clean || disabled) return;
    onSend(clean);
    setText("");
  };

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.input}
        value={text}
        onChangeText={setText}
        placeholder="Escreva sua mensagem…"
        placeholderTextColor={colors.textMuted}
        maxLength={500}
        editable={!disabled}
        returnKeyType="send"
        onSubmitEditing={submit}
        accessibilityLabel="Campo de mensagem"
      />
      <Pressable
        style={({ pressed }) => [
          styles.sendButton,
          !canSend && styles.sendButtonDisabled,
          pressed && canSend && styles.sendButtonPressed,
        ]}
        onPress={submit}
        disabled={!canSend}
        accessibilityLabel="Enviar mensagem"
        accessibilityRole="button"
      >
        <Text style={styles.sendText}>➤</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
    backgroundColor: colors.surface,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  input: {
    flex: 1,
    minHeight: 46,
    borderRadius: radii.input,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.background,
    paddingHorizontal: spacing.lg,
    paddingVertical: 10,
    fontSize: fonts.body,
    color: colors.text,
  },
  sendButton: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  sendButtonDisabled: {
    backgroundColor: "#E3A9A2",
  },
  sendButtonPressed: {
    backgroundColor: colors.primaryDark,
  },
  sendText: {
    color: colors.white,
    fontSize: 20,
    fontWeight: "800",
    marginLeft: 2,
  },
});