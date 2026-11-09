"""Extensiones compartidas entre app.py y los controladores (evita imports circulares)."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# El almacenamiento se configura en app.py con RATELIMIT_STORAGE_URI
# (por defecto memory://: cada worker de gunicorn lleva su propio conteo;
# para un límite global entre workers usar redis://...).
limiter = Limiter(key_func=get_remote_address, default_limits=[])
