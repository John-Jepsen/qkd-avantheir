# Operational Constraints and Deployment Considerations

## 1. Distance and Loss Limitations

### Deployment Scenarios

| Scenario | Typical Range | Trust Model | Key Infrastructure |
|----------|---------------|-------------|-------------------|
| Direct fiber QKD | Metro (<50 km), regional (50-100+ km) | End-to-end | Dark fiber or dedicated wavelength |
| Trusted-node backbone | 1000s of km | Trust at each node | Secured relay facilities |
| Satellite/free-space | Intercontinental | Satellite trust | Ground stations + space segment |

### Practical Distance Tiers

| Tier | Distance | Key Rate | Feasibility | Vendor Examples |
|------|----------|----------|-------------|-----------------|
| Metro | <50 km | Mbps range | Production-ready today | Toshiba, IDQ/IonQ, LuxQuanta, Q*Bird |
| Regional | 50-100 km | kbps to low Mbps | Achievable with careful engineering | Toshiba (80 km DWDM), LuxQuanta (120 km CV-QKD) |
| Long-haul | 100-300 km | bps to low kbps | Possible but marginal | Q*Bird MDI (303 km demo), Toshiba (184 km demo) |
| Ultra-long | 300-1000+ km | Sub-bps (lab only) | Requires TF-QKD or trusted nodes | QuantumCTek (12,000+ km trusted-node) |

### Fiber QKD Distance Factors

| Factor | Impact |
|--------|--------|
| Optical loss | ~0.2 dB/km in telecom fiber; ~0.16 dB/km ultra-low-loss |
| Detector dark counts | Noise floor limits signal-to-noise ratio |
| Chromatic dispersion | Timing uncertainty affects protocols |
| Polarization drift | Requires active compensation |
| Background light | In WDM scenarios, requires filtering |

Each 15 km roughly halves photon transmission probability. The TF-QKD record of 1,002 km (USTC, 2023) used ultra-low-loss fiber at 0.16 dB/km — but at 0.0034 bps, far too low for operational use.

## 2. Infrastructure Requirements

### Optical Path Requirements

| Requirement | DV-QKD | CV-QKD |
|-------------|--------|--------|
| Fiber type | Single-mode, low-loss | Single-mode, low-loss |
| Dark fiber preferred | Yes (but DWDM co-existence now proven) | Yes (but CWDM co-existence proven at 120 km) |
| WDM compatibility | Toshiba: 33.4 Tbps co-existence | LuxQuanta: fully populated CWDM |
| Fiber quality | High (low PMD, low loss) | High |
| Splice quality | Low loss, low reflectance | Low loss, low reflectance |

**DWDM co-existence is no longer a fundamental barrier.** Toshiba demonstrated 33.4 Tbps classical + QKD co-existence over 80 km (March 2025). LuxQuanta demonstrated CV-QKD over 120 km with fully populated CWDM. This eliminates the dark fiber cost barrier for many metro deployments.

### Endpoint Equipment

**DV-QKD Systems (Toshiba, IDQ/IonQ, QuantumCTek, Q*Bird):**
- Single-photon detectors (SPADs or SNSPDs)
- Precise timing electronics
- Temperature stabilization
- Polarization control
- Single-photon sources or attenuated laser with decoy states

**CV-QKD Systems (LuxQuanta):**
- Coherent detection (homodyne/heterodyne) — standard telecom components
- Low-noise receivers
- Local oscillator management
- High-bandwidth electronics
- Phase and polarization tracking
- **No single-photon detectors, no cryogenics** — significant operational advantage

### Environmental Requirements

| Factor | Specification |
|--------|---------------|
| Temperature | Typically 18-25°C, stable within +/-2°C |
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

**Critical:** Trusted nodes see key material during relay. This is the model used by China's QuantumCTek backbone. Physical and personnel security at these nodes is paramount.

**Alternative:** MDI-QKD (Q*Bird Falqon) reduces trust requirements at relay nodes by design — the relay performs measurements but gains no key information.

## 4. Side-Channel and Implementation Attacks

The gap between theoretical QKD security proofs and real-world implementations is the most frequently cited criticism of QKD.

### Major Attack Classes

| Attack | Description | Mitigation | Status |
|--------|-------------|------------|--------|
| Photon-Number Splitting (PNS) | Exploits multi-photon emissions | Decoy-state protocols (standard in all commercial DV-QKD) | Mitigated |
| Detector Blinding | Forces SPDs into classical mode | Monitoring, random activation, **MDI-QKD eliminates entirely** | Active concern for DV-QKD |
| Trojan Horse | Injects light to probe internal states | Optical isolation, monitoring | Active concern |
| Calibration Attacks | Exploits calibration procedures | Secure calibration protocols | Active concern |
| Timing Side Channels | Variations in response times leak info | Constant-time implementations | Active concern |

### Protocol-Level Mitigations

| Protocol | Attacks Mitigated |
|----------|-------------------|
| Decoy-state BB84 | PNS attacks |
| MDI-QKD (Q*Bird) | All detector-side attacks |
| CV-QKD (LuxQuanta) | Detector blinding (no SPDs) |
| Device-independent QKD | All device attacks (research-only, very low rates) |

### Certification Gap

No FIPS 140-3 equivalent exists for QKD devices. ETSI GS QKD 016 provides a security evaluation framework but adoption is minimal. Buyers cannot independently verify that a QKD system's implementation matches its theoretical security claims.

