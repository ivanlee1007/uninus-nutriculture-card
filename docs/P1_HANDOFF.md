# P1 接手說明

## 交付邊界

- 伴隨卡片儲存庫：`uninus-nutriculture-card`，版本 `0.1.0-alpha.1`。
- 正式使用檔：根目錄 `uninus-nutriculture-card.js`，無打包／安裝／CDN 步驟。
- 僅修改本儲存庫；未修改兄弟整合 `uninus-nutriculture`，未修改控制者 `docs/DEVELOPMENT_PLAN.md`。
- 未 commit、push、release、部署、讀取憑證或連接線上 HA。

## 對接契約與選擇

本卡依賴凍結的 `schema_version: 1`、`mode: shadow`、三個 `source_entities`、最多十項的 `parameter_entities` 與三種 status state。Number 的實際 metadata 是輸入範圍／精度／單位唯一依據；沒有猜 ID 或呼叫自訂服務。後端只發布健康且可用的實際映射與 metadata；停用、刪除、缺少 state、unavailable、unknown、非有限數或非數字 state 的目標應刻意省略，卡片不可猜補 ID。此澄清不更改凍結契約，也不代表整合 P1 已通過全部獨立審查。

`invalid` 表示來源無效，不是 schema 不相容；可讓使用者修正仍健康的 Number，但絕不顯示灌溉許可。未知 state／缺失 status／active mode 全部鎖定。即使後端錯誤傳送 `ready_for_irrigation: true`，卡片永遠保留「尚未提供灌溉許可」。

跨欄位成組更新留至 P3，UI 明確為單項儲存。若後端拒絕暫時相衝突的上下限，會保留該列草稿和錯誤；不應為本卡新增不安全的繞過路徑。

## 生命週期實作

卡片只建立一次 DOM；telemetry 更新只 patch 文字、metadata、按鈕 gate。dirty 輸入不回填，保留游標和節點。Entity 改變清除草稿；映射改變清除該列。每次 setConfig／disconnect 失效舊世代，請求捕捉目標與數值。跨世代完成只能釋放對應 transport lock，不能改寫新草稿／訊息。未解決 Promise 的 Number 目標鎖在同一實例內跨重新掛載保留；不同卡片實例之間不提供交易鎖。

視覺編輯器為無依賴原生 HTML select／input／checkbox，透過 HA `getConfigElement()` 與 bubbling/composed `config-changed` 介面運作，保留未知鍵；不是依賴私有 HA picker API 的複製品。狀態 select 列出 sensor；真正相容性在卡片執行時 fail-closed 驗證。

## 已驗證／未驗證

- Node 18.6.0 真實執行語法與五個 prototype 單元探測。
- Playwright 1.56.0 驅動已安裝 Chromium 156.0.8078.4，測試根目錄 shipped JS，不是另一個 build。
- 正式最終命令與測試數，以 `docs/TESTING.md` 與 `docs/evidence/final-package-gate/result.json` 為準。
- 原始 RED/GREEN、精確 source/test 快照、錯誤嘗試與最終 screenshot／geometry 均保留，沒有將已綠的補充測試冒稱 RED。
- CI workflow 已加入；尚未遠端執行。未驗證真實 HA 宿主的完整新增卡片流程、HA 權限與後端 service 實作、HACS 安裝或設備行為。

## 控制者後續

1. 獨立檢視候選檔與證據；需要時重跑測試，使用新的 evidence 目錄避免覆寫原始記錄。
2. 與兄弟後端確認 Number 映射／metadata 即可，不要求後端改動服務契約。
3. roadmap／milestone／GitHub 發布由控制者處理。本交付不代表正式發行或線上驗收。
