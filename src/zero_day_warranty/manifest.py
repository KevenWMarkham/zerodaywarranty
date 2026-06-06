"""Manifest models + loaders for the service definition.

The service definition under ``service/AXLE-WARRANTY-01/`` follows the APEX
convention: a ``scenario.yaml`` declaring the 24-step chain and its agents, one
``agent.yaml`` per agent role, and an optional agent-catalog entry per agent
(the ``AgentSpec`` shape from ``apex_agents``). These Pydantic models parse and
validate those manifests so tests can assert the contracts hold.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

PRACTICE_CODES: tuple[str, ...] = ("rc", "hls", "er", "axle", "tmt", "th", "ice")


class ModelTier(StrEnum):
    """Three-tier model strategy (APEX Sellers Guide §6.2)."""

    LIGHTWEIGHT = "lightweight"
    STANDARD = "standard"
    REASONING = "reasoning"


class OversightMode(StrEnum):
    """Oversight spectrum (APEX Sellers Guide §2.2C)."""

    HITL = "HITL"
    HOTL = "HOTL"
    HIC = "HIC"


# ---------------------------------------------------------------------------
# scenario.yaml
# ---------------------------------------------------------------------------


class ChainStep(BaseModel):
    """One step in the 24-step chain."""

    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=1, le=24)
    key: str
    cluster: int = Field(ge=1, le=7)
    title: str
    layer: str
    agent_role: str
    gpu: bool = False


class ScenarioAgentRef(BaseModel):
    """A scenario's reference to one of its agents."""

    model_config = ConfigDict(extra="forbid")

    role: str
    label: str
    cluster: int = Field(ge=1, le=7)
    config: str  # relative path to agents/{role}/agent.yaml


class ScenarioManifest(BaseModel):
    """The ``scenario.yaml`` top-level manifest."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    title: str
    service_code: str
    domain: str
    featured: bool = True
    moment: str
    solution: str
    use_case: str
    personas: str
    kpi: str
    waves: dict[str, str]
    chain_24: list[ChainStep]
    agents: list[ScenarioAgentRef]

    @field_validator("chain_24")
    @classmethod
    def _validate_chain_length(cls, v: list[ChainStep]) -> list[ChainStep]:
        if len(v) != 24:
            raise ValueError(f"chain_24 must declare exactly 24 steps, got {len(v)}")
        if [s.step for s in v] != list(range(1, 25)):
            raise ValueError("chain_24 steps must be numbered 1..24 in order")
        return v


# ---------------------------------------------------------------------------
# agents/{role}/agent.yaml
# ---------------------------------------------------------------------------


class AgentManifest(BaseModel):
    """One agent role's ``agent.yaml`` manifest."""

    model_config = ConfigDict(extra="forbid")

    role: str
    label: str
    cluster: int = Field(ge=1, le=7)
    scenario_id: str
    service_code: str
    archetype: str
    canonical_pattern: Literal["sequential", "concurrent", "handoff", "group_chat", "magentic"]
    model: str
    steps: list[int]
    tools: list[str] = Field(default_factory=list)
    schemas_read: list[str] = Field(default_factory=list)
    schemas_write: list[str] = Field(default_factory=list)
    hitl_gate: bool = False
    audit_row_emit: bool = True
    prompt_ref: str
    prompt_version: str
    manifest_version: str
    classification_propagation: list[str] = Field(default_factory=list)
    operator_obo_required: bool = False


# ---------------------------------------------------------------------------
# catalog/agents/*.yaml  (AgentSpec — apex_agents shape)
# ---------------------------------------------------------------------------


class ToolBinding(BaseModel):
    """One MCP tool the agent is authorized to call."""

    model_config = ConfigDict(extra="forbid")

    tool_id: str
    purpose: str
    write: bool = False


class HITLGate(BaseModel):
    """One HITL gate declared on a catalog agent."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    fires_when: str
    surface: Literal["teams_card", "copilot_studio", "dashboard", "mobile"] = "teams_card"
    sla_minutes: int = 60


class KpiTarget(BaseModel):
    """One KPI a catalog agent targets."""

    model_config = ConfigDict(extra="forbid")

    name: str
    direction: Literal["up", "down", "money", "neutral"]
    target_band: str = ""


class AgentSpec(BaseModel):
    """Catalog agent manifest (mirrors ``apex_agents.AgentSpec``)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["agent"] = "agent"
    name: str
    version: str = "0.1.0"
    practice: str
    persona: str
    service_codes: list[str]
    model_tier: ModelTier
    model_pin: str
    tools: list[ToolBinding] = Field(default_factory=list)
    hitl_gates: list[HITLGate] = Field(default_factory=list)
    kpis: list[KpiTarget] = Field(default_factory=list)
    oversight_modes: list[OversightMode] = Field(default_factory=list)
    description: str = ""
    archetype_id: str | None = None
    primary_contact: str = ""

    @field_validator("practice")
    @classmethod
    def _validate_practice(cls, v: str) -> str:
        if v.lower() not in PRACTICE_CODES:
            raise ValueError(f"practice must be one of {PRACTICE_CODES}, got {v!r}")
        return v.lower()

    def write_tools(self) -> list[ToolBinding]:
        """Tools that produce side effects."""
        return [t for t in self.tools if t.write]

    def has_hitl(self) -> bool:
        """True when the agent declares at least one HITL gate."""
        return len(self.hitl_gates) > 0


# ---------------------------------------------------------------------------
# loaders
# ---------------------------------------------------------------------------


def _load_yaml(path: str | Path) -> dict[str, object]:
    with Path(path).open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping, got {type(data).__name__}")
    return data


def load_scenario(path: str | Path) -> ScenarioManifest:
    """Parse a ``scenario.yaml`` manifest."""
    return ScenarioManifest.model_validate(_load_yaml(path))


def load_agent(path: str | Path) -> AgentManifest:
    """Parse an ``agents/{role}/agent.yaml`` manifest."""
    return AgentManifest.model_validate(_load_yaml(path))


def load_agent_spec(path: str | Path) -> AgentSpec:
    """Parse a ``catalog/agents/*.yaml`` catalog manifest."""
    return AgentSpec.model_validate(_load_yaml(path))


__all__ = [
    "PRACTICE_CODES",
    "AgentManifest",
    "AgentSpec",
    "ChainStep",
    "HITLGate",
    "KpiTarget",
    "ModelTier",
    "OversightMode",
    "ScenarioAgentRef",
    "ScenarioManifest",
    "ToolBinding",
    "load_agent",
    "load_agent_spec",
    "load_scenario",
]
