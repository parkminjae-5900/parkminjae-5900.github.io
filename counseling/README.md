# 온결 장례상담 연결 모듈

검증 자료 검색과 규칙 기반 응답 모듈입니다. 생성형 인공지능 서버나 운영 중인 온결 챗봇으로 표시하지 않습니다. 기존 홈페이지·견적 페이지·금액 파일을 변경하지 않았습니다.

## 실행

Node.js 20 이상, 외부 의존성 및 API 키 없이 실행합니다.

```sh
node tests/counseling/evaluate.mjs
printf '%s\n' '{"question":"인천 무빈소 비용이 총액인가요?"}' | node counseling/cli.mjs
```

`engine.mjs`의 `respond(question, state, knowledge, today)`를 서버에서 호출합니다. `state`는 이전 응답에서 돌려받되 같은 상담 세션에만 전달하세요. 지역은 상담 희망 지역이며 고인의 주소·거주기간·관내 자격을 추정하지 않습니다. 새 상담은 `{}`로 초기화합니다. 입력 원문·전화번호·개인정보를 파일에 저장하지 않습니다. 사용자 입력을 화면에 표시할 때 `textContent`를 사용하세요.

응답은 `answers`(답변·근거·확인일·예외·추가 확인), `needs`, `handoff`, `quote`, `state`로 분리합니다. 모르는 내용·자료 만료·예외 분쟁은 보류 또는 상담 전환합니다. `connected:false`는 실제 접수·전화 연결이 이루어진 것이 아님을 뜻합니다.

## 지식과 평가 데이터

- `knowledge.json`: 기존 질문 10개와 추가 12개. 회사 안내와 공공·시설 근거의 적용 범위를 명시합니다. 법령의 최종 개정 여부는 운영 전 원문 재검토가 필요합니다.
- `search-baseline.json`: 기존 검색 질문 100개 원문. 정답은 비어 있으며 학습 정답으로 사용할 수 없습니다.
- `tests/counseling/evaluate.mjs`: 24개 독립 의도 문항과 맥락·예외·금액·잘못된 응답 검출, 100개 원문 회귀 검사.
- `evaluation-report.json`: 재현 가능한 자동검사 결과. 테스트 통과율은 실제 상담 정확도가 아닙니다.

검토기한 30일은 개발팀의 보수적 운영 정책이며 법적 유효기간이 아닙니다. 시설 요금은 이 지식자료에 넣지 않았습니다. 새 근거는 실제 확인 후 출처·확인일·범위·예외·검토기한을 함께 추가해야 합니다. 출처 주소만 존재한다고 검증된 지식이 되는 것은 아닙니다.

## 비용 연결 계약

`calculateQuote(items, options)`는 검증된 가격 어댑터에서만 호출합니다. 사용자·모델이 `verified`, `official`, `confirmed`를 임의로 지정한 값을 신뢰해서는 안 됩니다. 이 모듈은 입력 메타데이터의 증빙 진위를 외부에서 검증하지 않으므로 서버가 공식 요금표와 자격 증빙을 확인하고 공급해야 합니다.

항목 필수값: `id`, `facilityId`, `status:verified`, `sourceGrade:official`, `sourceUrl`, `checkedAt`, `reviewBy`, `effectiveFrom`, `effectiveUntil`, `unitPrice`(원 정수), `quantity`(확정 청구 단위 수), `unit`(hour/day/person/each/fixed), `billingRuleConfirmed:true`.

옵션: `facilityId`, `serviceDate`, `today`, `requiredIds`. 관내·감면 항목은 `eligibilityRequired:true`, `category`와 함께 시설별 `eligibility` 증빙이 필요합니다. 시설명만 일치하는 자료는 연결하지 않습니다. 일당 요금을 임의로 24로 나누거나 최소 빈소를 예약 빈소로 간주하지 않습니다.

미확인 항목이 하나라도 있으면 `total:null`이며 확인된 항목만 `subtotal`로 반환합니다. 중복 ID·음수·소수·무한대·계산 범위 초과는 오류로 거절합니다. 미이용은 `not_applicable`과 별도 확인을 통해 명시합니다. 상품에 포함된 항목은 `includedIn`으로 보류하고 계약 대조 후 제거해야 합니다.

## 생성형 연결 시

현재 외부 모델은 호출하지 않습니다. 모델을 붙이더라도 자유 생성문을 그대로 노출하지 말고, 검증된 카드 선택·구조화된 질문 의도 추출에 한정하는 방식부터 시작하세요. `validateCandidate`는 원문 답변·근거·확인일·예외·추가 확인·전환·계산값의 변조를 거절합니다. 허용된 필드만 렌더링하고 거절된 결과 대신 `respond`의 안전한 응답을 사용합니다. 이 검사는 자유문장의 사실성을 의미적으로 판정하는 도구가 아닙니다.

