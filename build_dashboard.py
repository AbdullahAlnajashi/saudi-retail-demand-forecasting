"""Builds dashboard.html from results/dashboard_data.json (run analysis.py first)."""
import json, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))   # paths below are relative to this script's folder
with open("results/dashboard_data.json", encoding="utf-8") as f: D = f.read()
NOTES = {
 "iPhone": "Largest and most stable demand signal. Interest spikes every September (index ~1.3x) when new models launch, then stays elevated in October. Annual interest has been flat at about 50 since 2024, below its 2019-2020 peak. Action: align stock and promotions to the September launch window.",
 "Perfume": "Strongest structural growth: annual interest rose from about 6 (2015) to about 26 (2025-26). Peaks follow Ramadan/Eid, which move about 11 days earlier each year, so Gregorian-month averages blur the peak. No model beat last year's pattern, so the forecast repeats it. Action: build inventory before Ramadan/Eid; use the 80% range for safety stock.",
 "Bag": "Back-to-school product: July-August run 1.2-1.5x the average month. Interest grew about 4-5x since 2015 and has levelled off. Holt-Winters beat the baseline by about 32% on MAE. Action: stock bags in June for the July-August peak.",
 "Deep fryer": "Very low search volume (index 0-11, rounded to whole numbers), so forecasts are weak signals only. Interest appears only from 2020-21. A flat forecast was most accurate. Action: monitor, do not over-invest on this evidence alone.",
 "Firewood": "Clear winter product: November-January run 1.9-2.8x the average month, almost nothing in April-June. Values are tiny integers (0-4), so treat magnitudes as indicative. Action: winter-only stocking in the cold-season window."}
