// v4: 連番画像と音を1本のMP4にし、できた実ファイルを調べる。
// 使い方: node scripts/finish_video.mjs --frames <連番フォルダ> --audio <audio.wav> --out <新規.mp4> [--fps 30 --checks <新規フォルダ> --times 0.5,3.2 --silent]
// 出力: MP4 (H.264 / yuv420p / AAC / +faststart)、checks/video.json、checks/frame-01.png ...
import {existsSync,readdirSync,readFileSync,writeFileSync,statSync,mkdirSync} from 'node:fs';
import {join,dirname,resolve,basename} from 'node:path';
import {parseArgs,number,freshFile,findFfmpeg,runFfmpeg,fail} from './runtime.mjs';

const USAGE='usage: node scripts/finish_video.mjs --frames <frames dir> --audio <audio.wav> --out <new.mp4> [--fps 30 --checks <new dir> --times 0.5,3.2,... --silent]';
try{
 const a=parseArgs(process.argv.slice(2),{values:['frames','audio','out','fps','checks','times'],flags:['silent']});
 if(a._.length||!a.frames||!a.out)throw Error(USAGE);
 if(!a.audio&&!a.silent)throw Error('--audio is required. Add --silent only when a video without sound is really intended.');
 const framesDir=resolve(a.frames);
 if(!existsSync(framesDir)||!statSync(framesDir).isDirectory())throw Error('frames folder not found: '+framesDir);
 if(!/\.mp4$/i.test(a.out))throw Error('--out must end with .mp4');
 const audio=a.audio?resolve(a.audio):null;
 if(audio&&!existsSync(audio))throw Error('audio file not found: '+audio);

 // 連番の確認（接頭辞・桁数・拡張子が1種類で、番号に抜けが無いこと）
 const found=readdirSync(framesDir).map(n=>n.match(/^(.*?)(\d+)\.(jpg|jpeg|png)$/i)).filter(Boolean);
 if(!found.length)throw Error('no numbered images (jpg/png) in: '+framesDir);
 const kinds=new Set(found.map(m=>`${m[1]}|${m[2].length}|${m[3].toLowerCase()}`));
 if(kinds.size!==1)throw Error('the frames folder mixes several file name patterns: '+[...kinds].join(' , '));
 const [prefix,digits,ext]=[...kinds][0].split('|');
 const nums=found.map(m=>Number(m[2])).sort((x,y)=>x-y);
 const start=nums[0];
 for(let i=0;i<nums.length;i++)if(nums[i]!==start+i)throw Error(`frame numbers are not continuous (missing ${start+i})`);
 const pattern=join(framesDir,`${prefix.replace(/%/g,'%%')}%0${digits}d.${ext}`);

 let info={};
 const infoPath=join(framesDir,'frames.json');
 if(existsSync(infoPath)){try{info=JSON.parse(readFileSync(infoPath,'utf8'));}catch{info={};}}
 const fps=number(a.fps,info.fps??30,1,60,'--fps');
 if(a.fps!==undefined&&info.fps&&Number(a.fps)!==info.fps)console.log(`[INFO] --fps ${a.fps} differs from the capture fps ${info.fps}. The video speed will change.`);
 const expectedDuration=nums.length/fps;

 const out=freshFile(a.out);
 const checks=resolve(a.checks||join(dirname(out),'checks'));
 if(existsSync(checks))throw Error('Output already exists: '+checks+' (pass a new folder with --checks)');
 let times;
 if(a.times){
  times=a.times.split(',').map(s=>Number(s.trim()));
  if(!times.length||times.some(t=>!Number.isFinite(t)||t<0||t>=expectedDuration))throw Error(`Invalid --times (each value must be 0 <= t < ${expectedDuration.toFixed(2)})`);
 }else times=Array.from({length:7},(_,i)=>Math.round(((i+0.5)/7)*expectedDuration*1000)/1000);

 const ff=findFfmpeg();
 console.log('[INFO] ffmpeg: '+ff.used);
 mkdirSync(dirname(out),{recursive:true});
 const argv=['-hide_banner','-v','error','-n','-framerate',String(fps),'-start_number',String(start),'-i',pattern];
 if(audio)argv.push('-i',audio);
 argv.push('-map','0:v:0');
 if(audio)argv.push('-map','1:a:0','-af','apad,aformat=channel_layouts=mono,pan=stereo|c0=c0|c1=c0','-c:a','aac','-b:a','192k','-ar','48000');
 argv.push('-vf','scale=out_color_matrix=bt709:out_range=tv,format=yuv420p','-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p',
  '-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-color_range','tv','-r',String(fps),'-t',expectedDuration.toFixed(6),'-movflags','+faststart',out);
 const enc=runFfmpeg(ff.path,argv);
 if(enc.status!==0||!existsSync(out))fail('ffmpeg could not create the MP4',(enc.stderr||String(enc.error||'')).slice(-2000));

 // ---- 実ファイルの検査 ----
 const probe=runFfmpeg(ff.path,['-hide_banner','-i',out]).stderr;
 const d=probe.match(/Duration: (\d+):(\d+):([\d.]+)/);
 const v=probe.split('\n').find(s=>/Stream.*Video:/.test(s))||'';
 const au=probe.split('\n').find(s=>/Stream.*Audio:/.test(s))||'';
 const size=v.match(/\b(\d{2,5})x(\d{2,5})\b/),rate=v.match(/([\d.]+) fps/);
 if(!d||!size||!rate)fail('could not read the created MP4',probe.slice(-1500));
 const video={
  file:basename(out),size_bytes:statSync(out).size,
  width:+size[1],height:+size[2],fps:+rate[1],duration:+d[1]*3600 + +d[2]*60 + +d[3],
  video_codec:(v.match(/Video: (\w+)/)||[])[1]||null,pix_fmt:(v.match(/\b(yuvj?4\d\dp\w*)/)||[])[1]||null,
  has_audio:Boolean(au),audio_codec:(au.match(/Audio: (\w+)/)||[])[1]||null,audio_max_volume_db:null,
  source_frames:nums.length,expected_duration:Math.round(expectedDuration*1000)/1000,silent_requested:Boolean(a.silent),
  check_frames:[],problems:[],
 };
 if(video.has_audio){
  const vol=runFfmpeg(ff.path,['-hide_banner','-i',out,'-vn','-af','volumedetect','-f','null','-']).stderr.match(/max_volume: (-?[\d.]+|-inf) dB/);
  if(vol)video.audio_max_volume_db=vol[1]==='-inf'?null:Number(vol[1]);
  if(!vol||vol[1]==='-inf'||Number(vol[1])<-50)video.problems.push('the audio track is (almost) silent');
 }else if(!a.silent)video.problems.push('no audio track in the MP4');
 if(info.width&&(info.width!==video.width||info.height!==video.height))video.problems.push(`size ${video.width}x${video.height} differs from the captured ${info.width}x${info.height}`);
 if(Math.abs(video.fps-fps)>0.01)video.problems.push(`fps ${video.fps} differs from ${fps}`);
 if(Math.abs(video.duration-expectedDuration)>0.1)video.problems.push(`duration ${video.duration}s differs from the expected ${expectedDuration.toFixed(2)}s`);
 if(video.video_codec!=='h264')video.problems.push('video codec is not h264');
 if(video.pix_fmt!=='yuv420p')video.problems.push('pixel format is not yuv420p');

 mkdirSync(checks,{recursive:true});
 times.forEach((t,i)=>{
  const name=`frame-${String(i+1).padStart(2,'0')}.png`;
  const r=runFfmpeg(ff.path,['-hide_banner','-v','error','-n','-ss',t.toFixed(3),'-i',out,'-frames:v','1',join(checks,name)]);
  if(r.status!==0||!existsSync(join(checks,name)))video.problems.push(`could not extract a frame at ${t}s`);
  else video.check_frames.push({file:name,t});
 });
 writeFileSync(join(checks,'video.json'),JSON.stringify(video,null,2));
 console.log(`[INFO] ${video.width}x${video.height} ${video.fps}fps ${video.duration.toFixed(2)}s video=${video.video_codec}/${video.pix_fmt} audio=${video.has_audio?video.audio_codec+' (max '+video.audio_max_volume_db+' dB)':'none'}`);
 console.log(`[INFO] checks: ${join(checks,'video.json')} + ${video.check_frames.length} frame(s). Open the frames and look at them before saying the video is done.`);
 if(video.problems.length)fail('the MP4 was created but did not pass the checks: '+out,video.problems);
 console.log('[OK] '+out);
}catch(e){fail(e.message);}
