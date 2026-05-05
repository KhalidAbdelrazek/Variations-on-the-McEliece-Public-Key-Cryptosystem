import numpy as np
import random
from gf_arithmetic import rref_gf2, matrix_multiply_gf2

class GoppaCode:
    def __init__(self, n, m, t, gf):
        self.n = n
        self.m = m
        self.t = t
        self.gf = gf
        self.g = self._generate_irreducible_poly()
        self.L = self._generate_support()
        
        # Parity Check Matrix H
        self.H_gf = self._generate_H_gf()
        self.H_bin = self._convert_H_to_bin(self.H_gf)
        
        # Generator Matrix G
        self.G, self.P_cols = self._generate_G_from_H(self.H_bin)
        # Reorder support based on column permutation during G generation
        self.L = [self.L[i] for i in self.P_cols]

    def _poly_pow_mod(self, base, exp, mod_poly):
        res = [1]
        base = self.gf.poly_mod(base, mod_poly)
        while exp > 0:
            if exp % 2 == 1:
                res = self.gf.poly_mod(self.gf.poly_mul(res, base), mod_poly)
            base = self.gf.poly_mod(self.gf.poly_mul(base, base), mod_poly)
            exp //= 2
        return res

    def _is_irreducible(self, poly):
        # Ben-Or's Irreducibility Test for GF(2^m)
        x = [0, 1]
        u = x
        for i in range(1, self.t // 2 + 1):
            u = self._poly_pow_mod(u, 1 << self.m, poly)
            u_minus_x = self.gf.poly_add(u, x)
            gcd, _, _ = self.gf.poly_ext_gcd(poly, u_minus_x)
            if len(gcd) > 1: # GCD is not a constant
                return False
        
        u = x
        for _ in range(self.t):
            u = self._poly_pow_mod(u, 1 << self.m, poly)
        
        # Must have x^(2^(mt)) = x mod poly
        if len(u) != 2 or u[0] != 0 or u[1] != 1:
            return False
            
        return True

    def _generate_irreducible_poly(self):
        while True:
            # Generate random monic polynomial of degree t
            poly = [random.randint(0, self.gf.size - 1) for _ in range(self.t)] + [1]
            if self._is_irreducible(poly):
                return poly

    def _generate_support(self):
        # All elements of GF(2^m) that are not roots of g(x)
        L = []
        for i in range(self.gf.size):
            if self.gf.poly_eval(self.g, i) != 0:
                L.append(i)
        if len(L) < self.n:
            raise ValueError(f"Cannot find enough support elements. Needed {self.n}, found {len(L)}.")
        return random.sample(L, self.n)

    def _generate_H_gf(self):
        H = []
        for i in range(self.t):
            row = []
            for alpha in self.L:
                num = self.gf.power(alpha, i)
                den = self.gf.poly_eval(self.g, alpha)
                row.append(self.gf.div(num, den))
            H.append(row)
        return H

    def _convert_H_to_bin(self, H_gf):
        H_bin = []
        for row in H_gf:
            for b in range(self.m):
                bin_row = []
                for val in row:
                    bin_row.append((val >> b) & 1)
                H_bin.append(bin_row)
        return np.array(H_bin, dtype=int)

    def _generate_G_from_H(self, H_bin):
        # We need G such that H_bin * G^T = 0
        # Bring H_bin to systematic form [I | R] by column permutations
        rows, cols = H_bin.shape
        M = np.copy(H_bin)
        P_cols = list(range(cols))
        
        r = 0
        for c in range(cols):
            if r >= rows:
                break
            pivot_c = c
            while pivot_c < cols and M[r, pivot_c] == 0:
                pivot_c += 1
            if pivot_c == cols:
                # Column swap if we didn't find a pivot in this row
                # We need to find a 1 in a lower row, but wait, it's easier to just do full pivoting
                pivot_r = r
                pivot_c = c
                found = False
                for pr in range(r, rows):
                    for pc in range(c, cols):
                        if M[pr, pc] == 1:
                            pivot_r, pivot_c = pr, pc
                            found = True
                            break
                    if found: break
                if not found:
                    break
                
                # Swap rows r and pivot_r
                M[[r, pivot_r]] = M[[pivot_r, r]]
            
            # Swap columns c and pivot_c
            if c != pivot_c:
                M[:, [c, pivot_c]] = M[:, [pivot_c, c]]
                P_cols[c], P_cols[pivot_c] = P_cols[pivot_c], P_cols[c]
            
            # Eliminate
            for i in range(rows):
                if i != r and M[i, c] == 1:
                    M[i] = (M[i] + M[r]) % 2
            r += 1
            
        # M is now [I | R] (if full rank)
        rank = r
        I = M[:rank, :rank]
        R = M[:rank, rank:]
        
        # G = [R^T | I]
        k = cols - rank
        G = np.hstack((R.T, np.eye(k, dtype=int)))
        return G, P_cols

    def decode(self, received_vector):
        """
        Patterson's Algorithm for Goppa Decoding.
        """
        # 1. Calculate Syndrome S(x)
        # S(x) = sum( c_i / (x - alpha_i) ) mod g(x)
        S = []
        for i, c_i in enumerate(received_vector):
            if c_i == 1:
                alpha = self.L[i]
                # 1 / (x - alpha) mod g(x) -> inverse of (x - alpha) mod g(x)
                poly_to_inv = [self.gf.add(0, alpha), 1] # alpha + x
                try:
                    inv_poly = self.gf.poly_inv_mod(poly_to_inv, self.g)
                    S = self.gf.poly_add(S, inv_poly)
                except ValueError:
                    # Rare case: x - alpha is not invertible, which means alpha is a root of g(x).
                    # But we chose support L to not be roots of g(x).
                    pass
                    
        S = self.gf.poly_mod(S, self.g)
        
        if len(S) == 0:
            return received_vector # No errors detected
            
        # 2. Compute T(x) = S(x)^{-1} + x mod g(x)
        try:
            S_inv = self.gf.poly_inv_mod(S, self.g)
        except ValueError:
            return received_vector # Decoding failure
            
        T = self.gf.poly_add(S_inv, [0, 1]) # Add x
        T = self.gf.poly_mod(T, self.g)
        
        # 3. Compute R(x) = sqrt(T(x)) mod g(x)
        # In GF(2^(mt)), sqrt(T) = T^(2^(mt-1)) mod g(x)
        power = 1 << (self.m * self.t - 1)
        R = self._poly_pow_mod(T, power, self.g)
        
        # 4. Extended Euclidean Algorithm on g(x) and R(x)
        # We need a(x) R(x) + b(x) = c(x) g(x) with deg(a) <= floor(t/2)
        old_r, r_poly = self.g[:], R[:]
        old_a, a = [0], [1]
        
        while len(r_poly) > 0 and (len(r_poly) - 1) > self.t // 2:
            quotient, remainder = self.gf.poly_div(old_r, r_poly)
            old_r, r_poly = r_poly, remainder
            
            qa = self.gf.poly_mul(quotient, a)
            new_a = self.gf.poly_add(old_a, qa)
            old_a, a = a, new_a
            
        a_poly = a
        b_poly = r_poly
        
        # 5. Error locator polynomial sigma(x) = a(x)^2 * x + b(x)^2
        a_sq = self.gf.poly_mul(a_poly, a_poly)
        b_sq = self.gf.poly_mul(b_poly, b_poly)
        
        a_sq_x = [0] + a_sq # Multiply by x
        sigma = self.gf.poly_add(a_sq_x, b_sq)
        
        # 6. Find roots of sigma(x) in L
        error_vector = np.zeros(self.n, dtype=int)
        for i, alpha in enumerate(self.L):
            if self.gf.poly_eval(sigma, alpha) == 0:
                error_vector[i] = 1
                
        corrected_vector = (received_vector + error_vector) % 2
        return corrected_vector
