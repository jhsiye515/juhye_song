# 문서 사이트 빌드: main(확정본)의 md · 기획서 HTML → index.html 한 장 + plans/<기획>/screen.html · downloads/
#   python3 tools/site/build.py <저장소 폴더> <출력 폴더> [기준 커밋] [최근 기록(시각\t누가\t내용 줄들)]
# 저장소 폴더는 main 을 그대로 꺼낸 것이어야 한다 (작업 중인 파일이 섞이지 않게).
# 사이트는 손으로 고치지 않는다. 고칠 것은 저장소에 PR 로 올리고 다시 빌드한다.
import base64, json, re, shutil, subprocess, sys, datetime
from pathlib import Path

SRC = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()


QA_GROUP = {'테스트결과': 'test', '화면문구': 'ui', '역기획결과': 'rev', '결정표': 'rev'}
QA_LABEL = {  # (문서, 확장자): (보이는 이름, 순서)
    ('테스트결과', 'html'): ('보고서', 1), ('테스트결과', 'xlsx'): ('엑셀 · 정본', 2),
    ('역기획결과', 'html'): ('역기획 보고서', 1), ('결정표', 'html'): ('결정표', 2), ('역기획결과', 'xlsx'): ('엑셀 · 정본', 3),
    ('화면문구', 'xlsx'): ('화면 문구 · 용어집 엑셀 · 정본', 1),
    ('화면문구 변경요청', 'md'): ('변경 요청 문서', 2), ('화면문구 변경요청', 'csv'): ('변경 요청 표', 3),
}


def xlsx_sheet(path, *names):
    """엑셀 시트 하나를 [{머리글: 값}] 로 읽는다. names 가운데 먼저 있는 시트. 표준 라이브러리로 읽는다"""
    import zipfile, xml.etree.ElementTree as ET
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
          'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    try:
        z = zipfile.ZipFile(path)
        ss = []
        if 'xl/sharedStrings.xml' in z.namelist():
            for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', ns):
                ss.append(''.join(t.text or '' for t in si.iter('{%s}t' % ns['m'])))
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        sheets = {s.get('name'): s.get('{%s}id' % ns['r']) for s in wb.find('m:sheets', ns)}
        rid = next((sheets[n] for n in names if n in sheets), None)
        if not rid: return []
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        tgt = next(r.get('Target') for r in rels if r.get('Id') == rid).lstrip('/')
        sh = ET.fromstring(z.read(tgt if tgt.startswith('xl/') else 'xl/' + tgt))
    except Exception:
        return []
    def val(c):
        v = c.find('m:v', ns)
        if c.get('t') == 's' and v is not None: return ss[int(v.text)]
        if c.get('t') == 'inlineStr': return ''.join(t.text or '' for t in c.iter('{%s}t' % ns['m']))
        return v.text if v is not None else None
    def col(ref): return re.match(r'[A-Z]+', ref).group(0)
    rows = sh.find('m:sheetData', ns)
    if rows is None or not len(rows): return []
    head = {col(c.get('r')): (val(c) or '').strip() for c in rows[0]}
    out = []
    for r in rows[1:]:
        d = {head[col(c.get('r'))]: (val(c) or '').strip() for c in r if head.get(col(c.get('r')))}
        if any(d.values()): out.append(d)
    return out



# 용어의 영문 · 용어집 분류: 공통 정책 POL-GLOSSARY 표(GLOSSARY-Tn)
_TERMREF = None
def term_ref():
    global _TERMREF
    if _TERMREF is not None:
        return _TERMREF
    dic, gl = {}, {}
    f = SRC / 'references' / 'i18n' / 'ko-en.json'
    if f.exists():
        try:
            dic = json.loads(f.read_text()).get('사전', {})
        except ValueError:
            dic = {}
    g = SRC / 'policies' / 'product' / 'terms' / 'POL-GLOSSARY.md'
    if g.exists():
        tid = title = ''
        for line in g.read_text().splitlines():
            m = re.match(r'^###\s+(GLOSSARY-T\d+)\s+(.+)$', line)
            if m:
                tid, title = m.group(1), m.group(2).strip(); continue
            if line.startswith('## '):
                tid = ''
            if tid and line.startswith('|') and not re.match(r'^\|\s*(-|용어|구분|콘솔|표기)', line):
                c0 = line.strip('|').split('|')[0].strip()
                m2 = re.match(r'^(.+?)\s*\(([A-Za-z][^)]*)\)\s*$', c0)
                ko, en = (m2.group(1).strip(), m2.group(2).strip()) if m2 else (re.sub(r'\s*\([^)]*\)\s*$', '', c0).strip(), '')
                if ko and ko not in gl:
                    gl[ko] = dict(tid=tid, title=title, en=en)
    _TERMREF = (dic, gl)
    return _TERMREF

