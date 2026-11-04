# P3a Card local handoff — implementation verified, not delivered P3a

Source schema1/2/3 parser, native nutrient mapping, complete normal/dosing/weekday Apply/Cancel, revision readback, CAS conflict/epoch/pending isolation and responsive geometry are implemented. Root JS hash: 8cc5d7e3bbe1898f163b0057b703c1e348d0a623ae8c1511c20bfcff73ad3d9f.

- Original parser/UI RED/GREEN retained under p3a-card-01..04.
- p3a-card-05 failed old geometry because a hidden nutrient row was still in the internal map. The worker's surviving source already removes it for v1/v2; parent preserved the original five-button size/overflow checks and added exact-five-key assertion. p3a-card-06 retained the incomplete harness attempt. The new invalid-contract test now captures the actual old button before mutation, so removed-row negative checks truly click the stale node rather than failing on undefined private map access.
- p3a-card-07: Node10 / Chromium29 passed.
- Offline schema3 settings demo: p3a-card-08 genuine missing-mode RED; p3a-card-09 GREEN Node10 / Chromium30. Demo is memory-only, explicitly unsupported nutrient engine, and browser asserts no network requests beyond file resources.
- Actual JS/native group boundary is verified by backend docs/evidence/p3a-settings-bridge-03-final/. Frontend fixture-only nutrient/run examples are NOT a working backend dosing engine.
- No package/version bump, commit/push or original HA. A2 and joint independent reviews remain required. Issue#3 stays open.
