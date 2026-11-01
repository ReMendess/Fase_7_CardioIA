import React, { useState } from "react";
import {
  View,
  Text,
  Button,
  Image,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Platform,
  ScrollView,
} from "react-native";
import * as ImagePicker from "expo-image-picker";

import { API_URL } from "@/constants/api";
import { buildImageFormData } from "@/utils/uploadImage";

export default function HomeScreen() {
  const [image, setImage] = useState(null);
  const [result, setResult] = useState(null);
  const [confidence, setConfidence] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const pickImage = async () => {
    if (Platform.OS !== "web") {
      const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        Alert.alert("Permissão necessária", "Permita o acesso à galeria para selecionar imagens.");
        return;
      }
    }

    const response = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 1,
    });

    if (!response.canceled) {
      const asset = response.assets[0];
      setImage({
        uri: asset.uri,
        mimeType: asset.mimeType ?? "image/jpeg",
        fileName: asset.fileName ?? "xray.jpg",
      });
      setResult(null);
      setConfidence(null);
      setErrorMsg(null);
    }
  };

  const analyzeImage = async () => {
    if (!image) {
      Alert.alert("Atenção", "Selecione uma imagem antes de analisar.");
      return;
    }

    setLoading(true);
    setResult(null);
    setConfidence(null);
    setErrorMsg(null);

    try {
      const formData = await buildImageFormData(
        image.uri,
        image.mimeType,
        image.fileName
      );

      const response = await fetch(`${API_URL}/predict`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error ?? `Erro do servidor: ${response.status}`);
      }

      setResult(data.class);
      setConfidence(data.confidence);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Erro desconhecido";
      setErrorMsg(message);
      if (Platform.OS !== "web") {
        Alert.alert(
          "Erro na análise",
          `Servidor: ${API_URL}\n\n${message}\n\nConfirme que o backend está rodando (python app.py).`
        );
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <View style={styles.container}>
        <Text style={styles.title}>Assistente de Detecção de Pneumonia</Text>
        <Text style={styles.subtitle}>Envie uma radiografia de tórax para análise</Text>

        <Button title="Selecionar Imagem" onPress={pickImage} />

        {image && <Image source={{ uri: image.uri }} style={styles.image} />}

        {image && (
          <Button
            title={loading ? "Analisando..." : "Analisar"}
            onPress={analyzeImage}
            disabled={loading}
          />
        )}

        {loading && <ActivityIndicator size="large" style={styles.loader} />}

        {errorMsg && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{errorMsg}</Text>
          </View>
        )}

        {result && (
          <View style={styles.resultBox}>
            <Text style={styles.resultLabel}>Resultado:</Text>
            <Text style={[styles.resultValue, result === "Pneumonia" && styles.alert]}>
              {result}
            </Text>
            <Text style={styles.confidence}>Confiança: {confidence}%</Text>
          </View>
        )}

        <Text style={styles.apiHint}>Servidor: {API_URL}</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: {
    flexGrow: 1,
  },
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
    backgroundColor: "#f5f5f5",
    minHeight: "100%",
  },
  title: {
    fontSize: 22,
    fontWeight: "bold",
    marginBottom: 8,
    textAlign: "center",
  },
  subtitle: {
    fontSize: 14,
    color: "#666",
    marginBottom: 24,
    textAlign: "center",
  },
  image: {
    width: 250,
    height: 250,
    margin: 20,
    borderRadius: 8,
  },
  loader: {
    marginTop: 16,
  },
  errorBox: {
    marginTop: 16,
    padding: 12,
    backgroundColor: "#ffebee",
    borderRadius: 8,
    maxWidth: 320,
  },
  errorText: {
    color: "#c62828",
    textAlign: "center",
  },
  resultBox: {
    marginTop: 20,
    padding: 16,
    backgroundColor: "#fff",
    borderRadius: 8,
    alignItems: "center",
    minWidth: 200,
  },
  resultLabel: {
    fontSize: 16,
    fontWeight: "600",
  },
  resultValue: {
    fontSize: 24,
    fontWeight: "bold",
    marginVertical: 8,
    color: "#2e7d32",
  },
  alert: {
    color: "#c62828",
  },
  confidence: {
    fontSize: 16,
    color: "#555",
  },
  apiHint: {
    marginTop: 24,
    fontSize: 11,
    color: "#999",
  },
});
