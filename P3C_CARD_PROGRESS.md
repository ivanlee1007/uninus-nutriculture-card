# P3c Card checkpoint

契約/wire SHA 已核對：6edd0bfde7c2405dcea691432536af425afd3e47522d7ab94e03477629c1d310 / 32fad886199a9c8bde3f2fc3366074260914ddb68d45c6b858f1532843fa576c。

已取得真 browser RED `test-results/p3c-red`：shipped bundle 四列 count 0 != 4。已接通四列、排序/星期原子 5-key payload、嚴格 S5、兩 writer namespace，`p3c-green-2` focused PASS；原 Node 12 PASS、browser 原33+新增1=34 PASS（p3c-node-1 / p3c-browser-1）。首輪 p3c-green-1 揭示新 fixture 既有 mix mon/tue 與測試期待不同，保留原失敗；只對新 p3c fixture 明確初始化 mix=[]，未改舊 fixtures/assertions。接續七日 preview/async 邊界與 demo 驗證。

## 初始開發交接（未自批准）

- 已實作 shipped 四列：up/down 保留 start_rule、下拉規則、整秒 delay/wait、level/ph/ec gte/lte 有限條件、七日 checkbox、global timeout。Apply / Cancel / Preview 分離。
- Plan 5-key CAS 保存排序＋星期；Preview 6-key payload 經 `hass.callWS({type:'call_service',domain:'uninus_nutriculture',service,service_data,return_response:true})` 取得原生服務 response，解析 `.response`，七日各一請求；不在 shipped bundle 計算安全 eligibility / finish。
- S5 exact30 roots＋四 HA metadata，兩 target 同 entry、closed phase/result/reason、四物理輸出、run_plan、plan 全結構與原 v4 group validator；v1–v4 原測試不改 assertion。
- Settings v5 7-key 不含 weekday；與 plan dirty 草稿獨立，衝突保留舊 revision。plan 成功須 response 嚴格驗證且當前同 entry/revision/全值讀回；不改 hass/entity。
- Cancel 零 call；pending transport lock 跨 remount 保留、晚 reject 不覆新 draft；Preview 有 draft epoch，Cancel 後舊 response 不入 UI。
- Demo 新 settings5 四列／七日結果，明示 memory-only / NOT native；未連外。截圖 `test-results/p3c-consumed-final/browser/p3c-v5-memory-only.png`。

### 驗證與 provenance

- 真 shipped browser RED：`test-results/p3c-red`，0 != 4；demo RED：`p3c-red-demo`，settings5 option 0 != 1。前後 source/test 完整 bytes、command、child rc、raw SHA 皆在各 result.json / snapshot。
- 最終 canonical：`test-results/p3c-canonical-final/result.json`，Node18.6 syntax PASS、parsed Node **13/13**（原12＋新增1）、Chromium156 browser **38/38**（原33＋新增5），無 skipped。重跑 `p3c-consumed-final` 同38 cases，不重複加總。
- 補充 consumed snapshot 包含 p3a/p3b/p3c fixtures 與 contract/wire，執行後全部 source hash 比對一致 `SNAPSHOT_MATCH=TRUE`；canonical 舊 runner 未列新 fixture，以此補齊。
- 首輪 p3c-green-1 fixture mon/tue 預設差異已明列；p3c-supplement-1 preview button/result 重複 selector ERROR 保留，修正 production data-preview-results，非把它冒稱 behavior RED。
- 最終 source SHA256 `4fd326a406531c601e490393d77e4ac1632a2e72cd1df9bc424aaa1909250e0f`。
- 最終 browser raw SHA256 `7714a49d9845ac4700a9d7c36ae91e2bde9cf411dd7da6d7089998b8d1e7e141`。
- RED raw SHA256 `2f3c33b053fb94aba6f3884286287244e417519860606d8688a2d8a89c894015`。
- 完整變更檔 SHA：`test-results/P3C_CARD_SHA256.json`。

### 父端必做／尚未宣稱

本階段只驗 frontend transport mock 與 memory demo，**不是 backend 整合 GREEN**。父端 join 必將這份 shipped bundle 原樣送出的 callWS payload 經 registered HA service/native Store，驗真七日 preview、安全 eligibility、兩 writer CAS、4-stage start/overlap/shared-circ/own runtime 投影。尚無實體 HA、憑證、硬體、遠端 CI、發布／部署。獨立 SPEC→品質 review 與父端 native join 尚待執行；Issue3 不可關閉。新增 v5 專屬 320px/table geometry、trusted typing連續性、多 Card native CAS等未全覆蓋，不能由舊v1–v4 geometry PASS外推。

### 可重用工作流（限 owned 目錄紀錄）

先核 contract/wire SHA → 寫 browser 可操作行為 assertion → p3c_run.py 以新目錄先存完整 source/fixtures 再啟動 child → 保留 RED → 實作 → canonical check.py＋補充全 inputs snapshot runner → parsed case count 核對且重跑不加總 → SHA/邊界交接。不要把 `.git` 缺失、module/import錯或 selector 歧義算作功能 RED；不要讀正在修改的 peer backend 當整合 fixture。

