"""Agent console + audit-ledger views, generated from a live chain run.

Two operator-facing pages, both rendered from an actual
:class:`~zero_day_warranty.chain.ChainResult`:

- :func:`render_agent_console_html` — a "mission control" console: the
  orchestrator + the seven cluster agents, with the decision stream they produce
  played back step by step (which agent is running, what it decided, the tools it
  called, its confidence, the HITL gate).
- :func:`render_audit_ledger_html` — the APEX audit ledger: every sealed
  14-field row with its hash-chain link and HMAC-SHA256 signature, plus the live
  ``verify_chain`` result, so the process is regulator-replayable.

Both are self-contained HTML (no external assets) so the orchestrator can serve
them straight from Azure.
"""

from __future__ import annotations

import json
from html import escape
from typing import Any

from zero_day_warranty.chain import STEP_CATALOG, ChainResult, WarrantyRootCauseChain
from zero_day_warranty.lanes import _summarize
from zero_day_warranty.synthetic import generate

#: role -> (display name, cluster number, accent hex). Mirrors STEP_CATALOG roles.
ROLE_META: dict[str, tuple[str, int, str]] = {
    "detect": ("Detect & Scope", 1, "#2EA0E6"),
    "context": ("Build Context", 2, "#0078D4"),
    "stattest": ("Statistical Test", 3, "#76B900"),
    "quality": ("Quality & Telemetry", 4, "#5C9300"),
    "supplier": ("Supplier Attribution", 5, "#7C3AED"),
    "hypothesis": ("Hypothesis & Evidence", 6, "#0EA5E9"),
    "compliance": ("Compliance & HITL", 7, "#B85450"),
}
ORCHESTRATOR = ("Orchestrator", "Agent Framework · Foundry", "#94A3B8")


def _roles_in_order() -> list[str]:
    seen: list[str] = []
    for _step, _key, _cluster, role, _title in STEP_CATALOG:
        if role not in seen:
            seen.append(role)
    return seen


def build_console_graph(result: ChainResult) -> dict[str, Any]:
    """Agent roster + the ordered decision stream from a chain run."""
    rows = result.ledger.rows()
    by_step = {r["decision_output"]["step"]: r for r in rows}

    agents: list[dict[str, Any]] = [
        {
            "id": "apex.axle.agents.orchestrator",
            "role": "orchestrator",
            "name": ORCHESTRATOR[0],
            "platform": ORCHESTRATOR[1],
            "color": ORCHESTRATOR[2],
            "cluster": 0,
            "steps": list(range(1, len(STEP_CATALOG) + 1)),
        }
    ]
    for role in _roles_in_order():
        name, cluster, color = ROLE_META[role]
        steps = [s for s, _k, _c, r, _t in STEP_CATALOG if r == role]
        agents.append(
            {
                "id": f"apex.axle.agents.warranty-{role}",
                "role": role,
                "name": name,
                "platform": f"cluster {cluster}",
                "color": color,
                "cluster": cluster,
                "steps": steps,
            }
        )

    events: list[dict[str, Any]] = []
    for step, _key, cluster, role, title in STEP_CATALOG:
        r = by_step.get(step)
        out = r["decision_output"] if r else {}
        sealed_at = str(r.get("sealed_at", "")) if r else ""
        events.append(
            {
                "n": step,
                "role": role,
                "agent_id": r["agent_id"] if r else f"apex.axle.agents.warranty-{role}",
                "cluster": cluster,
                "title": title,
                "tools": list(r["tools_called"]) if r else [],
                "summary": _summarize(out) if out else "",
                "confidence": r.get("confidence_score") if r else None,
                "hitl": str(r.get("hitl_status", "none")) if r else "none",
                "time": sealed_at[11:19] if len(sealed_at) >= 19 else "",
                "sig": (str(r.get("signature", ""))[:10] + "…") if r else "",
            }
        )

    return {
        "meta": _meta(result),
        "agents": agents,
        "events": events,
    }


def _meta(result: ChainResult) -> dict[str, Any]:
    rows = result.ledger.rows()
    model = str(rows[0]["model_version"]) if rows else ""
    return {
        "trace_id": result.trace_id,
        "suspect_lot": result.suspect_lot,
        "confidence": result.confidence,
        "model_version": model,
        "ledger_rows": len(result.ledger),
        "verified": result.ledger.verify_chain(),
        "hitl_status": result.hitl_status.value,
    }


