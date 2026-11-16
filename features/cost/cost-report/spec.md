---
id: CST-SPEC
title: "월별 비용 기능정의서"
type: feature-spec
code: CST
status: review
owner: 기획
release: v1.0
related:
  spec: features/cost/cost-report/spec.md
  policy: features/cost/cost-report/policy.md
  screens: features/cost/cost-report/screens/index.md
---

## 1. 개요

비용 › 월별 비용에서 한 달 비용을 클라우드와 프로젝트로 나눠 보고, 전월보다 늘어난 곳을 찾는 기능을 정의한다.

| 항목 | 내용 |
| --- | --- |
| 메뉴 | 비용 › 월별 비용 |
| 범위 | 월별 합계 · 클라우드별 · 프로젝트별 조회. 예산 설정은 예산 기획 |
| 근거 | 재무팀 요구사항(CST-RQ-01) |

## 2. 범례

| 구분 | 값 |
| --- | --- |
| 우선순위 | M 필수 · S 권장 · C 여유 시 |
| 권한 | A 관리자 · O 운영자 · V 조회자 |
| 난이도 | 1 단순 표시 · 2 상태 관리 · 3 서버 연동 · 배치 |
| 구분 | 신규 · 변경 · 유지 |

## 3. 기능 목록

### 3.1 요구사항

| 요구사항 ID | 내용 | 출처 |
| --- | --- | --- |
| CST-RQ-01 | 월 비용이 어디서 늘었는지 프로젝트 단위로 본다 | 재무팀 |

### 3.2 조회

| 기능 ID | 대분류 | 중분류 | 기능명 | 기능 설명 | 화면 ID | 요구사항 ID | 우선순위 | 권한 | 정책 ID | 난이도 | 구분 | 비고 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CST-FN-RPT-01 | 조회 | 기간 | 월 선택 | 최근 6개월 가운데 한 달을 고른다 | CO-CST-RPT-R | CST-RQ-01 | M | A, V | TIME-04 | 1 | 신규 | — |
| CST-FN-RPT-02 | 조회 | 추이 | 최근 6개월 막대 | 클라우드별로 쌓은 월 비용 막대 | CO-CST-RPT-R | CST-RQ-01 | M | A, V | CST-PL-AMT-01 | 2 | 신규 | — |
| CST-FN-RPT-03 | 조회 | 프로젝트 | 프로젝트별 비용 · 전월 대비 | 고른 달 비용이 큰 순서로 정렬하고 전월 대비 증감률을 보인다 | CO-CST-RPT-R | CST-RQ-01 | M | A, V | CST-PL-AMT-01 | 2 | 신규 | — |
