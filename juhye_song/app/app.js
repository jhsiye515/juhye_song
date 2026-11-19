// 가나다 운영 콘솔 · 기획서(features/*)대로 브라우저 안에서 동작하는 예시
// 데이터: data.json(= data/all.json). 바꾼 것은 이 브라우저에만 저장되고 「처음으로」로 되돌린다.
// 기능 · 정책 ID는 코드 옆 주석과 화면의 「기획 ID 보기」에 같은 이름으로 단다.
'use strict';
const KEY = 'ganada-console-v1';
const BASE_NOW = '2026-11-16 09:00';
let D = null;      // 원본 예시 데이터(읽기 전용)
let S = null;      // 바뀌는 상태: incidents · alerts · clock · user · ids
const UI = {inc: {view: '처리 대기', sel: null, prio: '', who: '', q: ''}, srv: {view: '전체', sel: null, st: '', prj: '', q: ''},
  stat: {days: 30}, cost: {month: null}, alert: {}};

// ───────── 바탕 도구 ─────────
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const fmt = n => Number(n).toLocaleString('ko-KR');
const pad = n => String(n).padStart(2, '0');
const parse = s => new Date(s.replace(' ', 'T') + ':00+09:00');
// TIME-01 · TIME-03: 연-월-일 시:분, 한국 시간
const stamp = d => { const k = new Date(d.getTime() + 9 * 36e5); return `${k.getUTCFullYear()}-${pad(k.getUTCMonth() + 1)}-${pad(k.getUTCDate())} ${pad(k.getUTCHours())}:${pad(k.getUTCMinutes())}`; };
// 시계: 예시 데이터의 「지금」(2026-11-16 09:00)에서 실제로 흐른 시간만큼 간다
const now = () => new Date(parse(BASE_NOW).getTime() + (Date.now() - S.clock));
const hoursBetween = (a, b) => (b - a) / 36e5;
// TIME-02: 1시간 미만 분 · 48시간 미만 소수점 한 자리 시간 · 그 이상 일
const dur = h => h < 1 ? Math.max(0, Math.round(h * 60)) + '분' : h < 48 ? h.toFixed(1) + '시간' : Math.round(h / 24) + '일';
const user = id => D.users.find(u => u.id === id);
const me = () => user(S.user);
const ROLE = {'관리자': 'A', '운영자': 'O', '조회자': 'V'};
const role = () => ROLE[me().role];
const srv = id => D.servers.find(s => s.id === id) || {};
const prj = id => (D.projects.find(p => p.id === id) || {}).name || '—';
const TARGET = {P1: 4, P2: 8, P3: 24, P4: 72};                 // INC-PL-SLA-01
const PRIO_NOTE = {P1: '서비스 전체가 멈춤', P2: '주요 기능 일부가 멈춤', P3: '성능 저하 · 우회 가능', P4: '영향 적음'};
const ST_CLS = {'신규': 'info', '처리 중': 'warn', '해결': 'ok', '종료': 'mute'};   // STATUS-02
const SRV_CLS = {'실행 중': 'ok', '중지': 'mute', '오류': 'bad'};                 // STATUS-03

// 기획 ID → 그 ID를 정의한 포트폴리오 문서 자리
function docHref(id) {
  const plan = {INC: 'incident-queue', SRV: 'server-list', CST: 'cost-report'};
  let m = id.match(/^(INC|SRV|CST)-(FN|RQ)-/); if (m) return `../${plan[m[1]]}/spec.html#${id}`;
  m = id.match(/^(INC|SRV|CST)-(PL|OQ)-/); if (m) return `../${plan[m[1]]}/policy.html#${id}`;
  m = id.match(/^(OP|IN|CO)-(INC|SRV|CST)-/); if (m) return `../${plan[m[2]]}/screens.html#${id}`;
  m = id.match(/^(TIME|TABLE|STATUS)-/); if (m) return `../policies/POL-${m[1]}.html#${id}`;
  return '../';
}
const fid = (...ids) => ids.map(i => `<a class="fid" href="${docHref(i)}" target="_blank" rel="noopener" title="기획서에서 보기">${i}</a>`).join(' ');

// ───────── 저장 ─────────
function fresh() {
  return {v: 1, clock: Date.now(), user: 'U01', ids: false,
    incidents: JSON.parse(JSON.stringify(D.incidents)), alerts: JSON.parse(JSON.stringify(D.alerts))};
}
function load() {
  try { const s = JSON.parse(localStorage.getItem(KEY) || 'null'); if (s && s.v === 1) return s; } catch (e) { /* 저장소를 못 쓰면 새로 */ }
  return fresh();
}
function save() { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* 저장 못 해도 화면은 동작 */ } }
function toast(msg) {
  document.querySelectorAll('.toast').forEach(x => x.remove());
  const t = document.createElement('div'); t.className = 'toast'; t.setAttribute('role', 'status'); t.textContent = msg;
  document.body.appendChild(t); setTimeout(() => t.remove(), 3200);
}

// ───────── 틀 ─────────
const MENU = [['운영', [['인시던트', '#/incidents'], ['알림', '#/alerts']]], ['인프라', [['서버', '#/servers'], ['네트워크', null]]],
  ['비용', [['월별 비용', '#/costs'], ['예산', null]]]];
const ICO = {  // 16px 선 아이콘
  '인시던트': '<path d="M8 2.5 14 13H2L8 2.5Z"/><path d="M8 6.5v3"/><circle cx="8" cy="11.3" r=".4" fill="currentColor"/>',
  '알림': '<path d="M4 11V7a4 4 0 0 1 8 0v4l1 1.5H3L4 11Z"/><path d="M6.5 14h3"/>',
  '서버': '<rect x="2.5" y="2.5" width="11" height="4.5" rx="1.2"/><rect x="2.5" y="9" width="11" height="4.5" rx="1.2"/><path d="M5 4.75h.01M5 11.25h.01"/>',
  '네트워크': '<circle cx="8" cy="8" r="5.5"/><path d="M2.5 8h11M8 2.5c1.6 1.6 2.3 3.4 2.3 5.5S9.6 11.9 8 13.5C6.4 11.9 5.7 10.1 5.7 8S6.4 4.1 8 2.5Z"/>',
  '월별 비용': '<path d="M2.5 13.5h11"/><rect x="3.5" y="8" width="2" height="4" rx=".5"/><rect x="7" y="5" width="2" height="7" rx=".5"/><rect x="10.5" y="3" width="2" height="9" rx=".5"/>',
  '예산': '<rect x="2" y="4" width="12" height="9" rx="1.5"/><path d="M2 7h12M10.5 10h1.5"/>'};
