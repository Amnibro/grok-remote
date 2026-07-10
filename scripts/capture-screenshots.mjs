import {chromium,devices} from "playwright-core";
import {mkdir,copyFile,unlink} from "fs/promises";
import {dirname,join} from "path";
import {fileURLToPath} from "url";
import {existsSync} from "fs";
const __dir=dirname(fileURLToPath(import.meta.url));
const root=join(__dir,"..");
const out=join(root,"docs","screenshots");
const base=process.env.GROK_REMOTE_URL||"http://127.0.0.1:2421";
const demo="demo=1&variant=grok&mode=dark&tour=0&auto=0";
function chromePath(){
  const c=[
    process.env.CHROME_PATH,
    "C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe",
    "C:\\\\Program Files (x86)\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe",
    process.env.LOCALAPPDATA&&join(process.env.LOCALAPPDATA,"Google","Chrome","Application","chrome.exe")
  ].filter(Boolean);
  for(const p of c){if(existsSync(p))return p}
  throw new Error("Chrome not found");
}
async function shot(page,name){
  const p=join(out,name);
  await page.screenshot({path:p});
  console.log("wrote",name);
}
async function prep(page,{privacy=false,layout="desktop"}={}){
  await page.goto(`${base}/?${demo}&privacy=${privacy?1:0}&layout=${layout}&chat=1`,{waitUntil:"networkidle",timeout:30000});
  await page.waitForFunction(()=>document.querySelectorAll("#sessList .item").length>0||document.querySelector("#feed .row"),{timeout:20000});
  await page.evaluate(({privacy,layout})=>{
    if(layout==="desktop")document.body.classList.add("desktop");
    else{document.body.classList.remove("desktop","electron");document.body.classList.add("touch-ui");document.body.classList.remove("can-hover")}
    if(window.applyTheme)window.applyTheme("grok","dark",false);
    if(window.setPrivacy)window.setPrivacy(!!privacy);
    if(window.applyUx)window.applyUx();
    if(window.paintDemoChat)window.paintDemoChat();
    document.querySelectorAll(".tool.collapsed").forEach(el=>el.classList.remove("collapsed"));
  },{privacy,layout});
  await page.waitForTimeout(450);
}
async function main(){
  await mkdir(out,{recursive:true});
  const browser=await chromium.launch({executablePath:chromePath(),headless:true});
  try{
    const desk=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1});
    const d=await desk.newPage();
    await prep(d,{privacy:false,layout:"desktop"});
    await shot(d,"desktop-chat.png");
    await d.evaluate(()=>{
      const tray=document.getElementById("composerTools"),btn=document.getElementById("btnPlus");
      if(tray){tray.classList.add("on");tray.style.display="flex"}
      if(btn){btn.classList.add("on");btn.textContent="×";btn.setAttribute("aria-expanded","true")}
    });
    await d.waitForTimeout(300);
    await shot(d,"desktop-tools.png");
    await d.evaluate(()=>{
      const tray=document.getElementById("composerTools");if(tray)tray.classList.remove("on");
      const btn=document.getElementById("btnPlus");if(btn){btn.classList.remove("on");btn.textContent="+"}
      const more=document.getElementById("btnMore");if(more)more.click();
    });
    await d.waitForTimeout(350);
    await shot(d,"desktop-menu.png");
    await d.keyboard.press("Escape");
    await prep(d,{privacy:true,layout:"desktop"});
    await shot(d,"desktop-spoiler.png");
    await d.goto(`${base}/?${demo}&privacy=0&layout=desktop&view=setup`,{waitUntil:"networkidle",timeout:30000});
    await d.evaluate(()=>{
      if(window.showPage)window.showPage("setup",true);
      if(window.applyTheme)window.applyTheme("grok","dark",false);
      if(window.setPrivacy)window.setPrivacy(false);
      if(window.applyUx)window.applyUx();
    });
    await d.waitForTimeout(400);
    await shot(d,"setup.png");
    await desk.close();
    const phone=await browser.newContext({...devices["Pixel 7"],viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2});
    const p=await phone.newPage();
    await prep(p,{privacy:false,layout:"mobile"});
    await shot(p,"phone-chat.png");
    await prep(p,{privacy:true,layout:"mobile"});
    await shot(p,"phone-spoiler.png");
    await phone.close();
    const aliases={
      "desktop-cockpit-spoiler.png":"desktop-spoiler.png",
      "desktop-menu-spoiler.png":"desktop-menu.png",
      "composer-tools-spoiler.png":"desktop-tools.png",
      "phone-grok-spoiler.png":"phone-spoiler.png",
      "setup-spoiler.png":"setup.png",
      "hero-desktop-spoiler.png":"desktop-chat.png",
      "hero-menu-spoiler.png":"desktop-menu.png",
      "hero-phone-spoiler.png":"phone-chat.png",
      "02-sessions-chat-spoiler.png":"desktop-chat.png",
      "03-chat-history-spoiler.png":"desktop-chat.png",
      "04-menu-spoiler.png":"desktop-menu.png",
      "05-composer-tools-spoiler.png":"desktop-tools.png",
      "06-phone-spoiler.png":"phone-spoiler.png",
      "07-phone-grok-spoiler.png":"phone-chat.png"
    };
    for(const [legacy,src] of Object.entries(aliases)){
      try{await copyFile(join(out,src),join(out,legacy))}catch(e){console.warn("alias skip",legacy,e.message)}
    }
  }finally{
    await browser.close();
  }
  console.log("done");
}
main().catch(e=>{console.error(e);process.exit(1)});
