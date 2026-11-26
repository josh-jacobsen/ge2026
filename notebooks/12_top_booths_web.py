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
# # 12 – Voting places: Green and Opportunity (TOP) vote, a browsable web page
# Notebook 11 prints top-3 tables with many columns. This builds one self-contained HTML page instead
# (`data/geo/top_booths.html`, gitignored; open in any browser, no server or internet needed).
#
# A voting place is the **whole venue** (votes added over every electorate that lists it, as in the notebook 04 swing map),
# placed in its **home electorate** (the general-roll electorate with most votes there). Same data as notebook 11, built by `src/booths.py`.
#
# On the page you choose the party (Green or TOP), the year (2023 or 2026), and what to rank by (number of votes or share of the venue's ballots).
# * **Focus seats** or **All electorates**: a card per home electorate with its top 3 venues.
# * **One electorate**: every venue in it, ranked, with the top 3 highlighted.
# * **Min ballots at venue** (default 100) keeps tiny venues out of the share ranking.
# * **Local %** on every row: the share of the party's votes at the venue cast by voters of the home electorate.
#
# Ordinary votes only: special, overseas and mobile-team votes belong to an electorate, not a venue. Electorates were
# redrawn for 2026, so home electorates (and the electorate list) differ between the years.

# %%
import json, sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
import booths, vote_scope

COUNT_STAGE = "preliminary"   # 2026 count: "preliminary" or "final"
FOCUS = ["North Shore", "Northcote", "East Coast Bays", "Upper Harbour"]
SUBTITLE = f"Party vote, ordinary votes at voting places. 2023 final; 2026 {COUNT_STAGE}."
OUT = ROOT / "data" / "geo" / "top_booths.html"

# %% [markdown]
# ## 1. One row per venue

# %%
pv = vote_scope.load("stg_party_votes", "ordinary", COUNT_STAGE)
rows = booths.venue_table(pv)
rows = rows[rows.total > 0]
print(rows.groupby("election_year").agg(venues=("total", "size"), electorates=("home_electorate", "nunique")))
assert (rows.green_home <= rows.green).all() and (rows.top_home <= rows.top).all()
print(rows[rows.place.str.contains("Milford Shopping") & (rows.election_year == 2026)][["place", "home_electorate", "total", "green", "green_home"]])

# %% [markdown]
# ## 2. The page

