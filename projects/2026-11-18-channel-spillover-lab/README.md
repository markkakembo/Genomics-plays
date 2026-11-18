# Channel Spillover Lab: Why Image Channels Lie

**Da Vinci's Poet · November 18, 2026 · educational simulation**

## Triggering research

Lequyer, J., Nowlan, F., Hsu, W.-H., et al. **A zero-shot spillover denoiser for highly multiplexed images.** *Nature Methods*, published **18 November 2026**. DOI: [10.1038/s41592-026-03263-y](https://doi.org/10.1038/s41592-026-03263-y).

The peer-reviewed paper introduces **SpillOT**, a zero-shot approach that addresses image noise and channel spillover using optimal transport and other techniques, without calibration experiments or representative training datasets. See the [authors' actual implementation](https://github.com/jason-lequyer/SpillOT/).

**This repository does not implement SpillOT**, use its code, reproduce its benchmarks, or claim to validate the paper.

## Why this demonstration matters

In multiplexed microscopy, a strong signal in one channel can leak into another and resemble a real biological marker. That may lead to false cell identities or associations. This mini-project teaches the **simplest linear mixing model** and shows why correcting bleed-through without calibration is a hard inference problem.

Let true channel intensities be A and B, and observed channels be X and Y:

```text
X = A + alpha * B
Y = beta * A + B
```

If **alpha** and **beta** are known and `1 - alpha*beta != 0`, algebraically invert the 2×2 matrix to recover the synthetic true channels. If they are unknown, the same observation admits multiple explanations. Noise and biological co-expression make real-world inference even harder.

## Run (Python 3.10+, no third-party dependencies)

```bash
cd projects/2026-11-18-channel-spillover-lab
python spillover.py
python -m unittest discover -s . -p 'test_*.py' -v
```

Expected noiseless example: true `(8, 3)`, observed `(8.6, 3.8)`, recovered `(8, 3)`.

## What is and isn't established

- **Demonstrated mathematically:** exact recovery in a synthetic noiseless two-channel model with known mixing coefficients and nonsingular matrix.
- **Demonstrated by test:** round-trip recovery, singular matrix rejection, invalid-value rejection, and ambiguity under unknown coefficients.
- **Not demonstrated:** performance on biological images, real-world mixing coefficients, spatially varying spillover, Poisson noise, zero-shot denoising, optimal transport, or improvements to cell classification.
- **Important:** simple inverse mixing can produce negative values or amplify measurement noise. In real experiments, co-expression may be biological rather than contamination.

## Sources and independence

Primary source: [Lequyer et al., Nature Methods, 18 November 2026](https://www.nature.com/articles/s41592-026-03263-y). Original software: [SpillOT](https://github.com/jason-lequyer/SpillOT/). This project is an original teaching simulation using elementary linear algebra, not a derivative implementation of SpillOT. No research images or proprietary data included.

MIT license: covered by the parent repository's LICENSE.
