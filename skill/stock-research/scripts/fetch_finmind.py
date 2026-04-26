"""
FinMind API Wrapper
====================
FinMind 是台股最完整的開源 API。免費版 600 次/小時。
文件：https://finmindtrade.com/analysis/#/data/api

使用：
    from fetch_finmind import FinMindClient
    client = FinMindClient(token=os.getenv("FINMIND_TOKEN"))
    info = client.stock_info("2330")
    revenue = client.month_revenue("2330", start_date="2024-01-01")
"""

import os
import time
import json
import datetime as dt
from typing import Optional, Any
from urllib import request, parse, error

BASE = "https://api.finmindtrade.com/api/v4/data"


class FinMindError(Exception):
    """FinMind API 錯誤"""
    pass


class FinMindClient:
    """FinMind API 客戶端 — 不依賴 requests，純標準庫"""

    def __init__(self, token: Optional[str] = None, timeout: int = 30):
        self.token = token or os.getenv("FINMIND_TOKEN", "")
        self.timeout = timeout
        self._cache: dict[str, Any] = {}

    def _get(self, dataset: str, **params) -> list[dict]:
        """通用 GET 請求"""
        params["dataset"] = dataset
        if self.token:
            params["token"] = self.token

        # 過濾 None 參數
        params = {k: v for k, v in params.items() if v is not None}
        url = f"{BASE}?{parse.urlencode(params)}"

        cache_key = url
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            req = request.Request(url, headers={"User-Agent": "stock-radar/0.1"})
            with request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as e:
            raise FinMindError(f"HTTP {e.code} on {dataset}: {e.read().decode('utf-8', 'ignore')[:200]}")
        except error.URLError as e:
            raise FinMindError(f"Network error on {dataset}: {e.reason}")
        except json.JSONDecodeError:
            raise FinMindError(f"Invalid JSON response from {dataset}")

        if payload.get("status") != 200:
            raise FinMindError(f"{dataset}: {payload.get('msg', 'unknown error')}")

        data = payload.get("data", [])
        self._cache[cache_key] = data
        return data

    # ---------- 公開方法 ----------

    def stock_info(self, stock_id: str) -> Optional[dict]:
        """基本資料：公司全名、產業、市場別"""
        try:
            rows = self._get("TaiwanStockInfo", data_id=stock_id)
            return rows[0] if rows else None
        except FinMindError:
            return None

    def stock_price(self, stock_id: str, start_date: str, end_date: Optional[str] = None) -> list[dict]:
        """股價（日線）"""
        try:
            return self._get(
                "TaiwanStockPrice",
                data_id=stock_id,
                start_date=start_date,
                end_date=end_date or dt.date.today().isoformat()
            )
        except FinMindError:
            return []

    def latest_price(self, stock_id: str) -> Optional[dict]:
        """最新一筆股價（用近 10 天範圍找最後一筆）"""
        start = (dt.date.today() - dt.timedelta(days=10)).isoformat()
        rows = self.stock_price(stock_id, start)
        return rows[-1] if rows else None

    def month_revenue(self, stock_id: str, start_date: str) -> list[dict]:
        """月營收"""
        try:
            return self._get(
                "TaiwanStockMonthRevenue",
                data_id=stock_id,
                start_date=start_date
            )
        except FinMindError:
            return []

    def financial_statements(self, stock_id: str, start_date: str) -> list[dict]:
        """季報（綜合損益表）"""
        try:
            return self._get(
                "TaiwanStockFinancialStatements",
                data_id=stock_id,
                start_date=start_date
            )
        except FinMindError:
            return []

    def institutional(self, stock_id: str, start_date: str) -> list[dict]:
        """法人買賣超"""
        try:
            return self._get(
                "TaiwanStockInstitutionalInvestorsBuySell",
                data_id=stock_id,
                start_date=start_date
            )
        except FinMindError:
            return []

    def news(self, stock_id: str, start_date: str) -> list[dict]:
        """公司相關新聞"""
        try:
            return self._get(
                "TaiwanStockNews",
                data_id=stock_id,
                start_date=start_date
            )
        except FinMindError:
            return []

    # ---------- 整合查詢 ----------

    def fetch_all(self, stock_id: str, lookback_months: int = 12) -> dict:
        """一次抓齊一檔股票的所有資料"""
        start = (dt.date.today() - dt.timedelta(days=lookback_months * 31)).isoformat()
        return {
            "info": self.stock_info(stock_id),
            "latest_price": self.latest_price(stock_id),
            "month_revenue": self.month_revenue(stock_id, start),
            "financials": self.financial_statements(stock_id, start),
            "institutional": self.institutional(
                stock_id,
                (dt.date.today() - dt.timedelta(days=30)).isoformat()
            ),
            "news": self.news(
                stock_id,
                (dt.date.today() - dt.timedelta(days=14)).isoformat()
            ),
            "_fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
        }


if __name__ == "__main__":
    import sys
    stock_id = sys.argv[1] if len(sys.argv) > 1 else "2330"
    client = FinMindClient()
    if not client.token:
        print("⚠️  FINMIND_TOKEN 未設定，部分資料可能無法取得", file=sys.stderr)
    result = client.fetch_all(stock_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
