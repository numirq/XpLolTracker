export function adminPageResponse() {
  return new Response(ADMIN_HTML, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
      "x-content-type-options": "nosniff",
      "x-frame-options": "DENY",
      "referrer-policy": "no-referrer",
      "permissions-policy": "camera=(), microphone=(), geolocation=()"
    }
  });
}

const ADMIN_HTML = String.raw`<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>LoL XP Tracker — dostęp znajomych</title>
  <style>
    :root{color-scheme:dark;--bg:#070b14;--side:#0b1220;--card:#111a2b;--alt:#162238;--line:#26344d;--text:#f2f5fa;--muted:#91a4bf;--gold:#c89b3c;--teal:#0ac8b9;--green:#35c978;--red:#ef5b67}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 "Segoe UI",system-ui,sans-serif}button,input,select{font:inherit}button{border:0;cursor:pointer}
    .shell{max-width:1320px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;align-items:center;gap:18px;margin-bottom:22px}.brand h1{margin:0;font-size:25px}.brand p{margin:4px 0 0;color:var(--muted)}.gold{color:var(--gold)}
    .card{background:var(--card);border:1px solid var(--line);padding:20px}.login{max-width:540px;margin:12vh auto}.login h2{margin-top:0}.help{color:var(--muted);font-size:13px}.hidden{display:none!important}
    input,select{width:100%;background:#0c1424;color:var(--text);border:1px solid var(--line);padding:11px 12px;outline:none}input:focus,select:focus{border-color:var(--teal)}label{display:block;color:var(--muted);font-size:12px;margin:12px 0 5px}
    .btn{background:var(--gold);color:#111827;padding:10px 14px;font-weight:650}.btn.secondary{background:var(--alt);color:var(--text)}.btn.danger{background:var(--red);color:white}.btn.small{padding:7px 10px;font-size:12px}.row{display:flex;gap:10px;align-items:end}.row>*{flex:1}.row .fit{flex:0 0 auto}
    .stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:18px}.stat{background:var(--card);border:1px solid var(--line);padding:16px}.stat strong{display:block;font-size:24px}.stat span{color:var(--muted);font-size:12px}.stat.alert{border-color:var(--red)}
    .grid{display:grid;grid-template-columns:minmax(420px,1.05fr) minmax(420px,.95fr);gap:18px}.section-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:14px}.section-head h2{margin:0;font-size:18px}.badge{border-radius:999px;background:var(--red);padding:3px 9px;font-weight:700;font-size:12px}
    .friend{background:var(--alt);border:1px solid var(--line);padding:14px;margin-top:10px}.friend.off{opacity:.62}.friend-top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}.friend h3{margin:0}.hint{color:var(--muted);font:12px Consolas,monospace}.actions{display:flex;flex-wrap:wrap;gap:7px;justify-content:flex-end}.account{display:flex;justify-content:space-between;align-items:center;background:#0c1424;padding:8px 10px;margin-top:8px}.account span{overflow-wrap:anywhere}
    .device{border:1px solid var(--line);padding:12px;margin-top:9px;background:var(--alt)}.device.new{border-color:var(--red);box-shadow:inset 3px 0 var(--red)}.device-title{display:flex;justify-content:space-between;gap:8px}.meta{color:var(--muted);font-size:12px;margin-top:4px}.danger-text{color:var(--red);font-weight:700}.ok-text{color:var(--green)}
    .activity{margin-top:18px}.table-wrap{overflow:auto;border:1px solid var(--line)}table{width:100%;border-collapse:collapse;min-width:780px}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line);font-size:12px}th{background:var(--alt);color:var(--muted)}td{background:var(--card)}
    .empty{color:var(--muted);padding:18px;text-align:center}.notice{margin:12px 0;padding:10px 12px;background:#30240f;border:1px solid var(--gold);color:#f5d78c}.error{margin:10px 0;color:var(--red)}
    dialog{width:min(720px,calc(100% - 30px));background:var(--card);color:var(--text);border:1px solid var(--line);padding:22px}dialog::backdrop{background:#000a}textarea{width:100%;min-height:82px;background:#0c1424;color:var(--text);border:1px solid var(--line);padding:10px;resize:vertical;font:12px Consolas,monospace}.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}
    @media(max-width:980px){.grid{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}.shell{padding:16px}}@media(max-width:600px){.top,.friend-top,.row{align-items:stretch;flex-direction:column}.stats{grid-template-columns:1fr 1fr}.actions{justify-content:flex-start}.row .fit{flex:auto}}
  </style>
</head>
<body>
  <main class="shell">
    <section id="login" class="card login">
      <h2><span class="gold">LOL</span> XP Tracker</h2>
      <p class="help">Panel właściciela. Kod administratora pozostaje tylko w tej karcie przeglądarki.</p>
      <form id="login-form">
        <label for="admin-token">Kod administratora</label>
        <input id="admin-token" type="password" autocomplete="current-password" required>
        <p id="login-error" class="error"></p>
        <button class="btn" type="submit">Otwórz panel</button>
      </form>
    </section>

    <section id="panel" class="hidden">
      <header class="top">
        <div class="brand"><h1><span class="gold">LOL</span> XP Tracker</h1><p>Znajomi, konta i aktywność kodów</p></div>
        <div class="actions"><button id="refresh" class="btn secondary">Odśwież</button><button id="logout" class="btn secondary">Wyloguj</button></div>
      </header>
      <div id="global-error" class="error"></div>
      <section class="stats">
        <div class="stat"><strong id="stat-friends">0</strong><span>znajomych</span></div>
        <div class="stat"><strong id="stat-accounts">0</strong><span>kont Riot</span></div>
        <div class="stat"><strong id="stat-devices">0</strong><span>urządzeń</span></div>
        <div id="alert-card" class="stat"><strong id="stat-alerts">0</strong><span>nowych urządzeń</span></div>
      </section>
      <div class="grid">
        <section class="card">
          <div class="section-head"><h2>Znajomi i ich konta</h2></div>
          <form id="friend-form">
            <div class="row">
              <div><label>Nazwa znajomego</label><input name="name" maxlength="60" placeholder="np. Kacper" required></div>
              <div><label>Pierwsze konto (opcjonalnie)</label><input name="game_name" maxlength="64" placeholder="Nazwa Riot"></div>
              <div><label>Tag</label><input name="tag_line" maxlength="16" placeholder="EUW"></div>
              <div class="fit"><button class="btn" type="submit">Dodaj</button></div>
            </div>
          </form>
          <div class="notice">Kod nie wygasa. Aplikacja pokaże go tylko po utworzeniu lub zmianie — skopiuj wtedy zaproszenie dla znajomego.</div>
          <div id="friends"></div>
        </section>
        <section class="card">
          <div class="section-head"><h2>Urządzenia</h2><span id="alert-badge" class="badge hidden">0 nowych</span></div>
          <p class="help">Nowe urządzenie nie jest blokowane. Dostęp działa, a wpis pozostaje czerwony, dopóki go nie oznaczysz jako znany.</p>
          <div id="devices"></div>
        </section>
      </div>
      <section class="card activity">
        <div class="section-head"><h2>Ostatnia aktywność</h2><span id="retention" class="help"></span></div>
        <div class="table-wrap"><table><thead><tr><th>Data</th><th>Znajomy</th><th>Zdarzenie</th><th>Konto</th><th>Urządzenie / kraj</th><th>Wynik</th></tr></thead><tbody id="activity"></tbody></table></div>
      </section>
    </section>
  </main>

  <dialog id="credentials">
    <h2>Gotowe — przekaż zaproszenie znajomemu</h2>
    <p class="help">Najłatwiej wysłać całe zaproszenie. Znajomy wklei je w aplikacji jednym ruchem. Kod jest bezterminowy.</p>
    <label>Kod dostępu</label><textarea id="new-code" readonly></textarea><button id="copy-code" class="btn secondary small">Kopiuj kod</button>
    <label>Zaproszenie (adres serwera + kod)</label><textarea id="new-invite" readonly></textarea><button id="copy-invite" class="btn small">Kopiuj zaproszenie</button>
    <div class="modal-actions"><button id="close-modal" class="btn secondary">Zamknij</button></div>
  </dialog>

  <script>
  (()=>{
    const $=id=>document.getElementById(id);let token=sessionStorage.getItem('lolxp_admin')||'';let data=null;
    const el=(tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node};
    const button=(text,cls,fn)=>{const node=el('button','btn small '+(cls||''),text);node.type='button';node.addEventListener('click',fn);return node};
    const fmt=value=>{if(!value)return '—';try{return new Date(value).toLocaleString('pl-PL')}catch{return value}};
    async function api(path,options={}){const headers={Authorization:'Bearer '+token,...(options.headers||{})};if(options.body)headers['Content-Type']='application/json';const response=await fetch(path,{...options,headers});let body={};try{body=await response.json()}catch{}if(!response.ok)throw new Error(body.error?.message||('Błąd '+response.status));return body}
    function showCredentials(result){$('new-code').value=result.code;$('new-invite').value=result.invitation;$('credentials').showModal()}
    async function copy(id,button){try{await navigator.clipboard.writeText($(id).value);const old=button.textContent;button.textContent='Skopiowano';setTimeout(()=>button.textContent=old,1200)}catch{$(id).select();document.execCommand('copy')}}
    function fail(error){$('global-error').textContent=error.message||String(error)}
    async function load(){try{data=await api('/v1/admin/overview');$('login').classList.add('hidden');$('panel').classList.remove('hidden');$('login-error').textContent='';render()}catch(error){sessionStorage.removeItem('lolxp_admin');token='';$('panel').classList.add('hidden');$('login').classList.remove('hidden');$('login-error').textContent=error.message}}
    function render(){
      $('global-error').textContent='';$('stat-friends').textContent=data.friends.length;$('stat-accounts').textContent=data.accounts.length;$('stat-devices').textContent=data.devices.length;$('stat-alerts').textContent=data.alerts;
      $('alert-card').classList.toggle('alert',data.alerts>0);$('alert-badge').classList.toggle('hidden',!data.alerts);$('alert-badge').textContent=data.alerts+' nowych';$('retention').textContent='logi z '+data.retention_days+' dni';renderFriends();renderDevices();renderActivity();
    }
    function renderFriends(){const root=$('friends');root.replaceChildren();if(!data.friends.length){root.append(el('div','empty','Nie dodano jeszcze znajomych.'));return}
      data.friends.forEach(friend=>{const card=el('article','friend'+(friend.enabled?'':' off'));const top=el('div','friend-top');const title=el('div');title.append(el('h3','',friend.name),el('div','hint','kod: ••••••'+friend.token_hint+' • '+(friend.enabled?'aktywny':'wyłączony')));const actions=el('div','actions');
        actions.append(button('Dodaj konto','secondary',()=>addAccount(friend)),button('Zmień kod','secondary',()=>rotate(friend)),button(friend.enabled?'Wyłącz kod':'Włącz kod',friend.enabled?'danger':'',()=>toggleFriend(friend)));top.append(title,actions);card.append(top);
        const accounts=data.accounts.filter(a=>a.friend_id===friend.id);if(!accounts.length)card.append(el('div','meta','Brak przypisanych kont — kod nie pobierze żadnego meczu.'));accounts.forEach(account=>{const row=el('div','account');row.append(el('span','',account.game_name+'#'+account.tag_line+' • '+account.platform),button('Usuń','danger',()=>removeAccount(friend,account)));card.append(row)});root.append(card)});
    }
    function renderDevices(){const root=$('devices');root.replaceChildren();if(!data.devices.length){root.append(el('div','empty','Brak zarejestrowanych urządzeń.'));return}data.devices.forEach(device=>{const card=el('article','device'+(device.trusted?'':' new'));const title=el('div','device-title');title.append(el('strong',device.trusted?'ok-text':'danger-text',device.name||('Urządzenie '+device.id.slice(0,8))));if(!device.trusted)title.append(el('span','danger-text','NOWE'));card.append(title,el('div','meta',device.friend_name+' • ostatnio '+fmt(device.last_seen_at)+' • kraj '+(device.last_country||'—')+' • aplikacja '+(device.app_version||'starsza wersja')));const actions=el('div','actions');actions.style.marginTop='9px';if(!device.trusted)actions.append(button('To znane urządzenie','',()=>trustDevice(device)));actions.append(button('Nazwij','secondary',()=>nameDevice(device)),button('Usuń','danger',()=>removeDevice(device)));card.append(actions);root.append(card)})}
    function renderActivity(){const root=$('activity');root.replaceChildren();if(!data.activity.length){const row=el('tr');const cell=el('td','empty','Brak aktywności.');cell.colSpan=6;row.append(cell);root.append(row);return}const labels={new_device:'Nowe urządzenie',request_ok:'Pobrano mecz',denied_account:'Odmowa dla konta',code_rotated:'Zmieniono kod'};data.activity.forEach(item=>{const row=el('tr');[fmt(item.occurred_at),item.friend_name||'—',labels[item.event_type]||item.event_type,item.requested_account||'—',(item.device_name||item.device_id?.slice(0,8)||'—')+' / '+(item.country||'—'),item.result].forEach(value=>row.append(el('td','',value)));root.append(row)})}
    async function addAccount(friend){const game=prompt('Nazwa Riot konta dla '+friend.name+':');if(!game)return;const tag=prompt('Tag po znaku # (np. EUW):');if(!tag)return;const platform=(prompt('Serwer platformy:', 'EUW1')||'EUW1').toUpperCase();try{await api('/v1/admin/friends/'+friend.id+'/accounts',{method:'POST',body:JSON.stringify({game_name:game,tag_line:tag,platform})});await load()}catch(error){fail(error)}}
    async function removeAccount(friend,account){if(!confirm('Usunąć dostęp do '+account.game_name+'#'+account.tag_line+'?'))return;try{await api('/v1/admin/friends/'+friend.id+'/accounts/'+account.id,{method:'DELETE'});await load()}catch(error){fail(error)}}
    async function rotate(friend){if(!confirm('Stary kod '+friend.name+' natychmiast przestanie działać. Kontynuować?'))return;try{showCredentials(await api('/v1/admin/friends/'+friend.id+'/rotate',{method:'POST'}));await load()}catch(error){fail(error)}}
    async function toggleFriend(friend){try{await api('/v1/admin/friends/'+friend.id,{method:'PATCH',body:JSON.stringify({enabled:!friend.enabled})});await load()}catch(error){fail(error)}}
    async function trustDevice(device){try{await api('/v1/admin/devices/'+device.id,{method:'PATCH',body:JSON.stringify({trusted:true})});await load()}catch(error){fail(error)}}
    async function nameDevice(device){const name=prompt('Nazwa urządzenia:',device.name||'');if(name===null)return;try{await api('/v1/admin/devices/'+device.id,{method:'PATCH',body:JSON.stringify({name})});await load()}catch(error){fail(error)}}
    async function removeDevice(device){if(!confirm('Usunąć urządzenie? Przy następnym użyciu pojawi się ponownie jako nowe.'))return;try{await api('/v1/admin/devices/'+device.id,{method:'DELETE'});await load()}catch(error){fail(error)}}
    $('login-form').addEventListener('submit',event=>{event.preventDefault();token=$('admin-token').value.trim();sessionStorage.setItem('lolxp_admin',token);load()});
    $('friend-form').addEventListener('submit',async event=>{event.preventDefault();const form=new FormData(event.currentTarget);try{const result=await api('/v1/admin/friends',{method:'POST',body:JSON.stringify(Object.fromEntries(form))});event.currentTarget.reset();showCredentials(result);await load()}catch(error){fail(error)}});
    $('refresh').addEventListener('click',load);$('logout').addEventListener('click',()=>{sessionStorage.removeItem('lolxp_admin');location.reload()});$('close-modal').addEventListener('click',()=>$('credentials').close());$('copy-code').addEventListener('click',event=>copy('new-code',event.currentTarget));$('copy-invite').addEventListener('click',event=>copy('new-invite',event.currentTarget));
    if(token)load();
  })();
  </script>
</body>
</html>`;
