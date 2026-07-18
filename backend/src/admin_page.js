const ADMIN_HTML = String.raw`<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>LoL XP Tracker — Panel 2.0</title>
  <style>
    :root{color-scheme:dark;--bg:#060a12;--side:#09111f;--card:#101a2b;--alt:#152238;--deep:#0b1424;--line:#263650;--text:#f3f6fb;--muted:#8fa4c0;--gold:#d5a63b;--teal:#12c9ba;--green:#39ce7c;--red:#f15b6c;--blue:#5b9dff}
    *{box-sizing:border-box}html,body{min-height:100%}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 "Segoe UI",system-ui,sans-serif}button,input,select{font:inherit}button{border:0;cursor:pointer}.hidden{display:none!important}
    .login{width:min(520px,calc(100% - 32px));margin:12vh auto;background:var(--card);border:1px solid var(--line);padding:26px}.login h1{margin:0 0 5px}.help,.muted{color:var(--muted)}.error{color:var(--red);min-height:20px}.gold{color:var(--gold)}
    input,select,textarea{width:100%;background:var(--deep);color:var(--text);border:1px solid var(--line);padding:11px 12px;outline:none}input:focus,select:focus,textarea:focus{border-color:var(--teal)}label{display:block;color:var(--muted);font-size:12px;margin:11px 0 5px}
    .btn{background:var(--gold);color:#111827;padding:10px 14px;font-weight:700}.btn.secondary{background:var(--alt);color:var(--text)}.btn.danger{background:var(--red);color:#fff}.btn.positive{background:var(--teal);color:#071512}.btn.small{padding:7px 10px;font-size:12px}.actions{display:flex;flex-wrap:wrap;gap:7px;justify-content:flex-end}
    .app{min-height:100vh;display:grid;grid-template-columns:246px minmax(0,1fr)}.sidebar{position:sticky;top:0;height:100vh;background:var(--side);border-right:1px solid var(--line);padding:24px 16px;display:flex;flex-direction:column}.brand{padding:0 10px 22px}.brand h1{margin:0;font-size:21px}.brand p{margin:4px 0 0;color:var(--muted);font-size:12px}.nav{display:grid;gap:6px}.nav button{display:flex;align-items:center;justify-content:space-between;text-align:left;background:transparent;color:var(--muted);padding:11px 12px;border-left:3px solid transparent}.nav button:hover{background:var(--deep);color:var(--text)}.nav button.active{background:var(--alt);color:var(--text);border-left-color:var(--gold)}.nav .count{min-width:22px;text-align:center;background:var(--red);color:white;border-radius:999px;padding:1px 6px;font-size:11px;font-weight:800}.sidebar-foot{margin-top:auto;border-top:1px solid var(--line);padding:15px 10px 0;color:var(--muted);font-size:12px}.online-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--green);margin-right:7px}.online-dot.off{background:var(--red)}
    .main{min-width:0;padding:22px 28px 44px}.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px}.topbar h2{margin:0;font-size:24px}.topbar p{margin:3px 0 0;color:var(--muted)}.top-actions{display:flex;gap:8px;align-items:center}.global-search{width:min(360px,35vw)}
    .panel{background:var(--card);border:1px solid var(--line);padding:19px;margin-bottom:16px}.panel-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:13px}.panel-head h3{margin:0;font-size:17px}.notice{padding:11px 13px;background:#30240f;border:1px solid var(--gold);color:#f5d78c;margin:12px 0}.grid{display:grid;gap:16px}.grid.two{grid-template-columns:minmax(0,1.15fr) minmax(320px,.85fr)}
    .stats{display:grid;grid-template-columns:repeat(5,minmax(120px,1fr));gap:12px;margin-bottom:16px}.stat{background:var(--card);border:1px solid var(--line);padding:16px;position:relative;overflow:hidden}.stat::after{content:"";position:absolute;left:0;bottom:0;width:100%;height:3px;background:var(--teal)}.stat.alert::after{background:var(--red)}.stat strong{display:block;font-size:25px}.stat span{color:var(--muted);font-size:12px}
    .form-grid{display:grid;grid-template-columns:1.1fr 1fr .65fr .65fr auto;gap:9px;align-items:end}.toolbar{display:grid;grid-template-columns:minmax(220px,1fr) 210px;gap:9px;margin:13px 0}
    .friend{background:var(--alt);border:1px solid var(--line);padding:16px;margin-top:11px}.friend.off{opacity:.7}.friend-top{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.friend h3{margin:0}.hint{color:var(--muted);font:12px Consolas,monospace}.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.chip{background:var(--deep);border:1px solid var(--line);color:var(--muted);padding:3px 8px;border-radius:999px;font-size:11px}.chip.alert{color:var(--red);border-color:var(--red)}
    .subsection{border-top:1px solid var(--line);margin-top:13px;padding-top:11px}.subsection h4{margin:0 0 6px;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}.account,.device,.alert-row{display:flex;align-items:center;justify-content:space-between;gap:12px;background:var(--deep);border:1px solid var(--line);padding:10px 11px;margin-top:7px}.account{border-left:3px solid var(--teal)}.account.new,.device.new,.alert-row.new{border-color:var(--red);box-shadow:inset 3px 0 var(--red)}.item-title{font-weight:700}.meta{color:var(--muted);font-size:12px;margin-top:2px}.danger-text{color:var(--red);font-weight:700}.ok-text{color:var(--green);font-weight:700}.status{display:inline-block;border-radius:999px;padding:3px 8px;font-size:11px;font-weight:700;background:var(--alt);color:var(--muted)}.status.good{color:var(--green);border:1px solid #246342}.status.bad{color:var(--red);border:1px solid #7a3140}.status.warn{color:var(--gold);border:1px solid #785f27}
    .table-wrap{overflow:auto;border:1px solid var(--line)}table{width:100%;border-collapse:collapse;min-width:820px}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line);font-size:12px}th{background:var(--alt);color:var(--muted);position:sticky;top:0}td{background:var(--card)}.empty{color:var(--muted);padding:24px;text-align:center}
    .system-grid{display:grid;grid-template-columns:repeat(3,minmax(180px,1fr));gap:12px}.system-card{background:var(--deep);border:1px solid var(--line);padding:16px}.system-card strong{display:block;margin-bottom:5px}.system-card.good{border-left:3px solid var(--green)}.system-card.bad{border-left:3px solid var(--red)}.system-card.warn{border-left:3px solid var(--gold)}
    dialog{width:min(720px,calc(100% - 28px));background:var(--card);color:var(--text);border:1px solid var(--line);padding:22px}dialog::backdrop{background:#000b}textarea{min-height:82px;resize:vertical;font:12px Consolas,monospace}.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}
    @media(max-width:1120px){.stats{grid-template-columns:repeat(3,1fr)}.grid.two{grid-template-columns:1fr}.form-grid{grid-template-columns:1fr 1fr}.form-grid .submit{grid-column:span 2}.system-grid{grid-template-columns:repeat(2,1fr)}}
    @media(max-width:760px){.app{grid-template-columns:1fr}.sidebar{position:static;height:auto;padding:15px}.brand{padding-bottom:12px}.nav{grid-template-columns:repeat(3,1fr)}.nav button{border-left:0;border-bottom:3px solid transparent;padding:9px}.nav button.active{border-left:0;border-bottom-color:var(--gold)}.sidebar-foot{display:none}.main{padding:16px}.topbar{align-items:flex-start;flex-direction:column}.top-actions{width:100%;flex-wrap:wrap}.global-search{width:100%;max-width:none}.stats{grid-template-columns:repeat(2,1fr)}.friend-top,.account,.device,.alert-row{align-items:stretch;flex-direction:column}.actions{justify-content:flex-start}.toolbar,.form-grid,.system-grid{grid-template-columns:1fr}.form-grid .submit{grid-column:auto}}
  </style>
</head>
<body>
  <section id="login" class="login">
    <h1><span class="gold">LOL</span> XP Tracker</h1>
    <p class="help">Panel zarządzania 2.0. Hasło administratora pozostaje tylko w tej karcie.</p>
    <form id="login-form">
      <label for="admin-token">Hasło administratora</label>
      <input id="admin-token" type="password" autocomplete="current-password" required>
      <p id="login-error" class="error"></p>
      <button class="btn" type="submit">Otwórz panel</button>
    </form>
  </section>

  <div id="app" class="app hidden">
    <aside class="sidebar">
      <div class="brand"><h1><span class="gold">LOL</span> XP Tracker</h1><p>Panel zarządzania 2.0</p></div>
      <nav class="nav">
        <button class="active" data-view="dashboard"><span>Pulpit</span><span id="nav-alerts" class="count hidden">0</span></button>
        <button data-view="friends"><span>Znajomi</span></button>
        <button data-view="accounts"><span>Konta Riot</span><span id="nav-account-alerts" class="count hidden">0</span></button>
        <button data-view="devices"><span>Urządzenia</span><span id="nav-device-alerts" class="count hidden">0</span></button>
        <button data-view="activity"><span>Aktywność</span></button>
        <button data-view="system"><span>Stan systemu</span></button>
      </nav>
      <div class="sidebar-foot"><span id="worker-dot" class="online-dot off"></span><span id="worker-label">Sprawdzanie Workera…</span><div id="worker-version" class="meta"></div></div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div><h2 id="view-title">Pulpit</h2><p id="view-subtitle">Najważniejsze informacje i alerty</p></div>
        <div class="top-actions"><input id="global-search" class="global-search" type="search" placeholder="Szukaj w bieżącym widoku"><button id="refresh" class="btn secondary">Odśwież</button><button id="logout" class="btn secondary">Wyloguj</button></div>
      </header>
      <div id="global-error" class="error"></div>

      <section id="view-dashboard" class="view">
        <div class="stats">
          <div class="stat"><strong id="stat-friends">0</strong><span>znajomych</span></div>
          <div class="stat"><strong id="stat-accounts">0</strong><span>kont Riot</span></div>
          <div class="stat"><strong id="stat-devices">0</strong><span>urządzeń</span></div>
          <div id="stat-alert-card" class="stat"><strong id="stat-alerts">0</strong><span>alertów do sprawdzenia</span></div>
          <div class="stat"><strong id="stat-requests">0</strong><span>pobrań meczu / 24 h</span></div>
        </div>
        <div class="grid two">
          <section class="panel"><div class="panel-head"><h3>Wymagają uwagi</h3><span id="dashboard-alert-count" class="status">0</span></div><div id="dashboard-alerts"></div></section>
          <section class="panel"><div class="panel-head"><h3>Stan systemu</h3><button class="btn secondary small" data-go="system">Szczegóły</button></div><div id="dashboard-system" class="system-grid"></div></section>
        </div>
        <section class="panel"><div class="panel-head"><h3>Ostatnia aktywność</h3><button class="btn secondary small" data-go="activity">Pokaż wszystko</button></div><div class="table-wrap"><table><thead><tr><th>Data</th><th>Znajomy</th><th>Zdarzenie</th><th>Konto</th><th>Wynik</th></tr></thead><tbody id="dashboard-activity"></tbody></table></div></section>
      </section>

      <section id="view-friends" class="view hidden">
        <section class="panel">
          <div class="panel-head"><h3>Dodaj znajomego</h3></div>
          <form id="friend-form" class="form-grid">
            <div><label>Nazwa profilu</label><input name="name" maxlength="60" placeholder="np. Kacper" required></div>
            <div><label>Pierwsze Riot ID (opcjonalnie)</label><input name="game_name" maxlength="64" placeholder="Nazwa Riot"></div>
            <div><label>Tag</label><input name="tag_line" maxlength="16" placeholder="EUW"></div>
            <div><label>Serwer</label><select name="platform"><option>EUW1</option><option>EUN1</option><option>NA1</option><option>KR</option><option>TR1</option></select></div>
            <div class="submit"><button class="btn" type="submit">Dodaj profil</button></div>
          </form>
          <div class="notice">Kod nie wygasa. Każde kolejne konto użyte przez znajomego zostanie dopisane automatycznie i pokaże się jako alert — pobieranie meczu nie będzie blokowane.</div>
        </section>
        <section class="panel"><div class="panel-head"><h3>Profile znajomych</h3></div><div class="toolbar"><input id="friend-filter" type="search" placeholder="Szukaj profilu, Riot ID lub urządzenia"><select id="friend-status"><option value="all">Wszystkie profile</option><option value="active">Tylko aktywne</option><option value="disabled">Tylko wyłączone</option><option value="alerts">Tylko z alertami</option></select></div><div id="friends"></div></section>
      </section>

      <section id="view-accounts" class="view hidden">
        <section class="panel"><div class="panel-head"><h3>Wszystkie konta Riot</h3><span id="account-summary" class="muted"></span></div><div class="toolbar"><input id="account-filter" type="search" placeholder="Szukaj Riot ID lub znajomego"><select id="account-status"><option value="all">Wszystkie konta</option><option value="new">Tylko nowe</option><option value="reviewed">Tylko sprawdzone</option></select></div><div id="accounts"></div></section>
      </section>

      <section id="view-devices" class="view hidden">
        <section class="panel"><div class="panel-head"><h3>Urządzenia według znajomych</h3><span id="device-summary" class="muted"></span></div><div class="toolbar"><input id="device-filter" type="search" placeholder="Szukaj urządzenia, kraju lub znajomego"><select id="device-status"><option value="all">Wszystkie urządzenia</option><option value="new">Tylko nowe</option><option value="trusted">Tylko znane</option></select></div><div id="devices"></div></section>
      </section>

      <section id="view-activity" class="view hidden">
        <section class="panel"><div class="panel-head"><h3>Dziennik aktywności</h3><span id="retention" class="muted"></span></div><div class="toolbar"><select id="activity-friend"><option value="all">Wszyscy znajomi</option></select><select id="activity-event"><option value="all">Wszystkie zdarzenia</option><option value="account_auto_added">Automatycznie dodane konta</option><option value="new_device">Nowe urządzenia</option><option value="request_ok">Pobrane mecze</option><option value="account_reviewed">Sprawdzone konta</option><option value="code_rotated">Zmiany kodów</option></select></div><div class="table-wrap"><table><thead><tr><th>Data</th><th>Znajomy</th><th>Zdarzenie</th><th>Konto</th><th>Urządzenie / kraj</th><th>Wynik</th></tr></thead><tbody id="activity"></tbody></table></div></section>
      </section>

      <section id="view-system" class="view hidden">
        <section class="panel"><div class="panel-head"><h3>Stan usług</h3><span id="system-refreshed" class="muted"></span></div><div id="system-cards" class="system-grid"></div></section>
        <section class="panel"><h3>Jak czytać ten ekran</h3><p class="muted">Panel sprawdza, czy Worker odpowiada i czy wymagane elementy są skonfigurowane. Status „zapisany” przy kluczu Riot nie potwierdza daty jego wygaśnięcia — błąd klucza pojawi się w aplikacji i dzienniku po żądaniu do Riot.</p></section>
      </section>
    </main>
  </div>

  <dialog id="credentials">
    <h2>Gotowe — przekaż zaproszenie znajomemu</h2>
    <p class="help">Najłatwiej wysłać całe zaproszenie. Znajomy wklei je w aplikacji jednym ruchem.</p>
    <label>Kod dostępu</label><textarea id="new-code" readonly></textarea><button id="copy-code" class="btn secondary small">Kopiuj kod</button>
    <label>Zaproszenie (adres serwera + kod)</label><textarea id="new-invite" readonly></textarea><button id="copy-invite" class="btn small">Kopiuj zaproszenie</button>
    <div class="modal-actions"><button id="close-modal" class="btn secondary">Zamknij</button></div>
  </dialog>

  <script>
  (()=>{
    const $=id=>document.getElementById(id);let token=sessionStorage.getItem('lolxp_admin')||'';let data=null;let health=null;let currentView='dashboard';let refreshedAt=null;
    const titles={dashboard:['Pulpit','Najważniejsze informacje i alerty'],friends:['Znajomi','Profile, zaproszenia i przypisany dostęp'],accounts:['Konta Riot','Konta dopisane ręcznie i automatycznie'],devices:['Urządzenia','Instalacje aplikacji pogrupowane według znajomych'],activity:['Aktywność','30-dniowy dziennik użycia kodów'],system:['Stan systemu','Worker, baza i konfiguracja prywatnego API']};
    const labels={new_device:'Nowe urządzenie',account_auto_added:'Automatycznie dodano konto',first_account_claimed:'Przypisano pierwsze konto',request_ok:'Pobrano mecz',denied_account:'Odmowa dla konta',code_rotated:'Zmieniono kod',account_reviewed:'Sprawdzono konto'};
    const el=(tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node};
    const button=(text,cls,fn)=>{const node=el('button','btn small '+(cls||''),text);node.type='button';node.addEventListener('click',fn);return node};
    const fmt=value=>{if(!value)return '—';try{return new Date(value).toLocaleString('pl-PL')}catch{return value}};
    const friendOf=id=>data.friends.find(friend=>friend.id===id);
    const searchable=(...values)=>values.flat().filter(Boolean).join(' ').toLocaleLowerCase('pl');
    const query=()=>($('global-search').value||'').trim().toLocaleLowerCase('pl');
    async function api(path,options={}){const headers={Authorization:'Bearer '+token,...(options.headers||{})};if(options.body)headers['Content-Type']='application/json';const response=await fetch(path,{...options,headers});let body={};try{body=await response.json()}catch{}if(!response.ok){const error=new Error(body.error?.message||('Błąd '+response.status));error.status=response.status;throw error}return body}
    async function getHealth(){try{const response=await fetch('/health',{cache:'no-store'});if(!response.ok)throw new Error('HTTP '+response.status);return await response.json()}catch(error){return {status:'offline',version:'—',message:error.message}}}
    function fail(error){$('global-error').textContent=error.message||String(error);window.scrollTo({top:0,behavior:'smooth'})}
    function showCredentials(result){$('new-code').value=result.code;$('new-invite').value=result.invitation;$('credentials').showModal()}
    async function copy(id,control){try{await navigator.clipboard.writeText($(id).value);const old=control.textContent;control.textContent='Skopiowano';setTimeout(()=>control.textContent=old,1200)}catch{$(id).select();document.execCommand('copy')}}
    function setCount(id,value){const node=$(id);node.textContent=value;node.classList.toggle('hidden',!value)}
    async function load(){try{const result=await Promise.all([api('/v1/admin/overview'),getHealth()]);data=result[0];health=result[1];refreshedAt=new Date();$('login').classList.add('hidden');$('app').classList.remove('hidden');$('login-error').textContent='';$('global-error').textContent='';render()}catch(error){if(error.status===401){sessionStorage.removeItem('lolxp_admin');token='';$('app').classList.add('hidden');$('login').classList.remove('hidden');$('login-error').textContent=error.message}else fail(error)}}
    function render(){renderChrome();renderStats();renderDashboard();renderFriends();renderAccounts();renderDevices();renderActivity();renderSystem()}
    function renderChrome(){const online=health?.status==='ok';$('worker-dot').classList.toggle('off',!online);$('worker-label').textContent=online?'Worker działa':'Worker niedostępny';$('worker-version').textContent='backend '+(health?.version||'—');setCount('nav-alerts',data.alerts||0);setCount('nav-account-alerts',data.account_alerts||0);setCount('nav-device-alerts',data.device_alerts||0);$('retention').textContent='logi z '+data.retention_days+' dni'}
    function renderStats(){const since=Date.now()-86400000;const requests=data.activity.filter(item=>item.event_type==='request_ok'&&Date.parse(item.occurred_at)>=since).length;$('stat-friends').textContent=data.friends.length;$('stat-accounts').textContent=data.accounts.length;$('stat-devices').textContent=data.devices.length;$('stat-alerts').textContent=data.alerts||0;$('stat-requests').textContent=requests;$('stat-alert-card').classList.toggle('alert',Boolean(data.alerts))}
    function systemCard(title,value,kind,description){const card=el('div','system-card '+kind);card.append(el('strong','',title),el('div','status '+(kind==='good'?'good':kind==='bad'?'bad':'warn'),value));if(description)card.append(el('div','meta',description));return card}
    function renderDashboard(){const root=$('dashboard-alerts');root.replaceChildren();const newAccounts=data.accounts.filter(account=>!account.reviewed);const newDevices=data.devices.filter(device=>!device.trusted);$('dashboard-alert-count').textContent=(newAccounts.length+newDevices.length)+' alertów';newAccounts.forEach(account=>{const friend=friendOf(account.friend_id);const row=el('div','alert-row new');const info=el('div');info.append(el('div','danger-text','Nowe konto Riot'),el('div','item-title',account.game_name+'#'+account.tag_line),el('div','meta',(friend?.name||'Nieznany profil')+' • '+account.platform+' • '+fmt(account.created_at)));const actions=el('div','actions');actions.append(button('Oznacz jako sprawdzone','positive',()=>reviewAccount(friend,account)),button('Usuń','danger',()=>removeAccount(friend,account)));row.append(info,actions);root.append(row)});newDevices.forEach(device=>{const row=el('div','alert-row new');const info=el('div');info.append(el('div','danger-text','Nowe urządzenie'),el('div','item-title',device.name||('Urządzenie '+device.id.slice(0,8))),el('div','meta',device.friend_name+' • '+(device.last_country||'—')+' • aplikacja '+(device.app_version||'starsza')));const actions=el('div','actions');actions.append(button('To znane urządzenie','positive',()=>trustDevice(device)),button('Nazwij','secondary',()=>nameDevice(device)));row.append(info,actions);root.append(row)});if(!root.children.length)root.append(el('div','empty','Wszystko sprawdzone — brak nowych kont i urządzeń.'));const system=$('dashboard-system');system.replaceChildren(systemCard('Worker',health?.status==='ok'?'Działa':'Offline',health?.status==='ok'?'good':'bad','wersja '+(health?.version||'—')),systemCard('Baza profili',health?.friend_profiles?'Połączona':'Brak',health?.friend_profiles?'good':'bad'));renderActivityRows($('dashboard-activity'),data.activity.slice(0,6),false)}
    function renderFriends(){const root=$('friends');root.replaceChildren();const local=($('friend-filter').value||'').trim().toLocaleLowerCase('pl');const q=[query(),local].filter(Boolean);const status=$('friend-status').value;let shown=0;data.friends.forEach(friend=>{const accounts=data.accounts.filter(a=>a.friend_id===friend.id);const devices=data.devices.filter(d=>d.friend_id===friend.id);const alerts=accounts.filter(a=>!a.reviewed).length+devices.filter(d=>!d.trusted).length;const hay=searchable(friend.name,accounts.map(a=>a.game_name+'#'+a.tag_line),devices.map(d=>[d.name,d.id,d.last_country]));if(q.some(term=>!hay.includes(term)))return;if(status==='active'&&!friend.enabled)return;if(status==='disabled'&&friend.enabled)return;if(status==='alerts'&&!alerts)return;shown+=1;const card=el('article','friend'+(friend.enabled?'':' off'));const top=el('div','friend-top');const title=el('div');title.append(el('h3','',friend.name),el('div','hint','kod: ••••••'+friend.token_hint+' • '+(friend.enabled?'aktywny':'wyłączony')));const chips=el('div','chips');chips.append(el('span','chip',accounts.length+' kont Riot'),el('span','chip',devices.length+' urządzeń'));if(alerts)chips.append(el('span','chip alert',alerts+' alertów'));title.append(chips);const actions=el('div','actions');actions.append(button('Zmień nazwę','secondary',()=>renameFriend(friend)),button('Dodaj konto','secondary',()=>addAccount(friend)),button('Zmień kod','secondary',()=>rotate(friend)),button(friend.enabled?'Wyłącz kod':'Włącz kod',friend.enabled?'danger':'positive',()=>toggleFriend(friend)),button('Usuń profil','danger',()=>removeFriend(friend)));top.append(title,actions);card.append(top);const accountSection=el('div','subsection');accountSection.append(el('h4','',accounts.length?'Konta Riot ('+accounts.length+')':'Konta Riot'));if(!accounts.length)accountSection.append(el('div','meta','Pierwsze użyte konto zostanie dopisane automatycznie.'));accounts.forEach(account=>accountSection.append(renderAccount(account,friend)));card.append(accountSection);const deviceSection=el('div','subsection');deviceSection.append(el('h4','',devices.length?'Urządzenia ('+devices.length+')':'Urządzenia'));if(!devices.length)deviceSection.append(el('div','meta','Brak zarejestrowanych urządzeń.'));devices.forEach(device=>deviceSection.append(renderDevice(device)));card.append(deviceSection);root.append(card)});if(!shown)root.append(el('div','empty','Brak profili pasujących do filtrów.'))}
    function renderAccount(account,friend){const row=el('div','account'+(account.reviewed?'':' new'));const info=el('div');info.append(el('div','item-title',account.game_name+'#'+account.tag_line),el('div','meta',(friend?.name||'—')+' • '+account.platform+' • dodano '+fmt(account.created_at)));const actions=el('div','actions');if(!account.reviewed)actions.append(el('span','status bad','NOWE'),button('Sprawdzone','positive',()=>reviewAccount(friend,account)));else actions.append(el('span','status good','SPRAWDZONE'));actions.append(button('Usuń','danger',()=>removeAccount(friend,account)));row.append(info,actions);return row}
    function renderAccounts(){const root=$('accounts');root.replaceChildren();const local=($('account-filter').value||'').trim().toLocaleLowerCase('pl');const q=[query(),local].filter(Boolean);const status=$('account-status').value;let shown=0;data.accounts.forEach(account=>{const friend=friendOf(account.friend_id);const hay=searchable(account.game_name,account.tag_line,account.platform,friend?.name);if(q.some(term=>!hay.includes(term)))return;if(status==='new'&&account.reviewed)return;if(status==='reviewed'&&!account.reviewed)return;root.append(renderAccount(account,friend));shown+=1});$('account-summary').textContent=data.account_alerts+' nowych • '+data.accounts.length+' wszystkich';if(!shown)root.append(el('div','empty','Brak kont pasujących do filtrów.'))}
    function renderDevice(device){const row=el('div','device'+(device.trusted?'':' new'));const info=el('div');const latest=data.activity.find(item=>item.device_id===device.id&&item.requested_account);info.append(el('div',device.trusted?'item-title':'danger-text',device.name||('Urządzenie '+device.id.slice(0,8))),el('div','meta','Ostatnie konto: '+(latest?.requested_account||'—')+' • '+device.friend_name+' • '+(device.last_country||'—')+' • '+fmt(device.last_seen_at)+' • aplikacja '+(device.app_version||'starsza')));const actions=el('div','actions');if(!device.trusted)actions.append(el('span','status bad','NOWE'),button('To znane urządzenie','positive',()=>trustDevice(device)));else actions.append(el('span','status good','ZNANE'));actions.append(button('Nazwij','secondary',()=>nameDevice(device)),button('Usuń','danger',()=>removeDevice(device)));row.append(info,actions);return row}
    function renderDevices(){const root=$('devices');root.replaceChildren();const local=($('device-filter').value||'').trim().toLocaleLowerCase('pl');const q=[query(),local].filter(Boolean);const status=$('device-status').value;let shown=0;data.friends.forEach(friend=>{const devices=data.devices.filter(device=>device.friend_id===friend.id).filter(device=>{const hay=searchable(device.name,device.id,device.last_country,device.app_version,friend.name);if(q.some(term=>!hay.includes(term)))return false;if(status==='new'&&device.trusted)return false;if(status==='trusted'&&!device.trusted)return false;return true});if(!devices.length)return;const group=el('article','friend');group.append(el('h3','',friend.name));devices.forEach(device=>group.append(renderDevice(device)));root.append(group);shown+=devices.length});$('device-summary').textContent=data.device_alerts+' nowych • '+data.devices.length+' wszystkich';if(!shown)root.append(el('div','empty','Brak urządzeń pasujących do filtrów.'))}
    function renderActivityRows(root,items,full=true){root.replaceChildren();if(!items.length){const row=el('tr');const cell=el('td','empty','Brak aktywności.');cell.colSpan=full?6:5;row.append(cell);root.append(row);return}items.forEach(item=>{const row=el('tr');const values=full?[fmt(item.occurred_at),item.friend_name||'—',labels[item.event_type]||item.event_type,item.requested_account||'—',(item.device_name||item.device_id?.slice(0,8)||'—')+' / '+(item.country||'—'),item.result]:[fmt(item.occurred_at),item.friend_name||'—',labels[item.event_type]||item.event_type,item.requested_account||'—',item.result];values.forEach(value=>row.append(el('td','',value)));root.append(row)})}
    function renderActivity(){const friendSelect=$('activity-friend');const selected=friendSelect.value;friendSelect.replaceChildren(new Option('Wszyscy znajomi','all'));data.friends.forEach(friend=>friendSelect.add(new Option(friend.name,friend.id)));friendSelect.value=[...friendSelect.options].some(option=>option.value===selected)?selected:'all';const friendId=friendSelect.value;const eventType=$('activity-event').value;const q=query();const items=data.activity.filter(item=>(friendId==='all'||item.friend_id===friendId)&&(eventType==='all'||item.event_type===eventType)&&(!q||searchable(item.friend_name,item.event_type,labels[item.event_type],item.requested_account,item.device_name,item.country,item.result).includes(q)));renderActivityRows($('activity'),items,true)}
    function renderSystem(){const root=$('system-cards');root.replaceChildren();const online=health?.status==='ok';root.append(systemCard('Cloudflare Worker',online?'Działa':'Niedostępny',online?'good':'bad',health?.message||'Prywatne API odpowiada'),systemCard('Wersja backendu',health?.version||'—',online?'good':'warn','Wdrożona wersja usługi'),systemCard('Baza D1',health?.friend_profiles?'Połączona':'Brak połączenia',health?.friend_profiles?'good':'bad','Profile, konta, urządzenia i logi'),systemCard('Klucz Riot API',health?.riot_api_configured?'Zapisany':'Brak',health?.riot_api_configured?'good':'bad','Wartość pozostaje ukryta'),systemCard('Ochrona panelu',health?.admin_configured?'Aktywna':'Brak',health?.admin_configured?'good':'bad','ADMIN_TOKEN'),systemCard('Przechowywanie logów',data.retention_days+' dni','good','Automatyczne czyszczenie'));$('system-refreshed').textContent='odświeżono '+(refreshedAt?refreshedAt.toLocaleTimeString('pl-PL'):'—')}
    function showView(name){currentView=name;document.querySelectorAll('.view').forEach(view=>view.classList.toggle('hidden',view.id!=='view-'+name));document.querySelectorAll('.nav button[data-view]').forEach(control=>control.classList.toggle('active',control.dataset.view===name));$('view-title').textContent=titles[name][0];$('view-subtitle').textContent=titles[name][1];$('global-search').value='';if(data)render()}
    async function addAccount(friend){const game=prompt('Nazwa Riot konta dla '+friend.name+':');if(!game)return;const tag=prompt('Tag po znaku # (np. EUW):');if(!tag)return;const platform=(prompt('Serwer platformy:','EUW1')||'EUW1').toUpperCase();try{await api('/v1/admin/friends/'+friend.id+'/accounts',{method:'POST',body:JSON.stringify({game_name:game,tag_line:tag,platform})});await load()}catch(error){fail(error)}}
    async function reviewAccount(friend,account){try{await api('/v1/admin/friends/'+friend.id+'/accounts/'+account.id,{method:'PATCH'});await load()}catch(error){fail(error)}}
    async function removeAccount(friend,account){if(!confirm('Usunąć dostęp do '+account.game_name+'#'+account.tag_line+'? Jeśli znajomy ponownie użyje tego konta, zostanie ono automatycznie dopisane.'))return;try{await api('/v1/admin/friends/'+friend.id+'/accounts/'+account.id,{method:'DELETE'});await load()}catch(error){fail(error)}}
    async function rotate(friend){if(!confirm('Stary kod '+friend.name+' natychmiast przestanie działać. Kontynuować?'))return;try{showCredentials(await api('/v1/admin/friends/'+friend.id+'/rotate',{method:'POST'}));await load()}catch(error){fail(error)}}
    async function renameFriend(friend){const name=prompt('Nowa nazwa profilu:',friend.name);if(name===null||name.trim()===friend.name)return;try{await api('/v1/admin/friends/'+friend.id,{method:'PATCH',body:JSON.stringify({name:name.trim()})});await load()}catch(error){fail(error)}}
    async function toggleFriend(friend){try{await api('/v1/admin/friends/'+friend.id,{method:'PATCH',body:JSON.stringify({enabled:!friend.enabled})});await load()}catch(error){fail(error)}}
    async function removeFriend(friend){if(!confirm('Trwale usunąć profil '+friend.name+' wraz z kontami, urządzeniami i historią?'))return;const typed=prompt('Aby potwierdzić, wpisz dokładnie nazwę profilu: '+friend.name);if(typed!==friend.name){if(typed!==null)fail(new Error('Nazwa nie zgadza się — niczego nie usunięto.'));return}try{await api('/v1/admin/friends/'+friend.id,{method:'DELETE'});await load()}catch(error){fail(error)}}
    async function trustDevice(device){try{await api('/v1/admin/devices/'+device.id,{method:'PATCH',body:JSON.stringify({trusted:true})});await load()}catch(error){fail(error)}}
    async function nameDevice(device){const name=prompt('Nazwa urządzenia:',device.name||'');if(name===null)return;try{await api('/v1/admin/devices/'+device.id,{method:'PATCH',body:JSON.stringify({name})});await load()}catch(error){fail(error)}}
    async function removeDevice(device){if(!confirm('Usunąć urządzenie? Przy następnym użyciu pojawi się ponownie jako nowe.'))return;try{await api('/v1/admin/devices/'+device.id,{method:'DELETE'});await load()}catch(error){fail(error)}}
    $('login-form').addEventListener('submit',event=>{event.preventDefault();token=$('admin-token').value.trim();sessionStorage.setItem('lolxp_admin',token);load()});
    $('friend-form').addEventListener('submit',async event=>{event.preventDefault();const formElement=event.currentTarget;const form=new FormData(formElement);try{const result=await api('/v1/admin/friends',{method:'POST',body:JSON.stringify(Object.fromEntries(form))});formElement.reset();showCredentials(result);await load()}catch(error){fail(error)}});
    document.querySelectorAll('.nav button[data-view]').forEach(control=>control.addEventListener('click',()=>showView(control.dataset.view)));document.querySelectorAll('[data-go]').forEach(control=>control.addEventListener('click',()=>showView(control.dataset.go)));
    ['friend-filter','account-filter','device-filter','global-search'].forEach(id=>$(id).addEventListener('input',()=>{if(data)render()}));['friend-status','account-status','device-status','activity-friend','activity-event'].forEach(id=>$(id).addEventListener('change',()=>{if(data)render()}));
    $('refresh').addEventListener('click',load);$('logout').addEventListener('click',()=>{sessionStorage.removeItem('lolxp_admin');location.reload()});$('close-modal').addEventListener('click',()=>$('credentials').close());$('copy-code').addEventListener('click',event=>copy('new-code',event.currentTarget));$('copy-invite').addEventListener('click',event=>copy('new-invite',event.currentTarget));
    if(token)load();
  })();
  </script>
</body>
</html>`;

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
