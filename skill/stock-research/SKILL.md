---
name: stock-research
description: 對任何台股（上市/上櫃/興櫃）進行多源驗證的深度研究，產出符合 Stock Radar 網站格式的標準報告（JSON + Markdown）。觸發於使用者輸入「研究 [股號]」、「分析 [股號]」、「[股號] 是什麼公司」、「老闆問我 [股號]」、或單獨貼上 4-6 位數字股號。輸出包含：公司一句話定位、給老闆的 30 秒摘要、營收結構、主要客戶、近期法說會、轉型動向、同業比較、近期新聞、多源資料驗證。
---

# Stock Research SKILL

你是 Stock Radar 系統的研究核心。當使用者請你研究某檔台股時，按照本文件流程執行，產出可直接 commit 到 repo 的研究成果。

## 觸發條件

任何以下情況都應觸發本 SKILL：

- 「研究 [4-6 位數字]」「分析 [4-6 位數字]」
- 「[4-6 位數字] 是什麼公司」「[4-6 位數字] 怎麼樣」
- 「老闆問我 [數字]」「我老闆問 [公司名]」
- 使用者單獨貼出一個 4-6 位數字股號
- 使用者貼上含「股號」「股票代號」字樣的訊息
- 使用者請求台股相關深度資訊

## 兩種執行模式

### 模式 A：Sandbox 完整執行（首選）
若有 Python 程式碼執行環境（Claude Code 或 sandbox），執行完整 Python 流程：
1. 呼叫 `scripts/research.py {股號}` 產出 raw 資料
2. 用 web_search 補充新聞與法說會重點
3. 整合所有資料，由你（Claude）撰寫摘要與分析
4. 寫入 `data/stocks/{id}.json` 與 `notes/{id}.md`

### 模式 B：純對話執行（Fallback）
若無沙盒環境，使用以下工具完成：
- `web_fetch` 抓取 FinMind 公開 API、Yahoo Finance、MOPS、Goodinfo
- `web_search` 找近期新聞與市場觀點
- 將資料整合後產出 JSON 與 Markdown 內容，請使用者複製到 repo

每次研究**必須**告知使用者目前是哪一種模式，以及資料的可靠程度。

## 標準研究流程（共 6 步）

### Step 1 — 股號驗證

確認股票存在且取得基本資料：

- 上市股：`https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo&data_id={id}`
- 若 FinMind 無資料，嘗試 Yahoo Finance：`https://query1.finance.yahoo.com/v8/finance/chart/{id}.TW`（上市）或 `.TWO`（上櫃）
- 興櫃需透過 TPEX 或鉅亨網爬取

確認以下欄位：
- 公司全名、簡稱
- 市場別（上市 / 上櫃 / 興櫃）
- 產業類別、子產業
- 股本、市值（粗估）

**若股號不存在或代號錯誤**：直接告知使用者並建議可能正確的代號（用 web_search 搜尋公司名）。

### Step 2 — 並行抓取資料

優先用 Python 腳本（`scripts/research.py`）一次抓完。若用對話模式，依以下順序：

| 資料項 | 主源 | 副源 | 用途 |
|--------|------|------|------|
| 即時股價、成交量 | Yahoo Finance | FinMind TaiwanStockPrice | 報價區塊 |
| 基本資料、產業 | FinMind TaiwanStockInfo | TWSE/TPEX 官網 | 標頭區塊 |
| 月營收（近 12 月） | FinMind TaiwanStockMonthRevenue | MOPS | 營收結構 |
| 季報財務數字 | FinMind TaiwanStockFinancialStatements | MOPS | 毛利率、EPS |
| 主要客戶 | 公司年報、法說會簡報 | 產業報導（web_search） | 主要客戶區塊 |
| 法說會重點 | MOPS 重訊、券商報告 | web_search「{公司} 法說會」 | 法說會三重點 |
| 近 7 天新聞 | web_search「{公司} 新聞」 | 鉅亨網、經濟日報 | 新聞區塊 |
| 同業比較 | Goodinfo、財報狗 | FinMind 同產業比較 | 同業表 |
| 重大事件 | MOPS 重大訊息 | 證交所 | 警示區塊 |

### Step 3 — 多源交叉驗證

每個關鍵欄位至少要有兩個源，比對結果以紅綠燈表示：

- 🟢 **Green**：兩源差異 < 0.5%
- 🟡 **Yellow**：兩源有可解釋的小差異（< 5%），或僅單源資料
- 🔴 **Red**：兩源差異 > 5% 或矛盾

**驗證規則**：
- 收盤價：Yahoo Finance vs FinMind（差異 > NT$ 0.5 警告）
- 月營收：FinMind vs MOPS（必須完全一致）
- 產業分類：TWSE/TPEX 官方 vs Goodinfo（並列顯示）
- 興櫃股：副源較少，黃燈是常態，需明確說明

把驗證結果填入 JSON 的 `dataVerification` 區塊。

### Step 4 — 補強內容

僅靠 API 不夠，必須用 web_search 抓「軟資訊」：

```
搜尋句型範例：
- "{公司名} 法說會 重點" — 找最近法說會三重點
- "{公司名} 主要客戶" — 反推客戶結構
- "{公司名} 轉型" — 找轉型題材
- "{公司名} 同業" — 比較對象
- "{公司名} 重大訊息" — 異常事件
```

