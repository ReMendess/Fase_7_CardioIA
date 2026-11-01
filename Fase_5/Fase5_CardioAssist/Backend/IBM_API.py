"""
CardioAssist — Configuração e cliente do IBM Watson Assistant.

As credenciais vem **somente** de variáveis de ambiente
(WATSON_API_KEY, WATSON_SERVICE_URL, WATSON_ASSISTANT_ID, WATSON_ENVIRONMENT_ID).
Copie `Backend/.env.example` para `Backend/.env` e preencha localmente.
"""

import os

from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

# Credenciais: lidas do ambiente. Sem valor padrao — um default aqui faria o
# servico autenticar com uma credencial de exemplo sem o operador perceber.
API_KEY = os.getenv("WATSON_API_KEY", "")
SERVICE_URL = os.getenv("WATSON_SERVICE_URL", "")
ASSISTANT_ID = os.getenv("WATSON_ASSISTANT_ID", "")
ENVIRONMENT_ID = os.getenv("WATSON_ENVIRONMENT_ID", "")

# Versão da API de Watson Assistant usada pelo SDK
VERSION = "2024-08-25"

# Timeout de rede para as chamadas a Watson (segundos)
WATSON_TIMEOUT = 30


def get_assistant() -> AssistantV2:
    """Retorna un cliente AssistantV2 autenticado y listo para usar."""
    authenticator = IAMAuthenticator(API_KEY)
    assistant = AssistantV2(version=VERSION, authenticator=authenticator)
    assistant.set_service_url(SERVICE_URL)
    assistant.set_http_config({"timeout": WATSON_TIMEOUT})
    return assistant
