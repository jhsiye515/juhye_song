# 공통 정책 규칙 색인: policies/ 의 규칙 행을 한 표로 뽑는다
#   python3 tools/check/rules.py                 정책 문서 목록(정책 · 분야 · 규칙 수 · 다루는 것)
#   python3 tools/check/rules.py 테이블 시간      내용 · 절 · 정책 이름에 낱말이 들어간 규칙
#   python3 tools/check/rules.py POL-TABLE       그 정책의 규칙 전체
# 기획 정책정의서 1.2 「따르는 공통 정책」을 채울 때 쓴다. 색인으로 관련 정책을 고르고, 그 문서를 열어 확인한다.
# 문서 사이트(tools/site/build.py)와 같은 기준으로 규칙 행을 읽는다: 첫 칸이 <코드>-<번호> 인 표 행.
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = {'rule': '확정', 'draft': '미확정', 'open': '미확정(U)'}


def front(text):
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(':')
            if re.match(r'^[a-z_]+$', k):
                meta[k] = v.strip().strip('"')
        text = text[m.end():]
    return meta, text


def load():
    out = []
    for f in sorted((ROOT / 'policies').rglob('POL-*.md')):
        if 'review' in f.parts:
            continue
        meta, body = front(f.read_text())
        pid = meta.get('id') or f.stem
        code, sec = pid[4:], ''
        rules = []
        for line in body.splitlines():
            if re.match(r'^#{1,4} ', line):
                sec = line.lstrip('#').strip()
            elif line.startswith('|'):
                c = [x.strip() for x in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
                if c and re.fullmatch(re.escape(code) + r'-(M?\d+|U\d+)', c[0]):
                    kind = 'open' if re.search(r'-U\d+$', c[0]) else ('draft' if sec.startswith('미확정') else 'rule')
                    rules.append(dict(id=c[0], sec=sec, text=c[1] if len(c) > 1 else '', kind=kind))
        out.append(dict(id=pid, title=meta.get('title', ''), cat=meta.get('category', ''),
                        path=str(f.relative_to(ROOT)), rules=rules))
    return out


def cell(s, n=90):
    s = s.replace('|', '/')
    return s if len(s) <= n else s[:n - 1] + '…'


def main(args):
    pols = load()
    if not args:
        print('| 정책 | 이름 | 분야 | 규칙 | 미확정 | 파일 |\n| --- | --- | --- | --- | --- | --- |')
        for p in pols:
            n = sum(r['kind'] != 'rule' for r in p['rules'])
            print(f"| {p['id']} | {p['title']} | {p['cat']} | {len(p['rules'])} | {n} | {p['path']} |")
        print(f"\n정책 {len(pols)}개 · 규칙 {sum(len(p['rules']) for p in pols):,}줄")
        return
    one = [p for p in pols if p['id'] in args]
    hits = []
    for p in one or pols:
        for r in p['rules']:
            hay = ' '.join([p['id'], p['title'], r['sec'], r['text']])
            if one or all(w.lower() in hay.lower() for w in args):
                hits.append((p, r))
    print('| 규칙 ID | 정책 | 절 | 내용 | 상태 |\n| --- | --- | --- | --- | --- |')
    for p, r in hits:
        print(f"| {r['id']} | {p['title']} | {cell(r['sec'], 30)} | {cell(r['text'])} | {STATE[r['kind']]} |")
    print(f'\n{len(hits):,}줄')


if __name__ == '__main__':
    main(sys.argv[1:])
