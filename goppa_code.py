import numpy as np
import random
from gf_arithmetic import rref_gf2, matrix_multiply_gf2

class GoppaCode:
    def __init__(self, n, m, t, gf):
        # n: code length
        # m: field GF(2^m)
        # t: error-correcting capability
        # gf: finite field arithmetic object

        self.n = n
        self.m = m
        self.t = t
        self.gf = gf

        # Generate irreducible polynomial (defines the field structure)
        self.g = self._generate_irreducible_poly()

        # Support set L: evaluation points in GF(2^m)
        self.L = self._generate_support()

        # -------------------------
        # Parity-check matrix H
        # -------------------------

        # H in GF(2^m) representation
        self.H_gf = self._generate_H_gf()

        # Convert H from GF elements to binary matrix (0/1)
        self.H_bin = self._convert_H_to_bin(self.H_gf)

        # -------------------------
        # Generator matrix G
        # -------------------------

        # Construct generator matrix from H
        self.G, self.P_cols = self._generate_G_from_H(self.H_bin)

        # Reorder support according to column permutations
        self.L = [self.L[i] for i in self.P_cols]

    # -----------------------------------------
    # Polynomial exponentiation with modulus
    # -----------------------------------------
    def _poly_pow_mod(self, base, exp, mod_poly):
        res = [1]  # identity element

        base = self.gf.poly_mod(base, mod_poly)

        while exp > 0:
            if exp % 2 == 1:
                res = self.gf.poly_mod(self.gf.poly_mul(res, base), mod_poly)

            base = self.gf.poly_mod(self.gf.poly_mul(base, base), mod_poly)
            exp //= 2

        return res

    # -----------------------------------------
    # Check if a polynomial is irreducible
    # -----------------------------------------
    def _is_irreducible(self, poly):
        x = [0, 1]  # polynomial x
        u = x

        # Ben-Or irreducibility test
        for i in range(1, self.t // 2 + 1):
            u = self._poly_pow_mod(u, 1 << self.m, poly)
            u_minus_x = self.gf.poly_add(u, x)

            gcd, _, _ = self.gf.poly_ext_gcd(poly, u_minus_x)

            if len(gcd) > 1:
                return False

        # Additional test condition
        u = x
        for _ in range(self.t):
            u = self._poly_pow_mod(u, 1 << self.m, poly)

        if len(u) != 2 or u[0] != 0 or u[1] != 1:
            return False

        return True

    # -----------------------------------------
    # Generate random irreducible polynomial
    # -----------------------------------------
    def _generate_irreducible_poly(self):
        while True:
            # random monic polynomial of degree t
            poly = [random.randint(0, self.gf.size - 1)
                    for _ in range(self.t)] + [1]

            if self._is_irreducible(poly):
                return poly

    # -----------------------------------------
    # Generate support set L
    # -----------------------------------------
    def _generate_support(self):
        L = []

        # take all GF elements except roots of g(x)
        for i in range(self.gf.size):
            if self.gf.poly_eval(self.g, i) != 0:
                L.append(i)

        if len(L) < self.n:
            raise ValueError("Not enough support elements")

        # randomly select n elements
        return random.sample(L, self.n)

    # -----------------------------------------
    # Build parity-check matrix over GF(2^m)
    # -----------------------------------------
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

    # -----------------------------------------
    # Convert GF matrix to binary matrix
    # -----------------------------------------
    def _convert_H_to_bin(self, H_gf):
        H_bin = []

        for row in H_gf:
            for b in range(self.m):
                bin_row = []

                for val in row:
                    # extract bit b from field element
                    bin_row.append((val >> b) & 1)

                H_bin.append(bin_row)

        return np.array(H_bin, dtype=int)

    # -----------------------------------------
    # Generate generator matrix G from H
    # -----------------------------------------
    def _generate_G_from_H(self, H_bin):
        rows, cols = H_bin.shape
        M = np.copy(H_bin)

        P_cols = list(range(cols))  # track column permutations

        r = 0

        for c in range(cols):
            if r >= rows:
                break

            # find pivot
            pivot_c = c

            while pivot_c < cols and M[r, pivot_c] == 0:
                pivot_c += 1

            if pivot_c == cols:
                break

            # swap columns if needed
            if c != pivot_c:
                M[:, [c, pivot_c]] = M[:, [pivot_c, c]]
                P_cols[c], P_cols[pivot_c] = P_cols[pivot_c], P_cols[c]

            # Gaussian elimination
            for i in range(rows):
                if i != r and M[i, c] == 1:
                    M[i] = (M[i] + M[r]) % 2

            r += 1

        rank = r

        # split matrix into systematic form
        I = M[:rank, :rank]
        R = M[:rank, rank:]

        # G = [R^T | I]
        k = cols - rank
        G = np.hstack((R.T, np.eye(k, dtype=int)))

        return G, P_cols

    # -----------------------------------------
    # Patterson decoding algorithm
    # -----------------------------------------
    def decode(self, received_vector):

        # Step 1: Compute syndrome S(x)
        S = []

        for i, c_i in enumerate(received_vector):
            if c_i == 1:
                alpha = self.L[i]

                poly_to_inv = [self.gf.add(0, alpha), 1]

                try:
                    inv_poly = self.gf.poly_inv_mod(poly_to_inv, self.g)
                    S = self.gf.poly_add(S, inv_poly)
                except:
                    pass

        S = self.gf.poly_mod(S, self.g)

        if len(S) == 0:
            return received_vector

        # Step 2: Compute inverse of syndrome
        try:
            S_inv = self.gf.poly_inv_mod(S, self.g)
        except:
            return received_vector

        T = self.gf.poly_add(S_inv, [0, 1])  # + x
        T = self.gf.poly_mod(T, self.g)

        # Step 3: square root step
        power = 1 << (self.m * self.t - 1)
        R = self._poly_pow_mod(T, power, self.g)

        # Step 4: Extended Euclidean Algorithm
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

        # Step 5: error locator polynomial σ(x)
        a_sq = self.gf.poly_mul(a_poly, a_poly)
        b_sq = self.gf.poly_mul(b_poly, b_poly)

        sigma = self.gf.poly_add([0] + a_sq, b_sq)

        # Step 6: find error positions
        error_vector = np.zeros(self.n, dtype=int)

        for i, alpha in enumerate(self.L):
            if self.gf.poly_eval(sigma, alpha) == 0:
                error_vector[i] = 1

        # correct received vector
        corrected = (received_vector + error_vector) % 2

        return corrected