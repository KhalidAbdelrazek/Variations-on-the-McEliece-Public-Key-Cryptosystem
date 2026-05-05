import numpy as np
from gf_arithmetic import matrix_multiply_gf2
from encryption import generate_error_vector

def generate_niederreiter_keys(goppa_code):
    """
    Generate Niederreiter keys. 
    This is the standard way to achieve shortened ciphertexts with Goppa codes.
    The public key is H_pub instead of G_pub.
    """
    from key_generation import generate_invertible_matrix, generate_permutation_matrix
    
    n_k, n = goppa_code.H_bin.shape # H_bin is (n-k) x n
    
    S_H = generate_invertible_matrix(n_k)
    P = generate_permutation_matrix(n)
    
    # H_pub = S_H * H_bin * P
    SH = matrix_multiply_gf2(S_H, goppa_code.H_bin)
    H_pub = matrix_multiply_gf2(SH, P)
    
    public_key = {
        'H_pub': H_pub,
        't': goppa_code.t
    }
    
    private_key = {
        'S_H': S_H,
        'H_bin': goppa_code.H_bin,
        'P': P,
        'goppa_code': goppa_code
    }
    
    return public_key, private_key

def encrypt_shortened(public_key):
    """
    Niederreiter encryption. The message is actually the error vector e of weight t.
    Ciphertext is the syndrome s = H_pub * e^T.
    Ciphertext length is n-k instead of n.
    """
    H_pub = public_key['H_pub']
    t = public_key['t']
    n = H_pub.shape[1]
    
    # In Niederreiter, the message is mapped to a weight t error vector.
    # For educational purposes, we just generate a random message/error vector.
    message_e = generate_error_vector(n, t)
    
    # s = H_pub * e^T
    ciphertext = matrix_multiply_gf2(H_pub, message_e.reshape(-1, 1)).flatten()
    
    return ciphertext, message_e

def decrypt_shortened(ciphertext, private_key):
    """
    Niederreiter decryption.
    """
    S_H = private_key['S_H']
    P = private_key['P']
    goppa_code = private_key['goppa_code']
    
    # 1. Compute s' = S_H^-1 * s
    from gf_arithmetic import invert_matrix_gf2
    S_H_inv = invert_matrix_gf2(S_H)
    s_prime = matrix_multiply_gf2(S_H_inv, ciphertext.reshape(-1, 1)).flatten()
    
    # 2. Find e' such that H_bin * e'^T = s'
    # This is exactly what the Goppa decoder does given a syndrome!
    # Wait, our Goppa decoder expects a received vector r to compute its syndrome.
    # We can create a dummy received vector r such that H_bin * r^T = s'
    # Since H_bin is in systematic form (or we can make it so), we can easily find one.
    # Or we can just modify the decoder to accept a syndrome directly.
    # To keep things simple without rewriting the decoder, let's find a dummy r.
    
    # H_bin * r^T = s'
    # Since H_bin has rank n-k, we can solve for a basic solution.
    n_k, n = goppa_code.H_bin.shape
    
    # Find a submatrix of H_bin that is invertible to get a particular solution
    # Actually, we can use numpy's lstsq over GF2, but it's simpler:
    # Just find n-k independent columns in H_bin
    cols = []
    for i in range(n):
        cols.append(i)
        if np.linalg.matrix_rank(goppa_code.H_bin[:, cols]) == len(cols):
            if len(cols) == n_k:
                break
        else:
            cols.pop()
            
    H_sub = goppa_code.H_bin[:, cols]
    H_sub_inv = invert_matrix_gf2(H_sub)
    r_sub = matrix_multiply_gf2(H_sub_inv, s_prime.reshape(-1, 1)).flatten()
    
    dummy_r = np.zeros(n, dtype=int)
    dummy_r[cols] = r_sub
    
    # Now decode dummy_r
    corrected_r = goppa_code.decode(dummy_r)
    
    # e' = dummy_r + corrected_r
    e_prime = (dummy_r + corrected_r) % 2
    
    # 3. e = e' * P^-1 (which is P^T because e is a row vector here)
    P_inv = P.T
    message_e = matrix_multiply_gf2(e_prime.reshape(1, -1), P_inv).flatten()
    
    return message_e
