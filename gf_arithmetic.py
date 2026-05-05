import numpy as np

class GF2m:
    def __init__(self, m, prim_poly):
        """
        Initialize the Galois Field GF(2^m).
        :param m: Degree of the field.
        :param prim_poly: Primitive polynomial in integer representation (e.g., x^4 + x + 1 is 19).
        """
        self.m = m
        self.size = 1 << m
        self.prim_poly = prim_poly

        self.exp_table = [0] * (self.size * 2)
        self.log_table = [0] * self.size

        # Generate exponential and logarithm tables
        x = 1
        for i in range(self.size - 1):
            self.exp_table[i] = x
            self.log_table[x] = i
            x <<= 1
            if x & self.size:
                x ^= self.prim_poly

        # Complete exponential table for overflow cases in multiplication
        for i in range(self.size - 1, self.size * 2):
            self.exp_table[i] = self.exp_table[i - (self.size - 1)]

    def add(self, a, b):
        return a ^ b

    def sub(self, a, b):
        return a ^ b  # In GF(2^m), addition and subtraction are identical

    def mul(self, a, b):
        if a == 0 or b == 0:
            return 0
        return self.exp_table[self.log_table[a] + self.log_table[b]]

    def div(self, a, b):
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero in GF(2^m)")
        if a == 0:
            return 0
        return self.exp_table[(self.log_table[a] - self.log_table[b] + (self.size - 1)) % (self.size - 1)]

    def inv(self, a):
        return self.div(1, a)

    def power(self, a, p):
        if a == 0:
            return 0
        if p == 0:
            return 1
        return self.exp_table[(self.log_table[a] * p) % (self.size - 1)]

    def poly_add(self, p1, p2):
        max_len = max(len(p1), len(p2))
        res = [0] * max_len
        for i in range(len(p1)):
            res[i] ^= p1[i]
        for i in range(len(p2)):
            res[i] ^= p2[i]
        # Remove trailing zeros
        while len(res) > 0 and res[-1] == 0:
            res.pop()
        return res

    def poly_mul(self, p1, p2):
        if not p1 or not p2:
            return []
        res = [0] * (len(p1) + len(p2) - 1)
        for i, a in enumerate(p1):
            for j, b in enumerate(p2):
                res[i+j] ^= self.mul(a, b)
        # Remove trailing zeros
        while len(res) > 0 and res[-1] == 0:
            res.pop()
        return res

    def poly_mod(self, p, mod_poly):
        """
        Compute p(x) mod mod_poly(x) over GF(2^m)
        """
        p = p[:]
        mod_poly = mod_poly[:]
        if len(mod_poly) == 0:
            raise ValueError("Modulus polynomial cannot be zero")
        
        while len(p) >= len(mod_poly):
            # The coefficient to eliminate the leading term of p
            coeff = self.div(p[-1], mod_poly[-1])
            degree_diff = len(p) - len(mod_poly)
            
            for i in range(len(mod_poly)):
                p[i + degree_diff] ^= self.mul(coeff, mod_poly[i])
            
            while len(p) > 0 and p[-1] == 0:
                p.pop()
        return p

    def poly_div(self, num, den):
        """
        Divide polynomial num by den over GF(2^m), returns quotient and remainder.
        """
        num = num[:]
        den = den[:]
        if len(den) == 0:
            raise ValueError("Division by zero polynomial")
        
        quotient = [0] * max(1, len(num) - len(den) + 1)
        while len(num) >= len(den):
            deg_diff = len(num) - len(den)
            coeff = self.div(num[-1], den[-1])
            quotient[deg_diff] = coeff
            for i in range(len(den)):
                num[i + deg_diff] ^= self.mul(coeff, den[i])
            while len(num) > 0 and num[-1] == 0:
                num.pop()
        return quotient, num

    def poly_ext_gcd(self, a, b):
        """
        Extended Euclidean Algorithm for polynomials.
        Returns gcd, x, y such that a*x + b*y = gcd
        """
        old_r, r = a[:], b[:]
        old_s, s = [1], []
        old_t, t = [], [1]

        while len(r) > 0:
            quotient, remainder = self.poly_div(old_r, r)
            old_r, r = r, remainder
            
            # old_s - quotient * s
            qs = self.poly_mul(quotient, s)
            new_s = self.poly_add(old_s, qs)
            old_s, s = s, new_s
            
            # old_t - quotient * t
            qt = self.poly_mul(quotient, t)
            new_t = self.poly_add(old_t, qt)
            old_t, t = t, new_t

        # Normalize so that leading coefficient of gcd is 1
        if len(old_r) > 0:
            lead = old_r[-1]
            if lead != 1:
                inv_lead = self.inv(lead)
                old_r = self.poly_mul(old_r, [inv_lead])
                old_s = self.poly_mul(old_s, [inv_lead])
                old_t = self.poly_mul(old_t, [inv_lead])

        return old_r, old_s, old_t

    def poly_inv_mod(self, p, mod_poly):
        gcd, x, y = self.poly_ext_gcd(p, mod_poly)
        if len(gcd) != 1 or gcd[0] != 1:
            raise ValueError("Polynomial is not invertible modulo the given polynomial")
        return self.poly_mod(x, mod_poly)

    def poly_deriv(self, p):
        """
        Formal derivative of polynomial over GF(2^m).
        Since char is 2, odd degree terms become even degree terms, even degree terms vanish.
        """
        res = [0] * max(1, len(p) - 1)
        for i in range(1, len(p)):
            if i % 2 != 0:
                res[i-1] = p[i]
        while len(res) > 0 and res[-1] == 0:
            res.pop()
        return res

    def sqrt(self, a):
        """
        Square root of an element in GF(2^m).
        In GF(2^m), sqrt(a) = a^(2^(m-1))
        """
        return self.power(a, 1 << (self.m - 1))

    def poly_sqrt(self, p):
        """
        Square root of a polynomial over GF(2^m).
        Only works if all odd powers have 0 coefficients.
        """
        for i in range(1, len(p), 2):
            if p[i] != 0:
                raise ValueError("Polynomial does not have a perfect square root")
        
        res = [0] * ((len(p) + 1) // 2)
        for i in range(0, len(p), 2):
            res[i//2] = self.sqrt(p[i])
        return res

    def poly_eval(self, p, x):
        """
        Evaluate polynomial p at x using Horner's method.
        """
        res = 0
        for i in range(len(p)-1, -1, -1):
            res = self.add(self.mul(res, x), p[i])
        return res

# Helper for matrices over GF(2)
def matrix_multiply_gf2(A, B):
    A_np = np.array(A, dtype=int)
    B_np = np.array(B, dtype=int)
    return np.dot(A_np, B_np) % 2

def rref_gf2(M):
    """
    Computes the Reduced Row Echelon Form of a matrix over GF(2).
    """
    M = np.copy(M)
    rows, cols = M.shape
    r = 0
    for c in range(cols):
        if r >= rows:
            break
        # Find pivot
        pivot_r = r
        while pivot_r < rows and M[pivot_r, c] == 0:
            pivot_r += 1
        if pivot_r == rows:
            continue
        # Swap rows
        M[[r, pivot_r]] = M[[pivot_r, r]]
        # Eliminate other rows
        for i in range(rows):
            if i != r and M[i, c] == 1:
                M[i] = (M[i] + M[r]) % 2
        r += 1
    return M

def invert_matrix_gf2(M):
    rows, cols = M.shape
    if rows != cols:
        raise ValueError("Matrix must be square to invert")
    
    aug_M = np.hstack((M, np.eye(rows, dtype=int)))
    rref_M = rref_gf2(aug_M)
    
    # Check if invertible
    left = rref_M[:, :cols]
    if not np.array_equal(left, np.eye(rows, dtype=int)):
        raise ValueError("Matrix is not invertible")
        
    return rref_M[:, cols:]
