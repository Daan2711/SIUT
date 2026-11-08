FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Usuario sin privilegios: si la app se ve comprometida, no tiene root
RUN useradd --create-home --uid 10001 appuser

# El código queda propiedad de root: appuser puede leerlo pero no modificarlo
COPY . .

# Carpeta de CV (UPLOAD_DIR por defecto): lo único que la app puede escribir
RUN mkdir -p /app/instance/uploads/cv && chown -R appuser:appuser /app/instance

USER appuser

EXPOSE 5000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} app:app"]
