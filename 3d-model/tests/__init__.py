"""Philly3D invariant suite. Run from 3d-model/:

    python3 -m unittest discover -s tests -v

Stdlib only (plain python3 from the Xcode CommandLineTools is enough). Every test
resolves the model directory from its own location and skips cleanly when the
data it needs is not committed / not built.
"""