const ico = m => `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICO[m] || ''}</svg>`;
function shell(menu, crumb, body) {
  const users = D.users.map(u => `<option value="${u.id}" ${u.id === S.user ? 'selected' : ''}>${esc(u.name)} · ${u.role}</option>`).join('');
  return `<div class="app ${S.ids ? 'ids' : ''}"><nav class="nav" aria-label="메뉴"><div class="logo"><i></i><span>가나다 운영 콘솔<small>가나다커머스 · 예시</small></span></div>
  ${MENU.map(([g, ms]) => `<div class="grp">${g}</div>` + ms.map(([m, h]) => h
    ? `<a href="${h}" class="${m === menu ? 'on' : ''}" ${m === menu ? 'aria-current="page"' : ''}>${ico(m)}${m}</a>`
    : `<a class="off" aria-disabled="true" title="이 예시에는 기획이 없는 메뉴입니다">${ico(m)}${m}<small>기획 없음</small></a>`).join('')).join('')}
  <div class="foot">가상 회사 · 예시 데이터입니다. <a href="../">기획 문서로 돌아가기</a></div></nav>
  <div class="main"><div class="top"><span class="crumb">${crumb}</span><span class="sp"></span>
    <span class="clock" title="예시 데이터의 시각에서 실제로 흐른 만큼 갑니다">${stamp(now())}</span>
    <span class="sample">예시 데이터</span>
    <div class="ctl"><button class="btn sm ${S.ids ? 'on' : ''}" data-act="ids" aria-pressed="${S.ids}">기획 ID 보기</button>
    <button class="btn sm ghost" data-act="reset">처음으로</button>
    <label class="who"><i aria-hidden="true">${esc(me().name[0])}</i><select class="sel" data-act="user" aria-label="사용자 바꾸기">${users}</select></label></div></div>
  <div class="page">${body}</div></div></div>`;
}
function denied(menu, crumb, what, who) {
  return shell(menu, crumb, `<div class="card denied"><div class="bd" style="padding:28px"><h2>${what}은 볼 수 없습니다</h2>
  <p>${esc(me().name)} 님은 ${me().role}입니다. 이 화면은 ${who}만 봅니다.</p><p class="hint">오른쪽 위에서 사용자를 바꿔 볼 수 있습니다. ${fid('CST-FN-RPT-01')}</p></div></div>`);
}

