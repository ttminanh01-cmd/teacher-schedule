/* =========================================================
   Trang Quản trị
   ========================================================= */
const posName = id => (App.meta.positions.find(p => p.id === id) || {}).name || '';
const dowKey = dateStr => ((parseDate(dateStr).getDay() + 6) % 7) + 1; // 1 = T2 … 7 = CN

async function refreshSwapCount() {
  const list = await api('/admin/swaps').catch(() => []);
  App.setCount('swaps', list.filter(s => s.status === 'pending').length);
}

/* =========================================================
   1. Tổng quan
   ========================================================= */
async function aDashboard(v) {
  let day = todayStr();
  v.innerHTML = pageHead('Tổng quan', 'Tình hình ca trực trong ngày.') + `
    <div class="filters"><input type="date" class="input" id="day" value="${day}"></div><div id="body">${loading()}</div>`;
  const load = async () => {
    const d = await api('/admin/dashboard', { query: { day } });
    App.setCount('swaps', d.pending_swaps); App.setCount('timesheet', d.pending_days);
    $('#body').innerHTML = `<div class="stats">
        <div class="stat"><div class="label">Ca trong ngày</div><div class="value">${d.total}</div></div>
        <div class="stat"><div class="label">Đang trong ca</div><div class="value">${d.working}</div></div>
        <div class="stat"><div class="label">Đã xong</div><div class="value">${d.done}</div></div>
        <div class="stat"><div class="label">Ngày chờ duyệt chấm công</div><div class="value ${d.pending_days ? 'accent' : ''}">${d.pending_days}</div></div>
        <div class="stat"><div class="label">Phiếu đổi ca chờ duyệt</div><div class="value">${d.pending_swaps}</div></div>
        <div class="stat"><div class="label">Đăng ký ${d.reg_key.length === 7 ? fmtYM(d.reg_key).toLowerCase() : 'tuần ' + fmtDM(d.reg_week)}</div><div class="value">${d.availability_submitted}<span class="muted" style="font-size:16px"> / ${d.active_ctv}</span></div></div>
      </div>
      <div class="card"><div class="card-head"><h2>Ca trực ${fmtDate(d.day)}</h2><a class="btn btn-sm" href="#schedule">Xếp lịch</a></div><div id="tbl"></div></div>`;
    dataTable($('#tbl'), d.schedule, [
      { label: 'Ca', render: s => `<b>${s.start}–${s.end}</b>` },
      { label: 'CTV', render: s => `${esc(s.username)}<br><span class="small muted">${esc(s.name)}</span>` },
      { label: 'Vị trí', render: s => `${esc(s.position || '')}<br><span class="small muted">${esc(s.team || '')}</span>` },
      { label: 'Trạng thái', render: attStatus },
    ], { pageSize: 50, empty: 'Không có ca nào trong ngày' });
  };
  $('#day').onchange = e => { day = e.target.value || todayStr(); load(); };
  load();
}

/* =========================================================
   2. Xếp lịch
   ========================================================= */
/* Duyệt lịch tuần (CTV mới thấy lịch) + đẩy lên tab "Lịch trực" của Google Sheet */
async function weekSyncDialog(start, after) {
  const end = ymd(addDays(parseDate(start), 6));
  modal({
    title: `Duyệt lịch tuần ${fmtDM(start)} – ${fmtDM(end)}`, wide: true,
    body: `<div id="ws">${loading()}</div>`,
    footer: `<span id="ws-st" class="small muted" style="margin-right:auto"></span><button class="btn" id="ws-un" hidden>Bỏ duyệt</button><button class="btn" id="ws-push" hidden>Chỉ đẩy lại lên Sheet</button><button class="btn" data-close>Đóng</button><button class="btn btn-primary" id="ws-ok" disabled>Duyệt lịch tuần</button>`,
    async onOpen(el, close) {
      el.querySelector('.modal').classList.add('modal-xl');
      let cfg, pv, wk;
      const setup = () => `<div class="notice" style="border-color:var(--border);background:var(--surface-2)">
          <b>Cài đặt 1 lần để portal tự ghi lịch vào sheet</b> <span class="muted small">(không bắt buộc — vẫn duyệt được, chỉ là chưa ghi sheet)</span>
          <ol class="small" style="margin:8px 0 8px 18px;line-height:1.7">
            <li>Mở <a href="${esc(pv ? pv.sheet_url : '#')}" target="_blank" rel="noopener">Google Sheet</a> → <b>Tiện ích mở rộng → Apps Script</b>.</li>
            <li>Xoá code mẫu, dán đoạn code bên dưới → bấm 💾 Lưu.</li>
            <li><b>Triển khai → Tùy chọn triển khai mới</b> → loại <b>Ứng dụng web</b>; Thực thi với tư cách: <b>Tôi</b>; Người có quyền truy cập: <b>Bất kỳ ai</b> → Triển khai → cho phép quyền.</li>
            <li>Sao chép <b>URL ứng dụng web</b> (dạng https://script.google.com/macros/s/…/exec) dán vào ô dưới → Lưu.</li>
          </ol>
          <div style="position:relative"><textarea class="input mono" id="ws-code" rows="7" readonly style="font-size:11.5px">${esc(cfg.script)}</textarea>
            <button class="btn btn-sm" id="ws-copy" style="position:absolute;right:8px;top:8px">${icon('copy')} Sao chép</button></div>
          <div class="form-row" style="margin-top:10px"><div class="field"><label>URL ứng dụng web (Apps Script)</label><input class="input" id="ws-url" value="${esc(cfg.url)}" placeholder="https://script.google.com/macros/s/…/exec"></div>
            <div class="field"><label>Link Google Sheet có tab “Lịch trực”</label><input class="input" id="ws-sheet" value="${esc(cfg.sheet)}"></div></div>
          <button class="btn" id="ws-save">Lưu cài đặt</button>
          <p class="small muted" style="margin-top:6px">Mã bảo mật trong code là riêng của portal này — không chia sẻ code ra ngoài.</p></div>`;
      const shiftLabel = g => ({ sang: 'Sáng', chieu: 'Chiều', toi: 'Tối' }[g] || g);
      const paint = () => {
        const ok = !!cfg.url;
        const warn = [...pv.missing.map(d => `Sheet chưa có cột ngày ${fmtDM(d)} — ngày này sẽ bỏ qua`), ...pv.unplaced.map(x => `Không có ô phù hợp: ${esc(x)}`),
          ...pv.days.flatMap(d => d.overflow).map(x => `Nhiều người hơn số ô (${esc(x)}) — gộp vào ô cuối bằng dấu /`)];
        const changed = pv.days.reduce((a, d) => a + d.values.filter((v, i) => v.trim() !== (d.current[i] || '').trim()).length, 0);
        $('#ws', el).innerHTML = `
          ${wk.approved_at ? `<div class="notice" style="border-color:var(--green);background:var(--green-soft)">Tuần này đã duyệt lúc ${hm(wk.approved_at)} ${fmtDate(wk.approved_at.slice(0, 10))} bởi ${esc(wk.approved_by)}${pv.approved ? ` · đã ghi sheet lúc ${hm(pv.approved.at)} ${fmtDate(pv.approved.at.slice(0, 10))}` : ''}.</div>` : ''}
          ${ok ? '' : setup()}
          <p class="small muted" style="margin:6px 0 10px">Xem trước nội dung sẽ ghi vào tab <b>${esc(pv.tab)}</b>, hàng ${pv.slots[0].row}–${pv.slots[pv.slots.length - 1].row}. Ô viền vàng là ô sẽ thay đổi (di chuột để xem giá trị đang có). Người đã có trong sheet được giữ nguyên ô.</p>
          ${warn.length ? `<div class="notice">${warn.map(w => `<div>• ${w}</div>`).join('')}</div>` : ''}
          <div class="table-wrap"><table class="table ws"><thead><tr><th>Hàng</th><th>Ca · vị trí</th>${pv.days.map(d => `<th>${dowOf(d.date)} ${fmtDM(d.date)}<span class="muted small"> · cột ${d.col}</span></th>`).join('')}</tr></thead><tbody>
            ${pv.slots.map((s, i) => `<tr class="${i && pv.slots[i - 1].shift !== s.shift ? 'sep' : ''}"><td class="muted mono">${s.row}</td><td class="nowrap"><b>${shiftLabel(s.shift)}</b> <span class="muted small">${s.kind === 'monitor' ? 'Monitor' : 'Page + Hotline'}</span></td>
              ${pv.days.map(d => { const v = d.values[i], c = (d.current[i] || '').trim(); const diff = v.trim() !== c;
                return `<td class="${diff ? 'diff' : ''}" ${diff ? `title="Đang là: ${esc(c || '(trống)')}"` : ''}>${esc(v) || '<span class="muted">—</span>'}</td>`; }).join('')}</tr>`).join('')}
          </tbody></table></div>`;
        $('#ws-st', el).textContent = changed ? `${changed} ô sẽ thay đổi` : 'Sheet đã khớp với lịch hiện tại';
        btns();
        $('#ws-copy', el)?.addEventListener('click', () => { navigator.clipboard.writeText(cfg.script).then(() => toast('Đã sao chép code')); });
        $('#ws-save', el)?.addEventListener('click', e => run(e.currentTarget, async () => {
          await api('/admin/sheet-sync/config', { method: 'PUT', body: { url: $('#ws-url', el).value, sheet: $('#ws-sheet', el).value } });
          toast('Đã lưu cài đặt'); await load();
        }));
      };
      const btns = () => {
        const ok = !!(cfg && cfg.url);
        $('#ws-ok', el).disabled = false;
        $('#ws-ok', el).textContent = wk.approved_at ? (ok ? 'Duyệt lại & đẩy lên Sheet' : 'Duyệt lại') : ok ? 'Duyệt & đẩy lên Sheet' : 'Duyệt lịch tuần';
        $('#ws-un', el).hidden = !wk.approved_at;
        $('#ws-push', el).hidden = !(wk.approved_at && ok);
      };
      const load = async () => {
        wk = await api('/admin/week', { query: { start } });
        try {
          [cfg, pv] = await Promise.all([api('/admin/sheet-sync/config'), api('/admin/sheet-sync/preview', { query: { start } })]);
          paint();
        } catch (e) {
          $('#ws', el).innerHTML = `<div class="notice">Không xem trước được Google Sheet: ${esc(e.message)}<br>Bạn vẫn có thể duyệt lịch trên portal.</div>`;
          btns();
        }
      };
      $('#ws-un', el).onclick = e => run(e.currentTarget, async () => {
        await api('/admin/week/unapprove', { method: 'POST', body: { start } }); toast('Đã bỏ duyệt — CTV tạm không thấy lịch tuần này'); close(); after && after();
      });
      $('#ws-push', el).onclick = e => run(e.currentTarget, async () => {
        const r = await api('/admin/sheet-sync/push', { method: 'POST', body: { start } }); toast(`Đã ghi ${r.days} ngày lên Google Sheet`); close(); after && after();
      });
      $('#ws-ok', el).onclick = async e => {
        const btn = e.currentTarget;
        const push = !!(cfg && cfg.url && pv);
        if (!(await confirmDialog(`Duyệt lịch tuần ${fmtDM(start)} – ${fmtDM(end)}?`, `CTV sẽ thấy lịch và nhận thông báo lịch tuần đã chốt.${push ? ` Hàng ${pv.slots[0].row}–${pv.slots[pv.slots.length - 1].row} tab “${pv.tab}” trên Google Sheet sẽ được ghi theo lịch này.` : ''}`, 'Duyệt'))) return;
        run(btn, async () => {
          const r = await api('/admin/week/approve', { method: 'POST', body: { start, push } });
          if (r.push_error) toast(`Đã duyệt, nhưng chưa ghi được sheet: ${r.push_error}`, 'error');
          else toast(r.pushed ? 'Đã duyệt & ghi lên Google Sheet' : 'Đã duyệt lịch tuần');
          close(); after && after();
        });
      };
      load();
    },
  });
}

