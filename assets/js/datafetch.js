/**
 * Stock Radar — Client-side Data Fetcher
 *
 * 直接從瀏覽器打 FinMind API。已驗證 FinMind 支援 CORS。
 *
 * 設計原則：
 * - 永不阻塞 UI：所有 fetch 都是 async，失敗時回傳 null（不 throw）
 * - 透明：每個回傳都帶 _meta { source, fetchedAt }
 * - Cache：同一 session 內，相同股票 60 秒內不重複打 API
 *
 * FinMind 免費版限制：60 次/小時（無 token），有 token 600 次/小時
 * 我們不在前端塞 token（會洩漏），所以仰賴免費額度。
 */

(function () {
  'use strict';

  const FINMIND_BASE = 'https://api.finmindtrade.com/api/v4/data';
  const CACHE_TTL_MS = 60 * 1000; // 60 秒

  const cache = new Map();

  function cacheKey(dataset, stockId, params) {
    return `${dataset}:${stockId}:${JSON.stringify(params || {})}`;
  }

  function getCached(key) {
    const entry = cache.get(key);
    if (!entry) return null;
    if (Date.now() - entry.ts > CACHE_TTL_MS) {
      cache.delete(key);
      return null;
    }
    return entry.value;
  }

  function setCached(key, value) {
    cache.set(key, { value, ts: Date.now() });
  }

  /**
   * 通用 FinMind 查詢
   */
  async function finmindQuery(dataset, stockId, params = {}) {
    const key = cacheKey(dataset, stockId, params);
    const cached = getCached(key);
    if (cached) return cached;

    const url = new URL(FINMIND_BASE);
    url.searchParams.set('dataset', dataset);
    url.searchParams.set('data_id', stockId);
    Object.entries(params).forEach(([k, v]) => {
      if (v != null) url.searchParams.set(k, v);
    });

    try {
      const res = await fetch(url.toString());
      if (!res.ok) {
        return { ok: false, error: `HTTP ${res.status}`, _meta: meta('FinMind', null) };
      }
      const json = await res.json();
      if (json.status !== 200) {
        return { ok: false, error: json.msg || 'API error', _meta: meta('FinMind', null) };
      }
      const result = {
        ok: true,
        data: json.data || [],
        _meta: meta('FinMind', new Date()),
      };
      setCached(key, result);
      return result;
    } catch (err) {
      return { ok: false, error: err.message, _meta: meta('FinMind', null) };
    }
  }

  function meta(source, fetchedAt) {
    return {
      source,
      fetchedAt: fetchedAt ? fetchedAt.toISOString() : null,
      fetchedAtDisplay: fetchedAt ? formatTime(fetchedAt) : '—',
    };
  }

  function formatTime(d) {
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  /**
   * 抓最新一筆股價（找近 10 天）
   */
  async function fetchLatestPrice(stockId) {
    const today = new Date();
    const start = new Date(today.getTime() - 10 * 86400_000);
    const startStr = start.toISOString().slice(0, 10);

    const result = await finmindQuery('TaiwanStockPrice', stockId, { start_date: startStr });
    if (!result.ok || result.data.length === 0) {
      return { ok: false, error: result.error || 'no data', _meta: result._meta };
    }

    // 取最後一筆（最新交易日）
    const latest = result.data[result.data.length - 1];
    const prev = result.data.length >= 2 ? result.data[result.data.length - 2] : null;

    const close = latest.close;
    const previousClose = prev ? prev.close : (close - (latest.spread || 0));
    const change = latest.spread !== undefined ? latest.spread : (close - previousClose);
    const changePercent = previousClose ? (change / previousClose) * 100 : null;

    return {
      ok: true,
      tradeDate: latest.date,
      price: {
        current: close,
        change: change,
        changePercent: changePercent,
        previousClose: previousClose,
        open: latest.open,
        high: latest.max,
        low: latest.min,
        volume: latest.Trading_Volume,
      },
      _meta: result._meta,
    };
  }

  /**
   * 抓基本資料（公司名稱、產業、市場別）
   */
  async function fetchStockInfo(stockId) {
    const result = await finmindQuery('TaiwanStockInfo', stockId);
    if (!result.ok || result.data.length === 0) {
      return { ok: false, error: result.error || 'no data', _meta: result._meta };
    }

    const info = result.data[0];

    // type 對照：twse=上市, otc=上櫃, emerging=興櫃
    const marketMap = {
      twse: '上市',
      otc: '上櫃',
      emerging: '興櫃',
    };

    return {
      ok: true,
      name: info.stock_name,
      industry: info.industry_category,
      market: marketMap[info.type] || info.type,
      _meta: result._meta,
    };
  }

  /**
   * 抓最近 N 個月的月營收
   */
  async function fetchMonthlyRevenue(stockId, months = 12) {
    const today = new Date();
    const start = new Date(today.getTime() - months * 31 * 86400_000);
    const startStr = start.toISOString().slice(0, 10);

    const result = await finmindQuery('TaiwanStockMonthRevenue', stockId, { start_date: startStr });
    if (!result.ok || result.data.length === 0) {
      return { ok: false, error: result.error || 'no data', _meta: result._meta };
    }

    return {
      ok: true,
      revenues: result.data,
      _meta: result._meta,
    };
  }

  // ---------- Expose ----------
  window.StockRadarFetch = {
    fetchLatestPrice,
    fetchStockInfo,
    fetchMonthlyRevenue,
    // for debugging
    _cache: cache,
  };
})();