html = r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Retail Demand Decision Support - Google Trends, Saudi Arabia</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js" integrity="sha512-CQBWl4fJHWbryGE+Pc7UAxWMUMNMWzWxF4SQo9CgkJIN1kx6djDQZjh3Y8SZ1d+6I+1zze6Z7kHXO7q3UyZAWw==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
<style>:root{--bg:#fff;--fg:#1c1f24;--mu:#5d6570;--card:#f3f5f8;--bd:#d9dee5;--ac:#c0392b;--bl:#2c6fbb;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#15181c;--fg:#e8eaed;--mu:#a0a8b3;--card:#1f2429;--bd:#343b43;--ac:#ff7a6b;--bl:#6aa9ee}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,Arial,sans-serif;padding:16px;max-width:1100px;margin:auto}
h1{font-size:20px;margin:0 0 4px}.sub,.cap{color:var(--mu);font-size:13px}select{font-size:15px;padding:6px 10px;border-radius:8px;border:1px solid var(--bd);background:var(--card);color:var(--fg)}
.k{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}.c{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:10px 12px}.c b{display:block;font-size:20px}
.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:12px}.box{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:12px}.box canvas{max-height:260px}
.note{border-left:4px solid var(--ac);padding:8px 12px;background:var(--card);margin:12px 0;border-radius:6px}.w{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}td,th{border-bottom:1px solid var(--bd);padding:5px 8px;text-align:right}td:first-child,th:first-child{text-align:left}
@media(max-width:480px){.g{grid-template-columns:1fr}}</style></head><body>
<h1>Retail Demand Decision Support</h1><div class="sub">Google Trends search interest (index 0-100) as a demand proxy, Saudi Arabia, monthly 2015-2026. Interest is NOT unit sales. Indices of all 5 products share one common scale. IS 366 - Group Project 1.</div>
<p>Product: <select id="p"></select></p><div class="k" id="k"></div><div class="note" id="n"></div>
<div class="g"><div class="box"><b>1. History and 12-month forecast</b><div class="cap">Grey = actual history. Red = forecast (Nov 2026 - Oct 2027). Shaded = 80% range.</div><canvas id="c1"></canvas></div>
<div class="box"><b>2. Seasonality: which months are strongest</b><div class="cap">1.0 = average month. Above 1.0 = busier than normal.</div><canvas id="c2"></canvas></div>
<div class="box"><b>3. Accuracy check: last 12 months (not used for training)</b><div class="cap">Actual vs best model vs simple baseline (same month last year).</div><canvas id="c3"></canvas></div>
<div class="box"><b>4. Annual average interest, all products</b><div class="cap">Shows long-term growth and relative size.</div><canvas id="c4"></canvas></div></div>
<div class="box w" style="margin-top:12px"><b>5. Model comparison (3 rolling test years, 36 months)</b><div class="cap">Lower is better. MAE/RMSE in index points. MAPE shown only where volume is high enough (n/a otherwise). Selected = lowest MAE.</div><table id="t"></table></div>
<p class="cap">Method: models trained on Jan 2015 onward; tested on the last three 12-month windows. Forecast ranges use backtest RMSE (approximate). Assumes past patterns continue; search interest can differ from actual sales.</p>
<script>
const D=__D__,N=__N__,M=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],ps=Object.keys(D.hist),col=getComputedStyle(document.documentElement);let ch=[];
Chart.defaults.color=col.getPropertyValue("--mu").trim();Chart.defaults.borderColor=col.getPropertyValue("--bd").trim();
const sel=document.getElementById("p");ps.forEach(x=>sel.add(new Option(x,x)));
function mk(id,cfg){const c=new Chart(document.getElementById(id),cfg);ch.push(c);}
function run(){ch.forEach(c=>c.destroy());ch=[];const p=sel.value,h=D.hist[p],f=D.fc[p],b=D.bt[p],s=D.desc.find(r=>r.series==p),a=D.metrics.filter(r=>r.series==p);
const n=60,hd=h.d.slice(-n),hv=h.v.slice(-n),pad=Array(n-1).fill(null),all=hd.concat(f.d);
const pk=f.d[f.f.indexOf(Math.max(...f.f))],bm=a.find(r=>r.model==D.best[p]),bs=a.find(r=>r.model.includes("baseline"));
document.getElementById("k").innerHTML=[["Avg interest, last 12 mo",s.mean_last12],["Change vs prior 12 mo",s["yoy_change_%"]==null?"n/a":(s["yoy_change_%"]>0?"+":"")+s["yoy_change_%"]+"%"],["Rank (of 5)","#"+s.rank_last12],["Forecast peak month",Math.max(...f.f)==Math.min(...f.f)?"none (flat at "+f.f[0]+")":pk+" ("+Math.max(...f.f)+")"],["Selected model",D.best[p].replace(" (baseline)","")],["MAE vs baseline",bm.model==bs.model?"is the baseline":bm["MAE_vs_baseline_%"]+"%"]].map(x=>`<div class="c">${x[0]}<b>${x[1]}</b></div>`).join("");
document.getElementById("n").textContent=N[p];
const o={responsive:true,plugins:{legend:{labels:{boxWidth:12}}},scales:{x:{ticks:{maxTicksLimit:8}}}};
mk("c1",{type:"line",data:{labels:all,datasets:[{label:"Actual",data:hv.concat(Array(12).fill(null)),borderColor:"#888",pointRadius:0,borderWidth:1.5},{label:"Forecast",data:pad.concat([hv[n-1]],f.f),borderColor:"#c0392b",pointRadius:0,borderWidth:2},{label:"80% high",data:pad.concat([hv[n-1]],f.hi),borderColor:"transparent",backgroundColor:"rgba(192,57,43,.15)",pointRadius:0,fill:"+1"},{label:"80% low",data:pad.concat([hv[n-1]],f.lo),borderColor:"transparent",pointRadius:0,fill:false}]},options:o});
mk("c2",{type:"bar",data:{labels:M,datasets:[{label:"Seasonal index",data:D.seas[p],backgroundColor:D.seas[p].map(v=>v>=1.15?"#c0392b":"#2c6fbb")}]},options:{responsive:true,plugins:{legend:{display:false}}}});
mk("c3",{type:"line",data:{labels:b.d,datasets:[{label:"Actual",data:b.a,borderColor:"#888",borderWidth:2},{label:"Best model: "+D.best[p].replace(" (baseline)",""),data:b.best,borderColor:"#c0392b"},{label:"Baseline (last year)",data:b.base,borderColor:"#2c6fbb",borderDash:[5,4]}]},options:o});
mk("c4",{type:"line",data:{labels:D.annual.y,datasets:ps.map((x,i)=>({label:x,data:D.annual[x],borderWidth:x==p?3.5:1.2,pointRadius:0,borderColor:["#c0392b","#2c6fbb","#8e7cc3","#2e9e6b","#d4a017"][i]}))},options:o});
document.getElementById("t").innerHTML="<tr><th>Model</th><th>MAE</th><th>RMSE</th><th>MAPE %</th><th>MAE vs baseline</th></tr>"+a.map(r=>`<tr${r.model==D.best[p]?' style="font-weight:700"':""}><td>${r.model}${r.model==D.best[p]?" (selected)":""}</td><td>${r.MAE}</td><td>${r.RMSE}</td><td>${r["MAPE_%"]<0?"n/a":r["MAPE_%"]}</td><td>${r["MAE_vs_baseline_%"]}%</td></tr>`).join("");}
sel.onchange=run;run();
</script></body></html>'''
with open("dashboard.html", "w", encoding="utf-8") as f: f.write(html.replace("__D__", D).replace("__N__", json.dumps(NOTES)))
print(len(html) // 1024, "KB template")
