(function () {
  'use strict';

  const STORAGE_KEY = 'dahamPreferredRegion';
  const MAX_AUTO_DISTANCE_KM = 95;
  const REGION_POINTS = [
    ['강남',37.5172,127.0473],['강동',37.5301,127.1238],['강북',37.6396,127.0257],
    ['강서',37.5509,126.8495],['관악',37.4784,126.9516],['광진',37.5385,127.0823],
    ['구로',37.4955,126.8874],['금천',37.4569,126.8955],['노원',37.6542,127.0568],
    ['도봉',37.6688,127.0471],['동대문',37.5744,127.0396],['동작',37.5124,126.9393],
    ['마포',37.5663,126.9019],['서대문',37.5791,126.9368],['서초',37.4837,127.0324],
    ['성동',37.5633,127.0369],['성북',37.5894,127.0167],['송파',37.5145,127.1059],
    ['양천',37.5169,126.8665],['영등포',37.5264,126.8963],['용산',37.5326,126.9900],
    ['은평',37.6027,126.9291],['종로',37.5735,126.9790],['서울 중구',37.5641,126.9979],
    ['중랑',37.6063,127.0927],
    ['수원',37.2636,127.0286],['성남',37.4200,127.1265],['고양',37.6584,126.8320],
    ['용인',37.2411,127.1776],['부천',37.5034,126.7660],['안산',37.3219,126.8309],
    ['안양',37.3943,126.9568],['남양주',37.6360,127.2165],['화성',37.1995,126.8312],
    ['평택',36.9921,127.1129],['의정부',37.7381,127.0337],['시흥',37.3802,126.8029],
    ['파주',37.7599,126.7800],['김포',37.6153,126.7156],['광명',37.4786,126.8644],
    ['경기 광주',37.4294,127.2550],['군포',37.3617,126.9352],['하남',37.5393,127.2148],
    ['오산',37.1498,127.0770],['이천',37.2720,127.4350],['안성',37.0080,127.2797],
    ['구리',37.5943,127.1296],['의왕',37.3449,126.9683],['포천',37.8949,127.2003],
    ['양주',37.7853,127.0458],['동두천',37.9034,127.0605],['과천',37.4292,126.9876],
    ['여주',37.2983,127.6370],['양평',37.4917,127.4876],['가평',37.8315,127.5096],
    ['연천',38.0964,127.0748],
    ['인천 중구',37.4738,126.6218],['인천 동구',37.4739,126.6432],['인천 미추홀구',37.4635,126.6500],
    ['인천 연수구',37.4102,126.6780],['인천 남동구',37.4473,126.7315],['인천 부평구',37.5070,126.7218],
    ['인천 계양구',37.5373,126.7377],['인천 서구',37.5454,126.6759],['인천 강화군',37.7465,126.4880],
    ['춘천',37.8813,127.7298],['원주',37.3422,127.9202],['강릉',37.7519,128.8761],
    ['동해',37.5247,129.1143],['태백',37.1641,128.9856],['속초',38.2070,128.5918],
    ['삼척',37.4500,129.1650],['홍천',37.6972,127.8886],['횡성',37.4918,127.9850],
    ['영월',37.1837,128.4610],['평창',37.3705,128.3903],['정선',37.3806,128.6609],
    ['철원',38.1467,127.3134],['화천',38.1063,127.7082],['양구',38.1100,127.9900],
    ['인제',38.0695,128.1707],['고성',38.3806,128.4679],['양양',38.0755,128.6191]
  ].map(([name, lat, lon]) => ({ name, lat, lon }));

  const PAGE_COPY = {
    family: {
      label: '가족장',
      title: region => `${region} 가족장 | 소규모 장례·후불상조 · 다함상조`,
      description: region => `${region} 가족장 상담. 지역 장례식장 비교, 소규모 장례, 후불상조, 장례비용을 24시간 안내합니다. 1600-6131`,
      keywords: region => `${region} 가족장, ${region} 소규모 장례, ${region} 장례식장, ${region} 후불상조, ${region} 장례비용`,
      badge: region => `${region} 가족장 · 소규모 장례`,
      heading: region => `${region} 가족장 안내`,
      lead: region => `가족과 가까운 분들 중심으로 조용하고 품격 있게 진행하는 ${region} 가족장 상담을 안내합니다.`,
      summaryHeading: region => `${region} 가족장이란?`,
      summary: region => `가족장은 조문 규모를 줄이고 가족 중심으로 고인과 마지막 시간을 보내는 장례 방식입니다. ${region} 지역의 장례식장 이용 조건과 가족 상황을 함께 확인해 빈소 운영, 입관, 발인 절차를 안내합니다.`,
      search: region => `${region} 가족장, ${region} 소규모 장례, ${region} 장례식장, ${region} 후불상조, ${region} 장례비용 상담을 찾으시는 분들께 다함상조가 필요한 절차와 비용을 안내해드립니다.`
    },
    nobinso: {
      label: '무빈소 장례',
      title: region => `${region} 무빈소 장례 | 간소장례·후불상조 · 다함상조`,
      description: region => `${region} 무빈소 장례 상담. 빈소 없이 필요한 절차 중심으로 진행하는 간소장례와 장례비용을 24시간 안내합니다. 1600-6131`,
      keywords: region => `${region} 무빈소 장례, ${region} 무빈소, ${region} 간소장례, ${region} 후불상조, ${region} 장례비용`,
      badge: region => `${region} 무빈소 · 간소장례`,
      heading: region => `${region} 무빈소 장례 안내`,
      lead: region => `빈소 운영 부담을 줄이고 필요한 절차 중심으로 진행하는 ${region} 무빈소 장례 상담을 안내합니다.`,
      summaryHeading: region => `${region} 무빈소 장례란?`,
      summary: region => `무빈소 장례는 별도 빈소 운영 없이 고인 이송, 안치, 입관, 발인과 화장장 이동 등 필요한 절차 중심으로 진행합니다. ${region} 지역의 이용 가능한 시설과 일정을 확인해 안내합니다.`,
      search: region => `${region} 무빈소 장례, ${region} 간소장례, ${region} 장례식장, ${region} 후불상조, ${region} 장례비용 상담을 찾으시는 분들께 다함상조가 필요한 절차와 비용을 안내해드립니다.`
    },
    cost: {
      label: '장례비용',
      title: region => `${region} 장례비용 상담 | 가족장·무빈소·후불상조`,
      description: region => `${region} 장례비용 상담. 가족장, 무빈소 장례, 일반장례, 후불상조의 필요 항목과 별도 비용을 24시간 안내합니다. 1600-6131`,
      keywords: region => `${region} 장례비용, ${region} 가족장 비용, ${region} 무빈소 비용, ${region} 후불상조, ${region} 장례식장 비용`,
      badge: region => `${region} 장례비용 · 후불상조`,
      heading: region => `${region} 장례비용 안내`,
      lead: region => `${region} 장례식장의 빈소 사용 여부, 장례 일수, 용품, 차량과 인력 구성을 확인해 필요한 비용을 안내합니다.`,
      summaryHeading: region => `${region} 장례비용이 달라지는 이유`,
      summary: region => `${region} 지역에서도 빈소 사용 여부, 조문 규모, 입관용품, 관·수의, 차량, 도우미 인력과 화장장 일정에 따라 장례비용이 달라질 수 있습니다. 상담 시 포함 항목과 별도 비용을 구분해 안내합니다.`,
      search: region => `${region} 장례비용, ${region} 가족장 비용, ${region} 무빈소 비용, ${region} 후불상조, ${region} 장례식장 비용 상담을 찾으시는 분들께 다함상조가 필요한 절차와 비용을 안내해드립니다.`
    }
  };

  function haversine(lat1, lon1, lat2, lon2) {
    const rad = value => value * Math.PI / 180;
    const dLat = rad(lat2 - lat1);
    const dLon = rad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLon / 2) ** 2;
    return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function nearestRegion(lat, lon) {
    let best = null;
    REGION_POINTS.forEach(region => {
      const distance = haversine(lat, lon, region.lat, region.lon);
      if (!best || distance < best.distance) best = { name: region.name, distance };
    });
    return best && best.distance <= MAX_AUTO_DISTANCE_KM ? best : null;
  }

  function normalizeRegion(raw) {
    let region = String(raw || '').replace(/[<>"'`]/g, '').replace(/\s+/g, ' ').trim();
    if (!region || region.length > 18 || !/[가-힣]/.test(region)) return '';
    region = region.replace(/^(서울특별시|경기도|강원특별자치도|강원도)\s*/, '').replace(/(특별자치시|특별자치도|특별시|광역시)$/,'');
    if (/^(수원|성남|고양|용인|부천|안산|안양|남양주|화성|평택|의정부|시흥|파주|김포|광명|광주|군포|하남|오산|이천|안성|구리|의왕|포천|양주|동두천|과천|여주)시$/.test(region)) region = region.slice(0, -1);
    if (/^(양평|가평|연천|춘천|원주|강릉|동해|태백|속초|삼척|홍천|횡성|영월|평창|정선|철원|화천|양구|인제|고성|양양)군$/.test(region)) region = region.slice(0, -1);
    if (/^(강남|강동|강북|강서|관악|광진|구로|금천|노원|도봉|동대문|동작|마포|서대문|서초|성동|성북|송파|양천|영등포|용산|은평|종로|중랑)구$/.test(region)) region = region.slice(0, -1);
    const withoutSuffix = region.replace(/[시군구]$/, '');
    if (REGION_POINTS.some(point => point.name === withoutSuffix)) region = withoutSuffix;
    return region;
  }

  function updateMeta(selector, content) {
    const node = document.querySelector(selector);
    if (node) node.setAttribute('content', content);
  }

  function applyRegionPage(region) {
    const service = document.body.dataset.regionService;
    const copy = PAGE_COPY[service];
    if (!copy || !region) return;
    // 공통 대표주소의 검색 정보는 유지하고 본문 지역 안내만 개인화합니다.
    const values = {
      'region-badge': copy.badge(region),
      'region-title': copy.heading(region),
      'region-lead': copy.lead(region),
      'region-summary-title': copy.summaryHeading(region),
      'region-summary': copy.summary(region),
      'region-search': copy.search(region)
    };
    Object.entries(values).forEach(([id, value]) => {
      const element = document.getElementById(id);
      if (element) element.textContent = value;
    });
    const bar = document.createElement('div');
    bar.className = 'daham-region-bar';
    bar.innerHTML = `<strong>현재 지역 안내: <span></span></strong><button type="button">지역 변경</button>`;
    bar.querySelector('span').textContent = region;
    bar.querySelector('button').addEventListener('click', () => openRegionDialog(location.pathname.split('/').pop() || 'index.html', true));
    const hero = document.querySelector('.hero');
    if (hero) hero.before(bar);
  }

  function addInterfaceStyles() {
    if (document.getElementById('daham-region-styles')) return;
    const style = document.createElement('style');
    style.id = 'daham-region-styles';
    style.textContent = `
      .daham-region-bar{display:flex;justify-content:center;align-items:center;gap:14px;padding:10px 18px;background:#fff4d8;border-bottom:1px solid #e5c77f;color:#4d3218;font-size:15px;position:relative;z-index:30}
      .daham-region-bar button{border:1px solid #9b6a15;background:#fff;color:#6f470c;border-radius:999px;padding:7px 13px;font-weight:800;cursor:pointer}
      .daham-region-overlay{position:fixed;inset:0;background:rgba(20,15,10,.62);z-index:12000;display:grid;place-items:center;padding:18px}
      .daham-region-dialog{width:min(520px,100%);background:#fff;border-radius:22px;padding:28px;box-shadow:0 28px 80px rgba(0,0,0,.3);color:#271d16;position:relative}
      .daham-region-dialog h2{margin:0 42px 8px 0;font-size:26px;color:#3f2a18}
      .daham-region-dialog p{margin:8px 0 16px;font-size:16px;line-height:1.65}
      .daham-region-close{position:absolute;right:17px;top:12px;border:0;background:transparent;font-size:30px;cursor:pointer;color:#5d5048}
      .daham-location-btn,.daham-manual-btn{width:100%;border:0;border-radius:12px;padding:14px 18px;font-size:17px;font-weight:900;cursor:pointer}
      .daham-location-btn{background:#b88712;color:#fff;margin-bottom:12px}
      .daham-manual{display:flex;gap:8px;margin-top:12px}
      .daham-manual input{min-width:0;flex:1;border:1px solid #cdbb9f;border-radius:12px;padding:13px;font-size:16px}
      .daham-manual-btn{width:auto;background:#281d15;color:#fff;white-space:nowrap}
      .daham-region-status{min-height:26px;color:#755119;font-weight:700}
      .daham-region-privacy{font-size:13px!important;color:#746a61;margin-bottom:0!important}
      @media(max-width:520px){.daham-manual{display:grid}.daham-manual-btn{width:100%}.daham-region-dialog{padding:24px 20px}.daham-region-bar{justify-content:space-between}}
    `;
    document.head.appendChild(style);
  }

  function navigateTo(page, region) {
    const clean = normalizeRegion(region);
    if (!clean) return false;
    try { localStorage.setItem(STORAGE_KEY, clean); } catch (error) { /* storage may be blocked */ }
    location.href = `${page}?region=${encodeURIComponent(clean)}`;
    return true;
  }

  function openRegionDialog(page, manualFirst) {
    document.querySelector('.daham-region-overlay')?.remove();
    const overlay = document.createElement('div');
    overlay.className = 'daham-region-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'daham-region-heading');
    overlay.innerHTML = `
      <div class="daham-region-dialog">
        <button class="daham-region-close" type="button" aria-label="닫기">×</button>
        <h2 id="daham-region-heading">현재 지역 맞춤 안내</h2>
        <p>현재 위치를 확인해 <b>지역명 + 장례 안내</b>로 보여드립니다.</p>
        <button class="daham-location-btn" type="button">현재 위치로 찾기</button>
        <div class="daham-region-status" aria-live="polite"></div>
        <div class="daham-manual">
          <input type="text" maxlength="18" placeholder="지역 직접 입력 (예: 수원, 강남, 철원)" aria-label="지역명">
          <button class="daham-manual-btn" type="button">지역 적용</button>
        </div>
        <p class="daham-region-privacy">위치 좌표는 서버로 전송하거나 저장하지 않고, 지역명 판별에만 사용합니다.</p>
      </div>`;
    document.body.appendChild(overlay);
    const status = overlay.querySelector('.daham-region-status');
    const input = overlay.querySelector('input');
    const close = () => overlay.remove();
    overlay.querySelector('.daham-region-close').addEventListener('click', close);
    overlay.addEventListener('click', event => { if (event.target === overlay) close(); });
    const submitManual = () => {
      const region = normalizeRegion(input.value);
      if (!region) {
        status.textContent = '지역명을 한글로 입력해 주세요.';
        input.focus();
        return;
      }
      navigateTo(page, region);
    };
    overlay.querySelector('.daham-manual-btn').addEventListener('click', submitManual);
    input.addEventListener('keydown', event => { if (event.key === 'Enter') submitManual(); });
    const locate = () => {
      if (!navigator.geolocation) {
        status.textContent = '이 브라우저에서는 위치 확인을 지원하지 않습니다. 지역을 직접 입력해 주세요.';
        input.focus();
        return;
      }
      status.textContent = '현재 위치를 확인하고 있습니다…';
      navigator.geolocation.getCurrentPosition(position => {
        const match = nearestRegion(position.coords.latitude, position.coords.longitude);
        if (!match) {
          status.textContent = '현재 위치의 시·군·구를 직접 입력해 주세요.';
          input.focus();
          return;
        }
        status.textContent = `${match.name} 지역 안내로 이동합니다.`;
        navigateTo(page, match.name);
      }, () => {
        status.textContent = '위치 권한을 확인하지 못했습니다. 지역을 직접 입력해 주세요.';
        input.focus();
      }, { enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 });
    };
    overlay.querySelector('.daham-location-btn').addEventListener('click', locate);
    if (manualFirst) input.focus(); else locate();
  }

  function initializeLinks() {
    document.querySelectorAll('[data-region-target]').forEach(link => {
      link.addEventListener('click', event => {
        event.preventDefault();
        event.stopPropagation();
        openRegionDialog(link.dataset.regionTarget, false);
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    addInterfaceStyles();
    initializeLinks();
    const requested = normalizeRegion(new URLSearchParams(location.search).get('region'));
    if (requested) {
      try { localStorage.setItem(STORAGE_KEY, requested); } catch (error) { /* storage may be blocked */ }
      applyRegionPage(requested);
    }
  });

  window.DahamRegion = { nearestRegion, normalizeRegion };
})();
