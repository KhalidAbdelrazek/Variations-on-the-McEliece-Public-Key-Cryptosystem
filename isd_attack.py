import numpy as np
import random
from gf_arithmetic import invert_matrix_gf2, matrix_multiply_gf2

def isd_attack(ciphertext, public_key, max_iterations=10000):
    """
    Perform a basic Information Set Decoding (ISD) attack using Prange's algorithm.
    :param ciphertext: The intercepted ciphertext.
    :param public_key: The public key containing G_pub and t.
    :return: The recovered message and error vector if successful, else None.
    """
    G_pub = public_key['G_pub']
    t = public_key['t']
    k, n = G_pub.shape
    
    for i in range(max_iterations):
        # 1. Randomly select an information set (k columns)
        # We hope these k columns are error-free in the ciphertext.
        info_set = random.sample(range(n), k)
        
        # Extract the submatrix G_info
        G_info = G_pub[:, info_set]
        
        # Check if G_info is invertible
        if np.linalg.matrix_rank(G_info) < k:
            continue # Try another set
            
        # 2. Compute G_info_inv
        try:
            G_info_inv = invert_matrix_gf2(G_info)
        except ValueError:
            continue
            
        # 3. Guess the message: m' = c_info * G_info_inv
        c_info = ciphertext[info_set]
        m_guess = matrix_multiply_gf2(c_info.reshape(1, -1), G_info_inv).flatten()
        
        # 4. Compute the corresponding error vector: e' = c - m' * G_pub
        c_prime = matrix_multiply_gf2(m_guess.reshape(1, -1), G_pub).flatten()
        e_guess = (ciphertext + c_prime) % 2
        
        # 5. Check if the weight of e' is exactly t
        weight = np.sum(e_guess)
        if weight == t:
            print(f"ISD Attack succeeded after {i+1} iterations!")
            return m_guess, e_guess
            
    print(f"ISD Attack failed after {max_iterations} iterations.")
    return None, None
