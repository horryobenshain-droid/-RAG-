using ll = long long;

ll qpow(ll base, ll exponent, ll mod) {
    // Computes base^exponent modulo mod in O(log exponent) time.
    ll result = 1 % mod;
    base %= mod;
    while (exponent > 0) {
        if (exponent & 1) {
            result = result * base % mod;
        }
        base = base * base % mod;
        exponent >>= 1;
    }
    return result;
}
