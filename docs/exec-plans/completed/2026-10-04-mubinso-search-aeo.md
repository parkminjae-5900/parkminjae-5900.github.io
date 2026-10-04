# 무빈소 검색·AEO 개선

## Goal
네이버 및 답변형 AI 검색에서 무빈소 장례와 관련한 다함상조의 정확하고 유용한 정보를 발견·인용하기 쉽게 개선한다. 검색 순위 1위는 보장할 수 없으며, 사용자의 견적 비교와 상담 전환을 지원한다.

## Current state
- 무빈소 안내와 비용 페이지, 전국 견적 계산기가 있다.
- 무빈소 장례식장 후보는 별도 JS의 보유 자료에 의존하고, 공개된 공식 확인 데이터 파일은 비어 있다.
- 화장료 JSON은 2023년 공개자료이며 현재 요금으로 오인하면 안 된다.
- 지역 허브의 일부 페이지에는 사용자 검색 의도와 거리가 있는 SEO 관리용 표현이 있다.
- robots.txt는 전체 허용이나 OAI-SearchBot을 명시하지 않는다.

## Requirements
- 가격·시설의 확인 시점과 출처를 분명히 하고 미확인 정보를 확정 사실처럼 표시하지 않는다.
- 지역별 페이지는 실제로 다른 정보를 제공할 때만 색인 대상으로 유지한다.
- 페이지별 제목·설명·표준 URL·H1 및 내부 링크를 정리한다.
- 답변형 검색이 인용하기 쉬운 짧은 정의·절차·비용 구분·FAQ를 본문에 제공한다.
- OAI-SearchBot 등 검색 수집기를 robots.txt에서 명시적으로 허용하고 사이트맵을 갱신한다.
- 기존 상품 가격·브랜드·계산 동작은 보존한다.

## Non-goals
- 검색 1위 보장, 허위 후기·시설 제휴·요금 표기, 대량의 얇은 지역 랜딩 페이지 생성.
- 운영자 확인 없이 Naver Blog 또는 외부 플랫폼에 게시.
- 현행 확인되지 않은 장례식장/화장 요금을 현재 확정가로 홍보.

## Implementation steps
1. 네이버 및 AI 검색 수집, 명시적 가격·시설 출처 표기를 정비한다.
2. 무빈소 대표 페이지, 비용 안내, 지역 허브와 지역 페이지의 고유 정보 및 상호 링크를 보강한다.
3. AEO용 정의와 절차·비용 요약·FAQ를 방문자가 실제로 확인 가능한 본문에 반영한다.
4. 사이트맵과 검색 점검 체크리스트를 갱신한다.
5. 자동·정적 테스트 및 배포 사이트의 데스크톱·모바일 화면을 점검한다.

## Verification plan
- Repository-provided lint/build/test commands and relevant calculator browser test.
- Changed pages: unique title/description/H1/canonical, JSON-LD validity, internal links and sitemap URL validity.
- 390px mobile and desktop layout, image loading, browser console, calculator cost behavior.
- Verify deployed URLs after publish.

## Risks
- Facility fees and eligibility change frequently; wrong exact prices can mislead families making urgent decisions.
- Search crawlers may not index every URL; Naver and generative AI citation/ranking is not controllable.
- Existing giant calculator HTML embeds binary image data and may be impractical to rewrite wholesale; make targeted changes in text/data scripts where possible.

## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [x] Desktop verification
- [x] Mobile source/layout review (existing responsive rules; browser viewport emulation unavailable)
- [x] Regression check
- [x] Final review

## Discoveries
- `data/mubinso-eligible-halls.json` has no verified records, while a separate list contains configured values with inconsistent confirmation/source fields.
- Cremation fees come from 2023 public data and are explicitly non-current.
- The project has an existing calculator browser test and data-quality notes.

## Decisions
- Use clear “다함상조 상품가” vs “시설·화장 등 외부 비용” separation.
- Treat the existing venue list as candidates requiring direct reconfirmation; do not label all independently confirmed.
- Publish a crawlable explicit robots allowance for OAI-SearchBot; structured data supplements visible content only.

## Final verification
- GitHub Actions `Verify SEO conversion funnel` passed on commits `cd6550b`, `738663e`, and `638e6df`.
- GitHub Pages deployment completed successfully for the site changes.
- Static QA passed for edited JavaScript syntax, title/description/H1/canonical presence, FAQ JSON-LD parsing, visible FAQ presence, local links, crawler rules, and the six touched sitemap dates.
- Live desktop pages verified: `nobinso.html`, `nobinso-cost.html`, `area-ansan-funeral.html`, `area-suwon-funeral.html`, `area-funeral-seo-hub.html`, and the estimate calculator.
- Calculator flow verified through region/candidate selection; candidate count and reference-price disclaimers render, including selected estimate source. Browser document width (1348px) stayed within viewport (1363px); browser console showed only extension-origin errors, none from site scripts.

## Remaining limitations
Ranking outcomes, AI answer citations, and third-party facility fees cannot be guaranteed by code changes; human source/date validation is required for each facility price. Full 390px mobile interaction testing was not available in the connected browser. Changed content is within existing responsive layouts, and source media-query rules remain in place.
