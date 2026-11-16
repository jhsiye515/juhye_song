---
id: CST-POLICY
title: "월별 비용 정책정의서"
type: policy
code: CST
status: review
owner: 기획
release: v1.0
related:
  spec: features/cost/cost-report/spec.md
  policy: features/cost/cost-report/policy.md
  screens: features/cost/cost-report/screens/index.md
---

## 1. 정책 목록

### 1.1 이 기획의 정책

| 정책 ID | 주제 | 참조 화면 | 담당 |
| --- | --- | --- | --- |
| CST-PL-AMT-01 | 금액 계산 · 표기 | CO-CST-RPT-R | 기획 |

### 1.2 따르는 공통 정책

| 공통 정책 | 규칙 ID | 적용하는 곳 | 다르게 하는 것 |
| --- | --- | --- | --- |
| POL-TIME | TIME-04 | 월 선택 | — |

## 2. CST-PL-AMT-01 · 금액 계산 · 표기

- 비용 = 컴퓨트 + 스토리지 + 네트워크. 부가세 별도.
- 화면에는 만 원 단위로 반올림해 「2,222만 원」처럼 쓴다.
- 전월 대비 = (이번 달 − 전월) ÷ 전월, 소수점 한 자리. 늘면 빨강, 줄면 초록.
- 이번 달은 어제까지 쓴 비용이다.

## 3. 미결정 목록

| 미결정 ID | 항목 | 지금 | 정할 것 | 담당 | 기한 |
| --- | --- | --- | --- | --- | --- |
| CST-OQ-01 | 이번 달 전월 대비 | 어제까지 비용 ÷ 전월 전체 | 같은 날짜까지끼리 견줄지 | 재무팀 | 2026-11-28 |
| CST-OQ-02 | 사내 서버 비용 기준 | vCPU 당 월 단가 | 감가상각 기준으로 바꿀지 | 재무팀 | 2026-12-12 |
