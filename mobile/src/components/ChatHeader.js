import { StyleSheet, Text, View } from "react-native";

import { colors, fonts, spacing, shadow } from "../theme";

export default function ChatHeader({ online = false }) {
  return (
    <View style={styles.header}>
      <View style={styles.avatar}>
        <Text style={styles.avatarText}>❤</Text>
      </View>
      <View style={styles.titles}>
        <Text style={styles.title}>CardioAssist</Text>
        <View style={styles.statusRow}>
          <View
            style={[
              styles.statusDot,
              { backgroundColor: online ? colors.online : colors.textMuted },
            ]}
          />
          <Text style={styles.statusText}>
            {online ? "Conectado" : "Conectando…"}
          </Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
    ...shadow,
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primarySoft,
    alignItems: "center",
    justifyContent: "center",
    marginRight: spacing.md,
  },
  avatarText: {
    fontSize: fonts.header,
  },
  titles: {
    flex: 1,
  },
  title: {
    fontSize: fonts.title,
    fontWeight: "700",
    color: colors.text,
  },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 2,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  statusText: {
    fontSize: fonts.small,
    color: colors.textMuted,
  },
});