/* =========================================================
   Trang CTV
   ========================================================= */

const fmtSecs = s => { const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60; return `${h ? h + 'g ' : ''}${m}p ${pad(x)}s`; };

const cdText = st => `${st.key === 'wait' ? 'Bắt đầu sau ' : 'Còn '}${fmtSecs(st.secs)}${st.key === 'working' ? ' là hết ca' : ''}`;
function todayCard(s) {
  const st = shiftState(s);
  return `<div class="today-card">
    <div style="display:flex;justify-content:space-between;align-items:center"><span class="time">${s.start} – ${s.end}</span><span class="badge ${st.badge}">${st.label}</span></div>
    <div class="meta">${esc(s.shift_name || '')} · ${esc(s.team || '')} · ${esc(s.position || '')}</div>
    ${st.secs != null ? `<div class="count" data-cd="${s.id}">${cdText(st)}</div>` : ''}</div>`;
}

/* đếm ngược cho vùng chứa thẻ ca hôm nay; bấm thẻ để xem chi tiết */
function wireToday(container, shifts, reload) {
  container.onclick = e => { const c = e.target.closest('[data-cd]'); if (c) shiftDialog(shifts.find(s => s.id === +c.dataset.cd), reload); };
  let prev = shifts.map(s => shiftState(s).key).join();
  const timer = setInterval(() => {
    const keys = shifts.map(s => shiftState(s).key).join();
    if (keys !== prev) { prev = keys; container.innerHTML = shifts.map(todayCard).join(''); return; }
    shifts.forEach(s => {
      const el = container.querySelector(`[data-cd="${s.id}"]`); const st = shiftState(s);
      if (el && st.secs != null) el.textContent = cdText(st);
    });
  }, 1000);
  App.onLeave(() => clearInterval(timer));
}

/* chi tiết 1 ca: giờ, vị trí, đổi ca */
function shiftDialog(s, reload) {
  const st = shiftState(s);
  const canSwap = s.date >= todayStr() && st.key !== 'done';
  modal({
    title: `${s.shift_name || 'Ca'} · ${dowOf(s.date)} ${fmtDate(s.date)}`,
    body: `<dl class="kv">
        <dt>Giờ</dt><dd>${s.start} – ${s.end}</dd>
        <dt>Team</dt><dd>${esc(s.team || '—')}</dd>
        <dt>Vị trí</dt><dd>${esc(s.position || '—')}</dd>
        <dt>Trạng thái</dt><dd><span class="badge ${st.badge}">${st.label}</span></dd>
        ${planDiff(s) ? `<dt>Điều chỉnh</dt><dd>${planDiff(s)}</dd>` : ''}
        ${s.note ? `<dt>Ghi chú</dt><dd>${esc(s.note)}</dd>` : ''}
      </dl>`,
    footer: `${canSwap ? `<button class="btn" id="sd-swap">${icon('swap')} Xin đổi ca</button>` : ''}
      <button class="btn" data-close>Đóng</button>`,
    onOpen(el, close) {
      $('#sd-swap', el)?.addEventListener('click', () => { close(); swapDialog(s, reload); });
    },
  });
}

async function swapDialog(s, reload) {
  const cands = await api('/ctv/swap-candidates', { query: { schedule_id: s.id } }).catch(e => { toast(e.message, 'error'); return null; });
  if (!cands) return;
  modal({
    title: 'Xin đổi ca',
    body: `<p class="muted" style="margin-bottom:14px">${dowOf(s.date)} ${fmtDate(s.date)} · ${s.start}–${s.end} · ${esc(s.position || '')}</p>
      <div class="field"><label>Người làm thay</label>
        <select class="input" id="sw-to">${cands.length ? '<option value="">— Chọn CTV đang rảnh —</option>' + cands.map(c => `<option value="${c.id}">${esc(c.username)} · ${esc(c.name)}</option>`).join('') : '<option value="">Không có CTV nào rảnh khung giờ này</option>'}</select>
        <span class="hint">Chỉ hiện những người chưa có ca trùng giờ</span></div>
      <div class="field"><label>Lý do</label><textarea class="input" rows="3" id="sw-reason" placeholder="VD: Trùng lịch thi"></textarea></div>`,
    footer: `<button class="btn" data-close>Huỷ</button><button class="btn btn-primary" id="sw-ok">Gửi phiếu</button>`,
    onOpen(el, close) {
      $('#sw-ok', el).onclick = e => run(e.currentTarget, async () => {
        if (!$('#sw-to', el).value) throw new Error('Vui lòng chọn người làm thay');
        await api('/ctv/swaps', { method: 'POST', body: { schedule_id: s.id, to_user: +$('#sw-to', el).value, reason: $('#sw-reason', el).value } });
        close(); toast('Đã gửi phiếu, chờ quản lý duyệt'); reload && reload();
      });
    },
  });
}

/* =========================================================
   1. Tổng quan
   ========================================================= */
async function pageDashboard(v) {
  v.innerHTML = pageHead(`Xin chào, ${esc(App.user.name.split(' ').pop())}`, 'Tổng quan ca trực và giờ làm của bạn trong tháng này.') + loading();
  const [d, today] = await Promise.all([api('/ctv/dashboard'), api('/ctv/schedule', { query: { start: todayStr(), end: todayStr() } })]);
  const reload = () => App.route();
  v.innerHTML = pageHead(`Xin chào, ${esc(App.user.name.split(' ').pop())}`, 'Tổng quan ca trực và giờ làm của bạn trong tháng này.') + `
    <div class="stats">
      <div class="stat"><div class="label">Giờ đã chấm công</div><div class="value">${d.hours}</div></div>
      <div class="stat"><div class="label">Ca đã chấm công / được xếp</div><div class="value">${d.done}<span class="muted" style="font-size:16px"> / ${d.shifts}</span></div>${d.waiting ? `<div class="small muted">${d.waiting} ca chờ admin duyệt</div>` : ''}</div>
      <div class="stat"><div class="label">Giờ theo lịch cả tháng</div><div class="value">${d.planned_hours}</div></div>
    </div>
    <div class="card"><div class="card-head"><h2>Ca hôm nay</h2><a class="btn btn-sm" href="#schedule">Xem lịch</a></div>
      <div class="card-pad">${today.length ? `<div class="today-list" id="today">${today.map(todayCard).join('')}</div>` : '<p class="muted">Hôm nay bạn không có ca nào.</p>'}</div></div>
    <div class="card" style="margin-top:16px"><div class="card-head"><h2>Giờ làm theo tuần</h2></div><div class="card-pad">${barChart(d.weeks.map(w => ({ label: w.label, value: w.hours })))}</div></div>
    <div class="card"><div class="card-head"><h2>Ca sắp tới</h2></div>
      ${d.upcoming.length ? `<div class="table-wrap"><table class="table"><tbody>${d.upcoming.map(s => `<tr>
        <td class="nowrap"><b>${dowOf(s.date)}</b> ${fmtDate(s.date)}</td><td>${s.start}–${s.end}</td><td class="muted">${esc(s.position || '')}</td></tr>`).join('')}</tbody></table></div>`
        : emptyState('Chưa có ca sắp tới')}</div>`;
  if (today.length) wireToday($('#today'), today, reload);
}

/* =========================================================
   2. Lịch làm việc
   ========================================================= */
