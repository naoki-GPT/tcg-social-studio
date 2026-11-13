// v1.4: 同一商品が飛ぶ不具合を検出し、別商品との切替と区別する。
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dependencies,browserOptions} from './runtime.mjs';
test('same product continuity and exact seek restoration',async()=>{
 const browser=await dependencies().chromium.launch(browserOptions());
 try{
  const page=await browser.newPage({viewport:{width:1080,height:1920}});
  const template=readFileSync(new URL('../templates/story/index.html',import.meta.url),'utf8');
  const image='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="630" height="880"><rect width="630" height="880" fill="blue"/></svg>');
  const scene={layout:'hero',heading:'A card',subheading:'Details',seconds:4,items:[{image,label:'Test',value:'Sample'}]};
  const data={ratio:'9:16',draft:false,scenes:[scene,{...scene,heading:'New text'}]};
  await page.setContent(template.replace('<script src="content.js"></script>','<script>window.STORY='+JSON.stringify(data)+'</script>'));
  await page.waitForFunction(()=>[...document.images].every(x=>x.complete&&x.naturalWidth));
  await page.evaluate(()=>window.__seek(5.25));
  assert.deepEqual(await page.evaluate(()=>window.__checkContinuity()),[]);
  assert.equal(await page.evaluate(()=>window.__time),5.25);
  await page.evaluate(()=>document.querySelectorAll('.media img')[1].style.transform='translateY(60px)');
  assert.match((await page.evaluate(()=>window.__checkContinuity())).join(),/Same product jumps/);
  assert.equal(await page.evaluate(()=>window.__time),5.25);
  await page.evaluate(()=>{const img=document.querySelectorAll('.media img')[1];img.src+='#different-product'});
  assert.deepEqual(await page.evaluate(()=>window.__checkContinuity()),[]);
 }finally{await browser.close()}
});
