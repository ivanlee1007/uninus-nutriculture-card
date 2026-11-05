# P4a SPEC-01 repair r1 — implemented, pending independent review

- 本輪 **1/2**，P3歷史4/4不動；唯一 SPEC-01，非 SPEC/quality 自行批准。
- 原 JS `b78b5057c02ada12ee5ee9c107b129275126d6e465a9d7f7e71ef6865cb0eb2a` → 最終 JS `68551485d4c83b9cb24b622c2275fa4f53b46455a517a661d3d0b2107bdbd360`。
- 產品僅修改 root `uninus-nutriculture-card.js`、`tests/p4a_browser.py`；新增本交接及 `_spec01-repair-r1/` owned 證據。backend、原兩庫、frozen、既有 evidence/contract 均未改。

## 最小修正

名稱 DTO（含 last_applied）與 draft 共享 Unicode code-point 計長，與 Python len(str) 一致；不是 grapheme，不 normalize、不重寫名稱。移除 HTML UTF-16 maxlength，改由原 draft guard 嚴拒超過80 code points，避免將貼上的 astral81 靜默截成可送出的80。trim、C0、UUID、數值及整包 DTO fail-closed 原保護保持。

永久 browser 新增2 cases（12/13）：ASCII80／🌱80／BMP+astral80 可整庫 load、edit、save、select、apply、delete；歷史合法 Unicode 與同庫其他配方可用。81字真 fill 不截斷且不發送，另驗 DOM 強制 overflow、DTO/last_applied 81字與 C0/trim 拒絕。分解重音80/81證明非 grapheme／未 normalize。

## 真 RED → GREEN

證據均相對 `_spec01-repair-r1/`：
- `REDBYTES/` 保存原 b78 JS + 新測試 bytes；`red-native-dto-valid-harness.log` 保持原 SPEC probe/assert，只有輸入路徑替換：exit1，Unicode loaded=false，ASCII positive loaded=true。原 native DTO/state bytes 複製未修改。
- `red-permanent-behavioral.log`：13 cases，原11全綠，新2出3個行為 assertion failures（catalog拒絕、astral80/mixed80輸入截斷），exit1。
- 初試 maxlength160 的真貼上81回歸再 RED：`input-red/`、`red-81-paste-no-truncation.log`，exit1；最終移除 code-unit cap，保持 code-point guard。
- 最終 `GREENBYTES-final/canonical-final/`：canonical **npm test exit0**，所有 child raw exits0。**Node13、legacy browser38、P4a browser13（原11＋2）分開報，各0skip**；Node18.6.0、Chromium156.0.8078.4。`green-final-native-dto.log` 原 probe exit0，Unicode與ASCII都loaded=true／3 options。
- 輸入來源、commands、raw exits、每階段 bytes/hash 及最終 canonical11 inputs snapshot 均保留，見 `receipts.json`、`source-pre/post.json`、`changed-inputs.json`、`FINAL.json`。

## Affected native joint 真重跑

沿既有 attempt5 scripts 複製 fresh owned 根，backend production/fixtures保持同hash；30 actual imports逐一對候選，見 `joint-imports-verified.json`。只在owned browser harness補 details toggle 後等待 recipeData（原 pending0 可能早於 toggle event）；所有原 assertions 保留。

- **最終 JS** `joint/attempt5/`：原16 requests／10 checkpoints，parent/browser exits0。
- **最終 JS** `joint/attempt4/`：28 requests／13 checkpoints，包含原16及真正 production registered API 產出的 ASCII80／astral80／mixed80 → shipped consumer Save/edit/select/Apply/Delete/history；保留其他配方、zero I/O、正常 STOP＋fresh SDK process完整options/10Numbers讀回。不是 fake catalog 或唯讀 replay 冒充 joint。
- `joint/attempt4` 與 `attempt5` 的 wire/result/commands/imports/browser source/readback 為確切證據；不可把原 b78 joint 當新JS批准。full native378 未重跑，backend沒變。

## 誠實保留的 harness/environment 失敗

最早 RED copies 少 build parent／fixture 的失敗非行為RED；後來合法setup反例另存。一次 npm 被環境 Node26 reporter造成 canonical計數parser拒絕（unit實際13 pass），已用原Node18 PATH完整重跑。joint初次因 toggle非同步尚未發GET，補owned同步等待後再跑，未改產品來迎合harness。舊 logs 全保留。

## 完整性與下一步

- 原獨立 review **21 sealed artifacts** 及其整個目錄前後hash一致；`review-before.json`／`review-after.json`。
- frozen **6595 files** 全hash重核無差異；MANIFEST `a4b831399f8bdb0bde132fd6b4da4e93e3fac14672d9f6ebda21a0b14a015589`，`frozen-readonly-verification.json`。
- 封存白名單排除 runtime `control-ha/`、`.storage/`、auth、open stdout；不把認證資料archive。
- parent應 freeze successor，再獨立 affected SPEC → quality；本交付不宣稱已通過審查或發布。無commit/push/install/siteHA/auth/hardware/tag/release/deploy。