let weekStart = mondayOf(new Date());
async function pageSchedule(v) {
  v.innerHTML = pageHead('Lịch làm việc', 'Bấm vào một ca để xem chi tiết hoặc xin đổi ca.',
    `<button class="btn" id="exp">${icon('download')} Xuất Excel tháng</button>`) + `
    <div id="today-wrap"></div>
    <div class="filters" style="margin-top:16px">
      <button class="btn btn-icon" id="prev" aria-label="Tuần trước">${icon('chevL')}</button>
      <button class="btn" id="this">Tuần này</button>
      <button class="btn btn-icon" id="next" aria-label="Tuần sau">${icon('chevR')}</button>
      <strong id="range" style="margin-left:8px"></strong>
    </div>
    <div class="card" id="week">${loading()}</div>`;

  const today = await api('/ctv/schedule', { query: { start: todayStr(), end: todayStr() } });
  if (today.length) {
    $('#today-wrap').innerHTML = `<div class="card"><div class="card-head"><h2>Hôm nay · ${today.length} ca</h2></div><div class="card-pad"><div class="today-list" id="today">${today.map(todayCard).join('')}</div></div></div>`;
    wireToday($('#today'), today, () => App.route());
  }

  const load = async () => {
    const end = addDays(weekStart, 6);
    $('#range').textContent = `${fmtDate(ymd(weekStart))} – ${fmtDate(ymd(end))}`;
    const list = await api('/ctv/schedule', { query: { start: ymd(weekStart), end: ymd(end) } });
    $('#week').innerHTML = `<div class="week">${Array.from({ length: 7 }, (_, i) => {
      const d = ymd(addDays(weekStart, i)); const items = list.filter(s => s.date === d);
      return `<div class="day ${d === todayStr() ? 'today' : ''} ${items.length ? '' : 'empty-day'}">
        <div class="day-h"><span>${DOW_FULL[parseDate(d).getDay()]}</span><b>${fmtDM(d)}</b></div>
        <div class="day-body">${App.meta.shifts.map(sh => {
          const label = esc(sh.name.replace(/^ca\s+/i, ''));
          const inSlot = items.filter(s => s.shift_code === sh.code);
          if (!inSlot.length) return `<div class="slot-row"><span class="slot-name">${label}</span><div class="slot-empty">Trống</div></div>`;
          return `<div class="slot-row"><span class="slot-name">${label}</span>${inSlot.map(s => {
            const st = shiftState(s);
            return `<button class="chip ${st.key === 'done' ? 'done' : st.key === 'missed' ? 'missed' : ''}" data-id="${s.id}">
              <b>${s.start}–${s.end}</b>${esc(s.position || '')}<br><span class="who">${st.label}</span></button>`;
          }).join('')}</div>`;
        }).join('')}</div></div>`;
    }).join('')}</div>${list.length ? '' : '<div class="empty">Tuần này bạn không có ca nào.</div>'}`;
    $('#week').onclick = e => { const c = e.target.closest('[data-id]'); if (c) shiftDialog(list.find(s => s.id === +c.dataset.id), load); };
  };
  $('#prev').onclick = () => { weekStart = addDays(weekStart, -7); load(); };
  $('#next').onclick = () => { weekStart = addDays(weekStart, 7); load(); };
  $('#this').onclick = () => { weekStart = mondayOf(new Date()); load(); };
  $('#exp').onclick = async () => {
    const ym = ymOf(addDays(weekStart, 3)); const { start, end } = monthBounds(ym);
    const rows = await api('/ctv/schedule', { query: { start, end } });
    downloadCSV(`lich-lam-${ym}.csv`, ['Ngày', 'Thứ', 'Ca', 'Giờ', 'Team', 'Vị trí'],
      rows.map(s => [fmtDate(s.date), dowOf(s.date), s.shift_name, `${s.start}-${s.end}`, s.team, s.position]));
  };
  load();
}

/* =========================================================
   3. Đăng ký lịch rảnh
   ========================================================= */
const WEEK_KEYS = [1, 2, 3, 4, 5, 6, 7]; // 1 = Thứ 2 … 7 = Chủ nhật
const WEEK_LABEL = { 1: 'Thứ 2', 2: 'Thứ 3', 3: 'Thứ 4', 4: 'Thứ 5', 5: 'Thứ 6', 6: 'Thứ 7', 7: 'Chủ nhật' };

/* tuần đăng ký: khoá = ngày thứ 2 (YYYY-MM-DD); hạn chót 19:00 CN trước tuần */
const regDeadline = ws => { const d = addDays(parseDate(ws), -1); d.setHours(19, 0, 0, 0); return d; };
const weekLabel = ws => `${fmtDM(ws)} – ${fmtDM(ymd(addDays(parseDate(ws), 6)))}`;
const fmtLeft = ms => { const m = Math.max(0, Math.floor(ms / 60000)), d = Math.floor(m / 1440), h = Math.floor(m % 1440 / 60); return d ? `${d} ngày ${h} giờ` : h ? `${h} giờ ${m % 60} phút` : `${m % 60} phút`; };

