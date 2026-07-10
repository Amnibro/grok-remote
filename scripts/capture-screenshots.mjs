import {chromium,devices} from "playwright-core";
import {mkdir,copyFile} from "fs/promises";
import {dirname,join} from "path";
import {fileURLToPath} from "url";
import {existsSync} from "fs";
const __dir=dirname(fileURLToPath(import.meta.url));
const root=join(__dir,"..");
const out=join(root,"docs","screenshots");
const base=process.env.GROK_REMOTE_URL||"http://127.0.0.1:2421";
const q="demo=1&variant=grok&mode=dark&privacy=1&tour=0&auto=0";
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
async function shot(page,name,full=false){
  const p=join(out,name);
  await page.screenshot({path:p,fullPage:!!full});
  console.log("wrote",name);
  return p;
}
async function waitUi(page,{needRail=true}={}){
  await page.waitForFunction((needRail)=>{
    const items=document.querySelectorAll("#sessList .item").length;
    const feed=document.getElementById("feed");
    const feedOk=feed&&feed.children.length>0;
    if(!needRail)return items>0||feedOk||document.body.classList.contains("page-chat");
    const pick=document.getElementById("picker");
    const railOn=pick&&(pick.classList.contains("on")||getComputedStyle(pick).display!=="none");
    return items>0&&railOn;
  },needRail,{timeout:20000});
  await page.waitForTimeout(400);
}
async function main(){
  await mkdir(out,{recursive:true});
  const browser=await chromium.launch({executablePath:chromePath(),headless:true});
  try{
    const desk=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1});
    const d=await desk.newPage();
    await d.goto(`${base}/?${q}&layout=desktop&chat=1`,{waitUntil:"networkidle",timeout:30000});
    await waitUi(d);
    await d.evaluate(()=>{document.body.classList.add("desktop");if(window.applyUx)window.applyUx()});
    await d.waitForTimeout(300);
    await shot(d,"desktop-cockpit-spoiler.png");
    await copyFile(join(out,"desktop-cockpit-spoiler.png"),join(out,"02-sessions-chat-spoiler.png"));
    await copyFile(join(out,"desktop-cockpit-spoiler.png"),join(out,"03-chat-history-spoiler.png"));
    await copyFile(join(out,"desktop-cockpit-spoiler.png"),join(out,"hero-desktop-spoiler.png"));
    const menuBtn=await d.$("#btnMenu, #menuBtn, button.menu, .hdrbtn.menu, #orbit");
    if(menuBtn){await menuBtn.click();await d.waitForTimeout(400)}
    else{
      await d.evaluate(()=>{
        const b=document.getElementById("btnMenu")||document.querySelector("[aria-label='Menu'], .hdrbtn");
        if(b)b.click();
        const m=document.getElementById("orbitMenu")||document.getElementById("mainMenu");
        if(m){m.classList.add("on","open");m.style.display="block"}
      });
      await d.waitForTimeout(400);
    }
    await shot(d,"desktop-menu-spoiler.png");
    await copyFile(join(out,"desktop-menu-spoiler.png"),join(out,"04-menu-spoiler.png"));
    await copyFile(join(out,"desktop-menu-spoiler.png"),join(out,"hero-menu-spoiler.png"));
    await d.keyboard.press("Escape");
    await d.evaluate(()=>{
      const plus=document.getElementById("btnPlus");
      if(plus)plus.click();
      const tools=document.getElementById("composerTools");
      if(tools){tools.classList.add("on","open");tools.style.display="flex"}
    });
    await d.waitForTimeout(350);
    await shot(d,"composer-tools-spoiler.png");
    await copyFile(join(out,"composer-tools-spoiler.png"),join(out,"05-composer-tools-spoiler.png"));
    await d.goto(`${base}/?${q}&layout=desktop&view=setup`,{waitUntil:"networkidle",timeout:30000});
    await d.evaluate(()=>{
      const panel=document.getElementById("setup")||document.querySelector(".panel");
      if(panel)panel.style.display="block";
      if(typeof showPage==="function")showPage("setup");
      else if(typeof pushPage==="function")pushPage("setup");
      else{document.body.dataset.page="setup";const p=document.getElementById("setup");if(p)p.classList.add("on")}
      if(window.applyTheme)window.applyTheme("grok","dark",false);
      if(window.setPrivacy)window.setPrivacy(true);
      if(window.applyUx)window.applyUx();
    });
    await d.waitForTimeout(400);
    await shot(d,"setup-spoiler.png");
    await desk.close();
    const phone=await browser.newContext({
      ...devices["Pixel 7"],
      viewport:{width:390,height:844},
      isMobile:true,
      hasTouch:true,
      deviceScaleFactor:2
    });
    const p=await phone.newPage();
    await p.goto(`${base}/?${q}&layout=mobile&chat=1`,{waitUntil:"networkidle",timeout:30000});
    await waitUi(p,{needRail:false});
    await p.evaluate(()=>{
      document.body.classList.remove("desktop","electron");
      document.body.classList.add("touch-ui");
      document.body.classList.remove("can-hover");
      if(window.applyTheme)window.applyTheme("grok","dark",false);
      if(window.setPrivacy)window.setPrivacy(true);
      if(window.applyUx)window.applyUx();
      const h=document.getElementById("hint");if(h)h.textContent="demo session · spoiler-safe";
    });
    await p.waitForTimeout(450);
    await shot(p,"phone-grok-spoiler.png");
    await copyFile(join(out,"phone-grok-spoiler.png"),join(out,"07-phone-grok-spoiler.png"));
    await copyFile(join(out,"phone-grok-spoiler.png"),join(out,"hero-phone-spoiler.png"));
    await p.evaluate(()=>{if(window.applyTheme)window.applyTheme("scient","dark",false);if(window.applyUx)window.applyUx()});
    await p.waitForTimeout(400);
    await shot(p,"phone-spoiler.png");
    await copyFile(join(out,"phone-spoiler.png"),join(out,"06-phone-spoiler.png"));
    await phone.close();
  }finally{
    await browser.close();
  }
  console.log("done");
}
main().catch(e=>{console.error(e);process.exit(1)});
