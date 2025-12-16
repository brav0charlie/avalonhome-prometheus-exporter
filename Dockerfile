FROM python:3.12-alpine

WORKDIR /app

# Create non-root user/group
RUN addgroup -S app && adduser -S -G app app

# Copy app (and ensure ownership)
COPY app/exporter.py /app/exporter.py
RUN chown -R app:app /app

# Make logs unbuffered and avoid writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AVALON3_PORT=4028 \
    UPDATE_INTERVAL=10 \
    EXPORTER_PORT=9100

EXPOSE 9100

# Healthcheck hits /health using python stdlib (no curl/wget dependency)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9100/health', timeout=2).read()"

USER app

CMD ["python", "/app/exporter.py"]