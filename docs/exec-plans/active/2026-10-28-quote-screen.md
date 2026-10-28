# 공통 견적 개발화면 연결

## Goal
기존·시제품 입력 어댑터를 같은 검수 화면에서 실행하고 모바일·인쇄 검사 추가.
## Current state
개발안29 원격 98834e51, 시제품24 55c0534a 유지 확인. 기존 엔진검사48 통과.
## Requirements
상품 변경, 인력 일수, 추가 도우미·차량·수의, 미확인 빈소비 표시. 두 경로 소계 비교. 고객 운영파일 변경 금지.
## Non-goals
상품 구성 추정, 시설가격 변경, 고객 배포.
## Implementation steps
1. dev/quote-rules/index.html 및 screen.mjs 작성.
2. tests/quote-rules/browser.cjs로 390/1280 너비, 인쇄, 오류·넘침 검사.
3. 독립 GitHub 자동검사 실행.
## Verification plan
엔진48 검사, 모듈 문법검사, 브라우저16 시나리오 및 인쇄 PDF. 신규 이미지 없음. 별도 빌드 없음.
## Risks
로컬 Chromium 설치 파일 손상으로 실행 차단. 원격 검사 대체 사용. 상품 상세 미확인 유지.
## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification — 계산48·문법 통과
- [ ] Desktop verification
- [ ] Mobile verification
- [x] Regression check — 운영파일 변경 없음
- [ ] Final review
## Discoveries
로컬 브라우저 설치가 자동 재시도 후에도 손상된 ZIP으로 실패.
## Decisions
두 원본 화면은 보호하고 개발 비교화면에서 양쪽 어댑터를 연결. 검증 상태 승격 버튼 제공 안 함.
## Final verification
원격 브라우저 검사 결과 대기.
## Remaining limitations
상세 구성 확정 및 실제 고객 화면 연결은 수행하지 않음.
