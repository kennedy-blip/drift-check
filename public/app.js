const $ = (selector) => document.querySelector(selector);
const state = { datasets: [], active: null, result: null, api: false };
const sample = {
  id: "mpesa-checkout-batch", name: "M-Pesa checkout latency",
  description: "Checkout amount, latency, and payment channel telemetry",
  baseline: [
    {amount_kes:850,latency_ms:420,channel:"STK_PUSH",merchant:"retail",receipt:"RCP-1001"},
    {amount_kes:1200,latency_ms:390,channel:"STK_PUSH",merchant:"retail",receipt:"RCP-1002"},
    {amount_kes:560,latency_ms:460,channel:"WEB",merchant:"fuel",receipt:"RCP-1003"},
    {amount_kes:2400,latency_ms:510,channel:"STK_PUSH",merchant:"retail",receipt:"RCP-1004"},
    {amount_kes:700,latency_ms:405,channel:"WEB",merchant:"food",receipt:"RCP-1005"},
    {amount_kes:1500,latency_ms:435,channel:"STK_PUSH",merchant:"fuel",receipt:"RCP-1006"}
  ],
  candidate: [
    {amount_kes:900,latency_ms:445,channel:"STK_PUSH",merchant:"retail",receipt:"RCP-2001"},
    {amount_kes:1150,latency_ms:470,channel:"STK_PUSH",merchant:"retail",receipt:"RCP-2002"},
    {amount_kes:610,latency_ms:490,channel:"WEB",merchant:"fuel",receipt:"RCP-2003"},
    {amount_kes:2550,latency_ms:530,channel:"STK_PUSH",merchant:"retail",receipt:"RCP-2004"},
    {amount_kes:730,latency_ms:455,channel:"WEB",merchant:"food",receipt:"RCP-2005"},
    {amount_kes:1600,latency_ms:480,channel:"STK_PUSH",merchant:"fuel",receipt:"RCP-2006"}
  ], fieldRules: {}, lastDriftScore: 12
};
const esc = (value) => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function toast(message) { const node=$("#toast"); node.textContent=message; node.classList.add("show"); setTimeout(()=>node.classList.remove("show"),2600); }
function parseEditor(id) { const value=$(id).value; const parsed=JSON.parse(value); if(!Array.isArray(parsed)||!parsed.length||!parsed.every(x=>x&&typeof x==="object"&&!Array.isArray(x))) throw new Error("Each editor must contain a non-empty JSON array of objects."); return parsed; }
function setDataset(dataset) {
  state.active=dataset;
  $("#baseline-editor").value=JSON.stringify(dataset.baseline,null,2);
  $("#candidate-editor").value=JSON.stringify(dataset.candidate,null,2);
  $("#baseline-count").textContent=dataset.baseline.length+" RECORDS";
  $("#candidate-count").textContent=dataset.candidate.length+" RECORDS";
  $("#dataset-select").value=dataset.id;
  state.result=null; renderResult(null);
}
function renderRegistry() {
  $("#registry-count").textContent=state.datasets.length+" SNAPSHOTS";
  $("#registry").innerHTML=state.datasets.map(d=>`<article class="registry-card" data-id="${esc(d.id)}"><h3>${esc(d.name)}</h3><p>${esc(d.description||"Saved dataset snapshot")}</p><div class="registry-foot"><span>${d.baseline.length} BASELINE / ${d.candidate.length} CANDIDATE</span><span>${d.lastDriftScore==null?"NOT RUN":d.lastDriftScore+" SCORE"}</span></div></article>`).join("");
  $("#dataset-select").innerHTML=state.datasets.map(d=>`<option value="${esc(d.id)}">${esc(d.name)}</option>`).join("");
  $("#registry").querySelectorAll("[data-id]").forEach(card=>card.addEventListener("click",()=>{const d=state.datasets.find(x=>x.id===card.dataset.id);if(d){setDataset(d);toast("Snapshot loaded");}}));
}
function renderResult(result) {
  state.result=result;
  const badge=$("#health-badge"), score=$("#hero-score"), bar=$("#score-bar");
  if(!result){badge.className="badge neutral";badge.textContent="AWAITING ANALYSIS";score.textContent="—";bar.style.width="0%";$("#score-caption").textContent="Run an analysis to establish a signal";$("#field-count").textContent="NO RESULTS";$("#diagnostics").className="diagnostics empty-state";$("#diagnostics").innerHTML='<div class="empty-icon">⌁</div><b>Waiting for your first analysis</b><span>Run drift analysis to inspect field-level signals.</span>';return;}
  const statusClass=result.status==="HEALTHY"?"healthy":result.status==="WARNING"?"warning":"drift";
  badge.className="badge "+statusClass;badge.textContent=result.status;score.textContent=result.driftScore;bar.style.width=result.driftScore+"%";bar.style.background=result.driftScore>=55?"var(--rose)":result.driftScore>0?"var(--amber)":"var(--green)";
  $("#score-caption").textContent=result.summary.fieldsWithDrift+" of "+result.summary.fieldsChecked+" fields showing signals";
  $("#field-count").textContent=result.fields.length+" FIELDS ANALYZED";
  $("#diagnostics").className="diagnostics";
  $("#diagnostics").innerHTML=result.fields.map(f=>{const cls=f.status==="HEALTHY"?"healthy":f.status==="WARNING"?"warning":"drift";const metrics=f.type==="numeric"?[
    ["BASELINE MEAN",f.baselineMean],["CANDIDATE MEAN",f.candidateMean],["STD DEV SHIFT",f.stdDevShiftPct+"%"],["Z-SCORE",f.zScore]
  ]:[["BASELINE UNIQUE",f.baselineUnique],["CANDIDATE UNIQUE",f.candidateUnique],["DISTRIBUTION SHIFT",f.distributionShiftPct+"%"],["UNSEEN VALUES",(f.unseenValues||[]).length]];
  metrics.push(["NULL RATE Δ",f.nullDeltaPct+"%"],["BASELINE NULL",f.baselineNullPct+"%"]);
  return `<article class="field-card"><div class="field-top"><div><div class="field-name">${esc(f.field)}</div><div class="field-type">${esc(f.type)} FIELD · SEVERITY ${f.severity}/100</div></div><span class="field-status ${cls}">${f.status}</span></div><div class="metric-grid">${metrics.map(m=>`<div class="metric"><span>${m[0]}</span><b class="${m[0].includes("Z-SCORE")||m[0].includes("STD DEV")?"violet-text":""}">${esc(m[1]??"—")}</b></div>`).join("")}</div>${f.issues.length?`<ul class="issue-list">${f.issues.map(i=>`<li>${esc(i)}</li>`).join("")}</ul>`:'<div class="issue-list healthy-text">No material drift detected</div>'}${f.unseenValues?.length?`<div class="field-type">UNSEEN: ${f.unseenValues.map(esc).join(", ")}</div>`:""}</article>`;
  }).join("");
}
function fallbackAnalyze(baseline,candidate,threshold,nullLimit) {
  const keys=[...new Set([...baseline.flatMap(Object.keys),...candidate.flatMap(Object.keys)])].sort();
  const fields=keys.map(key=>{
    const b=baseline.map(r=>r[key]??null),a=candidate.map(r=>r[key]??null),bn=b.filter(x=>x!==null),an=a.filter(x=>x!==null);
    const numeric=[...bn,...an].length>0&&[...bn,...an].every(x=>typeof x==="number"&&Number.isFinite(x));
    const bNull=b.filter(x=>x===null).length/b.length*100,aNull=a.filter(x=>x===null).length/a.length*100;
    let severity=0,issues=[],metrics={};
    if(numeric){const mean=x=>x.length?x.reduce((s,v)=>s+v,0)/x.length:0,sd=x=>x.length>1?Math.sqrt(x.reduce((s,v)=>s+(v-mean(x))**2,0)/x.length):0;const bm=mean(bn),am=mean(an),bs=sd(bn),as=sd(an),z=Math.abs(am-bm)/(bs||Math.max(Math.abs(bm)*.01,1)),shift=bs>1e-9?Math.abs(as-bs)/bs*100:(as?100:0);Object.assign(metrics,{baselineMean:+bm.toFixed(4),candidateMean:+am.toFixed(4),baselineStdDev:+bs.toFixed(4),candidateStdDev:+as.toFixed(4),zScore:+z.toFixed(4),stdDevShiftPct:+shift.toFixed(2)});if(z>=threshold){issues.push("Mean shift exceeds Z-score threshold");severity+=Math.min(45,15+z*5)}if(shift>=50){issues.push("Population standard deviation changed materially");severity+=Math.min(20,shift/5)}if(bn.length&&an.some(v=>v<Math.min(...bn)||v>Math.max(...bn))){issues.push("Candidate value outside baseline observed range");severity+=15}}
    else{const bc={},ac={};bn.forEach(v=>bc[String(v)]=(bc[String(v)]||0)+1);an.forEach(v=>ac[String(v)]=(ac[String(v)]||0)+1);const unseen=Object.keys(ac).filter(v=>!(v in bc));const all=new Set([...Object.keys(ac),...Object.keys(bc)]);const tvd=.5*[...all].reduce((s,k)=>s+Math.abs((bc[k]||0)/(bn.length||1)-(ac[k]||0)/(an.length||1)),0);Object.assign(metrics,{baselineUnique:Object.keys(bc).length,candidateUnique:Object.keys(ac).length,unseenValues:unseen,distributionShiftPct:+(tvd*100).toFixed(2)});if(unseen.length){issues.push("Unseen categorical values detected");severity+=Math.min(35,15+unseen.length*5)}if(tvd>=.25){issues.push("Categorical distribution shifted");severity+=Math.min(25,tvd*40)}}
    const delta=aNull-bNull;if(delta>nullLimit){issues.push("Null rate increased beyond configured limit");severity+=Math.min(40,15+delta-nullLimit)}if(!an.length){issues.push("Candidate field contains no non-null values");severity+=35}if(b.some((_,i)=>!(key in baseline[i]))||candidate.some(r=>!(key in r))){issues.push("Field missing from one or more records");severity+=20}
    Object.assign(metrics,{baselineNullPct:+bNull.toFixed(2),candidateNullPct:+aNull.toFixed(2),nullDeltaPct:+delta.toFixed(2),type:numeric?"numeric":"categorical"});
    severity=Math.min(100,severity);return {field:key,severity:+severity.toFixed(2),status:severity>=55?"DRIFT_DETECTED":severity>0?"WARNING":"HEALTHY",issues:[...new Set(issues)],...metrics};
  });
  const driftScore=Math.round(fields.reduce((s,f)=>s+f.severity,0)/(fields.length||1));
  return {status:driftScore>=55||fields.some(f=>f.status==="DRIFT_DETECTED")?"DRIFT_DETECTED":driftScore>0?"WARNING":"HEALTHY",driftScore,summary:{baselineRecords:baseline.length,candidateRecords:candidate.length,fieldsChecked:fields.length,fieldsWithDrift:fields.filter(f=>f.status!=="HEALTHY").length},fields};
}
async function loadDatasets() {
  try{const response=await fetch("/api/datasets");if(!response.ok)throw new Error("API unavailable");const data=await response.json();state.datasets=data.datasets;state.api=true;$("#engine-status").textContent="Active";$("#engine-status").style.color="var(--green)";}
  catch{state.api=false;state.datasets=[sample];$("#engine-status").textContent="Offline fallback";$("#engine-status").style.color="var(--amber)";toast("Python API unavailable — browser fallback enabled");}
  renderRegistry();setDataset(state.datasets[0]||sample);
}
async function runAnalysis() {
  const button=$("#run-analysis");button.disabled=true;button.textContent="Analyzing…";
  try{
    const baselineRecords=parseEditor("#baseline-editor"),candidateRecords=parseEditor("#candidate-editor");
    const payload={datasetId:state.active?.id,baselineRecords,candidateRecords,zScoreThreshold:Number($("#z-threshold").value),maxNullDeltaPct:Number($("#null-threshold").value)};
    let result;
    if(state.api){const response=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});if(!response.ok){const error=await response.json();throw new Error(error.error||"Analysis request failed")}result=await response.json();}
    else result=fallbackAnalyze(baselineRecords,candidateRecords,payload.zScoreThreshold,payload.maxNullDeltaPct);
    renderResult(result);toast("Analysis complete · "+result.status);
  }catch(error){toast(error.message||"Unable to analyze this batch");}
  finally{button.disabled=false;button.innerHTML="<span>▶</span> Run drift analysis";}
}
$("#run-analysis").addEventListener("click",runAnalysis);
$("#z-threshold").addEventListener("input",e=>$("#z-value").textContent=Number(e.target.value).toFixed(1));
$("#null-threshold").addEventListener("input",e=>$("#null-value").textContent=e.target.value+"%");
$("#dataset-select").addEventListener("change",e=>{const d=state.datasets.find(x=>x.id===e.target.value);if(d)setDataset(d)});
$("#load-preset").addEventListener("click",()=>{const d=state.datasets.find(x=>x.id==="mpesa-checkout-batch")||state.datasets[0]||sample;setDataset(d);toast("Preset dataset loaded")});
$("#inject-anomaly").addEventListener("click",()=>{try{const data=parseEditor("#candidate-editor");const first=data[0];const numeric=Object.keys(first).find(k=>typeof first[k]==="number");if(numeric)data.forEach((r,i)=>{if(typeof r[numeric]==="number")r[numeric]=r[numeric]* (i%2?5:8)});else data.forEach(r=>r.source="unexpected_partner");$("#candidate-editor").value=JSON.stringify(data,null,2);$("#candidate-count").textContent=data.length+" RECORDS";toast("Anomaly injected into candidate batch");}catch(e){toast(e.message)}});
$("#save-snapshot").addEventListener("click",async()=>{try{const baseline=parseEditor("#baseline-editor"),candidate=parseEditor("#candidate-editor"),name=prompt("Name this snapshot:","Custom production snapshot");if(!name)return;const item={id:"local-"+Date.now(),name,description:"Browser-saved snapshot",baseline,candidate,lastDriftScore:state.result?.driftScore??null};if(state.api){const response=await fetch("/api/datasets",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name,baseline,candidate})});if(!response.ok)throw new Error((await response.json()).error||"Save failed");item.id=(await response.json()).dataset.id;}state.datasets.unshift(item);renderRegistry();setDataset(item);toast("Snapshot saved in this session");}catch(e){toast(e.message)}});
loadDatasets();
