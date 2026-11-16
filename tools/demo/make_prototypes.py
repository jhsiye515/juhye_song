# 가상 기획 세 개의 화면 설계서(screens/prototype.html)를 만든다.
#   python3 tools/demo/make_prototypes.py
# 화면은 data/all.json(예시 데이터)과 design/kit.css(제품 양식)를 한 파일 안에 넣는다. 밖의 파일을 부르지 않는다.
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
D = json.loads((ROOT / 'data/all.json').read_text())
CSS = (ROOT / 'design/kit.css').read_text()
SHELL = (HERE / 'shell.html').read_text()
base = dict(now='2026-11-16 09:00', users=D['users'], projects=D['projects'])
PLANS = [
    ('features/ops/incident-queue', '인시던트 처리 큐', 'INC', 'incident-queue.js',
     dict(base, incidents=D['incidents'], servers=[{k: s[k] for k in ('id', 'name', 'cloud')} for s in D['servers']])),
    ('features/infra/server-list', '서버 목록', 'SRV', 'server-list.js',
     dict(base, servers=D['servers'], alerts=[{k: a[k] for k in ('server', 'time', 'rule', 'severity')} for a in D['alerts']],
          metrics=[{k: m[k] for k in ('server', 'date', 'cpu_avg', 'cpu_max')} for m in D['metrics_daily']])),
    ('features/cost/cost-report', '월별 비용', 'CST', 'cost-report.js', dict(base, costs=D['costs_monthly'])),
]
for d, title, code, js, data in PLANS:
    out = ROOT / d / 'screens/prototype.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    html = (SHELL.replace('__TITLE__', title).replace('__CODE__', code).replace('__CSS__', CSS)
            .replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
            .replace('__SCRIPT__', (HERE / js).read_text()))
    out.write_text(html)
    print(out.relative_to(ROOT), f'{len(html) // 1024} KB')
