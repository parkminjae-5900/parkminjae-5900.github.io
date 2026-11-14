# 견적 공통 규칙 개발

## Goal
상품비와 개별 인력·용품비의 중복을 막는 공통 엔진과 두 계산기 입력 어댑터를 개발 전용 경로에 구현한다.

## Current state
main 20ebd59366e1e1e8689091c408a1076de4bc04c2, PR24 55c0534a9bd96855074b85e5da17351135d1720b, PR25 cde1e6063eb12444d735d4bbd18f34760c8b71c7 확인.
기존 개별 견적은 780000원 필수 서비스와 선택품목 합계. PR24는 상품가와 빈소·수기 입력 합계.

## Requirements
상품/개별 모드 분리, 불명확한 구성 합산 보류, 확인된 초과분·차액만 계산, 시설·호실·단위·시간 검증, 자동검사 및 원본 대비 재현.

## Non-goals
고객 HTML·시설 식별·가격 원본·PR24·PR25 변경, 운영 배포 및 main 병합 금지.

## Implementation steps
1. 공식 안내와 실제 코드 대조 및 근거 기록.
2. dev/quote-rules 엔진·입력 어댑터 구현.
3. tests/quote-rules 원본 함수 재현과 회귀검사.
4. 별도 개발 브랜치에 저장하고 결과 보고.

## Verification plan
Node 문법검사 및 node --test, 원본 함수 VM 실행, git diff --check, 기존 Python 검사. 이 개발 라이브러리는 사용자 화면·이미지를 변경하지 않으므로 모바일/데스크톱·콘솔·이미지 검수 대상 화면 없음. 별도 build/lint/type-check 설정 없음.

## Risks
가족장·일반장·프리미엄의 상세 구성 미공개. 염습상례사와 보조 장례지도사의 이름이 다름. 하루 단가를 무조건 24시간으로 비례 계산하면 오류. 프런트엔드 확인 플래그는 인증 기능이 아니므로 운영 연결 시 서버 검증 필요.

## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [x] Desktop verification — 화면 변경 없음
- [x] Mobile verification — 화면 변경 없음
- [x] Regression check
- [x] Final review

## Discoveries
공식 무빈소 상세표에 지도사 1명 3일, 염습상례사 1명 1일, 관·수의·입관용품이 명시됨. 다른 세 상품의 정확한 수량·사양은 공개 안내로 확정 불가.

## Decisions
현행 페이지의 인라인 함수를 직접 교체하지 않고 개발용 입력 어댑터를 제공한다. 누락 정보를 무료로 간주하지 않으며 상품 전환 전 계약 근거는 재사용하지 않는다. AGENTS.md의 행사 정산 수당은 고객 견적 단가가 아니므로 사용하지 않는다.

## Final verification
node --test tests/quote-rules/engine.test.mjs: 48개 통과. 기존 Python unittest 15개 통과. 두 mjs 문법 및 git diff --check 통과. 기존 추적 파일 변경 없음.

## Remaining limitations
정확한 세 상품 구성표와 운영 화면 연결은 별도 검증 후 수행해야 한다. 개발 전용 구현 범위만 검증 완료.
