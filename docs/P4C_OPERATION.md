> 現行來源狀態（2026-11-08）：P1–P3、P4a／P4b／P4c軟體來源及對應精確HEAD hosted CI已交付。本版P5a四階段視覺工作台／手機鍵盤已實作，修正後完整SPEC與品質兩審均批准，Q-01已關閉；Preview／Apply／Options／Store與fresh SDK隔離驗收已通過。P5a joint-review repair 1/1已用，P4c 4/4及P3 5/5結案不重置。本提交仍須以其精確HEAD hosted CI與遠端產物完成來源交付核驗；不得將本機或來源審查當成hosted CI／完整P5／實機／HACS驗收。完整P5十二項後續範圍保留，未tag／release／部署。

# P4c Card 操作與驗證邊界

狀態：現行狀態（2026-11-07）：P4b正式交付與exact-HEAD hosted CI／產物核對已完成。P4c R4來源已通過SPEC及獨立品質兩審，本機完整553 cases／82 modules（144／116／137／156）與真Core／shipped Card join已完成；目前僅準備出版successor，尚未push，未驗新exact-HEAD hosted CI。P4c初始2輪＋explicit Options卸載1輪＋explicit quota1輪＝4/4；P3歷史4輪＋explicit mix1輪＝5/5，皆結案、不重置。完整P4／P5、實機commissioning及HACS實裝未完成，未tag／release／部署。內嵌0.2.0保留既有封裝，不代表功能階段。 共同契約與schema維持原凍結版本。

## 使用

1. 在 Card 編輯器以原生 `ha-selector` 明確選擇 `result_entity`（sensor）；不由名稱、槽名或 Entity ID 前綴猜 config entry。可單獨配置結果入口，也可與既有狀態／品質入口並列。若同時配置狀態入口，其 entry 必須吻合。
2. 展開「本輪結果（唯讀）」：嚴格驗證獨立 `result_v1` attributes；優先 current_run，否則 last_result，皆空為 idle。unsupported、無效 DTO／state 不一致、離線明示未知／唯讀。保留最後 terminal；顯示四階段 phase/result/reason/time 與 run closure。accepted 表示「已受理」，completed 不授予 quality／permit；既有 quality_v1、S1–S5、recipe 解析未擴欄。
3. 人類 admin、原生連線／callWS、已宣告 `get_result_v1` 能力與 supported 結果齊備時，才可開私有通知管理。frontend 的 `is_active` 未提供不視為拒絕；明確 false、非 admin、system-generated 或無效 user ID 拒絕。原生後端 ACL 始終是權威。
4. 開面板只做私有 cache GET。provider 可為未選取、persistent_notification、notify_entity；NotifyEntity 僅私有 backend catalog 下拉，沒有任意收件者／service／template 輸入。勾選事件、設定 cooldown 60–86400 秒。初始為 disabled、provider/target null、events []、工程預設 300 秒。
5. Save 只送 PolicyInput：enabled/provider/events/cooldown_seconds/target_entity_id；server 產生 target_binding。以最後私有 GET 的實際 epoch/revision CAS，不能從 Entity revision 或 quality epoch 猜值。Save 回覆需 revision+1／完整 policy 一致，再做私有 GET 確認同 revision 與 policy 才顯示保存成功；不 optimistic 修改 sensor、fault 或 permit。取消不發請求、不寫入。
6. 「更新通知狀態」只呼叫 cache GET，查看 queued／handoff_returned／timeout／已讀。handoff_returned 只表示原生交接返回，**不是送達確認**；timeout 為**結果未知**，不能聲稱未寄出。
7. 「標為已讀（不復歸）」只針對本 entry／epoch 私有 ledger 事件，且回覆需確認指定事件已讀。沒有 dismiss、reset、重送或測試通知。
8. 「重新讀取通知設定」是明確私有 reconcile；只送 config_entry_id/expected_epoch。沒有自動 reconcile、reloadControlEntry、replay、scheduler 或控制輸出。indeterminate／Save transport 不確定會封鎖後續 Save；cache GET 不解除 client 的不確定鎖，明確 reconcile 回覆後才可恢復。

