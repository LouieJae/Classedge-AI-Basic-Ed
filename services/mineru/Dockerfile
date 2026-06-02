FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV MINERU_CACHE_DIR=/data/cache

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8765"]
