# FRONTEND SRC KNOWLEDGE BASE

## OVERVIEW
Application source for route shells, pages, feature components, hooks, and API services.

## STRUCTURE
```text
frontend/src/
├── pages/       # Role dashboards + user journeys
├── features/    # Domain UI clusters (authority, worker, common)
├── components/  # Shared UI and route guards
├── hooks/       # Auth/session state and reusable logic
├── services/    # API/auth clients
└── test/        # Vitest helpers/setup
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Add route | `App.jsx` | Keep role guards and nesting consistent |
| Auth context updates | `hooks/useAuth*` | Source of current user/session state |
| API behavior changes | `services/api.js` | Retry/refresh queue and credentials |
| Citizen UX flow | `pages/citizen/*` | Report + my reports journey |
| Authority/worker UX flow | `features/authority/*`, `features/worker/*` | Operational workflows |

## CONVENTIONS
- Prefer feature/page composition over large monolithic components.
- Keep side-effecting API calls in `services/` and consume via hooks/components.
- Preserve React Query provider usage from `main.jsx` when adding data hooks.

## ANTI-PATTERNS
- Avoid duplicate auth state sources outside `hooks` + service layer.
- Avoid direct `window.location` redirects except established auth/logout flow points.
- Avoid hardcoding backend host URLs inside components.