# %%
data = {
    # [year, home electorate, suburb, venue, green, green from home voters, top, top from home voters, all ballots, home ballots, electorates listing]
    "rows": [[int(r.election_year), r.home_electorate, r.suburb, r.venue, int(r.green), int(r.green_home), int(r.top), int(r.top_home),
              int(r.total), int(r.home_total), int(r.n_electorates)] for r in rows.itertuples()],
    "focus": FOCUS, "subtitle": SUBTITLE,
}
payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Voting venues: Green and TOP</title>
<style>
:root{--bg:#fafaf8;--fg:#1d2420;--mute:#66706a;--card:#fff;--line:#dfe3df;--g:#1f8f4e;--t:#d98a00;--hi:#eef7f1;--hit:#fdf4e1}
@media (prefers-color-scheme:dark){:root{--bg:#161a18;--fg:#e6ebe7;--mute:#9aa59e;--card:#1f2522;--line:#333b36;--g:#4fc17f;--t:#f0b03a;--hi:#1d2c23;--hit:#33291a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.4 system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:1.3rem;margin:.2rem 0}.sub{color:var(--mute);margin:0 0 12px;font-size:.9rem}
.bar{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;margin-bottom:14px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}
.seg button{border:0;background:var(--card);color:var(--fg);padding:6px 12px;font:inherit;cursor:pointer}
.seg button[aria-pressed=true]{background:var(--accent,var(--g));color:#fff}
select,input[type=number]{font:inherit;padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
input[type=number]{width:5.5em}label{color:var(--mute);font-size:.9rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.card h3{margin:0 0 6px;font-size:1rem;display:flex;justify-content:space-between;gap:8px}
.card h3 small{color:var(--mute);font-weight:400}
.pl{display:grid;grid-template-columns:1.4em 1fr auto;gap:6px;padding:5px 0;border-top:1px solid var(--line);align-items:baseline}
.pl:first-of-type{border-top:0}.rk{font-weight:700;color:var(--accent)}
.nm{overflow-wrap:anywhere}.nm small{display:block;color:var(--mute);font-size:.78rem}
.num{text-align:right;white-space:nowrap}.num small{display:block;color:var(--mute);font-size:.78rem}
.tag{font-size:.7rem;border:1px solid var(--line);border-radius:4px;padding:0 4px;color:var(--mute);margin-left:4px;white-space:nowrap}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:6px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.8rem;color:var(--mute);text-transform:uppercase;letter-spacing:.03em}
td.r,th.r{text-align:right}tr.top td{background:var(--hi)}
.meter{height:6px;background:var(--line);border-radius:3px;margin-top:3px;min-width:70px}.meter i{display:block;height:100%;background:var(--accent);border-radius:3px}
.note{color:var(--mute);font-size:.85rem;margin:10px 0}
@media(max-width:560px){th:nth-child(6),td:nth-child(6){display:none}}
</style></head><body><main>
<h1>Voting places: <span id="ptitle"></span></h1><p class="sub" id="sub"></p>
<div class="bar">
 <div class="seg" id="party"><button data-v="g">Green Party</button><button data-v="t">Opportunity (TOP)</button></div>
 <div class="seg" id="year"><button data-v="2023">2023</button><button data-v="2026">2026</button></div>
 <div class="seg" id="rank"><button data-v="v">Most votes</button><button data-v="pct">Highest share</button></div>
 <select id="elec" aria-label="Electorate"></select>
 <label>Min ballots at venue <input type="number" id="minv" min="0" step="10"></label>
</div>
<div id="out"></div><p class="note" id="foot"></p>
</main>
<script>
const D=__DATA__;
const S={party:'g',year:2023,rank:'v',elec:'__focus',minv:100};
const $=id=>document.getElementById(id), esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const NAMES={g:'Green Party',t:'Opportunity Party (TOP)'};
const f0=n=>n.toLocaleString('en-NZ'), f1=n=>n.toFixed(1)+'%';
function rowsFor(){
  const pi=S.party==='g'?4:6;
  return D.rows.filter(r=>r[0]===S.year).map(r=>({e:r[1],s:r[2],p:r[3],v:r[pi],h:r[pi+1],n:r[8],m:r[10],pct:100*r[pi]/r[8],hp:r[pi]?100*r[pi+1]/r[pi]:0}));
}
function rankRows(rs){
  const ok=rs.filter(r=>S.rank==='pct'?r.n>=S.minv:true&&r.n>=0);
  const key=S.rank==='pct'?'pct':'v';
  return {ok:ok.filter(r=>r[key]>0).sort((a,b)=>b[key]-a[key]||b.n-a.n),hidden:rs.length-ok.length};
}
function name(r){return `<span class="nm">${esc(r.s)}<small>${esc(r.p)}</small></span>`}
function tag(r){return r.hp<50?`<span class="tag" title="Under half of this venue's votes for the party came from voters of ${esc(r.e)}">mostly non-local</span>`:''}
function val(r){return `<span class="num">${S.rank==='pct'?f1(r.pct):f0(r.v)}<small>${S.rank==='pct'?f0(r.v)+' of '+f0(r.n):f1(r.pct)+' of '+f0(r.n)}<br>${Math.round(r.hp)}% local</small></span>`}
function render(){
  document.documentElement.style.setProperty('--accent',S.party==='g'?'var(--g)':'var(--t)');
  $('ptitle').textContent=NAMES[S.party]+', '+S.year;
  $('sub').textContent=D.subtitle;
  for(const id of ['party','year','rank'])for(const b of $(id).children)b.setAttribute('aria-pressed',String(b.dataset.v===String(S[id==='rank'?'rank':id])));
  const rs=rowsFor(), by={};
  rs.forEach(r=>(by[r.e]=by[r.e]||[]).push(r));
  const out=$('out');
  if(S.elec.startsWith('__')){
    let es=Object.keys(by).sort((a,b)=>a.localeCompare(b));
    if(S.elec==='__focus')es=D.focus.filter(e=>by[e]);
    out.innerHTML='<div class="grid">'+es.map(e=>{
      const {ok}=rankRows(by[e]), top=ok.slice(0,3);
      return `<div class="card"><h3>${esc(e)}<small>${by[e].length} venues</small></h3>`+
       (top.map((r,i)=>`<div class="pl"><span class="rk">${i+1}</span><span class="nm">${esc(r.s)}${tag(r)}<small>${esc(r.p)}</small></span>${val(r)}</div>`).join('')||'<div class="note">No venue qualifies.</div>')+'</div>';
    }).join('')+'</div>';
    $('foot').textContent=(S.rank==='pct'?`Ranked by share among places with at least ${S.minv} ballots. `:'')+'Click an electorate in the menu to see every place in it.';
  }else{
    const {ok,hidden}=rankRows(by[S.elec]||[]), max=Math.max(...ok.map(r=>S.rank==='pct'?r.pct:r.v),1);
    out.innerHTML=`<table><thead><tr><th>#</th><th>Venue</th><th class="r">${S.rank==='pct'?'Share':'Votes'}</th><th class="r">${S.rank==='pct'?'Votes':'Share'}</th><th class="r">Local %</th><th class="r">All ballots</th></tr></thead><tbody>`+
     ok.map((r,i)=>`<tr class="${i<3?'top':''}"><td>${i+1}</td><td>${esc(r.s)}${tag(r)}<small style="display:block;color:var(--mute)">${esc(r.p)}</small></td>`+
       `<td class="r">${S.rank==='pct'?f1(r.pct):f0(r.v)}<div class="meter"><i style="width:${100*(S.rank==='pct'?r.pct:r.v)/max}%"></i></div></td>`+
       `<td class="r">${S.rank==='pct'?f0(r.v):f1(r.pct)}</td><td class="r">${Math.round(r.hp)}%</td><td class="r">${f0(r.n)}</td></tr>`).join('')+'</tbody></table>';
    $('foot').textContent=`${ok.length} venues ranked`+(hidden?`; ${hidden} venues with fewer than ${S.minv} ballots left out of the share ranking`:'')+'. Top 3 highlighted.';
  }
}
function fillElec(){
  const es=[...new Set(D.rows.filter(r=>r[0]===S.year).map(r=>r[1]))].sort((a,b)=>a.localeCompare(b));
  $('elec').innerHTML='<option value="__focus">Focus seats (4)</option><option value="__all">All electorates</option>'+
    '<optgroup label="One electorate: every venue">'+es.map(e=>`<option>${esc(e)}</option>`).join('')+'</optgroup>';
  if(!(S.elec.startsWith('__')||es.includes(S.elec)))S.elec='__focus';
  $('elec').value=S.elec;
}
for(const id of ['party','year','rank'])$(id).addEventListener('click',e=>{const v=e.target.dataset.v;if(!v)return;S[id==='rank'?'rank':id]=id==='year'?+v:v;if(id==='year')fillElec();render()});
$('elec').addEventListener('change',e=>{S.elec=e.target.value;render()});
$('minv').addEventListener('input',e=>{S.minv=Math.max(0,+e.target.value||0);render()});
$('minv').value=S.minv;fillElec();render();
</script></body></html>"""
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB)")

# %% [markdown]
# ## 3. Check the page's numbers
# Recompute one electorate's share ranking in Python and compare with notebook 11's logic for the same filters.

# %%
chk = booths.top_n(rows, "green", "pct", 100)
print(chk[(chk.election_year == 2026) & (chk.home_electorate == "Northcote")][["suburb", "green", "total", "pct", "home_pct"]].round(1).to_string(index=False))
