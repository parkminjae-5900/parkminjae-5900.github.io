(function () {
  "use strict";

  var COPIES = {
    1: {
      eyebrow: "처음 보이는 가격보다 실제 총비용",
      title: "장례비, 도대체 얼마가 정상일까요?",
      sub: "누구는 300만 원, 누구는 700만 원. 같은 장례인데 왜 이렇게 다를까요?",
      desc: "비싼 게 좋은 장례는 아닙니다. 우리 가족에게 꼭 필요한 것만 남긴 실제 장례비를 먼저 확인하세요.",
      cta: "실제 장례비 확인하기 →"
    },
    2: {
      eyebrow: "처음부터 실제 비용을 투명하게",
      title: "장례비 때문에 더 힘들 필요는 없습니다.",
      sub: "처음엔 저렴해 보여도 하나씩 추가되면 금액은 달라집니다.",
      desc: "그래서 다함상조는 처음부터 실제로 들어갈 비용을 보여드립니다.",
      cta: "우리 가족 장례비 바로 보기 →"
    },
    3: {
      eyebrow: "선불 가입 없이 · 이용 후 정산",
      title: "장례는 처음이라…",
      sub: "그 말을 이용하지 않겠습니다.",
      desc: "그래서, 장례비는 얼마일까요? 처음 보이는 상품가격이 아니라 우리 가족이 실제로 내게 될 비용을 확인하세요.",
      cta: "실제 장례비 확인하기 →"
    },
    4: {
      eyebrow: "광고가격보다 실제 결제금액",
      title: "99만원? 199만원?",
      sub: "중요한 건 광고가격이 아닙니다.",
      desc: "장례가 끝난 뒤, 실제로 얼마를 냈는지가 중요합니다.",
      cta: "실제 장례비 확인하기 →"
    }
  };

  function norm(v) {
    try { return decodeURIComponent(String(v || "")).toLowerCase().replace(/\+/g, " "); }
    catch (e) { return String(v || "").toLowerCase(); }
  }

  function getSignal() {
    var p = new URLSearchParams(location.search);
    var keys = [
      "utm_term", "utm_campaign", "utm_content", "utm_source",
      "n_keyword", "n_query", "keyword", "query", "term",
      "ad_keyword", "campaign", "search"
    ];
    var parts = [location.pathname, location.hash];
    keys.forEach(function (k) {
      var v = p.get(k);
      if (v) parts.push(v);
    });

    // 검색엔진이 검색어를 referrer에 남기는 경우만 보조 신호로 사용합니다.
    var ref = document.referrer || "";
    if (/naver\.|google\.|daum\.|bing\./i.test(ref)) parts.push(ref);

    return norm(parts.join(" "));
  }

  function pickVersion(signal) {
    // 강한 가격·상조 비교 의도 → 4안
    if (/(장례\s*비용|장례비|장례\s*가격|상조\s*가격|상품\s*가격|후불\s*상조|후불상조|비용\s*비교|가격\s*비교|postpaid|funeral-cost|cost)/i.test(signal)) return 4;

    // 가족장 검색 의도 → 2안
    if (/(가족장|family\s*funeral|family)/i.test(signal)) return 2;

    // 무빈소·간소장 검색 의도 → 1안
    if (/(무빈소|무빈소\s*장례|간소장|nobinso|no-binso)/i.test(signal)) return 1;

    // 브랜드·일반 검색·직접 방문 → 3안
    return 3;
  }

  function applyCopy(copy, version) {
    var eyebrow = document.querySelector("[data-dynamic-hero='eyebrow']");
    var title = document.querySelector("[data-dynamic-hero='title']");
    var sub = document.querySelector("[data-dynamic-hero='sub']");
    var desc = document.querySelector("[data-dynamic-hero='desc']");
    var cta = document.querySelector("[data-dynamic-hero='cta']");

    if (eyebrow) eyebrow.textContent = copy.eyebrow;
    if (title) title.textContent = copy.title;
    if (sub) sub.textContent = copy.sub;
    if (desc) desc.textContent = copy.desc;
    if (cta) cta.textContent = copy.cta;

    document.documentElement.setAttribute("data-hero-copy-version", String(version));

    // GA4/태그매니저가 있으면 A/B 성과분석에 바로 사용할 수 있도록 이벤트를 남깁니다.
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event: "hero_copy_impression",
      hero_copy_version: "v" + version,
      hero_signal: getSignal().slice(0, 180)
    });
  }

  function init() {
    var signal = getSignal();
    var version = pickVersion(signal);
    applyCopy(COPIES[version], version);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();