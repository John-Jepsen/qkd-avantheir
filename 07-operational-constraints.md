# Operational Constraints and Deployment Considerations

## 1. Distance and Loss Limitations

### Three Distinct Deployment Scenarios

| Scenario | Typical Range | Trust Model | Key Infrastructure |
|----------|---------------|-------------|-------------------|
| Direct fiber QKD | 10s to ~100+ km per segment | End-to-end | Dark fiber or dedicated wavelength |
| Trusted-node backbone | 1000s of km | Trust at each node | Secured relay facilities |
| Satellite/free-space | Intercontinental | Satellite trust | Ground stations + space segment |

### Fiber QKD Distance Factors

| Factor | Impact |
|--------|--------|
| Optical loss | ~0.2 dB/km in telecom fiber; limits photon transmission |
| Detector dark counts | Noise floor limits signal-to-noise ratio |
| Chromatic dispersion | Timing uncertainty affects protocols |
| Polarization drift | Requires active compensation |
| Background light | In WDM scenarios, requires filtering |

### Practical Distance Guidance

```
Metro deployments (< 50 km):
- Generally straightforward with modern systems
- Key rates in kbps to Mbps range typical

Regional deployments (50-100+ km):
- Requires careful link engineering
- Key rates decrease significantly
- May need ultra-low-loss fiber, amplification research ongoing

Long-haul (> 100 km single span):
- Trusted nodes or quantum repeaters (future)
- Satellite relay for intercontinental
```

**Note:** Specific distance claims vary by vendor, system configuration, and environmental conditions. Always validate against vendor specifications and site surveys.

## 2. Infrastructure Requirements

### Optical Path Requirements

| Requirement | DV-QKD | CV-QKD |
|-------------|--------|--------|
| Fiber type | Single-mode, low-loss | Single-mode, low-loss |
| Dark fiber preferred | Yes | Yes |
| WDM compatibility | Possible with isolation | Possible with isolation |
| Fiber quality | High (low PMD, low loss) | High |
| Splice quality | Low loss, low reflectance | Low loss, low reflectance |

### Endpoint Equipment

**DV-QKD Systems:**
- Single-photon detectors (APDs or SNSPDs)
- Precise timing electronics
- Temperature stabilization
- Polarization control
- Single-photon sources or attenuated laser

**CV-QKD Systems:**
- Coherent detection (homodyne/heterodyne)
- Low-noise receivers
- Local oscillator management
- High-bandwidth electronics
- Phase and polarization tracking

### Environmental Requirements

| Factor | Specification |
|--------|---------------|
| Temperature | Typically 18-25°C, stable within ±2°C |
| Humidity | 30-60% RH, non-condensing |
| Vibration | Minimal; optical alignment sensitive |
| EMI | Shielded environment preferred |
| Power | Clean, uninterruptible supply |

## 3. Physical Security Requirements

### QKD Node Security

```
┌─────────────────────────────────────────────────────────────┐
│                    QKD Secure Facility                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Physical Security Layer                 │   │
│  │  - Access control (multi-factor)                    │   │
│  │  - Intrusion detection                              │   │
│  │  - CCTV monitoring                                  │   │
│  │  - Environmental monitoring                         │   │
│  │                                                     │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │           QKD Equipment Zone                 │   │   │
│  │  │  - Tamper-evident enclosures                │   │   │
│  │  │  - Tamper-responsive mechanisms             │   │   │
│  │  │  - Zeroization capability                   │   │   │
│  │  │                                             │   │   │
│  │  │  ┌─────────────┐    ┌─────────────┐        │   │   │
│  │  │  │  QKD Unit   │    │    KME      │        │   │   │
│  │  │  └─────────────┘    └─────────────┘        │   │   │
│  │  │                                             │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Fiber Entry:                                               │
│  - Protected conduit                                        │
│  - Intrusion detection on fiber path                       │
│  - Tamper-evident seals                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Trusted Node Security (Multi-Hop)

| Security Measure | Purpose |
|------------------|---------|
| Physical isolation | Prevent unauthorized access |
| Personnel vetting | Reduce insider threat |
| Dual-person integrity | Critical operations require two authorized persons |
| Audit logging | All access and operations recorded |
| Key material handling | Secure erasure after relay |
| Continuous monitoring | Real-time security status |

**Critical:** Trusted nodes see key material during relay. Physical and personnel security at these nodes is paramount.

## 4. Noise Tolerance and Key Rates

### QBER Thresholds

| QBER Range | Status | Action |
|------------|--------|--------|
| < 3% | Normal | Full key rate |
| 3-5% | Elevated | Monitor, investigate |
| 5-10% | Warning | Reduced key rate, active investigation |
| > 11% | Critical | Security threshold approached, may abort |

### Key Rate Factors

```
Secret Key Rate = Raw Rate × Sifting Factor × Error Correction Efficiency × Privacy Amplification Factor

