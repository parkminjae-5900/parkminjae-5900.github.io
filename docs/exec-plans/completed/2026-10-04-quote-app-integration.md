# 견적 앱 홈페이지 결합
## Goal
홈페이지에서 장례식장 견적 앱으로 연결하고 무빈소 선택 시 제공 PDF 기준 지역별 가능 식장과 설정 요금을 표시한다.
## Current state
정적 홈페이지 및 11단계 맞춤설계 화면. 기존 계산기 사용자 수정 파일은 보존했다.
## Requirements
공식 로고 원본 유지. 고객용 앱의 비용자료 편집 기능 제외. 내부 원금과 배수 제외. 무빈소 지역 변경 시 이전 식장비 제거. 3일장 전국 식장 기능 유지.
## Non-goals
승인 전 실제 홈페이지 배포, 실제 결제와 개인정보 수집.
## Implementation steps
1. 홈페이지 및 계산기에 견적 앱 진입 버튼 추가.
2. quote-app 폴더에 고객 검토용 앱 설치.
3. PDF 전사 자료 기반 무빈소 지역 필터 및 계산 연결.
4. 모바일 및 PC 검수 후 로컬 브라우저 새로고침.
## Verification plan
정적 프로젝트로 별도 빌드/lint/typecheck 명령 없음. Playwright로 경로, 계산, 지역 변경, 일반 모드 복귀, 오류 및 화면 폭을 확인. git diff --check와 로고 해시 확인.
## Risks
제공 PDF는 현재 예약 가능 여부를 보장하지 않는다. 기존 고객용 설계는 개별 품목 선택, 앱은 상품 선택 방식이므로 서로 다른 진입점을 유지한다.
## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [x] Desktop verification
- [x] Mobile verification
- [x] Regression check
- [x] Final review
## Discoveries
홈페이지 원본은 이 작업과 인접한 repo 폴더에 있다. 기존 계산기는 별도 변경 사항이 있었다.
## Decisions
기존 맞춤설계를 삭제하지 않고 상품 기반 견적 앱을 추가했다. 무빈소는 제공 표의 41개 식장 설정 요금만 사용한다.
## Final verification
qa_website_integration.mjs PASS: 두 진입점, 390/1280, 앱 합계, 편집기 제외, 콘솔 오류 없음.
qa_website_nohall.mjs PASS: 서울 강서구 개화 960000원, 미등록 지역, 지역 변경 금액 초기화, 일반 모드 복귀, 390/1280.
원본 로고 SHA256 확인 통과. UI 실제 탭 새로고침 및 무빈소 서울 강서구 목록 확인.
## Remaining limitations
사용자의 기존 사전 승인 조건에 따라 게시하지 않았다. 100원 결제 및 휴대폰 인증은 미연결 상태다.

## Publication authorization and checks
사용자가 적용시켜라고 승인함. main 99f6194 기반 별도 작업본에서 적용. 기존 전국 견적 회귀검수 및 무빈소 모바일/PC 검수 통과. 로고 원본 해시 일치. 실제 결제와 고객 DB는 구현 범위에 포함되지 않음.

## Residence auto-link follow-up
거주지 단독 지역명과 시군구 입력으로 공시 시설목록 또는 기존 검수된 공동 이용 지역을 연결. 도 단위 복수 시설은 선택목록을 제공하며 광주 동명 지역은 추가입력 요청. 자동 연결은 자격 확정과 구분하여 요금과 증빙 확인 체크는 자동 설정하지 않음. qa_residence.mjs 11개 주소 및 모호지역·모바일PC 검수 통과. 전국 견적 회귀검수 통과.

## No-hall helper and readable summary follow-up
무빈소는 접객도우미 패널을 숨기고 인원을 0으로 초기화하여 숨은 비용 합산 방지. 일반 장례 복귀 시 패널 복원. 음식·접객 미사용, 장지 별도 견적, 추가주문 확인 체크 3종은 무빈소에서 숨김. 장지 미확인 비용 자체는 유지. 요약은 항목별 카드로 표시하고 미확인 비용 건수 표현을 상담 확인 사항 안내로 변경. 견적 앱 링크를 절대 경로와 버전 인자로 갱신. 모바일 터치 및 PC 클릭, 체크 숨김과 비용 제외, 기존 전국 견적 회귀검수 통과.

## Gyeonggi city selection
상품형 견적 앱에 경기 시군 선택 추가. 일반 사례 및 무빈소 목록에 지역 필터 적용. 시군/지역/상품 전환 시 선택과 금액 갱신. qa_city_filter.mjs 모바일390/PC1280에서 부천시·수원시 분리, 서울 전환 초기화, 부천 무빈소 5개 식장 및 2160000원 합계 검수 통과. 원본 로고 유지. 앱 서비스워커 캐시 v3으로 갱신.
