# 포트폴리오 사이트 빌드
#   python3 tools/portfolio/build.py <저장소 폴더> <출력 폴더>
# 위계: 홈 → 사례(사이트) → 기획 → 문서
#   index.html                          홈: 소개 · 하는 일 · 사례 카드 · 문서 연결 방식
#   work/<사례>/index.html              사례: 배경 · 접근 · 결과 · 기획 목록 · 공통 정책
#   work/<사례>/<기획>/index.html       기획: 요약 · 숫자 · 화면 설계서 · 문서 바로가기
#   work/<사례>/<기획>/<문서>.html      문서: 기능 정의서 · 정책 정의서 · 화면 목록 · 품질 결과
#   portal/                             기획 · 품질 문서 포털(tools/site/build.py 결과)
# 내용은 portfolio/home.md · portfolio/cases/*.md 에 쓴다. 사례를 늘리려면 cases/ 에 md 를 하나 더 둔다.
import html, json, re, shutil, subprocess, sys
from pathlib import Path

SRC = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
HERE = Path(__file__).resolve().parent
PF = SRC / 'portfolio'
REPO = 'https://github.com/jhsiye515/juhye_song'
STATUS = {'approved': ('확정', 'ok'), 'review': ('검토 중', 'warn'), 'in-review': ('검토 중', 'warn'),
          'draft': ('작성 중', 'mute'), 'sample': ('샘플', 'mute'), '확정': ('확정', 'ok')}
DOCS = [('spec', 'spec.md', '기능 정의서', '요구사항을 기능 단위로 쪼개고 화면 · 정책 · 권한을 붙인 표'),
        ('policy', 'policy.md', '정책 정의서', '숫자 · 조건 · 상태 전이 규칙과 따르는 공통 정책'),
        ('screens', 'screens/index.md', '화면 목록', '화면 ID · 진입 경로 · 화면마다 쓰는 기능'),
        ('qa', None, '품질 결과', '차수별 테스트 실행 · 결함 · 결정 필요 · 개선 제안')]
ID_RE = re.compile(r'(?<![\w-])[A-Z]{2,6}(?:-[A-Z0-9]{1,4}){1,3}(?![\w-])')
esc = lambda s: html.escape(str(s), quote=True)


# ---------- 읽기 ----------
def front(text):
    m = re.match(r'^---\n(.*?)\n---\n?', text, re.S)
    meta, key = {}, None
    if not m:
        return meta, text
    for line in m.group(1).splitlines():
        if re.match(r'^[a-z][a-z0-9_]*:', line):
            key, v = line.split(':', 1)
            v = v.strip().strip('"')
            meta[key] = v if v else []
        elif key and line.strip().startswith('- ') and isinstance(meta.get(key), list):
            meta[key].append(line.strip()[2:].strip())
    return meta, text[m.end():]


def sections(body):
    """## 제목 단위로 나눈다 → [(제목, 본문)]"""
    out, cur, buf = [], None, []
    for line in body.splitlines():
        if line.startswith('## '):
            if cur is not None:
                out.append((cur, '\n'.join(buf).strip()))
            cur, buf = line[3:].strip(), []
        else:
            buf.append(line)
    if cur is not None:
        out.append((cur, '\n'.join(buf).strip()))
    return out


def table_rows(body):
    for line in body.splitlines():
        s = line.strip()
        if s.startswith('|') and not re.match(r'^\|[\s\-:|]+\|$', s):
            yield [c.strip() for c in re.split(r'(?<!\\)\|', s)[1:-1]]


# ---------- ID 색인: 어느 쪽 어느 자리에서 정의했나 ----------
REG = {}  # ID → 출력 루트 기준 경로#앵커


def register(text, href):
    for h in re.findall(r'^#{2,4} .*?((?:[A-Z]{2,6}-)[A-Z0-9-]+)', text, re.M):
        if ID_RE.fullmatch(h):
            REG.setdefault(h, f'{href}#{h}')
    for r in table_rows(text):
        if r and ID_RE.fullmatch(r[0]):
            REG.setdefault(r[0], f'{href}#{r[0]}')


# ---------- 마크다운 → HTML ----------
def inline(s, root, here, skip=None):
    s = esc(s)
    codes = []
    s = re.sub(r'`([^`]+)`', lambda m: codes.append(m.group(1)) or f'\x00{len(codes) - 1}\x00', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)

    def link(m):
        t, u = m.group(1), html.unescape(m.group(2))
        if not re.match(r'^(https?:|#|mailto:)', u):  # 저장소 안 파일은 GitHub 원본으로
            p = (SRC / here).parent / u.split('#')[0]
            try:
                u = f'{REPO}/blob/main/{p.resolve().relative_to(SRC).as_posix()}'
            except ValueError:
                u = REPO
        ext = ' target="_blank" rel="noopener"' if u.startswith('http') else ''
        return f'<a href="{esc(u)}"{ext}>{t}</a>'
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, s)

    def idl(m):
        i = m.group(0)
        if i == skip or i not in REG:
            return i
        return f'<a class="idl" href="{root}{REG[i]}">{i}</a>'
    s = re.sub(r'(<a [^>]*>.*?</a>)|' + ID_RE.pattern, lambda m: m.group(1) or idl(m), s)
    s = re.sub(r'\x00(\d+)\x00', lambda m: f'<code>{codes[int(m.group(1))]}</code>', s)
    return s.replace('&lt;br&gt;', '<br>')


