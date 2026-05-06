"""
McEliece Cryptosystem Web API
Flask backend — wraps existing crypto modules without modifying them.
Run with: python app.py
"""

import sys
import os
import json
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ─── Make sure the crypto modules are importable ────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from gf_arithmetic import GF2m
from goppa_code import GoppaCode
from key_generation import generate_keys
from encryption import encrypt
from decryption import decrypt
from semantic_security import cca2_encrypt, cca2_decrypt
from isd_attack import isd_attack
# from shortened_ciphertext import (
#     generate_niederreiter_keys,
#     encrypt_shortened,
#     decrypt_shortened,
# )

# ─── App setup ───────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

# ─── In-memory session state (single-user demo) ──────────────────────────────
state = {
    "gf": None,
    "goppa": None,
    "public_key": None,
    "private_key": None,
    # Last encrypt results (needed by ISD endpoint)
    "last_ciphertext": None,
    "last_message": None,
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def to_list(obj):
    """Recursively convert numpy arrays to plain Python lists."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: to_list(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_list(i) for i in obj]
    return obj


def ok(data: dict):
    return jsonify({"success": True, **data})


def err(message: str, code: int = 400):
    return jsonify({"success": False, "error": message}), code


# ─── Serve SPA ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ─── /api/init ───────────────────────────────────────────────────────────────

@app.route("/api/init", methods=["POST"])
def api_init():
    """Initialize the Galois Field and Goppa code."""
    body = request.get_json(force=True)
    try:
        m = int(body.get("m", 4))
        prim_poly = int(body.get("prim_poly", 19))
        t = int(body.get("t", 2))
        n = int(body.get("n", 15))
    except (TypeError, ValueError) as e:
        return err(f"Invalid parameters: {e}")

    try:
        gf = GF2m(m, prim_poly)
        goppa = GoppaCode(n, m, t, gf)
        k, n_actual = goppa.G.shape

        # Reset downstream state when re-initializing
        state.update({
            "gf": gf,
            "goppa": goppa,
            "public_key": None,
            "private_key": None,
            "last_ciphertext": None,
            "last_message": None,
        })

        return ok({
            "message": f"GF(2^{m}) and Goppa code initialized successfully.",
            "details": {
                "field": f"GF(2^{m})",
                "primitive_polynomial": prim_poly,
                "t": t,
                "n": n_actual,
                "k": k,
                "generator_matrix_shape": [k, n_actual],
                "parity_check_shape": list(goppa.H_bin.shape),
            },
        })
    except Exception as e:
        return err(str(e))


# ─── /api/generate-keys ──────────────────────────────────────────────────────

@app.route("/api/generate-keys", methods=["POST"])
def api_generate_keys():
    if state["goppa"] is None:
        return err("System not initialized. Call /api/init first.")
    try:
        pub, priv = generate_keys(state["goppa"])
        state["public_key"] = pub
        state["private_key"] = priv
        # Reset downstream
        state["last_ciphertext"] = None
        state["last_message"] = None

        k, n = pub["G_pub"].shape
        return ok({
            "message": "Key pair generated successfully.",
            "details": {
                "public_key_shape": [k, n],
                "t": pub["t"],
                "private_key_components": ["S (scrambler)", "G (generator)", "P (permutation)", "goppa_code"],
            },
        })
    except Exception as e:
        return err(str(e))


# ─── /api/encrypt ─────────────────────────────────────────────────────────────

@app.route("/api/encrypt", methods=["POST"])
def api_encrypt():
    if state["public_key"] is None:
        return err("Keys not generated. Call /api/generate-keys first.")

    body = request.get_json(force=True)
    pub = state["public_key"]
    k = pub["G_pub"].shape[0]

    # Accept explicit message or auto-generate
    msg_input = body.get("message")
    if msg_input is None or msg_input == "":
        import random
        message = np.array([random.randint(0, 1) for _ in range(k)], dtype=int)
        auto_generated = True
    else:
        try:
            bits = [int(b) for b in str(msg_input).replace(" ", "")]
            if any(b not in (0, 1) for b in bits):
                return err("Message must be a binary string (e.g. 1011010).")
            if len(bits) != k:
                return err(f"Message must have exactly k={k} bits for this key.")
            message = np.array(bits, dtype=int)
            auto_generated = False
        except ValueError as e:
            return err(str(e))

    try:
        ciphertext, error_vec = encrypt(message, pub)
        state["last_ciphertext"] = ciphertext
        state["last_message"] = message

        return ok({
            "message": "Encryption successful.",
            "auto_generated": auto_generated,
            "details": {
                "original_message": to_list(message),
                "original_message_str": "".join(str(b) for b in message.tolist()),
                "error_vector": to_list(error_vec),
                "error_weight": int(np.sum(error_vec)),
                "ciphertext": to_list(ciphertext),
                "ciphertext_str": "".join(str(b) for b in ciphertext.tolist()),
                "ciphertext_length": len(ciphertext),
            },
        })
    except Exception as e:
        return err(str(e))


# ─── /api/decrypt ─────────────────────────────────────────────────────────────

@app.route("/api/decrypt", methods=["POST"])
def api_decrypt():
    if state["private_key"] is None:
        return err("Keys not generated. Call /api/generate-keys first.")
    if state["last_ciphertext"] is None:
        return err("No ciphertext available. Call /api/encrypt first.")

    try:
        ciphertext = state["last_ciphertext"]
        original_message = state["last_message"]
        decrypted = decrypt(ciphertext, state["private_key"])

        success = bool(np.array_equal(original_message, decrypted)) if original_message is not None else None

        return ok({
            "message": "Decryption successful.",
            "details": {
                "decrypted_message": to_list(decrypted),
                "decrypted_message_str": "".join(str(b) for b in decrypted.tolist()),
                "original_message": to_list(original_message) if original_message is not None else None,
                "decryption_match": success,
            },
        })
    except Exception as e:
        return err(str(e))


# ─── /api/cca2 ───────────────────────────────────────────────────────────────

@app.route("/api/cca2", methods=["POST"])
def api_cca2():
    if state["public_key"] is None or state["private_key"] is None:
        return err("Keys not generated. Call /api/generate-keys first.")

    body = request.get_json(force=True)
    msg_input = body.get("message")

    try:
        if msg_input is None or msg_input == "":
            import random
            msg_len = int(body.get("length", 10))
            cca2_msg = np.array([random.randint(0, 1) for _ in range(msg_len)], dtype=int)
            auto_generated = True
        else:
            bits = [int(b) for b in str(msg_input).replace(" ", "")]
            if any(b not in (0, 1) for b in bits):
                return err("Message must be a binary string.")
            cca2_msg = np.array(bits, dtype=int)
            auto_generated = False

        ciphertext_dict = cca2_encrypt(cca2_msg, state["public_key"])
        decrypted = cca2_decrypt(ciphertext_dict, state["private_key"])
        verified = bool(np.array_equal(cca2_msg, decrypted))

        return ok({
            "message": "CCA2 encrypt/decrypt completed.",
            "auto_generated": auto_generated,
            "details": {
                "original_message": to_list(cca2_msg),
                "original_message_str": "".join(str(b) for b in cca2_msg.tolist()),
                "c1": to_list(ciphertext_dict["c1"]),
                "c1_str": "".join(str(b) for b in ciphertext_dict["c1"].tolist()),
                "c2": to_list(ciphertext_dict["c2"]),
                "c2_str": "".join(str(b) for b in ciphertext_dict["c2"].tolist()),
                "decrypted_message": to_list(decrypted),
                "decrypted_message_str": "".join(str(b) for b in decrypted.tolist()),
                "verification": "PASSED ✓" if verified else "FAILED ✗",
                "verified": verified,
            },
        })
    except Exception as e:
        return err(str(e))


# # ─── /api/niederreiter ───────────────────────────────────────────────────────

# @app.route("/api/niederreiter", methods=["POST"])
# def api_niederreiter():
#     if state["goppa"] is None:
#         return err("System not initialized. Call /api/init first.")

#     try:
#         nied_pub, nied_priv = generate_niederreiter_keys(state["goppa"])
#         nied_c, nied_e = encrypt_shortened(nied_pub)
#         nied_dec_e = decrypt_shortened(nied_c, nied_priv)
#         success = bool(np.array_equal(nied_e, nied_dec_e))

#         return ok({
#             "message": "Niederreiter variant completed.",
#             "details": {
#                 "h_pub_shape": list(nied_pub["H_pub"].shape),
#                 "syndrome_length": len(nied_c),
#                 "syndrome": to_list(nied_c),
#                 "syndrome_str": "".join(str(b) for b in nied_c.tolist()),
#                 "original_error_vector": to_list(nied_e),
#                 "original_error_str": "".join(str(b) for b in nied_e.tolist()),
#                 "decrypted_error_vector": to_list(nied_dec_e),
#                 "decrypted_error_str": "".join(str(b) for b in nied_dec_e.tolist()),
#                 "decryption_match": success,
#                 "result": "SUCCESS ✓" if success else "FAILED ✗",
#             },
#         })
#     except Exception as e:
#         return err(str(e))


# ─── /api/isd ────────────────────────────────────────────────────────────────

@app.route("/api/isd", methods=["POST"])
def api_isd():
    if state["public_key"] is None:
        return err("Keys not generated. Call /api/generate-keys first.")
    if state["last_ciphertext"] is None:
        return err("No ciphertext to attack. Call /api/encrypt first.")

    body = request.get_json(force=True)
    max_iter = int(body.get("max_iterations", 5000))

    try:
        ciphertext = state["last_ciphertext"]
        original_message = state["last_message"]

        m_recovered, e_recovered = isd_attack(ciphertext, state["public_key"], max_iterations=max_iter)

        if m_recovered is not None:
            match = bool(np.array_equal(original_message, m_recovered)) if original_message is not None else None
            return ok({
                "message": "ISD Attack succeeded!",
                "details": {
                    "status": "SUCCESS",
                    "recovered_message": to_list(m_recovered),
                    "recovered_message_str": "".join(str(b) for b in m_recovered.tolist()),
                    "recovered_error_vector": to_list(e_recovered),
                    "matches_original": match,
                    "max_iterations": max_iter,
                },
            })
        else:
            return ok({
                "message": f"ISD Attack failed after {max_iter} iterations.",
                "details": {
                    "status": "FAILED",
                    "recovered_message": None,
                    "max_iterations": max_iter,
                },
            })
    except Exception as e:
        return err(str(e))


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  McEliece Cryptosystem Web UI")
    print("  Open http://localhost:5000 in your browser")
    print("=" * 55)
    app.run(debug=True, port=5000, threaded=False)
