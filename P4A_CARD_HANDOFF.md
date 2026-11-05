# P4a Card handoff — candidate, not release

## 結果
已在 root shipped JS 加入完整參數配方區：首次開啟讀取 / Refresh、以目前 authoritative DTO parameters 新增、穩定 UUID 選擇、名稱及 10 參數編輯、Save、Apply、Cancel、Delete 第二確認（可 Escape 取消）。Save 只 catalog；Apply 使用雙 revision 與 recipe_id 一個原生呼叫，不直接寫 Number / pump，不修改 hass.states。名稱/歷史全 textContent；同名 option 顯示完整 UUID；last_applied 明確為歷史且 false matches 顯示「與現值不同」。

只在有效 S5 settings_target + callWS + 四服務存在時掛載 UI；不支援 host 完全移除此區，舊操作照常。S1–S5 validators/allowlist 及 header/version 前綴與原檔逐字相同。只有 root shipped JS，無 dist copy 需同步。

嚴格 DTO 8keys、version/target、safeinteger revisions、拒 revision 回退、UUID32、唯一 IDs、最多100筆、完整10參數 range/step/low<high、last snapshot 與 match 一致性。所有 RPC 讀 result.response。entry/generation/epoch/operation/transport fences；transport flight 鎖持續到 promise 結束；telemetry 不重新抓 catalog、不重建輸入，draft/focus 保留。CAS 失敗不 refresh、不重送。

## 本 writer 變更
- uninus-nutriculture-card.js
- tests/p4a_browser.py（11 個真 Chromium cases，fixture transport，不是 native HA）
- tests/p4a_capture.py（local pinned audit capture runner）
- tests/check.py（註冊新獨立suite、case count驗證、可指定 sibling evidence 路徑）
- P4A_CARD_PROGRESS.md / P4A_CARD_HANDOFF.md

父層已改的 README / docs 狀態文件未由我編輯。原庫/後端/凍結 contract/歷史 guards 未寫；459 historical evidence files 對 readonly original byte 相同。

## 真正測試與 provenance
最終執行：`npm test`（PATH prepend 原 Card .venv/Scripts；CHROMIUM_EXECUTABLE 指定既存 chromium-1248；CARD_TEST_EVIDENCE_DIR 指到 sibling `_card-work/14-npm-final`）。
- Node v18.6.0；原 Node TAP **13/13 pass，0 skip/cancel/todo**。
- Chromium 156.0.8078.4；原 Playwright **38/38 pass，0 skip**。
- 新 Playwright **11/11 pass，0 skip**：完整 save/select/edit/apply/cancel/delete；雙 catalog/settings CAS；兩 Card 競爭；同名IDs/XSS；320px keyboard/node/focus/geometry；closed DTO / regressed revisions；換槽 late success/error；disconnect；缺能力 legacy。
- 各 child exit=0，check.py AST expected/executed count 完全相符。不是把 file wrapper 算 case。
- 最終原始 TAP / browser logs / result.json / source+test bytes：`../_card-work/14-npm-final/`。
- shipped JS SHA256：`b78b5057c02ada12ee5ee9c107b129275126d6e465a9d7f7e71ef6865cb0eb2a`；與 gate snapshot 哈希一致。請 parent 最後記新 identity，沒有改 historicalP3 hash 去規避。

RED→GREEN（各有當時 source/test 完整 bytes + raw child log + exit）：
1. 01-save-red：使用 transport-only UI scaffold 真 click Save 後 catalog 長度仍0（AssertionError）→02-save-green。
2. 03-lifecycle-red：真 select New 後 name 仍舊值→04-lifecycle-green（2 cases）。
3. 06-boundaries-red-corrected-harness：disconnect 後 busy owner 未釋放→10-npm-test green（8新 cases）。07/08 雖目錄名有green，但真 child=1；完整保留、不冒稱綠燈。
4. 13-revision-red：有效非負但回退 revisions 接受並清草稿→14-npm-final green（11新 cases）。
額外新 probe 立即通過者僅為 supplementary verification，不冒稱原始 RED。

## 問題與界線
- 05-boundaries-red 是 fixture evaluate 回傳 Promise 導致 harness timeout；外層90秒中止，無完整 result.json，**不是 behavioral RED，不計完成測試**。06 修正 evaluate 明確 void wrapper 後取得真正 disconnect RED。
- 09-npm-test 原38 suite 有13 locator errors/1 assertion fail，因 hidden recipe subtree 仍存在；修正不支援 host 不掛載新 subtree，未修改既有tests或guards；10/12/14 均原38綠燈。
- 隔離樹沒有 .git；git diff 檢查不可用，未冒稱通過。以來源/fixture snapshot及readonly original byte比較驗證範圍。
- 所有 browser 顯式 close；未啟動 HTTP listener。owned-process-cleanup.json 顯示 exact p4a capture/browser suite 0 matching processes，沒有殺其他 writer。
- 真 registered Core / ACL / Store正常關閉讀回 **留 parent 在雙 writer freeze 後接線測試**；本組 fixture catalog 僅模擬 frozen API，不能稱真 HA或硬體接受。
- 未跑後端335 / S5 realbridge（backend peer 正在寫）；未進行整合SPEC→品質，P4a repair預算仍0/2未消耗。完整P4/P5/實機 commissioning 保留。
- 無 install/network/siteHA/auth/stage/commit/push/tag/release/deploy。