let boardStart = mondayOf(new Date());
async function aSchedule(v) {
  const shifts = App.meta.shifts;
  const avCache = {};
  let list = [], users = [];
  v.innerHTML = pageHead('Xếp lịch', 'Bấm “+ Thêm” để xếp CTV vào ca, bấm vào tên CTV để sửa giờ vào / ra, ca hoặc vị trí.',
    `<button class="btn" id="copy">${icon('copy')} Sao chép tuần trước</button><button class="btn" id="auto">${icon('refresh')} Tự xếp ca</button><button class="btn btn-primary" id="sync">${icon('check')} Duyệt lịch tuần</button>`) + `
    <div class="filters">
      <button class="btn btn-icon" id="prev" aria-label="Tuần trước">${icon('chevL')}</button>
      <button class="btn" id="this">Tuần này</button>
      <button class="btn btn-icon" id="next" aria-label="Tuần sau">${icon('chevR')}</button>
      <strong id="range" style="margin-left:8px"></strong><span style="flex:1"></span>
    </div>
    <div id="wk-st"></div>
    <div class="card"><div class="table-wrap" id="board">${loading()}</div></div>
    <p class="small muted" style="margin-top:8px">Đây là lịch dự kiến. Thay đổi thực tế (PIC, vị trí, giờ vào muộn…) sửa ở mục <a href="#timesheet">Chấm công</a> rồi duyệt — lương tính theo bản đã duyệt.</p>`;

  const availability = async ym => avCache[ym] || (avCache[ym] = await api('/admin/availability', { query: { ym } }));

  const load = async () => {
    const end = addDays(boardStart, 6);
    $('#range').textContent = `${fmtDate(ymd(boardStart))} – ${fmtDate(ymd(end))}`;
    let wk;
    [list, users, wk] = await Promise.all([api('/admin/schedules', { query: { start: ymd(boardStart), end: ymd(end) } }), users.length ? users : api('/admin/users'),
      api('/admin/week', { query: { start: ymd(boardStart) } })]);
    paintWeek(wk);
    const shown = list;
    const days = Array.from({ length: 7 }, (_, i) => ymd(addDays(boardStart, i)));
    $('#board').innerHTML = `<div class="board"><div class="bh"></div>${days.map(d => `<div class="bh ${d === todayStr() ? 'today' : ''}">${dowOf(d)}<b>${fmtDM(d)}</b></div>`).join('')}
      ${mainShifts().map(sh => `<div class="br">${esc(sh.name)}<span>${sh.start}–${sh.end}</span></div>${days.map(d => {
        const items = shown.filter(s => s.date === d && shiftGroup(s.shift_code) === sh.code)  // ca gãy tối nằm chung dòng Tối
          .sort((a, b) => a.start.localeCompare(b.start) || a.username.localeCompare(b.username));
        const ni = needInfo(items.length, sh);
        return `<div class="cell">${ni.target ? `<div class="need ${ni.cls}">${ni.text}${ni.missing ? ` · thiếu ${ni.missing}` : ''}</div>` : ''}${items.map(s => `<div class="pill ${s.approved_at ? 'in' : ''} ${s.source === 'auto' ? 'auto' : ''}" data-edit-s="${s.id}" role="button" tabindex="0" title="Bấm để sửa giờ / ca · ${esc(s.name)} · ${s.start}–${s.end} · ${esc(s.position || '')}${s.source === 'auto' ? ' · hệ thống tự xếp' : ''}${s.approved_at ? ' · đã chấm công' : ''}">
          <span>${esc(s.username)} <span class="muted">${esc(s.position || '')}</span>${s.shift_code !== sh.code ? ` <span class="tag-mon">${esc(shortShift(s.shift_code))}</span>` : ''}${s.start !== sh.start || s.end !== sh.end ? `<br><span class="pill-time">${s.start}–${s.end}</span>` : ''}</span>
          ${s.approved_at ? '' : `<button class="rm" data-rm="${s.id}" aria-label="Xoá">×</button>`}</div>`).join('')}
          <button class="add-chip" data-add="${d}|${sh.code}">+ Thêm</button></div>`;
      }).join('')}`).join('')}</div>`;
  };

  $('#board').onclick = async e => {
    const rm = e.target.closest('[data-rm]'), add = e.target.closest('[data-add]'), pill = !rm && e.target.closest('[data-edit-s]');
    if (pill) editDialog(list.find(x => x.id === +pill.dataset.editS));
    if (rm) {
      const s = list.find(x => x.id === +rm.dataset.rm);
      if (!(await confirmDialog('Xoá ca này?', `${s.username} · ${fmtDate(s.date)} ${s.start}–${s.end}`, 'Xoá', true))) return;
      run(null, async () => { await api(`/admin/schedules/${s.id}`, { method: 'DELETE' }); toast('Đã xoá ca'); load(); });
    }
    if (add) {
      const [d, code] = add.dataset.add.split('|');
      assignDialog(d, shifts.find(s => s.code === code), await availability(ymd(mondayOf(parseDate(d)))));  // đăng ký theo tuần (+ lịch tháng nếu chưa đăng ký tuần)
    }
  };

  const sheetToast = (msg, r) => r && r.sheet_error ? toast(`${msg} — nhưng chưa ghi được sheet Lịch trực: ${r.sheet_error}`, 'error')
    : toast(r && r.sheet === 'updated' ? `${msg} · đã cập nhật sheet Lịch trực` : msg);
  /* sửa 1 ca đã xếp: người trực, ca, giờ vào / ra, vị trí, ghi chú */
  function editDialog(s) {
    if (s.approved_at) return toast('Ca này đã chấm công — sửa ở mục Chấm công (bỏ duyệt ngày đó trước)', 'info');
    modal({
      title: `Sửa ca · ${esc(s.username)} · ${dowOf(s.date)} ${fmtDate(s.date)}`,
      body: `<div class="field"><label>CTV trực (PIC)</label><select class="input" id="es-user">${users.filter(u => u.active || u.id === s.user_id).sort((a, b) => a.username.localeCompare(b.username)).map(u => `<option value="${u.id}" ${u.id === s.user_id ? 'selected' : ''}>${esc(u.username)} · ${esc(u.name)}</option>`).join('')}</select>
          <span class="hint">Đổi ca ngoài web thì chọn người làm thay — hệ thống ghi “Đổi ca: A → B” vào chấm công.</span></div>
        <div class="field"><label>Ca</label><select class="input" id="es-shift">${shifts.map(x => `<option value="${x.code}" ${x.code === s.shift_code ? 'selected' : ''}>${esc(x.name)} (${x.start}–${x.end})</option>`).join('')}</select></div>
        <div class="form-row"><div class="field"><label>Giờ vào</label><input type="time" class="input" id="es-start" value="${s.start}" step="300"></div>
          <div class="field"><label>Giờ ra</label><input type="time" class="input" id="es-end" value="${s.end}" step="300"></div></div>
        <div class="field"><label>Vị trí</label><select class="input" id="es-pos">${App.meta.positions.map(p => `<option value="${p.id}" ${p.id === s.position_id ? 'selected' : ''}>${esc(p.name)}</option>`).join('')}</select></div>
        <div class="field"><label>Ghi chú</label><input class="input" id="es-note" value="${esc(s.note || '')}" placeholder="VD: vào muộn 30p, kèm CTV…"></div>`,
      footer: `<button class="btn btn-danger" id="es-del" style="margin-right:auto">Xoá ca</button><button class="btn" data-close>Huỷ</button><button class="btn btn-primary" id="es-ok">Lưu</button>`,
      onOpen(el, close) {
        searchSelect($('#es-user', el));
        $('#es-shift', el).onchange = e => { const x = shifts.find(y => y.code === e.target.value); $('#es-start', el).value = x.start; $('#es-end', el).value = x.end; };
        $('#es-ok', el).onclick = ev => run(ev.currentTarget, async () => {
          if (!$('#es-user', el).value) throw new Error('Vui lòng chọn CTV trực trong danh sách gợi ý');
          const r = await api(`/admin/schedules/${s.id}`, { method: 'PUT', body: { user_id: +$('#es-user', el).value, shift_code: $('#es-shift', el).value, start: $('#es-start', el).value, end: $('#es-end', el).value,
            position_id: +$('#es-pos', el).value, note: $('#es-note', el).value } });
          close(); sheetToast('Đã sửa ca', r); load();
        });
        $('#es-del', el).onclick = async ev => {
          if (!(await confirmDialog('Xoá ca này?', `${s.username} · ${fmtDate(s.date)} ${s.start}–${s.end}`, 'Xoá', true))) return;
          run(ev.currentTarget, async () => { const r = await api(`/admin/schedules/${s.id}`, { method: 'DELETE' }); close(); sheetToast('Đã xoá ca', r); load(); });
        };
      },
    });
  }

  function assignDialog(d, sh, av) {
    const taken = new Set(list.filter(s => s.date === d && t2m(s.start) < t2m(sh.end) && t2m(s.end) > t2m(sh.start)).map(s => s.user_id));
    const main = shifts.find(x => x.code === shiftGroup(sh.code)) || sh;
    const grp = shiftVariants(main).length ? shiftVariants(main) : [sh];
    const multi = grp.length > 1;   // Tối: Ca full / Ca gãy → admin chọn ca cho từng CTV
    const key = `${dowKey(d)}-${sh.code}`, gkey = `${dowKey(d)}-${shiftGroup(sh.code)}`;  // ca gãy tối → xem đăng ký ca Tối
    const ctvs = users.filter(u => u.role === 'ctv' && u.active && !taken.has(u.id)).map(u => {
      const a = av.users.find(x => x.id === u.id);
      if (multi) {
        const regs = grp.filter(x => a && a.slots[`${dowKey(d)}-${x.code}`]);
        const code = (regs.find(x => x.code === sh.code) || regs[0] || sh).code;
        return { ...u, regs, code, fit: regs.length ? 2 : 0, a };
      }
      const slot = a && (a.slots[key] || a.slots[gkey]);
      const fit = !slot ? 0 : (t2m(slot.start) <= t2m(sh.start) && t2m(slot.end) >= t2m(sh.end)) ? 2 : 1;
      return { ...u, slot, fit };
    }).sort((a, b) => b.fit - a.fit || a.username.localeCompare(b.username));
    const fitBadge = c => multi
      ? (c.regs.length ? c.regs.map(x => { const z = c.a.slots[`${dowKey(d)}-${x.code}`]; return `<span class="badge green" title="Đã đăng ký ${z.start}–${z.end}">ĐK ${esc(variantLabel(x))}</span>`; }).join(' ') : '<span class="badge">Chưa đăng ký</span>')
      : c.fit === 2 ? `<span class="badge green">Rảnh ${c.slot.start}–${c.slot.end}</span>` : c.fit === 1 ? `<span class="badge amber">Rảnh một phần ${c.slot.start}–${c.slot.end}</span>` : '<span class="badge">Chưa đăng ký</span>';
    const pickShift = c => multi ? `<select class="input as-ca" data-ca="${c.id}" style="width:auto;height:30px;padding:0 6px;font-size:13px" title="Ca xếp cho ${esc(c.username)}">${grp.map(x => `<option value="${x.code}" ${x.code === c.code ? 'selected' : ''}>${esc(variantLabel(x))}</option>`).join('')}</select>` : '';
    modal({
      title: `Xếp ca · ${esc(main.name)} ${dowOf(d)} ${fmtDate(d)}`, wide: true,
      body: `<div class="form-row">
          <div class="field"><label>Vị trí</label><select class="input" id="as-pos">${App.meta.positions.map(p => `<option value="${p.id}">${esc(p.name)} · ${esc((App.meta.teams.find(t => t.id === p.team_id) || {}).name || '')}</option>`).join('')}</select></div>
          ${multi ? '' : `<div class="field"><label>Giờ làm</label><div style="display:flex;gap:8px;align-items:center"><input type="time" class="input" id="as-start" value="${sh.start}" step="900"> – <input type="time" class="input" id="as-end" value="${sh.end}" step="900"></div></div>`}
        </div>
        ${multi ? `<p class="small muted" style="margin:-4px 0 10px">Chọn <b>Ca full</b> hoặc <b>Ca gãy</b> cho từng CTV (mặc định theo ca bạn ấy đăng ký). Giờ làm theo ca đã chọn — cần giờ khác thì bấm vào tên sau khi xếp để sửa.</p>` : ''}
        <div class="field"><label>Chọn CTV (có thể chọn nhiều)</label>
          <div class="search" style="margin-bottom:8px">${icon('search')}<input class="input full" id="as-q" placeholder="Tìm CTV"></div>
          <div id="as-list" style="max-height:320px;overflow:auto;border:1px solid var(--border);border-radius:8px">
          ${ctvs.length ? ctvs.map(c => `<label data-name="${esc((c.username + ' ' + c.name).toLowerCase())}" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-bottom:1px solid var(--border);cursor:pointer;flex-wrap:wrap">
            <input type="checkbox" value="${c.id}"><span style="flex:1;min-width:140px"><b>${esc(c.username)}</b> <span class="muted">${esc(c.name)}</span></span>${fitBadge(c)}${pickShift(c)}</label>`).join('') : emptyState('Tất cả CTV đều đã có ca trùng giờ')}
          </div></div>`,
      footer: `<button class="btn" data-close>Huỷ</button><button class="btn btn-primary" id="as-ok">Xếp ca</button>`,
      onOpen(el, close) {
        $('#as-q', el).oninput = e => { const q = foldVi(e.target.value.trim()); $$('#as-list label', el).forEach(l => { l.hidden = !foldVi(l.dataset.name).includes(q); }); };
        // chọn ca cho 1 CTV thì tự tích chọn bạn ấy
        $$('.as-ca', el).forEach(x => { x.onchange = () => { x.closest('label').querySelector('input[type=checkbox]').checked = true; }; });
        $('#as-ok', el).onclick = ev => run(ev.currentTarget, async () => {
          const ids = $$('#as-list input:checked', el).map(i => +i.value);
          if (!ids.length) throw new Error('Chưa chọn CTV nào');
          const pos = +$('#as-pos', el).value, errors = [];
          for (const id of ids) {
            let body;
            if (multi) { const x = grp.find(y => y.code === $(`[data-ca="${id}"]`, el).value); body = { shift_code: x.code, start: x.start, end: x.end }; }
            else body = { shift_code: sh.code, start: $('#as-start', el).value, end: $('#as-end', el).value };
            await api('/admin/schedules', { method: 'POST', body: { ...body, date: d, position_id: pos, user_id: id } }).catch(e => errors.push(e.message));
          }
          close(); load();
          errors.length ? toast(`Xếp được ${ids.length - errors.length}/${ids.length}. ${errors[0]}`, 'error') : toast(`Đã xếp ${ids.length} CTV`);
        });
      },
    });
  }

  $('#sync').onclick = () => weekSyncDialog(ymd(boardStart), load);
  $('#auto').onclick = async e => {
    const btn = e.currentTarget;
    if (!(await confirmDialog(`Tự xếp ca tuần ${fmtDM(ymd(boardStart))}?`, 'Hệ thống xếp theo đăng ký lịch rảnh và chỉ tiêu từng ca. Ca bạn đã xếp tay được giữ nguyên; các ca tự xếp trước đó (chưa chấm công) sẽ được xếp lại.', 'Tự xếp'))) return;
    run(btn, async () => {
      const r = await api('/admin/week/auto', { method: 'POST', body: { start: ymd(boardStart) } });
      toast(`Đã tự xếp ${r.added} ca${r.short.length ? ` · ${r.short.length} ô còn thiếu người` : ''}`); load();
    });
  };
  function paintWeek(wk) {
    const G = { sang: 'Sáng', chieu: 'Chiều', toi: 'Tối' };
    const dl = wk.deadline.slice(11, 16) + ' ' + fmtDM(wk.deadline.slice(0, 10)), gt = wk.gen_time.slice(11, 16) + ' ' + fmtDM(wk.gen_time.slice(0, 10));
    const byMonth = wk.reg_mode === 'month', regLbl = byMonth ? 'theo tháng (' + fmtYM(wk.reg_key).toLowerCase() + ')' : 'theo tuần';
    const rep_ = wk.report || {};
    const status = wk.approved_at ? `<span class="badge green">Đã duyệt</span> <span class="small muted">${esc(wk.approved_by || '')} · ${hm(wk.approved_at)} ${fmtDate(wk.approved_at.slice(0, 10))} — CTV đã thấy lịch. Vẫn sửa được (bấm vào tên để đổi người / giờ); thay đổi hiện ngay cho CTV${wk.sync ? ' và tự cập nhật sheet' : ''}.</span>`
      : wk.generated_at ? `<span class="badge amber">Bản nháp tự xếp — chờ duyệt</span> <span class="small muted">${esc(wk.generated_by || '')} xếp lúc ${hm(wk.generated_at)} ${fmtDate(wk.generated_at.slice(0, 10))}. CTV chưa thấy lịch tuần này cho tới khi bạn bấm “Duyệt lịch tuần”.</span>`
      : byMonth && wk.registered_week ? `<span class="badge">Chưa tự xếp</span> <span class="small muted">CTV đăng ký ${regLbl}${wk.reg_open ? ' — vẫn đang nhận đăng ký' : ''} · hệ thống tự xếp lúc ${gt}, hoặc bấm “Tự xếp ca” để xếp ngay.</span>`
      : !byMonth && wk.reg_open ? `<span class="badge blue">Đang nhận đăng ký</span> <span class="small muted">Hạn chót ${dl} · tự xếp ca lúc ${gt}</span>`
      : wk.registered_week ? `<span class="badge">Chưa tự xếp</span> <span class="small muted">Hạn đăng ký đã qua (${dl}). Bấm “Tự xếp ca” để xếp ngay.</span>`
      : `<span class="badge">Lịch xếp tay</span> <span class="small muted">Tuần này không có CTV đăng ký ${regLbl} — lịch do admin xếp, CTV đang thấy bình thường.</span>`;
    $('#wk-st').innerHTML = `<div class="wk-st card card-pad">
      <div>${status}</div>
      <div class="small muted" style="margin-top:6px">${wk.registered_week}/${wk.active_ctv} CTV đã đăng ký ${regLbl}${wk.registered > wk.registered_week ? ` (+${wk.registered - wk.registered_week} bạn dùng lịch rảnh ${byMonth ? 'tuần' : 'tháng'})` : ''} · <a href="#availability" id="go-av">xem đăng ký</a>${wk.sync ? ` · đã ghi sheet lúc ${hm(wk.sync.at)} ${fmtDate(wk.sync.at.slice(0, 10))}` : ''}</div>
      ${!wk.approved_at && rep_.short && rep_.short.length ? `<div class="low-list" style="margin-top:8px">${rep_.short.map(x => `<span class="chip-low">${dowOf(x.date)} ${fmtDM(x.date)} · ${G[x.group] || x.group}: ${x.have}/${x.need} <b>thiếu ${x.need - x.have}</b>${x.registered <= x.have ? ' (hết người đăng ký)' : ''}</span>`).join('')}</div>` : ''}
      ${!wk.approved_at && rep_.no_monitor && rep_.no_monitor.length ? `<p class="small" style="margin-top:6px;color:var(--amber)">Ca tối chưa có Monitor: ${rep_.no_monitor.map(fmtDM).join(', ')}</p>` : ''}
    </div>`;
    $('#go-av').onclick = () => { avWeek = byMonth ? wk.reg_key : ymd(boardStart); };
  }
  $('#prev').onclick = () => { boardStart = addDays(boardStart, -7); load(); };
  $('#next').onclick = () => { boardStart = addDays(boardStart, 7); load(); };
  $('#this').onclick = () => { boardStart = mondayOf(new Date()); load(); };
  $('#copy').onclick = async e => {
    if (!(await confirmDialog('Sao chép tuần trước?', `Toàn bộ ca của tuần ${fmtDate(ymd(addDays(boardStart, -7)))} sẽ được chép sang tuần đang xem. Ca bị trùng giờ sẽ được bỏ qua.`, 'Sao chép'))) return;
    run(e.currentTarget, async () => {
      const r = await api('/admin/schedules/copy-week', { method: 'POST', body: { from: ymd(addDays(boardStart, -7)), to: ymd(boardStart) } });
      toast(`Đã thêm ${r.added} ca`); load();
    });
  };
  load();
}

/* =========================================================
   3. Lịch rảnh CTV
   ========================================================= */
