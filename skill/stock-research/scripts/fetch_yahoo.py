"""
Yahoo Finance Wrapper (非官方 API)
====================================
用於即時報價、市值、簡單基本面交叉驗證。
注意：非正式 API，可能變更，僅作副源使用。

使用：
    from fetch_yahoo import YahooClient
    y = YahooClient()
    quote = y.quote("2330")     # 上市
    quote = y.quote("3711.TW")
    quote = y.quote("3595.TWO") # 上櫃/興櫃
"""

import json
import datetime as dt
from typing import Optional, Any
from urllib import request, parse, error

CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
QUOTE_BASE = "https://query1.finance.yahoo.com/v7/finance/quote"


class YahooError(Exception):
    pass


class YahooClient:
    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; stock-radar/0.1)",
            "Accept": "application/json",
        }

    def _normalize_symbol(self, stock_id: str) -> list[str]:
        """
        台股後綴對照：
        - 上市：.TW
        - 上櫃 / 興櫃：.TWO
        因為單一輸入不知道屬性，回傳兩個候選讓呼叫端輪詢。
        """
        if "." in stock_id:
            return [stock_id]
        return [f"{stock_id}.TW", f"{stock_id}.TWO"]

    def _get(self, url: str) -> dict:
        try:
            req = request.Request(url, headers=self.headers)
            with request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as e:
            raise YahooError(f"HTTP {e.code}")
        except error.URLError as e:
            raise YahooError(f"Network: {e.reason}")
        except json.JSONDecodeError:
            raise YahooError("Invalid JSON")

    def chart(self, stock_id: str, range_: str = "5d", interval: str = "1d") -> Optional[dict]:
        """K 線資料 + meta（含當日報價）"""
        for sym in self._normalize_symbol(stock_id):
            url = f"{CHART_BASE}/{sym}?range={range_}&interval={interval}"
            try:
                data = self._get(url)
            except YahooError:
                continue
            chart = data.get("chart", {})
            results = chart.get("result")
            if results:
                return results[0]
        return None

    def quote(self, stock_id: str) -> Optional[dict]:
        """
        標準化報價輸出。
        Returns: {symbol, current, change, changePercent, open, high, low,
                  previousClose, volume, marketCap, currency, exchangeName}
        """
        chart_data = self.chart(stock_id, range_="5d", interval="1d")
        if not chart_data:
            return None

        meta = chart_data.get("meta", {})
        current = meta.get("regularMarketPrice")
        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")

        change = None
        change_pct = None
        if current is not None and prev_close:
            change = round(current - prev_close, 4)
            change_pct = round((change / prev_close) * 100, 4)

        return {
            "symbol": meta.get("symbol"),
            "current": current,
            "previousClose": prev_close,
            "open": meta.get("regularMarketDayHigh") and meta.get("regularMarketDayLow")
                    and self._extract_open(chart_data),
            "high": meta.get("regularMarketDayHigh"),
            "low": meta.get("regularMarketDayLow"),
            "volume": meta.get("regularMarketVolume"),
            "change": change,
            "changePercent": change_pct,
            "currency": meta.get("currency"),
            "exchangeName": meta.get("exchangeName"),
            "_fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
        }

    def _extract_open(self, chart_data: dict) -> Optional[float]:
        try:
            quotes = chart_data["indicators"]["quote"][0]
            opens = quotes.get("open", [])
            for o in reversed(opens):
                if o is not None:
                    return o
        except (KeyError, IndexError):
            pass
        return None


if __name__ == "__main__":
    import sys
    stock_id = sys.argv[1] if len(sys.argv) > 1 else "2330"
    client = YahooClient()
    result = client.quote(stock_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
