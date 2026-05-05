import numpy as np
from gf_arithmetic import invert_matrix_gf2, matrix_multiply_gf2

def systematic_form_gf2(M):
    """
    Converts a k x n binary matrix M into systematic form [I | R] over GF(2).
    Returns (M_sys, U, P_cols) such that U * M * P_cols = M_sys.
    """
    k, n = M.shape
    M_sys = np.copy(M)
    U = np.eye(k, dtype=int)
    P_cols = np.eye(n, dtype=int)
    
    for r in range(k):
        # 1. Find pivot (search columns first to prioritize earlier columns)
        pivot_r, pivot_c = -1, -1
        for j in range(r, n):
            for i in range(r, k):
                if M_sys[i, j] == 1:
                    pivot_r, pivot_c = i, j
                    break
            if pivot_r != -1:
                break
                
        if pivot_r == -1:
            raise ValueError("Matrix is not full rank.")
            
        # 2. Swap rows if necessary
        if pivot_r != r:
            M_sys[[r, pivot_r]] = M_sys[[pivot_r, r]]
            U[[r, pivot_r]] = U[[pivot_r, r]]
            
        # 3. Swap columns if necessary
        if pivot_c != r:
            M_sys[:, [r, pivot_c]] = M_sys[:, [pivot_c, r]]
            P_cols[:, [r, pivot_c]] = P_cols[:, [pivot_c, r]]
            
        # 4. Eliminate other entries in the current column
        for i in range(k):
            if i != r and M_sys[i, r] == 1:
                M_sys[i] = (M_sys[i] + M_sys[r]) % 2
                U[i] = (U[i] + U[r]) % 2
                
    return M_sys, U, P_cols

def get_systematic_public_key(public_key, private_key):
    """
    Converts the public key G_pub into systematic form [I | R] to reduce its size.
    The private key S matrix is also updated to reflect this change.
    :return: (reduced_public_key, updated_private_key)
    """
    G_pub = public_key['G_pub']
    k, n = G_pub.shape
    
    # Get systematic form G_sys = U * G_pub * P_cols
    G_sys, U, P_cols = systematic_form_gf2(G_pub)
    
    # Verify the first k columns form an identity matrix
    assert np.array_equal(G_sys[:, :k], np.eye(k, dtype=int)), "Failed to convert to systematic form!"
    
    R = G_sys[:, k:]
    
    # Update private key
    # Original G_pub = S * G * P
    # New G_pub = U * original_G_pub * P_cols = (U * S) * G * (P * P_cols)
    new_private_key = private_key.copy()
    new_private_key['S'] = matrix_multiply_gf2(U, private_key['S'])
    new_private_key['P'] = matrix_multiply_gf2(private_key['P'], P_cols)
    new_private_key['G_pub'] = G_sys
    
    new_public_key = public_key.copy()
    new_public_key['G_pub'] = G_sys
    new_public_key['R'] = R # The actual reduced key
    
    return new_public_key, new_private_key
