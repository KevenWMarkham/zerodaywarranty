"""3D process fly-through (three.js) generated from a live chain run.

A real-time WebGL companion to the (flat) Swim Lane Views: the 24-step
investigation laid out as a swim-lane grid in 3D — lanes as parallel rails,
phases as glass gates, steps as nodes — with a glowing **trace** that flows
through the steps in execution order, lighting each lane as it passes.

Like the rest of the design pack, the geometry and the on-screen figures are
**generated from an actual** :class:`~zero_day_warranty.chain.ChainResult`
(:func:`build_process_graph`), so the scene stays truthful to the running chain.
:func:`render_process_3d_html` emits a self-contained HTML page that loads
three.js via an ES-module import map (no build step) and embeds the graph inline.
"""

from __future__ import annotations

import json
from typing import Any

from zero_day_warranty.chain import STEP_CATALOG, ChainResult, WarrantyRootCauseChain
from zero_day_warranty.lanes import LANE_SPECS, PHASES, _summarize
from zero_day_warranty.synthetic import generate

THREE_VERSION = "0.160.0"

#: Operational lanes that get a 3D rail, in display order, with a distinct hue
#: drawn from the design-system palette. ``governance`` is the audit *floor*
#: (under every step), not a rail, so it is handled separately.
RAIL_LANES: tuple[tuple[str, str], ...] = (
    ("consumption", "#2EA0E6"),
    ("dataplane", "#0078D4"),
    ("orchestration", "#5B8DEF"),
    ("analytics", "#76B900"),
    ("hitl", "#B85450"),
    ("downstream", "#D97706"),
    ("day0", "#5C9300"),
)
GOVERNANCE_HEX = "#334155"

#: The lane that *leads* each step — where the trace sits and the node is placed.
#: Chosen to tell the story as a flowing arc (signal → join → science →
#: hypothesis → action → human gate → audit → value), faithful to the chain.
PRIMARY_LANE: dict[int, str] = {
    1: "consumption",
    2: "orchestration",
    3: "dataplane",
    4: "dataplane",
    5: "dataplane",
    6: "dataplane",
    7: "dataplane",
    8: "analytics",
    9: "dataplane",
    10: "analytics",
    11: "dataplane",
    12: "analytics",
    13: "dataplane",
    14: "analytics",
    15: "analytics",
    16: "analytics",
    17: "analytics",
    18: "orchestration",
    19: "dataplane",
    20: "downstream",
    21: "downstream",
    22: "hitl",
    23: "orchestration",
    24: "consumption",
}

# layout constants (world units)
_STEP_DX = 2.4
_LANE_DZ = 3.4
_NODE_Y = 0.6

#: Real-to-life equipment model shown for each step (built from primitives in the
#: scene), chosen to match what the step actually does.
STEP_EQUIPMENT: dict[int, str] = {
    1: "monitor",  # warranty-cost dashboard raises the signal
    2: "monitor",  # scope the cohort on the dashboard
    3: "database",  # pull VINs
    4: "database",  # join build records
    5: "database",  # build-week distribution
    6: "magnifier",  # find over-represented weeks
    7: "tool",  # station / tool distribution
    8: "magnifier",  # statistical interaction test
    9: "camera",  # quality / inline inspection events
    10: "magnifier",  # SPC anomalies
    11: "database",  # join telemetry
    12: "tool",  # tool calibration drift
    13: "database",  # supplier lot codes
    14: "magnifier",  # lot warranty rate
    15: "magnifier",  # lot significance
    16: "magnifier",  # rank interactions
    17: "document",  # root-cause hypothesis
    18: "document",  # evidence package
    19: "document",  # chargeback exposure
    20: "document",  # chargeback documentation
    21: "shield",  # NHTSA EWR check
    22: "approver",  # HITL review
    23: "shield",  # audit-ledger write
    24: "monitor",  # notify downstream / KPI rollup
}

#: A plain-language description of what happens at each step (shown in the HUD).
STEP_DETAIL: dict[int, str] = {
    1: "A warranty-cost dashboard trips a cluster-threshold alert — a brake-actuator failure mode is trending across connected vehicles.",
    2: "The agent scopes the claim cohort by part number, failure mode, and severity to define exactly which claims to investigate.",
    3: "It resolves the cohort to a concrete VIN list through the warranty MCP tool.",
    4: "Each VIN is joined to its factory build record in the Fabric Gold view — the per-VIN spine of the whole investigation.",
    5: "The build-week distribution of the affected VINs is extracted to see when the suspect cars were made.",
    6: "Build weeks that are over-represented versus baseline production are flagged as the 'hot' weeks.",
    7: "Within the hot weeks the cohort is broken down by assembly station, tool, and shift.",
    8: "A two-proportion z-test checks whether the claim rate at the hot station is significantly above the rest.",
    9: "Quality-event records (inline inspection results) are joined in for the hot population.",
    10: "SPC anomalies at the hot station preceding the hot build weeks are counted.",
    11: "Assembly telemetry traces are joined to bring in the tool readings.",
    12: "The agent correlates tool calibration drift with the defects at the hot station.",
    13: "Supplier lot codes present in the hot VIN population are extracted.",
    14: "The warranty rate for the suspect supplier lot is computed against the baseline rate.",
    15: "A significance test confirms the supplier-lot attribution is real, not noise.",
    16: "Cohort × station × supplier-lot interactions are ranked to isolate the strongest signal.",
    17: "A root-cause hypothesis is generated with a confidence interval.",
    18: "The full evidence package is assembled — cohort, statistical tests, and raw supporting data.",
    19: "Chargeback dollar exposure attributable to the supplier lot is computed.",
    20: "Supplier chargeback documentation is drafted from the evidence.",
    21: "A compliance check evaluates NHTSA Early Warning Reporting (49 CFR 579) applicability.",
    22: "The evidence package is routed to the Quality Director as a Teams Adaptive Card — the single human approval gate.",
    23: "The decision and rationale are sealed to the hash-chained audit ledger.",
    24: "Downstream owners — CAPA, supplier quality, dealer advisories — are notified and the KPIs roll up.",
}


