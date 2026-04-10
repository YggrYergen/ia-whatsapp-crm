# Phase 5A Simulation Report

- **Date:** 2026-04-10 08:46:28
- **Target:** `http://localhost:8000`
- **Total Duration:** 95094ms
- **Result:** 9/9 passed, 0 failed

## Scenarios

| # | Scenario | Status | Duration | HTTP Codes | Notes |
|---|----------|--------|----------|------------|-------|
| | 1_happy_path_single_text | ✅ PASS | 1985ms | 200 |  |
| | 2_tool_trigger_booking | ✅ PASS | 625ms | 200 |  |
| | 3_tool_trigger_escalation | ✅ PASS | 656ms | 200 |  |
| | 4_clinical_keyword_force_escalation | ✅ PASS | 703ms | 200 |  |
| | 5_status_only_webhook | ✅ PASS | 1469ms | 200, 200 |  |
| | 6_malformed_payloads | ✅ PASS | 4109ms | 200, 200, 200 |  |
| | 7_rapid_burst_same_user | ✅ PASS | 2422ms | 200, 200, 200, 200, 200 |  |
| | 8_multi_user_concurrent | ✅ PASS | 781ms | 200, 200, 200 |  |
| | 9_edge_cases | ✅ PASS | 12344ms | 200, 200, 200, 200, 200 |  |

## Next Steps

- [ ] Check Sentry dashboard for expected error events (scenario 6)
- [ ] Check Discord for alert notifications (scenario 6)
- [ ] Check dev frontend for simulated conversations
- [ ] Run `cleanup.py` to remove simulation data from dev DB