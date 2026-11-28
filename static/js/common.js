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
  target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
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
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
  mail: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  chevL: '<path d="m15 18-6-6 6-6"/>',
  chevR: '<path d="m9 18 6-6-6-6"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  alert: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1A1.7 1.7 0 0 0 9 19.4a1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
  megaphone: '<path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
  video: '<rect x="2" y="5" width="14" height="14" rx="2"/><path d="m16 10 6-3v10l-6-3"/>',
  play: '<path d="M7 4v16l13-8z"/>',
  file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>',
  external: '<path d="M14 4h6v6"/><path d="M20 4 10 14"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
};
const icon = n => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[n] || ''}</svg>`;

/* ---------- API ---------- */
let TOKEN_KEY = 'ctv_token';
const STAFF_ROLES = ['admin', 'subadmin'];
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
/* ca chính + các ca phụ cùng nhóm (VD Tối: Ca full 18–22 và Ca gãy 19–22), ca chính đứng đầu */
const shiftVariants = main => App.meta.shifts.filter(s => shiftGroup(s.code) === main.code).sort((a, b) => (b.code === main.code) - (a.code === main.code));
const isGay = s => /gay/.test(String(s.name + ' ' + s.code).normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').toLowerCase());
/* tên ngắn khi đăng ký: nhóm có nhiều ca → "Ca full" / "Ca gãy" */
const variantLabel = s => shiftGroup(s.code) !== s.code ? (isGay(s) ? 'Ca gãy' : s.name)
  : (App.meta.shifts.some(x => x.code !== s.code && shiftGroup(x.code) === s.code) ? 'Ca full' : s.name);
/* đăng ký lịch rảnh: nhóm có nhiều ca gãy (VD gãy 18:30–21:30 và 19:00–22:00) chỉ cho CTV chọn 1 ô "Ca gãy";
   gãy khung giờ nào do admin chọn khi xếp. Đăng ký lưu vào ca gãy đầu tiên của nhóm. */
const gayOf = g => App.meta.shifts.filter(s => shiftGroup(s.code) === g && s.code !== g && isGay(s)).sort((a, b) => a.start.localeCompare(b.start))[0];
const regVariants = main => { const g = gayOf(main.code); return shiftVariants(main).filter(s => !isGay(s) || s.code === main.code || s === g); };
const regShifts = () => App.meta.shifts.filter(s => !isGay(s) || s.code === shiftGroup(s.code) || gayOf(shiftGroup(s.code)) === s);
/* gộp đăng ký cũ ở ca gãy khác về ô "Ca gãy" chung */
const foldGay = slots => {
  const out = {};
  Object.entries(slots || {}).forEach(([key, v]) => {
    const k = key.slice(0, key.indexOf('-')), code = key.slice(key.indexOf('-') + 1);
    const s = App.meta.shifts.find(x => x.code === code), g = s && s.code !== shiftGroup(code) && isGay(s) && gayOf(shiftGroup(code));
    const nk = g ? `${k}-${g.code}` : key;
    if (!out[nk]) out[nk] = g && g.code !== code ? { start: g.start, end: g.end, ...(v.note ? { note: v.note } : {}) } : v;
  });
  return out;
};
/* tên đầy đủ cho admin: "Ca Tối · full", "Ca Tối · gãy" */
const regName = s => { const g = shiftGroup(s.code), main = App.meta.shifts.find(x => x.code === g);
  if (!main || !App.meta.shifts.some(x => x.code !== g && shiftGroup(x.code) === g)) return s.name;
  return `${main.name} · ${variantLabel(s).replace(/^Ca\s+/i, '')}`; };
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

/* bỏ dấu để tìm "ha" cũng ra "Hà", "dung" ra "Dũng" */
const foldVi = s => String(s || '').normalize('NFC').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase();

/* Biến <select> chọn nhân sự thành ô tìm kiếm: gõ vài ký tự → gợi ý những người có chứa ký tự đó
   (username hoặc họ tên, không phân biệt dấu). <select> gốc vẫn giữ giá trị nên code đọc .value không đổi. */
function searchSelect(sel, { placeholder = 'Gõ tên hoặc username để tìm…', limit = 50, allowNew = false } = {}) {
  if (!sel || sel.dataset.combo) return;
  sel.dataset.combo = 1;
  const opts = [...sel.options].filter(o => o.value);
  // allowNew: gõ tên chưa có → thêm dòng “+ Thêm …”; chọn thì sel.value = '__new__', tên ở sel.dataset.newName
  const NEW = { value: '__new__', textContent: '' };
  const wrap = document.createElement('div');
  wrap.className = 'combo';
  wrap.innerHTML = `<div class="search">${icon('search')}<input class="input full" type="text" autocomplete="off" spellcheck="false" role="combobox" aria-autocomplete="list" aria-expanded="false" placeholder="${esc(placeholder)}">
      <button type="button" class="combo-clear" aria-label="Xoá" hidden>${icon('x')}</button></div>
    <div class="combo-list" role="listbox" hidden></div>`;
  sel.hidden = true; sel.after(wrap);
  const inp = $('input', wrap), list = $('.combo-list', wrap), clr = $('.combo-clear', wrap);
  if (sel.disabled) inp.disabled = true;
  if (sel.required) { sel.required = false; inp.required = true; }   // select ẩn không nhận focus khi trình duyệt báo thiếu
  const cur = () => opts.find(o => o.value === sel.value);
  const hl = (text, q) => {   // tô đậm phần khớp (chữ NFC: bỏ dấu không đổi độ dài)
    const t = text.normalize('NFC'), f = foldVi(t), i = q ? f.indexOf(q) : -1;
    if (i < 0 || f.length !== t.length) return esc(t);
    return esc(t.slice(0, i)) + '<mark>' + esc(t.slice(i, i + q.length)) + '</mark>' + esc(t.slice(i + q.length));
  };
  let shown = [], active = 0;
  const open = on => { list.hidden = !on; inp.setAttribute('aria-expanded', on); };
  const paint = () => {
    const q = foldVi(inp.value.trim());
    const all = opts.filter(o => !q || foldVi(o.textContent).includes(q));
    // ưu tiên người có username / tên bắt đầu bằng chuỗi gõ
    if (q) all.sort((a, b) => (foldVi(b.textContent).split(/[\s.·]+/).some(w => w.startsWith(q))) - (foldVi(a.textContent).split(/[\s.·]+/).some(w => w.startsWith(q))));
    shown = all.slice(0, limit);
    const typed = inp.value.trim();
    if (allowNew && typed && !opts.some(o => foldVi(o.textContent) === q || foldVi(o.textContent.split(' · ')[0]) === q)) shown.push({ ...NEW, textContent: typed, isNew: true });
    active = Math.min(active, Math.max(0, shown.length - 1));
    list.innerHTML = shown.length
      ? shown.map((o, i) => `<div class="combo-opt ${i === active ? 'active' : ''} ${o.value === sel.value ? 'sel' : ''}" role="option" data-i="${i}">${o.isNew ? `${icon('plus')} Thêm mới “<b>${esc(o.textContent)}</b>” (chưa có trong Nhân sự)` : hl(o.textContent, q)}</div>`).join('')
        + (all.length > limit ? `<div class="combo-more">… còn ${all.length - limit} người, gõ thêm để lọc</div>` : '')
      : `<div class="combo-more">Không tìm thấy nhân sự chứa “${esc(inp.value.trim())}”</div>`;
    open(true);
  };
  const pick = o => {
    if (o && o.isNew) {
      let opt = sel.querySelector('option[value="__new__"]');
      if (!opt) { opt = new Option('', '__new__'); sel.add(opt); }
      opt.textContent = o.textContent; sel.dataset.newName = o.textContent;
      o = opt;
    } else delete sel.dataset.newName;
    sel.value = o ? o.value : '';
    inp.value = o ? (o.value === '__new__' ? `${o.textContent} (thêm mới)` : o.textContent) : '';
    clr.hidden = !o;
    open(false);
    sel.dispatchEvent(new Event('change', { bubbles: true }));
  };
  const sync = () => { const o = cur() || (sel.value === '__new__' ? sel.querySelector('option[value="__new__"]') : null); inp.value = o ? (o.value === '__new__' ? `${o.textContent} (thêm mới)` : o.textContent) : ''; clr.hidden = !o; };
  sync();
  inp.addEventListener('focus', () => { inp.select(); active = 0; paint(); });
  inp.addEventListener('input', () => { active = 0; if (sel.value) { sel.value = ''; sel.dispatchEvent(new Event('change', { bubbles: true })); } clr.hidden = !inp.value; paint(); });
  inp.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault(); if (list.hidden) return paint();
      active = (active + (e.key === 'ArrowDown' ? 1 : -1) + shown.length) % Math.max(1, shown.length); paint();
      $('.combo-opt.active', list)?.scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter') {
      if (!list.hidden && shown[active]) { e.preventDefault(); pick(shown[active]); }
    } else if (e.key === 'Escape' && !list.hidden) { e.preventDefault(); e.stopPropagation(); open(false); sync(); }
  });
  inp.addEventListener('blur', () => setTimeout(() => { if (!wrap.contains(document.activeElement)) { open(false); if (!sel.value && shown.length === 1 && !shown[0].isNew && inp.value.trim()) pick(shown[0]); else sync(); } }, 150));
  list.addEventListener('mousedown', e => e.preventDefault());   // giữ focus ở ô nhập
  list.addEventListener('click', e => { const d = e.target.closest('[data-i]'); if (d) pick(shown[+d.dataset.i]); });
  clr.addEventListener('mousedown', e => e.preventDefault());
  clr.addEventListener('click', () => { pick(null); inp.focus(); });
}

/* =========================================================
   Khung ứng dụng: đăng nhập, sidebar, định tuyến
   ========================================================= */
const App = {
  user: null, meta: null, config: null, cleanup: [],

  start(config) {
    this.config = config;
    if (new URLSearchParams(location.search).get('embed')) document.documentElement.classList.add('embed');   // nhúng trong trang Quản trị
    // /ctv?view=<id>: admin "xem như CTV" — token riêng cho từng người được xem, không đụng phiên đăng nhập thật
    this.viewId = config.role === 'ctv' ? new URLSearchParams(location.search).get('view') : null;
    TOKEN_KEY = this.viewId ? 'ctv_view_' + this.viewId : 'ctv_token_' + config.role;
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
    if (this.viewId) {
      document.body.innerHTML = `<div class="login"><div class="login-card card card-pad"><h1>Phiên xem đã hết hạn</h1>
        <p>Quay lại trang Quản trị và bấm <b>Xem như CTV</b> lần nữa (mỗi phiên xem dùng được 2 giờ).</p>
        <button class="btn btn-block" onclick="window.close()">Đóng tab</button></div></div>`;
      return;
    }
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
        if (c.role === 'admin' && !STAFF_ROLES.includes(r.user.role)) throw new Error('Tài khoản này không có quyền quản trị');
        store.set(TOKEN_KEY, r.token);
        this.enter(r.user);
      });
    };
  },

  async enter(user) {
    if (this.config.role === 'admin' && !STAFF_ROLES.includes(user.role)) { store.set(TOKEN_KEY, null); return this.showLogin(); }
    this.user = user;
    this.meta = await api('/meta');
    const c = this.config;
    // menu theo vai trò: ở trang Quản trị, sub admin chỉ thấy các mục có roles chứa 'subadmin'
    const allowed = i => i.only ? i.only.includes(user.role)   // only: mục riêng cho vai trò đó (admin không thấy)
      : c.role !== 'admin' || user.role === 'admin' || (i.roles || []).includes(user.role);
    this.nav = c.nav.map(g => ({ ...g, items: g.items.filter(allowed) })).filter(g => g.items.length);
    document.body.innerHTML = `<div class="shell">
      <aside class="sidebar" id="sidebar">
        <div class="brand"><div class="brand-mark">C</div><div>${c.brand}<small>${c.subtitle}</small></div></div>
        <nav class="nav" id="nav">${this.nav.map(g => `<div class="nav-group">${g.group}</div>` +
          g.items.map(i => `<a href="#${i.id}" data-id="${i.id}">${icon(i.icon)}<span>${i.label}</span><span class="count" data-count="${i.id}" hidden></span></a>`).join('')).join('')}</nav>
        ${STAFF_ROLES.includes(user.role) ? `<a class="switch-portal" id="switch-portal" href="/${c.role === 'admin' ? 'ctv' : 'admin'}">${icon(c.role === 'admin' ? 'users' : 'grid')}<span>${c.role === 'admin' ? 'Xem trang CTV' : 'Sang trang Quản trị'}</span>${icon('chevR')}</a>` : ''}
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
        ${user.view_as ? `<div class="view-as">${icon('info')}<div>Đang xem trang của <b>${esc(user.name)}</b> (${esc(user.username)}) — <b>chỉ xem</b>, mọi thao tác gửi / sửa đều bị chặn.
          CTV không thấy bạn đang xem, thông báo / nhận xét mới của họ vẫn giữ nguyên dấu "mới".</div><button class="btn btn-sm" onclick="window.close()">Đóng</button></div>` : ''}
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
      if (this._presence) this._presence(true);
      await api('/logout', { method: 'POST' }).catch(() => {});
      store.set(TOKEN_KEY, null); location.hash = ''; this.showLogin();
    };
    $('#open-nav').onclick = () => this.toggleNav(true);
    this.refreshNotifCount();
    setInterval(() => { if (document.visibilityState === 'visible') this.refreshNotifCount(); }, 120000);
    this.route();
    c.onEnter && c.onEnter();
    if (user.view_as) { document.title = `Xem như ${user.username}`; return; }
    if (document.documentElement.classList.contains('embed')) return;
    this.startPresence();
    if (user.must_change_pw) changePasswordDialog(true);
  },

  /* báo "đang mở web" cho trang Nhật ký hệ thống của admin: 1 phút/lần + khi đổi mục / ẩn hiện tab / đóng tab */
  startPresence() {
    if (this._presence) return;
    let tab = '';
    try { tab = sessionStorage.getItem('ctv_tab') || ''; if (!tab) { tab = Math.random().toString(36).slice(2, 12); sessionStorage.setItem('ctv_tab', tab); } }
    catch (e) { tab = Math.random().toString(36).slice(2, 12); }
    this._presence = bye => {
      const t = store.get(TOKEN_KEY);
      if (!t || !this.user) return;
      fetch('/api/presence', { method: 'POST', keepalive: true, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + t },
        body: JSON.stringify({ tab, portal: this.config.role, page: document.title.split(' · ')[0], visible: document.visibilityState === 'visible', bye: !!bye }) }).catch(() => {});
    };
    this._presence();
    setInterval(() => this._presence(), 60000);
    document.addEventListener('visibilitychange', () => this._presence());
    addEventListener('pagehide', () => this._presence(true));
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
    if (this.config.role === 'ctv') this.setCount('notifications', n);   // số thông báo mới cạnh mục "Thông báo"
    return list;
  },

  route() {
    if (!this.user || !$('#view')) return;
    this.cleanup.forEach(fn => fn()); this.cleanup = [];
    const items = this.nav.flatMap(g => g.items);
    if (location.hash === '#pip') history.replaceState(null, '', this.config.role === 'admin' ? '#qcctv' : '#nhanxetqc');   // link cũ
    const item = items.find(i => i.id === location.hash.slice(1)) || items[0];
    $$('#nav a').forEach(a => a.classList.toggle('active', a.dataset.id === item.id));
    // sub admin ở mục chỉ xem: ẩn các nút thêm / sửa / xoá (server cũng chặn)
    document.body.classList.toggle('ro-page', this.user.role === 'subadmin' && !(item.write || []).includes('subadmin'));
    this.toggleNav(false);
    const v = $('#view');
    v.innerHTML = '';
    window.scrollTo(0, 0);
    document.title = `${item.label} · ${this.config.brand}`;
    if (this._presence) this._presence();
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

const notifItem = n => `<div class="notif ${n.unread ? 'new' : ''}">
  <div style="display:flex;gap:8px;align-items:center"><strong>${esc(n.title)}</strong>${n.unread ? '<span class="badge accent">Mới</span>' : ''}</div>
  ${n.body ? `<div class="notif-b">${esc(n.body)}</div>` : ''}
  <div class="small muted" style="margin-top:4px">${fmtDate(n.created_at.slice(0, 10))} ${n.created_at.slice(11, 16)}</div></div>`;

async function notificationsDialog() {
  if (App.config.role === 'ctv') { location.hash = '#notifications'; return; }
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
