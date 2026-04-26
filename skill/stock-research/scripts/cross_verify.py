"""
Cross-Source Verification
==========================
比對來自不同資料源的資料，產出紅綠燈狀態。

規則（節選自 SKILL.md）：
- 收盤價：差異 < 0.5% green / < 5% yellow / >= 5% red
- 月營收：必須完全一致才 green，否則 red
- 產業分類：兩源並列（很常不一致，但都正確）
"""

from typing import Any, Optional


def verify_price(finmind_price: Optional[float], yahoo_price: Optional[float]) -> dict:
    """收盤價交叉驗證"""
    sources_present = []
    if finmind_price is not None:
        sources_present.append("FinMind")
    if yahoo_price is not None:
        sources_present.append("Yahoo Finance")

    if len(sources_present) == 0:
        return {
            "sources": [],
            "status": "red",
            "diff": None,
            "note": "兩源都無資料"
        }
    if len(sources_present) == 1:
        return {
            "sources": sources_present,
            "status": "yellow",
            "diff": None,
            "note": "僅單一資料源"
        }

    # 兩源都有
    diff_abs = abs(finmind_price - yahoo_price)
    diff_pct = (diff_abs / max(finmind_price, yahoo_price)) * 100 if max(finmind_price, yahoo_price) else 0

    if diff_pct < 0.5:
        status = "green"
    elif diff_pct < 5:
        status = "yellow"
    else:
        status = "red"

    return {
        "sources": sources_present,
        "status": status,
        "diff": round(diff_pct, 3),
        "note": f"FinMind={finmind_price}, Yahoo={yahoo_price}" if status != "green" else None
    }


def verify_revenue(finmind_revenue: Optional[int], mops_revenue: Optional[int]) -> dict:
    """月營收交叉驗證 — 必須完全一致才 green"""
    sources = []
    if finmind_revenue is not None:
        sources.append("FinMind")
    if mops_revenue is not None:
        sources.append("MOPS")

    if not sources:
        return {"sources": [], "status": "red", "note": "兩源都無資料"}

    if len(sources) == 1:
        return {"sources": sources, "status": "yellow", "note": "僅單一資料源"}

    if finmind_revenue == mops_revenue:
        return {"sources": sources, "status": "green"}
    else:
        return {
            "sources": sources,
            "status": "red",
            "note": f"FinMind={finmind_revenue}, MOPS={mops_revenue}"
        }


def verify_industry(twse_industry: Optional[str], goodinfo_industry: Optional[str]) -> dict:
    """產業分類驗證 — 兩源並列展示，不一致是常態"""
    sources = []
    notes = []
    if twse_industry:
        sources.append("TWSE/TPEX")
        notes.append(f"官方歸類：{twse_industry}")
    if goodinfo_industry:
        sources.append("Goodinfo")
        notes.append(f"Goodinfo：{goodinfo_industry}")

    if not sources:
        return {"sources": [], "status": "red", "note": "無資料"}

    if len(sources) == 1:
        return {"sources": sources, "status": "yellow", "note": notes[0]}

    if twse_industry == goodinfo_industry:
        return {"sources": sources, "status": "green", "note": twse_industry}
    else:
        return {"sources": sources, "status": "yellow", "note": "；".join(notes)}


def overall_status(verifications: dict) -> str:
    """總結整體一致性"""
    statuses = [v.get("status") for v in verifications.values() if isinstance(v, dict)]
    if "red" in statuses:
        return "red"
    if "yellow" in statuses:
        return "yellow"
    return "green"


if __name__ == "__main__":
    # 測試
    import json
    test = {
        "price": verify_price(1180.00, 1179.50),
        "revenue": verify_revenue(285000, 285000),
        "industry": verify_industry("半導體業", "半導體"),
    }
    test["_overall"] = overall_status(test)
    print(json.dumps(test, ensure_ascii=False, indent=2))
