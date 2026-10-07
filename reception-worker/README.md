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