let avWeek = null;
async function aAvailability(v) {
  const thisMon = mondayOf(new Date()), now = new Date();
  const mode = App.meta.reg_mode === 'month' ? 'month' : 'week';
  const opts = mode === 'month'
    ? [-1, 0, 1, 2].map(i => ymOf(new Date(now.getFullYear(), now.getMonth() + i, 1)))
    : [-1, 0, 1, 2].map(i => ymd(addDays(thisMon, 7 * i)));
  let ym = avWeek && (avWeek.length === 7) === (mode === 'month') ? avWeek : opts[2];
  avWeek = null;
  const wl = w => `${fmtDM(w)} – ${fmtDM(ymd(addDays(parseDate(w), 6)))}`;
  const optLabel = mode === 'month'
    ? w => w === opts[1] ? 'Tháng này' : fmtYM(w)
    : w => w === ymd(thisMon) ? 'Tuần này' : w < ymd(thisMon) ? 'Tuần trước' : 'Tuần ' + wl(w);
  const shifts = App.meta.shifts;
  // ca chính có ca phụ (Tối = Ca full + Ca gãy): CTV đăng ký ca nào trong nhóm cũng tính là rảnh ca Tối
  const isMainMulti = s => s.code === shiftGroup(s.code) && shiftVariants(s).length > 1;
  const regd = (u, k, s) => isMainMulti(s) ? shiftVariants(s).some(x => u.slots[`${k}-${x.code}`]) : !!u.slots[`${k}-${s.code}`];
  const regNote = (u, k, s) => { const n = (isMainMulti(s) ? shiftVariants(s) : [s]).map(x => (u.slots[`${k}-${x.code}`] || {}).note).find(Boolean);
    return n ? `<div class="small" style="margin-top:4px">📝 ${esc(n)}</div>` : ''; };
  const regText = (u, k, s) => (isMainMulti(s) ? shiftVariants(s) : [s]).filter(x => u.slots[`${k}-${x.code}`])
    .map(x => { const z = u.slots[`${k}-${x.code}`]; return `<span class="badge accent">${isMainMulti(s) ? esc(variantLabel(x)) + ' ' : ''}${z.start}–${z.end}</span>`; }).join(' ') + regNote(u, k, s);
  v.innerHTML = pageHead('Lịch rảnh CTV', mode === 'month'
      ? 'CTV đăng ký 1 lần cho cả tháng (những ca rảnh hằng tuần), tự chốt 19:00 ngày 29 của tháng trước. 20:00 Chủ nhật hệ thống tự xếp ca tuần tới theo lịch tháng để bạn duyệt ở mục Xếp lịch.'
      : 'CTV đăng ký theo tuần, tự chốt 19:00 Chủ nhật; 20:00 hệ thống tự xếp ca để bạn duyệt ở mục Xếp lịch.') + `
    <div class="filters" style="margin-bottom:8px"><span class="small muted">Mở đăng ký theo</span>
      <div class="seg" id="mode"><button data-m="week" class="${mode === 'week' ? 'active' : ''}">Tuần</button><button data-m="month" class="${mode === 'month' ? 'active' : ''}">Tháng</button></div></div>
    <div class="filters"><div class="seg" id="wk">${opts.map(w => `<button data-w="${w}">${optLabel(w)}</button>`).join('')}</div>
      <span style="flex:1"></span><span id="toggle"></span><button class="btn" id="to-board">${icon('calendar')} ${mode === 'month' ? 'Xếp lịch' : 'Xếp lịch tuần này'}</button></div>
    <div id="body">${loading()}</div>`;
  const load = async () => {
    const d = await api('/admin/availability', { query: { ym } });
    $$('#wk button').forEach(b => b.classList.toggle('active', b.dataset.w === ym));
    $('#toggle').innerHTML = `<span class="badge ${d.open ? 'green' : ''}" style="margin-right:8px">${!d.open ? 'Đã chốt đăng ký' : mode === 'month' ? 'Đang mở · hạn 19:00 ngày ' + fmtDM(d.deadline.slice(0, 10)) : 'Đang mở · hạn 19:00 CN ' + fmtDM(ymd(addDays(parseDate(ym), -1)))}</span>
      <button class="btn" id="tg">${d.open ? (mode === 'month' ? 'Đóng đăng ký' : 'Đóng sớm') : (mode === 'month' ? 'Mở đăng ký' : 'Mở lại đăng ký')}</button>`;
    $('#tg').onclick = e => run(e.currentTarget, async () => { await api('/admin/reg-month', { method: 'PUT', body: { ym, open: !d.open } }); toast('Đã cập nhật'); load(); });
    const c = { submitted: 0, draft: 0, empty: 0 }; d.users.forEach(u => c[u.status || 'empty']++); d.users.forEach(u => { u.status = u.status || 'empty'; });
    const max = Math.max(1, d.users.length);
    const fromMonth = d.users.filter(u => u.source === 'month').length;
    $('#body').innerHTML = `${fromMonth ? `<div class="notice">${fromMonth} CTV chưa đăng ký theo tuần — đang hiển thị <b>lịch rảnh đăng ký theo tháng</b> của các bạn (nhãn “theo tháng”). Hệ thống cũng dùng lịch này khi tự xếp ca nếu bạn ấy không đăng ký tuần.</div>` : ''}<div class="stats">
        <div class="stat"><div class="label">Đã gửi đăng ký</div><div class="value">${c.submitted}</div></div>
        <div class="stat"><div class="label">Chưa gửi (nháp)</div><div class="value">${c.draft}</div></div>
        <div class="stat"><div class="label">Chưa nộp</div><div class="value ${c.empty ? 'accent' : ''}">${c.empty}</div></div></div>
      ${(() => { const low = []; shifts.forEach(s => [1, 2, 3, 4, 5, 6, 7].forEach(k => { const ni = needInfo(d.users.filter(u => regd(u, k, s)).length, s, true); if (ni.missing) low.push(`<button class="chip-low" data-slot="${k}-${s.code}">${k === 7 ? 'CN' : 'T' + (k + 1)} · ${esc(regName(s).replace(/^ca\s+/i, ''))}: ${ni.text} <b>thiếu ${ni.missing}</b></button>`); }));
        return `<div class="card card-pad"><h2 style="font-size:15px;margin-bottom:10px">Ca còn thiếu CTV ${low.length ? `<span class="badge red">${low.length}</span>` : ''}</h2>${low.length ? `<div class="low-list">${low.join('')}</div>` : '<p class="muted">✓ Tất cả các ca đã đủ CTV đăng ký</p>'}</div>`; })()}
      <div class="card card-pad"><h2 style="font-size:15px;margin-bottom:4px">Số CTV rảnh theo khung (đã chốt + nháp)</h2><p class="small muted" style="margin-bottom:12px">Đỏ: thiếu so với chỉ tiêu · xanh: đủ. Bấm vào ô để xem CTV nào đã đăng ký.</p>
        <div class="table-wrap"><div class="heat" style="min-width:560px"><div></div>${[1, 2, 3, 4, 5, 6, 7].map(k => `<div class="h">${k === 7 ? 'CN' : 'T' + (k + 1)}</div>`).join('')}
        ${shifts.map(s => `<div class="r">${esc(isMainMulti(s) ? s.name + ' (tổng)' : regName(s))}</div>${[1, 2, 3, 4, 5, 6, 7].map(k => {
          const n = d.users.filter(u => regd(u, k, s)).length; const ni = needInfo(n, s, true);
          return ni.target ? `<button class="c need-c ${ni.cls}" data-slot="${k}-${s.code}">${ni.text}${ni.missing ? `<small>thiếu ${ni.missing}</small>` : ''}</button>`
            : `<button class="c" data-slot="${k}-${s.code}" style="background:color-mix(in srgb, var(--accent) ${Math.round(n / max * 70)}%, var(--surface-2));color:${n / max > .45 ? '#fff' : 'var(--text)'}">${n}</button>`;
        }).join('')}`).join('')}</div></div></div>
      <div class="card"><div class="card-head"><h2>Danh sách CTV</h2>
        <button class="btn btn-sm" id="exp">${icon('download')} Xuất Excel</button></div><div id="tbl"></div></div>`;
    const ST = { submitted: ['Đã gửi', 'green'], draft: ['Nháp', 'amber'], empty: ['Chưa đăng ký', ''] };
    $('#body').onclick = e => {
      const c = e.target.closest('[data-slot]'); if (!c) return;
      const key = c.dataset.slot, [k, code] = [+key.split('-')[0], key.slice(key.indexOf('-') + 1)];
      const s = shifts.find(x => x.code === code), who = d.users.filter(u => regd(u, k, s));
      const ni = needInfo(who.length, s, true);
      modal({ title: `${k === 7 ? 'Chủ nhật' : 'Thứ ' + (k + 1)} · ${esc(isMainMulti(s) ? s.name : regName(s))} (${s.start}–${s.end})`,
        body: `<p style="margin-bottom:10px">${ni.target ? `Đã đăng ký <b>${who.length}</b> / cần <b>${ni.target}</b> CTV${ni.missing ? ` — <span class="accent">thiếu ${ni.missing}</span>` : ' — đủ'}` : `<b>${who.length}</b> CTV đăng ký`}</p>
          ${who.length ? `<table class="table"><tbody>${who.map(u => `<tr><td><b>${esc(u.username)}</b><br><span class="small muted">${esc(u.name)}</span></td><td>${regText(u, k, s)}</td><td><span class="badge ${ST[u.status][1]}">${ST[u.status][0]}</span></td></tr>`).join('')}</tbody></table>` : emptyState('Chưa có CTV nào đăng ký khung này')}` });
       };
    dataTable($('#tbl'), d.users, [
      { label: 'CTV', render: u => `<b>${esc(u.username)}</b><br><span class="small muted">${esc(u.name)}</span>` },
      { label: 'Team', render: u => esc(u.team || '—') },
      { label: 'Trạng thái', render: u => `<span class="badge ${ST[u.status][1]}">${ST[u.status][0]}</span>${u.source === 'month' ? ' <span class="badge" title="Chưa đăng ký theo tuần — đang dùng lịch rảnh đăng ký theo tháng">theo tháng</span>' : ''}` },
      { label: 'Số ca rảnh', render: u => `${Object.keys(u.slots).length || '—'}${Object.values(u.slots).some(x => x.note) ? ' <span class="badge amber" title="Có ghi chú vào muộn / ra sớm">📝 có ghi chú</span>' : ''}` },
      { label: 'Cập nhật', render: u => u.updated_at ? `<span class="small muted">${fmtDate(u.updated_at.slice(0, 10))} ${u.updated_at.slice(11, 16)}</span>` : '—' },
      { label: '', cls: 'right', render: u => `<div class="actions">${Object.keys(u.slots).length ? `<button class="btn btn-sm" data-view="${u.id}">Xem</button>` : ''}${u.status === 'submitted' && ym.length === 7 ? `<button class="btn btn-sm" data-unlock="${u.id}">Mở khoá</button>` : ''}</div>` },
    ], { pageSize: 50 });
    $('#tbl').addEventListener('click', async e => {
      const vb = e.target.closest('[data-view]'), ub = e.target.closest('[data-unlock]');
      if (vb) {
        const u = d.users.find(x => x.id === +vb.dataset.view);
        modal({ title: `Lịch rảnh · ${esc(u.username)}`, wide: true, body: `<div class="table-wrap"><table class="table"><thead><tr><th></th>${[1, 2, 3, 4, 5, 6, 7].map(k => `<th>${k === 7 ? 'CN' : 'T' + (k + 1)}</th>`).join('')}</tr></thead>
          <tbody>${shifts.map(s => `<tr><td><b>${esc(regName(s))}</b></td>${[1, 2, 3, 4, 5, 6, 7].map(k => { const x = u.slots[`${k}-${s.code}`]; return `<td>${x ? `<span class="badge accent">${x.start}–${x.end}</span>${x.note ? `<div class="small" style="margin-top:4px;max-width:150px">📝 ${esc(x.note)}</div>` : ''}` : '<span class="muted">—</span>'}</td>`; }).join('')}</tr>`).join('')}</tbody></table></div>` });
      }
      if (ub) {
        if (!(await confirmDialog('Mở khoá lịch rảnh?', 'CTV sẽ có thể sửa và chốt lại lịch rảnh tháng này.', 'Mở khoá'))) return;
        run(ub, async () => { await api('/admin/availability/unlock', { method: 'POST', body: { user_id: +ub.dataset.unlock, ym } }); toast('Đã mở khoá'); load(); });
      }
    });
    $('#exp').onclick = () => downloadCSV(`lich-ranh-${ym}.csv`, ['Username', 'Họ tên', 'Trạng thái', ...shifts.flatMap(s => [1, 2, 3, 4, 5, 6, 7].map(k => `${k === 7 ? 'CN' : 'T' + (k + 1)} ${regName(s)}`))],
      d.users.map(u => [u.username, u.name, ST[u.status][0], ...shifts.flatMap(s => [1, 2, 3, 4, 5, 6, 7].map(k => { const x = u.slots[`${k}-${s.code}`]; return x ? `${x.start}-${x.end}${x.note ? ` (${x.note})` : ''}` : ''; }))]));
  };
  $('#wk').onclick = e => { const b = e.target.closest('[data-w]'); if (b) { ym = b.dataset.w; load(); } };
  $('#mode').onclick = async e => {
    const b = e.target.closest('[data-m]'); if (!b || b.dataset.m === mode) return;
    const m = b.dataset.m;
    if (!(await confirmDialog(`Chuyển sang đăng ký theo ${m === 'month' ? 'tháng' : 'tuần'}?`, m === 'month'
      ? 'CTV sẽ đăng ký 1 lần cho cả tháng (những ca rảnh hằng tuần). Đăng ký tháng sau tự chốt 19:00 ngày 29 tháng này (bạn vẫn đóng sớm / mở lại được). Hệ thống vẫn tự xếp ca mỗi tuần dựa trên lịch tháng.'
      : 'CTV sẽ đăng ký từng tuần, tự chốt 19:00 Chủ nhật. CTV nào chưa đăng ký tuần thì hệ thống tạm dùng lịch rảnh tháng của bạn ấy.', 'Chuyển'))) return;
    run(b, async () => {
      await api('/admin/reg-mode', { method: 'PUT', body: { mode: m } });
      App.meta.reg_mode = m; toast(`Đã chuyển sang đăng ký theo ${m === 'month' ? 'tháng' : 'tuần'}`); aAvailability(v);
    });
  };
  $('#to-board').onclick = () => { boardStart = ym.length === 7 ? (ym === opts[1] ? thisMon : mondayOf(addDays(parseDate(ym + '-01'), 3))) : parseDate(ym); location.hash = '#schedule'; };
  load();
}

/* =========================================================
   4. Chấm công — bản raw theo lịch xếp, admin sửa rồi duyệt
   ========================================================= */
let tsDay = null;
async function aTimesheet(v) {
  let day = tsDay || todayStr(), data = null, list = [], users = [], dirty = false;
  tsDay = null;
  v.innerHTML = pageHead('Chấm công', 'Mỗi ngày hệ thống tạo bản raw từ lịch đã xếp. Kiểm tra, sửa PIC / vị trí / giờ thực tế rồi bấm Duyệt — lương tính theo bản đã duyệt.',
    `<button class="btn" id="exp">${icon('download')} Xuất Excel tháng</button>`) + `
    <div class="filters ts-head">
      <button class="btn btn-icon" id="prev" aria-label="Ngày trước">${icon('chevL')}</button>
      <input type="date" class="input" id="day">
      <button class="btn btn-icon" id="next" aria-label="Ngày sau">${icon('chevR')}</button>
      <button class="btn" id="today">Hôm nay</button>
      <span id="st" style="margin-left:8px"></span><span style="flex:1"></span><span id="acts" class="actions"></span>
    </div>
    <div class="ts-pending" id="pend"></div>
    <div class="card" id="body">${loading()}</div>`;

  const shiftLabel = code => esc(((App.meta.shifts.find(s => s.code === code) || {}).name || code).replace(/^ca\s+/i, ''));
  const userName = id => (users.find(u => u.id === id) || {}).username || '';
  const isChanged = (r, k) => r.orig && r.orig[k] !== r[k];

  const paint = () => {
    const locked = data.approved, future = day > todayStr();
    $('#day').value = day;
    $('#st').innerHTML = !data.rows.length ? '<span class="badge">Không có ca</span>'
      : locked ? `<span class="badge green">Đã duyệt</span> <span class="small muted">${esc(data.approved_by || '')} · ${hm(data.approved_at)} ${fmtDate((data.approved_at || '').slice(0, 10))}</span>`
      : future ? '<span class="badge">Chưa đến ngày</span>' : '<span class="badge amber">Chờ duyệt</span>';
    $('#acts').innerHTML = locked ? `<button class="btn" id="unap">Bỏ duyệt để sửa</button>`
      : `<button class="btn" id="add">${icon('plus')} Thêm dòng</button><button class="btn" id="save" ${dirty ? '' : 'disabled'}>Lưu</button>
         <button class="btn btn-primary" id="approve" ${future || !list.some(r => !r.delete) ? 'disabled' : ''}>Duyệt chấm công</button>`;
    const pend = data.pending_days.filter(d => d !== day || !locked);
    $('#pend').innerHTML = pend.length ? `<span class="muted">Ngày chưa duyệt:</span>${pend.slice(-14).map(d => `<button data-go="${d}" class="${d === day ? 'active' : ''}">${dowOf(d)} ${fmtDM(d)}</button>`).join('')}${pend.length > 14 ? `<span class="muted">+${pend.length - 14} ngày cũ hơn</span>` : ''}`
      : '<span class="muted">✓ Tất cả các ngày đã duyệt chấm công</span>';

    if (!list.length) { $('#body').innerHTML = emptyState('Không có ca nào trong ngày này' + (locked ? '' : ' — bấm “Thêm dòng” nếu có người trực')); return; }
    const userOpts = sel => users.filter(u => u.active || u.id === sel).map(u => `<option value="${u.id}" ${u.id === sel ? 'selected' : ''}>${esc(u.username)} · ${esc(u.name)}</option>`).join('');
    const posOpts = sel => App.meta.positions.map(p => `<option value="${p.id}" ${p.id === sel ? 'selected' : ''}>${esc(p.name)}</option>`).join('');
    const total = list.filter(r => !r.delete).reduce((a, r) => a + Math.max(0, hoursOf(r)), 0);
    $('#body').innerHTML = `<div class="table-wrap"><table class="table ts-table"><thead><tr>
        <th>Ca</th><th>PIC</th><th>Vị trí</th><th>Vào</th><th>Ra</th><th class="right">Giờ</th><th>Ghi chú</th><th></th></tr></thead><tbody>
      ${list.map((r, i) => locked ? `<tr>
          <td><b>${shiftLabel(r.shift_code)}</b></td>
          <td>${esc(userName(r.user_id))}${isChanged(r, 'user_id') ? `<div class="ts-orig">Lịch: ${esc(userName(r.orig.user_id))}</div>` : ''}</td>
          <td>${esc(posName(r.position_id))}</td>
          <td class="mono">${r.start}</td><td class="mono">${r.end}</td>
          <td class="right mono">${hoursOf(r)}</td>
          <td class="small">${planDiff(r.src) ? `<div>${planDiff(r.src)}</div>` : ''}<span class="muted">${esc(r.note || '')}</span></td><td></td></tr>`
        : `<tr class="${r.delete ? 'removed' : ''}" data-i="${i}">
          <td>${r.id ? `<b>${shiftLabel(r.shift_code)}</b>` : `<select class="input" data-k="shift_code">${App.meta.shifts.map(s => `<option value="${s.code}" ${s.code === r.shift_code ? 'selected' : ''}>${shiftLabel(s.code)}</option>`).join('')}</select>`}</td>
          <td><select class="input ${isChanged(r, 'user_id') ? 'changed' : ''}" data-k="user_id"><option value="">— Chọn PIC —</option>${userOpts(r.user_id)}</select>
            ${isChanged(r, 'user_id') ? `<div class="ts-orig">Lịch: ${esc(userName(r.orig.user_id))}</div>` : ''}</td>
          <td><select class="input ${isChanged(r, 'position_id') ? 'changed' : ''}" data-k="position_id">${posOpts(r.position_id)}</select></td>
          <td><input type="time" class="input ${isChanged(r, 'start') ? 'changed' : ''}" data-k="start" value="${r.start}">${isChanged(r, 'start') ? `<div class="ts-orig">Lịch: ${r.orig.start}</div>` : ''}</td>
          <td><input type="time" class="input ${isChanged(r, 'end') ? 'changed' : ''}" data-k="end" value="${r.end}">${isChanged(r, 'end') ? `<div class="ts-orig">Lịch: ${r.orig.end}</div>` : ''}</td>
          <td class="right mono" data-h>${hoursOf(r)}</td>
          <td><input class="input" data-k="note" value="${esc(r.note || '')}" placeholder="VD: vào muộn 30p"></td>
          <td class="right"><button class="btn btn-sm ${r.delete ? '' : 'btn-danger'}" data-del="${i}">${r.delete ? 'Hoàn tác' : 'Xoá'}</button></td></tr>`).join('')}
      </tbody><tfoot><tr><td colspan="5" class="right muted">Tổng giờ trong ngày</td><td class="right mono"><b id="tot">${total}</b></td><td colspan="2"></td></tr></tfoot></table></div>
      ${locked ? '' : '<p class="small muted card-pad">Ô viền vàng: khác với lịch xếp ban đầu. Xoá dòng nếu CTV nghỉ ca đó. Sau khi duyệt, CTV xem được ở mục Chấm công và ca được tính lương.</p>'}`;
  };

  const load = async () => {
    if (!users.length) users = (await api('/admin/users')).sort((a, b) => a.username.localeCompare(b.username));
    data = await api('/admin/timesheet', { query: { day } });
    list = data.rows.map(s => {
      let plan = null; try { plan = s.plan ? JSON.parse(s.plan) : null; } catch { }
      const base = plan && !plan.added ? plan : s;
      return { id: s.id, user_id: s.user_id, position_id: s.position_id, shift_code: s.shift_code, start: s.start, end: s.end, note: s.note || '',
        src: s, orig: { user_id: base.user_id, position_id: base.position_id, start: base.start, end: base.end } };
    });
    dirty = false;
    App.setCount('timesheet', data.pending_days.length);
    paint();
  };
  const go = async d => {
    if (dirty && !(await confirmDialog('Bỏ thay đổi chưa lưu?', 'Các chỉnh sửa của ngày này sẽ mất.', 'Bỏ thay đổi', true))) { $('#day').value = day; return; }
    day = d; $('#body').innerHTML = loading(); load();
  };
  const save = (btn, approve) => run(btn, async () => {
    const bad = list.find(r => !r.delete && !r.user_id);
    if (bad) throw new Error('Mỗi dòng cần chọn PIC');
    const r = await api('/admin/timesheet', { method: 'PUT', body: { day, approve,
      rows: list.map(x => ({ id: x.id, delete: x.delete, user_id: x.user_id, position_id: x.position_id, shift_code: x.shift_code, start: x.start, end: x.end, note: x.note })) } });
    toast(approve ? `Đã duyệt chấm công ${fmtDate(day)}` : `Đã lưu${r.changed ? ` ${r.changed} thay đổi` : ''}`);
    dirty = false;
    if (approve) { const nxt = data.pending_days.find(d => d !== day); if (nxt) { day = nxt; } }
    load();
  });

  $('#prev').onclick = () => go(ymd(addDays(parseDate(day), -1)));
  $('#next').onclick = () => go(ymd(addDays(parseDate(day), 1)));
  $('#today').onclick = () => go(todayStr());
  $('#day').onchange = e => e.target.value && go(e.target.value);
  $('#pend').onclick = e => { const b = e.target.closest('[data-go]'); if (b) go(b.dataset.go); };
  $('#acts').onclick = async e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.id === 'add') {
      const sh = App.meta.shifts[0];
      list.push({ id: null, user_id: null, position_id: App.meta.positions[0]?.id, shift_code: sh.code, start: sh.start, end: sh.end, note: '', orig: null });
      dirty = true; paint();
    }
    if (b.id === 'save') save(b, false);
    if (b.id === 'approve') {
      const n = list.filter(r => !r.delete).length;
      if (await confirmDialog(`Duyệt chấm công ${dowOf(day)} ${fmtDate(day)}?`, `${n} ca sẽ được tính lương và CTV xem được kết quả.`, 'Duyệt')) save(b, true);
    }
    if (b.id === 'unap') run(b, async () => { await api('/admin/timesheet/unapprove', { method: 'POST', body: { day } }); toast('Đã bỏ duyệt, có thể sửa lại'); load(); });
  };
  $('#body').addEventListener('change', e => {
    const k = e.target.dataset.k; const tr = e.target.closest('[data-i]'); if (!k || !tr) return;
    const r = list[+tr.dataset.i];
    let val = e.target.value;
    if (k === 'user_id' || k === 'position_id') val = val ? +val : null;
    r[k] = val;
    dirty = true;
    if (k === 'shift_code') { const sh = App.meta.shifts.find(s => s.code === val); r.start = sh.start; r.end = sh.end; paint(); return; }
    // cập nhật tại chỗ (không vẽ lại cả bảng để không mất cú bấm nút ngay sau khi rời ô)
    if (k !== 'note') e.target.classList.toggle('changed', isChanged(r, k));
    $('[data-h]', tr).textContent = hoursOf(r);
    $('#tot').textContent = list.filter(x => !x.delete).reduce((a, x) => a + Math.max(0, hoursOf(x)), 0);
    if ($('#save')) $('#save').disabled = false;
  });
  $('#body').addEventListener('click', e => {
    const b = e.target.closest('[data-del]'); if (!b) return;
    const i = +b.dataset.del;
    if (!list[i].id) list.splice(i, 1); else list[i].delete = !list[i].delete;
    dirty = true; paint();
  });
  $('#exp').onclick = async () => {
    const { start, end } = monthBounds(day.slice(0, 7));
    const all = await api('/admin/schedules', { query: { start, end } });
    downloadCSV(`cham-cong-${day.slice(0, 7)}.csv`, ['Ngày', 'Ca', 'PIC', 'Họ tên', 'Vị trí', 'Vào', 'Ra', 'Số giờ', 'Trạng thái', 'Ghi chú'],
      all.map(s => [fmtDate(s.date), s.shift_name, s.username, s.name, s.position, s.start, s.end, hoursOf(s), s.approved_at ? 'Đã duyệt' : 'Chờ duyệt', s.note]));
  };
  App.onLeave(() => { if (dirty) toast('Thay đổi chấm công chưa được lưu', 'info'); });
  load();
}