// ───────── 인시던트 · 처리 큐 (OP-INC-LST-R) ─────────
function elapsed(x) {                                        // INC-FN-LST-03 · INC-PL-SLA-01
  const end = x.resolved ? parse(x.resolved) : now();       // 해결 건은 해결 시각까지
  const h = hoursBetween(parse(x.opened), end), r = h / x.target_hours;
  const cls = r > 1 ? 'bad' : r >= 0.75 ? 'warn' : '';
  return {h, r, html: `<div class="elapsed" title="목표의 ${Math.round(r * 100)}%"><div class="bar"><i class="${cls}" style="width:${Math.min(100, r * 100)}%"></i></div><span>${dur(h)} / ${x.target_hours}시간</span></div>`};
}
const VIEWS = {'처리 대기': x => x.state === '신규' || x.state === '처리 중', '해결': x => x.state === '해결', '전체': () => true};  // INC-PL-STT-01
function canAct(x) {                                          // INC-PL-STS-01
  const r = role();
  if (x.state === '신규') return r === 'A' || r === 'O' ? ['담당 맡기', 'pri', ''] : ['담당 맡기', 'pri', '조회자는 담당을 맡을 수 없습니다.'];
  if (x.state === '처리 중') return r === 'A' || x.assignee === S.user ? ['해결', 'pri', ''] : ['해결', 'pri', '담당자나 관리자만 해결할 수 있습니다.'];
  if (x.state === '해결') return r === 'A' ? ['종료', '', ''] : ['종료', '', '관리자만 종료할 수 있습니다.'];
  return null;
}
const ACT_ID = {'담당 맡기': 'INC-FN-STA-01', '해결': 'INC-FN-STA-02', '종료': 'INC-FN-STA-04'};
function incidents() {
  const Q = UI.inc, all = S.incidents;
  const q = Q.q.trim().toLowerCase();
  const pass = x => (!Q.prio || x.priority === Q.prio) && (!Q.who || (Q.who === '-' ? !x.assignee : x.assignee === Q.who))
    && (!q || x.title.toLowerCase().includes(q) || (srv(x.server).name || '').toLowerCase().includes(q));
  const list = all.filter(VIEWS[Q.view]).filter(pass).sort((a, b) => b.opened.localeCompare(a.opened));
  if (!list.find(x => x.id === Q.sel)) Q.sel = list[0] ? list[0].id : null;
  const open = all.filter(VIEWS['처리 대기']);
  const risk = open.filter(x => elapsed(x).r >= 0.75).length;           // INC-PL-SLA-01: 처리 대기 가운데 75% 이상
  const mon = stamp(now()).slice(0, 7);
  const month = all.filter(x => x.resolved && x.resolved.startsWith(mon));
  const inT = month.filter(x => x.within_target).length;
  const cnt = k => all.filter(VIEWS[k]).filter(pass).length;               // TABLE-03: 보기마다 건수
  const assignees = [...new Set(all.map(x => x.assignee).filter(Boolean))].map(user).sort((a, b) => a.name.localeCompare(b.name, 'ko'));
  const x = all.find(i => i.id === Q.sel);
  const canReg = role() !== 'V';
  const body = `
  <div class="phead"><div><h1>인시던트 ${fid('OP-INC-LST-R')}</h1><p>알림이 묶여 생긴 인시던트를 담당자에게 배정하고 해결 목표 시간 안에 처리합니다.</p></div><span class="sp"></span>
    <div class="tabs" role="tablist" style="border:0"><button class="on" role="tab" aria-selected="true">처리 큐</button><button role="tab" aria-selected="false" data-go="#/incidents/stats">처리 현황</button></div>
    <span class="fidwrap"><button class="btn pri" data-act="new" ${canReg ? '' : 'disabled title="조회자는 등록할 수 없습니다"'}>인시던트 등록</button> ${fid('INC-FN-REG-01')}</span></div>
  <div class="kpis">
    <div class="card kpi"><div class="k">신규</div><div class="v">${open.filter(i => i.state === '신규').length}<small>건</small></div><div class="s">담당자 없음</div></div>
    <div class="card kpi"><div class="k">처리 중</div><div class="v">${open.filter(i => i.state === '처리 중').length}<small>건</small></div><div class="s">담당자 배정됨</div></div>
    <div class="card kpi ${risk ? 'warn' : ''}"><div class="k">목표 임박 · 초과 ${fid('INC-PL-SLA-01')}</div><div class="v">${risk}<small>건</small></div><div class="s">목표 시간의 75% 이상 지남</div></div>
    <div class="card kpi"><div class="k">${+mon.slice(5)}월 목표 내 해결</div><div class="v">${month.length ? Math.round(inT / month.length * 100) : 0}<small>%</small></div><div class="s">${month.length}건 가운데 ${inT}건</div></div>
  </div>
  <div class="split">
    <div class="card">
      <div class="hd"><div class="seg" role="tablist" aria-label="빠른 보기">${Object.keys(VIEWS).map(k => `<button role="tab" aria-selected="${k === Q.view}" class="${k === Q.view ? 'on' : ''}" data-view="${k}">${k}<em>${cnt(k)}</em></button>`).join('')}</div> ${fid('INC-FN-LST-01', 'TABLE-03')}<span class="sp"></span>
        <div class="fbar">${fid('INC-FN-LST-02', 'TABLE-02')}
          <select class="sel" data-f="prio" aria-label="우선순위"><option value="">우선순위 전체</option>${['P1', 'P2', 'P3', 'P4'].map(p => `<option ${p === Q.prio ? 'selected' : ''}>${p}</option>`).join('')}</select>
          <select class="sel" data-f="who" aria-label="담당"><option value="">담당 전체</option><option value="-" ${Q.who === '-' ? 'selected' : ''}>미배정</option>${assignees.map(u => `<option value="${u.id}" ${u.id === Q.who ? 'selected' : ''}>${esc(u.name)}</option>`).join('')}</select>
          <input class="search" data-f="q" value="${esc(Q.q)}" placeholder="제목 · 서버 이름 찾기" aria-label="찾기"></div></div>
      <div class="bd" style="padding:10px 0 0"><div class="tblwrap"><table class="tbl"><thead><tr><th>ID</th><th>제목</th><th>우선순위</th><th>상태</th><th>담당</th><th>경과 / 목표 ${fid('INC-FN-LST-03')}</th></tr></thead><tbody>
      ${list.length ? list.map(i => `<tr class="row ${i.id === Q.sel ? 'sel' : ''}" data-id="${i.id}" tabindex="0" aria-selected="${i.id === Q.sel}"><td class="mono">${i.id}</td><td><div class="ttl">${esc(i.title)}</div><div class="sub">${i.opened} 생성 · ${esc(srv(i.server).name)} · 알림 ${i.alerts.length}건</div></td><td><span class="prio ${i.priority}">${i.priority}</span></td><td><span class="bdg ${ST_CLS[i.state]}">${i.state}</span></td><td>${i.assignee ? esc(user(i.assignee).name) : '<span class="muted">미배정</span>'}</td><td>${elapsed(i).html}</td></tr>`).join('')
        : `<tr><td colspan="6" class="empty">${all.filter(VIEWS[Q.view]).length ? '조건에 맞는 인시던트가 없습니다. 필터를 바꿔 보십시오.' : '처리할 인시던트가 없습니다.'}</td></tr>`}
      </tbody></table></div><div class="pager">전체 ${list.length}건 ${fid('TABLE-01')}</div></div>
    </div>
    ${x ? incPanel(x) : '<div class="card panel"><div class="empty">목록에서 인시던트를 고르면 여기에 상세가 열립니다.</div></div>'}
  </div>`;
  return shell('인시던트', '운영 <span class="sl">/</span> <b>인시던트</b>', body);
}
function incPanel(x) {                                         // TABLE-04 · INC-FN-STA-03
  const a = canAct(x), s = srv(x.server), e = elapsed(x);
  const btn = a ? `<span class="fidwrap"><button class="btn sm ${a[1]}" data-act="state" data-id="${x.id}" ${a[2] ? `disabled title="${a[2]}"` : ''}>${a[0]}</button> ${fid(ACT_ID[a[0]])}</span>` : '';
  return `<div class="card panel" aria-label="${x.id} 상세"><div class="hd"><span class="mono muted">${x.id}</span><span class="bdg ${ST_CLS[x.state]}">${x.state}</span><span class="sp"></span>${btn}</div>
  <div class="bd">${a && a[2] ? `<p class="hint" style="margin:-6px 0 0">${a[2]}</p>` : ''}
    <div class="ttl">${esc(x.title)}</div>
    <dl class="kv"><dt>우선순위</dt><dd><span class="prio ${x.priority}">${x.priority}</span> 목표 ${x.target_hours}시간</dd>
      <dt>서버</dt><dd>${esc(s.name)} · ${esc(s.cloud)}</dd><dt>프로젝트</dt><dd>${esc(prj(x.project))}</dd>
      <dt>담당</dt><dd>${x.assignee ? esc(user(x.assignee).name) : '<span class="muted">미배정</span>'}</dd>
      <dt>경과</dt><dd>${e.html}</dd><dt>원인</dt><dd>${esc(x.cause || '—')}</dd>
      <dt>묶인 알림</dt><dd class="mono">${x.alerts.length ? x.alerts.map(esc).join(', ') : '— (직접 등록)'}</dd></dl>
    <div><h3>처리 이력 ${fid('INC-FN-STA-03')}</h3><ul class="tl" style="margin-top:10px">${x.timeline.map(t => `<li><b>${esc(t.event)}</b> · ${esc(t.by)}<span>${t.time}</span></li>`).join('')}</ul></div>
    ${x.state === '해결' || x.state === '종료' ? `<p class="note">해결 · 종료 건은 되돌릴 수 없습니다. 재발하면 새로 등록합니다. 되돌릴지는 아직 정하지 않았습니다. ${fid('INC-OQ-01')}</p>` : ''}
  </div></div>`;
}
function setState(id) {
  const x = S.incidents.find(i => i.id === id), a = canAct(x);
  if (!a || a[2]) return;
  const t = stamp(now()), by = me().name;
  if (x.state === '신규') {                                       // INC-FN-STA-01
    x.state = '처리 중'; x.assignee = S.user; x.timeline.push({time: t, event: '처리 시작', by});
    save(); toast(`${x.id} 담당을 맡았습니다. 처리 중으로 바뀌었습니다.`); render();
  } else if (x.state === '처리 중') {                             // INC-FN-STA-02: 원인을 골라 해결
    resolveDialog(x);
  } else if (x.state === '해결') {                                // INC-FN-STA-04
    x.state = '종료'; x.timeline.push({time: t, event: '종료', by});
    save(); toast(`${x.id}을 종료했습니다. 원인 통계에 들어갑니다.`); render();
  }
}
const CAUSES = () => [...new Set(D.incidents.map(i => i.cause).filter(c => c && c !== '원인 조사 중'))].sort((a, b) => a.localeCompare(b, 'ko')).concat('기타');
function dialog(title, body, okText, onOk) {
  const L = $('#layer');
  L.innerHTML = `<div class="dim"><form class="dlg" role="dialog" aria-modal="true" aria-labelledby="dlgT"><div class="hd"><h2 id="dlgT">${title}</h2></div>
    <div class="bd">${body}</div><div class="ft"><button type="button" class="btn" data-close>취소</button><button class="btn pri">${okText}</button></div></form></div>`;
  const f = L.querySelector('form'), close = () => { L.innerHTML = ''; };
  f.addEventListener('submit', e => { e.preventDefault(); if (onOk(f) !== false) close(); });
  L.querySelector('[data-close]').onclick = close;
  L.querySelector('.dim').addEventListener('mousedown', e => { if (e.target.classList.contains('dim')) close(); });
  f.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
  const first = f.querySelector('input,select'); if (first) first.focus();
}
function resolveDialog(x) {
  dialog(`${x.id} 해결`, `<p class="hint" style="margin:0">${esc(x.title)}</p>
    <label class="fld"><span>원인</span><select class="sel" name="cause" required><option value="">원인을 고르십시오</option>${CAUSES().map(c => `<option>${esc(c)}</option>`).join('')}</select><small class="hint">해결 · 종료 건의 원인은 처리 현황 통계에 들어갑니다. ${fid('INC-PL-STT-01')}</small></label>`,
  '해결로 바꾸기', f => {
    const c = f.cause.value; if (!c) { f.cause.focus(); return false; }
    const t = now(); x.state = '해결'; x.cause = c; x.resolved = stamp(t);
    x.within_target = hoursBetween(parse(x.opened), parse(x.resolved)) <= x.target_hours;
    x.timeline.push({time: x.resolved, event: '해결', by: me().name});
    save(); toast(`${x.id}을 해결했습니다. ${x.within_target ? '목표 시간 안입니다.' : '목표 시간을 넘겼습니다.'}`); render();
  });
}
function nextIncId() { return 'INC-' + String(Math.max(...S.incidents.map(i => +i.id.slice(4))) + 1).padStart(3, '0'); }
function newDialog() {                                         // INC-FN-REG-01
  const servers = [...D.servers].sort((a, b) => a.name.localeCompare(b.name));
  dialog('인시던트 등록', `
    <label class="fld"><span>제목</span><input class="search" name="title" maxlength="60" required placeholder="예: pay-01 응답 시간 3초 이상"></label>
    <div class="fld"><span>우선순위 ${fid('INC-PL-SLA-01')}</span><div class="radios">${['P1', 'P2', 'P3', 'P4'].map(p => `<label><input type="radio" name="prio" value="${p}" ${p === 'P3' ? 'checked' : ''}><span><b>${p} · 목표 ${TARGET[p]}시간</b>${PRIO_NOTE[p]}</span></label>`).join('')}</div></div>
    <label class="fld"><span>서버</span><select class="sel" name="server" required><option value="">서버를 고르십시오</option>${servers.map(s => `<option value="${s.id}">${esc(s.name)} · ${esc(s.cloud)} · ${esc(prj(s.project))}</option>`).join('')}</select></label>
    <p class="note">알림 없이 직접 만드는 인시던트입니다. 상태는 신규로 시작하고, 담당은 목록에서 맡습니다.</p>`,
  '등록', f => {
    const title = f.title.value.trim(); if (!title) { f.title.focus(); return false; }
    if (!f.server.value) { f.server.focus(); return false; }
    const s = srv(f.server.value), p = f.prio.value, t = stamp(now());
    const x = {id: nextIncId(), title, priority: p, state: '신규', server: s.id, project: s.project, assignee: null, opened: t, resolved: null,
      target_hours: TARGET[p], within_target: null, cause: null, alerts: [], timeline: [{time: t, event: '생성', by: me().name}]};
    S.incidents.push(x); UI.inc.view = '처리 대기'; UI.inc.sel = x.id; UI.inc.prio = UI.inc.who = UI.inc.q = '';
    save(); toast(`${x.id}을 등록했습니다.`); render();
  });
}

