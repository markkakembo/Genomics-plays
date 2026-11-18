"""Educational two-channel mixing/unmixing, NOT SpillOT.

Model: observed_A = true_A + alpha*true_B
       observed_B = beta*true_A + true_B
Known alpha/beta are required; the inverse becomes unstable as alpha*beta approaches 1.
"""
from math import isfinite

def mix(a: float, b: float, alpha: float, beta: float) -> tuple[float, float]:
    _validate(a, b, alpha, beta)
    return a + alpha*b, beta*a + b

def unmix(observed_a: float, observed_b: float, alpha: float, beta: float) -> tuple[float, float]:
    _validate(observed_a, observed_b, alpha, beta)
    determinant = 1 - alpha*beta
    if abs(determinant) < 1e-8:
        raise ValueError("Mixing matrix is singular or nearly singular")
    return ((observed_a - alpha*observed_b)/determinant,
            (observed_b - beta*observed_a)/determinant)

def _validate(*values: float) -> None:
    if not all(isfinite(x) for x in values):
        raise ValueError("Inputs must be finite")

def main() -> None:
    true_a, true_b = 8.0, 3.0
    alpha, beta = 0.2, 0.1
    observed = mix(true_a, true_b, alpha, beta)
    recovered = unmix(*observed, alpha, beta)
    print(f"True channels:      {(true_a, true_b)}")
    print(f"Observed channels:  {observed}")
    print(f"Recovered channels: {tuple(round(x, 8) for x in recovered)}")
    print("Note: known coefficients and noiseless synthetic signals; NOT a real-image validation.")

if __name__ == "__main__":
    main()
