# QKD Key Infrastructure — Avantheir Initiative

![QKD UML Diagram](DOCS/images/qkd-image.png)

ML-augmented Quantum Key Distribution for enterprise security. Replaces classical key exchange (DH/ECDHE) with QKD-derived symmetric material across TLS 1.3, IPsec/IKEv2, and service mesh authentication.

## Structure

| Directory | Contents |
|-----------|----------|
| `01-qkd-foundations/` | BB84, CV-QKD, MDI-QKD, TF-QKD protocols and global deployments |
| `02-tls-integration/` | TLS 1.3 PSK + hybrid QKD+PQC |
| `03-ipsec-ikev2-integration/` | IPsec RFC 8784 mixed-PSK |
| `04-service-mesh-auth/` | Symmetric rekeying, SDN-controlled allocation |
| `05-key-management/` | ETSI QKD 014 key lifecycle |
| `06-vendor-analysis/` | Toshiba, IDQ/IonQ, QuantumCTek, LuxQuanta, Q\*Bird, QLabs, IBM, Lockheed |
| `07-operational-constraints/` | Distance, cost, failure modes, certification gaps |
| `08-references/` | Full reference list |
| `implementation/` | BB84 simulator, KME server, ML pipeline, adversarial gym |
| `frontend/` | React + D3 adversarial benchmark dashboard |
| `DOCS/` | Capstone outline, architecture diagrams, vocab guide |

## Quick Start

```bash
cd implementation
pip install -r requirements.txt

# Terminal 1 — KME server
python kme_server.py

# Terminal 2 — FastAPI pipeline (port 8000)
uvicorn api:app --reload --port 8000

# Terminal 3 — Frontend (port 3000)
cd ../frontend && npm install && npm run dev
```

See [implementation/README.md](implementation/README.md) for full setup details.

## ML Pipeline

Five models form a closed-loop adaptive security layer:

- **Eavesdrop detection** — RandomForest on 8-feature BB84 signal vector
- **Attack classification** — GradientBoosting, 5 classes (intercept-resend, beam-splitting, PNS, Trojan horse, clean)
- **QBER forecasting** — ARIMA time-series prediction
- **Parameter tuning** — GB Regressor for optimal BB84 config
- **KME anomaly detection** — Isolation Forest on traffic patterns

## Adversarial Agents
![Adversarial Agents UML Diagram](DOCS/images/adversarial-agents-uml.png)

DEAP evolutionary gym co-evolves attack strategies against defender models. Perturbations are bounded by QKD physics constraints (covariance enforcement, per-feature bounds). Phylogeny tree tracks attack lineage across generations.

## Vocab Quiz

Open [`quiz.html`](quiz.html) in a browser — no build step needed. Flash cards and multiple-choice drawn from 245 QKD terms.


