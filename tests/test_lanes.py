"""Tests for the per-swim-lane views (Swim Lane Views portal)."""

from __future__ import annotations

from html import escape

from zero_day_warranty.chain import WarrantyRootCauseChain
from zero_day_warranty.lanes import (
    LANE_SPECS,
    PHASES,
    build_lane_views,
    render_swimlane_views_html,
    render_swimlane_views_md,
)
from zero_day_warranty.synthetic import generate


def _result() -> object:
    return WarrantyRootCauseChain(generate().medallion).run()


def test_phases_tile_all_24_steps_once() -> None:
    covered: list[int] = []
    for _name, lo, hi in PHASES:
        covered.extend(range(lo, hi + 1))
    assert covered == list(range(1, 25))


def test_lane_specs_union_covers_all_steps() -> None:
    owned: set[int] = set()
    for spec in LANE_SPECS:
        owned |= set(spec[9])  # steps tuple
    assert owned == set(range(1, 25))


def test_build_lane_views_is_live_and_complete() -> None:
    result = _result()
    views = build_lane_views(result)
    assert len(views) == len(LANE_SPECS)
    for v in views:
        assert v.kpis, f"{v.id} has no KPIs"
        assert len(v.cells) == len(v.steps)
        # every owned step within the chain's 24 is sealed to the ledger
        for cell in v.cells:
            assert cell.sealed is True
            assert cell.phase != "—"


def test_governance_lane_reflects_verified_chain() -> None:
    views = {v.id: v for v in build_lane_views(_result())}
    gov = views["governance"]
    assert gov.steps == tuple(range(1, 25))
    vals = {k.label: k.value for k in gov.kpis}
    assert vals["Hash chain"] == "VERIFIED"
    assert vals["Audit rows sealed"] == "24"


def test_hitl_lane_carries_live_decision() -> None:
    views = {v.id: v for v in build_lane_views(_result())}
    hitl = views["hitl"]
    assert hitl.steps == (22,)
    vals = {k.label: k.value for k in hitl.kpis}
    assert "approve" in vals["Decision"]


def test_html_has_every_lane_tab_and_live_figures() -> None:
    result = _result()
    html = render_swimlane_views_html(result)
    assert html.startswith("<!DOCTYPE html>")
    for spec in LANE_SPECS:
        lane_id, name = spec[0], spec[1]
        assert f'data-tab="{lane_id}"' in html
        assert f'data-panel="{lane_id}"' in html
        assert escape(name) in html
    # live, truthful figures (not hand-typed)
    assert result.suspect_lot in html
    assert "VERIFIED" in html
    # cross-links to the companion design-pack artifacts
    assert "ZeroDayWarranty_Persona_Portals.html#" in html
    assert "ZeroDayWarranty_Capability_SwimLanes.html" in html
    # deep-linkable tabs: ...#lane=<id> (e.g. from the 3D view) opens that tab
    assert "hashchange" in html
    assert "activateTab" in html


def test_markdown_twin_renders() -> None:
    md = render_swimlane_views_md(_result())
    assert md.startswith("# Zero Day Warranty — Swim Lane Views")
    assert "## Human-in-the-Loop" in md
    assert "| Step | Title | Output | Audit |" in md


def test_generated_files_are_in_sync_with_generator() -> None:
    # the committed design-pack artifacts must match `zdw lanes --write` output
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    html_path = root / "docs" / "design" / "ZeroDayWarranty_SwimLane_Views.html"
    md_path = root / "docs" / "zero-day-warranty" / "swim-lane-views.md"
    result = WarrantyRootCauseChain(generate().medallion).run()
    assert html_path.read_text(encoding="utf-8") == render_swimlane_views_html(result)
    assert md_path.read_text(encoding="utf-8") == render_swimlane_views_md(result)
