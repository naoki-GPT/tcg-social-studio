// v1.9: 作り方カードのひな形。スライド枚数どおりの場面・冒頭の動き・最後のCTA・同じ商品の出直しを検査する。
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dependencies,browserOptions} from './runtime.mjs';
const tpl=readFileSync(new URL('../templates/recipe/index.html',import.meta.url),'utf8');
const card=n=>JSON.parse(readFileSync(new URL(`../templates/recipe-card.example.${n}.json`,import.meta.url),'utf8'));
const img='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800"><rect width="600" height="800" fill="red"/></svg>');
function content(over={}){const c=JSON.parse(readFileSync(new URL('../templates/recipe-content.example.json',import.meta.url),'utf8'));delete c._note;
 c.draft=false;c.brand='TEST';for(const k in c.texts)c.texts[k]='Text '+k;c.texts.cta='DM "TESTWORD" FOR A QUOTE';c.products=[{name:'A',image:img},{name:'B',image:img}];return {...c,...over};}
async function open(browser,recipe,c){const [w,h]=recipe.canvas.ratio==='4:5'?[1080,1350]:[1080,1920];const page=await browser.newPage({viewport:{width:w,height:h}});
 await page.setContent(tpl.replace('<script src="recipe.js"></script><script src="content.js"></script>',`<script>window.RECIPE=${JSON.stringify(recipe)};window.CONTENT=${JSON.stringify(c)}</script>`));
 await page.waitForFunction(()=>[...document.images].every(x=>x.complete));return page;}
test('recipe slideshow: one scene per slide and CTA on last slide',async()=>{
 const browser=await dependencies().chromium.launch(browserOptions());
 try{const r=card('slideshow');let page=await open(browser,r,content());
  assert.equal(await page.evaluate(()=>window.__sceneStarts.length),r.slide_count);
  assert.equal(await page.evaluate(()=>window.STORY.ratio),'4:5');
  for(const t of await page.evaluate(()=>window.__sceneStarts)){await page.evaluate(t=>window.__seek(t+.6),t);assert.deepEqual(await page.evaluate(()=>window.__check()),[]);}
  const c=content();c.texts.cta='';page=await open(browser,r,c);
  const bad=await page.evaluate(()=>window.__check());assert.ok(bad.includes('CTA missing at end'));assert.ok(bad.some(x=>x.startsWith('Missing text')));
 }finally{await browser.close()}
});
test('recipe video: opening effects are time-based and deterministic',async()=>{
 const browser=await dependencies().chromium.launch(browserOptions());
 try{const r=card('video');const page=await open(browser,r,content());
  assert.equal(await page.evaluate(()=>window.__dur),r.duration_s);
  const at=t=>page.evaluate(t=>{window.__seek(t);return [...document.querySelectorAll('.layer')].map(n=>[n.classList.contains('on'),n.style.opacity,n.style.transform,n.style.left,n.textContent].join('|'))},t);
  const a=await at(0.45),b=await at(3.3);assert.notDeepEqual(a,b);assert.deepEqual(await at(0.45),a);
  const flash=await page.evaluate(()=>{window.__seek(0.05);return +document.querySelector('.layer.shape').style.opacity});assert.ok(flash>0.3);
  const typed=await page.evaluate(()=>{window.__seek(3.3);return [...document.querySelectorAll('.layer.text.on')].map(n=>n.textContent)});assert.ok(typed.some(x=>x.length>0&&'Text detail'.startsWith(x)&&x!=='Text detail'));
  assert.deepEqual(await page.evaluate(()=>{window.__seek(7.9);return window.__check()}),[]);
  const moved=await page.evaluate(()=>{const p=document.querySelector('.layer.product');window.__seek(4.9);const a=p.style.width;window.__seek(5.6);return [a,p.style.width]});assert.notEqual(moved[0],moved[1]);
 }finally{await browser.close()}
});
test('recipe video: restarting the same product is flagged',async()=>{
 const browser=await dependencies().chromium.launch(browserOptions());
 try{const r=card('video');const p=r.timeline.find(x=>x.element==='product');p.t_end=5.2;delete p.move;r.timeline.push({...p,t_start:5.2,t_end:8});
  const page=await open(browser,r,content());assert.match((await page.evaluate(()=>window.__checkContinuity())).join(),/restarts/);
 }finally{await browser.close()}
});
test('v2 observed hard cuts and explicit motion keyframes',async()=>{
 const browser=await dependencies().chromium.launch(browserOptions());
 try{const r=card('video'),p=r.timeline.find(x=>x.element==='product');delete p.move;
  p.keyframes=[{at:0,x_px:0,y_px:0,scale:1,rotation:0,opacity:1},{at:1,x_px:100,y_px:20,scale:1.5,rotation:10,opacity:.8}];
  const page=await open(browser,r,content());
  const read=t=>page.evaluate(t=>{window.__seek(t);const n=document.querySelector('.layer.product');return [n.style.transform,n.style.opacity]},t);
  const half=await read(p.t_start+.5);assert.match(half[0],/translate\(50px,\s*10px\) scale\(1.25\) rotate\(5deg\)/);assert.equal(+half[1],.9);
  await read(7);assert.deepEqual(await read(p.t_start+.5),half);
  p.t_end=4;r.timeline.push({...p,t_start:4,t_end:8,reference_cut:true,observed:'Source has hard cut at frame 120'});
  const cut=await open(browser,r,content());assert.deepEqual(await cut.evaluate(()=>window.__checkContinuity()),[]);
 }finally{await browser.close()}
});
test('v2 caption CTA does not force a new final slide or shrink text',async()=>{
 const browser=await dependencies().chromium.launch(browserOptions());
 try{const r=card('slideshow');r.cta_placement=['caption'];for(const s of r.slides)s.layers=s.layers.filter(l=>l.style!=='cta');
  const c=content();const first=r.slides[0].layers.find(l=>l.element==='text');c.texts[first.slot]='OVERFLOW '.repeat(200);
  const page=await open(browser,r,c);await page.evaluate(()=>window.__seek(.6));
  const bad=await page.evaluate(()=>window.__check());assert.ok(!bad.includes('CTA missing at end'));assert.ok(bad.some(x=>x.startsWith('Text overflow')));
  const sizes=await page.evaluate(()=>{const n=document.querySelector('.layer.text');return [+n.dataset.base,parseFloat(n.style.fontSize)]});assert.equal(sizes[0],sizes[1]);
 }finally{await browser.close()}
});
