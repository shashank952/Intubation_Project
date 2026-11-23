# Deployment image for the FastAPI backend on Render.
#
# Render's Docker runtime builds the `Dockerfile` at the repository root
# (root-directory defaults to `.`), so this file lives here rather than in
# backend/deploy/. It mirrors backend/deploy/Dockerfile.api but uses a
# CPU-only PyTorch build and the slim requirements-api.txt. Image analysis
# (ultralytics + OpenCV) is the only heavy extra on this path.

FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

# CPU-only torch + torchvision; ultralytics needs torchvision and the PyPI
# default would pull the CUDA wheels.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.getenv('PORT', '8000') + '/health')"

CMD ["sh", "-c", "uvicorn backend.deploy.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