## 5. Key Rate and Consumption

### Key Rate vs Distance (Illustrative)

```
Key Rate (bps)
    |
10M + ####
    | #####
 1M + ######
    | #######
100k+ ########
    | #########
 10k+ ##########
    | ###########
  1k+ ############
    | #############
 100+ ##############
    | ###############
  10+ ################
    +─────────────────────────────
      10   30   50   70   90  110 km

Note: Actual rates vary significantly by system and vendor.
```

### Key Consumption Planning

| Application | Key Size | Rotation | Keys/Hour | Bits/Second |
|-------------|----------|----------|-----------|-------------|
| AES-256 session key | 256 bits | 10 min | 6 | 0.43 bps |
| TLS PSK | 256 bits | Per session | Variable | Depends on connection rate |
| IPsec IKE PPK | 256 bits | 1 hour | 1 | 0.07 bps |
| Link encryption (continuous) | 256 bits | 1 second | 3,600 | 256 bps |
| One-time pad | = message size | Per message | Impractical | Requires key rate = data rate |

**Rule of thumb:** For 100 concurrent TLS sessions rekeying every 10 minutes, consumption is 100 x 256 / 600 = 42.7 bps — easily met by metro QKD systems producing kbps-Mbps.

## 6. Failure Modes and Redundancy

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

**Hybrid Fallback (RECOMMENDED):**
```
QKD Available? ──Yes──► Use QKD key (information-theoretic security)
      │
      No
      │
      ▼
PQC Available? ──Yes──► Use PQC key exchange (computational quantum resistance)
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
| Failed | Low | Execute failover to PQC |
| Failed | Empty | PQC fallback or fail-closed |

## 7. Cost Considerations

### Capital Expenditure

| Item | Range | Notes |
|------|-------|-------|
| QKD endpoint pair (DV-QKD) | $100K - $500K+ | Vendor and feature dependent |
| QKD endpoint pair (CV-QKD) | Expected lower | No SPDs/cryogenics (LuxQuanta) |
| SNSPD detector system | $100K - $300K | Includes cryocooler (DV-QKD only) |
| Dark fiber (lease) | $1K - $10K/km/year | Eliminated if DWDM co-existence used |
| Integration engineering | $50K - $200K+ | Complexity dependent |
| Secure facility | Variable | May leverage existing |

### Operational Expenditure

| Item | Range | Notes |
|------|-------|-------|
| Fiber maintenance | $5K - $20K/year | Per link |
| Equipment maintenance | 10-20% of CapEx/year | Support contracts |
| Operations staff | Variable | Requires quantum-literate operators (rare skill) |
| Power and cooling | $5K - $15K/year | Per node; lower for CV-QKD (no cryogenics) |

### Cost Comparison: QKD vs PQC

| Metric | QKD (per link) | PQC (enterprise-wide) |
|--------|----------------|----------------------|
| Initial cost | $300K - $1M+ | $50K - $500K |
| Ongoing cost | $50K - $200K/year | Minimal (software) |
| Infrastructure | Fiber, QKD hardware, KME | Software update to existing systems |
| Scalability | Per-link (expensive) | Internet-scale (cheap) |

QKD is justified at a 10-100x cost premium only when information-theoretic security is required: government/defense strategic comms, financial interbank settlement, critical infrastructure with long-life confidentiality.

### Market Trajectory

QKD market projected to grow from $0.48B (2024) to $2.63B by 2030 (CAGR 32.6%). CV-QKD and photonic integrated circuits offer the most promising cost reduction path.

## 8. Monitoring and Operations

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

## 9. Standardization Gaps

### What Exists

| Standard | Status | Coverage |
|----------|--------|----------|
| ETSI GS QKD 004 | Published | Application interface |
| ETSI GS QKD 008 | Published | Quality of service |
| ETSI GS QKD 014 | Published | REST key delivery API |
| ETSI GS QKD 015 | Published | Security proofs |
| ETSI GS QKD 016 | Published | Security evaluation methodology |
| ITU-T Y.3800 series | Published | QKD network architecture |
| NIST FIPS 203/204/205 | Published (Aug 2024) | PQC standards (for hybrid) |
| ETSI TS 104 015 | Published (Feb 2025) | Hybrid key exchanges |
| IETF RFC 9794 | Published (June 2025) | Hybrid scheme terminology |

### What Is Missing

- **Interoperability testing:** No formal cross-vendor conformance tests
- **Implementation security certification:** No FIPS 140-3 equivalent for QKD devices
- **Key management interoperability:** Vendor differences in lifecycle management
- **Quantum network management:** Routing, topology, fault management standards immature
- **Workforce standards:** No certification for QKD network operators

## References

- [Beijing-Shanghai QKD Backbone](https://www.science.org/doi/10.1126/science.aap9681) - Chen et al. (2017)
- [Micius Satellite QKD](https://www.science.org/doi/10.1126/science.aan3211) - Yin et al. (2017)
- [Intercontinental Satellite QKD](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.120.030501) - Liao et al. (2018)
- [NISTIR on Quantum-Resistant Security](https://csrc.nist.gov/publications/detail/nistir/8413/final)
- [QKD Implementation Security Survey (2025)](https://arxiv.org/html/2508.04669v2)
- [QKD Market Projection](https://www.marketsandmarkets.com/Market-Reports/quantum-key-distribution-qkd-market-80654677.html)
- [ETSI QKD Standards](https://www.etsi.org/technologies/quantum-key-distribution)
