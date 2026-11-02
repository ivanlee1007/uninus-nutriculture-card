# Incomplete initial lifecycle harness attempt

The original `tests/record_run.py 04-lifecycle-red BrowserTests.test_04_old_completion_cannot_touch_reconfigured_draft` invocation exceeded its 150-second subprocess timeout.

The original capture implementation buffered output and did not persist child stdout/stderr on timeout. Only its genuine pre-execution snapshots remain in this directory. This attempt is incomplete harness evidence, NOT behavioral RED; no output has been reconstructed or invented.

The test evaluation was corrected to a block-bodied function without returning the assigned deferred service function. The capture runner was changed to file-backed output and owned-process-tree timeout cleanup. The next run is preserved separately in `../04-lifecycle-red-retry/` and fails the real assertion that the newly configured tank should not remain locked by the old lifecycle. `../04-lifecycle-green/` records the fix.
