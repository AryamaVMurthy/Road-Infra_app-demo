# FRONTEND TESTS KNOWLEDGE BASE

## OVERVIEW
Playwright suite validating OTP auth persistence, role journeys, analytics behavior, and lifecycle rigor.

## WHERE TO LOOK
| Scenario | Location | Notes |
|----------|----------|-------|
| Core e2e smoke | `e2e.spec.js`, `final_verify.spec.js` | Baseline cross-role checks |
| Auth/session behavior | `auth_persistence.spec.js` | Cookie-based auth persistence |
| Citizen journey | `citizen_rigor.spec.js` | Report + tracking assertions |
| Authority/worker lifecycle | `lifecycle_golden_thread.spec.js`, `worker_rigor.spec.js` | Transition and evidence workflows |
| Analytics coverage | `analytics_e2e.spec.js`, `universal_analytics.spec.js` | Public + admin analytics expectations |
| Test data helpers | `helpers/` | DB/API helper utilities |

## CONVENTIONS
- Tests exercise full UI and backend integration, not mocked browser-only behavior.
- Use helper modules in `helpers/` for repeatable OTP and DB-assisted setup.
- Keep assertions deterministic and state-based, not timing-only.

## ANTI-PATTERNS
- Do not hardcode brittle waits when deterministic selectors/state checks exist.
- Do not bypass login helper flow with token injection.
- Do not duplicate helper logic across specs; centralize shared setup.

## COMMANDS
```bash
cd frontend
npx playwright test --reporter=list
npx playwright test tests/lifecycle_golden_thread.spec.js --reporter=list
npx playwright test tests/auth_persistence.spec.js --reporter=list
```
