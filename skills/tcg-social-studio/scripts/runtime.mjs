// v1: 配布先の依存部品・ブラウザ・出力を扱う共通処理。個人の絶対パスを持たない。
import {createRequire} from 'node:module';
import {existsSync,mkdirSync,readFileSync,readdirSync} from 'node:fs';
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

// ---- v4: どのPCでも動かすための共通処理（ここから下を新しい道具が使う） ----
import {spawnSync} from 'node:child_process';
import {dirname} from 'node:path';
import {fileURLToPath} from 'node:url';

export const skillRoot=resolve(dirname(fileURLToPath(import.meta.url)),'..');

function requireFrom(){return process.env.TCG_NODE_MODULES?createRequire(join(resolve(process.env.TCG_NODE_MODULES),'resolver.cjs')):createRequire(import.meta.url);}

/** 値つきの引数と、値なしの旗（flags に列挙）を読む。未知の引数はエラー。 */
export function parseArgs(argv,{values=[],flags=[]}={}){
 const o={_:[]};
 for(let i=0;i<argv.length;i++){
  const a=argv[i];
  if(!a.startsWith('--')){o._.push(a);continue;}
  const key=a.slice(2);
  if(flags.includes(key)){o[key]=true;continue;}
  if(!values.includes(key))throw Error('Unknown option: '+a);
  if(argv[i+1]===undefined||argv[i+1].startsWith('--'))throw Error('Missing value: '+a);
  o[key]=argv[++i];
 }
 return o;
}

export function fail(message,extra){
 console.error('[ERROR] '+message);
 if(extra!==undefined)console.error(typeof extra==='string'?extra:JSON.stringify(extra,null,2));
 process.exit(1);
}

/** playwright-core の chromium を返す。無ければ分かる文でエラー。 */
export function loadChromium(){
 try{return requireFrom()('playwright-core').chromium;}
 catch(e){throw Error('playwright-core is not installed. Run "npm install" in the skill folder (or set TCG_NODE_MODULES). '+e.message);}
}

/** スキルのフォルダの .browsers/ に入れた試験用Chrome（npm run browser で入る）の実行ファイルを探す。無ければ ''。 */
export function findLocalChrome(){
 const names=new Set(['chrome.exe','chrome','Google Chrome for Testing']);
 const walk=(dir,depth)=>{
  if(depth>7)return '';
  let entries=[];try{entries=readdirSync(dir,{withFileTypes:true});}catch{return '';}
  for(const e of entries)if(!e.isDirectory()&&names.has(e.name))return join(dir,e.name);
  for(const e of entries)if(e.isDirectory()){const hit=walk(join(dir,e.name),depth+1);if(hit)return hit;}
  return '';
 };
 return walk(join(skillRoot,'.browsers'),0);
}

/**
 * ブラウザを順に試し、最初に起動できたものを返す。
 * 順番: CHROME_PATH → スキル内 .browsers/ の試験用Chrome → playwright 同梱 chromium（実体があれば）→ channel:'chrome' → channel:'msedge'
 * 戻り値: {browser, used, tried}  used は 'CHROME_PATH' | 'playwright-chromium' | 'chrome' | 'msedge'
 */
