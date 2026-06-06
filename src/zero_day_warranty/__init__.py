"""Zero Day Warranty — agentic automotive warranty root-cause investigation.

A single orchestrator agent joins connected-vehicle warranty claims back to
factory build history per VIN, surfaces the statistically significant
``cohort × station × tool × supplier-lot`` interactions that drive a warranty
cluster, and produces a supplier chargeback evidence package — collapsing an
8–12 week / 6-team manual RCA into roughly 12 minutes.

This package is the laptop-substrate reference implementation. It mirrors the
APEX delivery-accelerator conventions (medallion data plane, 14-field
hash-chained audit ledger, YAML scenario/agent manifests).

Public surface:

- :mod:`zero_day_warranty.domains`       — the four warranty data domains
- :mod:`zero_day_warranty.medallion`     — Bronze→Silver→Gold per-VIN view
- :mod:`zero_day_warranty.audit`         — hash-chained decision ledger
- :mod:`zero_day_warranty.calculations`  — the reference-scenario math
- :mod:`zero_day_warranty.synthetic`     — synthetic reference dataset
- :mod:`zero_day_warranty.chain`         — the 24-step agent chain
- :mod:`zero_day_warranty.manifest`      — scenario / agent manifest loaders
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
