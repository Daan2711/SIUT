"""Envío de correos con la API HTTPS de Brevo (https://www.brevo.com).

El plan gratis de Render bloquea el SMTP saliente, por eso se usa la API
HTTPS. Sin dependencias nuevas: solo la librería estándar.

Variables de entorno (ver docs/DESPLIEGUE_RENDER.md):
- BREVO_API_KEY: clave de la API de Brevo (secreto).
- CORREO_REMITENTE: correo verificado en Brevo como remitente.
- NOMBRE_REMITENTE: opcional, nombre que ve el destinatario (por defecto «SIUT»).
"""
import json
import os
import urllib.error
import urllib.request

BREVO_URL = 'https://api.brevo.com/v3/smtp/email'
TIEMPO_ESPERA = 10   # segundos


class CorreoNoEnviado(Exception):
    """Brevo no aceptó el correo o no respondió. El mensaje no incluye la clave."""


def correo_configurado():
    return bool(os.getenv('BREVO_API_KEY') and os.getenv('CORREO_REMITENTE'))


def enviar_correo(destinatario, asunto, texto, html=None):
    """Envía un correo. Lanza CorreoNoEnviado si falla."""
    if not correo_configurado():
        raise CorreoNoEnviado('Falta configurar BREVO_API_KEY o CORREO_REMITENTE')

    cuerpo = {
        'sender': {
            'name': os.getenv('NOMBRE_REMITENTE') or 'SIUT',
            'email': os.getenv('CORREO_REMITENTE'),
        },
        'to': [{'email': destinatario}],
        'subject': asunto,
        'textContent': texto,
    }
    if html:
        cuerpo['htmlContent'] = html

    peticion = urllib.request.Request(
        BREVO_URL,
        data=json.dumps(cuerpo).encode('utf-8'),
        headers={
            'api-key': os.getenv('BREVO_API_KEY'),
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA) as respuesta:
            if not 200 <= respuesta.status < 300:
                raise CorreoNoEnviado(f'Brevo respondió {respuesta.status}')
    except urllib.error.HTTPError as error:
        # El cuerpo de Brevo explica el motivo (p. ej. remitente sin verificar)
        detalle = error.read(300).decode('utf-8', 'replace')
        raise CorreoNoEnviado(f'Brevo respondió {error.code}: {detalle}') from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise CorreoNoEnviado(f'No se pudo conectar con Brevo: {error}') from None
