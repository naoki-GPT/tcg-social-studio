// v4: カルーセル用HTMLの各スライド要素を 01.png, 02.png ... として書き出す。
// 使い方: node scripts/shoot_slides.mjs <index.html> --out <新規フォルダ> [--width 1080 --height 1350 --selector .slide]
// 各スライド要素は指定サイズ（既定 1080x1350）ちょうどで作る。
import {writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {parseArgs,number,freshDir,launchBrowser,openLocalPage,inspectAssets,fail} from './runtime.mjs';

const USAGE='usage: node scripts/shoot_slides.mjs <index.html> --out <new dir> [--width 1080 --height 1350 --selector .slide]';
let browser;
try{
 const a=parseArgs(process.argv.slice(2),{values:['out','width','height','selector']});
 if(a._.length!==1||!a.out)throw Error(USAGE);
 const width=number(a.width,1080,16,4096,'--width');
 const height=number(a.height,1350,16,4096,'--height');
 if(!Number.isInteger(width)||!Number.isInteger(height))throw Error('--width and --height must be integers');
 const selector=a.selector||'.slide';

 const launched=await launchBrowser();browser=launched.browser;
 console.log(`[INFO] browser: ${launched.used} ${launched.version}`);
 const {page,problems}=await openLocalPage(browser,a._[0],width,height);
 const readyError=await page.evaluate(()=>(window.ready&&typeof window.ready.then==='function')?Promise.race([
  window.ready.then(()=>null,e=>String(e&&e.message||e)),
  new Promise(r=>setTimeout(()=>r('window.ready did not finish within 30 seconds'),30000)),
 ]):null);
 if(readyError)throw Error('window.ready failed: '+readyError);

 const assets=await inspectAssets(page);
 if(assets.badFonts.length)fail('fonts are not applied: '+assets.badFonts.map(f=>`${f.family} (${f.weight} ${f.style}, ${f.status})`).join(', '),{fontFaces:assets.fonts,hint:'Check the url() of each @font-face. Bundled fonts live in the skill "fonts" folder.'});
 for(const f of assets.fonts)console.log(`[OK] font applied: ${f.family} (${f.weight})`);
 if(!assets.fonts.length)console.log('[INFO] no @font-face in this HTML. Text is drawn with fonts installed on this PC, so the look can differ on another PC.');
 if(assets.missingImages.length||problems.failedRequests.length)fail('some images or files could not be loaded',{missingImages:assets.missingImages,failedRequests:problems.failedRequests});
 if(problems.pageErrors.length)fail('the page threw errors while loading',problems.pageErrors);

 const slides=page.locator(selector);
 const count=await slides.count();
 if(!count)throw Error(`no element matches "${selector}".`);
 const boxes=[];
 for(let i=0;i<count;i++){
  const b=await slides.nth(i).boundingBox();
  boxes.push(b?{index:i+1,width:Math.round(b.width*100)/100,height:Math.round(b.height*100)/100}:{index:i+1,width:0,height:0});
 }
 const wrong=boxes.filter(b=>Math.abs(b.width-width)>0.01||Math.abs(b.height-height)>0.01);
 if(wrong.length)fail(`each "${selector}" element must be exactly ${width}x${height}px (hidden elements count as 0x0)`,wrong);

 const out=freshDir(a.out);
 const digits=Math.max(2,String(count).length);const files=[];
 for(let i=0;i<count;i++){
  const name=String(i+1).padStart(digits,'0')+'.png';
  await slides.nth(i).screenshot({path:join(out,name),type:'png',animations:'disabled'});
  files.push(name);console.log('[OK] '+name);
 }
 if(problems.pageErrors.length)fail('the page threw errors',problems.pageErrors);
 writeFileSync(join(out,'slides.json'),JSON.stringify({count,width,height,selector,files,fonts:assets.fonts,browser:launched.used,blocked_external_requests:problems.blocked},null,2));
 if(problems.blocked.length)console.log(`[INFO] blocked ${problems.blocked.length} external request(s): ${[...new Set(problems.blocked)].slice(0,5).join(', ')}`);
 console.log(`[OK] ${count} slide(s) (${width}x${height}) -> ${out}`);
 await browser.close();
}catch(e){
 if(browser)await browser.close().catch(()=>{});
 fail(e.message,e.tried);
}
