---
id: SRV-SPEC
title: "서버 목록 기능정의서"
type: feature-spec
code: SRV
status: approved
owner: 기획
release: v1.0
related:
  spec: features/infra/server-list/spec.md
  policy: features/infra/server-list/policy.md
  screens: features/infra/server-list/screens/index.md
---

## 1. 개요

인프라 › 서버에서 AWS · Azure · 사내 서버를 한 목록으로 보고, 사용률이 높은 서버를 찾아 30일 추이와 최근 알림을 확인하는 기능을 정의한다.

| 항목 | 내용 |
| --- | --- |
| 메뉴 | 인프라 › 서버 |
| 범위 | 서버 목록 · 상세 패널. 서버 만들기 · 지우기는 다루지 않는다 |
| 근거 | 인프라팀 요구사항(SRV-RQ-01 · 02) |

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
| SRV-RQ-01 | 클라우드가 달라도 서버를 한곳에서 본다 | 인프라팀 |
| SRV-RQ-02 | 사용률이 높거나 낮은 서버를 골라낸다 | 비용 담당 |

### 3.2 목록 · 상세

| 기능 ID | 대분류 | 중분류 | 기능명 | 기능 설명 | 화면 ID | 요구사항 ID | 우선순위 | 권한 | 정책 ID | 난이도 | 구분 | 비고 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SRV-FN-LST-01 | 목록 | 빠른 보기 | 클라우드 빠른 보기 | 전체 · AWS · Azure · 사내 서버로 목록을 바꾼다 | IN-SRV-LST-R | SRV-RQ-01 | M | A, O, V | TABLE-03 | 1 | 신규 | — |
| SRV-FN-LST-02 | 목록 | 거르기 | 상태 · 프로젝트 필터, 찾기 | 상태 · 프로젝트로 거르고 이름 · IP로 찾는다 | IN-SRV-LST-R | SRV-RQ-01 | M | A, O, V | TABLE-02 | 1 | 신규 | — |
| SRV-FN-LST-03 | 목록 | 사용률 | CPU 30일 평균 · 추이 | 일 평균 사용률의 평균과 30일 선을 보인다 | IN-SRV-LST-R | SRV-RQ-02 | M | A, O, V | SRV-PL-MET-01 | 2 | 신규 | — |
| SRV-FN-DTL-01 | 상세 | 정보 | 서버 상세 패널 | 사양 · OS · IP · 생성일과 CPU 30일 그래프 | IN-SRV-LST-R | SRV-RQ-01 | M | A, O, V | SRV-PL-MET-01 | 2 | 신규 | — |
| SRV-FN-DTL-02 | 상세 | 알림 | 최근 알림 | 이 서버의 최근 알림 5건 | IN-SRV-LST-R | SRV-RQ-02 | S | A, O, V | — | 1 | 신규 | 알림 기획 데이터 |
