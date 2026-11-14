// v4: リール用HTMLを1コマずつ撮って連番画像にする。
// 使い方: node scripts/capture_frames.mjs <index.html> --out <新規フォルダ> --duration <秒> [--fps 30 --width 1080 --height 1920 --format jpg|png]
// HTML側の約束: window.seek(t) / window.ready (Promise) / window.fontCheck ({書体名: true|false})
import {writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {parseArgs,number,freshDir,launchBrowser,openLocalPage,inspectAssets,fail} from './runtime.mjs';

const USAGE='usage: node scripts/capture_frames.mjs <index.html> --out <new dir> --duration <sec> [--fps 30 --width 1080 --height 1920 --format jpg|png]';
let browser;
try{
 const a=parseArgs(process.argv.slice(2),{values:['out','duration','fps','width','height','format']});
 if(a._.length!==1||!a.out||a.duration===undefined)throw Error(USAGE);
 const duration=number(a.duration,undefined,0.1,600,'--duration');
 const fps=number(a.fps,30,1,60,'--fps');
 const width=number(a.width,1080,16,4096,'--width');
 const height=number(a.height,1920,16,4096,'--height');
 const format=(a.format||'jpg').toLowerCase();
 if(!['jpg','png'].includes(format))throw Error('Invalid --format (jpg or png)');
 if(!Number.isInteger(fps)||!Number.isInteger(width)||!Number.isInteger(height))throw Error('--fps, --width, --height must be integers');
 if(width%2||height%2)throw Error('--width and --height must be even numbers (required for MP4)');
 const total=Math.round(duration*fps);

 const launched=await launchBrowser();browser=launched.browser;
 console.log(`[INFO] browser: ${launched.used} ${launched.version}`);
 const {page,problems}=await openLocalPage(browser,a._[0],width,height);

 const contract=await page.evaluate(()=>({seek:typeof window.seek,ready:window.ready&&typeof window.ready.then==='function'}));
 if(contract.seek!=='function')throw Error('window.seek(t) is not defined in the HTML.');
 if(!contract.ready)throw Error('window.ready (a Promise that resolves after fonts are loaded) is not defined in the HTML.');
 const readyError=await page.evaluate(()=>Promise.race([
  window.ready.then(()=>null,e=>String(e&&e.message||e)),
  new Promise(r=>setTimeout(()=>r('window.ready did not finish within 30 seconds'),30000)),
 ]));
 if(readyError){
  const a2=await inspectAssets(page).catch(()=>({fonts:[],badFonts:[],missingImages:[]}));
  fail('window.ready failed: '+readyError,{fontsNotApplied:a2.badFonts.map(f=>`${f.family} (${f.weight} ${f.style}, ${f.status})`),missingImages:a2.missingImages,failedRequests:problems.failedRequests,hint:'Usually a font file in @font-face url() is missing. Bundled fonts live in the skill "fonts" folder.'});
 }

 const fontCheck=await page.evaluate(()=>window.fontCheck);
 if(!fontCheck||typeof fontCheck!=='object'||!Object.keys(fontCheck).length)throw Error('window.fontCheck is missing. Set it in window.ready as {"Font Name": document.fonts.check(...)}.');
 const notApplied=Object.entries(fontCheck).filter(([,v])=>v!==true).map(([k])=>k);
 const assets=await inspectAssets(page);
 const badFaces=assets.badFonts.map(f=>`${f.family} (${f.weight} ${f.style}, ${f.status})`);
 if(notApplied.length||badFaces.length){
  fail('fonts are not applied: '+[...new Set([...notApplied,...badFaces])].join(', '),{fontCheck,fontFaces:assets.fonts,hint:'Check the url() of each @font-face. Bundled fonts live in the skill "fonts" folder.'});
 }
 for(const [k] of Object.entries(fontCheck))console.log('[OK] font applied: '+k);
 if(assets.missingImages.length||problems.failedRequests.length)fail('some images or files could not be loaded',{missingImages:assets.missingImages,failedRequests:problems.failedRequests});
 if(await page.evaluate(()=>document.querySelectorAll('video,audio').length))throw Error('video/audio elements are not supported. Use still images + HTML; sound is added later by mix_audio.py.');
 if(problems.pageErrors.length)fail('the page threw errors while loading',problems.pageErrors);

 const out=freshDir(a.out);
 const digits=6,prefix='frame_';
 for(let i=0;i<total;i++){
  const t=i/fps;
  await page.evaluate(async t=>{await window.seek(t);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));},t);
  if(problems.pageErrors.length)fail(`the page threw errors at t=${t.toFixed(3)}`,problems.pageErrors);
  const path=join(out,prefix+String(i).padStart(digits,'0')+'.'+format);
  await page.screenshot(format==='jpg'?{path,type:'jpeg',quality:92}:{path,type:'png'});
  if((i+1)%(fps*2)===0||i===total-1)console.log(`[INFO] ${i+1}/${total} frames`);
 }
 const late=await page.evaluate(()=>[...document.images].filter(im=>!im.naturalWidth).map(im=>im.getAttribute('src')));
 if(late.length||problems.failedRequests.length)fail('some images could not be loaded during capture',{missingImages:late,failedRequests:problems.failedRequests});
 const info={frames:total,fps,width,height,duration:total/fps,format,pattern:`${prefix}%0${digits}d.${format}`,start_number:0,browser:launched.used,fontCheck,blocked_external_requests:problems.blocked};
 writeFileSync(join(out,'frames.json'),JSON.stringify(info,null,2));
 if(problems.blocked.length)console.log(`[INFO] blocked ${problems.blocked.length} external request(s): ${[...new Set(problems.blocked)].slice(0,5).join(', ')}`);
 console.log(`[OK] ${total} frames (${width}x${height}, ${fps}fps, ${(total/fps).toFixed(2)}s) -> ${out}`);
 await browser.close();
}catch(e){
 if(browser)await browser.close().catch(()=>{});
 fail(e.message,e.tried);
}
