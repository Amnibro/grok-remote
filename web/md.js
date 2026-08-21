(function(){
const E={"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"};
const esc=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>E[c]);
const HLKW={py:"and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield None True False self",
 js:"await async break case catch class const continue default delete do else export extends finally for function if import in instanceof let new of return static super switch this throw try typeof var void while yield null true false undefined",
 rs:"as async await break const continue crate dyn else enum extern fn for if impl in let loop match mod move mut pub ref return self static struct super trait type unsafe use where while true false",
 sh:"if then else elif fi for while do done case esac function return export local source echo cd exit",
 sql:"select from where insert update delete join left right inner outer group by order having limit values set into create table drop alter"};
HLKW.python=HLKW.py;HLKW.javascript=HLKW.js;HLKW.ts=HLKW.js;HLKW.typescript=HLKW.js;HLKW.jsx=HLKW.js;HLKW.rust=HLKW.rs;HLKW.bash=HLKW.sh;HLKW.shell=HLKW.sh;HLKW.ps1=HLKW.sh;
function hl(src,lang){
 lang=(lang||"").toLowerCase();
 const kw=new Set((HLKW[lang]||HLKW.py).split(" ")),isJson=lang==="json",isW=c=>/[A-Za-z0-9_$]/.test(c);
 let out="",i=0;const n=src.length;
 while(i<n){
  const c=src[i];
  if((c==="#"&&!isJson&&lang!=="js")||(c==="/"&&src[i+1]==="/")){let j=src.indexOf("\n",i);j=j<0?n:j;out+='<span class="hl-com">'+esc(src.slice(i,j))+"</span>";i=j;continue}
  if(c==="/"&&src[i+1]==="*"){let j=src.indexOf("*/",i);j=j<0?n:j+2;out+='<span class="hl-com">'+esc(src.slice(i,j))+"</span>";i=j;continue}
  if(c==='"'||c==="'"||c==="`"){let j=i+1;while(j<n&&src[j]!==c){j+=src[j]==="\\"?2:1}j=Math.min(j+1,n);out+='<span class="hl-str">'+esc(src.slice(i,j))+"</span>";i=j;continue}
  if(/[0-9]/.test(c)&&!isW(src[i-1]||"")){let j=i;while(j<n&&/[0-9a-fA-FxX._]/.test(src[j]))j++;out+='<span class="hl-num">'+esc(src.slice(i,j))+"</span>";i=j;continue}
  if(isW(c)){let j=i;while(j<n&&isW(src[j]))j++;const w=src.slice(i,j);let k=j;while(k<n&&src[k]===" ")k++;out+=kw.has(w)?'<span class="hl-kw">'+esc(w)+"</span>":src[k]==="("?'<span class="hl-fn">'+esc(w)+"</span>":esc(w);i=j;continue}
  if(/[+\-*/%=<>!|^~:?]/.test(c)){out+='<span class="hl-op">'+esc(c)+"</span>";i++;continue}
  out+=esc(c);i++;
 }
 return out;
}
const RE={hr:/^ {0,3}([-*_])[ \t]*(?:\1[ \t]*){2,}$/,
 head:/^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$/,
 quote:/^ {0,3}>[ \t]?(.*)$/,
 li:/^([ \t]*)([-*+\u2022]|\d{1,9}[.)])[ \t]+(.*)$/,
 code:/^(?: {4}|\t)(.*)$/,
 delim:/^[ \t]*(?=[^\n]*\|)\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$/,
 task:/^\[([ xX])\][ \t]+([\s\S]*)$/};
