/* =========================================================
   Dùng chung cho trang CTV và Admin
   ========================================================= */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const LINK_RE = /⟦([^⟦⟧|]*)\|([^⟧]*)⟧/g;
const esc0 = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const esc = s => esc0(String(s ?? '').replace(LINK_RE, '$1'));
const pad = n => String(n).padStart(2, '0');
const ymd = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const ymOf = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
const parseDate = s => new Date(s + 'T00:00:00');
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const mondayOf = d => addDays(d, -((d.getDay() + 6) % 7));
const fmtDate = s => s ? `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}` : '';
const fmtDM = s => `${s.slice(8, 10)}/${s.slice(5, 7)}`;
const fmtYM = ym => `Tháng ${+ym.slice(5)}/${ym.slice(0, 4)}`;
const hm = dt => dt ? dt.slice(11, 16) : '—';
const t2m = t => { const [h, m] = t.split(':').map(Number); return h * 60 + m; };
const m2t = m => `${pad(Math.floor(m / 60))}:${pad(m % 60)}`;
const money = n => (Math.round(n || 0)).toLocaleString('vi-VN') + ' đ';
const DOW = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
const DOW_FULL = ['Chủ nhật', 'Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7'];
const dowOf = s => DOW[parseDate(s).getDay()];
const initials = name => (name || '?').trim().split(/\s+/).slice(-2).map(w => w[0]).join('').toUpperCase();
const hoursOf = s => (t2m(s.end) - t2m(s.start)) / 60;
const todayStr = () => ymd(new Date());

/* ---------- icon (nét kiểu Lucide) ---------- */
const ICONS = {
  home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  checkSquare: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="m9 12 2 2 4-4"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
  swap: '<path d="M7 16V4M3 8l4-4 4 4M17 8v12M21 16l-4 4-4-4"/>',
  message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  wallet: '<path d="M20 12V8H6a2 2 0 0 1 0-4h12v4"/><path d="M4 6v12a2 2 0 0 0 2 2h14v-4"/><path d="M18 12a2 2 0 0 0 0 4h4v-4z"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15z"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  key: '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6M15.5 7.5l3 3L22 7l-3-3"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  chevL: '<path d="m15 18-6-6 6-6"/>',
  chevR: '<path d="m9 18 6-6-6-6"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  alert: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1A1.7 1.7 0 0 0 9 19.4a1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
  megaphone: '<path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
};
const icon = n => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[n] || ''}</svg>`;

/* ---------- API ---------- */
let TOKEN_KEY = 'ctv_token';
const store = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} },
};

async function api(path, { method = 'GET', body, query } = {}) {
  let url = '/api' + path;
  if (query) url += '?' + new URLSearchParams(Object.entries(query).filter(([, v]) => v != null && v !== '')).toString();
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + (store.get(TOKEN_KEY) || '') },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && path !== '/login') { store.set(TOKEN_KEY, null); App.showLogin(); throw new Error('Phiên đăng nhập đã hết hạn'); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || 'Có lỗi xảy ra, vui lòng thử lại');
  return data;
}

/* ---------- toast ---------- */
function toast(msg, type = 'success') {
  let box = $('.toasts');
  if (!box) { box = document.createElement('div'); box.className = 'toasts'; document.body.appendChild(box); }
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.setAttribute('role', 'status');
  el.innerHTML = `${icon(type === 'error' ? 'alert' : type === 'info' ? 'info' : 'check')}<div>${esc(msg)}</div>`;
  box.appendChild(el);
  setTimeout(() => el.remove(), type === 'error' ? 5000 : 3000);
}

/* ---------- modal ---------- */
function modal({ title, body, footer = '', wide = false, onOpen }) {
  const ov = document.createElement('div');
  ov.className = 'overlay';
  ov.innerHTML = `<div class="modal ${wide ? 'wide' : ''}" role="dialog" aria-modal="true">
    <div class="modal-h"><h2>${title}</h2><button class="btn btn-ghost btn-icon" data-close aria-label="Đóng">${icon('x')}</button></div>
    <div class="modal-b">${body}</div>${footer ? `<div class="modal-f">${footer}</div>` : ''}</div>`;
  const close = () => { ov.remove(); document.removeEventListener('keydown', onKey); };
  const onKey = e => { if (e.key === 'Escape') close(); };
  ov.addEventListener('click', e => { if (e.target === ov || e.target.closest('[data-close]')) close(); });
  document.addEventListener('keydown', onKey);
  document.body.appendChild(ov);
  const first = ov.querySelector('input, select, textarea');
  if (first) first.focus();
  onOpen && onOpen(ov, close);
  return { el: ov, close };
}

function confirmDialog(title, message, okLabel = 'Xác nhận', danger = false) {
  return new Promise(resolve => {
    const m = modal({
      title, body: `<p class="muted">${esc(message)}</p>`,
      footer: `<button class="btn" data-close>Huỷ</button><button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" data-ok>${okLabel}</button>`,
    });
    let done = false;
    m.el.querySelector('[data-ok]').onclick = () => { done = true; m.close(); resolve(true); };
    new MutationObserver((_, obs) => { if (!document.body.contains(m.el)) { obs.disconnect(); if (!done) resolve(false); } })
      .observe(document.body, { childList: true });
  });
}

