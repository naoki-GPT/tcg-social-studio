// v1.1: 編集済みstoryの全場面をPNGへ。未入力・画像欠損・文字あふれは停止する。
import {writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {args,number,dependencies,browserOptions,loadPage,seek,freshDir} from './runtime.mjs';
const o=args(process.argv.slice(2));
if(!o.input||!o.out)throw Error('Usage: node export_slides.mjs index.html --out new-folder [--ratio 4:5]');
const ratio=o.ratio||'4:5';if(!['4:5','9:16','custom'].includes(ratio))throw Error('Invalid ratio');
const {chromium}=dependencies();const browser=await chromium.launch(browserOptions());
try{
 const width=number(o.width,1080,100,4096,'width'),height=number(o.height,ratio==='9:16'?1920:1350,100,4096,'height');const {page,errors,state}=await loadPage(browser,o.input,width,height);
 const actual=await page.evaluate(()=>window.STORY.ratio);if(actual!==ratio)throw Error('Ratio differs from content.js');
 const declared=await page.evaluate(()=>window.STORY);if((declared.width&&declared.width!==width)||(declared.height&&declared.height!==height))throw Error('Canvas size mismatch');
 const starts=await page.evaluate(()=>window.__sceneStarts);const checks=[];const times=starts.map((t,i)=>{const end=starts[i+1]??state.duration;if(end<=t)throw Error('Invalid slide order');return t+Math.min(.6,(end-t)/2)});
 // 全場面を先に点検し、途中までの画像を納品と取り違えない。
 for(const t of times){await seek(page,t);const bad=await page.evaluate(()=>window.__check());if(bad.length)throw Error(bad.join(', '));}
 const out=freshDir(o.out);
 for(let i=0;i<starts.length;i++){await seek(page,times[i]);const file=String(i+1).padStart(2,'0')+'.png';await page.screenshot({path:join(out,file)});checks.push({file,seconds:times[i],width,height});}
 if(errors.length)throw Error(errors.join('\n'));
 writeFileSync(join(out,'slides_check.json'),JSON.stringify({slides:checks,visual_review_required:true},null,2));console.log('[OK]',checks.length,'slides; inspect actual images before delivery');
}finally{await browser.close()}
