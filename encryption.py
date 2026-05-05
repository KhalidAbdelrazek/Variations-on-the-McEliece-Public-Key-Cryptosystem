import numpy as np
import random
from gf_arithmetic import matrix_multiply_gf2

def generate_error_vector(n, t):
    """
    Generate a random error vector of length n and weight t.
    """
    e = np.zeros(n, dtype=int)
    error_positions = random.sample(range(n), t)
    for pos in error_positions:
        e[pos] = 1
    return e

def encrypt(message, public_key):
    """
    Encrypt a message using McEliece public key.
    :param message: A binary numpy array of length k.
    :param public_key: Dictionary containing 'G_pub' and 't'.
    :return: ciphertext as a binary numpy array.
    """
    G_pub = public_key['G_pub']
    t = public_key['t']
    n = G_pub.shape[1]
    
    # c_prime = m * G_pub
    c_prime = matrix_multiply_gf2(message.reshape(1, -1), G_pub).flatten()
    
    # Generate error vector e
    e = generate_error_vector(n, t)
    
    # c = c_prime + e
    ciphertext = (c_prime + e) % 2
    
    return ciphertext, e  # Return e as well for demonstration purposes
