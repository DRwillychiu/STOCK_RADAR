/**
 * Stock Radar — Main Application Logic
 *
 * 職責：
 * 1. 偵測當前頁面（首頁 / 個股頁）
 * 2. 載入對應資料並渲染
 * 3. 提供共用 utility（格式化、模板）
 *
 * 設計原則：
 * - 純 vanilla JS，不依賴框架
 * - 路徑參考 base path 自動處理（GitHub Pages /repo-name/ 子路徑）
 * - 所有 fetch 都有錯誤處理與降級
 */

// ---------- Base Path Detection ----------
// GitHub Pages 部署在 /repo-name/ 子路徑，需要動態決定 base path
const BASE_PATH = (() => {
  const path = window.location.pathname;
  // 如果路徑以 /repo-name/ 開頭，取第一段；否則為根
  const segments = path.split('/').filter(Boolean);
  if (segments.length > 0 && !segments[0].endsWith('.html')) {
    return '/' + segments[0] + '/';
  }
  return '/';
})();

// ---------- Number Formatters ----------
const fmt = {
  price(n) {
    if (n == null) return '—';
    return Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  },
  change(n) {
    if (n == null) return '—';
    const sign = n > 0 ? '+' : '';
    return sign + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  },
  percent(n) {
    if (n == null) return '—';
    const sign = n > 0 ? '+' : '';
    return sign + Number(n).toFixed(2) + '%';
  },
  volume(n) {
    if (n == null) return '—';
    if (n >= 100000000) return (n / 100000000).toFixed(2) + ' 億';
    if (n >= 10000) return (n / 10000).toFixed(1) + ' 萬';
    return n.toLocaleString();
  },
  marketCap(n) {
    if (n == null) return '—';
    if (n >= 1000000000000) return (n / 1000000000000).toFixed(2) + ' 兆';
    if (n >= 100000000) return (n / 100000000).toFixed(0) + ' 億';
    return (n / 10000).toFixed(0) + ' 萬';
  },
  date(iso) {
    if (!iso) return '—';
    return iso.slice(0, 10);
  },
  datetime(iso) {
    if (!iso) return '—';
    return iso.replace('T', ' ').slice(0, 16);
  }
};

const changeClass = (n) => n > 0 ? 'up' : n < 0 ? 'down' : 'neutral';

