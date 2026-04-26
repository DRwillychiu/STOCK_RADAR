"""
MOPS (公開資訊觀測站) 爬蟲
============================
抓取重大訊息、月營收、法說會公告。
MOPS 不提供 JSON API，需要 POST form data 取得 HTML / 內嵌 JSON。

注意：MOPS 偶爾會擋密集請求，建議呼叫間 sleep 1 秒。

使用：
    from fetch_mops import MopsClient
    m = MopsClient()
    revenue = m.month_revenue("2330", year=2026)
    news = m.material_news("2330", days=30)
"""

import time
import json
import datetime as dt
from typing import Optional
from urllib import request, parse, error

UA = "Mozilla/5.0 (compatible; stock-radar/0.1; +personal-research)"


class MopsError(Exception):
    pass


class MopsClient:
    """
    MOPS 主要 endpoints（非官方文件，從觀察 form 取得）：
    - 月營收：https://mops.twse.com.tw/mops/web/ajax_t05st10_ifrs
    - 重大訊息：https://mops.twse.com.tw/mops/web/ajax_t05sr01_1
    - 法說會：https://mops.twse.com.tw/mops/web/ajax_t100sb02_1

    注意：MOPS 改版頻繁，本模組僅作骨架。實作時建議搭配 web_fetch 取得最新 endpoint。
    """

    def __init__(self, timeout: int = 30, sleep_between: float = 1.0):
        self.timeout = timeout
        self.sleep_between = sleep_between
        self._last_call = 0.0

    def _post(self, url: str, data: dict) -> str:
        """POST form data，回傳純文字（HTML 或 JSON 字串）"""
        # 簡易 throttle
        elapsed = time.time() - self._last_call
        if elapsed < self.sleep_between:
            time.sleep(self.sleep_between - elapsed)

        body = parse.urlencode(data).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers={
                "User-Agent": UA,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "*/*",
            },
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                self._last_call = time.time()
                return resp.read().decode("utf-8", errors="replace")
        except error.HTTPError as e:
            raise MopsError(f"HTTP {e.code}: {url}")
        except error.URLError as e:
            raise MopsError(f"Network: {e.reason}")

    # ---------- 注意：以下方法為骨架，實際使用建議結合 web_fetch ----------

    def month_revenue_url(self, stock_id: str, year: int) -> str:
        """
        月營收頁面 URL（給 Claude 用 web_fetch 抓取）
        年份是民國年（西元 - 1911）
        """
        roc_year = year - 1911
        return (
            "https://mops.twse.com.tw/mops/web/t05st10_ifrs?"
            f"step=0&firstin=1&off=1&keyword4=&code1=&TYPEK2=&checkbtn=&"
            f"queryName=co_id&inpuType=co_id&TYPEK=all&isnew=false&"
            f"co_id={stock_id}&year={roc_year}&season="
        )

    def material_news_url(self, stock_id: str) -> str:
        """重大訊息頁面 URL"""
        return (
            "https://mops.twse.com.tw/mops/web/t05sr01_1?"
            f"step=0&firstin=true&off=1&keyword4=&code1=&TYPEK2=&checkbtn=&"
            f"queryName=co_id&inpuType=co_id&TYPEK=all&"
            f"co_id={stock_id}"
        )

    def annual_report_url(self, stock_id: str, year: int) -> str:
        """年報下載頁面"""
        roc_year = year - 1911
        return (
            "https://doc.twse.com.tw/server-java/t57sb01?"
            f"step=1&colorchg=1&seamon=&mtype=F&"
            f"co_id={stock_id}&year={roc_year}"
        )

    def company_profile_url(self, stock_id: str, market: str = "sii") -> str:
        """
        公司基本資料頁面
        market: sii (上市) | otc (上櫃) | rotc (興櫃)
        """
        return (
            "https://mops.twse.com.tw/mops/web/ajax_t05st03?"
            f"encodeURIComponent=1&step=1&firstin=1&off=1&"
            f"queryName=co_id&inpuType=co_id&TYPEK={market}&isnew=false&"
            f"co_id={stock_id}"
        )

    # ---------- 給 SKILL 的 helper ----------

    def get_research_urls(self, stock_id: str) -> dict:
        """
        回傳一組可給 web_fetch 用的 URL，讓 Claude 自行抓取解析。
        因為 MOPS 改版頻繁，純爬蟲容易壞掉，改用這種較穩定的方式。
        """
        return {
            "monthly_revenue_current_year": self.month_revenue_url(stock_id, dt.date.today().year),
            "monthly_revenue_last_year": self.month_revenue_url(stock_id, dt.date.today().year - 1),
            "material_news": self.material_news_url(stock_id),
            "company_profile_sii": self.company_profile_url(stock_id, "sii"),
            "company_profile_otc": self.company_profile_url(stock_id, "otc"),
            "company_profile_rotc": self.company_profile_url(stock_id, "rotc"),
        }


if __name__ == "__main__":
    import sys
    stock_id = sys.argv[1] if len(sys.argv) > 1 else "2330"
    client = MopsClient()
    urls = client.get_research_urls(stock_id)
    print(json.dumps(urls, ensure_ascii=False, indent=2))
