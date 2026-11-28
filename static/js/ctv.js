/* =========================================================
   Trang CTV
   ========================================================= */

const fmtSecs = s => { const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60; return `${h ? h + 'g ' : ''}${m}p ${pad(x)}s`; };

const cdText = st => `${st.key === 'wait' ? 'Bắt đầu sau ' : 'Còn '}${fmtSecs(st.secs)}${st.key === 'working' ? ' là hết ca' : ''}`;
function todayCard(s) {
  const st = shiftState(s);
  return `<div class="today-card">
    <div style="display:flex;justify-content:space-between;align-items:center"><span class="time"><small class="muted" style="font-size:12px;font-weight:500">Vào</small> ${s.start} – <small class="muted" style="font-size:12px;font-weight:500">Ra</small> ${s.end}</span><span class="badge ${st.badge}">${st.label}</span></div>
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
        <dt>Giờ vào – ra</dt><dd><b>${s.start}</b> – <b>${s.end}</b> (${hoursOf(s)} giờ)</dd>
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
      <div class="field"><label>Người làm thay / đổi ca với</label>
        <select class="input" id="sw-to">${cands.length ? '<option value="">— Chọn người —</option>' + cands.map((c, i) => `<option value="${i}">${esc(c.username)} · ${esc(c.name)}${c.swap_schedule_id ? ` — đổi lấy ca ${c.start}–${c.end}${c.position ? ' · ' + esc(c.position) : ''}` : ' — làm thay'}</option>`).join('') : '<option value="">Không có ai làm thay hoặc đổi ca được</option>'}</select>
        <span class="hint">Gõ vài ký tự tên / username để tìm · <b>làm thay</b>: người đó nhận ca của bạn · <b>đổi lấy ca …</b>: hai bạn đổi ca cho nhau (VD ca full ↔ ca gãy)</span></div>
      <p class="small" id="sw-info" style="margin-top:-6px"></p>
      <div class="field"><label>Lý do</label><textarea class="input" rows="3" id="sw-reason" placeholder="VD: Trùng lịch thi"></textarea></div>`,
    footer: `<button class="btn" data-close>Huỷ</button><button class="btn btn-primary" id="sw-ok">Gửi phiếu</button>`,
    onOpen(el, close) {
      const pick = () => cands[$('#sw-to', el).value];
      $('#sw-to', el).addEventListener('change', () => {
        const c = pick();
        $('#sw-info', el).innerHTML = !c ? '' : c.swap_schedule_id
          ? `Sau khi duyệt: <b>${esc(c.username)}</b> làm ca ${s.start}–${s.end} của bạn, <b>bạn</b> làm ca ${c.start}–${c.end} của ${esc(c.username)}.`
          : `Sau khi duyệt: <b>${esc(c.username)}</b> làm ca ${s.start}–${s.end} thay bạn.`;
      });
      if (cands.length) searchSelect($('#sw-to', el), { placeholder: 'Tìm người (VD: ha, ctv.dung…)' });
      $('#sw-ok', el).onclick = e => run(e.currentTarget, async () => {
        const c = pick();
        if (!c) throw new Error('Vui lòng chọn người làm thay / đổi ca');
        await api('/ctv/swaps', { method: 'POST', body: { schedule_id: s.id, to_user: c.id, swap_schedule_id: c.swap_schedule_id, reason: $('#sw-reason', el).value } });
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
  const [d, today, notifs] = await Promise.all([api('/ctv/dashboard'), api('/ctv/schedule', { query: { start: todayStr(), end: todayStr() } }), api('/notifications').catch(() => [])]);
  const unread = notifs.filter(n => n.unread);
  const reload = () => App.route();
  v.innerHTML = pageHead(`Xin chào, ${esc(App.user.name.split(' ').pop())}`, 'Tổng quan ca trực và giờ làm của bạn trong tháng này.') + `
    ${unread.length ? `<div class="card card-pad notif-box"><div class="card-head" style="padding:0 0 6px;border:0"><h2>${icon('bell')} ${unread.length} thông báo mới</h2><a class="btn btn-sm" href="#notifications">Xem tất cả</a></div>
      ${unread.slice(0, 3).map(notifItem).join('')}</div>` : ''}
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
        <div class="day-body">${mainShifts().map(sh => {
          const label = esc(sh.name.replace(/^ca\s+/i, ''));
          const inSlot = items.filter(s => shiftGroup(s.shift_code) === sh.code);  // ca tối gãy nằm trong ô Tối
          if (!inSlot.length) return `<div class="slot-row"><span class="slot-name">${label}</span><div class="slot-empty">Trống</div></div>`;
          return `<div class="slot-row"><span class="slot-name">${label}</span>${inSlot.map(s => {
            const st = shiftState(s);
            return `<button class="chip ${st.key === 'done' ? 'done' : st.key === 'missed' ? 'missed' : ''}" data-id="${s.id}">
              ${s.shift_code !== sh.code ? `<span class="badge" style="margin-bottom:3px">${esc(shortShift(s.shift_code))}</span>` : ''}<b>Vào ${s.start} · Ra ${s.end}</b>${esc(s.position || '')}<br><span class="who">${st.label}</span></button>`;
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
  const thisMon = mondayOf(new Date()), now = new Date();
  const byMonth = App.meta.reg_mode === 'month';   // admin chọn mở đăng ký theo tháng hay theo tuần
  const monthOf = i => ymOf(new Date(now.getFullYear(), now.getMonth() + i, 1));
  const weeks = [0, 1, 2].map(i => ymd(addDays(thisMon, 7 * (i + 1))));
  const opts = byMonth ? [0, 1, 2].map(monthOf) : [ymd(thisMon), ...weeks];
  // theo tháng: hạn chót 19:00 ngày 29 của tháng trước (tháng 2 → ngày cuối tháng)
  const monthDeadline = ym => { const y = +ym.slice(0, 4), m = +ym.slice(5, 7); return new Date(y, m - 2, Math.min(29, new Date(y, m - 1, 0).getDate()), 19, 0); };
  const deadlineOf = k => byMonth ? monthDeadline(k) : regDeadline(k);
  let ws = byMonth ? (new Date() < monthDeadline(opts[1]) ? opts[1] : opts[2]) : (weeks.find(w => regDeadline(w) > new Date()) || weeks[0]);
  let state = null;
  const periodName = k => byMonth ? fmtYM(k).toLowerCase() : 'tuần ' + weekLabel(k);

  v.innerHTML = pageHead('Đăng ký lịch rảnh', byMonth
      ? 'Đăng ký theo tháng: chọn những ca bạn có thể làm hằng tuần trong tháng rồi bấm “Gửi đăng ký”. Hạn chót 19:00 ngày 29 của tháng trước; mỗi tuần hệ thống tự chia ca theo lịch này và quản lý duyệt.'
      : 'Đăng ký theo tuần: chọn những ca bạn có thể làm rồi bấm “Gửi đăng ký”. Hạn chót 19:00 Chủ nhật, 20:00 hệ thống tự chia ca và quản lý duyệt.') + `
    <div class="filters">
      <div class="seg" id="wk">${opts.map(w => `<button data-w="${w}">${byMonth ? (w === opts[0] ? 'Tháng này' : fmtYM(w)) : w === ymd(thisMon) ? 'Tuần này' : 'Tuần ' + weekLabel(w)}</button>`).join('')}</div>
      <span id="status"></span><span style="flex:1"></span>
      <button class="btn" id="copy">${icon('copy')} Dùng lịch ${byMonth ? 'tháng' : 'tuần'} trước</button>
    </div>
    <div id="dl"></div>
    <div class="card"><div class="table-wrap" id="grid">${loading()}</div>
      <div class="card-pad" style="border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
        <div class="legend"><span id="summary"></span></div>
        <div class="actions"><button class="btn btn-primary" id="submit">Gửi đăng ký</button></div>
      </div></div>`;

  // theo tháng: đã gửi là chốt (muốn sửa nhờ quản lý mở khoá); theo tuần: sửa được tới hạn chót
  const locked = () => !state.open || (byMonth && state.status === 'submitted');
  const dayOf = k => ymd(addDays(parseDate(ws), k - 1));
  /* ghi chú ca tối (VD xin vào muộn / ra sớm): lưu trong từng slot đã chọn của ngày đó */
  const noteKeys = (k, m) => [m, ...regVariants(m)].filter((s, i, a) => a.findIndex(x => x.code === s.code) === i)
    .map(s => `${k}-${s.code}`).filter(x => state.slots[x]);
  const noteOf = (k, m) => (noteKeys(k, m).map(x => state.slots[x].note).find(Boolean) || '');
  const noteBtn = (k, m, L) => {
    if (shiftGroup(m.code) !== 'toi' || !noteKeys(k, m).length) return '';
    const n = noteOf(k, m);
    if (L) return n ? `<div class="av-note has" title="${esc(n)}">📝 ${esc(n)}</div>` : '';
    return `<button type="button" class="av-note ${n ? 'has' : ''}" data-note="${k}|${m.code}" title="${n ? esc(n) : 'Ghi chú nếu muốn vào muộn / ra sớm'}">${n ? '📝 ' + esc(n) : '+ Ghi chú in/out sớm'}</button>`;
  };

  function paint() {
    $$('#wk button').forEach(b => b.classList.toggle('active', b.dataset.w === ws));
    const dl = regDeadline(ws), open = state.open;
    $('#status').innerHTML = !open ? `<span class="badge">${byMonth && state.status !== 'submitted' ? 'Chưa mở / đã đóng đăng ký' : 'Đã chốt đăng ký'}</span>`
      : state.status === 'submitted' ? `<span class="badge green">${byMonth ? 'Đã gửi — đã chốt' : 'Đã gửi — vẫn sửa được tới hạn chót'}</span>`
      : state.status === 'draft' ? '<span class="badge amber">Chưa gửi</span>' : '<span class="badge blue">Đang mở đăng ký</span>';
    $('#dl').innerHTML = byMonth
      ? (open && state.status !== 'submitted'
        ? `<div class="notice" style="border-color:var(--accent);background:color-mix(in srgb,var(--accent) 6%,var(--surface))">⏰ Đăng ký <b>${periodName(ws)}</b> — hạn chót <b>19:00 ngày ${fmtDM(ymd(monthDeadline(ws)))}</b>, còn <b id="left">${fmtLeft(monthDeadline(ws) - new Date())}</b>. Chọn những ca bạn rảnh <b>hằng tuần</b> trong tháng. Sau khi gửi, lịch được chốt — muốn sửa thì liên hệ quản lý.</div>`
        : `<div class="notice" style="border-color:var(--border);background:var(--surface-2)">${state.status === 'submitted' ? `Bạn đã gửi đăng ký ${periodName(ws)}. Muốn sửa thì liên hệ quản lý để mở khoá.` : `Quản lý chưa mở (hoặc đã đóng) đăng ký ${periodName(ws)}.`} Lịch làm sẽ hiện ở mục <a href="#schedule">Lịch làm việc</a> sau khi quản lý duyệt.</div>`)
      : open
      ? `<div class="notice" style="border-color:var(--accent);background:color-mix(in srgb,var(--accent) 6%,var(--surface))">⏰ Hạn chót <b>19:00 Chủ nhật ${fmtDM(ymd(dl))}</b> — còn <b id="left">${fmtLeft(dl - new Date())}</b>. Sau đó hệ thống tự chia ca lúc 20:00.</div>`
      : `<div class="notice" style="border-color:var(--border);background:var(--surface-2)">Tuần ${weekLabel(ws)} đã chốt đăng ký. Lịch làm sẽ hiện ở mục <a href="#schedule">Lịch làm việc</a> sau khi quản lý duyệt.</div>`;
    ['#copy', '#submit'].forEach(s => { $(s).disabled = locked(); });
    $('#submit').textContent = state.status === 'submitted' ? 'Cập nhật đăng ký' : 'Gửi đăng ký';
    const L = locked();
    $('#grid').innerHTML = `<div class="av-grid"><div></div>${WEEK_KEYS.map(k => `<div class="h">${WEEK_LABEL[k]}${byMonth ? '' : `<br><span class="muted small">${fmtDM(dayOf(k))}</span>`}</div>`).join('')}
      ${mainShifts().map(m => {
        const vars = regVariants(m);   // Tối: chỉ Ca full + 1 ô Ca gãy (gãy mấy giờ do admin xếp)
        if (vars.length < 2) {   // ca thường: 1 ô / ngày
          return `<div class="rowh">${esc(m.name)}<span>${m.start}–${m.end}</span></div>${WEEK_KEYS.map(k => {
            const key = `${k}-${m.code}`; const on = !!state.slots[key];
            const ni = needInfo((state.counts[key] || 0) + (on ? 1 : 0), m, true);
            const cnt = `<span class="need ${ni.cls}" title="Số CTV đã đăng ký${ni.target ? ' / cần ' + ni.target : ''}">${ni.text} CTV${ni.missing ? ` · thiếu ${ni.missing}` : ''}</span>`;
            const attrs = L ? '' : `data-toggle="${key}" role="button" tabindex="0" aria-pressed="${on}" aria-label="${esc(m.name)} ${WEEK_LABEL[k]}"`;
            return on ? `<div class="slot-split"><div class="slot on ${L ? 'locked' : ''}" ${attrs}><b>✓ Rảnh</b>${cnt}</div>${noteBtn(k, m, L)}</div>`
              : `<div class="slot ${L ? 'locked' : ''}" ${attrs}>${L ? '—' : '+ Rảnh'}${cnt}</div>`;
          }).join('')}`;
        }
        // ca có nhiều lựa chọn (Tối: Ca full / Ca gãy): CTV chọn 1 hoặc cả 2, admin sẽ chọn ca khi chia lịch
        return `<div class="rowh">${esc(m.name)}${vars.map(s => `<span>${esc(variantLabel(s))}</span>`).join('')}</div>${WEEK_KEYS.map(k => {
          const mine = vars.some(s => state.slots[`${k}-${s.code}`]);
          const ni = needInfo((state.counts[`g:${k}-${m.code}`] || 0) + (mine ? 1 : 0), m, true);
          return `<div class="slot-split">${vars.map(s => {
            const key = `${k}-${s.code}`, on = !!state.slots[key];
            const attrs = L ? '' : `data-toggle="${key}" role="button" tabindex="0" aria-pressed="${on}" aria-label="${esc(m.name)} ${esc(variantLabel(s))} ${WEEK_LABEL[k]}"`;
            return `<div class="slot ${on ? 'on' : ''} ${L ? 'locked' : ''}" ${attrs} title="${esc(variantLabel(s))}"><b>${on ? '✓ ' : L ? '' : '+ '}${esc(variantLabel(s).replace(/^Ca\s+/i, ''))}</b></div>`;
          }).join('')}<span class="need ${ni.cls}" title="Số CTV đã đăng ký ca ${esc(m.name)}${ni.target ? ' / cần ' + ni.target : ''}">${ni.text} CTV${ni.missing ? ` · thiếu ${ni.missing}` : ''}</span>${noteBtn(k, m, L)}</div>`;
        }).join('')}`;
      }).join('')}</div>`;
    // 1 ngày đăng ký cả Full lẫn Gãy vẫn tính là 1 ca, lấy giờ dài nhất
    const perCell = {};
    Object.entries(state.slots).forEach(([key, x]) => {
      const k = key.slice(0, key.indexOf('-')), g = shiftGroup(key.slice(key.indexOf('-') + 1));
      const h = (t2m(x.end) - t2m(x.start)) / 60; perCell[`${k}-${g}`] = Math.max(perCell[`${k}-${g}`] || 0, h);
    });
    const n = Object.keys(perCell).length;
    const hrs = Object.values(perCell).reduce((a, h) => a + h, 0);
    $('#summary').textContent = n ? `${n} ca rảnh · khoảng ${hrs} giờ` + (state.updated_at ? ` · cập nhật ${fmtDate(state.updated_at.slice(0, 10))} ${state.updated_at.slice(11, 16)}` : '') : 'Chưa chọn ca nào';
  }

  async function load() {
    $('#grid').innerHTML = loading();
    state = await api('/ctv/availability', { query: { ym: ws } });
    state.slots = foldGay(state.slots);
    state.counts = state.counts || {};
    paint();
  }

  const timer = setInterval(() => { const el = $('#left'); if (el) el.textContent = fmtLeft(deadlineOf(ws) - new Date()); }, 30000);
  App.onLeave(() => clearInterval(timer));
  $('#wk').onclick = e => { const b = e.target.closest('[data-w]'); if (b) { ws = b.dataset.w; load(); } };
  $('#grid').addEventListener('click', e => {
    if (locked()) return;
    const nb = e.target.closest('[data-note]');
    if (nb) return noteDialog(...nb.dataset.note.split('|'));
    const t = e.target.closest('[data-toggle]'); if (!t) return;
    const key = t.dataset.toggle;
    if (state.slots[key]) delete state.slots[key];
    else {
      const s = shifts.find(x => x.code === key.slice(key.indexOf('-') + 1)), k = key.slice(0, key.indexOf('-'));
      // chọn thêm Full / Gãy cùng ngày: giữ ghi chú đã viết
      const sib = Object.entries(state.slots).find(([x, v]) => v.note && x.startsWith(k + '-') && shiftGroup(x.slice(x.indexOf('-') + 1)) === shiftGroup(s.code));
      state.slots[key] = { start: s.start, end: s.end, ...(sib ? { note: sib[1].note } : {}) };
    }
    if (state.status === 'empty') state.status = 'draft';
    paint();
    const again = $(`[data-toggle="${key}"]`); again && again.focus();
  });
  function noteDialog(k, code) {
    const m = shifts.find(x => x.code === code);
    modal({ title: `Ghi chú ca ${esc(m.name)} · ${WEEK_LABEL[k]}${byMonth ? ' hằng tuần' : ' ' + fmtDM(dayOf(+k))}`,
      body: `<div class="field"><label>Muốn vào muộn / ra sớm? Ghi rõ giờ để quản lý xếp ca</label>
          <input class="input" id="nt" maxlength="120" value="${esc(noteOf(k, m))}" placeholder="VD: Xin ra sớm lúc 21:00"></div>
        <div class="actions">${['Xin vào muộn 18:30', 'Xin ra sớm 21:00', 'Xin ra sớm 21:30'].map(t => `<button type="button" class="btn btn-sm" data-q="${t}">${t}</button>`).join('')}</div>`,
      footer: `<button class="btn" id="nt-clear">Xoá ghi chú</button><button class="btn btn-primary" id="nt-ok">Lưu ghi chú</button>`,
      onOpen(el, close) {
        const inp = $('#nt', el); inp.focus();
        el.addEventListener('click', ev => { const q = ev.target.closest('[data-q]'); if (q) { inp.value = q.dataset.q; inp.focus(); } });
        const save = val => {
          noteKeys(k, m).forEach(x => { if (val) state.slots[x].note = val; else delete state.slots[x].note; });
          if (state.status === 'empty') state.status = 'draft';
          close(); paint();
          toast(state.status === 'submitted' ? 'Nhớ bấm “Cập nhật đăng ký” để gửi ghi chú' : 'Nhớ bấm “Gửi đăng ký”', 'info');
        };
        $('#nt-ok', el).onclick = () => save(inp.value.trim().replace(/\s+/g, ' ').slice(0, 120));
        $('#nt-clear', el).onclick = () => save('');
        inp.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); $('#nt-ok', el).click(); } });
      } });
  }
  $('#grid').addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && e.target.dataset.toggle) { e.preventDefault(); e.target.click(); } });
  $('#submit').onclick = e => {
    if (!Object.keys(state.slots).length) return toast('Bạn chưa chọn ca rảnh nào', 'error');
    run(e.currentTarget, async () => {
      await api('/ctv/availability', { method: 'PUT', body: { ym: ws, slots: state.slots, submit: true } });
      toast(`Đã gửi đăng ký ${periodName(ws)}`); load();
    });
  };
  $('#copy').onclick = async () => {
    const prevWs = byMonth ? ymOf(new Date(+ws.slice(0, 4), +ws.slice(5, 7) - 2, 1)) : ymd(addDays(parseDate(ws), -7));
    let prev = await api('/ctv/availability', { query: { ym: prevWs } });
    if (!byMonth && !Object.keys(prev.slots).length) prev = await api('/ctv/availability', { query: { ym: prevWs.slice(0, 7) } }); // lịch theo tháng cũ
    if (!Object.keys(prev.slots).length) return toast(`${byMonth ? 'Tháng' : 'Tuần'} trước bạn chưa đăng ký lịch`, 'info');
    state.slots = foldGay(prev.slots); if (state.status === 'empty') state.status = 'draft';
    paint(); toast('Đã sao chép. Nhớ bấm “Gửi đăng ký”.', 'info');
  };
  load();
}

