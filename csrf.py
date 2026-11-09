"""Protección CSRF basada en un token por sesión (sin dependencias extra).

El token se guarda en la sesión firmada de Flask y el frontend lo envía en la
cabecera `X-CSRF-Token`. Otro sitio no puede leer el token (política de mismo
origen) ni fijar esa cabecera en una petición entre sitios sin CORS, así que
una petición falsificada no lo trae.

Uso en una ruta:
    if not csrf_valido():
        return jsonify(...), 403
"""
import hmac
import secrets

from flask import request, session

CLAVE_SESION = '_csrf_token'
CABECERA = 'X-CSRF-Token'


def token_csrf():
    """Token CSRF de la sesión actual (se crea la primera vez)."""
    token = session.get(CLAVE_SESION)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CLAVE_SESION] = token
    return token


def csrf_valido():
    """True si la petición trae en la cabecera el token de su sesión."""
    esperado = session.get(CLAVE_SESION)
    enviado = request.headers.get(CABECERA, '')
    return bool(esperado) and hmac.compare_digest(enviado.encode(), esperado.encode())
