FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Usuario sin privilegios: si la app se ve comprometida, no tiene root
RUN useradd --create-home --uid 10001 appuser

# El código queda propiedad de root: appuser puede leerlo pero no modificarlo.
# La app no escribe en disco: los CV se guardan en la base de datos.
COPY . .

USER appuser

EXPOSE 5000

# Render define PORT. 2 workers caben en los 512 MB del plan gratis; el
# timeout de 60 s cubre el arranque en frío de Neon y la subida de un CV.
# Los logs (accesos y errores) van a stdout/stderr, que Render muestra.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers ${WEB_CONCURRENCY:-2} --timeout 60 --access-logfile - --error-logfile - app:app"]