async function pageAvailability(v) {
  const shifts = App.meta.shifts;
  const thisMon = mondayOf(new Date());
  const weeks = [0, 1, 2].map(i => ymd(addDays(thisMon, 7 * (i + 1))));
  let ws = weeks.find(w => regDeadline(w) > new Date()) || weeks[0];
  let state = null;

  v.innerHTML = pageHead('Đăng ký lịch rảnh', 'Đăng ký theo tuần: chọn những ca bạn có thể làm rồi bấm “Gửi đăng ký”. Hạn chót 19:00 Chủ nhật, 20:00 hệ thống tự chia ca và quản lý duyệt.') + `
    <div class="filters">
      <div class="seg" id="wk">${[ymd(thisMon), ...weeks].map(w => `<button data-w="${w}">${w === ymd(thisMon) ? 'Tuần này' : 'Tuần ' + weekLabel(w)}</button>`).join('')}</div>
      <span id="status"></span><span style="flex:1"></span>
      <button class="btn" id="copy">${icon('copy')} Dùng lịch tuần trước</button>
    </div>
    <div id="dl"></div>
    <div class="card"><div class="table-wrap" id="grid">${loading()}</div>
      <div class="card-pad" style="border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
        <div class="legend"><span id="summary"></span></div>
        <div class="actions"><button class="btn btn-primary" id="submit">Gửi đăng ký</button></div>
      </div></div>`;

  const locked = () => !state.open;
  const dayOf = k => ymd(addDays(parseDate(ws), k - 1));

  function paint() {
    $$('#wk button').forEach(b => b.classList.toggle('active', b.dataset.w === ws));
    const dl = regDeadline(ws), open = state.open;
    $('#status').innerHTML = !open ? '<span class="badge">Đã chốt đăng ký</span>'
      : state.status === 'submitted' ? '<span class="badge green">Đã gửi — vẫn sửa được tới hạn chót</span>'
      : state.status === 'draft' ? '<span class="badge amber">Chưa gửi</span>' : '<span class="badge blue">Đang mở đăng ký</span>';
    $('#dl').innerHTML = open
      ? `<div class="notice" style="border-color:var(--accent);background:color-mix(in srgb,var(--accent) 6%,var(--surface))">⏰ Hạn chót <b>19:00 Chủ nhật ${fmtDM(ymd(dl))}</b> — còn <b id="left">${fmtLeft(dl - new Date())}</b>. Sau đó hệ thống tự chia ca lúc 20:00.</div>`
      : `<div class="notice" style="border-color:var(--border);background:var(--surface-2)">Tuần ${weekLabel(ws)} đã chốt đăng ký. Lịch làm sẽ hiện ở mục <a href="#schedule">Lịch làm việc</a> sau khi quản lý duyệt.</div>`;
    ['#copy', '#submit'].forEach(s => { $(s).disabled = locked(); });
    $('#submit').textContent = state.status === 'submitted' ? 'Cập nhật đăng ký' : 'Gửi đăng ký';
    const L = locked();
    $('#grid').innerHTML = `<div class="av-grid"><div></div>${WEEK_KEYS.map(k => `<div class="h">${WEEK_LABEL[k]}<br><span class="muted small">${fmtDM(dayOf(k))}</span></div>`).join('')}
      ${shifts.map(s => `<div class="rowh">${esc(s.name)}<span>${s.start}–${s.end}</span></div>${WEEK_KEYS.map(k => {
        const key = `${k}-${s.code}`; const on = !!state.slots[key];
        const ni = needInfo((state.counts[key] || 0) + (on ? 1 : 0), s, true);
        const cnt = `<span class="need ${ni.cls}" title="Số CTV đã đăng ký${ni.target ? ' / cần ' + ni.target : ''}">${ni.text} CTV${ni.missing ? ` · thiếu ${ni.missing}` : ''}</span>`;
        const attrs = L ? '' : `data-toggle="${key}" role="button" tabindex="0" aria-pressed="${on}" aria-label="${esc(s.name)} ${WEEK_LABEL[k]}"`;
        return on ? `<div class="slot on ${L ? 'locked' : ''}" ${attrs}><b>✓ Rảnh</b>${cnt}</div>`
          : `<div class="slot ${L ? 'locked' : ''}" ${attrs}>${L ? '—' : '+ Rảnh'}${cnt}</div>`;
      }).join('')}`).join('')}</div>`;
    const n = Object.keys(state.slots).length;
    const hrs = Object.values(state.slots).reduce((a, x) => a + (t2m(x.end) - t2m(x.start)) / 60, 0);
    $('#summary').textContent = n ? `${n} ca rảnh · khoảng ${hrs} giờ` + (state.updated_at ? ` · cập nhật ${fmtDate(state.updated_at.slice(0, 10))} ${state.updated_at.slice(11, 16)}` : '') : 'Chưa chọn ca nào';
  }

  async function load() {
    $('#grid').innerHTML = loading();
    state = await api('/ctv/availability', { query: { ym: ws } });
    state.counts = state.counts || {};
    paint();
  }

  const timer = setInterval(() => { const el = $('#left'); if (el) el.textContent = fmtLeft(regDeadline(ws) - new Date()); }, 30000);
  App.onLeave(() => clearInterval(timer));
  $('#wk').onclick = e => { const b = e.target.closest('[data-w]'); if (b) { ws = b.dataset.w; load(); } };
  $('#grid').addEventListener('click', e => {
    if (locked()) return;
    const t = e.target.closest('[data-toggle]'); if (!t) return;
    const key = t.dataset.toggle;
    if (state.slots[key]) delete state.slots[key];
    else { const s = shifts.find(x => x.code === key.slice(key.indexOf('-') + 1)); state.slots[key] = { start: s.start, end: s.end }; }
    if (state.status === 'empty') state.status = 'draft';
    paint();
    const again = $(`[data-toggle="${key}"]`); again && again.focus();
  });
  $('#grid').addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && e.target.dataset.toggle) { e.preventDefault(); e.target.click(); } });
  $('#submit').onclick = e => {
    if (!Object.keys(state.slots).length) return toast('Bạn chưa chọn ca rảnh nào', 'error');
    run(e.currentTarget, async () => {
      await api('/ctv/availability', { method: 'PUT', body: { ym: ws, slots: state.slots, submit: true } });
      toast(`Đã gửi đăng ký tuần ${weekLabel(ws)}`); load();
    });
  };
  $('#copy').onclick = async () => {
    const prevWs = ymd(addDays(parseDate(ws), -7));
    let prev = await api('/ctv/availability', { query: { ym: prevWs } });
    if (!Object.keys(prev.slots).length) prev = await api('/ctv/availability', { query: { ym: prevWs.slice(0, 7) } }); // lịch theo tháng cũ
    if (!Object.keys(prev.slots).length) return toast('Tuần trước bạn chưa đăng ký lịch', 'info');
    state.slots = prev.slots; if (state.status === 'empty') state.status = 'draft';
    paint(); toast('Đã sao chép. Nhớ bấm “Gửi đăng ký”.', 'info');
  };
  load();
}

/* =========================================================
   4. Lịch team theo ngày
   ========================================================= */
async function pageTeam(v) {
  let day = new Date();
  v.innerHTML = pageHead('Lịch team theo ngày', 'Xem ai trực cùng ca để tiện phối hợp.') + `
    <div class="filters">
      <button class="btn btn-icon" id="prev" aria-label="Ngày trước">${icon('chevL')}</button>
      <input type="date" class="input" id="day">
      <button class="btn btn-icon" id="next" aria-label="Ngày sau">${icon('chevR')}</button>
      <select class="input" id="team"><option value="">Tất cả team</option>${App.meta.teams.map(t => `<option value="${t.id}">${esc(t.name)}</option>`).join('')}</select>
    </div><div id="body">${loading()}</div>`;
  const load = async () => {
    $('#day').value = ymd(day);
    const list = await api('/team-day', { query: { day: ymd(day), team_id: $('#team').value } });
    if (!list.length) { $('#body').innerHTML = `<div class="card">${emptyState('Không có ai được xếp ca trong ngày này')}</div>`; return; }
    $('#body').innerHTML = App.meta.shifts.map(sh => {
      const inShift = list.filter(s => s.shift_code === sh.code); if (!inShift.length) return '';
      const groups = {}; inShift.forEach(s => { const k = `${s.team || ''} · ${s.position || 'Khác'}`; (groups[k] = groups[k] || []).push(s); });
      return `<div class="card" style="margin-bottom:16px"><div class="card-head"><h2>${esc(sh.name)} <span class="muted" style="font-weight:400">${sh.start}–${sh.end}</span></h2><span class="badge">${inShift.length} người</span></div>
        ${Object.entries(groups).map(([k, ps]) => `<div class="team-block"><h3>${esc(k)}</h3><div class="people">${ps.map(p => `
          <div class="person ${p.user_id === App.user.id ? 'me' : ''}" title="${esc(p.name)}"><div class="avatar">${initials(p.name)}</div>
            <div>${esc(p.username)} <small>${p.start}–${p.end}</small></div></div>`).join('')}</div></div>`).join('')}</div>`;
    }).join('');
  };
  $('#prev').onclick = () => { day = addDays(day, -1); load(); };
  $('#next').onclick = () => { day = addDays(day, 1); load(); };
  $('#day').onchange = e => { if (e.target.value) { day = parseDate(e.target.value); load(); } };
  $('#team').onchange = load;
  load();
}

/* =========================================================
   5. Phiếu đổi ca
   ========================================================= */
