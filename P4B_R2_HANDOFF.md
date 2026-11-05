# P4b frontend R2/2 handoff — C/D only, not approval

## Outcome
- C: legitimate owned source-policy Save now transfers a separately checked acceptance fence only after full valid native/service agreement: same entry, operation, owner, callWS, connection; exactly one epoch-generation advance; submitted changed sources/policy; policy revision +1; unchanged settings/flow CAS; advanced observation. Original captured first Save now automatically GETs and acknowledges revision1/source confirmations without manual Refresh. Epoch changes alone never transfer ownership.
- D: open combined panel coalesces native observation advances into read-only GETs. One unresolved flight per entry; at most one attempt per observation token; latest-token follow-up after a delayed GET; no timer polling, mutation retries or browser authority. Failed reads clear display data; a separately owner-bound last-accepted DTO is only a convergence anchor, not displayed authorization. Dirty draft, original three CAS, DOM nodes and focus remain preserved.
- Display keeps the original native/API entry+epoch+observation join, with additional blocked-token gate. Successful read acceptance requires full native/API DTO equality. No old strict validator, recipe, Number, backend or wire changes.

## Product paths / final SHA256
Root: `C:/Users/ivanl/.hermes/cache/scratch/nutriculture-p4b-isolated-development/uninus-nutriculture-card`
- `uninus-nutriculture-card.js`: `9759de6ddc03e2c98913b836754ed260b3890aa1e03d292fecad0287d7dc74e3`
- `tests/p4b_browser.py`: `8faedaeb4bc9b04f329a74f7b16270c757b59c64cced2c9dc986f0b773b79a89`
- `tests/check.py`: `a759649c2460c12481ef6ccbd4af855fce649769869dfe99b1da96aa980106ae` (adds explicit capture inputs to snapshot only; dispatch/count validation unchanged)
- New exact captured inputs `tests/p4b_r2_capture/{events.json,wire.json,grant.json}` copied from J attempt5, hashes respectively `8f7b612bfb2e38fc2e9ecce98b8cb382bee658aa038e4245fa5800c0ee2ccf74`, `0cc10f8963bdbfcb97f51000e7d0231f90a12e20569acf5fc78aab70d1b14407`, `279d0e1636ae8de83ced4419200604af0dae3f7341ad470451fa52ec7e22cf9c`.

## Executed evidence
OWNED: `C:/Users/ivanl/.hermes/cache/scratch/nutriculture-p4b-isolated-development/_frontend-repair-r2`
- `red-cd/`: actual pre-implementation RED on original JS SHA `585b66095d502a1f5ee99675a35e34bad04ec0d5c351c3631d3f835f063ffe10`: C missing automatic GET assertion; D no obs65 convergence (timeout). Full executed source/test snapshots, raw log and child rc1 retained.
- `green-cd/`: first corrected C/D run 2/2, rc0.
- `old-red-final-02/`: final permanent test bytes replayed against original JS in an explicit-input owned tree. Actual 2 tests, 2 behavioral assertion failures, rc1: C GET/Save only instead of GET/Save/GET; D cache35 != native65. `baseline.py` is the reproducible runner. The preceding `old-red-final/` is a retained **harness failure** (missing fixtures/p3a.json), not RED evidence.
- `expanded/`: preserved intermediate run; original test05 caught unrelated over-strengthened display equality (restored original version join, no old test edit); test13 initially held the wrong transport function (owned fixture corrected). Neither failure hidden.
- `canonical-final/receipt.json`, `canonical-final/raw.log`, `canonical-final/canonical/result.json`: final actual `npm test`, outer rc0, all 6 child returncodes0. Node **v18.6.0**; Chromium **156.0.8078.4**. Node 14/14 (case count, not Node14 runtime), legacy browser38/38, P4a16/16, P4b17/17; zero skips. Final source hashes rechecked against all canonical consumed snapshots.
- Final C/D raw actual cache/native/baseline/dirty/requests/DOM/notice/page_errors: `canonical-final/canonical/browser/C-after-first-save.json` and `D-after-native65.json`; both page_errors `[]`.
- Canonical raw SHA256: `216f3683cae0b9c68f1d64ff13ef8772021f950c8568ce86f80f444346ebdf17`.

Commands (cwd selected by runner to the exact Card root):
```
"D:/UNiNUS Projects/AI project/uninus-nutriculture-card/.venv/Scripts/python.exe" -B <OWNED>/run.py canonical-final
"D:/UNiNUS Projects/AI project/uninus-nutriculture-card/.venv/Scripts/python.exe" -B <OWNED>/baseline.py
```
These named output directories already exist and are immutable run receipts; change output directory before an independent rerun. `run.py` dispatches actual `C:/Program Files/nodejs/npm.cmd test`, not an imitation gate. All env/runtime/cwd/commands recorded in runner and receipts; pre-existing original venv used without installs.

## Permanent tests / sourceSelfScope
- Added cases11–17: captured legal epoch Save; captured dirty three-truth convergence; five rejection interleavings (remount, connection, callWS, other epoch, wrong policy revision); delayed GET coalescing/latest/lock; PRIVATE read error/no same-token retry; dirty native policy CAS conflict; event-driven revoke-to-False. Revocation case is explicitly a **derived DTO boundary**, not a newly captured native revoke.
- Original P4b AST comparison changes only parent-approved `test_04_dirty_keyboard_320_and_no_poll_io`: replaces blanket calls1 with exact bounded GET2, quiescence and reads-only assertions, retaining keyboard/node/focus/320px/noGrant/writes0. All nine other original methods and setup/teardown unchanged. No original Node/legacy/P4a cases removed or weakened.
- JS changes confined to independent quality methods between initQuality and qualityRequest; old validators/recipe/Number untouched. check.py only includes the three new capture fixtures in its source snapshot inventory.
- Full frozen G MANIFEST **6617** files and original J seal **63** artifacts rehashed after execution: zero hash/size changes. Adjudication REPORT's referenced original inputs likewise unchanged. Original JS before SHA585b…; final SHA9759… above.

## Boundaries / pending
Evidence is **CAPTURED_NATIVE_REPLAY_NOT_LIVE_JOIN**, with exact original native request equality (except original native id), service context/response envelopes and full native DTO snapshots. Historical DTO timestamps are validation/display data, not a claim of current authorization. No new Core/auth/device/live HA deployment or new native join was executed. Parent still must perform final new-bytes native live join, backend R1 integration verification and any pending held-closure/two-slot/full-SPEC gates. This local green does not close those or authorize release. No third repair round, Git/tag/deploy, API/schema/frozen-doc change, backend source access/edit, original repository write or old evidence rewrite.
