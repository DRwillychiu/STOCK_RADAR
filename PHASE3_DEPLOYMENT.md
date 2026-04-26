# Phase 3 部署指南

> 把 Phase 1+2 的成果接上自動化引擎。每天早上 07:00 自動更新硬資料。

---

## 心智模型：兩條軌道

把 Phase 3 想成你既有籌碼專案的進階版，但有個重要差異：

**你的籌碼專案**：每天抓資料 → 直接覆蓋舊檔 → push
**Stock Radar**：每天抓資料 → **合併進舊檔（保留 Claude 寫的洞察）** → push

這個合併邏輯在 `scripts/update_watchlist.py` 的 `merge_into_existing()` 函數。記住：

| 欄位 | 誰負責 | 排程會動嗎？ |
|------|--------|--------------|
| `price.*` | 排程 | ✅ 每天替換 |
| `revenueStructure.quarterlyTrend` | 排程 | ✅ 季度更新 |
| `dataVerification` | 排程 | ✅ 每天重跑 |
| `lastUpdated` | 排程 | ✅ 每天更新 |
| `oneLineDef` | Claude (SKILL) | ❌ 絕不動 |
| `executiveSummary` | Claude (SKILL) | ❌ 絕不動 |
| `transformation` | Claude (SKILL) | ❌ 絕不動 |
| `majorCustomers` | Claude (SKILL) | ❌ 絕不動 |
| `peerComparison` | Claude (SKILL) | ❌ 絕不動 |
| `earningsCallHighlights` | Claude (SKILL) | ❌ 絕不動 |
| `recentNews` | Claude (SKILL) | ❌ 絕不動 |
| `warnings` | Claude (SKILL) | ❌ 絕不動 |

---

## 部署 Step-by-Step

### Step 1：本機測試 update_watchlist.py（5 分鐘）

確保腳本能正確運作再上 GitHub。

```bash
cd stock-radar

# 設定 FinMind token（從 https://finmindtrade.com 取得）
export FINMIND_TOKEN="你的token"

# 1. 先 dry-run 看看不會壞
python3 scripts/update_watchlist.py --dry-run --force

# 預期輸出：
# 🚀 開始更新 3 檔股票...
# 📡 2330 ... ✓ DRY-RUN (status=green, errors=0)
# 📡 3711 ... ✓ DRY-RUN (status=green, errors=0)
# 📡 3595 ... ✓ DRY-RUN (status=yellow, errors=0)  # 興櫃單源
# ✅ 完成：3/3 成功
```

**遇到錯誤時的判讀**：
- `errors=0` 但 status=yellow → 正常，表示某資料源缺失但合理（如興櫃）
- `errors > 0` → 看訊息判斷是 token 問題、網路問題還是 API 改版
- 全部 `errors > 0` → 通常是 token 沒設或 FinMind 服務異常

### Step 2：實際寫入測試（2 分鐘）

確認 dry-run 通過後，實際寫入：

```bash
python3 scripts/update_watchlist.py --force

# 看一下 git diff，確認哪些欄位變動了
git diff data/stocks/2330.json
```

**驗收重點**：`git diff` 應該**只**顯示 `price`、`lastUpdated`、`dataVerification` 這幾個區塊有變動。`executiveSummary`、`transformation` 等欄位**絕對不能**動。如果動了，就是 `merge_into_existing()` 邏輯有問題，先別 commit。

### Step 3：設定 GitHub Secrets（3 分鐘）

讓 GitHub Actions 拿得到 FinMind token：

1. 在 GitHub repo 頁面：**Settings** → **Secrets and variables** → **Actions**
2. 點 **New repository secret**
3. Name: `FINMIND_TOKEN`，Value: 貼上你的 token
4. 點 **Add secret**

⚠️ 即使是 public repo，secrets 也不會被洩漏到日誌或 fork。

### Step 4：Push workflow 並手動觸發測試（5 分鐘）

```bash
# 確認 workflow 檔案在
ls .github/workflows/daily_update.yml

# 推上去
git add .
git commit -m "Phase 3: GitHub Actions automation"
git push
```

接著到 GitHub repo：

1. 點上方 **Actions** tab
2. 左側清單選 **Daily Stock Data Update**
3. 右側點 **Run workflow** → 把 `force` 設 `true`、`dry_run` 設 `true`
4. 點綠色 **Run workflow** 按鈕
5. 等 30 秒，重新整理頁面，會看到一筆執行記錄

