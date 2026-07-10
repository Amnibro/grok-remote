(function(){
function safeParse(raw,fallback){
 try{
  if(raw==null||raw==="")return fallback;
  const s=String(raw).replace(/^\uFEFF/,"").trim();
  if(!s)return fallback;
  return JSON.parse(s);
 }catch(e){return fallback}
}
const api={
 async get(url){
  const r=await fetch(url,{cache:"no-store"});
  const text=await r.text();
  const body=safeParse(text,null);
  if(!r.ok)throw new Error((body&&(body.error||body.message))||text.slice(0,200)||("HTTP "+r.status));
  if(body===null)throw new Error("bad json from "+url);
  return body;
 },
 async post(url,body){
  const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body||{})});
  const text=await r.text();
  const parsed=safeParse(text,null);
  if(!r.ok)throw new Error((parsed&&(parsed.error||parsed.message))||text.slice(0,200)||("HTTP "+r.status));
  if(parsed===null)throw new Error("bad json from "+url);
  return parsed;
 }
};
const state={open:false,rel:".",files:[],dirs:[],tabs:[],active:null,dirty:{},root:"",touched:[],touchMeta:{}};
function $(id){return document.getElementById(id)}
function extLang(name){
 const e=(name||"").split(".").pop().toLowerCase();
 const m={js:"javascript",ts:"typescript",tsx:"typescript",jsx:"javascript",py:"python",rs:"rust",go:"go",md:"markdown",json:"json",css:"css",html:"html",htm:"html",sh:"shell",ps1:"powershell",yml:"yaml",yaml:"yaml",toml:"toml",c:"c",h:"c",cpp:"cpp",hpp:"cpp",java:"java",cs:"csharp",sql:"sql"};
 return m[e]||e||"text";
}
function notify(msg){if(typeof chip==="function")chip(msg);else console.log(msg)}
function normPath(p){
 let s=String(p||"").trim().replace(/^file:\/\//i,"").replace(/^b\//,"").replace(/^a\//,"");
 s=s.replace(/\\/g,"/");
 if(state.root){
  const root=String(state.root).replace(/\\/g,"/");
  if(s.toLowerCase().startsWith(root.toLowerCase()+"/"))s=s.slice(root.length+1);
  else if(s.toLowerCase()===root.toLowerCase())s=".";
 }
 if(s.startsWith("./"))s=s.slice(2);
 return s;
}
function isPathish(p){
 if(!p||p.length<2)return false;
 if(/^https?:/i.test(p))return false;
 return /[\\/]|\.[a-z0-9]{1,12}$/i.test(p)||/^[A-Za-z]:[\\/]/.test(p);
}
async function ensureRoot(){
 if(state.root)return state.root;
 try{const j=await api.get("/api/fs/root");state.root=j.root||"";return state.root}catch(e){return ""}
}
async function loadList(rel){
 state.rel=rel||".";
 const j=await api.get("/api/fs/list?path="+encodeURIComponent(state.rel));
 state.dirs=j.dirs||[];state.files=j.files||[];state.root=j.root||state.root;
 paintTree(j);
 return j;
}
function paintTree(j){
 const tree=$("ideTree");if(!tree)return;
 tree.innerHTML="";
 const head=document.createElement("div");head.className="ide-tree-head";
 head.innerHTML="<b>Workspace</b><span class='spoiler-path'>"+escHtml((j&&j.root)||state.root||"")+"</span>";
 tree.appendChild(head);
 if(state.touched.length){
  const sec=document.createElement("div");sec.className="ide-touched";
  sec.innerHTML="<div class='ide-sec-label'>Grok touched</div>";
  state.touched.slice(0,16).forEach(rel=>{
   const el=document.createElement("div");
   el.className="ide-item ide-file ide-agent"+(state.active===rel?" on":"");
   const meta=state.touchMeta[rel]||{};
   el.innerHTML="<span>⚡ "+escHtml(rel.split("/").pop())+"</span><small class='spoiler-path'>"+escHtml(rel)+"</small>";
   el.title=(meta.kind||"tool")+" · click to open";
   el.onclick=()=>openFile(rel,{forceReload:true}).catch(e=>notify(String(e)));
   sec.appendChild(el);
  });
  tree.appendChild(sec);
 }
 if(j&&j.parent!=null){
  const up=document.createElement("div");up.className="ide-item ide-up";up.textContent="↑ ..";
  up.onclick=()=>loadList(j.parent).catch(e=>notify(String(e)));
  tree.appendChild(up);
 }
 (state.dirs||[]).forEach(d=>{
  const el=document.createElement("div");el.className="ide-item ide-dir";
  el.textContent="📁 "+d.name;
  el.onclick=()=>loadList(d.rel).catch(e=>notify(String(e)));
  tree.appendChild(el);
 });
 (state.files||[]).forEach(f=>{
  const touched=state.touched.includes(f.rel);
  const el=document.createElement("div");el.className="ide-item ide-file"+(state.active===f.rel?" on":"")+(touched?" ide-agent":"");
  el.textContent=(f.text===false?"📦 ":"📄 ")+(touched?"⚡ ":"")+f.name;
  el.onclick=()=>openFile(f.rel).catch(e=>notify(String(e)));
  tree.appendChild(el);
 });
}
function escHtml(s){return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}
function paintTabs(){
 const bar=$("ideTabs");if(!bar)return;
 bar.innerHTML="";
 state.tabs.forEach(t=>{
  const agent=state.touched.includes(t.rel);
  const b=document.createElement("button");
  b.type="button";b.className="ide-tab"+(state.active===t.rel?" on":"")+(state.dirty[t.rel]?" dirty":"")+(agent?" agent-touch":"");
  b.innerHTML="<span>"+(agent?"⚡ ":"")+escHtml(t.name)+(state.dirty[t.rel]?" •":"")+"</span><i title='Close'>×</i>";
  b.querySelector("span").onclick=()=>activate(t.rel);
  b.querySelector("i").onclick=e=>{e.stopPropagation();closeTab(t.rel)};
  bar.appendChild(b);
 });
}
function activate(rel){
 const t=state.tabs.find(x=>x.rel===rel);if(!t)return;
 state.active=rel;
 const ed=$("ideEditor");
 if(ed){ed.value=t.content;ed.dataset.rel=rel}
 const st=$("ideStatus");
 if(st)st.textContent=(state.dirty[rel]?"modified · ":"")+(t.rel||"")+" · "+extLang(t.name);
 paintTabs();
 loadList(state.rel).catch(()=>{});
}
async function openFile(rel,opts){
 await ensureRoot();
 rel=normPath(rel);
 if(!rel||rel===".")return;
 let t=state.tabs.find(x=>x.rel===rel||normPath(x.rel)===rel);
 if(!t||(opts&&opts.forceReload&&!state.dirty[rel])){
  const j=await api.get("/api/fs/read?path="+encodeURIComponent(rel));
  if(j.binary||j.text===false){notify("binary file — open elsewhere");return}
  const nr=j.rel||rel;
  t=state.tabs.find(x=>x.rel===nr);
  if(!t){
   t={rel:nr,name:j.name||nr.split(/[/\\]/).pop(),content:j.content||"",path:j.path};
   state.tabs.push(t);
  }else if(opts&&opts.forceReload&&!state.dirty[nr]){
   t.content=j.content||"";
  }
 }
 activate(t.rel);
 if(!(opts&&opts.keepClosed))showIde(true);
 return t;
}
function noteAgentFiles(paths,meta){
 const list=[].concat(paths||[]).map(normPath).filter(isPathish);
 if(!list.length)return;
 list.forEach(rel=>{
  state.touchMeta[rel]=Object.assign({},state.touchMeta[rel]||{},meta||{},{at:Date.now()});
  state.touched=state.touched.filter(x=>x!==rel);
  state.touched.unshift(rel);
 });
 state.touched=state.touched.slice(0,24);
 paintTabs();
 if(state.open)loadList(state.rel).catch(()=>{});
 else paintTree({root:state.root,parent:state.rel==="."?null:state.rel,dirs:state.dirs,files:state.files});
 const auto=!!(meta&&meta.autoOpen);
 const kind=String((meta&&meta.kind)||"");
 const wrote=/write|edit|diff|patch|create|update/i.test(kind)||meta&&meta.wrote;
 if(auto&&list[0]){
  openFile(list[0],{forceReload:true}).catch(()=>{});
 }else if(state.open&&list[0]&&wrote){
  const t=state.tabs.find(x=>x.rel===list[0]);
  if(t&&!state.dirty[list[0]])openFile(list[0],{forceReload:true,keepClosed:false}).catch(()=>{});
 }else{
  paintTabs();
 }
}
function closeTab(rel){
 if(state.dirty[rel]&&!confirm("Discard unsaved changes to "+rel+"?"))return;
 state.tabs=state.tabs.filter(x=>x.rel!==rel);
 delete state.dirty[rel];
 if(state.active===rel){
  state.active=state.tabs[0]?state.tabs[0].rel:null;
  const ed=$("ideEditor");
  if(ed){ed.value=state.active?(state.tabs.find(x=>x.rel===state.active)||{}).content||"":"";ed.dataset.rel=state.active||""}
 }
 paintTabs();
}
async function saveActive(){
 const rel=state.active;if(!rel)return;
 const t=state.tabs.find(x=>x.rel===rel);if(!t)return;
 const ed=$("ideEditor");
 if(ed&&ed.dataset.rel===rel)t.content=ed.value;
 await api.post("/api/fs/write",{path:rel,content:t.content});
 delete state.dirty[rel];
 paintTabs();
 notify("saved "+rel);
 const st=$("ideStatus");if(st)st.textContent="saved · "+rel;
 return t;
}
function onEditorInput(){
 const ed=$("ideEditor");if(!ed||!state.active)return;
 const t=state.tabs.find(x=>x.rel===state.active);if(!t)return;
 t.content=ed.value;state.dirty[state.active]=true;paintTabs();
}
function buildReviewPrompt(files){
 const parts=["# Grok Review — post-edit bug check","","You are reviewing local workspace edits in a Grok Remote IDE session.","Find bugs, security issues, regressions, missing edge cases, and suggest minimal fixes.","Structure:","1. Critical","2. Warnings","3. Suggestions","4. Optional patches as fenced code with filepath comments","","---",""];
 files.forEach(f=>{
  const lang=extLang(f.name);
  parts.push("## File: `"+f.rel+"`","");
  parts.push("```"+lang,f.content, "```","");
 });
 parts.push("Review thoroughly. If clean, say so briefly.");
 return parts.join("\n");
}
async function reviewActive(){
 const rel=state.active;
 if(!rel){notify("open a file first");return}
 if(state.dirty[rel])await saveActive();
 const t=state.tabs.find(x=>x.rel===rel);if(!t)return;
 await sendReview([t]);
}
async function reviewDirty(){
 const dirty=state.tabs.filter(t=>state.dirty[t.rel]);
 if(!dirty.length){
  if(state.active)return reviewActive();
  notify("no dirty files");return;
 }
 for(const t of dirty){state.active=t.rel;await saveActive()}
 await sendReview(dirty);
}
async function sendReview(files){
 if(typeof sendPromptExternal!=="function"&&typeof window.grokRemoteSend!=="function"){
  if(typeof box!=="undefined"&&box&&typeof sendPrompt==="function"){
   if(!window.sid&&typeof sid!=="undefined"&&!sid){notify("connect a session first");return}
  }
 }
 const text=buildReviewPrompt(files);
 showIde(true);
 if(typeof window.grokIdeSend==="function"){
  await window.grokIdeSend(text);
  notify("Grok Review sent");
  return;
 }
 notify("connect to a session, then Review again");
 throw new Error("no session sender");
}
function showIde(on){
 state.open=on!==false;
 const panel=$("idePanel");
 if(panel)panel.classList.toggle("on",state.open);
 document.body.classList.toggle("ide-open",state.open);
 const btn=$("btnIde");
 if(btn)btn.classList.toggle("on",state.open);
 if(state.open&&!state.root)loadList(".").catch(e=>notify(String(e)));
}
function toggleIde(){showIde(!state.open)}
async function pickRoot(){
 if(window.grokRemote&&window.grokRemote.pickFolder){
  const p=await window.grokRemote.pickFolder();
  if(!p)return;
  await api.post("/api/fs/root",{path:p});
  state.tabs=[];state.dirty={};state.active=null;
  const ed=$("ideEditor");if(ed)ed.value="";
  await loadList(".");
  if(window.grokRemote.setCwd)await window.grokRemote.setCwd(p);
  notify("workspace "+p);
  return;
 }
 const p=prompt("Workspace folder path on the PC",state.root||"");
 if(!p)return;
 await api.post("/api/fs/root",{path:p});
 state.tabs=[];state.dirty={};state.active=null;
 await loadList(".");
 notify("workspace "+p);
}
async function newSessionHere(){
 const root=(await api.get("/api/fs/root")).root;
 if(typeof window.grokIdeNewSession==="function"){
  await window.grokIdeNewSession(root,"Explore this workspace and be ready for IDE edits + Grok Review.");
  return;
 }
 notify("new session @ "+root);
}
function bind(){
 const ed=$("ideEditor");
 if(ed){
  ed.addEventListener("input",onEditorInput);
  ed.addEventListener("keydown",e=>{
   if((e.ctrlKey||e.metaKey)&&e.key==="s"){e.preventDefault();saveActive().catch(err=>notify(String(err)))}
   if((e.ctrlKey||e.metaKey)&&e.key==="s"&&e.shiftKey){e.preventDefault();reviewActive().catch(err=>notify(String(err)))}
  });
 }
 const bIde=$("btnIde");if(bIde)bIde.onclick=()=>{try{if(typeof window.closeMoreMenu==="function")window.closeMoreMenu()}catch(e){}toggleIde()};
 const bClose=$("ideClose");if(bClose)bClose.onclick=()=>showIde(false);
 const bSave=$("ideSave");if(bSave)bSave.onclick=()=>saveActive().catch(e=>notify(String(e)));
 const bRev=$("ideReview");if(bRev)bRev.onclick=()=>reviewActive().catch(e=>notify(String(e)));
 const bRevAll=$("ideReviewAll");if(bRevAll)bRevAll.onclick=()=>reviewDirty().catch(e=>notify(String(e)));
 const bRoot=$("ideRoot");if(bRoot)bRoot.onclick=()=>pickRoot().catch(e=>notify(String(e)));
 const bNew=$("ideNewSess");if(bNew)bNew.onclick=()=>newSessionHere().catch(e=>notify(String(e)));
 const bRef=$("ideRefresh");if(bRef)bRef.onclick=()=>loadList(state.rel).catch(e=>notify(String(e)));
}
window.grokIde={toggle:toggleIde,show:showIde,openFile,saveActive,reviewActive,reviewDirty,loadList,pickRoot,noteAgentFiles,normPath,state};
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",bind);else bind();
})();
