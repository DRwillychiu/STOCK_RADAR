# stock-research SKILL

> 對任何台股進行多源驗證的深度研究，產出 Stock Radar 網站可直接讀取的標準格式。

---

## 這是什麼

一個 Claude SKILL。當你跟 Claude 對話時輸入「研究 2330」，Claude 會按照 [`SKILL.md`](./SKILL.md) 的流程執行研究並產出標準格式的 JSON + Markdown。

---

## 三種使用方式

### 方式 A：Claude 對話中直接使用（最簡單）

把 [`SKILL.md`](./SKILL.md) 的內容貼到 Claude 對話開頭，然後輸入「研究 2330」。Claude 會：
- 用 web_search 搜尋公司基本資料
- 用 web_fetch 抓 FinMind 公開 endpoint、MOPS、Goodinfo
- 撰寫摘要
- 產出 JSON + Markdown 內容讓你複製到 repo

**優點**：不用安裝任何東西
**缺點**：Claude 沒有真正執行 Python，所有資料抓取都是即時的

### 方式 B：Claude Code（最完整）

如果你裝了 [Claude Code](https://docs.claude.com/en/docs/claude-code)：

```bash
# clone 整個 repo
git clone <your-repo-url>
cd stock-radar

# 設定 FinMind token
export FINMIND_TOKEN="你的token"

# 跟 Claude Code 對話
claude
> 研究 2330
```

Claude Code 會自動：
1. 偵測 `skill/stock-research/SKILL.md` 並載入
2. 執行 `research.py 2330` 取得 raw 資料
3. 用 web_search/web_fetch 補強
4. 寫入 `data/stocks/2330.json` 與 `notes/2330.md`
5. 給你 git commit 指令

### 方式 C：純 Python 自動化（給排程用）

直接執行 Python 腳本（不經過 Claude）：

```bash
cd skill/stock-research
pip install -r scripts/requirements.txt   # 目前無外部依賴

python scripts/research.py 2330 -o ../../data/stocks/2330_raw.json
```

這只會產出 raw dump（沒有 executiveSummary 等需要 LLM 撰寫的欄位）。
適合用 GitHub Actions 每日定期更新「硬資料」（價格、營收、財務數字），
而需要洞察的部分留給 Claude 撰寫。

---

## 檔案結構

```
stock-research/
├── SKILL.md                          ← 主文件（給 Claude 的指令）
├── README.md                         ← 本文件（給人類）
├── scripts/
│   ├── research.py                   ← 主流程（CLI 入口）
│   ├── fetch_finmind.py              ← FinMind API 客戶端
│   ├── fetch_yahoo.py                ← Yahoo Finance 客戶端
│   ├── fetch_mops.py                 ← MOPS URL 產生器
│   ├── cross_verify.py               ← 多源比對
│   └── requirements.txt
├── templates/
│   ├── stock_data_schema.json        ← JSON 標準格式
│   └── notes_template.md             ← 筆記模板
└── reference/
    └── industry_taxonomy.json        ← 產業分類對照
```

---

## FinMind Token 怎麼取得

1. 註冊 [FinMind](https://finmindtrade.com/)（免費）
2. 登入後到「會員中心」取得 API token
3. 設為環境變數：`export FINMIND_TOKEN="..."`

免費版限制 600 次/小時，個人使用足夠。

---

## 實際跑一次看看

最簡單的驗證方式：

```bash
# 1. 測 FinMind
python skill/stock-research/scripts/fetch_finmind.py 2330

# 2. 測 Yahoo Finance（不需 token）
python skill/stock-research/scripts/fetch_yahoo.py 2330

# 3. 測完整 pipeline
python skill/stock-research/scripts/research.py 2330

# 4. 測交叉驗證邏輯
python skill/stock-research/scripts/cross_verify.py
```

---

## 常見問題

**Q: 為什麼 research.py 只產出 raw dump，不產出最終 JSON？**
A: 因為最終 JSON 中的 `executiveSummary`、`oneLineDef`、`transformation.summary` 等欄位需要綜合判斷與寫作能力，這是 Claude（LLM）的工作而非 Python 腳本。Python 負責抓資料與驗證、Claude 負責整合與洞察。

**Q: 我可以不用 Claude，純 Python 跑嗎？**
A: 可以，但你會失去最有價值的「30 秒摘要」「轉型分析」等內容。建議至少把 `research.py` 跑出來的 raw dump 餵給 Claude 一次。

**Q: MOPS 為什麼只給 URL 不直接爬？**
A: MOPS 改版頻繁，純 Python 爬蟲容易壞掉。改用 web_fetch 由 Claude 即時解析 HTML 較穩定。

**Q: 興櫃股資料品質如何？**
A: 普遍較差。FinMind 部分 dataset 不支援興櫃。`SKILL.md` 已對興櫃有特別處理規範（見「興櫃個股特別處理」段落）。

---

## 版本

v0.1 — 2026-04-26
