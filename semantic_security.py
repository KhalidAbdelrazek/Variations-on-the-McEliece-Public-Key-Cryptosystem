import hashlib
import numpy as np
import random

from encryption import encrypt
from decryption import decrypt
from gf_arithmetic import matrix_multiply_gf2


# =========================================================
# Helpers
# =========================================================

def hash_to_error_vector(data, n, t):
    """
    Deterministically generates an error vector of length n and weight t
    from SHA-256 hash.
    """
    h = hashlib.sha256(data).digest()

    rng = random.Random(h)

    e = np.zeros(n, dtype=int)
    positions = rng.sample(range(n), t)

    for p in positions:
        e[p] = 1

    return e


def hash_data(data, length):
    """
    Expands SHA-256 hash into a binary vector of given length.
    """
    h = hashlib.sha256(data).digest()

    bits = []
    while len(bits) < length:
        for byte in h:
            for i in range(8):
                bits.append((byte >> (7 - i)) & 1)
                if len(bits) == length:
                    return np.array(bits, dtype=int)
        h = hashlib.sha256(h).digest()

    return np.array(bits[:length], dtype=int)


# CCA2 ENCRYPTION
def cca2_encrypt(message_bits, public_key):
    """
    c1 = r * G_pub + e
    c2 = m XOR Hash(r)
    e  = Hash(r || c2) mapped to weight t
    """

    G_pub = public_key['G_pub']
    n = G_pub.shape[1]
    k = G_pub.shape[0]
    t = public_key['t']

    # 1. random r
    r = np.array([random.randint(0, 1) for _ in range(k)], dtype=int)

    # stable byte conversion
    r_bytes = r.astype(np.uint8).tobytes()

    # 2. c2 = m XOR Hash(r)
    h_r = hash_data(r_bytes, len(message_bits))
    c2 = (message_bits + h_r) % 2

    # 3. e = Hash(r || c2)
    c2_bytes = c2.astype(np.uint8).tobytes()
    r_c2_bytes = r_bytes + c2_bytes

    e = hash_to_error_vector(r_c2_bytes, n, t)

    # 4. c1 = r * G_pub + e
    c_prime = matrix_multiply_gf2(r.reshape(1, -1), G_pub).flatten()
    c1 = (c_prime + e) % 2

    return {'c1': c1, 'c2': c2}


# CCA2 DECRYPTION
def cca2_decrypt(ciphertext, private_key):
    """
    Verify integrity + recover message
    """

    c1 = ciphertext['c1']
    c2 = ciphertext['c2']

    G_pub = private_key['G_pub']
    t = private_key['goppa_code'].t

    # 1. recover r using McEliece decryption
    r = decrypt(c1, private_key)

    # 2. recompute expected error
    r_bytes = r.astype(np.uint8).tobytes()
    c2_bytes = c2.astype(np.uint8).tobytes()
    r_c2_bytes = r_bytes + c2_bytes

    e_expected = hash_to_error_vector(r_c2_bytes, len(c1), t)

    # 3. recompute c1
    c_prime = matrix_multiply_gf2(r.reshape(1, -1), G_pub).flatten()
    c1_expected = (c_prime + e_expected) % 2

    # 4. integrity check
    if not np.array_equal(c1, c1_expected):
        raise ValueError("CCA2 verification failed: ciphertext tampering detected.")

    # 5. recover message
    h_r = hash_data(r_bytes, len(c2))
    m = (c2 + h_r) % 2

    return m
