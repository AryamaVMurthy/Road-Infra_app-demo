# FRONTEND KNOWLEDGE BASE

## OVERVIEW
React 18 + Vite SPA with role-based routes, cookie-auth session flow, and map/analytics-heavy dashboards.

## STRUCTURE
```text
frontend/
├── src/            # Application code
├── tests/          # Playwright E2E + helpers
├── package.json    # Dev/build/test/lint scripts
└── vite.config.js  # Dev server + API proxy behavior
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Route/auth shell | `src/App.jsx` | Role-gated route tree via `PrivateRoute` |
| App bootstrap | `src/main.jsx` | BrowserRouter + QueryClientProvider wiring |
| HTTP client/auth refresh | `src/services/api.js` | `withCredentials` + 401 refresh queue |
| Auth actions | `src/services/auth.js` | OTP login/logout/me wrappers |
| E2E flows | `tests/*.spec.js` | Full user lifecycle and rigor checks |

## CONVENTIONS
- Use cookie/session auth model; browser sends cookies automatically.
- Keep API calls centralized in `src/services/` rather than page-level `fetch` calls.
- Keep role-protected pages behind `PrivateRoute` wrappers.

## ANTI-PATTERNS
- Do not store access tokens in localStorage/sessionStorage.
- Do not bypass the refresh queue in `src/services/api.js`.
- Do not add new protected pages outside existing role route groups.

## NOTES
- `VITE_API_URL` overrides default `/api/v1` base path.
- Unit/integration tests run with Vitest; browser rigor tests run with Playwright.
