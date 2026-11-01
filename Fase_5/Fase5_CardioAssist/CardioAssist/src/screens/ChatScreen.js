import { useCallback, useRef, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import ChatHeader from "../components/ChatHeader";
import ChatInput from "../components/ChatInput";
import ErrorBanner from "../components/ErrorBanner";
import MessageBubble from "../components/MessageBubble";
import TypingIndicator from "../components/TypingIndicator";
import { colors, spacing } from "../theme";
import {
  friendlyErrorText,
  sendChatMessage,
  WatsonApiError,
} from "../services/watsonApi";

const SUGGESTIONS = [
  "O que você faz?",
  "Dor no peito",
  "Quais sintomas devo observar?",
];

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function welcomeMessage() {
  return {
    id: "welcome",
    role: "assistant",
    text:
      "Olá! Sou o CardioAssist, um assistente virtual para orientação inicial sobre saúde cardiovascular.\n\nPosso ajudar você a entender alguns sintomas e identificar possíveis sinais de alerta.\n\nComo posso ajudar?",
    timestamp: new Date().toISOString(),
  };
}

export default function ChatScreen() {
  const [messages, setMessages] = useState([welcomeMessage()]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null); // { message, retriable }
  const [online, setOnline] = useState(false);

  const scrollRef = useRef(null);
  const busyRef = useRef(false);
  const sessionRef = useRef(null);
  const lastUserTextRef = useRef("");

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      scrollRef.current?.scrollToEnd?.({ animated: true });
    }, 60);
  }, []);

  const handleSend = useCallback(async (rawText) => {
    const text = String(rawText).trim();
    if (!text || busyRef.current) return;

    busyRef.current = true;
    lastUserTextRef.current = text;
    setError(null);
    setSending(true);

    setMessages((prev) => [
      ...prev,
      { id: makeId(), role: "user", text, timestamp: new Date().toISOString() },
    ]);

    try {
      const result = await sendChatMessage(text, {
        sessionId: sessionRef.current,
      });

      sessionRef.current = result.sessionId ?? sessionRef.current;
      setOnline(true);

      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: "assistant",
          text: result.reply,
          timestamp: result.timestamp,
        },
      ]);
    } catch (err) {
      const retriable = err instanceof WatsonApiError ? err.retriable : true;
      setError({ message: friendlyErrorText(err), retriable });
    } finally {
      busyRef.current = false;
      setSending(false);
    }
  }, []);

  const handleRetry = useCallback(() => {
    if (!lastUserTextRef.current) return;
    handleSend(lastUserTextRef.current);
  }, [handleSend]);

  const showSuggestions = messages.length === 1 && !sending && !error;

  return (
    <View style={styles.screen}>
      <ChatHeader online={online} />

      <ScrollView
        ref={scrollRef}
        style={styles.messages}
        contentContainerStyle={styles.messagesContent}
        keyboardShouldPersistTaps="handled"
        onContentSizeChange={scrollToBottom}
      >
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {sending && <TypingIndicator />}

        {error && (
          <ErrorBanner
            message={error.message}
            onRetry={error.retriable ? handleRetry : null}
          />
        )}
      </ScrollView>

      {showSuggestions && (
        <View style={styles.suggestions}>
          {SUGGESTIONS.map((suggestion) => (
            <Pressable
              key={suggestion}
              style={({ pressed }) => [
                styles.chip,
                pressed && styles.chipPressed,
              ]}
              onPress={() => handleSend(suggestion)}
              accessibilityRole="button"
            >
              <Text style={styles.chipText}>{suggestion}</Text>
            </Pressable>
          ))}
        </View>
      )}

      <ChatInput disabled={sending} onSend={handleSend} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.background,
  },
  messages: {
    flex: 1,
  },
  messagesContent: {
    padding: spacing.lg,
    paddingBottom: spacing.xl,
    rowGap: spacing.md,
  },
  suggestions: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xs,
  },
  chip: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 18,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  chipPressed: {
    backgroundColor: colors.primarySoft,
  },
  chipText: {
    color: colors.primary,
    fontSize: 14,
    fontWeight: "600",
  },
});