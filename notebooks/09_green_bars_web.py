# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.6
# ---

# %% [markdown]
# # 09 – Green vote by electorate: a sortable web page
# Turns the section 5b chart of notebook 06 (four bars per electorate: party vote 2023, party vote 2026, candidate vote 2023,
# candidate vote 2026) into one self-contained HTML page you can re-sort by clicking any of the four series, the electorate
# name, or the gap between candidate and party vote. Notebook 06 is not changed.
#
# **Needs notebook 06 to have run first**: it reads `data/staging/green_electorate_comparison.csv`, so the page always shows
# whatever scope and count stage (`VOTE_SCOPE`, `COUNT_STAGE`) notebook 06 used. When the final results are loaded, re-run
# 06 then this notebook.
#
# Output: `data/geo/green_electorates.html` (gitignored; open it in any browser, no server or internet needed).

# %%
import json, sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
import candidates, electorates

PARTY = "Green Party"
SUBTITLE = "all votes including special votes; 2026 is the final count"   # edit if the count basis changes
FOCUS_NOTE = "North Shore, Northcote, East Coast Bays, Upper Harbour"
SRC = ROOT / "data/staging/green_electorate_comparison.csv"
OUT = ROOT / "data/geo/green_electorates.html"

t = pd.read_csv(SRC)
need = ["electorate_2026", "party_2023", "party_2026", "cand_2023", "cand_2026", "party_vs_nat_2023", "party_vs_nat_2026", "roll", "focus"]
missing = [c for c in need if c not in t.columns]
assert not missing, f"re-run notebook 06; missing columns {missing}"
assert len(t) == 71 and t.electorate_2026.is_unique, len(t)

# national party share = seat share minus the seat's gap to national (constant across seats)
nat = {y: t[f"party_{y}"] - t[f"party_vs_nat_{y}"] for y in (2023, 2026)}   # the CSV is rounded to 2 decimals
assert all(s.max() - s.min() < 0.03 for s in nat.values()), "national share not constant: notebook 06 output changed shape"
nat = {y: float(s.mean()) for y, s in nat.items()}
print(f"national {PARTY} party share: 2023 {nat[2023]:.2f}%  2026 {nat[2026]:.2f}%  ({len(t)} electorates)")

# Green candidate names under each electorate: 2026 from the Commission's candidate list, 2023 from the staged 2023 results
# (renamed to the 2026 electorate names), both shown as "Given Surname"
c26 = pd.read_csv(ROOT / "data/reference/ge2026_green_candidates.csv")
c23 = electorates.align_2023(pd.read_parquet(ROOT / "data/staging/stg_candidate_party.parquet").query("party == @PARTY"))
assert c26.electorate.is_unique and c23.electorate.is_unique
assert set(c26.electorate) <= set(t.electorate_2026), "a 2026 candidate's electorate is not in the 2026 list"
gone = sorted(set(c23.electorate) - set(t.electorate_2026))   # 2023 seats with no 2026 counterpart (Ōhāriu) have no row on this page
c23 = c23[c23.electorate.isin(t.electorate_2026)]
print("2023 Green candidates in seats not on this page:", gone)
n26 = dict(zip(c26.electorate, c26.candidate.map(candidates.display_name)))
n23 = dict(zip(c23.electorate, c23.candidate.map(candidates.display_name)))
# a candidate name exists exactly where the page shows a candidate bar
assert {e for e, v in zip(t.electorate_2026, t.cand_2026) if pd.notna(v)} == set(n26), "2026 candidate bars and names disagree"
assert {e for e, v in zip(t.electorate_2026, t.cand_2023) if pd.notna(v)} == set(n23), "2023 candidate bars and names disagree"
print(f"Green candidate names: {len(n26)} in 2026, {len(n23)} in 2023; same person both years in {sum(n26[e] == n23[e] for e in set(n26) & set(n23))} seats")

