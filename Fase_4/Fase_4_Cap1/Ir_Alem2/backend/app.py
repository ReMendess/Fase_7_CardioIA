from pathlib import Path
import io

from flask import Flask, request, jsonify
from flask_cors import CORS
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "mobilenet_pneumonia.keras"

app = Flask(__name__)
CORS(app)

if not MODEL_PATH.exists():
    raise FileNotFoundError(f"Modelo não encontrado: {MODEL_PATH}")

model = load_model(str(MODEL_PATH))


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": MODEL_PATH.name})


@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "Campo 'image' é obrigatório"}), 400

    file = request.files["image"]
    file_data = file.read()
    if not file_data:
        return jsonify({"error": "Nenhuma imagem enviada"}), 400

    try:
        file_bytes = io.BytesIO(file_data)
        img = image.load_img(file_bytes, target_size=(128, 128))
        img = image.img_to_array(img)
        img = img / 255.0
        img = np.expand_dims(img, axis=0)

        prediction = model.predict(img, verbose=0)
        probability = float(prediction[0][0])

        result = "Pneumonia" if probability > 0.5 else "Normal"
        confidence = probability if probability > 0.5 else 1 - probability

        return jsonify({
            "class": result,
            "confidence": round(confidence * 100, 2),
        })
    except Exception as exc:
        return jsonify({"error": f"Falha ao processar imagem: {exc}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