def ui_text(x):
    """화면 문구 정본(품질 플러그인 uitext · 「화면문구.xlsx」) 요약: 판단 수 · 바꿀 문구 · 보류 · 용어집 용어.
    화면별 전체 시트의 판단 · 제안 문구와 용어집 시트를 읽는다. 같은 문구 줄(판단이 수식)은 처음 줄만 센다"""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(x, read_only=True, data_only=True)
    except Exception:
        return None
    if '화면별 전체' not in wb.sheetnames:
        return None
    it = wb['화면별 전체'].iter_rows(min_row=3, values_only=True)
    h = [str(c or '').replace('\n', '') for c in next(it)]
    ix = {k: i for i, k in enumerate(h)}
    g = lambda r, k: (str(r[ix[k]]).strip() if k in ix and ix[k] < len(r) and r[ix[k]] is not None else '')
    cnt = {'정상': 0, '수정': 0, '보류': 0, '미검토': 0}
    fixes, total = [], 0
    for r in it:
        if not g(r, 'ID') or not g(r, '문구'):
            continue
        j = g(r, '판단')
        if j.startswith('='):
            continue
        total += 1
        cnt[j if j in cnt else '미검토'] += 1
        if j in ('수정', '보류'):
            menu = ' > '.join(v for v in (g(r, '1뎁스대메뉴'), g(r, '2뎁스중메뉴'), g(r, '3뎁스소메뉴')) if v and v != '—')
            loc = ' · '.join(v for v in (g(r, '탭'), g(r, '창 · 영역')) if v and v not in ('—', '화면 기본', '기본'))
            fixes.append(dict(id=g(r, 'ID'), state=j, menu=menu, screen=g(r, '화면'), stype=g(r, '화면유형'), loc=loc, type=g(r, '유형'),
                              text=g(r, '문구'), to=g(r, '제안 문구'), cat=g(r, '분류'), note=g(r, '비고')))
    # 전체 문구: 문구 ID → 메뉴 뎁스 · 화면 · 탭 · 창 · 영역 · 종류 · 실제 문구 (용어가 쓰인 정확한 자리)
    loc = {}
    if '전체 문구' in wb.sheetnames:
        it = wb['전체 문구'].iter_rows(values_only=True)
        ah = [str(c or '') for c in next(it)]
        for r in it:
            d = {k: (str(v).strip() if v is not None else '') for k, v in zip(ah, r)}
            if not d.get('ID'):
                continue
            nz = lambda v: '' if v in ('—', '-', 'None') else v
            loc[d['ID']] = dict(id=d['ID'], path=[nz(d.get('1뎁스 대메뉴', '')), nz(d.get('2뎁스 중메뉴', '')), nz(d.get('3뎁스 소메뉴', '')), nz(d.get('화면', ''))],
                                stype=nz(d.get('화면 유형', '')), loc=' · '.join(v for v in (nz(d.get('탭', '')), nz(d.get('창', '')), nz(d.get('영역', ''))) if v and v != '기본') or '화면 기본',
                                type=nz(d.get('유형', '')) or nz(d.get('원래 종류', '')), text=d.get('문구', ''))
    terms, seen, bys, order = [], {}, {}, []
    if '용어집' in wb.sheetnames:
        it = wb['용어집'].iter_rows(min_row=3, values_only=True)
        gh = [str(c or '') for c in next(it)]
        for r in it:
            d = {k: (str(v).strip() if v is not None else '') for k, v in zip(gh, r)}
            t = d.get('용어')
            if not t:
                continue
            scr = ' > '.join(v for v in (d.get('2뎁스 중메뉴'), d.get('화면')) if v and v != '—')
            path = tuple(v if v and v != 'None' else '—' for v in (d.get('1뎁스 대메뉴'), d.get('2뎁스 중메뉴'), d.get('3뎁스 소메뉴'), d.get('화면')))
            if path not in bys: bys[path] = []; order.append(path)
            if t not in bys[path]: bys[path].append(t)
            ids = re.findall(r'U\d{4,}', d.get('쓰인 곳', ''))
            if t in seen:
                o = seen[t]
                if scr and scr not in o['screens']: o['screens'].append(scr)
                o['at'] += [loc[i] for i in ids if i in loc and all(a['id'] != i for a in o['at'])]
                continue
            o = dict(term=t, mean=d.get('뜻', ''), avoid='' if d.get('쓰지 않는 말') in ('—', 'None') else d.get('쓰지 않는 말', ''),
                     used=d.get('쓰인 곳', ''), state=d.get('상태', ''), apply=d.get('용어집 반영', ''), note=d.get('근거 · 비고', ''), screens=[scr] if scr else [])
            o['open'] = o['state'] != '확정' and not o['apply'].startswith('올리지 않음')
            dic, gl = term_ref()
            g_ = gl.get(t) or gl.get(t.replace(' ', '')) or {}
            en_ = list(dic.get(t, []) or dic.get(t.replace(' ', ''), []))
            if g_.get('en') and g_['en'] not in en_: en_.append(g_['en'])
            o['en'] = en_; o['gl'] = dict(tid=g_['tid'], title=g_['title']) if g_ else None
            o['latin'] = bool(re.match(r'^[A-Za-z0-9 .\-_/()]+$', t))
            o['at'] = [loc[i] for i in dict.fromkeys(ids) if i in loc]
            seen[t] = o; terms.append(o)
    wb.close()
    # 쓰지 않는 말이 화면에 남은 곳: 쓰지 않는 말(「 · 」 · 쉼표로 여럿)을 글자에 담은 문구
    for o in terms:
        ws_ = [w.strip() for w in re.split(r'[·,/]', o['avoid']) if len(w.strip()) >= 2 and not re.match(r'^[(∞]', w.strip())]
        o['avoid_at'] = [v for v in loc.values() if any(w in v['text'] for w in ws_)][:40] if ws_ else []
    # 화면별: 용어집 시트의 메뉴 뎁스(1 · 2 · 3뎁스 · 화면)마다 쓰인 용어
    screens = [dict(path=list(k), terms=bys[k]) for k in order]
    return dict(file=x.name, day=x.name[:6], total=total, cnt=cnt, fixes=fixes, terms=terms, screens=screens)

