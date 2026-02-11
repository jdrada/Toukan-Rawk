# Stage 1: Install dependencies
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.prod.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.prod.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ app/
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