/* =========================================================
   5. Duyệt đổi ca
   ========================================================= */
async function aSwaps(v) {
  let rows = [], status = 'pending';
  const ST = { pending: ['Chờ duyệt', 'amber'], approved: ['Đã duyệt', 'green'], rejected: ['Từ chối', 'red'] };
  v.innerHTML = pageHead('Duyệt đổi ca', 'Khi duyệt, ca tự chuyển sang người làm thay: PIC trong Chấm công, lương và lịch của 2 bạn đều cập nhật; nếu tuần đã đẩy lên sheet Lịch trực thì sheet cũng được ghi lại.') + `<div class="filters"><div class="seg" id="seg"></div></div><div class="card" id="body">${loading()}</div>`;
  const paint = () => {
    const c = { all: rows.length, pending: 0, approved: 0, rejected: 0 }; rows.forEach(r => c[r.status]++);
    App.setCount('swaps', c.pending);
    $('#seg').innerHTML = [['pending', 'Chờ duyệt'], ['approved', 'Đã duyệt'], ['rejected', 'Từ chối'], ['all', 'Tất cả']]
      .map(([k, l]) => `<button class="${status === k ? 'active' : ''}" data-s="${k}">${l} <span class="n">${c[k]}</span></button>`).join('');
    dataTable($('#body'), rows.filter(r => status === 'all' || r.status === status), [
      { label: 'Ca', render: r => `<b>${dowOf(r.date)} ${fmtDate(r.date)}</b><br><span class="small muted">${r.start}–${r.end} · ${esc(r.position || '')}</span>` },
      { label: 'Người xin đổi → làm thay', render: r => `${esc(r.from_username)} → <b>${esc(r.to_username)}</b>${r.swap_schedule_id ? `<br><span class="small muted">🔁 Đổi chéo: ${esc(r.from_username)} nhận ca ${r.swap_start || '?'}–${r.swap_end || '?'}${r.swap_position ? ' · ' + esc(r.swap_position) : ''} của ${esc(r.to_username)}</span>` : ''}` },
      { label: 'Lý do', render: r => `<span class="muted">${esc(r.reason || '—')}</span>` },
      { label: 'Gửi lúc', render: r => `<span class="small muted nowrap">${fmtDate(r.created_at.slice(0, 10))} ${r.created_at.slice(11, 16)}</span>` },
      { label: 'Trạng thái', render: r => `<span class="badge ${ST[r.status][1]}">${ST[r.status][0]}</span>${r.handled_by ? `<br><span class="small muted">${esc(r.handled_by)}</span>` : ''}` },
      { label: '', cls: 'right', render: r => r.status === 'pending' ? `<div class="actions"><button class="btn btn-sm btn-danger" data-act="reject" data-id="${r.id}">Từ chối</button><button class="btn btn-sm btn-primary" data-act="approve" data-id="${r.id}">Duyệt</button></div>` : '' },
    ], { empty: 'Không có phiếu nào' });
  };
  const load = async () => { rows = await api('/admin/swaps'); paint(); };
  $('#seg').onclick = e => { const b = e.target.closest('[data-s]'); if (b) { status = b.dataset.s; paint(); } };
  $('#body').addEventListener('click', e => {
    const b = e.target.closest('[data-act]'); if (!b) return;
    run(b, async () => {
      const r = await api(`/admin/swaps/${b.dataset.id}/${b.dataset.act}`, { method: 'POST' });
      if (b.dataset.act !== 'approve') toast('Đã từ chối phiếu');
      else if (r.sheet_error) toast(`Đã duyệt — PIC & chấm công đã cập nhật, nhưng chưa ghi được sheet: ${r.sheet_error}`, 'error');
      else toast(r.sheet === 'updated' ? 'Đã duyệt — đã cập nhật PIC, chấm công và sheet Lịch trực' : 'Đã duyệt — đã cập nhật PIC và chấm công');
      load();
    });
  });
  load();
}

/* =========================================================
   6. Bảng lương
   ========================================================= */
/* Điều chỉnh lương: bảng công cả tháng của 1 nhân sự — chọn ngày nào làm ca nào, giờ vào / ra */
async function monthSheetDialog(ym, userId, after) {
  const s = await api('/admin/salary/user', { query: { ym, user_id: userId } }).catch(e => { toast(e.message, 'error'); return null; });
  if (!s) return;
  const shifts = App.meta.shifts, positions = App.meta.positions;
  const { start: mStart, end: mEnd } = monthBounds(ym);
  const days = []; for (let d = parseDate(mStart); ymd(d) <= mEnd; d = addDays(d, 1)) days.push(ymd(d));
  let list = [...s.rows, ...s.pending_rows].map(r => ({ id: r.id, date: r.date, shift_code: r.shift_code, start: r.start, end: r.end, position_id: r.position_id, note: r.note || '', approved: !!r.approved_at }));
  const rate = id => s.user.hourly_rate || (positions.find(p => p.id === id) || {}).hourly_rate || 0;  // mức lương riêng của nhân sự, không có thì theo vị trí
  const posShort = p => p.name.replace('Page Hotline Monitor', 'PHM').replace('Page Hotline', 'PH');
  const normT = v => { const m = String(v).trim().replace(/[h.]/, ':').match(/^(\d{1,2})(?::?(\d{2}))?$/); return m && +m[1] < 24 && +(m[2] || 0) < 60 ? `${m[1].padStart(2, '0')}:${m[2] || '00'}` : null; };

  /* chỉ 3 cột Sáng / Chiều / Tối; ca phụ (VD Tối gãy) hiện trong cột ca chính, giữ giờ riêng */
  const GROUP_NAMES = { sang: 'Sáng', chieu: 'Chiều', toi: 'Tối' };
  const cols = ['sang', 'chieu', 'toi'].map(g => ({ g, name: GROUP_NAMES[g],
    main: shifts.find(x => x.code === g) || shifts.find(x => shiftGroup(x.code) === g) })).filter(c => c.main);
  const colOf = code => { const g = shiftGroup(code); return cols.find(c => c.g === g) || cols[cols.length - 1]; };
  const cell = (d, col) => {
    const sh = col.main;
    const items = list.map((e, i) => ({ e, i })).filter(x => x.e.date === d && colOf(x.e.shift_code) === col);
    return items.map(({ e, i }) => `<div class="ms-entry ${e.approved ? '' : 'pending'}" data-i="${i}">
        <input class="input ms-t" data-k="start" value="${e.start}" maxlength="5" inputmode="numeric" placeholder="hh:mm"><span>–</span><input class="input ms-t" data-k="end" value="${e.end}" maxlength="5" inputmode="numeric" placeholder="hh:mm">
        <select class="input" data-k="position_id" title="Vị trí">${positions.map(p => `<option value="${p.id}" ${p.id === e.position_id ? 'selected' : ''}>${esc(posShort(p))}</option>`).join('')}</select>
        <button type="button" class="ms-x" data-rm="${i}" aria-label="Bỏ ca">×</button>
        ${e.note ? `<input class="input ms-note" data-k="note" value="${esc(e.note)}" title="Ghi chú">` : ''}</div>`).join('')
      + (items.length ? `<button type="button" class="ms-kem" data-add="${d}|${items.length ? items[items.length - 1].e.shift_code : sh.code}|kem" title="Thêm 1 ca trùng giờ (VD làm kèm CTV)">+ kèm</button>` : '')
      || `<button type="button" class="ms-add" data-add="${d}|${sh.code}">+</button>`;
  };
  const totals = () => {
    const ok = list.filter(e => e.date < todayStr() || e.approved);
    const h = ok.reduce((a, e) => a + Math.max(0, hoursOf(e)), 0);
    const money_ = ok.reduce((a, e) => a + Math.round(Math.max(0, hoursOf(e)) * rate(e.position_id)), 0);
    return { h: Math.round(h * 100) / 100, money: money_ };
  };
  const paintTotals = el => {
    const t = totals();
    const bonus = +$('#ms-b', el).value || 0, ded = +$('#ms-d', el).value || 0;
    $('#ms-sum', el).innerHTML = `<b>${t.h}</b> giờ · lương giờ <b>${money(t.money)}</b> − phạt QC ${money(s.qc_fine)} + thưởng ${money(bonus)} − khấu trừ ${money(ded)} = <b class="accent">${money(t.money - s.qc_fine + bonus - ded)}</b>`;
    days.forEach(d => { const c = $(`[data-dh="${d}"]`, el); if (c) c.textContent = list.filter(e => e.date === d).reduce((a, e) => a + Math.max(0, hoursOf(e)), 0) || ''; });
  };
  const table = () => `<table class="table ms"><thead><tr><th>Ngày</th>${cols.map(c => `<th>${c.name} <span class="muted small">${c.main.start}–${c.main.end}</span></th>`).join('')}<th class="right">Giờ</th></tr></thead><tbody>
    ${days.map(d => { const w = parseDate(d).getDay(); return `<tr class="${w === 0 || w === 6 ? 'we' : ''} ${d > todayStr() ? 'future' : ''}">
      <td class="nowrap"><b>${dowOf(d)}</b> ${fmtDM(d)}</td>${cols.map(c => `<td>${cell(d, c)}</td>`).join('')}<td class="right mono" data-dh="${d}"></td></tr>`; }).join('')}
    </tbody></table>`;

  modal({
    title: `Bảng công ${fmtYM(ym).toLowerCase()} · ${esc(s.user.username)} — ${esc(s.user.name)}`, wide: true,
    body: `<div class="ms-wrap">
      <p class="small muted" style="margin-bottom:10px">Bấm <b>+</b> để thêm ca, <b>×</b> để bỏ ca, gõ giờ vào / ra dạng 24h (VD <b>18:30</b>). Vị trí: PH = Page Hotline, PHM = Page Hotline Monitor. <b>+ kèm</b>: thêm 1 ca trùng giờ được chấm công (VD làm kèm CTV). Ca của ngày đã qua sẽ được lưu là <b>đã chấm công</b>; ngày chưa tới là lịch dự kiến. Viền vàng: ca chưa duyệt.</p>
      <div class="table-wrap" id="ms-tbl">${table()}</div>
      <div class="form-row" style="margin-top:14px">
        <div class="field"><label>Lương CTV gọi / thưởng (đ)</label><input type="number" class="input" id="ms-b" value="${s.bonus}" min="0" step="10000"></div>
        <div class="field"><label>Khấu trừ khác (đ)</label><input type="number" class="input" id="ms-d" value="${s.deduction}" min="0" step="10000"></div></div>
      <div class="field"><label>Ghi chú (CTV xem được)</label><input class="input" id="ms-n" value="${esc(s.note || '')}" placeholder="VD: Thưởng chuyên cần"></div>
      <div class="ms-sum" id="ms-sum"></div></div>`,
    footer: `<button class="btn" data-close>Huỷ</button><button class="btn btn-primary" id="ms-ok">Lưu bảng công</button>`,
    onOpen(el, close) {
      el.querySelector('.modal').classList.add('modal-xl');
      const repaint = () => { $('#ms-tbl', el).innerHTML = table(); paintTotals(el); };
      paintTotals(el);
      $('#ms-tbl', el).addEventListener('click', e => {
        const add = e.target.closest('[data-add]'), rm = e.target.closest('[data-rm]');
        if (add) {
          const [d, code, kem] = add.dataset.add.split('|'); const sh = shifts.find(x => x.code === code);
          const prev = list.find(x => x.shift_code === code);
          const same = kem && list.find(x => x.date === d && x.shift_code === code);
          list.push({ id: null, date: d, shift_code: code, start: same ? same.start : sh.start, end: same ? same.end : sh.end,
            position_id: (prev || {}).position_id || positions[0].id, note: kem ? 'Kèm CTV' : '', approved: false });
          repaint();
        }
        if (rm) { list.splice(+rm.dataset.rm, 1); repaint(); }
      });
      $('#ms-tbl', el).addEventListener('change', e => {
        const k = e.target.dataset.k, box = e.target.closest('[data-i]'); if (!k || !box) return;
        let val = e.target.value;
        if (k === 'start' || k === 'end') { const t = normT(val); e.target.classList.toggle('bad', !t); if (!t) return; e.target.value = val = t; }
        list[+box.dataset.i][k] = k === 'position_id' ? +val : val;
        paintTotals(el);
      });
      ['#ms-b', '#ms-d'].forEach(id => $(id, el).addEventListener('input', () => paintTotals(el)));
      $('#ms-ok', el).onclick = ev => run(ev.currentTarget, async () => {
        if ($('.ms-t.bad', el)) throw new Error('Có ô giờ chưa đúng dạng hh:mm');
        const bad = list.find(x => !x.start || !x.end || t2m(x.end) <= t2m(x.start));
        if (bad) throw new Error(`Giờ vào / ra ngày ${fmtDM(bad.date)} không hợp lệ`);
        const r = await api('/admin/salary/month-sheet', { method: 'PUT', body: { ym, user_id: userId,
          rows: list.map(x => ({ id: x.id, date: x.date, shift_code: x.shift_code, start: x.start, end: x.end, position_id: x.position_id, note: x.note })),
          bonus: +$('#ms-b', el).value || 0, deduction: +$('#ms-d', el).value || 0, note: $('#ms-n', el).value } });
        close(); toast(`Đã lưu bảng công${r.changed ? ` (${r.changed} ca thay đổi)` : ''}`); after && after();
      });
    },
  });
}

