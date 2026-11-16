# 기획 문서 대조: 기능정의서 · 정책정의서 · 화면 목록 · 기획서가 서로 맞는지 본다
#   python3 tools/check/lists.py features/<서비스>/<기획>
#   python3 tools/check/lists.py --all      기획 코드 · ID가 기획끼리 겹치지 않는지
# PR 전에 돌린다. 「오류」가 0건이어야 검토 요청을 연다. 「확인」은 기획자가 보고 판단한다.
# 표 양식(0.2)과 단락 양식(0.1, #### 기능 ID)을 다 읽는다.
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rules import load as load_rules  # noqa: E402

NEED_META = ['id', 'title', 'type', 'code', 'status', 'owner', 'release']
NEED_FN = ['기능 ID', '대분류', '중분류', '기능명', '기능 설명', '화면 ID', '우선순위', '권한', '정책 ID']
# 구분(이전 판 대비)은 기획서 대비표에 없는 기능이 많아 비어 있으면 「확인」으로 알린다
NEED_SCR = ['화면 ID', '화면명', '계층', '진입 경로', '기능 ID']
PRI, GUBUN = {'M', 'S', 'C', 'W', '결정 대기'}, {'신규', '변경', '유지', '폐지'}
EMPTY = {'', '—', '-', '[', '–'}

err, warn = [], []


def front(text):
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(':')
            if re.match(r'^[a-z_]+$', k):
                meta[k] = re.sub(r'\s+#.*$', '', v).strip().strip('"')
        text = text[m.end():]
    return meta, text