Typical factors affecting each:
- Raw rate: Source brightness, detector efficiency, link loss
- Sifting: ~50% for BB84 (basis matching)
- Error correction: Depends on QBER, ~1.1× Shannon limit achievable
- Privacy amplification: Removes Eve's information, depends on QBER
```

### Key Rate vs Distance (Illustrative)

```
Key Rate (bps)
    │
10M ┤ ████
    │ █████
 1M ┤ ██████
    │ ███████
100k┤ ████████
    │ █████████
 10k┤ ██████████
    │ ███████████
  1k┤ ████████████
    │ █████████████
 100┤ ██████████████
    │ ███████████████
  10┤ ████████████████
    └─────────────────────────────
      10   30   50   70   90  110 km

Note: Actual rates vary significantly by system.
Contact vendor for specifications.
```

### Key Consumption Planning

| Application | Key Size | Rotation | Keys/Hour |
|-------------|----------|----------|-----------|
| AES-256 session key | 256 bits | 10 min | 6 |
| TLS PSK | 256 bits | Per session | Variable |
| IPsec IKE PPK | 256 bits | 1 hour | 1 |
| One-time pad | = message size | Per message | Impractical for bulk |

**Rule:** `Key generation rate > Peak key consumption rate`

## 5. Failure Modes and Redundancy

### Common Failure Modes

| Failure | Cause | Detection | Mitigation |
|---------|-------|-----------|------------|
| Fiber cut | Physical damage | Loss of signal | Redundant paths, fast failover |
| High QBER | Fiber disturbance, equipment drift | QBER monitoring | Automatic recalibration, fallback |
| Key exhaustion | Consumption > generation | Buffer monitoring | Rate limiting, fallback |
| Equipment failure | Hardware fault | Health checks | Redundant systems, spares |
| Timing drift | Clock instability | Sync monitoring | NTP/PTP, recalibration |

### Redundancy Patterns

**Active-Passive:**
```
Primary QKD Link ────────► Active
                          │
Backup QKD Link  ────────► Standby (failover)
```

**Active-Active:**
```
QKD Link A ──────┐
                 ├──► Key Aggregation ──► KME Buffer
QKD Link B ──────┘
```

**Hybrid Fallback:**
```
QKD Available? ──Yes──► Use QKD key
      │
      No
      │
      ▼
PQC Available? ──Yes──► Use PQC key exchange
      │
      No
      │
      ▼
