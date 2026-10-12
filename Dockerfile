# Deployment image for the FastAPI backend on Render.
#
# Render's Docker runtime builds the `Dockerfile` at the repository root
# (root-directory defaults to `.`), so this file lives here rather than in
# backend/deploy/. It mirrors backend/deploy/Dockerfile.api but uses a
# CPU-only PyTorch build and the slim requirements-api.txt, because the API
# never imports cv2 / timm / mlflow / onnx / torchvision.

FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --no-cache-dir --upgrade pip

# CPU-only torch (~200MB) instead of the default ~2.5GB CUDA wheel.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.getenv('PORT', '8000') + '/health')"

CMD ["sh", "-c", "uvicorn backend.deploy.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