export async function launchBrowser(){
 const chromium=loadChromium();const candidates=[];const tried=[];
 if(process.env.CHROME_PATH){
  const p=resolve(process.env.CHROME_PATH);
  if(existsSync(p))candidates.push({used:'CHROME_PATH',options:{executablePath:p}});
  else tried.push({used:'CHROME_PATH',ok:false,reason:'file not found'});
 }
 const local=findLocalChrome();
 if(local)candidates.push({used:'skill .browsers',options:{executablePath:local}});
 let bundled='';try{bundled=chromium.executablePath();}catch{bundled='';}
 if(bundled&&existsSync(bundled))candidates.push({used:'playwright-chromium',options:{}});
 else tried.push({used:'playwright-chromium',ok:false,reason:'not installed'});
 candidates.push({used:'chrome',options:{channel:'chrome'}},{used:'msedge',options:{channel:'msedge'}});
 for(const c of candidates){
  try{
   const browser=await chromium.launch({headless:true,...c.options});
   tried.push({used:c.used,ok:true});
   return {browser,used:c.used,version:browser.version(),tried};
  }catch(e){tried.push({used:c.used,ok:false,reason:/is not found|doesn't exist|ENOENT/i.test(String(e.message||e))?'not installed':String(e.message||e).split('\n')[0].slice(0,200)});}
 }
 const err=Error('No browser could be started. Run "npm run browser" in the skill folder (downloads a test Chrome into .browsers/), or install Google Chrome or Microsoft Edge, or set CHROME_PATH to a Chromium-based browser executable.');
 err.tried=tried;throw err;
}

function runs(bin){try{const r=spawnSync(bin,['-version'],{encoding:'utf8',windowsHide:true});return r.status===0&&/ffmpeg version/.test(r.stdout||'');}catch{return false;}}

/**
 * ffmpeg を順に探し、実際に実行できた最初のものを返す。
 * 順番: FFMPEG_PATH → ffmpeg-static（スキル内 node_modules）→ PATH 上の ffmpeg
 * 戻り値: {path, used}
 */
export function findFfmpeg(){
 const tried=[];
 if(process.env.FFMPEG_PATH){const p=resolve(process.env.FFMPEG_PATH);if(existsSync(p)&&runs(p))return {path:p,used:'FFMPEG_PATH'};tried.push('FFMPEG_PATH');}
 try{const p=requireFrom()('ffmpeg-static');if(p&&existsSync(p)&&runs(p))return {path:p,used:'ffmpeg-static'};}catch{}
 tried.push('ffmpeg-static');
 if(runs('ffmpeg'))return {path:'ffmpeg',used:'PATH'};
 tried.push('PATH');
 throw Error('ffmpeg was not found (tried: '+tried.join(', ')+'). Run "npm install" in the skill folder, or set FFMPEG_PATH.');
}

/** ffmpeg を実行して {status, stdout, stderr} を返す。 */
export function runFfmpeg(ffmpegPath,argv){
 const r=spawnSync(ffmpegPath,argv,{encoding:'utf8',windowsHide:true,maxBuffer:64*1024*1024});
 return {status:r.status,stdout:r.stdout||'',stderr:r.stderr||'',error:r.error};
}

/**
 * ローカルのHTMLを開く。外部通信（file: / data: / blob: 以外）は遮断する。
 * 戻り値: {page, problems}  problems.pageErrors / failedRequests / blocked は開いた後も増える。
 */
export async function openLocalPage(browser,input,width,height){
 const file=resolve(input);
 if(!existsSync(file))throw Error('HTML not found: '+file);
 const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:1});
 const page=await context.newPage();
 const problems={pageErrors:[],failedRequests:[],blocked:[]};
 page.on('pageerror',e=>problems.pageErrors.push(String(e.message||e)));
 await context.route('**/*',route=>{
  const url=route.request().url();
  if(/^(file|data|blob|about):/i.test(url))return route.continue();
  problems.blocked.push(url);return route.abort();
 });
 page.on('requestfailed',req=>{const url=req.url();if(/^file:/i.test(url))problems.failedRequests.push(decodeURIComponent(url));});
 await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:30000});
 return {page,problems};
}

/**
 * 画像と書体の確認。@font-face で宣言された書体をすべて読み込み、document.fonts.check で当たりを確かめる。
 * 戻り値: {missingImages:[src], fonts:[{family,weight,style,status,ok}], badFonts:[...]}
 */
export async function inspectAssets(page){
 await page.waitForFunction(()=>[...document.images].every(im=>im.complete),{},{timeout:30000});
 return await page.evaluate(async()=>{
  const faces=[...document.fonts];
  await Promise.all(faces.map(f=>f.load().catch(()=>null)));
  await document.fonts.ready;
  const fonts=faces.map(f=>{
   const family=f.family.replace(/^["']|["']$/g,'');
   const weight=String(f.weight).split(' ')[0];
   const ok=f.status==='loaded'&&document.fonts.check(`${f.style} ${weight} 32px "${family}"`);
   return {family,weight:f.weight,style:f.style,status:f.status,ok};
  });
  const missingImages=[...document.images].filter(im=>!im.naturalWidth).map(im=>im.getAttribute('src'));
  return {missingImages,fonts,badFonts:fonts.filter(f=>!f.ok)};
 });
}

export function metadata(text){const d=text.match(/Duration: (\d+):(\d+):([\d.]+)/),v=text.split('\n').find(s=>/Stream.*Video:/.test(s))||'',size=v.match(/\b(\d{2,5})x(\d{2,5})\b/),fps=v.match(/([\d.]+) fps/);if(!d||!size||!fps)throw Error('Could not parse video metadata');return {duration:+d[1]*3600 + +d[2]*60 + +d[3],width:+size[1],height:+size[2],fps:+fps[1],has_audio:/Stream.*Audio:/.test(text)};}
