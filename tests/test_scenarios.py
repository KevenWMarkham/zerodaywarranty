"""Tests for the scenario library lookup + registration."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from zero_day_warranty.scenarios import (
    LIBRARY_CSV,
    LIBRARY_XLSX,
    ScenarioRow,
    append_to_csv,
    append_to_xlsx,
    find,
    load_library,
    missing_from_library,
    repo_scenarios,
    search,
)

REPO = Path(__file__).resolve().parents[1]


def test_library_loads_with_expected_columns() -> None:
    rows = load_library(LIBRARY_CSV)
    assert len(rows) > 700
    first = rows[0]
    assert first.scenario_id
    assert first.service_code
    assert first.industry == first.service_code.split("-")[0].lower()


def test_search_by_industry_and_term() -> None:
    rows = load_library(LIBRARY_CSV)
    axle = search(rows, industry="axle")
    assert axle and all(r.industry == "axle" for r in axle)
    markdown = search(rows, term="markdown")
    assert any(
        "markdown" in r.scenario_id.lower() or "markdown" in r.title.lower() for r in markdown
    )


def test_repo_scenarios_include_zero_day_warranty() -> None:
    repo = repo_scenarios(REPO / "service")
    ids = {r.scenario_id for r in repo}
    assert "axle-warranty-zero-day-root-cause" in ids
    zdw = find(repo, "axle-warranty-zero-day-root-cause")
    assert zdw is not None
    assert zdw.service_code == "AXLE-WARRANTY-01"
    assert zdw.schemas  # schemas were derived from the agent manifests


def test_missing_detection_against_synthetic_library() -> None:
    library = [ScenarioRow(scenario_id="rc-known", service_code="RC-E2E-03")]
    candidates = [
        ScenarioRow(scenario_id="rc-known", service_code="RC-E2E-03"),
        ScenarioRow(scenario_id="axle-new", service_code="AXLE-WARRANTY-01"),
    ]
    missing = missing_from_library(library, candidates)
    assert [m.scenario_id for m in missing] == ["axle-new"]


def test_append_to_csv_continues_index(tmp_path: Path) -> None:
    csv_copy = tmp_path / "lib.csv"
    shutil.copy(LIBRARY_CSV, csv_copy)
    before = load_library(csv_copy)
    added = append_to_csv(
        [ScenarioRow(scenario_id="axle-test-x", service_code="AXLE-X-01")], csv_copy
    )
    after = load_library(csv_copy)
    assert added == 1
    assert len(after) == len(before) + 1
    new = find(after, "axle-test-x")
    assert new is not None
    assert new.index == (max(r.index or 0 for r in before) + 1)


def test_append_to_xlsx_roundtrip(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    xlsx_copy = tmp_path / "chains.xlsx"
    shutil.copy(LIBRARY_XLSX, xlsx_copy)
    added = append_to_xlsx(
        [ScenarioRow(scenario_id="axle-test-y", service_code="AXLE-Y-01")], xlsx_copy
    )
    assert added == 1
    wb = openpyxl.load_workbook(xlsx_copy, read_only=True)
    ws = wb["Scenario Library"]
    ids = [row[1] for row in ws.iter_rows(min_row=2, max_col=2, values_only=True)]
    assert "axle-test-y" in ids
