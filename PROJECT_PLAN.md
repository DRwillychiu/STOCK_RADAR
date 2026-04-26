# 個人台股研究系統 — 完整專案規劃

> **文件版本**：v1.0
> **建立日期**：2026-04-25
> **維護者**：[你的名字]
> **核心目的**：讓老闆隨口問一支股票時，能在 5 分鐘內掌握該公司的產業定位、營收結構、轉型動向、近期動態，並提出有見地的觀察。

---

## 目錄

0. [TL;DR — 一頁讀完整個專案](#0-tldr)
1. [專案目的與定位](#1-專案目的與定位)
2. [前置知識檢核](#2-前置知識檢核)
3. [系統架構設計](#3-系統架構設計)
4. [資料源策略](#4-資料源策略)
5. [研究 SKILL 規劃](#5-研究-skill-規劃)
6. [網站功能規劃](#6-網站功能規劃)
7. [GitHub Repo 結構](#7-github-repo-結構)
8. [Roadmap 與里程碑](#8-roadmap-與里程碑)
9. [詳細 To-Do List](#9-詳細-to-do-list)
10. [進度追蹤](#10-進度追蹤)
11. [部署流程](#11-部署流程)
12. [日常使用 SOP](#12-日常使用-sop)
13. [風險、限制與注意事項](#13-風險限制與注意事項)
14. [附錄](#14-附錄)

---

## 0. TL;DR

這個系統由**三層**組成：

1. **研究層（SKILL）**：一個固定流程的 Claude Skill。輸入「幫我研究 2330」，自動抓多個資料源、交叉驗證、產出標準格式的 markdown 研究報告。
2. **資料層（GitHub Actions + JSON）**：你的 watchlist 每天早上自動更新，多源比對結果以 JSON 寫回 repo。
3. **展示層（GitHub Pages 網站）**：搜尋框 + Watchlist Dashboard + 個股詳情頁。Watchlist 內的股票讀預先抓好的詳細 JSON；非 Watchlist 的股票即時用 FinMind API 抓基本盤。

**核心設計哲學**：SKILL 是大腦，網站是介面，GitHub Repo 是知識庫。三者解耦，任何一層出問題都不會拖垮另外兩層。

**預估完成時間**：5 個 Phase，每個 Phase 1-2 週，總計約 6-10 週可達到完整功能版本。MVP 第一週就能有產出。

---

## 1. 專案目的與定位

### 1.1 為什麼要做這個

- **痛點**：老闆隨口問股票時，無法立即講出有見地的內容
- **不解決的話**：每次都要花 30+ 分鐘臨時 Google，還容易抓到品質參差的資訊
- **目標狀態**：5 分鐘內掌握重點，且資訊經過多重驗證

### 1.2 成功指標

| 指標 | 目標 |
|------|------|
| 隨機個股初步掌握時間 | < 5 分鐘 |
| Watchlist 內個股回應時間 | < 30 秒 |
| 資料來源數 | ≥ 3 源交叉比對 |
| 涵蓋範圍 | 上市 + 上櫃 + 興櫃 |

### 1.3 不做什麼（明確排除）

- ❌ 不做投資建議或買賣訊號（避免法律風險）
- ❌ 不做即時報價系統（已有看盤軟體）
- ❌ 不做技術分析（K 線、指標）
- ❌ 不做公開分享（個人使用，repo 可設 private 或 public 視需要）

---

## 2. 前置知識檢核

### 2.1 你已經會的（從你的籌碼專案推測）

- ✅ Python 基礎
- ✅ GitHub 操作（commit、push、PR）
- ✅ GitHub Actions（你已經有自動更新在跑）
- ✅ JSON 資料處理
- ✅ 排程任務概念

### 2.2 你可能需要補的

| 技術 | 必要性 | 學習資源 | 替代方案 |
|------|--------|----------|----------|
| HTML / CSS 基礎 | 高 | [MDN HTML 教學](https://developer.mozilla.org/zh-TW/docs/Learn/HTML) | 我可以全部寫好你直接用 |
| JavaScript（client-side fetch） | 高 | [MDN Fetch API](https://developer.mozilla.org/zh-TW/docs/Web/API/Fetch_API/Using_Fetch) | 同上 |
| Chart.js 或 ECharts | 中 | [Chart.js 官網](https://www.chartjs.org/) | 改用靜態 SVG |
| GitHub Pages 設定 | 高 | [GitHub Pages 文件](https://docs.github.com/en/pages) | 無 |
| FinMind API 用法 | 高 | [FinMind 文件](https://finmindtrade.com/analysis/#/data/api) | 改用 yfinance（功能較少）|
| Markdown 進階語法 | 中 | 你已會基礎，補表格、TOC 即可 | 無 |

### 2.3 完全不需要會的

- React、Vue 等框架（純 HTML/CSS/JS 就夠）
- Node.js 後端（GitHub Pages 不支援）
- 資料庫（用 JSON 檔案就夠）

### 2.4 工具準備清單

- [ ] VSCode（編輯器）
- [ ] Git（你已有）
- [ ] Python 3.10+（你已有）
- [ ] FinMind 帳號（免費註冊，取得 API token）
- [ ] Claude（你已在用）

---

## 3. 系統架構設計

### 3.1 三層架構圖

```
┌─────────────────────────────────────────────────────────┐
│                  使用者（你）                              │
└─────────────────────────────────────────────────────────┘
              │                              │
              │ 老闆突然問                    │ 平日研究
              ▼                              ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│   展示層：Web UI         │    │   研究層：Claude SKILL    │
│   (GitHub Pages)         │    │   (stock-research)      │
│                          │    │                         │
│  - 搜尋框                 │    │  - 標準研究流程          │
│  - Watchlist Dashboard    │    │  - 多源資料抓取          │
│  - 個股詳情頁             │    │  - 交叉驗證              │
└─────────────────────────┘    │  - 產出 .md 報告         │
              ▲                 └─────────────────────────┘
              │ 讀取                          │
              │                              │ 產出 / 更新
              ▼                              ▼
┌─────────────────────────────────────────────────────────┐
│              資料層：GitHub Repo                         │
│                                                         │
│  /data/stocks/{id}.json   ← 排程更新                    │
│  /notes/{id}.md           ← 研究筆記（手動 / SKILL 產出）  │
│  /data/watchlist.json     ← 追蹤清單                    │
└─────────────────────────────────────────────────────────┘
              ▲
              │ 每日更新
              │
┌─────────────────────────────────────────────────────────┐
│           背景層：GitHub Actions                         │
│                                                         │
│  - 每日 07:00 跑 update_watchlist.py                    │
│  - 抓多源資料 → 比對 → 寫 JSON → commit                 │
└─────────────────────────────────────────────────────────┘
```

### 3.2 兩種使用情境的資料流

**情境 A：老闆問了一檔我有在追的股票（Watchlist 內）**

```
搜尋框輸入 2330
  → JS 讀 /data/stocks/2330.json（已預先抓好）
  → 顯示完整詳情頁（< 1 秒）
  → 同時顯示「上次更新時間：今早 07:15」
```

**情境 B：老闆問了一檔我沒在追的股票（Watchlist 外）**

```
搜尋框輸入 6488
  → JS 偵測 6488 不在 watchlist
  → 即時 fetch FinMind API + Yahoo Finance
  → 顯示「快速版」資料 + 警示「此股未列入追蹤，資料較淺」
  → 提供「加入 Watchlist 並深度研究」按鈕
  → 按下後在本地產出 SKILL 指令字串，你複製到 Claude 跑
```

### 3.3 為什麼選這樣的架構

- **解耦**：SKILL 壞掉不影響網站；網站壞掉 SKILL 還能跑
- **零成本**：GitHub Pages 免費、GitHub Actions 對 public repo 免費
- **可控**：所有資料、邏輯都在你自己的 repo 裡，不依賴第三方服務存活
- **離線可用**：把 repo clone 下來，網站本地用 `python -m http.server` 也能跑

---

## 4. 資料源策略

### 4.1 主要資料源清單

| 資料源 | 用途 | 是否支援 CORS | Rate Limit | 成本 |
|--------|------|--------------|------------|------|
| **FinMind** | 主力，財報、月營收、股價 | ✅ | 免費 600/hr，付費更高 | 免費足夠 |
| **Yahoo Finance（非官方）** | 即時報價、基本面 | ✅ | 寬鬆 | 免費 |
| **公開資訊觀測站 (MOPS)** | 重訊、法說會 | ❌（要爬） | 自行控制 | 免費 |
| **櫃買中心 (TPEX)** | 上櫃/興櫃資料 | ❌（要爬） | 自行控制 | 免費 |
| **Goodinfo** | 同業比較、產業歸類 | ❌（要爬） | 注意被擋 | 免費 |

### 4.2 多源比對邏輯

針對「越詳細越好 + 多重確認」的需求，每個關鍵欄位至少要有兩個源：

| 欄位 | 主源 | 副源 | 比對方式 |
|------|------|------|----------|
| 收盤價 | FinMind | Yahoo Finance | 差異 > 0.5% 警告 |
| 月營收 | FinMind | MOPS 爬蟲 | 完全一致才綠燈 |
| 產業分類 | TPEX/TWSE | Goodinfo | 兩者並列顯示 |
| 主要產品 | 法說會 PDF | 年報 | 人工確認後寫死 |

UI 上以**紅綠燈系統**呈現：
- 🟢 綠燈：兩源一致
- 🟡 黃燈：有小差異（< 1%）
- 🔴 紅燈：明顯差異或單源資料

### 4.3 法律與合規

- 所有資料源僅用於個人研究，不對外提供
- 不可重新打包資料對外發布（避免侵權）
- 網站若公開部署，需放免責聲明

---

## 5. 研究 SKILL 規劃

### 5.1 SKILL 是什麼

Claude Skill 是一個資料夾，包含 `SKILL.md` 主文件和支援腳本。當你的提問匹配 SKILL 的觸發條件時，Claude 會載入該 SKILL 的內容，按照其中定義的流程執行。

### 5.2 SKILL 結構設計

```
stock-research/
├── SKILL.md                  ← 觸發條件、執行流程、輸出格式
├── scripts/
│   ├── fetch_finmind.py      ← FinMind 資料抓取
│   ├── fetch_yahoo.py        ← Yahoo Finance 抓取
│   ├── fetch_mops.py         ← 公開資訊觀測站爬蟲
│   └── cross_verify.py       ← 多源比對邏輯
├── templates/
│   └── report_template.md    ← 標準研究報告格式
└── reference/
    └── industry_taxonomy.json ← 產業分類對照表
```

### 5.3 SKILL.md 觸發條件

```
觸發場景：
- 使用者輸入包含「研究 [股號]」「分析 [股號]」「[股號] 是什麼公司」
- 使用者貼上股票代號（4 位數字）
- 使用者問「老闆問我 XXX」
```

### 5.4 SKILL 執行的標準流程

```
Step 1: 確認股票代號（驗證是否存在於上市/上櫃/興櫃）
Step 2: 並行抓取
   ├─ FinMind: 基本資料、財報、月營收、股價
   ├─ Yahoo Finance: 即時報價、市值
   └─ MOPS: 最近 3 場法說會、最近 30 天重訊
Step 3: 交叉驗證
   ├─ 收盤價比對
   ├─ 營收數字比對
   └─ 產業分類比對
Step 4: 補充資訊（用 web_search）
   ├─ 近 7 天新聞
   ├─ 主要客戶/供應鏈
   └─ 轉型相關報導
Step 5: 產出報告
   ├─ 寫入 /notes/{id}.md
   ├─ 更新 /data/stocks/{id}.json
   └─ 給使用者一段話的口頭摘要（給老闆用的）
```

### 5.5 標準報告格式（report_template.md）

```markdown
# {公司名稱} ({股號})

> 最後更新：{timestamp}
> 資料一致性：🟢/🟡/🔴

## 一句話定位
{產業 / 子產業 / 商業模式}

## 給老闆的 30 秒摘要
{一段話總結公司現況、近期動態、最重要的一個轉型題材}

## 營收結構
- 主力產品 1：XX%
- 主力產品 2：XX%
- ...
（近 3 季趨勢）

## 主要客戶 / 供應鏈位置
...

## 近期法說會三重點
1. ...
2. ...
3. ...

## 轉型 / 新業務動向
...

## 同業比較
| 指標 | 本公司 | 同業 A | 同業 B |
| 毛利率 | ... | ... | ... |
| 本益比 | ... | ... | ... |

## 近 7 天新聞摘要
- {日期} {新聞標題} → {一句話重點}

## 個人筆記
（手動編輯區）

## 資料來源驗證
- 收盤價：FinMind ✅ Yahoo ✅
- 月營收：FinMind ✅ MOPS ✅
- ...
```

---

## 6. 網站功能規劃

### 6.1 頁面結構

```
/                       ← 首頁（搜尋 + Watchlist Dashboard）
/stock.html?id=2330     ← 個股詳情頁
/about.html             ← 說明 + 免責聲明
```

### 6.2 首頁設計

```
┌─────────────────────────────────────────────┐
│  [搜尋框: 輸入股號或公司名稱      ] [搜尋]      │  ← 全域搜尋
├─────────────────────────────────────────────┤
│  📋 我的 Watchlist                           │
│                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 2330      │ │ 3711      │ │ 3595      │ │  ← 卡片式
│  │ 台積電    │ │ 日月光    │ │ 山太士    │  │
│  │ 1,180.00  │ │  165.50  │ │ 2,770.00 │  │
│  │ +1.2% 🟢  │ │ -0.5% 🟢  │ │ -0.6% 🟡 │  │
│  └──────────┘ └──────────┘ └──────────┘   │
│                                             │
├─────────────────────────────────────────────┤
│  📰 今日重訊摘要（Watchlist 內）              │
│  - 2330: ...                                 │
└─────────────────────────────────────────────┘
```

### 6.3 個股詳情頁

按閱讀順序排列：

1. **標頭區**：公司名稱、股號、市場別、產業、收盤價（綠/紅燈）
2. **30 秒摘要**：AI 整合的一段話
3. **營收結構**：餅圖 + 近 3 季趨勢
4. **主要客戶 / 供應鏈位置**：圖示或列表
5. **近期法說會三重點**：時間軸樣式
6. **轉型 / 新業務動向**：突出顯示
7. **同業比較**：表格
8. **近 7 天新聞**：時間軸 + 一句話摘要
9. **我的筆記**：讀取 `/notes/{id}.md` 渲染
10. **資料來源驗證**：紅綠燈總表

### 6.4 視覺設計原則

使用 `frontend-design` SKILL 確保不是 AI 套版感。預期風格：
- 暗色或米白色基底（不要純白純黑）
- 數據導向，但不過度「終端機風」
- 中文字型用 Noto Sans TC 或 PingFang
- 重點用色彩強調，不用粗體濫用
- 留白充足

---

## 7. GitHub Repo 結構

```
your-stock-research/
├── README.md                    ← 專案說明（給未來的自己）
├── PROJECT_PLAN.md              ← 本文件
├── index.html                   ← 首頁
├── stock.html                   ← 個股詳情頁
├── about.html                   ← 關於頁
├── assets/
│   ├── css/
│   │   └── main.css
│   ├── js/
│   │   ├── app.js               ← 主邏輯
│   │   ├── search.js            ← 搜尋功能
│   │   ├── api.js               ← FinMind/Yahoo 封裝
│   │   └── charts.js            ← Chart.js 設定
│   └── icons/
├── data/
│   ├── watchlist.json           ← 追蹤清單
│   ├── industries.json          ← 產業分類對照
│   └── stocks/
│       ├── 2330.json
│       ├── 3711.json
│       └── 3595.json
├── notes/
│   ├── 2330.md
│   ├── 3711.md
│   └── 3595.md
├── scripts/
│   ├── update_watchlist.py
│   ├── fetch_finmind.py
│   ├── fetch_yahoo.py
│   ├── fetch_mops.py
│   ├── cross_verify.py
│   └── requirements.txt
├── .github/
│   └── workflows/
│       └── daily_update.yml
└── .gitignore
```

---

## 8. Roadmap 與里程碑

### Phase 1: MVP — 基礎可運作版（第 1 週）

**目標**：能用網站看到三檔練習股票的基本資料。

- 建立 repo
- 寫好 `index.html` 和 `stock.html` 骨架
- 手動建立三檔股票的 JSON 與筆記
- GitHub Pages 部署成功
- ✅ 完成標準：在手機上打開網站，能看到三檔股票

### Phase 2: 研究 SKILL（第 2-3 週）

**目標**：建立 stock-research SKILL，能自動產出研究報告。

- 設計 SKILL.md
- 寫 fetch_finmind.py、fetch_yahoo.py
- 寫 cross_verify.py
- 用三檔練習股票驗證
- ✅ 完成標準：在 Claude 輸入「研究 2330」能產出標準報告

### Phase 3: 自動化資料層（第 4 週）

**目標**：Watchlist 內股票每日自動更新。

- 寫 update_watchlist.py
- 設定 GitHub Actions（參考你的籌碼專案經驗）
- 測試排程穩定性
- ✅ 完成標準：連續 5 天每日 07:00 自動更新成功

### Phase 4: 即時查詢功能（第 5-6 週）

**目標**：搜尋 Watchlist 外的股票時，即時抓資料。

- 寫 client-side fetch 邏輯
- 處理 CORS 與錯誤狀態
- UI 區分「完整版」與「快速版」
- ✅ 完成標準：搜尋 6488，5 秒內顯示基本盤

### Phase 5: AI 整合與精煉（第 7-8 週）

**目標**：自動產出 30 秒摘要、新聞重點。

- 整合 Claude API（artifact 內或 SKILL 中）
- 撰寫摘要 prompt template
- 視覺優化（用 frontend-design SKILL）
- ✅ 完成標準：摘要品質達到「能直接念給老闆聽」的程度

### Phase 6（選做）: 進階功能

- 同業比較自動化
- 法說會 PDF 自動讀取摘要
- 異常事件警報（GitHub Issues 通知）
- 個人筆記用 Issues API 雙向同步

---

## 9. 詳細 To-Do List

### Phase 1: MVP

- [ ] 建立新 GitHub repo（命名建議 `stock-radar` 或自訂）
- [ ] 在 repo 設定 GitHub Pages（Settings → Pages → main branch）
- [ ] 建立目錄結構（複製本文件第 7 章的樹狀圖）
- [ ] 寫 `index.html`（搜尋框 + 三張卡片）
- [ ] 寫 `assets/css/main.css`（基礎樣式）
- [ ] 手動建立 `data/stocks/2330.json`（用模板格式）
- [ ] 手動建立 `data/stocks/3711.json`
- [ ] 手動建立 `data/stocks/3595.json`
- [ ] 手動建立 `notes/2330.md`、`3711.md`、`3595.md`
- [ ] 寫 `data/watchlist.json`
- [ ] 寫 `stock.html`（吃 URL 參數渲染）
- [ ] 寫 `assets/js/app.js`（讀 JSON、render）
- [ ] 部署測試（push → 等 1 分鐘 → 開 GitHub Pages 網址）
- [ ] 手機開啟測試 RWD

### Phase 2: 研究 SKILL

- [ ] 註冊 FinMind 帳號，取得 API token
- [ ] 建立 SKILL 資料夾結構
- [ ] 寫 `SKILL.md`（觸發條件、流程、格式）
- [ ] 寫 `scripts/fetch_finmind.py`
- [ ] 寫 `scripts/fetch_yahoo.py`
- [ ] 寫 `scripts/fetch_mops.py`
- [ ] 寫 `scripts/cross_verify.py`
- [ ] 寫 `templates/report_template.md`
- [ ] 寫 `reference/industry_taxonomy.json`
- [ ] 用 2330 測試完整流程
- [ ] 用 3711 測試
- [ ] 用 3595 測試（注意興櫃資料源差異）
- [ ] 把 SKILL 上傳到 Claude（如使用 skill 上傳功能）

### Phase 3: 自動化

- [ ] 寫 `scripts/update_watchlist.py`
- [ ] 寫 `requirements.txt`
- [ ] 寫 `.github/workflows/daily_update.yml`
- [ ] 設定 repo Secrets（FINMIND_TOKEN）
- [ ] 手動觸發一次測試
- [ ] 設定 cron 排程（07:00 台灣時間 = 23:00 UTC 前一日）
- [ ] 連續觀察 5 天

### Phase 4: 即時查詢

- [ ] 寫 `assets/js/api.js`（FinMind 客戶端封裝）
- [ ] 寫 `assets/js/search.js`（搜尋邏輯）
- [ ] 處理「股號不存在」錯誤
- [ ] 處理「API 限流」錯誤
- [ ] UI 加上「快速版/完整版」標記
- [ ] 加上「加入 Watchlist」按鈕（產生 SKILL 指令字串）

### Phase 5: AI 整合

- [ ] 設計 30 秒摘要 prompt
- [ ] 設計新聞重點 prompt
- [ ] 整合到 SKILL 流程（產出時自動呼叫 Claude API）
- [ ] 用 frontend-design SKILL 優化視覺
- [ ] 撰寫 `about.html`（含免責聲明）

---

## 10. 進度追蹤

複製以下表格到 README.md 隨時更新：

```markdown
## 專案進度

- [▰▰▰▱▱▱▱▱▱▱] Phase 1: MVP             30%
- [▱▱▱▱▱▱▱▱▱▱] Phase 2: 研究 SKILL        0%
- [▱▱▱▱▱▱▱▱▱▱] Phase 3: 自動化           0%
- [▱▱▱▱▱▱▱▱▱▱] Phase 4: 即時查詢          0%
- [▱▱▱▱▱▱▱▱▱▱] Phase 5: AI 整合          0%

最後更新：YYYY-MM-DD
當前重點：[寫一行你正在做什麼]
卡關：[寫一行你卡住的地方，沒有就寫「無」]
```

每完成一個 Phase 的任務，就更新進度條和「當前重點」。

---

## 11. 部署流程

### 11.1 GitHub Pages 啟用步驟

1. Repo Settings → Pages
2. Source 選 `Deploy from a branch`
3. Branch 選 `main` / `(root)`
4. Save 後等 1-2 分鐘
5. 網址會是 `https://{你的GitHub帳號}.github.io/{repo-name}/`

### 11.2 GitHub Actions 設定（daily_update.yml 範例）

```yaml
name: Daily Stock Data Update

on:
  schedule:
    - cron: '0 23 * * *'  # UTC 23:00 = 台灣時間 07:00
  workflow_dispatch:        # 允許手動觸發

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r scripts/requirements.txt
      - env:
          FINMIND_TOKEN: ${{ secrets.FINMIND_TOKEN }}
        run: python scripts/update_watchlist.py
      - run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add data/
          git diff --quiet && git diff --staged --quiet || git commit -m "Daily update: $(date +'%Y-%m-%d')"
          git push
```

### 11.3 環境變數設定

- Repo Settings → Secrets and variables → Actions
- 新增 `FINMIND_TOKEN`（值為 FinMind 給的 API token）

---

## 12. 日常使用 SOP

### 12.1 老闆突然問股票時

```
1. 打開網站（手機或電腦皆可）
2. 在搜尋框輸入股號
3. 看到完整版（Watchlist 內）→ 直接念「30 秒摘要」+ 補充任何欄位細節
   看到快速版（Watchlist 外）→ 念基本資訊，告訴老闆「我深入研究後再回報」
4. 之後找時間在 Claude 輸入「研究 XXXX」，產出完整報告
5. 把研究結果加入 Watchlist
```

### 12.2 平日維護

**每週一**（10 分鐘）：
- 打開網站，瀏覽 Watchlist 是否有異常
- 看「今日重訊摘要」

**每月初**（30 分鐘）：
- 檢查 Watchlist，移除不再關注的、加入新標的
- 跑一次完整 SKILL 更新所有 Watchlist 的研究筆記

### 12.3 加入新股票到 Watchlist

```
1. 在 Claude 對話框輸入「研究 [股號]」
2. SKILL 自動執行，產出 .md 報告
3. Claude 同時提供 git 指令：
   - 把 stocks/{id}.json 加進去
   - 把 notes/{id}.md 加進去
   - 修改 watchlist.json
4. 你執行 git commit & push
5. 隔天早上 GitHub Actions 會自動把它納入排程
```

---

## 13. 風險、限制與注意事項

### 13.1 技術風險

| 風險 | 機率 | 影響 | 緩解 |
|------|------|------|------|
| FinMind API 改版或停用 | 低 | 高 | 預留 yfinance 作為 fallback |
| GitHub Actions 額度用盡 | 極低 | 中 | Public repo 完全免費，私人也有 2000 分鐘/月 |
| 爬蟲被擋 IP | 中 | 中 | 加 sleep、輪換 User-Agent |
| 資料來源不一致 | 高 | 低 | 設計初衷就是要呈現這個，紅綠燈系統 |

### 13.2 個資與資安

- ⚠️ FinMind token 一定要放 Secrets，**不要寫死在程式碼**
- ⚠️ 個人筆記如果有敏感內容（聽到的內幕），repo 設為 private
- ⚠️ 不要在公開 repo 留下老闆名字、公司內部資訊

### 13.3 法律免責

如果網站公開部署，about.html 必須包含：
- 「資料僅供個人研究參考」
- 「不構成任何投資建議」
- 「資料準確性以官方來源為準」

### 13.4 維護成本估算

- **建置期**：6-10 週，每週投入 5-10 小時
- **穩定後**：每週 10-30 分鐘維護 + Watchlist 異動時加入新股票

---

## 14. 附錄

### 14.1 練習案例詳細資訊

| 項目 | 台積電 | 日月光投控 | 山太士 |
|------|--------|------------|--------|
| 股號 | 2330 | 3711 | 3595 |
| 市場 | 上市 | 上櫃 | 興櫃 |
| 產業 | 半導體 | 半導體封測 | 光電（轉型半導體封裝材料） |
| 為何選它當練習 | 全球最大代工，資料最豐富 | 封測龍頭，產業地位清楚 | 興櫃妖股，轉型題材，測試異常處理 |

### 14.2 常用 API endpoints

**FinMind**
- 文件：https://finmindtrade.com/analysis/#/data/api
- Base URL：https://api.finmindtrade.com/api/v4/data
- 範例 dataset：`TaiwanStockInfo`、`TaiwanStockMonthRevenue`、`TaiwanStockPrice`

**Yahoo Finance（非官方）**
- 範例：`https://query1.finance.yahoo.com/v8/finance/chart/2330.TW`
- 注意：非正式 API，可能變更

### 14.3 推薦的 Chart.js 圖表類型

- 餅圖（doughnut）：營收結構
- 折線圖（line）：月營收趨勢
- 長條圖（bar）：同業比較

### 14.4 用到的 Claude SKILL

| SKILL | 用途 | 何時用 |
|-------|------|--------|
| frontend-design | 網站視覺設計 | Phase 1, 5 |
| skill-creator | 建立 stock-research SKILL | Phase 2 |
| xlsx | 把研究結果匯出 Excel | Phase 6（選做） |
| pdf | 讀取法說會 PDF | Phase 6（選做） |

### 14.5 下次與 Claude 對話時的開頭建議

當你想推進這個專案時，可以這樣開頭：

```
我正在做 PROJECT_PLAN.md 描述的台股研究系統。
目前進度：Phase X 第 Y 個 to-do。
我現在想做：[具體任務]。
```

把 PROJECT_PLAN.md 貼給 Claude 或附上連結，Claude 就能立刻接續下去。

---

## 結語

這份文件是你的 single source of truth。每次開工前先看一眼進度條，每完成一件事就劃掉一個 checkbox。當你迷失在細節裡，回來看第 0 章 TL;DR；當你想知道「現在該做什麼」，看第 9 章 To-Do List；當你想評估還剩多遠，看第 8 章 Roadmap。

**開工前最後三個提醒**：

1. 不要追求一次到位。MVP 第一週就要有東西能跑，再慢慢加。
2. 三檔練習股票（台積電、日月光投控、山太士）是你的試金石——每個 Phase 都拿它們驗收。
3. SKILL 是核心生產力，網站只是介面。SKILL 做得好，未來幾年都能用。
