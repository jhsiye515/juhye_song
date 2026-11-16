# md 원본 → 외부 전달용 사본(xlsx · docx)
#   python3 tools/export/export.py <원본.md> <출력 폴더>
# 원본은 저장소의 md 하나뿐이다. 이 스크립트가 만든 파일은 고치지 않고, 고칠 것은 md 에 MR 로 올린다.
import re, sys, datetime
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = '맑은 고딕'
NAVY = '1D2733'
HEAD_FILL = 'E9E6DE'
NOTICE = '이 파일은 저장소 원본에서 자동으로 만든 사본입니다. 이 파일을 고치지 말고, 의견은 담당 기획자에게 주세요.'
KIND = {'spec': '기능정의서', 'policy': '정책정의서', 'prd': 'PRD',
        'feature-spec': '기능정의서', 'screen-index': '화면목록'}
FN_HEAD = ['기능 ID', '대분류', '중분류', '기능명', '기능 설명', '관련 화면 ID', '요구사항 ID', '우선순위', '권한', '역할', '관련 정책 ID', '난이도', '구분', '비고']
# 표 양식(0.2)의 칸 이름 → 엑셀 칸
FN_COL = {'화면 ID': '관련 화면 ID', '정책 ID': '관련 정책 ID'}


# ---------- md 읽기 ----------

def parse(path):
    text = Path(path).read_text()
    meta = {}
    m = re.match(r'---\n(.*?)\n---\n', text, re.S)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(':')
            meta[k.strip()] = v.strip()
        text = text[m.end():]
    blocks, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        s = lines[i].rstrip()
        if not s:
            i += 1
        elif s.startswith('#'):
            lv = len(s) - len(s.lstrip('#'))
            blocks.append(('h', lv, s[lv:].strip()))
            i += 1
        elif s.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                row = lines[i].strip()
                if not re.match(r'^\|[\s\-:|]+\|$', row):
                    cells = re.split(r'(?<!\\)\|', row)[1:-1]
                    rows.append([c.strip() for c in cells])
                i += 1
            blocks.append(('t', rows))
        elif re.match(r'^\s*[-*] ', s):
            items = []
            while i < len(lines) and re.match(r'^\s*[-*] ', lines[i]):
                items.append(re.sub(r'^\s*[-*] ', '', lines[i]).strip())
                i += 1
            blocks.append(('ul', items))
        else:
            para = [s]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r'^(#|\||\s*[-*] )', lines[i]):
                para.append(lines[i].strip())
                i += 1
            blocks.append(('p', ' '.join(para)))
    return meta, blocks


def plain(s):
    s = re.sub(r'\\([_|*\\])', r'\1', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
    return s.replace('`', '')


def runs(par, s, size=None, color=None):
    # **굵게** 만 살린다. 나머지 md 표기는 지운다
    for j, part in enumerate(re.split(r'\*\*(.+?)\*\*', re.sub(r'\\([_|*\\])', r'\1', s).replace('`', ''))):
        if not part:
            continue
        r = par.add_run(part)
        r.bold = j % 2 == 1 or None
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = RGBColor.from_string(color)


def kind(meta):
    return meta.get('type') or meta.get('doc')


def fn_rows(blocks):
    # 기능 목록 → 엑셀 표 한 장. 두 양식을 다 읽는다
    #   표 양식(0.2): 「기능 ID」로 시작하는 표의 한 줄 = 기능 하나
    #   단락 양식(0.1): #### ID 이름 + 설명 + 속성 줄
    out, cur, para = [FN_HEAD], None, []
    for b in blocks:
        if b[0] == 't' and b[1] and b[1][0] and b[1][0][0] == '기능 ID':
            head = [FN_COL.get(h, h) for h in b[1][0]]
            for r in b[1][1:]:
                d = dict(zip(head, r))
                out.append([d.get(h, '') for h in FN_HEAD])
        elif b[0] == 'h' and b[1] == 4 and re.match(r'^[A-Z]{3}-FN-', b[2]):
            fid, _, name = b[2].partition(' ')
            cur = dict(id=fid, name=name, desc=[])
            para.append(cur)
        elif b[0] == 'h' and b[1] <= 3:
            cur = None
        elif cur is not None and b[0] == 'p':
            cur['desc'].append(b[1])
        elif cur is not None and b[0] == 'ul':
            for it in b[1]:
                for part in re.split(r' · (?=[가-힣]+: )', it):
                    k, _, v = part.partition(': ')
                    cur[k.strip()] = v.strip()
    for r in para:
        big, _, mid = r.get('분류', '').partition(' › ')
        out.append([r['id'], big, mid, r['name'], ' '.join(r['desc']), r.get('화면', ''), r.get('요구사항', ''),
                    r.get('우선순위', ''), r.get('권한', ''), r.get('역할', ''), r.get('정책', ''), r.get('난이도', ''),
                    r.get('구분', ''), r.get('비고', '')])
    return out if len(out) > 1 else None


def sections(blocks):
    # 표마다 바로 위 제목을 붙여 돌려준다
    title = ''
    for b in blocks:
        if b[0] == 'h':
            title = b[2]
        elif b[0] == 't':
            yield title, b[1]


def stamp(meta, src):
    return [
        ('문서', meta.get('title', '')),
        ('종류', KIND.get(kind(meta), kind(meta) or '')),
        ('기획 코드', meta.get('code', '')),
        ('릴리스', meta.get('release', '')),
        ('상태', meta.get('status', '')),
        ('담당', meta.get('owner', '')),
        ('원본 최종 수정', meta.get('updated', '')),
        ('원본 위치', 'plan-portal / ' + src),
        ('생성 일시', datetime.datetime.now().strftime('%Y-%m-%d %H:%M')),
    ]


# ---------- 엑셀 ----------

thin = Side(style='thin', color='C9C4B8')
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)


