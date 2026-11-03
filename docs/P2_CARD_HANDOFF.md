# P2 Card handoff — 0.2.0-alpha.1

## Delivered

- The shipped root JS accepts schema 1 / shadow unchanged and schema 2 / control explicitly; schema 2 / shadow and unknown contracts fail closed.
- v2 displays authoritative flow_state, fault and run_id. Five mapped native controls call only `switch.turn_on`, `switch.turn_off`, or `button.press` with the exact mapped Entity ID. No direct domain start service, config_entry_id, raw output, scheduler or stage_link.
- Every action rechecks the latest schema/mode, flow consistency, map, domain, available Entity state, and refill capability where applicable. Switch state must be on/off. A native Button's initial `unknown` state is usable (it has no prior press timestamp); missing/unavailable Buttons are not.
- Successful service settlement does not modify Entity state or fabricate output feedback. Visible submission/readback wording and escaped rejection details remain separate from authoritative state.
- Per-target unresolved transport locks survive equivalent configuration, disconnect and remount. Epoch and row-operation identity fence stale completion; remapping invalidates the old row owner. Reconfiguration/disconnect clears scoped notices without releasing unresolved transport locks. A new target can act while an old target settles.
- Ten metadata-driven single-Number editors, dirty-draft binding, focus, disclosure and all P1 safety behavior remain. v2 help text warns that refill limits/timeouts are checked by the backend rather than claiming all time values are inert.
- Offline demo retains all original scenarios and adds v2 simulated refill/run, emergency stop/reset, and rejected operations. It mutates memory only and labels all calls as simulation. No network/HA credentials or external HA access.
- Version synchronized in package.json and root JS header. Picker/editor copy distinguishes v1 shadow from v2 native control. Stub discovery recognizes actual v2 control Sensors.

## Executed verification

Command (repository root, existing native Windows virtualenv):

```bash
CHROMIUM_EXECUTABLE='C:/Users/ivanl/AppData/Local/ms-playwright/chromium-1248/chrome-win64/chrome.exe' .venv/Scripts/python.exe tests/check.py --evidence docs/evidence/p2-06-canonical-green
```

- Native Node **v18.6.0**: syntax passed; **9/9 Node tests**, zero failed/skipped/cancelled. Node emits its existing experimental test-runner warning.
- Local browser interpreter: **Python 3.14.5** from `.venv/Scripts/python.exe`; `compileall -q tests` passed. Added-line static scans found no secret assignments, shell/eval/deserialization sinks or innerHTML writes. These scans are supplementary, not an independent security approval.
- GitHub workflow targets Node 22 / Python 3.13 on Ubuntu. That hosted matrix was **not run here**; no exact-head CI or independent parent review claim is made.
- Real Chromium **156.0.8078.4**: **23/23 browser tests**, zero failures/errors/skips; page-error capture remained empty.
- `tests/check.py` already discovers/counts test methods and Node declarations dynamically. It is unchanged: the recorded canonical result explicitly proves expected/executed **9/9** and **23/23**, not the old fixed 5/16 figures.
- Original **5 Node tests and 16 browser test methods are source-identical to HEAD**; verified programmatically against Git. Added probes are supplementary rather than replacements.
- v1 geometry retained at 320/768/1200; v2 adds both light/dark at all three widths (six persisted scenarios). v2 card widths 304/752/1184, no overflow/outside elements, control buttons >=64px wide and >=40px high. Screenshots and measured geometry are in the canonical evidence browser directory. Node/focus/disclosure continuity tested across repeated live updates.
- Version consistency, six-scenario geometry inventory, child return codes and original-test preservation checked separately. `git diff --check` passed (Git also prints ordinary LF/CRLF normalization notices).

## Evidence and provenance

All existing `p2-01-display-{red,green}` and `p2-02-actions-red` directories were preserved.

- `p2-02-actions-green`: completed test18 mapped-action behavior.
- `p2-03-lifecycle-red`: retained initial harness error (Playwright auto-called an assignment-returned function); **not behavioral RED**.
- `p2-03-lifecycle-behavior-red` -> `p2-03-lifecycle-green`: actual stale previous-slot rejection notice reproduced and fixed. Test19's boundary matrix passed immediately and is supplementary verification, not a claimed new RED.
- `p2-04-demo-geometry-red` -> `p2-04-demo-geometry-green`: actual undersized native control buttons and missing v2 demo reproduced, then corrected. Test21 was already-green supplementary lifecycle coverage. The older recorder captured JS/tests but **did not snapshot demo HTML in that RED run**; the unchanged baseline demo was contemporaneously read in the tool transcript and is available in HEAD. Do not misrepresent it as a demo snapshot captured during RED. Recorder now includes demo HTML for subsequent captures.
- `p2-05-stub-red` -> `p2-06-canonical-green`: native Node reproduced v2 stub falling back to an unrelated default; corrected discovery passed. Other new Node boundary tests were already-green supplementary coverage.

Each new evidence directory is distinct and retains raw child output, exact captured snapshots, command and hashes. Do not overwrite historical evidence for reruns.

## Limits / parent integration gate

This is Card-only offline verification. Browser `callService` transport is synthetic, not native HA backend acceptance. Parent must separately exercise shipped Card events through actual isolated backend native handlers and validate frozen-wire interoperability. Backend authorization, commissioning, registry identity, source validity, output closure, deduplication and run execution remain backend responsibilities; the frontend is not an authorization boundary. No physical-device or external-HA claim is made.

Unresolved calls retain their target lock until actual transport settlement; there is intentionally no UI timeout that pretends to cancel a dispatched write. Service acceptance is not output readback confirmation. P2 remains refill-only; nutrient/acid/standalone mix are unsupported and irrigation permission remains absent.

No backend, README, shared specification or frozen P2 contract was changed. No commit, push, release, deployment or external HA connection was performed. The preexisting untracked `docs/P2_CONTROL_CONTRACT.md` is retained untouched for the parent's ownership decision.
