import numpy as np
from gf_arithmetic import GF2m, matrix_multiply_gf2
from goppa_code import GoppaCode
from key_generation import generate_keys
from reduced_key import systematic_form_gf2

def test():
    m = 4
    prim_poly = 19
    t = 2
    n = 15
    gf = GF2m(m, prim_poly)
    goppa = GoppaCode(n, m, t, gf)
    public_key, private_key = generate_keys(goppa)
    
    G_pub = public_key['G_pub']
    S = private_key['S']
    G = private_key['G']
    P = private_key['P']
    
    # Verify original
    orig_computed = matrix_multiply_gf2(matrix_multiply_gf2(S, G), P)
    print("Orig matches:", np.array_equal(G_pub, orig_computed))
    
    G_sys, U, P_cols = systematic_form_gf2(G_pub)
    
    new_S = matrix_multiply_gf2(U, S)
    new_P = matrix_multiply_gf2(P, P_cols)
    
    new_computed = matrix_multiply_gf2(matrix_multiply_gf2(new_S, G), new_P)
    
    print("New matches G_sys:", np.array_equal(G_sys, new_computed))

test()