def width(rows, col):
    n = max(len(plain(r[col])) if col < len(r) else 0 for r in rows)
    return max(8, min(60, n * 1.6 + 2))


def put_table(ws, r0, rows):
    for ri, row in enumerate(rows):
        for ci, v in enumerate(row):
            c = ws.cell(row=r0 + ri, column=ci + 1, value=plain(v))
            c.font = Font(name=FONT, size=10, bold=ri == 0, color='FFFFFF' if ri == 0 else '000000')
            c.alignment = Alignment(wrap_text=True, vertical='top')
            c.border = BOX
            if ri == 0:
                c.fill = PatternFill('solid', fgColor=NAVY)
    return r0 + len(rows)


def to_xlsx(meta, blocks, src, out):
    wb = Workbook()
    cover = wb.active
    cover.title = '표지'
    cover['A1'] = meta.get('title', '')
    cover['A1'].font = Font(name=FONT, size=16, bold=True)
    for i, (k, v) in enumerate(stamp(meta, src), start=3):
        cover.cell(row=i, column=1, value=k).font = Font(name=FONT, bold=True)
        cover.cell(row=i, column=2, value=v).font = Font(name=FONT)
    cover.cell(row=13, column=1, value=NOTICE).font = Font(name=FONT, color='B5530F')
    cover.column_dimensions['A'].width = 16
    cover.column_dimensions['B'].width = 70

    # 기능 목록 표는 대분류마다 끊겨 있어도 한 시트로 합친다
    tabs = [(t, r) for t, r in sections(blocks) if not (r and r[0] and r[0][0] == '기능 ID')]
    fr = fn_rows(blocks)
    if fr:
        tabs.insert(0, ('기능 목록', fr))
    if len(tabs) <= 8:
        # 표가 적으면 표 하나 = 시트 하나 (기능정의서)
        for title, rows in tabs:
            ws = wb.create_sheet(re.sub(r'[\\/*?:\[\]]', '', title)[:31] or '표')
            put_table(ws, 1, rows)
            ws.freeze_panes = 'B2'
            ws.auto_filter.ref = ws.dimensions
            for ci in range(len(rows[0])):
                ws.column_dimensions[get_column_letter(ci + 1)].width = width(rows, ci)
    else:
        # 표가 많으면 한 시트에 장 제목과 함께 이어 붙인다 (정책정의서)
        ws = wb.create_sheet('정책 표')
        r, widest = 1, {}
        for title, rows in tabs:
            ws.cell(row=r, column=1, value=plain(title)).font = Font(name=FONT, size=12, bold=True)
            r = put_table(ws, r + 1, rows) + 1
            for ci in range(len(rows[0])):
                widest[ci] = max(widest.get(ci, 0), width(rows, ci))
        for ci, w in widest.items():
            ws.column_dimensions[get_column_letter(ci + 1)].width = w
        ws2 = wb.create_sheet('안내')
        ws2['A1'] = '엑셀에는 표만 들어 있습니다. 표 사이의 설명 문장과 목록은 워드(docx) 사본에서 보세요.'
        ws2['A1'].font = Font(name=FONT)
    wb.save(out)


# ---------- 워드 ----------

def set_font(style, size=None):
    style.font.name = FONT
    style.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
    if size:
        style.font.size = Pt(size)


def shade(cell, fill):
    tc = cell._tc.get_or_add_tcPr()
    sh = OxmlElement('w:shd')
    sh.set(qn('w:val'), 'clear')
    sh.set(qn('w:fill'), fill)
    tc.append(sh)


def repeat_header(row):
    tr = row._tr.get_or_add_trPr()
    el = OxmlElement('w:tblHeader')
    el.set(qn('w:val'), 'true')
    tr.append(el)


