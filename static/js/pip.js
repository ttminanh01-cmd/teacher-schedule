/* =========================================================
   Theo dõi CTV (PIP) — dùng chung cho trang Quản trị và trang CTV:
   dán ảnh Ctrl+V, ảnh cần đăng nhập, thẻ nhận xét + phản hồi
   ========================================================= */
const PIP_RATING = { 'Tốt': 'green', 'Đạt': 'blue', 'Cần cải thiện': 'amber', 'Chưa đạt': 'red' };
const PIP_STATUS = { active: ['Đang QC', 'accent'], passed: ['Đạt', 'green'], extended: ['Gia hạn', 'amber'], failed: ['Không đạt', 'red'] };
const pipStatusBadge = s => { const [l, c] = PIP_STATUS[s] || [s, '']; return `<span class="badge ${c}">${l}</span>`; };
const fmtDT = s => s ? `${s.slice(11, 16)} ${fmtDate(s.slice(0, 10))}` : '';
const pipGoals = g => { const l = String(g || '').split('\n').map(x => x.replace(/^[-•*\d.)\s]+/, '').trim()).filter(Boolean);
  return l.length ? `<ol class="pip-goals">${l.map(x => `<li>${esc(x)}</li>`).join('')}</ol>` : '<span class="muted">—</span>'; };

/* thu nhỏ ảnh trên trình duyệt (cạnh dài ≤ 1600px) → data URL JPEG; PNG nhỏ giữ nguyên cho nét chữ */
function shrinkImage(file, max = 1600) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file), img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      const k = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement('canvas'); c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
      const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height); g.drawImage(img, 0, 0, c.width, c.height);
      const png = file.type === 'image/png' && k === 1 && file.size < 300000 ? c.toDataURL('image/png') : null;
      resolve(png || c.toDataURL('image/jpeg', 0.85));
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Không đọc được ảnh')); };
    img.src = url;
  });
}

/* ô dán ảnh: Ctrl+V vào textarea (hoặc vào khung), kéo thả, hoặc bấm chọn ảnh. keep = id ảnh cũ (khi sửa) */
function imagePaste(box, textarea, keep = []) {
  let added = [], kept = [...keep];
  box.insertAdjacentHTML('beforeend', `<div class="paste-row"><div class="thumbs"></div>
    <label class="btn btn-sm btn-ghost paste-pick">${icon('plus')} Ảnh<input type="file" accept="image/*" multiple hidden></label>
    <span class="small muted">Ctrl+V để dán ảnh</span></div>`);
  const thumbs = $('.thumbs', box);
  const paint = () => {
    thumbs.innerHTML = kept.map(id => `<span class="thumb"><img data-img="${id}" alt=""><button type="button" data-rm-k="${id}" aria-label="Bỏ ảnh">×</button></span>`).join('')
      + added.map((d, i) => `<span class="thumb"><img src="${d}" alt=""><button type="button" data-rm-a="${i}" aria-label="Bỏ ảnh">×</button></span>`).join('');
    loadAuthImages(thumbs);
  };
  const addFiles = async files => {
    for (const f of [...files].filter(f => f.type.startsWith('image/'))) {
      if (added.length + kept.length >= 8) { toast('Tối đa 8 ảnh', 'error'); break; }
      try { added.push(await shrinkImage(f)); } catch (e) { toast(e.message, 'error'); }
    }
    paint();
  };
  const onPaste = e => {
    const files = [...(e.clipboardData?.items || [])].filter(i => i.kind === 'file').map(i => i.getAsFile()).filter(Boolean);
    if (files.length) { e.preventDefault(); addFiles(files); }
  };
  const zone = box.closest('form') || box;
  zone.addEventListener('paste', onPaste);
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drop'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drop'));
  zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('drop'); addFiles(e.dataTransfer.files); });
  $('.paste-pick input', box).onchange = e => { addFiles(e.target.files); e.target.value = ''; };
  thumbs.addEventListener('click', e => {
    const a = e.target.closest('[data-rm-a]'), k = e.target.closest('[data-rm-k]');
    if (a) added.splice(+a.dataset.rmA, 1); else if (k) kept = kept.filter(x => x !== +k.dataset.rmK); else return;
    paint();
  });
  paint();
  return { images: () => added, keep: () => kept, count: () => added.length + kept.length };
}

