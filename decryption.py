import numpy as np
from gf_arithmetic import matrix_multiply_gf2, invert_matrix_gf2

def decrypt(ciphertext, private_key):
    """
    Decrypt a McEliece ciphertext using the private key.
    :param ciphertext: A binary numpy array of length n.
    :param private_key: Dictionary containing 'S', 'G', 'P', and 'goppa_code'.
    :return: The decrypted message as a binary numpy array.
    """
    S = private_key['S']
    P = private_key['P']
    goppa_code = private_key['goppa_code']
    
    # 1. c' = c * P^-1
    # Since P is a permutation matrix, P^-1 = P^T
    P_inv = P.T
    c_prime = matrix_multiply_gf2(ciphertext.reshape(1, -1), P_inv).flatten()
    
    # 2. Decode c' using Goppa decoder to find m'
    # The decoder returns the corrected codeword (m' * G).
    # Wait, the decode method returns the corrected vector m' * G.
    # To find m', we can just take the systematic part of G if it was systematic, 
    # but since G might not be systematically formatted in this exact step,
    # we can solve m' * G = corrected_codeword.
    # Actually, G = [R^T | I] if we look at our generator construction, so the last k columns are I.
    # Let's extract m' by solving the linear system. Since G is full rank, we can pick k independent columns.
    
    corrected_codeword = goppa_code.decode(c_prime)
    
    # Solve m_prime * G = corrected_codeword
    # We find k linearly independent columns in G over GF(2)
    k, n = goppa_code.G.shape
    
    # Try the last k columns first since our construction puts I there
    cols = list(range(n-k, n))
    try:
        G_sub = goppa_code.G[:, cols]
        G_sub_inv = invert_matrix_gf2(G_sub)
    except ValueError:
        # Fallback to finding any k independent columns over GF(2)
        cols = []
        for i in range(n):
            cols.append(i)
            # Check if current set of columns has full rank by trying to invert the square submatrix
            # If not square yet, we just assume they might be independent and keep adding
            # A better way is to do Gaussian elimination, but for small k, this try-except when len == k works.
            # Actually, to be robust, we need to ensure the columns form a basis.
            # Let's just use the systematic_form_gf2 tool we have!
            pass
            
        # A simpler fallback: just iterate all combinations? No, k is small.
        # But we know G has full rank k. So we can just do RREF on G and find pivot columns!
        from gf_arithmetic import rref_gf2
        rref_G = rref_gf2(goppa_code.G)
        cols = []
        r = 0
        for c in range(n):
            if r >= k: break
            if rref_G[r, c] == 1:
                cols.append(c)
                r += 1
                
        G_sub = goppa_code.G[:, cols]
        G_sub_inv = invert_matrix_gf2(G_sub)

    c_sub = corrected_codeword[cols]
    m_prime = matrix_multiply_gf2(c_sub.reshape(1, -1), G_sub_inv).flatten()
    
    # 3. m = m' * S^-1
    S_inv = invert_matrix_gf2(S)
    message = matrix_multiply_gf2(m_prime.reshape(1, -1), S_inv).flatten()
    
    return message