async function aSalary(v) {
  const now = new Date();
  let ym = ymOf(now), data = null, view = 'month', personId = null, users = [];
  v.innerHTML = pageHead('Bảng lương', 'Lương tính theo bảng chấm công đã duyệt (theo PIC): giờ × đơn giá − phạt lỗi QC + lương CTV gọi.') + `
    <div class="steps">
      <a href="#timesheet"><b>1</b> Duyệt chấm công từng ngày</a><span>→</span>
      <span><b>2</b> Kiểm tra bảng lương theo tháng / ngày / nhân sự, điều chỉnh nếu cần</span><span>→</span>
      <span><b>3</b> Bấm <b>Duyệt &amp; công bố</b> để CTV xem được lương</span>
    </div>
    <div class="filters"><select class="input" id="ym">${monthOptions(ym, -12, 2)}</select>
      <div class="seg" id="view"><button data-v="month" class="active">Tổng hợp tháng</button><button data-v="day">Theo ngày</button><button data-v="person">Theo nhân sự</button><button data-v="est">EST lương</button></div>
      <select class="input" id="person" hidden></select>
      <span style="flex:1"></span><span id="pub"></span>
      <button class="btn" id="exp">${icon('download')} Xuất Excel</button></div>
    <div id="body">${loading()}</div>`;

  const notice = pend => pend.length ? `<div class="notice">Còn ${pend.length} ngày chưa duyệt chấm công trong tháng — các ca này chưa được tính lương:
      ${pend.map(d => `<a href="#timesheet" data-day="${d}">${fmtDM(d)}</a>`).join(', ')}</div>` : '';
  const wireNotice = () => $$('#body [data-day]').forEach(a => a.addEventListener('click', () => { tsDay = a.dataset.day; }));
  /* ---- tổng hợp tháng ---- */
  const viewMonth = () => {
    const total = data.rows.reduce((a, r) => a + r.total, 0), hours = data.rows.reduce((a, r) => a + r.hours, 0);
    $('#body').innerHTML = `${notice(data.pending_days)}<div class="stats">
        <div class="stat"><div class="label">Số nhân sự có công</div><div class="value">${data.rows.length}</div></div>
        <div class="stat"><div class="label">Tổng giờ</div><div class="value">${Math.round(hours * 10) / 10}</div></div>
        <div class="stat"><div class="label">Tổng chi</div><div class="value accent">${money(total)}</div></div></div>
      <div class="card" id="tbl"></div>`;
    wireNotice();
    dataTable($('#tbl'), data.rows, [
      { label: 'Nhân sự', render: r => `<a href="javascript:void 0" data-person="${r.id}"><b>${esc(r.username)}</b></a><br><span class="small muted">${esc(r.name)}</span>` },
      { label: 'Ca / Giờ', cls: 'mono', render: r => `${r.shifts} / ${r.hours}` },
      { label: 'Lương giờ', cls: 'right mono', render: r => money(r.base) },
      { label: 'Phạt QC', cls: 'right mono', render: r => r.qc_fine ? `<span class="minus">−${money(r.qc_fine)}</span><br><span class="small muted">${r.qc_count} lỗi</span>` : '—' },
      { label: 'Lương CTV gọi', cls: 'right mono', render: r => r.bonus ? `<span class="plus">+${money(r.bonus)}</span>` : '—' },
      { label: 'Khấu trừ', cls: 'right mono', render: r => r.deduction ? `<span class="minus">−${money(r.deduction)}</span>` : '—' },
      { label: 'Thực nhận', cls: 'right mono', render: r => `<b>${money(r.total)}</b>` },
      { label: '', cls: 'right', render: r => `<div class="actions"><button class="btn btn-sm" data-adj="${r.id}">Điều chỉnh công</button><button class="btn btn-sm" data-person="${r.id}">Chi tiết</button></div>` },
    ], { pageSize: 50, empty: 'Chưa có ca nào được duyệt chấm công trong tháng này' });
    $('#tbl').onclick = e => {
      const p = e.target.closest('[data-person]'), b = e.target.closest('[data-adj]');
      if (p) { personId = +p.dataset.person; setView('person'); }
      if (b) monthSheetDialog(ym, +b.dataset.adj, load);
    };
  };

  /* ---- theo ngày ---- */
  let daily = [];
  const viewDay = async () => {
    daily = await api('/admin/salary/daily', { query: { ym } });
    const ok = daily.filter(d => !d.pending);
    $('#body').innerHTML = `${notice(data.pending_days)}<div class="stats">
        <div class="stat"><div class="label">Ngày đã duyệt</div><div class="value">${ok.length}<span class="muted" style="font-size:16px"> / ${daily.length}</span></div></div>
        <div class="stat"><div class="label">Tổng giờ đã duyệt</div><div class="value">${Math.round(daily.reduce((a, d) => a + d.hours, 0) * 10) / 10}</div></div>
        <div class="stat"><div class="label">Lương giờ đã duyệt</div><div class="value accent">${money(daily.reduce((a, d) => a + d.amount, 0))}</div></div></div>
      <div class="card" id="tbl"></div>`;
    wireNotice();
    dataTable($('#tbl'), daily, [
      { label: 'Ngày', render: d => `<span class="nowrap"><b>${dowOf(d.date)}</b> ${fmtDate(d.date)}</span>` },
      { label: 'Số ca', cls: 'mono', render: d => d.shifts },
      { label: 'Số người', cls: 'mono', render: d => d.people },
      { label: 'Giờ', cls: 'right mono', render: d => d.hours },
      { label: 'Lương giờ', cls: 'right mono', render: d => money(d.amount) },
      { label: 'Trạng thái', render: d => d.date > todayStr() ? '<span class="badge">Chưa đến ngày</span>' : d.pending ? `<span class="badge amber">Chờ duyệt ${d.pending} ca</span>` : '<span class="badge green">Đã duyệt</span>' },
      { label: '', cls: 'right', render: d => `<a class="btn btn-sm" href="#timesheet" data-day="${d.date}">Xem chấm công</a>` },
    ], { pageSize: 31, empty: 'Không có ca nào trong tháng này' });
    wireNotice();
  };

  /* ---- EST lương: dự kiến theo mọi ca đã chia trong tháng ---- */
  let est = null;
  const viewEst = async () => {
    est = await api('/admin/salary/estimate', { query: { ym } });
    const R = est.rows, sum = k => R.reduce((a, r) => a + r[k], 0), hrs = k => Math.round(sum(k) * 10) / 10;
    const sub = (m, h) => `<div class="small muted" style="margin-top:2px">${h} giờ · ${money(m)}</div>`;
    $('#body').innerHTML = `<p class="small muted" style="margin:0 0 12px">Tính trên <b>tất cả ca đã chia</b> trong ${fmtYM(ym).toLowerCase()} (kể cả ca chưa duyệt chấm công và ca chưa tới ngày) × đơn giá giờ, rồi trừ phạt QC / khấu trừ và cộng thưởng đã ghi. Chỉ là số dự kiến — lương thật vẫn theo tab <b>Tổng hợp tháng</b> sau khi duyệt chấm công.</p>
      ${est.missing_days.length ? `<div class="notice">Đã chia ca ${est.days - est.missing_days.length} / ${est.days} ngày. Chưa có ca nào: ${est.missing_days.map(d => `<b>${dowOf(d)} ${fmtDM(d)}</b>`).join(', ')} — EST chưa tính các ngày này (chia ca xong sẽ tự cộng vào).</div>`
        : `<p class="small" style="margin:0 0 12px">✓ Đã chia ca đủ ${est.days} / ${est.days} ngày của tháng.</p>`}
      <div class="stats">
        <div class="stat"><div class="label">EST tổng chi</div><div class="value accent">${money(sum('total'))}</div><div class="small muted">${R.length} người · ${hrs('hours')} giờ</div></div>
        <div class="stat"><div class="label">Đã duyệt chấm công</div><div class="value">${money(sum('done'))}</div>${sub(sum('done'), hrs('done_h'))}</div>
        <div class="stat"><div class="label">Đã qua, chờ duyệt</div><div class="value">${money(sum('wait'))}</div>${sub(sum('wait'), hrs('wait_h'))}</div>
        <div class="stat"><div class="label">Chưa tới ngày</div><div class="value">${money(sum('next'))}</div>${sub(sum('next'), hrs('next_h'))}</div></div>
      <div class="card" id="tbl"></div>`;
    const part = (m, h) => m || h ? `<span class="nowrap">${money(m)}</span><br><span class="small muted">${h} giờ</span>` : '<span class="muted">—</span>';
    dataTable($('#tbl'), R, [
      { label: 'Nhân sự', render: r => `<a href="javascript:void 0" data-person="${r.id}"><b>${esc(r.username)}</b></a><br><span class="small muted">${esc(r.name)}</span>` },
      { label: 'Ca / Giờ', cls: 'mono', render: r => `<span class="nowrap">${r.shifts} / ${r.hours}</span>` },
      { label: 'Đã duyệt', cls: 'right mono', render: r => part(r.done, r.done_h) },
      { label: 'Chờ duyệt', cls: 'right mono', render: r => part(r.wait, r.wait_h) },
      { label: 'Chưa tới ngày', cls: 'right mono', render: r => part(r.next, r.next_h) },
      { label: 'Lương giờ dự kiến', cls: 'right mono', render: r => `<span class="nowrap">${money(r.amount)}</span>` },
      { label: 'Thưởng / phạt', cls: 'right mono', render: r => [r.bonus ? `<span class="plus">+${money(r.bonus)}</span>` : '',
          r.qc_fine ? `<span class="minus">−${money(r.qc_fine)}</span> <span class="small muted">QC</span>` : '',
          r.deduction ? `<span class="minus">−${money(r.deduction)}</span> <span class="small muted">KT</span>` : ''].filter(Boolean).join('<br>') || '—' },
      { label: 'EST thực nhận', cls: 'right mono', render: r => `<b class="nowrap">${money(r.total)}</b>` },
      { label: '', cls: 'right', render: r => `<div class="actions"><button class="btn btn-sm" data-adj="${r.id}">Xem / sửa công</button></div>` },
    ], { pageSize: 50, empty: 'Tháng này chưa chia ca nào' });
    $('#tbl').onclick = e => {
      const p = e.target.closest('[data-person]'), b = e.target.closest('[data-adj]');
      if (p) { personId = +p.dataset.person; setView('person'); }
      if (b) monthSheetDialog(ym, +b.dataset.adj, load);
    };
  };

  /* ---- theo nhân sự ---- */
  let person = null;
  const viewPerson = async () => {
    const withData = new Set(data.rows.map(r => r.id));
    const opts = [...users].sort((a, b) => (withData.has(b.id) - withData.has(a.id)) || a.username.localeCompare(b.username));
    if (!personId) personId = (data.rows[0] || opts[0] || {}).id;
    $('#person').innerHTML = opts.filter(u => u.active || withData.has(u.id)).map(u => `<option value="${u.id}" ${u.id === personId ? 'selected' : ''}>${esc(u.username)} · ${esc(u.name)}${withData.has(u.id) ? '' : ' (chưa có công)'}</option>`).join('');
    if (!personId) { $('#body').innerHTML = emptyState('Chưa có nhân sự'); return; }
    person = await api('/admin/salary/user', { query: { ym, user_id: personId } });
    const s = person;
    const all = [...s.rows.map(r => ({ ...r, ok: true })), ...s.pending_rows.map(r => ({ ...r, ok: false }))].sort((a, b) => a.date.localeCompare(b.date) || a.start.localeCompare(b.start));
    $('#body').innerHTML = `
      <div class="card card-pad salary-hero"><div><div class="muted">${esc(s.user.username)} · ${esc(s.user.name)} — thực nhận ${fmtYM(ym).toLowerCase()}</div><div class="amount">${money(s.total)}</div>
        <div class="muted">${s.shifts} ca · ${s.hours} giờ đã duyệt${s.pending_rows.length ? ` · <span class="accent">${s.pending_rows.length} ca chờ duyệt chưa tính</span>` : ''}</div></div>
        <div><button class="btn btn-primary" id="p-adj">Điều chỉnh bảng công</button></div></div>
      <div class="card card-pad" style="margin-top:16px"><table class="lines">
        <tr><td>Lương theo giờ (${s.hours} giờ)</td><td>${money(s.base)}</td></tr>
        <tr><td>Lương CTV gọi / thưởng</td><td class="plus">+ ${money(s.bonus)}</td></tr>
        <tr><td>Phạt lỗi QC (${s.qc_count} lỗi)</td><td class="minus">− ${money(s.qc_fine)}</td></tr>
        <tr><td>Khấu trừ khác</td><td class="minus">− ${money(s.deduction)}</td></tr>
        <tr class="total"><td>Thực nhận</td><td>${money(s.total)}</td></tr></table>
        ${s.note ? `<p class="muted small" style="margin-top:8px">Ghi chú: ${esc(s.note)}</p>` : ''}</div>
      <div class="card"><div class="card-head"><h2>Chi tiết theo ngày</h2></div><div id="days"></div></div>
      ${s.qc.length ? `<div class="card"><div class="card-head"><h2>Lỗi QC trong kỳ</h2><span class="badge red">− ${money(s.qc_fine)}</span></div><div id="qc"></div></div>` : ''}`;
    dataTable($('#days'), all, [
      { label: 'Ngày', render: r => `<span class="nowrap"><b>${dowOf(r.date)}</b> ${fmtDate(r.date)}</span>` },
      { label: 'Ca', render: r => `${esc((r.shift_name || '').replace(/^ca\s+/i, ''))} <span class="muted small">${r.start}–${r.end}</span>` },
      { label: 'Vị trí', render: r => esc(r.position || '') },
      { label: 'Giờ', cls: 'right mono', render: r => hoursOf(r) },
      { label: 'Thành tiền', cls: 'right mono', render: r => r.ok ? money(Math.round(hoursOf(r) * (r.hourly_rate || 0))) : '<span class="muted">—</span>' },
      { label: 'Trạng thái', render: r => r.ok ? '<span class="badge green">Đã duyệt</span>' : `<a href="#timesheet" data-day="${r.date}" class="badge amber">Chờ duyệt</a>` },
      { label: 'Điều chỉnh / ghi chú', render: r => `${planDiff(r) ? `<div class="small">${planDiff(r)}</div>` : ''}${r.note ? `<div class="small muted">${esc(r.note)}</div>` : ''}` },
    ], { pageSize: 62, empty: 'Không có ca nào trong tháng này' });
    if (s.qc.length) dataTable($('#qc'), s.qc, [
      { label: 'Ngày', render: r => `<span class="nowrap">${fmtDate(r.date)}</span>` },
      { label: 'Lỗi', render: r => `<div style="white-space:pre-wrap;max-width:520px">${esc(r.error || '—')}</div>` },
      { label: 'Hình thức', render: r => esc(r.penalty || '') },
      { label: 'Tiền phạt', cls: 'right mono', render: r => r.amount ? `<span class="minus">−${money(r.amount)}</span>` : '<span class="muted">Nhắc nhở</span>' },
    ], { pageSize: 20 });
    wireNotice();
    $('#p-adj').onclick = () => monthSheetDialog(ym, personId, () => { load(); });
  };

  const setView = nv => {
    view = nv;
    $$('#view button').forEach(b => b.classList.toggle('active', b.dataset.v === view));
    $('#person').hidden = view !== 'person';
    $('#body').innerHTML = loading();
    (view === 'month' ? viewMonth : view === 'day' ? viewDay : view === 'est' ? viewEst : viewPerson)();
  };
  const load = async () => {
    [data, users] = await Promise.all([api('/admin/salary', { query: { ym } }), users.length ? users : api('/admin/users')]);
    $('#pub').innerHTML = `<span class="badge ${data.published ? 'green' : ''}" style="margin-right:8px">${data.published ? 'Đã duyệt & công bố cho CTV' : 'Chưa công bố'}</span>
      <button class="btn ${data.published ? '' : 'btn-primary'}" id="pb">${data.published ? 'Thu hồi' : 'Duyệt & công bố'}</button>`;
    $('#pb').onclick = async e => {
      if (!data.published) {
        const warn = data.pending_days.length ? ` Lưu ý: còn ${data.pending_days.length} ngày chưa duyệt chấm công.` : '';
        if (!(await confirmDialog('Duyệt & công bố bảng lương?', `CTV sẽ xem được lương ${fmtYM(ym).toLowerCase()} và nhận thông báo.${warn}`, 'Công bố'))) return;
      }
      run(e.currentTarget, async () => { await api('/admin/salary/publish', { method: 'POST', body: { ym, published: !data.published } }); toast('Đã cập nhật'); load(); });
    };
    setView(view);
  };
  $('#ym').onchange = e => { ym = e.target.value; load(); };
  $('#view').onclick = e => { const b = e.target.closest('[data-v]'); if (b) setView(b.dataset.v); };
  $('#person').onchange = e => { personId = +e.target.value; viewPerson(); };
  $('#exp').onclick = () => {
    /* Tổng hợp tháng / EST: đúng 5 cột Mã CTV | Họ tên | CCCD | Tổng giờ | Thù lao (thù lao = thực nhận) */
    const info = id => users.find(x => x.id === id) || {};
    const pay = (file, list) => downloadCSV(file, ['Mã CTV', 'Họ tên', 'CCCD', 'Tổng giờ', 'Thù lao'],
      list.map(r => { const x = info(r.id); return [x.code || '', r.name, x.cccd ? `="${x.cccd}"` : '', r.hours, r.total]; }));
    if (view === 'est' && est) return pay(`est-luong-${ym}.csv`, est.rows);
    if (view === 'day') return downloadCSV(`luong-theo-ngay-${ym}.csv`, ['Ngày', 'Thứ', 'Số ca', 'Số người', 'Giờ đã duyệt', 'Lương giờ', 'Ca chờ duyệt'],
      daily.map(d => [fmtDate(d.date), dowOf(d.date), d.shifts, d.people, d.hours, d.amount, d.pending]));
    if (view === 'person' && person) return downloadCSV(`luong-${person.user.username}-${ym}.csv`, ['Ngày', 'Ca', 'Giờ', 'Vị trí', 'Số giờ', 'Thành tiền', 'Trạng thái', 'Ghi chú'],
      [...person.rows.map(r => [fmtDate(r.date), r.shift_name, `${r.start}-${r.end}`, r.position, hoursOf(r), Math.round(hoursOf(r) * (r.hourly_rate || 0)), 'Đã duyệt', r.note]),
       ...person.pending_rows.map(r => [fmtDate(r.date), r.shift_name, `${r.start}-${r.end}`, r.position, hoursOf(r), 0, 'Chờ duyệt', r.note])]);
    data && pay(`bang-luong-${ym}.csv`, data.rows);
  };
  load();
}

/* =========================================================
   Lỗi QC
   ========================================================= */
const QC_PRESETS = [
  { label: 'Nhắc nhở', amount: 0, category: 'Nhắc nhở' },
  { label: '1/2h làm', amount: 12500, category: 'Lỗi nhân sự' },
  { label: '1h làm', amount: 25000, category: 'Lỗi nhân sự' },
  { label: '50% buổi học', amount: '', category: 'GVVN' },
];
const QC_CATEGORIES = ['Lỗi nhân sự', 'GVVN', 'GVNN', 'Nhắc nhở'];