def build_ledger_view(result: ChainResult) -> dict[str, Any]:
    """The sealed audit rows + chain-verification metadata."""
    return {
        "meta": {
            **_meta(result),
            "algorithm": "HMAC-SHA256",
            "fields": 14,
            "signing": "Key Vault (prod) · dev key (this reference run)",
        },
        "rows": result.ledger.rows(),
    }


# --------------------------------------------------------------------------
# shared look

_CSS = """
  :root{ --navy:#1A2339; --navy2:#2A3349; --ms:#0078D4; --msd:#005A9E;
    --slate:#94A3B8; --line:#E5E7EB; --bg:#0b1020; --card:#121a30; --ok:#34d399; }
  *{box-sizing:border-box;} html,body{margin:0;}
  body{background:var(--bg);color:#e5e7eb;font-family:Aptos,system-ui,sans-serif;font-size:14px;line-height:1.5;}
  a{color:#7cc4ff;}
  .classification{background:#D97706;color:#fff;padding:5px 16px;text-align:center;font-size:10px;letter-spacing:0.18em;text-transform:uppercase;font-weight:700;}
  header.cover{padding:22px 28px;background:linear-gradient(135deg,var(--navy),var(--navy2));border-bottom:5px solid var(--ms);}
  header .eyebrow{font-size:11px;letter-spacing:0.28em;text-transform:uppercase;color:#7cc4ff;font-weight:700;}
  header h1{font-size:26px;margin:6px 0 2px;color:#fff;}
  header .sub{color:#cbd5e1;font-size:14px;margin-bottom:12px;}
  .chips{display:flex;flex-wrap:wrap;gap:8px;}
  .chip{font-family:"Cascadia Mono",monospace;font-size:11px;background:#16203a;border:1px solid var(--navy2);border-radius:999px;padding:4px 10px;color:#cbd5e1;}
  .chip b{color:#fff;} .chip.ok b{color:var(--ok);}
  main{max-width:1280px;margin:0 auto;padding:20px;}
  .links{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 16px;}
  .links a{font-weight:700;font-size:13px;text-decoration:none;padding:8px 14px;border-radius:8px;border:1px solid var(--ms);color:#7cc4ff;background:#0e1730;}
  .links a:hover{background:#13203f;}
"""


def _cover(
    eyebrow: str, title: str, sub: str, meta: dict[str, Any], *, extra_chips: str = ""
) -> str:
    ok = "ok" if meta["verified"] else ""
    verified = "VERIFIED" if meta["verified"] else "BROKEN"
    return f"""<div class="classification">Reference · Generated from a live chain run · Synthetic figures</div>
<header class="cover">
  <div class="eyebrow">{escape(eyebrow)}</div>
  <h1>{escape(title)}</h1>
  <div class="sub">{escape(sub)}</div>
  <div class="chips">
    <span class="chip">trace <b>{escape(meta["trace_id"])}</b></span>
    <span class="chip">suspect lot <b>{escape(meta["suspect_lot"])}</b></span>
    <span class="chip">model <b>{escape(meta["model_version"])}</b></span>
    <span class="chip">rows <b>{meta["ledger_rows"]}</b></span>
    <span class="chip {ok}">chain <b>{verified}</b></span>
    {extra_chips}
  </div>
</header>"""


_NAV = (
    '<div class="links">'
    '<a href="ZeroDayWarranty_Agent_Console.html">Agent console</a>'
    '<a href="ZeroDayWarranty_Audit_Ledger.html">Audit ledger</a>'
    '<a href="ZeroDayWarranty_SwimLane_Views.html">Swim lane views</a>'
    '<a href="ZeroDayWarranty_Process_3D.html">3D process</a>'
    "</div>"
)

_FONTS = (
    '<link href="https://fonts.googleapis.com/css2?family=Aptos:wght@400;600;700&'
    'family=Cascadia+Mono&display=swap" rel="stylesheet">'
)


# --------------------------------------------------------------------------
# agent console


def render_agent_console_html(result: ChainResult | None = None) -> str:
    """Render the agent console (roster + streamed decisions) page."""
    if result is None:
        result = WarrantyRootCauseChain(generate().medallion).run()
    graph = build_console_graph(result)
    data = json.dumps(graph, separators=(",", ":"))
    cover = _cover(
        "Operations · Agent Console",
        "Zero Day Warranty — agent console",
        "The orchestrator and seven cluster agents, and the decisions they make.",
        graph["meta"],
    )
    return (
        _CONSOLE_TEMPLATE.replace("__CSS__", _CSS)
        .replace("__FONTS__", _FONTS)
        .replace("__COVER__", cover)
        .replace("__NAV__", _NAV)
        .replace("__DATA__", data)
    )


