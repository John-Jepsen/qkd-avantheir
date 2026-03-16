# IKEv2 PPK Configuration Guide

Configuring strongSwan to use QKD-derived Post-quantum Preshared Keys (PPK)
per RFC 8784. This guide maps a key dispensed by the ETSI KME server to the
`ppk` parameter in a strongSwan IKEv2 tunnel.

---

## Background

RFC 8784 defines the **PPK** (Post-quantum Preshared Key) extension to IKEv2.
When both peers include `USE_PPK` or `REQUIRE_PPK` in their IKE_SA_INIT
exchange, the session derives an additional key from the PPK material:

```
SK_d_new  = prf+(PPK, SK_d)
SK_pi_new = prf+(PPK, SK_pi)
SK_pr_new = prf+(PPK, SK_pr)
```

A compromised ECDH private key alone cannot break the session — an attacker
would also need the PPK, which was exchanged via the quantum channel and never
transmitted classically.

---

## Step 1 — Fetch a key from the KME

With `kme_server.py` running, retrieve a 256-bit key intended for this IKEv2
tunnel. The script below fetches the key and writes it in the format
strongSwan expects.

```bash
#!/bin/bash
# fetch_ppk.sh — run on both ends; supply the same key_ID to the peer

KME="http://127.0.0.1:5000"
SAE="sae-peer-b"

# Master side (Alice / initiator) — get a new key
RESPONSE=$(curl -sf "${KME}/api/v1/keys/${SAE}/enc_keys?number=1&size=256")
KEY_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['keys'][0]['key_ID'])")
KEY_B64=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['keys'][0]['key'])")
KEY_HEX=$(python3 -c "import base64,sys; print(base64.b64decode('$KEY_B64').hex())")

echo "key_ID : $KEY_ID"
echo "key    : $KEY_HEX"

# Write to a file strongSwan can read
# Format: <ppk_id> : PPK 0x<hex_key>
echo "${KEY_ID} : PPK 0x${KEY_HEX}" >> /etc/swanctl/ppk.secrets
```

Send `KEY_ID` to the peer (e.g. via your management plane). The peer runs the
slave-side fetch:

```bash
# Slave side (Bob / responder) — retrieve matching key by key_ID
curl -sf -X POST "${KME}/api/v1/keys/${SAE}/dec_keys" \
  -H "Content-Type: application/json" \
  -d "{\"key_IDs\":[{\"key_ID\":\"${KEY_ID}\"}]}" \
| python3 -c "
import sys, json, base64
k = json.load(sys.stdin)['keys'][0]
hex_key = base64.b64decode(k['key']).hex()
print(f\"{k['key_ID']} : PPK 0x{hex_key}\")
" >> /etc/swanctl/ppk.secrets
```

---

## Step 2 — strongSwan swanctl configuration

### /etc/swanctl/ppk.secrets

```
# One line per QKD-derived PPK.
# Automatically appended by fetch_ppk.sh above.
# Format: <ppk_id> : PPK 0x<256-bit hex key>

a3f2c1d0-... : PPK 0xdeadbeef0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c
```

### /etc/swanctl/swanctl.conf (initiator, Alice)

```
connections {
  qkd-tunnel {
    version = 2
    proposals = aes256gcm16-prfsha384-ecp384     # ECDHE retained for auth;
                                                  # PPK hardens against future CRQC

    ppk_id   = a3f2c1d0-...   # matches ppk.secrets entry; use current key_ID
    ppk_required = yes         # REQUIRE_PPK — abort unless peer also supports PPK

    local {
      auth = psk
      id   = alice@example.com
    }
    remote {
      auth = psk
      id   = bob@example.com
    }
    children {
      net {
        local_ts  = 10.0.0.0/24
        remote_ts = 10.0.1.0/24
        esp_proposals = aes256gcm16
      }
    }
  }
}

secrets {
  ike-alice {
    id     = alice@example.com
    secret = "shared-ike-auth-psk"   # classical IKE authentication PSK (separate)
  }
}
```

### /etc/swanctl/swanctl.conf (responder, Bob)

Identical structure. The `ppk_id` must match the `key_ID` Alice used.

```
connections {
  qkd-tunnel {
    version = 2
    proposals = aes256gcm16-prfsha384-ecp384

    ppk_id       = a3f2c1d0-...
    ppk_required = yes

    local  { auth = psk; id = bob@example.com   }
    remote { auth = psk; id = alice@example.com }

    children {
      net {
        local_ts  = 10.0.1.0/24
        remote_ts = 10.0.0.0/24
        esp_proposals = aes256gcm16
      }
    }
  }
}

secrets {
  ike-bob {
    id     = bob@example.com
    secret = "shared-ike-auth-psk"
  }
}
```

---

## Step 3 — Load and verify

```bash
# Load the new config and secrets on both hosts
swanctl --load-all

# Initiate the tunnel (Alice)
swanctl --initiate --child net

# Verify the SA includes PPK
swanctl --list-sas | grep -i ppk
# Expected: "IKE_SA qkd-tunnel[1]: ESTABLISHED ... PPK"
```

---

## Key rotation

RFC 8784 recommends rotating PPKs at session re-key intervals. The KME
provides a fresh key on each call to `enc_keys`. Automate rotation by:

1. Fetching a new key pair from the KME before each IKE re-auth window
2. Appending the new entry to `ppk.secrets`
3. Calling `swanctl --load-creds` (hot reload, no tunnel teardown)
4. Updating `ppk_id` in `swanctl.conf` to the new `key_ID`
5. Calling `swanctl --load-conns`

---

## Security notes

| Consideration | Detail |
|---------------|--------|
| PPK confidentiality | The PPK is never transmitted over the network. key_ID is public; key_bytes are not. |
| Classical IKE PSK | Still required for peer authentication — separate from PPK. |
| PPK size | 256 bits (32 bytes) — matches the `prf+` input size for SHA-384 suites. |
| REQUIRE vs USE | `ppk_required = yes` → tunnel fails if peer does not support PPK. Use `ppk_required = no` (`USE_PPK`) for gradual rollout. |
| Key ID management | Automate key_ID exchange via your management plane or a shared configuration database. Do not hard-code IDs in production. |

---

## Reference

- RFC 8784 — *Mixing Preshared Keys in IKEv2 for Post-quantum Security*
- strongSwan PPK documentation: https://docs.strongswan.org/docs/latest/config/ppk.html
- ETSI GS QKD 014: https://www.etsi.org/deliver/etsi_gs/QKD/001_099/014/
