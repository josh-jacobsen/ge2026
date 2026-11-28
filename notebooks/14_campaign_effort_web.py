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
# # 14 – Campaign effort, week by week: a browsable web page
# Builds one self-contained HTML page (`data/geo/campaign_effort.html`, gitignored; open it in any browser, no server or internet
# needed) from the same weekly exports as notebook 13 (`src/campaign.py`).
#
# **Why this chart.** Effort is a count per week, and the question is "did 2026 look like 2023, week by week?". So:
# * **Small multiples**: one panel per seat, all on the same axes, so the four seats can be compared at a glance.
# * **x = weeks to election** (0 = election week, left = early). Calendar dates would not line the years up; this does
#   (2026 week N is 2023 week N−4, both elections on a Saturday).
# * **Side-by-side bars per week for 2023 and 2026** for counts. Bars suit counts per week and show the weeks with no effort
#   (a line would join them up and hide the bursts). **Lines** only for rates and cumulative share, where the points are connected by meaning.
# * The same greens as the party-vote bars in `green_electorates.html` (notebook 09): light green = 2023, dark green = 2026.
# * Rates are drawn only where the denominator is big enough (you set the minimum), so one call on a quiet week cannot look like a 100% contact rate.
#
# **On the page**: channel (door knocking, phone calls, or both added together), metric (attempts, contacts, meaningful interactions,
# contact rate, meaningful rate), weekly or cumulative, which seats and layout, shared or per-seat y axis, how many weeks to show,
# which years, and the minimum denominator for rates. Hover a week for exact values. The table underneath follows the same settings.
#
# **Sensitive**: the exports are internal campaign data. The page embeds them, so keep it local (it is gitignored under `data/geo/*.html`)
# and do not share or upload it.

# %%
import json, sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import campaign

OUT = ROOT / "data" / "geo" / "campaign_effort.html"
SEATS = list(campaign.SEATS.values())
CHANNELS = list(campaign.CHANNELS)          # door_knocking, phone_calls
YEARS = sorted(campaign.ELECTION_DATES)

# %% [markdown]
# ## 1. Data
# One row per seat × year × channel × week, through election week. Row format on the page:
# `[seat, year, channel, weeks to election, week start, attempts, contacts, meaningful]`.

# %%
eff = campaign.load_all()
rows = [[SEATS.index(r.seat), int(r.year), CHANNELS.index(r.channel), int(r.weeks_to_election), r.week_start.isoformat(),
         int(r.attempts), int(r.contacts), int(r.meaningful)] for r in eff.itertuples()]
data = {"seats": SEATS, "channels": [campaign.CHANNELS[c] for c in CHANNELS], "years": YEARS,
        "last": int(eff.weeks_to_election.max()), "rows": rows}
print(len(rows), "weekly rows; weeks to election 0 to", data["last"])
assert sum(r[5] for r in rows) == eff.attempts.sum()

# %% [markdown]
# ## 2. The page

