// 인시던트 처리 큐 · 화면 2개: 처리 큐(목록 + 상세 패널), 처리 현황 통계
const ST = {'신규': 'info', '처리 중': 'warn', '해결': 'ok', '종료': 'mute'};
const srv = id => DATA.servers.find(s => s.id === id) || {};
const hrs = (a, b) => (b - a) / 36e5;
const dt = s => new Date(s.replace(' ', 'T'));
function elapsed(x) {
  const end = x.resolved ? dt(x.resolved) : NOW, h = hrs(dt(x.opened), end), r = h / x.target_hours;
  const cls = r > 1 ? 'bad' : r > 0.75 ? 'warn' : '';
  const t = h < 1 ? Math.round(h * 60) + '분' : h < 48 ? h.toFixed(1) + '시간' : Math.round(h / 24) + '일';
  return {h, r, html: `<div class="elapsed"><div class="bar"><i class="${cls}" style="width:${Math.min(100, r * 100)}%"></i></div><span>${t} / ${x.target_hours}시간</span></div>`};
}
let Q = {view: '처리 대기', sel: null};
const VIEWS = {'처리 대기': x => x.state === '신규' || x.state === '처리 중', '해결': x => x.state === '해결', '전체': () => true};
function queue() {
  const list = DATA.incidents.filter(VIEWS[Q.view]).sort((a, b) => b.opened.localeCompare(a.opened));
  if (Q.sel === null || !list.find(x => x.id === Q.sel)) Q.sel = list[0] && list[0].id;
  const open = DATA.incidents.filter(VIEWS['처리 대기']);
  const risk = open.filter(x => elapsed(x).r > 0.75).length;
  const month = DATA.incidents.filter(x => x.resolved && x.resolved >= '2026-11-01');
  const inT = month.filter(x => x.within_target).length;
  const cnt = k => DATA.incidents.filter(VIEWS[k]).length;
  const x = DATA.incidents.find(i => i.id === Q.sel);
  return app('인시던트', '운영 › <b>인시던트</b>', `
  <div class="phead"><div><h1>인시던트</h1><p>알림이 묶여 생긴 인시던트를 담당자에게 배정하고 해결 목표 시간 안에 처리합니다.</p></div><span class="sp"></span><button class="btn pri" data-spot="1">인시던트 등록</button></div>
  <div class="kpis" data-spot="2">
    <div class="card kpi"><div class="k">신규</div><div class="v">${open.filter(i => i.state === '신규').length}<small>건</small></div><div class="s">담당자 없음</div></div>
    <div class="card kpi"><div class="k">처리 중</div><div class="v">${open.filter(i => i.state === '처리 중').length}<small>건</small></div><div class="s">담당자 배정됨</div></div>
    <div class="card kpi ${risk ? 'warn' : ''}"><div class="k">목표 임박 · 초과</div><div class="v">${risk}<small>건</small></div><div class="s">목표 시간의 75% 이상 지남</div></div>
    <div class="card kpi"><div class="k">11월 목표 내 해결</div><div class="v">${month.length ? Math.round(inT / month.length * 100) : 0}<small>%</small></div><div class="s">${month.length}건 가운데 ${inT}건</div></div>
  </div>
  <div class="split">
    <div class="card">
      <div class="hd"><div class="seg" data-spot="3">${Object.keys(VIEWS).map(k => `<button class="${k === Q.view ? 'on' : ''}" data-view="${k}">${k}<em>${cnt(k)}</em></button>`).join('')}</div><span class="sp"></span>
        <div class="fbar" data-spot="4"><select class="sel"><option>우선순위 전체</option></select><select class="sel"><option>담당 전체</option></select><input class="search" placeholder="제목 · 서버 이름 찾기"></div></div>
      <div class="bd" style="padding:10px 0 0"><div class="tblwrap"><table class="tbl" data-spot="5"><thead><tr><th>ID</th><th>제목</th><th>우선순위</th><th>상태</th><th>담당</th><th>경과 / 목표</th></tr></thead><tbody>
      ${list.length ? list.map(i => `<tr class="row ${i.id === Q.sel ? 'sel' : ''}" data-id="${i.id}"><td class="mono">${i.id}</td><td><div class="ttl">${esc(i.title)}</div><div class="sub">${esc(i.opened)} 생성 · 알림 ${i.alerts.length}건</div></td><td><span class="prio ${i.priority}">${i.priority}</span></td><td><span class="bdg ${ST[i.state]}">${i.state}</span></td><td>${i.assignee ? user(i.assignee) : '<span class="muted">미배정</span>'}</td><td>${elapsed(i).html}</td></tr>`).join('')
        : '<tr><td colspan="6" class="empty">처리할 인시던트가 없습니다.</td></tr>'}
      </tbody></table></div><div class="pager">${list.length}건</div></div>
    </div>
    ${x ? `<div class="card panel" data-spot="6"><div class="hd"><span class="mono muted">${x.id}</span><span class="bdg ${ST[x.state]}">${x.state}</span><span class="sp"></span>${x.state === '신규' ? '<button class="btn sm pri">담당 맡기</button>' : x.state === '처리 중' ? '<button class="btn sm pri">해결</button>' : x.state === '해결' ? '<button class="btn sm">종료</button>' : ''}</div>
      <div class="bd"><h2 style="font-size:16px;margin-bottom:12px">${esc(x.title)}</h2>
      <dl class="kv"><dt>우선순위</dt><dd><span class="prio ${x.priority}">${x.priority}</span> 목표 ${x.target_hours}시간</dd><dt>서버</dt><dd>${esc(srv(x.server).name)} · ${esc(srv(x.server).cloud)}</dd><dt>담당</dt><dd>${x.assignee ? user(x.assignee) : '미배정'}</dd><dt>경과</dt><dd>${elapsed(x).html}</dd><dt>원인</dt><dd>${esc(x.cause || '—')}</dd><dt>묶인 알림</dt><dd class="mono">${x.alerts.join(', ')}</dd></dl>
      <h3 style="font-size:13px;margin:16px 0 8px" data-spot="7">처리 이력</h3><ul class="tl">${x.timeline.slice().reverse().map(t => `<li><b>${esc(t.event)}</b> · ${esc(t.by)}<span>${esc(t.time)}</span></li>`).join('')}</ul></div></div>` : ''}
  </div>`);
}
function stats() {
  const days = [...Array(30)].map((_, i) => { const d = new Date(NOW); d.setDate(d.getDate() - 29 + i); return d.toISOString().slice(0, 10); });
  const by = days.map(d => DATA.incidents.filter(x => x.opened.slice(0, 10) === d));
  const mx = Math.max(...by.map(b => b.length), 1), W = 1100, H = 180, bw = W / 30;
  const bars = by.map((b, i) => ['P1', 'P2', 'P3', 'P4'].reduce((acc, p) => {
    const n = b.filter(x => x.priority === p).length, h = n / mx * (H - 20);
    acc.s += n ? `<rect x="${i * bw + 4}" y="${H - acc.y - h}" width="${bw - 8}" height="${h}" fill="var(--${p.toLowerCase()})" rx="2"/>` : ''; acc.y += h; return acc;
  }, {s: '', y: 0}).s).join('');
  const lbl = days.map((d, i) => i % 5 === 0 ? `<text x="${i * bw + bw / 2}" y="${H + 14}" font-size="11" text-anchor="middle" fill="var(--ink-3)">${d.slice(5)}</text>` : '').join('');
  const done = DATA.incidents.filter(x => x.resolved);
  const rows = ['P1', 'P2', 'P3', 'P4'].map(p => { const a = done.filter(x => x.priority === p), ok = a.filter(x => x.within_target).length;
    const avg = a.length ? a.reduce((s, x) => s + hrs(dt(x.opened), dt(x.resolved)), 0) / a.length : 0;
    return `<tr><td><span class="prio ${p}">${p}</span></td><td class="r num">${a.length}</td><td class="r num">${avg.toFixed(1)}시간</td><td class="r num">${a.length ? Math.round(ok / a.length * 100) : 0}%</td><td><span class="meter"><i class="${ok / (a.length || 1) < .7 ? 'warn' : ''}" style="width:${a.length ? ok / a.length * 100 : 0}%"></i></span></td></tr>`; }).join('');
  const causes = {}; done.forEach(x => causes[x.cause] = (causes[x.cause] || 0) + 1);
  const top = Object.entries(causes).sort((a, b) => b[1] - a[1]).slice(0, 5);
  return app('인시던트', '운영 › 인시던트 › <b>처리 현황</b>', `
  <div class="phead"><div><h1>처리 현황</h1><p>최근 30일 동안 생긴 인시던트와 해결 목표 시간을 지킨 비율입니다.</p></div><span class="sp"></span><div class="seg" data-spot="1"><button>7일</button><button class="on">30일</button><button>90일</button></div></div>
  <div class="card" data-spot="2"><div class="hd"><h2>날짜별 생성 건수</h2><span class="sp"></span><div class="legend">${['P1', 'P2', 'P3', 'P4'].map(p => `<span><i style="background:var(--${p.toLowerCase()})"></i>${p}</span>`).join('')}</div></div>
    <div class="bd"><svg class="chart" viewBox="0 0 ${W} ${H + 20}">${bars}${lbl}<line x1="0" x2="${W}" y1="${H}" y2="${H}" stroke="var(--line)"/></svg></div></div>
  <div class="split" style="grid-template-columns:1fr 1fr">
    <div class="card" data-spot="3"><div class="hd"><h2>우선순위별 해결</h2></div><div class="bd" style="padding:10px 0 0"><table class="tbl"><thead><tr><th>우선순위</th><th class="r">해결</th><th class="r">평균 해결 시간</th><th class="r">목표 내</th><th></th></tr></thead><tbody>${rows}</tbody></table></div></div>
    <div class="card" data-spot="4"><div class="hd"><h2>원인 상위 5개</h2></div><div class="bd">${top.map(([c, n]) => `<div style="display:flex;align-items:center;gap:10px;padding:6px 0"><span style="flex:1">${esc(c)}</span><span class="meter" style="width:140px"><i style="width:${n / top[0][1] * 100}%"></i></span><span class="num" style="width:36px;text-align:right">${n}건</span></div>`).join('')}</div></div>
  </div>`);
}
const SCREENS = [
  {name: '처리 큐', id: 'OP-INC-LST-R', purpose: '처리할 인시던트를 우선순위와 경과 시간 순으로 보고, 담당을 맡거나 해결로 넘긴다.', html: queue,
   bind() { document.querySelectorAll('[data-view]').forEach(b => b.onclick = () => { Q.view = b.dataset.view; Q.sel = null; render(); });
            document.querySelectorAll('tr.row').forEach(r => r.onclick = () => { Q.sel = r.dataset.id; render(); }); },
   spots: [
    ['인시던트 등록', ['알림 없이 직접 인시던트를 만듭니다.', '관리자 · 운영자에게만 보입니다.'], 'INC-FN-REG-01'],
    ['숫자 칸', ['신규 · 처리 중은 지금 건수입니다.', '목표 임박 · 초과: 경과 시간이 목표 시간의 75% 이상인 처리 대기 건입니다.', '목표 내 해결: 이번 달 해결된 건 가운데 목표 시간 안에 해결된 비율입니다.'], 'INC-PL-SLA-01'],
    ['빠른 보기', ['처리 대기: 신규 · 처리 중', '해결: 해결했으나 종료 전', '전체: 모든 상태', '처음 열면 처리 대기입니다.'], 'INC-FN-LST-01'],
    ['필터 · 찾기', ['우선순위 · 담당으로 거릅니다.', '제목과 서버 이름 일부로 찾습니다.'], 'INC-FN-LST-02'],
    ['목록', ['최근 생성 순으로 정렬합니다.', '경과 / 목표: 생성부터 지금(해결 건은 해결 시각)까지 시간을 목표 시간과 견줍니다.', '막대 색: 75% 미만 초록 · 75% 이상 주황 · 100% 초과 빨강', '행을 누르면 오른쪽 패널에 상세가 열립니다.'], 'INC-PL-STT-01'],
    ['상세 패널', ['상태에 따라 버튼 하나만 보입니다.', '신규: 담당 맡기 · 처리 중: 해결 · 해결: 종료', '종료 건은 버튼이 없습니다.'], 'INC-PL-STS-01'],
    ['처리 이력', ['최근 순으로 보입니다.', '생성은 시스템, 나머지는 행동한 사람 이름을 적습니다.'], 'INC-FN-STA-03'],
   ]},
  {name: '처리 현황', id: 'OP-INC-DSH-R', purpose: '기간 안에 생긴 인시던트 수와 목표 시간 준수율을 우선순위별로 본다.', html: stats,
   spots: [
    ['기간', ['7일 · 30일 · 90일 가운데 고릅니다.', '처음 열면 30일입니다.'], 'INC-FN-LST-05'],
    ['날짜별 생성 건수', ['막대 하나가 하루입니다.', '우선순위별로 쌓습니다.'], 'INC-PL-STT-01'],
    ['우선순위별 해결', ['해결 · 종료된 건만 셉니다.', '평균 해결 시간: 생성부터 해결까지', '목표 내 비율이 70% 미만이면 막대를 주황으로 표시합니다.'], 'INC-PL-SLA-01'],
    ['원인 상위 5개', ['해결할 때 고른 원인을 셉니다.'], 'INC-FN-STA-04'],
   ]},
];
