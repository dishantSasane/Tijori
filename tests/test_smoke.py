"""Smoke test so CI is green on day one. Real tests live next to each component's spec."""

import trading


def test_package_imports() -> None:
    assert trading.__version__
