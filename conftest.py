"""Root conftest for the Zero Day Warranty solution.

Shared fixtures available to the test suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    """Absolute path to the repository root."""
    return Path(__file__).parent


@pytest.fixture
def service_dir(repo_root: Path) -> Path:
    """Path to the AXLE-WARRANTY-01 service definition."""
    return repo_root / "service" / "AXLE-WARRANTY-01"


@pytest.fixture
def fixtures_dir(request: pytest.FixtureRequest) -> Path:
    """Per-test fixtures directory (``tests/fixtures/``)."""
    return Path(request.path).parent / "fixtures"
