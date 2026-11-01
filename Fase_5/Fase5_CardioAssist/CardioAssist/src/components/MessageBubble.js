import { StyleSheet, Text, View } from "react-native";

import { colors, fonts, radii, spacing } from "../theme";

function formatTime(iso) {
  if (!iso) return "";
  try {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    const hh = String(date.getHours()).padStart(2, "0");
    const mm = String(date.getMinutes()).padStart(2, "0");
    return `${hh}:${mm}`;
  } catch {
    return "";
  }
}

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <View style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}>
      {!isUser && (
        <View style={styles.miniAvatar}>
          <Text style={styles.miniAvatarText}>❤</Text>
        </View>
      )}
      <View
        style={[
          styles.bubble,
          isUser ? styles.bubbleUser : styles.bubbleAssistant,
        ]}
      >
        {!isUser && <Text style={styles.senderLabel}>CardioAssist</Text>}
        <Text style={isUser ? styles.textUser : styles.textAssistant}>
          {message.text}
        </Text>
        <Text
          style={[styles.time, isUser ? styles.timeUser : styles.timeAssistant]}
        >
          {formatTime(message.timestamp)}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "flex-end",
    maxWidth: "85%",
  },
  rowUser: {
    alignSelf: "flex-end",
  },
  rowAssistant: {
    alignSelf: "flex-start",
  },
  miniAvatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.primarySoft,
    alignItems: "center",
    justifyContent: "center",
    marginRight: spacing.sm,
    marginBottom: spacing.xs,
  },
  miniAvatarText: {
    fontSize: 13,
  },
  bubble: {
    flexShrink: 1,
    borderRadius: radii.bubble,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: spacing.xs,
  },
  bubbleUser: {
    backgroundColor: colors.primary,
    borderBottomRightRadius: 4,
  },
  bubbleAssistant: {
    backgroundColor: colors.assistantBubble,
    borderTopLeftRadius: 4,
  },
  senderLabel: {
    fontSize: fonts.tiny,
    fontWeight: "700",
    color: colors.primary,
    textTransform: "uppercase",
    marginBottom: 2,
    letterSpacing: 0.4,
  },
  textUser: {
    fontSize: fonts.body,
    lineHeight: 22,
    color: colors.white,
  },
  textAssistant: {
    fontSize: fonts.body,
    lineHeight: 22,
    color: colors.text,
  },
  time: {
    fontSize: fonts.tiny,
    marginTop: 4,
    textAlign: "right",
  },
  timeUser: {
    color: "rgba(255, 255, 255, 0.8)",
  },
  timeAssistant: {
    color: colors.textMuted,
  },
});