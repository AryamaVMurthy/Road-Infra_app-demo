# BACKEND TESTS KNOWLEDGE BASE

## OVERVIEW
Integration-first pytest suite validating auth, RBAC, workflow transitions, media evidence, and security controls.

## WHERE TO LOOK
| Scenario | Location | Notes |
|----------|----------|-------|
| Shared fixtures + DB overrides | `conftest.py` | Creates isolated test DB and FastAPI dependency overrides |
| Auth and cookie behavior | `test_auth_http.py`, `test_auth_overhaul.py`, `test_csrf.py` | OTP, session, CSRF, refresh behavior |
| Lifecycle invariants | `test_workflow_machine.py`, `test_rigor.py` | Assignment/accept/resolve/approve/reject constraints |
| Role matrix checks | `test_rbac_matrix.py` | Explicit role/action contract checks |
| Analytics integrity | `test_analytics_accuracy.py` | Status/category split correctness |

## CONVENTIONS
- Prefer full request flow tests over isolated unit stubs.
- Use `login_via_otp` helper to mirror production auth flow in tests.
- Keep assertions explicit about state transitions and audit writes.

## ANTI-PATTERNS
- Do not use production DB connection in tests.
- Do not bypass fixtures to create ad-hoc app/session wiring.
- Do not weaken tests by asserting only 200 status when state checks are required.

## NOTES
- Tests assume PostGIS availability and table truncation between cases.
- MinIO init occurs via fixtures; preserve fixture ordering when extending.

## COMMANDS
```bash
cd backend
python -m pytest tests -v --tb=short
python -m pytest tests/test_workflow_machine.py -v
python -m pytest tests/test_rbac_matrix.py -v
```