def tables(body):
    # (절 제목, 머리 칸, 줄들)
    sec, head, rows, out = '', None, [], []
    for line in body.splitlines() + ['']:
        if line.startswith('|'):
            c = [x.strip() for x in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
            if re.match(r'^\|[\s\-:|]+\|$', line.strip()):
                continue
            if head is None:
                head = c
            else:
                rows.append(dict(zip(head, c)))
            continue
        if head is not None:
            out.append((sec, head, rows))
            head, rows = None, []
        if re.match(r'^#{1,4} ', line):
            sec = line.lstrip('#').strip()
    return out


def ids(s):
    # 칸 안의 ID 들. 「FN-QTA-001, 002」 처럼 번호만 이어 쓴 것도 편다
    out, last = [], None
    for tok in re.split(r'[,·]\s*', s or ''):
        tok = tok.strip().strip('`')
        m = re.match(r'^([A-Z][A-Z0-9-]*?-)(\d+)$', tok)
        if m:
            last = m.group(1)
            out.append(tok)
        elif re.fullmatch(r'\d+', tok) and last:
            out.append(last + tok)
        elif re.fullmatch(r'[AU]C-[A-Z0-9-]+', tok):
            out.append(tok)
    return out


def rel(p):
    try:
        return p.relative_to(ROOT)
    except ValueError:
        return p


def blank(v):
    v = (v or '').strip()
    return v in EMPTY or bool(re.fullmatch(r'\[[^\]]*\]', v))  # 「[기획 이름]」 같은 양식 자리표시


def main(d):
    d = Path(d).resolve()
    files = {k: d / f for k, f in (('spec', 'spec.md'), ('policy', 'policy.md'), ('screens', 'screens/index.md'))}
    proto = d / 'screens' / 'prototype.html'
    text = {}
    for k, f in files.items():
        if not f.exists():
            err.append(f'{rel(f)} 없음')
            continue
        meta, body = front(f.read_text())
        text[k] = body
        for m in NEED_META:
            if m == 'owner' and meta.get('status') == 'sample':
                continue  # 샘플은 담당자를 모를 수 있다 (절차 I)
            if blank(meta.get(m)):
                err.append(f'{k}: 문서 정보 「{m}」 비어 있음')
        code = meta.get('code', '')
    if not proto.exists():
        err.append('screens/prototype.html 없음')
    code = front(files['spec'].read_text())[0].get('code', '') if files['spec'].exists() else ''

    # 기능
    fns, nogubun = {}, []
    for sec, head, rows in tables(text.get('spec', '')):
        if head and head[0] == '기능 ID':
            for r in rows:
                fid = r['기능 ID']
                if fid in fns:
                    err.append(f'기능 ID 중복: {fid}')
                fns[fid] = r
                for c in NEED_FN:
                    if c in head and blank(r.get(c)) and not (c in ('권한', '정책 ID') and (r.get(c) or '').strip() == '—') \
                            and not (c in ('화면 ID', '정책 ID') and (r.get('권한') or '').strip() == '—'):
                        err.append(f'{fid}: 「{c}」 비어 있음')
                if r.get('우선순위') and r['우선순위'] not in PRI:
                    err.append(f"{fid}: 우선순위 「{r['우선순위']}」 (M · S · C · W · 결정 대기)")
                if '구분' in head and blank(r.get('구분')):
                    nogubun.append(fid)
                if r.get('구분') and r['구분'] not in GUBUN:
                    err.append(f"{fid}: 구분 「{r['구분']}」 (신규 · 변경 · 유지 · 폐지)")
    for m in re.finditer(r'^#### ([A-Z]{3}-FN-[A-Z]+-\d+) (.+)$', text.get('spec', ''), re.M):
        fns.setdefault(m.group(1), {'기능 ID': m.group(1), '기능명': m.group(2), '_para': True})
    for fid in fns:
        if code and not fid.startswith(code + '-FN-'):
            err.append(f'{fid}: 기능 ID는 「{code}-FN-영역-번호」')

    # 정책 · 미결정 · 요구사항 · 화면
    pls = set(re.findall(r'^## \d+\. ([A-Z]{3}-PL-[A-Z]+-\d+) ·', text.get('policy', ''), re.M))
    oqs, rqs, scrs, follow = {}, {}, {}, set()
    for sec, head, rows in tables(text.get('policy', '')):
        for r in rows:
            first = r.get(head[0], '')
            if re.fullmatch(r'[A-Z]{3}-OQ-\d+', first):
                oqs[first] = r
            if '규칙 ID' in head:
                follow.update(ids(r['규칙 ID']))
    for sec, head, rows in tables(text.get('spec', '')):
        for r in rows:
            first = r.get(head[0], '')
            if re.fullmatch(r'[A-Z]{3}-RQ-\d+', first):
                rqs[first] = r
    for sec, head, rows in tables(text.get('screens', '')):
        if head and head[0] == '화면 ID':
            for r in rows:
                scrs[r['화면 ID']] = r
                for c in NEED_SCR:
                    if c in head and blank(r.get(c)):
                        err.append(f"화면 {r['화면 ID']}: 「{c}」 비어 있음")

    common = {r['id']: (p['id'], r['kind']) for p in load_rules() for r in p['rules']}
    alltext = '\n'.join(text.values())

    def known(i):
        return (i in fns or i in pls or i in oqs or i in rqs or i in scrs or i in common)

    # 문서 안의 모든 ID 참조가 정의돼 있나
    for i in sorted(set(re.findall(r'\b(?:[A-Z]{3}-(?:FN|PL|RQ|OQ)-[A-Z0-9-]*\d+|[AU]C-[A-Z0-9]+(?:-[A-Z0-9]+)+)\b', alltext))):
        i = re.sub(r'-(?=$)', '', i)
        if not known(i) and not re.fullmatch(r'[A-Z]{3}-(FN|PL)-[A-Z]+', i):
            err.append(f'정의되지 않은 ID 참조: {i}')
    for i in sorted(set(re.findall(r'\b([A-Z][A-Z0-9]{1,11}-(?:M?\d+|U\d+))\b', alltext))):
        pre = i.rsplit('-', 1)[0]
        if pre in {k.rsplit('-', 1)[0] for k in common} and i not in common:
            err.append(f'공통 정책에 없는 규칙 ID: {i}')

    # 공통 정책
    for i in sorted(follow):
        if i in common and common[i][1] != 'rule':
            warn.append(f'따르는 공통 규칙 {i}({common[i][0]})가 아직 미확정')
    if text.get('policy') and not follow:
        warn.append('정책정의서 1.2 「따르는 공통 정책」이 비어 있음 (tools/check/rules.py 로 대조)')

    # 기능 ↔ 화면
    on_screen = set()
    for sid, r in scrs.items():
        got = ids(r.get('기능 ID', ''))
        on_screen.update(got)
        for f in got:
            if f not in fns:
                err.append(f'화면 {sid}: 기능 목록에 없는 {f}')
        if not got and '기능 ID' in r:
            warn.append(f'화면 {sid}: 들어가는 기능 없음')
    for fid, r in fns.items():
        if r.get('_para'):
            continue
        for s in ids(r.get('화면 ID', '')):
            if s in scrs and scrs[s].get('기능 ID') is not None and fid not in ids(scrs[s].get('기능 ID', '')):
                warn.append(f'{fid}: 기능 목록은 화면 {s}라는데 화면 목록 {s}에는 이 기능이 없음')
        if r.get('권한') != '—' and not any(s in scrs for s in ids(r.get('화면 ID', ''))) and r.get('구분') != '폐지':
            warn.append(f'{fid}: 화면 목록에 있는 화면이 연결되지 않음')

    if nogubun:
        warn.append(f'구분(신규 · 변경 · 유지) 비어 있음 {len(nogubun)}개: ' + ', '.join(nogubun))

    # 요구사항 · 미결정
    for i, r in rqs.items():
        if blank(r.get('연결 기능', '')):
            warn.append(f'{i}: 연결 기능 없음')
    for i, r in oqs.items():
        for c in ('담당', '언제까지'):
            if c in r and blank(r[c]):
                warn.append(f'{i}: 「{c}」 비어 있음')

    # 기획서에 화면 ID가 있나
    if proto.exists():
        html = proto.read_text(errors='ignore')
        for r in sorted({r for r in re.findall(r'<(?:link[^>]+href|script[^>]+src|img[^>]+src)=["\']([^"\'#?]+)', html)
                         if not re.match(r'^(https?:|data:|blob:|//|javascript:)', r) and not (proto.parent / r).exists()}):
            err.append(f'기획서가 저장소에 없는 파일을 불러옴: {r} (파일 안에 넣어야 혼자 열림)')
        for sid in scrs:
            if sid not in html:
                warn.append(f'화면 {sid}: 기획서 HTML에 이 화면 ID가 없음')

    print(f'# {rel(d)}')
    print(f'기능 {len(fns)} · 화면 {len(scrs)} · 정책 {len(pls)} · 요구사항 {len(rqs)} · 미결정 {len(oqs)} · 따르는 공통 규칙 {len(follow)}')
    print(f'\n## 오류 {len(err)}건' + ('' if err else ' — 없음'))
    for e in err:
        print('- ' + e)
    print(f'\n## 확인 {len(warn)}건' + ('' if warn else ' — 없음'))
    for w in warn:
        print('- ' + w)
    return 1 if err else 0


def check_all():
    # 저장소 전체: 문서 ID 가 겹치지 않는지, 기능 · 정책 · 요구사항 · 미결정 ID가 두 기획에 함께 정의되지 않았는지
    seen, codes, docs, bad = {}, {}, {}, []
    for spec in sorted((ROOT / 'features').glob('*/*/spec.md')):
        d = spec.parent
        code = front(spec.read_text())[0].get('code', '')
        # 같은 제품 영역의 기획은 코드를 함께 쓴다(운영 규칙 3장). 겹치면 안 되는 것은 ID 와 문서 ID 다
        doc_id = front(spec.read_text())[0].get('id', '')
        if doc_id in docs:
            bad.append(f'문서 ID {doc_id} 가 두 기획에 있음: {rel(docs[doc_id])} · {rel(d)}')
        docs[doc_id] = d
        codes.setdefault(code, d)
        for f in (d / 'spec.md', d / 'policy.md'):
            if not f.exists():
                continue
            body = front(f.read_text())[1]
            mine = set(re.findall(r'^#### ([A-Z]{3}-FN-[A-Z]+-\d+)', body, re.M))
            mine |= set(re.findall(r'^## \d+\. ([A-Z]{3}-PL-[A-Z]+-\d+) ·', body, re.M))
            for sec, head, rows in tables(body):
                for r in rows:
                    first = r.get(head[0], '')
                    if re.fullmatch(r'[A-Z]{3}-(FN-[A-Z]+|RQ|OQ)-\d+', first):
                        mine.add(first)
            for i in mine:
                if i in seen and seen[i] != d:
                    bad.append(f'{i} 가 두 기획에 정의됨: {rel(seen[i])} · {rel(d)}')
                seen.setdefault(i, d)
            for i in mine:
                if code and not i.startswith(code + '-'):
                    bad.append(f'{rel(d)}: {i} 의 앞머리가 기획 코드 {code} 와 다름')
    print(f'# 저장소 전체 · 기획 {len(docs)} · ID {len(seen):,}')
    print(f'\n## 오류 {len(bad)}건' + ('' if bad else ' — 없음'))
    for b in bad:
        print('- ' + b)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(check_all() if sys.argv[1:] == ['--all'] else main(sys.argv[1]))