// ───────── 인시던트 · 처리 현황 (OP-INC-DSH-R) ─────────
function stats() {                                             // INC-FN-LST-05 · INC-PL-STT-01
  const days = UI.stat.days, end = now(), from = new Date(end.getTime() - days * 864e5);
  const inP = s => s && parse(s) >= from && parse(s) <= end;
  const created = S.incidents.filter(x => inP(x.opened));
  const solved = S.incidents.filter(x => inP(x.resolved));
  // 날짜별 생성 건수
  const dayKeys = []; for (let i = days - 1; i >= 0; i--) dayKeys.push(stamp(new Date(end.getTime() - i * 864e5)).slice(0, 10));
  const per = dayKeys.map(k => created.filter(x => x.opened.startsWith(k)).length);
  const mx = Math.max(2, ...per), W = 1100, H = 200, bw = (W - 40) / days, yv = v => H - v / mx * (H - 16);
  const svg = `<svg class="chart" viewBox="0 0 ${W} ${H + 24}" role="img" aria-label="날짜별 생성 건수, 최근 ${days}일">
    ${[0, Math.round(mx / 2), mx].map(v => `<line class="grid" x1="32" x2="${W}" y1="${yv(v)}" y2="${yv(v)}"/><text x="26" y="${yv(v) + 4}" text-anchor="end">${v}</text>`).join('')}
    ${per.map((v, i) => `<rect x="${36 + i * bw}" y="${yv(v)}" width="${Math.max(2, bw - 3)}" height="${H - yv(v)}" rx="2" fill="var(--c1)"><title>${dayKeys[i]} · ${v}건</title></rect>`).join('')}
    ${dayKeys.map((k, i) => i % Math.ceil(days / 7) === 0 ? `<text x="${36 + i * bw}" y="${H + 18}">${k.slice(5)}</text>` : '').join('')}</svg>`;
  const pr = ['P1', 'P2', 'P3', 'P4'].map(p => {
    const s = solved.filter(x => x.priority === p), ok = s.filter(x => x.within_target).length;
    const avg = s.length ? s.reduce((t, x) => t + hoursBetween(parse(x.opened), parse(x.resolved)), 0) / s.length : 0;
    return {p, n: s.length, ok, rate: s.length ? Math.round(ok / s.length * 100) : null, avg};
  });
  const causes = {}; S.incidents.filter(x => (x.state === '해결' || x.state === '종료') && x.cause && inP(x.resolved)).forEach(x => causes[x.cause] = (causes[x.cause] || 0) + 1);
  const top = Object.entries(causes).sort((a, b) => b[1] - a[1]).slice(0, 5), cm = Math.max(1, ...top.map(t => t[1]));
  const body = `
  <div class="phead"><div><h1>인시던트 ${fid('OP-INC-DSH-R')}</h1><p>기간 안에 생긴 건수, 우선순위별 해결과 목표 준수율, 자주 나온 원인을 봅니다.</p></div><span class="sp"></span>
    <div class="tabs" role="tablist" style="border:0"><button role="tab" aria-selected="false" data-go="#/incidents">처리 큐</button><button class="on" role="tab" aria-selected="true">처리 현황</button></div>
    <div class="seg" aria-label="기간">${[7, 30].map(d => `<button class="${d === days ? 'on' : ''}" data-days="${d}">최근 ${d}일</button>`).join('')}</div></div>
  <div class="kpis">
    <div class="card kpi"><div class="k">생성</div><div class="v">${created.length}<small>건</small></div><div class="s">최근 ${days}일</div></div>
    <div class="card kpi"><div class="k">해결</div><div class="v">${solved.length}<small>건</small></div><div class="s">기간 안에 해결된 건</div></div>
    <div class="card kpi"><div class="k">목표 내 해결 ${fid('INC-PL-STT-01')}</div><div class="v">${solved.length ? Math.round(solved.filter(x => x.within_target).length / solved.length * 100) : 0}<small>%</small></div><div class="s">${solved.length}건 가운데 ${solved.filter(x => x.within_target).length}건</div></div>
    <div class="card kpi"><div class="k">처리 대기</div><div class="v">${S.incidents.filter(VIEWS['처리 대기']).length}<small>건</small></div><div class="s">지금 기준</div></div>
  </div>
  <div class="card"><div class="hd"><h2>날짜별 생성 건수</h2></div><div class="bd">${svg}</div></div>
  <div class="cols2">
    <div class="card"><div class="hd"><h2>우선순위별 해결 ${fid('INC-PL-SLA-01')}</h2></div><div class="bd" style="padding:10px 0 0"><table class="tbl"><thead><tr><th>우선순위</th><th class="r">해결</th><th class="r">평균 해결 시간</th><th>목표 내 비율</th></tr></thead><tbody>
      ${pr.map(r => `<tr><td><span class="prio ${r.p}">${r.p}</span> <span class="muted">목표 ${TARGET[r.p]}시간</span></td><td class="r">${r.n}건</td><td class="r">${r.n ? dur(r.avg) : '-'}</td><td>${r.rate === null ? '<span class="muted">-</span>' : `<span class="meter"><i class="${r.rate < 70 ? 'warn' : ''}" style="width:${r.rate}%"></i></span> ${r.rate}%`}</td></tr>`).join('')}
    </tbody></table></div></div>
    <div class="card"><div class="hd"><h2>원인 상위 5개</h2></div><div class="bd">${top.length ? `<div class="bars">${top.map(([c, n]) => `<div class="b"><span>${esc(c)}</span><span class="t"><i style="width:${n / cm * 100}%"></i></span><span class="v">${n}건</span></div>`).join('')}</div>` : '<p class="empty">기간 안에 해결된 건이 없습니다.</p>'}
      <p class="hint">해결 · 종료 건의 원인을 셉니다.</p></div></div>
  </div>`;
  return shell('인시던트', '운영 <span class="sl">/</span> 인시던트 <span class="sl">/</span> <b>처리 현황</b>', body);
}

