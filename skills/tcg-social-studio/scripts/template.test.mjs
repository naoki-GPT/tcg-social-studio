// v1: 架空SVGのみで、素材差し替えと全場面・逆送りを確認。本編MP4は作らない。
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,readFileSync,writeFileSync,copyFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {dependencies,browserOptions,loadPage,seek} from './runtime.mjs';

test('template supports 3/9 cards, local images and deterministic seeking',async()=>{
 const parent=resolve(tmpdir()),root=mkdtempSync(join(parent,'tcg-template-'));
 const template=fileURLToPath(new URL('../templates/reel/',import.meta.url));
 let browser;
 try{
  copyFileSync(join(template,'index.html'),join(root,'index.html'));
  writeFileSync(join(root,'fixture.svg'),'<svg xmlns="http://www.w3.org/2000/svg" width="630" height="880"><rect width="630" height="880" fill="#245853"/><text x="80" y="440" fill="white" font-size="64">TEST CARD</text></svg>');
  const {chromium}=dependencies();browser=await chromium.launch(browserOptions());
  for(const count of [3,9]){
   const cards=Array.from({length:count},(_,i)=>({id:String(i),name:'Fixture '+i,src:'fixture.svg',number:'TEST-'+i,language:'Test only'}));
   const source=readFileSync(join(template,'content.js'),'utf8');
   writeFileSync(join(root,'content.js'),source+'\nC.cards='+JSON.stringify(cards)+';C.selected=1;C.brand="Fixture shop";');
   const {page,state,errors}=await loadPage(browser,join(root,'index.html'),1080,1920);
   assert.equal(state.duration,24);assert.equal(await page.locator('#grid .card').count(),count);
   const expected=new Map([[0,'grid-scene'],[2.999,'grid-scene'],[3,'hero-scene'],[4.999,'hero-scene'],[5,'hero-scene'],[6.999,'hero-scene'],[7,'binder-scene'],[9.999,'binder-scene'],[10,'enquiry-scene'],[13.999,'enquiry-scene'],[14,'send-scene'],[17.999,'send-scene'],[18,'cta-scene'],[23.9,'cta-scene']]);
   for(const [t,scene] of expected){await seek(page,t);assert.equal(await page.locator('.scene:visible').getAttribute('id'),scene);}
   assert.match(await page.locator('#info').textContent(),/Fixture 1/);
   await seek(page,8);const first=await page.screenshot();await seek(page,19);await seek(page,8);assert.deepEqual(await page.screenshot(),first);
   assert.deepEqual(errors,[]);await page.close();
  }
 }finally{
  await browser?.close();
  // このテストが作成した一時フォルダだけを削除する。
  if(resolve(root).startsWith(parent+sep))rmSync(root,{recursive:true,force:true});
 }
});