def xlsx_rounds(path):
    """테스트결과 엑셀 「실행」 시트의 「N차 판정」 칸마다 판정 수"""
    out = {}
    for r in xlsx_sheet(path, '실행'):
        for k, v in r.items():
            m = re.match(r'(\d+)차 판정$', k)
            if m and v:
                c = out.setdefault(m.group(1), {})
                c[v] = c.get(v, 0) + 1
    return [dict(round=f'{n}차', count=out[n]) for n in sorted(out, key=int) if out[n]]


# 품질 이슈: 기획마다 가장 늦은 차수 테스트결과 엑셀(정본)의 결함 · 결정 필요 · 진행 필요 · 개선 제안 시트.
# 닫힌 상태: 결함 상태가 아래 셋 가운데 하나인 것
DEFECT_CLOSED = ('확인 완료', '재현 안 됨', '기획 변경')


def qa_issues(path, plan, href, rnd):
    out = []
    base = dict(plan=plan, src=href, round=rnd)
    for r in xlsx_sheet(path, '결함'):
        if not r.get('ID'): continue
        st = r.get('상태') or '신규'
        out.append(dict(base, kind='defect', id=r['ID'], title=r.get('제목', ''), cat=r.get('범주', ''), type=r.get('유형', ''),
                        sev=r.get('심각도', ''), pri=r.get('우선순위', ''), status=st, open=st not in DEFECT_CLOSED,
                        owner=r.get('담당', ''), screen=r.get('화면', ''), tc=r.get('관련 TC', ''), steps=r.get('재현 절차', ''),
                        expected=r.get('기대', ''), actual=r.get('실제', ''), basis=r.get('근거', ''), evidence=r.get('증거', ''),
                        found=r.get('발견 차수', ''), verified=r.get('확인 차수', '')))
    for r in xlsx_sheet(path, '결정 필요', '정할 것'):
        if not r.get('ID'): continue
        done = bool(r.get('결정'))
        out.append(dict(base, kind='decision', id=r['ID'], title=r.get('항목', ''), cat=r.get('구분', ''), type=r.get('영역', ''),
                        status='결정됨' if done else '결정 필요', open=not done, owner=r.get('물을 곳', '') or '기획',
                        screen=r.get('화면', ''), now=r.get('지금 동작', ''), policy=r.get('공통 정책', ''), options=r.get('선택지', ''),
                        rec=r.get('추천', ''), why=r.get('이유', ''), effect=r.get('생기는 일', ''), decided=r.get('결정 내용', '') or r.get('결정', ''),
                        basis=r.get('근거 사실', ''), until=r.get('정하기 전까지', '')))
    for i, r in enumerate(xlsx_sheet(path, '진행 필요'), 1):
        if not r.get('항목'): continue
        st = r.get('상태') or '진행 필요'
        out.append(dict(base, kind='todo', id=f'{rnd} 진행 {i}', title=r['항목'], cat=r.get('단계', ''), status=st, open=st != '완료',
                        owner='기획', why=r.get('이유', ''), tc=r.get('TC', '') or r.get('관련 TC', ''), after=r.get('다시 돌릴 조건', '')))
    for r in xlsx_sheet(path, '개선 제안'):
        if not r.get('ID'): continue
        done = bool(r.get('결정'))
        out.append(dict(base, kind='ux', id=r['ID'], title=r.get('제안', ''), cat=r.get('종류', ''), screen=r.get('화면', ''),
                        status=r.get('결정') or '검토 전', open=not done, owner='기획', task=r.get('하려던 일', ''),
                        actual=r.get('관찰', ''), effect=r.get('영향', ''), basis=r.get('근거', ''), gain=r.get('효과', ''),
                        cost=r.get('비용', ''), oq=r.get('관련 미결정', '')))
    return out
