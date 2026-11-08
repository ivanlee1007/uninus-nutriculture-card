> 現行來源：P5b同槽pH／EC／液位歷史已完成正式來源交付（Backend `53e4f0b5dceb2cbd8c76bcef0470636d37868e41`、Card `863406040b2537f57001caa0d59c56f16af97a67`；精確CI `42476705488`／`42476693050` 已核驗）。P5c重要UI已完成隔離整合與獨立SPEC／品質安全兩審；來源出版與本提交hosted CI分別按實際核驗結果為準，不冒用舊批准。最新順序：重要UI → 另行確認測試機與致動範圍後實機測試 → 其餘P5。完整P5仍保留，未部署、HACS、tag或release；P3／P4／P5a／P5b結案修補額度不重置。


> 導航優先序：FUNCTIONAL_PARITY_REVIEW.md是舊commit的歷史F/D盤點，不代表目前沒有控制能力或所有D/R仍未決；不改寫其原文。P3C_FLOW_CONTRACT.md頂部提案語句屬來源歷史，現行以其§7已採納補充及本輪交付狀態為準，不再次凍結或重審。
# UNiNUS Nutriculture / 養液控制

## 目前開發狀態與完整目標

**P1–P3、P4a／P4b／P4c與P5a首片均已完成正式軟體來源、兩審、出版等價、精確HEAD CI及遠端交付核驗；完整P5、實機與HACS未完成。**

P3a 工程來源已交付，兩審與功能來源 CI 已完成，見 [P3A_PUBLICATION.md](docs/P3A_PUBLICATION.md)。本倉 P3b 加酸、獨立攪拌與 S4/schema4 已接通唯一後端並完成獨立規格及品質兩審；已審來源的 295 項 native 假硬體測試不代表真 HA／HACS／實機驗收。P3c 四階段可編順序／合法重疊／相對延遲與條件／星期及七日有效流程預覽已接通並完成兩審，P3軟體已交付而實機範圍分開；本文件不更新或重述遠端Issue即時狀態。P3b 來源交付不必等待完整 P3。P3b 遠端 CI 只以最終 commit 的實際 Actions 為準，不以本機 gate 代替；沒有內建 scheduler 或獨立 stage_link，未建立 tag/release 或部署。

**P3a 加養工程來源已推送，獨立規格／品質與功能來源的遠端 CI 均通過；未建立正式發行或部署實機。** 詳見 [P3A_PUBLICATION.md](docs/P3A_PUBLICATION.md)。

- 本機已接通原生 Options、整組參數／星期 CAS、schema3 Card，以及必要循環→加養脈衝→中點停泵→混合→新樣本穩定確認。設定保存不致動；原生 Switch 與外部 `start_flow` 共用後端。
- 隔離原生回歸、實際 Card 的設定與加養跨層已執行；都是假硬體，不是原 HA／HACS／實機驗收。精確來源與剩餘關卡記錄在後端工作樹 `docs/P3A_LOCAL_CHECKPOINT.json` 與 `docs/P3A_REVIEW_CANDIDATE.md`（P3a 來源交付範圍以 P3A_PUBLICATION.md 為準）。
- **P3b 加酸與獨立攪拌已接通；P3c 四階段可編順序／合法重疊／相對延遲與條件／星期及七日真正預覽亦已提供。** P3a 只是開發順序，不代表整個 P3，也不能把核心編排延至 P5。
- P4a配方已交付；P4b品質/完成/許可已實作並兩審及本機隔離驗證。舊S1–S5 `ready_for_irrigation` 固定false，新quality_v1與唯讀permit有效時可True；P4c通知/外部結果軟體來源與exact-HEAD hosted CI／產物核驗已正式交付。沒有內建排程器、獨立 stage_link 或瀏覽器關泵計時器。
- 已凍結的工程策略不再反覆要求使用者逐項決定；實際設備保護、最低液位與來源採樣能力仍由每槽 commissioning 明確確認。

