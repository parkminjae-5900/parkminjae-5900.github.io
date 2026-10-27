# 온결 상담 근거·평가 모듈

## Goal
실제 구현 조사와 연결 가능한 검증 지식·상담 응답·비용 검수 모듈 제공.

## Current state
조사 기준 main 20ebd59366e1e1e8689091c408a1076de4bc04c2. PR #24는 공개 전 초안이며 head 55c0534a9bd96855074b85e5da17351135d1720b. `ai-funeral-estimate.html`의 tokens/search는 문자열 가중 검색, facilityFee는 최저 빈소·시간 비례 계산이며 생성 모델 호출 없음. `ai-funeral-guide.html`은 정적 설명 페이지. 접근 가능한 저장소 3개(홈페이지, Hanul, daham-cemetery-site) 기본 브랜치 코드에서 온결·chatbot·주요 생성 API 문자열을 확인했으나 별도 상담 서버 식별 실패. 홈페이지의 원격 브랜치 이름·전체 커밋 메시지와 별도 견적 브랜치 파일 목록도 점검. 접근 불가능한 로컬 PC 또는 다른 계정 소스 존재 여부는 알 수 없음.

## Requirements
요청된 장례 범위, 검증 근거·확인일·예외, 미확인 요금 금지, 맥락·지역·계산·전환 검사.

## Non-goals
운영 배포, 기존 가격 수정, 생성형 서버가 연결됐다는 표시.

## Implementation steps
1. 코드와 기존 질문 10개·100개 검토.
2. counseling/knowledge.json 및 검색 입력 분리.
3. engine.mjs와 cli.mjs, 계산 모듈, 출력 검증.
4. 독립 사례·안전·계산 평가 및 CI.

## Verification plan
Node 구문 검사, 독립 의도·다중 대화·가격 산식·변조 검출, 저장소 기존 Python 테스트 및 보안 검사. 변경 UI 없음: 모바일·데스크톱·이미지·콘솔 검사는 해당 없음. 통합 UI 확인은 운영 전 필수. 패키지 빌드·타입체크 구성 없음.

## Risks
검색 규칙의 표현 변형 한계, 회사 자료의 적용 범위, 근거 시효, 미연결 운영 소스. 자동검사는 실제 상담 정확도나 시설 금액의 진위 검증을 대체하지 않음.

## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [x] Desktop verification (UI 변경 없음)
- [x] Mobile verification (UI 변경 없음)
- [x] Regression check
- [x] Final review

## Discoveries
기존 100문항은 무빈소 30, 가족장 20, 시설 20, 후불상조 15, 절차·장지 15개. 관측 열이 비어 있어 정답·학습자료 아님. 기존 FAQ 10개는 회사 설명이며 공공 규정과 분리 필요. PR #24의 동일명 대체 매칭·과거자료·과금 단위 확정 문제가 있어 새 모듈에서는 불확실하면 계산 보류.

## Decisions
실제 온결 서버 위치를 확인하지 못했으므로 독립 모듈을 홈페이지 저장소 새 브랜치에 추가하고 검수용 PR로 전달. 기존 실행 파일은 변경하지 않음. 시설 가격은 지식자료에 복사하지 않음. 생성형 제공자 API 키가 필요하지 않은 검증 카드 방식.

## Final verification
170개 자동검사 통과, 지식 카드 22개, 기존 검색 입력 100개. 독립 의도 사례 24개 외에 맥락·안전·수치·변조 검사 포함. 실제 상담 정답률 미측정. 기존 Python 테스트 15개 통과, 공개 저장소 보안 검사 통과, git diff --check 통과. CLI 입력·출력 확인.

## Remaining limitations
별도 온결 소스·생성형 서버·실시간 시설 자료 어댑터 미연결. 전문가 독립 정답 판정, 실제 요금표 대조, 통합 화면 검수 후 배포 가능.
