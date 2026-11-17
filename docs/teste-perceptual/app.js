(() => {
  "use strict";
  const CFG = window.VOICE_CONTROL_PERCEPTUAL;
  if (!CFG) throw new Error("Instrumento ausente: config.js");
  const $ = (id) => document.getElementById(id);
  const KEY = (participant) => CFG.storagePrefix + "::" + participant;
  const LABELS = ["A", "B", "C"];
  const PERMUTATIONS = [[0,1,2],[1,2,0],[2,0,1]];
  const VOTE_CHOICES = [...LABELS, "empate", "nao_avaliavel"];
  let participant = "";
  let currentIndex = 0;
  let state = null;
  let playing = null;
  let audios = [];
  let lastSave = null;
  let storageOkay = true;
  let submitting = false;
  let privateMedia = null;
  const userParams = new URLSearchParams(location.search);
  // Tokens somente no fragmento (#), fora do HTTP request e de logs do servidor.
  const invite = new URLSearchParams(location.hash.slice(1)).get("convite") || "";
  const participantIndex = (id) => CFG.people.findIndex(p => p.id === id);

  const esc = (s) => String(s || "").replace(/[&<>"']/g, ch => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[ch]));
  const formatTime = (s) => {
    const n = Math.max(0, Math.floor(Number(s)||0));
    return String(Math.floor(n/60)).padStart(2,"0")+":"+String(n%60).padStart(2,"0");
  };
  const now = () => new Date().toISOString();
  function fresh(person){
    return {
      schemaVersion:CFG.schemaVersion,
      studyId:CFG.studyId,
      participantId:person,
      sessionId:crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2),
      startedAt:now(), updatedAt:now(), completedAt:null,
      consent:true, sceneAnswers:{}, receipt:null
    };
  }
  function loadLocal(person){
    try {
      const raw = localStorage.getItem(KEY(person));
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (data.studyId !== CFG.studyId || data.schemaVersion !== CFG.schemaVersion ||
          data.participantId !== person || !data.sessionId ||
          typeof data.sceneAnswers !== "object" || data.sceneAnswers === null) return null;
      return data;
    } catch (err){console.warn("Não foi possível ler sessão local",err);return null;}
  }
  function status(msg,mode="local"){
    $("save-text").textContent = msg;
    $("status").dataset.mode = mode;
    const dot = $("status").querySelector(".status-dot");
    dot.style.background = mode==="error" ? "#ff888b" : mode==="remote" ? "#40d29a" : "#ffb86f";
    $("save-time").textContent = lastSave ? "Atualizado " + lastSave : "";
  }
  function persist(){
    if (!state) return false;
    state.updatedAt = now();
    try {
      localStorage.setItem(KEY(participant),JSON.stringify(state));
      storageOkay = true;
      lastSave = new Date().toLocaleTimeString("pt-BR",{hour:"2-digit",minute:"2-digit"});
      if (state.receipt) status("Resposta confirmada no servidor. Também salva neste navegador.","remote");
      else status("Rascunho salvo neste navegador · envio remoto ainda não confirmado.");
      return true;
    }catch(err){
      storageOkay = false;
      status("Armazenamento local indisponível. Exporte suas respostas ao terminar.","error");
      return false;
    }
  }
  function order(sceneIndex){
    return PERMUTATIONS[(participantIndex(participant) + sceneIndex) % 3];
  }
  function sceneState(sceneIndex){
    const id=CFG.scenes[sceneIndex].id;
    if(!state.sceneAnswers[id]){
      state.sceneAnswers[id]={
        votes:{}, speech:null, overlap:null, motorcycle:null,
        note:"", listened:[], playbackSeconds:{}, sceneUpdatedAt:null
      };
    }
    return state.sceneAnswers[id];
  }
  function view(id){
    ["welcome","test","finish"].forEach(k=>$(k).hidden=k!==id);
    window.scrollTo({top:0,behavior:"instant"});
    document.title = id==="test" ? "Trecho "+(currentIndex+1)+" de 3 · Voice Control" :
      "Escuta perceptual · Voice Control | PTC 3528";
  }
  function btnGlyph(paused){
    return paused
      ? '<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M6 3.8 16.2 10 6 16.2V3.8Z"/></svg>'
      : '<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><rect x="4" y="3.5" width="4" height="13" rx="1"/><rect x="12" y="3.5" width="4" height="13" rx="1"/></svg>';
  }
  function stopPlayers(except){
    for(const a of audios) if(a!==except&&!a.paused)a.pause();
    if(!except) playing=null;
  }
  function markListened(sampleIndex){
    const scene=sceneState(currentIndex);
    if(!scene.listened.includes(sampleIndex)) scene.listened.push(sampleIndex);
    scene.sceneUpdatedAt=now();
    persist();
    enableNext();
  }
  async function preparePrivateMedia(){
    if(!CFG.backend.enabled || !CFG.backend.url)return;
    if(privateMedia)return;
    if(!invite)throw new Error("Este link não contém o convite individual necessário.");
    const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),16000);
    try {
      const response=await fetch(CFG.backend.url+"?op=media&participant="+encodeURIComponent(participant),{
        method:"GET",headers:{"X-Invite":invite},mode:"cors",
        redirect:"error",signal:controller.signal
      });
      if(!response.ok)throw new Error("Acesso privado indisponível (HTTP "+response.status+").");
      const data=await response.json();
      if(data.ok!==true||!data.files||typeof data.files!=="object")
        throw new Error("O servidor não confirmou os arquivos privados.");
      for(const scene of CFG.scenes)for(const relative of scene.files) {
        const name=relative.split("/").pop();
        if(!/^c0[1-3]_s0[1-3]\.wav$/.test(name)||!String(data.files[name]||"").startsWith("https://"))
          throw new Error("Arquivo autorizado ausente: "+name);
      }
      privateMedia=data.files;
    } finally {clearTimeout(timeout);}
  }
  function renderPlayers(){
    const item=CFG.scenes[currentIndex];
    const indices=order(currentIndex);
    const wrap=$("audio-cards");
    wrap.innerHTML="";
    audios=[];
    indices.forEach((sourceIndex,labelIndex)=>{
      const label=LABELS[labelIndex], file=item.files[sourceIndex];
      const source=privateMedia?.[file.split("/").pop()]||file;
      const card=document.createElement("article");
      card.className="audio-card";
      card.innerHTML = `<div class="audio-top"><span class="audio-label">Áudio ${label}</span><span class="audio-chip">16 segundos</span></div>
      <div class="play-row"><button class="play" type="button" aria-label="Reproduzir áudio ${label}" title="Reproduzir / pausar">${btnGlyph(true)}</button>
      <div class="seek-box"><input class="timeline" aria-label="Avançar no áudio ${label}" type="range" min="0" max="16" step=".01" value="0" style="--fill:0%">
      <div class="time"><span class="elapsed">00:00</span><span class="duration">00:16</span></div></div></div><div class="audio-error" aria-live="polite"></div>`;
      const audio=document.createElement("audio");
      audio.preload="metadata";
      audio.src=source;
      audio.setAttribute("aria-label","Áudio "+label);
      card.appendChild(audio);
      wrap.appendChild(card);audios.push(audio);
      const btn=card.querySelector(".play"),line=card.querySelector(".timeline");
      const error=card.querySelector(".audio-error");
      const update=()=>{
        const duration=Number.isFinite(audio.duration)&&audio.duration>0?audio.duration:16;
        line.max=duration;
        line.value=Math.min(duration,audio.currentTime||0);
        line.style.setProperty("--fill",Math.min(100,(audio.currentTime||0)/duration*100)+"%");
        card.querySelector(".elapsed").textContent=formatTime(audio.currentTime);
        card.querySelector(".duration").textContent=formatTime(duration);
      };
      btn.addEventListener("click",async()=>{
        if(!audio.paused){audio.pause();return;}
        stopPlayers(audio);
        error.textContent="";
        try {
          await audio.play();
          markListened(sourceIndex);
        }catch(e){
          error.textContent="Áudio não disponível nesta prévia. Verifique a conexão ou os arquivos privados.";
          btn.title="Não foi possível reproduzir";
          console.warn("Audio unavailable",e);
        }
      });
      audio.addEventListener("play",()=>{
        stopPlayers(audio);playing=audio;card.classList.add("playing");
        btn.innerHTML=btnGlyph(false);btn.setAttribute("aria-label","Pausar áudio "+label);
      });
      audio.addEventListener("pause",()=>{
        card.classList.remove("playing");btn.innerHTML=btnGlyph(true);
        btn.setAttribute("aria-label","Reproduzir áudio "+label);
      });
      audio.addEventListener("ended",()=>{
        card.classList.remove("playing");btn.innerHTML=btnGlyph(true);
        update();
      });
      audio.addEventListener("timeupdate",update);
      audio.addEventListener("loadedmetadata",update);
      audio.addEventListener("error",()=>{error.textContent="O trecho privado ainda não foi disponibilizado neste endereço.";});
      line.addEventListener("input",()=>{
        if(audio.readyState>0 && Number.isFinite(audio.duration)){
          audio.currentTime=Number(line.value);
        }
        update();
      });
      const hasPlayed=sceneState(currentIndex).listened.includes(sourceIndex);
      if(hasPlayed) card.dataset.visited="true";
    });
  }
  function setVote(question,value){
    const answer=sceneState(currentIndex);
    if(!CFG.rubrics.some(r=>r.key===question)||!VOTE_CHOICES.includes(value))return;
    answer.votes[question]=value;
    answer.sceneUpdatedAt=now();
    persist();
    refreshVotes();
    enableNext();
  }
  function refreshVotes(){
    const a=sceneState(currentIndex);
    $("questions").querySelectorAll("button[data-question]").forEach(b=>{
      b.setAttribute("aria-pressed",String(a.votes[b.dataset.question]===b.dataset.value));
    });
  }
  function choiceName(s){
    return s==="nao_avaliavel"?"Não avaliável":s==="empate"?"Empate":s;
  }
  function renderQuestions(){
    const answers=sceneState(currentIndex);
    const container=$("questions");
    container.innerHTML=CFG.rubrics.map((q,i)=>`
      <div class="rubric" role="group" aria-labelledby="question_${i}">
      <div class="rubric-row">
        <div><p class="rubric-title" id="question_${i}">${i+1}. ${esc(q.title)}</p><p class="rubric-caption">${esc(q.hint)}</p></div>
        <div class="choice-grid" aria-label="${esc(q.title)}">${VOTE_CHOICES.map(v=>
          `<button type="button" data-question="${esc(q.key)}" data-value="${v}" aria-pressed="false">${choiceName(v)}</button>`
        ).join("")}</div>
      </div></div>`).join("");
    container.querySelectorAll("button[data-question]").forEach(b=>b.addEventListener("click",()=>setVote(b.dataset.question,b.dataset.value)));
    for(const key of ["speech","overlap","motorcycle"]){
      const group=document.querySelector('[data-field="'+key+'"]');
      group.querySelectorAll("button").forEach(b=>{
        b.setAttribute("aria-pressed",String(answers[key]===b.dataset.value));
        b.onclick=()=>{
          answers[key]=b.dataset.value;
          answers.sceneUpdatedAt=now();
          group.querySelectorAll("button").forEach(v=>v.setAttribute("aria-pressed",String(v===b)));
          persist();enableNext();
        };
      });
    }
    $("remark").value=answers.note||"";
    $("remark").oninput=()=>{
      answers.note=$("remark").value.slice(0,320);
      answers.sceneUpdatedAt=now();
      persist();
    };
    refreshVotes();
  }
  function sceneComplete(index){
    const a=sceneState(index);
    const complete=CFG.rubrics.every(q=>VOTE_CHOICES.includes(a.votes[q.key]));
    const contexts=["speech","overlap","motorcycle"].every(k=>["sim","nao","parcial","incerto"].includes(a[k]));
    const played=(a.listened||[]).length===3;
    return {complete,contexts,played,valid:complete&&contexts&&played};
  }
  function enableNext(){
    const c=sceneComplete(currentIndex);
    $("next").disabled=!c.valid;
    if(c.valid)$("validation").textContent="";
    else $("validation").textContent="";
  }
  function renderScene(){
    stopPlayers();audios=[];
    const s=CFG.scenes[currentIndex];
    $("progress-label").textContent="Escuta comparativa · "+(currentIndex+1)+" / 3";
    $("progress-ratio").textContent=Math.round(currentIndex/3*100)+"%";
    $("progress-bar").style.width=(currentIndex/3*100)+"%";
    $("scene-tag").textContent="TRECHO "+String(currentIndex+1).padStart(2,"0");
    $("test-title").textContent=s.title;
    $("scene-description").textContent="Três versões do mesmo intervalo · "+s.timeLabel;
    $("scene-tip").textContent=s.warning;
    $("next").innerHTML=currentIndex===2?"Concluir avaliação <span aria-hidden='true'>✓</span>":
      "Próximo trecho <span aria-hidden='true'>→</span>";
    $("back").disabled=currentIndex===0;
    renderPlayers();renderQuestions();enableNext();
    view("test");
  }
  async function begin(){
    const p=$("participant").value,consent=$("consent").checked;
    if(!CFG.people.some(x=>x.id===p)||!consent)return;
    participant=p;
    if(CFG.backend.enabled && CFG.backend.url) {
      $("begin").disabled=true;
      status("Validando convite e preparando os áudios privados…");
      try {await preparePrivateMedia();}
      catch(error) {
        status("Não foi possível abrir os áudios privados: "+error.message,"error");
        $("begin").disabled=false;
        return;
      }
      $("begin").disabled=false;
    }
    const prior=loadLocal(participant);
    state=prior||fresh(participant);
    if(prior&&prior.receipt) {
      // Submission has been finalized; allow review without modifying submitted answers.
      currentIndex=0;
      showFinish();return;
    }
    persist();
    currentIndex=0;
    for(let i=0;i<CFG.scenes.length;i++)if(!sceneComplete(i).valid){currentIndex=i;break;}
    if(CFG.scenes.every((_,i)=>sceneComplete(i).valid)){showFinish();return;}
    renderScene();
  }
  function toPayload(){
    const scenes=CFG.scenes.map((s,i)=>{
      const a=sceneState(i),orderIDs=order(i).map(j=>s.files[j].split("/").pop().replace(/\.wav$/,""));
      return {
        sceneId:s.id, timeRange:s.timeLabel,
        blindMapping:{"A":orderIDs[0],"B":orderIDs[1],"C":orderIDs[2]},
        votes:{...a.votes}, speech:a.speech, overlap:a.overlap,motorcycle:a.motorcycle,
        note:a.note||"", listenedSources:[...a.listened],updatedAt:a.sceneUpdatedAt
      };
    });
    return {
      studyId:CFG.studyId,schemaVersion:CFG.schemaVersion,
      sessionId:state.sessionId,participantId:participant,
      startedAt:state.startedAt, completedAt:state.completedAt,
      consent:state.consent, scenes,
      collectionContext:"Unblinded participant selection; A/B/C balanced by participant and scene; fixed 16s lowband-selected excerpts; exploratory convenience sample N≤3.",
      methodologicalLimits:{
        eventsIndependentlyVerified:false,
        loudnessPerfectlyMatched:false,
        thirdPartyAudioUploadedByForm:false
      }
    };
  }
  function showFinish(){
    stopPlayers();
    if(!state.completedAt){state.completedAt=now();persist();}
    const p=CFG.people.find(p=>p.id===participant);
    $("final-info").innerHTML=`<p><strong>Participante:</strong> ${esc(p.name)}<br>
      <strong>Trechos avaliados:</strong> 3 de 3<br>
      <strong>Respostas por trecho:</strong> 4 escolhas comparativas, 3 confirmações de contexto e observação opcional.<br>
      <strong>Identificação dos métodos:</strong> mantida em manifesto privado, fora desta página.</p>`;
    const text=state.receipt ? "Resposta já confirmada pelo servidor: "+state.receipt.receiptId :
      CFG.backend.enabled&&CFG.backend.url ? "Concluído no navegador. Envie para registrar com confirmação." :
      "Concluído e salvo neste navegador. Ainda não existe servidor remoto configurado; exporte a cópia JSON.";
    $("receipt").textContent=text;
    $("send").disabled=!!state.receipt || !CFG.backend.enabled || !CFG.backend.url;
    $("review").hidden=!!state.receipt;
    $("send").title=(!CFG.backend.enabled||!CFG.backend.url)?"Envio remoto não configurado nesta prévia":"Enviar respostas e aguardar recibo";
    view("finish");
    $("progress-bar").style.width="100%";
  }
  function checkCurrent(){
    const c=sceneComplete(currentIndex);
    if(!c.played){$("validation").textContent="Reproduza A, B e C ao menos uma vez antes de continuar.";return false;}
    if(!c.complete){$("validation").textContent="Responda aos quatro critérios, incluindo empate ou não avaliável quando necessário.";return false;}
    if(!c.contexts){$("validation").textContent="Registre se percebeu fala, ruído concomitante e motocicleta.";return false;}
    return true;
  }
  function exportFile(){
    const payload=JSON.stringify(toPayload(),null,2);
    const blob=new Blob([payload],{type:"application/json;charset=utf-8"});
    const url=URL.createObjectURL(blob),a=document.createElement("a");
    a.href=url;a.download="ptc3528-w261-"+participant+"-"+state.sessionId.slice(0,8)+".json";
    document.body.append(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    $("receipt").textContent=state.receipt ?
      "Resposta confirmada no servidor. Cópia JSON exportada.":
      "Cópia JSON baixada. ATENÇÃO: exportar não equivale a enviar suas respostas ao servidor.";
  }
  async function copyFile(){
    try{await navigator.clipboard.writeText(JSON.stringify(toPayload(),null,2));
      $("receipt").textContent="Conteúdo copiado. Colar e enviar manualmente não equivale a confirmação de recebimento automático.";}
    catch{$("receipt").textContent="Cópia indisponível neste navegador; utilize Baixar cópia JSON.";}
  }
  async function submit(){
    if(submitting||state.receipt)return;
    if(!CFG.backend.enabled||!CFG.backend.url){
      $("receipt").textContent="O servidor não foi configurado. Exporte o JSON para preservar as respostas.";return;
    }
    if(!invite){
      $("receipt").textContent="Link de convite ausente: não é possível verificar qual participante está enviando.";return;
    }
    submitting=true;$("send").disabled=true;
    $("receipt").textContent="Enviando… aguardando confirmação do servidor.";
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),16000);
    try {
      const response=await fetch(CFG.backend.url,{
        method:"POST",mode:"cors",redirect:"error",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({invitation:invite,...toPayload()}),
        signal:controller.signal
      });
      if(!response.ok)throw new Error("Servidor HTTP "+response.status);
      const data=await response.json();
      if(data?.ok!==true || !data.receiptId || !data.receivedAt)
        throw new Error("Servidor não confirmou o armazenamento da resposta.");
      state.receipt={receiptId:String(data.receiptId),receivedAt:String(data.receivedAt)};
      $("review").hidden=true;
      persist();
      $("receipt").textContent="Salvo no servidor com sucesso! Comprovante: "+state.receipt.receiptId+" · "+new Date(state.receipt.receivedAt).toLocaleString("pt-BR");
    }catch(error){
      $("receipt").textContent="Envio não confirmado ("+error.message+"). Suas respostas permanecem no navegador: tente novamente ou exporte JSON.";
      status("Envio remoto não confirmado; dados locais preservados.","error");
      console.error("Submission failed",error);
      $("send").disabled=false;
    }finally{clearTimeout(timeout);submitting=false;}
  }
  function initialize(){
    const pFromURL=userParams.get("participante");
    if(CFG.people.some(x=>x.id===pFromURL)){
      $("participant").value=pFromURL;
    }
    const toggle=()=>{
      const p=$("participant").value;
      $("begin").disabled=!CFG.people.some(x=>x.id===p) || !$("consent").checked;
      $("begin").textContent=loadLocal(p)?"Retomar avaliação →":"Começar avaliação →";
    };
    $("participant").addEventListener("change",toggle);
    $("consent").addEventListener("change",toggle);
    $("begin").addEventListener("click",begin);
    $("next").addEventListener("click",()=>{
      if(!checkCurrent())return;
      stopPlayers();
      if(currentIndex===CFG.scenes.length-1)showFinish();
      else {currentIndex++;renderScene();}
    });
    $("back").addEventListener("click",()=>{if(currentIndex>0){currentIndex--;renderScene();}});
    $("review").addEventListener("click",()=>{currentIndex=0;renderScene();});
    $("export").addEventListener("click",exportFile);
    $("copy").addEventListener("click",copyFile);
    $("send").addEventListener("click",submit);
    status(CFG.backend.enabled&&CFG.backend.url ?
      "Rascunho local · servidor disponível após confirmação de envio.":
      "Prévia local · respostas persistem neste navegador, sem envio remoto.");
    toggle();
  }
  initialize();
})();