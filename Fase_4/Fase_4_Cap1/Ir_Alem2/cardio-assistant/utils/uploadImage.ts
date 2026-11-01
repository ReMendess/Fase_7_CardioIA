import { Platform } from "react-native";

/**
 * Monta FormData compatível com web e dispositivos nativos.
 * Na web, { uri, type, name } não funciona — é preciso enviar Blob/File.
 */
export async function buildImageFormData(
  uri: string,
  mimeType = "image/jpeg",
  fileName = "xray.jpg"
): Promise<FormData> {
  const formData = new FormData();

  if (Platform.OS === "web") {
    const response = await fetch(uri);
    const blob = await response.blob();
    formData.append("image", blob, fileName);
  } else {
    formData.append("image", {
      uri,
      type: mimeType,
      name: fileName,
    } as unknown as Blob);
  }

  return formData;
}
