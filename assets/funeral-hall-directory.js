// Progressive enhancement: all records and pagination remain usable without JS.
(() => {
  const input = document.querySelector('#hall-filter');
  const status = document.querySelector('#filter-status');
  const cards = [...document.querySelectorAll('[data-facility-id]')];
  if (!input || !status) return;
  input.addEventListener('input', () => {
    const query = input.value.normalize('NFC').trim().toLocaleLowerCase('ko');
    let shown = 0;
    for (const card of cards) {
      const match = !query || card.textContent.normalize('NFC').toLocaleLowerCase('ko').includes(query);
      card.hidden = !match;
      if (match) shown++;
    }
    status.textContent = `이 페이지 ${cards.length}개 기록 중 ${shown}개 표시. 다른 지역은 아래 페이지/지역 링크에서 확인하세요.`;
  });
})();
