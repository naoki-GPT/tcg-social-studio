// v1.1: 全19型・2比率・各場面と逆送りを架空の商品で確認。本編MP4は作らない。
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtempSync,readFileSync,writeFileSync,copyFileSync,rmSync,mkdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {dependencies,browserOptions,loadPage,seek} from './runtime.mjs';

test('19 formats at both ratios: layouts, populated content, overflow and reverse seek',async()=>{
 const parent=resolve(tmpdir()),root=mkdtempSync(join(parent,'tcg-story-'));let browser;
 try{
  copyFileSync(fileURLToPath(new URL('../templates/story/index.html',import.meta.url)),join(root,'index.html'));
  writeFileSync(join(root,'fixture.svg'),'<svg xmlns="http://www.w3.org/2000/svg" width="630" height="880"><rect width="630" height="880" rx="40" fill="#315b6c"/><text x="60" y="440" fill="white" font-size="58">TEST PRODUCT</text></svg>');
  const formats=JSON.parse(readFileSync(new URL('../templates/formats.json',import.meta.url),'utf8')).formats;
  browser=await dependencies().chromium.launch(browserOptions());
  for(const recipe of formats)for(const ratio of ['4:5','9:16']){
   const scenes=recipe.scenes.map(([layout,heading],sceneIndex)=>({layout,heading,subheading:'Verified product details',seconds:4,note:'Sample only. Shipping excluded. Checked 2026-10-31.',source:'Fixture source; not a market price.',items:Array.from({length:({hero:1,grid:3,compare:2,table:3,steps:3,cta:0})[layout]},(_,i)=>({label:'Test product '+sceneIndex+'-'+(i+1),value:layout==='compare'?'USD 130.00':'Japanese / TEST-01',image:'fixture.svg?product='+sceneIndex+'-'+i}))}));
   const data={draft:false,format:recipe.id,ratio,brand:'TEST SHOP',scenes};writeFileSync(join(root,'content.js'),'window.STORY='+JSON.stringify(data));
   const {page,errors}=await loadPage(browser,join(root,'index.html'),1080,ratio==='4:5'?1350:1920);
   for(let i=0;i<scenes.length;i++){
    for(const t of [i*4,i*4+.6,i*4+3.99]){await seek(page,t);assert.equal(await page.locator('.scene.active').getAttribute('data-index'),String(i));}
    assert.deepEqual(await page.evaluate(()=>window.__check()),[],recipe.id+' '+ratio+' '+i);
   }
   const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
   await seek(page,1);const firstImage=await page.screenshot(),first=hash(firstImage);await seek(page,scenes.length*4-.1);await seek(page,1);const secondImage=await page.screenshot();
   if(process.env.TCG_TEST_ARTIFACTS&&first!==hash(secondImage)){mkdirSync(process.env.TCG_TEST_ARTIFACTS,{recursive:true});writeFileSync(join(process.env.TCG_TEST_ARTIFACTS,'before.png'),firstImage);writeFileSync(join(process.env.TCG_TEST_ARTIFACTS,'after.png'),secondImage);}
   assert.equal(hash(secondImage),first,recipe.id+' '+ratio+' reverse seek');
   await page.evaluate(()=>{STORY.draft=true});assert.ok((await page.evaluate(()=>window.__check())).includes('DRAFT'));
   assert.deepEqual(errors,[]);await page.close();
  }
 }finally{await browser?.close();if(resolve(root).startsWith(parent+sep))rmSync(root,{recursive:true,force:true});}
});