def md(text, root, here, toc=None):
    lines, out, i = text.splitlines(), [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1; continue
        if ln.startswith('```'):
            j = i + 1
            while j < len(lines) and not lines[j].startswith('```'):
                j += 1
            out.append('<pre><code>' + esc('\n'.join(lines[i + 1:j])) + '</code></pre>')
            i = j + 1; continue
        m = re.match(r'^(#{1,4}) (.*)', ln)
        if m:
            lv, t = len(m.group(1)), m.group(2).strip()
            if lv == 1:
                i += 1; continue  # 쪽 제목은 머리에서 쓴다
            ids = ID_RE.findall(t)
            aid = ids[0] if ids else 's' + str(len(out))
            if toc is not None and lv <= 3:
                toc.append((lv, aid, re.sub(r'`', '', t)))
            out.append(f'<h{lv} id="{aid}">{inline(t, root, here, skip=aid)}</h{lv}>')
            i += 1; continue
        if ln.lstrip().startswith('|'):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith('|'):
                rows.append(lines[i]); i += 1
            out.append(table('\n'.join(rows), root, here)); continue
        if re.match(r'^\s*([-*]|\d+\.) ', ln):
            tag = 'ol' if re.match(r'^\s*\d+\.', ln) else 'ul'
            items = []
            while i < len(lines) and re.match(r'^\s*([-*]|\d+\.) |^\s{2,}\S', lines[i]):
                t = re.sub(r'^\s*([-*]|\d+\.) ', '', lines[i])
                if re.match(r'^\s*([-*]|\d+\.) ', lines[i]) and not lines[i].startswith('   '):
                    items.append(t)
                else:
                    items[-1] += ' ' + t.strip()
                i += 1
            out.append(f'<{tag}>' + ''.join(f'<li>{inline(t, root, here)}</li>' for t in items) + f'</{tag}>')
            continue
        if ln.startswith('>'):
            buf = []
            while i < len(lines) and lines[i].startswith('>'):
                buf.append(lines[i].lstrip('> ')); i += 1
            out.append('<blockquote>' + inline(' '.join(buf), root, here) + '</blockquote>'); continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#|\||```|>|\s*([-*]|\d+\.) )', lines[i]):
            buf.append(lines[i].strip()); i += 1
        out.append('<p>' + inline(' '.join(buf), root, here) + '</p>')
    return '\n'.join(out)


def table(text, root, here):
    rows = list(table_rows(text))
    if not rows:
        return ''
    head, body = rows[0], rows[1:]
    idcol = [k for k, h in enumerate(head) if 'ID' in h or h in ('규칙', '공통 정책')]
    wide = len(head) >= 7
    th = ''.join(f'<th class="{"c-id" if k in idcol else ""}">{inline(h, root, here)}</th>' for k, h in enumerate(head))
    tr = []
    for r in body:
        rid = r[0] if r and ID_RE.fullmatch(r[0]) else ''
        tds = []
        for k, c in enumerate(r):
            cls = 'c-id' if k in idcol else ('c-desc' if k < len(head) and re.search(r'설명|내용|구성', head[k]) else '')
            if k == 0 and rid:
                tds.append(f'<td class="c-id c-key">{esc(c)}</td>'); continue
            if k in idcol and ',' in c:  # ID 여러 개는 한 줄에 하나씩 → 옆 칸으로 넘치지 않게
                c = '<br>'.join(x.strip() for x in c.split(','))
            tds.append(f'<td class="{cls}">{inline(c, root, here)}</td>')
        tr.append(f'<tr{f" id=\"{rid}\"" if rid else ""}>' + ''.join(tds) + '</tr>')
    hint = '<div class="tbl-hint">표가 넓습니다. 옆으로 밀어 봅니다 →</div>' if wide else ''
    return (hint + f'<div class="tbl{" wide" if wide else ""}"><table><thead><tr>{th}</tr></thead><tbody>'
            + ''.join(tr) + '</tbody></table></div>')


# ---------- 품질 결과 엑셀 ----------
def qa_read(folder):
    """qa/*.xlsx → 차수 목록(오래된 순) · 가장 늦은 차수의 결함 · 결정 필요 · 개선 제안"""
    try:
        import openpyxl
    except ImportError:
        return None
    files = sorted(folder.glob('*테스트결과 *차.xlsx')) if folder.exists() else []
    if not files:
        return None
    key = lambda x: (x.name[:6], int(re.search(r'(\d+)차', x.name).group(1)))
    files.sort(key=key)
    rounds, last = [], None
    for f in files:
        wb = openpyxl.load_workbook(f, data_only=True, read_only=True)
        sheet = lambda n: ([[c for c in r] for r in wb[n].iter_rows(values_only=True)] if n in wb.sheetnames else [])
        run = sheet('실행')
        col = len(run[0]) - 1 if run else 0
        res = [r[col] for r in run[1:] if r and r[0]]
        cnt = {k: res.count(k) for k in ('통과', '실패', '막힘') if res.count(k)}
        cnt['기타'] = len(res) - sum(cnt.values())
        rnd = f'{key(f)[1]}차'
        recs = lambda n: [dict(zip(s[0], r)) for s in [sheet(n)] if s for r in s[1:] if r and r[0]]
        last = dict(bugs=recs('결함'), decide=recs('결정 필요'), ux=recs('개선 제안'))
        rounds.append(dict(round=rnd, day='20' + f.name[:2] + '-' + f.name[2:4] + '-' + f.name[4:6], total=len(res), cnt=cnt,
                           file=f.name, bugs=len(last['bugs']),
                           open=sum(1 for b in last['bugs'] if b.get('상태') not in ('확인 완료', '재현 안 됨', '기획 변경'))))
    return dict(rounds=rounds, **last)


# ---------- 쪽 틀 ----------
CSS_V = '3'


def page(title, root, body, crumbs=(), wide=False, desc=''):
    cr = ''
    if crumbs:
        cr = '<nav class="crumb" aria-label="위치">' + ' <span>/</span> '.join(
            f'<a href="{root}{h}">{esc(t)}</a>' if h is not None else f'<b>{esc(t)}</b>' for t, h in crumbs) + '</nav>'
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc or HOME_META.get('lead', ''))}">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap">
<link rel="stylesheet" href="{root}assets/pf.css?v={CSS_V}"><meta name="color-scheme" content="light dark">
<script>try{{var t=localStorage.getItem('pf-theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}
function pfTheme(){{var d=document.documentElement,cur=d.dataset.theme||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'),n=cur==='dark'?'light':'dark';d.dataset.theme=n;try{{localStorage.setItem('pf-theme',n)}}catch(e){{}}}}</script>
</head><body class="{'is-wide' if wide else ''}">
<header class="top"><div class="top-in">
<a class="brand" href="{root}index.html"><span class="mark">기</span>기획 포트폴리오</a>
<nav class="topnav"><a href="{root}index.html#work">사례</a><a href="{root}index.html#how">일하는 방식</a><a href="{root}index.html#about">소개</a><a href="{REPO}" target="_blank" rel="noopener">GitHub ↗</a><button class="theme" type="button" aria-label="밝게 · 어둡게 바꾸기" onclick="pfTheme()"><svg class="moon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M13.5 9.5A5.5 5.5 0 1 1 6.5 2.5a4.5 4.5 0 0 0 7 7Z"/></svg><svg class="sun" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true"><circle cx="8" cy="8" r="3"/><path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1"/></svg></button></nav>
</div></header>
<main class="{'wide' if wide else ''}">{cr}{body}</main>
<footer class="foot"><div>{esc(HOME_META.get('note', ''))}</div><div><a href="{REPO}" target="_blank" rel="noopener">원본 저장소 ↗</a></div></footer>
</body></html>'''


def write(rel, text):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def badge(status):
    t, c = STATUS.get(status, (status or '-', 'mute'))
    return f'<span class="badge {c}">{esc(t)}</span>'


def stat(n, label, sub=''):
    return f'<div class="stat"><div class="n">{n}</div><div class="l">{esc(label)}</div>{f"<div class=s>{esc(sub)}</div>" if sub else ""}</div>'


# ---------- 시작 ----------
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
HOME_META, home_body = front((PF / 'home.md').read_text(encoding='utf-8'))

# 포털(사례 2)을 먼저 만든다. 포털 빌드가 실패해도 포트폴리오는 만든다
portal_ok = False
if (SRC / 'tools/site/build.py').exists():
    r = subprocess.run([sys.executable, str(SRC / 'tools/site/build.py'), str(SRC), str(OUT / 'portal')], capture_output=True, text=True)
    portal_ok = r.returncode == 0
    print(('포털: ' + r.stdout.strip().splitlines()[-1]) if portal_ok else '포털 빌드 실패\n' + r.stderr[-2000:])
(OUT / 'assets').mkdir(exist_ok=True)
shutil.copy(HERE / 'pf.css', OUT / 'assets/pf.css')
if (PF / 'img').exists():
    shutil.copytree(PF / 'img', OUT / 'assets/img')

# 사례 읽기
cases = []
for f in sorted((PF / 'cases').glob('*.md')):
    meta, body = front(f.read_text(encoding='utf-8'))
    meta['body'] = body
    meta['plans_data'] = []
    for d in meta.get('plans') or []:
        pdir = SRC / d
        docs = {}
        for k, fn, _, _ in DOCS:
            if fn and (pdir / fn).exists():
                docs[k] = front((pdir / fn).read_text(encoding='utf-8'))
        spec_meta = docs.get('spec', ({}, ''))[0]
        key = pdir.name
        title = re.sub(r'\s*기능정의서$', '', spec_meta.get('title', key))
        meta['plans_data'].append(dict(key=key, dir=d, title=title, code=spec_meta.get('code', ''),
                                       status=spec_meta.get('status', ''), docs=docs, qa=qa_read(pdir / 'qa'),
                                       href=f"work/{meta['key']}/{key}/"))
    pol = []
    if meta.get('policies'):
        for pf in sorted((SRC / meta['policies']).rglob('*.md')):
            pm, pb = front(pf.read_text(encoding='utf-8'))
            pol.append(dict(id=pm.get('id', pf.stem), title=pm.get('title', pf.stem), cat=pm.get('category', ''),
                            status=pm.get('status', ''), body=pb, path=pf.relative_to(SRC).as_posix(),
                            href=f"work/{meta['key']}/policies/{pm.get('id', pf.stem)}.html"))
    meta['pol'] = pol
    cases.append(meta)
cases.sort(key=lambda c: int(c.get('order', 99)))

# ID 색인
for c in cases:
    for p in c['plans_data']:
        for k, (m, b) in p['docs'].items():
            register(b, p['href'] + f'{k}.html')
    for q in c['pol']:
        REG.setdefault(q['id'], q['href'])
        register(q['body'], q['href'])


def count_ids(p, prefix):
    return sum(1 for r in table_rows(p['docs'].get(prefix[0], ({}, ''))[1]) if r and re.fullmatch(prefix[1], r[0]))


for c in cases:
    for p in c['plans_data']:
        p['n_fn'] = count_ids(p, ('spec', r'[A-Z]+-FN-[A-Z0-9-]+'))
        p['n_pl'] = len({h for h in re.findall(r'^## \d+\. ([A-Z]+-PL-[A-Z0-9-]+)', p['docs'].get('policy', ({}, ''))[1], re.M)}) or \
            count_ids(p, ('policy', r'[A-Z]+-PL-[A-Z0-9-]+'))
        p['n_sc'] = count_ids(p, ('screens', r'[A-Z]+-[A-Z]+-[A-Z]+-[A-Z]'))
        p['n_rq'] = count_ids(p, ('spec', r'[A-Z]+-RQ-\d+'))


def qa_line(q):
    if not q:
        return '품질 검사 전'
    r = q['rounds'][-1]
    return f"{r['round']}까지 · 결함 {r['bugs']}건 중 열림 {r['open']}건"


# ---------- 홈 ----------
def home():
    root = ''
    secs = dict(sections(home_body))
    tot = dict(fn=sum(p['n_fn'] for c in cases for p in c['plans_data']),
               pl=sum(p['n_pl'] for c in cases for p in c['plans_data']) + sum(len(c['pol']) for c in cases),
               sc=sum(p['n_sc'] for c in cases for p in c['plans_data']),
               tc=sum(len(p['qa']['rounds']) for c in cases for p in c['plans_data'] if p['qa']))
    counts = {'기능 정의': f"기능 {tot['fn']}개", '정책 정의': f"정책 {tot['pl']}개", '화면 설계': f"화면 {tot['sc']}개", '품질 검사': f"검사 {tot['tc']}차수"}
    first = next((p for c in cases for p in c['plans_data']), None)
    ex = {'기능 정의': 'spec.html', '정책 정의': 'policy.html', '화면 설계': '', '품질 검사': 'qa.html'}
    how = ''
    for i, r in enumerate(list(table_rows(secs.get('하는 일', '')))[1:], 1):
        h = (first['href'] + ex.get(r[0], '')) if first else '#'
        how += (f'<a class="how" href="{h}"><span class="step">{i:02d}</span><div class="how-h"><b>{esc(r[0])}</b><span>{esc(counts.get(r[0], ""))}</span></div>'
                f'<p>{esc(r[1])}</p><div class="how-o">{esc(r[2])} 보기 →</div></a>')
    cards = ''
    for c in cases:
        if c['key'] == 'portal':
            tags = ['문서 16', '자동 검사', '엑셀 · 워드 사본']
        else:
            tags = [f"기획 {len(c['plans_data'])}", f"품질 검사 {sum(len(p['qa']['rounds']) for p in c['plans_data'] if p['qa'])}차수"]
        meta = ''.join(f'<span class="chip">{esc(t)}</span>' for t in tags) + ('<span class="chip ok">직접 써 볼 수 있음</span>' if c.get('app') else '')
        img = f'assets/img/{c.get("cover")}.png'
        cards += (f'<a class="case" href="work/{c["key"]}/">'
                  f'<div class="shot"><div class="win"><span></span><span></span><span></span></div><img src="{img}" alt="{esc(c["title"])} 화면" loading="lazy"></div>'
                  f'<div class="case-b"><div class="kind">{esc(c.get("kind", ""))}</div><h3>{esc(c["title"])}</h3>'
                  f'<p>{esc(c.get("summary", ""))}</p><div class="chips">{meta}</div></div></a>')
    chain = ''
    if first:
        fn = next((r[0] for r in table_rows(first['docs']['spec'][1]) if re.fullmatch(r'[A-Z]+-FN-STA-\d+', r[0] or '')), None)
        steps = [('요구사항', 'INC-RQ-01', '무엇이 필요한가'), ('기능', fn or 'INC-FN-STA-01', '무엇을 할 수 있나'),
                 ('화면', 'OP-INC-LST-R', '어디서 하나'), ('정책', 'INC-PL-STS-01', '어떤 규칙인가'), ('공통 규칙', 'STATUS-01', '여러 화면이 같이 따르나')]
        chain = '<ol class="chain">' + ''.join(
            f'<li><span class="k">{esc(a)}</span><a class="idl" href="{REG.get(b, "#")}">{esc(b)}</a><span class="q">{esc(q)}</span></li>' for a, b, q in steps) + '</ol>'
    ab = secs.get('소개', '')
    about = ''
    if ab:
        ab_rows = list(table_rows(ab))[1:]
        ab_txt = '\n'.join(l for l in ab.splitlines() if l.strip() and not l.lstrip().startswith('|'))
        about = (f'<section id="about" class="sec about"><div><h2>소개</h2>{md(ab_txt, root, "portfolio/home.md")}</div>'
                 f'<dl>{"".join(f"<dt>{esc(r[0])}</dt><dd>{esc(r[1])}</dd>" for r in ab_rows)}</dl></section>')
    appc = next((c for c in cases if c.get('app')), None)
    hero_cta = f'<a class="btn pri" href="work/{appc["key"]}/app/" target="_blank" rel="noopener">운영 콘솔 직접 써 보기 ↗</a>' if appc else ''
    hero_shot = (f'<a class="hero-shot" href="work/{appc["key"]}/"><div class="win"><span></span><span></span><span></span></div>'
                 f'<img src="assets/img/{appc.get("cover")}.png" alt="{esc(appc["title"])} 화면"></a>') if appc else ''
    body = f'''
<section class="hero">
  <div class="eyebrow"><span class="dot"></span>서비스 기획 · 정책 · 화면 설계 · 품질</div>
  <h1>{esc(HOME_META.get("head1", ""))}<br><span>{esc(HOME_META.get("head2", ""))}</span></h1>
  <p class="lead">{esc(HOME_META.get("lead", ""))}</p>
  <div class="cta">{hero_cta}<a class="btn" href="#work">사례 보기</a></div>
  {hero_shot}
  <div class="hero-n">{stat(len(cases), "사례")}{stat(sum(len(c["plans_data"]) for c in cases), "기획")}{stat(len(REG), "연결된 ID")}{stat(sum(len(p["qa"]["rounds"]) for c in cases for p in c["plans_data"] if p["qa"]), "품질 검사 차수")}</div>
</section>
<section id="work" class="sec"><div class="sec-h"><h2>사례</h2><p>사례를 누르면 배경 · 접근 · 결과와 그 안의 문서를 봅니다.</p></div>
<div class="cases">{cards}</div></section>
<section id="how" class="sec"><div class="sec-h"><h2>일하는 방식</h2><p>기획 하나를 문서 넷과 품질 결과로 나눕니다. 카드를 누르면 실제 문서 예시로 갑니다.</p></div>
<div class="hows">{how}</div>
<h3 class="sub-h">문서는 ID로 이어집니다</h3>
<p class="muted">요구사항에서 공통 규칙까지 ID를 따라가면 근거가 끊기지 않습니다. 아래 ID를 누르면 그 ID를 정의한 자리로 갑니다.</p>
{chain}</section>
{about}'''
    write('index.html', page(HOME_META.get('title', '포트폴리오'), root, body))


# ---------- 사례 ----------
def case_page(c):
    root = '../../'
    secs = sections(c['body'])
    story = ''.join(f'<section class="story"><h2 id="s{i}">{esc(t)}</h2>{md(b, root, "portfolio/cases/x.md")}</section>' for i, (t, b) in enumerate(secs[:3]))
    facts = ''.join(f'<div><dt>{a}</dt><dd>{esc(c.get(b, ""))}</dd></div>' for a, b in (('역할', 'role'), ('범위', 'scope'), ('산출물', 'outputs'), ('기간', 'period')) if c.get(b))
    extra = ''
    TONE = {'정의 없음': 'warn', '기획 결함': 'bad', '결정 필요': ''}
    for t, b in secs[3:]:   # 배경 · 접근 · 결과 다음 구획: 표가 있으면 카드로 보인다
        rows = list(table_rows(b))
        intro = '\n'.join(l for l in b.splitlines() if l.strip() and not l.lstrip().startswith('|'))
        head, body_rows = (rows[0], rows[1:]) if rows else ([], [])
        if head[:1] == ['구분']:
            cards = ''.join(f'<div class="gap"><span class="badge {TONE.get(r[0], "")}">{esc(r[0])}</span><b>{esc(r[1])}</b><p>{esc(r[2])}</p>'
                            f'<span class="gap-id">{inline(r[3], root, "x") if len(r) > 3 else ""}</span></div>' for r in body_rows)
            inner = f'<div class="gaps">{cards}</div>'
        elif head[:1] == ['이름']:
            inner = '<div class="board">' + ''.join(f'<div><b>{esc(r[0])}</b><p>{esc(r[1])}</p></div>' for r in body_rows) + '</div>'
        else:
            inner = md(b, root, 'portfolio/cases/x.md')
            intro = ''
        extra += f'<section class="sec"><div class="sec-h"><h2>{esc(t)}</h2><p>{esc(intro)}</p></div>{inner}</section>'
    feat = ''
    if c.get('feature'):
        app_btn = f'<div class="cta"><a class="btn" href="app/" target="_blank" rel="noopener">켜서 확인해 보기 ↗</a></div>' if c.get('app') else ''
        feat = (f'<section class="sec feature"><div><div class="kind">기획 ID 보기</div><h2>{esc(c.get("feature_title", ""))}</h2>'
                f'<p>{esc(c.get("feature_text", ""))}</p>{app_btn}</div>'
                f'<figure><img src="{root}assets/img/{c["feature"]}.png" alt="기획 ID 보기를 켠 화면" loading="lazy"></figure></section>')
    if c.get('hero'):   # 기기 목업이 있으면 대표 화면 자리에 틀 없이 놓는다
        cover = f'<figure class="cover mock-hero"><img src="{root}assets/img/{c["hero"]}.png" alt="{esc(c["title"])} 노트북 · 모니터 화면"></figure>'
    else:
        cover = f'<figure class="cover"><img src="{root}assets/img/{c.get("cover")}.png" alt="{esc(c["title"])} 대표 화면"></figure>'
    mocks = ''
    for m in c.get('mocks') or []:
        f, t, d = (m.split('|') + ['', ''])[:3]
        mocks += (f'<section class="sec"><div class="sec-h"><h2>{esc(t)}</h2><p>{esc(d)}</p></div>'
                  f'<figure class="mock"><img src="{root}assets/img/{f}.png" alt="{esc(t)}" loading="lazy"></figure></section>')
    plans = ''
    if c['plans_data']:
        rows = ''
        for p in c['plans_data']:
            rows += (f'<a class="plan" href="{p["key"]}/"><div class="plan-t"><span class="code">{esc(p["code"])}</span><b>{esc(p["title"])}</b>{badge(p["status"])}</div>'
                     f'<div class="plan-m">요구사항 {p["n_rq"]} · 기능 {p["n_fn"]} · 정책 {p["n_pl"]} · 화면 {p["n_sc"]}</div>'
                     f'<div class="plan-q">{esc(qa_line(p["qa"]))}</div><span class="go">→</span></a>')
        plans = f'<section class="sec"><div class="sec-h"><h2>기획</h2><p>기획마다 기능 정의서 · 정책 정의서 · 화면 목록 · 화면 설계서 · 품질 결과가 한 묶음입니다.</p></div><div class="plans">{rows}</div></section>'
    pol = ''
    if c['pol']:
        pol = '<section class="sec"><div class="sec-h"><h2>공통 정책</h2><p>여러 기획이 함께 따르는 규칙입니다. 기획의 정책 정의서는 이 규칙 ID를 가리킵니다.</p></div><div class="pols">' + ''.join(
            f'<a class="pol" href="policies/{q["id"]}.html"><span class="code">{esc(q["id"])}</span><b>{esc(q["title"])}</b><span class="muted">{esc(q["cat"])}</span></a>' for q in c['pol']) + '</div></section>'
    cta = ''
    if c.get('link'):
        cta = (f'<div class="cta"><a class="btn pri" href="{root}{c["link"]}">포털 열어 보기</a>'
               f'<a class="btn" href="{REPO}/tree/main/tools/site" target="_blank" rel="noopener">빌드 코드 ↗</a></div>') if portal_ok else ''
    else:
        first = c['plans_data'][0] if c['plans_data'] else None
        if first:
            pri = (f'<a class="btn pri" href="app/" target="_blank" rel="noopener">운영 콘솔 직접 써 보기 ↗</a>' if c.get('app')
                   else f'<a class="btn pri" href="{first["key"]}/prototype.html" target="_blank" rel="noopener">화면 설계서 바로 열기 ↗</a>')
            cta = f'<div class="cta">{pri}<a class="btn" href="{first["key"]}/">{esc(first["title"])} 문서 보기</a></div>'
    body = f'''
<section class="case-hero"><div class="kind">{esc(c.get("kind", ""))}</div><h1>{esc(c["title"])}</h1>
<p class="lead">{esc(c.get("summary", ""))}</p><dl class="facts">{facts}</dl>{cta}</section>
{cover}
<div class="stories">{story}</div>
{mocks}{feat}{extra}{plans}{pol}'''
    write(f'work/{c["key"]}/index.html', page(c['title'] + ' · 기획 포트폴리오', root, body,
                                              crumbs=[('홈', 'index.html'), (c['title'], None)], desc=c.get('summary', '')))


# ---------- 기획 · 문서 ----------
def side(c, p, cur, root):
    items = [('', '개요')] + [(k, t) for k, fn, t, _ in DOCS if (k in p['docs']) or (k == 'qa' and p['qa'])]
    sub = ''.join(f'<a class="{"on" if cur == k else ""}" href="{root}{p["href"]}{k + ".html" if k else ""}">{esc(t)}</a>' for k, t in items)
    sub += f'<a href="{root}{p["href"]}prototype.html" target="_blank" rel="noopener">화면 설계서 ↗</a>'
    others = ''.join(f'<a href="{root}{o["href"]}">{esc(o["title"])}</a>' for o in c['plans_data'] if o is not p)
    pol = ''.join(f'<a href="{root}{q["href"]}">{esc(q["title"])}</a>' for q in c['pol'])
    return (f'<aside class="side"><div class="side-g"><div class="side-t">{esc(p["title"])}</div>{sub}</div>'
            + (f'<div class="side-g"><div class="side-t">다른 기획</div>{others}</div>' if others else '')
            + (f'<div class="side-g"><div class="side-t">공통 정책</div>{pol}</div>' if pol else '') + '</aside>')


def tocbox(toc):
    if not toc:
        return ''
    return '<nav class="toc"><div class="side-t">이 문서 목차</div>' + ''.join(
        f'<a class="l{lv}" href="#{a}">{inline(t, "", "x")}</a>'.replace('<a class="idl"', '<span').replace('</a></a>', '</span></a>') for lv, a, t in toc) + '</nav>'


def key_rules(p, root):
    """정책 정의서에서 상태 흐름 표와 우선순위 · 목표 표를 찾아 「핵심 규칙 한눈에」로 그린다. 없으면 빈 문자열"""
    pol = p['docs'].get('policy', ({}, ''))[1]
    blocks = []
    for title, body in sections(pol):
        pid = (ID_RE.findall(title) or [''])[0]
        rows = list(table_rows(body))
        if not rows:
            continue
        head, rs = rows[0], rows[1:]
        notes = ' '.join(l.strip()[2:] for l in body.splitlines() if l.strip().startswith('- '))[:160]
        idl = f'<a class="idl" href="{root}{REG[pid]}">{pid}</a>' if pid in REG else ''
        if head[0] == '상태' and len(head) >= 4:
            tone = ['info', 'warn', 'ok', 'mute']
            cells = ''.join(f'<div class="flow-s {tone[i % 4]}"><b>{esc(r[0])}</b><span>{esc(r[2])}</span><span class="who">{esc(r[3])}</span></div>' for i, r in enumerate(rs))
            blocks.append(f'<div class="rule"><div class="rule-h"><b>{esc(title.split("·")[-1].strip())}</b>{idl}</div><div class="flow">{cells}</div><p>{esc(notes)}</p></div>')
        elif head[0] == '우선순위' and len(head) >= 3:
            trs = ''.join(f'<tr><td><b>{esc(r[0])}</b></td><td class="r">{esc(r[1])}</td><td>{esc(r[2])}</td></tr>' for r in rs)
            blocks.append(f'<div class="rule"><div class="rule-h"><b>{esc(title.split("·")[-1].strip())}</b>{idl}</div><table class="mini">{trs}</table><p>{esc(notes)}</p></div>')
    if not blocks:
        return ''
    return ('<section><h2 class="h2">핵심 규칙 한눈에</h2><p class="muted" style="margin:-8px 0 20px">정책 정의서에서 가장 중요한 규칙입니다. 화면과 동작은 모두 이 규칙을 따릅니다.</p>'
            f'<div class="rules">{"".join(blocks)}</div></section>')


def plan_pages(c, p):
    root = '../../../'
    base = f'work/{c["key"]}/{p["key"]}/'
    (OUT / base).mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / p['dir'] / 'screens/prototype.html', OUT / base / 'prototype.html')
    crumbs = [('홈', 'index.html'), (c['title'], f'work/{c["key"]}/'), (p['title'], None)]
    # 개요
    spec = p['docs'].get('spec', ({}, ''))[1]
    ov = dict(sections(spec)).get('1. 개요', '')
    q = p['qa']
    tiles = stat(p['n_rq'], '요구사항') + stat(p['n_fn'], '기능') + stat(p['n_pl'], '정책') + stat(p['n_sc'], '화면')
    if q:
        last = q['rounds'][-1]
        rate = round(100 * last['cnt'].get('통과', 0) / max(1, last['cnt'].get('통과', 0) + last['cnt'].get('실패', 0)))
        tiles += stat(f'{rate}%', f'{last["round"]} 통과율', f'테스트 {last["total"]}개') + stat(f'{last["open"]}/{last["bugs"]}', '열린 결함', '열림 / 전체')
    cards = ''.join(
        f'<a class="doc" href="{k}.html"><b>{esc(t)}</b><p>{esc(d)}</p></a>' for k, fn, t, d in DOCS if (k in p['docs']) or (k == 'qa' and q))
    body = f'''<div class="docwrap">{side(c, p, '', root)}<article class="doc-main">
<div class="doc-head"><div class="kind">{esc(c["title"])} · {esc(p["code"])}</div><h1>{esc(p["title"])}</h1>{badge(p["status"])}
<div class="doc-src"><a href="{REPO}/tree/main/{p["dir"]}" target="_blank" rel="noopener">원본 폴더 ↗</a></div></div>
<div class="stats">{tiles}</div>
<section class="prose">{md(ov, root, p["dir"] + "/spec.md")}</section>
{key_rules(p, root)}
<section class="proto"><div class="proto-h"><h2>화면 설계서</h2><a class="btn" href="prototype.html" target="_blank" rel="noopener">새 창으로 크게 보기 ↗</a></div>
<p class="muted">예시 데이터로 움직이는 화면입니다. 탭 · 필터 · 행을 눌러 볼 수 있고, 오른쪽 번호 설명에 기능 · 정책 ID가 붙어 있습니다.</p>
<div class="frame" data-w="1680" data-h="1050"><iframe src="prototype.html" title="{esc(p["title"])} 화면 설계서" loading="lazy"></iframe></div>
<script>(()=>{{const f=document.querySelector('.frame'),i=f.querySelector('iframe'),W=+f.dataset.w,H=+f.dataset.h;
const fit=()=>{{const s=f.clientWidth/W;i.style.transform='scale('+s+')';f.style.height=(H*s)+'px'}};new ResizeObserver(fit).observe(f);fit()}})()</script></section>
<section><h2 class="h2">문서</h2><div class="docs">{cards}</div></section>
</article></div>'''
    write(base + 'index.html', page(f'{p["title"]} · {c["title"]}', root, body, crumbs, wide=True))
    # 문서
    for k, fn, t, d in DOCS:
        if k == 'qa':
            if q:
                qa_page(c, p, base, root, crumbs)
            continue
        if k not in p['docs']:
            continue
        m, b = p['docs'][k]
        toc = []
        html_body = md(b, root, f'{p["dir"]}/{fn}', toc)
        body = f'''<div class="docwrap">{side(c, p, k, root)}<article class="doc-main">
<div class="doc-head"><div class="kind">{esc(p["title"])} · {esc(m.get("id", ""))}</div><h1>{esc(t)}</h1>{badge(m.get("status", ""))}
<span class="muted ver">{esc(m.get("release", ""))}</span>
<div class="doc-src"><a href="{REPO}/blob/main/{p["dir"]}/{fn}" target="_blank" rel="noopener">원본 md ↗</a></div></div>
<div class="prose">{html_body}</div></article>{tocbox(toc)}</div>'''
        write(base + f'{k}.html', page(f'{t} · {p["title"]}', root, body, crumbs[:-1] + [(p['title'], p['href']), (t, None)], wide=True))


def qa_page(c, p, base, root, crumbs):
    q = p['qa']
    (OUT / base / 'qa').mkdir(exist_ok=True)
    rows = ''
    for r in q['rounds']:
        shutil.copy(SRC / p['dir'] / 'qa' / r['file'], OUT / base / 'qa' / r['file'])
        ok, ng = r['cnt'].get('통과', 0), r['cnt'].get('실패', 0)
        rate = round(100 * ok / max(1, ok + ng))
        bar = f'<div class="bar"><i style="width:{rate}%"></i></div>'
        rows += (f'<tr><td><b>{r["round"]}</b></td><td>{r["day"]}</td><td class="r">{r["total"]}</td><td class="r">{ok}</td><td class="r">{ng}</td>'
                 f'<td class="r">{r["cnt"].get("막힘", 0) + r["cnt"].get("기타", 0)}</td><td>{bar}<span class="r small">{rate}%</span></td>'
                 f'<td class="r">{r["open"]} / {r["bugs"]}</td><td><a href="qa/{html.escape(r["file"])}" download>엑셀</a></td></tr>')
    runs = ('<div class="tbl"><table><thead><tr><th>차수</th><th>날짜</th><th class="r">실행</th><th class="r">통과</th><th class="r">실패</th>'
            '<th class="r">막힘 · 기타</th><th>통과율</th><th class="r">열린 결함</th><th>원본</th></tr></thead><tbody>' + rows + '</tbody></table></div>')

    def recs(lst, cols):
        if not lst:
            return '<p class="muted">없음</p>'
        th = ''.join(f'<th>{esc(h)}</th>' for h in cols)
        tr = ''
        for x in lst:
            tds = ''
            for h in cols:
                v = x.get(h) or '-'
                if h == '상태' or h == '결정':
                    cls = 'ok' if v in ('확인 완료', '반영', '재현 안 됨') else ('bad' if v in ('수정 필요', '신규') else 'mute')
                    v = f'<span class="badge {cls}">{esc(v)}</span>'
                elif h == '심각도':
                    v = f'<span class="sev {"hi" if v in ("치명", "중요") else ""}">{esc(v)}</span>'
                else:
                    v = inline(str(v), root, 'x')
                short = h == 'ID' or len(str(x.get(h) or '-')) <= 8
                tds += f'<td class="{"c-id" if short else ""}">{v}</td>'
            tr += f'<tr>{tds}</tr>'
        return f'<div class="tbl"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'
    last = q['rounds'][-1]['round']
    CLOSED = ('확인 완료', '재현 안 됨', '기획 변경')
    SEV = {'치명': 0, '중요': 1, '보통': 2, '낮음': 3}

    def by_owner(bugs):
        out = ''
        for who in sorted({b.get('담당') or '기타' for b in bugs}, key=lambda w: ('기획', '디자인', '개발').index(w) if w in ('기획', '디자인', '개발') else 9):
            mine = sorted([b for b in bugs if (b.get('담당') or '기타') == who], key=lambda b: (b.get('상태') in CLOSED, SEV.get(b.get('심각도'), 9)))
            n_open = sum(1 for b in mine if b.get('상태') not in CLOSED)
            rows = ''.join(f'<li><span class="gid">{esc(b.get("ID"))}</span><span class="gt">{esc(b.get("제목"))}{" · " + esc(b.get("심각도")) if b.get("심각도") in ("치명", "중요") else ""}</span>'
                           f'<span class="badge {"ok" if b.get("상태") in CLOSED else "bad"}">{esc(b.get("상태"))}</span></li>' for b in mine)
            out += f'<div class="owner"><div class="owner-h"><b>{esc(who)}이 고칠 것</b><span>{len(mine)}건 · 열림 {n_open}</span></div><ul>{rows}</ul></div>'
        return f'<div class="owners">{out}</div>'
    r0, r1 = q['rounds'][0], q['rounds'][-1]
    pr = lambda r: round(100 * r['cnt'].get('통과', 0) / max(1, r['cnt'].get('통과', 0) + r['cnt'].get('실패', 0)))
    tiles = (stat(f'{pr(r1)}%', f'{r1["round"]} 통과율', f'{r0["round"]} {pr(r0)}%에서' if len(q['rounds']) > 1 else '')
             + stat(f'{r1["open"]} / {r1["bugs"]}', '열린 결함 / 전체') + stat(len(q['decide']), '결정 필요')
             + stat(len(q['ux']), '개선 제안'))
    body = f'''<div class="docwrap">{side(c, p, 'qa', root)}<article class="doc-main">
<div class="doc-head"><div class="kind">{esc(p["title"])}</div><h1>품질 결과</h1>
<div class="doc-src"><a href="{REPO}/tree/main/{p["dir"]}/qa" target="_blank" rel="noopener">원본 엑셀 폴더 ↗</a></div></div>
<p class="lead-s">테스트 결과 엑셀을 차수별로 읽어 요약했습니다. 통과율은 통과 ÷ (통과 + 실패)이고, 결함 · 결정 필요 · 개선 제안은 가장 늦은 차수({last}) 기준입니다.</p>
<div class="stats">{tiles}</div>
<div class="prose">
<h2 id="runs">차수별 실행</h2>{runs}
<h2 id="bugs">결함 · 고칠 곳별</h2><p class="muted">열린 것 먼저, 그다음 심각도 순입니다. 「확인 완료」는 다음 차수에서 고쳐진 것을 확인한 건입니다.</p>{by_owner(q["bugs"])}
<h3>전체 결함</h3>{recs(q["bugs"], ["ID", "제목", "유형", "심각도", "상태", "담당", "화면", "관련 TC"])}
<h2 id="decide">결정 필요</h2><p class="muted">결함이 아니라 정해지지 않은 것. 물을 곳과 추천안을 함께 적습니다.</p>{recs(q["decide"], ["ID", "항목", "물을 곳", "지금 동작", "선택지", "추천"])}
<h2 id="ux">개선 제안</h2>{recs(q["ux"], ["ID", "제안", "관찰", "효과", "비용", "결정"])}
</div></article>{tocbox([(2, "runs", "차수별 실행"), (2, "bugs", "결함"), (2, "decide", "결정 필요"), (2, "ux", "개선 제안")])}</div>'''
    write(base + 'qa.html', page(f'품질 결과 · {p["title"]}', root, body, crumbs[:-1] + [(p['title'], p['href']), ('품질 결과', None)], wide=True))


def policy_pages(c):
    root = '../../../'
    for q in c['pol']:
        toc = []
        h = md(q['body'], root, q['path'], toc)
        others = ''.join(f'<a class="{"on" if o is q else ""}" href="{root}{o["href"]}">{esc(o["title"])}</a>' for o in c['pol'])
        plans = ''.join(f'<a href="{root}{p["href"]}">{esc(p["title"])}</a>' for p in c['plans_data'])
        used = [p['title'] for p in c['plans_data'] if q['id'] in p['docs'].get('policy', ({}, ''))[1]]
        body = f'''<div class="docwrap"><aside class="side"><div class="side-g"><div class="side-t">공통 정책</div>{others}</div><div class="side-g"><div class="side-t">기획</div>{plans}</div></aside>
<article class="doc-main"><div class="doc-head"><div class="kind">공통 정책 · {esc(q["cat"])}</div><h1>{esc(q["title"])}</h1>{badge(q["status"])}<span class="muted ver">{esc(q["id"])}</span>
<div class="doc-src"><a href="{REPO}/blob/main/{q["path"]}" target="_blank" rel="noopener">원본 md ↗</a></div></div>
{f'<p class="lead-s">따르는 기획: {esc(" · ".join(used))}</p>' if used else ''}
<div class="prose">{h}</div></article>{tocbox(toc)}</div>'''
        write(q['href'], page(f'{q["title"]} · 공통 정책', root, body,
                              [('홈', 'index.html'), (c['title'], f'work/{c["key"]}/'), ('공통 정책', None), (q['title'], None)], wide=True))


def app_copy(c):
    # 기획서대로 동작하는 제품(app/)을 사례 아래 app/ 에 둔다. 제품 양식 · 예시 데이터를 같은 폴더에 함께 넣는다
    src = SRC / c['app']
    if not src.exists():
        return
    dst = OUT / 'work' / c['key'] / 'app'
    shutil.copytree(src, dst)
    shutil.copy(SRC / 'design/kit.css', dst / 'kit.css')
    shutil.copy(SRC / 'data/all.json', dst / 'data.json')


home()
for c in cases:
    if c.get('app'):
        app_copy(c)
    case_page(c)
    for p in c['plans_data']:
        plan_pages(c, p)
    policy_pages(c)
n = sum(1 for _ in OUT.rglob('*.html'))
print(f'포트폴리오: 사례 {len(cases)} · 기획 {sum(len(c["plans_data"]) for c in cases)} · ID {len(REG)} · 쪽 {n}')
