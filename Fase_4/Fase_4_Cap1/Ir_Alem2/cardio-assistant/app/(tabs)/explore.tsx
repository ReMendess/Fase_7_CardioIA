import { ScrollView, StyleSheet } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { API_URL } from '@/constants/api';

export default function AboutScreen() {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <ThemedView style={styles.section}>
        <ThemedText type="title">Sobre o app</ThemedText>
        <ThemedText style={styles.paragraph}>
          Este assistente usa um modelo MobileNet treinado para classificar radiografias de tórax
          como Normal ou Pneumonia.
        </ThemedText>
      </ThemedView>

      <ThemedView style={styles.section}>
        <ThemedText type="subtitle">Como usar</ThemedText>
        <ThemedText style={styles.paragraph}>
          1. Inicie o backend Python na pasta backend.{'\n'}
          2. Abra a aba Análise e selecione uma imagem de raio-X.{'\n'}
          3. Toque em Analisar para enviar ao servidor.
        </ThemedText>
      </ThemedView>

      <ThemedView style={styles.section}>
        <ThemedText type="subtitle">Servidor configurado</ThemedText>
        <ThemedText style={styles.paragraph}>{API_URL}</ThemedText>
        <ThemedText style={styles.paragraph}>
          Em celular físico, crie um arquivo .env com EXPO_PUBLIC_API_URL=http://SEU_IP:5000
        </ThemedText>
      </ThemedView>

      <ThemedView style={styles.section}>
        <ThemedText type="subtitle">Aviso</ThemedText>
        <ThemedText style={styles.paragraph}>
          Ferramenta educacional. Não substitui diagnóstico médico profissional.
        </ThemedText>
      </ThemedView>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 24,
    gap: 16,
  },
  section: {
    gap: 8,
    marginBottom: 16,
  },
  paragraph: {
    lineHeight: 22,
  },
});
