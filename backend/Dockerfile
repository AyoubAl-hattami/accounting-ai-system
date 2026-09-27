FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --requirement requirements.txt

COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY app ./app
COPY scripts/bootstrap_platform_admin.py ./scripts/bootstrap_platform_admin.py

USER app
EXPOSE 8000

# No --forwarded-allow-ips here on purpose.  uvicorn falls back to
# $FORWARDED_ALLOW_IPS and then to 127.0.0.1 (config.py:343-344), so the image
# keeps the safe default while the deployment that knows its own proxy
# addresses declares them next to the network it pins.  Passing the flag here
# would silently override that environment variable.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]
