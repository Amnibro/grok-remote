import {chromium} from "playwright-core";
import {existsSync} from "fs";
import {resolve} from "path";
const url=process.argv[2];
const chromePath=()=>{
  const c=[process.env.CHROME_PATH,"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe","C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",process.env.LOCALAPPDATA&&resolve(process.env.LOCALAPPDATA,"Google","Chrome","Application","chrome.exe")].filter(Boolean);
  for(const p of c)if(existsSync(p))return p;
  throw new Error("Chrome not found");
};
const browser=await chromium.launch({executablePath:chromePath(),headless:true});
const page=await browser.newPage({viewport:{width:420,height:860}});
const errs=[];
page.on("pageerror",e=>errs.push("pageerror: "+String(e&&e.message||e)));
page.on("console",m=>{m.type()==="error"&&errs.push("console: "+m.text().slice(0,300))});
await page.goto(url,{waitUntil:"domcontentloaded",timeout:30000});
await page.waitForTimeout(9000);
const st=await page.evaluate(()=>({
  feedRows:document.querySelectorAll("#feed .row").length,
  feedChildren:(document.getElementById("feed")||{children:[]}).children.length,
  sessItems:document.querySelectorAll("#sessList .item").length,
  bodyClass:document.body.className,
  orbit:(document.getElementById("orbitStatus")||{}).textContent||"",
  phase:(document.getElementById("livebar")||{}).textContent||"",
  sid:typeof sid!=="undefined"?String(sid||""):"?",
  visible:!!(document.getElementById("feed")&&document.getElementById("feed").offsetHeight)
}));
await page.screenshot({path:"tests/probe_live_page.png",fullPage:false});
console.log(JSON.stringify(st,null,1));
console.log("errors:",errs.length?errs.slice(0,10):"none");
await browser.close();
