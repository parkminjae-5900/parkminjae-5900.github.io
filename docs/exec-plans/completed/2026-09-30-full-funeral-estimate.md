# 전국 시설 요금 연결 견적

## Goal
기존 11단계 견적에서 실제 시설 요금 항목을 선택하고 산출내역·근거·미확인 비용을 공유 및 출력한다.

## Current state
GitHub Pages 공식 홈페이지. 구현 기준 main 7fd5b36, 원격 반영 기준 820a3e5. 자동 가격 수집 변경을 보존한다. 시설 목록 1080곳. 최근 수집 가격 33곳. 기존 계산기는 시설·화장료를 직접 입력만 하며 누락 금액을 0원처럼 표시했다.

## Requirements
전국 지역 선택, 시설 정확 명칭 매칭, 시간·일수·횟수 산출, 최신 수집값 우선, 2023 공시자료 표시, 관내·관외·감면 원문 선택, 직접 확인 금액 입력, 매장 시 화장료 제외, 견적 출처·미확인 항목 공유.

## Non-goals
로고·상품 사진 변경. API 키 노출. 근거 없는 최신 가격·감면 자격 자동 판정.

## Implementation steps
1. 제공 CSV의 시설임대료 및 화장시설 원문을 별도 JSON으로 보존.
2. 기존 calculator에 선택 UI와 별도 계산 확장 JS 연결.
3. 전국 시설목록 연결, 실패 및 누락 상태 제공.
4. 계산·모바일·PC 검수 후 기존 GitHub Pages에 반영.

## Verification plan
JS 구문 검사, 데이터 검증, Chromium 기반 390px/1440px UI 및 회귀 검수, 잘못된 입력/시설 변경/매장 전환/공유/인쇄 확인.

## Risks
공시자료는 2023년 기준. 최신 수집 데이터도 시행일·단위가 누락될 수 있다. 정확한 명칭 매칭 실패 및 온라인 연결 실패는 직접 입력으로 처리. 공유에 미확인 사항을 포함한다.

## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [x] Desktop verification
- [x] Mobile verification
- [x] Regression check
- [x] Final review

## Discoveries
교차 검토에서 동명 시설·다른 주소·원문 공유·복수 요금 파싱·과금 단위 누락·시설 변경 시 금액 및 근거 잔존 위험을 발견하고 자동 연결 제한 및 초기화를 적용했다. 공공데이터포털 15021763은 2023년 6월까지 업데이트된 1회성 자료라고 명시한다. 기존 최신 가격 DB는 33곳으로 전국 현행 확정값이 아니다.

## Decisions
전국 1026곳 5012개 시설임대 항목과 화장시설 60곳 721개 유효 원문 행을 연결하되 참고값으로 표시. 필요한 항목은 사용자가 선택하며 임의 합산·자격 추정은 하지 않는다.

## Final verification
JSON 및 모든 인라인·외부 JS 구문 검사 통과. Chromium 390px/1440px 전체 검수 통과: 가격×수량 정확값, 직접 입력 누락 경고, 화장료 400000원 포함, 매장 제외, 시설 변경 초기화, 음수 제한, 복사 산출내역 및 근거, 연결 실패 대응, 문서 가로 넘침 없음, A4 PDF 추출 및 시각 검토. 검증 실행 36713831917 / 36714477454 성공. 마지막 모바일 17지역 표시 변경도 실행 36714688633 성공. 공식 홈페이지 배포 후 지역 목록·화장 요금 UI를 추가 확인한다.

## Remaining limitations
전국 현행 요금 및 현재 예약 가능 여부는 확인되지 않음. 자동 수집된 가격의 정확한 시행일과 특수 과금 규정은 시설 확인 필요.

## Reproduction
원본 CSV 폴더와 선택적 화장시설 메타데이터 JSON으로 python3 scripts/build_estimate_price_catalog.py SOURCE_DIRECTORY [FACILITY_METADATA_JSON] 실행. 가격에 과금 단위·현재 시행일을 임의 추가하지 않는다. 정적 HTTP 서버와 Playwright 환경에서 tests/nationwide-estimate.cjs로 회귀 확인.