# %%
HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campaign effort, week by week</title>
<style>
:root{--bg:#fbfbfa;--fg:#1d1d1d;--mute:#6b6b6b;--card:#fff;--line:#d9d9d6;--grid:#ececea;--y2023:#a8d5ba;--y2026:#1b7f4b;--accent:#2a6fdb}
@media (prefers-color-scheme:dark){:root{--bg:#161616;--fg:#ececec;--mute:#9a9a9a;--card:#1f1f1f;--line:#3a3a3a;--grid:#2b2b2b;--y2023:#a8d5ba;--y2026:#1b7f4b;--accent:#6fa3f5}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1200px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:0 0 2px}
.sub{color:var(--mute);margin:0 0 12px}
.warn{background:var(--card);border:1px solid var(--line);border-left:4px solid #d97706;border-radius:6px;padding:8px 12px;margin:0 0 12px;font-size:13px}
.controls{display:flex;flex-wrap:wrap;gap:10px 18px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin-bottom:12px}
.ctl{display:flex;flex-direction:column;gap:3px}
.ctl>label,.ctl>span.l{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute)}
select,input[type=number]{font:inherit;color:var(--fg);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:4px 6px}
input[type=number]{width:72px}
.seg{display:flex;border:1px solid var(--line);border-radius:6px;overflow:hidden}
.seg button{font:inherit;color:var(--fg);background:var(--bg);border:0;border-right:1px solid var(--line);padding:4px 10px;cursor:pointer}
.seg button:last-child{border-right:0}
.seg button[aria-pressed=true]{background:var(--accent);color:#fff}
.chk{display:flex;gap:10px;align-items:center;height:28px}
.chk label{display:flex;gap:4px;align-items:center;font-size:14px;text-transform:none;letter-spacing:0;color:var(--fg)}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px}
#grid{display:grid;gap:12px}
#grid.g2{grid-template-columns:repeat(2,minmax(0,1fr))}
#grid.g1{grid-template-columns:minmax(0,1fr)}
@media (max-width:760px){#grid.g2{grid-template-columns:minmax(0,1fr)}}
.panel{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.panel h2{font-size:14px;margin:0}
.panel .tot{font-size:12px;color:var(--mute);margin:0 0 2px}
svg{width:100%;height:auto;display:block}
svg text{fill:var(--mute);font-size:10px}
.axis{stroke:var(--line)}.gl{stroke:var(--grid)}
.hit{fill:transparent}.hit:hover{fill:rgba(128,128,128,.12)}
#tip{position:fixed;pointer-events:none;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px 8px;font-size:12px;box-shadow:0 2px 8px rgba(0,0,0,.2);display:none;z-index:5;max-width:260px}
#tip b{display:block;margin-bottom:2px}
table{border-collapse:collapse;width:100%;margin-top:12px;background:var(--card);border:1px solid var(--line);font-size:13px}
th,td{padding:4px 8px;border-bottom:1px solid var(--line);text-align:right}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}
th{color:var(--mute);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
tr.tt td{font-weight:600}
.note{color:var(--mute);font-size:12px;margin-top:8px}
</style></head><body><main>
<h1>Campaign effort, week by week</h1>
<p class="sub" id="sub"></p>
<p class="warn"><b>Sensitive.</b> Internal campaign data embedded in this file. Keep it local; do not share or upload it.</p>
<div class="controls" id="controls">
 <div class="ctl"><span class="l">Channel</span><div class="seg" id="ch"></div></div>
 <div class="ctl"><span class="l">Metric</span><select id="metric"></select></div>
 <div class="ctl"><span class="l">View</span><div class="seg" id="view"></div></div>
 <div class="ctl"><label for="seat">Seats</label><select id="seat"></select></div>
 <div class="ctl"><label for="yaxis">Y axis</label><select id="yaxis"><option value="shared">Same in every seat</option><option value="own">Each seat its own</option></select></div>
 <div class="ctl"><label for="range">Weeks shown</label><select id="range"></select></div>
 <div class="ctl"><span class="l">Years</span><div class="chk" id="years"></div></div>
 <div class="ctl"><label for="minN">Hide rates under</label><input type="number" id="minN" min="1" step="1" value="10"></div>
</div>
<div id="grid"></div>
<div id="tip"></div>
<table id="tbl"></table>
<p class="note" id="note"></p>
</main>
<script>
const D=__DATA__;
const $=id=>document.getElementById(id);
const fmt=n=>n==null?'–':Number(n).toLocaleString('en-NZ');
const METRICS={att:{label:'Attempts',kind:'count',f:'a'},con:{label:'Contacts',kind:'count',f:'c'},mi:{label:'Meaningful interactions',kind:'count',f:'m'},
  cr:{label:'Contact rate (contacts ÷ attempts)',kind:'rate',num:'c',den:'a'},mr:{label:'Meaningful rate (meaningful ÷ contacts)',kind:'rate',num:'m',den:'c'}};
const CH=[{k:'both',label:'Both'},{k:0,label:'Door knocking'},{k:1,label:'Phone calls'}];
const S={ch:'both',metric:'att',view:'weekly',seat:'grid2',yaxis:'shared',range:26,years:D.years.slice(),minN:10};
const RANGES=[['all','All weeks'],[36,'Last 36 weeks'],[26,'Last 26 weeks'],[12,'Last 12 weeks'],[6,'Last 6 weeks']];

// index: IDX[seat][year][week] = {a,c,m} for the chosen channel
function build(ch){
  const idx=D.seats.map(()=>({}));
  for(const r of D.rows){
    const [s,y,c,w,date,a,con,m]=r;
    if(ch!=='both'&&c!==ch)continue;
    const yy=idx[s][y]||(idx[s][y]={});
    const o=yy[w]||(yy[w]={a:0,c:0,m:0});
    o.a+=a;o.c+=con;o.m+=m;
  }
  return idx;
}
const maxWeek=()=>S.range==='all'?D.last:Math.min(D.last,S.range-1);
const weeksShown=()=>{const o=[];for(let w=maxWeek();w>=0;w--)o.push(w);return o};
const years=()=>D.years.filter(y=>S.years.includes(y));
const yClass=y=>y===D.years[0]?'y2023':'y2026';
const yColor=y=>'var(--'+yClass(y)+')';
function rateOf(rec,m){if(!rec)return null;const d=rec[m.den];if(!d)return null;return rec[m.num]/d}
function valueAt(idx,seat,y,w,metric){
  const m=METRICS[metric],rec=(idx[seat][y]||{})[w];
  if(m.kind==='count')return rec?rec[m.f]:0;
  if(!rec||rec[m.den]<S.minN)return null;
  return rateOf(rec,m)*100;
}
// cumulative % of the whole campaign (all weeks), for count metrics
function cumulative(idx,seat,y,metric){
  const m=METRICS[metric],ws=idx[seat][y]||{};
  let tot=0;for(const w in ws)tot+=ws[w][m.f];
  const out={};let run=0;
  for(let w=D.last;w>=0;w--){run+=ws[w]?ws[w][m.f]:0;out[w]=tot?run/tot*100:null}
  return out;
}
function niceMax(v){if(!(v>0))return 1;const p=Math.pow(10,Math.floor(Math.log10(v))),f=v/p;return(f<=1?1:f<=2?2:f<=2.5?2.5:f<=5?5:10)*p}
function ticks(max){const n=max<=2.5?5:4,st=max/n,out=[];for(let i=0;i<=n;i++)out.push(st*i);return out}
const tickFmt=(v,rate)=>rate?(Math.round(v*10)/10)+'%':fmt(Math.round(v*10)/10);

// the series each panel will draw: {y, vals:{w:number|null}}
function seriesFor(idx,seat){
  const m=METRICS[S.metric],cum=S.view==='cumulative'&&m.kind==='count';
  return years().map(y=>({y,vals:cum?cumulative(idx,seat,y,S.metric):Object.fromEntries(weeksShown().map(w=>[w,valueAt(idx,seat,y,w,S.metric)]))}));
}
function aggregate(idx,seat,y){            // totals over the visible weeks
  let a=0,c=0,mm=0;for(const w of weeksShown()){const r=(idx[seat][y]||{})[w];if(r){a+=r.a;c+=r.c;mm+=r.m}}
  return {a,c,m:mm};
}
function yMaxFor(idx,seats){
  const m=METRICS[S.metric],cum=S.view==='cumulative'&&m.kind==='count';
  if(cum)return 100;
  let mx=0;
  for(const s of seats)for(const sr of seriesFor(idx,s))for(const w of weeksShown()){const v=sr.vals[w];if(v!=null&&v>mx)mx=v}
  return niceMax(mx*1.04);
}
function panel(idx,seat,yMax,big){
  const m=METRICS[S.metric],cum=S.view==='cumulative'&&m.kind==='count',rate=m.kind==='rate'||cum;
  const W=big?900:460,H=big?380:250,L=46,R=8,T=8,B=34,pw=W-L-R,ph=H-T-B;
  const ws=weeksShown(),n=ws.length,slot=pw/n,ys=years(),sr=seriesFor(idx,seat);
  const mx=yMax||yMaxFor(idx,[seat]);
  const X=i=>L+slot*i+slot/2,Y=v=>T+ph-(v/mx)*ph;
  let s='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+D.seats[seat]+'">';
  for(const t of ticks(mx)){const y=Y(t);s+='<line class="gl" x1="'+L+'" x2="'+(W-R)+'" y1="'+y+'" y2="'+y+'"/><text x="'+(L-5)+'" y="'+(y+3)+'" text-anchor="end">'+tickFmt(t,rate)+'</text>'}
  s+='<line class="axis" x1="'+L+'" x2="'+(W-R)+'" y1="'+(T+ph)+'" y2="'+(T+ph)+'"/>';
  const every=n>30?5:n>14?2:1;
  ws.forEach((w,i)=>{if(w%every===0||w===0)s+='<text x="'+X(i)+'" y="'+(H-B+13)+'" text-anchor="middle">'+w+'</text>'});
  s+='<text x="'+(L+pw/2)+'" y="'+(H-4)+'" text-anchor="middle">weeks to election (0 = election week)</text>';
  if(rate){
    for(const q of sr){
      let d='',pen=false,dots='';
      ws.forEach((w,i)=>{const v=q.vals[w];if(v==null){pen=false;return}d+=(pen?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1);pen=true;dots+='<circle cx="'+X(i).toFixed(1)+'" cy="'+Y(v).toFixed(1)+'" r="2.6" fill="'+yColor(q.y)+'"/>'});
      s+='<path d="'+d+'" fill="none" stroke="'+yColor(q.y)+'" stroke-width="1.6"/>'+dots;
    }
  }else{
    const bw=Math.max(1,slot*0.82/Math.max(1,sr.length));
    ws.forEach((w,i)=>sr.forEach((q,k)=>{
      const v=q.vals[w];if(!v)return;
      const h=(v/mx)*ph,x=L+slot*i+slot*0.09+bw*k;
      s+='<rect x="'+x.toFixed(1)+'" y="'+(T+ph-h).toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+h.toFixed(1)+'" fill="'+yColor(q.y)+'"/>';
    }));
  }
  ws.forEach((w,i)=>{s+='<rect class="hit" data-seat="'+seat+'" data-w="'+w+'" x="'+(L+slot*i).toFixed(1)+'" y="'+T+'" width="'+slot.toFixed(1)+'" height="'+ph+'"/>'});
  return s+'</svg>';
}
function totalsLine(idx,seat){
  const m=METRICS[S.metric];
  return years().map(y=>{
    const g=aggregate(idx,seat,y);
    const v=m.kind==='count'?fmt(g[m.f]):(g[m.den]?(g[m.num]/g[m.den]*100).toFixed(1)+'%':'–');
    return '<span class="sw" style="background:'+yColor(y)+'"></span> '+y+': <b>'+v+'</b>';
  }).join(' &nbsp; ');
}
function seatsShown(){return S.seat.startsWith('grid')?D.seats.map((_,i)=>i):[Number(S.seat)]}
function render(){
  const idx=build(S.ch),seats=seatsShown(),m=METRICS[S.metric];
  const cumOk=m.kind==='count';
  const view=cumOk?S.view:'weekly';
  const savedView=S.view;S.view=view;
  const shared=S.yaxis==='shared'?yMaxFor(idx,seats):null;
  const big=seats.length===1||S.seat==='grid1';
  const g=$('grid');g.className=seats.length===1||S.seat==='grid1'?'g1':'g2';
  g.innerHTML=seats.map(s=>'<div class="panel"><h2>'+D.seats[s]+'</h2><p class="tot">'+(view==='cumulative'?'cumulative share of the campaign':(m.kind==='count'?'total':'overall'))+' '+totalsLine(idx,s)+'</p>'+panel(idx,s,shared,big)+'</div>').join('');
  S.view=savedView;
  const chLabel=CH.find(c=>c.k===S.ch).label.toLowerCase();
  $('sub').textContent=m.label+(view==='cumulative'?', cumulative % of the campaign':', per week')+' · '+chLabel+' · '+years().join(' vs ')+' · '+(S.range==='all'?'all weeks':'last '+S.range+' weeks')+', through election week';
  document.querySelectorAll('#view button').forEach(b=>{b.disabled=!cumOk&&b.dataset.v==='cumulative'});
  $('note').textContent=(m.kind==='rate'?'Rates hidden where the week has fewer than '+S.minN+' '+(S.metric==='cr'?'attempts':'contacts')+'. ':'')+
    'Both elections were on a Saturday, so 2026 week N lines up with 2023 week N−4. A missing week means no activity was recorded. Door-knocking exports end 1 to 2 weeks before election week.';
  table(idx,seats);
}
function table(idx,seats){
  const ys=years();
  let h='<tr><th>Seat</th><th>Year</th><th>Attempts</th><th>Contacts</th><th>Meaningful</th><th>Contact %</th><th>Meaningful %</th></tr>';
  const row=(name,y,g,cls)=>'<tr class="'+cls+'"><td>'+name+'</td><td>'+y+'</td><td>'+fmt(g.a)+'</td><td>'+fmt(g.c)+'</td><td>'+fmt(g.m)+'</td><td>'+(g.a?(g.c/g.a*100).toFixed(1)+'%':'–')+'</td><td>'+(g.c?(g.m/g.c*100).toFixed(1)+'%':'–')+'</td></tr>';
  const tot={};ys.forEach(y=>tot[y]={a:0,c:0,m:0});
  for(const s of seats)for(const y of ys){const g=aggregate(idx,s,y);h+=row(D.seats[s],y,g,'');tot[y].a+=g.a;tot[y].c+=g.c;tot[y].m+=g.m}
  if(seats.length>1)for(const y of ys)h+=row('Four seats',y,tot[y],'tt');
  $('tbl').innerHTML=h;
}
function tipFor(seat,w,ev){
  const idx=build(S.ch),m=METRICS[S.metric],cum=S.view==='cumulative'&&m.kind==='count';
  let h='<b>'+D.seats[seat]+' · '+(w===0?'election week':w+' week'+(w===1?'':'s')+' before')+'</b>';
  for(const y of years()){
    const rec=(idx[seat][y]||{})[w]||{a:0,c:0,m:0};
    const cr=rec.a?(rec.c/rec.a*100).toFixed(0)+'%':'–',mr=rec.c?(rec.m/rec.c*100).toFixed(0)+'%':'–';
    const wk=(D.rows.find(r=>r[0]===seat&&r[1]===y&&r[3]===w&&(S.ch==='both'||r[2]===S.ch))||[])[4];
    h+='<div><span class="sw" style="background:'+yColor(y)+'"></span> '+y+(wk?' (w/c '+wk.slice(5)+')':'')+': '+fmt(rec.a)+' attempts, '+fmt(rec.c)+' contacts ('+cr+'), '+fmt(rec.m)+' meaningful ('+mr+')</div>';
  }
  const t=$('tip');t.innerHTML=h;t.style.display='block';
  const x=Math.min(ev.clientX+14,window.innerWidth-280),y=ev.clientY+14;t.style.left=x+'px';t.style.top=y+'px';
}
function seg(id,items,key,onchange){
  const el=$(id);el.innerHTML=items.map(i=>'<button type="button" data-v="'+i.k+'" aria-pressed="'+(String(S[key])===String(i.k))+'">'+i.label+'</button>').join('');
  el.onclick=e=>{const b=e.target.closest('button');if(!b||b.disabled)return;S[key]=isNaN(b.dataset.v)||b.dataset.v===''?b.dataset.v:Number(b.dataset.v);
    el.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));onchange()};
}
function init(){
  seg('ch',CH,'ch',render);
  seg('view',[{k:'weekly',label:'Weekly'},{k:'cumulative',label:'Cumulative %'}],'view',render);
  $('metric').innerHTML=Object.entries(METRICS).map(([k,m])=>'<option value="'+k+'">'+m.label+'</option>').join('');
  $('seat').innerHTML='<option value="grid2">All four (2 × 2)</option><option value="grid1">All four (one column)</option>'+D.seats.map((s,i)=>'<option value="'+i+'">'+s+' only (large)</option>').join('');
  $('range').innerHTML=RANGES.map(r=>'<option value="'+r[0]+'">'+r[1]+'</option>').join('');$('range').value=String(S.range);
  $('years').innerHTML=D.years.map(y=>'<label><input type="checkbox" value="'+y+'" checked><span class="sw" style="background:'+yColor(y)+'"></span>'+y+'</label>').join('');
  $('metric').onchange=e=>{S.metric=e.target.value;render()};
  $('seat').onchange=e=>{S.seat=e.target.value;render()};
  $('yaxis').onchange=e=>{S.yaxis=e.target.value;render()};
  $('range').onchange=e=>{S.range=e.target.value==='all'?'all':Number(e.target.value);render()};
  $('minN').onchange=e=>{S.minN=Math.max(1,Number(e.target.value)||1);render()};
  $('years').onchange=()=>{const on=[...document.querySelectorAll('#years input')].filter(i=>i.checked).map(i=>Number(i.value));
    if(!on.length){document.querySelector('#years input').checked=true;return}S.years=on;render()};
  const g=$('grid');
  g.addEventListener('mousemove',e=>{const h=e.target.closest&&e.target.closest('.hit');if(h)tipFor(Number(h.dataset.seat),Number(h.dataset.w),e);else $('tip').style.display='none'});
  g.addEventListener('mouseleave',()=>{$('tip').style.display='none'});
  render();
}
if(typeof document!=='undefined'&&document.getElementById)init();
</script></body></html>"""
payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KB)")