點進去看執行 log，重點看：
- ✅ "Set up Python" 通過
- ✅ "Run update script" 顯示三檔都成功
- ✅ "Commit and push changes" 應該顯示「跳過 commit」（因為 dry-run）

### Step 5：實際上線執行一次（5 分鐘）

dry-run 通過後，真的跑一次：

1. 再次手動觸發，這次 `dry_run` 設 `false`
2. 看 "Commit and push changes" step 應該成功 commit 並 push 回 main
3. 回到 repo 主頁，會看到剛才 GitHub Actions 機器人的 commit
4. 開你的 GitHub Pages 網站，watchlist 卡片的 lastUpdated 應該是最新時間

### Step 6：等明天早上看排程是否運作（隔天驗證）

不用做任何事，只要等。隔天早上 07:00 後（記得 cron 可能 delay 30 分鐘）：

1. 到 Actions 頁面看是否有自動執行記錄
2. 看是否有 commit
3. 開網站看資料是否更新

連續觀察 5 天，都正常就算 Phase 3 達標。

---

## 驗收清單

- [ ] 本機 `--dry-run --force` 跑成功，3 檔股票都顯示 ✓
- [ ] 本機 `--force` 跑成功，git diff 只動硬資料欄位
- [ ] GitHub Secrets 已設 `FINMIND_TOKEN`
- [ ] 手動觸發 workflow，執行成功
- [ ] Commit 由 `github-actions[bot]` 產生
- [ ] 網站 lastUpdated 時間有更新
- [ ] 隔天 07:00 排程自動執行成功（連續 5 天）

---

## 常見問題

### Q1：執行成功但 git diff 顯示沒變動？
排程用 Yahoo Finance 的即時報價，但盤後或假日抓不到變動的資料。檢查：
- 是不是非交易時段（盤前、盤後、休市日）跑的
- `lastUpdated` 應該至少有變動

### Q2：3595 山太士一直 yellow status？
正常。興櫃股 Yahoo Finance 與 FinMind 的覆蓋度本來就低，黃燈是常態。SKILL.md 已對興櫃有特別處理規範。

### Q3：workflow 跑了但網站沒更新？
GitHub Pages 部署有延遲（1-2 分鐘）。檢查：
- Actions 那邊 commit 是否成功
- Pages 設定是否還是 `main` branch
- 強制重新整理瀏覽器（Cmd+Shift+R）

### Q4：FinMind 額度爆了怎麼辦？
免費版 600 次/小時。3 檔股票 × ~6 個 dataset = 18 次/天，理論上完全夠。如果爆，看是不是有死循環或重試太多。考慮：
- 升級 FinMind 訂閱
- 或者讓排程改成每 12 小時跑一次（修改 cron）

### Q5：cron 到時間沒跑？
GitHub Actions 的 scheduled workflow **不保證準時**：
- 高峰時段（00:00 UTC 整點）可能延遲 30 分鐘以上
- 連續多次失敗的 workflow 會被自動停用
- repo 60 天無活動，scheduled workflow 會被停用

解決：把 cron 從 `0 23 * * *` 改成不那麼整點的 `15 23 * * *`，避開高峰。

### Q6：想加新股票到 watchlist？
兩種方式：

**方式 A（推薦）**：跟 Claude 說「研究 [股號]」，SKILL 會：
1. 產出 `data/stocks/{id}.json`（含完整軟洞察）
2. 給你 `data/watchlist.json` 的更新 patch

**方式 B（純手動）**：手動編輯 `data/watchlist.json`，加一筆 stock 進去。隔天排程會自動產出該檔的硬資料骨架，但 `executiveSummary` 等欄位會是空的，需要再請 Claude 補。

---

## 進入 Phase 4 前的提醒

Phase 3 完成後，Watchlist 內的股票會每天自動更新。
但**老闆問了 Watchlist 外的股票時，網站還是只能顯示「請用 SKILL 研究」**。

Phase 4 會補上「即時查詢任意股票」的能力——這時 client-side 的 JS 會直接打 FinMind 公開 endpoint，不用排程預先抓。

下次找我繼續：

```
Phase 3 已穩定運行 X 天。開始 Phase 4 — 即時查詢功能。
```
