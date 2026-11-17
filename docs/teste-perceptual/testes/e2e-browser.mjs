/** E2E Chrome DevTools QA: fake local answers only, never sent to real server. */
const origin="http://127.0.0.1:8767/teste-perceptual/";
const pages=await fetch("http://127.0.0.1:9223/json/list").then(r=>r.json());
const url=pages.find(p=>p.type==="page")?.webSocketDebuggerUrl;
if(!url)throw Error("CDP page not found");
const ws=new WebSocket(url);
await new Promise((resolve,reject)=>{
  ws.addEventListener("open",resolve,{once:true});
  ws.addEventListener("error",reject,{once:true});
});
let id=0;const waits=new Map();const errors=[];
ws.addEventListener("message",evt=>{
  const m=JSON.parse(evt.data);
  if(m.id&&waits.has(m.id)){
    const p=waits.get(m.id);waits.delete(m.id);
    m.error?p.reject(Error(m.error.message)):p.resolve(m.result);
  }
  if(m.method==="Runtime.exceptionThrown")errors.push(m.params.exceptionDetails.text);
});
function cdp(method,params={}){
  const mid=++id;
  return new Promise((resolve,reject)=>{
    waits.set(mid,{resolve,reject});
    ws.send(JSON.stringify({id:mid,method,params}));
  });
}
async function js(expression){
  const out=await cdp("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});
  if(out.exceptionDetails)throw Error(JSON.stringify(out.exceptionDetails));
  return out.result.value;
}
const sleep=(n)=>new Promise(r=>setTimeout(r,n));
async function load(){
  for(let i=0;i<40;i++){
    if(await js("document.readyState==='complete'&&!!document.getElementById('begin')"))return;
    await sleep(100);
  }
  throw Error("Page load timed out");
}
const choose="var p=document.getElementById('participant');p.value='augusto';p.dispatchEvent(new Event('change',{bubbles:true}));var c=document.getElementById('consent');c.checked=true;c.dispatchEvent(new Event('change',{bubbles:true}));document.getElementById('begin').click();";
await cdp("Page.enable");await cdp("Runtime.enable");
await cdp("Page.navigate",{url:origin});await sleep(400);await load();
// Isolated headless QA profile only: reset simulated data, never real-user responses.
await js("localStorage.removeItem('voice-control-perceptual-w261-v1::augusto')");
let state=await js("(function(){"+choose+"return {active:!document.getElementById('test').hidden,scene:document.getElementById('test-title').textContent};})()");
if(!state.active||!state.scene.includes("Trecho 01"))throw Error("Start failed "+JSON.stringify(state));
console.log("START",JSON.stringify(state));
async function completeScene(n){
  for(let j=0;j<3;j++){
    await js("document.querySelectorAll('.audio-card .play')["+j+"].click();");
    await sleep(350);
    const p=await js("(function(){var c=document.querySelectorAll('.audio-card')["+j+"];return {ready:c.querySelector('audio').readyState,error:c.querySelector('.audio-error').textContent};})()");
    if(p.ready<1||p.error)throw Error("Audio unavailable "+JSON.stringify({n,j,p}));
    await js("document.querySelectorAll('.audio-card .play')["+j+"].click();");
  }
  const result=await js("(function(){"+
    "for(const q of [['intelligibility','A'],['naturalness','B'],['noise','empate'],['preferred','C']])document.querySelector('button[data-question=\"'+q[0]+'\"][data-value=\"'+q[1]+'\"]').click();"+
    "for(const v of [['speech','sim'],['overlap','sim'],['motorcycle','incerto']])document.querySelector('[data-field=\"'+v[0]+'\"] button[data-value=\"'+v[1]+'\"]').click();"+
    "var note=document.getElementById('remark');note.value='QA sintético, não participação real';note.dispatchEvent(new Event('input',{bubbles:true}));"+
    "return {disabled:document.getElementById('next').disabled,played:document.querySelectorAll('.audio-card').length};})()");
  if(result.disabled)throw Error("Required answers did not validate "+JSON.stringify(result));
  await js("document.getElementById('next').click();");
  console.log("SCENE_OK",n);
}
await completeScene(1);
await cdp("Page.reload",{ignoreCache:true});await sleep(450);await load();
const scene=await js("(function(){"+choose+"return document.getElementById('test-title').textContent;})()");
if(!scene.includes("Trecho 02"))throw Error("Reload resume failed "+scene);
console.log("RELOAD_RESUMED",scene);
await completeScene(2);
await completeScene(3);
const result=await js("(function(){var x=JSON.parse(localStorage.getItem('voice-control-perceptual-w261-v1::augusto'));return {finished:!document.getElementById('finish').hidden,submitDisabled:document.getElementById('send').disabled,scenes:Object.keys(x.sceneAnswers).length,allPlayed:Object.values(x.sceneAnswers).every(v=>v.listened.length===3),completion:x.completedAt,receipt:x.receipt};})()");
if(!result.finished||!result.submitDisabled||result.scenes!==3||!result.allPlayed||!result.completion||result.receipt)throw Error("Finish invalid "+JSON.stringify(result));
console.log("FINISH",JSON.stringify(result));
console.log("JS_EXCEPTIONS",JSON.stringify(errors));
ws.close();
if(errors.length)process.exitCode=1;
