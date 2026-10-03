# 무빈소 시설 및 요금 선택

## Goal
무빈소에서 근거가 있는 시설만 표시하고 빈소·분향실·접객실 요금 선택과 합산을 제외한다.

## Current state
main 78dae3e. 전국 시설목록에는 무빈소 가능 flag 없음. 보유 장례식장 조건표도 관련 항목 없음. 사용자 제공 과거 가능 사례는 부천시민장례식장·신화장례식장. 공식 현재 운영 및 예약 검증 없음.

## Requirements
가능 사례 허용목록을 명칭+정확 주소로 검증. 목록·검색·드롭다운·chooseHall·계산에 동일 검증. 무빈소 시 임의 시설 입력 숨김. 분류·이름·상세설명에 빈소·분향·접객·영결식장 포함 행 제거. 안치·입관 유지. 형태 전환 시 기존 선택·시설 총액·기타비·근거·음식비 초기화. 일반 장례 전체 목록 복원. 데이터 로딩·실패·잘못된 주소는 미확인 시설 표시 금지.

## Non-goals
가격·로고·사진 수정 및 전국 가능 여부 추정. 과거 사례를 현재 예약 가능 확정으로 표현하지 않음.

## Implementation steps
1. data/mubinso-facilities.json에 사용자 제공 사례와 출처 구분만 보존.
2. 계산기·nationwide-prices.js에 공통 허용 검증 및 전환 초기화.
3. 가격 병합 뒤 room 행 삭제 및 계산 방어.
4. 모바일·PC·실패·회귀 검증 후 원격 main 최신 변경 보존 배포.

## Verification plan
JS/인라인 구문·diff 검사. 기존 nationwide-estimate.cjs와 신규 mubinso-estimate.cjs를 Chromium 390/1440px에서 실행. 확인시설/미확인시설·동명 주소·이전 비용·일반장 복원·모바일 넘침·pageerror·이미지 및 인쇄 회귀 확인. 정적 저장소로 build/lint/typecheck 명령 없음.

## Risks
전국 운영 검증자료가 아니며 현재 등록 사례 2곳만 근거 있음. 자료 실패 시 일부 지역 결과 없음. 기존 숨김 단계 비용이 잔류하지 않도록 전환 시 초기화.

## Progress
- [x] Investigation
- [x] Implementation
- [ ] Automated verification
- [ ] Desktop verification
- [ ] Mobile verification
- [ ] Regression check
- [ ] Final review

## Discoveries
5팀 검토에서 selectedHall 재삽입 우회, 기타/입관실 분류의 빈소 항목, 강제 갱신 시 수동금액 보존, 빈소 미노출 후 합계 잔류 위험을 확인.

## Decisions
확인 근거 없는 전국 시설을 가격으로 추정하지 않고 사용자 제공 사례만 등록. 현재 운영·예약은 상담 후 확인한다는 안내 유지. 내부 조건표 가격/수수료/직원 정보 공개하지 않음.

## Final verification
구문 및 diff 검사 통과. 브라우저 검증 진행 중.

## Remaining limitations
전국 무빈소 가능 시설 전체자료는 확보되지 않음. 등록 사례의 현재 운영·예약 및 현재 요금은 시설 최종 확인 필요.
