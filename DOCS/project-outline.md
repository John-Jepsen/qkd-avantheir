Capstone Project Outline — Submission 2

Student: John Jepsen
Program: MSCS (Season 04 Masters)
Date: March 30, 2026

⸻

Abstract

This project investigates the integration of Quantum Key Distribution (QKD) into enterprise network security through a machine learning–augmented architecture. The work centers on replacing classical key exchange mechanisms, such as Diffie-Hellman and Elliptic Curve Diffie-Hellman (ECDHE), with QKD-derived symmetric key material across TLS 1.3, IPsec/IKEv2 VPNs, and service-to-service authentication systems.

A core contribution of this project is the introduction of machine learning as a first-class component of QKD systems. Rather than treating QKD as a static cryptographic primitive, this work frames it as a dynamic system that produces observable signals—such as Quantum Bit Error Rate (QBER), key generation rates, and traffic patterns—which can be modeled, predicted, and classified using modern machine learning techniques. These models enable detection of adversarial behavior, adaptive tuning of protocol parameters, and improved operational resilience.

The project adopts a hybrid security model combining QKD with Post-Quantum Cryptography (PQC), specifically ML-KEM, to address both physical-layer and computational threats. This hybrid approach directly targets the “harvest now, decrypt later” threat model, where adversaries collect encrypted traffic today with the intention of decrypting it using future quantum capabilities.

The final deliverables include a technical documentation suite, a reference architecture, a working implementation of a QKD key delivery pipeline, and a set of machine learning modules that enhance detection, prediction, and system optimization.

⸻

1. System Overview

Machine Learning–Driven Architecture

The system is structured as a pipeline where machine learning operates alongside and across all layers rather than as a post-processing addition.

QKD Physical Layer → Key Distillation → KME → Application Protocols
         │                    │             │             │
         └──────── ML SIGNAL EXTRACTION AND ANALYSIS ─────┘

Machine learning modules consume signals from:
	•	QBER measurements
	•	Basis mismatch rates
	•	Key generation throughput
	•	KME request patterns
	•	Error correction statistics

These signals form the basis for classification, forecasting, anomaly detection, and adaptive control.

⸻

Component Map

┌─────────────────────────────────────────────────────────────────────┐
│                         QKD Physical Layer                          │
│  Alice Node ─── quantum channel ───► Bob Node (BB84 protocol)       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                Distillation Pipeline                                │
│  Sifting → QBER → Error Correction → Privacy Amplification          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│        Machine Learning Analysis Layer                              │
│  - Eavesdropper Classification                                      │
│  - Noise Prediction (time series)                                   │
│  - Anomaly Detection (KME traffic)                                  │
│  - Attack Classification                                            │
│  - Parameter Optimization                                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Key Management Entity (ETSI GS QKD 014)                │
└──────────┬──────────────────────────────────────────┬──────────────-┘
           ▼                                          ▼
     TLS 1.3 PSK                              IPsec / IKEv2 PPK
     Service Mesh Auth                        Hybrid QKD + PQC


⸻

Component Relationships

Component	Role	ML Interaction	Consumed By
BB84 Simulator	Generates raw key material	Produces training signals (QBER, noise)	KME, ML modules
ML Modules	Analyze and predict system behavior	Core analytical layer	Security monitoring, tuning
KME Server	Stores and distributes keys	Monitored for anomalies	TLS, IPsec, services
TLS/IPsec Integrations	Consume QKD keys	Use ML-informed parameters	End systems
Hybrid QKD+PQC Layer	Combines entropy sources	Evaluated via ML metrics	High-assurance deployments


⸻

2. Business Logic

The system operates as a closed-loop adaptive security pipeline.
	•	QKD generates entropy and observable channel metrics
	•	Machine learning models interpret those metrics
	•	Outputs influence system decisions:
	•	Abort thresholds
	•	Key refresh intervals
	•	Protocol mode selection
	•	Attack classification

Key principle:
	•	Static threshold systems (e.g., fixed QBER cutoff) miss subtle attacks
	•	Learned models detect patterns below threshold boundaries

Example:
	•	Traditional rule: abort if QBER > 11%
	•	ML model: detect structured deviations at 6–8% QBER

This shift moves QKD from a binary system to a probabilistic security model.

⸻

3. Major Milestones

Milestone 1 — QKD Foundations + ML Framing
	•	Formalize BB84 and variants
	•	Define all measurable signals for ML use
	•	Establish dataset structure for training models

⸻

Milestone 2 — Protocol Integration
	•	Map QKD outputs into:
	•	TLS 1.3 PSK modes
	•	IKEv2 PPK (RFC 8784)
	•	Service mesh authentication
	•	Define ML-informed parameter hooks

⸻

Milestone 3 — Key Management + Observability
	•	Implement ETSI QKD 014 KME
	•	Add logging and telemetry pipelines
	•	Feed structured data into ML models

⸻

Milestone 4 — Implementation + ML Integration
	•	Build BB84 simulator
	•	Implement KME server
	•	Integrate ML modules:
	•	Classification
	•	Forecasting
	•	Anomaly detection

⸻

Milestone 5 — Evaluation + Synthesis
	•	Validate system end-to-end
	•	Measure ML performance vs static rules
	•	Produce documentation and final analysis

⸻

4. Specifications

Machine Learning Requirements
	•	Supervised learning:
	•	Attack classification (multi-class)
	•	Eavesdropper detection
	•	Unsupervised learning:
	•	KME anomaly detection
	•	Time-series modeling:
	•	QBER forecasting
	•	Channel stability prediction
	•	Optimization:
	•	Adaptive parameter tuning

⸻

Implementation Requirements
	•	BB84 simulation with configurable noise
	•	Full distillation pipeline
	•	REST-based KME (ETSI QKD 014)
	•	TLS PSK demonstration using QKD keys
	•	IPsec PPK configuration mapping

⸻

5. Technology Stack

Core Stack
	•	Python 3.10+
	•	Flask (KME API)
	•	cryptography (AES-GCM, HKDF)

Machine Learning
	•	scikit-learn
	•	Random Forest
	•	Gradient Boosting
	•	Isolation Forest
	•	statsmodels
	•	ARIMA time-series forecasting

⸻

6. Machine Learning as Core System Layer

Five ML modules were introduced:
	•	Eavesdropper classifier
	•	Parameter tuner
	•	Noise predictor
	•	KME anomaly detector
	•	Attack classifier

Measured results Goals:
	•	Classification accuracy up to 96%
	•	QBER prediction error ≈ 0.006 MAE
	•	Anomaly detection rate ≈ 86%

Justification
	•	QKD produces structured, high-signal data
	•	Static thresholds fail under partial attacks
	•	ML captures multi-dimensional patterns across:
	•	Time
	•	Noise
	•	traffic behavior

Result:
	•	Increased detection sensitivity
	•	Adaptive system behavior
	•	Stronger hybrid QKD + PQC security model

⸻

Key Insight

QKD alone provides secure key generation.
Machine learning turns it into an adaptive security system.

⸻