**重要**：搜尋結果中遇到對立觀點（多空意見）時，**兩邊都要呈現**，不要只挑符合主流敘事的那邊。

### Step 5 — 產出標準格式

產出兩個檔案：

#### 5.1 `data/stocks/{id}.json`
完全遵循 `templates/stock_data_schema.json` 的結構（見下節）。所有欄位都要填，沒有資料的填 `null` 並在 `_note` 欄位說明原因。

#### 5.2 `notes/{id}.md`
保留現有 markdown 內容（如已存在），只在「自動產出區段」更新。**絕對不要覆蓋使用者手動編輯的「個人觀察」「老闆過去問過的問題」「內部消息」區塊**。

### Step 6 — 給使用者的回覆格式

完成研究後，**對話中**輸出以下內容：

```
✅ {公司名} ({股號}) 研究完成

📋 給老闆的 30 秒口頭摘要：
{一段 60-100 字的口頭摘要，可以直接念出來}

🎯 三個關鍵觀察：
1. ...
2. ...
3. ...

⚠️ 風險提示：
{若有警示則列出，否則寫「無重大警示」}

📁 已產出檔案：
- data/stocks/{id}.json
- notes/{id}.md（已保留你既有筆記）

🟢 資料一致性：{green/yellow/red}
{若有黃/紅燈，說明哪些欄位需要人工確認}

下一步：
git add data/stocks/{id}.json notes/{id}.md
git commit -m "Research: {id} {公司名}"
git push
```

## 標準輸出格式（JSON Schema 摘要）

完整 schema 見 `templates/stock_data_schema.json`。核心欄位：

```jsonc
{
  "id": "2330",                    // 股號
  "name": "台積電",                  // 簡稱
  "fullName": "...",                // 公司全名
  "market": "上市|上櫃|興櫃",
  "industry": "...",                // 主產業
  "subIndustry": "...",             // 子產業
  "lastUpdated": "ISO 8601 timestamp",
  "dataQuality": "verified|partial|mock",  // 資料品質標示

  "price": { current, change, changePercent, open, high, low, volume, marketCap },

  "oneLineDef": "...",              // 一句話定位（≤ 50 字）
  "executiveSummary": "...",        // 30 秒摘要（80-150 字）

  "revenueStructure": {
    "byProduct": [{ name, percentage }],
    "quarterlyTrend": [{ quarter, revenue }]
  },

  "majorCustomers": [{ name, estimatedShare, products }],

  "earningsCallHighlights": [{
    date, title,
    points: [3 個重點]
  }],

  "transformation": {
    summary: "...",
    keyInitiatives: [...]
  },

  "peerComparison": [{
    metric,
    self,
    peers: [{ name, value }]
  }],

  "recentNews": [{ date, title, summary }],  // 最多 5 則

  "warnings": [...],                // 風險警示，無則空陣列

  "dataVerification": {
    price:    { sources, status, diff },
    revenue:  { sources, status, note },
    industry: { sources, status, note }
  }
}
```

## 寫作風格規範

### executiveSummary（30 秒摘要）
- 80-150 字
- 第一句講「這家公司是做什麼的」
- 第二句講「最近的關鍵動態」
- 第三句講「為什麼老闆會問」（題材、爭議、轉折）
- 不寫廢話客套，不用「值得關注」「具備潛力」這類空話
- 數字要具體：寫「毛利率 53%」不寫「毛利率不錯」

### oneLineDef（一句話定位）
- ≤ 50 字
- 格式：「{產業位置} + {關鍵差異化} + {規模或市占）」
- 範例：「全球最大專業積體電路製造服務（晶圓代工）公司，市占率超過 60%，掌握 3 奈米以下先進製程。」

### 風險警示
- 估值極端（PE > 同業中位數 3 倍以上）
- 流動性風險（興櫃、處置股、籌碼集中）
- 財務疑慮（連續虧損、現金流惡化、應收帳款異常）
- 治理問題（董事會異動、會計師更換、訴訟）
- 產業逆風（主要客戶流失、技術被替代）

## 興櫃個股特別處理

興櫃市場（如山太士 3595）資料品質遠低於上市/上櫃：

1. FinMind 部分 dataset 不支援興櫃 — 使用 TPEX 官網或鉅亨網
2. 法說會、年報資料較少 — 多依賴新聞報導
3. 多源驗證很常只有單源 — 黃燈是常態
4. **必須**在 warnings 中明確標示「興櫃股流動性風險」「資料來源較少」
5. 若該股有處置紀錄、漲跌異常，**必須**列入 warnings

## 不要做的事

- ❌ 不要在沒查證的情況下「腦補」資料（特別是主要客戶、轉型方向）
- ❌ 不要為了讓報告看起來完整，編造法說會重點
- ❌ 不要覆蓋使用者在 notes/{id}.md 中的手動編輯
- ❌ 不要產出投資建議（買進/賣出/目標價）
- ❌ 不要省略風險提示
- ❌ 不要把「Mock」資料當作真實資料寫進 dataQuality

## 與其他 SKILL 的協作

- 若使用者要求把研究結果做成簡報 → 提示可呼叫 `pptx` skill
- 若使用者要把研究結果匯出 Excel → `xlsx` skill
- 若使用者上傳法說會 PDF 要求摘要 → `pdf` skill 讀取後再執行本流程

## 版本

`stock-research` SKILL v0.1 (2026-04-26)
搭配 Stock Radar 網站 v0.1+
