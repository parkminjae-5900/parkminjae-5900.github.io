(function () {
  "use strict";

  // 검색의도별 메인 카피. 시안 번호와 실제 운영 번호를 동일하게 유지합니다.
  var COPIES = {
    1: {
      eyebrow: "일반 · 브랜드 · 직접접속",
      title: "장례는 처음이라…",
      sub: "그 말을 이용하지 않겠습니다.",
      desc: "처음 보이는 상품가격이 아니라 우리 가족이 실제로 내게 될 비용을 확인하세요.",
      cta: "실제 장례비 확인하기 →"
    },
    2: {
      eyebrow: "장례비용 · 장례가격 · 후불상조",
      title: "99만원? 199만원?",
      sub: "중요한 건 광고가격이 아닙니다.",
      desc: "장례가 끝난 뒤, 실제로 얼마를 냈는지가 중요합니다.",
      cta: "실제 장례비 확인하기 →"
    },
    3: {
      eyebrow: "가족장",
      title: "장례비 때문에",
      sub: "더 힘들 필요는 없습니다.",
      desc: "처음엔 저렴해 보여도 하나씩 추가되면 금액은 달라집니다. 처음부터 실제로 들어갈 비용을 보여드립니다.",
      cta: "우리 가족 장례비 바로 보기 →"
    },
    4: {
      eyebrow: "무빈소 · 약식장례 · 간소장",
      title: "장례비, 도대체",
      sub: "얼마가 정상일까요?",
      desc: "무빈소 장례도 이송·안치·입관·화장까지 실제로 들어가는 비용을 먼저 확인하세요.",
      cta: "실제 장례비 확인하기 →"
    }
  };

  // 개인정보가 드러나는 사진은 메인 배경에서 제외합니다.
  var BACKGROUNDS = {
    1: "gallery6.jpg",
    2: "gallery5.jpg",
    3: "gallery6.jpg",
    4: "gallery5.jpg"
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

    var ref = document.referrer || "";
    if (/naver\.|google\.|daum\.|bing\./i.test(ref)) parts.push(ref);
    return norm(parts.join(" "));
  }

  function pickVersion(signal) {
    var p = new URLSearchParams(location.search);
    var forced = Number(p.get("hero"));
    if ([1,2,3,4].indexOf(forced) !== -1) return forced;

    if (/(장례\s*비용|장례비|장례\s*가격|상조\s*가격|상품\s*가격|후불\s*상조|후불상조|비용\s*비교|가격\s*비교|postpaid|funeral-cost|cost)/i.test(signal)) return 2;
    if (/(가족장|family\s*funeral|family)/i.test(signal)) return 3;
    if (/(무빈소|무빈소\s*장례|약식\s*장례|간소장|간소\s*장례|nobinso|no-binso)/i.test(signal)) return 4;
    return 1;
  }

  function applyCopy(copy, version) {
    var eyebrow = document.querySelector("[data-dynamic-hero='eyebrow']");
    var title = document.querySelector("[data-dynamic-hero='title']");
    var sub = document.querySelector("[data-dynamic-hero='sub']");
    var desc = document.querySelector("[data-dynamic-hero='desc']");
    var cta = document.querySelector("[data-dynamic-hero='cta']");
    var hero = document.querySelector(".hero");

    if (eyebrow) eyebrow.textContent = copy.eyebrow;
    if (title) title.textContent = copy.title;
    if (sub) sub.textContent = copy.sub;
    if (desc) desc.textContent = copy.desc;
    if (cta) cta.textContent = copy.cta;
    if (hero) {
      hero.style.setProperty("--hero-bg", "url('" + BACKGROUNDS[version] + "')");
      hero.setAttribute("data-hero-version", String(version));
    }

    document.documentElement.setAttribute("data-hero-copy-version", String(version));
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

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();