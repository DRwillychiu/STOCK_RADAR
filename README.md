# Stock Radar 📡

> 個人化台股研究儀表板。三層架構：Claude SKILL 研究、GitHub Actions 排程、靜態網頁展示。

詳細專案規劃請見 [`PROJECT_PLAN.md`](./PROJECT_PLAN.md)。

---

## 專案進度

```
[▰▰▰▰▰▰▰▰▰▰] Phase 1: MVP                100%   ✅ 已完成
[▰▰▰▰▰▰▰▰▰▰] Phase 2: 研究 SKILL          100%   ✅ 已完成
[▱▱▱▱▱▱▱▱▱▱] Phase 3: 自動化資料層           0%
[▱▱▱▱▱▱▱▱▱▱] Phase 4: 即時查詢功能           0%
[▱▱▱▱▱▱▱▱▱▱] Phase 5: AI 整合與精煉          0%
[▱▱▱▱▱▱▱▱▱▱] Phase 6: 進階功能（選做）       0%
```

**最後更新**：2026-04-26
**當前重點**：SKILL 完成，準備進入 Phase 3 建立 GitHub Actions 自動化排程
**卡關**：無

### Phase 2 產出

- `skill/stock-research/SKILL.md` — Claude 的標準研究流程
- `skill/stock-research/scripts/` — FinMind / Yahoo / MOPS / 交叉驗證 (純標準庫)
- `skill/stock-research/templates/` — JSON Schema、筆記模板
- `skill/stock-research/reference/industry_taxonomy.json` — 產業分類對照

---

## 快速開始

### 本機預覽

```bash
# clone repo 後在根目錄執行
python3 -m http.server 8000
# 瀏覽器打開 http://localhost:8000
```

### 部署到 GitHub Pages

1. Push 到 GitHub repo
2. Settings → Pages → Source 選 `Deploy from a branch` → `main` / `(root)`
3. 等 1-2 分鐘，網址：`https://{你的帳號}.github.io/{repo-name}/`

---

## 目錄結構

```
stock-radar/
├── README.md              ← 本文件
├── PROJECT_PLAN.md        ← 完整專案規劃（必讀）
├── index.html             ← 首頁
├── stock.html             ← 個股詳情頁（吃 ?id=2330 參數）
├── about.html             ← 系統說明
├── assets/
│   ├── css/main.css       ← 主樣式（Editorial Trading Desk）
│   └── js/
│       ├── app.js         ← 主邏輯
│       └── search.js      ← 搜尋
├── data/
│   ├── watchlist.json     ← 追蹤清單
│   └── stocks/            ← 個股詳情 JSON
├── notes/                 ← 個人筆記 markdown
└── scripts/               ← Python 腳本（Phase 2-3）
```

---

## 練習案例

| 股號 | 公司 | 市場 | 用途 |
|------|------|------|------|
| 2330 | 台積電 | 上市 | 資料豐富的標準案例 |
| 3711 | 日月光投控 | 上櫃 | 上櫃半導體封測代表 |
| 3595 | 山太士 | 興櫃 | 興櫃妖股、轉型題材、異常處理測試 |

---

## 設計理念

**Editorial Trading Desk** — 結合金融終端機的資訊密度與編輯雜誌的精緻排版。

- 深色基底，避免長時間使用刺眼
- Serif 標題（Fraunces）營造編輯感
- 等寬字（JetBrains Mono）展示金融數據
- 漲跌不用紅綠（warm gold / terracotta），對色盲友善
- 微動畫：頁面進場 stagger fade、卡片 hover 浮起、品牌點脈動

---

## License

個人使用，不對外發佈。
