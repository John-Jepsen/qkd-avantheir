# POC image: bundles BB84 simulator, KME, FastAPI ML pipeline, and the
# MVP demo scripts. One image, multiple entry modes.
#
# Build (from repo root):
#   docker build -f poc/docker/Dockerfile -t qkd-poc .
#
# Run the full MVP demo (~1 min, hits all 8 exit criteria):
#   docker run --rm qkd-poc mvp
#
# Run just the FastAPI service:
#   docker run --rm -p 8765:8765 qkd-poc api
#
# Run just the KME server:
#   docker run --rm -p 5000:5000 qkd-poc kme
#
# Drop into a shell for debugging:
#   docker run --rm -it qkd-poc bash

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    POC_SKIP_VENV=1

# Build tools needed for numpy/scipy/qiskit-aer wheels on slim base.
# bash + curl are needed by the POC scripts; jq is convenience for evidence.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ bash curl jq procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for layer caching.
COPY implementation/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && \
    pip install httpx deap

# Copy implementation source and POC scripts.
COPY implementation/ /app/implementation/
COPY poc/            /app/poc/

# If the host's COPY already brought in trained pickles, keep them. Otherwise
# train from scratch. This makes the build fast on a developer machine that
# has run the host MVP at least once, while still working from a clean checkout.
RUN cd /app/implementation && \
    if [ -f data/eavesdrop_model.pkl ] && [ -f data/attack_model.pkl ] && [ -f data/param_tuner_model.pkl ]; then \
        echo "Models already present — skipping training"; \
    else \
        python train_all_models.py; \
    fi

# Make scripts executable (in case the build host stripped the bit).
RUN chmod +x /app/poc/scripts/*.sh /app/poc/docker/entrypoint.sh

# Default ports: KME=5000, FastAPI=8765, PSK Bob=8443.
EXPOSE 5000 8765 8443

ENTRYPOINT ["/app/poc/docker/entrypoint.sh"]
CMD ["mvp"]
