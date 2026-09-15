#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sestaví šifrovanou statickou stránku „Škola“ pro GitHub Pages.

Čte _data/timetable.json (z fetch_timetable.py), payload ZAŠIFRUJE (AES-GCM, klíč z hesla přes PBKDF2-SHA256) a vygeneruje
stránku, kde se obsah dešifruje AŽ V PROHLÍŽEČI po zadání rodinného hesla.

Prostředí / GitHub Secrets:
    APP_PASSWORD   heslo pro odemčení stránky (stejné jako u Účtů)
"""

import base64
import hashlib
import json
import os
import sys

PBKDF2_ITERS = 200_000
OUT = "public"


def encrypt(payload: dict, password: str):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt = os.urandom(16)
    iv = os.urandom(12)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERS, dklen=32)
    ct = AESGCM(key).encrypt(iv, json.dumps(payload, ensure_ascii=False).encode("utf-8"), None)
    b = lambda x: base64.b64encode(x).decode()
    return b(salt), b(iv), b(ct)


PAGE = r"""<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta http-equiv="refresh" content="1800">
<meta name="theme-color" content="#0c1410">
<title>Škola</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500..700&family=IBM+Plex+Mono:wght@500;600;700&display=swap" rel="stylesheet">
<style>
  :root{--bg:#0c1410; --panel:#121d17; --ink:#eaf1ec; --muted:#7e9588;
    --line:rgba(255,255,255,.09); --green:#4cc99a; --gold:#d8b66b; --red:#ff7a6b;}
  *{box-sizing:border-box;}
  body{margin:0; min-height:100vh; color:var(--ink); background:var(--bg);
    font-family:"IBM Plex Mono",ui-monospace,monospace; padding:0 16px 50px;
    background-image:radial-gradient(120% 55% at 50% -10%, rgba(76,201,154,.12), transparent 60%);
    background-attachment:fixed; display:flex; flex-direction:column; align-items:center;}
  .wrap{width:100%; max-width:560px;}
  header{padding:46px 2px 8px;}
  .kicker{font-size:.7rem; letter-spacing:.3em; text-transform:uppercase; color:var(--muted);}
  h1{font-family:"Fraunces",Georgia,serif; font-weight:600; font-size:clamp(2.2rem,9vw,3rem);
    margin:.12em 0 .1em; letter-spacing:-.02em;}
  h1 .d{color:var(--green);}
  .sub{font-size:.74rem; color:var(--muted);}

  .lock{margin-top:30px; background:var(--panel); border:1px solid var(--line);
    border-radius:18px; padding:26px 22px; text-align:center;}
  .lock .ico{font-size:1.6rem;}
  .lock p{color:var(--muted); font-size:.82rem; margin:10px 0 16px;}
  .lock form{display:flex; gap:8px;}
  .lock input{flex:1; background:var(--bg); border:1px solid var(--line); border-radius:11px;
    color:var(--ink); font-family:inherit; font-size:1rem; padding:12px 14px;}
  .lock input:focus{outline:none; border-color:var(--green);}
  .lock button{background:var(--green); color:#06140d; border:0; border-radius:11px;
    font-family:inherit; font-weight:700; font-size:.95rem; padding:12px 18px; cursor:pointer;}
  .err{color:var(--red); font-size:.78rem; margin-top:10px; min-height:1em;}

  #data{margin-top:24px; display:none;}
  #data.on{display:block;}
  .card{background:var(--panel); border:1px solid var(--line); border-radius:16px;
    padding:18px 20px; margin:12px 0; animation:rise .5s cubic-bezier(.2,.7,.2,1) both;}
  @keyframes rise{from{opacity:0; transform:translateY(10px);} to{opacity:1; transform:none;}}
  .sect{font-size:.7rem; letter-spacing:.25em; text-transform:uppercase; color:var(--muted);
    margin:26px 2px 6px;}

  .when-foot{text-align:center; color:var(--muted); font-size:.72rem; margin-top:18px;}
  .lockbtn{display:block; margin:14px auto 0; background:none; border:1px solid var(--line);
    color:var(--muted); border-radius:999px; padding:7px 16px; font-family:inherit; font-size:.74rem; cursor:pointer;}

  /* rozvrh */
  .pills{display:flex; gap:6px; flex-wrap:wrap; margin:16px 2px 0;}
  .pills button{background:none; border:1px solid var(--line); color:var(--muted); border-radius:999px;
    padding:6px 14px; font-family:inherit; font-size:.75rem; cursor:pointer;}
  .pills button.sel{border-color:var(--green); color:var(--green); background:rgba(76,201,154,.08);}
  .tt .khead{display:flex; justify-content:space-between; align-items:baseline; gap:10px; margin-bottom:12px;}
  .tt .who{font-family:"Fraunces",serif; font-size:1.15rem; font-weight:600;}
  .tt .kmeta{font-size:.68rem; color:var(--muted); text-align:right; line-height:1.4;}
  .tt .dayhead{font-size:.7rem; letter-spacing:.16em; text-transform:uppercase; color:var(--gold);
    margin:16px 0 4px; padding-top:12px; border-top:1px solid var(--line);}
  .tt .dayhead:first-of-type{margin-top:0; padding-top:0; border-top:0;}
  .tt table{width:100%; border-collapse:collapse; font-size:.84rem;}
  .tt td{padding:6px 0; vertical-align:top; border-top:1px solid var(--line);}
  .tt tr:first-child td{border-top:0;}
  .tt .h{width:1.3em; color:var(--muted); font-size:.7rem; padding-right:6px;}
  .tt .t{width:3.5em; color:var(--muted); font-size:.7rem; white-space:nowrap; padding-right:8px;}
  .tt .s{font-weight:600; line-height:1.3;}
  .tt .r{text-align:right; color:var(--muted); font-size:.7rem; white-space:nowrap; padding-left:8px;}
  .tt .note{font-size:.7rem; line-height:1.35; margin-top:3px; color:var(--muted);}
  .tt tr.removed .s{color:var(--red); font-weight:500;}
  .tt tr.removed .subj{text-decoration:line-through;}
  .tt tr.removed .note, .tt tr.removed .r{color:var(--red);}
  .tt tr.sub .s, .tt tr.sub .note{color:var(--gold);}
  .tt tr.added .s, .tt tr.added .note{color:var(--green);}
  .ttnav{display:flex; align-items:center; gap:10px; margin:18px 2px 14px;}
  .ttnav button{flex:0 0 auto; width:38px; height:38px; display:flex; align-items:center;
    justify-content:center; background:var(--panel); border:1px solid var(--line);
    color:var(--muted); border-radius:11px; font:inherit; font-size:.8rem; line-height:1;
    cursor:pointer; transition:color .15s, border-color .15s;}
  .ttnav button:hover{color:var(--green); border-color:var(--green);}
  .ttnav .navlab{flex:1 1 auto; min-width:0; text-align:center; font-size:.92rem;
    font-weight:600; letter-spacing:.01em; color:var(--fg); line-height:1.25;}
  .ttnav .navlab small{display:block; font-size:.66rem; font-weight:400; letter-spacing:.14em;
    text-transform:uppercase; color:var(--muted); margin-top:2px;}
  .ttnav .today-btn{width:auto; padding:0 12px; font-size:.7rem; color:var(--green);
    border-color:rgba(76,201,154,.4);}
  .tt tr.clubrow .subj{color:var(--green);}
  .tt tbody.clubs tr:first-child td{border-top:2px solid var(--line);}

  .tt .gridwrap{overflow-x:auto; -webkit-overflow-scrolling:touch; margin:0 -2px;}
  .tt table.grid{min-width:500px; table-layout:fixed; font-size:.74rem;}
  .tt table.grid th{padding:3px 4px; text-align:left; font-size:.66rem; font-weight:600;
    letter-spacing:.08em; text-transform:uppercase; color:var(--gold);
    border-bottom:1px solid var(--line);}
  .tt table.grid th .thd{display:block; font-size:.6rem; color:var(--muted);
    font-weight:400; letter-spacing:0; text-transform:none;}
  .tt table.grid td{padding:4px; border-top:1px solid var(--line); vertical-align:top;}
  .tt table.grid .tcol{width:4.4em; color:var(--muted); font-size:.62rem; white-space:nowrap;}
  .tt table.grid .tcol b{color:var(--fg); font-weight:600;}
  .tt .cell{font-weight:600; line-height:1.2; display:block;}
  .tt .cellr{display:block; color:var(--muted); font-size:.6rem; font-weight:400; line-height:1.25;}
  .tt .cell.removed{color:var(--red); text-decoration:line-through;}
  .tt .cell.sub{color:var(--gold);}
  .tt .cell.added{color:var(--green);}
  .tt .cell.club{color:var(--green);}
  .tt .today{background:rgba(255,255,255,.045);}
  .tt .empty{color:var(--muted); font-size:.85rem;}
  .tt .warn{color:var(--gold); font-size:.76rem;}

  footer{margin-top:26px; text-align:center; font-size:.68rem; color:var(--muted);}
  footer a{color:var(--green);}
  [hidden]{display:none!important;}
  @media (prefers-reduced-motion:reduce){*{animation:none!important;}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="kicker">Bakaláři · rozvrh a zprávy</div>
    <h1>Škola<span class="d">.</span></h1>
    <div class="sub">Soukromé · chráněno heslem</div>
  </header>

  <div id="lock" class="lock">
    <div class="ico">🔒</div>
    <p>__LOCKMSG__</p>
    <form id="f" __FORMDISABLED__>
      <input id="pw" type="password" inputmode="text" autocomplete="current-password" placeholder="Heslo" autofocus>
      <button type="submit">Odemknout</button>
    </form>
    <div class="err" id="err"></div>
  </div>

  <div id="data"></div>

  <footer><a href="https://dinkotom.github.io/domov-60de93c6/">← Doma</a> · zdroj: Bakaláři · obnova á 30 min</footer>
</div>

<script>
  var ENC = __ENC__;
  var lock=document.getElementById('lock'), dataEl=document.getElementById('data'),
      err=document.getElementById('err'), form=document.getElementById('f'), pwEl=document.getElementById('pw');

  function b64(s){ return Uint8Array.from(atob(s), function(c){return c.charCodeAt(0);}); }
  function esc(s){ return (s||'').replace(/[<>&]/g, function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;'}[c];}); }

  // minimální markdown -> HTML (nadpisy, tučné, odrážky)

  // ---------- rozvrh ----------
  var TT=null, ttView=null, ttDate=null, ttMon=null;
  var DOW=['ne','po','út','st','čt','pá','so'];
  var DOWFULL=['neděle','pondělí','úterý','středa','čtvrtek','pátek','sobota'];

  function daysBetween(a,b){
    return Math.round((new Date(b+'T00:00:00') - new Date(a+'T00:00:00'))/86400000);
  }
  function dayOffLabel(from,to){
    var n=daysBetween(from,to);
    if(n===-1) return 'včera';
    return n>0 ? ('za '+n+' dní') : ('před '+(-n)+' dny');
  }
  function weekOffLabel(from,to){
    var n=Math.round(daysBetween(from,to)/7);
    if(n===1) return 'příští týden';
    if(n===-1) return 'minulý týden';
    return n>0 ? ('za '+n+' týdny') : ('před '+(-n)+' týdny');
  }

  function iso(d){ return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }
  function shift(d,n){ var x=new Date(d.getTime()); x.setDate(x.getDate()+n); return x; }
  function czLabel(d){ return DOW[d.getDay()]+' '+d.getDate()+'.'+(d.getMonth()+1)+'.'; }
  function mondayOf(d){ return shift(d, -(((d.getDay()+6)%7))); }
  function isoDow(d){ return d.getDay()===0 ? 7 : d.getDay(); }
  function mins(t){ var p=String(t||'0:0').split(':'); return (+p[0])*60+(+p[1]); }
  function dayOf(kid, dt){ return (kid.days||[]).filter(function(d){return d.date===dt;})[0]||null; }
  function lastDay(kid){ var ds=kid.days||[]; return ds.length? ds[ds.length-1].date : null; }
  function clubsOn(kid, dow){ return (kid.clubs||[]).filter(function(c){ return c.dow===dow; }); }

  // ---- pohled DEN: řádková tabulka pod sebou ----
  function lessonRows(day){
    return (day.lessons||[]).map(function(l){
      var subj = l.subject || l.abbrev || (l.change_kind==='removed' ? 'odpadá' : '—');
      var notes=[];
      if(l.change) notes.push(l.change);
      if(l.theme) notes.push(l.theme);
      var right=[l.room, l.group].filter(Boolean).join(' · ');
      return '<tr class="'+(l.change_kind||'')+'">'+
        '<td class="h">'+esc(l.hour)+'</td>'+
        '<td class="t">'+esc(l.from)+'</td>'+
        '<td class="s"><span class="subj">'+esc(subj)+'</span>'+
          (notes.length? '<div class="note">'+esc(notes.join(' · '))+'</div>' : '')+'</td>'+
        '<td class="r">'+esc(right)+'</td></tr>';
    }).join('');
  }

  function clubRows(kid, dow){
    return clubsOn(kid, dow).map(function(c){
      var notes=[c.place, c.note].filter(Boolean).join(' · ');
      return '<tr class="clubrow">'+
        '<td class="h">🏃</td>'+
        '<td class="t">'+esc(c.from||'')+'</td>'+
        '<td class="s"><span class="subj">'+esc(c.name||'')+'</span>'+
          (notes? '<div class="note">'+esc(notes)+'</div>' : '')+'</td>'+
        '<td class="r">'+esc(c.to||'')+'</td></tr>';
    }).join('');
  }

  function dayTable(kid, dt){
    var day=dayOf(kid, dt), d=new Date(dt+'T00:00:00');
    var rows = day ? lessonRows(day) : '';
    var cr = clubRows(kid, isoDow(d));
    if(!rows && !cr){
      var stale=lastDay(kid);
      return (stale && dt>stale)
        ? '<div class="warn">⚠ Tak daleko rozvrh ještě není načtený.</div>'
        : '<div class="empty">volno 🎉</div>';
    }
    var head = (day && day.desc) ? '<div class="dayhead">'+esc(day.desc)+'</div>' : '';
    return head+'<table><tbody>'+rows+cr+'</tbody></table>';
  }

  // ---- pohled TÝDEN: klasická mřížka po–pá ----
  function cellHtml(l){
    if(!l) return '';
    var txt = l.abbrev || l.subject || (l.change_kind==='removed' ? 'odpadá' : '');
    if(!txt) return '';
    var sub   = [l.room, l.group].filter(Boolean).join(' ');
    var title = [l.subject, l.teacher, l.room, l.change].filter(Boolean).join(' · ');
    return '<span class="cell '+(l.change_kind||'')+'" title="'+esc(title)+'">'+esc(txt)+'</span>'+
           (sub? '<span class="cellr">'+esc(sub)+'</span>' : '');
  }

  function slotKey(l){ return l.hour ? 'h:'+l.hour : 't:'+(l.from||''); }

  function weekGrid(kid, dates){
    var today=iso(new Date()), slots={}, cl=(kid.clubs||[]);

    // Řádky mřížky = čísla hodin (klasický rozvrh), ne přesné časy — jinak by se
    // blok začínající v jeden den 13:15 a v jiný 13:30 rozpadl na dva řádky.
    dates.forEach(function(dt){
      var day=dayOf(kid, dt); if(!day) return;
      (day.lessons||[]).forEach(function(l){
        if(!l.from && !l.hour) return;
        var k=slotKey(l), sl=slots[k];
        if(!sl) slots[k]={hour:l.hour||'', from:l.from||'', sort:mins(l.from)};
        else if(mins(l.from) < sl.sort){ sl.sort=mins(l.from); sl.from=l.from||sl.from; }
      });
    });
    var keys=Object.keys(slots).sort(function(a,b){ return slots[a].sort-slots[b].sort; });
    if(!keys.length && !cl.length) return '<div class="empty">volno 🎉</div>';

    function th(dt){
      var d=new Date(dt+'T00:00:00');
      return '<th'+(dt===today?' class="today"':'')+'>'+esc(DOW[d.getDay()])+
             '<span class="thd">'+esc(d.getDate()+'.'+(d.getMonth()+1)+'.')+'</span></th>';
    }

    var h='<div class="gridwrap"><table class="grid"><thead><tr><th class="tcol"></th>'+
          dates.map(th).join('')+'</tr></thead><tbody>';

    keys.forEach(function(k){
      var sl=slots[k];
      h+='<tr><td class="tcol">'+(sl.hour? '<b>'+esc(sl.hour)+'</b> ' : '')+esc(sl.from)+'</td>';
      dates.forEach(function(dt){
        var day=dayOf(kid, dt);
        var ls = day ? (day.lessons||[]).filter(function(x){ return slotKey(x)===k; }) : [];
        h+='<td'+(dt===today?' class="today"':'')+'>'+ls.map(cellHtml).join('')+'</td>';
      });
      h+='</tr>';
    });
    h+='</tbody>';

    if(cl.length){
      var times={};
      cl.forEach(function(c){ times[c.from]=1; });
      h+='<tbody class="clubs">';
      Object.keys(times).sort(function(a,b){ return mins(a)-mins(b); }).forEach(function(t){
        h+='<tr><td class="tcol">🏃 '+esc(t)+'</td>';
        dates.forEach(function(dt){
          var dw=isoDow(new Date(dt+'T00:00:00'));
          var c=cl.filter(function(x){ return x.dow===dw && x.from===t; })[0];
          h+='<td'+(dt===today?' class="today"':'')+'>'+
             (c? '<span class="cell club" title="'+esc([c.name,c.place,c.note].filter(Boolean).join(' · '))+'">'+
                 esc((c.name||'').split('–')[0].trim())+'</span>'+
                 (c.place? '<span class="cellr">'+esc(c.place)+'</span>' : '') : '')+'</td>';
        });
        h+='</tr>';
      });
      h+='</tbody>';
    }
    return h+'</table></div>';
  }

  function kidCard(kid, body, extra){
    var meta=[esc(kid.school||''), esc(kid['class']||''), esc(extra||'')].filter(Boolean).join('<br>');
    var h='<div class="card tt"><div class="khead"><span class="who">'+esc(kid.name)+'</span>'+
          '<span class="kmeta">'+meta+'</span></div>';
    if(kid.error){
      h += '<div class="warn">⚠ '+esc(kid.error)+'</div>';
    } else {
      if(kid.fallback) h += '<div class="warn">⚠ '+esc(kid.fallback)+'</div>';
      h += body;
    }
    return h+'</div>';
  }

  function paintTT(){
    var el=document.getElementById('s-tt');
    if(!el) return;
    if(!TT || !(TT.kids||[]).length){
      el.innerHTML='<div class="card"><div class="empty">Rozvrhy se nepodařilo načíst.</div></div>';
      return;
    }
    var h='<div class="pills" id="p-view">'+
      [['den','Den'],['tyden','Týden']].map(function(v){
        return '<button data-v="'+v[0]+'"'+(ttView===v[0]?' class="sel"':'')+'>'+v[1]+'</button>';
      }).join('')+'</div>';

    if(ttView==='tyden'){
      var mon=new Date(ttMon+'T00:00:00');
      var dates=[0,1,2,3,4].map(function(i){ return iso(shift(mon,i)); });
      var curMon=iso(mondayOf(new Date()));
      h+='<div class="ttnav"><button data-step="-7" aria-label="předchozí týden">◀</button>'+
         '<span class="navlab">'+esc(mon.getDate()+'. '+(mon.getMonth()+1)+'. – '+
           shift(mon,4).getDate()+'. '+(shift(mon,4).getMonth()+1)+'.')+
         '<small>'+(ttMon===curMon?'tento týden':weekOffLabel(curMon, ttMon))+'</small></span>'+
         (ttMon===curMon?'':'<button class="today-btn" data-jump="week">dnes</button>')+
         '<button data-step="7" aria-label="další týden">▶</button></div>';
      h+=TT.kids.map(function(k){
           var first=dates.map(function(d){ return dayOf(k,d); }).filter(Boolean)[0];
           return kidCard(k, weekGrid(k,dates), first && first.cycle);
         }).join('');
    } else {
      var d=new Date(ttDate+'T00:00:00'), wknd=(d.getDay()===0||d.getDay()===6);
      var curD=iso(new Date());
      h+='<div class="ttnav"><button data-step="-1" aria-label="předchozí den">◀</button>'+
         '<span class="navlab">'+esc(DOWFULL[d.getDay()]+' '+d.getDate()+'. '+(d.getMonth()+1)+'.')+
         '<small>'+(ttDate===curD?'dnes':(ttDate===iso(shift(new Date(),1))?'zítra':
           dayOffLabel(curD, ttDate)))+(wknd?' · víkend':'')+'</small></span>'+
         (ttDate===curD?'':'<button class="today-btn" data-jump="day">dnes</button>')+
         '<button data-step="1" aria-label="další den">▶</button></div>';
      h+=TT.kids.map(function(k){
           var day=dayOf(k, ttDate);
           return kidCard(k, dayTable(k, ttDate), day && day.cycle);
         }).join('');
    }
    h += '<div class="when-foot">aktualizováno '+esc((TT.ts)||'')+' · živě z Bakalářů (Ota, Eda)</div>';
    el.innerHTML=h;
  }

  function setView(v){ ttView=v; paintTT(); }

  function render(p){
    TT=p.tt||null;

    var h='<section id="s-tt"></section>';
    h += '<button class="lockbtn" onclick="lockNow()">Zamknout</button>';
    dataEl.innerHTML=h; dataEl.classList.add('on'); lock.style.display='none';

    // Po 14:00 rodinu zajímá spíš zítřek — stejná logika jako v ranním briefingu.
    if(!ttView) ttView='den';
    if(!ttDate){ var _n=new Date(); ttDate=iso(_n.getHours()<14 ? _n : shift(_n,1)); }
    if(!ttMon) ttMon=iso(mondayOf(new Date(ttDate+'T00:00:00')));
    paintTT();

    document.getElementById('s-tt').addEventListener('click', function(e){
      var v=e.target.closest('button[data-v]'), st=e.target.closest('button[data-step]');
      if(v){ setView(v.getAttribute('data-v')); return; }
      var jp=e.target.closest('button[data-jump]');
      if(jp){
        var now=new Date();
        ttDate=iso(now); ttMon=iso(mondayOf(now)); paintTT(); return;
      }
      if(st){
        var n=parseInt(st.getAttribute('data-step'),10);
        if(ttView==='tyden') ttMon=iso(shift(new Date(ttMon+'T00:00:00'), n));
        else {
          ttDate=iso(shift(new Date(ttDate+'T00:00:00'), n));
          ttMon=iso(mondayOf(new Date(ttDate+'T00:00:00')));
        }
        paintTT();
      }
    });
  }

  function lockNow(){ try{sessionStorage.removeItem('spw');}catch(e){}; location.reload(); }

  async function decrypt(pw){
    var salt=b64(ENC.salt), iv=b64(ENC.iv), ct=b64(ENC.ct);
    var km=await crypto.subtle.importKey('raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveKey']);
    var key=await crypto.subtle.deriveKey({name:'PBKDF2', salt:salt, iterations:ENC.iter, hash:'SHA-256'},
              km, {name:'AES-GCM', length:256}, false, ['decrypt']);
    var pt=await crypto.subtle.decrypt({name:'AES-GCM', iv:iv}, key, ct);
    return JSON.parse(new TextDecoder().decode(pt));
  }
  async function unlock(pw, silent){
    try{ var p=await decrypt(pw); try{sessionStorage.setItem('spw', pw);}catch(e){}; render(p); }
    catch(e){ if(!silent){ err.textContent='Špatné heslo.'; pwEl.value=''; pwEl.focus(); } }
  }
  if(ENC && form){
    form.addEventListener('submit', function(e){ e.preventDefault(); err.textContent=''; unlock(pwEl.value, false); });
    var saved=null; try{ saved=sessionStorage.getItem('spw'); }catch(e){}
    if(saved) unlock(saved, true);
  }
</script>
</body>
</html>
"""


def build_page(enc, configured):
    if configured and enc:
        salt, iv, ct = enc
        enc_js = json.dumps({"salt": salt, "iv": iv, "ct": ct, "iter": PBKDF2_ITERS})
        lockmsg = "Zadej rodinné heslo pro zobrazení školních zpráv."
        formdis = ""
    else:
        enc_js = "null"
        lockmsg = "Stránka zatím není nakonfigurovaná (chybí secrets)."
        formdis = "style=\"display:none\""
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(PAGE.replace("__ENC__", enc_js)
                    .replace("__LOCKMSG__", lockmsg)
                    .replace("__FORMDISABLED__", formdis))


def main():
    password = os.getenv("APP_PASSWORD")
    if not password:
        print("VAROVÁNÍ: chybí APP_PASSWORD – stavím nenakonfigurovanou stránku.", file=sys.stderr)
        build_page(None, configured=False)
        return

    try:
        with open("_data/timetable.json", encoding="utf-8") as f:
            tt = json.load(f)
    except FileNotFoundError:
        sys.exit("Chybí _data/timetable.json (spusť nejdřív fetch_timetable.py).")

    payload = {"ts": tt.get("ts"), "tt": tt}
    enc = encrypt(payload, password)
    build_page(enc, configured=True)
    n_kids = len(tt.get("kids") or [])
    print(f"Hotovo: rozvrhy {n_kids} dětí, zašifrováno.", file=sys.stderr)


if __name__ == "__main__":
    main()