// ---------- Data Loaders ----------
async function loadJSON(path) {
  try {
    const url = BASE_PATH + path.replace(/^\//, '');
    const res = await fetch(url, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('Failed to load', path, err);
    return null;
  }
}

async function loadText(path) {
  try {
    const url = BASE_PATH + path.replace(/^\//, '');
    const res = await fetch(url, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.text();
  } catch (err) {
    console.error('Failed to load', path, err);
    return null;
  }
}

// ---------- Markdown to HTML (minimal) ----------
function md2html(md) {
  if (!md) return '';
  let html = md;
  // Code blocks first (避免被其他規則破壞)
  html = html.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${escapeHtml(code.trim())}</code></pre>`);
  // Inline code
  html = html.replace(/`([^`]+)`/g, (_, code) => `<code>${escapeHtml(code)}</code>`);
  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  // Blockquote
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
  // Horizontal rule
  html = html.replace(/^---+$/gm, '<hr>');
  // Lists
  html = html.replace(/^(\s*)- \[ \] (.+)$/gm, '$1<li><input type="checkbox" disabled> $2</li>');
  html = html.replace(/^(\s*)- \[x\] (.+)$/gim, '$1<li><input type="checkbox" disabled checked> $2</li>');
  html = html.replace(/^(\s*)- (.+)$/gm, '$1<li>$2</li>');
  // Wrap lists
  html = html.replace(/(<li>[\s\S]*?<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
  // Bold / italic
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/_([^_\n]+)_/g, '<em>$1</em>');
  // Paragraphs (剩餘的非 tag 行)
  html = html.split(/\n\n+/).map(block => {
    if (block.trim().startsWith('<') || !block.trim()) return block;
    return `<p>${block.replace(/\n/g, '<br>')}</p>`;
  }).join('\n');
  return html;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ---------- Page Routing ----------
document.addEventListener('DOMContentLoaded', () => {
  const page = document.body.dataset.page;
  if (page === 'home') initHome();
  else if (page === 'stock') initStock();
});

// ---------- Home Page ----------
async function initHome() {
  const watchlist = await loadJSON('data/watchlist.json');
  if (!watchlist) {
    document.getElementById('watchlist-grid').innerHTML = '<div class="empty">資料載入失敗</div>';
    return;
  }

  // 載入每檔的詳細資料
  const stocks = await Promise.all(
    watchlist.stocks.map(s => loadJSON(`data/stocks/${s.id}.json`))
  );

  const grid = document.getElementById('watchlist-grid');
  grid.innerHTML = '';

  watchlist.stocks.forEach((meta, i) => {
    const data = stocks[i];
    if (!data) return;
    grid.appendChild(buildWatchCard(meta, data, i));
  });

  // 更新 hero 統計
  document.getElementById('stat-watchlist-count').textContent = watchlist.stocks.length;
  document.getElementById('stat-last-updated').textContent = fmt.datetime(watchlist.lastUpdated);

  // 即時更新所有卡片的價格（async，不阻塞）
  enrichWatchlistPrices(watchlist.stocks);
}

async function enrichWatchlistPrices(stocks) {
  if (!window.StockRadarFetch) return;

  for (const s of stocks) {
    try {
      const fresh = await window.StockRadarFetch.fetchLatestPrice(s.id);
      if (!fresh.ok) continue;

      const card = document.querySelector(`a[href*="id=${s.id}"]`);
      if (!card) continue;

      // 更新價格
      const priceEl = card.querySelector('.watch-card-price-num');
      const changeEl = card.querySelector('.watch-card-change');
      if (priceEl) priceEl.textContent = fmt.price(fresh.price.current);
      if (changeEl) {
        const cls = changeClass(fresh.price.change);
        changeEl.className = `watch-card-change ${cls}`;
        changeEl.textContent = `${fmt.change(fresh.price.change)} · ${fmt.percent(fresh.price.changePercent)}`;
      }

      // 加上即時標記（如果還沒有）
      if (!card.querySelector('.live-badge')) {
        const badge = document.createElement('div');
        badge.className = 'live-badge';
        badge.innerHTML = `<span class="live-dot"></span> ${fresh.tradeDate} · FinMind`;
        card.appendChild(badge);
      }
    } catch (err) {
      console.warn(`Failed to enrich ${s.id}:`, err);
    }
  }
}

function buildWatchCard(meta, data, idx) {
  const card = document.createElement('a');
  card.href = `${BASE_PATH}stock.html?id=${meta.id}`;
  card.className = `watch-card fade-up fade-up-${Math.min(idx + 1, 6)}`;
  card.style.textDecoration = 'none';

  const cls = changeClass(data.price.change);
  const tags = (meta.tags || []).map(t => {
    const isWarning = ['妖股', '高風險', '處置股'].some(w => t.includes(w));
    return `<span class="tag${isWarning ? ' warning' : ''}">${escapeHtml(t)}</span>`;
  }).join('');

  card.innerHTML = `
    <div class="watch-card-head">
      <span class="watch-card-id">${meta.id}</span>
      <span class="watch-card-market">${meta.market}</span>
    </div>
    <div class="watch-card-name">${escapeHtml(meta.name)}</div>
    <div class="watch-card-industry">${escapeHtml(meta.industry)}</div>
    <div class="watch-card-price">
      <span class="watch-card-price-num">${fmt.price(data.price.current)}</span>
      <span class="watch-card-change ${cls}">
        ${fmt.change(data.price.change)} · ${fmt.percent(data.price.changePercent)}
      </span>
    </div>
    <div class="watch-card-tags">${tags}</div>
  `;
  return card;
}

// ---------- Stock Detail Page ----------
async function initStock() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get('id');
  const main = document.getElementById('stock-main');

  if (!id) {
    main.innerHTML = '<div class="empty">未指定股票代號</div>';
    return;
  }

  const data = await loadJSON(`data/stocks/${id}.json`);

  if (!data) {
    // 不在 Watchlist 中 — 顯示快速版佔位（Phase 4 會接 FinMind 即時抓）
    renderQuickFallback(id, main);
    return;
  }

  const noteMd = await loadText(`notes/${id}.md`);
  renderStockDetail(data, noteMd, main);

  // 即時抓最新價格覆蓋顯示（async，不阻塞首次渲染）
  enrichStockDetailPrice(id, data);
}

async function enrichStockDetailPrice(stockId, baseData) {
  if (!window.StockRadarFetch) return;

  // 顯示「正在抓取即時資料」訊號
  const banner = document.createElement('div');
  banner.className = 'live-banner loading';
  banner.innerHTML = `<span class="live-dot"></span> 正在抓取即時報價 · FinMind...`;

  const header = document.querySelector('.detail-header');
  if (header) header.insertBefore(banner, header.firstChild);

  try {
    const fresh = await window.StockRadarFetch.fetchLatestPrice(stockId);

    if (!fresh.ok) {
      banner.className = 'live-banner error';
      banner.innerHTML = `⚠️ 即時資料抓取失敗：${escapeHtml(fresh.error || 'unknown')} · 顯示資料為本地快取（${fmt.datetime(baseData.lastUpdated)}）`;
      return;
    }

    // 更新 DOM 中的價格
    const main = document.querySelector('.price-main');
    const change = document.querySelector('.price-change');
    const detail = document.querySelector('.price-detail');

    const cls = changeClass(fresh.price.change);
    if (main) {
      main.className = `price-main ${cls}`;
      main.textContent = fmt.price(fresh.price.current);
    }
    if (change) {
      change.className = `price-change ${cls}`;
      change.textContent = `${fmt.change(fresh.price.change)} · ${fmt.percent(fresh.price.changePercent)}`;
    }
    if (detail) {
      detail.innerHTML = `
        <span>開 <strong>${fmt.price(fresh.price.open)}</strong></span>
        <span>高 <strong>${fmt.price(fresh.price.high)}</strong></span>
        <span>低 <strong>${fmt.price(fresh.price.low)}</strong></span>
        <span>量 <strong>${fmt.volume(fresh.price.volume)}</strong></span>
      `;
    }

    // 替換 banner 為成功訊號
    banner.className = 'live-banner success';
    banner.innerHTML = `
      <span class="live-dot active"></span>
      <span class="live-banner-text">
        即時報價已更新 · 交易日 <strong>${fresh.tradeDate}</strong> ·
        資料來源：<strong>FinMind</strong> · 抓取時間：<strong>${fresh._meta.fetchedAtDisplay}</strong>
      </span>
    `;

    // 同時在頁尾加上完整的資料品質報告
    appendDataQualityFooter(baseData, fresh);

  } catch (err) {
    banner.className = 'live-banner error';
    banner.innerHTML = `⚠️ 即時資料抓取失敗：${escapeHtml(err.message)}`;
  }
}

function appendDataQualityFooter(baseData, fresh) {
  const main = document.getElementById('stock-main');
  if (!main) return;

  // 移除舊的（如果有）
  const old = main.querySelector('.data-quality-footer');
  if (old) old.remove();

  const isMockSoft = baseData.dataQuality === 'mock' || baseData.dataQuality === 'partial';

  const footer = document.createElement('section');
  footer.className = 'data-quality-footer';
  footer.innerHTML = `
    <div class="dq-header">
      <span class="dq-title">資料品質報告 · DATA QUALITY</span>
    </div>
    <div class="dq-grid">
      <div class="dq-row">
        <span class="dq-light green"></span>
        <span class="dq-field">即時報價</span>
        <span class="dq-detail">FinMind · ${fresh.tradeDate} · 抓取於 ${fresh._meta.fetchedAtDisplay}</span>
      </div>
      <div class="dq-row">
        <span class="dq-light ${isMockSoft ? 'yellow' : 'green'}"></span>
        <span class="dq-field">產業分析、轉型、客戶、法說</span>
        <span class="dq-detail">${isMockSoft ? '⚠️ 目前為人工撰寫的範例資料，需用 stock-research SKILL 更新真實洞察' : '由 stock-research SKILL 產出'}</span>
      </div>
      <div class="dq-row">
        <span class="dq-light yellow"></span>
        <span class="dq-field">月營收、財務數字</span>
        <span class="dq-detail">本地快取 · 上次更新 ${fmt.datetime(baseData.lastUpdated)} · Phase 3 GitHub Actions 啟用後每日更新</span>
      </div>
      <div class="dq-row">
        <span class="dq-light green"></span>
        <span class="dq-field">本地基本資料</span>
        <span class="dq-detail">手動維護於 data/stocks/${baseData.id}.json</span>
      </div>
    </div>
  `;

  main.appendChild(footer);
}

function renderQuickFallback(id, main) {
  document.title = `${id} · Stock Radar`;
  main.innerHTML = `
    <div class="snapshot-banner">
      <div class="snapshot-banner-text">
        <strong>${escapeHtml(id)}</strong> 不在你的 Watchlist 中
        <small>Phase 4 完成後將自動透過 FinMind API 即時抓取基本資料。目前先用以下方式深入研究：</small>
      </div>
    </div>
    <div class="summary-card">
      <div class="summary-text">
        <strong>建議流程：</strong>在 Claude 對話框輸入「研究 ${escapeHtml(id)}」，stock-research SKILL 會自動產出完整研究報告，commit 到 repo 後此頁面會自動載入。
      </div>
    </div>
  `;
}

function renderStockDetail(d, noteMd, main) {
  document.title = `${d.name} ${d.id} · Stock Radar`;

  const cls = changeClass(d.price.change);
  const isWarn = d.warnings && d.warnings.length > 0;

  // 計算營收結構最大值用於 bar
  const revenueData = d.revenueStructure?.byProduct || [];
  const maxPct = Math.max(...revenueData.map(r => r.percentage), 1);

  // 季度趨勢最大值
  const trends = d.revenueStructure?.quarterlyTrend || [];
  const maxRev = Math.max(...trends.map(t => t.revenue), 1);

  main.innerHTML = `
    <header class="detail-header fade-up">
      <div class="detail-meta">
        <span>${escapeHtml(d.market)}</span>
        <span class="detail-meta-divider">·</span>
        <span>${escapeHtml(d.industry)}</span>
        <span class="detail-meta-divider">·</span>
        <span>${escapeHtml(d.subIndustry || '')}</span>
        <span class="detail-meta-divider">·</span>
        <span>更新：${fmt.datetime(d.lastUpdated)}</span>
      </div>
      <h1 class="detail-title">
        <span>${escapeHtml(d.name)}</span>
        <span class="detail-title-id">${escapeHtml(d.id)}</span>
      </h1>
      <p class="detail-oneliner">${escapeHtml(d.oneLineDef)}</p>
      <div class="price-row">
        <span class="price-main ${cls}">${fmt.price(d.price.current)}</span>
        <span class="price-change ${cls}">
          ${fmt.change(d.price.change)} · ${fmt.percent(d.price.changePercent)}
        </span>
        <div class="price-detail">
          <span>開 <strong>${fmt.price(d.price.open)}</strong></span>
          <span>高 <strong>${fmt.price(d.price.high)}</strong></span>
          <span>低 <strong>${fmt.price(d.price.low)}</strong></span>
          <span>量 <strong>${fmt.volume(d.price.volume)}</strong></span>
          <span>市值 <strong>${fmt.marketCap(d.price.marketCap)}</strong></span>
        </div>
      </div>
    </header>

    <div class="summary-card fade-up fade-up-1">
      <p class="summary-text">${escapeHtml(d.executiveSummary)}</p>
    </div>

    ${isWarn ? `
      <div class="warning-box fade-up fade-up-2">
        <div class="warning-box-title">Risk Notes · 風險提示</div>
        <ul class="warning-list">
          ${d.warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}
        </ul>
      </div>
    ` : ''}

    <section class="section fade-up fade-up-2">
      <div class="section-header">
        <div class="section-title">
          <span class="section-title-num">01</span>
          <span class="section-title-text">營收結構</span>
        </div>
        <span class="section-meta">REVENUE BREAKDOWN</span>
      </div>
      <div class="two-col">
        <div>
          <h4>產品別占比</h4>
          <div class="bar-list">
            ${revenueData.map(r => `
              <div class="bar-item">
                <div class="bar-label-row">
                  <span class="label">${escapeHtml(r.name)}</span>
                  <span class="value">${r.percentage.toFixed(1)}%</span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill" style="width: ${(r.percentage / maxPct * 100).toFixed(1)}%"></div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
        <div>
          <h4>近 4 季營收趨勢</h4>
          <div class="trend-chart">
            ${trends.map(t => `
              <div class="trend-bar-wrap">
                <div class="trend-bar" style="height: ${(t.revenue / maxRev * 85).toFixed(1)}%">
                  <span class="trend-bar-value">${t.revenue.toLocaleString()}</span>
                </div>
                <span class="trend-bar-label">${escapeHtml(t.quarter)}</span>
              </div>
            `).join('')}
          </div>
          <p style="font-size:0.75rem; color: var(--text-tertiary); margin-top: var(--space-4); font-family: var(--font-mono);">
            單位：百萬元
          </p>
        </div>
      </div>
    </section>

    <section class="section fade-up fade-up-3">
      <div class="section-header">
        <div class="section-title">
          <span class="section-title-num">02</span>
          <span class="section-title-text">主要客戶</span>
        </div>
        <span class="section-meta">KEY CUSTOMERS</span>
      </div>
      <div class="customer-list">
        ${(d.majorCustomers || []).map(c => `
          <div class="customer-row">
            <div>
              <div class="customer-name">${escapeHtml(c.name)}</div>
              <div class="customer-products">${escapeHtml(c.products || '')}</div>
            </div>
            <div class="customer-share">${escapeHtml(c.estimatedShare || '—')}</div>
          </div>
        `).join('')}
      </div>
    </section>

    <section class="section fade-up fade-up-3">
      <div class="section-header">
        <div class="section-title">
          <span class="section-title-num">03</span>
          <span class="section-title-text">近期法說會重點</span>
        </div>
        <span class="section-meta">EARNINGS CALL</span>
      </div>
      ${(d.earningsCallHighlights || []).map(e => `
        <div class="earnings-card">
          <div class="earnings-date">${escapeHtml(e.date)}</div>
          <div class="earnings-title">${escapeHtml(e.title)}</div>
          <ol class="earnings-points">
            ${(e.points || []).map(p => `<li>${escapeHtml(p)}</li>`).join('')}
          </ol>
        </div>
      `).join('')}
    </section>

    <section class="section fade-up fade-up-4">
      <div class="section-header">
        <div class="section-title">
          <span class="section-title-num">04</span>
          <span class="section-title-text">轉型與新業務</span>
        </div>
        <span class="section-meta">TRANSFORMATION</span>
      </div>
      <p style="font-family: var(--font-display); font-variation-settings: 'SOFT' 30; font-size: 1.1rem; line-height: 1.6; color: var(--text-primary); margin-bottom: var(--space-5);">
        ${escapeHtml(d.transformation?.summary || '')}
      </p>
      <ul style="list-style: none; display: flex; flex-direction: column; gap: var(--space-3);">
        ${(d.transformation?.keyInitiatives || []).map(k => `
          <li style="display: grid; grid-template-columns: 24px 1fr; gap: var(--space-3); padding: var(--space-3) 0; border-bottom: 1px dashed var(--ink-border);">
            <span style="color: var(--accent-gold); font-family: var(--font-mono);">→</span>
            <span style="font-family: var(--font-tc); color: var(--text-primary);">${escapeHtml(k)}</span>
          </li>
        `).join('')}
      </ul>
    </section>

    <section class="section fade-up fade-up-4">
      <div class="section-header">
        <div class="section-title">
          <span class="section-title-num">05</span>
          <span class="section-title-text">同業比較</span>
        </div>
        <span class="section-meta">PEER COMPARISON</span>
      </div>
      <table class="compare-table">
        <thead>
          <tr>
            <th>指標</th>
            <th>本公司</th>
            <th colspan="3">同業</th>
          </tr>
        </thead>
        <tbody>
          ${(d.peerComparison || []).map(p => `
            <tr>
              <td class="label-cell">${escapeHtml(p.metric)}</td>
              <td class="self-cell">${escapeHtml(p.self)}</td>
              ${(p.peers || []).map(peer => `
                <td class="peer-cell">${escapeHtml(peer.name)}: ${escapeHtml(peer.value)}</td>
              `).join('')}
            </tr>
          `).join('')}
        </tbody>
      </table>
    </section>

    <section class="section fade-up fade-up-5">
      <div class="section-header">
        <div class="section-title">
          <span class="section-title-num">06</span>
          <span class="section-title-text">近期新聞</span>
        </div>
        <span class="section-meta">RECENT NEWS</span>
      </div>
      <div class="news-list">
        ${(d.recentNews || []).map(n => `
          <div class="news-item">
            <div class="news-date">${escapeHtml(n.date)}</div>
            <div>
              <div class="news-title">${escapeHtml(n.title)}</div>
              <div class="news-summary">${escapeHtml(n.summary)}</div>
            </div>
          </div>
        `).join('')}
      </div>
    </section>

    <section class="section fade-up fade-up-5">
      <div class="section-header">
        <div class="section-title">
          <span class="section-title-num">07</span>
          <span class="section-title-text">個人筆記</span>
        </div>
        <span class="section-meta">PERSONAL NOTES</span>
      </div>
      <div class="notes-card">
        ${noteMd ? md2html(noteMd) : '<p style="color: var(--text-tertiary); font-style: italic;">尚未建立筆記。在 repo 的 <code>notes/' + escapeHtml(d.id) + '.md</code> 編輯後 commit & push 即可顯示。</p>'}
      </div>
    </section>

    <section class="section fade-up fade-up-6">
      <div class="section-header">
        <div class="section-title">
          <span class="section-title-num">08</span>
          <span class="section-title-text">資料來源驗證</span>
        </div>
        <span class="section-meta">DATA INTEGRITY</span>
      </div>
      <div class="verify-list">
        ${Object.entries(d.dataVerification || {}).map(([field, v]) => `
          <div class="verify-row">
            <span class="light ${v.status}"></span>
            <span class="verify-field">${escapeHtml(fieldLabel(field))}</span>
            <span class="verify-detail">
              ${(v.sources || []).join(' · ')}
              ${v.note ? ` — ${escapeHtml(v.note)}` : ''}
            </span>
          </div>
        `).join('')}
      </div>
    </section>
  `;
}

function fieldLabel(key) {
  const labels = {
    price: '收盤價',
    revenue: '月營收',
    industry: '產業分類'
  };
  return labels[key] || key;
}

// ---------- Expose for debugging ----------
window.StockRadar = { fmt, loadJSON, BASE_PATH };
