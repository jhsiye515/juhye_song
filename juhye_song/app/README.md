# 가나다 운영 콘솔 (동작하는 예시)

기획서(`features/*`)의 기능 · 정책을 그대로 구현한 화면입니다. 서버 없이 브라우저 안에서 동작하고, 바꾼 내용은 보는 사람 브라우저에만 저장됩니다. 「처음으로」로 예시 데이터를 되돌립니다.

| 화면 | 주소 | 구현한 기능 · 정책 |
| --- | --- | --- |
| 인시던트 · 처리 큐 | `#/incidents` | INC-FN-REG-01 · STA-01~04 · LST-01~03, INC-PL-STS-01 · SLA-01 · STT-01, TABLE-01~04 |
| 인시던트 · 처리 현황 | `#/incidents/stats` | INC-FN-LST-05, INC-PL-STT-01 |
| 알림 | `#/alerts` | INC-FN-REG-02, INC-PL-GRP-01 (예시 알림 보내기) |
| 서버 | `#/servers` | SRV-FN-LST-01~03 · DTL-01~02, SRV-PL-MET-01 |
| 월별 비용 | `#/costs` | CST-FN-RPT-01~03, CST-PL-AMT-01, TIME-04 |

- 권한: 오른쪽 위에서 사용자를 바꾸면 관리자 · 운영자 · 조회자 권한대로 버튼과 화면이 바뀝니다.
- 「기획 ID 보기」를 켜면 화면 위에 근거 ID가 붙고, 누르면 포트폴리오의 해당 기획서 자리로 갑니다.
- 기획서에 정해지지 않은 값(자동 등록 인시던트의 우선순위)은 화면에 그렇다고 밝히고 예시 값을 씁니다.
- 실행: 포트폴리오 빌드(`tools/portfolio/build.py`)가 이 폴더를 `work/console/app/` 에 두고 `design/kit.css` · `data/all.json` 을 함께 넣습니다.
