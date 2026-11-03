# UNiNUS Nutriculture / 養液控制

> 最新控制定案（尚未實作）：取消獨立鏈結、各階段實際開始前查星期、新增原生整輪運行Switch並保留start_flow；見[CONTROL_DECISIONS.md](docs/CONTROL_DECISIONS.md)。P1仍僅影子監測。

**0.1.0-alpha.1 · P1 影子監測**

獨立、無執行期依賴的 Home Assistant Lovelace 卡片。發行檔只有 `uninus-nutriculture-card.js`；不載入 CDN、不保存權杖、不使用 localStorage。

> **影子監測、不控制設備、尚未提供灌溉許可。**
> `within_range` 只表示監測讀值在範圍內，絕不代表可灌溉；即使後端傳入 `ready_for_irrigation: true`，本卡也不顯示灌溉許可。

## 已實作

- pH、EC、液位三個來源 Entity 即時讀值；未知／無法使用時顯示 `—`。
- 三種 P1 狀態及原始穩定原因碼；缺少／不相容狀態與無法儲存的 Number 警告。
- 可收合的十項參數、實際 Number 的 min／max／step／unit。
- **明確按「儲存」才送出單項變更**，輸入、失焦、即時監測更新均不自動寫入。
- Home Assistant 卡片選擇器與原生 HTML 視覺編輯器：狀態 Entity、標題、顯示參數。編輯器保留未知設定鍵，不修改傳入的設定物件；取消由 HA 宿主處理。
- 保留輸入節點、焦點、游標與展開狀態；防止重複送出與跨 Entity 的過期回應污染。
- HA 主題變數、緊湊藍綠配色；已在真正 Chromium 測量 320／768／1200 px。

## 手動安裝

1. 將 `uninus-nutriculture-card.js` 複製至 HA `/config/www/`。
2. 在儀表板資源新增 **JavaScript Module**：

   ```yaml
   url: /local/uninus-nutriculture-card.js?v=0.1.0-alpha.1
   type: module
   ```

3. 重載瀏覽器，在新增卡片選擇 `UNiNUS Nutriculture / 養液控制`，或使用 YAML：

   ```yaml
   type: custom:uninus-nutriculture-card
   entity: sensor.your_actual_status
   title: UNiNUS Nutriculture
   show_parameters: true
   ```

`entity` 必填，必須是狀態 sensor 的實際 Entity ID，不是來源 pH／EC／液位 sensor。`title` 選填；`show_parameters` 預設為 `true`，設為 `false` 會移除參數區。

此儲存庫包含 HACS 前端卡片中繼資料，現已依使用者要求公開，仍為 alpha 專案；**尚未執行 HACS 安裝、正式發行或線上 HA 驗收**。Public 不代表已列入 HACS 預設清單，也不等於 HACS 安裝已驗證成功。

## 凍結的 P1 狀態契約

狀態 `.state`：`within_range`／`out_of_range`／`invalid`。必要屬性：

```yaml
schema_version: 1
mode: shadow
ready_for_irrigation: false
source_entities:
  ph: sensor.actual_ph
  ec: sensor.actual_ec
  level: sensor.actual_level
parameter_entities:
  ph_low: number.actual_ph_low
  # 其餘九項均映射至後端實際建立的 number Entity
parameters:
  ph_low: 5.4
reasons: []
```

本卡只使用狀態中的明確映射，**不猜測 Number ID**。來源讀值來自 `hass.states`；`parameters` 只供無法取得 Number 時的唯讀參考，不能授權儲存。Number 缺失、不在 `number.*`、值無效或 metadata 無效，該列禁止儲存。schema 非 1、mode 非 `shadow`、狀態缺失／未知時全列禁止儲存。來源無效但狀態契約仍為 `invalid` 時，可調整健康的 Number 參數；這不是設備操作。