def _x(step: int) -> float:
    return round((step - 1) * _STEP_DX - (23 * _STEP_DX) / 2, 3)


def _phase_of(step: int) -> str:
    for name, lo, hi in PHASES:
        if lo <= step <= hi:
            return name
    return "—"


def _lanes_of(step: int) -> list[str]:
    """All rail lanes whose capability set includes this step (for highlight)."""
    out: list[str] = []
    for spec in LANE_SPECS:
        lane_id, steps = spec[0], spec[9]
        if lane_id == "governance":
            continue
        if step in steps:
            out.append(lane_id)
    return out


def build_process_graph(result: ChainResult) -> dict[str, Any]:
    """Lay out the 24-step chain as a 3D swim-lane graph with live figures."""
    fin = result.financials
    stats = result.evidence_package.get("statistics", {})

    lanes_z = {
        lane_id: round(i * _LANE_DZ - (len(RAIL_LANES) - 1) * _LANE_DZ / 2, 3)
        for i, (lane_id, _hex) in enumerate(RAIL_LANES)
    }
    lane_name = {spec[0]: spec[1] for spec in LANE_SPECS}

    lanes = [
        {
            "id": lane_id,
            "name": lane_name.get(lane_id, lane_id),
            "color": hex_,
            "z": lanes_z[lane_id],
        }
        for lane_id, hex_ in RAIL_LANES
    ]

    phases = []
    for name, lo, hi in PHASES:
        x0 = _x(lo) - _STEP_DX / 2
        x1 = _x(hi) + _STEP_DX / 2
        phases.append(
            {
                "name": name,
                "x0": round(x0, 3),
                "x1": round(x1, 3),
                "xc": round((x0 + x1) / 2, 3),
                "lo": lo,
                "hi": hi,
            }
        )

    rows = {row["decision_output"]["step"]: row for row in result.ledger.rows()}
    steps: list[dict[str, Any]] = []
    path: list[list[float]] = []
    for n in range(1, 25):
        _, _key, cluster, _role, title = STEP_CATALOG[n - 1]
        primary = PRIMARY_LANE[n]
        z = lanes_z[primary]
        x = _x(n)
        row = rows.get(n)
        summary = _summarize(row["decision_output"]) if row else ""
        steps.append(
            {
                "n": n,
                "title": title,
                "summary": summary,
                "cluster": cluster,
                "phase": _phase_of(n),
                "primaryLane": primary,
                "lanes": _lanes_of(n),
                "tools": list(row["tools_called"]) if row else [],
                "sealed": row is not None,
                "equip": STEP_EQUIPMENT.get(n, "monitor"),
                "detail": STEP_DETAIL.get(n, ""),
                "confidence": row.get("confidence_score") if row else None,
                "x": x,
                "z": z,
            }
        )
        path.append([x, _NODE_Y, z])

    return {
        "meta": {
            "trace_id": result.trace_id,
            "suspect_lot": result.suspect_lot,
            "hot_station": result.hot_station,
            "hot_tool": result.hot_tool,
            "hot_weeks": result.affected_weeks,
            "confidence": result.confidence,
            "rate_ratio": stats.get("rate_ratio"),
            "p_value": stats.get("p_value"),
            "attributable_usd": round(fin.attributable_usd, 2),
            "agentic_recovery_usd": round(fin.agentic_recovery_usd, 2),
            "manual_recovery_usd": round(fin.manual_recovery_usd, 2),
            "improvement_pct": round(fin.improvement_pct, 1),
            "ledger_rows": len(result.ledger),
            "verified": result.ledger.verify_chain(),
        },
        "governanceColor": GOVERNANCE_HEX,
        "phases": phases,
        "lanes": lanes,
        "steps": steps,
        "path": path,
    }


