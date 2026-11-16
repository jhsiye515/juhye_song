// 월별 비용 · 화면 1개
const CL = [['AWS', 'c1'], ['Azure', 'c2'], ['사내 서버', 'c3']];
let C = {month: null};
function report() {
  const months = [...new Set(DATA.costs.map(c => c.month))].sort();
  C.month = C.month || months[months.length - 1];
  const tot = c => c.compute + c.storage + c.network;
  const sum = (m, f = () => true) => DATA.costs.filter(c => c.month === m && f(c)).reduce((s, c) => s + tot(c), 0);
  const prev = months[months.indexOf(C.month) - 1];
  const cur = sum(C.month), pv = prev ? sum(prev) : 0;
  const W = 640, H = 200, bw = W / months.length, mx = Math.max(...months.map(m => sum(m)));
  const bars = months.map((m, i) => { let y = H; return CL.map(([c, v]) => { const h = sum(m, x => x.cloud === c) / mx * (H - 16); y -= h;
    return `<rect x="${i * bw + 18}" y="${y}" width="${bw - 36}" height="${h}" fill="var(--${v})" opacity="${m === C.month ? 1 : .45}"/>`; }).join('')
    + `<text x="${i * bw + bw / 2}" y="${H + 16}" font-size="12" text-anchor="middle" fill="var(--ink-3)">${m.slice(5)}월</text>`; }).join('');
  const prj = DATA.projects.map(p => ({p, now: sum(C.month, c => c.project === p.id), was: prev ? sum(prev, c => c.project === p.id) : 0})).sort((a, b) => b.now - a.now);
  const d = (a, b) => { if (!b) return '—'; const r = (a - b) / b * 100; return `<span class="delta ${r > 0 ? 'up' : 'down'}">${r > 0 ? '+' : ''}${r.toFixed(1)}%</span>`; };
  return app('월별 비용', '비용 › <b>월별 비용</b>', `
  <div class="phead"><div><h1>월별 비용</h1><p>클라우드와 사내 서버 비용을 프로젝트별로 나눠 봅니다. 금액은 부가세 별도입니다.</p></div><span class="sp"></span>
    <select class="sel" data-spot="1" id="mon">${months.map(m => `<option ${m === C.month ? 'selected' : ''}>${m}</option>`).join('')}</select></div>
  <div class="kpis" data-spot="2">
    <div class="card kpi"><div class="k">${C.month.slice(5)}월 합계</div><div class="v">${won(cur)}</div><div class="s">전월 대비 ${d(cur, pv)}</div></div>
    ${CL.map(([c]) => { const n = sum(C.month, x => x.cloud === c), p = prev ? sum(prev, x => x.cloud === c) : 0; return `<div class="card kpi"><div class="k">${c}</div><div class="v">${won(n)}</div><div class="s">전월 대비 ${d(n, p)}</div></div>`; }).join('')}
  </div>
  <div class="split" style="grid-template-columns:1.1fr 1fr">
    <div class="card" data-spot="3"><div class="hd"><h2>최근 6개월</h2><span class="sp"></span><div class="legend">${CL.map(([c, v]) => `<span><i style="background:var(--${v})"></i>${c}</span>`).join('')}</div></div>
      <div class="bd"><svg class="chart" viewBox="0 0 ${W} ${H + 22}">${bars}<line x1="0" x2="${W}" y1="${H}" y2="${H}" stroke="var(--line)"/></svg></div></div>
    <div class="card" data-spot="4"><div class="hd"><h2>프로젝트별</h2></div><div class="bd" style="padding:10px 0 0"><table class="tbl"><thead><tr><th>프로젝트</th><th>부서</th><th class="r">${C.month.slice(5)}월</th><th class="r">전월 대비</th></tr></thead><tbody>
      ${prj.map(r => `<tr><td class="ttl">${esc(r.p.name)}</td><td class="sub">${esc(r.p.dept)}</td><td class="r num">${won(r.now)}</td><td class="r num">${d(r.now, r.was)}</td></tr>`).join('')}</tbody></table></div></div>
  </div>`);
}
const SCREENS = [
  {name: '월별 비용', id: 'CO-CST-RPT-R', purpose: '한 달 비용을 클라우드와 프로젝트로 나눠 보고, 전월보다 늘어난 곳을 찾는다.', html: report,
   bind() { const m = document.getElementById('mon'); if (m) m.onchange = () => { C.month = m.value; render(); }; },
   spots: [
    ['월 선택', ['최근 6개월 가운데 고릅니다.', '처음 열면 이번 달입니다. 이번 달은 어제까지 쓴 비용입니다.'], 'CST-FN-RPT-01'],
    ['숫자 칸', ['합계와 클라우드별 비용입니다.', '전월 대비: 늘면 빨강, 줄면 초록으로 표시합니다.'], 'CST-PL-AMT-01'],
    ['최근 6개월', ['클라우드별로 쌓은 막대입니다.', '고른 달만 진하게 표시합니다.'], 'CST-FN-RPT-02'],
    ['프로젝트별', ['고른 달 비용이 큰 순서로 정렬합니다.', '비용 = 컴퓨트 + 스토리지 + 네트워크'], 'CST-PL-AMT-01'],
   ]},
];
