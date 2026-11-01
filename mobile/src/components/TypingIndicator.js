import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { colors, fonts, radii, spacing } from "../theme";

const DOTS = 3;
const FRAME_MS = 400;

/**
 * Indicador de digitação com três pontos que "pulsam" em sequência.
 */
export default function TypingIndicator() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActive((frame) => (frame + 1) % DOTS);
    }, FRAME_MS);
    return () => clearInterval(timer);
  }, []);

  return (
    <View style={styles.row}>
      <View style={styles.miniAvatar}>
        <Text style={styles.miniAvatarText}>❤</Text>
      </View>
      <View style={styles.bubble}>
        <Text style={styles.sender}>CardioAssist</Text>
        <View style={styles.dotsRow}>
          {Array.from({ length: DOTS }, (_, index) => (
            <View
              key={index}
              style={[
                styles.dot,
                index === active ? styles.dotActive : styles.dotIdle,
              ]}
            />
          ))}
          <Text style={styles.label}>escrevendo…</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "flex-end",
    alignSelf: "flex-start",
    maxWidth: "85%",
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
    backgroundColor: colors.assistantBubble,
    borderRadius: radii.bubble,
    borderTopLeftRadius: 4,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  sender: {
    fontSize: fonts.tiny,
    fontWeight: "700",
    color: colors.primary,
    textTransform: "uppercase",
    letterSpacing: 0.4,
    marginBottom: 4,
  },
  dotsRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    marginRight: 5,
  },
  dotActive: {
    backgroundColor: colors.primary,
    opacity: 1,
  },
  dotIdle: {
    backgroundColor: colors.primary,
    opacity: 0.25,
  },
  label: {
    fontSize: fonts.small,
    color: colors.textMuted,
    marginLeft: 4,
  },
});