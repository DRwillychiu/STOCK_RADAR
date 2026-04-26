#!/usr/bin/env python3
"""
research.py — Stock Research Main Pipeline
=============================================
整合所有 fetcher，產出 raw 資料 dump 給 Claude 撰寫摘要。

使用：
    python research.py 2330
    python research.py 2330 --output ./data/stocks/2330_raw.json

流程：
1. 並行抓 FinMind + Yahoo Finance
2. 列出 MOPS 待 web_fetch 的 URL（不直接爬，由 Claude 用 web_fetch 處理）
3. 多源交叉驗證
4. 輸出 raw JSON，由 Claude 接手撰寫 executiveSummary、oneLineDef 等

注意：本腳本「不」產出最終的 stocks/{id}.json，那一步必須由 Claude（人類智慧）完成。
本腳本只負責資料抓取與驗證。
"""

import os
import sys
import json
import argparse
import datetime as dt
from concurrent.futures import ThreadPoolExecutor

# 確保可以 import 同目錄模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_finmind import FinMindClient, FinMindError
from fetch_yahoo import YahooClient, YahooError
from fetch_mops import MopsClient
from cross_verify import verify_price, verify_industry, overall_status


def fetch_all_sources(stock_id: str) -> dict:
    """並行抓所有資料源"""
    finmind = FinMindClient()
    yahoo = YahooClient()
    mops = MopsClient()

    with ThreadPoolExecutor(max_workers=3) as ex:
        f_finmind = ex.submit(finmind.fetch_all, stock_id)
        f_yahoo = ex.submit(yahoo.quote, stock_id)
        f_mops_urls = ex.submit(mops.get_research_urls, stock_id)

        finmind_data = f_finmind.result()
        yahoo_data = f_yahoo.result()
        mops_urls = f_mops_urls.result()

    return {
        "finmind": finmind_data,
        "yahoo": yahoo_data,
        "mops_urls_for_claude_to_fetch": mops_urls,
    }


def build_raw_dump(stock_id: str) -> dict:
    """建立 raw dump，給 Claude 整合"""
    print(f"📡 開始研究 {stock_id}...", file=sys.stderr)
    sources = fetch_all_sources(stock_id)

    # 從 FinMind 取基本資料
    info = sources["finmind"].get("info") or {}
    finmind_price_data = sources["finmind"].get("latest_price") or {}
    yahoo_data = sources["yahoo"] or {}

    # 交叉驗證
    fin_price = finmind_price_data.get("close") if finmind_price_data else None
    yh_price = yahoo_data.get("current") if yahoo_data else None

    verifications = {
        "price": verify_price(fin_price, yh_price),
        "industry": verify_industry(info.get("industry_category"), None),
    }
    overall = overall_status(verifications)

    # 取最近月營收
    revenues = sources["finmind"].get("month_revenue", [])
    revenues_sorted = sorted(revenues, key=lambda r: r.get("date", ""), reverse=True)[:12]

    # 取財報（推算毛利率、EPS 等）
    financials = sources["finmind"].get("financials", [])

    # 取新聞
    news = sources["finmind"].get("news", [])[:10]

    return {
        "_meta": {
            "stock_id": stock_id,
            "fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
            "overall_data_quality": overall,
        },
        "basic_info": {
            "id": stock_id,
            "name": info.get("stock_name"),
            "industry": info.get("industry_category"),
            "type": info.get("type"),  # 上市/上櫃
        },
        "price": {
            "finmind": finmind_price_data,
            "yahoo": yahoo_data,
        },
        "monthly_revenue_recent_12": revenues_sorted,
        "financial_statements": financials,
        "recent_news": news,
        "mops_urls_to_fetch_with_web_fetch": sources["mops_urls_for_claude_to_fetch"],
        "verifications": verifications,
        "_instructions_for_claude": (
            "這是 raw 資料 dump。下一步請：\n"
            "1. 用 web_fetch 取 mops_urls_to_fetch_with_web_fetch 中的 URL，補強重訊與營收細節\n"
            "2. 用 web_search 搜尋『{公司名} 法說會 重點』『{公司名} 主要客戶』『{公司名} 轉型』\n"
            "3. 整合所有資料，按 SKILL.md Step 5 的格式撰寫 stocks/{id}.json\n"
            "4. 產出時 dataQuality 欄位依本 dump 的 overall_data_quality 決定\n"
            "5. 撰寫 oneLineDef、executiveSummary 時遵循 SKILL.md 的「寫作風格規範」"
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stock_id", help="台股代號，例：2330")
    parser.add_argument("-o", "--output", help="輸出檔案路徑（預設輸出到 stdout）")
    args = parser.parse_args()

    raw = build_raw_dump(args.stock_id)
    output_str = json.dumps(raw, ensure_ascii=False, indent=2, default=str)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str)
        print(f"✅ Raw dump 已輸出至 {args.output}", file=sys.stderr)
    else:
        print(output_str)


if __name__ == "__main__":
    main()
