from math import sqrt


def wilson(k, n, z=1.96):
    """95% Wilson score interval for k successes in n trials. Returns (low, high)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    adj = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (centre - adj) / denom), min(1.0, (centre + adj) / denom))
