(function(){
if(window.grokWork)return;
const VERB={read:"read",edit:"edited",write:"wrote",create:"created",delete:"deleted",run:"ran",find:"searched",list:"listed",search:"searched",grep:"searched",bash:"ran",shell:"ran",tool:"used"};
const HOT={write:1,edit:1,create:1,delete:1};
const CSS="#gwk{position:fixed;inset:0;z-index:20040;display:none}#gwk.on{display:block}#gwk .wscrim{position:absolute;inset:0;background:rgba(8,10,14,.4)}#gwk .wpan{position:absolute;top:0;right:0;bottom:0;width:min(420px,96vw);display:flex;flex-direction:column;background:var(--panel,#161a22);color:var(--tx,#eef);border-left:1px solid var(--line,#2a3140);box-shadow:var(--elev-3,0 14px 40px rgba(0,0,0,.5))}#gwk .whd{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid var(--line);flex:none}#gwk .wtabs{display:flex;gap:2px;background:var(--panel2,#111);border-radius:9px;padding:2px}#gwk .wtabs button{border:0;background:none;color:var(--mut);font:inherit;font-size:12.5px;font-weight:600;padding:5px 10px;border-radius:7px;cursor:pointer}#gwk .wtabs button[aria-pressed=true]{background:var(--panel);color:var(--tx)}#gwk .wx{margin-left:auto;border:0;background:none;color:var(--mut);font-size:16px;cursor:pointer;padding:6px 8px}#gwk .wfilt{display:flex;gap:6px;padding:6px 12px;border-bottom:1px solid var(--line);flex:none}#gwk .wfilt input{flex:1;min-width:0;border:1px solid var(--line);background:var(--in);color:var(--tx);border-radius:8px;padding:5px 9px;font:inherit;font-size:12px}#gwk .wfilt button{border:1px solid var(--line);background:var(--panel2);color:var(--mut);border-radius:8px;padding:5px 9px;font:inherit;font-size:11.5px;font-weight:600;cursor:pointer}#gwk .wfilt button[aria-pressed=true]{background:var(--acc);border-color:var(--acc);color:#fff}#gwk .wfeed,#gwk .wlist{flex:1;min-height:0;overflow-y:auto;-webkit-overflow-scrolling:touch}#gwk .wsec{flex:1;min-height:0;display:none;flex-direction:column;overflow:hidden}#gwk .wsec.on{display:flex}#gwk .row{display:grid;grid-template-columns:52px 1fr;gap:8px;padding:6px 12px;border-left:3px solid transparent;font-size:12.5px;line-height:1.45}#gwk .row.hot{border-left-color:var(--acc)}#gwk .row .t{color:var(--mut);font-size:10.5px;font-variant-numeric:tabular-nums}#gwk .row .vb{color:var(--mut)}#gwk .row.hot .vb{color:var(--tx);font-weight:600}#gwk .row .p{font-family:var(--font-mono,ui-monospace,Consolas,monospace);font-size:11.5px;color:var(--tx);background:var(--in);border-radius:5px;padding:1px 5px;cursor:pointer;word-break:break-all}#gwk .empty{padding:22px 16px;color:var(--mut);font-size:12.5px;text-align:center;line-height:1.6}#gwk .crumb{display:flex;flex-wrap:wrap;gap:2px;align-items:center;padding:7px 12px;font-size:11.5px;border-bottom:1px solid var(--line)}#gwk .crumb button{border:0;background:none;color:var(--acc);font:inherit;font-size:11.5px;cursor:pointer}#gwk .it{display:flex;align-items:center;gap:8px;padding:7px 12px;font-size:12.5px;cursor:pointer;border:0;background:none;color:var(--tx);width:100%;text-align:left;font-family:inherit}#gwk .it:hover,#gwk .row:hover{background:var(--acc-dim,rgba(255,255,255,.04))}#gwk .it .nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}#gwk .it.dir .nm{font-weight:600}#gwk pre.code{margin:0;flex:1;min-height:0;overflow:auto;padding:10px 12px;font-family:var(--font-mono,ui-monospace,Consolas,monospace);font-size:11.5px;line-height:1.55;white-space:pre}#gwk .n{background:var(--acc);color:#fff;border-radius:9px;padding:0 5px;font-size:10px;line-height:15px;min-width:15px;text-align:center;margin-left:4px}#gwk .n[hidden]{display:none}@media(max-width:720px){#gwk .wpan{top:auto;left:0;right:0;bottom:0;width:auto;height:min(82vh,720px);border-left:0;border-top:1px solid var(--line);border-radius:18px 18px 0 0}}";
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const clock=t=>{const d=new Date(t||Date.now());return d.toTimeString().slice(0,8)};
const kindOf=k=>{const r=String(k||"").toLowerCase();if(/edit|write|apply_patch|str_replace|multi_edit/.test(r))return"edit";if(/read|search|grep|glob|list_dir|find/.test(r))return"read";if(/bash|shell|terminal|run/.test(r))return"run";return r.split(/[^a-z0-9]/)[0]||"tool"};
let EV=[],TAB="work",OPEN=false,UNSEEN=0,ONLY=false,Q="",DIR=".",FILE="";
function el(){return document.getElementById("gwk")}
function mount(){
 if(el())return window.grokWork;
 const st=document.createElement("style");st.textContent=CSS;document.head.appendChild(st);
 const d=document.createElement("div");d.id="gwk";d.setAttribute("aria-hidden","true");
 d.innerHTML='<div class="wscrim" data-x="1"></div><div class="wpan" role="dialog" aria-label="Work"><div class="whd"><div class="wtabs" role="group"><button data-t="work" aria-pressed="true">Work<i class="n" id="gwk-n" hidden>0</i></button><button data-t="files" aria-pressed="false">Files</button></div><button class="wx" data-x="1" aria-label="Close">✕</button></div><div class="wbody" style="flex:1;min-height:0;display:flex;flex-direction:column"><section class="wsec on" data-p="work"><div class="wfilt"><input id="gwk-q" placeholder="filter by path or tool" autocomplete="off"><button id="gwk-only" aria-pressed="false">Changes</button></div><div class="wfeed" id="gwk-feed"></div></section><section class="wsec" data-p="files"><div class="crumb" id="gwk-crumb"></div><div class="wlist" id="gwk-ls"></div><pre class="code" id="gwk-code" hidden></pre></section></div></div>';
 document.body.appendChild(d);
 d.addEventListener("click",e=>{
  if(e.target.closest("[data-x]"))return close();
  const t=e.target.closest(".wtabs button");if(t)return tab(t.dataset.t);
  const p=e.target.closest(".row .p");if(p&&p.dataset.p)return openPath(p.dataset.p);
  const it=e.target.closest(".it");if(it)return it.dataset.d?ls(it.dataset.d):openPath(it.dataset.f);
 });
 $("#gwk-q").oninput=e=>{Q=(e.target.value||"").toLowerCase();paintFeed()};
 $("#gwk-only").onclick=e=>{ONLY=!ONLY;e.currentTarget.setAttribute("aria-pressed",ONLY?"true":"false");paintFeed()};
 document.addEventListener("keydown",e=>{if(e.key==="Escape"&&OPEN)close()});
 return window.grokWork;
}
function tab(name){
 TAB=name==="files"?"files":"work";
 document.querySelectorAll("#gwk .wtabs button").forEach(b=>b.setAttribute("aria-pressed",b.dataset.t===TAB?"true":"false"));
 document.querySelectorAll("#gwk .wsec").forEach(s=>s.classList.toggle("on",s.getAttribute("data-p")===TAB));
 if(TAB==="files")ls(DIR);
 if(TAB==="work"){UNSEEN=0;badge()}
}
function badge(){
 const n=$("#gwk-n");if(!n)return;
 if(!OPEN&&UNSEEN){n.hidden=false;n.textContent=UNSEEN>99?"99+":String(UNSEEN)}
 else n.hidden=true;
 const b=document.getElementById("btnWork");
 if(b)b.classList.toggle("on",OPEN||UNSEEN>0);
}
function paintFeed(){
 const host=$("#gwk-feed");if(!host)return;
 const rows=EV.filter(e=>{
  if(ONLY&&!HOT[kindOf(e.kind)])return false;
  if(Q){const blob=(e.title+" "+(e.locs||[]).join(" ")+" "+e.kind).toLowerCase();if(blob.indexOf(Q)<0)return false}
  return true;
 });
 if(!rows.length){host.innerHTML='<div class="empty">No tool calls yet.<br>They land here as Grok reads, edits, and runs.</div>';return}
 host.innerHTML=rows.slice().reverse().map(e=>{
  const k=kindOf(e.kind);
  const loc=(e.locs&&e.locs[0])||"";
  const vb=VERB[k]||e.kind||"tool";
  return '<div class="row'+(HOT[k]?" hot":"")+'"><span class="t">'+clock(e.ts)+'</span><div><span class="vb">'+esc(vb)+'</span> '+(loc?'<span class="p" data-p="'+esc(loc)+'">'+esc(loc.split(/[/\\\\]/).slice(-2).join("/"))+"</span>":esc(e.title||""))+(e.status?' <span class="t">'+esc(e.status)+"</span>":"")+"</div></div>";
 }).join("");
}
async function ls(rel){
 DIR=rel||".";FILE="";
 const code=$("#gwk-code");if(code)code.hidden=true;
 const list=$("#gwk-ls");if(list)list.hidden=false;
 const crumb=$("#gwk-crumb");
 try{
  const r=await fetch("/api/fs/list?path="+encodeURIComponent(DIR),{cache:"no-store"});
  const j=await r.json();
  if(crumb){
   const parts=(j.rel||".").split("/").filter(p=>p&&p!==".");
   let acc=".";
   crumb.innerHTML='<button data-d=".">root</button>'+parts.map(p=>{acc=acc==="."?p:acc+"/"+p;return '<span>/</span><button data-d="'+esc(acc)+'">'+esc(p)+"</button>"}).join("");
   crumb.querySelectorAll("button").forEach(b=>b.onclick=()=>ls(b.getAttribute("data-d")));
  }
  if(list){
   list.innerHTML=(j.dirs||[]).map(d=>'<button class="it dir" data-d="'+esc(d.rel)+'"><span>▸</span><span class="nm">'+esc(d.name)+"</span></button>").join("")+
    (j.files||[]).map(f=>'<button class="it" data-f="'+esc(f.rel)+'"><span>·</span><span class="nm">'+esc(f.name)+"</span></button>").join("")||
    '<div class="empty">Empty folder</div>';
  }
 }catch(e){if(list)list.innerHTML='<div class="empty">Could not list files</div>'}
}
async function openPath(p){
 if(!p)return;
 if(window.grokIde&&window.grokIde.openFile){try{await window.grokIde.openFile(p,{forceReload:false})}catch(e){}}
 TAB="files";tab("files");
 FILE=p;
 const list=$("#gwk-ls");if(list)list.hidden=true;
 const code=$("#gwk-code");if(!code)return;
 code.hidden=false;code.textContent="loading…";
 try{
  const r=await fetch("/api/fs/read?path="+encodeURIComponent(p),{cache:"no-store"});
  const j=await r.json();
  code.textContent=j.binary?"(binary "+(j.size||0)+" bytes)":(j.content||"");
 }catch(e){code.textContent=String(e)}
}
function push(ev){
 if(!ev)return;
 const id=String(ev.id||"");
 const prev=id?EV.find(x=>x.id===id):null;
 if(prev){Object.assign(prev,ev);if(OPEN&&TAB==="work")paintFeed();return}
 EV.push(ev);
 if(EV.length>400)EV=EV.slice(-300);
 if(!OPEN)UNSEEN++;
 badge();
 if(OPEN&&TAB==="work")paintFeed();
}
function open(){mount();OPEN=true;el().classList.add("on");el().setAttribute("aria-hidden","false");UNSEEN=0;badge();paintFeed();if(TAB==="files")ls(DIR)}
function close(){OPEN=false;const n=el();if(n){n.classList.remove("on");n.setAttribute("aria-hidden","true")}badge()}
function toggle(){OPEN?close():open()}
window.grokWork={mount,open,close,toggle,push,paintFeed};
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",mount);else mount();
})();
