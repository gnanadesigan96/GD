"""
dashboard_page.py
The webapp's single HTML page: a Zoho-credentials form plus the trend
dashboard (reuses the same chart/interaction design as
zoho_trends/dashboard_template.py, adapted to fetch data via POST /tickets
instead of embedding it at build time). No external JS/CSS/CDN deps.
"""
from __future__ import annotations

from fetch import DEFAULT_DEPT_ID, DEFAULT_ORG_ID


def render() -> str:
    return _HTML.replace("__DEFAULT_ORG_ID__", DEFAULT_ORG_ID).replace("__DEFAULT_DEPT_ID__", DEFAULT_DEPT_ID)


_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Zoho Ticket Trend Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
  .viz-root {
    --page: #f9f9f7; --surface-1: #fcfcfb; --text-primary: #0b0b0b; --text-secondary: #52514e;
    --text-muted: #898781; --gridline: #e1e0d9; --baseline: #c3c2b7; --border: rgba(11,11,11,0.10);
    --good: #006300; --serious: #ec835a; --critical: #d03b3b;
    --series-1: #2a78d6; --series-2: #eb6834; --series-3: #1baf7a; --series-4: #eda100;
    --series-5: #e87ba4; --series-6: #008300; --series-7: #4a3aa7; --series-8: #e34948;
    --seq-100:#cde2fb; --seq-200:#9ec5f4; --seq-250:#86b6ef; --seq-350:#5598e7;
    --seq-400:#3987e5; --seq-500:#256abf; --seq-600:#184f95; --seq-650:#104281;
    min-height: 100vh; background: var(--page); color: var(--text-primary);
  }
  @media (prefers-color-scheme: dark) {
    :root:where(:not([data-theme="light"])) .viz-root {
      --page:#0d0d0d; --surface-1:#1a1a19; --text-primary:#ffffff; --text-secondary:#c3c2b7;
      --text-muted:#898781; --gridline:#2c2c2a; --baseline:#383835; --border: rgba(255,255,255,0.10);
      --good:#0ca30c; --series-1:#3987e5; --series-2:#d95926; --series-3:#199e70; --series-4:#c98500;
      --series-5:#d55181; --series-6:#008300; --series-7:#9085e9; --series-8:#e66767;
    }
  }
  :root[data-theme="dark"] .viz-root {
    --page:#0d0d0d; --surface-1:#1a1a19; --text-primary:#ffffff; --text-secondary:#c3c2b7;
    --text-muted:#898781; --gridline:#2c2c2a; --baseline:#383835; --border: rgba(255,255,255,0.10);
    --good:#0ca30c; --series-1:#3987e5; --series-2:#d95926; --series-3:#199e70; --series-4:#c98500;
    --series-5:#d55181; --series-6:#008300; --series-7:#9085e9; --series-8:#e66767;
  }
  .wrap { max-width: 1180px; margin: 0 auto; padding: 28px 20px 64px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .sub { color: var(--text-secondary); font-size: 13px; margin: 0 0 22px; line-height: 1.5; }
  .card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; margin-bottom: 18px; }
  .card h2 { font-size: 14px; margin: 0 0 2px; }
  .card .hint { font-size: 12px; color: var(--text-muted); margin: 0 0 14px; }

  /* Credentials card */
  .cred-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); gap: 10px; align-items: end; }
  .cred-field label { display:block; font-size: 11.5px; color: var(--text-secondary); margin-bottom: 4px; }
  .cred-field input, .cred-field select {
    width: 100%; font: inherit; font-size: 13px; padding: 7px 10px; border-radius: 8px;
    border: 1px solid var(--border); background: var(--page); color: var(--text-primary);
  }
  .cred-note { font-size: 11.5px; color: var(--text-muted); margin-top: 10px; line-height: 1.5; }
  .cred-error { font-size: 12.5px; color: var(--critical); margin-top: 8px; min-height: 1.2em; }
  #load-btn {
    font: inherit; font-size: 13px; padding: 8px 16px; border-radius: 8px; border: none;
    background: var(--series-1); color: #fff; cursor: pointer; white-space: nowrap;
  }
  #load-btn:disabled { opacity: 0.6; cursor: default; }
  #cred-card.collapsed .cred-grid, #cred-card.collapsed .cred-note { display: none; }
  #cred-card.collapsed { padding: 10px 20px; }
  .cred-summary { display: none; font-size: 12.5px; color: var(--text-secondary); }
  #cred-card.collapsed .cred-summary { display: flex; justify-content: space-between; align-items: center; }
  .cred-summary a { color: var(--series-1); cursor: pointer; text-decoration: underline; }
  #empty-state { text-align: center; color: var(--text-muted); font-size: 13px; padding: 50px 20px; }

  /* Filter bar */
  .filters { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
  .filters select, .filters button {
    font: inherit; font-size: 13px; padding: 7px 10px; border-radius: 8px;
    border: 1px solid var(--border); background: var(--surface-1); color: var(--text-primary);
  }
  .filters button.reset { cursor: pointer; color: var(--text-secondary); }
  .filters button.reset:hover { color: var(--text-primary); }
  .active-filters { font-size: 12px; color: var(--text-secondary); margin-left: auto; }
  .chip { display: inline-flex; align-items: center; gap: 6px; background: var(--page); border: 1px solid var(--border); border-radius: 999px; padding: 3px 10px; margin-left: 6px; font-size: 12px; }

  .kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
  .kpi { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; }
  .kpi .label { font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
  .kpi .value { font-size: 26px; font-weight: 600; }
  .kpi .delta { font-size: 12px; margin-top: 4px; }
  .kpi .delta.up { color: var(--series-8); }
  .kpi .delta.down { color: var(--good); }
  .kpi .delta.flat { color: var(--text-muted); }

  .tabs { display: flex; gap: 4px; margin-bottom: 14px; border-bottom: 1px solid var(--gridline); }
  .tab { font-size: 13px; padding: 8px 14px; cursor: pointer; color: var(--text-secondary); border-bottom: 2px solid transparent; user-select: none; }
  .tab.active { color: var(--text-primary); border-bottom-color: var(--series-1); font-weight: 600; }

  .explorer-grid { display: grid; grid-template-columns: 300px 1fr; gap: 20px; }
  .rank-list { display: flex; flex-direction: column; gap: 2px; max-height: 420px; overflow-y: auto; }
  .rank-row { display: grid; grid-template-columns: 1fr auto 70px; gap: 8px; align-items: center; padding: 6px 8px; border-radius: 6px; cursor: pointer; font-size: 12.5px; }
  .rank-row:hover { background: var(--page); }
  .rank-row.selected { background: var(--page); outline: 1px solid var(--series-1); }
  .rank-row .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rank-row .count { color: var(--text-secondary); font-variant-numeric: tabular-nums; }
  .rank-row .spark { width: 70px; height: 20px; }

  .legend { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 10px; font-size: 12px; color: var(--text-secondary); }
  .legend .item { display: flex; align-items: center; gap: 6px; }
  .legend .swatch { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }

  svg { display: block; overflow: visible; }
  .axis-label { font-size: 11px; fill: var(--text-muted); }
  .grid-line { stroke: var(--gridline); stroke-width: 1; }
  .baseline { stroke: var(--baseline); stroke-width: 1; }
  .bar-label { font-size: 11px; fill: var(--text-secondary); font-variant-numeric: tabular-nums; }

  table.ticket-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  table.ticket-table th {
    text-align: left; font-weight: 600; color: var(--text-secondary); font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.02em; padding: 6px 10px; border-bottom: 1px solid var(--gridline); position: sticky; top: 0; background: var(--surface-1);
  }
  table.ticket-table td { padding: 6px 10px; border-bottom: 1px solid var(--gridline); }
  table.ticket-table tbody tr:hover { background: var(--page); }
  .table-scroll { max-height: 420px; overflow-y: auto; border: 1px solid var(--border); border-radius: 8px; }
  .pri-badge { display: inline-block; padding: 1px 7px; border-radius: 999px; font-size: 11px; font-weight: 600; }
  .pri-P1 { background: var(--seq-650); color: #fff; }
  .pri-P2 { background: var(--seq-500); color: #fff; }
  .pri-P3 { background: var(--seq-350); color: #0b0b0b; }
  .pri-P4 { background: var(--seq-200); color: #0b0b0b; }

  .tooltip {
    position: fixed; pointer-events: none; background: var(--text-primary); color: var(--surface-1);
    font-size: 12px; padding: 6px 9px; border-radius: 6px; z-index: 50; opacity: 0; transition: opacity 0.08s; max-width: 240px; line-height: 1.4;
  }
  .empty-note { font-size: 12.5px; color: var(--text-muted); padding: 20px; text-align: center; }
  .footer-note { font-size: 11.5px; color: var(--text-muted); margin-top: 22px; line-height: 1.6; }
</style>
</head>
<body>
<div class="viz-root">
<div class="wrap">
  <h1>Zoho Ticket Trend Dashboard</h1>
  <p class="sub">Current quarter + previous 2 quarters, by priority, customer, bundle, and ticket type. notify-sre / Gmail / Gartner noise is filtered automatically.</p>

  <div class="card" id="cred-card">
    <div class="cred-summary">
      <span id="cred-summary-text"></span>
      <a id="change-creds">Change credentials</a>
    </div>
    <div class="cred-grid">
      <div class="cred-field"><label>Zoho Client ID</label><input id="c-client-id" type="text" autocomplete="off"></div>
      <div class="cred-field"><label>Zoho Client Secret</label><input id="c-client-secret" type="password" autocomplete="off"></div>
      <div class="cred-field"><label>Zoho Refresh Token</label><input id="c-refresh-token" type="password" autocomplete="off"></div>
      <div class="cred-field"><label>Org ID</label><input id="c-org-id" type="text" value="__DEFAULT_ORG_ID__"></div>
      <div class="cred-field"><label>Department ID</label><input id="c-dept-id" type="text" value="__DEFAULT_DEPT_ID__"></div>
      <div class="cred-field">
        <label>Window</label>
        <select id="c-quarters-back">
          <option value="0">Current quarter only</option>
          <option value="1">Current + last quarter</option>
          <option value="2" selected>Current + last 2 quarters</option>
          <option value="3">Current + last 3 quarters</option>
        </select>
      </div>
      <div class="cred-field"><button id="load-btn" onclick="fetchAndRender()">Load dashboard</button></div>
    </div>
    <p class="cred-note">
      Sent directly to this app's own backend, used once to call the Zoho Desk API on your behalf, then discarded —
      not stored, not logged, not written to disk. Not persisted across page reloads either; you'll re-enter it next visit.
      Org ID / Department ID are pre-filled with CoreStack Support's defaults — change them if you're pointing at a different department.
    </p>
    <div class="cred-error" id="cred-error"></div>
  </div>

  <div id="empty-state">Enter your Zoho credentials above and click <b>Load dashboard</b>.</div>

  <div id="dashboard-body" style="display:none">
    <div class="card">
      <div class="filters">
        <select id="f-customer"><option value="">All customers</option></select>
        <select id="f-bundle"><option value="">All bundles</option></select>
        <select id="f-type"><option value="">All ticket types</option></select>
        <select id="f-priority"><option value="">All priorities</option></select>
        <button class="reset" id="reset-filters">Clear filters</button>
        <span class="active-filters" id="active-filters"></span>
      </div>
    </div>

    <div class="kpi-row" id="kpi-row"></div>

    <div class="card">
      <h2>Quarterly volume by priority</h2>
      <p class="hint">Ticket count per quarter, segmented by priority (P1 = most severe).</p>
      <div id="chart-priority"></div>
      <div class="legend" id="legend-priority"></div>
    </div>

    <div class="card">
      <h2>Quarterly volume by ticket type</h2>
      <p class="hint">What customers are actually raising tickets about, quarter over quarter (CoreStack's "Reporting Feature" field, or subject-classified when that's blank).</p>
      <div id="chart-type"></div>
      <div class="legend" id="legend-type"></div>
    </div>

    <div class="card">
      <h2>Drill down</h2>
      <p class="hint">Pick a customer, bundle, or ticket type to see its quarter-by-quarter mix and the underlying tickets.</p>
      <div class="tabs" id="tabs">
        <div class="tab active" data-dim="customer">By customer</div>
        <div class="tab" data-dim="bundle">By bundle</div>
        <div class="tab" data-dim="type">By ticket type</div>
      </div>
      <div class="explorer-grid">
        <div class="rank-list" id="rank-list"></div>
        <div>
          <div id="explorer-chart"></div>
          <div class="legend" id="explorer-legend"></div>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Tickets <span id="ticket-count-label"></span></h2>
      <p class="hint">Reflects all filters and drill-down selections above.</p>
      <div class="table-scroll">
        <table class="ticket-table">
          <thead><tr><th>Date</th><th>Quarter</th><th>Customer</th><th>Bundle</th><th>Type</th><th>Priority</th><th>Status</th><th>Subject</th></tr></thead>
          <tbody id="ticket-tbody"></tbody>
        </table>
      </div>
    </div>

    <p class="footer-note" id="footer-note"></p>
  </div>
</div>
</div>
<div class="tooltip" id="tooltip"></div>

<script>
let DATA = [];
let META = {};
let ALL_QUARTERS = [];

const PRIORITIES = ["P1","P2","P3","P4"];
const PRIORITY_COLORS = {P1:"var(--seq-650)", P2:"var(--seq-500)", P3:"var(--seq-350)", P4:"var(--seq-200)"};
const CAT_COLORS = ["var(--series-1)","var(--series-2)","var(--series-3)","var(--series-4)","var(--series-5)","var(--series-6)","var(--series-7)","var(--series-8)"];

let state = { customer: "", bundle: "", type: "", priority: "", dim: "customer", drill: null };

function uniqueSorted(arr){ return [...new Set(arr)].sort(); }
function quarterSort(a,b){
  const [qa,ya]=a.split(" "), [qb,yb]=b.split(" ");
  return ya!==yb ? ya-yb : qa.localeCompare(qb);
}
function recomputeQuarters(){ ALL_QUARTERS = uniqueSorted(DATA.map(d=>d.quarter)).sort(quarterSort); }

function populateSelect(id, values, current){
  const sel = document.getElementById(id);
  sel.innerHTML = sel.querySelector('option[value=""]').outerHTML;
  values.forEach(v=>{
    const o=document.createElement("option"); o.value=v; o.textContent=v;
    if (v===current) o.selected=true;
    sel.appendChild(o);
  });
}
function populateFilters(){
  populateSelect("f-customer", uniqueSorted(DATA.map(d=>d.customer)));
  populateSelect("f-bundle", uniqueSorted(DATA.map(d=>d.bundle)));
  populateSelect("f-type", uniqueSorted(DATA.map(d=>d.type)));
  populateSelect("f-priority", PRIORITIES);
}

function baseFiltered(){
  return DATA.filter(d=>
    (!state.customer || d.customer===state.customer) &&
    (!state.bundle || d.bundle===state.bundle) &&
    (!state.type || d.type===state.type) &&
    (!state.priority || d.priority===state.priority)
  );
}

function fmtDelta(curr, prev){
  if (prev===0) return {text: curr>0 ? "new activity" : "—", cls:"flat"};
  const pct = Math.round(((curr-prev)/prev)*100);
  if (pct===0) return {text:"flat vs prior quarter", cls:"flat"};
  return {text:`${pct>0?"+":""}${pct}% vs prior quarter`, cls: pct>0?"up":"down"};
}

function isQuarterPartial(qLabel){
  const [q,y] = qLabel.split(" ");
  const endMonth = parseInt(q.slice(1)) * 3;
  const quarterEnd = new Date(Date.UTC(parseInt(y), endMonth, 0));
  return new Date() < quarterEnd;
}

function renderKPIs(){
  const data = baseFiltered();
  const byQ = {};
  ALL_QUARTERS.forEach(q=>byQ[q]=0);
  data.forEach(d=>byQ[d.quarter]=(byQ[d.quarter]||0)+1);
  const lastQ = ALL_QUARTERS[ALL_QUARTERS.length-1];
  const prevQ = ALL_QUARTERS[ALL_QUARTERS.length-2];
  const delta = fmtDelta(byQ[lastQ]||0, prevQ ? (byQ[prevQ]||0) : 0);
  const partial = lastQ ? isQuarterPartial(lastQ) : false;
  const highPri = data.filter(d=>d.priority==="P1"||d.priority==="P2").length;
  const customers = new Set(data.map(d=>d.customer)).size;
  const bundles = new Set(data.map(d=>d.bundle)).size;

  const kpis = [
    {label:"Total tickets (filtered)", value: data.length.toLocaleString(), delta:null},
    {label:`This quarter (${lastQ||"—"}${partial?", in progress":""})`, value:(byQ[lastQ]||0).toLocaleString(),
      delta: partial ? {text:"quarter not yet complete — not comparable to prior full quarter", cls:"flat"} : delta},
    {label:"P1+P2 share", value: data.length? Math.round(highPri/data.length*100)+"%":"—", delta:null},
    {label:"Distinct customers", value: customers.toLocaleString(), delta:null},
    {label:"Distinct bundles", value: bundles.toLocaleString(), delta:null},
  ];
  document.getElementById("kpi-row").innerHTML = kpis.map(k=>`
    <div class="kpi">
      <div class="label">${k.label}</div>
      <div class="value">${k.value}</div>
      ${k.delta ? `<div class="delta ${k.delta.cls}">${k.delta.text}</div>` : ""}
    </div>`).join("");
}

const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs){ const el = document.createElementNS(NS, tag); for (const k in attrs) el.setAttribute(k, attrs[k]); return el; }
function roundedTopRect(x,y,w,h,r){
  r = Math.min(r, w/2, h);
  if (h<=0) return svg("path",{d:""});
  const d = `M${x},${y+h} L${x},${y+r} Q${x},${y} ${x+r},${y} L${x+w-r},${y} Q${x+w},${y} ${x+w},${y+r} L${x+w},${y+h} Z`;
  return svg("path",{d});
}
function roundedRightRect(x,y,w,h,r){
  r = Math.min(r, h/2, Math.max(w,0.01));
  const d = `M${x},${y} L${x+w-r},${y} Q${x+w},${y} ${x+w},${y+r} L${x+w},${y+h-r} Q${x+w},${y+h} ${x+w-r},${y+h} L${x},${y+h} Z`;
  return svg("path",{d});
}

const tooltip = document.getElementById("tooltip");
function showTip(html, evt){ tooltip.innerHTML = html; tooltip.style.opacity = 1; moveTip(evt); }
function moveTip(evt){ tooltip.style.left = (evt.clientX + 14) + "px"; tooltip.style.top = (evt.clientY + 14) + "px"; }
function hideTip(){ tooltip.style.opacity = 0; }

function stackedBarChart(container, categories, seriesKeys, seriesColors, seriesLabels, dataByCategory, opts){
  opts = opts || {};
  container.innerHTML = "";
  const W = container.clientWidth || 1080, H = opts.height || 260;
  const marginL = 40, marginB = 24, marginT = 10, marginR = 10;
  const plotW = W - marginL - marginR, plotH = H - marginT - marginB;
  const maxTotal = Math.max(1, ...categories.map(c => seriesKeys.reduce((s,k)=> s + (dataByCategory[c]?.[k]||0), 0)));
  const s = svg("svg", {width:W, height:H, viewBox:`0 0 ${W} ${H}`});
  const steps = 4;
  for (let i=0;i<=steps;i++){
    const y = marginT + plotH - (plotH*i/steps);
    s.appendChild(svg("line",{x1:marginL,x2:marginL+plotW,y1:y,y2:y,class: i===0?"baseline":"grid-line"}));
    const lbl = svg("text",{x:marginL-8,y:y+3,class:"axis-label","text-anchor":"end"});
    lbl.textContent = Math.round(maxTotal*i/steps);
    s.appendChild(lbl);
  }
  const bandW = plotW/categories.length;
  const barW = Math.min(56, bandW*0.55);
  categories.forEach((cat,ci)=>{
    const cx = marginL + bandW*ci + bandW/2 - barW/2;
    let yTop = marginT + plotH;
    const total = seriesKeys.reduce((s,k)=> s + (dataByCategory[cat]?.[k]||0), 0);
    seriesKeys.forEach((key, si)=>{
      const val = dataByCategory[cat]?.[key] || 0;
      if (val<=0) return;
      const segH = Math.max(0,(val/maxTotal)*plotH - (si < seriesKeys.length-1 ? 1 : 0));
      const y = yTop - segH;
      const isTop = seriesKeys.slice(si+1).every(k => !(dataByCategory[cat]?.[k]));
      const rect = isTop ? roundedTopRect(cx,y,barW,segH,4) : svg("rect",{x:cx,y,width:barW,height:segH});
      rect.setAttribute("fill", seriesColors[si]);
      rect.style.cursor = "pointer";
      rect.addEventListener("mousemove", e=>{ showTip(`<b>${cat}</b><br>${seriesLabels[si]}: ${val}<br>Total: ${total}`, e); });
      rect.addEventListener("mouseleave", hideTip);
      s.appendChild(rect);
      yTop = y - 2;
    });
    const catLbl = svg("text",{x:marginL+bandW*ci+bandW/2, y:H-6, class:"axis-label", "text-anchor":"middle"});
    catLbl.textContent = cat;
    s.appendChild(catLbl);
    if (total>0){
      const totLbl = svg("text",{x:marginL+bandW*ci+bandW/2, y:marginT+plotH-(total/maxTotal)*plotH-8, class:"bar-label", "text-anchor":"middle"});
      totLbl.textContent = total;
      s.appendChild(totLbl);
    }
  });
  container.appendChild(s);
}

function rankedBarChart(container, rows, opts){
  opts = opts || {};
  container.innerHTML = "";
  const W = container.clientWidth || 620;
  const rowH = 22, gap = 6;
  const H = rows.length * (rowH+gap);
  const labelW = 150, marginR = 40;
  const plotW = Math.max(40, W - labelW - marginR);
  const max = Math.max(1, ...rows.map(r=>r.count));
  const s = svg("svg",{width:W, height: Math.max(H,20), viewBox:`0 0 ${W} ${Math.max(H,20)}`});
  rows.forEach((r,i)=>{
    const y = i*(rowH+gap);
    const w = (r.count/max)*plotW;
    const lbl = svg("text",{x:0,y:y+rowH/2+4,class:"axis-label"});
    lbl.textContent = r.name.length>20 ? r.name.slice(0,19)+"…" : r.name;
    lbl.setAttribute("title", r.name);
    s.appendChild(lbl);
    const rect = roundedRightRect(labelW, y, w, rowH, 4);
    rect.setAttribute("fill","var(--seq-400)");
    rect.style.cursor="pointer";
    rect.addEventListener("mousemove", e=>showTip(`<b>${r.name}</b><br>${r.count} tickets`, e));
    rect.addEventListener("mouseleave", hideTip);
    if (opts.onClick) rect.addEventListener("click", ()=>opts.onClick(r.name));
    s.appendChild(rect);
    const vLbl = svg("text",{x:labelW+w+6,y:y+rowH/2+4,class:"bar-label"});
    vLbl.textContent = r.count;
    s.appendChild(vLbl);
  });
  container.appendChild(s);
}

function sparkline(container, values, w, h){
  container.innerHTML = "";
  const max = Math.max(1, ...values);
  const s = svg("svg",{width:w,height:h,viewBox:`0 0 ${w} ${h}`});
  const stepX = w/Math.max(1,values.length-1);
  const pts = values.map((v,i)=>`${i*stepX},${h - (v/max)*(h-4) - 2}`).join(" ");
  s.appendChild(svg("polyline",{points:pts, fill:"none", stroke:"var(--series-1)", "stroke-width":1.6, "stroke-linecap":"round","stroke-linejoin":"round"}));
  container.appendChild(s);
}

function countBy(data, keyFn){ const m = {}; data.forEach(d=>{ const k=keyFn(d); m[k]=(m[k]||0)+1; }); return m; }

function renderPriorityChart(){
  const data = baseFiltered();
  const byQ = {};
  ALL_QUARTERS.forEach(q=>{ byQ[q]={}; PRIORITIES.forEach(p=>byQ[q][p]=0); });
  data.forEach(d=>{ if(byQ[d.quarter]) byQ[d.quarter][d.priority]=(byQ[d.quarter][d.priority]||0)+1; });
  stackedBarChart(document.getElementById("chart-priority"), ALL_QUARTERS, PRIORITIES,
    PRIORITIES.map(p=>PRIORITY_COLORS[p]), PRIORITIES, byQ, {height:260});
  document.getElementById("legend-priority").innerHTML = PRIORITIES.map(p=>
    `<span class="item"><span class="swatch" style="background:${PRIORITY_COLORS[p]}"></span>${p}</span>`).join("");
}

function topNWithOther(data, keyFn, n){
  const counts = countBy(data, keyFn);
  const sorted = Object.entries(counts).sort((a,b)=>b[1]-a[1]);
  const top = sorted.slice(0,n).map(x=>x[0]);
  const otherTotal = sorted.slice(n).reduce((s,x)=>s+x[1],0);
  return otherTotal>0 ? [...top,"Other"] : top;
}

function renderTypeChart(){
  const data = baseFiltered();
  const keys = topNWithOther(data, d=>d.type, 7);
  const byQ = {};
  ALL_QUARTERS.forEach(q=>{ byQ[q]={}; keys.forEach(k=>byQ[q][k]=0); });
  data.forEach(d=>{
    const k = keys.includes(d.type) ? d.type : "Other";
    if (byQ[d.quarter]) byQ[d.quarter][k]=(byQ[d.quarter][k]||0)+1;
  });
  stackedBarChart(document.getElementById("chart-type"), ALL_QUARTERS, keys, CAT_COLORS, keys, byQ, {height:280});
  document.getElementById("legend-type").innerHTML = keys.map((k,i)=>
    `<span class="item"><span class="swatch" style="background:${CAT_COLORS[i]}"></span>${k}</span>`).join("");
}

function fieldForDim(dim){ return dim==="customer" ? "customer" : dim==="bundle" ? "bundle" : "type"; }

function renderExplorer(){
  const dim = state.dim;
  const field = fieldForDim(dim);
  const data = baseFiltered();
  const counts = countBy(data, d=>d[field]);
  const rows = Object.entries(counts).sort((a,b)=>b[1]-a[1]).map(([name,count])=>({name,count}));

  const list = document.getElementById("rank-list");
  list.innerHTML = "";
  if (rows.length===0){ list.innerHTML = '<div class="empty-note">No tickets match the current filters.</div>'; }
  rows.forEach(r=>{
    const row = document.createElement("div");
    row.className = "rank-row" + (state.drill===r.name ? " selected" : "");
    row.innerHTML = `<span class="name" title="${r.name}">${r.name}</span><span class="count">${r.count}</span><span class="spark"></span>`;
    row.addEventListener("click", ()=>{ state.drill = (state.drill===r.name) ? null : r.name; renderExplorer(); });
    list.appendChild(row);
    const seriesVals = ALL_QUARTERS.map(q => data.filter(d=>d[field]===r.name && d.quarter===q).length);
    sparkline(row.querySelector(".spark"), seriesVals, 70, 20);
  });

  const chartDiv = document.getElementById("explorer-chart");
  const legendDiv = document.getElementById("explorer-legend");
  if (!state.drill){
    rankedBarChart(chartDiv, rows.slice(0,15), {onClick:(name)=>{ state.drill=name; renderExplorer(); }});
    legendDiv.innerHTML = rows.length>15 ? `<span>Showing top 15 of ${rows.length}. Click a row to drill in.</span>` : "";
    return;
  }
  const sub = data.filter(d=>d[field]===state.drill);
  const otherField = dim==="type" ? "customer" : "type";
  const keys = topNWithOther(sub, d=>d[otherField], 7);
  const byQ = {};
  ALL_QUARTERS.forEach(q=>{ byQ[q]={}; keys.forEach(k=>byQ[q][k]=0); });
  sub.forEach(d=>{
    const k = keys.includes(d[otherField]) ? d[otherField] : "Other";
    if (byQ[d.quarter]) byQ[d.quarter][k]=(byQ[d.quarter][k]||0)+1;
  });
  stackedBarChart(chartDiv, ALL_QUARTERS, keys, CAT_COLORS, keys, byQ, {height:260});
  legendDiv.innerHTML = keys.map((k,i)=>`<span class="item"><span class="swatch" style="background:${CAT_COLORS[i]}"></span>${k}</span>`).join("") +
    `<span class="item" style="margin-left:auto;color:var(--text-muted)">${sub.length} tickets total for "${state.drill}" — breakdown by ${otherField}</span>`;
}

function renderTicketTable(){
  const data = baseFiltered().filter(d=>{
    if (!state.drill) return true;
    return d[fieldForDim(state.dim)] === state.drill;
  }).sort((a,b)=> b.created_date.localeCompare(a.created_date));
  document.getElementById("ticket-count-label").textContent = `(${data.length.toLocaleString()})`;
  const CAP = 400;
  const rows = data.slice(0,CAP).map(d=>`
    <tr>
      <td>${d.created_date}</td><td>${d.quarter}</td><td>${d.customer}</td><td>${d.bundle}</td>
      <td>${d.type}</td><td><span class="pri-badge pri-${d.priority}">${d.priority}</span></td>
      <td>${d.status||""}</td><td>${(d.subject||"").replace(/</g,"&lt;")}</td>
    </tr>`).join("");
  document.getElementById("ticket-tbody").innerHTML = rows || '<tr><td colspan="8" class="empty-note">No tickets match.</td></tr>';
  if (data.length>CAP){
    document.getElementById("ticket-tbody").insertAdjacentHTML("beforeend",
      `<tr><td colspan="8" class="empty-note">Showing first ${CAP} of ${data.length} — narrow the filters to see more.</td></tr>`);
  }
}

function renderActiveFilters(){
  const el = document.getElementById("active-filters");
  const chips = [];
  if (state.customer) chips.push(["customer", state.customer]);
  if (state.bundle) chips.push(["bundle", state.bundle]);
  if (state.type) chips.push(["type", state.type]);
  if (state.priority) chips.push(["priority", state.priority]);
  el.innerHTML = chips.map(([k,v])=>`<span class="chip">${k}: ${v}</span>`).join("");
}

function renderAll(){
  document.getElementById("footer-note").innerHTML =
    `${DATA.length.toLocaleString()} tickets · ${META.start_date} → ${META.end_date} · fetched ${META.fetched_at||""}. ` +
    `Ticket type prefers Zoho's "Reporting Feature" field, falling back to subject-keyword classification when blank. Bundle comes from "Reporting Bundle".`;
  renderKPIs();
  renderPriorityChart();
  renderTypeChart();
  renderExplorer();
  renderTicketTable();
  renderActiveFilters();
}

async function fetchAndRender(){
  const btn = document.getElementById("load-btn");
  const errEl = document.getElementById("cred-error");
  errEl.textContent = "";
  const payload = {
    client_id: document.getElementById("c-client-id").value.trim(),
    client_secret: document.getElementById("c-client-secret").value.trim(),
    refresh_token: document.getElementById("c-refresh-token").value.trim(),
    org_id: document.getElementById("c-org-id").value.trim(),
    dept_id: document.getElementById("c-dept-id").value.trim(),
    quarters_back: parseInt(document.getElementById("c-quarters-back").value, 10),
  };
  if (!payload.client_id || !payload.client_secret || !payload.refresh_token){
    errEl.textContent = "Client ID, Client Secret, and Refresh Token are all required.";
    return;
  }
  btn.disabled = true; btn.textContent = "Fetching from Zoho…";
  try {
    const resp = await fetch("tickets", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)});
    const body = await resp.json();
    if (!resp.ok) throw new Error(body.error || ("HTTP " + resp.status));
    DATA = body.tickets; META = body.meta;
    recomputeQuarters();
    document.getElementById("cred-card").classList.add("collapsed");
    document.getElementById("cred-summary-text").textContent =
      `Connected · ${DATA.length.toLocaleString()} tickets · ${META.start_date} → ${META.end_date}`;
    document.getElementById("empty-state").style.display = "none";
    document.getElementById("dashboard-body").style.display = "";
    populateFilters();
    state = { customer:"", bundle:"", type:"", priority:"", dim: state.dim, drill:null };
    renderAll();
  } catch (e) {
    errEl.textContent = "Could not load tickets: " + e.message;
  } finally {
    btn.disabled = false; btn.textContent = "Load dashboard";
  }
}

document.getElementById("change-creds").addEventListener("click", ()=>{
  document.getElementById("cred-card").classList.remove("collapsed");
});
["customer","bundle","type","priority"].forEach(f=>{
  document.getElementById("f-"+f).addEventListener("change", e=>{ state[f]=e.target.value; state.drill=null; renderAll(); });
});
document.getElementById("reset-filters").addEventListener("click", ()=>{
  state = { customer:"", bundle:"", type:"", priority:"", dim: state.dim, drill:null };
  ["customer","bundle","type","priority"].forEach(f=>document.getElementById("f-"+f).value="");
  renderAll();
});
document.querySelectorAll(".tab").forEach(t=>{
  t.addEventListener("click", ()=>{
    document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
    t.classList.add("active");
    state.dim = t.dataset.dim; state.drill = null;
    renderAll();
  });
});
window.addEventListener("resize", ()=>{ if (DATA.length){ renderPriorityChart(); renderTypeChart(); renderExplorer(); } });
</script>
</body>
</html>
"""
