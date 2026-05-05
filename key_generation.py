import numpy as np
import random
from gf_arithmetic import matrix_multiply_gf2

def generate_invertible_matrix(k):
    """
    Generate a random k x k invertible matrix over GF(2).
    A simple way is to generate random matrices until one has full rank,
    or construct it by multiplying random elementary matrices.
    Here we use a randomized construction.
    """
    S = np.eye(k, dtype=int)
    # Perform random row operations to ensure invertibility
    for _ in range(k * 5):
        r1 = random.randint(0, k - 1)
        r2 = random.randint(0, k - 1)
        if r1 != r2:
            S[r1] = (S[r1] + S[r2]) % 2
            
    # Also do some random column operations or just more row ops
    for _ in range(k * 5):
        c1 = random.randint(0, k - 1)
        c2 = random.randint(0, k - 1)
        if c1 != c2:
            S[:, c1] = (S[:, c1] + S[:, c2]) % 2
            
    return S

def generate_permutation_matrix(n):
    """
    Generate a random n x n permutation matrix.
    """
    P = np.eye(n, dtype=int)
    perm = list(range(n))
    random.shuffle(perm)
    return P[perm]

def generate_keys(goppa_code):
    """
    Generate McEliece Public and Private Keys.
    :param goppa_code: An instance of GoppaCode.
    :return: (public_key, private_key)
    """
    k, n = goppa_code.G.shape
    
    # Generate S and P
    S = generate_invertible_matrix(k)
    P = generate_permutation_matrix(n)
    
    # Calculate G_pub = S * G * P
    # First S * G
    SG = matrix_multiply_gf2(S, goppa_code.G)
    # Then SG * P
    G_pub = matrix_multiply_gf2(SG, P)
    
    public_key = {
        'G_pub': G_pub,
        't': goppa_code.t
    }
    
    private_key = {
        'S': S,
        'G': goppa_code.G,
        'P': P,
        'goppa_code': goppa_code,
        'G_pub': G_pub
    }
    
    return public_key, private_key