// ───────── 알림 (알림 묶기 규칙 시연) ─────────
const SEV_CLS = {'심각': 'bad', '경고': 'warn', '정보': 'info'};
const RULES = ['CPU 사용률 80% 이상', '메모리 사용률 90% 이상', '디스크 사용률 85% 이상', '응답 시간 3초 이상', '헬스 체크 실패'];
function alerts() {
  const list = [...S.alerts].sort((a, b) => b.time.localeCompare(a.time) || b.id.localeCompare(a.id)).slice(0, 40);
  const incOf = id => S.incidents.find(i => i.alerts.includes(id));
  const body = `
  <div class="phead"><div><h1>알림</h1><p>서버 알림입니다. 알림을 보내 보면 인시던트 묶기 규칙이 어떻게 동작하는지 볼 수 있습니다.</p></div><span class="sp"></span>
    <span class="fidwrap"><button class="btn pri" data-act="alert">예시 알림 보내기</button> ${fid('INC-FN-REG-02', 'INC-PL-GRP-01')}</span></div>
  <div class="note"><b>묶기 규칙</b> · 같은 서버에서 3시간 안에 생긴 심각 · 경고 알림을 인시던트 하나로 묶습니다. 한 인시던트에 5건까지 묶고, 6번째부터 새 인시던트를 만듭니다. 정보 등급은 묶지 않습니다.<br>
    <span class="muted">기획서에 자동 등록 인시던트의 우선순위가 정해져 있지 않아, 이 예시에서는 심각 P2 · 경고 P3 으로 둡니다.</span></div>
  <div class="card"><div class="hd"><h2>최근 알림</h2><span class="sp"></span><span class="muted" style="font-size:12.5px">전체 ${fmt(S.alerts.length)}건 가운데 최근 40건</span></div>
    <div class="bd" style="padding:10px 0 0"><div class="tblwrap"><table class="tbl"><thead><tr><th>ID</th><th>시각</th><th>서버</th><th>규칙</th><th>등급</th><th>인시던트</th></tr></thead><tbody>
    ${list.map(a => { const i = incOf(a.id); return `<tr><td class="mono">${a.id}</td><td class="num">${a.time}</td><td>${esc(srv(a.server).name)}</td><td>${esc(a.rule)}</td><td><span class="bdg ${SEV_CLS[a.severity]}">${a.severity}</span></td><td>${i ? `<a href="#/incidents" data-open="${i.id}" class="mono">${i.id}</a>` : '<span class="muted">—</span>'}</td></tr>`; }).join('')}
    </tbody></table></div></div></div>`;
  return shell('알림', '운영 <span class="sl">/</span> <b>알림</b>', body);
}
function alertDialog() {
  const servers = [...D.servers].filter(s => s.status !== '중지').sort((a, b) => a.name.localeCompare(b.name));
  const last = UI.alert;
  dialog('예시 알림 보내기', `
    <label class="fld"><span>서버</span><select class="sel" name="server">${servers.map(s => `<option value="${s.id}" ${s.id === last.server ? 'selected' : ''}>${esc(s.name)} · ${esc(s.cloud)}</option>`).join('')}</select></label>
    <label class="fld"><span>규칙</span><select class="sel" name="rule">${RULES.map(r => `<option ${r === last.rule ? 'selected' : ''}>${r}</option>`).join('')}</select></label>
    <div class="fld"><span>등급</span><div class="radios">${['심각', '경고', '정보'].map(v => `<label><input type="radio" name="sev" value="${v}" ${v === (last.sev || '경고') ? 'checked' : ''}><span><b>${v}</b>${v === '정보' ? '인시던트로 묶지 않습니다' : '묶기 대상'}</span></label>`).join('')}</div></div>
    <p class="hint">같은 서버로 여러 번 보내 보면 5건까지 한 인시던트에 묶이고, 6번째에 새 인시던트가 생깁니다.</p>`,
  '보내기', f => {
    const sv = srv(f.server.value), sev = f.sev.value, t = now(), ts = stamp(t);
    UI.alert = {server: sv.id, rule: f.rule.value, sev};
    const id = 'AL-' + String(Math.max(...S.alerts.map(a => +a.id.slice(3))) + 1).padStart(4, '0');
    S.alerts.push({id, time: ts, server: sv.id, project: sv.project, rule: f.rule.value, severity: sev, acknowledged: false});
    if (sev === '정보') { save(); toast(`${id}을 받았습니다. 정보 등급이라 인시던트로 묶지 않았습니다.`); render(); return; }
    // INC-PL-GRP-01: 같은 서버 · 3시간 안 · 처리 대기 인시던트 · 묶인 알림 5건 미만
    const since = new Date(t.getTime() - 3 * 36e5);
    const host = S.incidents.filter(i => i.server === sv.id && VIEWS['처리 대기'](i) && i.alerts.length < 5 && parse(i.opened) >= since)
      .sort((a, b) => b.opened.localeCompare(a.opened))[0];
    if (host) {
      host.alerts.push(id); host.timeline.push({time: ts, event: `알림 묶음 (${host.alerts.length}/5)`, by: '시스템'});
      save(); toast(`${id}을 ${host.id}에 묶었습니다. 묶인 알림 ${host.alerts.length}/5건입니다.`);
    } else {
      const p = sev === '심각' ? 'P2' : 'P3';
      const full = S.incidents.some(i => i.server === sv.id && VIEWS['처리 대기'](i) && i.alerts.length >= 5 && parse(i.opened) >= since);
      const x = {id: nextIncId(), title: `${sv.name} ${f.rule.value}`, priority: p, state: '신규', server: sv.id, project: sv.project, assignee: null, opened: ts, resolved: null,
        target_hours: TARGET[p], within_target: null, cause: null, alerts: [id], timeline: [{time: ts, event: '생성', by: '시스템'}]};
      S.incidents.push(x); save();
      toast(`${id}으로 ${x.id}을 새로 만들었습니다${full ? '. 앞 인시던트에 알림이 5건 묶여 있어서입니다.' : '.'}`);
    }
    render();
  });
}