## 운영 배포 전 별도 통과 조건

1. 실제 온결 저장소·실행 경로·세션 관리·견적 어댑터 확인 후 통합 테스트.
2. 장례지도사가 새로운 질문과 다중 대화를 독립 채점: 의도 적합성, 사실, 근거 범위, 예외·확인질문, 상담 전환을 각각 평가. 무근거 요금·자격 확정·예약 완료 오표시는 1건도 허용하지 않음.
3. 공식 시설 요금표 표본으로 원 단위 수동 계산 대조. 자동 단위환산·중복 포함·감면·무료·누락·날짜 변경을 별도 검수.
4. 실제 화면 모바일 390px·데스크톱 1440px의 출력, 링크, 콘솔, 세션 분리를 확인. 이 변경은 화면을 추가하지 않아 브라우저 검사는 해당 없음.
5. 통과 전 운영 병합·배포 보류. 실제 모델 답변 정확도나 실제 시설 견적 검수를 완료했다고 보고하지 않음.

## 알려진 한계

한국어 의미 이해 모델이 아닌 규칙 기반 분류입니다. 표현 변형, 부정·정정, 복잡한 지시어는 충분히 처리하지 못할 수 있습니다. 100개 검색 질문의 맞춤 답변 완결성을 검증한 것이 아닙니다. 지역별 조례·요금·예약 가능 여부는 실시간 연결 전이며 성남의 안내를 전국 자격 기준으로 일반화하지 않습니다. 상담 전화번호는 기존 회사 공개 안내를 사용했습니다.


## 2026-10-28 후속 검수 및 연결 계층

`session.mjs`의 `createCounselingSession({knowledge, trustedQuoteProvider, clock})`를 상담별로 하나씩 생성합니다. `reply(question)`는 Promise로 응답하며, `reset()`은 상태를 지우고 진행 중인 이전 요청의 결과를 폐기합니다. `snapshot()`은 복사본만 반환합니다. 원본 입력·전화번호·상담 로그를 저장하지 않습니다. 이 모듈을 가져오는 것만으로 온결 원본의 이벤트와 자동 연결되지는 않습니다.

```js
import {createCounselingSession} from './counseling/session.mjs';
const knowledge = await fetch('./counseling/knowledge.json').then(r => r.json());
const session = createCounselingSession({knowledge});
const result = await session.reply('인천 무빈소 비용');
// 실제 화면에서는 answers의 승인된 필드만 textContent로 표시합니다.
// 새 상담 시작시 session.reset()을 호출합니다.
```

`trustedQuoteProvider`는 서버가 관리하는 함수로 `{items, options}`를 돌려줍니다. 공식 요금 확인을 마친 자료만 공급하며 사용자·생성 모델이 검증 플래그를 지정하게 해서는 안 됩니다. 지정하지 않으면 금액을 만들어 내지 않고 확인 필요 상태를 유지합니다. 공급자가 실패하거나 자료가 불완전하면 확정 합계는 null입니다. `verified_items_complete`는 서버가 지정한 필수 항목 집합의 계산 완료일 뿐 장례 전체 비용 확정이나 예약 완료가 아닙니다.

추가 검사:

```sh
node tests/counseling/hardening.mjs
node tests/counseling/session.mjs
node tests/counseling/prices.mjs
node counseling/audit-prices.mjs --write
```

이번 단계에서 실제 가격을 신규 수집하거나 현행 요금으로 인증하지 않았습니다. `price-readiness-report.json`은 저장소 자료의 연결 적격성 검사입니다. 39개 장례식장의 200개 항목은 식별·유효기간·과금 조건 확인 전이며, 62개 화장시설의 721개 항목은 2023년 참고자료이므로 자동 확정 금액에 사용하지 않습니다. 원래 가격 파일은 변경하지 않았습니다.

이전 작업 기록에 원본 위치가 `%USERPROFILE%\Documents\Codex\2026-10-13\new-chat\outputs\funeral-planner\index.html`, 로컬 주소가 `http://127.0.0.1:4317/#explore`로 남아 있습니다. 현재 실행 환경에 그 Windows 폴더가 연결되어 있지 않아 파일 존재·내용은 직접 검증하지 못했습니다. 이 로컬 주소를 현재 서버의 localhost에 대입하거나 홈페이지 시제품을 온결 원본으로 간주해서는 안 됩니다.