## 傳輸與生命週期

- 只使用 `hass.callWS` 的 `uninus_nutriculture/notification_v1/get|save|ack|reconcile`。不透過 call_service 傳通知資料；不提供服務名稱 fallback。HA callWS 自動分配 transport `id`；Card 不自行冒用／配置 websocket request ID。schema 的 id 由原生 transport envelope 補上。
- 私有 owner 與 quality owner 分離；綁 principal primitive（ID/admin/active/system-generated）、選定 Entity/entry/runtime epoch、connection/callWS、mounted 狀態及確切 operation identity。setter/render/每個 async settle 都重驗，而非保留 mutable user 物件當授權。
- principal/entry/epoch/transport/offline/reconnect/disconnect 改變會清 cache、draft、catalog 與 ledger DOM；舊 GET/SAVE/ACK/RECONCILE 不復活原 target。相同 entry 未 settled flight 持續鎖定直到真正 settle，不重送；舊 entry settle 不清新 entry operation。unauthorized 會 latch 並清私有資料。
- 沒有 browser 安全 timer、通知輪詢或自動 IO；Card 只是 display/API client，不控制底層、不自斷許可。文字皆經 textContent／DOM option 建立。

## 可重跑驗證

沿現有只讀 venv／Node／Chromium，不安裝套件：

```bash
PYTHONDONTWRITEBYTECODE=1 NODE='C:/Program Files/nodejs/node.exe' CHROMIUM_EXECUTABLE='C:/Users/ivanl/AppData/Local/ms-playwright/chromium-1248/chrome-win64/chrome.exe' 'D:/UNiNUS Projects/AI project/uninus-nutriculture-card/.venv/Scripts/python.exe' -m unittest discover -s tests -p p4c_browser.py -v
```

- 新測試為 shipped root JS + 真 Chromium + **fake private WS**，不是 native Core／Store／Options backend 整合。selector 以原生 value-changed 事件邊界操作，並未載入完整 HA frontend picker 實作。
- 16 個新 unittest；其中 structural malformed DTO 迴圈屬 parser 負例，不計額外 UI／wire cases。owner 測試遍歷四條 route 的晚回與多種 primitive/scope/transport 變更。
- 原 canonical unit 14、legacy browser 38、P4a browser 16、P4b browser 21 分開執行；原檔及斷言保持原始 bytes，沒有 expected-keyset 放寬。
- 外置原始證據：`C:/Users/ivanl/.hermes/cache/scratch/p4c-card-implementation`。每次 run 分開保存 source/test bytes、raw log、實際 child exit、hash，primary 有 screenshot／DOM／emitted payload。red01 為缺 editor selection 的行為 RED；red02 為未知保存仍可 Save／unauthorized 仍可 GET；red03 為未確認 ACK 卻顯示成功。green01/02 為 harness CustomEvent／collapsed innerText 修正前的失敗，未當產品 RED；green05 為 supported→unsupported 未清私有 cache 的實際產品失敗並已修。canonical01 保留兩個 P4b 失敗：新增 listener 在未配置 result 時碰到原 fixture 單 listener map；修為只有 result scope mounted 時訂閱，未改原 P4b 測試。

## 未驗與限制

- parent已另驗早期F0真Core／NativeStore／原生Options與shipped Card雙向主路徑；此次合流含後端新修及fresh持久化，仍需最終同版真join與兩審。完整HA frontend/network與現場仍未驗；未push／tag／release／deploy，未對真通知收件者送訊息。
- R4 source已完成native ACL／physical Store／Options／provider handoff與完整553 cases本機驗收；本文件早期Card-only結果不冒稱當時已覆蓋backend。新HEAD hosted CI仍未執行。
- screenshot 已由 Chromium 產生；本機 vision 工具因模型不支援而無法讀圖，未宣稱人工視覺簽核。可操作性另以 DOM、trusted keyboard、320/768/1200 controls geometry 斷言確認。
- provider 返回不保證收件、外部副作用無 exactly-once 保證；backend runtime ledger/replay/timeout 資源邊界依共同凍結契約，不由 Card 補做。
