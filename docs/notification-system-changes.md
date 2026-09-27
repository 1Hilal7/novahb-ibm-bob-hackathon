# LLM-Powered Notification System — Change Summary

## Files Modified

### `frontend/src/api.js`
- Added two new exported async fetch functions:
  - **`fetchNotification(developerId)`** — calls `GET /notify/{developer_id}` to retrieve the list of AI-generated questions for a developer.
  - **`submitNotificationAnswer(developerId, optionId)`** — calls `POST /notify/{developer_id}/ask` with `{ "option_id": "..." }` and returns the LLM-generated answer.
- Both functions throw a descriptive `Error` on non-ok HTTP responses, consistent with the existing functions in the file.

---

### `frontend/src/App.jsx`
- **Imports** — added `useCallback` to the React import; added `fetchNotification` and `submitNotificationAnswer` to the `./api` import.
- **New `NotificationPanel` component** — see details below.
- **`backendError` state** — new `useState(null)` to track backend reachability failures.
- **`impactReport` initial state** — changed from `mockImpactReport` to `null` so the app no longer silently pretends live data is present on first render.
- **`loadImpactReport`** (mount-time effect) — replaced silent mock fallback with `setBackendError(…)`.
- **`handleAnalyze`** — replaced mock fallback and artificial delay with `setBackendError(…)`; clears the error state at the start of each new attempt.
- **`projectNodes` / `fullNetworkNodes`** — added `developerId` field to every developer `detail` object so the inspector can pass it to `NotificationPanel`; added a null-guard for the case where routes are not yet loaded.
- **Error banner** — rendered between `<header>` and `.workspace`; shown whenever `backendError` is set, dismissible with ×.
- **Node inspector** — `NotificationPanel` is now rendered at the bottom of the inspector whenever the selected node is of type `Developer`.

---

### `frontend/src/App.css`
- Added `.notif-panel` and related styles for `NotificationPanel` (question buttons, per-answer states, loading spinner, error text) — all using existing CSS custom properties from `:root`.
- Added `.backend-error-banner` and related styles for the full-width error banner, using the existing `--review` red token.

---

## How the Notification System is Integrated

The feature is triggered entirely through the existing graph interaction — no new navigation or dedicated page is required:

1. The user clicks any **developer node** on the Project Focus or Full Network graph.
2. The node inspector panel opens (existing behaviour).
3. `NotificationPanel` is mounted at the bottom of the inspector, receiving the clicked developer's `developer_id` as a prop.
4. On mount, `NotificationPanel` calls `GET /notify/{developer_id}` and displays up to 4 AI-generated questions as clickable buttons.
5. When the user clicks a question, `POST /notify/{developer_id}/ask` is called with the selected `option_id`; the LLM answer appears inline below the clicked button.
6. Multiple questions can be expanded simultaneously — each has its own isolated loading / answer / error state.
7. The inspector can be closed at any time with ×, which unmounts `NotificationPanel` and discards all in-flight requests via the `cancelled` flag.

### Loading & Error States

| Situation | What the user sees |
|---|---|
| Questions loading | Three pulsing brand-coloured dots |
| Questions failed to load | Red error message inside the panel |
| Answer loading | Button disabled + italic "Thinking…" |
| Answer received | Response text with a green left-border accent |
| Answer failed | Error text with a red left-border accent |

---

## How the Silent Mock Fallback Was Fixed

**Before:** both the mount-time `loadImpactReport` effect and the `handleAnalyze` function caught backend errors silently — logging a `console.warn` and substituting `mockImpactReport` as if nothing had gone wrong. The `dataSource` badge would show `MOCK DATA` with no further explanation.

**After:**

- `impactReport` now starts as `null` instead of `mockImpactReport`, so there is no implicit pretence of live data.
- When `fetchLatestImpact` fails on load, the code silently falls through to `analyzeChange` (the intended cascade — no cached report yet is not an error).
- When `analyzeChange` also fails, `setBackendError("Live backend is unreachable. No impact report could be loaded.")` is called.
- When the **Analyze Change** button is clicked and the backend is unreachable, `setBackendError("Live backend is unreachable. Analysis could not be completed.")` is called; the artificial 1-second delay and mock data substitution are removed entirely.
- A dismissible full-width **error banner** appears immediately below the top bar, making the failure explicit and visible to the user.
- The banner is cleared automatically at the start of any new successful request, so it disappears as soon as the backend becomes reachable again.
