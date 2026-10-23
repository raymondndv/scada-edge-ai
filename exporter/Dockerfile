FROM python:3.10-slim

# libgomp1 bắt buộc để XGBoost chạy trên Linux/ARM64
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# -u: log realtime ra console
CMD ["python", "-u", "stream_exporter.py"]