目標對齊與有限後續順序見[GOAL_ALIGNMENT.md](docs/GOAL_ALIGNMENT.md)。下方 P2 段落是已發布基線的歷史範圍，不限制本倉 P3a／P3b 已提供的功能；現況以上方交付狀態為準。


## 已發布 P2 基線：隔離測試入口與限制（歷史範圍）

**P2補水候選已通過獨立SPEC與品質／安全審查；未部署原HA，不應直接接管實機。**完整結果與交付界線見[P2_ACCEPTANCE.md](docs/P2_ACCEPTANCE.md)。

- 後端原生Options明選已註冊補水輸出、commissioning確認、回饋期限及星期；保存/取消不致動。
- 先允許總開關與補水子開關，再用原生整輪Switch或`uninus_nutriculture.start_flow`請求一次補水；ON不會自行打開其他Enable。
- 新版Card選擇後端實際的**schema2控制狀態Sensor**，即可看見總/補水/整輪、急停/復歸；舊schema1監測Sensor仍無控制按鈕。不要使用來源pH/EC/液位Sensor作入口或猜測Entity ID。
- 高水位、正常停止、過期/無效來源、逾時及急停交由後端處理；未確認OFF不顯示假成功。運行中重複ON不重啟，重啟HA不續藥。
- 人類操作預設僅管理員；原生automation可使用內部Context。P2只有補水，養/酸/獨立混合不可啟動，也沒有流程編排UI或內建排程。
- Commissioning勾選不是韌體/斷線保護的軟體證明；HA當機/通訊失效時，一般Switch不保證會自停。只能識別已知Registry/平台uniqueId綁定，不能推測所有實體別名；部署前需另行確認設備端保護。
- 本機已驗證：backend151項、Card Node9項/真Chromium23項及shipped UI→真隔離HA handler→SwitchEntity假硬體。這不是原HA前台宿主、HACS安裝或物理驗收；最新CI只以對應commit的Actions為準。



**0.2.0-alpha.1 · P1監測相容＋P2受控補水候選**

獨立、無執行期依賴的 Home Assistant Lovelace 卡片。發行檔只有 `uninus-nutriculture-card.js`；不載入 CDN、不保存權杖、不使用 localStorage。

> schema1維持影子監測；schema2透過原生安全入口操作P2補水。**獨立審查已通過，實機／HACS尚未驗收；兩模式都不提供灌溉許可。**
> `within_range` 只表示監測讀值在範圍內，絕不代表可灌溉；legacy ready_for_irrigation不是許可欄位，即使錯傳true仍拒絕；新quality_entity面板獨立顯示後端permit.granted。

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
   url: /local/uninus-nutriculture-card.js?v=0.2.0-alpha.1
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

本卡只使用狀態中的明確映射，**不猜測 Number ID**。來源讀值來自 `hass.states`；`parameters` 只供無法取得 Number 時的唯讀參考，不能授權儲存。Number 缺失、不在 `number.*`、值無效或 metadata 無效，該列禁止儲存。只接受合法的 schema1/shadow 或 schema2/3/4/5 control 狀態；schema2 的 `flow_state` 還必須與 Entity state 一致，其他契約或狀態缺失／未知時全列禁止儲存。來源無效但狀態契約仍合法時，可調整健康的 Number 參數；這不是直接設備操作。

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

P1/v2參數編輯的寫入路徑（控制操作另見P2段落）：

```javascript
hass.callService('number', 'set_value', {
  entity_id: '<parameter_entities 對應的實際 number>',
  value: /* 通過 min/max/step 檢查的有限數值 */
});
```

schema1不顯示控制操作；schema2另提供總/補水/整輪Switch與急停/復歸，僅呼叫後端映射的switch.turn_on/turn_off及button.press，不直接操作實體泵或瀏覽器計時。v1/v2 每次單項儲存獨立；schema3 加養及 schema4 酸／獨立混合使用整組 Apply/Cancel 與 CAS，後端跨欄位驗證與權限仍是最終權威。服務拒絕保留草稿及錯誤。服務成功僅顯示已送出，顯示值以 Number Entity 讀回為準，不捏造成功讀回。

