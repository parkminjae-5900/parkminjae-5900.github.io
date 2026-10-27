# 개발 전용 공통 견적 엔진

운영 페이지에 연결하지 않은 모듈입니다. `engine.mjs`는 공통 계산 규칙, `adapters.mjs`는 기존 계산기 state/입력값과 PR24 상품 선택값을 공통 입력으로 바꿉니다. 기존 인라인 함수, 시설 식별, 데이터 파일은 변경하지 않습니다.

실행:

```sh
node --test tests/quote-rules/engine.test.mjs
node --check dev/quote-rules/engine.mjs
node --check dev/quote-rules/adapters.mjs
```

```js
import {fromLegacy, fromPrototype} from './adapters.mjs';
const legacy = fromLegacy({mode:'package',productId:'nobinso'});
const prototype = fromPrototype({product:1200000});
console.assert(legacy.subtotal === prototype.subtotal);
// 1200000: 최종 총액이 아니라 확인된 상품비 소계
console.assert(legacy.finalTotal === null);
console.assert(legacy.readyForCustomer === false);
```

## 입력 계약

- `mode`는 `package` 또는 `itemized`. 개별 모드에는 상품 ID를 넣을 수 없습니다. 어댑터의 기존 기본 모드는 개별 견적입니다.
- 상품 ID: `nobinso`, `family249`, `general360`, `premium499`. PR24 숫자 상품가는 어댑터에서 ID로 변환합니다.
- 서비스 ID는 인력·용품·차량별 고정 목록을 사용합니다. 같은 ID 두 행은 오류입니다. 포함 수량 내 선택은 금액 0, 상태 `included`로 표시합니다. `pending`은 금액 `null`입니다.
- 무빈소 관·수의는 공식 사양과 일치할 때만 포함으로 분류합니다. 카탈로그의 개별 판매가를 상품 안의 원가·공제금액으로 쓰지 않습니다.
- `assistant`는 기존 ‘보조 장례지도사(입관식)’와 공식 ‘염습상례사’의 입관 업무 중첩을 막기 위한 대응입니다. 자격·인물·계약 명칭의 완전한 동일성을 확정하는 기능은 아닙니다. 별도 업무라면 확인된 추가 약정이 필요합니다.
- 추가인력·차량의 `quantity`는 전체 필요량입니다. 확인된 포함량을 뺀 양수 초과분만 계산합니다. 도우미의 인시간 전환은 계약의 인원·시간 조건이 전환 가능한 경우에만 사용합니다. 기존 계산기는 원래 단위 `인회`를 보존합니다.
- `coverage` 추가약정은 `status:'confirmed'`, `reference`, `productId`, `quantity`, `unit`을 요구합니다. `tariff`는 같은 상품·서비스·단위의 `serviceId`, `unitPrice`까지 일치해야 합니다.
- 교체품목은 `kind:'upgrade'`, `delta`, `deltaEvidence`를 사용합니다. 근거에 상품 ID·서비스 ID·승인된 `amount`가 정확히 대응해야 합니다. 음수 공제는 이 모듈에서 지원하지 않습니다.
- 외부비는 `room`, `morgue`, `preparation`, `food`, `cremation`, `burial`, `facilityOther`로 분리합니다. 선택 시설·호실 ID와 근거가 일치해야 하며, 시설요금은 `applicabilityConfirmed:true`가 필요합니다. 외부요금 근거는 `category`, `unit`, `unitPrice`, `status`, `reference`를 포함합니다.
- 시간 요금은 `hour/hourly`, 일 요금은 확인된 `day/ceil24` 또는 `day/prorata24`만 허용합니다. 근거의 `billing`도 일치해야 합니다. 달력일·최소시간·심야 등 다른 규칙은 이 엔진에서 추정하지 않고 보류합니다.
- `notUsed:true`는 실제 미사용을 명시한 경우에만 전달합니다. 무빈소는 빈소만 자동 미사용이며, 안치·입관실은 계속 미확인으로 남습니다.
- 수기 입력을 공식 확인값으로 자동 승격하지 않습니다. 원본의 `hallCost`, `hallEtc`는 둘 다 확인 대기 명세에 보존합니다. 시설 전체 금액을 항목별 금액과 함께 중복 전달하면 안 됩니다.
- `proof`/`coverage`는 개발 API의 신뢰된 입력 계약이며, 인증·전자서명 기능이 아닙니다. 운영 연결 시 고객이 직접 확인 플래그를 설정하지 못하도록 검증 계층이 생성해야 합니다.

## 반환 및 연결 제한

`subtotal`, `rows`, `pending`, `warnings`를 반환합니다. `finalTotal:null`, `readyForCustomer:false`는 의도적인 개발 단계 표시입니다. 포함·미사용·미확인을 화면에서 구분하고 미확인 항목을 생략하지 않는 소비자가 필요합니다.

고객용 두 화면의 연결, 화면·인쇄·모바일 검증, 세 상품의 상세 구성 확정은 아직 수행하지 않았습니다. 이 모듈 통과만으로 고객 배포가 승인되는 것은 아닙니다.