HERE = Path(__file__).resolve().parent
import os
REPO = os.environ.get('REPO_URL', 'https://github.com/jhsiye515/juhye_song')  # 저장소 주소(GitHub)

AREA = {
    'guide': ('가이드', 0),
    'product/display': ('제품 · 표기', 1), 'product/list': ('제품 · 목록 조회', 2),
    'product/status': ('제품 · 상태', 3), 'domain/ops': ('도메인 · 운영', 10),
}

# 기획 목록. 폴더가 있으면 사이트에 나온다. 정의서 md 가 있으면 탭이 생긴다
PLANS = [
    dict(key='incident-queue', dir='features/ops/incident-queue', title='인시던트 처리 큐', menu='운영 › 인시던트', code='INC'),
    dict(key='server-list', dir='features/infra/server-list', title='서버 목록', menu='인프라 › 서버', code='SRV'),
    dict(key='cost-report', dir='features/cost/cost-report', title='월별 비용', menu='비용 › 월별 비용', code='CST'),
]
DOC_TITLE = {'spec': '기능정의서', 'policy': '정책정의서', 'screens': '화면 목록'}
DOC_FILE = {'spec': 'spec.md', 'policy': 'policy.md', 'screens': 'screens/index.md'}


def front(text):
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    meta = {}
    if not m:
        return meta, text
    key = None
    for line in m.group(1).splitlines():
        if re.match(r'^[a-z_]+:', line):
            key, v = line.split(':', 1)
            meta[key] = re.sub(r'\s+#.*$', '', v).strip().strip('"')
        elif key and line.strip().startswith('- '):
            meta[key] = (meta.get(key) + '\n' if meta.get(key) else '') + line.strip()[2:]
    return meta, text[m.end():]


def rows(body):
    sec = ''
    for line in body.splitlines():
        if re.match(r'^#{1,3} ', line):
            sec = line.lstrip('#').strip()
        elif line.startswith('|') and not re.match(r'^\|[\s\-:|]+\|$', line.strip()):
            yield sec, [c.strip() for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]


docs, defs = [], {}


def missing_refs(html_path):
    # 기획서가 밖의 파일(상대 경로 CSS · JS · 이미지)을 불러오는데 그 파일이 저장소에 없으면 화면이 깨진다
    html = html_path.read_text(errors='ignore')
    refs = re.findall(r'<(?:link[^>]+href|script[^>]+src|img[^>]+src)=["\']([^"\'#?]+)', html)
    return sorted({r for r in refs if not re.match(r'^(https?:|data:|blob:|//|javascript:)', r)
                   and not (html_path.parent / r).exists()})


def define(i, doc, label, kind):
    defs.setdefault(i, dict(doc=doc, label=re.sub(r'\\(.)', r'\1', label)[:80], kind=kind))


# 공통 정책
for f in sorted((SRC / 'policies').rglob('*.md')):
    if f.name.startswith('_') or f.name == 'README.md':
        continue
    area = str(f.relative_to(SRC / 'policies').parent)
    if area.startswith('review'):
        continue
    meta, body = front(f.read_text())
    group, order = AREA.get(area, (area, 99))
    did = meta.get('id') or f.stem
    title = meta.get('title') or (re.search(r'^# (.+)$', body, re.M) or [None, did])[1]
    docs.append(dict(id=did, kind='policy', title=title, group=group, order=order, meta=meta, body=body,
                     path='policies/' + str(f.relative_to(SRC / 'policies'))))
    define(did, did, title, 'doc')
    code = did[4:]
    for sec, c in rows(body):
        if re.fullmatch(re.escape(code) + r'-(M?\d+|U\d+|T\d+)', c[0]):
            kind = 'open' if re.search(r'-U\d+$', c[0]) else ('draft' if sec.startswith('미확정') else 'rule')
            define(c[0], did, c[1] if len(c) > 1 else '', kind)