async function aQC(v) {
  const now = new Date();
  let ym = ymOf(now), rows = [], users = [];
  v.innerHTML = pageHead('Lỗi QC', 'Ghi lỗi và tiền phạt của CTV. Tiền phạt được trừ vào lương của tháng tính lương tương ứng.',
    `<button class="btn" id="exp">${icon('download')} Xuất Excel</button><button class="btn btn-primary" id="add">${icon('plus')} Ghi lỗi</button>`) + `
    <div class="filters"><select class="input" id="ym">${monthOptions(ym, -12, 1)}</select>
      <div class="search">${icon('search')}<input class="input" id="q" placeholder="Tìm CTV, lỗi, ticket"></div></div>
    <div class="stats" id="stats"></div><div class="card" id="body">${loading()}</div>`;
  const paint = () => {
    const q = $('#q').value.trim().toLowerCase();
    const list = rows.filter(r => !q || `${r.username} ${r.name} ${r.error} ${r.note} ${r.ticket}`.toLowerCase().includes(q));
    const total = rows.reduce((a, r) => a + r.amount, 0);
    $('#stats').innerHTML = `<div class="stat"><div class="label">Số lỗi</div><div class="value">${rows.length}</div></div>
      <div class="stat"><div class="label">CTV bị ghi lỗi</div><div class="value">${new Set(rows.map(r => r.user_id)).size}</div></div>
      <div class="stat"><div class="label">Tổng tiền phạt</div><div class="value accent">${money(total)}</div></div>`;
    dataTable($('#body'), list, [
      { label: 'Ngày', render: r => `<span class="nowrap">${fmtDate(r.date)}</span>` },
      { label: 'CTV', render: r => `<b>${esc(r.username)}</b><br><span class="small muted">${esc(r.name)}</span>` },
      { label: 'Lỗi', render: r => `<div style="white-space:pre-wrap;max-width:460px">${esc(r.error || '—')}</div>${r.note ? `<div class="small muted" style="white-space:pre-wrap;margin-top:4px">${esc(r.note)}</div>` : ''}` },
      { label: 'Hình thức', render: r => `${esc(r.penalty || '')}${r.category ? `<br><span class="badge">${esc(r.category)}</span>` : ''}` },
      { label: 'Ticket', render: r => /^https?:/.test(r.ticket || '') ? `<a href="${esc(r.ticket)}" target="_blank" rel="noopener">Mở</a>` : esc(r.ticket || '—') },
      { label: 'Tiền phạt', cls: 'right mono', render: r => r.amount ? `<span class="minus">−${money(r.amount)}</span>` : '<span class="muted">0</span>' },
      { label: '', cls: 'right', render: r => `<div class="actions"><button class="btn btn-sm btn-danger" data-del="${r.id}">Xoá</button><button class="btn btn-sm" data-edit="${r.id}">Sửa</button></div>` },
    ], { pageSize: 30, empty: 'Chưa có lỗi nào trong tháng này' });
  };
  const load = async () => {
    [rows, users] = await Promise.all([api('/admin/qc', { query: { ym } }), users.length ? users : api('/admin/users')]);
    paint();
  };
  const form = r => modal({
    title: r ? 'Sửa lỗi QC' : 'Ghi lỗi QC', wide: true,
    body: `<form id="qf">
      <div class="form-row"><div class="field"><label>CTV</label><select class="input" name="user_id" required><option value="">— Chọn CTV —</option>
          ${users.filter(u => u.role === 'ctv').sort((a, b) => (b.active ? 1 : 0) - (a.active ? 1 : 0)).map(u => `<option value="${u.id}" ${r && r.user_id === u.id ? 'selected' : ''}>${esc(u.username)} · ${esc(u.name)}${u.active ? '' : ' (đã nghỉ)'}</option>`).join('')}</select></div>
        <div class="form-row"><div class="field"><label>Ngày ghi lỗi</label><input class="input" type="date" name="date" value="${(r && r.date) || todayStr()}" required></div>
          <div class="field"><label>Tính vào lương tháng</label><input class="input" type="month" name="ym" value="${(r && r.ym) || ym}" required></div></div></div>
      <div class="field"><label>Lỗi</label><textarea class="input" name="error" rows="3" required>${esc((r && r.error) || '')}</textarea></div>
      <div class="field"><label>Ghi chú</label><textarea class="input" name="note" rows="2">${esc((r && r.note) || '')}</textarea></div>
      <div class="field"><label>Link ticket</label><input class="input" name="ticket" value="${esc((r && r.ticket) || '')}" placeholder="https://crm…"></div>
      <div class="field"><label>Hình thức phạt (chọn nhanh)</label><div class="seg" id="qf-presets">${QC_PRESETS.map((p, i) => `<button type="button" data-p="${i}">${p.label}</button>`).join('')}</div></div>
      <div class="form-row"><div class="field"><label>Mô tả hình thức</label><input class="input" name="penalty" value="${esc((r && r.penalty) || '')}" placeholder="VD: 1/2h làm"></div>
        <div class="form-row"><div class="field"><label>Số tiền phạt (đ)</label><input class="input" type="number" name="amount" min="0" step="500" value="${r ? r.amount : 0}"></div>
          <div class="field"><label>Phân loại</label><select class="input" name="category"><option value="">—</option>${QC_CATEGORIES.map(c => `<option ${r && r.category === c ? 'selected' : ''}>${c}</option>`).join('')}</select></div></div></div>
      <button class="btn btn-primary btn-block">Lưu</button></form>`,
    onOpen(el, close) {
      const f = $('#qf', el);
      $('#qf-presets', el).onclick = e => {
        const b = e.target.closest('[data-p]'); if (!b) return;
        const p = QC_PRESETS[+b.dataset.p];
        f.penalty.value = p.label;
        if (p.amount !== '') f.amount.value = p.amount; else f.amount.focus();
        f.category.value = p.category;
        $$('#qf-presets button', el).forEach(x => x.classList.toggle('active', x === b));
      };
      searchSelect(f.user_id, { placeholder: 'Gõ tên / username CTV để tìm…' });
      f.onsubmit = e => {
        e.preventDefault();
        run(e.submitter, async () => {
          if (!f.user_id.value) throw new Error('Vui lòng chọn CTV trong danh sách gợi ý');
          await api('/admin/qc', { method: 'POST', body: { id: r && r.id, user_id: +f.user_id.value, date: f.date.value, ym: f.ym.value,
            error: f.error.value, note: f.note.value, ticket: f.ticket.value, penalty: f.penalty.value, amount: +f.amount.value, category: f.category.value } });
          close(); toast('Đã lưu lỗi QC'); load();
        });
      };
    },
  });
  $('#ym').onchange = e => { ym = e.target.value; load(); };
  $('#q').oninput = paint;
  $('#add').onclick = () => form(null);
  $('#body').addEventListener('click', async e => {
    const ed = e.target.closest('[data-edit]'), del = e.target.closest('[data-del]');
    if (ed) form(rows.find(r => r.id === +ed.dataset.edit));
    if (del) {
      if (!(await confirmDialog('Xoá lỗi QC này?', 'Tiền phạt sẽ không còn bị trừ vào lương.', 'Xoá', true))) return;
      run(del, async () => { await api(`/admin/qc/${del.dataset.del}`, { method: 'DELETE' }); toast('Đã xoá'); load(); });
    }
  });
  $('#exp').onclick = () => downloadCSV(`loi-qc-${ym}.csv`, ['Tháng', 'Ngày ghi phạt', 'CTV', 'Ticket', 'Lỗi', 'Note', 'Phạt', 'Tính tiền', 'Phân loại'],
    rows.map(r => [r.ym, fmtDate(r.date), r.username, r.ticket, r.error, r.note, r.penalty, r.amount, r.category]));
  load();
}

/* =========================================================
   7. Nhân sự
   ========================================================= */
async function aUsers(v) {
  let rows = [], tab = 'active';   // active = đang làm việc · left = đã nghỉ việc (tài khoản đã khoá)
  v.innerHTML = pageHead('Nhân sự', 'Quản lý tài khoản CTV và quản trị viên.', `<button class="btn btn-primary" id="add">${icon('plus')} Thêm tài khoản</button>`) + `
    <div class="filters"><div class="seg" id="tab"></div><div class="search">${icon('search')}<input class="input" id="q" placeholder="Tìm theo tên, username, CCCD"></div>
      <select class="input" id="role"><option value="">Tất cả vai trò</option><option value="ctv">CTV</option><option value="admin">Quản trị</option></select></div>
    <div class="card" id="body">${loading()}</div>`;
  const paint = () => {
    const q = foldVi($('#q').value.trim()), role = $('#role').value;
    const n = { active: rows.filter(u => u.active).length, left: rows.filter(u => !u.active).length };
    $('#tab').innerHTML = [['active', 'Nhân sự'], ['left', 'Nhân sự đã nghỉ việc']].map(([k, l]) => `<button class="${tab === k ? 'active' : ''}" data-t="${k}">${l} <span class="n">${n[k]}</span></button>`).join('');
    dataTable($('#body'), rows.filter(u => (tab === 'left' ? !u.active : !!u.active) && (!role || u.role === role) && (!q || foldVi(`${u.username} ${u.name} ${u.phone} ${u.code} ${u.email} ${u.cccd || ''}`).includes(q))), [
      { label: 'Tài khoản', render: u => `<div style="display:flex;gap:10px;align-items:center"><div class="avatar">${initials(u.name)}</div><div><b>${esc(u.username)}</b>${u.role === 'admin' ? ' <span class="badge blue">Quản trị</span>' : ''}${u.active ? '' : ' <span class="badge red">Đã nghỉ</span>'}<br><span class="small muted">${esc(u.name)}</span></div></div>` },
      { label: 'Mã CTV · Team', cls: 'nowrap', render: u => `${esc(u.code || '—')}<br><span class="small muted">${esc(u.team || '')}</span>` },
      { label: 'CCCD', cls: 'mono nowrap', render: u => u.cccd ? esc(u.cccd) : '<span class="muted">—</span>' },
      { label: 'Email', render: u => `<span class="small">${esc(u.email || '—')}</span>` },
      { label: 'Mức lương', cls: 'right nowrap', render: u => u.hourly_rate ? `<b>${money(u.hourly_rate)}</b><span class="small muted"> /giờ</span>` : `<span class="small muted" title="Chưa đặt mức lương riêng — tính theo đơn giá vị trí">Theo vị trí</span>` },
      { label: '', cls: 'right nowrap', render: u => `<div class="actions"><button class="btn btn-sm" data-edit="${u.id}">Sửa</button><button class="btn btn-sm" data-reset="${u.id}" title="Đặt lại mật khẩu">Đặt lại MK</button></div>` },
    ], { pageSize: 30, empty: tab === 'left' ? 'Chưa có nhân sự nào nghỉ việc' : 'Không có nhân sự nào' });
  };
  const load = async () => { rows = await api('/admin/users'); paint(); };
  const form = u => modal({
    title: u ? `Sửa · ${esc(u.username)}` : 'Thêm tài khoản',
    body: `<form id="uf">
      <div class="form-row"><div class="field"><label>Tên đăng nhập</label><input class="input" name="username" value="${esc(u?.username || '')}" ${u ? 'disabled' : 'required'}></div>
        <div class="field"><label>Họ tên</label><input class="input" name="name" value="${esc(u?.name || '')}" required></div></div>
      <div class="form-row"><div class="field"><label>Vai trò</label><select class="input" name="role"><option value="ctv">CTV</option><option value="admin" ${u?.role === 'admin' ? 'selected' : ''}>Quản trị</option></select></div>
        <div class="field"><label>Team</label><select class="input" name="team_id"><option value="">—</option>${App.meta.teams.map(t => `<option value="${t.id}" ${u?.team_id === t.id ? 'selected' : ''}>${esc(t.name)}</option>`).join('')}</select></div></div>
      <div class="form-row"><div class="field"><label>Mã CTV</label><input class="input" name="code" value="${esc(u?.code || '')}" placeholder="VD: CTV.4161"></div>
        <div class="field"><label>Email</label><input class="input" name="email" type="email" value="${esc(u?.email || '')}"></div></div>
      <div class="field"><label>Mức lương (đ / giờ)</label><input class="input" name="hourly_rate" type="number" min="0" step="1000" value="${u?.hourly_rate || ''}" placeholder="Để trống = theo đơn giá vị trí (Danh mục)">
        <span class="hint">Bảng công = Mức lương × số giờ làm đã duyệt.</span></div>
      <div class="form-row"><div class="field"><label>Số CCCD</label><input class="input" name="cccd" value="${esc(u?.cccd || '')}" inputmode="numeric" maxlength="14" placeholder="12 chữ số"></div>
        <div class="field"><label>Điện thoại</label><input class="input" name="phone" value="${esc(u?.phone || '')}"></div></div>
      <div class="form-row">
        ${u ? `<div class="field"><label>Trạng thái</label><select class="input" name="active"><option value="1">Hoạt động</option><option value="0" ${u.active ? '' : 'selected'}>Đã nghỉ việc (khoá)</option></select></div>`
          : `<div class="field"><label>Mật khẩu ban đầu</label><input class="input" name="password" placeholder="Mặc định: 123456"></div>`}</div>
      <button class="btn btn-primary btn-block">Lưu</button></form>`,
    onOpen(el, close) {
      $('#uf', el).onsubmit = e => {
        e.preventDefault(); const f = e.target;
        run(e.submitter, async () => {
          await api('/admin/users', { method: 'POST', body: {
            id: u?.id, username: u ? u.username : f.username.value, name: f.name.value, role: f.role.value,
            team_id: f.team_id.value ? +f.team_id.value : null, phone: f.phone.value, code: f.code.value, email: f.email.value,
            active: u ? f.active.value === '1' : true, password: f.password?.value, hourly_rate: +f.hourly_rate.value || 0, cccd: f.cccd.value,
          } });
          close(); toast('Đã lưu tài khoản'); load();
        });
      };
    },
  });
  $('#add').onclick = () => form(null);
  $('#q').oninput = paint; $('#role').onchange = paint;
  $('#tab').onclick = e => { const b = e.target.closest('[data-t]'); if (b) { tab = b.dataset.t; paint(); } };
  $('#body').addEventListener('click', e => {
    const ed = e.target.closest('[data-edit]'), rs = e.target.closest('[data-reset]');
    if (ed) form(rows.find(u => u.id === +ed.dataset.edit));
    if (rs) {
      const u = rows.find(x => x.id === +rs.dataset.reset);
      modal({
        title: `Đặt lại mật khẩu · ${esc(u.username)}`,
        body: `<div class="field"><label>Mật khẩu mới</label><input class="input" id="np" placeholder="Mặc định: 123456"><span class="hint">CTV sẽ bị đăng xuất khỏi mọi thiết bị.</span></div>`,
        footer: `<button class="btn" data-close>Huỷ</button><button class="btn btn-primary" id="np-ok">Đặt lại</button>`,
        onOpen(el, close) {
          $('#np-ok', el).onclick = ev => run(ev.currentTarget, async () => {
            const r = await api(`/admin/users/${u.id}/reset-password`, { method: 'POST', body: { password: $('#np', el).value } });
            close(); toast(`Đã đặt lại mật khẩu: ${r.password}`, 'info');
          });
        },
      });
    }
  });
  load();
}

/* =========================================================
   8. Danh mục (team, vị trí, khung ca, môn học)
   ========================================================= */
const CATALOGS = {
  teams: { label: 'Team', key: 'id', fields: [{ k: 'name', label: 'Tên team' }] },
  positions: { label: 'Vị trí', key: 'id', fields: [
    { k: 'name', label: 'Tên vị trí' },
    { k: 'team_id', label: 'Team', type: 'team' },
    { k: 'hourly_rate', label: 'Đơn giá / giờ (đ)', type: 'number', fmt: money }] },
  shifts: { label: 'Khung ca', key: 'code', fields: [
    { k: 'code', label: 'Mã (không dấu)' }, { k: 'name', label: 'Tên ca' },
    { k: 'start', label: 'Giờ bắt đầu', type: 'time' }, { k: 'end', label: 'Giờ kết thúc', type: 'time' },
    { k: 'reg_min', label: 'Đăng ký rảnh từ', type: 'time' }, { k: 'reg_max', label: 'Đăng ký rảnh đến', type: 'time' },
    { k: 'sort', label: 'Thứ tự', type: 'number' },
    { k: 'need_min', label: 'Cần tối thiểu (CTV)', type: 'number' }, { k: 'need_max', label: 'Tối đa (CTV)', type: 'number' }] },
};

async function aCatalog(v) {
  let kind = 'positions', rows = [];
  v.innerHTML = pageHead('Danh mục', 'Cấu hình team, vị trí & đơn giá và khung ca.', `<button class="btn btn-primary" id="add">${icon('plus')} Thêm</button>`) + `
    <div class="filters"><div class="seg" id="seg">${Object.entries(CATALOGS).map(([k, c]) => `<button data-k="${k}">${c.label}</button>`).join('')}</div></div>
    <div class="card" id="body">${loading()}</div>`;
  const teamName = id => (App.meta.teams.find(t => t.id === id) || {}).name || '—';
  const load = async () => {
    $$('#seg button').forEach(b => b.classList.toggle('active', b.dataset.k === kind));
    const c = CATALOGS[kind];
    rows = await api(`/admin/catalog/${kind}`);
    dataTable($('#body'), rows, [
      ...c.fields.map(f => ({ label: f.label, render: r => f.type === 'team' ? esc(teamName(r[f.k])) : f.fmt ? f.fmt(r[f.k]) : esc(r[f.k] ?? '—') })),
      { label: '', cls: 'right', render: r => `<div class="actions"><button class="btn btn-sm btn-danger" data-del="${esc(r[c.key])}">Xoá</button><button class="btn btn-sm" data-edit="${esc(r[c.key])}">Sửa</button></div>` },
    ], { pageSize: 50 });
  };
  const reloadMeta = async () => { App.meta = await api('/meta'); };
  const form = r => {
    const c = CATALOGS[kind];
    modal({
      title: `${r ? 'Sửa' : 'Thêm'} ${c.label.toLowerCase()}`,
      body: `<form id="cf">${c.fields.map(f => `<div class="field"><label>${f.label}</label>${f.type === 'team'
        ? `<select class="input" name="${f.k}">${App.meta.teams.map(t => `<option value="${t.id}" ${r?.[f.k] === t.id ? 'selected' : ''}>${esc(t.name)}</option>`).join('')}</select>`
        : `<input class="input" name="${f.k}" type="${f.type || 'text'}" value="${esc(r?.[f.k] ?? '')}" ${f.optional ? '' : 'required'}>`}</div>`).join('')}
        <button class="btn btn-primary btn-block">Lưu</button></form>`,
      onOpen(el, close) {
        $('#cf', el).onsubmit = e => {
          e.preventDefault();
          const body = { _key: r ? r[c.key] : null };
          c.fields.forEach(f => { const val = e.target[f.k].value; body[f.k] = ['number', 'team'].includes(f.type) ? +val : val; });
          run(e.submitter, async () => { await api(`/admin/catalog/${kind}`, { method: 'POST', body }); close(); toast('Đã lưu'); await reloadMeta(); load(); });
        };
      },
    });
  };
  $('#seg').onclick = e => { const b = e.target.closest('[data-k]'); if (b) { kind = b.dataset.k; load(); } };
  $('#add').onclick = () => form(null);
  $('#body').addEventListener('click', async e => {
    const c = CATALOGS[kind];
    const ed = e.target.closest('[data-edit]'), del = e.target.closest('[data-del]');
    if (ed) form(rows.find(r => String(r[c.key]) === ed.dataset.edit));
    if (del) {
      if (!(await confirmDialog('Xoá mục này?', 'Không thể xoá nếu mục đang được sử dụng.', 'Xoá', true))) return;
      run(del, async () => { await api(`/admin/catalog/${kind}/${encodeURIComponent(del.dataset.del)}`, { method: 'DELETE' }); toast('Đã xoá'); await reloadMeta(); load(); });
    }
  });
  load();
}

