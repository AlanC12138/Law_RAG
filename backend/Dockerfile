FROM python:3.11-slim as builder

# Use /opt as WORKDIR so poetry creates the venv at /opt/.venv (in-project mode).
# That makes every script shebang read #!/opt/.venv/bin/python — the same path
# we'll use in the final stage, avoiding the "exec: no such file" shebang mismatch.
WORKDIR /opt

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --user --no-cache-dir poetry

COPY pyproject.toml poetry.lock* /opt/

RUN /root/.local/bin/poetry config virtualenvs.in-project true && \
    /root/.local/bin/poetry install --without dev --no-root

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
# /opt/.venv is outside /app — bind mounts on /app won't touch it
ENV PATH="/opt/.venv/bin:$PATH"

COPY --from=builder /opt/.venv /opt/.venv

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