/* ảnh lưu trong DB cần token → tải bằng fetch rồi gắn blob URL (có cache trong phiên) */
const _imgCache = new Map();
function loadAuthImages(root) {
  $$('img[data-img]', root).forEach(img => {
    const id = img.dataset.img;
    const url = id.startsWith('qc:') ? `/api/qc/images/${id.slice(3)}` : `/api/pip/images/${id}`;
    if (!_imgCache.has(id)) _imgCache.set(id, fetch(url, { headers: { Authorization: 'Bearer ' + (store.get(TOKEN_KEY) || '') } })
      .then(r => { if (!r.ok) throw new Error(); return r.blob(); }).then(b => URL.createObjectURL(b)).catch(() => { _imgCache.delete(id); return ''; }));
    _imgCache.get(id).then(u => { if (u) img.src = u; });
  });
}
function lightbox(src) {
  const ov = document.createElement('div'); ov.className = 'lightbox';
  ov.innerHTML = `<img src="${src}" alt="">`;
  const close = () => { ov.remove(); document.removeEventListener('keydown', onKey, true); };
  const onKey = e => { if (e.key === 'Escape') { e.stopPropagation(); close(); } };
  ov.onclick = close;
  document.addEventListener('keydown', onKey, true); document.body.appendChild(ov);
}
document.addEventListener('click', e => { const im = e.target.closest('.pip-imgs img, .thumb img'); if (im && im.src) lightbox(im.src); });

const pipImgs = ids => ids && ids.length ? `<div class="pip-imgs">${ids.map(id => `<img data-img="${id}" alt="Ảnh đính kèm" loading="lazy">`).join('')}</div>` : '';

/* thẻ 1 nhận xét. admin = trang quản trị (có nút sửa / xoá nhận xét); me = id người đang xem */
function pipReviewCard(r, { admin = false, me = 0 } = {}) {
  const shifts = (r.shifts_text || '').split('\n').filter(Boolean);
  return `<div class="pip-review ${r.unread ? 'unread' : ''}" data-rid="${r.id}">
    <div class="pip-review-h">
      <div class="pip-shifts"><div class="pip-shifts-label">${shifts.length > 1 ? `${shifts.length} ca được nhận xét` : 'Ca được nhận xét'}</div>
        ${shifts.length ? shifts.map(s => { const [d, ...rest] = s.split(' · ');
          return `<span class="pip-shift">${icon('calendar')}<b>${esc(d)}</b>${rest.length ? `<span>${esc(rest.join(' · '))}</span>` : ''}</span>`; }).join('')
          : `<span class="pip-shift general">${icon('message')}<b>Nhận xét chung</b></span>`}</div>
      <div class="actions">${r.rating ? `<span class="badge pip-rating ${PIP_RATING[r.rating] || ''}">${esc(r.rating)}</span>` : ''}${r.unread ? '<span class="badge accent">Mới</span>' : ''}
        ${admin ? `<button class="btn btn-sm btn-ghost" data-edit-r="${r.id}">Sửa</button><button class="btn btn-sm btn-ghost" data-del-r="${r.id}">Xoá</button>` : ''}</div>
    </div>
    ${r.content ? `<div class="pip-text">${esc(r.content)}</div>` : ''}${pipImgs(r.images)}
    <div class="small muted">${esc(r.author || 'Quản lý')} · ${fmtDT(r.created_at)}${r.updated_at && r.updated_at !== r.created_at ? ` · đã sửa ${fmtDT(r.updated_at)}` : ''}</div>
    <div class="pip-thread">${(r.comments || []).map(c => `<div class="pip-comment ${c.role}">
        <div class="small"><b>${esc(c.author)}</b> <span class="muted">${c.role === 'ctv' ? 'CTV phản hồi' : 'Quản lý trả lời'} · ${fmtDT(c.created_at)}</span>
          ${admin || c.user_id === me ? `<button type="button" class="link-btn" data-del-c="${c.id}">Xoá</button>` : ''}</div>
        ${c.body ? `<div class="pip-text">${esc(c.body)}</div>` : ''}${pipImgs(c.images)}</div>`).join('')}
      ${App.user && App.user.view_as ? '' : `<form class="pip-reply" data-reply="${r.id}"><textarea class="input full" rows="2" placeholder="${admin ? 'Trả lời CTV…' : 'Có ý kiến khác hoặc thấy chưa đúng? Viết phản hồi cho quản lý…'}"></textarea>
        <div class="pip-reply-f"><div class="paste-box"></div><button class="btn btn-sm btn-primary">Gửi phản hồi</button></div></form>`}
    </div></div>`;
}

/* gắn sự kiện cho các thẻ nhận xét trong root: dán ảnh vào ô phản hồi, gửi, xoá phản hồi. onChange = tải lại */
function bindPipThreads(root, onChange) {
  $$('form[data-reply]', root).forEach(f => {
    const ta = $('textarea', f), pb = imagePaste($('.paste-box', f), ta);
    f.onsubmit = e => {
      e.preventDefault();
      run(e.submitter, async () => {
        if (!ta.value.trim() && !pb.count()) throw new Error('Vui lòng nhập nội dung phản hồi');
        await api(`/pip/reviews/${f.dataset.reply}/comments`, { method: 'POST', body: { body: ta.value, images: pb.images() } });
        toast('Đã gửi phản hồi'); onChange();
      });
    };
  });
  $$('[data-del-c]', root).forEach(d => d.onclick = async () => {
    if (!(await confirmDialog('Xoá phản hồi này?', 'Không thể hoàn tác.', 'Xoá', true))) return;
    run(null, async () => { await api(`/pip/comments/${d.dataset.delC}`, { method: 'DELETE' }); onChange(); });
  });
  loadAuthImages(root);
}

