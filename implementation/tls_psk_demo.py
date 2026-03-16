"""
QKD-derived PSK Demo — end-to-end secure channel

Demonstrates the pre-shared key pattern that QKD enables:

  1. Alice (master SAE) calls GET /enc_keys  → receives key_ID + key_bytes
  2. Alice sends key_ID to Bob over a plain channel (key_ID is not secret)
  3. Bob  (slave SAE)  calls POST /dec_keys  → receives the same key_bytes
  4. Both encrypt/decrypt with AES-256-GCM — no Diffie-Hellman involved

This is the PSK pattern used in TLS 1.3 (RFC 8446 §4.2.11):
  - The external_psk_identity maps to key_ID
  - The external_psk maps to key_bytes
  - In production this key feeds the TLS 1.3 pre_shared_key extension,
    replacing the ECDHE key exchange entirely

Usage (requires KME server running in a separate terminal):
  python kme_server.py                  # Terminal 1

  python tls_psk_demo.py server         # Terminal 2 — Bob
  python tls_psk_demo.py client         # Terminal 3 — Alice

Requirements:
  pip install requests cryptography
"""

import os
import struct
import socket
import sys
import base64

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ── Configuration ──────────────────────────────────────────────────────────────

KME_URL       = "http://127.0.0.1:5000"
SLAVE_SAE_ID  = "sae-bob"          # The SAE that will receive/decrypt
SERVER_HOST   = "127.0.0.1"
SERVER_PORT   = 8443
RECV_TIMEOUT  = 10                 # seconds


# ── KME client helpers ─────────────────────────────────────────────────────────

def kme_fetch_enc_key() -> tuple[str, bytes]:
    """
    Alice: request a new 256-bit key from the KME (master SAE role).
    Returns (key_id, key_bytes).
    """
    resp = requests.get(
        f"{KME_URL}/api/v1/keys/{SLAVE_SAE_ID}/enc_keys",
        params={"number": 1, "size": 256},
        timeout=5,
    )
    resp.raise_for_status()
    obj = resp.json()["keys"][0]
    return obj["key_ID"], base64.b64decode(obj["key"])


def kme_fetch_dec_key(key_id: str) -> bytes:
    """
    Bob: retrieve a specific key by key_ID from the KME (slave SAE role).
    Returns key_bytes.
    """
    resp = requests.post(
        f"{KME_URL}/api/v1/keys/{SLAVE_SAE_ID}/dec_keys",
        json={"key_IDs": [{"key_ID": key_id}]},
        timeout=5,
    )
    resp.raise_for_status()
    return base64.b64decode(resp.json()["keys"][0]["key"])


# ── Framing helpers ────────────────────────────────────────────────────────────
# 4-byte big-endian length prefix so we can send variable-length messages.

def send_msg(sock: socket.socket, data: bytes) -> None:
    sock.sendall(struct.pack(">I", len(data)) + data)


def recv_msg(sock: socket.socket) -> bytes:
    header = _recv_exact(sock, 4)
    length = struct.unpack(">I", header)[0]
    return _recv_exact(sock, length)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed unexpectedly")
        buf += chunk
    return bytes(buf)


# ── AES-256-GCM channel ────────────────────────────────────────────────────────

def encrypt(key: bytes, plaintext: bytes) -> bytes:
    """Returns nonce (12 bytes) + ciphertext+tag."""
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext, None)
    return nonce + ct


def decrypt(key: bytes, nonce_ct: bytes) -> bytes:
    """Splits nonce and ciphertext, decrypts and authenticates."""
    nonce, ct = nonce_ct[:12], nonce_ct[12:]
    return AESGCM(key).decrypt(nonce, ct, None)


# ── Server (Bob) ───────────────────────────────────────────────────────────────

def run_server() -> None:
    print("[Bob/Server] Waiting for Alice on", f"{SERVER_HOST}:{SERVER_PORT}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen(1)

    conn, addr = server.accept()
    conn.settimeout(RECV_TIMEOUT)
    print(f"[Bob/Server] Connection from {addr}")

    # Alice sends the key_ID in plaintext — it's a non-secret identifier,
    # analogous to the psk_identity field in TLS 1.3's pre_shared_key extension.
    key_id = recv_msg(conn).decode()
    print(f"[Bob/Server] Received key_ID : {key_id}")

    # Bob retrieves the matching key from his KME using the key_ID
    key = kme_fetch_dec_key(key_id)
    print(f"[Bob/Server] Retrieved key   : {key.hex()[:32]}...  ({len(key)*8} bits)")
    print(f"[Bob/Server] Key matches Alice's? — will verify via authenticated decryption")

    # Receive Alice's encrypted message
    nonce_ct = recv_msg(conn)
    plaintext = decrypt(key, nonce_ct)
    print(f"[Bob/Server] Decrypted message: \"{plaintext.decode()}\"")
    print(f"[Bob/Server] AES-GCM authentication tag verified — key agreement confirmed")

    # Send an encrypted reply
    reply = b"ACK from Bob. QKD-derived PSK established. No DH used."
    send_msg(conn, encrypt(key, reply))
    print(f"[Bob/Server] Sent encrypted reply")

    conn.close()
    server.close()
    print("[Bob/Server] Session complete.")


# ── Client (Alice) ─────────────────────────────────────────────────────────────

def run_client() -> None:
    print("[Alice/Client] Fetching key from KME...")

    # Alice gets a fresh key from the KME
    key_id, key = kme_fetch_enc_key()
    print(f"[Alice/Client] Got key_ID  : {key_id}")
    print(f"[Alice/Client] Got key     : {key.hex()[:32]}...  ({len(key)*8} bits)")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(RECV_TIMEOUT)
    sock.connect((SERVER_HOST, SERVER_PORT))
    print(f"[Alice/Client] Connected to {SERVER_HOST}:{SERVER_PORT}")

    # Send key_ID so Bob knows which key to retrieve from his KME.
    # This is equivalent to the psk_identity in TLS 1.3 ClientHello.
    send_msg(sock, key_id.encode())
    print(f"[Alice/Client] Sent key_ID (PSK identity)")

    # Encrypt a message with the QKD-derived key
    message = b"Hello from Alice. This message is secured with a QKD-derived key."
    send_msg(sock, encrypt(key, message))
    print(f"[Alice/Client] Sent encrypted message")

    # Receive Bob's reply
    nonce_ct = recv_msg(sock)
    reply = decrypt(key, nonce_ct)
    print(f"[Alice/Client] Bob replied: \"{reply.decode()}\"")

    sock.close()
    print("[Alice/Client] Session complete.")
    print()
    print("━" * 60)
    print("Summary: Both sides used the same key, fetched independently")
    print("from the ETSI KME. No Diffie-Hellman or RSA was performed.")
    print("In TLS 1.3, this key_ID/key pair maps directly into the")
    print("pre_shared_key extension (RFC 8446 §4.2.11).")
    print("━" * 60)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("server", "client"):
        print(__doc__)
        print("Usage: python tls_psk_demo.py server | client")
        sys.exit(1)

    if sys.argv[1] == "server":
        run_server()
    else:
        run_client()
