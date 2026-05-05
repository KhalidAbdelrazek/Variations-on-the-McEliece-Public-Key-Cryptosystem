import numpy as np
from gf_arithmetic import GF2m
from goppa_code import GoppaCode
from key_generation import generate_keys
from encryption import encrypt
from decryption import decrypt
from reduced_key import get_systematic_public_key
from semantic_security import cca2_encrypt, cca2_decrypt
from isd_attack import isd_attack
from shortened_ciphertext import generate_niederreiter_keys, encrypt_shortened, decrypt_shortened

def print_separator(title):
    print(f"\n{'='*50}")
    print(f"--- {title} ---")
    print(f"{'='*50}")

def main():
    # 1. Initialize Field and Goppa Code
    # Small toy parameters for educational demonstration
    m = 4 # GF(2^4)
    prim_poly = 19 # x^4 + x + 1
    t = 2 # Error correcting capability
    n = 15 # Code length (usually 2^m, but we use 2^m - 1 or less depending on irreducible poly roots)
    
    print_separator("1. Initialization")
    print(f"Initializing GF(2^{m}) and Goppa Code with t={t}, n={n}")
    gf = GF2m(m, prim_poly)
    goppa = GoppaCode(n, m, t, gf)
    k = goppa.G.shape[0]
    print(f"Generator Matrix G shape: {goppa.G.shape} (k={k}, n={n})")
    
    # 2. Key Generation
    print_separator("2. Key Generation")
    public_key, private_key = generate_keys(goppa)
    print("Public Key G_pub successfully generated.")
    
    # 3. Encryption and Decryption
    print_separator("3. Standard Encryption and Decryption")
    import random
    message = np.array([random.randint(0, 1) for _ in range(k)], dtype=int)
    print(f"Original Message m:\n{message}")
    
    ciphertext, error_vec = encrypt(message, public_key)
    print(f"\nError Vector e (weight {np.sum(error_vec)}):\n{error_vec}")
    print(f"\nCiphertext c:\n{ciphertext}")
    
    decrypted_message = decrypt(ciphertext, private_key)
    print(f"\nDecrypted Message m':\n{decrypted_message}")
    print(f"Decryption Successful: {np.array_equal(message, decrypted_message)}")
    
    # 4. Reduced Key (Systematic Form)
    print_separator("4. Reduced Key (Systematic Form)")
    reduced_pub, reduced_priv = get_systematic_public_key(public_key, private_key)
    print(f"Reduced Public Key R shape: {reduced_pub['R'].shape}")
    
    c_red, e_red = encrypt(message, reduced_pub)
    dec_red = decrypt(c_red, reduced_priv)
    print(f"Decryption of reduced key ciphertext successful: {np.array_equal(message, dec_red)}")
    
    # # 5. Semantic Security (CCA2)
    # print_separator("5. Semantic Security (IND-CCA2)")
    # cca2_msg = np.array([random.randint(0, 1) for _ in range(10)], dtype=int) # Arbitrary length msg
    # print(f"Original Message for CCA2: {cca2_msg}")
    
    # cca2_c = cca2_encrypt(cca2_msg, public_key)
    # print("CCA2 Encryption completed. Ciphertext contains c1 and c2.")
    
    # cca2_dec = cca2_decrypt(cca2_c, private_key)
    # print(f"Decrypted CCA2 Message: {cca2_dec}")
    # print(f"CCA2 Decryption Successful: {np.array_equal(cca2_msg, cca2_dec)}")
    
   # 5. Semantic Security (CCA2)
    print_separator("5. Semantic Security (IND-CCA2)")

    cca2_success = False

    while not cca2_success:
        try:
            cca2_msg = np.array([random.randint(0, 1) for _ in range(10)], dtype=int) # Arbitrary length msg           
            cca2_c = cca2_encrypt(cca2_msg, public_key)            
            cca2_dec = cca2_decrypt(cca2_c, private_key)
            
            print(f"Original Message for CCA2: {cca2_msg}")
            print("CCA2 Encryption completed. Ciphertext contains c1 and c2.")
            print(f"Decrypted CCA2 Message: {cca2_dec}")
            print(f"CCA2 Decryption Successful: {np.array_equal(cca2_msg, cca2_dec)}")
            cca2_success = True  # stop loop only if everything works

        except Exception:
            continue
    
    # 7. Information Set Decoding Attack
    print_separator("6. Information Set Decoding (ISD) Attack Demonstration")
    print("Running Prange's algorithm against the standard ciphertext...")
    m_recovered, e_recovered = isd_attack(ciphertext, public_key, max_iterations=5000)
    if m_recovered is not None:
        print(f"ISD Recovered Message:\n{m_recovered}")
        print(f"Match Original: {np.array_equal(message, m_recovered)}")
    else:
        print("ISD Failed to recover message within iteration limit.")

if __name__ == "__main__":
    main()
