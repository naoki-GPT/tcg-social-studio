// v4: 初回確認。このPCで道具が動くかを1行ずつ表示し、最後にJSONも出す。1つでも欠けたら終了コード1。
// 使い方: node scripts/check_env.mjs [--json <書き出し先.json>]
import {existsSync,readFileSync,writeFileSync,statSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {join} from 'node:path';
import {skillRoot,launchBrowser,findFfmpeg,parseArgs} from './runtime.mjs';

const results=[];
const add=(name,ok,detail,fix)=>{results.push({name,ok,detail,...(ok||!fix?{}:{fix})});console.log(`${ok?'[OK]':'[ERROR]'} ${name}: ${detail}${ok||!fix?'':' -> '+fix}`);};
const info=(name,detail)=>{results.push({name,ok:null,detail});console.log(`[INFO] ${name}: ${detail}`);};

let jsonOut=null;
try{jsonOut=parseArgs(process.argv.slice(2),{values:['json']}).json||null;}catch(e){console.error('[ERROR] '+e.message);process.exit(1);}

// 1. node
const major=Number(process.versions.node.split('.')[0]);
add('node',major>=22,'v'+process.versions.node,'Install Node.js 22 or newer.');

// 2. browser（実際に起動してページを1枚開き、閉じる）
try{
 const {browser,used,version,tried}=await launchBrowser();
 const page=await browser.newPage();await page.setContent('<p>ok</p>');await browser.close();
 add('browser',true,`${used} ${version}`);
 const skipped=tried.filter(t=>!t.ok).map(t=>`${t.used} (${t.reason})`);
 if(skipped.length)info('browser tried first',skipped.join(', '));
}catch(e){
 add('browser',false,e.message.split('. ')[0],'Run "npm run browser" in the skill folder (downloads a test Chrome into .browsers/). Or install Google Chrome or Microsoft Edge, or set CHROME_PATH.');
 if(e.tried)info('browser tried',e.tried.map(t=>`${t.used} (${t.reason||'ok'})`).join(', '));
}

// 3. ffmpeg
try{const ff=findFfmpeg();add('ffmpeg',true,ff.used);}
catch(e){add('ffmpeg',false,'not found','Run "npm install" in the skill folder, or set FFMPEG_PATH.');}

// 4. python と Pillow
let python=null;
// スキル内の専用環境（.venv）があれば、それを先に使う
const venvPy=[join(skillRoot,'.venv','Scripts','python.exe'),join(skillRoot,'.venv','bin','python')].find(p=>existsSync(p));
for(const [cmd,pre] of [...(venvPy?[[venvPy,[]]]:[]),['python',[]],['py',['-3']],['python3',[]]]){
 try{
  const r=spawnSync(cmd,[...pre,'-c','import sys;print("%d.%d.%d"%sys.version_info[:3])'],{encoding:'utf8',windowsHide:true});
  if(r.status===0&&/^\d+\.\d+\.\d+/.test((r.stdout||'').trim())){python={cmd,pre,version:r.stdout.trim()};break;}
 }catch{}
}
if(python){
 const [maj,min]=python.version.split('.').map(Number);
 const label=[python.cmd,...python.pre].join(' ');
 add('python',maj===3&&min>=9,`${python.version} (command: ${label})`,'Install Python 3.9 or newer.');
 const mod=name=>{const r=spawnSync(python.cmd,[...python.pre,'-c',`import ${name} as m;print(m.__version__)`],{encoding:'utf8',windowsHide:true});return r.status===0?(r.stdout||'').trim():null;};
 const pil=mod('PIL');
 add('pillow',Boolean(pil),pil||'not installed',`Run: ${label} -m pip install -r requirements.txt  (if pip answers "externally-managed-environment", make a private environment first: ${label} -m venv .venv , then use the python inside .venv. See START_HERE.md section 2.)`);
 const cv=mod('cv2'),np=mod('numpy');
 info('analysis libraries (optional)',cv&&np?`opencv ${cv}, numpy ${np}`:`not installed. Needed only for analyze_reference_video.py: ${label} -m pip install -r requirements-analysis.txt`);
}else{
 add('python',false,'not found','Install Python 3.9 or newer and make "python" (or "py -3") runnable.');
 add('pillow',false,'python not found','Install Python first.');
}

// 5. 同梱の書体
for(const f of ['Anton-Regular.ttf','ShipporiMincho-Bold.ttf']){
 const p=join(skillRoot,'fonts',f);
 const ok=existsSync(p)&&statSync(p).size>1000;
 add('font '+f,ok,ok?'found':'missing','Restore the "fonts" folder from the distributed skill.');
}

// 6. 効果音
try{
 const manifest=JSON.parse(readFileSync(join(skillRoot,'se-pack','manifest.json'),'utf8'));
 const names=[...new Set(manifest.items.map(i=>i.file))];
 const missing=names.filter(n=>{const p=join(skillRoot,'se-pack',n);return !existsSync(p)||statSync(p).size===0;});
 add('se-pack',missing.length===0,missing.length?`${missing.length} of ${names.length} file(s) missing: ${missing.join(', ')}`:`${names.length} file(s)`,'Restore the "se-pack" folder from the distributed skill.');
}catch(e){add('se-pack',false,'manifest.json could not be read','Restore the "se-pack" folder from the distributed skill.');}

const ok=results.every(r=>r.ok!==false);
const report={ok,platform:process.platform,checked_at:new Date().toISOString(),results};
if(jsonOut)writeFileSync(jsonOut,JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
console.log(ok?'[OK] all checks passed':'[ERROR] some checks failed. Fix the lines marked [ERROR] and run this again.');
process.exit(ok?0:1);
