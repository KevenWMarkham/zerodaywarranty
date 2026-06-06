"""Manifest conformance tests for AXLE-WARRANTY-01.

Mirrors the APEX ``test_agent_manifests.py`` smoke-test pattern: verifies every
agent.yaml declares production fields, every prompt is authored (not a stub),
the HITL gate is wired on the compliance agent, and the scenario chain is a
well-formed 24-step chain whose agents cover all 24 steps exactly once.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zero_day_warranty.manifest import (
    PRACTICE_CODES,
    load_agent,
    load_agent_spec,
    load_scenario,
)

SERVICE_DIR = Path(__file__).resolve().parents[1] / "service" / "AXLE-WARRANTY-01"
CATALOG_DIR = Path(__file__).resolve().parents[1] / "catalog" / "agents"

EXPECTED_ROLES = {
    "detect",
    "context",
    "stattest",
    "quality",
    "supplier",
    "hypothesis",
    "compliance",
}
HITL_GATE_ROLES = {"compliance"}


def test_scenario_loads_and_is_24_steps() -> None:
    scenario = load_scenario(SERVICE_DIR / "scenario.yaml")
    assert scenario.service_code == "AXLE-WARRANTY-01"
    assert len(scenario.chain_24) == 24
    assert [s.step for s in scenario.chain_24] == list(range(1, 25))


def test_scenario_agents_cover_every_step_once() -> None:
    scenario = load_scenario(SERVICE_DIR / "scenario.yaml")
    covered: list[int] = []
    role_steps = {a.role: [] for a in scenario.agents}  # type: ignore[var-annotated]
    for step in scenario.chain_24:
        role_steps[step.agent_role].append(step.step)
        covered.append(step.step)
    assert sorted(covered) == list(range(1, 25))
    # each agent.yaml's declared steps match the scenario chain
    for ref in scenario.agents:
        agent = load_agent(SERVICE_DIR / ref.config)
        assert agent.steps == role_steps[ref.role]


def test_all_expected_roles_present() -> None:
    scenario = load_scenario(SERVICE_DIR / "scenario.yaml")
    assert {a.role for a in scenario.agents} == EXPECTED_ROLES


@pytest.mark.parametrize("role", sorted(EXPECTED_ROLES))
def test_each_agent_has_real_model(role: str) -> None:
    agent = load_agent(SERVICE_DIR / "agents" / role / "agent.yaml")
    assert agent.model != "TBD"
    assert agent.model.startswith("gpt-")


@pytest.mark.parametrize("role", sorted(EXPECTED_ROLES))
def test_each_prompt_is_authored(role: str) -> None:
    agent = load_agent(SERVICE_DIR / "agents" / role / "agent.yaml")
    prompt = (SERVICE_DIR / "agents" / role / agent.prompt_ref).read_text(encoding="utf-8")
    assert "TBD" not in prompt
    assert len(prompt) > 500


@pytest.mark.parametrize("role", sorted(EXPECTED_ROLES))
def test_hitl_gate_wired_only_where_expected(role: str) -> None:
    agent = load_agent(SERVICE_DIR / "agents" / role / "agent.yaml")
    assert agent.hitl_gate is (role in HITL_GATE_ROLES)


def test_compliance_agent_requires_obo_and_emits_audit() -> None:
    agent = load_agent(SERVICE_DIR / "agents" / "compliance" / "agent.yaml")
    assert agent.operator_obo_required is True
    assert agent.audit_row_emit is True
    assert "Warranty.ChargebackDecision" in agent.schemas_write


@pytest.mark.conformance
def test_catalog_agents_valid_and_write_tools_have_hitl() -> None:
    specs = [load_agent_spec(p) for p in sorted(CATALOG_DIR.glob("*.yaml"))]
    assert specs, "expected at least one catalog agent"
    for spec in specs:
        assert spec.practice in PRACTICE_CODES
        assert spec.name.startswith("apex.axle.agents.")
        # any agent with a write tool must declare HITL or be pure-HOTL
        if spec.write_tools():
            assert spec.has_hitl() or spec.oversight_modes == ["HOTL"]