const SWAP_STATUS = { pending: ['Chờ duyệt', 'amber'], approved: ['Đã duyệt', 'green'], rejected: ['Từ chối', 'red'] };
async function pageSwaps(v) {
  let status = 'all', dir = 'all', rows = [];
  v.innerHTML = pageHead('Phiếu đổi ca', 'Các ca bạn xin đổi và các ca bạn nhận làm thay.', `<button class="btn btn-primary" id="new">${icon('plus')} Xin đổi ca</button>`) + `
    <div class="filters"><div class="seg" id="st"></div>
      <select class="input" id="dir"><option value="all">Tất cả</option><option value="out">Tôi xin đổi</option><option value="in">Tôi làm thay</option></select></div>
    <div class="card" id="body">${loading()}</div>`;
  const paint = () => {
    const c = { all: rows.length, pending: 0, approved: 0, rejected: 0 }; rows.forEach(r => c[r.status]++);
    $('#st').innerHTML = [['all', 'Tất cả'], ['pending', 'Chờ duyệt'], ['approved', 'Đã duyệt'], ['rejected', 'Từ chối']]
      .map(([k, l]) => `<button class="${status === k ? 'active' : ''}" data-s="${k}">${l} <span class="n">${c[k]}</span></button>`).join('');
    const me = App.user.id;
    const list = rows.filter(r => (status === 'all' || r.status === status) && (dir === 'all' || (dir === 'out' ? r.from_user === me : r.to_user === me)));
    dataTable($('#body'), list, [
      { label: 'Ca', render: r => `<b>${fmtDate(r.date)}</b><br><span class="muted small">${r.start}–${r.end} · ${esc(r.position || '')}</span>` },
      { label: 'Người xin đổi', render: r => r.from_user === me ? '<b>Tôi</b>' : esc(r.from_username) },
      { label: 'Người làm thay', render: r => r.to_user === me ? '<b>Tôi</b>' : esc(r.to_username) },
      { label: 'Lý do', render: r => `<span class="muted">${esc(r.reason || '—')}</span>` },
      { label: 'Trạng thái', render: r => `<span class="badge ${SWAP_STATUS[r.status][1]}">${SWAP_STATUS[r.status][0]}</span>${r.handled_by ? `<br><span class="small muted">${esc(r.handled_by)}</span>` : ''}` },
      { label: '', cls: 'right', render: r => r.status === 'pending' && r.from_user === me ? `<button class="btn btn-sm btn-danger" data-cancel="${r.id}">Huỷ</button>` : '' },
    ], { empty: 'Không có phiếu nào' });
  };
  const load = async () => { rows = await api('/ctv/swaps'); paint(); };
  $('#st').onclick = e => { const b = e.target.closest('[data-s]'); if (b) { status = b.dataset.s; paint(); } };
  $('#dir').onchange = e => { dir = e.target.value; paint(); };
  $('#body').addEventListener('click', async e => {
    const b = e.target.closest('[data-cancel]'); if (!b) return;
    if (!(await confirmDialog('Huỷ phiếu đổi ca?', 'Phiếu sẽ bị xoá và ca vẫn thuộc về bạn.', 'Huỷ phiếu', true))) return;
    run(b, async () => { await api(`/ctv/swaps/${b.dataset.cancel}`, { method: 'DELETE' }); toast('Đã huỷ phiếu'); load(); });
  });
  $('#new').onclick = async () => {
    const end = ymd(addDays(new Date(), 45));
    const mine = (await api('/ctv/schedule', { query: { start: todayStr(), end } })).filter(s => shiftState(s).key !== 'done');
    if (!mine.length) return toast('Bạn không có ca sắp tới nào để đổi', 'info');
    modal({
      title: 'Chọn ca muốn đổi',
      body: `<div class="field"><select class="input" id="pick">${mine.map(s => `<option value="${s.id}">${dowOf(s.date)} ${fmtDate(s.date)} · ${s.start}–${s.end} · ${esc(s.position || '')}</option>`).join('')}</select></div>`,
      footer: `<button class="btn" data-close>Huỷ</button><button class="btn btn-primary" id="go">Tiếp tục</button>`,
      onOpen(el, close) { $('#go', el).onclick = () => { const s = mine.find(x => x.id === +$('#pick', el).value); close(); swapDialog(s, load); }; },
    });
  };
  load();
}

/* =========================================================
   6. Cẩm nang (đồng bộ từ Google Sheet)
   ========================================================= */
const linkify = t => esc(t).replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
/* bỏ dấu tiếng Việt để tìm "doi lich" cũng ra "Đổi lịch" */
const fold = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase();
const words = q => fold(q).split(/\s+/).filter(Boolean);
const matches = (text, ws) => { const t = fold(text); return ws.every(w => t.includes(w)); };
/* tô vàng từ khoá (không phân biệt dấu) trong HTML đã escape */
function mark(html, q) {
  const ws = words(q); if (!ws.length) return html;
  return html.replace(/(<[^>]+>)|([^<]+)/g, (m, tag, text) => {
    if (tag) return tag;
    const f = fold(text); const hits = [];
    ws.forEach(w => { let i = f.indexOf(w); while (i >= 0) { hits.push([i, i + w.length]); i = f.indexOf(w, i + 1); } });
    if (!hits.length) return text;
    hits.sort((a, b) => a[0] - b[0]);
    let out = '', pos = 0;
    hits.forEach(([s, e]) => { if (s < pos) return; out += text.slice(pos, s) + '<mark>' + text.slice(s, e) + '</mark>'; pos = e; });
    return out + text.slice(pos);
  });
}

/* Tách dòng tiêu đề / header / dữ liệu của một tab dạng tài liệu */
const isNum = s => /^\d+([.,]\d+)*\.?$/.test(String(s).trim());
function splitSheet(rows) {
  const filled = r => r.filter(Boolean).length;
  const h = rows.findIndex(r => filled(r) >= 2);
  if (h < 0) return { titles: rows.map(r => r.find(Boolean)), header: null, body: [] };
  const titles = rows.slice(0, h).map(r => r.find(Boolean));
  // dòng đầu tiên bắt đầu bằng số thứ tự là dữ liệu, không phải tiêu đề cột
  if (isNum(rows[h][0])) return { titles, header: rows[h].map(() => ''), body: rows.slice(h) };
  return { titles, header: rows[h], body: rows.slice(h + 1) };
}

/* Bảng giống file sheet: cột nội dung dài tự rộng hơn, giữ xuống dòng như trong sheet */
function sheetTableHtml(header, body, q = '') {
  const n = header.length;
  const avg = i => { const v = body.map(r => r[i] || '').filter(Boolean); return v.length ? v.reduce((a, s) => a + Math.min(s.length, 600), 0) / v.length : 0; };
  const widths = header.map((_, i) => { const a = avg(i); return a > 150 ? 'w-xl' : a > 60 ? 'w-lg' : a > 20 ? 'w-md' : 'w-sm'; });
  const cell = c => {
    if (!c) return '';
    const html = `<div class="hb-cell">${mark(linkify(c), q)}</div>`;
    return c.length > 80 ? html + `<button class="btn btn-sm btn-ghost hb-copy" data-copy>${icon('copy')} Sao chép</button>` : html;
  };
  return `<div class="table-wrap hb-wrap"><table class="table hb-table">
    ${header.some(Boolean) ? `<thead><tr>${header.map((c, i) => `<th class="${widths[i]}">${esc(c)}</th>`).join('')}</tr></thead>` : ''}
    <tbody>${body.map(r => `<tr>${Array.from({ length: n }, (_, i) => `<td class="${widths[i]}">${cell(r[i] || '')}</td>`).join('')}</tr>`).join('')}</tbody>
  </table></div>`;
}