# 기획 목록에 없는 기획 폴더(features/<서비스>/<기획>/)도 찾아 넣는다. 이름 · 코드는 정의서 문서 정보에서 읽는다
_known = {p['dir'] for p in PLANS}
for _d in sorted((SRC / 'features').glob('*/*/')):
    _rel = str(_d.relative_to(SRC)).rstrip('/')
    if _rel in _known or not (_d / 'screens/prototype.html').exists():
        continue
    _m = {}
    for _f in ('spec.md', 'policy.md', 'screens/index.md'):
        if (_d / _f).exists():
            _m = front((_d / _f).read_text())[0]
            if _m: break
    _t = re.sub(r'^\[[^\]]*\]\s*', '', _m.get('title', '')); _t = re.sub(r'\s*(기능정의서|정책정의서|화면 목록)$', '', _t).strip() or _d.name
    PLANS.append(dict(key=_d.name, dir=_rel, title=_t, menu=_m.get('menu', ''), code=_m.get('code', '')))

# 기획
plans, open_items = [], []
for p in PLANS:
    base = SRC / p['dir']
    if not (base / 'screens/prototype.html').exists():
        continue
    p = dict(p, docs=[], files=[], status='', owner='')
    p['screen'] = f"plans/{p['key']}/screen.html"
    p['broken'] = missing_refs(base / 'screens/prototype.html')
    for k in ('spec', 'policy', 'screens'):
        f = base / DOC_FILE[k]
        if not f.exists():
            continue
        meta, body = front(f.read_text())
        p['code'] = meta.get('code') or p.get('code', '')
        did = f"{p['code']}/{k}"
        docs.append(dict(id=did, kind='plan', title=DOC_TITLE[k], group=p['title'], order=50, meta=meta, body=body,
                         path=f"{p['dir']}/{DOC_FILE[k]}"))
        p['docs'].append(did)
        p['files'].append(dict(path=f"{p['dir']}/{DOC_FILE[k]}", what=DOC_TITLE[k]))
        p['screen_url'] = p.get('screen_url') or meta.get('artifact', '')
        p['status'] = p['status'] or meta.get('status', '')
        p['owner'] = p['owner'] or meta.get('owner', '')
        if k == 'spec':
            for m in re.finditer(r'^#### ([A-Z]{3}-FN-[A-Z]+-\d+) (.+)$', body, re.M):
                define(m.group(1), did, m.group(2), 'fn')
            for sec, c in rows(body):
                if re.fullmatch(r'[A-Z]{3}-RQ-\d+', c[0]):
                    define(c[0], did, c[1], 'rq')
                elif re.fullmatch(r'[A-Z]{3}-FN-[A-Z]+-\d+', c[0]) and len(c) > 3:
                    define(c[0], did, c[3], 'fn')  # 표 양식(0.2): 기능 ID | 대분류 | 중분류 | 기능명 | …
        elif k == 'policy':
            for m in re.finditer(r'^## \d+\. ([A-Z]{3}-PL-[A-Z]+-\d+) · (.+)$', body, re.M):
                define(m.group(1), did, m.group(2), 'pl')
            for sec, c in rows(body):
                if re.fullmatch(r'[A-Z]{3}-OQ-\d+', c[0]):
                    define(c[0], did, c[1], 'oq')
                    open_items.append(dict(id=c[0], doc=did, label=c[1], kind='oq',
                                           now=c[2] if len(c) > 2 else '', need=c[3] if len(c) > 3 else '',
                                           who=c[4] if len(c) > 5 else (c[-1] if len(c) > 4 else '')))  # 0.2: … | 담당 | 언제까지
        else:
            for sec, c in rows(body):
                if re.fullmatch(r'[A-Z]{2}-[A-Z]{3}-[A-Z0-9-]+|SCR-[A-Z]+-\d+', c[0]):  # P2P 화면 ID, 아직 없으면 기획서 화면 ID
                    define(c[0], did, c[1], 'scr')
    p.setdefault('code', p['key'][:3].upper())
    p['files'].append(dict(path=f"{p['dir']}/screens/prototype.html", what='기획서 HTML (내려받아 브라우저로 열기)'))
    p['status'] = p['status'] or '기획서만'
    plans.append(p)

