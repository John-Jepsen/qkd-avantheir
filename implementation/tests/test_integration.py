"""
Integration tests: end-to-end QKD key delivery and PSK session.

These tests exercise the full pipeline without external processes:
  BB84 → KME pool → enc_keys → dec_keys → AES-256-GCM encrypt/decrypt

The KME server runs as a Flask test client. The tls_psk_demo KME fetch
functions are patched to call the test client instead of real HTTP, then
Alice and Bob run their socket exchange over a real in-process TCP pair.
"""

import base64
import socket
import threading
import os

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_test_fetchers(kme_client):
    """
    Return (fetch_enc_key, fetch_dec_key) functions that call the Flask
    test client rather than real HTTP, so tests run without a live server.
    """

    def fetch_enc_key() -> tuple[str, bytes]:
        resp = kme_client.get("/api/v1/keys/sae-test/enc_keys")
        assert resp.status_code == 200
        obj = resp.get_json()["keys"][0]
        return obj["key_ID"], base64.b64decode(obj["key"])

    def fetch_dec_key(key_id: str) -> bytes:
        resp = kme_client.post(
            "/api/v1/keys/sae-test/dec_keys",
            json={"key_IDs": [{"key_ID": key_id}]},
        )
        assert resp.status_code == 200
        return base64.b64decode(resp.get_json()["keys"][0]["key"])

    return fetch_enc_key, fetch_dec_key


# ── BB84 → KME pipeline ────────────────────────────────────────────────────────

def test_kme_pool_serves_bb84_keys(kme_client):
    """Keys served by the KME are 32-byte values derived from BB84."""
    resp = kme_client.get("/api/v1/keys/sae-test/enc_keys")
    key  = base64.b64decode(resp.get_json()["keys"][0]["key"])
    assert len(key) == 32
    assert key != b"\x00" * 32   # not zero — real entropy


def test_enc_dec_round_trip(kme_client):
    """enc_keys followed by dec_keys with the same key_ID returns identical bytes."""
    enc  = kme_client.get("/api/v1/keys/sae-test/enc_keys").get_json()
    kid  = enc["keys"][0]["key_ID"]
    orig = enc["keys"][0]["key"]

    dec = kme_client.post(
        "/api/v1/keys/sae-test/dec_keys",
        json={"key_IDs": [{"key_ID": kid}]},
    ).get_json()

    assert dec["keys"][0]["key"] == orig


# ── AES-256-GCM encrypt/decrypt ────────────────────────────────────────────────

def test_aes_gcm_round_trip(kme_client):
    """Messages encrypted with the KME key decrypt correctly."""
    from tls_psk_demo import encrypt, decrypt

    fetch_enc, fetch_dec = make_test_fetchers(kme_client)
    key_id, key_a = fetch_enc()
    key_b         = fetch_dec(key_id)

    assert key_a == key_b   # both sides have the same key

    plaintext  = b"Hello from integration test - QKD-derived AES-256-GCM"
    ciphertext = encrypt(key_a, plaintext)
    recovered  = decrypt(key_b, ciphertext)

    assert recovered == plaintext


def test_wrong_key_fails_decryption(kme_client):
    """Decryption with a different key raises an exception (GCM tag mismatch)."""
    from tls_psk_demo import encrypt, decrypt
    from cryptography.exceptions import InvalidTag

    fetch_enc, _ = make_test_fetchers(kme_client)
    _, key_a  = fetch_enc()
    wrong_key = os.urandom(32)

    ciphertext = encrypt(key_a, b"secret message")

    with pytest.raises(InvalidTag):
        decrypt(wrong_key, ciphertext)


# ── Full Alice ↔ Bob socket session ───────────────────────────────────────────

def test_alice_bob_session():
    """
    Full end-to-end: Alice fetches key from KME, sends key_ID to Bob over TCP,
    Bob fetches the same key, they exchange an encrypted message and reply.

    Alice and Bob run in threads; a real TCP loopback socket connects them.
    Each thread creates its own Flask test client (the client is not thread-safe
    when shared across threads).
    """
    from kme_server import app as kme_app
    from tls_psk_demo import send_msg, recv_msg, encrypt, decrypt, SERVER_HOST

    errors: list[str] = []

    # Pick a free port by binding to :0 and reading the assigned port
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind((SERVER_HOST, 0))
    port = probe.getsockname()[1]
    probe.close()

    def run_bob():
        try:
            kme_app.config["TESTING"] = True
            with kme_app.test_client() as client:
                _, fetch_dec = make_test_fetchers(client)

                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind((SERVER_HOST, port))
                server.listen(1)
                server.settimeout(5)
                conn, _ = server.accept()
                conn.settimeout(5)

                key_id   = recv_msg(conn).decode()
                key      = fetch_dec(key_id)
                nonce_ct = recv_msg(conn)
                plain    = decrypt(key, nonce_ct)
                assert plain == b"Hello from Alice"

                send_msg(conn, encrypt(key, b"ACK from Bob"))
                conn.close()
                server.close()
        except Exception as exc:
            errors.append(f"Bob error: {exc}")

    def run_alice():
        try:
            kme_app.config["TESTING"] = True
            with kme_app.test_client() as client:
                fetch_enc, _ = make_test_fetchers(client)

                key_id, key = fetch_enc()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((SERVER_HOST, port))
                send_msg(sock, key_id.encode())
                send_msg(sock, encrypt(key, b"Hello from Alice"))
                reply_ct = recv_msg(sock)
                reply    = decrypt(key, reply_ct)
                assert reply == b"ACK from Bob"
                sock.close()
        except Exception as exc:
            errors.append(f"Alice error: {exc}")

    bob_thread   = threading.Thread(target=run_bob)
    alice_thread = threading.Thread(target=run_alice)

    bob_thread.start()
    bob_thread.join(timeout=0.2)    # let Bob bind and listen
    alice_thread.start()

    bob_thread.join(timeout=15)
    alice_thread.join(timeout=15)

    assert not errors, "\n".join(errors)