Classical (degraded) ───► Alert + classical key exchange
```

### Failover Decision Matrix

| QKD Status | Key Buffer | Action |
|------------|------------|--------|
| Healthy | Adequate | Normal operation |
| Healthy | Low | Rate limit, alert |
| Degraded | Adequate | Use buffer, investigate |
| Degraded | Low | Prepare failover |
| Failed | Adequate | Use buffer, failover ready |
| Failed | Low | Execute failover |
| Failed | Empty | Failover or fail-closed |

## 6. Implementation Security

### Side-Channel Vulnerabilities

QKD implementations face practical attacks beyond protocol security:

| Attack Class | Description | Mitigation |
|--------------|-------------|------------|
| Detector blinding | Manipulate SPDs to control detection | Monitoring, countermeasures |
| Trojan horse | Inject light to probe internal state | Optical isolation, monitoring |
| Calibration attacks | Exploit calibration procedures | Secure calibration protocols |
| Timing attacks | Extract information from timing | Constant-time operations |

### Firmware and Supply Chain

| Concern | Mitigation |
|---------|------------|
| Malicious firmware | Verified boot, signed updates |
| Hardware tampering | Tamper-evident packaging, inspection |
| Supply chain compromise | Trusted suppliers, chain of custody |
| Backdoors | Code review, certification |

### Endpoint Security

QKD does NOT protect against:
- Compromised endpoints (malware)
- Insider threats with physical access
- Side-channel leakage from applications
- Key mishandling after delivery

**Defense in depth required:**
- Endpoint hardening
- Access control
- Monitoring and audit
- Secure key handling APIs

## 7. Monitoring and Operations

### Key Metrics Dashboard

| Category | Metrics |
|----------|---------|
| QKD Link Health | QBER, raw key rate, sifted key rate, secret key rate |
| Key Management | Buffer level, consumption rate, generation rate, key age distribution |
| Infrastructure | Link loss, detector counts, timing offset, temperature |
| Security | Failed authentications, anomalous patterns, intrusion alerts |

### Operational Procedures

| Procedure | Frequency | Owner |
|-----------|-----------|-------|
| Link calibration | Daily or as needed | Operations |
| QBER review | Continuous (automated) | Monitoring |
| Key audit | Weekly | Security |
| Physical inspection | Monthly | Security |
| Firmware updates | As released (tested) | Engineering |
| Incident response | As needed | Security |
| Capacity review | Quarterly | Planning |

### Alerting Thresholds

```yaml
alerts:
  - name: qber_warning
    condition: qber > 0.03
    severity: warning
    action: investigate

  - name: qber_critical
    condition: qber > 0.08
    severity: critical
    action: page_oncall, prepare_failover

  - name: key_buffer_low
    condition: key_buffer_count < 100
    severity: warning
    action: alert_ops

  - name: key_buffer_critical
    condition: key_buffer_count < 20
    severity: critical
    action: rate_limit, prepare_failover

  - name: link_down
    condition: no_signal_5min
    severity: critical
    action: failover, page_oncall
```

## 8. Cost Considerations

### Capital Expenditure

| Item | Range | Notes |
|------|-------|-------|
| QKD endpoint pair | $100K - $500K+ | Vendor and feature dependent |
| Dark fiber (lease) | $1K - $10K/km/year | Market dependent |
| Secure facility | Variable | May leverage existing |
| Integration engineering | $50K - $200K+ | Complexity dependent |

### Operational Expenditure

| Item | Range | Notes |
|------|-------|-------|
| Fiber maintenance | $5K - $20K/year | Per link |
| Equipment maintenance | 10-20% of CapEx/year | Support contracts |
| Operations staff | Variable | Shared with other duties possible |
| Power and cooling | $5K - $15K/year | Per node |

### TCO Guidance

QKD deployments make economic sense for:
- High-value data protection requirements
- Long-term confidentiality needs (decades)
- Regulatory or policy mandates
- Specific threat models (nation-state adversaries)

Compare against:
- Post-quantum cryptography (lower cost, broader applicability)
- Crypto-agility investment (prepare for future transitions)

## References

- [Beijing-Shanghai QKD Backbone](https://www.science.org/doi/10.1126/science.aap9681) - Chen et al. (2017)
- [Micius Satellite QKD](https://www.science.org/doi/10.1126/science.aan3211) - Yin et al. (2017)
- [Intercontinental Satellite QKD](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.120.030501) - Liao et al. (2018)
- [APS Review on Satellite QKD](https://journals.aps.org/rmp/abstract/10.1103/RevModPhys.92.025002)
- [NISTIR on Quantum-Resistant Security](https://csrc.nist.gov/publications/detail/nistir/8413/final)
