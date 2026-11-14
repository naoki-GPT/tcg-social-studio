// v1: client.json の点検。足りない必須欄を一覧で出す。1つでも問題があれば終了コード1。
// 使い方: node scripts/check_client.mjs [client.json の場所]
import {existsSync,readFileSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {skillRoot} from './runtime.mjs';

const TEMPLATE_SHEET_ID='19XXnnN8qqeR9QfVx0vm2pTFGMYACJrmC0l2njbYKO2M';
const file=resolve(process.argv[2]||join(skillRoot,'client.json'));
const problems=[];
const bad=(key,what)=>{problems.push(key);console.log(`[ERROR] ${key}: ${what}`);};
const ok=(key,value)=>console.log(`[OK] ${key}: ${value}`);

if(!existsSync(file)){console.log('[ERROR] client.json not found: '+file);process.exit(1);}
let c;
try{c=JSON.parse(readFileSync(file,'utf8').replace(/^﻿/,''));}
catch(e){console.log('[ERROR] client.json is not valid JSON: '+e.message);process.exit(1);}

const text=v=>typeof v==='string'?v.trim():'';
for(const key of ['client_name','shop_name_en','instagram_handle','sheet_url','output_folder','share_folder_url']){
 const v=text(c[key]);
 if(!v)bad(key,'empty. Fill it in (see START_HERE.md and client.example.json).');
 else ok(key,v);
}
const handle=text(c.closing&&c.closing.handle_text);
if(!handle)bad('closing.handle_text','empty. Write the account name shown at the end of every post.');else ok('closing.handle_text',handle);
const type=text(c.contact&&c.contact.type);
if(!['dm','link'].includes(type))bad('contact.type','must be "dm" or "link".');
else if(type==='link'&&!text(c.contact.link_url))bad('contact.link_url','empty, but contact.type is "link".');
else ok('contact.type',type);

const sheet=text(c.sheet_url);
if(sheet&&sheet.includes(TEMPLATE_SHEET_ID))bad('sheet_url','this is the template sheet itself. Open it, choose File > Make a copy, and write the address of the copy.');
else if(sheet&&!/docs\.google\.com\/spreadsheets\/d\/[\w-]{20,}/.test(sheet))bad('sheet_url','does not look like a Google Sheets address.');

const time=v=>/^([01]\d|2[0-3]):[0-5]\d$/.test(text(v));
if(c.create_time!==undefined&&!time(c.create_time))bad('create_time','write as "06:00".');
if(c.post_times!==undefined&&(!Array.isArray(c.post_times)||!c.post_times.length||!c.post_times.every(time)))bad('post_times','write as ["08:00","12:00","21:00"].');
if(c.daily_set!==undefined&&(!Array.isArray(c.daily_set)||!c.daily_set.length))bad('daily_set','write as ["リール","カルーセル","画像"].');

console.log(problems.length?`[ERROR] ${problems.length} item(s) to fix: ${problems.join(', ')}`:'[OK] client.json is ready');
process.exit(problems.length?1:0);
