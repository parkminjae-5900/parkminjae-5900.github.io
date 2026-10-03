# SEO 검색→견적→상담 전환 구조 완성

## Goal
지역·장례식장·비용 검색 유입이 맞춤 장례견적과 상담으로 이어지게 한다.

## Current state
- 정적 HTML 기반 GitHub Pages.
- 지역 랜딩, 병원/장례식장 랜딩, 장례비용 페이지, 맞춤 장례견적 계산기 존재.
- 지역 개인화와 검색의도별 메인 카피 존재.
- 일부 공개 페이지에 과거 상품명/가격 표현이 남아 있음.
- 공식 로고 assets/daham_logo.jpg 수정 금지.

## Requirements
- 지역/장례식장/비용 의도 페이지에 공통 전환 패널 적용.
- 지역·장례식장·장례형태·조문객 수를 맞춤 장례견적으로 전달.
- 대표번호 전화와 상담내용 복사 지원.
- dataLayer 전환 이벤트 기록.
- 확인되지 않은 시설비/총액 생성 금지.
- 확정 상품: 무빈소 120 / 꽃나라 199 / 별나라 299.
- canonical, 구조화데이터, 지역개인화 보존.
- 모바일과 데스크톱에서 CTA 가시성 유지.

## Non-goals
- 공식 로고 수정 금지.
- 공공데이터 가격 임의 변경 금지.
- 지역명만 바꾼 신규 doorway 페이지 대량 생성 금지.
- 확인되지 않은 리뷰·평점·시설가격 생성 금지.

## Implementation steps
1. conversion-funnel.js 추가.
2. 핵심 검색 랜딩에 모듈 연결.
3. 맞춤 장례견적 URL prefill 추가.
4. 과거 가격 표현 정리.
5. 자동 검증 스크립트와 CI 추가.
6. PR diff 검수 및 수정.
7. 메인 병합 후 배포 검증.

## Verification plan
- 대상 HTML의 conversion-funnel.js 포함 검사.
- 오래된 상품가격 표현 검사.
- canonical 누락 검사.
- 로컬 href/src 경로 검사.
- 브라우저 콘솔 오류 여부.
- 360~430px 모바일과 1280px 이상 데스크톱 레이아웃 확인.
- GitHub Actions 성공 확인.

## Risks
- 페이지별 마크업 차이.
- 자동 데이터 갱신 커밋과 충돌.
- 계산기 초기화와 prefill 실행순서 충돌.

## Progress
- [x] Investigation
- [x] Implementation started
- [ ] Automated verification
- [ ] Desktop verification
- [ ] Mobile verification
- [ ] Regression check
- [ ] Final review

## Discoveries
기존 맞춤 장례견적은 전국 장례식장/외부비용 데이터와 상담 요약 기능을 이미 보유한다.

## Decisions
신규 계산기를 중복 제작하지 않고 검색 랜딩의 맥락을 기존 계산기로 전달한다.

## Final verification
진행 중.

## Remaining limitations
진행 중.