/* ---------- phản hồi lỗi QC (CTV ↔ quản lý), dùng ở tab Lỗi QC của cả 2 trang ---------- */
const qcReplyCell = r => r.replies || r.unread
  ? `<button class="btn btn-sm ${r.unread ? 'btn-reply-new' : ''}" data-thread="${r.id}">${icon('message')} ${r.replies}${r.unread ? ' · mới' : ''}</button>`
  : `<button class="btn btn-sm btn-ghost" data-thread="${r.id}">${icon('message')} ${App.config.role === 'admin' ? '—' : 'Phản hồi'}</button>`;

function qcThreadModal(qid, onChange) {
  const viewOnly = !!(App.user && App.user.view_as);
  const m = modal({ title: 'Phản hồi lỗi QC', wide: true, body: `<div id="qct">${loading(2)}</div>` });
  const load = async () => {
    const box = $('#qct', m.el); if (!box) return;
    const d = await api(`/qc/${qid}/thread`), q = d.qc, mine = q.user_id === App.user.id;
    box.innerHTML = `<div class="qc-sum">
        <div class="small muted">${fmtDate(q.date)} · ${esc(q.username)} · ${esc(q.name)}${q.category ? ` · <span class="badge">${esc(q.category)}</span>` : ''}</div>
        <div class="pip-text" style="font-weight:500">${esc(q.error || '—')}</div>
        ${q.note ? `<div class="small muted pip-text">${esc(q.note)}</div>` : ''}
        <div class="small">${q.penalty ? esc(q.penalty) + ' · ' : ''}${q.amount ? `<span class="minus">−${money(q.amount)}</span>` : 'Nhắc nhở'}
          ${/^https?:/.test(q.ticket || '') ? ` · <a href="${esc(q.ticket)}" target="_blank" rel="noopener">Mở ticket</a>` : ''}</div></div>
      <div class="pip-thread" style="border-top:0;padding-top:0">
        ${d.comments.length ? d.comments.map(c => `<div class="pip-comment ${c.role}">
          <div class="small"><b>${esc(c.author)}</b> <span class="muted">${c.role === 'ctv' ? 'CTV phản hồi' : 'Quản lý trả lời'} · ${fmtDT(c.created_at)}</span>
            ${!viewOnly && (App.config.role === 'admin' || c.user_id === App.user.id) ? `<button type="button" class="link-btn" data-del-qc="${c.id}">Xoá</button>` : ''}</div>
          ${c.body ? `<div class="pip-text">${esc(c.body)}</div>` : ''}${pipImgs((c.images || []).map(i => 'qc:' + i))}</div>`).join('')
          : `<div class="small muted">${mine || App.config.role !== 'admin' ? 'Chưa có phản hồi. Nếu thấy lỗi này chưa đúng, bạn có thể giải thích và gửi kèm ảnh bằng chứng (Ctrl+V).' : 'CTV chưa phản hồi lỗi này.'}</div>`}
        ${viewOnly ? '' : `<form class="pip-reply" id="qct-f"><textarea class="input full" rows="3" placeholder="${App.config.role === 'admin' ? 'Trả lời CTV…' : 'Giải thích / ý kiến của bạn về lỗi này…'}"></textarea>
          <div class="pip-reply-f"><div class="paste-box"></div><button class="btn btn-sm btn-primary">Gửi phản hồi</button></div></form>`}
      </div>`;
    loadAuthImages(box);
    const f = $('#qct-f', box);
    if (f) {
      const ta = $('textarea', f), pb = imagePaste($('.paste-box', f), ta);
      f.onsubmit = e => {
        e.preventDefault();
        run(e.submitter, async () => {
          if (!ta.value.trim() && !pb.count()) throw new Error('Vui lòng nhập nội dung phản hồi');
          await api(`/qc/${qid}/comments`, { method: 'POST', body: { body: ta.value, images: pb.images() } });
          toast('Đã gửi phản hồi'); await load(); onChange && onChange();
        });
      };
    }
    $$('[data-del-qc]', box).forEach(b => b.onclick = async () => {
      if (!(await confirmDialog('Xoá phản hồi này?', 'Không thể hoàn tác.', 'Xoá', true))) return;
      run(null, async () => { await api(`/qc/comments/${b.dataset.delQc}`, { method: 'DELETE' }); await load(); onChange && onChange(); });
    });
  };
  load().then(() => onChange && onChange(), e => { const b = $('#qct', m.el); if (b) b.innerHTML = emptyState(e.message); });
}
