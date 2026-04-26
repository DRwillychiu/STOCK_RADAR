#!/usr/bin/env python3
"""
update_watchlist.py — Daily Hard Data Refresh
===============================================
讀取 data/watchlist.json 中所有股票，更新硬資料部分。

⚠️ 核心原則：絕對不覆蓋 Claude 寫的軟洞察欄位。

✅ 排程會更新的欄位（每天會變）：
- price.* (current, change, open, high, low, volume, marketCap, etc.)
- revenueStructure.quarterlyTrend (若有新季報資料)
- dataVerification.* (重新跑驗證)
- lastUpdated

❌ 排程「絕不」更新的欄位（需要 Claude 撰寫）：
- oneLineDef
- executiveSummary
- transformation
- majorCustomers
- peerComparison
- earningsCallHighlights
- recentNews
- warnings

使用：
    python scripts/update_watchlist.py
    python scripts/update_watchlist.py --dry-run     # 不寫入檔案
    python scripts/update_watchlist.py --skip-yahoo  # 只用 FinMind
"""

import os
import sys
import json
import argparse
import datetime as dt
from pathlib import Path
from typing import Optional

# 把 skill/stock-research/scripts 加入 path 以便 import
REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_SCRIPTS = REPO_ROOT / "skill" / "stock-research" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

try:
    from fetch_finmind import FinMindClient, FinMindError
    from fetch_yahoo import YahooClient
    from cross_verify import verify_price, verify_industry
except ImportError as e:
    print(f"❌ 無法 import fetcher 模組：{e}", file=sys.stderr)
    print(f"   確認 {SKILL_SCRIPTS} 存在", file=sys.stderr)
    sys.exit(1)


# ---------- 哪些欄位排程能改 ----------
# 用 deep merge 而非整個物件 replace，確保不會誤刪軟欄位
HARD_FIELDS_TOP_LEVEL = {"price", "lastUpdated", "dataVerification"}


def is_taiwan_business_day(today: Optional[dt.date] = None) -> bool:
    """
    粗略判斷是否台股交易日。
    僅判斷週末，不判斷國定假日（週末足以省掉大部分無效執行）。
    """
    today = today or dt.date.today()
    return today.weekday() < 5  # Mon-Fri


def load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ⚠️  讀取 {path.name} 失敗：{e}", file=sys.stderr)
        return None


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def fetch_hard_data(stock_id: str, finmind: FinMindClient, yahoo: Optional[YahooClient]) -> dict:
    """
    抓硬資料：價格 + 基本資料 + 季營收。
    回傳 dict 含 price / quarterlyTrend / verifications / errors。
    """
    result = {
        "price": None,
        "quarterly_trend": None,
        "verifications": {},
        "errors": [],
    }

    # ---- FinMind 基本資料 ----
    try:
        info = finmind.stock_info(stock_id)
    except FinMindError as e:
        info = None
        result["errors"].append(f"FinMind stock_info: {e}")

    # ---- FinMind 最新價 ----
    try:
        finmind_price = finmind.latest_price(stock_id)
    except FinMindError as e:
        finmind_price = None
        result["errors"].append(f"FinMind price: {e}")

    # ---- Yahoo 最新價 ----
    yahoo_quote = None
    if yahoo:
        try:
            yahoo_quote = yahoo.quote(stock_id)
        except Exception as e:
            result["errors"].append(f"Yahoo: {e}")

    # ---- 整合 price 區塊 ----
    if yahoo_quote and yahoo_quote.get("current") is not None:
        # Yahoo 有資料優先用，因為通常較即時
        result["price"] = {
            "current": yahoo_quote.get("current"),
            "change": yahoo_quote.get("change"),
            "changePercent": yahoo_quote.get("changePercent"),
            "previousClose": yahoo_quote.get("previousClose"),
            "open": yahoo_quote.get("open"),
            "high": yahoo_quote.get("high"),
            "low": yahoo_quote.get("low"),
            "volume": yahoo_quote.get("volume"),
            "marketCap": None,  # Yahoo chart endpoint 不提供，留空
        }
    elif finmind_price:
        result["price"] = {
            "current": finmind_price.get("close"),
            "change": finmind_price.get("spread"),
            "changePercent": None,  # FinMind 需自行算
            "previousClose": None,
            "open": finmind_price.get("open"),
            "high": finmind_price.get("max"),
            "low": finmind_price.get("min"),
            "volume": finmind_price.get("Trading_Volume"),
            "marketCap": None,
        }

    # ---- 季營收趨勢（從月營收聚合） ----
    try:
        start = (dt.date.today() - dt.timedelta(days=400)).isoformat()
        revenues = finmind.month_revenue(stock_id, start)
        if revenues:
            quarterly = aggregate_to_quarterly(revenues)
            result["quarterly_trend"] = quarterly[-4:]  # 最近 4 季
    except FinMindError as e:
        result["errors"].append(f"FinMind month_revenue: {e}")

    # ---- 多源驗證 ----
    fin_close = finmind_price.get("close") if finmind_price else None
    yh_close = yahoo_quote.get("current") if yahoo_quote else None
    result["verifications"]["price"] = verify_price(fin_close, yh_close)
    result["verifications"]["industry"] = verify_industry(
        info.get("industry_category") if info else None,
        None
    )

    return result


