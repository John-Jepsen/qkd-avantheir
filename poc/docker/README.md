# Docker — POC

Self-contained Docker setup that bundles every piece of the MVP into a
single image: BB84 simulator, ETSI KME server, the FastAPI ML pipeline,
the TLS PSK demo, and the eight-criteria assertion script.

The trained ML pickles are baked in at build time, so containers start
instantly — no first-run training delay.

---

## TL;DR

```bash
# From the repo root
docker build -f poc/docker/Dockerfile -t qkd-poc .
docker run --rm qkd-poc
```

That runs the full MVP demo and prints `PASS` for all 8 exit criteria.
Total wall clock ≈ 1 minute (most of it is the KME pre-filling 50 keys).

---

## Build the image

```bash
cd /path/to/qkd-avantheir
docker build -f poc/docker/Dockerfile -t qkd-poc .
```

What happens:

1. `python:3.11-slim` base + system build tools (`gcc`, `g++`, `bash`,
   `curl`, `jq`).
2. `pip install` everything in `implementation/requirements.txt` plus
   `httpx` and `deap`.
3. `implementation/` and `poc/` copied into `/app`.
4. `python train_all_models.py` runs at build time so the runtime image
   ships with all 5 trained model pickles in `/app/implementation/data/`.

First build is on the order of 5 minutes (most of it is the qiskit /
scipy / scikit-learn install). Re-builds are seconds when only source
files change because the deps layer is cached.

---

## Run modes

The container's entrypoint routes the first argument to a command:

| Command | What it does | Useful flags |
|---------|--------------|--------------|
| `mvp` *(default)* | Runs `poc/scripts/run_mvp.sh` — every step, every assertion. Container exits 0 if all 8 criteria pass. | `--rm` to auto-clean |
| `api` | Starts the FastAPI ML pipeline on `0.0.0.0:8765`. | `-p 8765:8765` to publish |
| `kme` | Starts the ETSI KME on `0.0.0.0:5000`. | `-p 5000:5000` to publish |
| `psk-server` | Starts the TLS PSK Bob server on `0.0.0.0:8443`. | `-p 8443:8443` |
| `psk-client` | Runs the PSK Alice client once and exits. | Set `KME_URL` to point at the KME |
| `bash` | Drops into an interactive shell at `/app/implementation`. | `-it` |
| anything else | Exec'd directly — e.g., `python -c "..."` | |

Examples:

```bash
# Full demo
docker run --rm qkd-poc                     # implicit "mvp"
docker run --rm qkd-poc mvp                 # explicit

# Standalone API service (Swagger UI at http://localhost:8765/docs)
docker run --rm -p 8765:8765 qkd-poc api

# Standalone KME (ETSI 014 endpoints under /api/v1/keys/)
docker run --rm -p 5000:5000 qkd-poc kme

# Debug
docker run --rm -it qkd-poc bash
```

To capture evidence on the host filesystem, mount the evidence dir:

```bash
docker run --rm -v "$PWD/poc/evidence:/app/poc/evidence" qkd-poc mvp
```

After the run, `poc/evidence/*.json` will contain the captured outputs
documented in `poc/docs/RESULTS.md`.

---

## Multi-service: docker-compose

For exploring the system as separate long-lived services, use the compose
file. It defines `kme`, `api`, `psk-server`, `psk-client`, and `mvp` —
all sharing the same image.

```bash
# One-shot demo (runs the assertions, exits)
docker compose -f poc/docker/docker-compose.yml run --rm mvp

# Long-running services — KME on :5000, FastAPI on :8765
docker compose -f poc/docker/docker-compose.yml up kme api

# In another terminal, exercise them
curl http://localhost:5000/api/v1/keys/sae-bob/status
curl -X POST http://localhost:8765/analyze \
  -H "Content-Type: application/json" \
  -d '{"n_bits": 2048, "error_rate": 0.01, "eavesdrop": true, "backend": "classical"}'

# Run the PSK exchange against the running KME
docker compose -f poc/docker/docker-compose.yml up psk-server -d
docker compose -f poc/docker/docker-compose.yml run --rm psk-client

# Tear down
docker compose -f poc/docker/docker-compose.yml down
```

The healthchecks built into `kme` and `api` mean `psk-server` and
`psk-client` will wait until the KME is actually serving keys before
they start.

---

## Environment variables

| Variable | Default | Used by | Purpose |
|----------|---------|---------|---------|
| `API_PORT` | 8765 | `api` mode | Port FastAPI binds to |
| `KME_PORT` | 5000 | `kme` mode | Port the Flask KME binds to |
| `KME_URL` | `http://127.0.0.1:5000` | `psk-client` mode | KME endpoint Alice fetches the key from |
| `POC_SKIP_VENV` | `1` (set in image) | `mvp` mode | Skips creating an in-container venv since deps are already installed system-wide |

---

## Sizing

Final image is ~1.6 GB — most of which is qiskit-aer + scipy + scikit-learn
+ statsmodels + numpy. There is room to slim down (e.g., wheels-only
multi-stage build) but the simple `python:3.11-slim` base is the right
tradeoff for the POC: easy to reproduce, no surprise compilation needs.

If you only want the runtime API and not the full demo, you can use the
existing single-purpose `Dockerfile` at the repo root, which is the
production Cloud Run image and skips the POC scripts.

---

## Troubleshooting

**Build fails compiling numpy / scipy.** The `python:3.11-slim` base
needs `gcc` and `g++` to build wheels for ARM Macs. The Dockerfile
installs these. If you customize the base image, keep them.

**Container exits with `address already in use`.** Another process on
the host (or a previous container) is on the same port. `docker ps` to
find it. The `--rm` flag prevents stale containers from accumulating.

**`mvp` mode fails on the KME step.** The KME pre-fills 50 keys via
BB84 and does so twice (once at module import, once at CLI startup) for
about 30s total. If the assertion script's HTTP wait window of 90s
elapses, the host may be CPU-throttled. Increase the wait in
`poc/scripts/03_kme_psk_demo.sh` or check `docker stats` for CPU/IO
contention.

**`psk-client` connects to the wrong KME.** The default `KME_URL` is
`http://127.0.0.1:5000`, which only works inside the same container.
When using compose, the file sets `KME_URL=http://kme:5000` so Alice
hits the `kme` service over the compose network.
