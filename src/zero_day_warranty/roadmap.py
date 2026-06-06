"""Sprint roadmap orchestrator.

Loads the delivery backlog (``backlog/roadmap.yaml``) and drives it: validates
the structure, computes per-sprint and overall progress, and renders a checkbox
board. Deployments are gated — a deployment is only *validated* once it is
**built → deployed → tested** (all three checked).

This is the single mechanism behind the ``zdw roadmap`` / ``zdw sprints`` /
``zdw checklist`` commands, mirroring the APEX ``apex.py status`` pattern.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Status(StrEnum):
    """Story / sprint status."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


#: Glyphs for the checkbox board.
STATUS_BOX: dict[Status, str] = {
    Status.DONE: "[x]",
    Status.IN_PROGRESS: "[~]",
    Status.TODO: "[ ]",
    Status.BLOCKED: "[!]",
}


class Story(BaseModel):
    """One backlog story."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    status: Status = Status.TODO
    acceptance: str = ""

    @property
    def box(self) -> str:
        """Checkbox glyph for this story's status."""
        return STATUS_BOX[self.status]


class Deployment(BaseModel):
    """One deployable component, gated built → deployed → tested."""

    model_config = ConfigDict(extra="forbid")

    id: str
    component: str
    built: bool = False
    deployed: bool = False
    tested: bool = False

    @property
    def validated(self) -> bool:
        """True only when built AND deployed AND tested."""
        return self.built and self.deployed and self.tested

    @property
    def gate(self) -> str:
        """Render the three gates as checkboxes, e.g. ``[x] built [ ] deployed``."""

        def mark(flag: bool) -> str:
            return "x" if flag else " "

        return (
            f"[{mark(self.built)}] built  "
            f"[{mark(self.deployed)}] deployed  "
            f"[{mark(self.tested)}] tested"
        )


class Phase(BaseModel):
    """A roadmap phase grouping several sprints."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    goal: str = ""


class Sprint(BaseModel):
    """One sprint: a set of stories and (optionally) gated deployments."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    phase: str
    goal: str = ""
    status: Status = Status.TODO
    stories: list[Story] = Field(default_factory=list)
    deployments: list[Deployment] = Field(default_factory=list)

    @property
    def done_stories(self) -> int:
        """Count of stories marked done."""
        return sum(1 for s in self.stories if s.status is Status.DONE)

    @property
    def story_pct(self) -> int:
        """Percent of stories done (0 when the sprint has no stories)."""
        return round(100 * self.done_stories / len(self.stories)) if self.stories else 0

    @property
    def validated_deployments(self) -> int:
        """Count of deployments that are built, deployed, and tested."""
        return sum(1 for d in self.deployments if d.validated)

    @property
    def deploy_ready(self) -> bool:
        """True when every deployment in the sprint is validated (or there are none)."""
        return all(d.validated for d in self.deployments)


class Roadmap(BaseModel):
    """The whole roadmap: phases + sprints, validated for referential integrity."""

    model_config = ConfigDict(extra="forbid")

    meta: dict[str, str] = Field(default_factory=dict)
    phases: list[Phase]
    sprints: list[Sprint]

    @model_validator(mode="after")
    def _check_integrity(self) -> Roadmap:
        phase_ids = {p.id for p in self.phases}
        seen_sprint: set[str] = set()
        seen_item: set[str] = set()
        for sp in self.sprints:
            if sp.phase not in phase_ids:
                raise ValueError(f"sprint {sp.id}: unknown phase {sp.phase!r}")
            if sp.id in seen_sprint:
                raise ValueError(f"duplicate sprint id {sp.id!r}")
            seen_sprint.add(sp.id)
            for st in sp.stories:
                if st.id in seen_item:
                    raise ValueError(f"duplicate story id {st.id!r}")
                seen_item.add(st.id)
            for d in sp.deployments:
                if d.id in seen_item:
                    raise ValueError(f"duplicate deployment id {d.id!r}")
                seen_item.add(d.id)
        return self

    # -- aggregates ----------------------------------------------------

    def sprints_in(self, phase_id: str) -> list[Sprint]:
        """Sprints belonging to a phase, in declared order."""
        return [s for s in self.sprints if s.phase == phase_id]

    def overall_story_pct(self) -> int:
        """Percent of all stories done across every sprint."""
        stories = [st for sp in self.sprints for st in sp.stories]
        done = sum(1 for st in stories if st.status is Status.DONE)
        return round(100 * done / len(stories)) if stories else 0

    def deployments(self) -> list[Deployment]:
        """Every gated deployment across all sprints."""
        return [d for sp in self.sprints for d in sp.deployments]

    def deployment_summary(self) -> dict[str, int]:
        """Aggregate counts: total, built, deployed, tested, validated."""
        deps = self.deployments()
        return {
            "total": len(deps),
            "built": sum(1 for d in deps if d.built),
            "deployed": sum(1 for d in deps if d.deployed),
            "tested": sum(1 for d in deps if d.tested),
            "validated": sum(1 for d in deps if d.validated),
        }


