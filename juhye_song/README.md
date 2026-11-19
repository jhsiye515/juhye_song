# OPS 기획 문서 저장소

가상 회사 「가나다커머스」 운영 콘솔의 기획 문서(화면 설계서 · 기능정의서 · 정책정의서 · 화면 목록)와 공통 정책을 한곳에 두는 저장소입니다. 들어 있는 회사 · 사람 · 서버 · 금액은 모두 예시 데이터입니다.

`main`에 있는 것이 확정본이고, 바꿀 때는 PR로 올립니다. 머지하면 문서 포털이 다시 만들어집니다.

## 1. 구성

```
features/<영역>/<기획>/     기획 하나 = 폴더 하나
  spec.md                   기능정의서: 무엇을 할 수 있나
  policy.md                 정책정의서: 어떤 규칙인가 (숫자 · 조건)
  screens/index.md          화면 목록
  screens/prototype.html    화면 설계서 (예시 데이터로 움직임)
  qa/                       품질 검사 결과
policies/                   여러 기획이 함께 따르는 공통 정책
design/kit.css              제품 양식 (화면 설계서가 씀)
data/                       예시 데이터와 생성 스크립트
portfolio/                  포트폴리오 소개 · 사례 글(md)과 대표 화면
tools/portfolio/            포트폴리오 사이트 빌드 (홈 → 사례 → 기획 → 문서)
tools/site/                 문서 포털 빌드
tools/demo/                 화면 설계서 생성
tools/check/                기획 목록 · 정책 규칙 검사
```

## 2. 기획 목록

| 기획 | 코드 | 메뉴 | 상태 |
| --- | --- | --- | --- |
| 인시던트 처리 큐 | INC | 운영 › 인시던트 | 확정 |
| 서버 목록 | SRV | 인프라 › 서버 | 확정 |
| 월별 비용 | CST | 비용 › 월별 비용 | 검토 중 |

## 3. 만들기

```bash
python3 data/gen.py                      # 예시 데이터
python3 tools/demo/make_prototypes.py    # 화면 설계서
python3 tools/portfolio/build.py . site  # 포트폴리오 → site/index.html, 문서 포털 → site/portal/
```

문서끼리는 ID로 이어집니다. 예: 기능 `INC-FN-STA-01` → 화면 `OP-INC-LST-R` → 정책 `INC-PL-STS-01` → 공통 규칙 `STATUS-01`.