切換狀態 Entity 會清除舊草稿；Number 映射改變亦清除該列草稿並提示重新輸入。每個請求擷取當時 Entity／目標／值與世代，舊成功或失敗不會改寫新的草稿或訊息。未完成的同一目標請求，在同一張卡片重新設定或移除再掛載後仍保持寫入鎖，直到原 Promise 結束。已送出的後端呼叫無法由前端取消或回滾。

## 離線模擬與測試

直接以瀏覽器開啟 `demo/index.html`，或在此目錄執行 `npm run demo` 後開啟 `http://127.0.0.1:8765/demo/`。頁面醒目標示 **模擬資料／非即時系統**，儲存只改變頁面記憶體。沒有 HA 連線或設備操作。

測試步驟、TDD 原始證據與範圍限制見 [docs/TESTING.md](docs/TESTING.md)；後端對接與接手資訊見 [docs/P1_HANDOFF.md](docs/P1_HANDOFF.md)。

## 分期狀態

- P1–P3軟體已交付：schema2補水、schema3加養/群組設定、schema4酸/獨立mix與schema5有限編排均有來源/兩審/對應CI；物理commissioning及HACS另列未驗。
- P3（軟體已交付）：四階段可配置順序/重疊/相對延遲與條件、每階段七日複選；最小可排序階段列＋開始條件＋並行組＋預覽、加藥/混合/資源仲裁、成組原子參數與版本衝突處理。
- P4：配方、外部action/結果互通與通知、完成/品質/灌溉許可介面。何時啟動整輪由外部排程/HA automation決定；不建排程器、不匯入排程、不管理外部腳本/旁支。星期只判允許，不自動產生工作；混合/脈衝/安全期限仍屬後端。
- P5a四階段視覺關係入口／手機鍵盤首片已交付；完整P5的後續進階編輯、完整手機鍵盤體驗、歷史／診斷與完整多槽產品仍保留；不是把核心可配置流程延到P5。
- 正式發行、HACS 遠端安裝、真實 HA 與實體設備驗收皆未執行；GitHub 程式推送不代表這些步驟已完成。

研究依據見 [流程編排/UI、星期與外部啟動研究](docs/FLOW_DESIGN_RESEARCH.md)。已確認取消獨立stage_link，以編排決定接續；R03採各階段實際開始前查星期，新增原生整輪運行Switch。P3c 有限圖語意已凍結；R04 已凍結，P3c 可編流程已提供。

