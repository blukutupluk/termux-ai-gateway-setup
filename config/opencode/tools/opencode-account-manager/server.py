import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8787"))
# Dinamis: Windows -> C:\Users\<USERNAME>\.local\share\opencode\opencode.db
# Termux/Android -> ~/.local/share/opencode/opencode.db
# Bisa ditimpa lewat env OPENCODE_DB_PATH bila lokasi DB berbeda.
DB_PATH = os.environ.get("OPENCODE_DB_PATH") or os.path.join(
    os.path.expanduser("~"), ".local", "share", "opencode", "opencode.db"
)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data.json")
DATA_LOCK = threading.Lock()


def _default_data():
    return {"accounts": {}, "general_note": "", "updated_at": None}


def load_data():
    with DATA_LOCK:
        if not os.path.exists(DATA_PATH):
            return _default_data()
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return _default_data()
            data.setdefault("accounts", {})
            data.setdefault("general_note", "")
            data.setdefault("updated_at", None)
            if not isinstance(data.get("accounts"), dict):
                data["accounts"] = {}
            return data
        except Exception:
            return _default_data()


def save_data(data):
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    with DATA_LOCK:
        tmp = DATA_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_PATH)
    return data


def _redact(text):
    """Jangan pernah kirim token/api key/password ke UI atau log."""
    if not text:
        return ""
    text = re.sub(
        r"(?i)(api[_-]?key|token|password|secret)(\s*[:=]\s*)(\S+)",
        r"\1\2[disembunyikan]",
        text,
    )
    text = re.sub(r"\bsk-[A-Za-z0-9_\-]{8,}\b", "sk-[disembunyikan]", text)
    return text