def render_process_3d_html(result: ChainResult | None = None) -> str:
    """Render the self-contained three.js process fly-through page."""
    if result is None:
        result = WarrantyRootCauseChain(generate().medallion).run()
    graph = build_process_graph(result)
    graph_json = json.dumps(graph, separators=(",", ":"))
    return _HTML_TEMPLATE.replace("__THREE_VERSION__", THREE_VERSION).replace(
        "__GRAPH_JSON__", graph_json
    )


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Zero Day Warranty · 3D Process Fly-Through</title>
<link href="https://fonts.googleapis.com/css2?family=Aptos:wght@400;600;700&family=Cascadia+Mono&display=swap" rel="stylesheet">
<style>
  :root{ --navy:#1A2339; --ms:#0078D4; --slate:#94A3B8; --border:#2A3349; }
  *{box-sizing:border-box;} html,body{margin:0;height:100%;}
  body{background:#0b1020;color:#e5e7eb;font-family:Aptos,system-ui,sans-serif;overflow:hidden;}
  .classification{position:fixed;top:0;left:0;right:0;z-index:30;background:#D97706;color:#fff;
    padding:5px 16px;text-align:center;font-size:10px;letter-spacing:0.18em;text-transform:uppercase;font-weight:700;}
  #scene{position:fixed;inset:0;}
  .label{font-family:Aptos,sans-serif;font-weight:600;color:#cbd5e1;font-size:12px;
    text-shadow:0 1px 4px rgba(0,0,0,0.8);pointer-events:none;white-space:nowrap;}
  .label.phase{font-size:13px;color:#fff;letter-spacing:0.08em;text-transform:uppercase;}
  .label.lane{font-size:11px;color:#94A3B8;}
  /* HUD */
  #hud{position:fixed;left:18px;top:42px;z-index:20;width:330px;max-width:42vw;
    background:rgba(13,18,34,0.82);border:1px solid var(--border);border-radius:12px;
    padding:14px 16px;backdrop-filter:blur(8px);box-shadow:0 8px 30px rgba(0,0,0,0.4);}
  #hud h1{font-size:15px;margin:0 0 2px;color:#fff;}
  #hud .sub{font-size:11px;color:var(--slate);margin-bottom:10px;}
  .chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;}
  .chip{font-size:10.5px;font-family:"Cascadia Mono",monospace;background:#16203a;
    border:1px solid var(--border);border-radius:999px;padding:3px 9px;color:#cbd5e1;}
  .chip b{color:#fff;}
  .now{border-top:1px solid var(--border);padding-top:10px;}
  .now .ph{font-size:10px;text-transform:uppercase;letter-spacing:0.1em;color:var(--ms);font-weight:700;}
  .now .st{font-size:14px;color:#fff;font-weight:600;margin:3px 0;}
  .now .sm{font-size:11px;color:var(--slate);font-family:"Cascadia Mono",monospace;line-height:1.5;min-height:30px;}
  .now .seal{font-size:10px;color:#34d399;margin-top:4px;}
  .now .toportal{display:inline-block;margin-top:10px;font-size:12px;font-weight:700;
    color:#fff;text-decoration:none;background:var(--ms);padding:7px 12px;border-radius:8px;}
  .now .toportal:hover{background:#0a63ad;}
  /* controls */
  #ctl{position:fixed;left:50%;bottom:20px;transform:translateX(-50%);z-index:20;
    display:flex;align-items:center;gap:10px;background:rgba(13,18,34,0.86);
    border:1px solid var(--border);border-radius:999px;padding:8px 14px;backdrop-filter:blur(8px);}
  #ctl button{background:#16203a;border:1px solid var(--border);color:#e5e7eb;border-radius:8px;
    padding:7px 12px;font-family:Aptos,sans-serif;font-weight:600;font-size:12px;cursor:pointer;}
  #ctl button:hover{background:#1e2b4d;}
  #ctl button.primary{background:var(--ms);border-color:var(--ms);color:#fff;}
  #scrub{width:230px;accent-color:var(--ms);}
  #ctl .t{font-family:"Cascadia Mono",monospace;font-size:11px;color:var(--slate);min-width:54px;text-align:center;}
  #lanes{position:fixed;right:18px;top:42px;z-index:20;display:flex;flex-direction:column;gap:6px;}
  #lanes button{background:rgba(13,18,34,0.82);border:1px solid var(--border);color:#cbd5e1;
    border-radius:8px;padding:6px 10px;font-size:11px;font-weight:600;cursor:pointer;text-align:left;
    display:flex;align-items:center;gap:8px;backdrop-filter:blur(8px);}
  #lanes button:hover{border-color:var(--ms);color:#fff;}
  #lanes .dot{width:9px;height:9px;border-radius:50%;flex:none;}
  #lanes .all{justify-content:center;}
  .credit{position:fixed;right:14px;bottom:16px;z-index:20;font-size:10px;color:#64748b;}
  .credit a{color:#94A3B8;}
  /* bottom step-detail box */
  #detail{position:fixed;left:50%;transform:translateX(-50%);bottom:74px;z-index:21;width:min(940px,94vw);
    background:rgba(11,16,32,0.92);border:1px solid var(--border);border-left:5px solid var(--ms);
    border-radius:12px;padding:13px 18px;backdrop-filter:blur(10px);box-shadow:0 10px 34px rgba(0,0,0,0.5);}
  #detail .dt-top{display:flex;justify-content:space-between;align-items:baseline;gap:10px;}
  #detail .ph{font-family:Aptos,sans-serif;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#7cc4ff;}
  #detail .lane{font-family:Aptos,sans-serif;font-size:11px;font-weight:700;color:var(--slate);}
  #detail h2{font-family:Aptos,sans-serif;font-size:18px;color:#fff;margin:4px 0 6px;}
  #detail .desc{font-size:13.5px;color:#dbe4f0;line-height:1.55;margin:0;}
  #detail .facts{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px;align-items:center;}
  #detail .f{font-family:"Cascadia Mono",monospace;font-size:11px;background:#16203a;border:1px solid var(--border);
    border-radius:999px;padding:3px 9px;color:#cbd5e1;}
  #detail .f:empty{display:none;}
  #detail .f.seal{color:#34d399;border-color:#1f5c43;}
  #detail .toportal{margin-left:auto;font-family:Aptos,sans-serif;font-size:12px;font-weight:700;color:#fff;
    text-decoration:none;background:var(--ms);padding:7px 12px;border-radius:8px;}
  #detail .toportal:hover{background:#0a63ad;}
  #fallback{position:fixed;inset:0;z-index:40;display:none;align-items:center;justify-content:center;
    background:#0b1020;text-align:center;padding:40px;}
  #fallback div{max-width:520px;color:#cbd5e1;}
  @media (max-width:760px){ #hud{display:none;} #lanes{display:none;} #scrub{width:120px;} }
</style>
</head>
<body>
<div class="classification">Reference · 3D process fly-through · Generated from a live chain run · Synthetic figures</div>
<div id="scene"></div>

<div id="hud">
  <h1>Zero Day Warranty — process</h1>
  <div class="sub">One investigation, flowing through the swim lanes.</div>
  <div class="chips">
    <span class="chip">lot <b id="m-lot">—</b></span>
    <span class="chip">rate <b id="m-rate">—</b></span>
    <span class="chip">p <b id="m-p">—</b></span>
    <span class="chip">exposure <b id="m-exp">—</b></span>
    <span class="chip">recovery <b id="m-rec">—</b></span>
    <span class="chip">audit <b id="m-rows">—</b></span>
  </div>
</div>

<div id="lanes"></div>

<div id="detail">
  <div class="dt-top">
    <span class="ph"><span id="n-phase">Detect</span> · step <span id="n-step">1</span>/24</span>
    <span class="lane" id="n-lane">—</span>
  </div>
  <h2 id="n-title">—</h2>
  <p class="desc" id="n-desc">—</p>
  <div class="facts">
    <span class="f" id="n-sum"></span>
    <span class="f" id="n-conf"></span>
    <span class="f" id="n-tools"></span>
    <span class="f seal" id="n-seal"></span>
    <a class="toportal" id="n-portal" href="ZeroDayWarranty_SwimLane_Views.html">Open lane in portal ›</a>
  </div>
</div>

<div id="ctl">
  <button id="play" class="primary">⏸ Pause</button>
  <button id="restart">↺</button>
  <input id="scrub" type="range" min="0" max="1000" value="0">
  <span class="t" id="time">0%</span>
  <button id="speed">0.5×</button>
  <button id="orbit">Free orbit</button>
</div>

<div class="credit">three.js r__THREE_VERSION__ · <a href="ZeroDayWarranty_SwimLane_Views.html">flat swim lanes ›</a></div>

<div id="fallback"><div>
  <h2>3D view needs WebGL</h2>
  <p>Your browser/session can't render WebGL. The same investigation is available
  as the flat <a href="ZeroDayWarranty_SwimLane_Views.html">Swim Lane Views</a>.</p>
</div></div>

<script id="graph" type="application/json">__GRAPH_JSON__</script>

<script type="importmap">
{ "imports": {
  "three": "./vendor/three@__THREE_VERSION__/build/three.module.js",
  "three/addons/": "./vendor/three@__THREE_VERSION__/examples/jsm/"
}}
</script>

<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const GRAPH = JSON.parse(document.getElementById('graph').textContent);

// ---- WebGL guard ---------------------------------------------------------
function hasWebGL(){ try { const c=document.createElement('canvas');
  return !!(window.WebGLRenderingContext && (c.getContext('webgl2')||c.getContext('webgl'))); }
  catch(e){ return false; } }
if(!hasWebGL()){ document.getElementById('fallback').style.display='flex'; throw new Error('no webgl'); }

// ---- meta chips ----------------------------------------------------------
const M = GRAPH.meta;
const usd = v => '$'+Math.round(v).toLocaleString();
document.getElementById('m-lot').textContent  = M.suspect_lot;
document.getElementById('m-rate').textContent = (M.rate_ratio??'—')+'×';
document.getElementById('m-p').textContent    = (M.p_value!=null? M.p_value.toExponential(0): '—');
document.getElementById('m-exp').textContent  = usd(M.attributable_usd);
document.getElementById('m-rec').textContent  = usd(M.agentic_recovery_usd);
document.getElementById('m-rows').textContent = M.ledger_rows+(M.verified?' ✓':'');

// ---- renderer / scene ----------------------------------------------------
const host = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ antialias:true, powerPreference:'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
host.appendChild(renderer.domElement);

const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(innerWidth, innerHeight);
labelRenderer.domElement.style.position='fixed';
labelRenderer.domElement.style.top='0';
labelRenderer.domElement.style.pointerEvents='none';
host.appendChild(labelRenderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color('#0b1020');
scene.fog = new THREE.Fog('#0b1020', 55, 130);

const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

const camera = new THREE.PerspectiveCamera(46, innerWidth/innerHeight, 0.1, 500);
camera.position.set(-34, 26, 34);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = 0.06;
controls.maxPolarAngle = Math.PI*0.49; controls.minDistance = 12; controls.maxDistance = 110;
controls.target.set(0, 1, 0);
let userOrbit = false;
controls.addEventListener('start', ()=>{ userOrbit = true; });

// ---- lighting ------------------------------------------------------------
scene.add(new THREE.HemisphereLight('#8fb7ff', '#0a0f1e', 0.55));
const key = new THREE.DirectionalLight('#ffffff', 2.1);
key.position.set(22, 38, 18); key.castShadow = true;
key.shadow.mapSize.set(2048,2048);
key.shadow.camera.near=1; key.shadow.camera.far=140;
const sc=44; Object.assign(key.shadow.camera,{left:-sc,right:sc,top:sc,bottom:-sc});
key.shadow.bias=-0.0002; scene.add(key);

// ---- governance floor (the audit foundation) -----------------------------
const floorGeo = new THREE.PlaneGeometry(120, 60);
const floorMat = new THREE.MeshStandardMaterial({ color:'#0d1426', metalness:0.85, roughness:0.18 });
const floor = new THREE.Mesh(floorGeo, floorMat);
floor.rotation.x = -Math.PI/2; floor.position.y = 0; floor.receiveShadow = true;
scene.add(floor);
const grid = new THREE.GridHelper(120, 60, GRAPH.governanceColor, '#13203a');
grid.material.opacity = 0.25; grid.material.transparent = true; grid.position.y = 0.01;
scene.add(grid);
// glowing audit slab that pulses when the trace seals a row
const slabMat = new THREE.MeshStandardMaterial({ color:GRAPH.governanceColor, emissive:GRAPH.governanceColor,
  emissiveIntensity:0.0, metalness:0.6, roughness:0.4, transparent:true, opacity:0.5 });
const slab = new THREE.Mesh(new THREE.BoxGeometry(110, 0.12, 26), slabMat);
slab.position.y = 0.02; scene.add(slab);
addLabel('Governance Foundation · hash-chained audit', 0, 0.2, 14.5, 'phase');

// ---- helpers -------------------------------------------------------------
function addLabel(text, x, y, z, cls){
  const d=document.createElement('div'); d.className='label '+(cls||''); d.textContent=text;
  const o=new CSS2DObject(d); o.position.set(x,y,z); scene.add(o); return o;
}
function colorOf(id){ const l=GRAPH.lanes.find(l=>l.id===id); return l? l.color : '#0078D4'; }

// ---- lane rails ----------------------------------------------------------
const minX = GRAPH.phases[0].x0, maxX = GRAPH.phases[GRAPH.phases.length-1].x1;
const railLen = (maxX-minX)+3;
const railMeshes = {};
GRAPH.lanes.forEach(l=>{
  const mat = new THREE.MeshStandardMaterial({ color:l.color, metalness:0.95, roughness:0.35,
    emissive:l.color, emissiveIntensity:0.04 });
  const rail = new THREE.Mesh(new THREE.CylinderGeometry(0.16,0.16,railLen,20), mat);
  rail.rotation.z = Math.PI/2; rail.position.set((minX+maxX)/2, 0.18, l.z);
  rail.castShadow = true; scene.add(rail);
  railMeshes[l.id] = rail;
  addLabel(l.name, minX-2.2, 0.7, l.z, 'lane');
});

// ---- phase gates (frosted glass) + labels --------------------------------
const laneZ = GRAPH.lanes.map(l=>l.z);
const zSpan = Math.max(...laneZ)-Math.min(...laneZ);
GRAPH.phases.forEach(p=>{
  const glass = new THREE.MeshPhysicalMaterial({ color:'#bcd4ff', metalness:0, roughness:0.08,
    transmission:0.92, thickness:0.6, transparent:true, opacity:0.5, ior:1.3 });
  const panel = new THREE.Mesh(new RoundedBoxGeometry(0.12, 6.4, zSpan+5, 4, 0.05), glass);
  panel.position.set(p.x0, 3.2, 0); scene.add(panel);
  addLabel(p.name, p.xc, 6.4, 0, 'phase');
});
// close the last gate
(()=>{ const p=GRAPH.phases[GRAPH.phases.length-1];
  const glass=new THREE.MeshPhysicalMaterial({color:'#bcd4ff',metalness:0,roughness:0.08,
    transmission:0.92,thickness:0.6,transparent:true,opacity:0.5,ior:1.3});
  const panel=new THREE.Mesh(new RoundedBoxGeometry(0.12,6.4,zSpan+5,4,0.05),glass);
  panel.position.set(p.x1,3.2,0); scene.add(panel); })();

// ---- step equipment (real-to-life models built from primitives) ----------
const NODE_Y = 0.6;
const EQUIP_SCALE = 1.15;
const nodeMeshes = {};

const matBody = ()=> new THREE.MeshStandardMaterial({ color:'#3a4661', metalness:0.7, roughness:0.45 });
const matMetal = ()=> new THREE.MeshStandardMaterial({ color:'#c7d2e0', metalness:0.9, roughness:0.32 });
const matPaper = ()=> new THREE.MeshStandardMaterial({ color:'#eef2f7', metalness:0.05, roughness:0.7 });
const matSkin = ()=> new THREE.MeshStandardMaterial({ color:'#e9c6a8', metalness:0.05, roughness:0.6 });
const matGlass = ()=> new THREE.MeshPhysicalMaterial({ color:'#cfe7ff', metalness:0, roughness:0.08,
  transmission:0.9, thickness:0.4, transparent:true, opacity:0.6 });

function buildEquip(type, color){
  const g = new THREE.Group();
  const accent = [];
  const acc = ()=>{ const m = new THREE.MeshStandardMaterial({ color:color, metalness:0.45,
    roughness:0.3, emissive:color, emissiveIntensity:0.12 }); accent.push(m); return m; };
  const add = (geo, mat, p, r)=>{ const m=new THREE.Mesh(geo,mat);
    if(p) m.position.set(p[0],p[1],p[2]); if(r) m.rotation.set(r[0],r[1],r[2]);
    m.castShadow=true; m.receiveShadow=true; g.add(m); return m; };
  const H = Math.PI/2;

  if(type==='monitor'){
    add(new RoundedBoxGeometry(1.0,0.7,0.08,3,0.03), matBody(), [0,0.2,0]);
    add(new THREE.PlaneGeometry(0.84,0.54), acc(), [0,0.2,0.045]);
    add(new THREE.CylinderGeometry(0.04,0.04,0.28,12), matMetal(), [0,-0.1,0]);
    add(new THREE.CylinderGeometry(0.24,0.24,0.05,24), matMetal(), [0,-0.26,0]);
  } else if(type==='database'){
    for(let i=0;i<3;i++){
      add(new THREE.CylinderGeometry(0.34,0.34,0.16,28), i===0?acc():matBody(), [0,-0.3+i*0.3,0]);
      add(new THREE.TorusGeometry(0.34,0.018,8,28), acc(), [0,-0.22+i*0.3,0], [H,0,0]);
    }
  } else if(type==='magnifier'){
    add(new THREE.TorusGeometry(0.3,0.07,16,32), acc(), [0,0.15,0]);
    add(new THREE.CircleGeometry(0.26,32), matGlass(), [0,0.15,0.001]);
    add(new THREE.CylinderGeometry(0.05,0.05,0.5,12), matMetal(), [0.28,-0.18,0], [0,0,-0.7]);
  } else if(type==='tool'){
    add(new THREE.CylinderGeometry(0.13,0.13,0.7,20), matBody(), [0.05,0.12,0], [0,0,H]);
    add(new THREE.CylinderGeometry(0.16,0.16,0.22,24), acc(), [0.45,0.12,0], [0,0,H]);
    add(new THREE.CylinderGeometry(0.09,0.11,0.5,16), matBody(), [-0.18,-0.16,0]);
    add(new THREE.BoxGeometry(0.1,0.12,0.16), acc(), [-0.03,-0.02,0]);
  } else if(type==='camera'){
    add(new RoundedBoxGeometry(0.5,0.42,0.5,2,0.05), matBody(), [0,0.12,0]);
    add(new THREE.CylinderGeometry(0.17,0.2,0.28,24), matMetal(), [0,0.12,0.3], [H,0,0]);
    add(new THREE.CylinderGeometry(0.12,0.12,0.05,24), acc(), [0,0.12,0.46], [H,0,0]);
    add(new THREE.CylinderGeometry(0.03,0.03,0.34,8), matMetal(), [0,-0.22,0]);
  } else if(type==='document'){
    for(let i=0;i<3;i++) add(new RoundedBoxGeometry(0.55,0.03,0.72,2,0.01), matPaper(), [i*0.04-0.04,i*0.06-0.05,i*0.03]);
    for(let i=0;i<3;i++) add(new THREE.BoxGeometry(0.36,0.012,0.04), acc(), [0,0.14,-0.18+i*0.15]);
  } else if(type==='approver'){
    add(new THREE.SphereGeometry(0.16,20,16), matSkin(), [0,0.34,0]);
    add(new THREE.CylinderGeometry(0.18,0.26,0.5,20), acc(), [0,0.0,0]);
    add(new RoundedBoxGeometry(0.42,0.3,0.03,2,0.01), matPaper(), [0,0.12,0.34]);
    add(new THREE.BoxGeometry(0.14,0.02,0.02), acc(), [0,0.08,0.36]);
  } else if(type==='shield'){
    add(new RoundedBoxGeometry(0.6,0.55,0.12,4,0.05), acc(), [0,0.2,0]);
    add(new THREE.ConeGeometry(0.42,0.42,4), acc(), [0,-0.2,0], [Math.PI,Math.PI/4,0]);
    const chk = matPaper();
    add(new THREE.BoxGeometry(0.06,0.18,0.06), chk, [-0.07,0.14,0.09], [0,0,0.6]);
    add(new THREE.BoxGeometry(0.06,0.32,0.06), chk, [0.1,0.2,0.09], [0,0,-0.5]);
  } else {
    add(new RoundedBoxGeometry(0.8,0.8,0.8,4,0.12), acc());
  }
  g.userData.accent = accent;
  return g;
}

GRAPH.steps.forEach(s=>{
  const g = buildEquip(s.equip, colorOf(s.primaryLane));
  g.scale.setScalar(EQUIP_SCALE);
  g.position.set(s.x, NODE_Y, s.z);
  g.userData.step = s;
  scene.add(g); nodeMeshes[s.n] = g;
  const num = addLabel(String(s.n), s.x, NODE_Y+1.3, s.z, 'lane');
  num.element.style.fontFamily='Cascadia Mono, monospace';
});

// flow tube through the path (execution order)
const curvePts = GRAPH.path.map(p=>new THREE.Vector3(p[0],p[1],p[2]));
const curve = new THREE.CatmullRomCurve3(curvePts, false, 'catmullrom', 0.4);
const tube = new THREE.Mesh(
  new THREE.TubeGeometry(curve, 400, 0.05, 8, false),
  new THREE.MeshStandardMaterial({ color:'#3b4a6b', emissive:'#1b2d4d', emissiveIntensity:0.2,
    metalness:0.4, roughness:0.6, transparent:true, opacity:0.55 }));
scene.add(tube);

// ---- the trace orb -------------------------------------------------------
const orb = new THREE.Mesh(new THREE.SphereGeometry(0.26, 24, 24),
  new THREE.MeshStandardMaterial({ color:'#ffffff', emissive:'#8fd0ff', emissiveIntensity:1.6,
    metalness:0.2, roughness:0.2 }));
orb.castShadow = true; scene.add(orb);
const orbLight = new THREE.PointLight('#9bd0ff', 3, 16, 2); scene.add(orbLight);

// pulsing ground ring that marks the equipment currently being worked
const ringMat = new THREE.MeshBasicMaterial({ color:'#7cc4ff', transparent:true, opacity:0.5,
  side:THREE.DoubleSide });
const activeRing = new THREE.Mesh(new THREE.RingGeometry(0.85,1.15,48), ringMat);
activeRing.rotation.x = -Math.PI/2; activeRing.position.y = 0.04; scene.add(activeRing);

// ---- post-processing: bloom for the glow ---------------------------------
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.35, 0.25, 0.9);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// ---- lane focus buttons + deep-link --------------------------------------
const lanesBox = document.getElementById('lanes');
GRAPH.lanes.forEach(l=>{
  const b=document.createElement('button');
  b.innerHTML='<span class="dot" style="background:'+l.color+'"></span>'+l.name;
  b.onclick=()=>focusLane(l.id); lanesBox.appendChild(b);
});
const allBtn=document.createElement('button'); allBtn.className='all'; allBtn.textContent='Overview';
allBtn.onclick=()=>{ focusLaneId=null; userOrbit=false; }; lanesBox.appendChild(allBtn);

let focusLaneId = null;
function focusLane(id){ focusLaneId=id; userOrbit=false;
  // jump the timeline to that lane's first step
  const first = GRAPH.steps.find(s=>s.primaryLane===id || s.lanes.includes(id));
  if(first){ progress = first.n-1; } playing = true; setPlay();
}

// ---- animation -----------------------------------------------------------
const N = GRAPH.steps.length;
let progress = 0;          // 0 .. N-1
let playing = true;
let speed = 0.5;           // steps per second (default 0.5× — slower)
const SPEEDS=[0.5,1,2,4];
const clock = new THREE.Clock();

const playBtn=document.getElementById('play');
const scrub=document.getElementById('scrub');
const timeEl=document.getElementById('time');
function setPlay(){ playBtn.textContent = playing?'⏸ Pause':'▶ Play'; playBtn.classList.toggle('primary',playing); }
playBtn.onclick=()=>{ playing=!playing; setPlay(); };
document.getElementById('restart').onclick=()=>{ progress=0; playing=true; setPlay(); };
document.getElementById('speed').onclick=(e)=>{ const i=(SPEEDS.indexOf(speed)+1)%SPEEDS.length;
  speed=SPEEDS[i]; e.target.textContent=speed+'×'; };
document.getElementById('orbit').onclick=()=>{ userOrbit=!userOrbit; focusLaneId=null; };
scrub.oninput=()=>{ progress=(scrub.value/1000)*(N-1); playing=false; setPlay(); };

let curStep=-1;
function updateNow(s){
  const lane = GRAPH.lanes.find(l=>l.id===s.primaryLane);
  const col = lane?lane.color:'#0078D4';
  document.getElementById('n-phase').textContent=s.phase;
  document.getElementById('n-step').textContent=s.n;
  const ln=document.getElementById('n-lane'); ln.textContent=lane?lane.name:''; ln.style.color=col;
  document.getElementById('n-title').textContent=s.title;
  document.getElementById('n-desc').textContent=s.detail||s.summary||'';
  document.getElementById('n-sum').textContent=s.summary||'';
  document.getElementById('n-conf').textContent=(s.confidence!=null)?('confidence '+Math.round(s.confidence*100)+'%'):'';
  document.getElementById('n-tools').textContent=(s.tools&&s.tools.length)?('tools: '+s.tools.join(', ')):'';
  document.getElementById('n-seal').textContent=s.sealed?'● sealed to audit ledger':'';
  document.getElementById('detail').style.borderLeftColor=col;
  const a=document.getElementById('n-portal');
  a.href='ZeroDayWarranty_SwimLane_Views.html#lane='+s.primaryLane;
  a.textContent='Open '+(lane?lane.name:'this lane')+' ›';
}

function emphasize(stepN){
  GRAPH.steps.forEach(s=>{
    const g=nodeMeshes[s.n]; const active = s.n===stepN; const passed = s.n<stepN;
    const target = active?0.85:(passed?0.28:0.05);
    (g.userData.accent||[]).forEach(mt=>{ mt.emissiveIntensity += (target-mt.emissiveIntensity)*0.2; });
    const sc = (active?1.28:1.0)*EQUIP_SCALE; g.scale.lerp(new THREE.Vector3(sc,sc,sc),0.18);
    g.rotation.y = active ? g.rotation.y + 0.01 : g.rotation.y * 0.96;
  });
  const cur = GRAPH.steps[stepN-1];
  for(const id in railMeshes){
    const on = cur && (cur.primaryLane===id || cur.lanes.includes(id));
    const t = on?0.28:0.03;
    railMeshes[id].material.emissiveIntensity += (t-railMeshes[id].material.emissiveIntensity)*0.15;
  }
}

const camTmp=new THREE.Vector3();
function tick(){
  const dt=Math.min(clock.getDelta(),0.05);
  if(playing){ progress += speed*dt; if(progress>=N-1){ progress=N-1; playing=false; setPlay(); } }
  const t = N>1 ? progress/(N-1) : 0;
  const pos = curve.getPoint(t);
  orb.position.copy(pos); orbLight.position.copy(pos).y+=1.0;
  orb.position.y += Math.sin(performance.now()*0.005)*0.04;
  // strobe — the small bright marker pulses fast to read as the active head
  const strobe = 0.5 + 0.5*Math.sin(performance.now()*0.018);  // ~3 Hz
  orb.material.emissiveIntensity = 1.3 + strobe*2.7;
  orbLight.intensity = 2.2 + strobe*4.5;
  orb.scale.setScalar(0.8 + strobe*0.3);

  const stepN = Math.min(N, Math.floor(progress)+1);
  if(stepN!==curStep){ curStep=stepN; updateNow(GRAPH.steps[stepN-1]); }
  emphasize(stepN);

  // move + pulse the ground ring under the equipment being worked
  const cs = GRAPH.steps[stepN-1];
  if(cs){
    activeRing.position.set(cs.x, 0.04, cs.z);
    ringMat.color.set(colorOf(cs.primaryLane));
    ringMat.opacity = 0.3 + 0.45*strobe;
    activeRing.scale.setScalar(1 + 0.18*strobe);
  }

  // governance slab pulses around the audit-write step (23)
  const dAudit = Math.abs(progress-(22));
  slab.material.emissiveIntensity += (((dAudit<1.2)?0.6:0.04)-slab.material.emissiveIntensity)*0.1;

  scrub.value = Math.round(t*1000); timeEl.textContent=Math.round(t*100)+'%';

  // camera: follow the trace unless the user grabbed orbit
  if(!userOrbit){
    let look = pos.clone();
    let want;
    if(focusLaneId){ const l=GRAPH.lanes.find(x=>x.id===focusLaneId);
      want = camTmp.set(pos.x-10, 11, l.z+13); look = new THREE.Vector3(pos.x, 1, l.z); }
    else { want = camTmp.set(pos.x-16, 18, 24); }
    camera.position.lerp(want, 0.025);
    controls.target.lerp(look, 0.05);
  }
  controls.update();
  composer.render();
  labelRenderer.render(scene, camera);
  requestAnimationFrame(tick);
}
setPlay(); tick();

// apply a ?#lane=<id> deep link now that timeline state exists
(function(){ const h=location.hash.match(/lane=([a-z0-9-]+)/i); if(h) focusLane(h[1]); })();
addEventListener('hashchange', ()=>{ const h=location.hash.match(/lane=([a-z0-9-]+)/i); if(h) focusLane(h[1]); });

addEventListener('resize', ()=>{
  camera.aspect=innerWidth/innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth,innerHeight); composer.setSize(innerWidth,innerHeight);
  labelRenderer.setSize(innerWidth,innerHeight);
});
</script>
</body>
</html>
"""


__all__ = [
    "GOVERNANCE_HEX",
    "PRIMARY_LANE",
    "RAIL_LANES",
    "THREE_VERSION",
    "build_process_graph",
    "render_process_3d_html",
]