def page_number(par):
    for kind, text in (('begin', None), (None, 'PAGE'), ('end', None)):
        r = par.add_run()
        if kind:
            f = OxmlElement('w:fldChar')
            f.set(qn('w:fldCharType'), kind)
            r._r.append(f)
        else:
            t = OxmlElement('w:instrText')
            t.text = text
            r._r.append(t)


def fit_widths(t, rows, total):
    # 칸 너비를 글 길이에 비례해 나눈다. 짧은 칸(ID · 값)은 최소 너비만 준다
    n = len(rows[0])
    need = []
    for ci in range(n):
        lens = sorted(len(plain(r[ci])) if ci < len(r) else 0 for r in rows)
        need.append(max(lens[len(lens) * 9 // 10], len(plain(rows[0][ci])), 4))
    # ID 처럼 끊으면 안 되는 낱말이 한 줄에 들어가는 너비 (글자당 약 0.19cm, 한글은 두 배)
    def word_w(s):
        return sum(2 if ord(ch) > 0x2fff else 1 for ch in s) * Cm(0.19) + Cm(0.4)
    floor = [max(word_w(wd) for r in rows if ci < len(r) for wd in (plain(r[ci]).split() or [''])) for ci in range(n)]
    floor = [min(f, total * 0.18) for f in floor]
    w = [max(floor[ci], total * need[ci] / sum(need)) for ci in range(n)]
    w = [int(x * total / sum(w)) for x in w]
    t.autofit = False
    for row in t.rows:
        for ci, c in enumerate(row.cells):
            c.width = w[ci]


def to_docx(meta, blocks, src, out):
    d = Document()
    for name in ('Normal', 'Heading 1', 'Heading 2', 'Heading 3', 'Title'):
        set_font(d.styles[name])
    d.styles['Normal'].font.size = Pt(10)
    sec = d.sections[0]
    widest = max((len(b[1][0]) for b in blocks if b[0] == 't'), default=0)
    if widest >= 7:
        # 칸이 많은 표가 있으면 가로 방향
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for side in ('left_margin', 'right_margin', 'top_margin', 'bottom_margin'):
        setattr(sec, side, Cm(1.8))

    hp = sec.header.paragraphs[0]
    runs(hp, f"{meta.get('title', '')}  ·  {meta.get('release', '')}  ·  상태 {meta.get('status', '')}", 8, '5B6573')
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    runs(fp, '사본 — 원본: plan-portal / ' + src + '    ', 8, '5B6573')
    page_number(fp)

    # 표지
    d.add_paragraph().paragraph_format.space_before = Pt(80)
    runs(d.add_paragraph(), meta.get('title', ''), 24)
    t = d.add_table(rows=0, cols=2)
    t.style = 'Table Grid'
    for k, v in stamp(meta, src):
        c = t.add_row().cells
        runs(c[0].paragraphs[0], f'**{k}**')
        runs(c[1].paragraphs[0], v)
        shade(c[0], HEAD_FILL)
    p = d.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    runs(p, NOTICE, 9, 'B5530F')
    d.add_page_break()

    for b in blocks:
        if b[0] == 'h':
            d.add_heading(plain(b[2]), level=min(b[1], 3))
        elif b[0] == 'p':
            p = d.add_paragraph()
            if re.match(r'^표 \d', b[1]):
                runs(p, b[1], 8, '5B6573')
            else:
                runs(p, b[1])
        elif b[0] == 'ul':
            for it in b[1]:
                runs(d.add_paragraph(style='List Bullet'), it)
        elif b[0] == 't':
            rows = b[1]
            n = len(rows[0])
            t = d.add_table(rows=0, cols=n)
            t.style = 'Table Grid'
            for ri, row in enumerate(rows):
                cells = t.add_row().cells
                for ci in range(n):
                    runs(cells[ci].paragraphs[0], row[ci] if ci < len(row) else '', 8.5 if n >= 7 else 9.5)
                    if ri == 0:
                        shade(cells[ci], HEAD_FILL)
                        for r in cells[ci].paragraphs[0].runs:
                            r.bold = True
                if ri == 0:
                    repeat_header(t.rows[0])
            fit_widths(t, rows, sec.page_width - sec.left_margin - sec.right_margin)
            d.add_paragraph()
    d.save(out)


if __name__ == '__main__':
    src, outdir = Path(sys.argv[1]), Path(sys.argv[2])
    meta, blocks = parse(src)
    rel = '/'.join(src.parts[src.parts.index('features'):]) if 'features' in src.parts else src.name
    name = f"{meta.get('code', 'DOC')}_{KIND.get(kind(meta), kind(meta))}_{meta.get('release', '')}"
    to_xlsx(meta, blocks, rel, outdir / f'{name}.xlsx')
    to_docx(meta, blocks, rel, outdir / f'{name}.docx')
    print(name, '· 표', sum(1 for b in blocks if b[0] == 't'), '· 제목', sum(1 for b in blocks if b[0] == 'h'))
