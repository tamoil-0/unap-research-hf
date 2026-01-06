FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Cache persistente de HF
ENV HF_HOME=/data/hf
ENV TRANSFORMERS_CACHE=/data/hf
ENV TORCH_HOME=/data/torch

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

COPY models_semantic/ ./models_semantic/

# Verificar que los archivos LFS se descargaron correctamente
RUN if [ ! -f models_semantic/faiss.index ]; then \
        echo "ERROR: faiss.index not found!"; \
        exit 1; \
    fi && \
    FILE_SIZE=$(stat -f%z models_semantic/faiss.index 2>/dev/null || stat -c%s models_semantic/faiss.index) && \
    echo "faiss.index size: $FILE_SIZE bytes" && \
    if [ "$FILE_SIZE" -lt 1000 ]; then \
        echo "ERROR: faiss.index is too small (probably a Git LFS pointer)"; \
        cat models_semantic/faiss.index; \
        exit 1; \
    fi

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