完整分階段路線圖見 [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md)；[總/子開關與流程組合](docs/CONTROL_SWITCHES.md) 及 [原系統功能差異盤點](docs/FUNCTIONAL_PARITY_REVIEW.md) 依分期實作；P2 已發布；P3a 工程來源已交付並通過兩審／功能來源 CI，P3c來源/兩審/出版等價/exactHEAD CI及軟體named驗收已完成；P4a來源/兩審/出版等價/exact-commit CI已完成；P4b已實作並兩審、本機隔離驗證，來源與exact-HEAD hosted已驗證，完整P4–P5與實機仍待完成；schema1監測介面不因此產生控制操作。配套後端為 [uninus-nutriculture](https://github.com/ivanlee1007/uninus-nutriculture)。遠端 CI 結果以 Actions 的對應 commit 為準。

## 共同開發規範

[DEVELOPMENT_SPEC.md](docs/DEVELOPMENT_SPEC.md)統整已確認結論、前後端責任、開關/流程/星期/外部排程邊界與決策／工程待辦狀態；既有版本化控制已交付；P1/shadow相容介面本身仍不控制設備。

控制目標與前台可調安全參數已補入[CONTROL_PARAMETERS.md](docs/CONTROL_PARAMETERS.md)：平均目標停止投藥、危險門檻預設採原HA且可調；D01已定，不阻擋繼續開發。

## P3c 現行流程與原生操作

- 四列必須各含一次 `refill`、`nutrient`、`acid`、`mix`。可改順序；第一列為 `flow_start`，其餘可選 `flow_start`、`after_previous_started` 或 `after_previous_finished`，延遲相對於該錨點，不是任意腳本或排程時間。合法 overlap 仍受後端輸出資源、最低液位、採樣及安全 gate 約束，不保證同時致動。
- 必要加藥循環與獨立 mix 不同：停用獨立 mix 不會解除加藥必要循環。共用 circulation 由後端仲裁；不能以 Card 或其他入口繞過 ownership。
- 有限 condition 僅 `level` / `ph` / `ec` 的 `gte` / `lte` 有限數值，或 `none`；不是 template。液位用 m（0–10）、pH 0–14、EC 用 mS/cm（0–20）。每列等待期限與整輪期限有界。
- 到「設定 → 裝置與服務 → UNiNUS Nutriculture → 該槽的設定／選項」，勾選 **Open flow plan editor (no settings saved)**（`flow_plan`），開啟 **Flow plan / 流程計畫**。這是原生 selector 表單，不必貼 JSON；進入編輯器不會保存同頁其他設定。
- 每列有 stage、start rule、delay seconds、wait timeout seconds、condition source/operator/value 及 weekdays；`run_timeout_seconds` 為整輪期限。用 **Save / seven-day Preview / Cancel / move row up or down** 的 `row_0_down` / `row_1_up` 等動作調序；規則隨列保留，調序後第一列仍須 `flow_start`。
- `action=preview` 讀草稿，列出七日有效流程；`save` 才以版本衝突檢查原子保存，作用於下一輪，不啟動設備；`cancel` 不保存。其他頁面已改設定時須重開並協調，不能覆蓋新版本。Card 同樣提供階段列、上下移動、星期、Preview／套用／取消；參數群與流程草稿為分開 namespace。
- 每階段真正 admission 前依 **HA 設定時區** 的當地星期重查；跨午夜不沿用整輪開始日。星期是允許 gate，不會自行排程、補跑或啟動。外部 automation／`uninus_nutriculture.start_flow` 與原生整輪 Switch 共用後端；Enable 開關不是 start。
- Preview 使用相同有限依賴／略過與資源模型，反映停用、星期、條件、等待和依賴，不再只是單一 eligible 清單。未來感測、實際加藥／補水完成時刻及跨日 admission 可能未知；七日預覽不是確切時間表、成功保證或灌溉許可。無致動也不建立運行任務。
- P3c交付時永久 native suite 為 335；P4a交付時 suite 為378；R4 full 339 包含四項外加 QA probes，不屬正常 repo，不能要求乾淨 CI 收集 339。源碼兩審不取代 publication-equivalence 審核或 exact-commit hosted CI。內嵌版本未升正式發行版本；不為顯示美觀修改 bundle/hash/version metadata。

## P4a 本輪交付範圍（已實作並兩審；非完整P4/發布宣稱）

- [參數配方契約](docs/P4A_RECIPE_CONTRACT.md)
- 原生Options與Card共用entry-owned UUID配方庫：建立/編輯/選擇/刪除二確認，Save/Cancel不改運行參數，Apply原子更新既有10參數且零致動。不能變更commissioning、Enable、fault、流程、星期或裝置保護。
- P4a切片來源歷史（非現行整案範圍）：只交參數配方；P4b品質/完成/許可已實作並兩審；完整配方擴充及P4c外部結果/通知仍待後續，不標全P4完成；舊S1–S5 ready_for_irrigation固定false；新quality_v1／唯讀permit有效時可True。
- 不新建通用測試框架，不重做已交付P3，不用物理驗收待辦阻擋隔離軟體開發。每個主要行為真RED→GREEN、一次整合SPEC→品質；P4a最多兩輪具體repair，P3的4/4歷史不重置。

## P4b 現行操作與交付界線

見[P4b原生／Card操作與唯一權威](docs/P4B_OPERATION.md)。P4b source、兩審、出版等價、push與exact-HEAD hosted CI及下載產物核對均已完成；仍不等同HACS或實機驗收。P4c正式來源交付、出版等價、push、新exact-HEAD hosted CI及遠端／下載產物核驗均已完成；P5進階體驗、兩槽皆commissioned與shared-output實機驗收仍pending；本文件不寫入遠端Issue，完整P5仍保留。修復預算4/4不重置。

## P4c 軟體來源已正式交付；實機／HACS分開

- 以 [P4C_RESULT_NOTIFICATION_CONTRACT.md](docs/P4C_RESULT_NOTIFICATION_CONTRACT.md) §8及 [P4C_API_SCHEMA.json](docs/P4C_API_SCHEMA.json)優先：既有整輪trigger→穩定result_v1投影／事件；nativeOptions與Card共用私有通知權威、選native provider／事件／cooldown；default disabled。無scheduler、任意service runner或直接灌溉。
- P4c R4來源兩審、本機完整gate、出版等價、正式Card commit pin、新exact-HEAD hosted CI及遠端／下載產物核驗均已完成。P4c 4/4、P3 5/5結案，不重開產品修復。通知失敗／ACK不改安全OFF、fault、quality或permit；Core STOP與普通flow Stop分辨；明確private reconcile，不自動entry reload。
- P5a四階段視覺入口／手機鍵盤首片已交付；P5後續進階視覺與完整手機鍵盤、完整歷史／診斷、兩槽各自全流程／跨槽共output commissioning、HACS與實機仍保留；P4c必要idle低pH／高EC唯讀告警G1不延後。原F/D及歷史失敗不回寫。

## P5a 視覺工作台與操作入口

四階段關係按鈕可進入既有規則欄位，保留調序／重疊／延遲／有限條件／星期→七日後端Preview→明確套用→native讀回／重開路徑；見[P5a視覺工作台操作說明](docs/P5A_VISUAL_WORKFLOW.md)。真隔離Core19 requests整合與修正後獨立SPEC→品質兩審已完成；既有P5a基線精確HEAD hosted CI與遠端交付核驗亦已完成；後續新候選另驗自身CI，不宣稱完整P5或實機完成。草稿示意／Preview不保證物理可行性或arrival；不增加schema、scheduler、raw IO或現場控制。

## P5b：同槽 pH／EC／液位歷史

選擇槽的狀態Entity後，展開「歷史」並選擇1／6／24小時；來源自動沿用後端`source_entities`，不另填感測ID。支援分圖、觸控／鍵盤選點及資料表。正常密集資料採保留首尾、分段極值與缺口的有界代表抽樣；無法安全表示的指標獨立提示，不清空其他指標。原始／正規化／顯示筆數均明示。

無可讀紀錄可能是Recorder保留／排除或READ權限過濾，不代表健康或確定沒有Recorder；歷史不影響控制、品質或灌溉許可。詳見[P5b操作與限制](docs/P5B_HISTORY_CONTRACT.md)。本片不等於完整P5、HACS實裝或實機驗收；未部署／tag／release。


## P5c重要UI與後續順序（隔離整合與兩審完成）

1. **重要UI已實作並完成隔離驗證／兩審**：四階段即時運行視覺、真資源等待／略過／停止確認、HA觀察輸出、Recorder的stage／output／permit與停止原因時間軸；補齊新增畫面的手機／鍵盤與切槽一致性。沿用後端唯一權威，不把草稿當運行計畫、不把輸出狀態當物理到達、不把歷史許可當現行授權。
2. **再進行實機測試**：完成必要整合與獨立SPEC→品質後，先確認指定測試機、硬體、可連線／可致動範圍與停止條件。此排序不解除原站不連線、不讀取現場憑證、不部署的現行界線。
3. **最後補其餘P5**：選配水溫／通訊診斷、完整兩槽commissioned與共享輸出矩陣、完整HA宿主／HACS、文件／備份還原及另授發行準備；不是取消這些需求。

P5a編輯入口與P5b感測歷史已交付，不重做。P5c契約見[P5C_RUNTIME_TRACE_CONTRACT.md](docs/P5C_RUNTIME_TRACE_CONTRACT.md)。
