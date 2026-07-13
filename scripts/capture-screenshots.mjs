import {chromium,devices} from "playwright-core";
import {mkdir,copyFile} from "fs/promises";
import {dirname,join} from "path";
import {fileURLToPath} from "url";
import {existsSync} from "fs";
const __dir=dirname(fileURLToPath(import.meta.url));
const root=join(__dir,"..");
const out=join(root,"docs","screenshots");
const base=process.env.GROK_REMOTE_URL||"http://127.0.0.1:2421";
function chromePath(){
  const c=[
    process.env.CHROME_PATH,
    "C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe",
    "C:\\\\Program Files (x86)\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe",
    process.env.LOCALAPPDATA&&join(process.env.LOCALAPPDATA,"Google","Chrome","Application","chrome.exe")
  ].filter(Boolean);
  for(const p of c){if(existsSync(p))return p}
  throw new Error("Chrome not found — set CHROME_PATH");
}
async function shot(page,name,{fullPage=false}={}){
  const p=join(out,name);
  await page.screenshot({path:p,fullPage,animations:"disabled"});
  console.log("wrote",name);
}
async function openDemo(page,{privacy=false,layout="desktop",variant="grok",mode="dark",view="chat"}={}){
  const q=new URLSearchParams({
    demo:"1",variant,mode,tour:"0",auto:"0",
    privacy:privacy?"1":"0",layout,
    chat:view==="chat"?"1":"0",
    view:view==="setup"?"setup":"chat"
  });
  await page.goto(`${base}/?${q}`,{waitUntil:"networkidle",timeout:45000});
  await page.waitForFunction(()=>document.querySelectorAll("#sessList .item").length>0||document.querySelector("#feed .row"),{timeout:25000}).catch(()=>{});
  await page.evaluate(({privacy,layout,variant,mode,view})=>{
    window.__demoMode=true;
    if(layout==="desktop"){document.body.classList.add("desktop");document.body.classList.remove("touch-ui")}
    else{document.body.classList.remove("desktop","electron");document.body.classList.add("touch-ui");document.body.classList.remove("can-hover")}
    if(window.applyTheme)window.applyTheme(variant,mode,false);
    if(window.setPrivacy)window.setPrivacy(!!privacy);
    if(window.applyUx)window.applyUx();
    if(view==="setup"&&window.showPage)window.showPage("setup",true);
    else if(window.showPage)window.showPage("chat",true);
    if(window.paintDemoChat&&view==="chat")window.paintDemoChat();
    if(window.paintDemoChat&&view==="chat"){
      try{
        const foot=document.getElementById("foot");
        if(foot)foot.style.display="";
        const live=document.getElementById("livebar");
        if(live){live.dataset.phase="responding";const p=document.getElementById("lbPhase");if(p)p.textContent="responding"}
        const lb=document.getElementById("lbLink");if(lb)lb.textContent="live";
        const pe=document.getElementById("lbPerm");if(pe)pe.textContent="perm: always";
        const ef=document.getElementById("lbEffort");if(ef)ef.textContent="effort: high";
      }catch(e){}
    }
    document.querySelectorAll(".tool.collapsed").forEach(el=>el.classList.remove("collapsed"));
    document.querySelectorAll(".orbit-menu.on,.more-menu.on").forEach(el=>{el.classList.remove("on");el.hidden=true});
  },{privacy,layout,variant,mode,view});
  await page.waitForTimeout(500);
}
async function openCommandDeck(page){
  await page.evaluate(()=>{
    try{if(window.closeOrbitMenu)window.closeOrbitMenu()}catch(e){}
    try{if(window.closeAllSheets)window.closeAllSheets()}catch(e){}
    const b=document.getElementById("btnMore");
    if(b)b.click();
  });
  await page.waitForTimeout(400);
  await page.evaluate(()=>{
    const m=document.getElementById("moreMenu"),b=document.getElementById("btnMore");
    if(m){
      m.hidden=false;m.classList.add("on");
      if(window.placeFixedMenu&&b)window.placeFixedMenu(m,b);
      if(window.paintMoreMenuChrome)try{window.paintMoreMenuChrome()}catch(e){}
    }
  });
  await page.waitForTimeout(350);
}
async function openOrbit(page){
  await page.evaluate(()=>{
    try{if(window.closeMoreMenu)window.closeMoreMenu()}catch(e){}
    const o=document.getElementById("orbit");
    if(o)o.click();
  });
  await page.waitForTimeout(350);
  await page.evaluate(()=>{
    const m=document.getElementById("orbitMenu"),o=document.getElementById("orbit");
    if(m){m.hidden=false;m.classList.add("on");if(window.placeFixedMenu&&o)window.placeFixedMenu(m,o)}
  });
  await page.waitForTimeout(250);
}
async function openSkills(page){
  await page.evaluate(()=>{
    try{if(window.closeMoreMenu)window.closeMoreMenu()}catch(e){}
    const sheet=document.getElementById("skillsSheet");
    if(sheet){sheet.classList.add("on");sheet.style.display="flex"}
    const list=document.getElementById("cmdList");
    if(list&&!list.children.length){
      list.innerHTML=
        '<div class="cmd"><div class="n">/compact <span class="badge">agent</span></div><div class="d">Compress conversation history</div></div>'+
        '<div class="cmd"><div class="n">/effort <span class="badge">remote</span></div><div class="d">Set reasoning effort · low|medium|high</div></div>'+
        '<div class="cmd"><div class="n">/loop <span class="badge">remote</span></div><div class="d">Hub scheduler · no CLI window required</div></div>'+
        '<div class="cmd"><div class="n">/remote <span class="badge">plugin</span></div><div class="d">Start LAN UI + agent serve</div></div>';
    }
  });
  await page.waitForTimeout(350);
}
async function ensureToolsInMenu(page){
  await page.evaluate(()=>{
    const host=document.getElementById("moreToolsHost");
    if(!host)return;
    if(host.querySelector("#toolsRow"))return;
    const wrap=document.createElement("div");
    wrap.id="toolsRow";
    wrap.innerHTML=
      '<button type="button"><span class="mm-ico">@</span><span class="mm-lab">Add path</span><span class="mm-k">file</span></button>'+
      '<button type="button"><span class="mm-ico">☑</span><span class="mm-lab">Todos</span><span class="mm-k">3</span></button>'+
      '<button type="button"><span class="mm-ico">〉</span><span class="mm-lab">Terminal</span><span class="mm-k">shell</span></button>'+
      '<button type="button"><span class="mm-ico">±</span><span class="mm-lab">Git diff</span><span class="mm-k">diff</span></button>'+
      '<button type="button"><span class="mm-ico">↓</span><span class="mm-lab">Export chat</span><span class="mm-k">html</span></button>';
    host.appendChild(wrap);
  });
}
async function main(){
  await mkdir(out,{recursive:true});
  const browser=await chromium.launch({executablePath:chromePath(),headless:true});
  try{
    const desk=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1});
    const d=await desk.newPage();
    await openDemo(d,{layout:"desktop",variant:"grok",mode:"dark"});
    await shot(d,"01-hero-desktop-grok.png");
    await shot(d,"desktop-chat.png");
    await ensureToolsInMenu(d);
    await openCommandDeck(d);
    await shot(d,"02-command-deck.png");
    await shot(d,"desktop-menu.png");
    await d.evaluate(()=>{
      const m=document.getElementById("moreMenu");
      if(m){
        const tools=m.querySelector(".mm-sec");
        const host=document.getElementById("moreToolsHost");
        if(host)host.scrollIntoView({block:"center"});
      }
    });
    await d.waitForTimeout(200);
    await shot(d,"03-command-deck-tools.png");
    await d.keyboard.press("Escape");
    await d.evaluate(()=>{try{if(window.closeMoreMenu)window.closeMoreMenu()}catch(e){}});
    await openOrbit(d);
    await shot(d,"04-orbit-link.png");
    await d.keyboard.press("Escape");
    await openSkills(d);
    await shot(d,"05-skills-sheet.png");
    await d.evaluate(()=>{const s=document.getElementById("skillsSheet");if(s){s.classList.remove("on");s.style.display=""}});
    await openDemo(d,{layout:"desktop",variant:"grok",mode:"dark",view:"setup"});
    await shot(d,"06-setup-themes-grok.png");
    await shot(d,"setup.png");
    for(const [variant,name] of [["scient","07-theme-scient.png"],["matrix","08-theme-matrix.png"],["ubuntu","09-theme-ubuntu.png"],["commodore","10-theme-commodore.png"]]){
      await openDemo(d,{layout:"desktop",variant,mode:"dark",view:"chat"});
      await shot(d,name);
    }
    await openDemo(d,{layout:"desktop",variant:"grok",mode:"light",view:"chat"});
    await shot(d,"11-theme-grok-light.png");
    await openDemo(d,{layout:"desktop",variant:"grok",mode:"dark",privacy:true,view:"chat"});
    await shot(d,"12-spoiler-desktop.png");
    await shot(d,"desktop-spoiler.png");
    await desk.close();
    const phone=await browser.newContext({...devices["Pixel 7"],viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2});
    const p=await phone.newPage();
    await openDemo(p,{layout:"mobile",variant:"grok",mode:"dark"});
    await shot(p,"13-phone-chat-grok.png");
    await shot(p,"phone-chat.png");
    await ensureToolsInMenu(p);
    await openCommandDeck(p);
    await shot(p,"14-phone-command-deck.png");
    await p.keyboard.press("Escape").catch(()=>{});
    await p.evaluate(()=>{try{if(window.closeMoreMenu)window.closeMoreMenu()}catch(e){}});
    await openDemo(p,{layout:"mobile",variant:"grok",mode:"dark",privacy:true});
    await shot(p,"15-phone-spoiler.png");
    await shot(p,"phone-spoiler.png");
    await openDemo(p,{layout:"mobile",variant:"scient",mode:"dark"});
    await shot(p,"16-phone-scient.png");
    await phone.close();
    const aliases={
      "desktop-tools.png":"03-command-deck-tools.png",
      "desktop-cockpit-spoiler.png":"12-spoiler-desktop.png",
      "desktop-menu-spoiler.png":"02-command-deck.png",
      "composer-tools-spoiler.png":"03-command-deck-tools.png",
      "phone-grok-spoiler.png":"15-phone-spoiler.png",
      "setup-spoiler.png":"06-setup-themes-grok.png",
      "hero-desktop-spoiler.png":"01-hero-desktop-grok.png",
      "hero-menu-spoiler.png":"02-command-deck.png",
      "hero-phone-spoiler.png":"13-phone-chat-grok.png",
      "02-sessions-chat-spoiler.png":"01-hero-desktop-grok.png",
      "03-chat-history-spoiler.png":"01-hero-desktop-grok.png",
      "04-menu-spoiler.png":"02-command-deck.png",
      "05-composer-tools-spoiler.png":"03-command-deck-tools.png",
      "06-phone-spoiler.png":"15-phone-spoiler.png",
      "07-phone-grok-spoiler.png":"13-phone-chat-grok.png"
    };
    for(const [legacy,src] of Object.entries(aliases)){
      try{await copyFile(join(out,src),join(out,legacy));console.log("alias",legacy,"<-",src)}catch(e){console.warn("alias skip",legacy,e.message)}
    }
  }finally{
    await browser.close();
  }
  console.log("done →",out);
}
main().catch(e=>{console.error(e);process.exit(1)});