# 공통 정책 검토 항목 (policies/review): 사람이 정할 것
RV = SRC / 'policies' / 'review'
if RV.exists():
    for f in sorted(RV.glob('*.md')):
        if f.name.startswith('ISSUES'):
            continue
        meta, body = front(f.read_text())
        did = 'REVIEW/' + f.stem
        title = (re.search(r'^# (.+)$', body, re.M) or [None, f.stem])[1]
        docs.append(dict(id=did, kind='review', title=title, group='검토 항목', order=90, meta=meta, body=body,
                         path='policies/review/' + f.name))
        cur = ''
        for line in body.splitlines():
            if line.startswith('## '):
                cur = line[3:].strip()
            m = re.match(r'^- \[(R-[^\]]+)\] (.+?)(?: \(→ ([^)]+)\))?\s*〔([^〕]+)〕', line)
            if m:
                issue, _, opts = m.group(2).partition(' — ')
                define(m.group(1), did, issue, 'review')
                open_items.append(dict(id=m.group(1), doc=did, label=issue, kind='review', need=opts, now=m.group(4), who=cur, uid=m.group(3) or ''))
        if f.name.startswith('02-CODE-GAP'):
            # 정책 · 코드 차이: | ID | 우선 | 차이 | 처리 | 할 일 | 맡는 곳 |
            for line in body.splitlines():
                c = [x.strip() for x in line.strip().strip('|').split('|')]
                if line.startswith('| ') and re.fullmatch(r'[GV]\d*-\d+', c[0]) and len(c) >= 6:
                    define(c[0], did, c[2], 'gap')
                    open_items.append(dict(id=c[0], doc=did, label=c[2], kind='gap', pri=c[1], now=c[3], need=c[4], who=c[5]))
        if f.name.startswith('00-'):
            sec = ''
            for line in body.splitlines():
                if line.startswith('## '):
                    sec = line
                if '결정 대기' in sec and re.match(r'^\| X\d+ ', line):
                    c = [x.strip() for x in line.strip().strip('|').split('|')]
                    define(c[0], did, c[1], 'cross')
                    open_items.append(dict(id=c[0], doc=did, label=c[1], kind='cross', need=c[2] if len(c) > 2 else '', now=c[3] if len(c) > 3 else ''))
dec = SRC / 'policies/guide/DECISIONS.md'
if dec.exists():
    sec = ''
    for line in dec.read_text().splitlines():
        if line.startswith('## '):
            sec = line
        if sec.startswith('## 6.') and line.startswith('|') and not re.match(r'^\|[\s\-:|]+\|$', line.strip()):
            c = [x.strip() for x in line.strip().strip('|').split('|')]
            if c[0] in ('규칙',):
                continue
            open_items.append(dict(id=c[0], doc='DECISIONS', label=c[1] if len(c) > 1 else '', kind='recheck', now=c[2] if len(c) > 2 else '', need=c[3] if len(c) > 3 else ''))

# 운영 문서
GUIDES = [('README.md', 'RM-00'), ('guides/README.md', 'GD-00'), ('CONTRIBUTING.md', 'RL-01'), ('guides/git-workflow.md', 'GD-01'), ('guides/upload-process.md', 'GD-02'),
          ('guides/user-guide.md', 'GD-03'), ('guides/spec.md', 'GD-04'), ('guides/policy.md', 'GD-05'), ('guides/screens.md', 'GD-06'), ('guides/planbook.md', 'GD-07'), ('guides/claude.md', 'GD-08'),
          ('guides/qa.md', 'GD-09'), ('tools/README.md', 'TL-01'), ('tools/site/DESIGN.md', 'TL-02')]
for i, (f, num) in enumerate(GUIDES):
    fp = SRC / f
    if not fp.exists():
        continue
    meta, body = front(fp.read_text())
    title = (re.search(r'^# (.+)$', body, re.M) or [None, f])[1]
    body = re.sub(r'^# .+\n+', '', body, count=1)
    here = Path(f).parent
    def relink(m, here=here):
        t, u = m.group(1), m.group(2)
        if re.match(r'^(https?:|#|mailto:)', u):
            return m.group(0)
        path, _, frag = u.partition('#')
        norm = str((here / path).as_posix())
        parts = []
        for x in norm.split('/'):
            if x == '..' and parts: parts.pop()
            elif x not in ('.', ''): parts.append(x)
        norm = '/'.join(parts)
        num = dict(GUIDES).get(norm)
        if num:
            return f'[{t}](#/doc/{num})'
        return f'[{t}]({REPO}/blob/main/{norm})'
    body = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', relink, body)
    docs.append(dict(id=num, kind='guide', title=title, group='운영 문서', order=i, meta=meta, body=body, path=f))

# 참조: 정의된 ID 가 다른 자리에 나오면 참조
ids = sorted(defs, key=len, reverse=True)
idre = re.compile(r'(?<![A-Za-z0-9-])(' + '|'.join(map(re.escape, ids)) + r')(?![A-Za-z0-9-])')
refs = {}
for d in docs:
    sec = ''
    for line in d['body'].splitlines():
        if re.match(r'^#{1,4} ', line):
            sec = line.lstrip('#').strip()
        first = line.strip().strip('|').split('|')[0].strip() if line.startswith('|') else ''
        for m in idre.finditer(line):
            i = m.group(1)
            if defs[i]['doc'] == d['id'] and (i == first or defs[i]['kind'] == 'doc' or sec.startswith(i)):
                continue
            where = first if first and first != i and first in defs else sec
            lst = refs.setdefault(i, [])
            item = dict(doc=d['id'], where=where)
            if item not in lst:
                lst.append(item)