async function pageHandbook(v) {
  const head = actions => pageHead('Cẩm nang', 'Quy trình, quy định, script và thông tin tra cứu — tự cập nhật theo Google Sheet.', actions);
  v.innerHTML = head('') + loading();
  const idx = await api('/handbook');
  const tabName = g => (idx.tabs.find(t => t.gid === g) || {}).name || '';
  let gid = store.get('hb_tab');
  if (!idx.tabs.some(t => t.gid === gid)) gid = idx.tabs[0] && idx.tabs[0].gid;
  let parsed = null, limit = 200, q = '', searchSeq = 0;

  v.innerHTML = head(`<button class="btn" id="hb-toggle">${icon('menu')} <span>Ẩn danh sách mục</span></button>
      <button class="btn" id="hb-refresh">${icon('refresh')} Làm mới</button><a class="btn" href="${esc(idx.sheet_url)}" target="_blank" rel="noopener">Mở Google Sheet</a>`) + `
    <div class="search hb-search">${icon('search')}<input class="input full" id="hb-q" placeholder="Tìm trong toàn bộ cẩm nang — VD: đổi lịch, xin nghỉ, lỗi cam mic…" autocomplete="off">
      <button class="btn btn-ghost btn-sm hb-clear" id="hb-clear" hidden aria-label="Xoá tìm kiếm">${icon('x')}</button></div>
    <div class="hb ${store.get('hb_nav') === 'hide' ? 'nav-hidden' : ''}" id="hb">
      <nav class="card hb-nav" id="hb-nav" aria-label="Các mục cẩm nang">${idx.tabs.map(t => `<button data-gid="${t.gid}">${esc(t.name)}</button>`).join('')}</nav>
      <select class="input hb-select" id="hb-select" aria-label="Chọn mục">${idx.tabs.map(t => `<option value="${t.gid}">${esc(t.name)}</option>`).join('')}</select>
      <div class="hb-main">
        <div class="hb-bar"><h2 id="hb-heading"></h2><span class="small muted" id="hb-time"></span></div>
        <div class="card" id="hb-body"></div>
      </div>
    </div>`;
  const syncToggle = () => { $('#hb-toggle span').textContent = $('#hb').classList.contains('nav-hidden') ? 'Hiện danh sách mục' : 'Ẩn danh sách mục'; };
  syncToggle();

  /* ----- xem 1 mục: dạng bảng như file ----- */
  const paintTab = () => {
    const { titles, header, body } = parsed;
    const t = titles.filter(Boolean).map(x => `<div class="hb-title">${esc(x)}</div>`).join('');
    if (!header) { $('#hb-body').innerHTML = t ? `<div class="card-pad">${t}</div>` : emptyState('Mục này chưa có nội dung'); return; }
    if (!body.length) { $('#hb-body').innerHTML = emptyState('Mục này chưa có nội dung'); return; }
    $('#hb-body').innerHTML = (t ? `<div class="hb-titles">${t}</div>` : '') + sheetTableHtml(header, body.slice(0, limit)) +
      (body.length > limit ? `<div class="hb-more"><span class="muted small">Đang hiện ${limit}/${body.length} dòng</span><button class="btn" data-more>Xem thêm</button></div>` : '');
  };
  const loadTab = async (refresh = false) => {
    $$('#hb-nav button').forEach(b => b.classList.toggle('active', b.dataset.gid === gid));
    $('#hb-select').value = gid; store.set('hb_tab', gid);
    $('#hb-heading').textContent = tabName(gid);
    $('#hb-body').innerHTML = '<div class="skel"></div><div class="skel w60"></div><div class="skel"></div>';
    try {
      const d = await api(`/handbook/tab/${gid}`, { query: { refresh: refresh ? 1 : '' } });
      parsed = splitSheet(d.rows); limit = 200;
      $('#hb-time').textContent = `Cập nhật lúc ${d.fetched_at.slice(11, 16)}` + (d.warning ? ' · đang dùng bản lưu tạm' : '');
      paintTab();
    } catch (e) { $('#hb-body').innerHTML = emptyState(e.message); }
  };

  /* ----- tìm trên tất cả mục: trình bày theo vai trò của từng mục -----
     show    → hiện sẵn (Script, Template, Kho ticket)
     suggest → gợi ý thu gọn, bấm để xem các bước (Tra cứu nghiệp vụ)
     other   → nội dung liên quan khác, thu gọn */
  const modeOf = g => (idx.tabs.find(t => t.gid === g) || {}).mode || 'other';
  const score = (text, title) => {
    const ws = words(q), ph = fold(q).replace(/\s+/g, ' ').trim(), t = fold(text), tt = fold(title);
    if (!ws.every(w => t.includes(w))) return 0;
    if (tt.includes(ph)) return 4;            // đúng cụm từ ở tiêu đề
    if (ws.every(w => tt.includes(w))) return 3;
    if (t.includes(ph)) return 2;              // đúng cụm từ ở nội dung
    return 1;                                  // chỉ có các từ rời rạc
  };
  // gom dòng nối tiếp (cột đầu trống) vào dòng phía trên — như ô gộp trong sheet
  const blocksOf = body => { const out = []; body.forEach(r => { if (r[0] || !out.length) out.push([]); out[out.length - 1].push(r); }); return out; };
  const avgLen = (body, i) => { const v = body.map(r => r[i]).filter(Boolean); return v.length ? v.reduce((a, s) => a + s.length, 0) / v.length : 0; };
  let state = {};
  const stepName = (tab, mode) => {
    const n = fold(tab);
    if (mode === 'suggest') return { title: 'Các bước xử lý', sub: `Gợi ý từ ${tab} — bấm vào từng tình huống để xem chi tiết` };
    if (n.includes('script')) return { title: 'Script trả lời', sub: tab };
    if (n.includes('template')) return { title: 'Lên ticket (nếu cần)', sub: `Template và kho nhận ticket theo sản phẩm · ${tab}` };
    if (n.includes('ticket')) return { title: 'Ticket', sub: `${tab} — nếu cần lên ticket` };
    return { title: tab, sub: '' };
  };

  function showSection(g) {
    const blocks = blocksOf(g.body).map(rows => ({ rows, s: score(rows.flat().join(' '), rows[0].slice(0, 2).join(' ')) }))
      .filter(b => b.s).sort((a, b) => b.s - a.s);
    if (!blocks.length) return null;
    const strong = blocks.filter(b => b.s >= 2);
    const main = strong.length ? strong : blocks, rest = strong.length ? blocks.filter(b => b.s < 2) : [];
    state[g.gid] = { header: g.header, main, rest, shown: Math.min(3, main.length) };
    return { count: main.length, html: `<div data-sec="${g.gid}">${showTable(g.gid)}</div>` };
  }
  const copyBtn = `<button class="btn btn-sm btn-ghost hb-copy" data-copy>${icon('copy')} Sao chép</button>`;
  const partHtml = (v, forceCopy) => `<div class="hb-part"><div class="hb-cell">${mark(linkify(v), q)}</div>${forceCopy || v.length > 60 ? copyBtn : ''}</div>`;

  /* 1 mục dạng thẻ: tiêu đề + các trường có nhãn (dùng cho Script và nội dung khác) */
  function entryHtml(rows, h) {
    const first = rows[0];
    const ti = isNum(first[0]) && first[1] ? 1 : 0;           // cột STT → lấy cột kế tiếp làm tiêu đề
    const title = first[ti] || '';
    const fields = [];
    rows.forEach((r, ri) => r.forEach((c, i) => { if (c && !(ri === 0 && i <= ti)) fields.push({ label: h[i] || '', v: c, note: /note|ghi chu|luu y/.test(fold(h[i])) }); }));
    return `<div class="hb-entry">
      ${title ? `<div class="hb-entry-title">${isNum(first[0]) && ti ? `<span class="hb-no">${esc(first[0])}</span>` : ''}<span>${mark(esc(title), q)}</span></div>` : ''}
      ${fields.map(f => `<div class="hb-entry-field ${f.note ? 'is-note' : ''}">${f.label ? `<div class="hb-label">${esc(f.label)}</div>` : ''}${partHtml(f.v)}</div>`).join('')}
    </div>`;
  }

  /* Template ticket: mỗi sản phẩm 1 khối — tiêu đề ticket, template theo size lớp, kho nhận ticket */
  function templateHtml(rows, h, khoCols) {
    const issue = rows[0][0] || '';
    const prodCols = h.map((_, i) => i).filter(i => i >= 2 && !khoCols.includes(i));
    const isTitleRow = r => /tieu de/.test(fold(r[1]));
    const prods = prodCols.map(i => {
      const kho = khoCols.includes(i + 1) ? i + 1 : -1;
      const titleRow = rows.find(isTitleRow);
      const sizes = rows.filter(r => !isTitleRow(r) && r[i]).map(r => ({ size: r[1], text: r[i], kho: kho >= 0 ? r[kho] : '' }));
      return { name: h[i], title: titleRow ? titleRow[i] : '', sizes };
    }).filter(p => p.title || p.sizes.length);
    if (!prods.length) return entryHtml(rows, h);
    const [main, ...sub] = issue.split('\n');
    return `<div class="hb-entry">
      <div class="hb-entry-title"><span>${mark(esc(main), q)}</span></div>
      ${sub.length ? `<div class="small muted" style="margin:-4px 0 10px">${esc(sub.join(' ').trim())}</div>` : ''}
      <div class="hb-tpl-grid">${prods.map(p => `<div class="hb-tpl-prod">
        <div class="hb-tpl-name">${esc(p.name)}</div>
        ${p.title ? `<div class="hb-label">Tiêu đề ticket</div>${partHtml(p.title, true)}` : ''}
        ${p.sizes.map(z => `<div class="hb-tpl-size"><div class="hb-label">${z.size ? `Lớp ${esc(z.size)}` : 'Nội dung'}${z.kho ? ` <span class="badge accent">Kho: ${esc(z.kho)}</span>` : ''}</div>${partHtml(z.text, true)}</div>`).join('')}
      </div>`).join('')}</div>
    </div>`;
  }

  function showTable(gid) {
    const st = state[gid];
    const list = st.main.slice(0, st.shown);
    const more = st.main.length - st.shown;
    const h = st.header;
    const khoCols = h.map((_, i) => i).filter(i => /kho ticket/.test(fold(h[i]).replace(/\s+/g, ' ')));
    const body = list.map(bk => khoCols.length ? templateHtml(bk.rows, h, khoCols) : entryHtml(bk.rows, h)).join('');
    return `<div class="hb-entries">${body}</div><div class="hb-group-more">
      ${more > 0 ? `<button class="btn btn-sm" data-showmore="${gid}">Xem thêm ${more} kết quả</button>` : ''}
      ${!more && st.rest.length ? `<button class="btn btn-sm btn-ghost" data-showrest="${gid}">+ ${st.rest.length} kết quả ít liên quan</button>` : ''}</div>`;
  }

  function suggestSection(g) {
    const { header } = g;
    // điền xuống các cột ngắn bị gộp ô (Thời điểm, Sản phẩm, Phân loại…)
    const shortCols = header.map((h, i) => i).filter(i => header[i] && avgLen(g.body, i) <= 25);
    const prev = {};
    const body = g.body.map(r => r.map((c, i) => { if (shortCols.includes(i)) { if (c) prev[i] = c; else c = prev[i] || ''; } return c; }));
    let ti = header.findIndex(h => /chi tiết phân loại|tình huống|vấn đề/i.test(h));
    if (ti < 0) ti = header.findIndex((h, i) => h && !shortCols.includes(i));
    const di = header.findIndex((h, i) => i !== ti && /mô tả/i.test(h));
    const rows = body.map(r => ({ r, s: score(r.join(' '), `${r[ti] || ''} ${di >= 0 ? r[di] || '' : ''}`) })).filter(x => x.s && (r => r[ti] || (di >= 0 && r[di]))(x.r))
      .sort((a, b) => b.s - a.s);
    if (!rows.length) return null;
    state[g.gid] = { rows, ti, di, shortCols, header, shown: Math.min(8, rows.length) };
    return { count: rows.length, html: `<div data-sec="${g.gid}">${suggestList(g.gid)}</div>` };
  }
  function suggestList(gid) {
    const st = state[gid];
    const item = ({ r }) => {
      const badges = st.shortCols.filter(i => i !== st.ti && r[i]).map(i => `<span class="badge" title="${esc(st.header[i])}">${esc(r[i])}</span>`).join('');
      const details = st.header.map((h, i) => ({ h, i, v: r[i] })).filter(x => x.v && x.i !== st.ti && x.i !== st.di && !st.shortCols.includes(x.i));
      return `<details class="hb-sug"><summary>
          <div class="hb-sug-title"><b>${mark(esc(r[st.ti] || r[st.di] || ''), q)}</b>${st.di >= 0 && r[st.di] && r[st.ti] ? `<span class="muted"> — ${mark(esc(r[st.di]), q)}</span>` : ''}</div>
          <div class="hb-sug-badges">${badges}</div></summary>
        <div class="hb-sug-body">${details.map(x => `<div class="hb-sug-field"><div class="hb-label">${esc(x.h || 'Ghi chú')}</div>
          <div class="hb-part"><div class="hb-cell">${mark(linkify(x.v), q)}</div>${x.v.length > 80 ? `<button class="btn btn-sm btn-ghost hb-copy" data-copy>${icon('copy')} Sao chép</button>` : ''}</div></div>`).join('') || '<span class="muted">Không có thêm thông tin</span>'}</div>
      </details>`;
    };
    const more = st.rows.length - st.shown;
    return `<div class="hb-sug-list">${st.rows.slice(0, st.shown).map(item).join('')}</div>
      ${more > 0 ? `<div class="hb-group-more"><button class="btn btn-sm" data-sugmore="${gid}">Xem thêm ${more} gợi ý</button></div>` : ''}`;
  }

  function otherSection(g) {
    const blocks = blocksOf(g.body).map(rows => ({ rows, s: score(rows.flat().join(' '), rows[0].slice(0, 2).join(' ')) })).filter(b => b.s).sort((a, b) => b.s - a.s);
    if (!blocks.length) return null;
    return { count: blocks.length, html: `<div class="hb-entries hb-other-body">${blocks.slice(0, 10).map(b => entryHtml(b.rows, g.header)).join('')}</div>` };
  }

  const search = async () => {
    const seq = ++searchSeq;
    $$('#hb-nav button').forEach(b => b.classList.remove('active'));
    $('#hb-heading').textContent = `Kết quả cho “${q}”`; $('#hb-time').textContent = '';
    $('#hb-body').innerHTML = '<div class="skel"></div><div class="skel w60"></div><div class="skel"></div>';
    let res;
    try { res = await api('/handbook/search', { query: { q } }); } catch (e) { if (seq === searchSeq) $('#hb-body').innerHTML = emptyState(e.message); return; }
    if (seq !== searchSeq) return; // đã có lượt tìm mới hơn
    state = {};
    const secs = { show: [], suggest: [], other: [] };
    res.forEach(g => {
      const sp = splitSheet(g.rows); if (!sp.header) return;
      const mode = modeOf(g.gid);
      const gg = { ...g, header: sp.header, body: sp.body };
      const out = mode === 'show' ? showSection(gg) : mode === 'suggest' ? suggestSection(gg) : otherSection(gg);
      if (out) secs[mode in secs ? mode : 'other'].push({ ...g, ...out });
    });
    const all = [...secs.show, ...secs.suggest, ...secs.other];
    if (!all.length) { $('#hb-body').innerHTML = emptyState(`Không tìm thấy nội dung nào cho “${q}”`); return; }
    $('#hb-time').textContent = '';
    const steps = [...secs.show.map(x => ({ ...x, mode: 'show' })), ...secs.suggest.map(x => ({ ...x, mode: 'suggest' }))];
    const stepHead = (x, i) => { const nm = stepName(x.tab, x.mode); return `<div class="hb-step-head"><span class="hb-step-no">${i + 1}</span>
      <div><h3>${esc(nm.title)} <span class="badge">${x.count}</span></h3>${nm.sub ? `<div class="small muted">${esc(nm.sub)}</div>` : ''}</div>
      <button class="btn btn-sm btn-ghost" data-open="${x.gid}">Mở sheet ${icon('chevR')}</button></div>`; };
    $('#hb-body').innerHTML = `
      ${steps.map((x, i) => `<section class="hb-step" id="sec-${x.gid}">${stepHead(x, i)}<div class="hb-step-body">${x.html}</div></section>`).join('')}
      ${secs.other.length ? `<section class="hb-step hb-step-other"><div class="hb-step-head"><span class="hb-step-no">+</span><div><h3>Nội dung liên quan khác</h3><div class="small muted">Bấm để mở</div></div></div>
        ${secs.other.map(s => `<details class="hb-other" id="sec-${s.gid}"><summary><b>${esc(s.tab)}</b> <span class="badge">${s.count}</span></summary>${s.html}</details>`).join('')}</section>` : ''}`;
  };

  let timer;
  $('#hb-q').oninput = e => {
    q = e.target.value.trim(); $('#hb-clear').hidden = !q;
    clearTimeout(timer);
    if (q.length >= 2) timer = setTimeout(search, 350);
    else if (!q) { searchSeq++; loadTab(); }
  };
  $('#hb-q').onkeydown = e => { if (e.key === 'Enter' && q.length >= 2) { clearTimeout(timer); search(); } if (e.key === 'Escape') $('#hb-clear').click(); };
  $('#hb-clear').onclick = () => { $('#hb-q').value = ''; q = ''; $('#hb-clear').hidden = true; searchSeq++; loadTab(); $('#hb-q').focus(); };
  const openTab = g => { $('#hb-q').value = ''; q = ''; $('#hb-clear').hidden = true; searchSeq++; gid = g; loadTab(); window.scrollTo(0, 0); };
  $('#hb-nav').onclick = e => { const b = e.target.closest('[data-gid]'); if (b) openTab(b.dataset.gid); };
  $('#hb-select').onchange = e => openTab(e.target.value);
  $('#hb-toggle').onclick = () => { const h = $('#hb').classList.toggle('nav-hidden'); store.set('hb_nav', h ? 'hide' : 'show'); syncToggle(); };
  $('#hb-refresh').onclick = e => run(e.currentTarget, () => (q.length >= 2 ? search() : loadTab(true)));
  $('#hb-body').onclick = e => {
    const t = e.target;
    const c = t.closest('[data-copy]'), o = t.closest('[data-open]'), m = t.closest('[data-more]'), j = t.closest('[data-jump]');
    const sm = t.closest('[data-showmore]'), sr = t.closest('[data-showrest]'), gm = t.closest('[data-sugmore]');
    if (c) { e.preventDefault(); navigator.clipboard.writeText(c.previousElementSibling.innerText).then(() => toast('Đã sao chép'), () => toast('Trình duyệt chặn sao chép', 'error')); }
    if (o) openTab(o.dataset.open);
    if (m) { limit += 200; paintTab(); }
    if (j) { const el = $(`#sec-${j.dataset.jump}`); if (el) { if (el.tagName === 'DETAILS') el.open = true; el.scrollIntoView({ behavior: 'smooth', block: 'start' }); } }
    if (sm) { const st = state[sm.dataset.showmore]; st.shown = st.main.length; $(`[data-sec="${sm.dataset.showmore}"]`).innerHTML = showTable(sm.dataset.showmore); }
    if (sr) { const st = state[sr.dataset.showrest]; st.main = st.main.concat(st.rest); st.rest = []; st.shown = st.main.length; $(`[data-sec="${sr.dataset.showrest}"]`).innerHTML = showTable(sr.dataset.showrest); }
    if (gm) { const st = state[gm.dataset.sugmore]; st.shown = st.rows.length; $(`[data-sec="${gm.dataset.sugmore}"]`).innerHTML = suggestList(gm.dataset.sugmore); }
  };
  if (idx.warning) toast('Không kết nối được Google Sheet, đang hiển thị bản lưu tạm', 'info');
  if (gid) loadTab(); else $('#hb-body').innerHTML = emptyState('Chưa có mục nào');
}