def get_accounts():
    if not os.path.exists(DB_PATH):
        return []
    con = sqlite3.connect("file:" + DB_PATH.replace("?", "%3f") + "?mode=ro", uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    rows = cur.execute(
        """
        SELECT id, integration_id, label, active, value, time_created, time_updated
        FROM credential
        ORDER BY integration_id ASC, active DESC, time_updated DESC
        """
    ).fetchall()
    accounts = []
    for r in rows:
        meta = {}
        email = None
        org_name = None
        ctype = None
        try:
            j = json.loads(r["value"] or "{}")
            meta = j.get("metadata") or {}
            email = meta.get("email")
            org_name = meta.get("orgName")
            ctype = j.get("type")
        except Exception:
            pass
        accounts.append(
            {
                "id": r["id"],
                "integration_id": r["integration_id"],
                "label": r["label"],
                "active": bool(r["active"]),
                "email": email,
                "orgName": org_name,
                "type": ctype,
                "time_updated": r["time_updated"],
            }
        )
    con.close()
    return accounts


def _integration_for(credential_id):
    try:
        if not os.path.exists(DB_PATH):
            return "opencode"
        con = sqlite3.connect("file:" + DB_PATH.replace("?", "%3f") + "?mode=ro", uri=True, timeout=10)
        row = con.execute("SELECT integration_id FROM credential WHERE id = ?", (credential_id,)).fetchone()
        con.close()
        return (row[0] if row and row[0] else "opencode")
    except Exception:
        return "opencode"


def switch_account(credential_id):
    target = _integration_for(credential_id)
    try:
        proc = subprocess.run(
            ["opencode", "auth", "switch", target, credential_id],
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,
        )
        ok = proc.returncode == 0
        msg = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        return ok, _redact(msg.strip() or ("Berhasil" if ok else "Gagal"))
    except Exception as e:
        return False, _redact(str(e))


INDEX_HTML = r"""<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OpenCode Account Manager</title>
  <style>
    :root {
      --bg: #0b1020;
      --card: #141c3a;
      --card2: #182246;
      --text: #e8ecff;
      --muted: #9aa7d6;
      --accent: #6ee7ff;
      --accent2: #8b5cf6;
      --green: #34d399;
      --yellow: #fbbf24;
      --red: #f87171;
      --border: rgba(255,255,255,0.08);
      --shadow: 0 10px 30px rgba(0,0,0,0.35);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(1200px 600px at 10% -10%, rgba(139,92,246,0.25), transparent 60%),
        radial-gradient(900px 500px at 110% 0%, rgba(110,231,255,0.18), transparent 55%),
        linear-gradient(180deg, var(--bg), #090d1a 60%, #070a14);
      min-height: 100vh;
    }
    .wrap { max-width: 1140px; margin: 0 auto; padding: 32px 20px 48px; }
    header { display: flex; align-items: center; gap: 16px; margin-bottom: 22px; }
    .logo {
      width: 52px; height: 52px; border-radius: 14px;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      display: grid; place-items: center; font-weight: 800; color: #081018; font-size: 22px;
      box-shadow: 0 8px 24px rgba(110,231,255,0.25);
    }
    h1 { font-size: 1.6rem; margin: 0 0 4px; letter-spacing: 0.2px; }
    h2 { font-size: 1.1rem; margin: 0 0 6px; }
    .sub { color: var(--muted); margin: 0; }
    .bar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin: 18px 0 14px; flex-wrap: wrap; }
    .pill { font-size: 13px; color: var(--muted); background: rgba(255,255,255,0.04); border: 1px solid var(--border); padding: 8px 12px; border-radius: 999px; }
    button, select, textarea, input { font: inherit; }
    button {
      appearance: none; border: 1px solid var(--border); color: var(--text); background: var(--card2);
      padding: 9px 13px; border-radius: 10px; cursor: pointer; font-weight: 600;
    }
    button:hover { border-color: rgba(110,231,255,0.35); }
    button.primary { background: linear-gradient(135deg, rgba(110,231,255,0.18), rgba(139,92,246,0.18)); border-color: rgba(110,231,255,0.35); }
    button.small { padding: 7px 10px; font-size: 13px; }
    button.tiny { padding: 5px 8px; font-size: 12px; border-radius: 8px; }
    button[disabled] { opacity: 0.55; cursor: default; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }
    .card, .panel {
      background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)), var(--card);
      border: 1px solid var(--border); border-radius: 16px; padding: 16px; box-shadow: var(--shadow);
    }
    .card.active { border-color: rgba(52,211,153,0.45); box-shadow: 0 0 0 1px rgba(52,211,153,0.15) inset, var(--shadow); }
    .card.st-habis { border-color: rgba(248,113,113,0.45); }
    .card.st-hampir_habis { border-color: rgba(251,191,36,0.4); }
    .card.st-tersedia { border-color: rgba(52,211,153,0.28); }
    .badge { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 999px; }
    .badge.on { color: #052e1a; background: var(--green); }
    .badge.off { color: var(--muted); background: rgba(255,255,255,0.06); border: 1px solid var(--border); }
    .qbadge { font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 999px; border: 1px solid var(--border); }
    .q-tersedia { color: #d1fae5; background: rgba(52,211,153,0.12); border-color: rgba(52,211,153,0.3); }
    .q-hampir_habis { color: #fef3c7; background: rgba(251,191,36,0.12); border-color: rgba(251,191,36,0.3); }
    .q-habis { color: #fee2e2; background: rgba(248,113,113,0.12); border-color: rgba(248,113,113,0.35); }
    .q-tidak_diketahui { color: var(--muted); background: rgba(255,255,255,0.04); }
    .name { font-size: 1.05rem; font-weight: 700; margin: 10px 0 4px; word-break: break-all; }
    .email { color: var(--muted); font-size: 0.92rem; min-height: 1.2em; word-break: break-all; }
    .meta { color: #7f8bb8; font-size: 12px; margin-top: 8px; }
    .row { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
    .msg { margin-top: 14px; padding: 12px 14px; border-radius: 12px; border: 1px solid var(--border); background: rgba(255,255,255,0.03); color: var(--muted); }
    .msg.ok { color: #c8ffec; border-color: rgba(52,211,153,0.35); }
    .msg.err { color: #ffd7d7; border-color: rgba(248,113,113,0.35); }
    .empty { color: var(--muted); padding: 30px; text-align: center; border: 1px dashed var(--border); border-radius: 14px; }
    .panel { margin-top: 18px; }
    label { display:block; font-size: 12px; color: var(--muted); margin: 10px 0 6px; }
    select, textarea, input[type="text"] {
      width: 100%; background: #0f1730; color: var(--text); border: 1px solid var(--border);
      border-radius: 10px; padding: 9px 10px;
    }
    textarea { min-height: 90px; resize: vertical; line-height: 1.45; }
    textarea.big { min-height: 220px; }
    .status-dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; vertical-align:middle; }
    .s-tersedia { background: var(--green); }
    .s-hampir_habis { background: var(--yellow); }
    .s-habis { background: var(--red); }
    .s-tidak_diketahui { background: #64748b; }
    .hint { font-size: 12px; color: #7f8bb8; margin-top: 8px; }
    .save-state { font-size: 12px; color: #7f8bb8; }
    .save-state.ok { color: #86efac; }
    .save-state.busy { color: #fde68a; }
    .save-state.err { color: #fca5a5; }
    .tools { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
    .copyrow { display:flex; gap:6px; margin-top:8px; flex-wrap:wrap; }
    footer { margin-top: 22px; color: #7f8bb8; font-size: 12px; }
    code { background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 6px; }
    input[type=file] { display:none; }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="logo">OC</div>
      <div>
        <h1>OpenCode Account Manager</h1>
        <p class="sub">Lihat & ganti akun aktif OpenCode Console · memo/catatan · status kuota free (manual) · backup</p>
      </div>
    </header>


    <div class="bar">
      <div class="pill" id="summary">Memuat akun…</div>
      <div class="tools">
        <select id="filterIntegration" style="width:auto; padding:8px 10px;">
          <option value="all">Semua integrasi</option>
        </select>
        <select id="filterStatus" style="width:auto; padding:8px 10px;">
          <option value="all">Semua status kuota</option>
          <option value="tersedia">Tersedia</option>
          <option value="hampir_habis">Hampir habis</option>
          <option value="habis">Habis</option>
          <option value="tidak_diketahui">Tidak diketahui</option>
        </select>
        <button id="refresh">Muat ulang</button>
      </div>
    </div>


    <div id="msg"></div>
    <div id="grid" class="grid" style="margin-top:12px;"></div>


    <div class="panel">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">
        <h2 style="margin:0;">Memo / Catatan Umum</h2>
        <span id="generalSaveState" class="save-state">Memuat…</span>
      </div>
      <p class="hint" style="margin-top:6px;">Tulis apa saja di sini. Catatan <b>otomatis tersimpan</b> ke file lokal dan tetap ada saat dibuka kembali di sesi berikutnya.</p>
      <textarea id="generalNote" class="big" placeholder="Tulis memo/catatan kamu di sini... (tersimpan otomatis)"></textarea>
      <div class="row" style="justify-content:space-between; margin-top:10px;">
        <div class="hint" style="margin:0;">Lokasi penyimpanan: <code>data.json</code></div>
        <div class="tools">
          <button class="small" id="exportBtn">Ekspor backup</button>
          <button class="small" id="importBtn">Impor backup</button>
          <input type="file" id="importFile" accept="application/json,.json">
          <button class="primary small" id="saveGeneral">Simpan sekarang</button>
        </div>
      </div>
    </div>


    <footer>Server lokal membaca akun dari <code>opencode.db</code>, mengganti akun via <code>opencode auth switch</code>, dan menyimpan memo/catatan/status ke <code>data.json</code>. Status kuota free bersifat manual.</footer>
  </div>


<script>
let accountMeta = {};
let generalNote = '';
let allAccounts = [];
const saveTimers = {};
let generalTimer = null;


async function api(path, opts={}) {
  const r = await fetch(path, Object.assign({headers: {'Content-Type':'application/json'}}, opts));
  const t = await r.text();
  let j; try { j = JSON.parse(t); } catch(e) { j = {raw:t}; }
  if (!r.ok) throw j;
  return j;
}
function esc(s){ return (s==null?'':String(s)).replace(/[&<>"']/g, c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c])); }
function showMsg(text, ok=true){
  const el = document.getElementById('msg');
  if(!text){ el.innerHTML=''; return; }
  el.innerHTML = `<div class="msg ${ok?'ok':'err'}">${esc(text)}</div>`;
}
function setSaveState(id, text, cls){
  const el = document.getElementById(id);
  if(!el) return;
  el.textContent = text;
  el.className = 'save-state ' + (cls||'');
}
function statusLabel(s){
  return ({tersedia:'Tersedia', hampir_habis:'Hampir habis', habis:'Habis', tidak_diketahui:'Tidak diketahui'})[s] || 'Tidak diketahui';
}
function nowStr(){ return new Date().toLocaleString(); }


function populateIntegrationFilter(){
  const sel = document.getElementById('filterIntegration');
  const cur = sel.value || 'all';
  const ints = [...new Set(allAccounts.map(a=>a.integration_id || 'opencode'))].sort();
  sel.innerHTML = '<option value="all">Semua integrasi</option>' + ints.map(i=>`<option value="${esc(i)}">${esc(i)}</option>`).join('');
  sel.value = ints.includes(cur) ? cur : 'all';
}
function render(){
  const grid = document.getElementById('grid');
  const intFilter = document.getElementById('filterIntegration').value || 'all';
  const filter = document.getElementById('filterStatus').value;
  const accs = allAccounts.filter(a => {
    const st = (accountMeta[a.id] || {}).free_status || 'tidak_diketahui';
    const okInt = intFilter === 'all' ? true : (a.integration_id || 'opencode') === intFilter;
    const okSt = filter === 'all' ? true : st === filter;
    return okInt && okSt;
  });
  const active = allAccounts.find(a=>a.active);
  document.getElementById('summary').textContent = `${allAccounts.length} akun (${[...new Set(allAccounts.map(a=>a.integration_id||'opencode'))].length} integrasi)` + (active ? ` · aktif: ${active.label} [${active.integration_id||'opencode'}]` : ' · tidak ada yang aktif') + (intFilter!=='all' ? ` · integrasi: ${intFilter}` : '') + (filter!=='all' ? ` · kuota: ${statusLabel(filter)}` : '');
  if(!accs.length){ grid.innerHTML = '<div class="empty">Tidak ada akun untuk filter ini.</div>'; return; }
  grid.innerHTML = accs.map(a => {
    const m = accountMeta[a.id] || {};
    const st = m.free_status || 'tidak_diketahui';
    const note = m.note || '';
    const checked = m.last_checked || '';
    const email = a.email || '';
    return `
    <div class="card ${a.active?'active':''} st-${esc(st)}" data-id="${esc(a.id)}">
      <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap;">
        <span class="badge ${a.active?'on':'off'}">${a.active?'● Aktif':'○ Tidak aktif'}</span>
        <span class="badge off" style="font-size:11px;">${esc(a.integration_id || 'opencode')}</span>
        <span class="qbadge q-${esc(st)}"><span class="status-dot s-${esc(st)}"></span>${esc(statusLabel(st))}</span>
      </div>
      <div class="name">${esc(a.label || '(tanpa nama)')}</div>
      <div class="email">${esc(email || (a.type==='key' ? 'Kredensial API key (tanpa email)' : ''))}</div>
      <div class="meta">Tipe: ${esc(a.type || '-')} ${a.orgName ? '· Org: '+esc(a.orgName) : ''}</div>
      <div class="copyrow">
        ${email ? `<button class="tiny" onclick="copyText('${esc(email)}','Email disalin')">Salin email</button>` : ''}
        <button class="tiny" onclick="copyText('${esc(a.id)}','ID disalin')">Salin ID</button>
      </div>
      <div class="row">
        <div class="meta" style="margin:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:55%;" title="${esc(a.id)}">${esc(a.id)}</div>
        <button class="primary small" ${a.active?'disabled':''} onclick="activate('${esc(a.id)}','${esc(a.label||a.id)}', this)">Jadikan aktif</button>
      </div>
      <label>Status kuota free (manual)</label>
      <select id="st-${esc(a.id)}" onchange="queueSaveMeta('${esc(a.id)}')">
        <option value="tidak_diketahui" ${st==='tidak_diketahui'?'selected':''}>Tidak diketahui</option>
        <option value="tersedia" ${st==='tersedia'?'selected':''}>Tersedia</option>
        <option value="hampir_habis" ${st==='hampir_habis'?'selected':''}>Hampir habis</option>
        <option value="habis" ${st==='habis'?'selected':''}>Habis</option>
      </select>
      <label>Catatan / memo akun</label>
      <textarea id="note-${esc(a.id)}" placeholder="Tulis catatan untuk akun ini... (tersimpan otomatis)" oninput="queueSaveMeta('${esc(a.id)}')">${esc(note)}</textarea>
      <div class="row" style="margin-top:10px;">
        <div class="meta" style="margin:0;">Dicek: <span id="checked-${esc(a.id)}">${esc(checked || '-')}</span></div>
        <span id="savestate-${esc(a.id)}" class="save-state ok">Tersimpan</span>
      </div>
    </div>`;
  }).join('');
}


async function load(){
  showMsg('');
  const grid = document.getElementById('grid');
  grid.innerHTML = '<div class="empty">Memuat…</div>';
  try {
    const data = await api('/api/state');
    allAccounts = data.accounts || [];
    accountMeta = data.meta || {};
    generalNote = data.general_note || '';
    const g = document.getElementById('generalNote');
    if (document.activeElement !== g) g.value = generalNote;
    setSaveState('generalSaveState', 'Tersimpan', 'ok');
    populateIntegrationFilter();
    render();
  } catch(e){
    grid.innerHTML = '<div class="empty">Gagal memuat akun.</div>';
    setSaveState('generalSaveState', 'Gagal memuat', 'err');
    showMsg((e && e.error) || 'Gagal memuat data.', false);
  }
}
async function activate(id, label, btn){
  if(!confirm(`Jadikan akun "${label}" sebagai akun aktif?`)) return;
  btn.disabled = true; btn.textContent = 'Memproses…';
  try {
    const res = await api('/api/switch', {method:'POST', body: JSON.stringify({id})});
    showMsg(res.message || 'Akun berhasil diganti.', true);
    await load();
  } catch(e){
    showMsg((e && (e.message||e.error)) || 'Gagal mengganti akun.', false);
    btn.disabled = false; btn.textContent = 'Jadikan aktif';
  }
}
async function copyText(text, okMsg){
  try { await navigator.clipboard.writeText(text); showMsg(okMsg || 'Disalin.', true); }
  catch(e){ showMsg('Gagal menyalin ke clipboard.', false); }
}
function queueSaveMeta(id){
  setSaveState('savestate-'+id, 'Menyimpan…', 'busy');
  if (saveTimers[id]) clearTimeout(saveTimers[id]);
  saveTimers[id] = setTimeout(()=>saveMeta(id), 800);
}
async function saveMeta(id){
  try {
    const status = document.getElementById('st-'+id).value;
    const note = document.getElementById('note-'+id).value;
    const last_checked = new Date().toISOString().slice(0,19).replace('T',' ');
    await api('/api/account-meta', {method:'POST', body: JSON.stringify({id, free_status: status, note, last_checked})});
    accountMeta[id] = {free_status: status, note, last_checked};
    const ch = document.getElementById('checked-'+id);
    if (ch) ch.textContent = last_checked;
    setSaveState('savestate-'+id, 'Tersimpan', 'ok');
    render();
  } catch(e){
    setSaveState('savestate-'+id, 'Gagal simpan', 'err');
    showMsg((e && (e.message||e.error)) || 'Gagal menyimpan catatan akun.', false);
  }
}
function queueSaveGeneral(){
  setSaveState('generalSaveState', 'Menyimpan…', 'busy');
  if (generalTimer) clearTimeout(generalTimer);
  generalTimer = setTimeout(saveGeneral, 800);
}
async function saveGeneral(){
  try {
    const note = document.getElementById('generalNote').value;
    await api('/api/general-note', {method:'POST', body: JSON.stringify({note})});
    setSaveState('generalSaveState', 'Tersimpan (' + nowStr() + ')', 'ok');
  } catch(e){
    setSaveState('generalSaveState', 'Gagal simpan', 'err');
    showMsg((e && (e.message||e.error)) || 'Gagal menyimpan catatan umum.', false);
  }
}
async function exportData(){
  try {
    const data = await api('/api/export');
    const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'opencode-account-manager-backup.json';
    a.click();
    URL.revokeObjectURL(a.href);
    showMsg('Backup berhasil diekspor.', true);
  } catch(e){ showMsg('Gagal ekspor backup.', false); }
}
async function importData(file){
  try {
    const text = await file.text();
    const data = JSON.parse(text);
    if(!confirm('Impor backup ini? Data memo/status yang ada akan digabung/ditimpa sesuai isi backup.')) return;
    await api('/api/import', {method:'POST', body: JSON.stringify(data)});
    showMsg('Backup berhasil diimpor.', true);
    await load();
  } catch(e){ showMsg((e && (e.message||e.error)) || 'Gagal impor backup. Pastikan file JSON valid.', false); }
}
document.getElementById('refresh').addEventListener('click', load);
document.getElementById('filterIntegration').addEventListener('change', render);
document.getElementById('filterStatus').addEventListener('change', render);
document.getElementById('saveGeneral').addEventListener('click', saveGeneral);
document.getElementById('generalNote').addEventListener('input', queueSaveGeneral);
document.getElementById('exportBtn').addEventListener('click', exportData);
document.getElementById('importBtn').addEventListener('click', ()=>document.getElementById('importFile').click());
document.getElementById('importFile').addEventListener('change', (e)=>{ if(e.target.files[0]) importData(e.target.files[0]); e.target.value=''; });
load();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, (bytes, bytearray)) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            return self._send(200, INDEX_HTML, "text/html; charset=utf-8")
        if parsed.path == "/api/accounts":
            try:
                accounts = get_accounts()
                return self._send(200, json.dumps({"accounts": accounts}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": _redact(str(e))}, ensure_ascii=False))
        if parsed.path == "/api/state":
            try:
                accounts = get_accounts()
                data = load_data()
                return self._send(200, json.dumps({
                    "accounts": accounts,
                    "meta": data.get("accounts", {}),
                    "general_note": data.get("general_note", ""),
                    "updated_at": data.get("updated_at"),
                }, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": _redact(str(e))}, ensure_ascii=False))
        if parsed.path == "/api/export":
            try:
                data = load_data()
                return self._send(200, json.dumps(data, ensure_ascii=False, indent=2))
            except Exception as e:
                return self._send(500, json.dumps({"error": _redact(str(e))}, ensure_ascii=False))
        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/api/switch":
                cred_id = payload.get("id")
                if not cred_id:
                    return self._send(400, json.dumps({"error": "missing id"}))
                ok, msg = switch_account(cred_id)
                code = 200 if ok else 500
                return self._send(code, json.dumps({"ok": ok, "message": msg}, ensure_ascii=False))

            if parsed.path == "/api/account-meta":
                cred_id = payload.get("id")
                if not cred_id:
                    return self._send(400, json.dumps({"error": "missing id"}))
                status = payload.get("free_status") or "tidak_diketahui"
                if status not in ("tersedia", "hampir_habis", "habis", "tidak_diketahui"):
                    status = "tidak_diketahui"
                note = payload.get("note") or ""
                last_checked = payload.get("last_checked") or ""
                data = load_data()
                data.setdefault("accounts", {})[cred_id] = {
                    "free_status": status,
                    "note": note,
                    "last_checked": last_checked,
                }
                save_data(data)
                return self._send(200, json.dumps({"ok": True}))

            if parsed.path == "/api/general-note":
                note = payload.get("note") or ""
                data = load_data()
                data["general_note"] = note
                save_data(data)
                return self._send(200, json.dumps({"ok": True, "updated_at": data.get("updated_at")}))

            if parsed.path == "/api/import":
                if not isinstance(payload, dict):
                    return self._send(400, json.dumps({"error": "invalid backup format"}))
                data = load_data()
                incoming_accounts = payload.get("accounts")
                if isinstance(incoming_accounts, dict):
                    for k, v in incoming_accounts.items():
                        if isinstance(v, dict):
                            status = v.get("free_status") or "tidak_diketahui"
                            if status not in ("tersedia", "hampir_habis", "habis", "tidak_diketahui"):
                                status = "tidak_diketahui"
                            data.setdefault("accounts", {})[k] = {
                                "free_status": status,
                                "note": v.get("note") or "",
                                "last_checked": v.get("last_checked") or "",
                            }
                if "general_note" in payload and isinstance(payload.get("general_note"), str):
                    data["general_note"] = payload.get("general_note") or ""
                save_data(data)
                return self._send(200, json.dumps({"ok": True}))
        except Exception as e:
            return self._send(500, json.dumps({"error": _redact(str(e))}, ensure_ascii=False))
        return self._send(404, json.dumps({"error": "not found"}))


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"OpenCode Account Manager running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