for i, v in defs.items():
    if v['kind'] in ('open', 'draft'):
        open_items.append(dict(id=i, doc=v['doc'], label=v['label'], kind=v['kind']))


def git(*a):
    try:
        return subprocess.run(['git', '-C', str(SRC), *a], capture_output=True, text=True).stdout.strip()
    except Exception:
        return ''


commit = (sys.argv[3] if len(sys.argv) > 3 else git('rev-parse', '--short', 'HEAD')) or '-'
log = [dict(zip(('at', 'who', 'msg'), l.split('\t', 2))) for l in (sys.argv[4] if len(sys.argv) > 4 else '').splitlines() if l]

# 용어집 표 이름(GLOSSARY-Tn → 제목): 화면 문구 · 용어 화면의 용어집 분류
_g = SRC / 'policies' / 'product' / 'terms' / 'POL-GLOSSARY.md'
glt = dict(re.findall(r'^###\s+(GLOSSARY-T\d+)\s+(.+?)\s*$', _g.read_text(), re.M)) if _g.exists() else {}
data = dict(docs=docs, defs=defs, refs=refs, plans=plans, open=open_items, log=log, commit=commit, repo=REPO, glt=glt,
            built=datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
for p in plans:
    (OUT / 'plans' / p['key']).mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / p['dir'] / 'screens/prototype.html', OUT / p['screen'])