/* =========================================================
   7. Tra cứu lương
   ========================================================= */
async function pageSalary(v) {
  const months = await api('/ctv/salary/months');
  v.innerHTML = pageHead('Tra cứu lương', 'Bảng lương được chốt vào ngày 02 hàng tháng. Thắc mắc vui lòng liên hệ quản lý team.') +
    (months.length ? `<div class="filters"><select class="input" id="ym">${months.map(m => `<option value="${m}">${fmtYM(m)}</option>`).join('')}</select></div><div id="body"></div>`
      : `<div class="card">${emptyState('Chưa có bảng lương nào được công bố')}<p class="small muted" style="text-align:center;padding:0 16px 20px">Giờ làm đã được duyệt xem ở mục <a href="#history">Chấm công</a>. Lương hiện ở đây sau khi quản lý duyệt &amp; công bố bảng lương tháng.</p>${''}</div>`);
  if (!months.length) return;
  const load = async () => {
    $('#body').innerHTML = loading();
    const s = await api('/ctv/salary', { query: { ym: $('#ym').value } });
    const [y, m] = s.ym.split('-').map(Number);
    const first = (new Date(y, m - 1, 1).getDay() + 6) % 7, days = new Date(y, m, 0).getDate();
    const perDay = {}; s.rows.forEach(r => { perDay[r.date] = (perDay[r.date] || 0) + hoursOf(r); });
    let cal = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'].map(d => `<div class="dh">${d}</div>`).join('') + '<div class="d blank"></div>'.repeat(first);
    for (let d = 1; d <= days; d++) { const k = `${s.ym}-${pad(d)}`; cal += `<div class="d ${perDay[k] ? 'w' : ''}"><b>${d}</b>${perDay[k] ? perDay[k] + 'h' : ''}</div>`; }
    $('#body').innerHTML = `
      <div class="card card-pad salary-hero"><div><div class="muted">Thực nhận ${fmtYM(s.ym).toLowerCase()}</div><div class="amount">${money(s.total)}</div>
        <div class="muted">${s.shifts} ca · ${s.hours} giờ</div></div></div>
      <div class="grid-2" style="margin-top:16px">
        <div class="card card-pad"><h2 style="font-size:15px;margin-bottom:8px">Chi tiết</h2><table class="lines">
          <tr><td>Lương theo giờ (${s.hours} giờ)</td><td>${money(s.base)}</td></tr>
          <tr><td>Lương CTV gọi / thưởng</td><td class="plus">+ ${money(s.bonus)}</td></tr>
          <tr><td>Phạt lỗi QC (${s.qc_count} lỗi)</td><td class="minus">− ${money(s.qc_fine)}</td></tr>
          <tr><td>Khấu trừ khác</td><td class="minus">− ${money(s.deduction)}</td></tr>
          <tr class="total"><td>Thực nhận</td><td>${money(s.total)}</td></tr></table>
          ${s.note ? `<p class="muted small" style="margin-top:8px">Ghi chú: ${esc(s.note)}</p>` : ''}</div>
        <div class="card card-pad"><h2 style="font-size:15px;margin-bottom:12px">Ngày công</h2><div class="cal">${cal}</div></div>
      </div>
      ${s.qc.length ? `<div class="card"><div class="card-head"><h2>Lỗi QC trong kỳ</h2><span class="badge red">− ${money(s.qc_fine)}</span></div><div id="qc"></div></div>` : ''}
      <div class="card"><div class="card-head"><h2>Ca đã làm</h2></div><div id="rows"></div></div>`;
    if (s.qc.length) dataTable($('#qc'), s.qc, QC_COLUMNS, { pageSize: 20 });
    dataTable($('#rows'), s.rows, [
      { label: 'Ngày', render: r => `${dowOf(r.date)} ${fmtDate(r.date)}` },
      { label: 'Ca', render: r => `${r.start}–${r.end}` },
      { label: 'Vị trí', render: r => esc(r.position || '') },
      { label: 'Giờ', cls: 'right mono', render: r => hoursOf(r) },
    ], { pageSize: 15 });
  };
  $('#ym').onchange = load; load();
}