/* =========================================================
   4. Lịch team theo ngày
   ========================================================= */
async function pageTeam(v) {
  let day = new Date(), mode = store.get('team_mode') || 'day';
  const isMon = p => /monitor/i.test(p.position || '');
  const sortP = (a, b) => isMon(b) - isMon(a) || a.start.localeCompare(b.start) || a.username.localeCompare(b.username);
  const tags = (p, sh) => `${isMon(p) ? ' <span class="tag-mon">Monitor</span>' : ''}${p.shift_code !== sh.code ? ` <span class="tag-mon">${esc(shortShift(p.shift_code))}</span>` : ''}`;
  v.innerHTML = pageHead('Lịch team', 'Xem ai trực cùng ca theo ngày hoặc cả tuần để tiện phối hợp.') + `
    <div class="filters">
      <div class="seg" id="mode"><button data-m="day">Theo ngày</button><button data-m="week">Theo tuần</button></div>
      <button class="btn btn-icon" id="prev" aria-label="Lùi">${icon('chevL')}</button>
      <input type="date" class="input" id="day">
      <button class="btn btn-icon" id="next" aria-label="Tiến">${icon('chevR')}</button>
      <button class="btn" id="today">Hôm nay</button>
      <strong id="range" style="margin-left:4px"></strong>
    </div><div id="body">${loading()}</div>`;

  const loadDay = async () => {
    const list = await api('/team-day', { query: { day: ymd(day) } });
    if (!list.length) { $('#body').innerHTML = `<div class="card">${emptyState('Không có ai được xếp ca trong ngày này')}</div>`; return; }
    // mỗi ca 1 hàng chung tất cả CTV; người trực Monitor có nhãn; ca tối gãy nằm chung ca Tối
    $('#body').innerHTML = mainShifts().map(sh => {
      const inShift = list.filter(s => shiftGroup(s.shift_code) === sh.code).sort(sortP);
      if (!inShift.length) return '';
      return `<div class="card" style="margin-bottom:16px"><div class="card-head"><h2>${esc(sh.name)} <span class="muted" style="font-weight:400">${sh.start}–${sh.end}</span></h2><span class="badge">${inShift.length} người</span></div>
        <div class="team-block"><div class="people">${inShift.map(p => `
          <div class="person ${p.user_id === App.user.id ? 'me' : ''}" title="${esc(p.name)} · ${esc(p.position || '')}${p.team ? ' · ' + esc(p.team) : ''}"><div class="avatar">${initials(p.name)}</div>
            <div>${esc(p.username)}${tags(p, sh)} <small>${p.start}–${p.end}</small></div></div>`).join('')}</div></div></div>`;
    }).join('');
  };

  const loadWeek = async () => {
    const ws = mondayOf(day), days = Array.from({ length: 7 }, (_, i) => ymd(addDays(ws, i)));
    $('#range').textContent = `${fmtDate(days[0])} – ${fmtDate(days[6])}`;
    const list = await api('/team-week', { query: { start: days[0] } });
    if (!list.length) { $('#body').innerHTML = `<div class="card">${emptyState('Tuần này chưa có lịch trực')}</div>`; return; }
    const cell = (d, sh) => {
      const ps = list.filter(s => s.date === d && shiftGroup(s.shift_code) === sh.code).sort(sortP);
      return ps.length ? ps.map(p => `<div class="tw-p ${p.user_id === App.user.id ? 'me' : ''}" title="${esc(p.name)} · ${esc(p.position || '')}">
          <span>${esc(p.username.replace(/^ctv\./, ''))}${tags(p, sh)}</span>${p.start !== sh.start || p.end !== sh.end ? `<small>${p.start}–${p.end}</small>` : ''}</div>`).join('')
        : '<span class="muted small">—</span>';
    };
    $('#body').innerHTML = `<div class="card"><div class="table-wrap"><table class="table tw">
      <thead><tr><th></th>${days.map(d => `<th class="${d === todayStr() ? 'tw-today' : ''}">${dowOf(d)}<br><b>${fmtDM(d)}</b></th>`).join('')}</tr></thead>
      <tbody>${mainShifts().map(sh => `<tr><th class="tw-shift">${esc(sh.name.replace(/^ca\s+/i, ''))}<br><span class="muted small">${sh.start}–${sh.end}</span></th>
        ${days.map(d => `<td class="${d === todayStr() ? 'tw-today' : ''}">${cell(d, sh)}</td>`).join('')}</tr>`).join('')}</tbody></table></div></div>
      <p class="small muted" style="margin-top:8px">Tên của bạn được tô màu. Giờ nhỏ bên dưới tên là giờ làm khác giờ chuẩn của ca (ca gãy, vào muộn…).</p>`;
  };

  const load = async () => {
    $$('#mode button').forEach(b => b.classList.toggle('active', b.dataset.m === mode));
    $('#day').value = ymd(day);
    $('#day').hidden = mode === 'week'; $('#range').hidden = mode !== 'week';
    $('#body').innerHTML = loading();
    return mode === 'week' ? loadWeek() : loadDay();
  };
  $('#mode').onclick = e => { const b = e.target.closest('[data-m]'); if (b) { mode = b.dataset.m; store.set('team_mode', mode); load(); } };
  $('#prev').onclick = () => { day = addDays(day, mode === 'week' ? -7 : -1); load(); };
  $('#next').onclick = () => { day = addDays(day, mode === 'week' ? 7 : 1); load(); };
  $('#today').onclick = () => { day = new Date(); load(); };
  $('#day').onchange = e => { if (e.target.value) { day = parseDate(e.target.value); load(); } };
  load();
}

