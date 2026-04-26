/**
 * Stock Radar — Search Module
 *
 * MVP 階段：
 * - 從 watchlist.json 載入清單
 * - 純前端 client-side filter（股號 prefix / 公司名 contains）
 * - Enter / 點選後跳轉到 stock.html?id=...
 *
 * Phase 4 階段（未實作）：
 * - 整合全市場股票清單（FinMind 一次性下載 stock_info）
 * - 不在 watchlist 也能搜尋
 */

(function () {
  const input = document.getElementById('search-input');
  const results = document.getElementById('search-results');
  if (!input || !results) return;

  let watchlist = [];
  let highlightedIdx = -1;

  // 初始載入 watchlist
  fetch(window.StockRadar.BASE_PATH + 'data/watchlist.json', { cache: 'no-cache' })
    .then(r => r.json())
    .then(data => { watchlist = data.stocks || []; })
    .catch(err => console.error('Search: failed to load watchlist', err));

  function search(q) {
    q = q.trim();
    if (!q) return [];
    const lower = q.toLowerCase();

    return watchlist.filter(s =>
      s.id.startsWith(q) ||
      s.name.toLowerCase().includes(lower) ||
      (s.industry || '').toLowerCase().includes(lower)
    ).slice(0, 8);
  }

  function render(items) {
    if (items.length === 0) {
      // 如果輸入是 4 位數字，顯示「直接前往」選項
      const q = input.value.trim();
      if (/^\d{4,6}$/.test(q)) {
        results.innerHTML = `
          <div class="search-result-item highlighted" data-id="${q}">
            <span class="search-result-id">${q}</span>
            <span class="search-result-name" style="color: var(--text-tertiary); font-style: italic;">不在 Watchlist · 即時查詢</span>
            <span class="search-result-market">→</span>
          </div>
        `;
        highlightedIdx = 0;
        results.classList.add('active');
        return;
      }
      results.classList.remove('active');
      return;
    }

    results.innerHTML = items.map((s, i) => `
      <div class="search-result-item${i === 0 ? ' highlighted' : ''}" data-id="${s.id}">
        <span class="search-result-id">${s.id}</span>
        <span class="search-result-name">${escapeHtml(s.name)}</span>
        <span class="search-result-market">${escapeHtml(s.market)}</span>
      </div>
    `).join('');
    highlightedIdx = 0;
    results.classList.add('active');

    results.querySelectorAll('.search-result-item').forEach(el => {
      el.addEventListener('click', () => goTo(el.dataset.id));
    });
  }

  function goTo(id) {
    if (!id) return;
    window.location.href = window.StockRadar.BASE_PATH + 'stock.html?id=' + encodeURIComponent(id);
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // 防抖
  let timer;
  input.addEventListener('input', (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => render(search(e.target.value)), 100);
  });

  input.addEventListener('focus', () => {
    if (input.value.trim()) render(search(input.value));
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-wrap')) {
      results.classList.remove('active');
    }
  });

  // 鍵盤導航
  input.addEventListener('keydown', (e) => {
    const items = results.querySelectorAll('.search-result-item');
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      highlightedIdx = Math.min(highlightedIdx + 1, items.length - 1);
      updateHighlight(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      highlightedIdx = Math.max(highlightedIdx - 1, 0);
      updateHighlight(items);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (highlightedIdx >= 0 && items[highlightedIdx]) {
        goTo(items[highlightedIdx].dataset.id);
      } else if (/^\d{4,6}$/.test(input.value.trim())) {
        goTo(input.value.trim());
      }
    } else if (e.key === 'Escape') {
      results.classList.remove('active');
      input.blur();
    }
  });

  function updateHighlight(items) {
    items.forEach((el, i) => {
      el.classList.toggle('highlighted', i === highlightedIdx);
    });
    if (items[highlightedIdx]) {
      items[highlightedIdx].scrollIntoView({ block: 'nearest' });
    }
  }
})();