const QC_COLUMNS = [
  { label: 'Ngày', render: r => `<span class="nowrap">${fmtDate(r.date)}</span>` },
  { label: 'Lỗi', render: r => `<div style="white-space:pre-wrap;max-width:520px">${esc(r.error || '—')}</div>${r.note ? `<div class="small muted" style="white-space:pre-wrap;margin-top:4px">${esc(r.note)}</div>` : ''}` },
  { label: 'Hình thức', render: r => `${esc(r.penalty || '')}${r.category ? `<br><span class="badge">${esc(r.category)}</span>` : ''}` },
  { label: 'Ticket', render: r => /^https?:/.test(r.ticket || '') ? `<a href="${esc(r.ticket)}" target="_blank" rel="noopener">Mở</a>` : esc(r.ticket || '—') },
  { label: 'Tiền phạt', cls: 'right mono', render: r => r.amount ? `<span class="minus">−${money(r.amount)}</span>` : '<span class="muted">Nhắc nhở</span>' },
];

/* =========================================================
   8. Lịch sử làm việc · 9. Nhật ký
   ========================================================= */
async function pageHistory(v) {
  v.innerHTML = pageHead('Chấm công', 'Giờ làm được admin duyệt sau mỗi ngày. Chỉ ca đã chấm công mới được tính lương.', `<button class="btn" id="exp">${icon('download')} Xuất Excel</button>`) + `
    <div class="filters"><select class="input" id="ym">${monthOptions(ymOf(new Date()), -12, 0)}</select></div>
    <div class="stats" id="stats"></div><div class="card" id="body">${loading()}</div>`;
  let rows = [];
  const load = async () => {
    rows = await api('/ctv/history', { query: { ym: $('#ym').value } });
    const done = rows.filter(r => r.approved_at), wait = rows.filter(r => !r.approved_at);
    $('#stats').innerHTML = `
      <div class="stat"><div class="label">Ca được giao</div><div class="value">${rows.length}</div></div>
      <div class="stat"><div class="label">Đã chấm công</div><div class="value">${done.length}</div></div>
      <div class="stat"><div class="label">Chờ duyệt</div><div class="value ${wait.length ? 'accent' : ''}">${wait.length}</div></div>
      <div class="stat"><div class="label">Giờ được tính lương</div><div class="value">${done.reduce((a, r) => a + hoursOf(r), 0)}</div></div>`;
    dataTable($('#body'), rows, [
      { label: 'Ngày', render: r => `<span class="nowrap">${dowOf(r.date)} ${fmtDate(r.date)}</span>` },
      { label: 'Ca', render: r => `${r.start}–${r.end}` },
      { label: 'Vị trí', render: r => `${esc(r.position || '')}<br><span class="small muted">${esc(r.team || '')}</span>` },
      { label: 'Giờ', cls: 'right mono', render: r => hoursOf(r) },
      { label: 'Trạng thái', render: attStatus },
      { label: 'Điều chỉnh / ghi chú', render: r => `${planDiff(r) ? `<div class="small">${planDiff(r)}</div>` : ''}${r.note ? `<div class="small muted">${esc(r.note)}</div>` : ''}` },
    ], { empty: 'Không có ca nào trong tháng này' });
  };
  $('#ym').onchange = load;
  $('#exp').onclick = () => downloadCSV(`lich-su-${$('#ym').value}.csv`, ['Ngày', 'Ca', 'Team', 'Vị trí', 'Số giờ', 'Trạng thái', 'Ghi chú'],
    rows.map(r => [fmtDate(r.date), `${r.start}-${r.end}`, r.team, r.position, hoursOf(r), r.approved_at ? 'Đã chấm công' : 'Chờ duyệt', r.note]));
  load();
}

