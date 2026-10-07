(function () {
  const cfg = window.DAHAM_INTAKE || {};
  const form = document.getElementById('callback-request');
  const fields = document.getElementById('request-fields');
  const availability = document.getElementById('availability');
  const result = document.getElementById('request-result');
  const submit = document.getElementById('request-submit');
  let token = '', widget, busy = false, completed = false, attempt;
  const unavailable = '온라인 접수를 준비 중입니다. 전화 1600-6131 또는 카카오톡으로 문의해 주세요.';
  let endpoint;
  try {
    endpoint = new URL(cfg.endpoint);
    if (endpoint.protocol !== 'https:' || endpoint.username || endpoint.password || !cfg.turnstileSiteKey) throw Error();
  } catch (_) { availability.textContent = unavailable; return; }
  availability.textContent = '보안 확인을 불러오고 있습니다.';
  window.dahamIntakeReady = function () {
    try {
      widget = window.turnstile.render('#security-check', {
        sitekey: cfg.turnstileSiteKey, action: 'consultation', size: 'flexible',
        callback: function (value) { token = value; },
        'expired-callback': function () { token = ''; },
        'error-callback': function () { token = ''; result.textContent = '보안 확인을 다시 진행해 주세요. 계속 실패하면 전화로 문의해 주세요.'; }
      });
      fields.disabled = false;
      availability.textContent = '';
    } catch (_) { availability.textContent = unavailable; }
  };
  const script = document.createElement('script');
  script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?onload=dahamIntakeReady&render=explicit';
  script.async = true;
  script.onerror = function () { availability.textContent = unavailable; };
  document.head.appendChild(script);
  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    if (busy || completed || !form.reportValidity()) return;
    const data = new FormData(form);
    const phone = String(data.get('phone') || '').replace(/[\s()+-]/g, '').replace(/^82/, '0');
    if (!/^0\d{8,10}$/.test(phone)) { result.textContent = '연락 가능한 국내 전화번호를 확인해 주세요.'; return; }
    if (!token) { result.textContent = '보안 확인을 완료한 뒤 다시 신청해 주세요.'; return; }
    const payload = {name: String(data.get('name') || '').trim(), phone, contactTime: data.get('contactTime'), consent: data.get('consent') === 'on', consentVersion: '2026-10-07'};
    // Retain only in memory. Reuse the request ID after uncertain network failures.
    const fingerprint = JSON.stringify(payload);
    if (!attempt || attempt.fingerprint !== fingerprint) attempt = {id: crypto.randomUUID(), fingerprint};
    busy = true; fields.disabled = true; submit.textContent = '접수 중…'; result.textContent = '';
    try {
      const response = await fetch(endpoint.href, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({...payload, requestId:attempt.id, turnstileToken:token}), signal:AbortSignal.timeout(15000), credentials:'omit', referrerPolicy:'no-referrer'});
      const receipt = await response.json();
      if (!response.ok || receipt.ok !== true || receipt.requestId !== attempt.id) throw Error('not-confirmed');
      completed = true;
      form.reset(); form.hidden = true;
      result.textContent = '상담 신청이 접수되었습니다. 신청을 확인한 뒤 전화드리겠습니다. 긴급한 경우 1600-6131로 연락해 주세요. 접수번호: ' + receipt.requestId;
      result.focus();
      // No contact data, request IDs, free text or attribution storage sent to GA4.
      try { if (typeof window.gtag === 'function') window.gtag('event', 'consult_submit', {form_id:'callback_request', method:'website', send_to:window.DAHAM_ANALYTICS?.ga4MeasurementId}); } catch (_) {}
      attempt = null;
    } catch (_) {
      result.textContent = '접수 완료를 확인하지 못했습니다. 다시 신청해 주세요. 이 화면에서 같은 내용으로 재시도하면 중복 접수를 방지합니다. 급한 상담은 1600-6131로 전화해 주세요.';
      result.focus();
    } finally {
      busy = false;
      if (!completed) { fields.disabled = false; submit.textContent = '다시 신청하기'; token = ''; window.turnstile.reset(widget); }
    }
  });
})();