def load_roadmap(path: str | Path) -> Roadmap:
    """Parse and validate the backlog YAML."""
    with Path(path).open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")
    return Roadmap.model_validate(data)


# ---------------------------------------------------------------------------
# Renderers (plain text for the CLI)
# ---------------------------------------------------------------------------


def _bar(pct: int, width: int = 20) -> str:
    filled = round(width * pct / 100)
    return "█" * filled + "·" * (width - filled)


def render_roadmap(rm: Roadmap) -> str:
    """Phase + sprint overview with progress bars."""
    lines = [
        f"Zero Day Warranty · roadmap ({rm.meta.get('product', '')})",
        f"Overall stories complete: {rm.overall_story_pct()}%   {_bar(rm.overall_story_pct())}",
        "-" * 64,
    ]
    for phase in rm.phases:
        sprints = rm.sprints_in(phase.id)
        done = sum(1 for s in sprints if s.status is Status.DONE)
        lines.append(f"\n{phase.id} · {phase.name}  ({done}/{len(sprints)} sprints done)")
        if phase.goal:
            lines.append(f"   {phase.goal}")
        for sp in sprints:
            box = STATUS_BOX[sp.status]
            dep = (
                f" · deploy {sp.validated_deployments}/{len(sp.deployments)}"
                if sp.deployments
                else ""
            )
            lines.append(
                f"   {box} {sp.id} {sp.name:<34} {sp.story_pct:>3}% {_bar(sp.story_pct, 12)}{dep}"
            )
    return "\n".join(lines)


def render_sprints(rm: Roadmap, phase: str | None = None) -> str:
    """Every story as a checkbox, grouped by sprint."""
    lines = ["Zero Day Warranty · sprint backlog", "-" * 64]
    for sp in rm.sprints:
        if phase and sp.phase != phase:
            continue
        lines.append(
            f"\n{STATUS_BOX[sp.status]} {sp.id} · {sp.name}  [{sp.phase}] — {sp.story_pct}%"
        )
        for st in sp.stories:
            lines.append(f"    {st.box} {st.id} {st.title}")
        for d in sp.deployments:
            mark = "x" if d.validated else " "
            lines.append(f"    [{mark}] {d.id} (deploy) {d.component}")
    return "\n".join(lines)


def render_checklist(rm: Roadmap) -> str:
    """Deployment validation matrix — built / deployed / tested per component."""
    s = rm.deployment_summary()
    lines = [
        "Zero Day Warranty · deployment validation checklist",
        f"validated {s['validated']}/{s['total']}  ·  built {s['built']}  deployed {s['deployed']}  tested {s['tested']}",
        "-" * 78,
    ]
    for sp in rm.sprints:
        if not sp.deployments:
            continue
        lines.append(f"\n{sp.id} · {sp.name}")
        for d in sp.deployments:
            flag = "✓" if d.validated else " "
            lines.append(f"  {flag} {d.component}")
            lines.append(f"      {d.gate}")
    if s["validated"] == s["total"] and s["total"]:
        lines.append("\nALL DEPLOYMENTS VALIDATED")
    else:
        lines.append(f"\n{s['total'] - s['validated']} deployment(s) not yet validated")
    return "\n".join(lines)


__all__ = [
    "STATUS_BOX",
    "Deployment",
    "Phase",
    "Roadmap",
    "Sprint",
    "Status",
    "Story",
    "load_roadmap",
    "render_checklist",
    "render_roadmap",
    "render_sprints",
]
