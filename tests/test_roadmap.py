"""Tests for the sprint roadmap orchestrator and the backlog."""

from __future__ import annotations

from pathlib import Path

import pytest

from zero_day_warranty.roadmap import (
    Deployment,
    Roadmap,
    Status,
    load_roadmap,
    render_checklist,
    render_roadmap,
    render_sprints,
)

BACKLOG = Path(__file__).resolve().parents[1] / "backlog" / "roadmap.yaml"


@pytest.fixture
def rm() -> Roadmap:
    return load_roadmap(BACKLOG)


def test_backlog_loads_and_validates(rm: Roadmap) -> None:
    assert rm.phases
    assert rm.sprints
    # every sprint references a declared phase (model validator enforces this too)
    phase_ids = {p.id for p in rm.phases}
    assert all(s.phase in phase_ids for s in rm.sprints)


def test_story_and_deployment_ids_are_unique(rm: Roadmap) -> None:
    ids = [st.id for sp in rm.sprints for st in sp.stories]
    ids += [d.id for sp in rm.sprints for d in sp.deployments]
    assert len(ids) == len(set(ids))


def test_deployment_gate_requires_all_three() -> None:
    d = Deployment(id="x", component="c", built=True, deployed=True, tested=False)
    assert not d.validated
    assert Deployment(id="y", component="c", built=True, deployed=True, tested=True).validated


def test_deployments_start_unvalidated(rm: Roadmap) -> None:
    # Nothing is deployed yet — every gate is open (design stage).
    s = rm.deployment_summary()
    assert s["total"] > 0
    assert s["validated"] == 0


def test_overall_progress_is_a_percentage(rm: Roadmap) -> None:
    pct = rm.overall_story_pct()
    assert 0 <= pct <= 100


def test_phase_p1_is_complete(rm: Roadmap) -> None:
    # The foundation phase (reference build) is done.
    p1 = rm.sprints_in("P1")
    assert p1
    assert all(s.status is Status.DONE for s in p1)


def test_renderers_produce_text(rm: Roadmap) -> None:
    assert "roadmap" in render_roadmap(rm).lower()
    assert "[x]" in render_sprints(rm)  # at least one done story
    chk = render_checklist(rm)
    assert "built" in chk and "deployed" in chk and "tested" in chk


def test_invalid_phase_reference_is_rejected() -> None:
    bad = {
        "phases": [{"id": "P1", "name": "x"}],
        "sprints": [{"id": "S1", "name": "y", "phase": "P9"}],
    }
    with pytest.raises(ValueError, match="unknown phase"):
        Roadmap.model_validate(bad)