/* =========================================================
   Cẩm nang (cấu hình nguồn Google Sheet)
   ========================================================= */
async function aHandbook(v) {
  const desc = 'Trang Cẩm nang của CTV đọc trực tiếp từ Google Sheet và tự cập nhật mỗi 5 phút.';
  v.innerHTML = loading();
  const d = await api('/admin/handbook');
  v.innerHTML = docHead(desc, `<a class="btn btn-sm" href="/ctv#handbook" target="_blank" rel="noopener">${icon('external')} Xem như CTV</a>`) + `
    <form class="card card-pad" id="hb-form">
      <div class="field"><label for="hb-sheet">Link Google Sheet</label>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><input class="input" style="flex:1;min-width:260px" id="hb-sheet" value="${esc(d.sheet_url)}">
          <a class="btn" href="${esc(d.sheet_url)}" target="_blank" rel="noopener">Mở sheet</a></div>
        <span class="hint">Sheet chia sẻ “Bất kỳ ai có đường liên kết”, hoặc cài Apps Script bên dưới (cho sheet chỉ chia sẻ trong công ty). Đổi link rồi bấm Lưu để tải danh sách tab mới.</span></div>
      ${d.error ? `<p style="margin-bottom:14px"><span class="badge red">${esc(d.error)}</span></p>` : ''}
      <details style="margin-bottom:16px" ${d.push.data_at ? '' : 'open'}><summary style="cursor:pointer"><b>Sheet chỉ chia sẻ trong công ty? Cài Apps Script để tự gửi sang portal</b> ${d.push.data_at ? '<span class="badge green">Đã cài</span>' : '<span class="muted small">(cài 1 lần)</span>'}</summary>
        ${d.push.data_at ? `<p class="small" style="margin:8px 0">Dữ liệu sheet nhận lúc <b>${hm(d.push.data_at)} ${fmtDate(d.push.data_at.slice(0, 10))}</b>${d.push.seen_at ? ` · Apps Script gửi kiểm tra gần nhất lúc ${hm(d.push.seen_at)} ${fmtDate(d.push.seen_at.slice(0, 10))}` : ''}. Sửa sheet là portal cập nhật gần như ngay (chậm nhất ~1 phút). Bản cài trước ngày 25/11 kiểm tra 10 phút/lần — sao chép lại code, dán đè, chạy lại setup để nhanh hơn.</p>` : ''}
        ${d.push.other_sheet ? '<p style="margin:8px 0"><span class="badge amber">Apps Script đang gửi một sheet khác link ở trên — sao chép lại code bên dưới, dán đè rồi chạy lại setup</span></p>' : ''}
        <ol class="small" style="margin:8px 0 8px 18px;line-height:1.7">
          <li>Đăng nhập Google bằng tài khoản <b>công ty xem được sheet Cẩm nang</b> → mở <a href="https://script.google.com/home/projects/create" target="_blank" rel="noopener">script.google.com → Dự án mới</a>.</li>
          <li>Xoá code mẫu, dán đoạn code bên dưới → bấm 💾 <b>Lưu</b>.</li>
          <li>Trên thanh công cụ, ô chọn hàm chọn <b>setup</b> → bấm <b>▶ Chạy</b> → <b>Xem xét quyền</b> → chọn tài khoản → <b>Cho phép</b>.</li>
          <li>Nhật ký hiện “Đã gửi … tab sang portal” là xong → tải lại trang này. <b>Không cần</b> bấm Triển khai.</li>
        </ol>
        <div style="position:relative;display:block;width:100%"><textarea class="input mono" rows="6" readonly style="font-size:11.5px;display:block;width:100%;box-sizing:border-box">${esc(d.gas_script)}</textarea>
          <button type="button" class="btn btn-sm" id="hb-copy" style="position:absolute;right:8px;top:8px">${icon('copy')} Sao chép</button></div>
        <span class="hint">Đổi link sheet ở trên thì bấm Lưu, sao chép lại code và chạy lại setup. Mã bảo mật trong code là riêng của portal — không chia sẻ ra ngoài. Tài khoản chạy script mất quyền xem sheet thì Cẩm nang giữ bản cũ, không cập nhật nữa.</span></details>
      <div class="field"><label>Cách hiển thị từng mục khi CTV tìm kiếm</label>
        <span class="hint" style="margin-bottom:6px">Hiện sẵn: hiện ngay các dòng khớp (VD Script, Template, Kho ticket) · Gợi ý: danh sách gọn, bấm để xem chi tiết (VD Tra cứu nghiệp vụ) · Khác: thu gọn cuối trang · Ẩn: CTV không thấy mục này.</span>
        ${d.tabs.length ? `<div style="border:1px solid var(--border);border-radius:8px">${d.tabs.map(t => `<div style="display:flex;gap:10px;align-items:center;justify-content:space-between;padding:8px 12px;border-bottom:1px solid var(--border)">
          <span>${esc(t.name)}</span><select class="input" data-gid="${t.gid}" style="height:32px">
          ${[['show', 'Hiện sẵn'], ['suggest', 'Gợi ý'], ['other', 'Khác'], ['hidden', 'Ẩn']].map(([v, l]) => `<option value="${v}" ${t.mode === v ? 'selected' : ''}>${l}</option>`).join('')}</select></div>`).join('')}</div>` : '<span class="muted">Chưa đọc được tab nào.</span>'}
        ${d.fetched_at ? `<span class="hint">Đã đọc lúc ${d.fetched_at.slice(11, 16)} ${fmtDate(d.fetched_at.slice(0, 10))}</span>` : ''}</div>
      <button class="btn btn-primary">Lưu</button>
    </form>`;
  $('#hb-form').onsubmit = e => {
    e.preventDefault();
    const modes = Object.fromEntries($$('#hb-form select[data-gid]').map(sel => [sel.dataset.gid, sel.value]));
    run(e.submitter, async () => { await api('/admin/handbook', { method: 'PUT', body: { sheet: $('#hb-sheet').value, modes } }); toast('Đã lưu'); aHandbook(v); });
  };
  $('#hb-copy').onclick = () => navigator.clipboard.writeText(d.gas_script).then(() => toast('Đã sao chép code'));
}

/* Thao tác ở CRM: dán link Drive (thư mục hoặc từng video) → CTV xem video ngay trên web */
async function aCRM(v) {
  const desc = 'Dán link Google Drive của thư mục hoặc từng video. CTV xem trực tiếp ở mục Tra cứu → Thao tác ở CRM.';
  v.innerHTML = loading();
  const [d, ph] = await Promise.all([api('/admin/crm-videos'), api('/admin/ph-videos')]);
  let src = d.sources.length ? d.sources : [{ title: '', url: '' }];
  v.innerHTML = docHead(desc, `<a class="btn btn-sm" href="/ctv#crm" target="_blank" rel="noopener">${icon('external')} Xem như CTV</a>`) + `
    <form class="card card-pad" id="cv-form">
      <div class="field"><label>Link Google Drive</label>
        <span class="hint" style="margin-bottom:8px">Thư mục / video phải chia sẻ “Bất kỳ ai có đường liên kết — Người xem”. Dán link thư mục thì mọi video trong thư mục (và thư mục con) tự hiện; thêm video vào thư mục Drive là web tự cập nhật sau tối đa 5 phút.</span>
        <div id="cv-rows"></div>
        <button type="button" class="btn btn-sm" id="cv-add" style="margin-top:8px">${icon('plus')} Thêm link</button></div>
      <button class="btn btn-primary">Lưu</button>
    </form>
    <form class="card card-pad" id="ph-form">
      <div class="field"><label>Kênh YouTube — Video hướng dẫn PH</label>
        <span class="hint" style="margin-bottom:8px">CTV xem ở mục Tra cứu → Video hướng dẫn PH (xem trước + sao chép link gửi PH). Video mới đăng lên kênh tự hiện sau tối đa 10 phút.</span>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><input class="input" name="channel" value="${esc(ph.channel)}" placeholder="https://www.youtube.com/@TenKenh" style="flex:1;min-width:260px">
          <button class="btn btn-primary">Lưu kênh</button><a class="btn" href="/ctv#ph-videos" target="_blank" rel="noopener">Xem như CTV</a></div></div>
    </form>
    <div class="card"><div class="card-head"><h2>CTV đang thấy</h2><span class="badge">${d.groups.reduce((a, g) => a + g.items.length, 0)} video / tệp</span></div>
      <div class="card-pad">${d.groups.length ? d.groups.map(g => `<div style="margin-bottom:12px"><b>${esc(g.title)}</b> <span class="small muted">${g.items.length} mục</span>
        ${g.error ? `<div><span class="badge red">${esc(g.error)}</span></div>` : ''}
        <div class="small muted" style="margin-top:4px">${g.items.map(it => esc(it.title)).join(' · ') || '—'}</div></div>`).join('') : '<p class="muted">Chưa có link nào.</p>'}</div></div>`;
  const rowsEl = $('#cv-rows');
  const paint = () => {
    rowsEl.innerHTML = src.map((s, i) => `<div class="form-row" style="align-items:center;margin-bottom:8px" data-i="${i}">
      <input class="input" data-k="title" value="${esc(s.title)}" placeholder="Tên nhóm (tuỳ chọn, VD: Đặt lịch học)" style="max-width:260px">
      <div style="display:flex;gap:8px;flex:1;min-width:260px"><input class="input" data-k="url" value="${esc(s.url)}" placeholder="https://drive.google.com/drive/folders/…" style="flex:1">
        <button type="button" class="btn btn-icon" data-rm="${i}" aria-label="Xoá link">${icon('x')}</button></div></div>`).join('');
  };
  const collect = () => { src = $$('#cv-rows [data-i]').map(r => ({ title: $('[data-k="title"]', r).value, url: $('[data-k="url"]', r).value })); };
  paint();
  $('#cv-add').onclick = () => { collect(); src.push({ title: '', url: '' }); paint(); $$('#cv-rows [data-k="url"]').pop().focus(); };
  rowsEl.onclick = e => { const b = e.target.closest('[data-rm]'); if (!b) return; collect(); src.splice(+b.dataset.rm, 1); if (!src.length) src.push({ title: '', url: '' }); paint(); };
  $('#cv-form').onsubmit = e => {
    e.preventDefault(); collect();
    run(e.submitter, async () => { await api('/admin/crm-videos', { method: 'PUT', body: { sources: src.filter(s => s.url.trim()) } }); toast('Đã lưu'); aCRM(v); });
  };
  $('#ph-form').onsubmit = e => {
    e.preventDefault();
    run(e.submitter, async () => { const r = await api('/admin/ph-videos', { method: 'PUT', body: { channel: e.target.channel.value } }); toast(`Đã lưu kênh · ${r.count} video`); aCRM(v); });
  };
}

/* =========================================================
   Document: gom Cẩm nang + Video thao tác CRM + các tab tài liệu admin tự thêm
   ========================================================= */
