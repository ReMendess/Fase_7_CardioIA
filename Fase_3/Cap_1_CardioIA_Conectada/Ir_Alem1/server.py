from flask import Flask, request, jsonify
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# ==========================
# CONFIGURAÇÃO EMAIL
# ==========================

EMAIL_REMETENTE = "seu.email@exemplo.com"
EMAIL_SENHA = "SECRET"
EMAIL_DESTINO = "destino@exemplo.com"

# ==========================
# FUNÇÃO EMAIL
# ==========================

def enviar_email(alerta):

    assunto = "ALERTA MÉDICO"

    corpo = f"""
    Foi detectada uma situação de risco.

    ALERTA:
    {alerta}
    """

    msg = MIMEText(corpo)

    msg["Subject"] = assunto
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_DESTINO

    try:

        servidor = smtplib.SMTP("smtp.gmail.com", 587)

        servidor.starttls()

        servidor.login(EMAIL_REMETENTE, EMAIL_SENHA)

        servidor.send_message(msg)

        servidor.quit()

        print("E-mail enviado com sucesso.")

    except Exception as e:

        print("Erro ao enviar e-mail:", e)

# ==========================
# API REST
# ==========================

@app.route("/sinais", methods=["POST"])
def receber_sinais():

    dados = request.json

    temperatura = dados.get("temperatura")
    bpm = dados.get("bpm")
    movimento = dados.get("movimento")

    alerta = None

    # ==========================
    # REGRAS DE RISCO
    # ==========================

    if temperatura > 38:
        alerta = "FEBRE DETECTADA"

    elif bpm > 120:
        alerta = "TAQUICARDIA DETECTADA"

    elif movimento == False:
        alerta = "AUSÊNCIA DE MOVIMENTO"

    # ==========================

    if alerta:

        enviar_email(alerta)

        return jsonify({
            "status": "ALERTA",
            "mensagem": alerta
        })

    return jsonify({
        "status": "NORMAL",
        "mensagem": "Paciente estável"
    })

# ==========================

if __name__ == "__main__":

    app.run(debug=True)