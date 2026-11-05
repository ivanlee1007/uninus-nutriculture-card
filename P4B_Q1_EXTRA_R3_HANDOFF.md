# P4b Q1 額外 R3/3 交接

## 結果（非 review approval）
僅修 quality owner：以捕捉時 primitive principal ID / admin / active 綁管理快取、同步 anchor、draft baseline、操作與 reply 接納。相同 user 物件原地降權／換 ID，hass setter、render、request/accept 邊界同步清 management DTO、baseline、private draft；舊 owner 晚回覆／自動 follow-up 不得復活。非 admin、inactive、無 user 不發 quality management mutation/read。重新 admin 必須 fresh GET。
保留同 principal 合法 transport 換線 draft/CAS；baseline 綁 principal 而非整個 transport owner，以免誤阻既有 Save。未 settle flight 依 exact entry/op 保存；obsolete flight 實際結束後僅重畫當前 UI，不清別 entry 新操作。普通 standalone native readonly True 不禁止。

## 修改範圍
- `uninus-nutriculture-card.js`：只 qualityWritable 周邊 principal helpers 與 quality draft/update/converge/render/request。
- `tests/p4b_browser.py`：FIXTURE 增 primitive user metadata；追加 test18–21 與 Q1 helper。
- 本交接文件。
`tests/check.py` 未改（自動 AST discovery 已收新 cases）。原17個 test methods AST 全相同；test04 不改。JS quality DTO/policy/native validators、static getConfigElement 起之後全部 bytes 原樣；recipe/Number/P3/backend/wire 未動。

## RED / GREEN 與真回歸
- 先用質審原 desired assertion + 真 captured native grant，在原 JS `9759de6d...` 取得 loaded-cache behavioral RED，再做最小修正 GREEN。
- 新 test19/20/21 是相鄰補充驗證；最終 fixture 在原 JS owned overlay 重播三項皆 behavioral FAIL，不冒稱它們早於首次實作。
- 另獨立 exact-after-release probe：hold 已產生 reply，same callWS/connection，原地降權後 release exact object；原 JS 真 RED、最終 JS 真 GREEN，沒有原質審 transport-swap 誤證。
- canonical `C:/Program Files/nodejs/npm.cmd test` 最終 `canonical-03`：unit14、legacy38、P4a16、P4b21（原17+4）全 PASS；六 child returncode0；0 skip；browser teardown pageerrors0。Node 實測 v18.6.0，Chromium 156.0.8078.4（既有 chromium-1248）。所有 gate snapshot hash 與 final source 相同。
- own Save epoch handover、finite coalesced GET、dirty typing focus/CAS、transport resolve/reject、不同 entry operation 隔離均由原測試實跑。

## 如實保留的中間失敗
write_file adapter JSON decode 未寫入，改 owned Python 寫檔。第一 canonical cmd quoting 失敗；第二 canonical 暴露 baseline 綁整個 transport owner 誤阻原 test06/13，已只改為 primitive principal baseline，原 asserts 未改。初始 Q1 held fixture 在 capture transport 自己 push 時換 user 物件、且 transport-swap block token 使 fresh GET 無法接納；修正 owned/new helper 初始化，完整保留所有 attempt。舊 quality 的「held control PASS」從未視作 same-transport 證明。

## Source scope / byte drift
F2 manifest `8de0b9bd...` 全6624 frozen hashes 仍 match。D 對 F2 差兩個本輪 Card 檔，另 backend `tests/test_p4b_native_safety_matrix.py` 有既存 CRLF/LF byte 差（normalized text 完全相同；本輪未寫／未執行該檔）。**不得宣稱 D 全6624 bytes 不變**；parent successor 必須從 F2 明列 manifest 加本輪 Card delta，保留 F2 backend bytes，禁止 recursive D 複製。見 currentSource-all-inputs.json / development-byte-drift.json。

## 證據與後續
全部 raw/source/script/child receipts 在 `../_frontend-q1-extra-r3`，FINAL.json / SEAL.json 僅封 closed safe artifacts，無 runtime/.storage/auth/capability。最終 JS SHA256：85304603e7870baa1d31ac27f74f11b206d1a0cac24bfe281c8a1bf308c41798。
這是 shipped Chromium mock/captured-native replay，不是新 live Auth/Core join；未證明或聲稱 backend ACL bypass、actuator I/O、獨立 APPROVED。父端仍須 freeze successor → affected SPEC → quality 復審 → final source-bound affected live；不重做未變 backend432。不自行修 Minor README；used3/limit3，無第4輪。可於 parent 另行授權後整理此 primitive-owner/late-reply workflow 為 skill，本輪不寫 scope 外技能。