const docHead = (desc, actions = '') => `<div class="doc-sub"><p class="muted">${desc}</p>${actions ? `<div class="actions">${actions}</div>` : ''}</div>`;
const DOC_DESC = 'Tài liệu cho CTV: Cẩm nang, video thao tác CRM và các tab tài liệu tự thêm (link YouTube / Google Drive).';
const DOC_BUILTIN = [
  { id: 'handbook', name: 'Cẩm nang', render: aHandbook },
  { id: 'crm', name: 'Video thao tác CRM', render: aCRM },
  { id: 'milo', name: 'TK Milo', render: aMilo },
];
/* tab TK Milo: 3 file nguồn (chỉ chia sẻ trong công ty) → Apps Script gửi các dòng Milo sang portal */
async function aMilo(body) {
  body.innerHTML = loading();
  const d = await api('/admin/milo');
  const L = { s1: ['File ICC_Bàn giao học viên (tab Format)', 'https://docs.google.com/spreadsheets/d/…'], s2: ['File data_handover (tab ICC_15052024)', 'https://docs.google.com/spreadsheets/d/…'], vh: ['File làm việc Milo của VH (tab File làm việc Milo)', 'https://docs.google.com/spreadsheets/d/…'] };
  const c = d.count, m = d.mail || {};
  body.innerHTML = `<div class="card"><div class="card-pad">
    <p class="small muted" style="margin-bottom:12px">CTV vào <b>Document → TK Milo</b>, tìm học viên theo tên / email / SĐT để xem: đã bàn giao ở 2 file nguồn chưa, đã có trong file VH chưa, username / password được tạo và tình trạng cấp tài khoản. Khớp học viên giữa các file theo email hoặc SĐT.</p>
    ${d.data_at ? `<p class="small" style="margin-bottom:12px"><span class="badge green">Đang nhận dữ liệu</span> Cập nhật lúc <b>${hm(d.data_at)} ${fmtDate(d.data_at.slice(0, 10))}</b>${c ? ` · nguồn 1: ${c.s1} dòng Milo · nguồn 2: ${c.s2} · file VH: ${c.vh}` : ''}${d.seen_at ? ` · Apps Script kiểm tra gần nhất ${hm(d.seen_at)}` : ''}</p>` : '<p class="small" style="margin-bottom:12px"><span class="badge amber">Chưa nhận dữ liệu</span> Dán link 3 file → Lưu → cài Apps Script bên dưới.</p>'}
    <form id="milo-form">${Object.entries(L).map(([k, [lb, ph]]) => `<div class="field"><label>${lb}</label><input class="input" name="${k}" required value="${esc(d.sources[k])}" placeholder="${ph}"></div>`).join('')}
      <button class="btn btn-primary">Lưu</button></form>
    ${d.gas_script ? `<details style="margin-top:16px" ${d.data_at ? '' : 'open'}><summary style="cursor:pointer"><b>Cài Apps Script để tự gửi dữ liệu sang portal</b> ${d.data_at ? '<span class="badge green">Đã cài</span>' : '<span class="muted small">(cài 1 lần)</span>'}</summary>
      <ol class="small" style="margin:8px 0 8px 18px;line-height:1.7">
        <li>Đăng nhập Google bằng tài khoản <b>công ty xem được cả 3 file</b> → mở <a href="https://script.google.com/home/projects/create" target="_blank" rel="noopener">script.google.com → Dự án mới</a>.</li>
        <li>Xoá code mẫu, dán đoạn code bên dưới → bấm 💾 <b>Lưu</b>.</li>
        <li>Ô chọn hàm chọn <b>miloSetup</b> → <b>▶ Chạy</b> → <b>Xem xét quyền</b> → chọn tài khoản → <b>Cho phép</b>.</li>
        <li>Nhật ký hiện “Đã gửi sang portal …” là xong → tải lại trang này. Lần đầu đọc toàn bộ lịch sử (có thể cần vài lượt, mỗi lượt cách vài phút). Sau đó file VH sửa là gửi gần như ngay, 2 file bàn giao kiểm tra 2 phút/lần trong giờ làm (7h–23h), 15 phút/lần ban đêm (chỉ đọc ~200 dòng cuối mỗi file).</li>
      </ol>
      <div style="position:relative;display:block;width:100%"><textarea class="input mono" rows="6" readonly style="font-size:11.5px;display:block;width:100%;box-sizing:border-box">${esc(d.gas_script)}</textarea>
        <button type="button" class="btn btn-sm" id="milo-copy" style="position:absolute;right:8px;top:8px">${icon('copy')} Sao chép</button></div>
      <span class="hint">Đổi link file, hoặc sửa dòng cũ trong sheet, thì bấm Lưu → sao chép lại code → dán đè → chạy lại miloSetup (gửi lại toàn bộ lịch sử). Mã bảo mật trong code là riêng của portal — không chia sẻ ra ngoài.</span></details>` : ''}
  </div></div>
  <div class="card" style="margin-top:14px"><div class="card-pad">
    <h3 style="margin:0 0 6px">Mail đã gửi cho học viên (hộp mail chung)</h3>
    <p class="small muted" style="margin-bottom:12px">CTV tìm học viên ở tab TK Milo sẽ thấy các mail hộp mail chung đã gửi tới email học viên, bấm xem và <b>Sao chép ảnh</b> chụp mail để gửi cho học viên.</p>
    ${m.count ? `<p class="small" style="margin-bottom:12px"><span class="badge green">Đang nhận mail</span> Đã lưu <b>${m.count}</b> mail${m.oldest ? ` (cũ nhất gửi ngày <b>${fmtDate(m.oldest.slice(0, 10))}</b> — lịch sử gửi từ mới về cũ, ngày này còn lùi tức là chưa gửi xong)` : ''}${m.data_at ? ` · mail mới nhất về lúc ${hm(m.data_at)} ${fmtDate(m.data_at.slice(0, 10))}` : ''}${m.seen_at ? ` · Apps Script kiểm tra gần nhất ${hm(m.seen_at)}` : ''}</p>` : `<p class="small" style="margin-bottom:12px"><span class="badge amber">Chưa nhận mail</span>${m.seen_at ? ` Apps Script kiểm tra gần nhất ${hm(m.seen_at)}` : ' Cài Apps Script bên dưới bằng tài khoản mail chung.'}</p>`}
    <details ${m.count ? '' : 'open'}><summary style="cursor:pointer"><b>Cài Apps Script bằng tài khoản mail chung</b> <span class="muted small">(cài 1 lần — project riêng, không dán chung với script 3 file ở trên)</span></summary>
      <ol class="small" style="margin:8px 0 8px 18px;line-height:1.7">
        <li>Đăng nhập Google bằng <b>tài khoản mail chung</b> (hộp mail gửi tài khoản Milo cho học viên) → mở <a href="https://script.google.com/home/projects/create" target="_blank" rel="noopener">script.google.com → Dự án mới</a>.</li>
        <li>Xoá code mẫu, dán đoạn code bên dưới → bấm 💾 <b>Lưu</b>.</li>
        <li>Ô chọn hàm chọn <b>miloMailSetup</b> → <b>▶ Chạy</b> → <b>Xem xét quyền</b> → chọn tài khoản mail chung → <b>Cho phép</b> (quyền đọc Gmail để lấy thư mục Đã gửi).</li>
        <li>Nhật ký hiện “Đã gửi … mail” là xong. Lịch sử cũ gửi dần qua các lần chạy (mỗi lượt tối đa ~4 phút); mail mới kiểm tra 2 phút/lần giờ làm (7h–23h), 15 phút/lần ban đêm.</li>
      </ol>
      <div style="position:relative;display:block;width:100%"><textarea class="input mono" rows="6" readonly style="font-size:11.5px;display:block;width:100%;box-sizing:border-box">${esc(m.gas_script)}</textarea>
        <button type="button" class="btn btn-sm" id="milo-mail-copy" style="position:absolute;right:8px;top:8px">${icon('copy')} Sao chép</button></div>
      <span class="hint">Chỉ lấy mail có tiêu đề chứa <b>[Speakwell - MILO]</b> (portal cũng bỏ qua mail khác); chỉ lấy lịch sử từ một ngày: sửa <span class="mono">MM_SINCE</span>. Sửa xong chạy lại miloMailSetup (xoá mail đã lưu và gửi lại). Muốn quét lại lịch sử mà không xoá mail đã lưu: chạy <b>miloMailHistory</b>. CTV báo có mail mà portal không thấy: điền email vào <span class="mono">MM_CHECK_EMAIL</span> → chạy hàm <b>miloMailCheck</b> (xem nguyên nhân trong nhật ký + gửi luôn mail đó).</span></details>
  </div></div>`;
  const mcb = $('#milo-mail-copy', body); if (mcb) mcb.onclick = () => navigator.clipboard.writeText(m.gas_script).then(() => toast('Đã sao chép code'));
  $('#milo-form', body).onsubmit = e => {
    e.preventDefault();
    const f = new FormData(e.target);
    run(e.submitter, async () => { await api('/admin/milo', { method: 'PUT', body: Object.fromEntries(f) }); toast('Đã lưu'); aMilo(body); });
  };
  const cb = $('#milo-copy', body); if (cb) cb.onclick = () => navigator.clipboard.writeText(d.gas_script).then(() => toast('Đã sao chép code'));
}
const DOC_KIND = url => {
  const u = (url || '').trim();
  if (/docs\.google\.com\/spreadsheets\/.*[#&?]gid=\d+/.test(u)) return 'Tab Google Sheet (tab của file Cẩm nang sẽ hiện thành bảng tra cứu)';
  if (/docs\.google\.com\/(document|spreadsheets|presentation|forms)\//.test(u)) return 'Google Docs';
  if (/drive\.google\.com\/.*\/folders\//.test(u)) return 'Thư mục Drive';
  if (/drive\.google\.com/.test(u)) return 'Tệp Drive';
  if (/(youtube\.com|youtu\.be)/.test(u)) return /[?&]v=|youtu\.be\/|\/shorts\//.test(u) ? 'Video YouTube' : /[?&]list=/.test(u) ? 'Playlist YouTube' : 'Kênh YouTube';
  return '';
};

async function aDocs(v) {
  v.innerHTML = pageHead('Document', DOC_DESC) + loading();
  let tabs = await api('/admin/docs');
  let cur = store.get('admin_doc_tab') || 'handbook';
  const all = () => [...DOC_BUILTIN, ...tabs];
  const save = async next => { tabs = await api('/admin/docs', { method: 'PUT', body: { tabs: next } }); };

  const paint = () => {
    if (!all().some(t => t.id === cur)) cur = 'handbook';
    v.innerHTML = pageHead('Document', DOC_DESC) + `
      <div class="doc-tabs" role="tablist">${all().map(t => `<button role="tab" data-tab="${t.id}" class="${t.id === cur ? 'active' : ''}">${esc(t.name)}</button>`).join('')}
        <button class="doc-add" id="doc-add">${icon('plus')} Thêm tab</button></div>
      <div id="doc-body"></div>`;
    $$('.doc-tabs [data-tab]').forEach(b => b.onclick = () => { cur = b.dataset.tab; store.set('admin_doc_tab', cur); paint(); });
    $('#doc-add').onclick = () => editTab();
    const b = DOC_BUILTIN.find(t => t.id === cur), body = $('#doc-body');
    Promise.resolve(b ? b.render(body) : customTab(body, tabs.find(t => t.id === cur)))
      .catch(e => { body.innerHTML = `<div class="card">${emptyState(e.message)}</div>`; });
  };

  const editTab = t => {
    const m = modal({ title: t ? 'Sửa tab' : 'Thêm tab tài liệu', body: `<form id="dt-form">
        <div class="field"><label for="dt-name">Tên tab</label><input class="input" id="dt-name" required maxlength="60" value="${esc(t ? t.name : '')}" placeholder="VD: Quy trình xử lý ticket"></div>
        <div class="field"><label for="dt-url">Link tài liệu</label><input class="input" id="dt-url" required value="${esc(t ? t.url : '')}" placeholder="https://youtube.com/… hoặc https://drive.google.com/…">
          <span class="hint">Hỗ trợ: video / playlist / kênh YouTube · tệp hoặc thư mục Google Drive · Google Docs, Sheets, Slides. Link Drive phải chia sẻ “Bất kỳ ai có đường liên kết — Người xem”.</span>
          <span class="hint" id="dt-kind"></span></div>
        <div class="field"><label for="dt-hb">Hoặc chọn 1 tab trong file Cẩm nang</label><select class="input" id="dt-hb"><option value="">Đang tải danh sách tab…</option></select>
          <span class="hint">CTV xem tab đó dạng bảng có ô tìm kiếm ngay trên portal (VD tra thông tin GV), không cần quyền mở sheet. Dữ liệu cập nhật theo Cẩm nang.</span></div>
        <button class="btn btn-primary">${t ? 'Lưu' : 'Thêm tab'}</button></form>` });
    api('/admin/handbook').then(h => {
      const sel = $('#dt-hb'); if (!sel) return;
      const base = h.sheet_url.replace(/\/+$/, '');
      sel.innerHTML = `<option value="">— Chọn tab —</option>` + h.tabs.map(x => `<option value="${esc(x.gid)}" data-name="${esc(x.name)}" ${t && t.url === `${base}/edit#gid=${x.gid}` ? 'selected' : ''}>${esc(x.name)}</option>`).join('');
      sel.onchange = () => {
        const o = sel.selectedOptions[0]; if (!sel.value) return;
        $('#dt-url').value = `${base}/edit#gid=${sel.value}`;
        if (!$('#dt-name').value.trim()) $('#dt-name').value = o.dataset.name;
        kind();
      };
    }).catch(() => { const sel = $('#dt-hb'); if (sel) sel.innerHTML = '<option value="">Chưa đọc được Cẩm nang</option>'; });
    const kind = () => { const k = DOC_KIND($('#dt-url').value); $('#dt-kind').textContent = k ? `Nhận dạng: ${k}` : ''; };
    $('#dt-url').oninput = kind; kind();
    $('#dt-name').focus();
    $('#dt-form').onsubmit = e => {
      e.preventDefault();
      const item = { id: t ? t.id : '', name: $('#dt-name').value, url: $('#dt-url').value };
      run(e.submitter, async () => {
        const before = tabs.map(x => x.id);
        await save(t ? tabs.map(x => x.id === t.id ? item : x) : [...tabs, item]);
        if (!t) cur = (tabs.find(x => !before.includes(x.id)) || {}).id || cur;
        store.set('admin_doc_tab', cur); m.close(); toast(t ? 'Đã lưu tab' : 'Đã thêm tab'); paint();
      });
    };
  };

  async function customTab(body, t) {
    const i = tabs.indexOf(t);
    body.innerHTML = docHead(`${esc(DOC_KIND(t.url) || 'Link')} · <a href="${esc(t.url)}" target="_blank" rel="noopener">${esc(t.url)}</a>`, `
      <button class="btn btn-sm" data-act="left" ${i === 0 ? 'disabled' : ''} title="Chuyển tab sang trái" aria-label="Chuyển tab sang trái">←</button>
      <button class="btn btn-sm" data-act="right" ${i === tabs.length - 1 ? 'disabled' : ''} title="Chuyển tab sang phải" aria-label="Chuyển tab sang phải">→</button>
      <button class="btn btn-sm" data-act="edit">Sửa</button>
      <button class="btn btn-sm" data-act="del">${icon('x')} Xoá tab</button>
      <a class="btn btn-sm" href="/ctv#docs" target="_blank" rel="noopener">${icon('external')} Xem như CTV</a>`) + `<div id="dv">${loading()}</div>`;
    $('.doc-sub', body).onclick = async e => {
      const a = e.target.closest('[data-act]'); if (!a) return;
      if (a.dataset.act === 'edit') return editTab(t);
      if (a.dataset.act === 'del') {
        if (!(await confirmDialog(`Xoá tab “${esc(t.name)}”?`, 'CTV sẽ không còn thấy tab này. Tài liệu gốc trên YouTube / Drive không bị ảnh hưởng.', 'Xoá', true))) return;
        return run(a, async () => { await save(tabs.filter(x => x.id !== t.id)); toast('Đã xoá tab'); paint(); });
      }
      const j = a.dataset.act === 'left' ? i - 1 : i + 1, next = tabs.slice();
      [next[i], next[j]] = [next[j], next[i]];
      run(a, async () => { await save(next); paint(); });
    };
    const d = await api(`/docs/${t.id}`, { query: { refresh: 1 } });
    if (d.table) {
      const bl = d.table.blocks || [];
      $('#dv', body).innerHTML = `<div class="card"><div class="card-head"><h2>CTV đang thấy</h2><span class="badge">${bl.length} bảng</span></div><div class="card-pad">
        ${d.warning ? `<p><span class="badge red">${esc(d.warning)}</span></p>` : ''}
        <p class="small muted">Lấy từ file Cẩm nang, CTV xem dạng bảng có ô tìm kiếm (tìm theo mọi cột, VD tên hoặc mã). Cập nhật lúc ${d.table.fetched_at.slice(11, 16)}.</p>
        ${d.ican ? `<div class="notice" style="margin:8px 0">Cột <b>Link teacher site</b> lấy theo tên GV từ <a href="https://www.icanconnect.vn/giao-vien" target="_blank" rel="noopener">icanconnect.vn/giao-vien</a>: khớp <b>${d.ican.matched}</b> GV${d.ican.missing.length ? ` · <b>${d.ican.missing.length}</b> GV không thấy trên web (giữ link trong sheet): <span class="small">${d.ican.missing.map(esc).join(', ')}</span>` : ''} · cột Link profile giữ nguyên theo sheet${d.ican.error ? `<br><span class="badge red">${esc(d.ican.error)}</span>` : ''}</div>` : ''}
        ${bl.map(b => `<div style="margin-top:8px"><b>${esc(b.title || 'Bảng')}</b> <span class="small muted">${b.rows.length} dòng · cột: ${b.header.filter(Boolean).map(esc).join(', ')}</span></div>`).join('') || '<span class="muted">Chưa có nội dung</span>'}</div></div>`;
      return;
    }
    const n = d.groups.reduce((a, g) => a + g.items.length, 0);
    $('#dv', body).innerHTML = `<div class="card"><div class="card-head"><h2>CTV đang thấy</h2><span class="badge">${n} mục</span></div><div class="card-pad">
      ${d.error ? `<p><span class="badge red">${esc(d.error)}</span></p>` : ''}${d.warning ? `<p><span class="badge red">${esc(d.warning)}</span></p>` : ''}
      ${d.single ? `<div class="crm-frame" style="border-radius:8px;overflow:hidden;max-width:720px"><iframe src="${esc(d.groups[0].items[0].embed)}" allow="autoplay; encrypted-media; fullscreen" allowfullscreen title="${esc(t.name)}"></iframe></div>`
        : d.groups.map(g => `<div style="margin-bottom:12px">${g.title ? `<b>${esc(g.title)}</b> ` : ''}<span class="small muted">${g.items.length} mục</span>
          <div class="small muted" style="margin-top:4px">${g.items.map(it => esc(it.title)).join(' · ') || '—'}</div></div>`).join('')}</div></div>`;
  }
  paint();
}

/* =========================================================
   9. Thông báo · 10. Nhật ký
   ========================================================= */
async function aNotifications(v) {
  v.innerHTML = pageHead('Thông báo', 'Gửi thông báo tới toàn bộ CTV. Thông báo hiện trong menu tài khoản.') + `
    <div class="grid-2"><form class="card card-pad" id="nf">
      <div class="field"><label>Tiêu đề</label><input class="input" name="title" required placeholder="VD: Mở đăng ký lịch rảnh tháng 12"></div>
      <div class="field"><label>Nội dung</label><textarea class="input" name="body" rows="5"></textarea></div>
      <button class="btn btn-primary">${icon('megaphone')} Gửi thông báo</button></form>
    <div class="card"><div class="card-head"><h2>Đã gửi</h2></div><div id="list">${loading()}</div></div></div>`;
  const load = async () => {
    const list = await api('/notifications');
    $('#list').innerHTML = list.length ? list.map(n => `<div style="padding:12px 20px;border-bottom:1px solid var(--border);display:flex;gap:12px;justify-content:space-between">
      <div><b>${esc(n.title)}</b>${n.body ? `<div class="muted small">${esc(n.body)}</div>` : ''}<div class="small muted">${fmtDate(n.created_at.slice(0, 10))} ${n.created_at.slice(11, 16)}</div></div>
      <button class="btn btn-sm btn-ghost" data-del="${n.id}" aria-label="Xoá">${icon('x')}</button></div>`).join('') : emptyState('Chưa có thông báo');
  };
  $('#nf').onsubmit = e => {
    e.preventDefault(); const f = e.target;
    run(e.submitter, async () => { await api('/admin/notifications', { method: 'POST', body: { title: f.title.value, body: f.body.value } }); f.reset(); toast('Đã gửi thông báo'); load(); });
  };
  $('#list').onclick = async e => {
    const b = e.target.closest('[data-del]'); if (!b) return;
    if (!(await confirmDialog('Xoá thông báo?', 'CTV sẽ không còn thấy thông báo này.', 'Xoá', true))) return;
    run(b, async () => { await api(`/admin/notifications/${b.dataset.del}`, { method: 'DELETE' }); load(); });
  };
  load();
}

/* ai đang mở web (trang gửi tín hiệu 1 phút/lần) — tự làm mới 30 giây/lần khi đang ở trang Nhật ký */
const agoText = s => s < 60 ? 'vừa xong' : s < 3600 ? `${Math.floor(s / 60)} phút trước` : `${Math.floor(s / 3600)} giờ ${Math.floor(s % 3600 / 60)} phút trước`;
const durText = s => s < 60 ? 'dưới 1 phút' : s < 3600 ? `${Math.floor(s / 60)} phút` : `${Math.floor(s / 3600)} giờ ${Math.floor(s % 3600 / 60)} phút`;
async function paintOnline(box) {
  const d = await api('/admin/online').catch(() => null);
  if (!d || !box.isConnected) return;
  const who = u => `<b>${esc(u.name)}</b> <span class="muted small">${esc(u.username)}${u.role === 'admin' ? ' · admin' : ''}</span>`;
  box.innerHTML = `<div class="card-head"><h2>Đang mở web <span class="badge ${d.online.length ? 'green' : ''}">${d.online.length}</span></h2>
      <span class="small muted">Tự cập nhật 30 giây/lần · rời quá ~2 phút coi như đã thoát</span></div>
    <div class="card-pad">${d.online.length ? `<div class="online-list">${d.online.map(u => `<div class="online-row">
        <span class="dot ${u.visible ? 'on' : 'idle'}" title="${u.visible ? 'Đang xem trang' : 'Đang mở nhưng ở tab khác / thu nhỏ'}"></span>
        <div>${who(u)}<div class="small muted">${u.portal === 'admin' ? 'Trang Quản trị' : 'Trang CTV'} · ${esc(u.page || '—')}${u.visible ? '' : ' · <i>tab nền</i>'}${u.tabs > 1 ? ` · ${u.tabs} tab` : ''} · đã mở ${durText(u.since)}</div></div></div>`).join('')}</div>`
      : '<p class="small muted">Hiện không có ai mở web.</p>'}
    ${d.left.length ? `<details style="margin-top:10px"><summary class="small" style="cursor:pointer">Đã rời trong 24 giờ qua (${d.left.length})</summary>
      <div class="online-list" style="margin-top:8px">${d.left.map(u => `<div class="online-row"><span class="dot off"></span><div>${who(u)}<div class="small muted">Rời ${agoText(u.ago)}</div></div></div>`).join('')}</div></details>` : ''}</div>`;
}

async function aLogs(v) {
  v.innerHTML = pageHead('Nhật ký hệ thống', 'Mọi thao tác của CTV và quản trị viên.') + `
    <div class="card" id="online" style="margin-bottom:16px">${loading()}</div>
    <div class="filters"><div class="search">${icon('search')}<input class="input" id="q" placeholder="Tìm người thực hiện, hành động"></div></div><div class="card" id="body">${loading()}</div>`;
  const ob = $('#online');
  paintOnline(ob);
  const timer = setInterval(() => paintOnline(ob), 30000);
  App.cleanup.push(() => clearInterval(timer));
  const rows = await api('/admin/logs');
  const paint = () => {
    const q = $('#q').value.trim().toLowerCase();
    dataTable($('#body'), rows.filter(r => !q || `${r.actor} ${r.action}`.toLowerCase().includes(q)), [
      { label: 'Thời gian', render: r => `<span class="nowrap muted">${fmtDate(r.created_at.slice(0, 10))} ${r.created_at.slice(11, 19)}</span>` },
      { label: 'Người thực hiện', render: r => esc(r.actor) },
      { label: 'Hành động', render: r => esc(r.action) },
    ], { pageSize: 30 });
  };
  $('#q').oninput = paint; paint();
}

/* ---------- khởi động ---------- */
App.start({
  role: 'admin', brand: 'Cổng CTV', subtitle: 'Quản trị', loginHint: 'Khu vực dành cho quản lý.',
  nav: [
    { group: 'Vận hành', items: [
      { id: 'dashboard', label: 'Tổng quan', icon: 'home', render: aDashboard },
      { id: 'schedule', label: 'Xếp lịch', icon: 'calendar', render: aSchedule },
      { id: 'availability', label: 'Lịch rảnh CTV', icon: 'checkSquare', render: aAvailability },
      { id: 'timesheet', label: 'Chấm công', icon: 'clock', render: aTimesheet },
      { id: 'swaps', label: 'Duyệt đổi ca', icon: 'swap', render: aSwaps },
    ] },
    { group: 'Tài chính', items: [
      { id: 'qc', label: 'Lỗi QC', icon: 'alert', render: aQC },
      { id: 'salary', label: 'Bảng lương', icon: 'wallet', render: aSalary },
    ] },
    { group: 'Hệ thống', items: [
      { id: 'users', label: 'Nhân sự', icon: 'users', render: aUsers },
      { id: 'catalog', label: 'Danh mục', icon: 'grid', render: aCatalog },
      { id: 'docs', label: 'Document', icon: 'book', render: aDocs },
      { id: 'notifications', label: 'Thông báo', icon: 'bell', render: aNotifications },
      { id: 'logs', label: 'Nhật ký hệ thống', icon: 'list', render: aLogs },
    ] },
  ],
});
setTimeout(() => { if (App.user) refreshSwapCount(); }, 800);
