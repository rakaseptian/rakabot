# =====================================================================
# AkarAI Studio - Wan 2.2 Animate Serverless Worker (MINIMAL)
#
# Strategi: image TIDAK berisi ComfyUI & model.
#   - ComfyUI + custom node + model SEMUA dari Network Volume
#     (volume 7p0yl3jbav, 100GB, EU-RO-1)
#   - Image hanya: python + runpod SDK + handler.py + start.sh
#
# Ukuran image : ~400MB (bukan 40GB)
# Build        : cepat, cocok untuk GitHub Actions (free)
# =====================================================================

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Direktori tempat Network Volume di-mount (RunPod serverless)
ENV COMFY_VOLUME=/runpod-volume

# ---------------------------------------------------------------
# System deps ringan
# ---------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ffmpeg \
        procps \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------
# Python deps
# ---------------------------------------------------------------
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------
# Worker files
# ---------------------------------------------------------------
COPY handler.py /handler.py
COPY start.sh /start.sh
COPY workflow_api.json /workflow_api.json
RUN chmod +x /start.sh

# Port ComfyUI (internal, tidak di-expose ke publik)
EXPOSE 8188

CMD ["/start.sh"]