/* chạy action với trạng thái loading trên nút, tự hiện lỗi */
async function run(btn, fn) {
  const html = btn ? btn.innerHTML : '';
  if (btn) { btn.disabled = true; btn.textContent = 'Đang xử lý…'; }
  try { return await fn(); }
  catch (e) { toast(e.message, 'error'); }
  finally { if (btn && document.body.contains(btn)) { btn.disabled = false; btn.innerHTML = html; } }
}

/* ---------- tiện ích hiển thị ---------- */
const loading = (n = 4) => `<div class="card">${Array.from({ length: n }, (_, i) => `<div class="skel ${i % 2 ? 'w60' : ''}"></div>`).join('')}</div>`;
const emptyState = msg => `<div class="empty">${esc(msg)}</div>`;
const pageHead = (title, desc = '', actions = '') =>
  `<div class="page-head"><div><h1>${title}</h1>${desc ? `<p>${desc}</p>` : ''}</div>${actions ? `<div class="actions">${actions}</div>` : ''}</div>`;

function monthOptions(selected, from = -6, to = 2) {
  const now = new Date(); const out = [];
  for (let i = to; i >= from; i--) {
    const v = ymOf(new Date(now.getFullYear(), now.getMonth() + i, 1));
    out.push(`<option value="${v}" ${v === selected ? 'selected' : ''}>${fmtYM(v)}</option>`);
  }
  return out.join('');
}

function monthBounds(ym) {
  const [y, m] = ym.split('-').map(Number);
  return { start: `${ym}-01`, end: `${ym}-${pad(new Date(y, m, 0).getDate())}` };
}

/* Bảng có phân trang. columns: [{label, render(row), cls}] */
function dataTable(container, rows, columns, { pageSize = 20, empty = 'Chưa có dữ liệu' } = {}) {
  let page = 1;
  const pages = Math.max(1, Math.ceil(rows.length / pageSize));
  const paint = () => {
    if (!rows.length) { container.innerHTML = emptyState(empty); return; }
    const slice = rows.slice((page - 1) * pageSize, page * pageSize);
    container.innerHTML = `<div class="table-wrap"><table class="table">
      <thead><tr>${columns.map(c => `<th class="${c.cls || ''}">${c.label}</th>`).join('')}</tr></thead>
      <tbody>${slice.map(r => `<tr>${columns.map(c => `<td class="${c.cls || ''}">${c.render(r)}</td>`).join('')}</tr>`).join('')}</tbody>
    </table></div>
    ${pages > 1 ? `<div class="pager"><span>${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, rows.length)} / ${rows.length}</span>
      <span class="actions"><button class="btn btn-sm" data-p="-1" ${page === 1 ? 'disabled' : ''}>${icon('chevL')}</button>
      <button class="btn btn-sm" data-p="1" ${page === pages ? 'disabled' : ''}>${icon('chevR')}</button></span></div>` : ''}`;
  };
  container.onclick = e => { const b = e.target.closest('[data-p]'); if (b) { page += +b.dataset.p; paint(); } };
  paint();
}

