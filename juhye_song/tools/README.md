# 도구 안내

| 폴더 | 하는 일 |
| --- | --- |
| `site/` | 문서 포털 빌드. `python3 tools/site/build.py . site` 가 md · 화면 설계서 · 공통 정책 · 품질 결과를 읽어 `site/index.html` 한 장을 만든다. 화면 규칙은 [TL-02](site/DESIGN.md) |
| `portfolio/` | 포트폴리오 사이트 빌드. `python3 tools/portfolio/build.py . site` 가 `portfolio/` 의 소개 · 사례 md 와 기획 문서를 읽어 홈 → 사례 → 기획 → 문서 네 단계 쪽을 만들고, 문서 포털은 `site/portal/` 에 함께 만든다 |
| `demo/` | 화면 설계서 생성. `data/all.json` 과 `design/kit.css` 를 한 파일에 넣어 기획마다 `screens/prototype.html` 을 만든다 |
| `check/` | 기획 목록 · ID 겹침 검사(`lists.py`), 공통 정책 규칙 색인(`rules.py`) |
| `export/` | 정의서 md 를 엑셀 · 워드 사본으로 바꾼다. 포털의 내려받기 파일 |

필요한 것: Python 3. 엑셀 · 워드 사본은 `openpyxl` · `python-docx`.

## 게시

GitHub 저장소를 Cloudflare Pages에 연결한다. 빌드 명령은 `pip install openpyxl python-docx && python3 tools/portfolio/build.py . site`, 출력 폴더는 `site`. `main`에 머지할 때마다 다시 게시되고 PR마다 미리보기 주소가 생긴다.