EXPORT = HERE.parent / 'export' / 'export.py'
issues = []
for p in plans:
    dl = OUT / 'plans' / p['key'] / 'downloads'
    dl.mkdir(parents=True, exist_ok=True)
    for k in ('spec', 'policy', 'screens'):
        f = SRC / p['dir'] / DOC_FILE[k]
        if f.exists() and EXPORT.exists():
            subprocess.run([sys.executable, str(EXPORT), str(f), str(dl)], capture_output=True)
    keep = {'기능정의서': '.xlsx', '정책정의서': '.docx', '화면목록': '.xlsx'}
    for x in list(dl.iterdir()):
        if not any(k in x.name and x.suffix == ext for k, ext in keep.items()):
            x.unlink()
    p['downloads'] = sorted(x.name for x in dl.iterdir())
    # 품질 검사 결과(qa/): 검사 종류(품질 검사 · 화면 문구 · 역기획)로 묶고, 그 안에서 날짜 · 차수마다 한 덩어리.
    # 덩어리 안의 파일(보고서 · 엑셀 · 결정표 · 변경 요청)은 아래로 나란히 둔다
    qa = SRC / p['dir'] / 'qa'
    p['qa'] = []
    if qa.exists():
        (OUT / 'plans' / p['key'] / 'qa').mkdir(parents=True, exist_ok=True)
        rows = {}
        for x in sorted(qa.iterdir()):
            m = re.match(r'^(\d{6}) (.+?) (테스트결과|역기획결과|결정표|화면문구)(?: (변경요청))?(?: (\S+))?\.(xlsx|html|csv|md)$', x.name)
            if not m:
                continue
            day, kind, req, rnd, ext = m.group(1), m.group(3), m.group(4), m.group(5) or '', m.group(6)
            if kind == '테스트결과' and rnd == '역기획':  # 1.2.0부터 역기획 결과도 테스트결과 이름(예전 이름 역기획결과도 읽는다)
                kind, rnd = '역기획결과', ''
            group = QA_GROUP[kind]
            shutil.copy(x, OUT / 'plans' / p['key'] / 'qa' / x.name)
            r = rows.setdefault((group, day, rnd), dict(group=group, day=day, round=rnd, files=[]))
            label = QA_LABEL.get((kind + (' 변경요청' if req else ''), ext))
            if not label:
                continue
            r['files'].append(dict(label=label[0], order=label[1], ext=ext, href=f"plans/{p['key']}/qa/{x.name}"))
            if kind == '테스트결과' and ext == 'xlsx': r['rounds'] = xlsx_rounds(x)
            if kind == '역기획결과': r['reverse'] = True
        # 선기획 품질 검사 날의 결정표 · 화면 문구는 그날 마지막 차수 줄에 함께 둔다(1차에 같이 낸 결과).
        # 그날 역기획결과가 있으면 역기획 결정표이므로 따로 둔다
        rk = lambda r: int(re.match(r'\d+', r['round']).group(0)) if re.match(r'\d+', r['round']) else -1  # 10차가 2차 앞에 오지 않게
        for (g, day, rnd), r in list(rows.items()):
            if g == 'test' or rnd: continue
            tests = [t for (tg, td, tr), t in rows.items() if tg == 'test' and td == day and tr]
            if not tests or (g == 'rev' and r.get('reverse')): continue  # 역기획 결과(보고서 · 엑셀 어느 하나라도)가 있는 날은 따로
            last = max(tests, key=rk)
            last['files'] += [dict(f, order=f['order'] + 10 * (2 if g == 'rev' else 3)) for f in r['files']]
            del rows[(g, day, rnd)]
        for r in rows.values(): r['files'].sort(key=lambda f: f['order'])
        p['qa'] = sorted(rows.values(), key=lambda r: (r['day'], rk(r)), reverse=True)
        # 품질 이슈는 가장 늦은 차수 테스트결과 엑셀 한 장에서 뽑는다(지난 차수 판정 · 결함까지 모두 들어 있음)
        tests = [x for x in qa.glob('*테스트결과 *차.xlsx') if re.match(r'^\d{6} ', x.name)]
        if tests:
            num = lambda x: (x.name[:6], int(re.search(r'(\d+)차\.xlsx$', x.name).group(1)))
            last = max(tests, key=num)
            p['qa_latest'] = dict(day=last.name[:6], round=f'{num(last)[1]}차', href=f"plans/{p['key']}/qa/{last.name}")
            issues += qa_issues(last, p['key'], p['qa_latest']['href'], p['qa_latest']['round'])
            # 결함 화면 사진: 같은 차수 테스트결과 보고서(html)의 IMG 묶음(결함 · 검증 ID → data URI)을 파일로 꺼내 상세 패널에 보인다
            rep = last.with_suffix('.html')
            if rep.exists():
                txt = rep.read_text(errors='ignore'); k = txt.find('const IMG=')
                if k >= 0:
                    try:
                        imgs, _ = json.JSONDecoder().raw_decode(txt[k + len('const IMG='):])
                    except ValueError:
                        imgs = {}
                    idir = OUT / 'plans' / p['key'] / 'qa' / 'img'; idir.mkdir(parents=True, exist_ok=True)
                    for iid, uri in imgs.items():
                        m = re.match(r'data:image/(\w+);base64,(.*)$', uri, re.S)
                        if not m or not re.match(r'^[A-Za-z0-9_-]+$', iid): continue
                        ext = 'jpg' if m.group(1) == 'jpeg' else m.group(1)
                        (idir / f'{iid}.{ext}').write_bytes(base64.b64decode(m.group(2)))
                        for it in issues:
                            if it.get('plan') == p['key'] and it.get('id') == iid: it['img'] = f"plans/{p['key']}/qa/img/{iid}.{ext}"
        # 품질요약.json: 품질 플러그인이 결과를 올릴 때 함께 만드는 요약(숫자 정의는 그 파일 한 곳, GD-09 4장). 있으면 품질 숫자는 이것만 쓴다
        # 화면 문구 · 용어: 가장 늦은 화면문구 엑셀(품질 플러그인 uitext) 한 장
        uis = sorted(x for x in qa.glob('*화면문구.xlsx') if re.match(r'^\d{6} ', x.name))
        if uis:
            u = ui_text(uis[-1])
            if u:
                u['href'] = f"plans/{p['key']}/qa/{uis[-1].name}"
                req = uis[-1].with_name(uis[-1].name.replace('화면문구.xlsx', '화면문구 변경요청.md'))
                if req.exists(): u['req'] = f"plans/{p['key']}/qa/{req.name}"
                p['ui'] = u
        qs = qa / '품질요약.json'
        if qs.exists():
            try:
                p['qs'] = json.loads(qs.read_text())
            except ValueError:
                pass
data['plans'] = plans
data['issues'] = issues
# 포털 양식(TL-02): 사이트 전용 CSS 한 장. 제품 디자인 양식은 쓰지 않는다
(OUT / 'ds').mkdir(exist_ok=True)
shutil.copy(HERE / 'ds' / 'portal.css', OUT / 'ds' / 'portal.css')
tpl = (HERE / 'template.html').read_text()
# 브라우저가 옛 CSS 를 기억하지 않게 주소에 커밋을 붙인다
tpl = tpl.replace('href="ds/portal.css"', f'href="ds/portal.css?v={commit}"')
(OUT / 'index.html').write_text(tpl.replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/')))
print('기획', len(plans), '· 문서', len(docs), '· ID', len(defs), '· 참조된 ID', len(refs), '· 미결', len(open_items),
      '· 품질 이슈', len(issues), '(열림', sum(i['open'] for i in issues), ') · 기준', commit)
