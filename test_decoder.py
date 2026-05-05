import numpy as np
from gf_arithmetic import GF2m, matrix_multiply_gf2
from goppa_code import GoppaCode
from encryption import generate_error_vector

def test_decoder():
    m = 4
    prim_poly = 19
    t = 2
    n = 15
    gf = GF2m(m, prim_poly)
    goppa = GoppaCode(n, m, t, gf)
    
    k = goppa.G.shape[0]
    m_test = np.random.randint(0, 2, k)
    c_pure = matrix_multiply_gf2(m_test.reshape(1, -1), goppa.G).flatten()
    
    e = generate_error_vector(n, t)
    c_err = (c_pure + e) % 2
    
    c_corr = goppa.decode(c_err)
    
    if np.array_equal(c_pure, c_corr):
        print("Decoder WORKS!")
    else:
        print("Decoder FAILED!")
        print("Expected:", c_pure)
        print("Got     :", c_corr)

test_decoder()
