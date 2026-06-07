"""Tests for the 3D process fly-through generator."""

from __future__ import annotations

import json
from pathlib import Path

from zero_day_warranty.chain import WarrantyRootCauseChain
from zero_day_warranty.process3d import (
    RAIL_LANES,
    build_process_graph,
    render_process_3d_html,
)
from zero_day_warranty.synthetic import generate


def _result() -> object:
    return WarrantyRootCauseChain(generate().medallion).run()


def test_graph_has_24_steps_on_valid_lanes() -> None:
    graph = build_process_graph(_result())
    rail_ids = {lid for lid, _hex in RAIL_LANES}
    assert len(graph["steps"]) == 24
    assert [s["n"] for s in graph["steps"]] == list(range(1, 25))
    for s in graph["steps"]:
        assert s["primaryLane"] in rail_ids
        assert s["phase"] != "—"
        for lane in s["lanes"]:
            assert lane in rail_ids  # governance is the floor, never a rail
    assert len(graph["path"]) == 24
    assert all(len(p) == 3 for p in graph["path"])  # x, y, z


def test_graph_layout_and_meta_are_live() -> None:
    result = _result()
    graph = build_process_graph(result)
    assert len(graph["lanes"]) == len(RAIL_LANES)
    assert len(graph["phases"]) == 7
    # node x-position matches the step's path point (single source of layout)
    for s, p in zip(graph["steps"], graph["path"], strict=True):
        assert s["x"] == p[0]
        assert s["z"] == p[2]
    meta = graph["meta"]
    assert meta["suspect_lot"] == result.suspect_lot
    assert meta["ledger_rows"] == 24
    assert meta["verified"] is True


def test_html_is_self_contained_three_js() -> None:
    result = _result()
    html = render_process_3d_html(result)
    assert html.startswith("<!DOCTYPE html>")
    assert '<script type="importmap">' in html
    assert "three.module.js" in html
    assert "UnrealBloomPass" in html  # the bloom glow
    assert "RoundedBoxGeometry" in html  # real-to-life beveled geometry
    # three.js is vendored (served from Azure), not a public CDN
    assert "vendor/three@" in html
    assert "cdn.jsdelivr" not in html
    # the embedded graph parses and carries the live suspect lot
    raw = html.split('<script id="graph" type="application/json">', 1)[1]
    raw = raw.split("</script>", 1)[0]
    embedded = json.loads(raw)
    assert embedded["meta"]["suspect_lot"] == result.suspect_lot
    assert len(embedded["steps"]) == 24
    # cross-link back to the flat portal
    assert "ZeroDayWarranty_SwimLane_Views.html" in html


def test_committed_html_in_sync_with_generator() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "docs" / "design" / "ZeroDayWarranty_Process_3D.html"
    result = WarrantyRootCauseChain(generate().medallion).run()
    assert path.read_text(encoding="utf-8") == render_process_3d_html(result)