/* =========================================================
   5. Phiếu đổi ca
   ========================================================= */
const swapBack = r => r.swap_schedule_id ? `<br><span class="small muted">🔁 đổi lấy ca ${r.swap_start || '?'}–${r.swap_end || '?'}${r.swap_position ? ' · ' + esc(r.swap_position) : ''}</span>` : '';
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
      { label: 'Người làm thay', render: r => (r.to_user === me ? '<b>Tôi</b>' : esc(r.to_username)) + swapBack(r) },
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
/* chữ có link gắn trong sheet (⟦chữ|url⟧) + URL ghi thẳng → link bấm được */
const linkify = t => {
  const parts = [];
  const s = String(t ?? '').replace(LINK_RE, (m, label, url) => { parts.push([label, url]); return `\u0000${parts.length - 1}\u0000`; });
  return esc0(s).replace(/(https?:\/\/[^\s<\u0000]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>')
    .replace(/\u0000(\d+)\u0000/g, (m, k) => { const [label, url] = parts[+k]; return /^https?:\/\//.test(url) ? `<a href="${esc0(url)}" target="_blank" rel="noopener">${esc0(label)}</a>` : esc0(label); });
};
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
    return c.replace(LINK_RE, '$1').length > 80 ? html + `<button class="btn btn-sm btn-ghost hb-copy" data-copy>${icon('copy')} Sao chép</button>` : html;
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
    <div class="search hb-search">${icon('search')}<input class="input full" id="hb-q" placeholder="Tìm trong cẩm nang (VD: đổi lịch, xin nghỉ…) hoặc nhập SĐT / email học viên" autocomplete="off">
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

  /* tra cứu học viên: ô tìm kiếm là SĐT / email → hiện thông tin học viên đó */
  const contactKind = s => /@/.test(s) ? 'email' : /^[+\d][\d\s.\-()]*$/.test(s) ? 'phone' : null;
  const normPhone = s => { let d = s.replace(/\D/g, ''); if (d.startsWith('84') && d.length >= 11) d = '0' + d.slice(2); if (d.length === 9) d = '0' + d; return d; };
  const contactReady = s => contactKind(s) === 'email' ? /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(s) : normPhone(s).length >= 10;
  const studentHtml = g => {
    const H = g.header.map(h => (h || '').trim());
    const val = (r, i) => ((r[i] || '') + '').trim();
    const cols = H.map((_, i) => i).filter(i => H[i] && g.rows.some(r => val(r, i)));
    const same = cols.filter(i => g.rows.every(r => val(r, i) === val(g.rows[0], i)));
    const seen = new Set(), fixed = same.filter(i => { const k = H[i] + '|' + val(g.rows[0], i); if (seen.has(k)) return false; seen.add(k); return true; });
    const vary = cols.filter(i => !same.includes(i));
    return `<section class="hb-step hb-student"><div class="hb-step-head"><span class="hb-step-no">${icon('users')}</span>
        <div><h3>Thông tin học viên</h3><div class="small muted">Sheet ${esc(g.tab)} · ${g.rows.length}${g.more ? '+' : ''} dòng khớp</div></div>
        <button class="btn btn-sm btn-ghost" data-open="${g.gid}">Mở sheet ${icon('chevR')}</button></div>
      <div class="hb-step-body"><dl class="kv">${fixed.map(i => `<dt>${esc(H[i])}</dt><dd>${linkify(val(g.rows[0], i))}</dd>`).join('')}</dl>
        ${vary.length ? `<div class="table-wrap" style="margin-top:12px"><table class="table"><thead><tr>${vary.map(i => `<th>${esc(H[i])}</th>`).join('')}</tr></thead>
          <tbody>${g.rows.map(r => `<tr>${vary.map(i => `<td>${linkify(val(r, i))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : ''}</div></section>`;
  };
  const lookup = async () => {
    const seq = ++searchSeq;
    $$('#hb-nav button').forEach(b => b.classList.remove('active'));
    $('#hb-heading').textContent = `Tra cứu học viên: ${q}`; $('#hb-time').textContent = '';
    if (!contactReady(q)) { $('#hb-body').innerHTML = emptyState(contactKind(q) === 'email' ? 'Nhập đủ địa chỉ email để tra cứu học viên' : 'Nhập đủ số điện thoại để tra cứu học viên (có hoặc không có 0 / 84 / +84 đầu đều được)'); return; }
    $('#hb-body').innerHTML = '<div class="skel"></div><div class="skel w60"></div>';
    let res;
    try { res = await api('/handbook/lookup', { query: { q } }); } catch (e) { if (seq === searchSeq) $('#hb-body').innerHTML = emptyState(e.message); return; }
    if (seq !== searchSeq) return;
    $('#hb-body').innerHTML = res.results.length ? res.results.map(studentHtml).join('')
      : emptyState(`Không tìm thấy học viên có ${res.type === 'email' ? 'email' : 'số điện thoại'} này`);
  };

  const search = async () => {
    if (contactKind(q)) return lookup();
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
   6b. Thao tác ở CRM — video hướng dẫn từ Google Drive
   ========================================================= */
async function pageCRM(v) {
  const desc = 'Video hướng dẫn thao tác trên CRM. Chọn một video để xem ngay tại đây.';
  const head = actions => pageHead('Thao tác ở CRM', desc, actions);
  v.innerHTML = head('') + loading();
  let d = await api('/crm-videos');
  let cur = store.get('crm_video'), q = '';
  const all = () => d.groups.flatMap(g => g.items.map(it => ({ ...it, group: g.title })));
  const kindIcon = k => icon(k === 'video' ? 'play' : 'file');

  v.innerHTML = head(`<button class="btn" id="crm-refresh">${icon('refresh')} Làm mới</button>`) + `
    <div class="crm">
      <div class="crm-side card">
        <div class="search crm-search">${icon('search')}<input class="input full" id="crm-q" placeholder="Tìm video (VD: đặt lịch, chứng chỉ…)" autocomplete="off"></div>
        <div id="crm-list" class="crm-list"></div>
      </div>
      <div class="crm-main"><div class="card" id="crm-player"></div></div>
    </div>`;

  const paintList = () => {
    const ws = words(q);
    const groups = d.groups.map(g => ({ ...g, items: g.items.filter(it => !ws.length || matches(`${it.title} ${g.title}`, ws)) }))
      .filter(g => g.items.length || (g.error && !ws.length));
    $('#crm-list').innerHTML = groups.length ? groups.map(g => `<div class="crm-group">
        ${d.groups.length > 1 || g.title !== 'Video hướng dẫn' ? `<div class="crm-group-h">${esc(g.title)} <span class="badge">${g.items.length}</span></div>` : ''}
        ${g.error ? `<div class="small" style="padding:6px 12px;color:var(--red)">${esc(g.error)}</div>` : ''}
        ${g.items.map(it => `<button class="crm-item ${it.id === cur ? 'active' : ''}" data-id="${it.id}">${kindIcon(it.kind)}<span>${mark(esc(it.title), q)}</span></button>`).join('')}
      </div>`).join('')
      : emptyState(d.groups.length ? `Không có video nào chứa “${q}”` : 'Quản lý chưa thêm video hướng dẫn nào');
  };
  const paintPlayer = () => {
    const it = all().find(x => x.id === cur);
    if (!it) { $('#crm-player').innerHTML = `<div class="crm-empty">${icon('video')}<p class="muted">${all().length ? 'Chọn một video bên trái để xem' : 'Chưa có video nào'}</p></div>`; return; }
    $('#crm-player').innerHTML = `<div class="crm-frame"><iframe src="https://drive.google.com/file/d/${encodeURIComponent(it.id)}/preview" allow="autoplay; fullscreen" allowfullscreen title="${esc(it.title)}"></iframe></div>
      <div class="crm-cap"><div><b>${esc(it.title)}</b>${it.group && it.group !== 'Video hướng dẫn' ? `<div class="small muted">${esc(it.group)}</div>` : ''}</div>
        <a class="btn btn-sm" href="https://drive.google.com/file/d/${encodeURIComponent(it.id)}/view" target="_blank" rel="noopener">${icon('external')} Mở trên Drive</a></div>`;
  };
  const select = id => {
    cur = id; store.set('crm_video', id);
    $$('#crm-list .crm-item').forEach(b => b.classList.toggle('active', b.dataset.id === id));
    paintPlayer();
    if (matchMedia('(max-width: 860px)').matches) $('#crm-player').scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  if (!all().some(x => x.id === cur)) cur = (all().find(x => x.kind === 'video') || all()[0] || {}).id;
  paintList(); paintPlayer();
  $('#crm-list').onclick = e => { const b = e.target.closest('[data-id]'); if (b) select(b.dataset.id); };
  $('#crm-q').oninput = e => { q = e.target.value.trim(); paintList(); };
  $('#crm-refresh').onclick = e => run(e.currentTarget, async () => { d = await api('/crm-videos', { query: { refresh: 1 } }); paintList(); paintPlayer(); toast('Đã cập nhật danh sách video'); });
}

/* =========================================================
   6c. Video hướng dẫn PH thao tác — từ kênh YouTube, xem trước + sao chép link gửi PH
   ========================================================= */
async function pagePH(v) {
  const desc = 'Video hướng dẫn phụ huynh / học viên thao tác. Xem trước rồi bấm “Sao chép link” để gửi cho PH.';
  const head = actions => pageHead('Video hướng dẫn PH', desc, actions);
  v.innerHTML = head('') + loading();
  let d = await api('/ph-videos');
  let cur = store.get('ph_video'), q = '';
  const all = () => d.groups.flatMap(g => g.items.map(it => ({ ...it, group: g.title })));
  const copy = (text, msg) => navigator.clipboard.writeText(text).then(() => toast(msg), () => toast('Trình duyệt chặn sao chép', 'error'));

  v.innerHTML = head(`<button class="btn" id="ph-refresh">${icon('refresh')} Làm mới</button>`) + `
    <div class="crm">
      <div class="crm-side card">
        <div class="search crm-search">${icon('search')}<input class="input full" id="ph-q" placeholder="Tìm video (VD: xin nghỉ, đặt lịch…)" autocomplete="off"></div>
        <div id="ph-list" class="crm-list"></div>
      </div>
      <div class="crm-main"><div class="card" id="ph-player"></div></div>
    </div>`;

  const paintList = () => {
    const ws = words(q);
    const groups = d.groups.map(g => ({ ...g, items: g.items.filter(it => !ws.length || matches(`${it.title} ${g.title}`, ws)) })).filter(g => g.items.length);
    $('#ph-list').innerHTML = d.error ? emptyState(d.error)
      : groups.length ? groups.map(g => `<div class="crm-group">
        ${d.groups.length > 1 ? `<div class="crm-group-h">${esc(g.title)} <span class="badge">${g.items.length}</span></div>` : ''}
        ${g.items.map(it => `<div class="ph-row"><button class="crm-item ${it.id === cur ? 'active' : ''}" data-id="${it.id}" title="${esc(it.title)}">${icon('play')}<span>${mark(esc(it.short), q)}</span></button>
          <button class="btn btn-icon btn-ghost ph-copy" data-copy="${it.id}" title="Sao chép link" aria-label="Sao chép link ${esc(it.short)}">${icon('copy')}</button></div>`).join('')}
      </div>`).join('')
      : emptyState(d.groups.length ? `Không có video nào chứa “${q}”` : 'Kênh chưa có video nào');
  };
  const paintPlayer = () => {
    const it = all().find(x => x.id === cur);
    if (!it) { $('#ph-player').innerHTML = `<div class="crm-empty">${icon('video')}<p class="muted">${all().length ? 'Chọn một video bên trái để xem' : 'Chưa có video nào'}</p></div>`; return; }
    $('#ph-player').innerHTML = `<div class="crm-frame"><iframe src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(it.id)}?rel=0" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen title="${esc(it.title)}"></iframe></div>
      <div class="crm-cap"><div style="min-width:0"><b>${esc(it.short)}</b><div class="small muted">${esc(it.group)} · <a href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.url)}</a></div></div>
        <div class="actions"><button class="btn btn-sm btn-primary" id="ph-c1">${icon('copy')} Sao chép link</button>
          <button class="btn btn-sm" id="ph-c2" title="Sao chép tiêu đề + link để dán vào tin nhắn">${icon('copy')} Kèm tiêu đề</button>
          <a class="btn btn-sm" href="${esc(it.url)}" target="_blank" rel="noopener">${icon('external')} YouTube</a></div></div>`;
    $('#ph-c1').onclick = () => copy(it.url, 'Đã sao chép link video');
    $('#ph-c2').onclick = () => copy(`${it.short}: ${it.url}`, 'Đã sao chép tiêu đề + link');
  };
  const select = id => {
    cur = id; store.set('ph_video', id);
    $$('#ph-list .crm-item').forEach(b => b.classList.toggle('active', b.dataset.id === id));
    paintPlayer();
    if (matchMedia('(max-width: 860px)').matches) $('#ph-player').scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  if (!all().some(x => x.id === cur)) cur = (all()[0] || {}).id;
  paintList(); paintPlayer();
  if (d.warning) toast('Không kết nối được YouTube, đang hiển thị bản lưu tạm', 'info');
  $('#ph-list').onclick = e => {
    const c = e.target.closest('[data-copy]');
    if (c) { const it = all().find(x => x.id === c.dataset.copy); if (it) copy(it.url, `Đã sao chép link: ${it.short}`); return; }
    const b = e.target.closest('[data-id]'); if (b) select(b.dataset.id);
  };
  $('#ph-q').oninput = e => { q = e.target.value.trim(); paintList(); };
  $('#ph-refresh').onclick = e => run(e.currentTarget, async () => { d = await api('/ph-videos', { query: { refresh: 1 } }); paintList(); paintPlayer(); toast('Đã cập nhật danh sách video'); });
}

/* =========================================================
   6d. Tài liệu — các tab quản lý tự thêm (link YouTube / Google Drive / Docs)
   ========================================================= */
async function pageDocs(v) {
  const desc = 'Tài liệu, video hướng dẫn do quản lý chia sẻ. Chọn tab để xem ngay tại đây.';
  const head = actions => pageHead('Document', desc, actions);
  v.innerHTML = head('') + loading();
  const tabs = await api('/docs');
  if (!tabs.length) { v.innerHTML = head('') + `<div class="card">${emptyState('Quản lý chưa thêm tài liệu nào')}</div>`; return; }
  let tid = store.get('doc_tab'), d = null, cur = null, q = '';
  if (!tabs.some(t => t.id === tid)) tid = tabs[0].id;
  const copy = (text, msg) => navigator.clipboard.writeText(text).then(() => toast(msg), () => toast('Trình duyệt chặn sao chép', 'error'));
  const all = () => d.groups.flatMap(g => g.items.map(it => ({ ...it, group: g.title })));

  v.innerHTML = head(`<button class="btn" id="doc-refresh">${icon('refresh')} Làm mới</button>`) + `
    <div class="doc-tabs" role="tablist">${tabs.map(t => `<button role="tab" data-tab="${t.id}">${esc(t.name)}</button>`).join('')}</div>
    <div id="doc-body"></div>`;

  const player = it => !it ? `<div class="crm-empty">${icon('video')}<p class="muted">${all().length ? 'Chọn một mục bên trái để xem' : 'Chưa có nội dung'}</p></div>`
    : `<div class="crm-frame ${it.kind === 'doc' ? 'doc-frame' : ''}"><iframe src="${esc(it.embed)}" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen title="${esc(it.title)}"></iframe></div>
      <div class="crm-cap"><div style="min-width:0"><b>${esc(it.title)}</b>${it.group && it.group !== it.title ? `<div class="small muted">${esc(it.group)}</div>` : ''}</div>
        <div class="actions">${it.copy ? `<button class="btn btn-sm" data-copylink="${esc(it.open)}">${icon('copy')} Sao chép link</button>` : ''}
          <a class="btn btn-sm" href="${esc(it.open)}" target="_blank" rel="noopener">${icon('external')} Mở trong tab mới</a></div></div>`;
  const paintList = () => {
    const ws = words(q);
    const groups = d.groups.map(g => ({ ...g, items: g.items.filter(it => !ws.length || matches(`${it.title} ${g.title}`, ws)) })).filter(g => g.items.length);
    $('#doc-list').innerHTML = groups.length ? groups.map(g => `<div class="crm-group">
        ${g.title && d.groups.length > 1 ? `<div class="crm-group-h">${esc(g.title)} <span class="badge">${g.items.length}</span></div>` : ''}
        ${g.items.map(it => `<button class="crm-item ${it.id === cur ? 'active' : ''}" data-id="${esc(it.id)}">${icon(it.kind === 'video' ? 'play' : 'file')}<span>${mark(esc(it.title), q)}</span></button>`).join('')}
      </div>`).join('') : emptyState(q ? `Không có mục nào chứa “${q}”` : 'Chưa có nội dung');
  };
  /* tab trong file Cẩm nang: bảng + ô tìm (VD tra thông tin GV) */
  let tlimit = 200;
  // mỗi tab có thể gồm nhiều bảng đặt cạnh nhau (VD GV nước ngoài | GV Việt Nam) → hiện từng bảng, tìm trong từng dòng của bảng
  const paintRows = () => {
    const ws = words(q), blocks = d.table.blocks || [];
    const total = blocks.reduce((a, b) => a + b.rows.length, 0);
    const shown = blocks.map(b => ({ ...b, list: ws.length ? b.rows.filter(r => matches(r.join(' ').replace(LINK_RE, '$1'), ws)) : b.rows })).filter(b => b.list.length);
    const hits = shown.reduce((a, b) => a + b.list.length, 0);
    $('#doc-table').innerHTML = !total ? `<div class="card">${emptyState('Tab này chưa có nội dung')}</div>`
      : !hits ? `<div class="card">${emptyState(`Không có dòng nào chứa “${q}”`)}</div>`
      : shown.map(b => `<div class="card" style="margin-bottom:14px">
          ${b.title || shown.length > 1 ? `<div class="card-head"><h2>${esc(b.title || 'Bảng')}</h2><span class="badge">${ws.length ? `${b.list.length} khớp` : `${b.rows.length} dòng`}</span></div>` : ''}
          ${sheetTableHtml(b.header, b.list.slice(0, tlimit))}
          ${b.list.length > tlimit ? `<div class="hb-more"><span class="muted small">Đang hiện ${tlimit}/${b.list.length} dòng</span><button class="btn" data-tmore>Xem thêm</button></div>` : ''}</div>`).join('');
    $('#doc-count').textContent = ws.length ? `${hits} dòng khớp` : `${total} dòng · cập nhật lúc ${d.table.fetched_at.slice(11, 16)}`;
  };
  const paintTable = () => {
    tlimit = 200;
    $('#doc-body').innerHTML = `<div class="search hb-search">${icon('search')}<input class="input full" id="doc-tq" placeholder="Tìm theo tên, mã… (VD: Melanie, TC015145 — gõ không dấu cũng được)" autocomplete="off" value="${esc(q)}"></div>
      <div class="small muted" id="doc-count" style="margin:6px 2px 8px"></div><div id="doc-table"></div>`;
    paintRows();
    let timer;
    $('#doc-tq').oninput = e => { clearTimeout(timer); timer = setTimeout(() => { q = e.target.value.trim(); tlimit = 200; paintRows(); }, 150); };
  };
  /* tab TK Milo: tra học viên đã bàn giao chưa, đã vào file VH chưa, tài khoản được tạo là gì */
  const MILO_ST = { granted: 'green', created: 'blue', in_vh: 'amber', handed: 'amber', none: 'red' };
  const miloCard = s => {
    const yes = t => `<span class="badge green">✓</span> ${t}`, no = t => `<span class="muted">${t}</span>`;
    // mỗi lần bàn giao: tóm tắt (lúc nào, ai bàn giao, team…) + bấm xem đủ mọi cột có dữ liệu của dòng gốc
    const handover = list => list.length ? list.map(r => `<div style="margin-bottom:6px"><span class="badge green">✓</span> <b>dòng ${r.row}</b>
        ${(r.summary || []).map(([k, v]) => `<span class="small"> · ${esc(k)}: <b>${esc(v)}</b></span>`).join('')}
        ${(r.fields || []).length ? `<details style="margin-top:4px"><summary class="small" style="cursor:pointer">Xem đầy đủ ${r.fields.length} cột</summary>
          <div class="table-wrap" style="margin-top:6px"><table class="table"><tbody>${r.fields.map(([k, v]) => `<tr><td class="small muted nowrap" style="width:1%">${esc(k)}</td><td class="small" style="word-break:break-word">${esc(v)}</td></tr>`).join('')}</tbody></table></div></details>` : ''}</div>`).join('') : no('Không thấy');
    const s1 = handover(s.s1), s2 = handover(s.s2);
    const cp = v => v ? `<b class="mono">${esc(v)}</b> <button class="btn btn-sm btn-ghost" data-copyval="${esc(v)}" title="Sao chép">${icon('copy')}</button>` : '<span class="muted">—</span>';
    const vh = s.vh.length ? s.vh.map(r => `<dl class="kv" style="margin-top:6px">
        <dt>Dòng</dt><dd>${r.row}${r.name ? ` · ${esc(r.name)}` : ''}${r.paid ? ` · TT ${esc(r.paid)}` : ''}</dd>
        <dt>Username</dt><dd>${cp(r.username)}</dd>
        <dt>Password</dt><dd>${cp(r.password)}</dd>
        <dt>Cấp tài khoản</dt><dd>${r.granted ? '<span class="badge green">Đã tích</span>' : '<span class="badge amber">Chưa tích</span>'}</dd>
        <dt>Mail</dt><dd>${r.mail ? esc(r.mail) : '<span class="muted">—</span>'}</dd></dl>`).join('<hr style="border:0;border-top:1px solid var(--border);margin:8px 0">') : no('Chưa có trong file VH');
    // mail hộp mail chung đã gửi tới học viên: bấm để xem, trong đó có nút sao chép ảnh chụp mail
    const mails = (s.mails || []).length ? s.mails.map(m => `<div class="mm-item"><button type="button" class="mm-row" data-mail="${esc(m.id)}">${icon('mail')}
        <span class="small muted nowrap">${m.at.slice(11, 16)} ${fmtDate(m.at.slice(0, 10))}</span> <b>${esc(m.subject || '(không tiêu đề)')}</b></button><div class="mm-view" hidden></div></div>`).join('')
      : no('Không thấy mail đã gửi tới email này');
    return `<div class="card" style="margin-bottom:12px">
      <div class="card-head"><h2>${esc(s.name || '(không tên)')}</h2><span class="badge ${MILO_ST[s.status]}">${esc(s.status_label)}</span></div>
      <div class="card-pad"><div class="small muted" style="margin-bottom:10px">${[...s.emails, ...s.phones].map(esc).join(' · ') || '—'}</div>
        <dl class="kv"><dt>Bàn giao (ICC – Format)</dt><dd>${s1}</dd><dt>Bàn giao (data_handover)</dt><dd>${s2}</dd><dt>File VH (tạo TK)</dt><dd>${vh}</dd>
          <dt>Mail đã gửi</dt><dd>${mails}</dd></dl></div></div>`;
  };
  /* xem mail đã gửi trong iframe (sandbox: không chạy script của mail) + chụp thành ảnh PNG để CTV dán vào Zalo / Messenger */
  const mailDoc = m => {
    const row = (k, v) => v ? `<div><span class="k">${k}:</span> ${esc(v)}</div>` : '';
    const imgs = m.atts.filter(a => a.data).map(a => `<img src="data:${esc(a.type)};base64,${a.data}" alt="${esc(a.name)}">`).join('');
    const files = m.atts.filter(a => !a.data).map(a => `<span class="f">📎 ${esc(a.name)}</span>`).join('');
    return `<!doctype html><html><head><meta charset="utf-8"><base target="_blank"><style>
      html,body{margin:0;background:#fff;color:#202124;font:14px/1.5 Arial,Helvetica,sans-serif}
      #mm-shot{background:#fff;display:flow-root}
      .mm-h{padding:16px 20px 12px;border-bottom:1px solid #e3e3e3}.mm-s{font-size:19px;margin:0 0 8px;font-weight:600}
      .mm-m{font-size:12.5px;color:#5f6368;line-height:1.6;word-break:break-word}.mm-m .k{color:#202124}
      .mm-b{padding:16px 20px;overflow-wrap:anywhere}.mm-b img{max-width:100%;height:auto}
      .mm-a{padding:0 20px 16px}.mm-a img{max-width:100%;display:block;margin:8px 0;border:1px solid #e3e3e3}
      .mm-a .f{display:inline-block;margin:4px 8px 0 0;padding:4px 8px;border:1px solid #e3e3e3;border-radius:6px;font-size:12.5px}
    </style></head><body><div id="mm-shot"><div class="mm-h"><div class="mm-s">${esc(m.subject || '(không tiêu đề)')}</div><div class="mm-m">
      ${row('Từ', m.from)}${row('Tới', m.to)}${row('Cc', m.cc)}${row('Lúc', `${m.at.slice(11, 16)} ${fmtDate(m.at.slice(0, 10))}`)}</div></div>
      <div class="mm-b">${m.html}</div>${imgs || files ? `<div class="mm-a">${imgs}${files}</div>` : ''}</div></body></html>`;
  };
  const fitFrame = f => { try { f.style.height = f.contentDocument.documentElement.scrollHeight + 'px'; } catch (e) { /* bỏ qua */ } };
  const loadShot = () => window.html2canvas ? Promise.resolve() : new Promise((ok, no) => {
    const sc = document.createElement('script');
    sc.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
    sc.onload = ok; sc.onerror = () => no(new Error('Không tải được công cụ chụp ảnh, thử lại'));
    document.head.appendChild(sc);
  });
  const shotMail = async f => {
    await loadShot();
    const doc = f.contentDocument, el = doc.getElementById('mm-shot');
    const c = await window.html2canvas(el, { useCORS: true, backgroundColor: '#ffffff', scale: 2, logging: false,
      windowWidth: doc.documentElement.scrollWidth, windowHeight: doc.documentElement.scrollHeight });
    return new Promise((ok, no) => c.toBlob(b => b ? ok(b) : no(new Error('Không tạo được ảnh')), 'image/png'));
  };
  const saveBlob = (b, name) => { const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 5000); };
  const mailAction = async (btn, kind) => {
    const box = btn.closest('.mm-view'), f = $('iframe', box), m = box._mail;
    const name = `mail-${(m.to.match(/[\w.+'-]+@[\w.-]+/) || ['hoc-vien'])[0]}-${m.at.slice(0, 10)}.png`;
    btn.disabled = true;
    try {
      if (kind === 'copy') {
        if (!navigator.clipboard || !window.ClipboardItem) throw new Error('Trình duyệt không cho sao chép ảnh — dùng nút Tải ảnh');
        // truyền Promise vào ClipboardItem để Safari vẫn coi là thao tác của người dùng
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': shotMail(f) })]);
        toast('Đã sao chép ảnh mail — dán (Ctrl+V) vào Zalo / Messenger');
      } else {
        saveBlob(await shotMail(f), name);
        toast('Đã tải ảnh mail');
      }
    } catch (er) {
      toast(/NotAllowed|denied/i.test(`${er.name} ${er.message}`) ? 'Trình duyệt chặn sao chép ảnh — dùng nút Tải ảnh' : er.message || 'Không chụp được ảnh', 'error');
    } finally { btn.disabled = false; }
  };
  const openMail = async btn => {
    const box = btn.nextElementSibling;
    if (!box.hidden) { box.hidden = true; return; }
    box.hidden = false;
    if (box._mail) return;
    box.innerHTML = loading();
    try {
      const m = box._mail = await api(`/milo/mail/${encodeURIComponent(btn.dataset.mail)}`);
      box.innerHTML = `<div class="mm-tools"><button type="button" class="btn btn-sm btn-primary" data-mailshot="copy">${icon('copy')} Sao chép ảnh</button>
        <button type="button" class="btn btn-sm" data-mailshot="save">${icon('download')} Tải ảnh</button></div>
        <iframe class="mm-frame" sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox" title="Nội dung mail"></iframe>`;
      const f = $('iframe', box);
      f.onload = () => { fitFrame(f); setTimeout(() => fitFrame(f), 600); };
      f.srcdoc = mailDoc(m);
    } catch (er) { box._mail = null; box.innerHTML = `<div class="small muted">${esc(er.message)}</div>`; }
  };
  const paintMilo = () => {
    $('#doc-body').innerHTML = `<div class="search hb-search">${icon('search')}<input class="input full" id="milo-q" placeholder="Tìm học viên Milo theo tên, email hoặc SĐT (gõ không dấu cũng được)" autocomplete="off" value="${esc(q)}"></div>
      <div class="small muted" id="milo-count" style="margin:6px 2px 8px">${d.ready ? `Dữ liệu cập nhật lúc ${d.data_at.slice(11, 16)} ${fmtDate(d.data_at.slice(0, 10))} · gõ ít nhất 2 ký tự` : 'Đang chờ dữ liệu từ Google Sheet (tối đa ~2 phút)…'}${d.partial && d.ready ? ' · <span class="badge amber">Đang tải lịch sử lần đầu — chưa có ~200 dòng mới nhất mỗi file, chờ thêm vài phút</span>' : ''}</div><div id="milo-res"></div>`;
    let timer, seq = 0;
    const go = async () => {
      const my = ++seq, text = q;
      if (text.length < 2) { $('#milo-res').innerHTML = ''; return; }
      $('#milo-res').innerHTML = loading();
      const r = await api('/milo/search', { query: { q: text } }).catch(e => ({ error: e.message }));
      if (my !== seq) return;
      if (r.error) { $('#milo-res').innerHTML = `<div class="card">${emptyState(r.error)}</div>`; return; }
      if (!r.ready) { $('#milo-res').innerHTML = `<div class="card">${emptyState('Portal chưa nhận được dữ liệu Milo, thử lại sau vài phút')}</div>`; return; }
      $('#milo-res').innerHTML = r.students.length
        ? r.students.map(miloCard).join('') + (r.more ? '<p class="small muted">Còn nữa — gõ cụ thể hơn để thu hẹp</p>' : '')
        : `<div class="card">${emptyState(r.partial ? `Chưa thấy “${text}” — portal đang tải lịch sử lần đầu, các dòng mới nhất chưa về. Thử lại sau vài phút.` : `Không thấy học viên nào khớp “${text}” trong 2 file bàn giao và file VH`)}</div>`;
    };
    $('#milo-q').oninput = e => { clearTimeout(timer); timer = setTimeout(() => { q = e.target.value.trim(); go(); }, 300); };
    $('#milo-q').focus();
    go();
  };
  const paint = () => {
    const body = $('#doc-body');
    if (d.error) { body.innerHTML = `<div class="card">${emptyState(d.error)}</div>`; return; }
    if (d.milo) { paintMilo(); return; }
    if (d.table) { paintTable(); return; }
    if (d.single) { body.innerHTML = `<div class="card doc-single">${player(all()[0])}</div>`; return; }
    if (!all().some(x => x.id === cur)) cur = (all().find(x => x.kind === 'video') || all()[0] || {}).id;
    body.innerHTML = `<div class="crm">
      <div class="crm-side card"><div class="search crm-search">${icon('search')}<input class="input full" id="doc-q" placeholder="Tìm trong tab này" autocomplete="off" value="${esc(q)}"></div><div id="doc-list" class="crm-list"></div></div>
      <div class="crm-main"><div class="card" id="doc-player">${player(all().find(x => x.id === cur))}</div></div></div>`;
    paintList();
    $('#doc-q').oninput = e => { q = e.target.value.trim(); paintList(); };
    $('#doc-list').onclick = e => {
      const b = e.target.closest('[data-id]'); if (!b) return;
      cur = b.dataset.id; store.set(`doc_item_${tid}`, cur);
      $$('#doc-list .crm-item').forEach(x => x.classList.toggle('active', x.dataset.id === cur));
      $('#doc-player').innerHTML = player(all().find(x => x.id === cur));
      if (matchMedia('(max-width: 860px)').matches) $('#doc-player').scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
  };
  const load = async refresh => {
    $$('.doc-tabs [data-tab]').forEach(b => b.classList.toggle('active', b.dataset.tab === tid));
    if (!refresh) $('#doc-body').innerHTML = loading();
    const want = tid, r = await api(`/docs/${tid}`, { query: { refresh: refresh ? 1 : '' } });
    if (want !== tid) return;  // đã chuyển tab khác trong lúc tải
    d = r; if (!refresh) { cur = store.get(`doc_item_${tid}`); q = ''; }
    paint();
    if (d.warning) toast('Không tải được bản mới nhất, đang hiển thị bản lưu tạm', 'info');
  };
  $('.doc-tabs').onclick = e => { const b = e.target.closest('[data-tab]'); if (!b || b.dataset.tab === tid) return; tid = b.dataset.tab; store.set('doc_tab', tid); load(false).catch(er => { $('#doc-body').innerHTML = `<div class="card">${emptyState(er.message)}</div>`; }); };
  $('#doc-body').addEventListener('click', e => {
    const c = e.target.closest('[data-copylink]'); if (c) copy(c.dataset.copylink, 'Đã sao chép link');
    const cv = e.target.closest('[data-copyval]'); if (cv) copy(cv.dataset.copyval, 'Đã sao chép');
    const ml = e.target.closest('[data-mail]'); if (ml) openMail(ml);
    const ms = e.target.closest('[data-mailshot]'); if (ms) mailAction(ms, ms.dataset.mailshot);
    const cc = e.target.closest('[data-copy]'); if (cc) { e.preventDefault(); copy(cc.previousElementSibling.innerText, 'Đã sao chép'); }
    if (e.target.closest('[data-tmore]')) { tlimit += 200; paintRows(); }
  });
  $('#doc-refresh').onclick = e => run(e.currentTarget, async () => { await load(true); toast('Đã cập nhật'); });
  await load(false);
}

/* =========================================================
   7. Tra cứu lương
   ========================================================= */
async function pageSalary(v) {
  const months = await api('/ctv/salary/months');
  v.innerHTML = pageHead('Tra cứu lương', 'Bảng lương được chốt vào ngày 02 hàng tháng. Thắc mắc vui lòng liên hệ quản lý team.') +
    (months.length ? `<div class="filters"><select class="input" id="ym">${months.map(m => `<option value="${m}">${fmtYM(m)}</option>`).join('')}</select></div><div id="body"></div>`
      : `<div class="card">${emptyState('Chưa có bảng lương nào được công bố')}<p class="small muted" style="text-align:center;padding:0 16px 20px">Lương hiện ở đây sau khi quản lý duyệt &amp; công bố bảng lương tháng.</p>${''}</div>`);
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
      { label: 'Ca', render: r => esc(shortShift(r.shift_code)) },
      { label: 'Giờ vào', cls: 'mono', render: r => r.start },
      { label: 'Giờ ra', cls: 'mono', render: r => r.end },
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
   8. Lỗi QC của tôi · 9. Nhật ký
   ========================================================= */
async function pageQC(v) {
  const desc = 'Các lỗi QC quản lý ghi nhận cho tài khoản của bạn. Tiền phạt được trừ vào lương của tháng tương ứng.';
  v.innerHTML = pageHead('Lỗi QC', desc) + loading();
  const all = await api('/ctv/qc');
  const months = [...new Set(all.map(r => r.ym).filter(Boolean))].sort().reverse();
  const nowYm = ymOf(new Date());
  let ym = months.includes(nowYm) ? nowYm : 'all';
  v.innerHTML = pageHead('Lỗi QC', desc, all.length ? `<button class="btn" id="exp">${icon('download')} Xuất Excel</button>` : '') + (all.length ? `
    <div class="filters"><select class="input" id="ym"><option value="all">Tất cả các tháng</option>
      ${months.map(m => `<option value="${m}">${fmtYM(m)} (${all.filter(r => r.ym === m).length} lỗi)</option>`).join('')}</select></div>
    <div class="stats" id="stats"></div><div class="card" id="body"></div>`
    : `<div class="card">${emptyState('Bạn chưa có lỗi QC nào. Giữ vững phong độ nhé!')}</div>`);
  if (!all.length) return;
  $('#ym').value = ym;
  const cols = [{ label: 'Tháng lương', render: r => `<span class="nowrap">${r.ym ? fmtYM(r.ym) : '—'}</span>` }, ...QC_COLUMNS];
  const paint = () => {
    const rows = ym === 'all' ? all : all.filter(r => r.ym === ym);
    const fine = rows.reduce((a, r) => a + (r.amount || 0), 0), warn = rows.filter(r => !r.amount).length;
    $('#stats').innerHTML = `
      <div class="stat"><div class="label">Số lỗi${ym === 'all' ? '' : ' ' + fmtYM(ym).toLowerCase()}</div><div class="value ${rows.length ? 'accent' : ''}">${rows.length}</div></div>
      <div class="stat"><div class="label">Tiền phạt</div><div class="value">${money(fine)}</div></div>
      <div class="stat"><div class="label">Chỉ nhắc nhở</div><div class="value">${warn}</div></div>`;
    dataTable($('#body'), rows, ym === 'all' ? cols : QC_COLUMNS, { pageSize: 20, empty: 'Không có lỗi nào trong tháng này' });
  };
  $('#ym').onchange = e => { ym = e.target.value; paint(); };
  $('#exp').onclick = () => {
    const rows = ym === 'all' ? all : all.filter(r => r.ym === ym);
    downloadCSV(`loi-qc-${ym}.csv`, ['Tháng lương', 'Ngày', 'Lỗi', 'Ghi chú', 'Hình thức', 'Phân loại', 'Ticket', 'Tiền phạt'],
      rows.map(r => [r.ym, fmtDate(r.date), r.error, r.note, r.penalty, r.category, r.ticket, r.amount || 0]));
  };
  paint();
}

async function pageLogs(v) {
  v.innerHTML = pageHead('Nhật ký hoạt động', 'Lịch sử thao tác của bạn trên hệ thống.') + `<div class="card" id="body">${loading()}</div>`;
  const rows = await api('/ctv/logs');
  dataTable($('#body'), rows, [
    { label: 'Thời gian', render: r => `<span class="nowrap muted">${fmtDate(r.created_at.slice(0, 10))} ${r.created_at.slice(11, 16)}</span>` },
    { label: 'Hành động', render: r => esc(r.action) },
  ]);
}

/* ---------- thông báo từ quản lý ---------- */
async function pageNotifications(v) {
  v.innerHTML = pageHead('Thông báo', 'Thông báo từ quản lý: lịch đã chốt, thay đổi ca, nhắc việc…') + loading();
  const list = await api('/notifications');
  v.innerHTML = pageHead('Thông báo', 'Thông báo từ quản lý: lịch đã chốt, thay đổi ca, nhắc việc…') +
    `<div class="card card-pad">${list.length ? list.map(notifItem).join('') : emptyState('Chưa có thông báo')}</div>`;
  if (list.some(n => n.unread)) { await api('/notifications/read', { method: 'POST' }).catch(() => {}); App.refreshNotifCount(); }
}

/* ---------- Theo dõi & nhận xét (PIP) ---------- */
async function pagePIP(v) {
  const desc = 'Nhận xét của quản lý sau các ca làm. Nếu thấy nhận xét chưa đúng, bạn có thể phản hồi ngay dưới nhận xét đó.';
  v.innerHTML = pageHead('Nhận xét QC', desc) + loading();
  const plans = await api('/ctv/pip');
  App.setCount('nhanxetqc', 0);
  if (!plans.length) { v.innerHTML = pageHead('Nhận xét QC', desc) + `<div class="card">${emptyState('Bạn chưa có nhận xét QC nào.')}</div>`; return; }
  v.innerHTML = pageHead('Nhận xét QC', desc) + plans.map(p => `
    <div class="card card-pad" style="margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px">
        <h2 style="font-size:15px">Đợt QC ${fmtDate(p.start_date)} → ${fmtDate(p.end_date)}</h2>${pipStatusBadge(p.status)}</div>
      <dl class="pip-dl">
        <dt>Phụ trách</dt><dd>${esc(p.owner || '—')}</dd>
        ${p.reason ? `<dt>Lý do</dt><dd>${esc(p.reason)}</dd>` : ''}
        <dt>Mục tiêu</dt><dd style="white-space:normal">${pipGoals(p.goals)}</dd>
        ${p.status !== 'active' && p.conclusion ? `<dt>Kết luận</dt><dd>${esc(p.conclusion)}</dd>` : ''}</dl>
    </div>
    <h2 style="font-size:15px;margin:4px 0 10px">Nhận xét (${p.reviews.length})</h2>
    <div class="pip-plan-reviews" style="margin-bottom:24px">${p.reviews.length ? p.reviews.map(r => pipReviewCard(r, { me: App.user.id })).join('')
      : `<div class="card">${emptyState('Quản lý chưa có nhận xét nào.')}</div>`}</div>`).join('');
  bindPipThreads(v, () => pagePIP(v));
}

async function refreshPipNav() {
  const r = await api('/ctv/pip/unread').catch(() => null);
  const a = $('#nav a[data-id="nhanxetqc"]');
  if (a && r) a.hidden = !r.has;
  if (r) App.setCount('nhanxetqc', r.unread);
}

/* ---------- khởi động ---------- */
App.start({
  onEnter: refreshPipNav,
  role: 'ctv', brand: 'Cổng CTV', subtitle: 'Cộng tác viên', loginHint: 'Tên đăng nhập dạng ctv.tenban (VD ctv.haott). Mật khẩu ban đầu do quản lý cấp.',
  nav: [
    { group: 'Tổng quan', items: [{ id: 'dashboard', label: 'Tổng quan', icon: 'home', render: pageDashboard },
      { id: 'notifications', label: 'Thông báo', icon: 'bell', render: pageNotifications }] },
    { group: 'Lịch làm', items: [
      { id: 'schedule', label: 'Lịch làm việc', icon: 'calendar', render: pageSchedule },
      { id: 'availability', label: 'Đăng ký lịch rảnh', icon: 'checkSquare', render: pageAvailability },
      { id: 'team', label: 'Lịch team', icon: 'users', render: pageTeam },
      { id: 'swaps', label: 'Phiếu đổi ca', icon: 'swap', render: pageSwaps },
    ] },
    { group: 'Tra cứu', items: [
      { id: 'handbook', label: 'Cẩm nang', icon: 'book', render: pageHandbook },
      { id: 'crm', label: 'Thao tác ở CRM', icon: 'video', render: pageCRM },
      { id: 'ph-videos', label: 'Video hướng dẫn PH', icon: 'play', render: pagePH },
      { id: 'docs', label: 'Document', icon: 'file', render: pageDocs },
    ] },
    { group: 'Cá nhân', items: [
      { id: 'salary', label: 'Tra cứu lương', icon: 'wallet', render: pageSalary },
      { id: 'qc', label: 'Lỗi QC', icon: 'alert', render: pageQC },
      { id: 'nhanxetqc', label: 'Nhận xét QC', icon: 'target', render: pagePIP },
      { id: 'logs', label: 'Nhật ký hoạt động', icon: 'list', render: pageLogs },
    ] },
  ],
});