| 參數 | 契約預設值 | 單位 |
| --- | ---: | --- |
| level_low | 2.25 | m |
| level_high | 2.4 | m |
| ph_low | 5.4 | — |
| ph_high | 5.8 | — |
| ec_low | 0.8 | mS/cm |
| ec_high | 0.9 | mS/cm |
| refill_timeout | 190 | min |
| ec_timeout | 90 | min |
| ph_timeout | 190 | min |
| mix_duration | 10 | min |

以上為契約說明，不是卡片自行建立或重設的值；輸入限制與顯示單位一律讀取實際 Number metadata。四個時間參數 P1 **僅儲存、不驅動控制**。

## 寫入與生命週期界線

唯一寫入路徑：

```javascript
hass.callService('number', 'set_value', {
  entity_id: '<parameter_entities 對應的實際 number>',
  value: /* 通過 min/max/step 檢查的有限數值 */
});
```

沒有自訂服務、啟停／泵浦／閥門／灌溉按鈕，也沒有任何設備控制路徑。每次儲存獨立，不保證上下限群組原子更新；後端的跨欄位驗證與權限仍是最終權威。服務拒絕保留草稿及錯誤。服務成功僅顯示已送出，顯示值以 Number Entity 讀回為準，不捏造成功讀回。

切換狀態 Entity 會清除舊草稿；Number 映射改變亦清除該列草稿並提示重新輸入。每個請求擷取當時 Entity／目標／值與世代，舊成功或失敗不會改寫新的草稿或訊息。未完成的同一目標請求，在同一張卡片重新設定或移除再掛載後仍保持寫入鎖，直到原 Promise 結束。已送出的後端呼叫無法由前端取消或回滾。

## 離線模擬與測試

直接以瀏覽器開啟 `demo/index.html`，或在此目錄執行 `npm run demo` 後開啟 `http://127.0.0.1:8765/demo/`。頁面醒目標示 **模擬資料／非即時系統**，儲存只改變頁面記憶體。沒有 HA 連線或設備操作。

測試步驟、TDD 原始證據與範圍限制見 [docs/TESTING.md](docs/TESTING.md)；後端對接與接手資訊見 [docs/P1_HANDOFF.md](docs/P1_HANDOFF.md)。

## 明確延期

- P2：總開關＋四子開關資料模型、統一gate、外部整輪服務契約、補水安全骨架；未支援階段不假啟用。
- P3：四階段可配置順序/重疊/相對延遲與條件、每階段七日複選；最小可排序階段列＋開始條件＋並行組＋預覽、加藥/混合/資源仲裁、成組原子參數與版本衝突處理。
- P4：配方、外部action/結果互通與通知、完成/品質/灌溉許可介面。何時啟動整輪由外部排程/HA automation決定；不建排程器、不匯入排程、不管理外部腳本/旁支。星期只判允許，不自動產生工作；混合/脈衝/安全期限仍屬後端。
- P5：進階視覺化編輯器、手機/鍵盤體驗、診斷/歷史與完整多槽產品；不是把核心可配置流程延到P5。
- 正式發行、HACS 遠端安裝、真實 HA 與實體設備驗收皆未執行；GitHub 程式推送不代表這些步驟已完成。

研究依據見 [流程編排/UI、星期與外部啟動研究](docs/FLOW_DESIGN_RESEARCH.md)。已確認取消獨立stage_link，以編排決定接續；R03採各階段實際開始前查星期，新增原生整輪運行Switch。R02/R04等細節仍待確認，以上尚未交付。

完整分階段路線圖見 [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md)；[總/子開關與流程組合](docs/CONTROL_SWITCHES.md) 及 [原系統功能差異盤點](docs/FUNCTIONAL_PARITY_REVIEW.md) 已納入後續規劃，尚未實作，不會使 P1 出現設備控制。配套後端為 [uninus-nutriculture](https://github.com/ivanlee1007/uninus-nutriculture)。遠端 CI 結果以 Actions 的對應 commit 為準。
