# 우선지역 공식가격 검증 확대

## Goal
서울 영등포·송파·강남 및 인천 시설의 공식 가격근거를 확보하고 검증된 레코드만 변경안으로 제출.
## Current state
main 시설 1080개, 우선지역 47개, 기존 가격 레코드 3개. PR #24는 UI 3개 파일 변경. 기존 스캐너 지점 가드는 유지.
## Requirements
시설명·주소·지점·항목·금액·단위·출처·확인일 대조. 미확인 가격 대체 금지.
## Non-goals
견적 UI, 시설 식별 로직, 자동 수집 상태 파일 변경 없음.
## Implementation steps
1. 47개 시설 기준목록 및 기존 상태 기록.
2. 공식 홈페이지·운영기관·공공자료 검색 및 근거 대조.
3. 검증 자료와 미확인 사유를 기존 가격 스키마 및 별도 감사대장에 반영.
4. 자동검사 및 회귀검사 후 독립 PR 제출.
## Verification plan
Python unittest, JSON 항목/금액/단위/정확 일치 검사, git diff --check. 데이터 표시 회귀 확인을 위해 desktop/mobile 브라우저 테스트도 시도. 독립 build/lint/type-check 명령 유무 확인.
## Risks
행정구역 명칭 변경, 다지점 공통홈페이지, 시간·일 요금 오독, 출처 갱신일과 확인일 혼동.
## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [ ] Desktop verification (Chromium 실행파일 없음·다운로드 실패)
- [ ] Mobile verification (동일 환경 제한)
- [x] Regression check (데이터·기존 단위테스트)
- [x] Final review (브라우저 제한 공개)
## Discoveries
보고서 최신 갱신 2026-10-26T06:11:26Z. 인천의료원 공식 주소는 제물포구, 기존 시설목록은 동구로 표시됨. 도로명·번호 및 운영기관으로 동일 시설 확인 필요.
## Decisions
기존 자료를 신규 검증으로 중복 집계하지 않음. 게시가격 확인은 요금 시행일 확인과 구분.
## Final verification
Python 전체 20개 테스트 통과. 기존 금액 범위·압축 baseline 검사 통과. 47개 범위 및 live/audit 스냅샷 일치 확인. 신규 4개, 기존 수정 2개, 기타 37개 동일. git diff --check 통과. 독립 package.json/build/lint/type-check 없음. UI/이미지 파일 변경 없음. Chromium 미설치 및 공식 다운로드가 잘린 ZIP으로 실패하여 desktop/mobile/console 시각 검증 미수행; PR에 제한 명시.
## Remaining limitations
미확인 40개와 경찰병원 기존 기록 재검증 1개는 추가 확보 필요. 브라우저 검증 환경 미확보. 공식 게시가격의 시행일은 미표기. 2023년 공공자료는 현행 가격에 반영하지 않음.

## Outcomes
우선 47개 조사, 신규 4개 시설과 기존 2개를 검증. 길병원의 무단위 안치료를 정정하고 18항목으로 확장. 인천사랑 호실, 세종 VIP1, 인천의료원 관리비는 보류. PR #24 파일과 중복 없음. 변경안 제출까지 완료하고 배포는 하지 않는다.
