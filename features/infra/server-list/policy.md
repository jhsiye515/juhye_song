---
id: SRV-POLICY
title: "서버 목록 정책정의서"
type: policy
code: SRV
status: approved
owner: 기획
release: v1.0
related:
  spec: features/infra/server-list/spec.md
  policy: features/infra/server-list/policy.md
  screens: features/infra/server-list/screens/index.md
---

## 1. 정책 목록

### 1.1 이 기획의 정책

| 정책 ID | 주제 | 참조 화면 | 담당 |
| --- | --- | --- | --- |
| SRV-PL-MET-01 | 사용률 계산 · 표시 | IN-SRV-LST-R | 기획 |

### 1.2 따르는 공통 정책

| 공통 정책 | 규칙 ID | 적용하는 곳 | 다르게 하는 것 |
| --- | --- | --- | --- |
| POL-TABLE | TABLE-01, TABLE-02, TABLE-03 | 서버 목록 | — |
| POL-STATUS | STATUS-01, STATUS-03 | 서버 상태 배지 | — |

## 2. SRV-PL-MET-01 · 사용률 계산 · 표시

- CPU 30일 평균 = 최근 30일 일 평균 사용률의 평균. 소수점 없이 반올림한다.
- 막대 색: 60% 미만 기본 · 60% 이상 주황 · 80% 이상 빨강.
- 중지된 서버는 중지한 날까지만 그린다.
- 상세 그래프는 일 평균과 일 최대를 함께 그리고 80% 기준선을 점선으로 둔다.

## 3. 미결정 목록

| 미결정 ID | 항목 | 지금 | 정할 것 | 담당 | 기한 |
| --- | --- | --- | --- | --- | --- |
| SRV-OQ-01 | 저사용 서버 표시 | 표시 없음 | 30일 평균 10% 미만을 따로 표시할지 | 비용 담당 | 2026-12-05 |
