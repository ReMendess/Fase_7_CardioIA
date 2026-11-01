import { Pressable, StyleSheet, Text, View } from "react-native";

import { colors, fonts, radii, spacing } from "../theme";

export default function ErrorBanner({ message, onRetry = null }) {
  return (
    <View style={styles.banner}>
      <Text style={styles.icon}>⚠️</Text>
      <View style={styles.body}>
        <Text style={styles.title}>Não foi possível responder</Text>
        <Text style={styles.message}>{message}</Text>
      </View>
      {onRetry && (
        <Pressable
          style={({ pressed }) => [
            styles.retryButton,
            pressed && styles.retryButtonPressed,
          ]}
          onPress={onRetry}
          accessibilityRole="button"
          accessibilityLabel="Tentar novamente"
        >
          <Text style={styles.retryText}>↻ Tentar novamente</Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: "row",
    alignItems: "flex-start",
    backgroundColor: colors.errorBg,
    borderWidth: 1,
    borderColor: "rgba(176, 42, 55, 0.25)",
    borderRadius: radii.banner,
    padding: spacing.md,
    gap: spacing.sm,
  },
  icon: {
    fontSize: 16,
    marginTop: 1,
  },
  body: {
    flex: 1,
  },
  title: {
    fontSize: fonts.small,
    fontWeight: "700",
    color: colors.error,
  },
  message: {
    fontSize: fonts.small,
    lineHeight: 18,
    color: colors.text,
    marginTop: 2,
  },
  retryButton: {
    alignSelf: "center",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.error,
    borderRadius: radii.chip,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  retryButtonPressed: {
    backgroundColor: colors.primarySoft,
  },
  retryText: {
    fontSize: fonts.small,
    fontWeight: "700",
    color: colors.error,
  },
});