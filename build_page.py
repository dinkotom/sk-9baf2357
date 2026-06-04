#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sestaví šifrovanou statickou stránku „Škola“ pro GitHub Pages.

Čte _data/items.json (z fetch_messages.py) a _data/digest.md (z `claude -p`),
payload ZAŠIFRUJE (AES-GCM, klíč z hesla přes PBKDF2-SHA256) a vygeneruje
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
<title>Škola – Eda</title>
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
  .digest{font-size:.92rem; line-height:1.5;}
  .digest h2{font-family:"Fraunces",serif; font-size:1.1rem; margin:.4em 0 .2em;}
  .digest strong{color:var(--green);}
  .digest ul{margin:.4em 0; padding-left:1.1em;}
  .digest li{margin:.3em 0;}

  .msg{position:relative;}
  .msg .top{display:flex; justify-content:space-between; gap:10px; align-items:baseline;}
  .msg .ttl{font-family:"Fraunces",serif; font-size:1.05rem; font-weight:600;}
  .msg .when{font-size:.7rem; color:var(--muted); white-space:nowrap;}
  .msg .from{font-size:.74rem; color:var(--muted); margin-top:2px;}
  .msg .body{font-size:.85rem; line-height:1.45; margin-top:8px; white-space:pre-wrap;}
  .msg .att{font-size:.72rem; color:var(--gold); margin-top:8px;}
  .badge{display:inline-block; background:var(--green); color:#06140d; font-size:.6rem;
    font-weight:700; letter-spacing:.08em; padding:2px 7px; border-radius:999px; vertical-align:middle; margin-left:8px;}
  .unread{border-color:rgba(76,201,154,.45); box-shadow:0 0 0 1px rgba(76,201,154,.18);}
  .msg .chk{display:inline-flex; align-items:center; gap:6px; margin-top:12px;
    font-size:.72rem; color:var(--muted); cursor:pointer; user-select:none;}
  .msg .chk input{accent-color:var(--green); width:15px; height:15px; cursor:pointer;}
  .msg.done{opacity:.5;}
  .toolbar{display:flex; justify-content:flex-end; margin:8px 2px 0;}
  .toolbar button{background:none; border:1px solid var(--line); color:var(--muted);
    border-radius:999px; padding:5px 13px; font-family:inherit; font-size:.72rem; cursor:pointer;}

  .when-foot{text-align:center; color:var(--muted); font-size:.72rem; margin-top:18px;}
  .lockbtn{display:block; margin:14px auto 0; background:none; border:1px solid var(--line);
    color:var(--muted); border-radius:999px; padding:7px 16px; font-family:inherit; font-size:.74rem; cursor:pointer;}
  footer{margin-top:26px; text-align:center; font-size:.68rem; color:var(--muted);}
  footer a{color:var(--green);}
  @media (prefers-reduced-motion:reduce){*{animation:none!important;}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="kicker">Bakaláři · digest</div>
    <h1>Škola <span class="d">– Eda</span></h1>
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
  function md(src){
    var lines=(src||'').split('\n'), out=[], inUl=false;
    function closeUl(){ if(inUl){ out.push('</ul>'); inUl=false; } }
    for(var i=0;i<lines.length;i++){
      var l=lines[i];
      var inline=function(t){ return esc(t)
        .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
        .replace(/`(.+?)`/g,'<code>$1</code>'); };
      var h=l.match(/^(#{1,3})\s+(.*)$/);
      var li=l.match(/^\s*[-*]\s+(.*)$/);
      if(h){ closeUl(); out.push('<h2>'+inline(h[2])+'</h2>'); }
      else if(li){ if(!inUl){ out.push('<ul>'); inUl=true; } out.push('<li>'+inline(li[1])+'</li>'); }
      else if(l.trim()===''){ closeUl(); }
      else { closeUl(); out.push('<p>'+inline(l)+'</p>'); }
    }
    closeUl();
    return out.join('');
  }

  var API=null, dismissed=new Set(), showDone=false, PAYLOAD=null;
  function isDone(m){ return dismissed.has(String(m.id)); }

  function msgCard(m){
    var done=isDone(m);
    var badge = m.read ? '' : '<span class="badge">nové</span>';
    var att = (m.attachments && m.attachments.length)
      ? '<div class="att">📎 '+m.attachments.map(esc).join(', ')+'</div>' : '';
    var chk = API ? '<label class="chk"><input type="checkbox" class="chk" data-id="'+
      esc(String(m.id))+'"'+(done?' checked':'')+'> vyřízeno</label>' : '';
    return '<div class="card msg '+(m.read?'':'unread')+(done?' done':'')+'">'+
      '<div class="top"><span class="ttl">'+esc(m.title||'(bez předmětu)')+badge+'</span>'+
      '<span class="when">'+esc(m.sent_label||'')+'</span></div>'+
      '<div class="from">'+esc(m.sender||'')+'</div>'+
      (m.text ? '<div class="body">'+esc(m.text)+'</div>' : '')+ att + chk +'</div>';
  }

  function paintList(){
    var p=PAYLOAD;
    var recv=(p.received||[]).filter(function(m){return showDone||!isDone(m);});
    var notice=(p.noticeboard||[]).filter(function(m){return showDone||!isDone(m);});
    var doneCount=(p.received||[]).concat(p.noticeboard||[]).filter(isDone).length;
    var h='';
    if(recv.length){
      var nNew=recv.filter(function(m){return !m.read && !isDone(m);}).length;
      h += '<div class="sect">Zprávy ('+recv.length+(nNew?(', '+nNew+' nových'):'')+')</div>';
      h += recv.map(msgCard).join('');
    }
    if(notice.length){ h += '<div class="sect">Nástěnka</div>'+notice.map(msgCard).join(''); }
    if(!recv.length && !notice.length){
      h += '<div class="card" style="text-align:center;color:var(--muted)">Vše vyřízeno 🎉</div>';
    }
    document.getElementById('list').innerHTML=h;
    var tb=document.getElementById('done-toggle');
    if(API && doneCount){ tb.style.display=''; tb.textContent=showDone?'Skrýt vyřízené':('Zobrazit vyřízené ('+doneCount+')'); }
    else { tb.style.display='none'; }
  }

  function render(p){
    PAYLOAD=p; API=p.api||null;
    var h='';
    if(p.digest){ h += '<div class="card digest">'+md(p.digest)+'</div>'; }
    h += '<div class="toolbar"><button id="done-toggle" style="display:none"></button></div>';
    h += '<div id="list"></div>';
    h += '<div class="when-foot">žák: '+esc(p.student||'')+' · aktualizováno '+esc(p.ts||'')+'</div>';
    h += '<button class="lockbtn" onclick="lockNow()">Zamknout</button>';
    dataEl.innerHTML=h; dataEl.classList.add('on'); lock.style.display='none';
    document.getElementById('done-toggle').addEventListener('click', function(){ showDone=!showDone; paintList(); });
    dataEl.addEventListener('change', function(e){
      var t=e.target;
      if(t && t.matches && t.matches('input.chk')){ toggleDone(t.getAttribute('data-id'), t.checked); }
    });
    paintList();
    refreshState();
  }

  function authHeaders(){ return {'Authorization':'Bearer '+API.secret, 'Content-Type':'application/json'}; }
  async function refreshState(){
    if(!API) return;
    try{
      var r=await fetch(API.url+'/state', {headers:authHeaders()});
      if(r.ok){ var j=await r.json(); dismissed=new Set((j.dismissed||[]).map(String)); paintList(); }
    }catch(e){}
  }
  async function toggleDone(id, val){
    if(!API) return;
    if(val) dismissed.add(String(id)); else dismissed.delete(String(id));
    paintList();
    try{ await fetch(API.url+'/dismiss', {method:'POST', headers:authHeaders(),
      body:JSON.stringify({id:String(id), dismissed:val})}); }catch(e){}
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
        with open("_data/items.json", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit("Chybí _data/items.json (spusť nejdřív fetch_messages.py).")

    digest = ""
    try:
        with open("_data/digest.md", encoding="utf-8") as f:
            digest = f.read().strip()
    except FileNotFoundError:
        print("VAROVÁNÍ: chybí _data/digest.md – stránka bude bez AI shrnutí.", file=sys.stderr)

    payload = {
        "ts": data.get("ts"),
        "student": data.get("student"),
        "unread_count": data.get("unread_count", 0),
        "digest": digest,
        "received": data.get("received", []),
        "noticeboard": data.get("noticeboard", []),
    }
    # Konfigurace stavového backendu jde DOVNITŘ šifrovaného payloadu —
    # tajemství je tak dostupné až po odemčení rodinným heslem, nikdy v cleartextu.
    api_url = os.getenv("STATE_API_URL")
    api_secret = os.getenv("STATE_API_SECRET")
    if api_url and api_secret:
        payload["api"] = {"url": api_url.rstrip("/"), "secret": api_secret}

    enc = encrypt(payload, password)
    build_page(enc, configured=True)
    print(f"Hotovo: {len(payload['received'])} zpráv, digest {'ano' if digest else 'ne'}, zašifrováno.",
          file=sys.stderr)


if __name__ == "__main__":
    main()
