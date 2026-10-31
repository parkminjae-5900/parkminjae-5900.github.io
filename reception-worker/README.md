# 다함상조 상담 접수 서버

상태: 구현 초안. 운영 배포 및 실제 접수 검증 전. 기존 GitHub Pages에는 서버 기능이 없어 별도 Worker/D1이 필요합니다.

## 공개 전 결재 사항
1. 접수 담당자와 비공개 접수 내역 확인 경로 확정. 이메일/SMS 자동 알림은 아직 연결하지 않았습니다.
2. 다함상조 소유 Cloudflare 계정의 Worker/D1/Turnstile 사용 승인 및 접근.
3. 연락처·선택 성함·희망 시간 수집, 상담 회신 목적 및 30일 보유 문구 확인.
4. 성공/실패/중복/모바일 실제 검증 후 홈페이지 배포.

## 설치
- `wrangler.example.jsonc`를 로컬 `wrangler.jsonc`로 복사하고 D1 ID 입력.
- D1 생성 후 `wrangler d1 migrations apply daham-consultation-intake --remote` 실행.
- Turnstile 사이트의 허용 호스트를 `www.dahamsangjo.co.kr`, `dahamsangjo.co.kr`로 제한.
- 서버 비밀 `TURNSTILE_SECRET`, 32자 이상의 무작위 `ADMIN_TOKEN`을 `wrangler secret put`으로 설정. 저장소/정적 페이지에 넣지 않음.
- `wrangler deploy` 후 `/requests` HTTPS 주소 및 공개 Turnstile site key를 `consult-request-config.js`에 설정.
- 접수 담당자가 `/admin/requests`를 Bearer 토큰으로 조회할 수 있는지 먼저 확인. 한 번에 최대 200건을 반환하며 `nextCursor`가 있으면 URL 인코딩한 값을 `before` 파라미터로 전달해 다음 페이지를 조회합니다. 조회 결과에 고객 개인정보가 포함되므로 공개 URL/로그/이슈에 올리지 않음.
- 일괄 자동 알림/직원용 로그인 화면은 별도 수신 경로 및 계정 확정 후 연결.

## 동작
보안 토큰·허용 호스트·동의·전화번호를 서버에서 검증하고 D1 저장 확인 후에만 접수 성공 반환. 재시도 UUID와 payload hash로 중복 저장 방지. 접수번호만 고객에게 반환. 관리자 API는 만료된 항목을 즉시 숨기고 예약 작업이 15분 이내 물리 삭제(백업 정책은 운영 계정에서 별도 확인). 개인정보 없는 consult_submit 이벤트만 성공 후 전송하며 분석 차단이 접수 성공을 방해하지 않음. 페이지에 자동 이메일 또는 전화 발신 없음.

## 운영 감시와 백업 결재
- 예시 설정은 Worker 관측 로그를 켜며, 만료 삭제 작업은 실행 시각과 삭제 건수만 기록합니다. 연락처·성함·접수번호는 로그에 남기지 않습니다.
- 운영자는 예약 삭제 실패 알림 경로와 담당자를 배포 전에 정해야 합니다. 로그 활성화만으로 알림 수신자가 만들어지지는 않습니다.
- 운영 계정에서 D1 복구 가능 기간과 복구 시험 절차를 확인해 문서화해야 합니다. 개인정보가 포함된 원본 백업을 GitHub, 분석 도구 또는 관제실에 복사하지 않습니다.
- 30일 보유 정책과 백업 복구 범위가 충돌하지 않도록 만료된 접수의 백업 잔존 처리 기준을 개인정보 안내와 함께 승인해야 합니다.

## 검증
`node --test tests/intake.test.mjs`
`node --check consult-request.js`
`node --check reception-worker/worker.mjs`
`node --check analytics-tracking.js`
`node --check conversion-funnel.js`

## 운영 전 제약
운영 계정·자원·키 미연결. 실제 전송과 UI 검증/담당자 인수 미완료. 설정이 비어 있으면 제출 비활성화하고 전화·카카오 대안 표시. 고객에게 접수 가능하다고 공지하지 않음.

## 2026-10-25 운영 연결 순서 (아직 미실행)
1. 운영 계정 로그인 후 계정 소유자·요금제와 기존 동명 Worker/D1 존재 여부를 확인합니다. 기존 자원이 있으면 재사용하고 새 DB로 바꾸지 않습니다.
2. `reception-worker` 폴더에서 설정 예시를 복사하고, DB가 없을 때만 `wrangler d1 create daham-consultation-intake`로 생성합니다. 반환된 실제 ID를 설정에 넣습니다. 로컬 설정·비밀값 파일은 Git에서 제외됩니다.
3. `wrangler d1 migrations apply daham-consultation-intake --remote`로 스키마를 적용하고 두 비밀값을 설정합니다. 관리자 토큰은 실제 담당자에게 비공개로 전달하고 저장소·채팅·명령행 인수에 넣지 않습니다.
4. Worker 배포 후 `/health`가 200인지 확인합니다. 이는 DB 연결·설정 검사이며 Turnstile 실검증이나 운영 승인 증거는 아닙니다.
5. 담당자 인증 조회, 시험 전용 데이터의 접수·재시도·실패·만료 삭제를 검증합니다. 실제 고객 레코드의 만료 시각을 시험 목적으로 바꾸지 않습니다. 삭제 실패 로그 `expired_requests_cleanup_failed` 및 예약 작업 미실행 감지에 대한 알림 수신자를 연결합니다.
6. PC 1280px 이상, 모바일 360/390/430px에서 보안 위젯·입력·동의·성공·실패 화면 및 전화/카카오 링크를 확인합니다. GA4에서 개인정보가 전송되지 않는지, `consult_submit` 수신과 주요 이벤트 설정도 확인합니다. 분석 차단으로 이벤트가 수집되지 않을 수 있으며 접수 성공과 별개입니다.
7. 아래 운영 조건을 실제 담당자가 확인한 뒤 공개 설정에 서버 주소와 공개 키를 입력합니다. 자동검사와 실제 검증이 모두 통과하면 PR 병합 후 운영 URL에서 다시 확인합니다.

### 보유 정책에서 빠뜨리기 쉬운 점
- D1 Time Travel 복구 범위는 무료 7일, 유료 30일입니다. 원본에서 삭제한 데이터가 복구 시점에 남아 있을 수 있으므로 '원본 30일 삭제'만으로 백업 삭제까지 완료됐다고 설명하면 안 됩니다.
- 요금제, 데이터 저장 위치, 위탁/국외 처리에 관한 실제 조건, 복구 데이터 접근자와 만료 데이터 재삭제 절차를 확인한 뒤 개인정보 안내 문구를 확정합니다. 현재 문구는 운영 법적 검토·승인 완료를 의미하지 않습니다.
- 복구 시 공개 접수를 잠시 중단하고 만료 데이터 삭제와 조회 차단을 확인한 후 재개합니다. 원본 백업 별도 반출은 하지 않습니다.
- 중복 방지는 같은 화면에서 동일한 접수 ID로 재시도하는 범위입니다. 새 탭·새 접수번호까지 전화번호 기준으로 차단하지 않습니다.

공식 참고 자료 (2026-10-25 확인):
- https://developers.cloudflare.com/d1/platform/limits/
- https://developers.cloudflare.com/d1/reference/time-travel/
- https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
- https://developers.google.com/analytics/devguides/collection/ga4/reference/config