def aggregate_to_quarterly(monthly_revenues: list[dict]) -> list[dict]:
    """
    把月營收 (FinMind 格式 [{date, revenue, ...}]) 聚合成季資料。
    """
    quarterly: dict[str, int] = {}
    for row in monthly_revenues:
        date = row.get("date") or row.get("revenue_year_month", "")
        revenue = row.get("revenue", 0)
        if not date or not revenue:
            continue
        try:
            d = dt.date.fromisoformat(date) if "-" in date else None
            if not d:
                continue
            q = (d.month - 1) // 3 + 1
            key = f"{d.year} Q{q}"
            quarterly[key] = quarterly.get(key, 0) + int(revenue / 1_000_000)  # 轉百萬元
        except (ValueError, TypeError):
            continue
    return [{"quarter": k, "revenue": v} for k, v in sorted(quarterly.items())]


def merge_into_existing(existing: dict, fresh: dict) -> dict:
    """
    把新抓的硬資料合併進現有 JSON，**只覆寫 hard fields**。
    """
    if existing is None:
        # 新檔案 — 只寫硬資料，留下其他欄位空殼供 Claude 之後填
        return {
            "id": fresh.get("id"),
            "name": fresh.get("name") or "",
            "fullName": "",
            "market": "",
            "industry": "",
            "subIndustry": "",
            "lastUpdated": fresh["lastUpdated"],
            "dataQuality": "partial",
            "_dataQualityNote": "排程僅產出硬資料，請用 stock-research SKILL 補齊軟洞察",
            "price": fresh.get("price") or {},
            "oneLineDef": "",
            "executiveSummary": "",
            "revenueStructure": {
                "byProduct": [],
                "quarterlyTrend": fresh.get("quarterly_trend") or []
            },
            "majorCustomers": [],
            "earningsCallHighlights": [],
            "transformation": {"summary": "", "keyInitiatives": []},
            "peerComparison": [],
            "recentNews": [],
            "warnings": [],
            "dataVerification": fresh.get("verifications") or {},
        }

    merged = dict(existing)  # shallow copy

    # 1. price — 整個替換
    if fresh.get("price"):
        merged["price"] = fresh["price"]

    # 2. revenueStructure.quarterlyTrend — 只替換這一個 sub field，不動其他
    if fresh.get("quarterly_trend"):
        rs = dict(merged.get("revenueStructure") or {})
        rs["quarterlyTrend"] = fresh["quarterly_trend"]
        merged["revenueStructure"] = rs

    # 3. dataVerification — 整個替換
    if fresh.get("verifications"):
        merged["dataVerification"] = fresh["verifications"]

    # 4. lastUpdated
    merged["lastUpdated"] = fresh["lastUpdated"]

    # ⚠️ 絕不動：oneLineDef, executiveSummary, transformation, majorCustomers,
    #            peerComparison, earningsCallHighlights, recentNews, warnings

    return merged