// ───────── 서버 목록 (IN-SRV-LST-R) ─────────
const metricsOf = id => D.metrics_daily.filter(m => m.server === id).sort((a, b) => a.date.localeCompare(b.date));
const avg30 = id => { const m = metricsOf(id).slice(-30); return m.length ? Math.round(m.reduce((t, x) => t + x.cpu_avg, 0) / m.length) : null; };  // SRV-PL-MET-01
const useCls = v => v >= 80 ? 'bad' : v >= 60 ? 'warn' : '';
function spark(id, w = 90, h = 24) {
  const m = metricsOf(id).slice(-30); if (m.length < 2) return '<span class="muted">-</span>';
  // 중지된 서버는 중지한 날까지만 그린다: 있는 날만 잇고 빈 날을 0으로 채우지 않는다
  const pts = m.map((x, i) => `${(i / 29 * w).toFixed(1)},${(h - x.cpu_avg / 100 * h).toFixed(1)}`).join(' ');
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="var(--acc)" stroke-width="1.5"/></svg>`;
}
function servers() {
  const Q = UI.srv, q = Q.q.trim().toLowerCase();
  const CL = {'전체': () => true, 'AWS': s => s.cloud === 'AWS', 'Azure': s => s.cloud === 'Azure', '사내 서버': s => s.cloud === '사내 서버'};
  const pass = s => (!Q.st || s.status === Q.st) && (!Q.prj || s.project === Q.prj) && (!q || s.name.toLowerCase().includes(q) || s.ip.includes(q));
  const list = D.servers.filter(CL[Q.view]).filter(pass).sort((a, b) => (avg30(b.id) ?? -1) - (avg30(a.id) ?? -1));
  if (!list.find(s => s.id === Q.sel)) Q.sel = list[0] ? list[0].id : null;
  const s = D.servers.find(x => x.id === Q.sel);
  const run = D.servers.filter(x => x.status === '실행 중'), hi = run.filter(x => avg30(x.id) >= 80).length;
  const body = `
  <div class="phead"><div><h1>서버 ${fid('IN-SRV-LST-R')}</h1><p>AWS · Azure · 사내 서버를 한 목록으로 보고, 사용률이 높은 서버를 찾아 30일 추이와 최근 알림을 확인합니다.</p></div></div>
  <div class="kpis">
    <div class="card kpi"><div class="k">서버</div><div class="v">${D.servers.length}<small>대</small></div><div class="s">실행 중 ${run.length}대</div></div>
    <div class="card kpi ${hi ? 'bad' : ''}"><div class="k">CPU 80% 이상</div><div class="v">${hi}<small>대</small></div><div class="s">30일 평균, 실행 중 서버</div></div>
    <div class="card kpi"><div class="k">오류</div><div class="v">${D.servers.filter(x => x.status === '오류').length}<small>대</small></div><div class="s">상태가 오류인 서버</div></div>
    <div class="card kpi"><div class="k">중지</div><div class="v">${D.servers.filter(x => x.status === '중지').length}<small>대</small></div><div class="s">추이는 중지한 날까지</div></div>
  </div>
  <div class="split">
    <div class="card"><div class="hd"><div class="seg" aria-label="클라우드 빠른 보기">${Object.keys(CL).map(k => `<button class="${k === Q.view ? 'on' : ''}" data-sview="${k}">${k}<em>${D.servers.filter(CL[k]).filter(pass).length}</em></button>`).join('')}</div> ${fid('SRV-FN-LST-01', 'TABLE-03')}<span class="sp"></span>
      <div class="fbar">${fid('SRV-FN-LST-02')}
        <select class="sel" data-sf="st" aria-label="상태"><option value="">상태 전체</option>${['실행 중', '중지', '오류'].map(v => `<option ${v === Q.st ? 'selected' : ''}>${v}</option>`).join('')}</select>
        <select class="sel" data-sf="prj" aria-label="프로젝트"><option value="">프로젝트 전체</option>${D.projects.map(p => `<option value="${p.id}" ${p.id === Q.prj ? 'selected' : ''}>${esc(p.name)}</option>`).join('')}</select>
        <input class="search" data-sf="q" value="${esc(Q.q)}" placeholder="이름 · IP 찾기" aria-label="찾기"></div></div>
    <div class="bd" style="padding:10px 0 0"><div class="tblwrap"><table class="tbl"><thead><tr><th>이름</th><th>클라우드</th><th>프로젝트</th><th>상태</th><th>CPU 30일 평균 ${fid('SRV-FN-LST-03', 'SRV-PL-MET-01')}</th><th>30일 추이</th></tr></thead><tbody>
    ${list.length ? list.map(x => { const v = avg30(x.id); return `<tr class="row ${x.id === Q.sel ? 'sel' : ''}" data-sid="${x.id}" tabindex="0"><td><div class="ttl">${esc(x.name)}</div><div class="sub mono">${x.ip}</div></td><td>${esc(x.cloud)}</td><td>${esc(prj(x.project))}</td><td><span class="bdg ${SRV_CLS[x.status]}">${x.status}</span></td><td class="num">${v === null ? '-' : `<span class="meter"><i class="${useCls(v)}" style="width:${v}%"></i></span> ${v}%`}</td><td>${spark(x.id)}</td></tr>`; }).join('')
      : '<tr><td colspan="6" class="empty">조건에 맞는 서버가 없습니다.</td></tr>'}
    </tbody></table></div><div class="pager">전체 ${list.length}대 ${fid('TABLE-01')}</div></div></div>
    ${s ? srvPanel(s) : ''}
  </div>`;
  return shell('서버', '인프라 <span class="sl">/</span> <b>서버</b>', body);
}
function srvPanel(s) {                                         // SRV-FN-DTL-01 · 02
  const m = metricsOf(s.id).slice(-30), W = 300, H = 120;
  const x = i => (i / 29 * (W - 30) + 26).toFixed(1), y = v => (H - v / 100 * (H - 8)).toFixed(1);
  const line = k => m.map((d, i) => `${x(i)},${y(d[k])}`).join(' ');
  const chart = m.length > 1 ? `<svg class="chart" viewBox="0 0 ${W} ${H + 18}" role="img" aria-label="CPU 30일 일 평균 · 일 최대">
    ${[0, 50, 100].map(v => `<line class="grid" x1="26" x2="${W}" y1="${y(v)}" y2="${y(v)}"/><text x="20" y="${+y(v) + 4}" text-anchor="end">${v}</text>`).join('')}
    <line class="ref" x1="26" x2="${W}" y1="${y(80)}" y2="${y(80)}"/>
    <polyline points="${line('cpu_max')}" fill="none" stroke="var(--c3)" stroke-width="1.2" opacity=".8"/>
    <polyline points="${line('cpu_avg')}" fill="none" stroke="var(--acc)" stroke-width="2"/>
    <text x="26" y="${H + 14}">${m[0].date.slice(5)}</text><text x="${W}" y="${H + 14}" text-anchor="end">${m[m.length - 1].date.slice(5)}</text></svg>
    <div class="legend"><span><i style="background:var(--acc)"></i>일 평균</span><span><i style="background:var(--c3)"></i>일 최대</span><span><i style="background:var(--bad)"></i>80% 기준</span></div>` : '<p class="muted">사용률 기록이 없습니다.</p>';
  const al = S.alerts.filter(a => a.server === s.id).sort((a, b) => b.time.localeCompare(a.time)).slice(0, 5);
  return `<div class="card panel" aria-label="${esc(s.name)} 상세"><div class="hd"><b>${esc(s.name)}</b><span class="bdg ${SRV_CLS[s.status]}">${s.status}</span><span class="sp"></span>${fid('SRV-FN-DTL-01')}</div>
  <div class="bd"><dl class="kv"><dt>클라우드</dt><dd>${esc(s.cloud)} · ${esc(s.region)}</dd><dt>프로젝트</dt><dd>${esc(prj(s.project))}</dd>
    <dt>사양</dt><dd>vCPU ${s.vcpu} · 메모리 ${s.memory_gb}GB</dd><dt>OS</dt><dd>${esc(s.os)}</dd><dt>IP</dt><dd class="mono">${s.ip}</dd><dt>생성일</dt><dd>${s.created}</dd></dl>
    <div><h3>CPU 30일</h3>${chart}</div>
    <div><h3>최근 알림 ${fid('SRV-FN-DTL-02')}</h3>${al.length ? `<ul class="tl" style="margin-top:10px">${al.map(a => `<li><b>${esc(a.rule)}</b> <span class="bdg ${SEV_CLS[a.severity]}" style="height:18px;font-size:11px">${a.severity}</span><span>${a.time}</span></li>`).join('')}</ul>` : '<p class="muted" style="font-size:13px">최근 알림이 없습니다.</p>'}</div>
  </div></div>`;
}

// ───────── 월별 비용 (CO-CST-RPT-R) ─────────
const CLOUDS = ['AWS', 'Azure', '사내 서버'], CCOL = {'AWS': 'var(--c1)', 'Azure': 'var(--c2)', '사내 서버': 'var(--c3)'};
const cost = r => r.compute + r.storage + r.network;               // CST-PL-AMT-01: 부가세 별도
const man = n => fmt(Math.round(n / 1e4)) + '만 원';
function costs() {
  if (role() === 'O') return denied('월별 비용', '비용 <span class="sl">/</span> <b>월별 비용</b>', '월별 비용', '관리자 · 조회자');   // 권한 A, V
  const months = [...new Set(D.costs_monthly.map(c => c.month))].sort().reverse().slice(0, 6);   // TIME-04: 최근 달이 위
  if (!months.includes(UI.cost.month)) UI.cost.month = months[0];
  const M = UI.cost.month, prev = months[months.indexOf(M) + 1] || null;
  const sum = (m, f = () => true) => D.costs_monthly.filter(c => c.month === m && f(c)).reduce((t, c) => t + cost(c), 0);
  const delta = (a, b) => b ? Math.round((a - b) / b * 1000) / 10 : null;
  const dl = v => v === null ? '<span class="muted">-</span>' : `<span class="delta ${v > 0 ? 'up' : v < 0 ? 'down' : ''}">${v > 0 ? '▲' : v < 0 ? '▼' : ''} ${Math.abs(v).toFixed(1)}%</span>`;
  const tot = sum(M), ptot = prev ? sum(prev) : null, cur = M === months[0];
  // 최근 6개월 클라우드별 쌓은 막대
  const asc = [...months].reverse(), mx = Math.max(...asc.map(m => sum(m))) * 1.08, W = 620, H = 300, bw = (W - 60) / asc.length;
  const bars = `<svg class="chart" viewBox="0 0 ${W} ${H + 26}" role="img" aria-label="최근 6개월 클라우드별 비용">
    ${asc.map((m, i) => { let yy = H; return CLOUDS.map(c => { const v = sum(m, r => r.cloud === c), h = v / mx * (H - 16); yy -= h;
      return `<rect x="${50 + i * bw + 8}" y="${yy}" width="${bw - 16}" height="${h}" fill="${CCOL[c]}" opacity="${m === M ? 1 : .45}"><title>${m} ${c} ${man(v)}</title></rect>`; }).join('')
      + `<text x="${50 + i * bw + bw / 2}" y="${H - sum(m) / mx * (H - 16) - 6}" text-anchor="middle" style="${m === M ? 'font-weight:600;fill:var(--ink)' : ''}">${fmt(Math.round(sum(m) / 1e4))}</text>`
      + `<text x="${50 + i * bw + bw / 2}" y="${H + 18}" text-anchor="middle" style="${m === M ? 'font-weight:600;fill:var(--ink)' : ''}">${m}</text>`; }).join('')}
    <text x="44" y="${H}" text-anchor="end">만 원</text><line class="grid" x1="48" x2="${W}" y1="${H}" y2="${H}"/></svg>`;
  const rows = D.projects.map(p => ({p, v: sum(M, r => r.project === p.id), pv: prev ? sum(prev, r => r.project === p.id) : null}))
    .filter(r => r.v || r.pv).sort((a, b) => b.v - a.v);
  const body = `
  <div class="phead"><div><h1>월별 비용 ${fid('CO-CST-RPT-R')}</h1><p>한 달 비용을 클라우드와 프로젝트로 나눠 보고, 전월보다 늘어난 곳을 찾습니다. 금액은 부가세 별도입니다.</p></div><span class="sp"></span>
    <label class="fidwrap">${fid('CST-FN-RPT-01', 'TIME-04')} <select class="sel" data-act="month" aria-label="월 선택">${months.map(m => `<option ${m === M ? 'selected' : ''}>${m}</option>`).join('')}</select></label></div>
  <div class="kpis">
    <div class="card kpi"><div class="k">${M} 비용 ${fid('CST-PL-AMT-01')}</div><div class="v">${man(tot).replace(' 원', '')}<small>원</small></div><div class="s">${cur ? '어제까지 쓴 비용' : '한 달 전체'}</div></div>
    <div class="card kpi"><div class="k">전월 대비</div><div class="v">${dl(delta(tot, ptot))}</div><div class="s">${prev ? `${prev} ${man(ptot)}` : '전월 자료 없음'}${cur ? ` ${fid('CST-OQ-01')}` : ''}</div></div>
    ${CLOUDS.slice(0, 2).map(c => `<div class="card kpi"><div class="k">${c}</div><div class="v">${man(sum(M, r => r.cloud === c)).replace(' 원', '')}<small>원</small></div><div class="s">${dl(delta(sum(M, r => r.cloud === c), prev ? sum(prev, r => r.cloud === c) : null))}</div></div>`).join('')}
  </div>
  ${cur ? `<p class="note">이번 달은 어제까지 쓴 비용을 전월 한 달 전체와 견줍니다. 같은 날짜까지끼리 견줄지는 재무팀과 정하고 있습니다. ${fid('CST-OQ-01')}</p>` : ''}
  <div class="cols2">
    <div class="card"><div class="hd"><h2>최근 6개월 ${fid('CST-FN-RPT-02')}</h2><span class="sp"></span><div class="legend">${CLOUDS.map(c => `<span><i style="background:${CCOL[c]}"></i>${c}</span>`).join('')}</div></div><div class="bd">${bars}</div></div>
    <div class="card"><div class="hd"><h2>프로젝트별 비용 ${fid('CST-FN-RPT-03')}</h2></div><div class="bd" style="padding:10px 0 0"><table class="tbl"><thead><tr><th>프로젝트</th><th class="r">${M}</th><th class="r">전월 대비</th></tr></thead><tbody>
      ${rows.map(r => `<tr><td>${esc(r.p.name)}</td><td class="r num">${man(r.v)}</td><td class="r num">${dl(delta(r.v, r.pv))}</td></tr>`).join('')}
    </tbody></table><div class="pager">전체 ${rows.length}개</div></div></div>
  </div>`;
  return shell('월별 비용', '비용 <span class="sl">/</span> <b>월별 비용</b>', body);
}

// ───────── 길 · 그리기 · 이벤트 ─────────
const ROUTES = {'#/incidents': incidents, '#/incidents/stats': stats, '#/alerts': alerts, '#/servers': servers, '#/costs': costs};
function render() {
  const r = ROUTES[location.hash] || incidents;
  const focusF = document.activeElement && document.activeElement.dataset ? (document.activeElement.dataset.f || document.activeElement.dataset.sf) : null;
  const pos = focusF ? document.activeElement.selectionStart : 0;
  $('#root').innerHTML = r();
  if (focusF) { const el = document.querySelector(`[data-f="${focusF}"],[data-sf="${focusF}"]`); if (el) { el.focus(); try { el.setSelectionRange(pos, pos); } catch (e) { /* select */ } } }
}
function bind() {
  const root = $('#root');
  root.addEventListener('click', e => {
    const t = e.target.closest('[data-act],[data-view],[data-sview],[data-days],[data-go],[data-open],tr[data-id],tr[data-sid]');
    if (!t) return;
    if (t.dataset.go) { location.hash = t.dataset.go; return; }
    if (t.dataset.open) { UI.inc.view = '전체'; UI.inc.sel = t.dataset.open; UI.inc.prio = UI.inc.who = UI.inc.q = ''; if (location.hash === '#/incidents') render(); return; }
    if (t.dataset.view) { UI.inc.view = t.dataset.view; render(); return; }
    if (t.dataset.sview) { UI.srv.view = t.dataset.sview; render(); return; }
    if (t.dataset.days) { UI.stat.days = +t.dataset.days; render(); return; }
    if (t.dataset.id && t.tagName === 'TR') { UI.inc.sel = t.dataset.id; render(); return; }
    if (t.dataset.sid) { UI.srv.sel = t.dataset.sid; render(); return; }
    const a = t.dataset.act;
    if (a === 'ids') { S.ids = !S.ids; save(); render(); }
    else if (a === 'reset') { S = fresh(); save(); Object.assign(UI.inc, {view: '처리 대기', sel: null, prio: '', who: '', q: ''}); toast('예시 데이터를 처음 상태로 되돌렸습니다.'); render(); }
    else if (a === 'new') newDialog();
    else if (a === 'state') setState(t.dataset.id);
    else if (a === 'alert') alertDialog();
  });
  root.addEventListener('keydown', e => {
    const tr = e.target.closest('tr[data-id],tr[data-sid]');
    if (tr && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); tr.click(); }
  });
  root.addEventListener('change', e => {
    const t = e.target;
    if (t.dataset.act === 'user') { S.user = t.value; save(); toast(`${me().name} · ${me().role}로 바꿨습니다.`); render(); }
    else if (t.dataset.act === 'month') { UI.cost.month = t.value; render(); }
    else if (t.dataset.f && t.tagName === 'SELECT') { UI.inc[t.dataset.f] = t.value; render(); }
    else if (t.dataset.sf && t.tagName === 'SELECT') { UI.srv[t.dataset.sf] = t.value; render(); }
  });
  root.addEventListener('input', e => {
    const t = e.target;
    if (t.dataset.f === 'q') { UI.inc.q = t.value; render(); }
    else if (t.dataset.sf === 'q') { UI.srv.q = t.value; render(); }
  });
  window.addEventListener('hashchange', () => { render(); window.scrollTo(0, 0); });
  // 경과 막대 · 시계는 1분마다 다시 그린다(창이 열려 있지 않을 때는 그리지 않는다)
  setInterval(() => { if (!$('#layer').innerHTML && !document.hidden) render(); }, 60000);
}
fetch('data.json').then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(d => {
  D = d; S = load(); if (!user(S.user)) S.user = 'U01';
  if (!location.hash) history.replaceState(null, '', '#/incidents');
  bind(); render();
}).catch(() => { $('#root').innerHTML = '<p class="empty">예시 데이터를 불러오지 못했습니다. 잠시 뒤 새로 고침해 주십시오.</p>'; });
