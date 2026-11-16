// 서버 목록 · 화면 1개: 목록 + 상세 패널
const SST = {'실행 중': 'ok', '중지': 'mute', '오류': 'bad'};
let S = {cloud: '전체', sel: null};
const avg = id => { const m = DATA.metrics.filter(x => x.server === id); return m.length ? m.reduce((s, x) => s + x.cpu_avg, 0) / m.length : 0; };
function spark(id, w = 90, h = 24) {
  const m = DATA.metrics.filter(x => x.server === id).map(x => x.cpu_avg);
  if (!m.length) return '<span class="muted">—</span>';
  const pts = m.map((v, i) => `${(i / (m.length - 1) * w).toFixed(1)},${(h - v / 100 * h).toFixed(1)}`).join(' ');
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts}" fill="none" stroke="var(--acc)" stroke-width="1.5"/></svg>`;
}
function cpuChart(id) {
  const m = DATA.metrics.filter(x => x.server === id), W = 320, H = 110;
  if (!m.length) return '';
  const p = k => m.map((x, i) => `${(i / (m.length - 1) * W).toFixed(1)},${(H - x[k] / 100 * H).toFixed(1)}`).join(' ');
  return `<svg class="chart" viewBox="0 0 ${W} ${H + 4}"><line x1="0" x2="${W}" y1="${H - 0.8 * H}" y2="${H - 0.8 * H}" stroke="var(--warn)" stroke-dasharray="3 3"/><polyline points="${p('cpu_max')}" fill="none" stroke="var(--acc-line)" stroke-width="1.5"/><polyline points="${p('cpu_avg')}" fill="none" stroke="var(--acc)" stroke-width="2"/><line x1="0" x2="${W}" y1="${H}" y2="${H}" stroke="var(--line)"/></svg>
  <div class="legend"><span><i style="background:var(--acc)"></i>일 평균</span><span><i style="background:var(--acc-line)"></i>일 최대</span><span><i style="background:var(--warn)"></i>80% 기준</span></div>`;
}
function list() {
  const clouds = ['전체', ...new Set(DATA.servers.map(s => s.cloud))];
  const rows = DATA.servers.filter(s => S.cloud === '전체' || s.cloud === S.cloud);
  if (!rows.find(s => s.id === S.sel)) S.sel = rows[0] && rows[0].id;
  const s = DATA.servers.find(x => x.id === S.sel), prj = id => (DATA.projects.find(p => p.id === id) || {}).name;
  const al = s ? DATA.alerts.filter(a => a.server === s.id).slice(-5).reverse() : [];
  return app('서버', '인프라 › <b>서버</b>', `
  <div class="phead"><div><h1>서버</h1><p>클라우드와 사내 서버를 한 목록에서 보고 사용률이 높은 서버를 찾습니다.</p></div></div>
  <div class="split">
    <div class="card"><div class="hd"><div class="seg" data-spot="1">${clouds.map(c => `<button class="${c === S.cloud ? 'on' : ''}" data-c="${c}">${c}<em>${c === '전체' ? DATA.servers.length : DATA.servers.filter(x => x.cloud === c).length}</em></button>`).join('')}</div><span class="sp"></span>
      <div class="fbar" data-spot="2"><select class="sel"><option>상태 전체</option></select><select class="sel"><option>프로젝트 전체</option></select><input class="search" placeholder="서버 이름 · IP 찾기"></div></div>
      <div class="bd" style="padding:10px 0 0"><div class="tblwrap"><table class="tbl" data-spot="3"><thead><tr><th>이름</th><th>프로젝트</th><th>상태</th><th>사양</th><th>IP</th><th class="r">CPU 30일 평균</th><th>추이</th></tr></thead><tbody>
      ${rows.map(x => { const a = avg(x.id); return `<tr class="row ${x.id === S.sel ? 'sel' : ''}" data-id="${x.id}"><td><div class="ttl">${esc(x.name)}</div><div class="sub">${esc(x.cloud)} · ${esc(x.region)}</div></td><td>${esc(prj(x.project))}</td><td><span class="bdg ${SST[x.status]}">${x.status}</span></td><td class="num">${x.vcpu} vCPU · ${x.memory_gb} GB</td><td class="mono">${x.ip}</td><td class="r num">${a.toFixed(0)}% <span class="meter" style="width:48px"><i class="${a >= 80 ? 'bad' : a >= 60 ? 'warn' : ''}" style="width:${a}%"></i></span></td><td>${spark(x.id)}</td></tr>`; }).join('')}
      </tbody></table></div><div class="pager">${rows.length}대</div></div></div>
    ${s ? `<div class="card panel" data-spot="4"><div class="hd"><h2>${esc(s.name)}</h2><span class="bdg ${SST[s.status]}">${s.status}</span></div><div class="bd">
      <dl class="kv"><dt>클라우드</dt><dd>${esc(s.cloud)} · ${esc(s.region)}</dd><dt>프로젝트</dt><dd>${esc(prj(s.project))}</dd><dt>사양</dt><dd>${s.vcpu} vCPU · ${s.memory_gb} GB</dd><dt>OS</dt><dd>${esc(s.os)}</dd><dt>IP</dt><dd class="mono">${s.ip}</dd><dt>생성일</dt><dd>${s.created}</dd></dl>
      <h3 style="font-size:13px;margin:16px 0 8px" data-spot="5">CPU 사용률 30일</h3>${cpuChart(s.id)}
      <h3 style="font-size:13px;margin:16px 0 8px" data-spot="6">최근 알림</h3>${al.length ? `<ul class="tl">${al.map(a => `<li><b>${esc(a.rule)}</b> · ${esc(a.severity)}<span>${esc(a.time)}</span></li>`).join('')}</ul>` : '<div class="muted" style="font-size:13px">최근 30일 알림이 없습니다.</div>'}
    </div></div>` : ''}
  </div>`);
}
const SCREENS = [
  {name: '서버 목록', id: 'IN-SRV-LST-R', purpose: '모든 서버의 상태와 사용률을 한 목록에서 보고, 서버를 골라 30일 추이와 최근 알림을 확인한다.', html: list,
   bind() { document.querySelectorAll('[data-c]').forEach(b => b.onclick = () => { S.cloud = b.dataset.c; S.sel = null; render(); });
            document.querySelectorAll('tr.row').forEach(r => r.onclick = () => { S.sel = r.dataset.id; render(); }); },
   spots: [
    ['클라우드 빠른 보기', ['전체 · AWS · Azure · 사내 서버', '숫자는 서버 대수입니다.'], 'SRV-FN-LST-01'],
    ['필터 · 찾기', ['상태 · 프로젝트로 거릅니다.', '이름과 IP 일부로 찾습니다.'], 'SRV-FN-LST-02'],
    ['목록', ['CPU 30일 평균: 일 평균 사용률의 평균입니다.', '막대 색: 60% 미만 남색 · 60% 이상 주황 · 80% 이상 빨강', '추이: 30일 일 평균 선입니다. 중지된 서버는 중지한 날까지만 그립니다.'], 'SRV-PL-MET-01'],
    ['상세 패널', ['행을 누르면 열립니다.', '사양 · OS · IP · 생성일을 보여 줍니다.'], 'SRV-FN-DTL-01'],
    ['CPU 사용률 30일', ['일 평균과 일 최대를 함께 그립니다.', '80% 기준선을 점선으로 표시합니다.'], 'SRV-PL-MET-01'],
    ['최근 알림', ['이 서버의 알림 5건을 최근 순으로 보여 줍니다.'], 'SRV-FN-DTL-02'],
   ]},
];