const isBlock=l=>RE.hr.test(l)||RE.head.test(l)||RE.quote.test(l)||RE.li.test(l);
function inl(s){
 const cs=[];
 s=String(s==null?"":s).replace(/(`+)([\s\S]*?[^`])\1(?!`)/g,(m,t,c)=>{cs.push(c);return "\uE020"+(cs.length-1)+"\uE021"});
 s=esc(s);
 const wsrel=u=>/^(?!\/|[a-zA-Z][a-zA-Z0-9+.-]*:)[\w][^\s<>"]*$/.test(u)||/^(\.\/|workspace\/)/.test(u);
 const unent=u=>u.replace(/&amp;/g,"&").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&quot;/g,'"').replace(/&#39;/g,"'");
 const wspath=u=>unent(u).replace(/^\.\//,"").replace(/^workspace\//,"");
 s=s.replace(/!\[([^\]]*)\]\(\s*([^)\s]+)[^)]*\)/g,(m,a,u)=>
  /^(https?:|data:image\/)/.test(u)?'<img src="'+u+'" alt="'+a+'" loading="lazy">':m);
 s=s.replace(/\[([^\]]*)\]\(\s*([^)\s]+)[^)]*\)/g,(m,a,u)=>
  /^(https?:|mailto:|#|\/)/.test(u)?'<a class="md-a" href="'+u+'" target="_blank" rel="noopener">'+(a||u)+"</a>":m);
 s=s.replace(/(^|[\s(])((?:https?:\/\/|www\.)[^\s<)]*[^\s<).,;:!?'"])/g,(m,p,u)=>p+'<a class="md-a" href="'+(u.indexOf("www.")===0?"https://"+u:u)+'" target="_blank" rel="noopener">'+u+"</a>");
 s=s.replace(/\*\*\*(?=\S)([\s\S]*?\S)\*\*\*/g,"<strong><em>$1</em></strong>");
 s=s.replace(/\*\*(?=\S)([\s\S]*?\S)\*\*/g,"<strong>$1</strong>");
 s=s.replace(/(^|[^\w_])__(?=\S)([\s\S]*?\S)__(?!\w)/g,"$1<strong>$2</strong>");
 s=s.replace(/(^|[^\w*])\*(?=\S)([^*\n]*?\S)\*(?!\w)/g,"$1<em>$2</em>");
 s=s.replace(/(^|[^\w_])_(?=\S)([^_\n]*?\S)_(?!\w)/g,"$1<em>$2</em>");
 s=s.replace(/~~(?=\S)([\s\S]*?\S)~~/g,"<s>$1</s>");
 s=s.replace(/[ \t]{2,}$/gm,"<br>");
 return s.replace(/\uE020(\d+)\uE021/g,(m,i)=>"<code>"+esc(cs[+i])+"</code>");
}
const liText=t=>{const m=RE.task.exec(t);return m?'<span class="task"><input type="checkbox" disabled'+(m[1]===" "?"":" checked")+">"+inl(m[2])+"</span>":inl(t)};
function cells(row){
 row=row.trim();
 const lead=row.charAt(0)==="|",trail=row.length>1&&row.charAt(row.length-1)==="|"&&row.charAt(row.length-2)!=="\\";
 const out=[];let cur="",tick=false;
 for(let i=0;i<row.length;i++){
  const c=row[i];
  if(c==="\\"&&row[i+1]==="|"){cur+="|";i++;continue}
  if(c==="`")tick=!tick;
  if(c==="|"&&!tick){out.push(cur);cur="";continue}
  cur+=c;
 }
 out.push(cur);
 lead&&out.shift();trail&&out.pop();
 return out.map(x=>x.trim());
}
function table(L,i){
 const head=cells(L[i]);
 if(!head.length)return null;
 const al=cells(L[i+1]).map(c=>/^:-+:$/.test(c)?"center":/^:-+$/.test(c)?"left":/^-+:$/.test(c)?"right":"");
 let j=i+2;const rows=[];
 while(j<L.length&&L[j].trim()&&L[j].indexOf("|")>=0&&!RE.delim.test(L[j])){rows.push(cells(L[j]));j++}
 const cellTag=(t,c,k)=>"<"+t+(al[k]?' style="text-align:'+al[k]+'"':"")+">"+inl(c)+"</"+t+">";
 const th=head.map((c,k)=>cellTag("th",c,k)).join("");
 const tb=rows.map(r=>"<tr>"+head.map((_,k)=>cellTag("td",r[k]||"",k)).join("")+"</tr>").join("");
 return {html:'<div class="tw"><table><thead><tr>'+th+"</tr></thead><tbody>"+tb+"</tbody></table></div>",next:j};
}
function gather(L,i){
 const items=[];let cur=null;
 while(i<L.length){
  const m=RE.li.exec(L[i]);
  if(m){cur={ind:m[1].replace(/\t/g,"  ").length,ord:/\d/.test(m[2]),start:parseInt(m[2],10)||1,text:m[3]};items.push(cur);i++;continue}
  if(!L[i].trim()){
   let j=i;while(j<L.length&&!L[j].trim())j++;
   if(j<L.length&&RE.li.test(L[j])){i=j;continue}
   break}
  if(cur&&/^[ \t]{2,}\S/.test(L[i])){cur.text+="\n"+L[i].trim();i++;continue}
  break;
 }
 return {items:items,next:i};
}
function renderList(items,pos,ind){
 const first=items[pos],ord=first.ord;
 let html=ord?"<ol"+(first.start>1?' start="'+first.start+'"':"")+">":"<ul>";
 while(pos<items.length&&items[pos].ind>=ind){
  const it=items[pos];
  if(it.ind>ind){
   const sub=renderList(items,pos,it.ind);
   html=/<\/li>$/.test(html)?html.replace(/<\/li>$/,sub.html+"</li>"):html+"<li>"+sub.html+"</li>";
   pos=sub.pos;continue}
  if(it.ord!==ord)break;
  html+="<li>"+liText(it.text)+"</li>";
  pos++;
 }
 return {html:html+(ord?"</ol>":"</ul>"),pos:pos};
}
function blocks(src){
 const L=String(src==null?"":src).replace(/\r\n?/g,"\n").split("\n");
 let out="",i=0;
 while(i<L.length){
  const l=L[i];
  if(!l.trim()){i++;continue}
  if(RE.hr.test(l)){out+="<hr>";i++;continue}
  let m=RE.head.exec(l);
  if(m){const n=Math.min(m[1].length,4);out+="<h"+n+">"+inl(m[2])+"</h"+n+">";i++;continue}
  if(RE.quote.test(l)){
   const buf=[];
   while(i<L.length&&L[i].trim()&&(RE.quote.test(L[i])||buf.length&&!isBlock(L[i]))){const q=RE.quote.exec(L[i]);buf.push(q?q[1]:L[i].trim());i++}
   out+="<blockquote>"+blocks(buf.join("\n"))+"</blockquote>";continue}
  if(i+1<L.length&&l.indexOf("|")>=0&&RE.delim.test(L[i+1])){
   const t=table(L,i);
   if(t){out+=t.html;i=t.next;continue}}
  if(RE.li.test(l)){
   const g=gather(L,i);
   if(g.items.length){
    let pos=0;
    while(pos<g.items.length){const r=renderList(g.items,pos,g.items[pos].ind);out+=r.html;pos=r.pos>pos?r.pos:pos+1}
    i=g.next;continue}}
  if(RE.code.test(l)){
   const buf=[];
   while(i<L.length){
    if(!L[i].trim()){let j=i;while(j<L.length&&!L[j].trim())j++;if(j>=L.length||!RE.code.test(L[j]))break;buf.push("");i=j;continue}
    if(!RE.code.test(L[i]))break;
    buf.push(RE.code.exec(L[i])[1]);i++}
   out+="<pre><code>"+esc(buf.join("\n"))+"</code></pre>";continue}
  const buf=[];
  while(i<L.length&&L[i].trim()&&!isBlock(L[i])&&!(i+1<L.length&&L[i].indexOf("|")>=0&&RE.delim.test(L[i+1]))){buf.push(L[i]);i++}
  if(!buf.length){buf.push(L[i]);i++}
  out+="<p>"+inl(buf.join("\n")).replace(/\n+/g," ")+"</p>";
 }
 return out;
}
function mdmath(raw){
 const math=[];let t=String(raw==null?"":raw);
 const grab=(re,display)=>{t=t.replace(re,(m,a,b)=>{math.push({tex:(a!==undefined?a:b)||"",display:display});return "\uE040"+(math.length-1)+"\uE041"})};
 grab(/\$\$([\s\S]+?)\$\$/g,true);
 grab(/\\\[([\s\S]+?)\\\]/g,true);
 grab(/\\\(([\s\S]+?)\\\)/g,false);
 grab(/(?<![\\$\w])\$(?![\s$])([^$\n]*?[^\s$])\$(?![\d$])/g,false);
 return {text:t,math:math};
}
function mathback(html,math){
 return html.replace(/\uE040(\d+)\uE041/g,(m,i)=>{
  const it=math[+i];
  if(!it)return m;
  const tex=String(it.tex).replace(/\uE042/g,"\\$");
  if(window.katex){try{return katex.renderToString(tex,{displayMode:it.display,throwOnError:false,strict:"ignore",output:"html"})}catch(e){}}
  return '<code class="rawmath">'+esc(it.display?"\\["+tex+"\\]":"\\("+tex+"\\)")+"</code>";
 });
}
function md(t){
 const code=[];
 let s=String(t==null?"":t).replace(/\r\n?/g,"\n");
 s=s.replace(/(^|\n)[ \t]{0,3}(```|~~~)([^\n]*)\n([\s\S]*?)(?:\n[ \t]{0,3}\2+[ \t]*(?=\n|$)|$)/g,(m,p,f,info,body)=>{code.push({lang:(info||"").trim().split(/[\s,]+/)[0],src:body});return p+"\uE030"+(code.length-1)+"\uE031"});
 s=s.replace(/\\\$/g,"\uE042");
 const ex=mdmath(s);
 return mathback(blocks(ex.text),ex.math).replace(/\uE042/g,"$").replace(/(?:<p>)?\uE030(\d+)\uE031(?:<\/p>)?/g,(m,i)=>{
  const b=code[+i];
  return b?'<pre><code class="lang-'+(b.lang||"txt")+'">'+hl(b.src,b.lang)+"</code></pre>":"";
 });
}
window.md=md;window.mdInline=inl;window.mdbody=blocks;window.mdEsc=esc;window.hl=hl;
window.mdbody_safe=t=>{try{return md(t)}catch(e){return "<p>"+esc(t)+"</p>"}};
window.tex=function(){};
})();
