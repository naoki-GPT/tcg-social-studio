// v1: ローカルHTMLをPNGでコマ撮りして無音MP4へ。既存出力は上書きしない。
import {spawn} from 'node:child_process';import {mkdirSync,mkdtempSync,rmSync,existsSync} from 'node:fs';import {tmpdir} from 'node:os';import {join,resolve,dirname,relative,isAbsolute} from 'node:path';
import {args,number,freshFile,dependencies,browserOptions,loadPage,seek} from './runtime.mjs';
const o=args(process.argv.slice(2));if(!o.input||!o.out)throw Error('Usage: node render.mjs input.html --out output.mp4 [--width 1080 --height 1920 --fps 30 --workers 2]');
const width=number(o.width,1080,100,4096,'width'),height=number(o.height,1920,100,4096,'height'),fps=number(o.fps,30,1,60,'fps'),workers=number(o.workers,2,1,4,'workers');
if(![width,height,fps,workers].every(Number.isInteger)||width%2||height%2)throw Error('Dimensions must be even integers; fps/workers integers');
const out=freshFile(o.out);const {chromium,ffmpeg}=dependencies();const tempRoot=resolve(tmpdir()),dir=mkdtempSync(join(tempRoot,'tcg-frames-'));let browser;
try{
 browser=await chromium.launch(browserOptions());const first=await loadPage(browser,o.input,width,height);const duration=number(first.state.duration,24,.1,300,'duration'),frames=Math.ceil(duration*fps),per=Math.ceil(frames/workers);const pages=[first];
 for(let i=1;i<workers;i++)pages.push(await loadPage(browser,o.input,width,height));
 console.log(`[INFO] ${duration}s / ${frames} frames / ${workers} workers`);
 const outcomes=await Promise.allSettled(pages.map(async({page,errors},k)=>{for(let i=k*per;i<Math.min(frames,(k+1)*per);i++){await seek(page,i/fps);if(errors.length)throw Error(errors.join('\n'));const bad=await page.evaluate(()=>typeof window.__check==='function'?window.__check():[]);if(bad.length)throw Error('Frame '+i+': '+bad.join(', '));await page.screenshot({path:join(dir,String(i).padStart(6,'0')+'.png'),type:'png'});if(i%90===0)console.log('[INFO] frame',i);} }));
 const failed=outcomes.find(x=>x.status==='rejected');if(failed)throw failed.reason;
 mkdirSync(dirname(out),{recursive:true});
 await new Promise((res,rej)=>{const p=spawn(ffmpeg,['-n','-v','error','-framerate',String(fps),'-i',join(dir,'%06d.png'),'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',out],{windowsHide:true,stdio:['ignore','ignore','pipe']});let err='';p.stderr.on('data',x=>err+=x);p.on('error',rej);p.on('close',c=>c===0?res():rej(Error(err||'ffmpeg failed')));});
 console.log('[OK]',out);
}finally{if(browser)await browser.close();const rel=relative(tempRoot,resolve(dir));if(rel&&!rel.startsWith('..')&&!isAbsolute(rel)&&existsSync(dir))rmSync(dir,{recursive:true,force:true,maxRetries:3});}