_CONSOLE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Zero Day Warranty · Agent Console</title>
__FONTS__
<style>__CSS__
  .grid{display:grid;grid-template-columns:300px 1fr;gap:16px;}
  @media(max-width:820px){.grid{grid-template-columns:1fr;}}
  .roster{display:flex;flex-direction:column;gap:8px;}
  .agent{background:var(--card);border:1px solid var(--navy2);border-left:4px solid var(--ms);border-radius:10px;padding:10px 12px;opacity:0.6;transition:all .2s;}
  .agent.active{opacity:1;box-shadow:0 0 0 2px rgba(124,196,255,.4);}
  .agent.done{opacity:0.85;}
  .agent .nm{font-weight:700;color:#fff;font-size:14px;display:flex;justify-content:space-between;align-items:center;}
  .agent .id{font-family:"Cascadia Mono",monospace;font-size:10.5px;color:var(--slate);margin-top:2px;word-break:break-all;}
  .agent .st{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;padding:2px 7px;border-radius:999px;background:#1e2b4d;color:var(--slate);}
  .agent.active .st{background:#0e3a5e;color:#7cc4ff;} .agent.done .st{background:#0c3a2a;color:var(--ok);}
  .console{background:#070b16;border:1px solid var(--navy2);border-radius:10px;padding:14px;min-height:460px;font-family:"Cascadia Mono",monospace;font-size:12.5px;}
  .ln{padding:5px 0;border-bottom:1px dotted #1b2540;display:grid;grid-template-columns:64px 1fr;gap:10px;animation:fade .25s ease;}
  @keyframes fade{from{opacity:0;transform:translateY(4px);}to{opacity:1;}}
  .ln .tm{color:#5b6a8c;}
  .ln .ag{font-weight:700;}
  .ln .ti{color:#e5e7eb;}
  .ln .sm{color:#9fb3d1;}
  .ln .meta{color:#5b6a8c;font-size:11px;}
  .ln .hitl{color:#fbbf24;font-weight:700;}
  .ctl{display:flex;gap:10px;align-items:center;margin-top:14px;flex-wrap:wrap;}
  .ctl button{background:#16203a;border:1px solid var(--navy2);color:#e5e7eb;border-radius:8px;padding:8px 14px;font-weight:700;font-size:12px;cursor:pointer;}
  .ctl button.primary{background:var(--ms);border-color:var(--ms);color:#fff;}
  .ctl .prog{flex:1;height:6px;background:#16203a;border-radius:999px;overflow:hidden;min-width:120px;}
  .ctl .prog>div{height:100%;width:0;background:var(--ms);}
</style></head><body>
__COVER__
<main>
__NAV__
<div class="grid">
  <div class="roster" id="roster"></div>
  <div>
    <div class="console" id="console"></div>
    <div class="ctl">
      <button id="play" class="primary">⏸ Pause</button>
      <button id="step">Step ›</button>
      <button id="restart">↺ Restart</button>
      <button id="speed">1×</button>
      <span class="prog"><div id="bar"></div></span>
      <span id="count" class="meta">0/0</span>
    </div>
  </div>
</div>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const AGENTS = DATA.agents, EVENTS = DATA.events, N = EVENTS.length;
const roster = document.getElementById('roster');
const cards = {};
AGENTS.forEach(a=>{
  const d=document.createElement('div'); d.className='agent'; d.style.borderLeftColor=a.color;
  d.innerHTML='<div class="nm">'+a.name+' <span class="st">idle</span></div>'+
    '<div class="id">'+a.id+'</div>';
  roster.appendChild(d); cards[a.role]=d;
});
const consoleEl=document.getElementById('console');
const bar=document.getElementById('bar'), count=document.getElementById('count');
let idx=0, playing=true, speed=1, acc=0, last=performance.now();
const SPEEDS=[0.5,1,2,4];
function color(role){ const a=AGENTS.find(x=>x.role===role); return a?a.color:'#7cc4ff'; }
function reveal(){
  if(idx>=N) return false;
  const e=EVENTS[idx++];
  const ln=document.createElement('div'); ln.className='ln';
  const conf = e.confidence!=null ? ' · conf '+Math.round(e.confidence*100)+'%' : '';
  const hitl = (e.hitl && e.hitl!=='none') ? ' <span class="hitl">HITL: '+e.hitl+'</span>' : '';
  const tools = e.tools.length ? ' · '+e.tools.join(', ') : '';
  ln.innerHTML='<span class="tm">'+(e.time||('#'+e.n))+'</span>'+
    '<span><span class="ag" style="color:'+color(e.role)+'">'+e.agent_id.split(".").pop()+'</span> '+
    '<span class="meta">▸ step '+e.n+'</span> <span class="ti">'+e.title+'</span>'+hitl+
    '<div class="sm">'+(e.summary||'…')+'</div>'+
    '<div class="meta">'+e.sig+conf+tools+'</div></span>';
  consoleEl.appendChild(ln); consoleEl.scrollTop=consoleEl.scrollHeight;
  // agent status
  AGENTS.forEach(a=>{ cards[a.role].classList.remove('active'); });
  const c=cards[e.role]; if(c){ c.classList.add('active'); c.querySelector('.st').textContent='running'; }
  // mark agents whose steps are all done
  AGENTS.forEach(a=>{
    if(a.role==='orchestrator') return;
    const done = a.steps.every(s=> EVENTS.slice(0,idx).some(x=>x.n===s));
    if(done && a.role!==e.role){ cards[a.role].classList.add('done'); cards[a.role].classList.remove('active'); cards[a.role].querySelector('.st').textContent='done'; }
  });
  cards['orchestrator'].classList.add('active'); cards['orchestrator'].querySelector('.st').textContent='running';
  bar.style.width=(idx/N*100)+'%'; count.textContent=idx+'/'+N;
  if(idx>=N){ playing=false; setPlay(); cards['orchestrator'].classList.remove('active'); cards['orchestrator'].classList.add('done'); cards['orchestrator'].querySelector('.st').textContent='done'; }
  return true;
}
const playBtn=document.getElementById('play');
function setPlay(){ playBtn.textContent=playing?'⏸ Pause':'▶ Play'; playBtn.classList.toggle('primary',playing); }
playBtn.onclick=()=>{ if(idx>=N){ restart(); return;} playing=!playing; setPlay(); };
document.getElementById('step').onclick=()=>{ playing=false; setPlay(); reveal(); };
function restart(){ idx=0; consoleEl.innerHTML=''; playing=true; setPlay();
  AGENTS.forEach(a=>{ cards[a.role].className='agent'; cards[a.role].style.borderLeftColor=a.color; cards[a.role].querySelector('.st').textContent='idle'; }); }
document.getElementById('restart').onclick=restart;
document.getElementById('speed').onclick=e=>{ speed=SPEEDS[(SPEEDS.indexOf(speed)+1)%SPEEDS.length]; e.target.textContent=speed+'×'; };
setPlay();
function loop(now){ const dt=(now-last)/1000; last=now; if(playing){ acc+=dt*speed; while(acc>=0.7){ acc-=0.7; if(!reveal())break; } } requestAnimationFrame(loop); }
requestAnimationFrame(loop);
</script>
</body></html>
"""


# --------------------------------------------------------------------------
# audit ledger


def _short(s: Any, n: int = 12) -> str:
    t = str(s)
    return t if len(t) <= n else t[:n] + "…"


def render_audit_ledger_html(result: ChainResult | None = None) -> str:
    """Render the audit-ledger page (sealed rows + hash chain + verify state)."""
    if result is None:
        result = WarrantyRootCauseChain(generate().medallion).run()
    view = build_ledger_view(result)
    meta = view["meta"]

    body_rows: list[str] = []
    for i, r in enumerate(view["rows"]):
        out = r.get("decision_output", {})
        tools = ", ".join(r.get("tools_called", []) or [])
        conf = r.get("confidence_score")
        conf_s = f"{round(conf * 100)}%" if isinstance(conf, (int, float)) else "—"
        hitl = str(r.get("hitl_status", "none"))
        detail = json.dumps(r, indent=2, default=str)
        body_rows.append(
            f"""<tr class="row" data-i="{i}">
  <td class="mono">{out.get("step", i + 1)}</td>
  <td>{escape(str(out.get("title", "")))}</td>
  <td class="mono">{escape(_short(r.get("agent_id", ""), 34))}</td>
  <td class="mono">{escape(tools) or "—"}</td>
  <td class="mono">{conf_s}</td>
  <td><span class="hitl {hitl}">{escape(hitl)}</span></td>
  <td class="mono prev">{escape(_short(r.get("prev_link", ""), 12))}</td>
  <td class="mono sig">{escape(_short(r.get("signature", ""), 12))}</td>
</tr>
<tr class="detail" data-i="{i}"><td colspan="8"><pre>{escape(detail)}</pre></td></tr>"""
        )

    verified = "VERIFIED" if meta["verified"] else "BROKEN"
    extra = (
        f'<span class="chip">algo <b>{escape(meta["algorithm"])}</b></span>'
        f'<span class="chip">fields <b>{meta["fields"]}</b></span>'
    )
    cover = _cover(
        "Governance · Audit Ledger",
        "Zero Day Warranty — audit ledger",
        "Every agent decision sealed as a 14-field, hash-chained, signed row.",
        meta,
        extra_chips=extra,
    )
    return (
        _LEDGER_TEMPLATE.replace("__CSS__", _CSS)
        .replace("__FONTS__", _FONTS)
        .replace("__COVER__", cover)
        .replace("__NAV__", _NAV)
        .replace("__VERIFIED__", verified)
        .replace("__VCLASS__", "ok" if meta["verified"] else "bad")
        .replace("__SIGNING__", escape(str(meta["signing"])))
        .replace("__ROWS__", "\n".join(body_rows))
    )


_LEDGER_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Zero Day Warranty · Audit Ledger</title>
__FONTS__
<style>__CSS__
  .verify{display:flex;align-items:center;gap:12px;background:var(--card);border:1px solid var(--navy2);border-radius:10px;padding:12px 16px;margin:0 0 14px;}
  .verify .dot{width:12px;height:12px;border-radius:50%;}
  .verify.ok .dot{background:var(--ok);box-shadow:0 0 10px var(--ok);} .verify.bad .dot{background:#f87171;}
  .verify .big{font-weight:700;font-size:16px;color:#fff;} .verify .note{color:var(--slate);font-size:12px;}
  table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--navy2);border-radius:10px;overflow:hidden;}
  thead th{background:#0e1730;color:#cbd5e1;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;padding:9px 10px;border-bottom:1px solid var(--navy2);}
  tbody td{padding:8px 10px;border-bottom:1px solid #18223c;vertical-align:top;font-size:12.5px;}
  tr.row{cursor:pointer;} tr.row:hover{background:#16203a;}
  .mono{font-family:"Cascadia Mono",monospace;font-size:11.5px;}
  td.prev{color:#7c8db0;} td.sig{color:#7cc4ff;}
  .hitl{font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 7px;border-radius:999px;background:#1e2b4d;color:var(--slate);}
  .hitl.approved{background:#0c3a2a;color:var(--ok);} .hitl.pending{background:#3a2f0c;color:#fbbf24;}
  tr.detail{display:none;} tr.detail.open{display:table-row;}
  tr.detail pre{margin:0;background:#070b16;border:1px solid var(--navy2);border-radius:8px;padding:12px;color:#bcd; font-family:"Cascadia Mono",monospace;font-size:11px;overflow:auto;max-height:340px;}
  .hint{color:var(--slate);font-size:12px;margin:10px 2px;}
</style></head><body>
__COVER__
<main>
__NAV__
<div class="verify __VCLASS__"><span class="dot"></span>
  <div><div class="big">Hash chain __VERIFIED__</div>
  <div class="note">HMAC-SHA256 · each row links to the prior row's signature · signing key: __SIGNING__. Tamper any row and verification fails from that row forward.</div></div>
</div>
<p class="hint">Click any row to expand its full sealed 14-field record (the exact bytes APEX captures).</p>
<table>
  <thead><tr><th>Step</th><th>Decision</th><th>Agent</th><th>Tools</th><th>Conf</th><th>HITL</th><th>prev_link</th><th>signature</th></tr></thead>
  <tbody>
__ROWS__
  </tbody>
</table>
</main>
<script>
  document.querySelectorAll('tr.row').forEach(function(r){
    r.addEventListener('click', function(){
      var i=r.getAttribute('data-i');
      var d=document.querySelector('tr.detail[data-i="'+i+'"]');
      if(d) d.classList.toggle('open');
    });
  });
</script>
</body></html>
"""


__all__ = [
    "ROLE_META",
    "build_console_graph",
    "build_ledger_view",
    "render_agent_console_html",
    "render_audit_ledger_html",
]