/* Xuất CSV (Excel mở được, có BOM UTF-8) */
function downloadCSV(filename, header, data) {
  const cell = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const csv = '﻿' + [header, ...data].map(r => r.map(cell).join(',')).join('\r\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

/* trạng thái ca theo giờ (không check-in): sắp tới / đang trong ca / đã làm */
function shiftState(s) {
  if (s.approved_at) return { key: 'done', label: 'Đã chấm công', badge: 'green' };
  const today = todayStr();
  if (s.date > today) return { key: 'future', label: 'Sắp tới', badge: '' };
  if (s.date < today) return { key: 'done', label: 'Chờ duyệt', badge: 'amber' };
  const now = new Date(); const nowS = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
  const startAt = t2m(s.start) * 60, endAt = t2m(s.end) * 60;
  if (nowS < startAt) return { key: 'wait', label: 'Sắp tới', badge: '', secs: startAt - nowS };
  if (nowS < endAt) return { key: 'working', label: 'Đang trong ca', badge: 'blue', secs: endAt - nowS };
  return { key: 'done', label: 'Chờ duyệt', badge: 'amber' };
}
/* ca chính (Sáng / Chiều / Tối); ca phụ như "Tối gãy" thuộc nhóm ca chính cùng tiền tố mã */
const shiftGroup = code => { const f = String(code || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').toLowerCase(); for (const g of ['toi', 'chieu', 'sang']) if (f === g || new RegExp(`(^|[^a-z])${g}([^a-z]|$)`).test(f)) return g; return code; };
const mainShifts = () => { const m = App.meta.shifts.filter(s => shiftGroup(s.code) === s.code); return m.length ? m : App.meta.shifts; };
const shortShift = code => ((App.meta.shifts.find(s => s.code === code) || {}).name || code).replace(/^ca\s+/i, '').replace(/^./, c => c.toUpperCase());
/* so số CTV với chỉ tiêu của ca (need_min–need_max) */
function needInfo(n, sh, overOk = false) {
  const lo = +sh.need_min || 0, hi = Math.max(lo, +sh.need_max || 0);
  if (!lo) return { cls: '', text: `${n}`, target: '', missing: 0 };
  const target = hi > lo ? `${lo}–${hi}` : `${lo}`;
  return { cls: n < lo ? 'low' : n > hi && !overOk ? 'over' : 'ok', text: `${n}/${target}`, target, missing: Math.max(0, lo - n) };
}
/* admin đã sửa so với lịch xếp ban đầu → mô tả ngắn */
function planDiff(s) {
  if (!s.plan) return '';
  let p; try { p = JSON.parse(s.plan); } catch { return ''; }
  if (p.added) return 'Admin thêm ca';
  const out = [];
  if (p.start !== s.start || p.end !== s.end) out.push(`Giờ: ${p.start}–${p.end} → <b>${s.start}–${s.end}</b>`);
  if (p.position_id !== s.position_id) out.push(`Vị trí: ${esc(p.position || '—')} → <b>${esc(s.position || '—')}</b>`);
  if (p.user_id !== s.user_id) out.push(`PIC: ${esc(p.username || '')} → <b>${esc(s.username)}</b>`);
  return out.join('<br>');
}
const attStatus = s => { const st = shiftState(s); return `<span class="badge ${st.badge}">${st.label}</span>`; };

/* =========================================================
   Khung ứng dụng: đăng nhập, sidebar, định tuyến
   ========================================================= */
const App = {
  user: null, meta: null, config: null, cleanup: [],

  start(config) {
    this.config = config;
    TOKEN_KEY = 'ctv_token_' + config.role;
    let theme = store.get('ctv_theme');
    if (!theme) theme = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    document.documentElement.dataset.theme = theme;
    addEventListener('hashchange', () => this.route());
    addEventListener('offline', () => { if (!$('.offline')) document.body.insertAdjacentHTML('afterbegin', '<div class="offline">Mất kết nối mạng</div>'); });
    addEventListener('online', () => $('.offline')?.remove());
    if (store.get(TOKEN_KEY)) {
      api('/me').then(u => this.enter(u)).catch(() => this.showLogin());
    } else this.showLogin();
  },

  showLogin() {
    const c = this.config;
    document.body.innerHTML = `<div class="login"><form class="login-card card card-pad" id="login-form">
      <div class="brand"><div class="brand-mark">C</div><div>${c.brand}<small>${c.subtitle}</small></div></div>
      <h1>Đăng nhập</h1><p>${c.loginHint}</p>
      <div class="field"><label for="lg-u">Tên đăng nhập</label><input class="input" id="lg-u" autocomplete="username" required></div>
      <div class="field"><label for="lg-p">Mật khẩu</label><input class="input" id="lg-p" type="password" autocomplete="current-password" required></div>
      <button class="btn btn-primary btn-block btn-lg">Đăng nhập</button>
    </form></div>`;
    $('#lg-u').focus();
    $('#login-form').onsubmit = e => {
      e.preventDefault();
      run(e.submitter, async () => {
        const r = await api('/login', { method: 'POST', body: { username: $('#lg-u').value, password: $('#lg-p').value } });
        if (c.role === 'admin' && r.user.role !== 'admin') throw new Error('Tài khoản này không có quyền quản trị');
        store.set(TOKEN_KEY, r.token);
        this.enter(r.user);
      });
    };
  },

  async enter(user) {
    if (this.config.role === 'admin' && user.role !== 'admin') { store.set(TOKEN_KEY, null); return this.showLogin(); }
    this.user = user;
    this.meta = await api('/meta');
    const c = this.config;
    document.body.innerHTML = `<div class="shell">
      <aside class="sidebar" id="sidebar">
        <div class="brand"><div class="brand-mark">C</div><div>${c.brand}<small>${c.subtitle}</small></div></div>
        <nav class="nav" id="nav">${c.nav.map(g => `<div class="nav-group">${g.group}</div>` +
          g.items.map(i => `<a href="#${i.id}" data-id="${i.id}">${icon(i.icon)}<span>${i.label}</span><span class="count" data-count="${i.id}" hidden></span></a>`).join('')).join('')}</nav>
        ${user.role === 'admin' ? `<a class="switch-portal" id="switch-portal" href="/${c.role === 'admin' ? 'ctv' : 'admin'}">${icon(c.role === 'admin' ? 'users' : 'grid')}<span>${c.role === 'admin' ? 'Xem trang CTV' : 'Sang trang Quản trị'}</span>${icon('chevR')}</a>` : ''}
        <div class="user-box">
          <button class="user-btn" id="user-btn" aria-haspopup="true"><div class="avatar">${initials(user.name)}</div>
            <div><strong>${esc(user.name)}</strong><span>${esc(user.username)}</span></div></button>
          <div class="menu" id="user-menu" hidden>
            <button id="m-notif">${icon('bell')} Thông báo <span class="badge accent" id="notif-count" hidden></span></button>
            <button id="m-theme">${icon('moon')} Đổi giao diện sáng/tối</button>
            <button id="m-pass">${icon('key')} Đổi mật khẩu</button>
            <button id="m-out" class="danger">${icon('logout')} Đăng xuất</button>
          </div>
        </div>
      </aside>
      <div class="main">
        <div class="topbar"><button class="btn btn-ghost btn-icon" id="open-nav" aria-label="Mở menu">${icon('menu')}</button>${c.brand}</div>
        <main class="content" id="view"></main>
      </div></div>`;

    // tài khoản admin: chuyển qua lại 2 trang mà không phải đăng nhập lại
    $('#switch-portal')?.addEventListener('click', () => store.set('ctv_token_' + (c.role === 'admin' ? 'ctv' : 'admin'), store.get(TOKEN_KEY)));
    const menu = $('#user-menu');
    $('#user-btn').onclick = e => { e.stopPropagation(); menu.hidden = !menu.hidden; };
    document.addEventListener('click', e => { if (!e.target.closest('.user-box')) menu.hidden = true; });
    $('#m-theme').onclick = () => {
      const t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = t; store.set('ctv_theme', t);
    };
    $('#m-pass').onclick = () => { menu.hidden = true; changePasswordDialog(); };
    $('#m-notif').onclick = () => { menu.hidden = true; notificationsDialog(); };
    $('#m-out').onclick = async () => {
      menu.hidden = true;
      if (!(await confirmDialog('Đăng xuất?', 'Bạn sẽ cần đăng nhập lại để tiếp tục.', 'Đăng xuất'))) return;
      await api('/logout', { method: 'POST' }).catch(() => {});
      store.set(TOKEN_KEY, null); location.hash = ''; this.showLogin();
    };
    $('#open-nav').onclick = () => this.toggleNav(true);
    this.refreshNotifCount();
    this.route();
    if (user.must_change_pw) changePasswordDialog(true);
  },

  toggleNav(open) {
    $('#sidebar').classList.toggle('open', open);
    $('.scrim')?.remove();
    if (open) {
      const s = document.createElement('div'); s.className = 'scrim'; s.onclick = () => this.toggleNav(false);
      document.body.appendChild(s);
    }
  },

  setCount(id, n) { const el = $(`[data-count="${id}"]`); if (el) { el.hidden = !n; el.textContent = n; } },

  async refreshNotifCount() {
    const list = await api('/notifications').catch(() => []);
    const n = list.filter(x => x.unread).length;
    const el = $('#notif-count'); if (el) { el.hidden = !n; el.textContent = n; }
  },

  route() {
    if (!this.user || !$('#view')) return;
    this.cleanup.forEach(fn => fn()); this.cleanup = [];
    const items = this.config.nav.flatMap(g => g.items);
    const item = items.find(i => i.id === location.hash.slice(1)) || items[0];
    $$('#nav a').forEach(a => a.classList.toggle('active', a.dataset.id === item.id));
    this.toggleNav(false);
    const v = $('#view');
    v.innerHTML = '';
    window.scrollTo(0, 0);
    document.title = `${item.label} · ${this.config.brand}`;
    Promise.resolve(item.render(v)).catch(e => { v.innerHTML = pageHead(item.label) + `<div class="card">${emptyState(e.message)}</div>`; });
  },

  onLeave(fn) { this.cleanup.push(fn); },
};

function changePasswordDialog(forced = false) {
  let unblock = () => {};
  modal({
    title: forced ? 'Đổi mật khẩu trước khi bắt đầu' : 'Đổi mật khẩu',
    body: `${forced ? '<p class="muted" style="margin-bottom:12px">Bạn đang dùng mật khẩu mặc định. Vì lý do bảo mật, vui lòng đặt mật khẩu mới để tiếp tục.</p>' : ''}<form id="pw-form">
      <div class="field"><label>Mật khẩu hiện tại</label><input class="input" type="password" name="old" required autocomplete="current-password"></div>
      <div class="field"><label>Mật khẩu mới</label><input class="input" type="password" name="new" required minlength="6" autocomplete="new-password"><span class="hint">Tối thiểu 6 ký tự</span></div>
      <div class="field"><label>Nhập lại mật khẩu mới</label><input class="input" type="password" name="again" required autocomplete="new-password"></div>
      <button class="btn btn-primary btn-block">Lưu mật khẩu</button></form>`,
    onOpen(el, close) {
      if (forced) {  // không cho đóng hộp thoại khi chưa đổi
        el.querySelector('[data-close]')?.remove();
        const stopClick = e => { if (e.target === el) e.stopImmediatePropagation(); };
        const stopKey = e => { if (e.key === 'Escape') e.stopImmediatePropagation(); };
        el.addEventListener('click', stopClick, true);
        document.addEventListener('keydown', stopKey, true);
        unblock = () => document.removeEventListener('keydown', stopKey, true);
      }
      $('#pw-form', el).onsubmit = e => {
        e.preventDefault(); const f = e.target;
        if (f.new.value !== f.again.value) return toast('Mật khẩu nhập lại không khớp', 'error');
        run(e.submitter, async () => {
          await api('/me/password', { method: 'POST', body: { old: f.old.value, new: f.new.value } });
          unblock(); if (App.user) App.user.must_change_pw = 0;
          close(); toast('Đã đổi mật khẩu');
        });
      };
    },
  });
}

async function notificationsDialog() {
  const list = await api('/notifications');
  modal({
    title: 'Thông báo',
    body: list.length ? list.map(n => `<div style="padding:12px 0;border-bottom:1px solid var(--border)">
      <div style="display:flex;gap:8px;align-items:center"><strong>${esc(n.title)}</strong>${n.unread ? '<span class="badge accent">Mới</span>' : ''}</div>
      ${n.body ? `<div class="muted" style="margin-top:2px">${esc(n.body)}</div>` : ''}
      <div class="small muted" style="margin-top:4px">${fmtDate(n.created_at.slice(0, 10))} ${n.created_at.slice(11, 16)}</div></div>`).join('') : emptyState('Chưa có thông báo'),
  });
  await api('/notifications/read', { method: 'POST' });
  App.refreshNotifCount();
}

/* biểu đồ cột đơn giản */
function barChart(data) {
  if (!data.length) return emptyState('Chưa có dữ liệu');
  const max = Math.max(...data.map(d => d.value), 1);
  return `<div class="bars">${data.map(d => `<div class="bar"><span class="v">${d.value}</span>
    <div class="fill" style="height:${Math.max(2, d.value / max * 130)}px"></div><span class="l">${esc(d.label)}</span></div>`).join('')}</div>`;
}

/* biểu đồ tròn đơn giản (SVG) */
function donut(parts) {
  const total = parts.reduce((s, p) => s + p.value, 0);
  const r = 46, c = 2 * Math.PI * r; let off = 0;
  const arcs = total ? parts.map(p => {
    const len = p.value / total * c;
    const a = `<circle r="${r}" cx="60" cy="60" fill="none" stroke="${p.color}" stroke-width="16" stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-off}"/>`;
    off += len; return a;
  }).join('') : `<circle r="${r}" cx="60" cy="60" fill="none" stroke="var(--surface-2)" stroke-width="16"/>`;
  return `<div class="donut-wrap"><svg viewBox="0 0 120 120" style="width:140px;height:140px;transform:rotate(-90deg)">${arcs}</svg>
    <div class="donut-legend">${parts.map(p => `<div><i style="background:${p.color}"></i>${p.label}: <b>${p.value}</b></div>`).join('')}</div></div>`;
}