def update_one(stock_id: str, repo_root: Path, finmind: FinMindClient,
               yahoo: Optional[YahooClient], dry_run: bool) -> dict:
    """更新單一股票，回傳結果摘要"""
    print(f"📡 {stock_id}", end=" ... ", flush=True)
    stock_path = repo_root / "data" / "stocks" / f"{stock_id}.json"

    raw = fetch_hard_data(stock_id, finmind, yahoo)
    raw["id"] = stock_id
    raw["lastUpdated"] = dt.datetime.now().isoformat(timespec="seconds")

    existing = load_json(stock_path)
    merged = merge_into_existing(existing, raw)

    summary = {
        "id": stock_id,
        "had_existing": existing is not None,
        "errors": raw["errors"],
        "verification": raw["verifications"].get("price", {}).get("status"),
    }

    if dry_run:
        print(f"✓ DRY-RUN (status={summary['verification']}, errors={len(raw['errors'])})")
    else:
        save_json(stock_path, merged)
        print(f"✓ saved (status={summary['verification']}, errors={len(raw['errors'])})")

    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="不寫入檔案")
    parser.add_argument("--skip-yahoo", action="store_true", help="跳過 Yahoo Finance")
    parser.add_argument("--force", action="store_true", help="假日也跑（預設週末跳過）")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="repo 根目錄")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()

    # 0. 假日跳過
    if not args.force and not is_taiwan_business_day():
        print(f"📅 今天是週末（{dt.date.today()}），跳過更新。用 --force 強制執行。")
        sys.exit(0)

    # 1. 讀 watchlist
    watchlist_path = repo_root / "data" / "watchlist.json"
    watchlist = load_json(watchlist_path)
    if not watchlist:
        print(f"❌ 找不到 {watchlist_path}", file=sys.stderr)
        sys.exit(1)

    stocks = watchlist.get("stocks", [])
    if not stocks:
        print("⚠️  Watchlist 為空，無事可做。")
        sys.exit(0)

    print(f"🚀 開始更新 {len(stocks)} 檔股票...")
    print(f"   Repo: {repo_root}")
    print(f"   Dry-run: {args.dry_run}")
    print()

    # 2. 初始化 client
    finmind = FinMindClient()
    if not finmind.token:
        print("⚠️  FINMIND_TOKEN 未設定，可能受免費額度限制", file=sys.stderr)
    yahoo = None if args.skip_yahoo else YahooClient()

    # 3. 逐檔更新
    results = []
    for s in stocks:
        try:
            r = update_one(s["id"], repo_root, finmind, yahoo, args.dry_run)
            results.append(r)
        except Exception as e:
            print(f"❌ {s['id']} 更新失敗：{e}")
            results.append({"id": s["id"], "errors": [str(e)]})

    # 4. 更新 watchlist 的 lastUpdated
    watchlist["lastUpdated"] = dt.datetime.now().isoformat(timespec="seconds")
    if not args.dry_run:
        save_json(watchlist_path, watchlist)

    # 5. 摘要
    print()
    print("=" * 50)
    success = sum(1 for r in results if not r.get("errors"))
    print(f"✅ 完成：{success}/{len(results)} 成功")

    failed = [r for r in results if r.get("errors")]
    if failed:
        print(f"⚠️  失敗 / 部分失敗：")
        for r in failed:
            print(f"   {r['id']}: {'; '.join(r['errors'][:2])}")

    # 6. exit code: 全部失敗才算 workflow 失敗
    if success == 0 and len(results) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