async function pageLogs(v) {
  v.innerHTML = pageHead('Nhật ký hoạt động', 'Lịch sử thao tác của bạn trên hệ thống.') + `<div class="card" id="body">${loading()}</div>`;
  const rows = await api('/ctv/logs');
  dataTable($('#body'), rows, [
    { label: 'Thời gian', render: r => `<span class="nowrap muted">${fmtDate(r.created_at.slice(0, 10))} ${r.created_at.slice(11, 16)}</span>` },
    { label: 'Hành động', render: r => esc(r.action) },
  ]);
}

/* ---------- khởi động ---------- */
App.start({
  role: 'ctv', brand: 'Cổng CTV', subtitle: 'Cộng tác viên', loginHint: 'Tên đăng nhập dạng ctv.tenban (VD ctv.haott). Mật khẩu ban đầu do quản lý cấp.',
  nav: [
    { group: 'Tổng quan', items: [{ id: 'dashboard', label: 'Tổng quan', icon: 'home', render: pageDashboard }] },
    { group: 'Lịch làm', items: [
      { id: 'schedule', label: 'Lịch làm việc', icon: 'calendar', render: pageSchedule },
      { id: 'availability', label: 'Đăng ký lịch rảnh', icon: 'checkSquare', render: pageAvailability },
      { id: 'team', label: 'Lịch team theo ngày', icon: 'users', render: pageTeam },
      { id: 'swaps', label: 'Phiếu đổi ca', icon: 'swap', render: pageSwaps },
    ] },
    { group: 'Tra cứu', items: [{ id: 'handbook', label: 'Cẩm nang', icon: 'book', render: pageHandbook }] },
    { group: 'Cá nhân', items: [
      { id: 'salary', label: 'Tra cứu lương', icon: 'wallet', render: pageSalary },
      { id: 'history', label: 'Chấm công', icon: 'clock', render: pageHistory },
      { id: 'logs', label: 'Nhật ký hoạt động', icon: 'list', render: pageLogs },
    ] },
  ],
});