rows = [{"name": r.electorate_2026, "n26": n26.get(r.electorate_2026), "n23": n23.get(r.electorate_2026), "maori": r.roll == "maori", "focus": bool(r.focus),
         "p23": r.party_2023, "p26": r.party_2026,
         "c23": None if pd.isna(r.cand_2023) else r.cand_2023,
         "c26": None if pd.isna(r.cand_2026) else r.cand_2026} for r in t.itertuples()]
rows = [{k: (None if isinstance(v, float) and v != v else v) for k, v in r.items()} for r in rows]

# %% [markdown]
# ## The page
# Plain HTML, CSS and JavaScript in one file, no libraries. Click a legend button to sort by that series (click again to
# reverse); missing bars (no Green candidate that year) always sort to the bottom.

# %%
TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Green vote by electorate</title>
<style>
:root{--bg:#fff;--fg:#1d2327;--muted:#5b666e;--line:#e3e7ea;--focus:#fff3c4;--card:#f6f8f9;--accent:#1b7f4b}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14181b;--fg:#e8ecee;--muted:#9aa6ad;--line:#2a3238;--focus:#4a4220;--card:#1c2226;--accent:#4cc38a}}
:root[data-theme="dark"]{--bg:#14181b;--fg:#e8ecee;--muted:#9aa6ad;--line:#2a3238;--focus:#4a4220;--card:#1c2226;--accent:#4cc38a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1000px;margin:0 auto;padding:20px 16px 48px}
h1{font-size:20px;margin:0 0 2px}
.sub{color:var(--muted);margin:0 0 14px}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 10px}
.btn{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:var(--card);color:var(--fg);
  padding:6px 10px;border-radius:8px;font:inherit;cursor:pointer}
.btn[aria-pressed="true"]{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent) inset}
.btn:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block}
.arrow{font-size:11px;color:var(--muted);min-width:10px}
input[type=search]{border:1px solid var(--line);background:var(--card);color:var(--fg);padding:6px 10px;border-radius:8px;font:inherit;min-width:220px}
label.chk{display:inline-flex;gap:6px;align-items:center;color:var(--muted);cursor:pointer}
.axis{display:grid;grid-template-columns:48px 170px 1fr;color:var(--muted);font-size:11px;margin-top:6px;align-items:end}
.rankhead{text-align:right;padding-right:8px;line-height:1.15}
.ticks{position:relative;height:16px}
.ticks span{position:absolute;transform:translateX(-50%)}
.row{display:grid;grid-template-columns:48px 170px 1fr;align-items:center;border-top:1px solid var(--line);padding:3px 0}
.rank{text-align:right;padding-right:8px;font-variant-numeric:tabular-nums;font-weight:600;color:var(--muted)}
.row.focus .rank{color:var(--fg)}
.row.focus{background:var(--focus)}
.name{padding-right:8px;overflow:hidden;line-height:1.2}
.name b{display:block;font-weight:inherit;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.name small{display:block;font-size:10px;color:var(--muted);font-weight:400;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row.focus .name b{font-weight:700}
.bars{position:relative;padding:1px 0}
.bar{display:flex;align-items:center;height:9px;margin:1px 0}
.bar i{display:block;height:9px;border-radius:0 2px 2px 0;min-width:1px}
.bar em{font-style:normal;font-size:10px;color:var(--muted);margin-left:4px;white-space:nowrap}
.bar.none em{font-style:italic}
.nat{position:absolute;top:0;bottom:0;border-left:1px dashed}
.legend-note{color:var(--muted);font-size:12px;margin-top:14px}
@media (max-width:560px){.axis,.row{grid-template-columns:44px 110px 1fr}.name b{font-size:11px}}
</style>
</head>
<body>
<main>
<h1>__PARTY__: party vote and candidate vote by electorate</h1>
<p class="sub">2023 vs 2026 (__SUBTITLE__). Shaded: __FOCUS_NOTE__. (M) = Māori electorate.</p>
<div class="controls" id="sorts" role="group" aria-label="Sort by"></div>
<div class="controls">
  <input type="search" id="q" placeholder="Find an electorate or candidate" aria-label="Find an electorate or candidate">
  <label class="chk"><input type="checkbox" id="onlyFocus"> Focus seats only</label>
  <label class="chk"><input type="checkbox" id="focusFirst"> Focus seats first</label>
</div>
<div class="axis"><div class="rankhead" id="rankhead">Rank</div><div></div><div class="ticks" id="ticks"></div></div>
<div id="rows"></div>
<p class="legend-note">Bars are the share of valid votes (%). Dashed lines are the national party share (2023 light, 2026 dark).
A missing bar means the Greens stood no candidate that year. Hover a row for exact figures.</p>
</main>
<script>
const DATA = __DATA__;
const NAT = __NAT__;
const SERIES = [
  {key:"p23", label:"Party vote 2023", color:"#a8d5ba"},
  {key:"p26", label:"Party vote 2026", color:"#1b7f4b"},
  {key:"c23", label:"Candidate vote 2023", color:"#f2c58b"},
  {key:"c26", label:"Candidate vote 2026", color:"#d9731a"},
];
const EXTRA = [{key:"name", label:"Electorate (A–Z)"}, {key:"gap26", label:"Gap 2026 (candidate − party)"}];
const MAX = Math.ceil(Math.max(...DATA.flatMap(r => [r.p23, r.p26, r.c23, r.c26].filter(v => v != null))) / 5) * 5;
DATA.forEach(r => { r.gap26 = r.c26 == null ? null : r.c26 - r.p26; });

const state = {key:"p26", dir:"desc"};
const $ = id => document.getElementById(id);
const fmt = v => v == null ? "–" : v.toFixed(1) + "%";

function cmp(a, b) {
  const k = state.key, va = a[k], vb = b[k];
  if (va == null && vb == null) return a.name.localeCompare(b.name);
  if (va == null) return 1;            // missing always last
  if (vb == null) return -1;
  const d = typeof va === "string" ? va.localeCompare(vb) : va - vb;
  return (state.dir === "asc" ? d : -d) || a.name.localeCompare(b.name);
}

// Rank among ALL electorates for the current sort (a search or filter never renumbers them). Ties share a rank;
// electorates with no value (no Green candidate) are unranked.
function assignRanks() {
  const all = [...DATA].sort(cmp);
  let prev, prevRank = 0;
  all.forEach((r, i) => {
    const v = r[state.key];
    if (v == null) { r.rank = null; return; }
    r.rank = (typeof v !== "string" && v === prev) ? prevRank : i + 1;
    prev = v; prevRank = r.rank;
  });
}
function rankLabel() {
  if (state.key === "name") return "A–Z";
  return `Rank<br>${state.dir === "desc" ? "1 = high" : "1 = low"}`;
}

function buildSorts() {
  const box = $("sorts");
  box.textContent = "";
  const items = [...SERIES.map(s => ({...s, sw:s.color})), ...EXTRA];
  for (const it of items) {
    const b = document.createElement("button");
    b.className = "btn"; b.type = "button";
    b.setAttribute("aria-pressed", state.key === it.key);
    if (it.sw) { const s = document.createElement("span"); s.className = "sw"; s.style.background = it.sw; b.append(s); }
    b.append(it.label);
    const a = document.createElement("span"); a.className = "arrow";
    a.textContent = state.key === it.key ? (state.dir === "desc" ? "▼" : "▲") : "";
    b.append(a);
    b.onclick = () => {
      if (state.key === it.key) state.dir = state.dir === "desc" ? "asc" : "desc";
      else { state.key = it.key; state.dir = it.key === "name" ? "asc" : "desc"; }
      render();
    };
    box.append(b);
  }
}

function buildTicks() {
  const t = $("ticks"); t.textContent = "";
  for (let v = 0; v <= MAX; v += 10) {
    const s = document.createElement("span"); s.style.left = (v / MAX * 100) + "%"; s.textContent = v + "%"; t.append(s);
  }
}

function render() {
  buildSorts();
  assignRanks();
  $("rankhead").innerHTML = rankLabel();
  const q = $("q").value.trim().toLowerCase();
  let rows = DATA.filter(r => (r.name + " " + (r.n26 || "") + " " + (r.n23 || "")).toLowerCase().includes(q) && (!$("onlyFocus").checked || r.focus));
  rows.sort(cmp);
  if ($("focusFirst").checked) rows.sort((a, b) => (b.focus - a.focus));   // stable: keeps the chosen order inside each group
  const host = $("rows"); host.textContent = "";
  const yr = state.key.endsWith("23") ? 2023 : 2026;
  const grid = "linear-gradient(to right, var(--line) 1px, transparent 1px)";
  for (const r of rows) {
    const row = document.createElement("div"); row.className = "row" + (r.focus ? " focus" : "");
    row.title = `${r.name}\nGreen candidate 2026: ${r.n26 || "none"}   2023: ${r.n23 || "none"}\nParty vote 2023: ${fmt(r.p23)}   2026: ${fmt(r.p26)}\nCandidate vote 2023: ${fmt(r.c23)}   2026: ${fmt(r.c26)}` +
      (r.gap26 == null ? "" : `\nGap 2026 (candidate − party): ${r.gap26.toFixed(1)} pts`);
    const rk = document.createElement("div"); rk.className = "rank"; rk.textContent = r.rank == null ? "–" : r.rank;
    rk.title = r.rank == null ? "no value for this series" : `${r.rank} of ${DATA.filter(d => d[state.key] != null).length}`;
    row.append(rk);
    const n = document.createElement("div"); n.className = "name";
    const nm = document.createElement("b"); nm.textContent = r.name + (r.maori ? " (M)" : "");
    const cand = document.createElement("small");   // the Green candidate for the year being sorted on (2023 series -> 2023, otherwise 2026)
    cand.textContent = `${yr}: ` + ((yr === 2023 ? r.n23 : r.n26) || "no Green candidate");
    n.append(nm, cand); row.append(n);
    const bars = document.createElement("div"); bars.className = "bars";
    bars.style.backgroundImage = grid; bars.style.backgroundSize = (10 / MAX * 100) + "% 100%";
    for (const s of SERIES) {
      const v = r[s.key];
      const bar = document.createElement("div"); bar.className = "bar" + (v == null ? " none" : "");
      const fill = document.createElement("i"); fill.style.width = v == null ? "0" : (v / MAX * 100) + "%"; fill.style.background = s.color;
      const lab = document.createElement("em"); lab.textContent = v == null ? "no candidate" : v.toFixed(1);
      bar.append(fill, lab); bars.append(bar);
    }
    for (const [y, color] of [[2023, "#a8d5ba"], [2026, "#1b7f4b"]]) {
      const line = document.createElement("div"); line.className = "nat"; line.style.left = (NAT[y] / MAX * 100) + "%"; line.style.borderColor = color; bars.append(line);
    }
    row.append(bars); host.append(row);
  }
  if (!rows.length) host.textContent = "No electorates match.";
}

buildTicks();
$("q").addEventListener("input", render);
$("onlyFocus").addEventListener("change", render);
$("focusFirst").addEventListener("change", render);
render();
</script>
</body>
</html>
"""

def embed(obj) -> str:
    # JSON inside <script>: break up "</" so a value can never close the tag
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

html = (TEMPLATE.replace("__DATA__", embed(rows)).replace("__NAT__", embed({2023: nat[2023], 2026: nat[2026]}))
        .replace("__PARTY__", PARTY).replace("__SUBTITLE__", SUBTITLE).replace("__FOCUS_NOTE__", FOCUS_NOTE))
assert "__" not in html.replace("__PROTO__", ""), "unreplaced placeholder"
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)}  ({len(html) / 1024:.0f} KB)")
