FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

# Create empty .env file to prevent slowapi/starlette FileNotFoundError
RUN touch /app/.env

EXPOSE 8000

COPY --from=datadog/serverless-init:1 /datadog-init /app/datadog-init

ENTRYPOINT ["/app/datadog-init"]

CMD ["ddtrace-run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
