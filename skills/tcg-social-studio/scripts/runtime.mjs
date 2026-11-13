// v1: 配布先の依存部品・ブラウザ・出力を扱う共通処理。個人の絶対パスを持たない。
import {createRequire} from 'node:module';
import {existsSync,mkdirSync,readFileSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
export function args(argv){const positional=[],o={};for(let i=0;i<argv.length;i++){if(argv[i].startsWith('--')){const key=argv[i].slice(2);if(!argv[i+1]||argv[i+1].startsWith('--'))throw Error('Missing value: '+key);o[key]=argv[++i]}else positional.push(argv[i]);}return {...o,input:positional[0]};}
export function number(value,fallback,min,max,name){const n=Number(value??fallback);if(!Number.isFinite(n)||n<min||n>max)throw Error('Invalid '+name);return n;}
export function freshFile(p){p=resolve(p);if(existsSync(p))throw Error('Output already exists: '+p);return p;}
export function freshDir(p){p=freshFile(p);mkdirSync(p,{recursive:true});return p;}
export function dependencies(){const require=process.env.TCG_NODE_MODULES?createRequire(join(resolve(process.env.TCG_NODE_MODULES),'resolver.cjs')):createRequire(import.meta.url);const {chromium}=require('playwright-core');const ffmpeg=process.env.FFMPEG_PATH?resolve(process.env.FFMPEG_PATH):require('ffmpeg-static');if(!ffmpeg||!existsSync(ffmpeg))throw Error('ffmpeg missing. Run npm install or set FFMPEG_PATH.');return {chromium,ffmpeg};}
export function browserOptions(){return {headless:true,...(process.env.CHROME_PATH?{executablePath:resolve(process.env.CHROME_PATH)}:{})};}
export async function loadPage(browser,input,width,height){
 const page=await browser.newPage({viewport:{width,height},deviceScaleFactor:1});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route(/^https?:\/\//,route=>route.abort());
 await page.goto(pathToFileURL(resolve(input)).href,{waitUntil:'load',timeout:30000});
 await page.evaluate(()=>document.fonts.ready);await page.waitForFunction(()=>[...document.images].every(im=>im.complete),{},{timeout:30000});
 const state=await page.evaluate(()=>({duration:window.__dur,seek:typeof window.__seek,missing:[...document.images].filter(im=>!im.naturalWidth).map(im=>im.getAttribute('src')),media:document.querySelectorAll('video,audio').length}));
 if(errors.length||state.missing.length||state.seek!=='function'||!Number.isFinite(state.duration)||state.duration<=0)throw Error(JSON.stringify({errors,...state}));
 if(state.media)throw Error('This renderer is for still images + HTML. Use a video editor for video/audio synchronization.');
 return {page,state,errors};
}
export async function seek(page,t){await page.evaluate(t=>window.__seek(t),t);await page.waitForFunction(()=>[...document.images].every(im=>im.complete),{},{timeout:30000});await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));}
export function metadata(text){const d=text.match(/Duration: (\d+):(\d+):([\d.]+)/),v=text.split('\n').find(s=>/Stream.*Video:/.test(s))||'',size=v.match(/\b(\d{2,5})x(\d{2,5})\b/),fps=v.match(/([\d.]+) fps/);if(!d||!size||!fps)throw Error('Could not parse video metadata');return {duration:+d[1]*3600 + +d[2]*60 + +d[3],width:+size[1],height:+size[2],fps:+fps[1],has_audio:/Stream.*Audio:/.test(text)};}
